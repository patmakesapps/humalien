"""What the mechanism must never do, however wrong the brain gets."""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from humalien_node.arms import (
    ARM_AXES,
    AXES,
    Arms,
    CENTER_US,
    CHANNELS,
    HEAD_AXES,
    LIMITS,
    NOD_LIMITS,
    PAN_LIMITS,
    PULSE_CLAMP,
    REST,
    SLEW_DPS,
    TICK,
)


class FakeDriver:
    def __init__(self):
        self.written = {}
        self.released = []

    def write(self, channel, microseconds):
        self.written[channel] = microseconds

    def release(self, channel):
        self.released.append(channel)


def travel(arms, axis, target, seconds=12.0, step=TICK):
    """Drive one axis to a target and return every position it passed."""

    arms.set_target(axis, target)

    seen = [arms.position[axis]]

    for _ in range(int(seconds / step)):
        arms.step(step)
        seen.append(arms.position[axis])

    return seen


def speeds(seen, step=TICK):
    return [(b - a) / step for a, b in zip(seen, seen[1:])]


def accelerations(seen, step=TICK):
    rates = speeds(seen, step)

    return [(b - a) / step for a, b in zip(rates, rates[1:])]


class TestDirection(unittest.TestCase):
    """node/SERVO_MAP.md, in assertions.

    cad/desk_bot.py poses both arms with POSITIVE angles for forward. If the
    arm inversion is ever lost the arms scissor - one forward, one back - on a
    linkage whose clearances were only swept with them moving together.
    """

    def test_forward_raises_the_right_arm_pulse(self):
        self.assertGreater(Arms().microseconds("arm_r", 40.0), CENTER_US)

    def test_forward_lowers_the_left_arm_pulse(self):
        self.assertLess(Arms().microseconds("arm_l", 40.0), CENTER_US)

    def test_the_same_forward_angle_moves_both_arms_equally(self):
        arms = Arms()

        right = arms.microseconds("arm_r", 40.0) - CENTER_US
        left = CENTER_US - arms.microseconds("arm_l", 40.0)

        self.assertAlmostEqual(right, left, places=6)

    def test_pan_left_raises_the_pulse(self):
        # SERVO_MAP.md: "left raises the pulse; right lowers it", and this
        # file's convention is that positive pan is the robot's own left.
        self.assertGreater(Arms().microseconds("pan", 10.0), CENTER_US)
        self.assertLess(Arms().microseconds("pan", -10.0), CENTER_US)

    def test_nod_up_lowers_the_pulse(self):
        # SERVO_MAP.md: "Physical up is a lower pulse. Keep the CAD convention
        # that positive nod means up, so this axis needs an electrical sign
        # of -1."
        self.assertLess(Arms().microseconds("nod", 20.0), CENTER_US)


