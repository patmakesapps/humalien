"""What Humalien can do besides talk.

Four tools, deliberately. Looking is slow and costs money, so the model
decides when it is worth it. Recognition is free and already running, so
asking who is here is cheap. Remembering a name writes immediately, because
the rest of the conversation depends on it. Feeling something is instant and
changes only how the eyes look.

Each tool declares its schema next to its handler. See tool_registry.py.
"""

import asyncio
from dataclasses import dataclass, field

from conversation import ConversationState
from describe import OllamaDescriber, to_jpeg
from eyes import Eyes
from mood import FEELINGS
from people import PeopleStore
from tool_registry import ToolError, ToolRegistry


REALTIME = "realtime"
OLLAMA = "ollama"

# Travels with the picture, in the same conversation item. The model has no
# other way to tell its own eyes from a photograph somebody handed it, and
# without this it says things like "in the image you sent me".
OWN_EYES = (
    "This is your own camera, from the moment they were asking. Nobody sent "
    "it to you. Talk about it as what you can see, not as a picture."
)

tools = ToolRegistry()


def log(message: str) -> None:
    print(f"[TOOLS] {message}", flush=True)


@dataclass
class Robot:
    """Everything the tools are allowed to touch."""

    eyes: Eyes
    store: PeopleStore
    describer: OllamaDescriber
    state: ConversationState = field(default_factory=ConversationState)
    realtime: object | None = None
    mood: object | None = None
    vision: str = REALTIME

    # The picture currently in front of the model, if any. Only ever one.
    showing: str | None = None
    looks: int = 0

    def looks_with_realtime(self) -> bool:
        return self.vision == REALTIME and self.realtime is not None

    def forget_showing(self) -> None:
        self.showing = None

    def fall_back_to_ollama(self, why: str) -> None:
        """Stop using Realtime vision for the rest of this session.

        A rejected image comes back as an asynchronous error event, long
        after the tool returned, so the turn that triggered it is already
        lost. Everything after it goes to Ollama instead.
        """

        if self.vision == OLLAMA:
            return

        self.vision = OLLAMA
        log(f"Realtime vision unavailable ({why}) - falling back to Ollama")


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
    # The moment worth looking at is when the question was asked, not now.
    # By the time a tool call arrives the speaker has finished talking, the
    # model has generated a sentence, and the hand being asked about has
    # moved.
    since, until = robot.state.speech_window()

    frame = robot.eyes.clearest_frame(since=since, until=until)

    if frame is None:
        raise ToolError("There is no camera, so you cannot see anything.")

    log(f'look: "{question}"')

    if robot.looks_with_realtime():
        try:
            # Take the previous picture away first, so only one is ever
            # being re-sent with every later turn. Follow-up questions still
            # work, because the one being discussed is the one still there.
            if robot.showing:
                await robot.realtime.delete_item(robot.showing)

            robot.looks += 1
            item_id = f"humalien_look_{robot.looks}"

            robot.showing = await robot.realtime.send_image(
                to_jpeg(frame),
                item_id=item_id,
                caption=OWN_EYES,
            )

            log(f"look -> handed the frame to the model ({item_id})")

            # Deliberately bare. Anything readable here gets read out.
            return {"looked": True}

        except Exception as error:
            robot.forget_showing()
            robot.fall_back_to_ollama(f"{type(error).__name__}: {error}")

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


@tools.tool(
    "feel",
    "Show an emotion in your eyes. Instant, silent, and free - call it "
    "whenever what you are about to say has a feeling attached, and keep "
    "talking. Your eyes already handle listening, thinking and talking on "
    "their own; this is only for the feeling underneath. Do not mention it "
    "or describe your eyes out loud.",
    properties={
        "feeling": {
            "type": "string",
            "enum": list(FEELINGS),
            "description": "How you feel right now.",
        }
    },
    required=["feeling"],
)
async def feel(robot: Robot, feeling: str) -> dict:
    if robot.mood is None:
        # No eyes on this robot. Not worth an error the model has to
        # apologise for - it simply does not show.
        return {"shown": None}

    if not robot.mood.feel(feeling):
        raise ToolError(
            f"{feeling!r} is not something you can show. Choose one of: "
            + ", ".join(FEELINGS)
        )

    return {"shown": feeling}
