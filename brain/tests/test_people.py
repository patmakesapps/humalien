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

    def test_recognizes_a_face_it_has_seen(self):
        person = self.store.create_person(embedding(1))

        match = self.store.match(embedding(1, noise=0.05))

        self.assertIsNotNone(match)
        self.assertEqual(match.person.id, person.id)
        self.assertGreater(match.similarity, MATCH_THRESHOLD)

    def test_does_not_confuse_two_people(self):
        self.store.create_person(embedding(1))

        self.assertIsNone(self.store.match(embedding(2)))

    def test_matches_unnamed_people_too(self):
        # Without this, one stranger seen on five days becomes five records.
        person = self.store.create_person(embedding(3))

        match = self.store.match(embedding(3, noise=0.05))

        self.assertEqual(match.person.id, person.id)
        self.assertIsNone(match.person.name)

    def test_naming_keeps_everything_already_attached(self):
        # The reason unknowns are not a separate table: promotion is an
        # UPDATE, so faces and facts carry over for free.
        person = self.store.create_person(embedding(4))
        self.store.add_fact(person.id, "likes robots")

        self.store.name_person(person.id, "Patrick")

        named = self.store.person(person.id)
        self.assertEqual(named.name, "Patrick")
        self.assertEqual(self.store.facts(person.id), ["likes robots"])
        self.assertEqual(self.store.match(embedding(4)).person.name, "Patrick")

    def test_merge_folds_one_record_into_another(self):
        keep = self.store.create_person(embedding(5))
        drop = self.store.create_person(embedding(6))
        self.store.add_fact(drop.id, "met at the door")

        self.store.merge(keep.id, drop.id)

        self.assertIsNone(self.store.person(drop.id))
        self.assertEqual(self.store.facts(keep.id), ["met at the door"])

        # Both faces now resolve to the surviving record.
        self.assertEqual(self.store.match(embedding(5)).person.id, keep.id)
        self.assertEqual(self.store.match(embedding(6)).person.id, keep.id)

    def test_merge_rejects_a_person_into_themselves(self):
        person = self.store.create_person(embedding(7))

        with self.assertRaises(ValueError):
            self.store.merge(person.id, person.id)

    def test_pruning_forgets_strangers_but_not_acquaintances(self):
        stranger = self.store.create_person(embedding(8), now=0.0)
        friend = self.store.create_person(embedding(9), now=0.0)
        self.store.name_person(friend.id, "Dana")

        removed = self.store.prune_unnamed(
            min_sightings=3,
            older_than_seconds=10.0,
            now=1_000.0,
        )

        self.assertEqual(removed, 1)
        self.assertIsNone(self.store.person(stranger.id))
        self.assertIsNotNone(self.store.person(friend.id))

    def test_pruning_keeps_a_stranger_seen_often(self):
        person = self.store.create_person(embedding(10), now=0.0)

        for _ in range(5):
            self.store.record_sighting(person.id, now=0.0)

        removed = self.store.prune_unnamed(
            min_sightings=3,
            older_than_seconds=10.0,
            now=1_000.0,
        )

        self.assertEqual(removed, 0)
        self.assertIsNotNone(self.store.person(person.id))

    def test_near_duplicate_views_are_not_stored(self):
        person = self.store.create_person(embedding(11))

        self.store.record_sighting(person.id, embedding(11), similarity=0.99)

        stored = self.store.connection.execute(
            "SELECT COUNT(*) FROM faces WHERE person_id = ?", (person.id,)
        ).fetchone()[0]

        self.assertEqual(stored, 1)

    def test_a_different_view_is_stored(self):
        person = self.store.create_person(embedding(12))

        self.store.record_sighting(person.id, embedding(12, noise=0.5), similarity=0.5)

        stored = self.store.connection.execute(
            "SELECT COUNT(*) FROM faces WHERE person_id = ?", (person.id,)
        ).fetchone()[0]

        self.assertEqual(stored, 2)

    def test_normalize_rejects_a_zero_vector(self):
        with self.assertRaises(ValueError):
            normalize(np.zeros(128, dtype=np.float32))


if __name__ == "__main__":
    unittest.main()
