"""What the eyes are doing, and why.

The rendering lives on the Pi - see node/humalien_node/pixels.py for why. This
file decides which mood and shared color are true, how loud things are, where
the gaze highlight belongs, and which one-shot effects should fire. It sends
one small message whenever that semantic state changes.

TWO SOURCES, ONE OUTPUT
-----------------------
Most of the time the mood is a fact about the conversation, not a choice:
somebody is talking, or the robot is, or it is waiting on the model. Those are
observed here and need no help from anybody.

The interesting ones are not observable. Nothing in the audio stream knows the
robot is delighted. So the model gets a `feel` tool, and what it picks becomes
an ACCENT: it wins for a few seconds and then expires back into the automatic
state underneath. Accents expire on purpose. A mood the model set and forgot
about would leave the robot beaming at somebody through bad news, and the
model has no reliable moment at which to take it back.

PRECEDENCE
----------
Highest first. The list is short because a mood machine with more rules than
this becomes impossible to predict from the outside:

  1. An unexpired accent from `feel`.
  2. The robot is speaking      -> speaking, driven by the playback envelope.
  3. The model is working       -> thinking.
  4. Somebody is speaking to it -> listening, driven by the microphone.
  5. A new face just appeared   -> curious, briefly.
  6. Nobody around for a while  -> sleepy.
  7. Otherwise                  -> idle.
"""

import asyncio
import json
import time
from collections import deque

from websockets.exceptions import ConnectionClosed

from appearance import (
    CELEBRATIONS,
    DEFAULT_EYE_COLOR,
    EYE_COLORS,
    WINK_EYES,
)


# The moods the node knows how to draw. Kept in step with MOODS in
# node/humalien_node/pixels.py by test_mood.py, which reads both.
MOODS = (
    "off",
    "idle",
    "listening",
    "thinking",
    "speaking",
    "excited",
    "happy",
    "curious",
    "surprised",
    "confused",
    "angry",
    "sleepy",
)

# What the model is allowed to ask for. The states it must not fake are
# excluded: `speaking` and `listening` are facts about the audio, and `off` is
# a hardware state, not a feeling.
FEELINGS = (
    "excited",
    "happy",
    "curious",
    "surprised",
    "confused",
    "angry",
    "thinking",
    "sleepy",
)

# How long a deliberate feeling holds before the automatic state comes back.
# Long enough to land on the sentence that caused it, short enough that a
# forgotten accent cannot colour the rest of the conversation.
FEEL_SECONDS = 4.0

# Grace periods, in seconds, before a signal counts as over. Both cover the
# gap between chunks rather than the end of a turn.
SPEAKING_TAIL = 0.35
HEARING_TAIL = 0.6

# How loud the room has to be before it counts as somebody talking.
#
# The microphone streams continuously, so without a floor here every chunk of
# room silence would refresh `since_hearing` and the eyes would sit in
# `listening` for the whole session - never idle, never curious, never
# asleep. This is a noise gate for the eyes only; the Realtime API's own VAD
# decides what is actually speech.
HEARING_FLOOR = 0.02

# How long a face stays newly arrived, and how long an empty room takes to
# become boring.
CURIOUS_SECONDS = 2.5
SLEEPY_AFTER = 90.0

# How often the mood is reconsidered. Nothing here changes fast; the node is
# animating at 40 Hz off whatever it was last told.
TICK = 0.1

# How much the loudness has to move to be worth a message on its own. The eye
# brightness follows it, so this trades wire traffic against smoothness - the
# node smooths between updates, which is what makes a coarse value survivable.
LEVEL_DEADBAND = 0.06

# Face tracking already smooths its target. This wider deadband keeps tiny
# camera movements from turning into ten eye messages a second.
GAZE_DEADBAND = 0.10


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