class TestLimits(unittest.TestCase):
    def test_arm_targets_are_clamped_to_the_cad_range(self):
        arms = Arms()

        arms.set_target("arm_l", 500.0)
        self.assertEqual(arms.target["arm_l"], LIMITS[1])

        arms.set_target("arm_l", -500.0)
        self.assertEqual(arms.target["arm_l"], LIMITS[0])

    def test_the_head_is_clamped_to_what_was_observed_not_to_the_cad(self):
        """cad/desk_bot.py says pan +-80 and nod +-22. Neither was observed."""

        arms = Arms()

        arms.set_target("pan", 80.0)
        self.assertEqual(arms.target["pan"], PAN_LIMITS[1])

        arms.set_target("nod", -22.0)
        self.assertEqual(arms.target["nod"], NOD_LIMITS[0])

    def test_the_nod_range_is_asymmetric_on_purpose(self):
        """Up was walked to +40 and watched. Down past -3.6 never was.

        A later attempt at full downward nods toward 1944 us was stopped
        after erratic motion. Making this symmetric would re-enter that.
        """

        self.assertGreater(NOD_LIMITS[1], 20.0)
        self.assertGreater(NOD_LIMITS[0], -5.0)

    def test_every_axis_stays_inside_its_own_bench_proven_band(self):
        arms = Arms()

        for axis, spec in AXES.items():
            for degrees in (-1000.0, spec.limits[0], 0.0, spec.limits[1], 1000.0):
                us = arms.microseconds(axis, degrees)

                self.assertGreaterEqual(us, spec.pulse_clamp[0], axis)
                self.assertLessEqual(us, spec.pulse_clamp[1], axis)

    def test_the_head_can_never_reach_an_arm_pulse(self):
        """A per-axis clamp is the point. One shared band would not do this."""

        arms = Arms()

        for axis in HEAD_AXES:
            for degrees in (-1000.0, 1000.0):
                us = arms.microseconds(axis, degrees)

                self.assertGreater(us, 1000.0, axis)
                self.assertLess(us, 1700.0, axis)

    def test_the_head_pulses_match_the_numbers_that_were_observed(self):
        """SERVO_MAP.md: pan 1340..1660, nod 1056..1540. Verified by eye."""

        arms = Arms()

        self.assertAlmostEqual(arms.microseconds("pan", PAN_LIMITS[0]), 1340, places=0)
        self.assertAlmostEqual(arms.microseconds("pan", PAN_LIMITS[1]), 1660, places=0)
        self.assertAlmostEqual(arms.microseconds("nod", NOD_LIMITS[0]), 1540, places=0)
        self.assertAlmostEqual(arms.microseconds("nod", NOD_LIMITS[1]), 1056, places=0)

    def test_an_unknown_axis_is_refused(self):
        self.assertFalse(Arms().set_target("jaw", 10.0))


class TestCalibration(unittest.TestCase):
    """Trim and the pulse inverse, which the benches depend on."""

    def test_trim_shifts_neutral_without_moving_the_range(self):
        arms = Arms()
        plain = arms.microseconds("arm_r", 0.0)

        arms.trim["arm_r"] = -40
        self.assertAlmostEqual(arms.microseconds("arm_r", 0.0), plain - 40)

    def test_trim_is_per_axis(self):
        arms = Arms()
        arms.trim["arm_r"] = -40

        self.assertEqual(arms.microseconds("arm_l", 0.0), CENTER_US)
        self.assertEqual(arms.microseconds("pan", 0.0), CENTER_US)

    def test_pulse_and_degrees_are_exact_inverses(self):
        arms = Arms()
        arms.trim["arm_l"] = 35

        for axis in ARM_AXES:
            for us in (900.0, 1200.0, CENTER_US, 1800.0, 2300.0):
                degrees = arms.degrees_from(axis, us)

                self.assertAlmostEqual(
                    arms.microseconds(axis, degrees), us, places=6
                )

    def test_trim_does_not_escape_the_pulse_clamp(self):
        arms = Arms()
        arms.trim["arm_r"] = 5000
        arms.trim["nod"] = -5000

        self.assertLessEqual(arms.microseconds("arm_r", LIMITS[1]), PULSE_CLAMP[1])
        self.assertGreaterEqual(
            arms.microseconds("nod", NOD_LIMITS[1]),
            AXES["nod"].pulse_clamp[0],
        )


