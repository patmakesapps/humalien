import asyncio
import functools
import json
import subprocess
from datetime import datetime

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

from humalien_node.arms import ARM_AXES, Arms, HEAD_AXES, Pca9685Driver
from humalien_node.pixels import Pixels, Pi5NeoPixelWrite


# Bind every interface, not just IPv4. The brain and the node have landed
# on different DHCP scopes off the same access point more than once, and
# IPv6 still reaches across that when 0.0.0.0 cannot. None binds both
# families.
HOST = None
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

# One second of audio in the wire format above. Byte counts mean nothing on
# their own; seconds of speech can be compared against what was said.
BYTES_PER_SECOND = SAMPLE_RATE * CHANNELS * 2

# How long to spend bringing the head home before releasing it anyway. Long
# enough to cross the whole nod range at the gentle rate humalien_node.arms
# uses, short enough that a jammed axis cannot hold the server open.
PARK_TIMEOUT = 6.0


def log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def show_listening():
    where = HOST if HOST is not None else "*"
    log(f"NODE LISTENING — waiting for brain on ws://{where}:{PORT}")


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
        stderr=subprocess.PIPE,
        bufsize=0,
    )


async def report_errors(process, name):
    """Log what ALSA says instead of throwing it away.

    aplay announces every buffer underrun on stderr. Sending that to
    DEVNULL meant a starved speaker and a healthy one looked identical
    from here, which cost an evening of looking at the wrong end of the
    link.
    """

    while True:
        line = await asyncio.to_thread(process.stderr.readline)

        if not line:
            return

        text = line.decode("utf-8", "replace").strip()

        if text:
            log(f"{name}: {text}")


async def microphone_to_brain(websocket, microphone, counts):
    while True:
        chunk = await asyncio.to_thread(
            microphone.stdout.read,
            CHUNK_SIZE,
        )

        if not chunk:
            return

        counts["mic"] += len(chunk)

        await websocket.send(chunk)


def apply_control(arms, message, pixels=None):
    """Act on one text frame from the brain.

    Audio is bytes and motion is text, on one socket, because the three have
    to stay in step: a gesture or an eye colour that arrived on a second
    connection would drift against the speech it belongs to.
    """

    try:
        event = json.loads(message)
    except (ValueError, TypeError):
        log(f"Ignoring unreadable control frame: {message[:80]!r}")
        return

    kind = event.get("type")

    if kind == "pose":
        if arms is None:
            return

        for axis, degrees in event.items():
            if axis == "type":
                continue

            if not arms.set_target(axis, degrees):
                log(f"Ignoring unknown axis {axis!r}")

    elif kind == "eyes":
        # The brain sends a mood, not pixels. humalien_node.pixels says why.
        if pixels is None:
            return

        if not pixels.set(
            mood=event.get("mood"),
            level=event.get("level"),
            brightness=event.get("brightness"),
        ):
            log(f"Ignoring unknown eye mood {event.get('mood')!r}")

    elif kind == "limp":
        if arms is not None:
            arms.limp()
            log("Arms limp on request")

    else:
        log(f"Ignoring control frame of type {kind!r}")


async def brain_to_speaker(websocket, speaker, counts, arms=None, pixels=None):
    # Report roughly once per second of audio, so the log shows whether
    # speech arrives as a steady stream or in starved bursts.
    reported = 0

    async for message in websocket:
        if isinstance(message, str):
            apply_control(arms, message, pixels)
            continue

        if isinstance(message, bytes):
            await asyncio.to_thread(
                speaker.stdin.write,
                message,
            )

            await asyncio.to_thread(
                speaker.stdin.flush,
            )

            counts["speaker"] += len(message)

            if counts["speaker"] - reported >= BYTES_PER_SECOND:
                reported = counts["speaker"]
                log(
                    f"Speaker fed {counts['speaker'] / BYTES_PER_SECOND:.1f}s "
                    f"of audio ({counts['speaker']} bytes)"
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


async def handle_connection(websocket, arms=None, pixels=None):
    remote = websocket.remote_address

    log("=" * 60)
    log(f"BRAIN CONNECTED — {remote}")

    microphone = None
    speaker = None
    errors_task = None
    motion_task = None
    pixel_task = None
    counts = {"mic": 0, "speaker": 0}

    try:
        # Tell the brain that the hardware node is alive and ready.
        await send_node_ready(websocket)

        log("Sent NODE READY signal to brain")

        microphone = start_microphone()
        speaker = start_speaker()

        log("Microphone ONLINE")
        log("Speaker ONLINE")
        log("AUDIO LINK ACTIVE")

        errors_task = asyncio.create_task(
            report_errors(speaker, "aplay")
        )

        if arms is not None:
            # Limp until a brain is actually here to drive them. The arms and
            # head come up at rest rather than wherever they were left.
            arms.engage()
            motion_task = asyncio.create_task(arms.run())

            log("Arms and head engaged at rest")

        if pixels is not None:
            # The eyes come up alive before the brain says anything, so a
            # booting robot looks awake rather than broken.
            pixels.set(mood="idle", level=0.0)
            pixel_task = asyncio.create_task(pixels.run())

            log("Eyes on")

        mic_task = asyncio.create_task(
            microphone_to_brain(websocket, microphone, counts)
        )

        speaker_task = asyncio.create_task(
            brain_to_speaker(websocket, speaker, counts, arms, pixels)
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
        if errors_task is not None:
            errors_task.cancel()

        if motion_task is not None:
            motion_task.cancel()

        if pixel_task is not None:
            pixel_task.cancel()

        if arms is not None:
            # The arms can simply stop. No pulse holds nothing and gets
            # nothing hot, and an unpowered arm hangs where it was.
            arms.limp(ARM_AXES)

            # The head cannot. Releasing it wherever it happened to be means
            # the next engage jumps it there and back, and the eye wiring
            # runs through the nod joint. Bring it home under acceleration
            # control first, then let go - but never wait forever for a
            # mechanism that may be jammed.
            if await arms.park(HEAD_AXES, timeout=PARK_TIMEOUT):
                log("Head parked at neutral")
            else:
                log("Head did not reach neutral in time - releasing anyway")

            arms.limp()
            log("Arms and head limp")

        if pixels is not None:
            # NeoPixels latch: stopping the render loop would leave the last
            # frame lit forever. A robot with no brain must not sit there
            # staring at an empty room.
            pixels.clear()
            log("Eyes dark")

        log(
            f"Session totals — mic {counts['mic'] / BYTES_PER_SECOND:.1f}s, "
            f"speaker {counts['speaker'] / BYTES_PER_SECOND:.1f}s"
        )

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

    arms = None
    pixels = None

    try:
        arms = Arms(Pca9685Driver())
        log("Servos ready: arms on 0/3, neck on 1, nod on 2")

    except Exception as error:
        # Audio is the point of this node; motion is an addition to it. A
        # missing servo board must not cost the robot its voice.
        log(f"No servo board, running without arms or head - {error}")

    try:
        pixels = Pixels(Pi5NeoPixelWrite())
        log("Eyes ready on GPIO13, 24 pixels")

    except Exception as error:
        log(f"No NeoPixels, running blind-faced - {error}")

    async with serve(
        functools.partial(handle_connection, arms=arms, pixels=pixels),
        HOST,
        PORT,
        max_size=None,
    ):
        show_listening()

        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())