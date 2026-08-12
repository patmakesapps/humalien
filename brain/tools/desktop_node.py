import asyncio
import json
import os
from functools import partial
from pathlib import Path

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed


HOST = "127.0.0.1"
PORT = 8765

SAMPLE_RATE = 48_000
DTYPE = "int16"
BLOCK_SIZE = 960

# The wire protocol is always 48 kHz stereo, because that is what the
# Waveshare hat produces and what the brain expects. A laptop microphone is
# usually mono, so the simulator converts locally rather than making the
# brain care which machine it is talking to.
WIRE_CHANNELS = 2

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def log(message: str) -> None:
    print(f"[DESKTOP NODE] {message}", flush=True)


def usable_channels(device: int, *, capture: bool) -> int:
    """How many channels this device actually has, up to stereo."""

    info = sd.query_devices(device)
    key = "max_input_channels" if capture else "max_output_channels"
    available = int(info[key])

    if available < 1:
        direction = "input" if capture else "output"
        raise RuntimeError(
            f"Device {device} ({info['name']}) has no {direction} channels. "
            "Run: python tools/list_audio_devices.py"
        )

    return min(WIRE_CHANNELS, available)


def to_stereo(audio: bytes) -> bytes:
    """Duplicate a mono capture across both wire channels."""

    mono = np.frombuffer(audio, dtype="<i2")
    stereo = np.repeat(mono[:, np.newaxis], WIRE_CHANNELS, axis=1)

    return stereo.astype("<i2", copy=False).tobytes()


def to_mono(audio: bytes) -> bytes:
    """Fold stereo playback down for a mono output device."""

    samples = np.frombuffer(audio, dtype="<i2")
    usable = len(samples) - (len(samples) % WIRE_CHANNELS)
    stereo = samples[:usable].reshape(-1, WIRE_CHANNELS)

    mono = stereo.astype(np.int32).mean(axis=1).clip(-32768, 32767)

    return mono.astype("<i2").tobytes()


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
    output_channels: int,
) -> None:
    async for message in websocket:
        if isinstance(message, bytes):
            if output_channels == 1:
                message = to_mono(message)

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
    input_channels: int,
    output_channels: int,
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

        audio = bytes(indata)

        if input_channels == 1:
            audio = to_stereo(audio)

        loop.call_soon_threadsafe(enqueue_audio, audio)

    log(f"Brain connected: {remote}")

    try:
        with (
            sd.RawInputStream(
                device=input_device,
                samplerate=SAMPLE_RATE,
                channels=input_channels,
                dtype=DTYPE,
                blocksize=BLOCK_SIZE,
                callback=microphone_callback,
            ) as microphone,
            sd.RawOutputStream(
                device=output_device,
                samplerate=SAMPLE_RATE,
                channels=output_channels,
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
                            "channels": WIRE_CHANNELS,
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
                    output_channels,
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

    input_channels = usable_channels(input_device, capture=True)
    output_channels = usable_channels(output_device, capture=False)

    handler = partial(
        handle_connection,
        input_device=input_device,
        output_device=output_device,
        input_channels=input_channels,
        output_channels=output_channels,
    )

    log("Humalien desktop hardware simulator")
    log(f"Input device: {input_device} ({input_channels} ch)")
    log(f"Output device: {output_device} ({output_channels} ch)")

    if input_channels == 1:
        log("Mono microphone - duplicating to stereo for the brain")

    if output_channels == 1:
        log("Mono speaker - folding the brain's stereo down")

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