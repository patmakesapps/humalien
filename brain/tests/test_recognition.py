"""The two ways Humalien got somebody's name wrong.

It called people by the wrong name and greeted somebody who was not in the
room, and it stopped being able to recognise people it had seen thousands
of times. Both are here because both were invisible to the thresholds.
"""

import unittest

import numpy as np

from people import (
    GREET_THRESHOLD,
    MATCH_THRESHOLD,
    MAX_FACES_PER_PERSON,
    Match,
    PeopleStore,
    normalize,
)
from perception import Sighting


def embedding(seed: int) -> np.ndarray:
    return normalize(np.random.default_rng(seed).normal(size=128).astype(np.float32))


def nudged(base: np.ndarray, seed: int, amount: float) -> np.ndarray:
    """A face that looks `amount` different from `base`."""

    drift = np.random.default_rng(seed).normal(size=base.shape).astype(np.float32)

    return normalize(base + amount * drift)


def sighting(match) -> Sighting:
    return Sighting(
        detection=None,
        embedding=embedding(0),
        match=match,
        first_seen_at=0.0,
        frames_seen=1,
    )


class ConfidenceTests(unittest.TestCase):
    """A match is two decisions: is that them, and is it safe to say so."""

    def setUp(self):
        self.store = PeopleStore(":memory:")
        self.person = self.store.enroll("Pat", embedding(1))

    def tearDown(self):
        self.store.close()

    def test_a_sure_match_can_be_named(self):
        self.assertTrue(sighting(Match(self.person, 0.9)).is_confident)

    def test_a_weak_match_is_a_face_not_a_name(self):
        # Above MATCH_THRESHOLD, below GREET_THRESHOLD - the band that was
        # being treated as certainty and produced the wrong name out loud.
        halfway = (MATCH_THRESHOLD + GREET_THRESHOLD) / 2

        self.assertTrue(halfway > MATCH_THRESHOLD)
        self.assertFalse(sighting(Match(self.person, halfway)).is_confident)

    def test_a_stranger_is_never_confident(self):
        self.assertFalse(sighting(None).is_confident)

    def test_the_bar_for_saying_a_name_is_higher_than_for_matching(self):
        self.assertGreater(GREET_THRESHOLD, MATCH_THRESHOLD)


class LearningTests(unittest.TestCase):
    """A full gallery used to mean learning stopped, permanently.

    Every person in the live database sat at exactly MAX_FACES_PER_PERSON,
    which is what a hard stop looks like from the outside: a face frozen at
    however it looked months ago, slowly drifting out of recognition.
    """

    def setUp(self):
        self.store = PeopleStore(":memory:")

    def tearDown(self):
        self.store.close()

    def faces(self, person_id: int) -> int:
        return self.store.connection.execute(
            "SELECT COUNT(*) AS n FROM faces WHERE person_id = ?", (person_id,)
        ).fetchone()["n"]

    def fill(self):
        """A person whose gallery is full of assorted views."""

        base = embedding(2)
        person = self.store.enroll("Pat", base)

        for i in range(MAX_FACES_PER_PERSON * 2):
            if self.faces(person.id) >= MAX_FACES_PER_PERSON:
                break
            self.store.record_sighting(person.id, embedding=nudged(base, i, 0.9), similarity=0.5)

        return person, base

    def test_the_gallery_fills_up(self):
        person, _ = self.fill()

        self.assertEqual(self.faces(person.id), MAX_FACES_PER_PERSON)

    def test_a_full_gallery_still_takes_a_new_view(self):
        person, base = self.fill()

        self.store.record_sighting(person.id, embedding=nudged(base, 99, 0.9), similarity=0.5)

        self.assertEqual(self.faces(person.id), MAX_FACES_PER_PERSON)

    def test_the_new_view_is_the_one_that_is_kept(self):
        person, base = self.fill()
        fresh = nudged(base, 99, 0.9)

        self.store.record_sighting(person.id, embedding=fresh, similarity=0.5)

        matrix, owners = self.store._embeddings()
        mine = matrix[[i for i, owner in enumerate(owners) if owner == person.id]]

        self.assertAlmostEqual(float(np.max(mine @ fresh)), 1.0, places=4)

    def test_a_new_camera_does_not_get_locked_out(self):
        """The failure in the field, in miniature.

        A gallery full of views from one camera, then every new view coming
        from a different one. The old cluster has to give way, or the person
        is never recognisable again.
        """

        person, base = self.fill()
        moved = normalize(embedding(7))

        for i in range(MAX_FACES_PER_PERSON):
            self.store.record_sighting(person.id, embedding=nudged(moved, i, 0.2), similarity=0.5)

        matrix, owners = self.store._embeddings()
        mine = matrix[[i for i, owner in enumerate(owners) if owner == person.id]]

        # The new look is now well represented rather than shut out.
        self.assertGreater(float(np.max(mine @ moved)), GREET_THRESHOLD)

    def test_an_unusual_view_outlives_a_near_duplicate(self):
        # Eviction drops the most redundant view, not the oldest, so the one
        # odd angle is not thrown away to keep a fifth identical head-on.
        base = embedding(3)
        person = self.store.enroll("Pat", base)
        odd = embedding(4)

        self.store.record_sighting(person.id, embedding=odd, similarity=0.5)

        while self.faces(person.id) < MAX_FACES_PER_PERSON:
            self.store.record_sighting(
                person.id,
                embedding=nudged(base, self.faces(person.id), 0.05),
                similarity=0.5,
            )

        self.store.record_sighting(person.id, embedding=embedding(5), similarity=0.5)

        matrix, owners = self.store._embeddings()
        mine = matrix[[i for i, owner in enumerate(owners) if owner == person.id]]

        self.assertAlmostEqual(float(np.max(mine @ odd)), 1.0, places=4)

    def test_a_single_stored_face_is_never_evicted_away(self):
        person = self.store.enroll("Pat", embedding(6))

        self.store._evict_most_redundant(person.id)

        self.assertEqual(self.faces(person.id), 1)


if __name__ == "__main__":
    unittest.main()
