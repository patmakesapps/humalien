"""Remove somebody from Humalien completely, face data and all.

WHAT IS ACTUALLY STORED

No photographs. Humalien never writes an image anywhere - a frame is
encoded in memory, handed to the vision model, and dropped. What persists
is a handful of face embeddings per person: 128 numbers describing a face
well enough to tell it from another one. Not a picture, and not something a
picture can be got back out of, but still an identifier for a specific
person, which is reason enough to be able to delete it.

Deleting a person takes their faces, their facts and any memory filed
against them with it, in one transaction. There is no undo, and no backup
is kept, so this asks for the id rather than the name - names are ambiguous
here, and this database really does have two people called Carter.

  python devtools/forget_person.py            # who is in there
  python devtools/forget_person.py --id 4     # what deleting #4 would take
  python devtools/forget_person.py --id 4 --yes
"""

import argparse
import os
import sys
from pathlib import Path

# Work whether launched as `python -m devtools.x` or `python devtools/x.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from people import PeopleStore


BRAIN = Path(__file__).resolve().parents[1]


def belongings(store: PeopleStore, person_id: int) -> dict:
    counts = {}

    for table in ("faces", "facts", "memories"):
        counts[table] = store.connection.execute(
            f"SELECT COUNT(*) AS n FROM {table} WHERE person_id = ?",
            (person_id,),
        ).fetchone()["n"]

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", type=int, help="Which person, from the listing.")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Actually delete. Without it this only says what would go.",
    )
    args = parser.parse_args()

    load_dotenv(BRAIN / ".env", override=True)

    store = PeopleStore(os.getenv("HUMALIEN_DB", str(BRAIN / "humalien.db")))

    try:
        people = {person.id: person for person in store.people()}

        if args.id is None:
            print("Everyone Humalien knows:\n")

            for person in people.values():
                counts = belongings(store, person.id)
                print(
                    f"  #{person.id}  {person.name:<18} "
                    f"{person.sighting_count:>6} sightings, "
                    f"{counts['faces']} face records"
                )

            print("\nDelete one with --id N, then --id N --yes to confirm.")
            return

        person = people.get(args.id)

        if person is None:
            print(f"There is no person #{args.id}. Run with no arguments to list.")
            sys.exit(1)

        counts = belongings(store, person.id)

        print(f"#{person.id} {person.name}")
        print(f"  {person.sighting_count} sightings")
        print(f"  {counts['faces']} face records - the only thing describing them")
        print(f"  {counts['facts']} facts, {counts['memories']} memories filed on them")

        if not args.yes:
            print("\nNothing deleted. Add --yes to go through with it.")
            return

        store.forget(person.id)

        # Read it back rather than trusting the delete, because this is the
        # one operation nobody can check afterwards by trying again.
        left = belongings(store, args.id)
        gone = store.person(args.id) is None and not any(left.values())

        print(f"\nDeleted {person.name}." if gone else f"\nSomething is left: {left}")
    finally:
        store.close()


if __name__ == "__main__":
    main()
