"""Body motion that follows what the robot is actually saying.

The shape of the idea is in PacedPlayback.is_speaking: the model finishes
generating a response about ten times sooner than the speaker finishes
playing it, so anything driven from `response.output_audio.delta` gestures
through a sentence the head has not said yet and then stops dead while it
keeps talking. The only place the audio and the wall clock agree is the
moment a chunk is released to the node, so that is where the envelope is
taken and that is what drives all four axes.

WHO ENFORCES WHAT
-----------------
This file SHAPES motion. node/humalien_node/arms.py ENFORCES it - the range
clamp, the electrical sign flips, and the slew rates all live down there, on
the machine holding the servos. A bug here can make the robot gesture badly.
It cannot make it drive the neck into a hard stop, and that separation is
deliberate: the brain is the part that talks to the network and the part most
likely to be wrong.

The limits below are copies of what the node enforces, used to keep generated
poses sensible before they are sent. They are not the safety boundary.

WHY THE HEAD IS NOT JUST SMALLER ARMS
-------------------------------------
The arms beat on the syllables. The head runs at about a third of that rate
and a fraction of the amplitude, because a neck that keeps time with speech
reads as a metronome wearing a face. Three things are summed into it:

  1. A slow sway and nod on the speech envelope - the head follows phrases.
  2. Where the face it is talking to actually is, via `look_at`. Gently:
     TRACK_GAIN is well under 1, so the robot turns TOWARD somebody rather
     than locking onto them like a gun turret.
  3. A very slow idle drift on two incommensurate periods, so a robot that
     is neither speaking nor tracking still looks like it is inhabited.

Nothing here ever stops moving completely. That is the point.
"""

import asyncio
import json
import math
import time

from websockets.exceptions import ConnectionClosed


# From cad/desk_bot.py. Positive is FORWARD on both arms; the node deals with
# the fact that the two channels are wired in opposite directions.
ARM_RANGE = (-20.0, 75.0)
ARM_REST = -8.0

# Mirrors node/humalien_node/arms.py, which mirrors what was observed on the
# assembled robot. See node/SERVO_MAP.md. Positive pan is the robot's own
# LEFT; positive nod is UP.
PAN_RANGE = (-14.4, 14.4)

# SERVO_MAP.md allows the node down to -3.6 and up to +40. Ordinary speech
# motion is deliberately kept inside the small envelope it asks for; only
# deliberate looking-up borrows any of the rest.
NOD_RANGE = (-3.6, 22.0)

# What the head may do when somebody ASKS it to look up, as opposed to what
# it does to itself while talking. Being asked is a different thing, and it
# has to be VISIBLY different: conversational motion now reaches +22 on its
# own, so a "look up" answered with anything near that reads as the robot
# carrying on rather than as it doing what it was told. Still well short of
# the +40 the node allows and the mechanism was walked to.
#
# The two ranges exist so that a bug in the speech envelope can never reach
# the larger one - only an explicit `command` unlocks it, and only while the
# hold lasts.
NOD_COMMAND_RANGE = (-3.6, 32.0)

# How loud a chunk has to be to earn a full-sized gesture. Speech sits well
# below full scale, so an envelope used raw barely moves the arms at all.
LEVEL_REFERENCE = 0.12

# Envelope time constants, in seconds. Attack is quick so a gesture lands
# with the syllable that caused it; release is slow so the arms ride over
# the gaps between words instead of dropping into every comma.
ATTACK = 0.05
RELEASE = 0.30

# Silence, in seconds without a released chunk, before the body goes home.
SILENCE_AFTER = 0.25

# The arm gesture. LIFT is how far both arms come up when talking at a normal
# volume; SWING is how far they then move against each other.
LIFT = 26.0
SWING = 14.0

# Beat rate of the alternation, in hertz. Slower than speech on purpose: this
# is the rhythm of somebody moving their hands while making a point, not one
# gesture per syllable.
BEAT_HZ = 0.45

