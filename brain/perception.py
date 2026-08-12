"""Who is in the room, updated continuously and cheaply.

Detection, embedding and matching all run here. None of it involves a
language model, which is what makes it affordable to leave running.
"""

import time
from dataclasses import dataclass

from people import Match, PeopleStore
from recognizer import FaceRecognizer
from vision import Detection, YuNetFaceDetector


# A face has to be seen this many polls running before it earns a record.
# A single frame is usually a glitch or someone walking past.
FRAMES_BEFORE_ENROLLING = 5

# ...and it has to have moved. A photograph on the wall is a perfect,
# permanently detected face that never shifts by a pixel.
MIN_MOVEMENT_PIXELS = 6.0

# Only ask a name once someone is actually engaged, not on first sight.
SECONDS_BEFORE_ASKING_NAME = 4.0


@dataclass
class Sighting:
    detection: Detection
    match: Match | None
    first_seen_at: float
    frames_seen: int
    travelled: float

    @property
    def person_id(self) -> int | None:
        return None if self.match is None else self.match.person.id

    @property
    def name(self) -> str | None:
        return None if self.match is None else self.match.person.name

    @property
    def looks_alive(self) -> bool:
        return (
            self.frames_seen >= FRAMES_BEFORE_ENROLLING
            and self.travelled >= MIN_MOVEMENT_PIXELS
        )

    def should_ask_name(self, now: float) -> bool:
        return (
            self.match is not None
            and self.name is None
            and now - self.first_seen_at >= SECONDS_BEFORE_ASKING_NAME
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

        detections = self.detector.detect(frame)
        sightings = []

        for detection in detections:
            previous = self._nearest_tracked(detection)
            embedding = self.recognizer.embed(frame, detection)
            match = self.store.match(embedding)

            sighting = self._track(previous, detection, match, now)

            # Only commit to the database once it looks like a real, moving
            # person rather than a glitch or a picture on the wall.
            if sighting.looks_alive:
                if match is None:
                    person = self.store.create_person(embedding, now=now)
                    sighting.match = Match(person, 1.0)
                else:
                    self.store.record_sighting(
                        match.person.id,
                        embedding,
                        similarity=match.similarity,
                        now=now,
                    )

            sightings.append(sighting)

        self._tracked = sightings
        return sightings

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

    def _track(
        self,
        previous: Sighting | None,
        detection: Detection,
        match: Match | None,
        now: float,
    ) -> Sighting:
        if previous is None:
            return Sighting(
                detection=detection,
                match=match,
                first_seen_at=now,
                frames_seen=1,
                travelled=0.0,
            )

        px, py = previous.detection.box.center
        x, y = detection.box.center
        moved = ((px - x) ** 2 + (py - y) ** 2) ** 0.5

        return Sighting(
            detection=detection,
            match=match,
            first_seen_at=previous.first_seen_at,
            frames_seen=previous.frames_seen + 1,
            travelled=previous.travelled + moved,
        )
