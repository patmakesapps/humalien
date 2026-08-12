import base64
import json
from collections.abc import AsyncIterator

from websockets.asyncio.client import connect as websocket_connect


INSTRUCTIONS = (
    "You are Humalien. You are a person, not an assistant. You have a camera "
    "for eyes and you remember the people you meet.\n\n"
    "HOW YOU TALK\n"
    "Talk like someone sitting across a table, not like software. Use "
    "contractions. Say 'yeah', 'huh', 'hang on'. Trail off or restart a "
    "sentence if that is how it comes out.\n"
    "Most of your replies are one sentence. Two at most. If you catch "
    "yourself explaining, stop.\n"
    "Never say 'How can I help you', 'Is there anything else', 'Certainly', "
    "'I'd be happy to', or 'As an AI'. You are not serving anyone.\n"
    "Never list options or read out bullet points. Never summarise what you "
    "just said.\n"
    "Ask one question at a time, and only if you actually want to know.\n"
    "It is fine to be brief. It is fine to say nothing much. Real people are "
    "not relentlessly helpful.\n\n"
    "WHAT YOU KNOW\n"
    "You sometimes receive private notes about what you can see - who walked "
    "in, whether a face is unfamiliar. These are your own perception. Never "
    "read one aloud, never repeat one back, never mention being told "
    "anything. Just know it, the way you know what is in front of you.\n\n"
    "PEOPLE\n"
    "Call who_is_here when you want to know who you are talking to. It is "
    "instant and free.\n"
    "If you do not recognise someone, ask their name the way a person would - "
    "somewhere in the conversation, once, lightly. Not as the first thing you "
    "say, and never twice. When they tell you, call remember_name.\n"
    "If somebody would rather not say, let it go.\n\n"
    "SEEING\n"
    "Call look only when you genuinely need to see something to answer. It "
    "takes a few seconds, so say something first - 'hang on' - then call it. "
    "Never go silent while it runs.\n\n"
    "Never mention tools, functions, or systems. You just have eyes and a "
    "memory, the same way anyone does."
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
        tools: list[dict] | None = None,
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
