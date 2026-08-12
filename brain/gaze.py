from dataclasses import dataclass
from math import exp


TRACKING = "tracking"
HOLDING = "holding"
RECENTERING = "recentering"
IDLE = "idle"


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


@dataclass(frozen=True)
class FaceBox:
    """A detected face in camera pixel coordinates."""

    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> tuple[float, float]:
        return (
            self.x + self.width / 2,
            self.y + self.height / 2,
        )

    @property
    def area(self) -> int:
        return self.width * self.height

    def normalized_center(
        self,
        frame_width: int,
        frame_height: int,
    ) -> tuple[float, float]:
        """Map the face center to camera coordinates in the range [-1, 1].

        X increases from left to right. Y increases from top to bottom. Servo
        direction, travel limits, and calibration deliberately live elsewhere.
        """
        if frame_width <= 0 or frame_height <= 0:
            raise ValueError("Frame dimensions must be positive")

        center_x, center_y = self.center

        normalized_x = (2 * center_x / frame_width) - 1
        normalized_y = (2 * center_y / frame_height) - 1

        return (
            _clamp(normalized_x, -1.0, 1.0),
            _clamp(normalized_y, -1.0, 1.0),
        )


def select_primary_face(faces: list[FaceBox]) -> FaceBox | None:
    """Select the most prominent face for Humalien to look at."""
    if not faces:
        return None

    return max(faces, key=lambda face: face.area)


@dataclass(frozen=True)
class GazeTarget:
    x: float
    y: float
    state: str


class GazeController:
    """Smooth detections and provide predictable behavior when a face is lost."""

    def __init__(
        self,
        *,
        smoothing_seconds: float = 0.12,
        hold_seconds: float = 0.35,
        recenter_seconds: float = 0.8,
    ) -> None:
        if smoothing_seconds <= 0:
            raise ValueError("smoothing_seconds must be positive")
        if hold_seconds < 0:
            raise ValueError("hold_seconds cannot be negative")
        if recenter_seconds <= 0:
            raise ValueError("recenter_seconds must be positive")

        self.smoothing_seconds = smoothing_seconds
        self.hold_seconds = hold_seconds
        self.recenter_seconds = recenter_seconds

        self._x = 0.0
        self._y = 0.0
        self._last_update: float | None = None
        self._last_seen: float | None = None

    def update(
        self,
        face: FaceBox | None,
        *,
        frame_width: int,
        frame_height: int,
        now: float,
    ) -> GazeTarget:
        if self._last_update is not None and now < self._last_update:
            raise ValueError("now must be monotonic")

        elapsed = (
            0.0
            if self._last_update is None
            else now - self._last_update
        )
        self._last_update = now

        if face is not None:
            measured_x, measured_y = face.normalized_center(
                frame_width,
                frame_height,
            )

            if self._last_seen is None:
                # Acquire the first face immediately. Smoothing is for jitter,
                # not for making initial eye contact feel sluggish.
                self._x = measured_x
                self._y = measured_y
            else:
                alpha = 1 - exp(-elapsed / self.smoothing_seconds)
                self._x += alpha * (measured_x - self._x)
                self._y += alpha * (measured_y - self._y)

            self._last_seen = now
            state = TRACKING

        elif self._last_seen is None:
            state = IDLE

        elif now - self._last_seen <= self.hold_seconds:
            # Brief detector misses are common. Do not twitch on each one.
            state = HOLDING

        else:
            alpha = 1 - exp(-elapsed / self.recenter_seconds)
            self._x += alpha * -self._x
            self._y += alpha * -self._y
            state = RECENTERING

        return GazeTarget(
            x=_clamp(self._x, -1.0, 1.0),
            y=_clamp(self._y, -1.0, 1.0),
            state=state,
        )
