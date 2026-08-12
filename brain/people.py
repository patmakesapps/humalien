"""Who Humalien knows, and what it knows about them.

Only confirmed people are stored. A face nobody has introduced leaves no
trace, which is what keeps this simple: there are no anonymous records to
accumulate, clean up, or confuse with real people.

Identity is an embedding problem, not a language problem. Faces become unit
vectors and recognition is a dot product. No language model is involved.
"""

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np


# Cosine similarity above which a face is someone we know. SFace's own
# documented operating point is 0.363; a little stricter suits a robot that
# would rather stay quiet than use the wrong name.
MATCH_THRESHOLD = 0.40

# Confident enough to say the name out loud, unprompted.
GREET_THRESHOLD = 0.50

# A new view of a known face is only worth storing if it differs from what
# we already have. Near-duplicates add storage without adding robustness.
NOVEL_BELOW = 0.75
MAX_FACES_PER_PERSON = 12

SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    id             INTEGER PRIMARY KEY,
    name           TEXT NOT NULL,
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
    name: str
    sighting_count: int
    last_seen_at: float


@dataclass(frozen=True)
class Match:
    person: Person
    similarity: float

    @property
    def confident_enough_to_greet(self) -> bool:
        return self.similarity >= GREET_THRESHOLD


class PeopleStore:
    def __init__(self, path: str | Path):
        self.path = str(path)

        # Recognition runs on a worker thread so it does not stall the
        # conversation. Only ever one caller at a time, so sharing the
        # connection across threads is safe.
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
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

    def match(self, embedding) -> Match | None:
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

    def rank(self, embedding) -> list[tuple[Person, float]]:
        """Everyone scored against this face, best first.

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
            (self.person(person_id), score) for person_id, score in best.items()
        ]
        ranked = [(person, score) for person, score in ranked if person]
        ranked.sort(key=lambda pair: pair[1], reverse=True)

        return ranked

    # -- writing ---------------------------------------------------------

    def enroll(self, name: str, embedding, *, now: float | None = None) -> Person:
        """Record someone who has introduced themselves.

        This is the only way a person enters the database. Detecting a face
        is not enough; somebody has to say who it belongs to.
        """

        if not name.strip():
            raise ValueError("A person needs a name")

        now = time.time() if now is None else now

        cursor = self.connection.execute(
            "INSERT INTO people"
            " (name, first_seen_at, last_seen_at, sighting_count)"
            " VALUES (?, ?, ?, 1)",
            (name.strip(), now, now),
        )
        person_id = int(cursor.lastrowid)

        self._add_face(person_id, embedding, now)
        self.connection.commit()

        return Person(person_id, name.strip(), 1, now)

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

        # Store a genuinely different view, not the same angle again. Safe
        # because we only ever add to a person we have confidently matched.
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

    def rename(self, person_id: int, name: str) -> None:
        if not name.strip():
            raise ValueError("A person needs a name")

        self.connection.execute(
            "UPDATE people SET name = ? WHERE id = ?",
            (name.strip(), person_id),
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

    def forget(self, person_id: int) -> None:
        """Remove someone entirely. Faces and facts go with them."""

        self.connection.execute("DELETE FROM people WHERE id = ?", (person_id,))
        self.connection.commit()
        self._cache = None

    def merge(self, keep_id: int, drop_id: int) -> None:
        """Fold one record into another, if somebody was enrolled twice."""

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
