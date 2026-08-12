import asyncio
import json
import subprocess
from datetime import datetime

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed


HOST = "0.0.0.0"
PORT = 8765

ALSA_DEVICE = "hw:2,0"
SAMPLE_RATE = 48000
CHANNELS = 2
FORMAT = "S16_LE"
CHUNK_SIZE = 3840

# Keep aplay's own buffer short. The brain paces audio to us in real time,
# so a deep buffer here would only delay interruptions. Microseconds.
BUFFER_TIME = 80_000
PERIOD_TIME = 20_000


def log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def show_listening():
    log(f"NODE LISTENING — waiting for brain on ws://{HOST}:{PORT}")


def start_microphone():
    return subprocess.Popen(
        [
            "arecord",
            "-D", ALSA_DEVICE,
            "-t", "raw",
            "-f", FORMAT,
            "-r", str(SAMPLE_RATE),
            "-c", str(CHANNELS),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
    )


def start_speaker():
    return subprocess.Popen(
        [
            "aplay",
            "-D", ALSA_DEVICE,
            "-t", "raw",
            "-f", FORMAT,
            "-r", str(SAMPLE_RATE),
            "-c", str(CHANNELS),
            "--buffer-time", str(BUFFER_TIME),
            "--period-time", str(PERIOD_TIME),
        ],
        stdin=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
    )


async def microphone_to_brain(websocket, microphone):
    while True:
        chunk = await asyncio.to_thread(
            microphone.stdout.read,
            CHUNK_SIZE,
        )

        if not chunk:
            return

        await websocket.send(chunk)


async def brain_to_speaker(websocket, speaker):
    async for message in websocket:
        if isinstance(message, bytes):
            await asyncio.to_thread(
                speaker.stdin.write,
                message,
            )

            await asyncio.to_thread(
                speaker.stdin.flush,
            )


async def stop_process(process):
    if process.poll() is not None:
        return

    process.terminate()

    try:
        await asyncio.wait_for(
            asyncio.to_thread(process.wait),
            timeout=2,
        )

    except asyncio.TimeoutError:
        process.kill()
        await asyncio.to_thread(process.wait)


async def send_node_ready(websocket):
    message = {
        "type": "node_status",
        "state": "ready",
        "node": "humalien-pi",
        "audio": {
            "device": ALSA_DEVICE,
            "sample_rate": SAMPLE_RATE,
            "channels": CHANNELS,
            "format": FORMAT,
        },
    }

    await websocket.send(json.dumps(message))


async def handle_connection(websocket):
    remote = websocket.remote_address

    log("=" * 60)
    log(f"BRAIN CONNECTED — {remote}")

    microphone = None
    speaker = None

    try:
        # Tell the brain that the hardware node is alive and ready.
        await send_node_ready(websocket)

        log("Sent NODE READY signal to brain")

        microphone = start_microphone()
        speaker = start_speaker()

        log("Microphone ONLINE")
        log("Speaker ONLINE")
        log("AUDIO LINK ACTIVE")

        mic_task = asyncio.create_task(
            microphone_to_brain(websocket, microphone)
        )

        speaker_task = asyncio.create_task(
            brain_to_speaker(websocket, speaker)
        )

        done, pending = await asyncio.wait(
            {mic_task, speaker_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

        await asyncio.gather(
            *pending,
            return_exceptions=True,
        )

        for task in done:
            try:
                task.result()

            except ConnectionClosed:
                pass

    except ConnectionClosed:
        pass

    except Exception as exc:
        log(f"CONNECTION ERROR — {exc}")

    finally:
        if microphone is not None:
            await stop_process(microphone)

        if speaker is not None:
            await stop_process(speaker)

        log(f"BRAIN DISCONNECTED — {remote}")
        log("Audio hardware released")
        log("=" * 60)

        # Server never stopped.
        # Explicitly show that we're ready for another brain connection.
        show_listening()


async def main():
    log("HUMALIEN HARDWARE NODE STARTING")
    log(
        f"Audio: {SAMPLE_RATE} Hz / "
        f"{CHANNELS} ch / {FORMAT} / {ALSA_DEVICE}"
    )

    async with serve(
        handle_connection,
        HOST,
        PORT,
        max_size=None,
    ):
        show_listening()

        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())