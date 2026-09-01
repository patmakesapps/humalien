"""What the arms must never do, however wrong the brain gets."""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from humalien_node.arms import (
    Arms,
    CENTER_US,
    CHANNELS,
    LIMITS,
    PULSE_CLAMP,
    REST,
    SLEW_DPS,
)


class FakeDriver:
    def __init__(self):
        self.written = {}
        self.released = []

    def write(self, channel, microseconds):
        self.written[channel] = microseconds

    def release(self, channel):
        self.released.append(channel)


class TestDirection(unittest.TestCase):
    """node/SERVO_MAP.md: channel 0 raises going forward, channel 3 lowers.

    cad/desk_bot.py poses both arms with POSITIVE angles for forward. If
    this inversion is ever lost the arms scissor - one forward, one back -
    on a linkage whose clearances were only swept with them moving together.
    """

    def test_forward_raises_the_right_arm_pulse(self):
        arms = Arms()

        self.assertGreater(arms.microseconds("arm_r", 40.0), CENTER_US)

    def test_forward_lowers_the_left_arm_pulse(self):
        arms = Arms()

        self.assertLess(arms.microseconds("arm_l", 40.0), CENTER_US)

    def test_the_same_forward_angle_moves_both_arms_equally(self):
        arms = Arms()

        right = arms.microseconds("arm_r", 40.0) - CENTER_US
        left = CENTER_US - arms.microseconds("arm_l", 40.0)

        self.assertAlmostEqual(right, left, places=6)


class TestLimits(unittest.TestCase):
    def test_targets_are_clamped_to_the_cad_range(self):
        arms = Arms()

        arms.set_target("arm_l", 500.0)
        self.assertEqual(arms.target["arm_l"], LIMITS[1])

        arms.set_target("arm_l", -500.0)
        self.assertEqual(arms.target["arm_l"], LIMITS[0])

    def test_pulses_stay_inside_the_bench_proven_band(self):
        arms = Arms()

        for axis in CHANNELS:
            for degrees in (-1000.0, LIMITS[0], 0.0, LIMITS[1], 1000.0):
                us = arms.microseconds(axis, degrees)

                self.assertGreaterEqual(us, PULSE_CLAMP[0])
                self.assertLessEqual(us, PULSE_CLAMP[1])

    def test_uncalibrated_axes_cannot_be_addressed(self):
        arms = Arms()

        # SERVO_MAP.md: pan and nod are wired but not calibrated.
        self.assertFalse(arms.set_target("pan", 10.0))
        self.assertFalse(arms.set_target("nod", 10.0))
        self.assertNotIn("pan", arms.target)


class TestMotion(unittest.TestCase):
    def test_arms_start_limp(self):
        arms = Arms(FakeDriver())

        self.assertIsNone(arms.position["arm_l"])
        self.assertIsNone(arms.position["arm_r"])

    def test_a_limp_arm_does_not_move_on_a_target(self):
        driver = FakeDriver()
        arms = Arms(driver)

        arms.set_target("arm_l", 60.0)
        arms.step(1.0)

        self.assertIsNone(arms.position["arm_l"])
        self.assertEqual(driver.written, {})

    def test_engage_brings_both_arms_to_rest(self):
        arms = Arms(FakeDriver())
        arms.engage()

        self.assertEqual(arms.position["arm_l"], REST)
        self.assertEqual(arms.position["arm_r"], REST)

    def test_a_far_target_is_slewed_not_jumped(self):
        arms = Arms(FakeDriver())
        arms.engage()
        arms.set_target("arm_l", LIMITS[1])

        arms.step(0.02)

        travelled = arms.position["arm_l"] - REST

        self.assertAlmostEqual(travelled, SLEW_DPS * 0.02, places=6)
        self.assertLess(arms.position["arm_l"], LIMITS[1])

    def test_slewing_arrives_and_then_holds(self):
        arms = Arms(FakeDriver())
        arms.engage()
        arms.set_target("arm_r", 40.0)

        for _ in range(500):
            arms.step(0.02)

        self.assertAlmostEqual(arms.position["arm_r"], 40.0, places=6)

    def test_limp_releases_every_channel(self):
        driver = FakeDriver()
        arms = Arms(driver)
        arms.engage()
        arms.limp()

        self.assertEqual(sorted(driver.released), sorted(CHANNELS.values()))
        self.assertIsNone(arms.position["arm_r"])


if __name__ == "__main__":
    unittest.main()