class TestMotion(unittest.TestCase):
    def test_everything_starts_limp(self):
        arms = Arms(FakeDriver())

        for axis in AXES:
            self.assertIsNone(arms.position[axis], axis)

    def test_a_limp_axis_does_not_move_on_a_target(self):
        driver = FakeDriver()
        arms = Arms(driver)

        arms.set_target("arm_l", 60.0)
        arms.step(1.0)

        self.assertIsNone(arms.position["arm_l"])
        self.assertEqual(driver.written, {})

    def test_engage_brings_everything_to_rest(self):
        arms = Arms(FakeDriver())
        arms.engage()

        self.assertEqual(arms.position["arm_l"], REST)
        self.assertEqual(arms.position["pan"], 0.0)
        self.assertEqual(arms.position["nod"], 0.0)

    def test_engage_can_take_a_subset(self):
        arms = Arms(FakeDriver())
        arms.engage(HEAD_AXES)

        self.assertIsNone(arms.position["arm_l"])
        self.assertEqual(arms.position["nod"], 0.0)

    def test_a_far_target_is_slewed_not_jumped(self):
        arms = Arms(FakeDriver())
        arms.engage()
        arms.set_target("arm_l", LIMITS[1])

        arms.step(TICK)

        self.assertGreater(arms.position["arm_l"], REST)
        self.assertLess(arms.position["arm_l"] - REST, SLEW_DPS * TICK)

    def test_slewing_arrives_and_then_holds(self):
        arms = Arms(FakeDriver())
        arms.engage()

        seen = travel(arms, "arm_r", 40.0)

        self.assertAlmostEqual(seen[-1], 40.0, places=6)
        self.assertAlmostEqual(arms.velocity["arm_r"], 0.0, places=6)

    def test_limp_releases_every_channel(self):
        driver = FakeDriver()
        arms = Arms(driver)
        arms.engage()
        arms.limp()

        self.assertEqual(sorted(driver.released), sorted(CHANNELS.values()))
        self.assertIsNone(arms.position["arm_r"])

    def test_limp_can_take_a_subset(self):
        driver = FakeDriver()
        arms = Arms(driver)
        arms.engage()
        arms.limp(ARM_AXES)

        self.assertEqual(sorted(driver.released), [0, 3])
        self.assertEqual(arms.position["nod"], 0.0)


class TestGentleness(unittest.TestCase):
    """The eye wiring runs through the nod joint. Nothing may snap.

    A speed limit alone still steps velocity from zero to the cap in one
    frame, and the servo answers that with everything it has. These are the
    tests that say the ramp is real.
    """

    def test_no_axis_starts_at_full_speed(self):
        arms = Arms(FakeDriver())
        arms.engage()

        for axis, spec in AXES.items():
            arms.engage()
            first = travel(arms, axis, spec.limits[1], seconds=TICK * 2)

            self.assertLess(
                abs(speeds(first)[0]),
                spec.slew_dps * 0.5,
                f"{axis} left at half its top speed in one frame",
            )

    def test_the_head_never_exceeds_its_acceleration_while_moving(self):
        """The limit holds everywhere except the frame it lands on.

        Arriving exactly on a target in discrete time means the last step is
        a partial one, which sheds slightly more speed than the nominal limit
        for that single frame. `test_the_landing_frame_is_the_only_exception`
        is what stops that becoming a hiding place for a real snap.
        """

        for axis in HEAD_AXES:
            arms = Arms(FakeDriver())
            arms.engage()

            spec = AXES[axis]

            # The worst case is a target that reverses at full speed.
            seen = travel(arms, axis, spec.limits[1], seconds=6.0)
            seen += travel(arms, axis, spec.limits[0], seconds=6.0)

            rates = speeds(seen)
            moving = [
                abs(rate)
                for rate, was in zip(accelerations(seen), rates)
                if abs(was) > 2.0
            ]

            worst = max(moving)

            self.assertLessEqual(
                worst,
                spec.accel_dps2 * 1.05,
                f"{axis} accelerated at {worst:.1f} deg/s2 while moving",
            )

    def test_the_landing_frame_is_the_only_exception(self):
        """Whatever the arrival frame sheds, it sheds it from walking pace."""

        for axis in HEAD_AXES:
            arms = Arms(FakeDriver())
            arms.engage()

            spec = AXES[axis]
            seen = travel(arms, axis, spec.limits[1], seconds=8.0)

            rates = speeds(seen)
            over = [
                abs(was)
                for rate, was in zip(accelerations(seen), rates)
                if abs(rate) > spec.accel_dps2 * 1.05
            ]

            self.assertLessEqual(
                max(over, default=0.0),
                2.0,
                f"{axis} broke its acceleration limit at speed, not on arrival",
            )

    def test_the_head_never_exceeds_its_speed(self):
        for axis in HEAD_AXES:
            arms = Arms(FakeDriver())
            arms.engage()

            spec = AXES[axis]
            seen = travel(arms, axis, spec.limits[1], seconds=8.0)

            worst = max(abs(s) for s in speeds(seen))

            self.assertLessEqual(worst, spec.slew_dps * 1.02, axis)

    def test_the_nod_takes_a_visible_moment_to_get_going(self):
        """A number to argue with, rather than a promise of smoothness."""

        spec = AXES["nod"]

        self.assertGreaterEqual(spec.reaches_speed_in, 0.25)

    def test_nothing_overshoots_its_target(self):
        """An overshoot puts a reversal into every move. Worse than slow."""

        for axis, spec in AXES.items():
            arms = Arms(FakeDriver())
            arms.engage()

            target = spec.limits[1]
            seen = travel(arms, axis, target, seconds=12.0)

            self.assertLessEqual(
                max(seen),
                target + 1e-6,
                f"{axis} overshot to {max(seen):.3f}",
            )

    def test_small_reversing_targets_cannot_make_it_snap(self):
        """What the gesture generator actually sends, and it is the hard case.

        A brain following speech reverses its target by a fraction of a
        degree many times a second. An anti-overshoot rule that snaps the
        axis onto the target regardless of which way it is already moving
        flips the velocity in one frame - a real jerk, on every reversal,
        invisible to any test that only ever asks for large moves.
        """

        for axis in HEAD_AXES:
            arms = Arms(FakeDriver())
            arms.engage()

            seen = [arms.position[axis]]

            for index in range(1500):
                # Slow enough that the axis keeps catching its own target,
                # which is what puts it mid-deceleration when the target
                # turns around.
                arms.set_target(axis, 3.0 * math.sin(index * 0.05))
                arms.step(TICK)
                seen.append(arms.position[axis])

            worst = max(abs(a) for a in accelerations(seen))

            self.assertLessEqual(
                worst,
                AXES[axis].accel_dps2 * 1.05,
                f"{axis} snapped at {worst:.1f} deg/s2 chasing small reversals",
            )

    def test_a_burst_of_conflicting_targets_cannot_make_it_snap(self):
        """What a broken brain looks like: a new extreme target every frame."""

        arms = Arms(FakeDriver())
        arms.engage()

        seen = [arms.position["nod"]]

        for index in range(400):
            arms.set_target("nod", NOD_LIMITS[index % 2])
            arms.step(TICK)
            seen.append(arms.position["nod"])

        worst = max(abs(a) for a in accelerations(seen))

        self.assertLessEqual(worst, AXES["nod"].accel_dps2 * 1.05)


