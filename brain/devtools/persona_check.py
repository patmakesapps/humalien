"""Prove whether the persona reaches the session, or is silently dropped.

session.update is accepted or rejected as one unit, so a bad tool schema
takes the instructions down with it and the robot answers as a stock
assistant. This connects exactly the way voice_core does - same persona,
same tools - and prints what the server echoes back, which is the only
account of the session that is not our own guess.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from realtime_client import RealtimeClient, load_persona, FALLBACK_PERSONA
from robot_tools import tools

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


async def main():
    load_dotenv(ENV_FILE, override=True)

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime-2.1")
    voice = os.getenv("OPENAI_REALTIME_VOICE", "marin")

    if not api_key:
        raise RuntimeError(f"OPENAI_API_KEY was not found in {ENV_FILE}")

    sent = load_persona(os.getenv("HUMALIEN_PERSONA"))
    definitions = tools.definitions()

    print("--- WHAT WE ARE SENDING ---")
    print(f"model        : {model}")
    print(f"persona chars: {len(sent)}")
    print(f"is fallback  : {sent == FALLBACK_PERSONA}")
    print(f"first line   : {sent.splitlines()[0][:70]}")
    print(f"tools        : {len(definitions)}")
    print()

    async with RealtimeClient(
        api_key=api_key,
        model=model,
        voice=voice,
        tools=definitions,
        persona=sent,
    ) as client:
        async for event in client.receive_events():
            event_type = event.get("type", "unknown")

            if event_type == "error":
                print("--- SERVER REJECTED THE SESSION ---")
                print(json.dumps(event, indent=2))
                print()
                print("VERDICT: persona DROPPED - session.update errored.")
                return 1

            if event_type == "session.updated":
                session = event.get("session") or {}
                got = session.get("instructions")

                print("--- WHAT THE SERVER HOLDS ---")
                print(f"instructions present: {got is not None}")
                print(f"instructions chars  : {len(got) if got else 0}")
                print(f"tools accepted      : {len(session.get('tools') or [])}")

                if got:
                    print(f"first line          : {got.splitlines()[0][:70]}")
                print()

                if got == sent:
                    print("VERDICT: persona ARRIVED intact.")
                    return 0

                print("VERDICT: persona DID NOT arrive as sent.")
                return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
