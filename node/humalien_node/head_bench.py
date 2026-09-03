"""The bench tool for the desk bot's head: pan, nod, and nothing else.

    ssh into the Pi, then:  python -m humalien_node.head_bench

READ THIS BEFORE THE FIRST RUN
------------------------------
node/SERVO_MAP.md records the head being walked by hand, under observation,
to 1340..1660 us on pan and 1056..1540 us on nod. Those pulses are what
humalien_node.arms enforces and this tool cannot exceed them.

What is NOT yet observed is the RATE. SERVO_MAP.md's "proven slow rate" of
3.6 deg/s is what the original bench script ramped at - a full pan sweep at
that rate takes eight seconds, which is not a conversation. arms.py now runs
pan at 18 deg/s and nod at 10, both acceleration-limited so nothing snaps at
either end of a move.

`profile` prints exactly what those numbers mean in seconds before anything
moves. Then walk `nod`, `pan` and `talk` with a hand near the power, and if
any of it looks harsh, lower PAN_SLEW_DPS / NOD_SLEW_DPS / the two ACCEL
figures in arms.py rather than living with it.

WHY THE HEAD GETS ITS OWN BENCH
-------------------------------
The eyes are wired through the neck: NeoPixel power and data run from the Pi
up past the nod joint into the head. The arms can be walked roughly. This
cannot - a harsh nod is a tug on a soldered ring behind a printed face, and
NEOPIXEL_MAP.md already records one of those rings being resoldered once.

THREE THINGS WORTH PROVING WITH YOUR HANDS ON THE ROBOT
------------------------------------------------------
  1. Direction. `pan 10` must turn the head to ITS OWN LEFT - your right,
     looking at it. `nod 10` must tip the face UP. If either goes the wrong
     way, flip that axis's sign in arms.py, not here and not upstream.
  2. Neutral. `home` should look level and straight ahead. If it does not,
     `trim nod -20` shifts its neutral in microseconds. Then `save`.
  3. Tracking direction. `track left` turns the head the way the robot will
     turn when a face is on the LEFT of the camera image. If it turns away
     from where the person would be, flip PAN_FROM_GAZE in brain/gestures.py.

Everything starts LIMP, and the head is parked at neutral before it is
released on the way out.
"""

import sys
import time

from humalien_node.arms import (
    AXES,
    Arms,
    HEAD_AXES,
    Pca9685Driver,
    TICK,
    US_PER_DEG,
    clamp,
)


NAMES = {"p": "pan", "n": "nod", "pan": "pan", "nod": "nod"}

HELP = """\
  engage            limp -> neutral. Do this first.
  pan <deg>         aim the neck. +ve is the robot's OWN LEFT.
  nod <deg>         aim the nod. +ve is UP.
  home              both back to 0
  profile           what the speed and acceleration limits mean, in seconds
  sweep <pan|nod>   slow 0 -> min -> max -> 0 on one axis
  talk              what speech actually looks like - small, slow, endless
  track <l|r|u>     where the head goes when a face is there
  nudge <p|n> <deg> small relative move, for finding the neutral by eye
  trim <p|n> <us>   shift an axis's neutral, e.g. `trim nod -20`
  pulse <p|n> <us>  drive a RAW pulse, for measuring - bypasses degrees
  calc <us> <deg>   us of travel and the degrees you measured -> US_PER_DEG
  save              print the lines to paste into arms.py
  off               park at neutral, then go limp
  q                 park, limp and quit

THE LIMITS THIS TOOL WILL NOT LET YOU PAST
  pan  %+.1f..%+.1f deg   (%.0f..%.0f us)
  nod  %+.1f..%+.1f deg   (%.0f..%.0f us)

  The nod is asymmetric on purpose. Up was walked to 1056 us and watched.
  Down past 1540 us never was - an attempt at full downward nods toward
  1944 us was stopped after erratic motion. See node/SERVO_MAP.md.
""" % (
    AXES["pan"].limits[0], AXES["pan"].limits[1],
    AXES["pan"].pulse_clamp[0], AXES["pan"].pulse_clamp[1],
    AXES["nod"].limits[0], AXES["nod"].limits[1],
    AXES["nod"].pulse_clamp[0], AXES["nod"].pulse_clamp[1],
)


