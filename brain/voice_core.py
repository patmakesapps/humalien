import asyncio
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from websockets.asyncio.client import connect as websocket_connect

from audio_adapter import ModelToPiAudio, PiToModelAudio
from describe import OllamaDescriber
from eyes import Eyes
from mic_gate import HALF_DUPLEX, build_mic_gate
from people import PeopleStore
from perception import Perception
from playback import PacedPlayback
from realtime_client import RealtimeClient, load_persona
from robot_tools import TOOL_DEFINITIONS, RobotTools


ENV_FILE = Path(__file__).resolve().parent / ".env"
DEFAULT_DB = Path(__file__).resolve().parent / "humalien.db"

# How long somebody must be out of view before walking back in counts as an
# arrival worth greeting again.
FORGET_PRESENCE_AFTER = 60.0

# How long a stranger must be genuinely gone before Humalien offers to meet
# them again. Detection drops out for a frame all the time; without this,
# a flicker makes it introduce itself over and over.
RE_OFFER_AFTER = 20.0


def log(message: str) -> None:
    print(f"[VOICE CORE] {message}", flush=True)


class ConversationState:
    """Whether the model is mid-answer, so nothing interrupts it."""

    def __init__(self):
        self.response_active = False


async def pi_to_realtime(pi_websocket, realtime: RealtimeClient, gate) -> None:
    adapter = PiToModelAudio()
    listening = True

    async for message in pi_websocket:
        if isinstance(message, bytes):
            if not gate.is_open:
                if listening:
                    listening = False
                    log("Microphone closed - Humalien is speaking")

                # Keep feeding the resampler so its state stays continuous
                # and reopening does not produce a click.
                adapter.convert(message)
                continue

            if not listening:
                listening = True
                log("Microphone open")

            converted_audio = adapter.convert(message)

            if converted_audio:
                await realtime.send_audio(converted_audio)

            continue

        try:
            event = json.loads(message)
        except json.JSONDecodeError:
            log(f"Unknown Pi message: {message}")
            continue

        event_type = event.get("type", "unknown")

        if event_type == "node_status":
            node = event.get("node", "unknown")
            state = event.get("state", "unknown")
            log(f"Pi node {node}: {state}")
        else:
            log(f"Pi event: {event_type}")


async def run_tool_call(
    realtime: RealtimeClient,
    tools: RobotTools,
    call_id: str,
    name: str,
    raw_arguments: str,
) -> None:
    try:
        arguments = json.loads(raw_arguments or "{}")
    except json.JSONDecodeError:
        arguments = {}

    result = await tools.call(name, arguments)

    await realtime.send_function_output(call_id, result)
    await realtime.create_response()


async def realtime_to_pi(
    realtime: RealtimeClient,
    playback: PacedPlayback,
    tools: RobotTools,
    state: ConversationState,
) -> None:
    adapter = ModelToPiAudio()
    answering = False

    async for event in realtime.receive_events():
        event_type = event.get("type", "unknown")

        if event_type == "session.updated":
            log("Realtime session ready")

        elif event_type == "input_audio_buffer.speech_started":
            log("User speech started")

            if playback.is_speaking:
                log("Interrupted - dropping queued speech")

                playback.clear()
                adapter = ModelToPiAudio()
                answering = False

                if state.response_active:
                    await realtime.cancel_response()

        elif event_type == "input_audio_buffer.speech_stopped":
            log("User speech stopped")

        elif event_type == "conversation.item.input_audio_transcription.completed":
            transcript = event.get("transcript")

            if transcript:
                log(f'User said: "{transcript.strip()}"')

        elif event_type == "response.created":
            state.response_active = True

        elif event_type == "response.done":
            state.response_active = False

        elif event_type == "response.function_call_arguments.done":
            # Deliberately not awaited. Looking takes several seconds, and
            # blocking here would stall the audio flowing to the Pi.
            asyncio.create_task(
                run_tool_call(
                    realtime,
                    tools,
                    event.get("call_id"),
                    event.get("name"),
                    event.get("arguments"),
                )
            )

        elif event_type == "response.output_audio.delta":
            if not answering:
                answering = True
                log("Humalien started answering")

            model_audio = realtime.decode_audio_delta(event)

            if model_audio:
                playback.push(adapter.convert(model_audio))

        elif event_type == "response.output_audio.done":
            # Flush the final samples held inside the streaming resampler.
            playback.push(adapter.convert(b"", final=True))

            adapter = ModelToPiAudio()

            # "Answering" means the model has finished generating, not that
            # the head has finished talking. PacedPlayback is still draining
            # for as long as it takes to speak. Drive a jaw from there.
            if answering:
                answering = False
                log("Humalien finished answering")

        elif event_type == "response.output_audio_transcript.done":
            transcript = event.get("transcript")

            if transcript:
                log(f'Humalien said: "{transcript.strip()}"')

        elif event_type == "error":
            # Logged rather than raised: a stray cancellation or an
            # unsupported field should not take the whole robot down.
            log(f"Realtime API error:\n{json.dumps(event, indent=2)}")


