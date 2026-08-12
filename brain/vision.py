from pathlib import Path

import cv2

from gaze import FaceBox


class OpenCVFaceDetector:
    """Small, model-download-free face detector for the webcam prototype."""

    def __init__(
        self,
        *,
        cascade_path: str | Path | None = None,
        scale_factor: float = 1.1,
        min_neighbors: int = 5,
        min_face_size: int = 60,
    ) -> None:
        if cascade_path is None:
            cascade_path = (
                Path(cv2.data.haarcascades)
                / "haarcascade_frontalface_default.xml"
            )

        self.cascade = cv2.CascadeClassifier(str(cascade_path))

        if self.cascade.empty():
            raise RuntimeError(
                f"Could not load OpenCV face cascade: {cascade_path}"
            )

        self.scale_factor = scale_factor
        self.min_neighbors = min_neighbors
        self.min_face_size = min_face_size

    def detect(self, frame) -> list[FaceBox]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        detections = self.cascade.detectMultiScale(
            gray,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
            minSize=(self.min_face_size, self.min_face_size),
        )

        return [
            FaceBox(
                x=int(x),
                y=int(y),
                width=int(width),
                height=int(height),
            )
            for x, y, width, height in detections
        ]
