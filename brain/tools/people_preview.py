"""Live test rig for recognition, enrollment and looking.

Keys:
  n  name the largest face on screen
  d  score the largest face against everyone known
  l  ask a question about what the camera sees
  p  list everyone Humalien has met
  q  quit
"""

import argparse
import sys
import time
from pathlib import Path

# Work whether launched as `python -m tools.x` or `python tools/x.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2

from describe import OllamaDescriber
from gaze import select_primary_face
from people import GREET_THRESHOLD, MATCH_THRESHOLD, PeopleStore
from perception import Perception


WINDOW_NAME = "Humalien people preview"

DEFAULT_DB = Path(__file__).resolve().parents[1] / "humalien.db"

KNOWN_COLOR = (80, 220, 80)
UNKNOWN_COLOR = (0, 180, 255)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", default="0")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--model", default="gemma4:cloud")
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


def label_for(sighting) -> tuple[str, tuple[int, int, int]]:
    if sighting.match is None:
        return "seen", UNKNOWN_COLOR

    person = sighting.match.person
    similarity = sighting.match.similarity

    if person.name:
        return f"{person.name} ({similarity:.2f})", KNOWN_COLOR

    return f"unknown #{person.id} ({similarity:.2f})", UNKNOWN_COLOR


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

    for index, line in enumerate(["n name  d score  l look  p people  q quit", answer]):
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


def name_primary(store: PeopleStore, sightings) -> str:
    primary = select_primary_face([s.detection for s in sightings])

    if primary is None:
        return "No face on screen to name."

    sighting = next(s for s in sightings if s.detection is primary)

    if sighting.match is None:
        return "That face is not settled yet — hold still a moment."

    person = sighting.match.person
    print(f"\nNaming person #{person.id} (currently {person.name!r})")
    name = input("Name: ").strip()

    if not name:
        return "Cancelled."

    store.name_person(person.id, name)
    return f"Saved: #{person.id} is {name}"


def diagnose(store: PeopleStore, perception: Perception, frame, sightings) -> str:
    """Score the current face against everyone, so margins are visible."""

    primary = select_primary_face([s.detection for s in sightings])

    if primary is None:
        return "No face on screen to score."

    ranked = store.rank(perception.recognizer.embed(frame, primary))

    if not ranked:
        return "Nobody known yet."

    print("\nSimilarity against everyone known:")

    for person, score in ranked:
        label = person.name or f"(unnamed #{person.id})"

        if score >= GREET_THRESHOLD:
            verdict = "GREET"
        elif score >= MATCH_THRESHOLD:
            verdict = "match"
        else:
            verdict = "-"

        print(f"  {score: .3f}  {verdict:<6} {label}")

    if len(ranked) > 1:
        margin = ranked[0][1] - ranked[1][1]
        print(f"  margin over runner-up: {margin:.3f}")

        return f"top {ranked[0][1]:.2f}, margin {margin:.2f} — see terminal"

    return f"top {ranked[0][1]:.2f}, nobody to compare against"


def list_people(store: PeopleStore) -> str:
    people = store.people()

    print(f"\n{len(people)} people known")

    for person in people:
        label = person.name or f"(unnamed #{person.id})"
        facts = store.facts(person.id)
        print(f"  #{person.id:<4} {label:<20} seen {person.sighting_count}x")

        for fact in facts:
            print(f"         - {fact}")

    return f"{len(people)} people — see terminal"


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
                answer = name_primary(store, sightings)

            elif key == ord("d"):
                answer = diagnose(store, perception, frame, sightings)

            elif key == ord("p"):
                answer = list_people(store)

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
