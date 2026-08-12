from pathlib import Path

import cv2
import numpy as np

from people import normalize
from vision import MISSING_MODEL, MODEL_DIR


SFACE_MODEL = MODEL_DIR / "face_recognition_sface_2021dec.onnx"


class FaceRecognizer:
    """Turn a detected face into a unit vector.

    This is the whole of identity. No language model is involved, which is
    why it can run continuously without costing anything: an embedding is
    a few milliseconds of CPU, and comparing two is a dot product.
    """

    def __init__(self, *, model_path: str | Path | None = None) -> None:
        path = Path(model_path) if model_path else SFACE_MODEL

        if not path.exists():
            raise FileNotFoundError(MISSING_MODEL.format(path=path))

        self.recognizer = cv2.FaceRecognizerSF.create(str(path), "")

    def embed(self, frame, detection) -> np.ndarray:
        """Embed one detected face.

        The alignment step is why detection has to supply landmarks. Feeding
        SFace a raw crop instead of an aligned one quietly degrades matching
        for exactly the turned heads we care about.
        """

        aligned = self.recognizer.alignCrop(frame, detection.row)
        feature = self.recognizer.feature(aligned)

        return normalize(feature)
