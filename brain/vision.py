from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np

from gaze import FaceBox


MODEL_DIR = Path(__file__).resolve().parent / "models"
YUNET_MODEL = MODEL_DIR / "face_detection_yunet_2023mar.onnx"

MISSING_MODEL = (
    "Face model not found: {path}\nRun: python devtools/fetch_models.py"
)


class Detection(NamedTuple):
    """A detected face, plus the landmarks recognition needs.

    `box` is the gaze contract and stays free of OpenCV types. `row` is
    YuNet's raw 15-column output — bounding box, five landmarks, score —
    which SFace requires to align the crop before embedding it.
    """

    box: FaceBox
    row: np.ndarray

    @property
    def area(self) -> int:
        # Lets select_primary_face pick a Detection without knowing about it.
        return self.box.area


class YuNetFaceDetector:
    """CNN face detector. Handles head turn, which Haar cascades do not.

    The Haar frontal cascade could not see a profile at all, and pairing it
    with the profile cascade still left a dead zone around the three-quarter
    view. YuNet covers the rotation smoothly in a single pass, and it is the
    only detector here that emits the landmarks SFace needs.
    """

    def __init__(
        self,
        *,
        model_path: str | Path | None = None,
        score_threshold: float = 0.7,
        nms_threshold: float = 0.3,
        top_k: int = 50,
    ) -> None:
        path = Path(model_path) if model_path else YUNET_MODEL

        if not path.exists():
            raise FileNotFoundError(MISSING_MODEL.format(path=path))

        self.detector = cv2.FaceDetectorYN.create(
            str(path),
            "",
            (320, 320),
            score_threshold,
            nms_threshold,
            top_k,
        )
        self._input_size = (320, 320)

    def detect(self, frame) -> list[Detection]:
        height, width = frame.shape[:2]

        if self._input_size != (width, height):
            self.detector.setInputSize((width, height))
            self._input_size = (width, height)

        _, faces = self.detector.detect(frame)

        if faces is None:
            return []

        return [
            Detection(
                box=FaceBox(
                    x=int(row[0]),
                    y=int(row[1]),
                    width=int(row[2]),
                    height=int(row[3]),
                ),
                row=row,
            )
            for row in faces
        ]
