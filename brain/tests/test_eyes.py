import unittest

import numpy as np

from eyes import Eyes, sharpness
from people import PeopleStore


def sharp_frame(seed: int = 0) -> np.ndarray:
    """High-contrast noise. Lots of edges, so a high Laplacian variance."""

    return np.random.default_rng(seed).integers(
        0, 255, (120, 160, 3), dtype=np.uint8
    )


def blurred_frame() -> np.ndarray:
    """Flat grey. No edges at all, so the blur score bottoms out."""

    return np.full((120, 160, 3), 128, dtype=np.uint8)


class SharpnessTests(unittest.TestCase):
    def test_a_flat_frame_scores_lower_than_a_detailed_one(self):
        self.assertLess(sharpness(blurred_frame()), sharpness(sharp_frame()))


class FrameMemoryTests(unittest.TestCase):
    def setUp(self):
        self.store = PeopleStore(":memory:")
        self.eyes = Eyes(None, remember_seconds=2.0)

    def tearDown(self):
        self.store.close()

    def test_nothing_seen_yet(self):
        self.assertIsNone(self.eyes.clearest_frame())

    def test_picks_the_sharpest_frame_in_the_window(self):
        # The blurred frame is the most recent, so "latest" would be wrong.
        self.eyes._remember(sharp_frame(1), at=10.0)
        self.eyes._remember(blurred_frame(), at=10.5)

        chosen = self.eyes.clearest_frame(since=9.0, until=11.0)

        self.assertGreater(sharpness(chosen), sharpness(blurred_frame()))

    def test_ignores_frames_outside_the_window(self):
        self.eyes._remember(sharp_frame(2), at=1.0)
        self.eyes._remember(blurred_frame(), at=10.0)

        chosen = self.eyes.clearest_frame(since=9.0, until=11.0)

        # Only the blurred frame was in the window, so it has to be that one
        # rather than the sharper frame from nine seconds earlier.
        np.testing.assert_array_equal(chosen, blurred_frame())

    def test_falls_back_to_the_latest_when_the_window_is_empty(self):
        self.eyes._remember(sharp_frame(3), at=1.0)

        chosen = self.eyes.clearest_frame(since=100.0, until=200.0)

        self.assertIsNotNone(chosen)

    def test_no_window_means_the_sharpest_of_everything(self):
        self.eyes._remember(blurred_frame(), at=1.0)
        self.eyes._remember(sharp_frame(4), at=2.0)

        chosen = self.eyes.clearest_frame()

        self.assertGreater(sharpness(chosen), sharpness(blurred_frame()))

    def test_old_frames_are_dropped(self):
        for index in range(500):
            self.eyes._remember(sharp_frame(index % 5), at=float(index))

        # Two seconds of history, not five hundred frames of it.
        self.assertLessEqual(len(self.eyes.recent), 30)

    def test_frames_are_stored_downscaled(self):
        big = np.zeros((1080, 1920, 3), dtype=np.uint8)

        self.eyes._remember(big, at=1.0)

        stored = self.eyes.recent[-1].frame
        self.assertLessEqual(max(stored.shape[:2]), 512)


if __name__ == "__main__":
    unittest.main()