def settle(arms, seconds):
    """Run the motion loop synchronously. The bench has no event loop."""

    for _ in range(max(1, int(seconds / TICK))):
        arms.step(TICK)
        time.sleep(TICK)


def arrive(arms, seconds=6.0):
    """Step until every head axis has stopped, or the time runs out."""

    for _ in range(max(1, int(seconds / TICK))):
        arms.step(TICK)
        time.sleep(TICK)

        if all(abs(arms.velocity[axis]) < 1e-6 for axis in HEAD_AXES):
            return


def show(arms):
    for axis in HEAD_AXES:
        here = arms.position[axis]

        if here is None:
            print("  %s limp" % axis)
        else:
            print("  %-3s %+6.1f deg  (%4.0f us)"
                  % (axis, here, arms.microseconds(axis, here)))


def goto(arms, axis, degrees, seconds=6.0):
    if arms.position[axis] is None:
        print("  REFUSED: %s is limp - `engage` first" % axis)
        return

    low, high = AXES[axis].limits

    if not low <= degrees <= high:
        print("  clamped: %+.1f is outside %+.1f..%+.1f" % (degrees, low, high))

    arms.set_target(axis, degrees)
    arrive(arms, seconds)
    show(arms)


def profile():
    """What the limits mean in seconds, before anything moves."""

    print("  what the head is allowed to do:")
    print("")

    for axis in HEAD_AXES:
        spec = AXES[axis]
        span = spec.limits[1] - spec.limits[0]

        # Time to cross the whole range: ramp up, cruise, ramp down.
        ramp = spec.reaches_speed_in
        covered = spec.slew_dps * ramp          # both ramps together

        if covered >= span:
            crossing = 2.0 * (span / spec.accel_dps2) ** 0.5
        else:
            crossing = 2.0 * ramp + (span - covered) / spec.slew_dps

        print("  %-3s  top speed %5.1f deg/s, reached in %.2f s" %
              (axis, spec.slew_dps, ramp))
        print("       whole range (%.1f deg) takes %.1f s end to end"
              % (span, crossing))

    print("")
    print("  If a move looks harsh, lower the ACCEL first, then the speed.")


def sweep(arms, axis):
    low, high = AXES[axis].limits

    print("  sweep %s: 0 -> %+.1f -> %+.1f -> 0" % (axis, low, high))

    for target in (low, high, 0.0):
        goto(arms, axis, target)
        time.sleep(0.4)


def talk(arms):
    """What the gesture layer will actually ask for, on repeat.

    Small, slow, and never still. If this looks like a machine keeping time
    rather than somebody talking, the numbers to change are in
    brain/gestures.py, not here.
    """

    print("  talking. ctrl-c to stop.")

    beats = (
        (2.0, 1.5), (-1.5, 2.5), (3.0, 0.5),
        (-2.5, 1.8), (1.0, 2.2), (0.0, 0.0),
    )

    try:
        while True:
            for pan, nod in beats:
                arms.set_target("pan", pan)
                arms.set_target("nod", nod)
                settle(arms, 1.4)

    except KeyboardInterrupt:
        print("\n  stopped")
        goto(arms, "pan", 0.0)
        goto(arms, "nod", 0.0)


def track(arms, where):
    """Where the head goes when a face is on one side of the camera image.

    brain/gestures.py turns a camera x of -1..+1 into degrees through
    PAN_FROM_GAZE and TRACK_GAIN. This reproduces the ends of that, so the
    sign can be checked against a real person standing in front of it.
    """

    from_gaze = {"l": (-1.0, 0.0), "r": (1.0, 0.0), "u": (0.0, -1.0)}[where]

    # Kept in step with brain/gestures.py by eye. This is a bench aid, not
    # the contract - the brain is what actually decides.
    pan = -from_gaze[0] * 0.65 * AXES["pan"].limits[1]
    nod = max(0.0, -from_gaze[1]) * 6.0

    side = {"l": "the LEFT of the image", "r": "the RIGHT of the image",
            "u": "ABOVE the camera"}[where]

    print("  a face at %s ->  pan %+.1f, nod %+.1f" % (side, pan, nod))
    print("  the head should now be pointing AT where that person would be.")

    arms.set_target("pan", pan)
    arms.set_target("nod", nod)
    arrive(arms)
    show(arms)


