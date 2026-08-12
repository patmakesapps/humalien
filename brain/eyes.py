"""The camera, running alongside the conversation.

Capture and recognition are blocking work, so they live on a worker thread
and publish their latest result here. The conversation reads it; it never
waits for it.

Recent frames are kept so a question can be answered with what was in front
of the camera *when it was asked*, rather than seconds later when the tool
call finally arrives.
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass

import cv2
import numpy as np

from describe import downscale
from people import Person
from perception import Perception, Sighting


WINDOW_NAME = "Humalien eyes"

KNOWN_COLOR = (80, 220, 80)
STRANGER_COLOR = (0, 180, 255)

# Capture faster than recognition. Recognition is happy at 4 Hz, but picking
# a sharp frame out of a moving hand needs candidates to choose from.
CAPTURE_INTERVAL = 0.08
RECOGNISE_INTERVAL = 0.25

# How much recent history to keep. Long enough to cover a spoken question
# and the pause before the tool call lands.
REMEMBER_SECONDS = 5.0


def sharpness(frame) -> float:
    """How in-focus a frame is. Motion blur scores low.

    Variance of the Laplacian - the standard cheap blur metric. About a
    millisecond on a downscaled frame.
    """

    grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    return float(cv2.Laplacian(grey, cv2.CV_64F).var())


@dataclass(frozen=True)
class Snapshot:
    at: float
    frame: np.ndarray
    sharpness: float


def log(message: str) -> None:
    print(f"[EYES] {message}", flush=True)


class Eyes:
    def __init__(
        self,
        perception: Perception,
        *,
        camera: int | str = 0,
        interval: float = RECOGNISE_INTERVAL,
        show_video: bool = False,
        remember_seconds: float = REMEMBER_SECONDS,
    ) -> None:
        self.perception = perception
        self.camera = camera
        self.interval = interval
        self.show_video = show_video

        self.frame = None
        self.sightings: list[Sighting] = []

        # Stored already downscaled, which is what a vision model gets
        # anyway, so nothing is lost and the buffer stays affordable.
        self.recent: deque[Snapshot] = deque(
            maxlen=max(1, int(remember_seconds / CAPTURE_INTERVAL))
        )

    @property
    def known(self) -> list[Person]:
        """Everyone currently visible that Humalien has met."""

        return [s.match.person for s in self.sightings if s.match is not None]

    def largest_stranger(self, *, now: float | None = None) -> Sighting | None:
        """An unrecognised face that has stayed long enough to be worth meeting."""

        now = time.time() if now is None else now

        strangers = [s for s in self.sightings if s.is_a_stranger(now)]

        if not strangers:
            return None

        return max(strangers, key=lambda s: s.detection.area)

    def clearest_frame(
        self,
        *,
        since: float | None = None,
        until: float | None = None,
    ):
        """The sharpest frame from a moment, or the latest if there is none.

        Given the window somebody was speaking in, this returns what the
        camera saw while they were asking. Sharpest rather than nearest,
        because a hand held up mid-sentence is usually moving, and a blurred
        frame from the right moment answers nothing.
        """

        if not self.recent:
            return None

        candidates = [
            snapshot
            for snapshot in self.recent
            if (since is None or snapshot.at >= since)
            and (until is None or snapshot.at <= until)
        ]

        if not candidates:
            return self.recent[-1].frame

        return max(candidates, key=lambda snapshot: snapshot.sharpness).frame

    def render(self, frame) -> None:
        """A debug view of what Humalien is looking at.

        Off by default. The robot has no screen, and drawing costs frames
        that recognition could be using.
        """

        display = frame.copy()

        for sighting in self.sightings:
            box = sighting.detection.box

            if sighting.match is None:
                label, color = "stranger", STRANGER_COLOR
            else:
                label = f"{sighting.name} ({sighting.match.similarity:.2f})"
                color = KNOWN_COLOR

            cv2.rectangle(
                display,
                (box.x, box.y),
                (box.x + box.width, box.y + box.height),
                color,
                2,
            )
            cv2.putText(
                display,
                label,
                (box.x, max(box.y - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
                cv2.LINE_AA,
            )

        cv2.imshow(WINDOW_NAME, display)
        cv2.waitKey(1)

    def _remember(self, frame, at: float) -> None:
        small = downscale(frame)

        self.recent.append(Snapshot(at=at, frame=small, sharpness=sharpness(small)))

    async def run(self) -> None:
        capture = await asyncio.to_thread(cv2.VideoCapture, self.camera)

        if not capture.isOpened():
            # Losing the eyes must not take the conversation down with them.
            log(f"Could not open camera {self.camera!r} - Humalien is blind")
            await asyncio.Event().wait()

        log(f"Camera {self.camera!r} online")

        recognised_at = 0.0

        try:
            while True:
                ok, frame = await asyncio.to_thread(capture.read)

                if not ok:
                    log("Camera stopped returning frames - Humalien is blind")
                    await asyncio.Event().wait()

                now = time.monotonic()
                self.frame = frame

                await asyncio.to_thread(self._remember, frame, now)

                # Recognition is CPU work and does not belong on the event
                # loop, where it would stall audio. It also does not need to
                # run on every captured frame.
                if now - recognised_at >= self.interval:
                    recognised_at = now
                    self.sightings = await asyncio.to_thread(
                        self.perception.poll,
                        frame,
                    )

                if self.show_video:
                    self.render(frame)

                await asyncio.sleep(CAPTURE_INTERVAL)

        finally:
            capture.release()

            if self.show_video:
                cv2.destroyWindow(WINDOW_NAME)

            log("Camera released")