class TestParking(unittest.IsolatedAsyncioTestCase):
    """The head is brought home before it is released, so it cannot jump."""

    async def test_park_brings_the_head_to_neutral(self):
        arms = Arms(FakeDriver())
        arms.engage()
        arms.set_target("nod", 30.0)

        for _ in range(400):
            arms.step(TICK)

        self.assertGreater(arms.position["nod"], 25.0)
        self.assertTrue(await arms.park(HEAD_AXES, timeout=30.0))
        self.assertAlmostEqual(arms.position["nod"], 0.0, places=1)

    async def test_park_gives_up_rather_than_hanging_on_a_jam(self):
        arms = Arms(FakeDriver())
        arms.engage()
        arms.set_target("nod", 40.0)

        for _ in range(400):
            arms.step(TICK)

        # Far too little time to travel 40 degrees at the nod's rate.
        self.assertFalse(await arms.park(HEAD_AXES, timeout=0.2))

    async def test_park_is_still_gentle(self):
        arms = Arms(FakeDriver())
        arms.engage()
        arms.set_target("nod", 40.0)

        for _ in range(400):
            arms.step(TICK)

        seen = [arms.position["nod"]]
        arms.target["nod"] = 0.0

        while abs(arms.position["nod"]) > 0.05:
            arms.step(TICK)
            seen.append(arms.position["nod"])

        worst = max(abs(a) for a in accelerations(seen))

        self.assertLessEqual(worst, AXES["nod"].accel_dps2 * 1.05)


if __name__ == "__main__":
    unittest.main()
