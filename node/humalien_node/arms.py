"""The desk bot's four driven axes: the sign flips, the limits, the motion loop.

    from humalien_node.arms import Arms

Named `arms` because that is all it drove first. It now carries the head as
well: same table, same slew loop, different numbers.

THE CONTRACT WITH THE MECHANISM
-------------------------------
Everything above this file - gestures, moods, the brain - speaks in CAD
degrees. This file is the only place that knows a PCA9685 exists, and the
only place the electrical sign flips live.

  arm_l / arm_r   cad/desk_bot.py: ARM_RANGE = (-20, 75), ARM_REST = -8, and
                  POSITIVE swings FORWARD on both arms. The wiring does not
                  agree with itself - SERVO_MAP.md records channel 0 (right)
                  moving forward as the pulse RISES and channel 3 (left)
                  moving forward as it FALLS. Get that backwards and the arms
                  scissor, on a linkage whose clearance sweeps were only ever
                  run with both arms moving together.

  pan             Neck rotation, channel 1. POSITIVE turns the head to its
                  own LEFT, which raises the pulse.

  nod             Head nod, channel 2. POSITIVE is UP, which LOWERS the
                  pulse - hence a sign of -1. This axis is not symmetric and
                  must not be made so: see below.

WHY THE HEAD LIMITS ARE NOT THE CAD LIMITS
------------------------------------------
cad/desk_bot.py says PAN_RANGE = (-80, 80) and NOD_RANGE = (-22, 22). Those
are geometric clearance sweeps - the angles the printed parts do not collide
through - and they are NOT what the assembled mechanism has been observed to
survive. SERVO_MAP.md records what was actually watched happening on the
robot, and that is what is enforced here:

  pan   1340..1660 us   = +-14.4 deg, both directions observed clean.
  nod   1056..1540 us   = -3.6 deg down, +40.0 deg up.

The nod asymmetry is real, not an oversight. Upward travel was walked to
1056 us under direct observation and explicitly set as the maximum. Downward
travel past 1540 us has NEVER been approved - one attempt at full nods
toward 1944 us produced erratic motion and was stopped. Do not tidy this
into a symmetric range.

SAFETY SHAPE
------------
  * Everything starts LIMP. A servo with no pulse holds nothing and hurts
    nothing.
  * The first command is always a move to rest, because a limp servo's
    position is unknown and the first pulse jumps wherever it likes.
  * Nothing jumps afterwards. Targets are slewed by the motion loop, so a
    burst of network messages cannot crack the linkage - which is how the
    v1 eye rig lost parts.
  * Nothing SNAPS either. Every axis is acceleration-limited as well as
    speed-limited - see below, it is the head's wiring that depends on it.
  * The head is parked at neutral before it is released, so the next engage
    has nowhere to jump from. This matters more now than it did: the head is
    fast enough that a jump from an unknown position would be a real yank.
  * Loss of the brain means limp, not a held pose. A stalled servo holding
    an arm out is the one failure mode that gets hot.
  * The pulse clamp is PER AXIS. A trim value or a recalibrated US_PER_DEG
    cannot walk the neck out into an arm's pulse range.

WHY ACCELERATION IS LIMITED AND NOT JUST SPEED
----------------------------------------------
A pure speed limit still steps the velocity from zero to the limit in one
frame. The servo answers that with everything it has, and the axis leaves and
arrives with a snap however low the speed cap is set.

That matters here because the NeoPixel eyes are wired through the neck. Their
data and power run from the Pi, up past the nod joint, into the head - so
every harsh nod is a tug on a soldered ring behind a printed face, and
NEOPIXEL_MAP.md already records one ring being resoldered once. The eyes are
the most delicate thing on the robot and they are downstream of the axis with
the most travel.

So each axis also carries `accel_dps2`, and `step` ramps velocity into and
out of every move, braking early enough to arrive without overshooting. The
head's speeds were walked up on the bench and approved; its ACCELERATIONS are
what keep it from snapping at either end, and they are the numbers to lower
first if it ever looks harsh again.
"""

