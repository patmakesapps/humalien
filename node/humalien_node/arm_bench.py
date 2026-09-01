"""The bench tool for the desk bot's arms: engage, aim, sweep, limp.

    ssh into the Pi, then:  python -m humalien_node.arm_bench

Walk each arm ALONE here before the brain is ever allowed to drive them.
Two things are worth proving with your hands on the robot before gestures run:

  1. Direction. `r 40` must swing the RIGHT arm FORWARD. If it goes back,
     the sign for that channel is wrong - fix SIGN in arms.py, not here,
     and not by negating angles somewhere upstream.
  2. Neutral. `rest` should look like arms hanging naturally. If an arm
     sits high or low, `trim r -40` shifts its neutral in microseconds.
     Copy whatever you land on into arms.py.

Everything starts LIMP and goes limp again on exit, the same shape as
humalien_node.eyes_bench.
"""

import sys
import time

from humalien_node.arms import (
    Arms,
    CHANNELS,
    LIMITS,
    Pca9685Driver,
    REST,
    TICK,
)


AXES = {"r": "arm_r", "l": "arm_l", "arm_r": "arm_r", "arm_l": "arm_l"}

HELP = """\
  engage           limp -> REST (%.0f deg). Do this first.
  r/l <deg>        aim right/left arm, in CAD degrees. +ve is FORWARD.
  both <deg>       aim both together
  sweep <r|l>      slow REST -> min -> max -> REST on one arm
  wave             a few alternating beats, what a gesture looks like
  trim <r|l> <us>  shift an axis's neutral, e.g. `trim r -40`
  rest             back to REST
  off              go limp (no pulse, no holding torque)
  q                limp and quit
""" % REST


def settle(arms, seconds):
    """Run the motion loop synchronously. The bench has no event loop."""

    steps = max(1, int(seconds / TICK))

    for _ in range(steps):
        arms.step(TICK)
        time.sleep(TICK)


def goto(arms, axis, degrees, seconds=1.2):
    if arms.position[axis] is None:
        print("  REFUSED: %s is limp - `engage` first" % axis)
        return

    low, high = LIMITS

    if not low <= degrees <= high:
        print("  clamped: %.1f is outside %.0f..%.0f" % (degrees, low, high))

    arms.set_target(axis, degrees)
    settle(arms, seconds)

    print("  %s at %+.1f deg (%.0f us)"
          % (axis, arms.position[axis],
             arms.microseconds(axis, arms.position[axis])))


def sweep(arms, axis):
    low, high = LIMITS
    print("  sweep %s: REST -> %.0f -> %.0f -> REST" % (axis, low, high))

    for target in (low, high, REST):
        goto(arms, axis, target, seconds=1.6)
        time.sleep(0.3)


def wave(arms):
    """What the gesture layer will actually ask for, done slowly."""

    print("  wave: alternating beats around REST")

    for left, right in ((25, -5), (-5, 25), (25, -5), (REST, REST)):
        arms.set_target("arm_l", left)
        arms.set_target("arm_r", right)
        settle(arms, 0.8)


def main():
    try:
        driver = Pca9685Driver()
    except Exception as error:
        print("No PCA9685: %s" % error)
        print("Is this the Pi, and is I2C enabled?")
        return 1

    arms = Arms(driver)

    print("arm bench. channels: %s" % CHANNELS)
    print("all limp.\n%s" % HELP)

    try:
        while True:
            try:
                words = input("> ").strip().lower().split()
            except EOFError:
                break

            if not words:
                continue

            command, args = words[0], words[1:]

            try:
                if command == "q":
                    break

                elif command == "engage":
                    arms.engage()
                    print("  engaged at REST %.0f deg. Arms are live." % REST)

                elif command == "off":
                    arms.limp()
                    print("  limp: all")

                elif command == "rest":
                    for axis in CHANNELS:
                        goto(arms, axis, REST, seconds=0.9)

                elif command in AXES and args:
                    goto(arms, AXES[command], float(args[0]))

                elif command == "both" and args:
                    degrees = float(args[0])

                    for axis in CHANNELS:
                        arms.set_target(axis, degrees)

                    settle(arms, 1.2)
                    print("  both at %+.1f deg" % degrees)

                elif command == "sweep" and args:
                    sweep(arms, AXES[args[0]])

                elif command == "wave":
                    wave(arms)

                elif command == "trim" and len(args) == 2:
                    axis = AXES[args[0]]
                    arms.trim[axis] += int(args[1])
                    print("  trim %s -> %+d us" % (axis, arms.trim[axis]))

                    if arms.position[axis] is not None:
                        arms._write(axis, arms.position[axis])

                else:
                    print(HELP)

            except (KeyError, ValueError):
                print(HELP)

    finally:
        arms.limp()
        print("all limp. good bench.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