# Radians of phase between the arms. Deliberately not pi - exact opposition
# reads as a mechanism keeping time rather than a person talking.
PHASE = 2.2

# ----------------------------------------------------------------- the head

# The head's own beat. Under the arms' - it follows phrases rather than
# syllables - but not by as much as it was. At 0.17 Hz the head changed
# direction once every three seconds, which on a desk is indistinguishable
# from not moving.
HEAD_BEAT_HZ = 0.38

# The head's own envelope, well slower than the arms'. ATTACK of 0.05 s is
# right for a hand that lands with the syllable, and wrong for a neck: the
# head's amplitudes all scale with the envelope, so an envelope that snaps
# from 0 to 1 in fifty milliseconds asks the neck for twenty degrees a second
# the instant anybody starts talking. The node would refuse it - it is
# acceleration-limited - but a refused request is a head visibly lagging its
# own gestures. Easing in over a third of a second asks for what it can have.
HEAD_ATTACK = 0.28
HEAD_RELEASE = 0.60

# How far the head moves on the speech envelope, in degrees, at full volume.
# This rides on top of wherever the robot is already looking, and the sum
# still has to fit inside PAN_RANGE - which is what stops these going higher.
PAN_SPEECH = 9.0
NOD_SPEECH = 6.0

# WHY THE NOD PIVOTS UPWARD INSTEAD OF AROUND ZERO
#
# The mechanism goes +40 degrees up and only -3.6 down. A nod in the ordinary
# sense - chin down, back up - is not a motion this head can make. Swinging a
# small amount either side of zero, which is what this did at first, spends
# almost all of its travel on the 3.6 degrees that do not exist and reads as
# a head that never moves vertically at all.
#
# So the head raises its chin while it talks and swings around THAT. The lift
# scales with the speech envelope, so it is level when quiet and has room to
# move when it is not: at full voice the nod lives between about +1 and +13,
# entirely inside the approved upward travel, and never goes near the floor.
NOD_SPEAKING_LIFT = 7.0

# Idle drift. Two periods that do not divide into each other, so the wander
# never repeats visibly. Amplitudes in degrees.
#
# The nod drift is biased upward for the same reason as the speaking lift:
# centred on zero it would spend half its time trying to go somewhere the
# mechanism cannot.
PAN_IDLE = 5.5
NOD_IDLE = 2.0
NOD_IDLE_CENTRE = 2.5
PAN_IDLE_PERIOD = 11.3
NOD_IDLE_PERIOD = 17.9

# ------------------------------------------------------------- the tracking

# How much of the way to a face the head actually turns. Under 1 on purpose:
# a robot that centres a face perfectly looks like a security camera. This
# turns toward somebody and lets the rest be implied.
TRACK_GAIN = 0.85

# Which way a face on the right of the CAMERA IMAGE moves the neck.
#
# gaze.py hands over x in [-1, 1], increasing left to right across the image.
# A forward-facing camera sees the room the way the robot does, so a face at
# x > 0 is to the robot's RIGHT, and the robot turns right, which is NEGATIVE
# pan. If the head turns AWAY from the person on the bench, flip this sign -
# and flip it here, not by negating x somewhere upstream.
PAN_FROM_GAZE = -1.0

# How far up the head is allowed to look to meet a face, in degrees.
#
# SERVO_MAP.md asks for ordinary speech nods inside +-3.6 "initially". This
# exceeds that, in the one direction the mechanism was actually walked (up,
# to +40, under direct observation), and by a fifth of the travel that was
# approved. It is what lets a desk bot raise its face to somebody standing
# over it instead of talking to their belt. Set it to 0 to switch looking-up
# off entirely without touching anything else.
NOD_TRACK_UP = 9.0

# How long a gaze target stays interesting after the last face update. The
# vision loop drops frames constantly; without this the head would snap back
# to centre between detections.
GAZE_STALE_AFTER = 1.5

