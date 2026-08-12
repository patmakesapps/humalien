"""Who is in the room, updated continuously and cheaply.

Detection, embedding and matching all run here. None of it involves a
language model, which is what makes it affordable to leave running.

Nothing is written to the database except sightings of people who are
already known. Enrolling somebody is a deliberate act, driven by the
conversation, not a side effect of being looked at.
"""

import time
from dataclasses import dataclass

import numpy as np

from people import Match, PeopleStore
from recognizer import FaceRecognizer
from vision import Detection, YuNetFaceDetector


# How long an unrecognised face has to stick around before it is worth
# interrupting to ask who they are. Somebody crossing the room should not
# trigger an introduction.
SECONDS_BEFORE_INTRODUCING = 4.0


@dataclass
class Sighting:
    detection: Detection
    embedding: np.ndarray
    match: Match | None
    first_seen_at: float
    frames_seen: int

    @property
    def person(self):
        return None if self.match is None else self.match.person

    @property
    def name(self) -> str | None:
        return None if self.match is None else self.match.person.name

    def is_a_stranger(self, now: float) -> bool:
        """An unknown face that has settled in and is worth introducing to."""

        return (
            self.match is None
            and now - self.first_seen_at >= SECONDS_BEFORE_INTRODUCING
        )


class Perception:
    def __init__(
        self,
        store: PeopleStore,
        *,
        detector: YuNetFaceDetector | None = None,
        recognizer: FaceRecognizer | None = None,
    ) -> None:
        self.store = store
        self.detector = detector or YuNetFaceDetector()
        self.recognizer = recognizer or FaceRecognizer()

        self._tracked: list[Sighting] = []

    def poll(self, frame, *, now: float | None = None) -> list[Sighting]:
        """Look at one frame and return who is currently visible."""

        now = time.time() if now is None else now

        sightings = []

        for detection in self.detector.detect(frame):
            embedding = self.recognizer.embed(frame, detection)
            match = self.store.match(embedding)

            previous = self._nearest_tracked(detection)

            sightings.append(
                Sighting(
                    detection=detection,
                    embedding=embedding,
                    match=match,
                    first_seen_at=now if previous is None else previous.first_seen_at,
                    frames_seen=1 if previous is None else previous.frames_seen + 1,
                )
            )

            # The only write: a person we already know was seen again.
            if match is not None:
                self.store.record_sighting(
                    match.person.id,
                    embedding,
                    similarity=match.similarity,
                    now=now,
                )

        self._tracked = sightings
        return sightings

    def enroll(self, name: str, sighting: Sighting, *, now: float | None = None):
        """Introduce somebody. The only way a person enters the database."""

        return self.store.enroll(name, sighting.embedding, now=now)

    def _nearest_tracked(self, detection: Detection) -> Sighting | None:
        """Follow a face between frames by position, before identity is known."""

        if not self._tracked:
            return None

        x, y = detection.box.center

        def distance(sighting: Sighting) -> float:
            px, py = sighting.detection.box.center
            return ((px - x) ** 2 + (py - y) ** 2) ** 0.5

        nearest = min(self._tracked, key=distance)
        limit = max(detection.box.width, detection.box.height)

        return nearest if distance(nearest) <= limit else None
