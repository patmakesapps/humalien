"""Print exactly what Tubby will be told about itself on the next run.

The instructions are assembled from live state - the camera attached now,
the people in the database now, what it remembers now - so the only way to
know what the model actually gets is to build it and look at it.

Nothing here connects to anything. devtools/persona_check.py is the one
that proves the session accepted it.
"""

import sys
from pathlib import Path

# Work whether launched as `python -m devtools.x` or `python devtools/x.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import os

from dotenv import load_dotenv

import camera as cameras
import system_prompt
from people import PeopleStore
from realtime_client import load_persona
from robot_tools import tools


BRAIN = Path(__file__).resolve().parents[1]


def main() -> None:
    load_dotenv(BRAIN / ".env", override=True)

    store = PeopleStore(os.getenv("HUMALIEN_DB", str(BRAIN / "humalien.db")))
    pinned = os.getenv("HUMALIEN_CAMERA") or None
    attached = cameras.choose(pinned).name if (pinned or cameras.attached()) else None

    try:
        prompt = system_prompt.build(
            persona=load_persona(os.getenv("HUMALIEN_PERSONA")),
            tools=[tool["name"] for tool in tools.definitions()],
            body={
                # A dry run cannot know whether the Pi will answer, so it
                # reports what .env asks for. The real prompt reports what
                # actually connected.
                "camera": attached,
                "moves": os.getenv("HUMALIEN_GESTURES", "1") == "1",
                "eyes": os.getenv("HUMALIEN_EYES", "1") == "1",
                "tracking": os.getenv("HUMALIEN_TRACK_FACES", "1") == "1",
            },
            people=[person.name for person in store.people()],
            memories=store.recall(),
        )
    finally:
        store.close()

    print(prompt)
    print(
        f"\n---\n{len(prompt)} characters, roughly {len(prompt) // 4} tokens, "
        "sent once when the session opens.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
