"""The camera, running alongside the conversation.

Capture and recognition are blocking work, so they live on a worker thread
and publish their latest result here. The conversation reads it; it never
waits for it.
"""

import asyncio
import time

import cv2

from people import Person
from perception import Perception, Sighting


WINDOW_NAME = "Humalien eyes"

KNOWN_COLOR = (80, 220, 80)
STRANGER_COLOR = (0, 180, 255)


def log(message: str) -> None:
    print(f"[EYES] {message}", flush=True)


class Eyes:
    def __init__(
        self,
        perception: Perception,
        *,
        camera: int | str = 0,
        interval: float = 0.25,
        show_video: bool = False,
    ) -> None:
        self.perception = perception
        self.camera = camera
        self.interval = interval
        self.show_video = show_video

        self.frame = None
        self.sightings: list[Sighting] = []

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

    async def run(self) -> None:
        capture = await asyncio.to_thread(cv2.VideoCapture, self.camera)

        if not capture.isOpened():
            # Losing the eyes must not take the conversation down with them.
            log(f"Could not open camera {self.camera!r} - Humalien is blind")
            await asyncio.Event().wait()

        log(f"Camera {self.camera!r} online")

        try:
            while True:
                ok, frame = await asyncio.to_thread(capture.read)

                if not ok:
                    log("Camera stopped returning frames - Humalien is blind")
                    await asyncio.Event().wait()

                self.frame = frame

                # Recognition is CPU work and does not belong on the event
                # loop, where it would stall audio.
                self.sightings = await asyncio.to_thread(
                    self.perception.poll,
                    frame,
                )

                if self.show_video:
                    self.render(frame)

                await asyncio.sleep(self.interval)

        finally:
            capture.release()

            if self.show_video:
                cv2.destroyWindow(WINDOW_NAME)

            log("Camera released")
