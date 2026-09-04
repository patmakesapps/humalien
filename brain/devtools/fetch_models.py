"""Download the ONNX models used for face detection and recognition.

These are small, but they are not bundled with opencv-python and they are not
committed to the repo. Run this once per machine.
"""

import urllib.request
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parents[1] / "models"

ZOO = "https://github.com/opencv/opencv_zoo/raw/main/models"

MODELS = {
    "face_detection_yunet_2023mar.onnx": (
        f"{ZOO}/face_detection_yunet/face_detection_yunet_2023mar.onnx"
    ),
    "face_recognition_sface_2021dec.onnx": (
        f"{ZOO}/face_recognition_sface/face_recognition_sface_2021dec.onnx"
    ),
}


def fetch(name: str, url: str) -> Path:
    destination = MODEL_DIR / name

    if destination.exists():
        size_kb = destination.stat().st_size / 1024
        print(f"{name}: already present ({size_kb:.0f} KB)")
        return destination

    print(f"{name}: downloading...")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # Download beside the target and rename, so an interrupted run does not
    # leave a truncated file that looks valid on the next pass.
    partial = destination.with_suffix(".partial")

    with urllib.request.urlopen(url, timeout=120) as response:
        partial.write_bytes(response.read())

    partial.replace(destination)

    size_kb = destination.stat().st_size / 1024
    print(f"{name}: saved ({size_kb:.0f} KB)")

    return destination


def main() -> None:
    for name, url in MODELS.items():
        fetch(name, url)

    print(f"\nModels are in {MODEL_DIR}")


if __name__ == "__main__":
    main()
