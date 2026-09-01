"""The arms must follow the speech, and stop when it does."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gestures import ARM_RANGE, ARM_REST, LEVEL_REFERENCE, Gestures
from playback import level


def run(gestures, seconds, step=0.05, loudness=None):
    """Advance the generator, optionally feeding it speech the whole way."""

    poses = []

    for _ in range(int(seconds / step)):
        if loudness is not None:
            gestures.feed(loudness)

        poses.append(gestures.pose(step))

    return poses


class TestLevel(unittest.TestCase):
    def test_silence_is_zero(self):
        self.assertEqual(level(b"\x00\x00" * 480), 0.0)

    def test_a_loud_chunk_reads_louder_than_a_quiet_one(self):
        import numpy as np

        quiet = (np.ones(480, dtype="<i2") * 800).tobytes()
        loud = (np.ones(480, dtype="<i2") * 12000).tobytes()

        self.assertLess(level(quiet), level(loud))

    def test_squaring_does_not_overflow(self):
        import numpy as np

        # Full scale in int16. Squared in int16 this wraps and reads quiet.
        full = (np.ones(480, dtype="<i2") * 32767).tobytes()

        self.assertGreater(level(full), 0.9)

    def test_a_ragged_chunk_does_not_raise(self):
        self.assertEqual(level(b"\x01"), 0.0)
        self.assertIsInstance(level(b"\x00\x00\x00"), float)


class TestGestures(unittest.TestCase):
    def test_silence_holds_the_arms_at_rest(self):
        gestures = Gestures(websocket=None)

        arm_l, arm_r = run(gestures, seconds=2.0)[-1]

        self.assertAlmostEqual(arm_l, ARM_REST, places=3)
        self.assertAlmostEqual(arm_r, ARM_REST, places=3)

    def test_speech_lifts_the_arms_forward(self):
        gestures = Gestures(websocket=None)

        poses = run(gestures, seconds=2.0, loudness=LEVEL_REFERENCE)
        highest = max(max(pose) for pose in poses)

        self.assertGreater(highest, ARM_REST + 10.0)

    def test_the_arms_come_home_when_the_speech_stops(self):
        gestures = Gestures(websocket=None)

        run(gestures, seconds=2.0, loudness=LEVEL_REFERENCE)
        arm_l, arm_r = run(gestures, seconds=4.0)[-1]

        self.assertAlmostEqual(arm_l, ARM_REST, places=1)
        self.assertAlmostEqual(arm_r, ARM_REST, places=1)

    def test_the_arms_do_not_move_as_one(self):
        """Both arms on the same target reads as a mechanism, not a person."""

        gestures = Gestures(websocket=None)
        poses = run(gestures, seconds=4.0, loudness=LEVEL_REFERENCE)

        self.assertTrue(any(abs(l - r) > 2.0 for l, r in poses))

    def test_every_pose_is_inside_the_cad_range(self):
        gestures = Gestures(websocket=None)

        # Far louder than speech ever is, for as long as it takes.
        for pose in run(gestures, seconds=20.0, loudness=1.0):
            for angle in pose:
                self.assertGreaterEqual(angle, ARM_RANGE[0])
                self.assertLessEqual(angle, ARM_RANGE[1])

    def test_quiet_speech_gestures_smaller_than_loud_speech(self):
        quiet = run(Gestures(None), 6.0, loudness=LEVEL_REFERENCE * 0.25)
        loud = run(Gestures(None), 6.0, loudness=LEVEL_REFERENCE)

        self.assertLess(
            max(max(pose) for pose in quiet),
            max(max(pose) for pose in loud),
        )

    def test_holding_still_is_silent_on_the_wire(self):
        gestures = Gestures(websocket=None)
        gestures.last_sent = (ARM_REST, ARM_REST)

        self.assertFalse(gestures.worth_sending(ARM_REST, ARM_REST))
        self.assertTrue(gestures.worth_sending(ARM_REST + 5.0, ARM_REST))


if __name__ == "__main__":
    unittest.main()
