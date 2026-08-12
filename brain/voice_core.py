import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from websockets.asyncio.client import connect as websocket_connect

from audio_adapter import ModelToPiAudio, PiToModelAudio
from realtime_client import RealtimeClient


ENV_FILE = Path(__file__).resolve().parent / ".env"


def log(message: str) -> None:
    print(f"[VOICE CORE] {message}", flush=True)


async def pi_to_realtime(
    pi_websocket,
    realtime: RealtimeClient,
) -> None:
    adapter = PiToModelAudio()

    async for message in pi_websocket:
        if isinstance(message, bytes):
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
    pi_websocket,
) -> None:
    adapter = ModelToPiAudio()
    speaking = False

    async for event in realtime.receive_events():
        event_type = event.get("type", "unknown")

        if event_type == "session.updated":
            log("Realtime session ready")

        elif event_type == "input_audio_buffer.speech_started":
            log("User speech started")

        elif event_type == "input_audio_buffer.speech_stopped":
            log("User speech stopped")

        elif event_type == "response.created":
            log("Humalien is thinking")

        elif event_type == "response.output_audio.delta":
            if not speaking:
                speaking = True
                log("Humalien started speaking")
                # Future: send mouth.speaking = true to the Pi.

            model_audio = realtime.decode_audio_delta(event)

            if model_audio:
                pi_audio = adapter.convert(model_audio)

                if pi_audio:
                    await pi_websocket.send(pi_audio)

        elif event_type == "response.output_audio.done":
            # Flush the final samples held inside the streaming resampler.
            remaining_audio = adapter.convert(b"", final=True)

            if remaining_audio:
                await pi_websocket.send(remaining_audio)

            adapter = ModelToPiAudio()

            if speaking:
                speaking = False
                log("Humalien stopped speaking")
                # Future: send mouth.speaking = false to the Pi.

        elif event_type == "response.output_audio_transcript.done":
            transcript = event.get("transcript")

            if transcript:
                log(f'Humalien said: "{transcript}"')

        elif event_type == "error":
            formatted_error = json.dumps(event, indent=2)
            raise RuntimeError(
                f"Realtime API error:\n{formatted_error}"
            )


async def run_voice_core() -> None:
    load_dotenv(ENV_FILE)

    api_key = os.getenv("OPENAI_API_KEY")
    pi_url = os.getenv(
        "HUMALIEN_PI_URL",
        "ws://10.0.0.83:8765",
    )
    model = os.getenv(
        "OPENAI_REALTIME_MODEL",
        "gpt-realtime-2.1",
    )
    voice = os.getenv(
        "OPENAI_REALTIME_VOICE",
        "marin",
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
        log(f"Connecting to OpenAI Realtime using {model}")

        async with RealtimeClient(
            api_key=api_key,
            model=model,
            voice=voice,
        ) as realtime:
            log("Connected to OpenAI Realtime")

            tasks = {
                asyncio.create_task(
                    pi_to_realtime(pi_websocket, realtime)
                ),
                asyncio.create_task(
                    realtime_to_pi(realtime, pi_websocket)
                ),
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