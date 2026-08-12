import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from websockets.asyncio.client import connect as websocket_connect

from audio_adapter import ModelToPiAudio, PiToModelAudio
from mic_gate import HALF_DUPLEX, build_mic_gate
from playback import PacedPlayback
from realtime_client import RealtimeClient


ENV_FILE = Path(__file__).resolve().parent / ".env"


def log(message: str) -> None:
    print(f"[VOICE CORE] {message}", flush=True)


async def pi_to_realtime(
    pi_websocket,
    realtime: RealtimeClient,
    gate,
) -> None:
    adapter = PiToModelAudio()
    listening = True

    async for message in pi_websocket:
        if isinstance(message, bytes):
            if not gate.is_open:
                if listening:
                    listening = False
                    log("Microphone closed — Humalien is speaking")

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


async def realtime_to_pi(
    realtime: RealtimeClient,
    playback: PacedPlayback,
) -> None:
    adapter = ModelToPiAudio()
    answering = False
    response_active = False

    async for event in realtime.receive_events():
        event_type = event.get("type", "unknown")

        if event_type == "session.updated":
            log("Realtime session ready")

        elif event_type == "input_audio_buffer.speech_started":
            log("User speech started")

            if playback.is_speaking:
                log("Interrupted — dropping queued speech")

                playback.clear()
                adapter = ModelToPiAudio()
                answering = False

                if response_active:
                    await realtime.cancel_response()

        elif event_type == "input_audio_buffer.speech_stopped":
            log("User speech stopped")

        elif event_type == "conversation.item.input_audio_transcription.completed":
            transcript = event.get("transcript")

            if transcript:
                log(f'User said: "{transcript.strip()}"')

        elif event_type == "response.created":
            response_active = True
            log("Humalien is thinking")

        elif event_type == "response.done":
            response_active = False

        elif event_type == "response.output_audio.delta":
            if not answering:
                answering = True
                log("Humalien started answering")
                # Future: send mouth.speaking = true to the Pi.

            model_audio = realtime.decode_audio_delta(event)

            if model_audio:
                playback.push(adapter.convert(model_audio))

        elif event_type == "response.output_audio.done":
            # Flush the final samples held inside the streaming resampler.
            playback.push(adapter.convert(b"", final=True))

            adapter = ModelToPiAudio()

            if answering:
                answering = False
                log("Humalien finished answering")
                # Future: send mouth.speaking = false to the Pi.

        elif event_type == "response.output_audio_transcript.done":
            transcript = event.get("transcript")

            if transcript:
                log(f'Humalien said: "{transcript.strip()}"')

        elif event_type == "error":
            # Logged rather than raised: a stray cancellation or an
            # unsupported field should not take the whole robot down.
            log(f"Realtime API error:\n{json.dumps(event, indent=2)}")


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

    if not api_key:
        raise RuntimeError(
            f"OPENAI_API_KEY was not found in {ENV_FILE}"
        )

    log(f"Connecting to Pi at {pi_url}")

    async with websocket_connect(
        pi_url,
        max_size=None,
    ) as pi_websocket:
        log("Connected to Pi")

        playback = PacedPlayback(pi_websocket)
        gate = build_mic_gate(gate_name, playback)

        log(f"Microphone gate: {gate.name}")
        log(f"Connecting to OpenAI Realtime using {model}")

        async with RealtimeClient(
            api_key=api_key,
            model=model,
            voice=voice,
            eagerness=eagerness,
            noise_reduction=noise_reduction,
            transcription_model=transcription_model,
        ) as realtime:
            log("Connected to OpenAI Realtime")

            tasks = {
                asyncio.create_task(
                    pi_to_realtime(pi_websocket, realtime, gate)
                ),
                asyncio.create_task(
                    realtime_to_pi(realtime, playback)
                ),
                asyncio.create_task(playback.run()),
            }

            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

            await asyncio.gather(
                *pending,
                return_exceptions=True,
            )

            for task in done:
                task.result()


def main() -> None:
    try:
        asyncio.run(run_voice_core())
    except KeyboardInterrupt:
        log("Stopped")


if __name__ == "__main__":
    main()
