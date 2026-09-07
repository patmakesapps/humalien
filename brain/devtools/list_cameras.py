"""What Humalien can see through, and which one it would pick.

The Arducam is the eye. Everything else is a stand-in. If the Arducam is
listed but not chosen, something is pinning HUMALIEN_CAMERA in .env.
"""

import sys
from pathlib import Path

# Work whether launched as `python -m devtools.x` or `python devtools/x.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import os

from dotenv import load_dotenv

import camera as cameras


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)

    attached = cameras.attached()

    if not attached:
        print(
            "No cameras could be named on this machine. Humalien will fall\n"
            "back to index 0. On Windows this usually means pygrabber is\n"
            "missing: pip install -r requirements.txt"
        )
    else:
        print("Cameras attached:\n")

        for camera in attached:
            print(f"  [{camera.source}] {camera.name}")

    pinned = os.getenv("HUMALIEN_CAMERA") or None
    chosen = cameras.choose(pinned)

    print(f"\nLooking for a name containing: {cameras.preference(None)!r}")

    if pinned:
        print(f"HUMALIEN_CAMERA pins it to {pinned!r}, so nothing is matched.")

    print(f"Humalien would use: {chosen}")


if __name__ == "__main__":
    main()
