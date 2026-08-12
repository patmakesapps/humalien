import unittest

from gaze import (
    HOLDING,
    IDLE,
    RECENTERING,
    TRACKING,
    FaceBox,
    GazeController,
    select_primary_face,
)


class FaceBoxTests(unittest.TestCase):
    def test_center_maps_to_zero(self):
        face = FaceBox(x=40, y=40, width=20, height=20)

        self.assertEqual(face.normalized_center(100, 100), (0.0, 0.0))

    def test_coordinates_are_clamped_to_camera_range(self):
        face = FaceBox(x=100, y=-40, width=20, height=20)

        self.assertEqual(face.normalized_center(100, 100), (1.0, -1.0))

    def test_largest_face_is_primary(self):
        small = FaceBox(x=0, y=0, width=20, height=20)
        large = FaceBox(x=20, y=20, width=60, height=40)

        self.assertIs(select_primary_face([small, large]), large)
        self.assertIsNone(select_primary_face([]))


class GazeControllerTests(unittest.TestCase):
    def setUp(self):
        self.controller = GazeController(
            smoothing_seconds=0.1,
            hold_seconds=0.3,
            recenter_seconds=0.5,
        )

    def update(self, face, now):
        return self.controller.update(
            face,
            frame_width=100,
            frame_height=100,
            now=now,
        )

    def test_starts_centered_without_a_face(self):
        target = self.update(None, 0.0)

        self.assertEqual(target.state, IDLE)
        self.assertEqual((target.x, target.y), (0.0, 0.0))

    def test_acquires_first_face_immediately(self):
        target = self.update(
            FaceBox(x=70, y=40, width=20, height=20),
            0.0,
        )

        self.assertEqual(target.state, TRACKING)
        self.assertAlmostEqual(target.x, 0.6)
        self.assertAlmostEqual(target.y, 0.0)

    def test_smooths_a_large_detection_jump(self):
        self.update(FaceBox(x=70, y=40, width=20, height=20), 0.0)
        target = self.update(
            FaceBox(x=10, y=40, width=20, height=20),
            0.05,
        )

        self.assertEqual(target.state, TRACKING)
        self.assertGreater(target.x, -0.6)
        self.assertLess(target.x, 0.6)

    def test_holds_a_brief_miss_then_recenters(self):
        acquired = self.update(
            FaceBox(x=70, y=40, width=20, height=20),
            0.0,
        )
        held = self.update(None, 0.2)
        recentering = self.update(None, 0.5)

        self.assertEqual(held.state, HOLDING)
        self.assertAlmostEqual(held.x, acquired.x)
        self.assertEqual(recentering.state, RECENTERING)
        self.assertLess(abs(recentering.x), abs(held.x))

    def test_rejects_time_moving_backwards(self):
        self.update(None, 1.0)

        with self.assertRaises(ValueError):
            self.update(None, 0.9)


if __name__ == "__main__":
    unittest.main()
