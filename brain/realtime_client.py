import base64
import json
from collections.abc import AsyncIterator

from websockets.asyncio.client import connect as websocket_connect


INSTRUCTIONS = (
    "You are Humalien, a curious and friendly cyborg. "
    "Speak as a friend and keep responses brief when possible."
)


class RealtimeClient:
    """Low-level connection to an OpenAI Realtime speech session."""

    def __init__(
        self,
        api_key: str,
        model: str,
        voice: str,
        *,
        eagerness: str = "auto",
        noise_reduction: str = "far_field",
        transcription_model: str = "gpt-4o-mini-transcribe",
    ):
        if not api_key:
            raise ValueError("An OpenAI API key is required")

        self.api_key = api_key
        self.model = model
        self.voice = voice
        self.eagerness = eagerness
        self.noise_reduction = noise_reduction
        self.transcription_model = transcription_model
        self.websocket = None

    def build_audio_input(self) -> dict:
        audio_input = {
            "format": {
                "type": "audio/pcm",
                "rate": 24_000,
            },
            "turn_detection": {
                "type": "semantic_vad",
                "eagerness": self.eagerness,
                # Let the server end our turn and cut its own reply short
                # the moment it hears the user start talking.
                "create_response": True,
                "interrupt_response": True,
            },
        }

        # Both are optional. Blank them in .env if the API rejects them.
        if self.noise_reduction:
            audio_input["noise_reduction"] = {
                "type": self.noise_reduction,
            }

        if self.transcription_model:
            audio_input["transcription"] = {
                "model": self.transcription_model,
            }

        return audio_input

    async def connect(self) -> None:
        url = f"wss://api.openai.com/v1/realtime?model={self.model}"

        self.websocket = await websocket_connect(
            url,
            additional_headers={
                "Authorization": f"Bearer {self.api_key}",
            },
            max_size=None,
        )

        await self.send_event(
            {
                "type": "session.update",
                "session": {
                    "type": "realtime",
                    "model": self.model,
                    "output_modalities": ["audio"],
                    "instructions": INSTRUCTIONS,
                    "audio": {
                        "input": self.build_audio_input(),
                        "output": {
                            "format": {
                                "type": "audio/pcm",
                                "rate": 24_000,
                            },
                            "voice": self.voice,
                        },
                    },
                },
            }
        )

    async def close(self) -> None:
        if self.websocket is not None:
            await self.websocket.close()
            self.websocket = None

    async def send_event(self, event: dict) -> None:
        if self.websocket is None:
            raise RuntimeError("Realtime client is not connected")

        await self.websocket.send(json.dumps(event))

    async def send_audio(self, audio: bytes) -> None:
        encoded_audio = base64.b64encode(audio).decode("ascii")

        await self.send_event(
            {
                "type": "input_audio_buffer.append",
                "audio": encoded_audio,
            }
        )

    async def cancel_response(self) -> None:
        await self.send_event({"type": "response.cancel"})

    async def receive_events(self) -> AsyncIterator[dict]:
        if self.websocket is None:
            raise RuntimeError("Realtime client is not connected")

        async for message in self.websocket:
            yield json.loads(message)

    @staticmethod
    def decode_audio_delta(event: dict) -> bytes | None:
        if event.get("type") != "response.output_audio.delta":
            return None

        delta = event.get("delta")

        if not delta:
            return None

        return base64.b64decode(delta)

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()
