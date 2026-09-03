"""Render the eyes and the head to a JSON blob a browser can play back.

    cd node && python tools/preview_eyes.py [out.json]

WHY THIS EXISTS
---------------
Tuning an animation by flashing it to a Pi, walking to the robot, and
watching six seconds of it is a slow loop, and the robot is not always on the
bench. This runs the REAL renderers - humalien_node.pixels for the eyes and
humalien_node.arms plus brain/gestures.py for the head - and dumps what they
actually produce.

Nothing here reimplements a mood or a motion curve. If it did, the preview
would drift from the hardware and become worse than useless. Change a
constant in pixels.py or arms.py, run this again, and the preview changes
with it.

The head section answers one specific question: how hard does the nod
actually move? It simulates a conversation, pushes the brain's poses through
the node's acceleration-limited motion loop, and reports the peak speed and
acceleration the mechanism would really see.
"""

import base64
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
BRAIN = HERE.parent / "brain"

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(BRAIN))

from humalien_node.arms import AXES, Arms, HEAD_AXES, TICK as SERVO_TICK
from humalien_node.pixels import (
    BRIGHTNESS,
    MOODS,
    PIXELS_PER_EYE,
    PIXEL_COUNT,
    Pixels,
)

import gestures as brain_gestures


# Playback rate for the preview. Lower than the node's 40 Hz to keep the file
# small; the moods are all slow enough that nothing is lost.
FPS = 25
SECONDS = 6.0

# The levels worth seeing. `speaking` and `listening` are the only moods that
# use one, but rendering them all keeps the viewer simple.
#
# Strings, and the same strings are both the JSON keys and the list the page
# iterates. Storing them as numbers and rebuilding the key in the browser
# does not survive the round trip: Python writes str(1.0) as "1.0" and
# JavaScript writes String(1.0) as "1", so the lookup misses and the whole
# viewer draws nothing.
LEVELS = ("0.15", "0.5", "1.0")

# How long a conversation to simulate for the head trace.
TALK_SECONDS = 24.0


def render(mood, level):
    """One mood at one level, as base64 frames of raw GRB bytes."""

    level = float(level)

    pixels = Pixels(brightness=BRIGHTNESS)
    pixels.set(mood=mood, level=level)

    step = 1.0 / FPS
    frames = []

    for _ in range(int(SECONDS * FPS)):
        # Keep the level fresh: the node decays it after half a second of
        # silence, which is right on the robot and wrong in a loop.
        pixels.set(level=level)

        frames.append(
            base64.b64encode(pixels.encode(pixels.frame(step))).decode()
        )

    return frames


def speech_envelope(t):
    """Something shaped like talking: phrases, with gaps between them."""

    phrase = math.sin(2.0 * math.pi * t / 5.0)

    if phrase < -0.2:
        return 0.0

    syllables = 0.55 + 0.45 * math.sin(2.0 * math.pi * 3.1 * t)

    return max(0.0, phrase) * syllables


def head_trace():
    """What the head really does across a conversation, brain and node.

    The brain's poses go through the node's own motion loop, so the `actual`
    series is the acceleration-limited result rather than the request.
    """

    shaping = brain_gestures.Gestures(None)
    arms = Arms()
    arms.engage()

    brain_step = brain_gestures.TICK
    per_pose = max(1, int(round(brain_step / SERVO_TICK)))

    trace = {
        "t": [],
        "pan_asked": [],
        "nod_asked": [],
        "pan_actual": [],
        "nod_actual": [],
    }

    clock = 0.0

    while clock < TALK_SECONDS:
        level = speech_envelope(clock)

        if level > 0.0:
            shaping.feed(level * brain_gestures.LEVEL_REFERENCE)

        # Somebody sitting slightly to one side, a little above the camera.
        if 6.0 < clock < 18.0:
            shaping.look_at(0.55, -0.4)

        pose = shaping.pose(brain_step)

        for axis in HEAD_AXES:
            arms.set_target(axis, pose[axis])

        for _ in range(per_pose):
            arms.step(SERVO_TICK)

            trace["t"].append(round(clock, 3))
            trace["pan_asked"].append(round(pose["pan"], 3))
            trace["nod_asked"].append(round(pose["nod"], 3))
            trace["pan_actual"].append(round(arms.position["pan"], 3))
            trace["nod_actual"].append(round(arms.position["nod"], 3))

            clock += SERVO_TICK

    return trace


def worst(series, step):
    """Peak speed and acceleration of a position series."""

    speeds = [(b - a) / step for a, b in zip(series, series[1:])]
    accels = [(b - a) / step for a, b in zip(speeds, speeds[1:])]

    return (
        max((abs(s) for s in speeds), default=0.0),
        max((abs(a) for a in accels), default=0.0),
    )


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("eyes_preview.json")

    trace = head_trace()

    data = {
        "fps": FPS,
        "seconds": SECONDS,
        "pixelsPerEye": PIXELS_PER_EYE,
        "pixelCount": PIXEL_COUNT,
        "brightness": BRIGHTNESS,
        "levels": list(LEVELS),
        "moods": {
            mood: {str(level): render(mood, level) for level in LEVELS}
            for mood in MOODS
        },
        "head": {
            "trace": trace,
            "limits": {
                axis: {
                    "range": list(AXES[axis].limits),
                    "slew": AXES[axis].slew_dps,
                    "accel": AXES[axis].accel_dps2,
                }
                for axis in HEAD_AXES
            },
            "worst": {
                axis: dict(
                    zip(
                        ("speed", "accel"),
                        worst(trace[f"{axis}_actual"], SERVO_TICK),
                    )
                )
                for axis in HEAD_AXES
            },
        },
    }

    out.write_text(json.dumps(data))

    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB)")

    for axis in HEAD_AXES:
        peak = data["head"]["worst"][axis]
        spec = data["head"]["limits"][axis]

        print(
            f"  {axis}: peak {peak['speed']:.1f} deg/s of {spec['slew']:.0f}, "
            f"{peak['accel']:.1f} deg/s2 of {spec['accel']:.0f}"
        )


if __name__ == "__main__":
    main()