import asyncio
import math
import time
from dataclasses import dataclass


CENTER_US = 1500                # electrical neutral, per SERVO_MAP.md

# Nominal for an MG90S: ~1000 us across 90 deg. NOT independently measured on
# this mechanism. The bench tools have a `calc` command that derives the real
# figure from two pulses and a protractor; paste the result here.
US_PER_DEG = 1000.0 / 90.0

TICK = 0.02                     # motion loop period, one 50 Hz servo frame


def clamp(value, low, high):
    return max(low, min(high, value))


def _us(degrees):
    """Degrees as an offset in microseconds, at the nominal scale."""

    return degrees * US_PER_DEG


@dataclass(frozen=True)
class Axis:
    """One servo: where it is wired, which way it goes, how far, how fast.

    `pulse_clamp` is a backstop, not the travel limit. `limits` is the real
    contract. The clamp only stops a trim value or a recalibrated us_per_deg
    from walking the pulse somewhere the bench never went.
    """

    channel: int
    sign: int
    limits: tuple
    rest: float
    slew_dps: float
    accel_dps2: float
    pulse_clamp: tuple
    us_per_deg: float = US_PER_DEG
    center_us: float = CENTER_US

    @property
    def reaches_speed_in(self):
        """Seconds from a standstill to full speed. For the bench to print."""

        return self.slew_dps / self.accel_dps2


# ---------------------------------------------------------------- the arms

# From cad/desk_bot.py. Change them there, not here.
ARM_LIMITS = (-20.0, 75.0)
ARM_REST = -8.0

# Fast enough to gesture with, slow enough that a printed linkage survives a
# bad target. Roughly a third of a second across a 30 degree beat.
ARM_SLEW_DPS = 100.0

# Up to speed in about a sixth of a second, so this is close to the plain
# speed limit the arms were proven with - just without the snap at each end.
ARM_ACCEL_DPS2 = 600.0

# The raw bench reached 2500 us right and 556 us left without binding, so
# these sit just inside observed-safe rather than at the servo's extremes.
ARM_PULSE_CLAMP = (600.0, 2400.0)

# ---------------------------------------------------------------- the head

# SERVO_MAP.md, verified on the assembled robot 2026-09-03. 1340..1660 us.
PAN_LIMITS = (-14.4, 14.4)
PAN_PULSE_CLAMP = (CENTER_US - _us(14.4), CENTER_US + _us(14.4))

# SERVO_MAP.md. Up is a LOWER pulse and was walked to 1056 us; down is
# approved only as far as 1540 us. Asymmetric on purpose - read the header.
NOD_LIMITS = (-3.6, 40.0)
NOD_PULSE_CLAMP = (CENTER_US - _us(40.0), CENTER_US + _us(3.6))

# WALKED ON THE ASSEMBLED ROBOT AND APPROVED, 2026-09-03.
#
# These are not a guess. The first runtime rates here were 18 and 10 deg/s,
# picked to be obviously safe; they were walked up on the bench in stages and
# accepted at these. The observed test was nod 0 -> -2 -> +5 -> 0 and pan
# 0 -> -5 -> +5 -> 0, at this exact profile, watched.
#
# What that does NOT cover: full-range travel and long-cycle durability. The
# rates are approved for short conversational motion, which is all the brain
# ever asks for, and are not yet proven for anything sustained.
PAN_SLEW_DPS = 144.0
NOD_SLEW_DPS = 108.0

# The eye wiring runs through the nod joint, so the accelerations still do the
# real work: pan reaches its cap in 0.36 s and nod in 0.46 s, and each spends
# the same again stopping. That ramp is what keeps a fast head from being a
# snapping one.
#
# These two are deliberately not round numbers. A flat 80% increase on the
# accelerations that matched the approved speeds - 450 and 324 - FAILED the
# discrete braking tests in test_arms.py: at those figures an axis can no
# longer bleed off its speed in whole 20 ms frames without a jerk on the
# landing frame. 398 and 237 are the nearby values that keep the invariant.
#
# Do not round them up, and do not relax the tests to make rounder ones pass.
# The tests are the reason these numbers are trustworthy.
PAN_ACCEL_DPS2 = 398.0
NOD_ACCEL_DPS2 = 237.0

