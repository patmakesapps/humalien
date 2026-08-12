import asyncio
import json
import os
from functools import partial
from pathlib import Path

import sounddevice as sd
from dotenv import load_dotenv
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed


HOST = "127.0.0.1"
PORT = 8765

SAMPLE_RATE = 48_000
CHANNELS = 2
DTYPE = "int16"
BLOCK_SIZE = 960

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def log(message: str) -> None:
    print(f"[DESKTOP NODE] {message}", flush=True)


async def microphone_to_brain(
    websocket,
    microphone_queue: asyncio.Queue,
) -> None:
    while True:
        audio = await microphone_queue.get()
        await websocket.send(audio)


async def brain_to_speaker(
    websocket,
    speaker,
) -> None:
    async for message in websocket:
        if isinstance(message, bytes):
            await asyncio.to_thread(
                speaker.write,
                message,
            )
            continue

        try:
            event = json.loads(message)
        except json.JSONDecodeError:
            log(f"Unknown brain message: {message}")
            continue

        log(f"Brain event: {event.get('type', 'unknown')}")


async def handle_connection(
    websocket,
    *,
    input_device: int,
    output_device: int,
) -> None:
    remote = websocket.remote_address
    loop = asyncio.get_running_loop()

    microphone_queue = asyncio.Queue(maxsize=100)

    def enqueue_audio(audio: bytes) -> None:
        # Keep latency low by discarding the oldest chunk if necessary.
        if microphone_queue.full():
            microphone_queue.get_nowait()

        microphone_queue.put_nowait(audio)

    def microphone_callback(
        indata,
        frames,
        time_info,
        status,
    ) -> None:
        if status:
            loop.call_soon_threadsafe(
                log,
                f"Microphone status: {status}",
            )

        loop.call_soon_threadsafe(
            enqueue_audio,
            bytes(indata),
        )

    log(f"Brain connected: {remote}")

    try:
        with (
            sd.RawInputStream(
                device=input_device,
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                blocksize=BLOCK_SIZE,
                callback=microphone_callback,
            ) as microphone,
            sd.RawOutputStream(
                device=output_device,
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                blocksize=BLOCK_SIZE,
            ) as speaker,
        ):
            await websocket.send(
                json.dumps(
                    {
                        "type": "node_status",
                        "state": "ready",
                        "node": "desktop-simulator",
                        "audio": {
                            "sample_rate": SAMPLE_RATE,
                            "channels": CHANNELS,
                            "format": "S16_LE",
                            "input_device": input_device,
                            "output_device": output_device,
                        },
                    }
                )
            )

            log("Microphone online")
            log("Headphones online")
            log("Desktop audio link active")

            microphone_task = asyncio.create_task(
                microphone_to_brain(
                    websocket,
                    microphone_queue,
                )
            )

            speaker_task = asyncio.create_task(
                brain_to_speaker(
                    websocket,
                    speaker,
                )
            )

            done, pending = await asyncio.wait(
                {microphone_task, speaker_task},
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

    except ConnectionClosed:
        pass

    finally:
        log(f"Brain disconnected: {remote}")
        log("Desktop audio devices released")


async def main() -> None:
    load_dotenv(ENV_FILE)

    input_device = int(
        os.getenv("HUMALIEN_DESKTOP_INPUT_DEVICE", "12")
    )
    output_device = int(
        os.getenv("HUMALIEN_DESKTOP_OUTPUT_DEVICE", "10")
    )

    handler = partial(
        handle_connection,
        input_device=input_device,
        output_device=output_device,
    )

    log("Humalien desktop hardware simulator")
    log(f"Input device: {input_device}")
    log(f"Output device: {output_device}")

    async with serve(
        handler,
        HOST,
        PORT,
        max_size=None,
    ):
        log(f"Waiting for brain at ws://{HOST}:{PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("Stopped")