import base64
import json
from collections.abc import AsyncIterator
from pathlib import Path

from websockets.asyncio.client import connect as websocket_connect


PERSONA_FILE = Path(__file__).resolve().parent / "persona.md"

# Fallback only. The real character lives in persona.md, so it can be edited
# and swapped without touching code - it is writing, not logic.
FALLBACK_PERSONA = (
    "You are Humalien. You are a person, not an assistant. Speak warmly and "
    "briefly, in one or two sentences, using contractions. Never sound like "
    "an assistant."
)


def load_persona(path: str | Path | None = None) -> str:
    """Read Humalien's character and delivery from disk.

    gpt-realtime has no separate voice or vibe parameter - accent, pacing and
    tone are all steered through these instructions. Keeping them in a text
    file means the vibe can be rewritten without a code change.
    """

    persona = Path(path) if path else PERSONA_FILE

    if not persona.exists():
        return FALLBACK_PERSONA

    return persona.read_text(encoding="utf-8").strip() or FALLBACK_PERSONA




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
        tools: list[dict] | None = None,
        persona: str | None = None,
    ):
        if not api_key:
            raise ValueError("An OpenAI API key is required")

        self.api_key = api_key
        self.model = model
        self.voice = voice
        self.eagerness = eagerness
        self.noise_reduction = noise_reduction
        self.transcription_model = transcription_model
        self.tools = tools or []
        self.persona = persona or load_persona()
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
                    "instructions": self.persona,
                    "tools": self.tools,
                    "tool_choice": "auto",
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

    async def create_response(self) -> None:
        await self.send_event({"type": "response.create"})

    async def send_function_output(self, call_id: str, output: str) -> None:
        await self.send_event(
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": output,
                },
            }
        )

    async def send_image(self, jpeg: bytes, *, item_id: str, caption: str) -> str:
        """Put a picture in front of the model.

        gpt-realtime takes image input directly, so it can look at a frame
        itself rather than reading somebody else's description of it.

        The caption travels in the same item as the picture. Without it the
        model has no way to tell its own eyes from something a person handed
        it, and will talk about "the image you sent me".

        The id is ours so the picture can be taken away again later. Note
        this is fire-and-forget: a rejection or rate limit comes back as an
        `error` event, not as a failure here.
        """

        encoded = base64.b64encode(jpeg).decode("ascii")

        await self.send_event(
            {
                "type": "conversation.item.create",
                "item": {
                    "id": item_id,
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": caption},
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{encoded}",
                        },
                    ],
                },
            }
        )

        return item_id

    async def delete_item(self, item_id: str) -> None:
        """Take something back out of the conversation.

        Used to drop the previous picture when a new one arrives, so at most
        one image is ever being re-sent with each turn.
        """

        await self.send_event(
            {"type": "conversation.item.delete", "item_id": item_id}
        )

    async def send_context(self, text: str) -> None:
        """Tell the model something it did not ask about.

        Used when somebody walks into view. The model cannot call a tool to
        discover that, because it has no reason to suspect anything changed.

        Pushing this without also calling `create_response` is usually what
        you want: the model absorbs it and uses it when the person speaks.
        Forcing a reply immediately leaves nothing in the turn except this
        note, and the model will read it out loud.
        """

        await self.send_event(
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "system",
                    "content": [{"type": "input_text", "text": text}],
                },
            }
        )

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
