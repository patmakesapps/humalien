import unittest

import numpy as np

from people import MATCH_THRESHOLD, PeopleStore, normalize


def embedding(seed: int, *, noise: float = 0.0) -> np.ndarray:
    """A deterministic fake face vector, optionally jittered."""

    generator = np.random.default_rng(seed)
    vector = generator.normal(size=128).astype(np.float32)

    if noise:
        vector = vector + generator.normal(size=128).astype(np.float32) * noise

    return normalize(vector)


class PeopleStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = PeopleStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_no_match_in_an_empty_room(self):
        self.assertIsNone(self.store.match(embedding(1)))

    def test_recognizes_someone_it_has_met(self):
        person = self.store.enroll("Pat", embedding(1))

        match = self.store.match(embedding(1, noise=0.05))

        self.assertIsNotNone(match)
        self.assertEqual(match.person.id, person.id)
        self.assertEqual(match.person.name, "Pat")
        self.assertGreater(match.similarity, MATCH_THRESHOLD)

    def test_does_not_confuse_two_people(self):
        self.store.enroll("Pat", embedding(1))

        self.assertIsNone(self.store.match(embedding(2)))

    def test_enrolling_requires_a_name(self):
        with self.assertRaises(ValueError):
            self.store.enroll("   ", embedding(3))

    def test_facts_belong_to_the_person(self):
        person = self.store.enroll("Pat", embedding(4))
        self.store.add_fact(person.id, "builds robots")

        self.assertEqual(self.store.facts(person.id), ["builds robots"])

    def test_a_second_view_of_a_known_face_is_stored(self):
        person = self.store.enroll("Pat", embedding(5))

        self.store.record_sighting(person.id, embedding(5, noise=0.5), similarity=0.5)

        stored = self.store.connection.execute(
            "SELECT COUNT(*) FROM faces WHERE person_id = ?", (person.id,)
        ).fetchone()[0]

        self.assertEqual(stored, 2)

    def test_near_duplicate_views_are_not_stored(self):
        person = self.store.enroll("Pat", embedding(6))

        self.store.record_sighting(person.id, embedding(6), similarity=0.99)

        stored = self.store.connection.execute(
            "SELECT COUNT(*) FROM faces WHERE person_id = ?", (person.id,)
        ).fetchone()[0]

        self.assertEqual(stored, 1)

    def test_sightings_accumulate(self):
        person = self.store.enroll("Pat", embedding(7))

        for _ in range(4):
            self.store.record_sighting(person.id)

        self.assertEqual(self.store.person(person.id).sighting_count, 5)

    def test_rank_orders_everyone_and_shows_the_margin(self):
        me = self.store.enroll("Pat", embedding(8))
        someone_else = self.store.enroll("Derrick", embedding(9))

        ranked = self.store.rank(embedding(8, noise=0.05))

        self.assertEqual(
            [person.id for person, _ in ranked], [me.id, someone_else.id]
        )

        # The gap is the number that says whether a match is trustworthy.
        self.assertGreater(ranked[0][1] - ranked[1][1], 0.3)

    def test_rank_reports_one_score_per_person(self):
        person = self.store.enroll("Pat", embedding(10))
        self.store.record_sighting(person.id, embedding(10, noise=0.5), similarity=0.5)

        self.assertEqual(len(self.store.rank(embedding(10))), 1)

    def test_forget_removes_the_person_and_their_face(self):
        person = self.store.enroll("Pat", embedding(11))
        self.store.add_fact(person.id, "builds robots")

        self.store.forget(person.id)

        self.assertEqual(self.store.people(), [])
        self.assertIsNone(self.store.match(embedding(11)))

    def test_merge_folds_a_duplicate_enrollment(self):
        keep = self.store.enroll("Pat", embedding(12))
        duplicate = self.store.enroll("Patrick", embedding(13))
        self.store.add_fact(duplicate.id, "met at the door")

        self.store.merge(keep.id, duplicate.id)

        self.assertIsNone(self.store.person(duplicate.id))
        self.assertEqual(self.store.facts(keep.id), ["met at the door"])
        self.assertEqual(self.store.match(embedding(13)).person.id, keep.id)

    def test_merge_rejects_a_person_into_themselves(self):
        person = self.store.enroll("Pat", embedding(14))

        with self.assertRaises(ValueError):
            self.store.merge(person.id, person.id)

    def test_rename(self):
        person = self.store.enroll("Pat", embedding(15))

        self.store.rename(person.id, "Patrick")

        self.assertEqual(self.store.person(person.id).name, "Patrick")

    def test_normalize_rejects_a_zero_vector(self):
        with self.assertRaises(ValueError):
            normalize(np.zeros(128, dtype=np.float32))


if __name__ == "__main__":
    unittest.main()
