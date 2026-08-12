"""Who Humalien has met, and what it knows about them.

Identity is an embedding problem, not a language problem. Faces become unit
vectors, and recognition is a dot product against everyone seen before. The
small language model never touches this path.
"""

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np


# Cosine similarity above which two faces are the same person. SFace's own
# documented operating point is 0.363; a little stricter suits a robot that
# would rather stay quiet than use the wrong name.
MATCH_THRESHOLD = 0.40

# Confident enough to say the name out loud, unprompted.
GREET_THRESHOLD = 0.50

# Below this, a face is unlike anyone we know and deserves its own record.
# Between here and MATCH_THRESHOLD is the ambiguous band: too different to
# call a match, too similar to be confident it is somebody new. Measured
# separation on real faces was ~0.28 between two different people and ~0.38
# for one person at an awkward angle, so the uncertainty sits in between.
CREATE_BELOW = 0.30

# A new view of a known face is only worth storing if it differs from what we
# already have. Near-duplicates add storage without adding robustness.
NOVEL_BELOW = 0.75
MAX_FACES_PER_PERSON = 12

SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    id             INTEGER PRIMARY KEY,
    name           TEXT,
    name_source    TEXT,
    first_seen_at  REAL NOT NULL,
    last_seen_at   REAL NOT NULL,
    sighting_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS faces (
    id        INTEGER PRIMARY KEY,
    person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    embedding BLOB NOT NULL,
    added_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS facts (
    id         INTEGER PRIMARY KEY,
    person_id  INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    text       TEXT NOT NULL,
    source     TEXT,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS faces_by_person ON faces(person_id);
CREATE INDEX IF NOT EXISTS facts_by_person ON facts(person_id);
"""


def normalize(embedding) -> np.ndarray:
    """Scale to unit length so cosine similarity is a plain dot product."""

    vector = np.asarray(embedding, dtype=np.float32).flatten()
    magnitude = float(np.linalg.norm(vector))

    if magnitude == 0:
        raise ValueError("Cannot normalize a zero embedding")

    return vector / magnitude


@dataclass(frozen=True)
class Person:
    id: int
    name: str | None
    sighting_count: int
    last_seen_at: float

    @property
    def is_known(self) -> bool:
        return self.name is not None


@dataclass(frozen=True)
class Match:
    person: Person
    similarity: float

    @property
    def confident_enough_to_greet(self) -> bool:
        return self.person.is_known and self.similarity >= GREET_THRESHOLD


class PeopleStore:
    def __init__(self, path: str | Path):
        self.path = str(path)

        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row

        # A robot head gets unplugged mid-write. WAL keeps that from
        # corrupting the database.
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA)
        self.connection.commit()

        self._cache: tuple[np.ndarray, list[int]] | None = None

    def close(self) -> None:
        self.connection.close()

    # -- reading ---------------------------------------------------------

    def _embeddings(self) -> tuple[np.ndarray, list[int]]:
        """All stored faces as one matrix, cached until faces change.

        At household scale this is a few dozen rows, so brute force beats
        any index. No vector database required.
        """

        if self._cache is not None:
            return self._cache

        rows = self.connection.execute(
            "SELECT person_id, embedding FROM faces"
        ).fetchall()

        if not rows:
            matrix = np.zeros((0, 0), dtype=np.float32)
            owners: list[int] = []
        else:
            matrix = np.stack(
                [np.frombuffer(row["embedding"], dtype=np.float32) for row in rows]
            )
            owners = [row["person_id"] for row in rows]

        self._cache = (matrix, owners)
        return self._cache

    def person(self, person_id: int) -> Person | None:
        row = self.connection.execute(
            "SELECT id, name, sighting_count, last_seen_at"
            " FROM people WHERE id = ?",
            (person_id,),
        ).fetchone()

        return None if row is None else Person(**dict(row))

    def people(self) -> list[Person]:
        rows = self.connection.execute(
            "SELECT id, name, sighting_count, last_seen_at"
            " FROM people ORDER BY last_seen_at DESC"
        ).fetchall()

        return [Person(**dict(row)) for row in rows]

    def facts(self, person_id: int) -> list[str]:
        rows = self.connection.execute(
            "SELECT text FROM facts WHERE person_id = ? ORDER BY created_at",
            (person_id,),
        ).fetchall()

        return [row["text"] for row in rows]

    def rank(self, embedding) -> list[tuple[Person, float]]:
        """Every known person, scored against this face, best first.

        `match` only reports the winner, which hides the number that
        actually matters: the gap between first and second place. A
        confident 0.7 with runner-up 0.6 is far shakier than 0.5 with
        runner-up 0.1.
        """

        matrix, owners = self._embeddings()

        if len(owners) == 0:
            return []

        similarities = matrix @ normalize(embedding)

        best: dict[int, float] = {}

        for person_id, similarity in zip(owners, similarities):
            score = float(similarity)

            if score > best.get(person_id, -1.0):
                best[person_id] = score

        ranked = [
            (self.person(person_id), score)
            for person_id, score in best.items()
        ]

        ranked = [(person, score) for person, score in ranked if person]
        ranked.sort(key=lambda pair: pair[1], reverse=True)

        return ranked

    def best_similarity(self, embedding) -> float:
        """How much this face resembles the closest thing we have seen.

        Reported even when it is too low to count as a match, because
        "resembles nobody at all" and "nearly matched someone" need very
        different handling.
        """

        matrix, owners = self._embeddings()

        if len(owners) == 0:
            return 0.0

        return float(np.max(matrix @ normalize(embedding)))

    def match(self, embedding) -> Match | None:
        """Find who this face belongs to, named or not.

        Matching against unnamed people as well as named ones is what stops
        one stranger becoming four hundred separate records.
        """

        matrix, owners = self._embeddings()

        if len(owners) == 0:
            return None

        similarities = matrix @ normalize(embedding)
        best = int(np.argmax(similarities))
        similarity = float(similarities[best])

        if similarity < MATCH_THRESHOLD:
            return None

        person = self.person(owners[best])

        return None if person is None else Match(person, similarity)

    # -- writing ---------------------------------------------------------

    def create_person(self, embedding, *, now: float | None = None) -> Person:
        now = time.time() if now is None else now

        cursor = self.connection.execute(
            "INSERT INTO people"
            " (name, name_source, first_seen_at, last_seen_at, sighting_count)"
            " VALUES (NULL, NULL, ?, ?, 1)",
            (now, now),
        )
        person_id = int(cursor.lastrowid)

        self._add_face(person_id, embedding, now)
        self.connection.commit()

        return Person(person_id, None, 1, now)

    def record_sighting(
        self,
        person_id: int,
        embedding=None,
        *,
        similarity: float | None = None,
        now: float | None = None,
    ) -> None:
        now = time.time() if now is None else now

        self.connection.execute(
            "UPDATE people"
            " SET last_seen_at = ?, sighting_count = sighting_count + 1"
            " WHERE id = ?",
            (now, person_id),
        )

        # Store a genuinely different view, not the same angle again.
        if embedding is not None and (
            similarity is None or similarity < NOVEL_BELOW
        ):
            stored = self.connection.execute(
                "SELECT COUNT(*) AS n FROM faces WHERE person_id = ?",
                (person_id,),
            ).fetchone()["n"]

            if stored < MAX_FACES_PER_PERSON:
                self._add_face(person_id, embedding, now)

        self.connection.commit()

    def _add_face(self, person_id: int, embedding, added_at: float) -> None:
        self.connection.execute(
            "INSERT INTO faces (person_id, embedding, added_at) VALUES (?, ?, ?)",
            (person_id, normalize(embedding).tobytes(), added_at),
        )
        self._cache = None

    def name_person(
        self,
        person_id: int,
        name: str,
        *,
        source: str = "asked",
    ) -> None:
        """Promote an unidentified record. Everything already attached stays.

        This is why there is no separate table for unknowns: learning a name
        is an UPDATE, not a migration.
        """

        self.connection.execute(
            "UPDATE people SET name = ?, name_source = ? WHERE id = ?",
            (name, source, person_id),
        )
        self.connection.commit()

    def add_fact(
        self,
        person_id: int,
        text: str,
        *,
        source: str = "conversation",
        now: float | None = None,
    ) -> None:
        now = time.time() if now is None else now

        self.connection.execute(
            "INSERT INTO facts (person_id, text, source, created_at)"
            " VALUES (?, ?, ?, ?)",
            (person_id, text, source, now),
        )
        self.connection.commit()

    def merge(self, keep_id: int, drop_id: int) -> None:
        """Fold one record into another after a mistaken split.

        Clustering is deliberately strict, which means it splits one person
        into several records rather than merging two people into one. This is
        the repair for that, and it is the reason strict is the safe default.
        """

        if keep_id == drop_id:
            raise ValueError("Cannot merge a person into themselves")

        for table in ("faces", "facts"):
            self.connection.execute(
                f"UPDATE {table} SET person_id = ? WHERE person_id = ?",
                (keep_id, drop_id),
            )

        dropped = self.connection.execute(
            "SELECT sighting_count, first_seen_at, last_seen_at"
            " FROM people WHERE id = ?",
            (drop_id,),
        ).fetchone()

        if dropped is not None:
            self.connection.execute(
                "UPDATE people SET"
                " sighting_count = sighting_count + ?,"
                " first_seen_at = MIN(first_seen_at, ?),"
                " last_seen_at = MAX(last_seen_at, ?)"
                " WHERE id = ?",
                (
                    dropped["sighting_count"],
                    dropped["first_seen_at"],
                    dropped["last_seen_at"],
                    keep_id,
                ),
            )

        self.connection.execute("DELETE FROM people WHERE id = ?", (drop_id,))
        self.connection.commit()
        self._cache = None

    def consolidate(self, *, threshold: float = MATCH_THRESHOLD) -> int:
        """Fold unnamed records into named people they now match.

        A creation-time threshold cannot prevent duplicates on its own,
        because a person's stored views accumulate. A face that genuinely
        resembled nobody when it was first seen can match confidently once
        the same person has been seen from that angle a few more times.

        Left alone those orphans actively steal sightings, since matching
        takes the best face across everyone. Re-checking them is what keeps
        one person from slowly fragmenting into several.

        Only unnamed records are folded, and only into named ones. Merging
        two named people is destructive and stays a human decision.
        """

        faces: dict[int, list[np.ndarray]] = {}

        for row in self.connection.execute(
            "SELECT person_id, embedding FROM faces"
        ):
            faces.setdefault(row["person_id"], []).append(
                np.frombuffer(row["embedding"], dtype=np.float32)
            )

        people = self.people()
        named = [person for person in people if person.name]
        unnamed = [person for person in people if not person.name]

        merged = 0

        for orphan in unnamed:
            mine = faces.get(orphan.id)

            if not mine:
                continue

            mine = np.stack(mine)
            best_person, best_score = None, threshold

            for person in named:
                theirs = faces.get(person.id)

                if not theirs:
                    continue

                score = float(np.max(mine @ np.stack(theirs).T))

                if score >= best_score:
                    best_person, best_score = person, score

            if best_person is not None:
                self.merge(best_person.id, orphan.id)
                merged += 1

        return merged

    def forget_unnamed(self) -> int:
        """Delete every unidentified record, whatever its history.

        Faces and facts cascade with them. Named people are untouched.
        Anyone deleted who turns up again simply gets enrolled afresh.
        """

        cursor = self.connection.execute("DELETE FROM people WHERE name IS NULL")
        self.connection.commit()
        self._cache = None

        return cursor.rowcount

    def prune_unnamed(
        self,
        *,
        min_sightings: int = 3,
        older_than_seconds: float = 7 * 24 * 3600,
        now: float | None = None,
    ) -> int:
        """Forget strangers, never acquaintances.

        A camera in a room will enroll the mailman, a delivery driver, and
        faces on the television. Named people are never touched.
        """

        now = time.time() if now is None else now

        cursor = self.connection.execute(
            "DELETE FROM people"
            " WHERE name IS NULL"
            " AND sighting_count < ?"
            " AND last_seen_at < ?",
            (min_sightings, now - older_than_seconds),
        )
        self.connection.commit()
        self._cache = None

        return cursor.rowcount