class Mood:
    """Decides the eye mood and sends it. Feed it; run() does the rest."""

    def __init__(
        self,
        websocket,
        log=None,
        brightness=None,
        is_speaking=None,
        color=DEFAULT_EYE_COLOR,
    ):
        self.websocket = websocket
        self.log = log
        self.brightness = brightness
        self.color = color if color in EYE_COLORS else DEFAULT_EYE_COLOR

        # Whether sound is actually coming out of the head, asked of
        # PacedPlayback rather than inferred from how recently a chunk was
        # released. See `decide` for why that distinction is the difference
        # between a mood and a strobe.
        self.is_speaking = is_speaking

        # Seconds since each signal, advanced by decide() on its own clock so
        # the whole state machine is testable without sleeping.
        self.since_speaking = SPEAKING_TAIL
        self.since_hearing = HEARING_TAIL
        self.since_new_face = CURIOUS_SECONDS
        self.since_feel = FEEL_SECONDS

        # Starts awake, not asleep. A robot that boots into `sleepy` because
        # it has not seen anybody *yet* looks broken rather than restful, and
        # it is the state somebody sees the first time they plug it in.
        self.since_face = 0.0

        self.speaking_level = 0.0
        self.hearing_level = 0.0

        self.working = False
        self.feeling = None
        self.gaze = None
        self.effects = deque()

        self.mood = None
        self.last_sent = None

    # ------------------------------------------------------------- the input

    def speaking(self, level: float) -> None:
        """Called as each chunk of the robot's own speech is released."""

        self.speaking_level = clamp(float(level))
        self.since_speaking = 0.0

    def hearing(self, level: float) -> None:
        """Called with the loudness of microphone audio, while listening.

        Quiet enough and nothing happens at all - see HEARING_FLOOR. This is
        called for every chunk off the microphone, silence included.
        """

        level = clamp(float(level))

        if level < HEARING_FLOOR:
            return

        # Rescaled above the floor, so the quietest audible speech still
        # opens the eyes a little rather than starting from nothing.
        self.hearing_level = (level - HEARING_FLOOR) / (1.0 - HEARING_FLOOR)
        self.since_hearing = 0.0

    def thinking(self, working: bool) -> None:
        self.working = bool(working)

    def seen(self, *, new: bool = False) -> None:
        """Called while any face is visible. `new` for somebody just arrived."""

        self.since_face = 0.0

        if new:
            self.since_new_face = 0.0

    def feel(self, name: str) -> bool:
        """A deliberate feeling from the model. Expires; see the header."""

        if name not in FEELINGS:
            return False

        self.feeling = name
        self.since_feel = 0.0

        if self.log:
            self.log(f"Feeling {name}")

        return True

    def set_color(self, color: str) -> bool:
        """Change both eyes together. Persistence belongs to AppearanceStore."""

        if color not in EYE_COLORS:
            return False

        self.color = color

        if self.log:
            self.log(f"Eye color: {color}")

        return True

    def wink(self, eye: str) -> bool:
        if eye not in WINK_EYES:
            return False

        self.effects.append({"name": "wink", "eye": eye})
        return True

    def celebrate(self, style: str) -> bool:
        if style not in CELEBRATIONS:
            return False

        self.effects.append({"name": "celebrate", "style": style})
        return True

    def look_at(self, x: float) -> None:
        self.gaze = clamp(float(x), -1.0, 1.0)

    def stop_looking(self) -> None:
        self.gaze = None

    # ------------------------------------------------------------ the choice

    def decide(self, elapsed: float) -> tuple:
        """Advance every clock and return (mood, level)."""

        self.since_speaking += elapsed
        self.since_hearing += elapsed
        self.since_face += elapsed
        self.since_new_face += elapsed
        self.since_feel += elapsed

        if self.feeling is not None and self.since_feel < FEEL_SECONDS:
            return self.feeling, self.speaking_level

        self.feeling = None

        # ASK, do not infer.
        #
        # This used to be `since_speaking < SPEAKING_TAIL` - is it less than a
        # third of a second since a chunk was released. That is not the same
        # question. PacedPlayback deliberately releases audio in bursts and
        # then sleeps, holding only LEAD_SECONDS in flight, so the gap between
        # releases is routinely longer than any tail worth having. The eyes
        # dropped out of `speaking` in every one of those gaps and came back
        # on the next chunk, several times a second, for the whole reply.
        #
        # `is_speaking` knows about the queue AND the audio still sitting
        # inside aplay, which is the actual question: is sound coming out of
        # the head. The tail below is only the fallback for a Mood built
        # without one, which is every test in test_mood.py.
        if self.is_speaking is not None:
            if self.is_speaking():
                return "speaking", self.speaking_level

        elif self.since_speaking < SPEAKING_TAIL:
            return "speaking", self.speaking_level

        if self.working:
            return "thinking", 0.0

        if self.since_hearing < HEARING_TAIL:
            return "listening", self.hearing_level

        if self.since_new_face < CURIOUS_SECONDS:
            return "curious", 0.0

        if self.since_face >= SLEEPY_AFTER:
            return "sleepy", 0.0

        return "idle", 0.0

    # -------------------------------------------------------------- the wire

    def worth_sending(self, mood, level) -> bool:
        if self.effects:
            return True

        if self.last_sent is None:
            return True

        was, before, color, gaze = self.last_sent

        gaze_changed = (
            (gaze is None) != (self.gaze is None)
            or (
                gaze is not None
                and self.gaze is not None
                and abs(gaze - self.gaze) >= GAZE_DEADBAND
            )
        )

        return (
            mood != was
            or color != self.color
            or gaze_changed
            or abs(level - before) >= LEVEL_DEADBAND
        )

    async def send(self, mood, level) -> None:
        message = {
            "type": "eyes",
            "mood": mood,
            "level": round(level, 3),
            "color": self.color,
            "gaze": None if self.gaze is None else round(self.gaze, 3),
        }

        if self.effects:
            message["effect"] = self.effects.popleft()

        # Only on the first frame. Resending it every time would let a value
        # the bench is tuning be overwritten twenty times a second.
        if self.brightness is not None and self.last_sent is None:
            message["brightness"] = self.brightness

        await self.websocket.send(json.dumps(message))

        self.last_sent = (mood, level, self.color, self.gaze)

    async def dark(self) -> None:
        """Close the eyes. Worth doing before the socket closes."""

        self.effects.clear()
        self.last_sent = None
        await self.send("off", 0.0)

    async def run(self) -> None:
        if self.log:
            self.log("Eyes on - the mood follows the conversation")

        last = time.monotonic()

        try:
            while True:
                await asyncio.sleep(TICK)

                now = time.monotonic()
                elapsed, last = now - last, now

                mood, level = self.decide(min(elapsed, TICK * 4))

                if mood != self.mood and self.log:
                    self.log(f"Eyes: {mood}")

                self.mood = mood

                if self.worth_sending(mood, level):
                    await self.send(mood, level)

        except ConnectionClosed:
            # A normal end. The node clears the rings itself.
            return