async def watch_the_room(
    eyes: Eyes,
    realtime: RealtimeClient,
    playback: PacedPlayback,
    store: PeopleStore,
    state: ConversationState,
) -> None:
    """Tell the model when somebody arrives.

    The model has no reason to suspect the room changed, so it will never
    call a tool to find out. Arrivals have to be pushed. Everything else
    stays pull-only.

    These messages report what happened and nothing else. What to do about
    it - whether to greet, introduce itself, or stay quiet - belongs to the
    session instructions, where the character lives. Scripting a reply here
    would be putting words in its mouth from the outside.
    """

    last_seen: dict[int, float] = {}
    greeted: set[int] = set()
    offered_to_meet = False
    stranger_gone_since: float | None = None

    while True:
        await asyncio.sleep(0.5)

        now = time.monotonic()
        idle = not state.response_active and not playback.is_speaking

        present = {person.id: person for person in eyes.known}

        for person_id in present:
            last_seen[person_id] = now

        # Somebody long gone counts as a new arrival when they return.
        for person_id, seen_at in list(last_seen.items()):
            if now - seen_at > FORGET_PRESENCE_AFTER:
                last_seen.pop(person_id)
                greeted.discard(person_id)

        arrivals = [
            person for person_id, person in present.items() if person_id not in greeted
        ]

        if arrivals and idle:
            for person in arrivals:
                greeted.add(person.id)

            names = ", ".join(person.name for person in arrivals)
            remembered = [
                fact for person in arrivals for fact in store.facts(person.id)
            ]

            log(f"{names} came into view")

            context = f"{names} has just come into view."

            if remembered:
                context += " You remember: " + "; ".join(remembered)

            await realtime.send_context(context)
            await realtime.create_response()
            continue

        stranger = eyes.largest_stranger()

        if stranger is None:
            # Detection drops out for a frame constantly. Only re-arm once
            # they are genuinely gone, or a flicker makes Humalien introduce
            # itself over and over.
            if stranger_gone_since is None:
                stranger_gone_since = now

            elif now - stranger_gone_since > RE_OFFER_AFTER:
                offered_to_meet = False

        else:
            stranger_gone_since = None

            if not offered_to_meet and idle and not present:
                offered_to_meet = True

                log("A stranger is here")

                # Deliberately no create_response. Forcing a reply here gave
                # the model nothing to respond to except this note, so it
                # read the note out. Now it simply knows, and uses it when
                # the person actually speaks.
                await realtime.send_context(
                    "A face you do not recognise has been in view for a few "
                    "seconds."
                )


async def run_voice_core() -> None:
    load_dotenv(ENV_FILE)

    api_key = os.getenv("OPENAI_API_KEY")
    pi_url = os.getenv("HUMALIEN_PI_URL", "ws://10.0.0.83:8765")
    model = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime-2.1-mini")
    voice = os.getenv("OPENAI_REALTIME_VOICE", "marin")
    gate_name = os.getenv("HUMALIEN_MIC_GATE", HALF_DUPLEX)
    eagerness = os.getenv("HUMALIEN_VAD_EAGERNESS", "auto")
    noise_reduction = os.getenv("HUMALIEN_NOISE_REDUCTION", "far_field")
    transcription_model = os.getenv(
        "HUMALIEN_TRANSCRIPTION_MODEL",
        "gpt-4o-mini-transcribe",
    )
    camera = os.getenv("HUMALIEN_CAMERA", "0")
    database = os.getenv("HUMALIEN_DB", str(DEFAULT_DB))
    vision_model = os.getenv("HUMALIEN_VISION_MODEL", "gemma4:cloud")
    show_video = os.getenv("HUMALIEN_SHOW_VIDEO", "0") == "1"
    greet_on_sight = os.getenv("HUMALIEN_GREET_ON_SIGHT", "1") == "1"
    persona_file = os.getenv("HUMALIEN_PERSONA")

    if not api_key:
        raise RuntimeError(f"OPENAI_API_KEY was not found in {ENV_FILE}")

    store = PeopleStore(database)
    eyes = Eyes(
        Perception(store),
        camera=int(camera) if camera.isdigit() else camera,
        show_video=show_video,
    )
    describer = OllamaDescriber(model=vision_model)

    log(f"Knows {len(store.people())} people")
    log(f"Connecting to Pi at {pi_url}")

    try:
        async with websocket_connect(pi_url, max_size=None) as pi_websocket:
            log("Connected to Pi")

            playback = PacedPlayback(pi_websocket)
            gate = build_mic_gate(gate_name, playback)
            tools = RobotTools(eyes, store, describer)
            state = ConversationState()

            log(f"Microphone gate: {gate.name}")
            log(f"Connecting to OpenAI Realtime using {model}")

            async with RealtimeClient(
                api_key=api_key,
                model=model,
                voice=voice,
                eagerness=eagerness,
                noise_reduction=noise_reduction,
                transcription_model=transcription_model,
                tools=TOOL_DEFINITIONS,
                persona=load_persona(persona_file),
            ) as realtime:
                log("Connected to OpenAI Realtime")

                tasks = {
                    asyncio.create_task(
                        pi_to_realtime(pi_websocket, realtime, gate)
                    ),
                    asyncio.create_task(
                        realtime_to_pi(realtime, playback, tools, state)
                    ),
                    asyncio.create_task(playback.run()),
                    asyncio.create_task(eyes.run()),
                }

                if greet_on_sight:
                    tasks.add(
                        asyncio.create_task(
                            watch_the_room(eyes, realtime, playback, store, state)
                        )
                    )
                else:
                    log("Speaking on sight is off - Humalien waits to be spoken to")

                done, pending = await asyncio.wait(
                    tasks,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in pending:
                    task.cancel()

                await asyncio.gather(*pending, return_exceptions=True)

                for task in done:
                    task.result()

    finally:
        store.close()


def main() -> None:
    try:
        asyncio.run(run_voice_core())
    except KeyboardInterrupt:
        log("Stopped")


if __name__ == "__main__":
    main()
