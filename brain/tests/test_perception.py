import unittest

import numpy as np

from people import PeopleStore, normalize
from perception import FRAMES_BEFORE_ENROLLING, Perception
from vision import Detection

from gaze import FaceBox


def base_embedding(seed: int = 0) -> np.ndarray:
    return normalize(np.random.default_rng(seed).normal(size=128).astype(np.float32))


def at_similarity(base: np.ndarray, target: float) -> np.ndarray:
    """Build a vector whose cosine similarity to `base` is exactly `target`."""

    other = np.random.default_rng(99).normal(size=len(base)).astype(np.float32)
    other = normalize(other - base * float(other @ base))

    return normalize(base * target + other * (1 - target**2) ** 0.5)


class FakeDetector:
    def __init__(self, boxes):
        self.boxes = boxes

    def detect(self, frame):
        box = self.boxes.pop(0) if self.boxes else None

        if box is None:
            return []

        return [Detection(box=box, row=np.zeros(15, dtype=np.float32))]


class FakeRecognizer:
    def __init__(self, embedding):
        self.embedding = embedding

    def embed(self, frame, detection):
        return self.embedding


def moving_boxes(count: int, *, step: int = 4) -> list[FaceBox]:
    return [FaceBox(x=100 + i * step, y=100, width=80, height=80) for i in range(count)]


def still_boxes(count: int) -> list[FaceBox]:
    return [FaceBox(x=100, y=100, width=80, height=80) for _ in range(count)]


class PerceptionTests(unittest.TestCase):
    def setUp(self):
        self.store = PeopleStore(":memory:")
        self.frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def tearDown(self):
        self.store.close()

    def run_polls(self, boxes, embedding):
        perception = Perception(
            self.store,
            detector=FakeDetector(list(boxes)),
            recognizer=FakeRecognizer(embedding),
        )

        for index in range(len(boxes)):
            perception.poll(self.frame, now=float(index))

    def test_a_moving_stranger_is_enrolled(self):
        self.run_polls(moving_boxes(FRAMES_BEFORE_ENROLLING + 2), base_embedding())

        self.assertEqual(len(self.store.people()), 1)

    def test_a_motionless_face_is_never_enrolled(self):
        # A photograph on the wall is a perfect, permanently detected face.
        self.run_polls(still_boxes(30), base_embedding())

        self.assertEqual(self.store.people(), [])

    def test_a_brief_glimpse_is_not_enough(self):
        self.run_polls(moving_boxes(FRAMES_BEFORE_ENROLLING - 1), base_embedding())

        self.assertEqual(self.store.people(), [])

    def test_a_near_miss_does_not_create_a_second_record(self):
        # 0.38 is the observed score for a known person at an awkward angle:
        # under MATCH_THRESHOLD, but far too similar to be a stranger.
        known = base_embedding()
        self.store.create_person(known)

        self.run_polls(moving_boxes(20), at_similarity(known, 0.38))

        self.assertEqual(len(self.store.people()), 1)

    def test_a_genuinely_different_person_still_enrolls(self):
        # Two different people measured around 0.28, so the guard must not
        # be so wide that real strangers can never be recorded.
        known = base_embedding()
        self.store.create_person(known)

        self.run_polls(moving_boxes(20), at_similarity(known, 0.28))

        self.assertEqual(len(self.store.people()), 2)

    def test_a_returning_face_reuses_its_record(self):
        known = base_embedding()

        self.run_polls(moving_boxes(20), known)
        self.run_polls(moving_boxes(20), at_similarity(known, 0.85))

        self.assertEqual(len(self.store.people()), 1)
        self.assertGreater(self.store.people()[0].sighting_count, 1)


if __name__ == "__main__":
    unittest.main()
