from pathlib import Path

import cv2

from gaze import FaceBox


FRONTAL_CASCADE = "haarcascade_frontalface_default.xml"
PROFILE_CASCADE = "haarcascade_profileface.xml"


def _load_cascade(path: str | Path | None, default_name: str):
    if path is None:
        path = Path(cv2.data.haarcascades) / default_name

    cascade = cv2.CascadeClassifier(str(path))

    if cascade.empty():
        raise RuntimeError(f"Could not load OpenCV face cascade: {path}")

    return cascade


class OpenCVFaceDetector:
    """Small, model-download-free face detector for the webcam prototype."""

    def __init__(
        self,
        *,
        cascade_path: str | Path | None = None,
        profile_cascade_path: str | Path | None = None,
        scale_factor: float = 1.1,
        min_neighbors: int = 5,
        min_face_size: int = 60,
        detect_profiles: bool = True,
    ) -> None:
        self.cascade = _load_cascade(cascade_path, FRONTAL_CASCADE)

        self.profile_cascade = (
            _load_cascade(profile_cascade_path, PROFILE_CASCADE)
            if detect_profiles
            else None
        )

        self.scale_factor = scale_factor
        self.min_neighbors = min_neighbors
        self.min_face_size = min_face_size

    def _run(self, cascade, gray) -> list[FaceBox]:
        detections = cascade.detectMultiScale(
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

    def detect(self, frame) -> list[FaceBox]:
        """Find faces, falling back to profile views when facing away.

        The frontal cascade is tried first because it is the most
        reliable and the common case, so a face looking at the robot
        costs a single pass. Turning side on costs up to three.
        """

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        faces = self._run(self.cascade, gray)

        if faces or self.profile_cascade is None:
            return faces

        faces = self._run(self.profile_cascade, gray)

        if faces:
            return faces

        # The profile cascade is trained on one direction only. Flip the
        # frame to catch a head turned the other way, then flip the
        # coordinates back so they still describe the real image.
        frame_width = gray.shape[1]
        flipped = self._run(self.profile_cascade, cv2.flip(gray, 1))

        return [face.mirrored(frame_width) for face in flipped]
