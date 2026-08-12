import unittest

import numpy as np

from gaze import FaceBox
from people import PeopleStore, normalize
from perception import SECONDS_BEFORE_INTRODUCING, Perception
from vision import Detection


def base_embedding(seed: int = 0) -> np.ndarray:
    return normalize(np.random.default_rng(seed).normal(size=128).astype(np.float32))


class FakeDetector:
    def __init__(self, boxes):
        self.boxes = boxes

    def detect(self, frame):
        box = self.boxes.pop(0) if self.boxes else None

        return [] if box is None else [
            Detection(box=box, row=np.zeros(15, dtype=np.float32))
        ]


class FakeRecognizer:
    def __init__(self, embedding):
        self.embedding = embedding

    def embed(self, frame, detection):
        return self.embedding


def boxes(count: int) -> list[FaceBox]:
    return [FaceBox(x=100 + i * 4, y=100, width=80, height=80) for i in range(count)]


class PerceptionTests(unittest.TestCase):
    def setUp(self):
        self.store = PeopleStore(":memory:")
        self.frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def tearDown(self):
        self.store.close()

    def build(self, count, embedding):
        return Perception(
            self.store,
            detector=FakeDetector(boxes(count)),
            recognizer=FakeRecognizer(embedding),
        )

    def run_polls(self, perception, count, *, step: float = 1.0):
        last = []

        for index in range(count):
            last = perception.poll(self.frame, now=index * step)

        return last

    def test_watching_a_stranger_stores_nothing(self):
        # The whole point of v1: a face nobody has introduced leaves no
        # trace, so there is nothing to clean up later.
        perception = self.build(50, base_embedding())

        self.run_polls(perception, 50)

        self.assertEqual(self.store.people(), [])

    def test_a_stranger_is_reported_but_unmatched(self):
        perception = self.build(3, base_embedding())

        sightings = self.run_polls(perception, 3)

        self.assertEqual(len(sightings), 1)
        self.assertIsNone(sightings[0].match)

    def test_a_lingering_stranger_is_worth_introducing(self):
        perception = self.build(10, base_embedding())

        sightings = self.run_polls(perception, 10)
        now = 9.0

        self.assertGreater(now, SECONDS_BEFORE_INTRODUCING)
        self.assertTrue(sightings[0].is_a_stranger(now))

    def test_a_glimpse_is_not_worth_introducing(self):
        perception = self.build(2, base_embedding())

        sightings = self.run_polls(perception, 2, step=0.1)

        self.assertFalse(sightings[0].is_a_stranger(0.1))

    def test_enrolling_makes_the_face_recognised(self):
        known = base_embedding()
        perception = self.build(6, known)

        sightings = self.run_polls(perception, 3)
        perception.enroll("Pat", sightings[0], now=0.0)

        sightings = self.run_polls(perception, 3)

        self.assertEqual(sightings[0].name, "Pat")

    def test_seeing_a_known_person_records_the_sighting(self):
        known = base_embedding()
        perception = self.build(6, known)

        sightings = self.run_polls(perception, 1)
        perception.enroll("Pat", sightings[0], now=0.0)

        self.run_polls(perception, 5)

        self.assertGreater(self.store.people()[0].sighting_count, 1)


if __name__ == "__main__":
    unittest.main()
