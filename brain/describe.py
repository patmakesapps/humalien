"""Answer a question about what the camera can see.

This is the expensive path, so it is deliberately pull-only: it runs when the
conversation model asks to look, not on a timer and not per frame.
"""

import base64
import json
import urllib.error
import urllib.request

import cv2


OLLAMA_URL = "http://localhost:11434/api/generate"

# Bigger images cost more and answer no better for "what is this" questions.
MAX_EDGE = 512
JPEG_QUALITY = 85

SYSTEM = (
    "You are the eyes of a robot called Humalien. Answer only what you can "
    "actually see, in one short spoken sentence. If the answer is not "
    "visible, say so plainly rather than guessing."
)


def downscale(frame, *, max_edge: int = MAX_EDGE):
    """Shrink a frame to what a vision model actually needs."""

    height, width = frame.shape[:2]
    longest = max(height, width)

    if longest <= max_edge:
        return frame

    scale = max_edge / longest

    return cv2.resize(
        frame,
        (round(width * scale), round(height * scale)),
        interpolation=cv2.INTER_AREA,
    )


def to_jpeg(frame, *, quality: int = JPEG_QUALITY) -> bytes:
    ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])

    if not ok:
        raise RuntimeError("Could not JPEG-encode the frame")

    return buffer.tobytes()


def encode_frame(frame, *, max_edge: int = MAX_EDGE) -> str:
    """Shrink and JPEG-encode a frame for a vision model."""

    return base64.b64encode(to_jpeg(downscale(frame, max_edge=max_edge))).decode(
        "ascii"
    )


class OllamaDescriber:
    """Describe a frame using an Ollama vision model, local or cloud."""

    def __init__(
        self,
        *,
        model: str = "gemma4:cloud",
        url: str = OLLAMA_URL,
        timeout: float = 30.0,
    ) -> None:
        self.model = model
        self.url = url
        self.timeout = timeout

    def describe(self, frame, question: str) -> str:
        payload = {
            "model": self.model,
            "system": SYSTEM,
            "prompt": question,
            "images": [encode_frame(frame)],
            "stream": False,
        }

        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                answer = json.load(response).get("response", "")

        except urllib.error.URLError as error:
            # The robot should say it cannot see, not fall over.
            return f"I can't see right now ({error.reason})."

        except TimeoutError:
            return "I couldn't get a good look in time."

        answer = answer.strip()

        return answer or "I'm not sure what I'm looking at."