# --------------------------------------------------------------- the table

AXES = {
    "arm_r": Axis(
        0, +1, ARM_LIMITS, ARM_REST,
        ARM_SLEW_DPS, ARM_ACCEL_DPS2, ARM_PULSE_CLAMP,
    ),
    "arm_l": Axis(
        3, -1, ARM_LIMITS, ARM_REST,
        ARM_SLEW_DPS, ARM_ACCEL_DPS2, ARM_PULSE_CLAMP,
    ),
    "pan": Axis(
        1, +1, PAN_LIMITS, 0.0,
        PAN_SLEW_DPS, PAN_ACCEL_DPS2, PAN_PULSE_CLAMP,
    ),
    "nod": Axis(
        2, -1, NOD_LIMITS, 0.0,
        NOD_SLEW_DPS, NOD_ACCEL_DPS2, NOD_PULSE_CLAMP,
    ),
}

ARM_AXES = ("arm_r", "arm_l")
HEAD_AXES = ("pan", "nod")

CHANNELS = {name: axis.channel for name, axis in AXES.items()}

# Per-axis neutral trim, in microseconds, added to the axis centre. The arm
# horns were re-indexed after the channel map was found, so the angle this
# code commands and the pose the mechanism takes do not agree until these are
# set. Discover them with `arm_bench` / `head_bench`, then paste the `save`
# output here so they survive a restart.
TRIM = {"arm_r": 0, "arm_l": 0, "pan": 0, "nod": 0}

