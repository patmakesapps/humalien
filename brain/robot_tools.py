"""What Humalien can do besides talk.

Three tools, deliberately. Looking is slow and costs money, so the model
decides when it is worth it. Recognition is free and already running, so
asking who is here is cheap. Remembering a name writes immediately, because
the rest of the conversation depends on it.

Each tool declares its schema next to its handler. See tool_registry.py.
"""

import asyncio
from dataclasses import dataclass

from describe import OllamaDescriber
from eyes import Eyes
from people import PeopleStore
from tool_registry import ToolError, ToolRegistry


tools = ToolRegistry()


def log(message: str) -> None:
    print(f"[TOOLS] {message}", flush=True)


@dataclass
class Robot:
    """Everything the tools are allowed to touch."""

    eyes: Eyes
    store: PeopleStore
    describer: OllamaDescriber


@tools.tool(
    "look",
    "Look through your camera and answer a question about what you can "
    "actually see right now: objects, colours, what someone is doing or "
    "holding. Takes several seconds, so say something like 'hang on' before "
    "you call it.",
    properties={
        "question": {
            "type": "string",
            "description": (
                "The specific question to answer about the view, phrased in "
                "full."
            ),
        }
    },
    required=["question"],
)
async def look(robot: Robot, question: str) -> dict:
    frame = robot.eyes.frame

    if frame is None:
        raise ToolError("There is no camera, so you cannot see anything.")

    log(f'look: "{question}"')

    # Several seconds of network call. Never on the event loop.
    answer = await asyncio.to_thread(robot.describer.describe, frame, question)

    log(f'look -> "{answer}"')

    return {"you_can_see": answer}


@tools.tool(
    "who_is_here",
    "Quietly check who is in front of you and what you remember about them. "
    "Instant and free. The result is private - it is your own perception, "
    "never something to read out, describe, or mention. You do not need this "
    "to greet somebody or make small talk.",
)
async def who_is_here(robot: Robot) -> dict:
    known = [
        {
            "name": person.name,
            "times_seen": person.sighting_count,
            "you_remember": robot.store.facts(person.id),
        }
        for person in robot.eyes.known
    ]

    strangers = sum(1 for s in robot.eyes.sightings if s.match is None)

    log(f"who_is_here -> {[p['name'] for p in known]}, {strangers} stranger(s)")

    return {"people_you_know": known, "unrecognised_faces": strangers}


@tools.tool(
    "remember_name",
    "Save the name of the person you are looking at, once they have told "
    "you. Only call this after somebody actually introduces themselves. From "
    "then on you will recognise their face. Do not announce that you saved "
    "it - just carry on talking.",
    properties={
        "name": {
            "type": "string",
            "description": "The name the person gave.",
        }
    },
    required=["name"],
)
async def remember_name(robot: Robot, name: str) -> dict:
    sighting = robot.eyes.largest_stranger()

    if sighting is None:
        # Either nobody unfamiliar is in view, or they have only just
        # appeared. Saying so is better than enrolling the wrong face.
        raise ToolError(
            "You cannot see an unfamiliar face to attach that name to."
        )

    person = await asyncio.to_thread(
        robot.eyes.perception.enroll,
        name,
        sighting,
    )

    log(f"remember_name -> {person.name} (#{person.id})")

    return {"saved": person.name}
