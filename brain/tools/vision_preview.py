import argparse
import json
import time

import cv2

from gaze import GazeController, select_primary_face
from vision import YuNetFaceDetector


WINDOW_NAME = "Humalien vision preview"


def camera_source(value: str) -> int | str:
    try:
        return int(value)
    except ValueError:
        return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Preview Humalien's face tracking and normalized gaze target."
        )
    )
    parser.add_argument(
        "--camera",
        default="0",
        help="OpenCV camera index or device path (default: 0)",
    )
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument(
        "--no-mirror",
        action="store_true",
        help="Do not mirror the preview horizontally",
    )
    parser.add_argument(
        "--emit-json",
        action="store_true",
        help="Print gaze_target JSON messages at about 10 Hz",
    )
    return parser.parse_args()


def draw_overlay(frame, face, target, fps: float) -> None:
    height, width = frame.shape[:2]
    center = (width // 2, height // 2)

    cv2.line(
        frame,
        (center[0] - 18, center[1]),
        (center[0] + 18, center[1]),
        (100, 100, 100),
        1,
    )
    cv2.line(
        frame,
        (center[0], center[1] - 18),
        (center[0], center[1] + 18),
        (100, 100, 100),
        1,
    )

    if face is not None:
        cv2.rectangle(
            frame,
            (face.x, face.y),
            (face.x + face.width, face.y + face.height),
            (80, 220, 80),
            2,
        )

    target_pixel = (
        min(width - 1, int((target.x + 1) * 0.5 * width)),
        min(height - 1, int((target.y + 1) * 0.5 * height)),
    )
    cv2.circle(frame, target_pixel, 10, (0, 200, 255), -1)

    lines = [
        f"state: {target.state}",
        f"target: x={target.x:+.3f}  y={target.y:+.3f}",
        f"fps: {fps:.1f}",
        "q / Esc: quit",
    ]

    for index, line in enumerate(lines):
        cv2.putText(
            frame,
            line,
            (18, 32 + index * 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )


def main() -> None:
    args = parse_args()

    capture = cv2.VideoCapture(camera_source(args.camera))
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    capture.set(cv2.CAP_PROP_FPS, args.fps)

    if not capture.isOpened():
        raise RuntimeError(
            f"Could not open camera {args.camera!r}. Try another --camera index."
        )

    detector = YuNetFaceDetector()
    controller = GazeController()

    previous_frame_at = time.monotonic()
    next_json_at = previous_frame_at

    print("Humalien vision online. Press q or Esc in the preview to stop.")

    try:
        while True:
            ok, frame = capture.read()

            if not ok:
                raise RuntimeError("The camera stopped returning frames")

            if not args.no_mirror:
                frame = cv2.flip(frame, 1)

            now = time.monotonic()
            frame_height, frame_width = frame.shape[:2]
            primary = select_primary_face(detector.detect(frame))
            face = None if primary is None else primary.box
            target = controller.update(
                face,
                frame_width=frame_width,
                frame_height=frame_height,
                now=now,
            )

            elapsed = max(now - previous_frame_at, 1e-9)
            previous_frame_at = now
            draw_overlay(frame, face, target, 1 / elapsed)

            if args.emit_json and now >= next_json_at:
                print(
                    json.dumps(
                        {
                            "type": "gaze_target",
                            "x": round(target.x, 4),
                            "y": round(target.y, 4),
                            "state": target.state,
                        }
                    ),
                    flush=True,
                )
                next_json_at = now + 0.1

            cv2.imshow(WINDOW_NAME, frame)
            key = cv2.waitKey(1) & 0xFF

            if key in (ord("q"), 27):
                return

    finally:
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
