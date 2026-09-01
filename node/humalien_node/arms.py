"""The desk bot's two arms: the sign flip, the limits, and the motion loop.

    from humalien_node.arms import Arms

THE CONTRACT WITH THE MECHANISM
-------------------------------
cad/desk_bot.py is the source of the numbers below. It defines

    ARM_RANGE = (-20.0, 75.0)   # +ve swings FORWARD, same sign both arms
    ARM_REST  = -8.0

and poses both arms with POSITIVE angles for forward movement. The wiring
does not agree with itself: node/SERVO_MAP.md records that channel 0 (the
right arm) moves forward as the pulse RISES, while channel 3 (the left arm)
moves forward as the pulse FALLS. That opposition lives here, in SIGN, and
nowhere else. Everything above this file - gestures, poses, the brain -
speaks in CAD degrees where positive is forward on both arms.

Get that backwards and the arms scissor: one goes forward, one goes back,
on a linkage whose clearance sweeps were only ever run with both arms
moving together.

WHAT IS DELIBERATELY MISSING
----------------------------
Channels 1 (pan) and 2 (nod) are wired but NOT calibrated, and SERVO_MAP.md
says so plainly. They are absent from CHANNELS rather than present and
commented out, because an axis you cannot address is an axis you cannot
drive into a hard stop by accident.

SAFETY SHAPE
------------
Same shape as humalien_node.eyes_bench, for the same reason:

  * Arms start LIMP. A servo with no pulse holds nothing and hurts nothing.
  * The first command is always a move to REST, because a limp servo's
    position is unknown and the first pulse jumps wherever it likes.
  * Nothing jumps afterwards. Targets are slewed at SLEW_DPS by the motion
    loop, so a burst of network messages cannot crack the linkage - which
    is how the v1 eye rig lost parts.
  * Loss of the brain means limp, not a held pose. A stalled servo holding
    an arm out is the one failure mode that gets hot.
"""

import asyncio
import time


# PCA9685 channel map, bench-identified 2026-08-31. See node/SERVO_MAP.md.
CHANNELS = {"arm_r": 0, "arm_l": 3}

# Electrical direction per channel. +1 means a forward (positive) CAD angle
# raises the pulse. SERVO_MAP.md: the right arm raises, the left arm lowers.
SIGN = {"arm_r": +1, "arm_l": -1}

# ARM_RANGE and ARM_REST from cad/desk_bot.py. Change them there, not here.
LIMITS = (-20.0, 75.0)
REST = -8.0

CENTER_US = 1500                # electrical neutral, per SERVO_MAP.md
US_PER_DEG = 1000.0 / 90.0      # MG90S: ~1000 us across 90 deg

# A backstop, not a travel limit. LIMITS is the real contract; this only
# stops a trim value from walking the pulse somewhere the bench never went.
# The raw bench reached 2500 us right and 556 us left without binding, so
# these sit just inside observed-safe rather than at the servo's extremes.
PULSE_CLAMP = (600, 2400)

# Fast enough to gesture with, slow enough that a printed linkage survives
# a bad target. Roughly a third of a second across a 30 degree beat.
SLEW_DPS = 100.0

TICK = 0.02                     # motion loop period, one 50 Hz servo frame


def clamp(value, low, high):
    return max(low, min(high, value))


class Pca9685Driver:
    """The real hardware. Imported lazily so this module loads anywhere."""

    def __init__(self):
        import board
        import busio
        from adafruit_pca9685 import PCA9685

        self.pca = PCA9685(busio.I2C(board.SCL, board.SDA))
        self.pca.frequency = 50

    def write(self, channel, microseconds):
        # Duty over a 20 ms frame, on the PCA's 16-bit counter.
        self.pca.channels[channel].duty_cycle = int(
            microseconds / 20000.0 * 0xFFFF
        )

    def release(self, channel):
        self.pca.channels[channel].duty_cycle = 0


class Arms:
    """Two servos, a target per axis, and a loop that slews toward them.

    The brain sends targets, never positions. Anything else would put the
    shape of the motion at the mercy of network jitter: a late message
    would become a stutter in the arm rather than a slightly stale goal.
    """

    def __init__(self, driver=None):
        self.driver = driver
        self.trim = {axis: 0 for axis in CHANNELS}      # us, set at the bench
        self.target = {axis: REST for axis in CHANNELS}
        self.position = {axis: None for axis in CHANNELS}   # None = limp

    def microseconds(self, axis, degrees):
        us = (
            CENTER_US
            + self.trim[axis]
            + SIGN[axis] * degrees * US_PER_DEG
        )

        return clamp(us, *PULSE_CLAMP)

    def _write(self, axis, degrees):
        self.position[axis] = degrees

        if self.driver is not None:
            self.driver.write(CHANNELS[axis], self.microseconds(axis, degrees))

    def engage(self):
        """Take the arms from limp to REST.

        This is the one move that is not slewed, and it cannot be: a limp
        servo has no known position to slew from. REST is a few degrees off
        neutral, so the jump is small by design.
        """

        for axis in CHANNELS:
            self.target[axis] = REST
            self._write(axis, REST)

    def limp(self):
        for axis in CHANNELS:
            self.position[axis] = None

            if self.driver is not None:
                self.driver.release(CHANNELS[axis])

    def set_target(self, axis, degrees):
        """Aim an axis. Out-of-range angles are clamped, not refused.

        eyes_bench refuses them, because a human typing at a bench wants to
        be told they are wrong. This runs under a gesture generator, where
        refusing means an arm silently stops following the speech while the
        other keeps going. Clamping degrades to a pose that is merely at the
        limit, which is the better failure.
        """

        if axis not in CHANNELS:
            return False

        self.target[axis] = clamp(float(degrees), *LIMITS)
        return True

    def step(self, seconds):
        """Advance every axis toward its target. Pure; the tests drive it."""

        limit = SLEW_DPS * seconds

        for axis in CHANNELS:
            here = self.position[axis]

            if here is None:
                # Limp. engage() is what ends that, not a target.
                continue

            error = self.target[axis] - here

            if abs(error) < 1e-6:
                continue

            self._write(axis, here + clamp(error, -limit, limit))

    async def run(self):
        """Slew toward the targets forever, one servo frame at a time."""

        last = time.monotonic()

        while True:
            await asyncio.sleep(TICK)

            now = time.monotonic()
            elapsed, last = now - last, now

            # A late wake-up must not become a lurch. Cap the step at a few
            # frames' worth of travel however long the loop actually slept.
            self.step(min(elapsed, TICK * 4))
