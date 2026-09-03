import asyncio
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from websockets.asyncio.client import connect as websocket_connect

from attention import Attention
from audio_adapter import ModelToPiAudio, PiToModelAudio
from gaze import GazeController, HOLDING, TRACKING
from gestures import Gestures
from playback import BYTES_PER_SECOND as PI_BYTES_PER_SECOND
from conversation import ConversationState
from describe import OllamaDescriber
from eyes import Eyes
from mic_gate import HALF_DUPLEX, build_mic_gate
from mood import Mood
from people import PeopleStore
from perception import Perception
from playback import PacedPlayback, level as loudness_of
from realtime_client import RealtimeClient, load_persona
from robot_tools import Robot, tools


ENV_FILE = Path(__file__).resolve().parent / ".env"
DEFAULT_DB = Path(__file__).resolve().parent / "humalien.db"

# How long somebody must be out of view before walking back in counts as an
# arrival worth greeting again.
FORGET_PRESENCE_AFTER = 60.0

# How long a stranger must be genuinely gone before Humalien offers to meet
# them again. Detection drops out for a frame all the time; without this,
# a flicker makes it introduce itself over and over.
RE_OFFER_AFTER = 20.0

# How often the head reconsiders where to look. Faster than recognition runs,
# because the smoothing wants a steady clock more than it wants new data.
TRACK_INTERVAL = 0.1


def log(message: str) -> None:
    print(f"[VOICE CORE] {message}", flush=True)


def looks_like_image_trouble(event: dict) -> bool:
    """Whether an error event is the session refusing a picture.

    Images are sent fire-and-forget, so a rejection or a rate limit only
    surfaces here, well after the tool returned. Matching on the message is
    crude, but the alternative is losing every look for the rest of the
    session to a failure nothing is watching for.
    """

    error = event.get("error") or {}
    text = f"{error.get('code', '')} {error.get('message', '')}".lower()

    return any(
        word in text
        for word in ("image", "rate limit", "rate_limit", "too large", "modality")
    )


async def pi_to_realtime(
    pi_websocket,
    realtime: RealtimeClient,
    gate,
    mood: Mood | None = None,
) -> None:
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

            # The eyes answer the room's voice while it is listening. Taken
            # from the raw microphone rather than the resampled copy, so a
            # converter that drops a chunk cannot flatten the reaction.
            if mood is not None:
                mood.hearing(loudness_of(message))

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
    robot: Robot,
    call_id: str,
    name: str,
    raw_arguments: str,
) -> None:
    result = await tools.execute(robot, name, raw_arguments)

    await realtime.send_function_output(call_id, result)
    await realtime.create_response()


