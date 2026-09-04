"""Live test rig for recognition, enrollment and looking.

Keys:
  n  introduce the largest face on screen
  d  score the largest face against everyone known
  l  ask a question about what the camera sees
  p  list everyone Humalien knows
  f  forget somebody
  q  quit
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Work whether launched as `python -m devtools.x` or `python devtools/x.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
from dotenv import load_dotenv

from describe import OllamaDescriber
from people import GREET_THRESHOLD, MATCH_THRESHOLD, PeopleStore
from perception import Perception


WINDOW_NAME = "Humalien people preview"

DEFAULT_DB = Path(__file__).resolve().parents[1] / "humalien.db"

KNOWN_COLOR = (80, 220, 80)
STRANGER_COLOR = (0, 180, 255)


def parse_args() -> argparse.Namespace:
    # Same settings the robot itself uses, so the preview matches it.
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", default=os.getenv("HUMALIEN_CAMERA", "0"))
    parser.add_argument("--db", default=os.getenv("HUMALIEN_DB", str(DEFAULT_DB)))
    parser.add_argument(
        "--model",
        default=os.getenv("HUMALIEN_VISION_MODEL", "gemma4:cloud"),
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.25,
        help="Seconds between recognition passes (default: 0.25)",
    )
    return parser.parse_args()


def camera_source(value: str) -> int | str:
    try:
        return int(value)
    except ValueError:
        return value


def largest(sightings):
    if not sightings:
        return None

    return max(sightings, key=lambda sighting: sighting.detection.area)


def label_for(sighting) -> tuple[str, tuple[int, int, int]]:
    if sighting.match is None:
        return "stranger", STRANGER_COLOR

    return (
        f"{sighting.name} ({sighting.match.similarity:.2f})",
        KNOWN_COLOR,
    )


def draw(frame, sightings, answer: str) -> None:
    for sighting in sightings:
        box = sighting.detection.box
        text, color = label_for(sighting)

        cv2.rectangle(
            frame,
            (box.x, box.y),
            (box.x + box.width, box.y + box.height),
            color,
            2,
        )
        cv2.putText(
            frame,
            text,
            (box.x, max(box.y - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
            cv2.LINE_AA,
        )

    lines = ["n meet  d score  l look  p people  f forget  q quit", answer]

    for index, line in enumerate(lines):
        if not line:
            continue

        cv2.putText(
            frame,
            line[:90],
            (18, 30 + index * 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )


def introduce(perception: Perception, sightings) -> str:
    sighting = largest(sightings)

    if sighting is None:
        return "No face on screen."

    if sighting.match is not None:
        print(f"\nThat is already {sighting.name}.")
        return f"Already know {sighting.name}"

    name = input("\nWho is this? ").strip()

    if not name:
        return "Cancelled."

    person = perception.enroll(name, sighting)
    return f"Met {person.name} (#{person.id})"


def diagnose(store: PeopleStore, sightings) -> str:
    """Score the current face against everyone, so margins are visible."""

    sighting = largest(sightings)

    if sighting is None:
        return "No face on screen to score."

    ranked = store.rank(sighting.embedding)

    if not ranked:
        return "Nobody known yet."

    print("\nSimilarity against everyone known:")

    for person, score in ranked:
        if score >= GREET_THRESHOLD:
            verdict = "GREET"
        elif score >= MATCH_THRESHOLD:
            verdict = "match"
        else:
            verdict = "-"

        print(f"  {score: .3f}  {verdict:<6} {person.name}")

    if len(ranked) > 1:
        margin = ranked[0][1] - ranked[1][1]
        print(f"  margin over runner-up: {margin:.3f}")

        return f"top {ranked[0][1]:.2f}, margin {margin:.2f} - see terminal"

    return f"top {ranked[0][1]:.2f}, nobody to compare against"


def list_people(store: PeopleStore) -> str:
    people = store.people()

    print(f"\n{len(people)} people known")

    for person in people:
        print(f"  #{person.id:<4} {person.name:<20} seen {person.sighting_count}x")

        for fact in store.facts(person.id):
            print(f"         - {fact}")

    return f"{len(people)} people - see terminal"


def forget(store: PeopleStore) -> str:
    list_people(store)
    answer = input("\nForget which id? ").strip()

    if not answer.isdigit():
        return "Cancelled."

    person = store.person(int(answer))

    if person is None:
        return f"No person #{answer}"

    store.forget(person.id)
    return f"Forgot {person.name}"


def main() -> None:
    args = parse_args()

    capture = cv2.VideoCapture(camera_source(args.camera))

    if not capture.isOpened():
        raise RuntimeError(f"Could not open camera {args.camera!r}")

    store = PeopleStore(args.db)
    perception = Perception(store)
    describer = OllamaDescriber(model=args.model)

    print(f"Database: {args.db}")
    print(f"Describer: {args.model}")
    print(f"{len(store.people())} people known")

    sightings = []
    answer = ""
    next_poll = 0.0

    try:
        while True:
            ok, frame = capture.read()

            if not ok:
                raise RuntimeError("The camera stopped returning frames")

            now = time.monotonic()

            # Recognition does not need to run at frame rate.
            if now >= next_poll:
                sightings = perception.poll(frame)
                next_poll = now + args.interval

            display = frame.copy()
            draw(display, sightings, answer)
            cv2.imshow(WINDOW_NAME, display)

            key = cv2.waitKey(1) & 0xFF

            if key in (ord("q"), 27):
                return

            if key == ord("n"):
                answer = introduce(perception, sightings)

            elif key == ord("d"):
                answer = diagnose(store, sightings)

            elif key == ord("p"):
                answer = list_people(store)

            elif key == ord("f"):
                answer = forget(store)

            elif key == ord("l"):
                question = input("\nAsk about the view: ").strip()

                if question:
                    started = time.monotonic()
                    answer = describer.describe(frame, question)
                    print(f"[{time.monotonic() - started:.1f}s] {answer}")

    except KeyboardInterrupt:
        print("\nStopped")

    finally:
        capture.release()
        cv2.destroyAllWindows()
        store.close()


if __name__ == "__main__":
    main()