# Kept for the arm bench and the arm tests, which predate the head and speak
# in bare arm numbers.
LIMITS = ARM_LIMITS
REST = ARM_REST
SLEW_DPS = ARM_SLEW_DPS
PULSE_CLAMP = ARM_PULSE_CLAMP
SIGN = {name: axis.sign for name, axis in AXES.items()}


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
    """Four servos, a target per axis, and a loop that slews toward them.

    The brain sends targets, never positions. Anything else would put the
    shape of the motion at the mercy of network jitter: a late message would
    become a stutter in the arm rather than a slightly stale goal.
    """

    def __init__(self, driver=None):
        self.driver = driver
        self.trim = dict(TRIM)
        self.target = {name: axis.rest for name, axis in AXES.items()}
        self.position = {name: None for name in AXES}   # None = limp

        # Degrees per second, carried between steps. This is what makes the
        # motion accelerate rather than snap; see the header.
        self.velocity = {name: 0.0 for name in AXES}

    def microseconds(self, axis, degrees):
        spec = AXES[axis]

        us = (
            spec.center_us
            + self.trim[axis]
            + spec.sign * degrees * spec.us_per_deg
        )

        return clamp(us, *spec.pulse_clamp)

    def degrees_from(self, axis, microseconds):
        """The angle a given pulse corresponds to. Inverse of microseconds().

        The bench needs this: measuring us_per_deg means commanding pulses
        directly, and an axis whose tracked position stopped matching the
        hardware would lurch on the next slewed move.
        """

        spec = AXES[axis]

        return (
            (microseconds - spec.center_us - self.trim[axis])
            / (spec.sign * spec.us_per_deg)
        )

    def _write(self, axis, degrees):
        self.position[axis] = degrees

        if self.driver is not None:
            self.driver.write(
                AXES[axis].channel,
                self.microseconds(axis, degrees),
            )

    def engage(self, axes=None):
        """Take the given axes from limp to their rest pose.

        This is the one move that is not slewed, and it cannot be: a limp
        servo has no known position to slew from. Every rest pose is at or
        near neutral, so the jump is small by design.
        """

        for axis in axes or AXES:
            self.target[axis] = AXES[axis].rest
            self.velocity[axis] = 0.0
            self._write(axis, AXES[axis].rest)

    def limp(self, axes=None):
        for axis in axes or AXES:
            self.position[axis] = None
            self.velocity[axis] = 0.0

            if self.driver is not None:
                self.driver.release(AXES[axis].channel)

    def parked(self, axes=None, within=0.05):
        """Whether the given axes have arrived at their rest pose.

        `park` is what uses this: an axis released while it is still somewhere
        else has to be jumped back the next time it engages, and a jump is
        exactly what the head's wiring cannot afford.
        """

        for axis in axes or AXES:
            here = self.position[axis]

            if here is not None and abs(here - AXES[axis].rest) > within:
                return False

        return True

    async def park(self, axes=None, timeout=3.0):
        """Bring axes home under acceleration control, then report.

        Called on the way out. Returning True means they arrived; False means
        the timeout won, and the caller should release them anyway rather
        than hold a pose forever on a dead connection.
        """

        axes = tuple(axes or AXES)

        for axis in axes:
            self.target[axis] = AXES[axis].rest

        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            if self.parked(axes):
                return True

            await asyncio.sleep(TICK)
            self.step(TICK)

        return self.parked(axes)

    def set_target(self, axis, degrees):
        """Aim an axis. Out-of-range angles are clamped, not refused.

        The benches refuse them, because a human typing at a bench wants to
        be told they are wrong. This runs under a gesture generator, where
        refusing means one axis silently stops following the speech while the
        others keep going. Clamping degrades to a pose that is merely at the
        limit, which is the better failure.
        """

        if axis not in AXES:
            return False

        self.target[axis] = clamp(float(degrees), *AXES[axis].limits)
        return True

    def step(self, seconds):
        """Advance every axis toward its target. Pure; the tests drive it.

        Speed AND acceleration limited. The velocity an axis is allowed to
        want is the lower of its own top speed and the speed it can still
        brake to a stop from in the distance that is left. Taking the braking
        term into account is what stops the axis overshooting and correcting,
        which would put a reversal into every single move.

        The braking term is the DISCRETE one, not v = sqrt(2 a s). The
        continuous curve tightens faster than one frame of deceleration can
        follow, so an axis running down it arrives still moving and has to be
        stopped dead on the last step - which is precisely the snap all of
        this exists to remove. Solving instead for the speed that a stack of
        whole frames can bleed off:

            v^2 + (a dt) v - 2 a s = 0

        leaves the axis genuinely at rest as it touches the target.
        """

        for axis, spec in AXES.items():
            here = self.position[axis]

            if here is None:
                # Limp. engage() is what ends that, not a target.
                self.velocity[axis] = 0.0
                continue

            error = self.target[axis] - here
            speed = self.velocity[axis]

            if abs(error) < 1e-9:
                self.velocity[axis] = 0.0
                continue

            step = spec.accel_dps2 * seconds

            braking = 0.5 * (
                -step
                + math.sqrt(step * step + 8.0 * spec.accel_dps2 * abs(error))
            )

            # `abs(error) / seconds` is the speed that lands exactly on the
            # target this frame. Including it means the axis aims to arrive
            # rather than to arrive-and-be-trimmed, and a trim is a velocity
            # change the acceleration limit never agreed to.
            wanted = math.copysign(
                min(spec.slew_dps, braking, abs(error) / seconds),
                error,
            )

            # The velocity itself is rate limited. This is the whole point,
            # and there is deliberately nothing after it that can move the
            # axis further than this allows.
            #
            # In particular there is no "snap onto the target" step. An axis
            # chasing a target that keeps moving - which is every axis, under
            # a gesture generator - would hit such a rule several times a
            # second, and each hit is a velocity change outside the limit.
            # If the arithmetic ever does carry it past the target, letting
            # it drift back is smooth; yanking it back is not.
            speed = clamp(wanted, speed - step, speed + step)

            landed = here + speed * seconds

            # Whatever the arithmetic did, the observed envelope holds.
            low, high = spec.limits

            if not low <= landed <= high:
                landed = clamp(landed, low, high)
                speed = 0.0

            self.velocity[axis] = speed
            self._write(axis, landed)

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
