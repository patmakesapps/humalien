"""Start Humalien and keep it running.

This is the entry point the robot boots into. It checks that the things
Humalien needs are actually there, says plainly what is missing, and then
supervises the conversation loop - reconnecting rather than exiting when a
network blip takes out the Pi or the Realtime session.
"""

import asyncio
import os
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv

BRAIN = Path(__file__).resolve().parent
ENV_FILE = BRAIN / ".env"
MODEL_DIR = BRAIN / "models"

REQUIRED_MODELS = [
    "face_detection_yunet_2023mar.onnx",
    "face_recognition_sface_2021dec.onnx",
]

# Reconnect delays. A robot in a house should ride out a router reboot
# without anybody having to go and restart it.
FIRST_RETRY = 1.0
MAX_RETRY = 30.0
STABLE_AFTER = 60.0


def log(message: str) -> None:
    print(f"[HUMALIEN] {message}", flush=True)


def preflight() -> tuple[list[str], list[str]]:
    """Check what Humalien needs. Returns (fatal, degraded)."""

    # override=True: .env is the configuration, so it must win over stale
    # OPENAI_API_KEY values inherited from the shell.
    load_dotenv(ENV_FILE, override=True)

    fatal, degraded = [], []

    if not ENV_FILE.exists():
        fatal.append(f"No .env file. Copy .env.example to {ENV_FILE}")

    if not os.getenv("OPENAI_API_KEY"):
        fatal.append("OPENAI_API_KEY is not set. Humalien cannot talk.")

    missing = [name for name in REQUIRED_MODELS if not (MODEL_DIR / name).exists()]

    if missing:
        degraded.append(
            f"Face models missing ({', '.join(missing)}). "
            "Run: python devtools/fetch_models.py - Humalien will be blind."
        )

    return fatal, degraded


async def supervise() -> None:
    """Run the conversation loop, restarting it when it falls over."""

    # Imported here so a missing dependency surfaces after preflight has had
    # its say, rather than as an import error nobody can interpret.
    from voice_core import run_voice_core

    delay = FIRST_RETRY

    while True:
        started = asyncio.get_running_loop().time()

        try:
            await run_voice_core()
            log("Conversation loop ended")

        except asyncio.CancelledError:
            raise

        except Exception as error:
            log(f"{type(error).__name__}: {error}")

        # A run that lasted a while was healthy, so start backing off afresh
        # rather than punishing it for one late failure.
        if asyncio.get_running_loop().time() - started > STABLE_AFTER:
            delay = FIRST_RETRY

        log(f"Restarting in {delay:.0f}s")
        await asyncio.sleep(delay)

        delay = min(delay * 2, MAX_RETRY)


def install_signal_handlers(task: asyncio.Task) -> None:
    """Let systemd stop Humalien cleanly with SIGTERM."""

    loop = asyncio.get_running_loop()

    for name in ("SIGINT", "SIGTERM"):
        signum = getattr(signal, name, None)

        if signum is None:
            continue

        try:
            loop.add_signal_handler(signum, task.cancel)
        except NotImplementedError:
            # Windows asyncio has no signal handler support. Ctrl+C still
            # raises KeyboardInterrupt, which is enough for desktop testing.
            pass


async def main_async() -> int:
    fatal, degraded = preflight()

    for problem in degraded:
        log(f"WARNING: {problem}")

    if fatal:
        for problem in fatal:
            log(f"ERROR: {problem}")

        return 1

    log("Humalien starting")

    task = asyncio.ensure_future(supervise())
    install_signal_handlers(task)

    try:
        await task
    except asyncio.CancelledError:
        log("Stopped")

    return 0


def main() -> None:
    try:
        sys.exit(asyncio.run(main_async()))
    except KeyboardInterrupt:
        log("Stopped")


if __name__ == "__main__":
    main()
