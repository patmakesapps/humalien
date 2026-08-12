"""What Humalien can do besides talk.

Three tools, deliberately. Looking is slow and costs money, so the model
decides when it is worth it. Recognition is free and already running, so
asking who is here is cheap. Remembering a name writes immediately, because
the rest of the conversation depends on it.
"""

import asyncio
import json

from describe import OllamaDescriber
from eyes import Eyes
from people import PeopleStore


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "name": "look",
        "description": (
            "Look through your camera and answer a question about what you "
            "can actually see right now: objects, colours, what someone is "
            "doing or holding. Takes several seconds, so say something like "
            "'let me look' before you call it."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": (
                        "The specific question to answer about the view, "
                        "phrased in full."
                    ),
                }
            },
            "required": ["question"],
        },
    },
    {
        "type": "function",
        "name": "who_is_here",
        "description": (
            "Check who is in front of you right now and what you remember "
            "about them. Instant and free. Use it whenever you need to know "
            "who you are talking to."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "remember_name",
        "description": (
            "Save the name of the person you are looking at, once they have "
            "told you. Only call this after somebody actually introduces "
            "themselves. From then on you will recognise their face."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name the person gave.",
                }
            },
            "required": ["name"],
        },
    },
]


def log(message: str) -> None:
    print(f"[TOOLS] {message}", flush=True)


class RobotTools:
    def __init__(
        self,
        eyes: Eyes,
        store: PeopleStore,
        describer: OllamaDescriber,
    ) -> None:
        self.eyes = eyes
        self.store = store
        self.describer = describer

    async def call(self, name: str, arguments: dict) -> str:
        handler = {
            "look": self.look,
            "who_is_here": self.who_is_here,
            "remember_name": self.remember_name,
        }.get(name)

        if handler is None:
            return json.dumps({"error": f"No such tool: {name}"})

        try:
            return await handler(arguments)

        except Exception as error:
            log(f"{name} failed: {error}")
            return json.dumps({"error": str(error)})

    async def look(self, arguments: dict) -> str:
        question = arguments.get("question", "What do you see?")
        frame = self.eyes.frame

        if frame is None:
            return json.dumps({"error": "No camera, so I cannot see anything."})

        log(f'look: "{question}"')

        # Several seconds of network call. Never on the event loop.
        answer = await asyncio.to_thread(
            self.describer.describe,
            frame,
            question,
        )

        log(f'look -> "{answer}"')
        return json.dumps({"you_can_see": answer})

    async def who_is_here(self, arguments: dict) -> str:
        known = [
            {
                "name": person.name,
                "times_seen": person.sighting_count,
                "you_remember": self.store.facts(person.id),
            }
            for person in self.eyes.known
        ]

        strangers = sum(1 for s in self.eyes.sightings if s.match is None)

        log(f"who_is_here -> {[p['name'] for p in known]}, {strangers} stranger(s)")

        return json.dumps(
            {
                "people_you_know": known,
                "unrecognised_faces": strangers,
            }
        )

    async def remember_name(self, arguments: dict) -> str:
        name = (arguments.get("name") or "").strip()

        if not name:
            return json.dumps({"error": "No name given."})

        sighting = self.eyes.largest_stranger()

        if sighting is None:
            # Either nobody unfamiliar is in view, or they have only just
            # appeared. Saying so is better than enrolling the wrong face.
            return json.dumps(
                {
                    "error": (
                        "I cannot see an unfamiliar face to attach that name "
                        "to right now."
                    )
                }
            )

        person = await asyncio.to_thread(
            self.eyes.perception.enroll,
            name,
            sighting,
        )

        log(f"remember_name -> {person.name} (#{person.id})")

        return json.dumps(
            {"saved": person.name, "note": "You will recognise this face from now on."}
        )
