import asyncio
import json
import os
import sys
from pathlib import Path

# Work whether launched as `python -m tools.x` or `python tools/x.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from realtime_client import RealtimeClient


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


async def main():
    load_dotenv(ENV_FILE)

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime-2.1")
    voice = os.getenv("OPENAI_REALTIME_VOICE", "marin")

    if not api_key:
        raise RuntimeError(
            f"OPENAI_API_KEY was not found in {ENV_FILE}"
        )

    print(f"Connecting to OpenAI Realtime using {model}...")

    async with RealtimeClient(
        api_key=api_key,
        model=model,
        voice=voice,
    ) as client:
        async for event in client.receive_events():
            event_type = event.get("type", "unknown")
            print(f"Received: {event_type}")

            if event_type == "error":
                print(json.dumps(event, indent=2))
                raise RuntimeError("Realtime API returned an error")

            if event_type == "session.updated":
                print("Humalien Realtime connection is ready.")
                return


if __name__ == "__main__":
    asyncio.run(main())