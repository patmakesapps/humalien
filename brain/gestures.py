"""Arm motion that follows what the robot is actually saying.

The shape of the idea is in PacedPlayback.is_speaking: the model finishes
generating a response about ten times sooner than the speaker finishes
playing it, so anything driven from `response.output_audio.delta` gestures
through a sentence the head has not said yet and then stops dead while it
keeps talking. The only place the audio and the wall clock agree is the
moment a chunk is released to the node, so that is where the envelope is
taken and that is what drives these arms.

WHO ENFORCES WHAT
-----------------
This file SHAPES motion. node/humalien_node/arms.py ENFORCES it - the
range clamp, the electrical sign flip, and the slew rate all live down
there, on the machine holding the servos. A bug here can make the robot
gesture badly. It cannot make it drive an arm into a hard stop, and that
separation is deliberate: the brain is the part that talks to the network
and the part most likely to be wrong.

The limits below are copies of cad/desk_bot.py, used to keep generated
poses sensible before they are sent. They are not the safety boundary.
"""

import asyncio
import json
import math
import time


# From cad/desk_bot.py. Positive is FORWARD on both arms; the node deals
# with the fact that the two channels are wired in opposite directions.
ARM_RANGE = (-20.0, 75.0)
ARM_REST = -8.0

# How loud a chunk has to be to earn a full-sized gesture. Speech sits well
# below full scale, so an envelope used raw barely moves the arms at all.
LEVEL_REFERENCE = 0.12

# Envelope time constants, in seconds. Attack is quick so a gesture lands
# with the syllable that caused it; release is slow so the arms ride over
# the gaps between words instead of dropping into every comma.
ATTACK = 0.05
RELEASE = 0.30

# Silence, in seconds without a released chunk, before the arms go home.
SILENCE_AFTER = 0.25

# The gesture itself. LIFT is how far both arms come up when talking at a
# normal volume; SWING is how far they then move against each other.
LIFT = 26.0
SWING = 14.0

# Beat rate of the alternation, in hertz. Slower than speech on purpose:
# this is the rhythm of somebody moving their hands while making a point,
# not one gesture per syllable.
BEAT_HZ = 0.45

# Radians of phase between the arms. Deliberately not pi - exact opposition
# reads as a mechanism keeping time rather than a person talking.
PHASE = 2.2

# How often a pose goes to the node. The node slews at 50 Hz between
# whatever targets it has, so sending faster than this buys nothing.
TICK = 0.05

# Degrees of change worth a message. Holding still should be silent on the
# wire rather than 20 identical poses a second.
DEADBAND = 0.4


def clamp(value, low, high):
    return max(low, min(high, value))


class Gestures:
    """Turns the playback envelope into arm targets and sends them.

    Feed it loudness from PacedPlayback; run() does the rest.
    """

    def __init__(self, websocket, log=None):
        self.websocket = websocket
        self.log = log

        self.raw = 0.0

        # Seconds since the last chunk was released, advanced by pose() on
        # the same clock it uses for everything else. Reading the wall clock
        # in here instead would leave the one path that matters - what the
        # arms do when the talking stops - impossible to test.
        self.since_audio = SILENCE_AFTER

        self.level = 0.0
        self.phase = 0.0

        self.last_sent = None

    def feed(self, loudness: float) -> None:
        """Called as each chunk of speech is released to the node."""

        self.raw = loudness
        self.since_audio = 0.0

    def pose(self, elapsed: float):
        """Advance the envelope and the beat, and return (arm_l, arm_r)."""

        self.since_audio += elapsed

        speaking = self.since_audio < SILENCE_AFTER
        target = clamp(self.raw / LEVEL_REFERENCE, 0.0, 1.0) if speaking else 0.0

        # Exponential follower. Attacking faster than it releases is what
        # keeps the arms from chattering between syllables.
        tau = ATTACK if target > self.level else RELEASE
        self.level += (target - self.level) * (1.0 - math.exp(-elapsed / tau))

        # The beat only advances while there is something to gesture about,
        # so speech always starts from the same place in the cycle rather
        # than wherever a free-running clock happened to be.
        if self.level > 0.01:
            self.phase += 2.0 * math.pi * BEAT_HZ * elapsed

        base = ARM_REST + LIFT * self.level
        swing = SWING * self.level

        return (
            clamp(base + swing * math.sin(self.phase), *ARM_RANGE),
            clamp(base + swing * math.sin(self.phase + PHASE), *ARM_RANGE),
        )

    def worth_sending(self, arm_l, arm_r) -> bool:
        if self.last_sent is None:
            return True

        return (
            abs(arm_l - self.last_sent[0]) >= DEADBAND
            or abs(arm_r - self.last_sent[1]) >= DEADBAND
        )

    async def send(self, arm_l, arm_r) -> None:
        await self.websocket.send(
            json.dumps({"type": "pose", "arm_l": arm_l, "arm_r": arm_r})
        )

        self.last_sent = (arm_l, arm_r)

    async def rest(self) -> None:
        """Put the arms down. Worth doing before the socket closes."""

        self.level = 0.0
        await self.send(ARM_REST, ARM_REST)

    async def run(self) -> None:
        if self.log:
            self.log("Gestures on - arms follow the speech")

        last = time.monotonic()

        while True:
            await asyncio.sleep(TICK)

            now = time.monotonic()
            elapsed, last = now - last, now

            arm_l, arm_r = self.pose(min(elapsed, TICK * 4))

            if self.worth_sending(arm_l, arm_r):
                await self.send(arm_l, arm_r)
