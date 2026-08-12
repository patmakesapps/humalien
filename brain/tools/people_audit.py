"""Check whether unnamed records are strangers or ghosts of known people.

A one-sighting unnamed record is usually a known face caught at a bad angle
that scored just too low to match. This scores every unnamed person against
every named one so you can tell the difference, and fold the ghosts back in.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from people import CREATE_BELOW, MATCH_THRESHOLD, PeopleStore


DEFAULT_DB = Path(__file__).resolve().parents[1] / "humalien.db"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument(
        "--merge-above",
        type=float,
        help="Fold unnamed records scoring above this into the named person",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Delete unnamed records seen fewer than 3 times",
    )
    parser.add_argument(
        "--forget-unnamed",
        action="store_true",
        help="Delete every unnamed record, whatever its history",
    )
    return parser.parse_args()


def faces_by_person(store: PeopleStore) -> dict[int, np.ndarray]:
    grouped: dict[int, list[np.ndarray]] = {}

    for row in store.connection.execute("SELECT person_id, embedding FROM faces"):
        vector = np.frombuffer(row["embedding"], dtype=np.float32)
        grouped.setdefault(row["person_id"], []).append(vector)

    return {person_id: np.stack(rows) for person_id, rows in grouped.items()}


def closest_named(
    faces: dict[int, np.ndarray],
    unnamed_id: int,
    named: list,
) -> tuple[object, float]:
    mine = faces.get(unnamed_id)
    best_person, best_score = None, 0.0

    for person in named:
        theirs = faces.get(person.id)

        if mine is None or theirs is None:
            continue

        score = float(np.max(mine @ theirs.T))

        if score > best_score:
            best_person, best_score = person, score

    return best_person, best_score


def main() -> None:
    args = parse_args()

    store = PeopleStore(args.db)
    faces = faces_by_person(store)

    people = store.people()
    named = [p for p in people if p.name]
    unnamed = [p for p in people if not p.name]

    print(f"{len(named)} named, {len(unnamed)} unnamed\n")

    if not named:
        print("Nobody is named yet, so there is nothing to compare against.")
        store.close()
        return

    verdicts = []

    for person in sorted(unnamed, key=lambda p: p.id):
        match, score = closest_named(faces, person.id, named)

        if match is None:
            verdict, label = "no faces", ""
        elif score >= MATCH_THRESHOLD:
            verdict, label = "GHOST", match.name
        elif score >= CREATE_BELOW:
            verdict, label = "likely ghost", match.name
        else:
            verdict, label = "stranger", match.name

        print(
            f"  #{person.id:<4} seen {person.sighting_count:<4}x"
            f"  closest: {score:.3f} ({label})  -> {verdict}"
        )

        verdicts.append((person, match, score, verdict))

    ghosts = [v for v in verdicts if v[3] in ("GHOST", "likely ghost")]

    print(
        f"\n{len(ghosts)} of {len(unnamed)} unnamed records look like known people."
    )

    if ghosts and args.merge_above is None and not args.prune:
        print(
            "\nIf these are ghosts, CREATE_BELOW in people.py is too low.\n"
            "Fold them in with:  --merge-above 0.30"
        )

    if args.merge_above is not None:
        merged = 0

        for person, match, score, _ in verdicts:
            if match is not None and score >= args.merge_above:
                store.merge(match.id, person.id)
                merged += 1
                print(f"  merged #{person.id} into {match.name}")

        print(f"\n{merged} records merged")

    if args.forget_unnamed:
        removed = store.forget_unnamed()
        print(f"\n{removed} unnamed records forgotten")

    elif args.prune:
        removed = store.prune_unnamed(min_sightings=3, older_than_seconds=0)
        print(f"\n{removed} unnamed records pruned")

    store.close()


if __name__ == "__main__":
    main()