# How fast the head's own idea of where to look catches up with the tracker,
# in seconds. This is a second, slower smoothing on top of GazeController's,
# and it is what stops the neck reacting to a head turning in a chair.
GAZE_TAU = 0.55

# ------------------------------------------------------------------ the wire

# How often a pose goes to the node. The node slews at 50 Hz between whatever
# targets it has, so sending faster than this buys nothing.
TICK = 0.05

# Degrees of change worth a message. Holding still should be silent on the
# wire rather than 20 identical poses a second.
DEADBAND = 0.4

# The head moves through much smaller angles than the arms, so the arms'
# deadband would swallow its motion entirely.
HEAD_DEADBAND = 0.15

# --------------------------------------------------------- asked-for poses

# What "turn your head left" is worth, in degrees. Modest on purpose: these
# are pulled out of a conversation, and a robot that swings to its stop every
# time somebody says "look left" gets old in about four goes. The node clamps
# them again anyway.
#
# LEFT AND RIGHT ARE THE ROBOT'S OWN, the way "raise your left hand" is. It is
# the reading that survives the robot turning round, and the one that matches
# `pan` throughout this codebase. Somebody facing it who meant their own left
# will say so, and can be answered.
COMMANDED = {
    ("head", "left"): {"pan": 13.0},
    ("head", "right"): {"pan": -13.0},
    ("head", "up"): {"nod": 30.0},
    ("head", "down"): {"nod": -3.6},
    ("head", "centre"): {"pan": 0.0, "nod": 0.0},
    ("left arm", "up"): {"arm_l": 55.0},
    ("left arm", "down"): {"arm_l": ARM_REST},
    ("right arm", "up"): {"arm_r": 55.0},
    ("right arm", "down"): {"arm_r": ARM_REST},
    ("both arms", "up"): {"arm_l": 55.0, "arm_r": 55.0},
    ("both arms", "down"): {"arm_l": ARM_REST, "arm_r": ARM_REST},
}

PARTS = ("head", "left arm", "right arm", "both arms")
DIRECTIONS = ("left", "right", "up", "down", "centre")

# How long an asked-for pose survives before the body goes back to gesturing.
#
# It has to expire. `pose` rewrites every axis twenty times a second off the
# speech envelope, so a commanded pose with no hold is overwritten within one
# frame and the robot simply ignores what it was asked. Holding it FOREVER is
# the opposite failure: the robot would freeze mid-conversation in whatever
# position it was last told, with no event that ever ends it - the model has
# no reliable moment to say "you may move again". A few seconds is long enough
# to be seen and short enough that it cannot become a mode.
HOLD_SECONDS = 4.5

AXES = ("arm_l", "arm_r", "pan", "nod")

DEADBANDS = {
    "arm_l": DEADBAND,
    "arm_r": DEADBAND,
    "pan": HEAD_DEADBAND,
    "nod": HEAD_DEADBAND,
}

REST_POSE = {"arm_l": ARM_REST, "arm_r": ARM_REST, "pan": 0.0, "nod": 0.0}


def clamp(value, low, high):
    return max(low, min(high, value))