def pulse(arms, axis, microseconds):
    """Drive a raw pulse, keeping the tracked position honest."""

    if arms.position[axis] is None:
        print("  REFUSED: %s is limp - `engage` first" % axis)
        return

    wanted = float(microseconds)
    allowed = clamp(wanted, *AXES[axis].pulse_clamp)

    if allowed != wanted:
        print("  clamped to %.0f us (observed band is %.0f..%.0f)"
              % (allowed, *AXES[axis].pulse_clamp))

    degrees = arms.degrees_from(axis, allowed)

    # Slewed, not written. A raw pulse on the head is still a head move.
    arms.set_target(axis, degrees)
    arrive(arms)

    print("  %s at %.0f us (= %+.1f deg by the current US_PER_DEG)"
          % (axis, allowed, degrees))


def calc(travel_us, measured_deg):
    """Turn a measured swing into the US_PER_DEG that would have produced it."""

    if measured_deg == 0:
        print("  measured 0 degrees - nothing to divide by")
        return

    found = abs(float(travel_us)) / abs(float(measured_deg))

    print("  measured %.1f deg across %.0f us" % (measured_deg, travel_us))
    print("  US_PER_DEG = %.4f   (currently %.4f, %+.1f%%)"
          % (found, US_PER_DEG, (found / US_PER_DEG - 1.0) * 100.0))
    print("  NOTE: US_PER_DEG is shared by all four axes. Changing it moves")
    print("  the arms too, and it rescales every limit in arms.py.")


def save(arms):
    """Print the calibration as source, so it survives a restart."""

    print("  paste into node/humalien_node/arms.py, keeping the arm values:")
    print("")
    print("TRIM = {\"arm_r\": %d, \"arm_l\": %d, \"pan\": %d, \"nod\": %d}"
          % (arms.trim["arm_r"], arms.trim["arm_l"],
             arms.trim["pan"], arms.trim["nod"]))


def park(arms):
    """Bring the head home gently, then release it. Never just let go."""

    if any(arms.position[axis] is not None for axis in HEAD_AXES):
        for axis in HEAD_AXES:
            arms.set_target(axis, 0.0)

        arrive(arms, seconds=8.0)

    arms.limp(HEAD_AXES)


def main():
    try:
        driver = Pca9685Driver()
    except Exception as error:
        print("No PCA9685: %s" % error)
        print("Is this the Pi, and is I2C enabled?")
        return 1

    arms = Arms(driver)

    print("head bench. channels: pan %d, nod %d"
          % (AXES["pan"].channel, AXES["nod"].channel))
    print("the arms are humalien_node.arm_bench, not this one.")
    print("head limp.\n%s" % HELP)

    profile()
    print("")

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
                    arms.engage(HEAD_AXES)
                    print("  engaged at neutral. The head is live.")
                    show(arms)

                elif command == "off":
                    park(arms)
                    print("  parked at neutral, now limp.")

                elif command == "home":
                    goto(arms, "pan", 0.0)
                    goto(arms, "nod", 0.0)

                elif command == "profile":
                    profile()

                elif command in NAMES and args:
                    goto(arms, NAMES[command], float(args[0]))

                elif command == "sweep" and args:
                    sweep(arms, NAMES[args[0]])

                elif command == "talk":
                    talk(arms)

                elif command == "track" and args:
                    track(arms, args[0][0])

                elif command == "nudge" and len(args) == 2:
                    axis = NAMES[args[0]]

                    if arms.position[axis] is None:
                        print("  REFUSED: %s is limp - `engage` first" % axis)
                    else:
                        goto(arms, axis, arms.position[axis] + float(args[1]))

                elif command == "pulse" and len(args) == 2:
                    pulse(arms, NAMES[args[0]], float(args[1]))

                elif command == "calc" and len(args) == 2:
                    calc(float(args[0]), float(args[1]))

                elif command == "save":
                    save(arms)

                elif command == "trim" and len(args) == 2:
                    axis = NAMES[args[0]]
                    arms.trim[axis] += int(args[1])
                    print("  trim %s -> %+d us" % (axis, arms.trim[axis]))

                    if arms.position[axis] is not None:
                        arms._write(axis, arms.position[axis])
                        show(arms)

                else:
                    print(HELP)

            except (KeyError, ValueError, IndexError):
                print(HELP)

    finally:
        park(arms)
        print("head parked and limp. good bench.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