async def realtime_to_pi(
    realtime: RealtimeClient,
    playback: PacedPlayback,
    robot: Robot,
    state: ConversationState,
    mood: Mood | None = None,
) -> None:
    adapter = ModelToPiAudio()
    answering = False

    async for event in realtime.receive_events():
        event_type = event.get("type", "unknown")

        if event_type == "session.updated":
            log("Realtime session ready")

        elif event_type == "input_audio_buffer.speech_started":
            log("User speech started")

            # Remember when, so looking can use the frame from this moment
            # rather than whatever the camera sees once the tool call lands.
            state.speech_started_at = time.monotonic()
            state.speech_stopped_at = None

            if playback.is_speaking:
                dropped = playback.clear()

                log(
                    "Interrupted - dropping "
                    f"{dropped / PI_BYTES_PER_SECOND:.1f}s of queued speech"
                )
                adapter = ModelToPiAudio()
                answering = False

                if state.response_active:
                    await realtime.cancel_response()

        elif event_type == "input_audio_buffer.speech_stopped":
            log("User speech stopped")

            state.speech_stopped_at = time.monotonic()

        elif event_type == "conversation.item.input_audio_transcription.completed":
            transcript = event.get("transcript")

            if transcript:
                log(f'User said: "{transcript.strip()}"')

        elif event_type == "response.created":
            state.response_active = True

            # The eyes go to work the moment the model does. This is the gap
            # people read as the robot having heard them, and leaving it
            # blank is what makes a slow answer feel like a broken one.
            if mood is not None:
                mood.thinking(True)

        elif event_type == "response.done":
            state.response_active = False

            if mood is not None:
                mood.thinking(False)

        elif event_type == "response.function_call_arguments.done":
            # Deliberately not awaited. Looking takes several seconds, and
            # blocking here would stall the audio flowing to the Pi.
            asyncio.create_task(
                run_tool_call(
                    realtime,
                    robot,
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

            log(f"Released {playback.sent_seconds:.1f}s of audio to the Pi")

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

            # A picture the session would not take surfaces here, long after
            # the tool returned. That turn is already lost; everything after
            # it goes to Ollama instead.
            if looks_like_image_trouble(event):
                robot.fall_back_to_ollama("the session rejected an image")


async def follow_faces(
    eyes: Eyes,
    gestures: Gestures | None,
    mood: Mood | None,
) -> None:
    """Point the head at whoever is being talked to.

    Three layers, and each exists because the one below it is not enough:

      attention.Attention  picks WHICH face, and commits to it. Two people at
                           a desk measure within a few percent of each other,
                           so "the biggest face" alternates several times a
                           second and the neck would hunt between them.
      gaze.GazeController  smooths the chosen face and decides what a lost
                           detection means - hold briefly, then give up.
      gestures.Gestures    turns that into degrees, slowly, and mixes it with
                           the speech motion and the idle drift.

    Nothing here talks to a servo. The head can be wrong about who it is
    looking at; it cannot be wrong about how far it may turn.
    """

    attention = Attention()
    controller = GazeController()
    had_somebody = False

    while True:
        await asyncio.sleep(TRACK_INTERVAL)

        frame = eyes.frame

        if frame is None:
            continue

        height, width = frame.shape[:2]
        now = time.monotonic()

        attended = attention.update(
            [sighting.detection.box for sighting in eyes.sightings],
            frame_width=width,
            now=now,
        )

        target = controller.update(
            attended.face if attended is not None else None,
            frame_width=width,
            frame_height=height,
            now=now,
        )

        if gestures is not None:
            if target.state in (TRACKING, HOLDING):
                gestures.look_at(target.x, target.y)
            else:
                # Recentering or idle. Let go rather than pinning the head
                # to dead ahead - the drift in Gestures is better company.
                gestures.stop_looking()

        if mood is not None and attended is not None:
            mood.seen(new=not had_somebody)

        had_somebody = attended is not None


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
    load_dotenv(ENV_FILE, override=True)

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
    vision = os.getenv("HUMALIEN_VISION", "realtime")
    show_video = os.getenv("HUMALIEN_SHOW_VIDEO", "0") == "1"
    greet_on_sight = os.getenv("HUMALIEN_GREET_ON_SIGHT", "1") == "1"
    gesturing = os.getenv("HUMALIEN_GESTURES", "1") == "1"
    expressive = os.getenv("HUMALIEN_EYES", "1") == "1"
    tracking = os.getenv("HUMALIEN_TRACK_FACES", "1") == "1"
    persona_file = os.getenv("HUMALIEN_PERSONA")

    # Overrides the node's own default. Set it once from the bench, in
    # brain/.env, rather than editing the Pi.
    eye_brightness = os.getenv("HUMALIEN_EYE_BRIGHTNESS")
    eye_brightness = float(eye_brightness) if eye_brightness else None

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

            gestures = Gestures(pi_websocket, log=log) if gesturing else None
            mood = (
                Mood(pi_websocket, log=log, brightness=eye_brightness)
                if expressive
                else None
            )

            def on_level(level: float) -> None:
                """One playback envelope, two things driving off it.

                Both the body and the eyes have to move with the speech that
                is actually audible, and this is the only moment the audio
                and the wall clock agree. See PacedPlayback.is_speaking.
                """

                if gestures is not None:
                    gestures.feed(level)

                if mood is not None:
                    mood.speaking(level)

            playback = PacedPlayback(pi_websocket, on_level=on_level)
            gate = build_mic_gate(gate_name, playback)
            state = ConversationState()
            robot = Robot(
                eyes=eyes,
                store=store,
                describer=describer,
                state=state,
                mood=mood,
                vision=vision,
            )

            log(f"Microphone gate: {gate.name}")
            log(f"Connecting to OpenAI Realtime using {model}")

            async with RealtimeClient(
                api_key=api_key,
                model=model,
                voice=voice,
                eagerness=eagerness,
                noise_reduction=noise_reduction,
                transcription_model=transcription_model,
                tools=tools.definitions(),
                persona=load_persona(persona_file),
            ) as realtime:
                log("Connected to OpenAI Realtime")

                # The look tool hands frames straight to the session, so it
                # needs the connection. Set here rather than at construction
                # because the session opens after the robot exists.
                robot.realtime = realtime

                log(f"Vision: {robot.vision}")

                tasks = {
                    asyncio.create_task(
                        pi_to_realtime(pi_websocket, realtime, gate, mood)
                    ),
                    asyncio.create_task(
                        realtime_to_pi(realtime, playback, robot, state, mood)
                    ),
                    asyncio.create_task(playback.run()),
                    asyncio.create_task(eyes.run()),
                }

                if gestures:
                    tasks.add(asyncio.create_task(gestures.run()))
                else:
                    log("Gestures are off - the arms and head will not move")

                if mood:
                    tasks.add(asyncio.create_task(mood.run()))
                else:
                    log("Eye moods are off - the eyes will sit at idle")

                if tracking:
                    tasks.add(
                        asyncio.create_task(follow_faces(eyes, gestures, mood))
                    )
                else:
                    log("Face tracking is off - the head drifts on its own")

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