class Gestures:
    """Turns the playback envelope into body targets and sends them.

    Feed it loudness from PacedPlayback and faces from the vision loop; run()
    does the rest.
    """

    def __init__(self, websocket, log=None):
        self.websocket = websocket
        self.log = log

        self.raw = 0.0

        # Seconds since the last chunk was released, advanced by pose() on the
        # same clock it uses for everything else. Reading the wall clock in
        # here instead would leave the one path that matters - what the body
        # does when the talking stops - impossible to test.
        self.since_audio = SILENCE_AFTER

        self.level = 0.0

        # The same envelope, followed slowly. See HEAD_ATTACK.
        self.head_level = 0.0

        self.phase = 0.0
        self.clock = 0.0

        # Where the tracker last saw a face, in camera coordinates, and how
        # long ago. None means nothing has ever been seen.
        self.gaze = None
        self.since_gaze = GAZE_STALE_AFTER

        # The head's own smoothed idea of where to look, in degrees.
        self.aim_pan = 0.0
        self.aim_nod = 0.0

        # Axes the model has asked to place, and how long each has left.
        # Empty is the normal state.
        self.held = {}

        self.last_sent = None

    # ------------------------------------------------------------- the input

    def feed(self, loudness: float) -> None:
        """Called as each chunk of speech is released to the node."""

        self.raw = loudness
        self.since_audio = 0.0

    def look_at(self, x: float, y: float) -> None:
        """Called with a smoothed face position in camera coordinates.

        x and y are gaze.GazeTarget's, in [-1, 1]: x increases left to right
        across the image, y increases downward. Turning those into degrees is
        this file's job, and turning degrees into pulses is the node's.
        """

        self.gaze = (clamp(float(x), -1.0, 1.0), clamp(float(y), -1.0, 1.0))
        self.since_gaze = 0.0

    def stop_looking(self) -> None:
        """Forget the face. The head drifts back to its own devices."""

        self.gaze = None
        self.since_gaze = GAZE_STALE_AFTER

    def command(self, part: str, direction: str, seconds: float = HOLD_SECONDS):
        """Place part of the body because somebody asked. Expires by itself.

        Returns the axes it took, or None if that is not a move this body
        can make. The angles are still clamped by `pose`, and clamped again
        by the node, so a bad entry in COMMANDED cannot reach a servo.
        """

        wanted = COMMANDED.get((part, direction))

        if wanted is None:
            return None

        for axis, degrees in wanted.items():
            self.held[axis] = [float(degrees), float(seconds)]

        return dict(wanted)

    def let_go(self, axis: str | None = None) -> None:
        """Hand an axis - or everything - back to the gesture generator."""

        if axis is None:
            self.held.clear()
        elif axis in self.held:
            del self.held[axis]

    def _hold(self, pose: dict, elapsed: float) -> dict:
        """Overwrite held axes, and retire the holds that have run out."""

        for axis in list(self.held):
            degrees, left = self.held[axis]
            left -= elapsed

            if left <= 0.0:
                del self.held[axis]
                continue

            self.held[axis] = [degrees, left]
            pose[axis] = degrees

        return pose

    # -------------------------------------------------------------- the pose

    def _aim(self, elapsed: float):
        """Where the head wants to point, before speech is added.

        Returns degrees. A stale or absent face aims at the idle drift rather
        than at dead centre, so losing somebody does not freeze the neck.
        """

        drift_pan = PAN_IDLE * math.sin(2.0 * math.pi * self.clock / PAN_IDLE_PERIOD)
        drift_nod = NOD_IDLE_CENTRE + NOD_IDLE * math.sin(
            2.0 * math.pi * self.clock / NOD_IDLE_PERIOD
        )

        if self.gaze is not None and self.since_gaze < GAZE_STALE_AFTER:
            x, y = self.gaze

            wanted_pan = PAN_FROM_GAZE * x * TRACK_GAIN * PAN_RANGE[1]

            # y increases downward, so a face high in the frame is a negative
            # y and wants a positive (upward) nod. Only upward: the mechanism
            # has no approved downward travel to spend.
            wanted_nod = max(0.0, -y) * NOD_TRACK_UP
        else:
            wanted_pan = drift_pan
            wanted_nod = drift_nod

        # Second-stage smoothing. GazeController already removes detector
        # jitter; this removes the difference between a glance and a move.
        catch_up = 1.0 - math.exp(-elapsed / GAZE_TAU)

        self.aim_pan += (wanted_pan - self.aim_pan) * catch_up
        self.aim_nod += (wanted_nod - self.aim_nod) * catch_up

        return self.aim_pan, self.aim_nod

    def pose(self, elapsed: float) -> dict:
        """Advance the envelope and the beats, and return every axis."""

        self.since_audio += elapsed
        self.since_gaze += elapsed
        self.clock += elapsed

        speaking = self.since_audio < SILENCE_AFTER
        target = clamp(self.raw / LEVEL_REFERENCE, 0.0, 1.0) if speaking else 0.0

        # Exponential follower. Attacking faster than it releases is what
        # keeps the arms from chattering between syllables.
        tau = ATTACK if target > self.level else RELEASE
        self.level += (target - self.level) * (1.0 - math.exp(-elapsed / tau))

        head_tau = HEAD_ATTACK if target > self.head_level else HEAD_RELEASE
        self.head_level += (target - self.head_level) * (
            1.0 - math.exp(-elapsed / head_tau)
        )

        # The beat only advances while there is something to gesture about, so
        # speech always starts from the same place in the cycle rather than
        # wherever a free-running clock happened to be.
        if self.level > 0.01:
            self.phase += 2.0 * math.pi * BEAT_HZ * elapsed

        base = ARM_REST + LIFT * self.level
        swing = SWING * self.level

        aim_pan, aim_nod = self._aim(elapsed)

        # The head rides the same envelope at its own, much slower rate. The
        # phases are offset from each other so pan and nod do not trace a
        # single diagonal line.
        head_phase = self.phase * (HEAD_BEAT_HZ / BEAT_HZ)

        pan = aim_pan + PAN_SPEECH * self.head_level * math.sin(head_phase)
        nod = (
            aim_nod
            + NOD_SPEAKING_LIFT * self.head_level
            + NOD_SPEECH * self.head_level * math.sin(head_phase * 1.7 + 0.9)
        )

        pose = {
            "arm_l": clamp(base + swing * math.sin(self.phase), *ARM_RANGE),
            "arm_r": clamp(base + swing * math.sin(self.phase + PHASE), *ARM_RANGE),
            "pan": clamp(pan, *PAN_RANGE),
            "nod": clamp(nod, *NOD_RANGE),
        }

        # An asked-for pose beats the speech, for as long as it lasts.
        pose = self._hold(pose, elapsed)

        return {
            "arm_l": clamp(pose["arm_l"], *ARM_RANGE),
            "arm_r": clamp(pose["arm_r"], *ARM_RANGE),
            "pan": clamp(pose["pan"], *PAN_RANGE),
            # Only a live hold unlocks the larger upward range. Generated
            # motion is clamped to the small one whatever it computes.
            "nod": clamp(
                pose["nod"],
                *(NOD_COMMAND_RANGE if "nod" in self.held else NOD_RANGE),
            ),
        }

    # -------------------------------------------------------------- the wire

    def worth_sending(self, pose: dict) -> bool:
        if self.last_sent is None:
            return True

        return any(
            abs(pose[axis] - self.last_sent[axis]) >= DEADBANDS[axis]
            for axis in AXES
        )

    async def send(self, pose: dict) -> None:
        await self.websocket.send(json.dumps({"type": "pose", **pose}))

        self.last_sent = dict(pose)

    async def rest(self) -> None:
        """Put the body down. Worth doing before the socket closes."""

        self.level = 0.0
        self.head_level = 0.0
        self.let_go()
        await self.send(dict(REST_POSE))

    async def run(self) -> None:
        if self.log:
            self.log("Gestures on - arms and head follow the speech")

        last = time.monotonic()

        try:
            while True:
                await asyncio.sleep(TICK)

                now = time.monotonic()
                elapsed, last = now - last, now

                pose = self.pose(min(elapsed, TICK * 4))

                if self.worth_sending(pose):
                    await self.send(pose)

        except ConnectionClosed:
            # The node hung up, or we are shutting down. Either way the body
            # is the node's problem now - it parks the head and goes limp on
            # its own. Raising here only produces a traceback on a normal
            # quit, which makes every exit look like a crash.
            return
