"""Hearing your own name while the microphone is shut.

Sleep closes the gate to the Realtime API, not the microphone: the Pi keeps
streaming and the brain keeps receiving. This listens to that leftover audio
locally, so being asleep costs nothing, sends nothing, and wakes instantly.

Deliberately offline. A mute whose only way back is a round trip to somebody
else's server is not much of a mute, and the whole point of sleeping is that
what gets said in the room stops leaving it.

Vosk is optional. Without it the robot still sleeps, and still wakes on the
timeout in voice_core - it just cannot be woken by voice. That degrades to
something usable rather than to a robot that has to be restarted.
"""

import json
import os
from pathlib import Path

from audio_adapter import WAKE_SAMPLE_RATE

# Recognition is constrained to these and nothing else, which is why a small
# model is accurate enough. "[unk]" is required: without somewhere to put
# everything that is not a wake phrase, Vosk forces every noise onto the
# nearest one and the robot wakes up constantly.
WAKE_PHRASES = (
    "tubby",
    "hey tubby",
    "ok tubby",
    "wake up",
    "tubby wake up",
)

GRAMMAR = json.dumps(list(WAKE_PHRASES) + ["[unk]"])

DEFAULT_MODEL_DIR = Path(__file__).resolve().parent / "models" / "vosk"


def log(message: str) -> None:
    print(f"[WAKE] {message}", flush=True)


def heard_wake_word(text: str) -> bool:
    """Whether a decoded phrase counts as somebody calling the robot.

    Substring rather than equality because the decoder emits the grammar's
    words, not its phrases: "hey tubby" comes back as "hey tubby" but also,
    when the first word is clipped by the gate opening, as bare "tubby".
    """

    spoken = " ".join(text.lower().split())

    if not spoken:
        return False

    return any(phrase in spoken for phrase in WAKE_PHRASES)


class WakeWord:
    """An offline listener for the robot's own name.

    Feed it 16 kHz mono PCM16 while asleep. It answers one question.
    """

    def __init__(self, recognizer):
        self.recognizer = recognizer

    def feed(self, audio: bytes) -> bool:
        """Whether this chunk completed a wake phrase.

        Final results only. Partials look tempting - they would save the
        pause after the word - but the decoder revises them as it hears
        more, and it revises through the wake phrases on the way past.
        "What time is it tomorrow afternoon" partials as `wake`, then
        `wake tubby`, before settling on `[unk]` in the final. Waking on
        that would mean a robot somebody muted turning itself back on
        because they said "tomorrow", which is worse than being slow.
        """

        if not self.recognizer.AcceptWaveform(audio):
            return False

        result = json.loads(self.recognizer.Result() or "{}")
        return heard_wake_word(result.get("text", ""))

    def reset(self) -> None:
        """Forget what it has heard so far.

        Called on waking. Otherwise the phrase that woke the robot is still
        sitting in the decoder and wakes it again the moment it sleeps.
        """

        self.recognizer.Reset()


def build_waker(model_dir: str | Path | None = None) -> WakeWord | None:
    """Load the wake word listener, or explain why there is not one.

    Never raises. A missing model is a reduced robot, not a broken one, and
    this runs on the path that also has to bring the eyes up.
    """

    path = Path(model_dir or os.getenv("HUMALIEN_WAKE_MODEL") or DEFAULT_MODEL_DIR)

    try:
        from vosk import KaldiRecognizer, Model, SetLogLevel
    except ImportError:
        log("vosk is not installed - sleep will not wake on your voice")
        log("  pip install vosk")
        return None

    if not path.is_dir():
        log(f"No wake word model at {path}")
        log("  Download a small model from https://alphacephei.com/vosk/models")
        log("  and unpack it there, or set HUMALIEN_WAKE_MODEL.")
        return None

    # Vosk logs its whole model load at info level, which buries the rest of
    # the startup output.
    SetLogLevel(-1)

    try:
        recognizer = KaldiRecognizer(Model(str(path)), WAKE_SAMPLE_RATE, GRAMMAR)
    except Exception as error:
        log(f"Could not load the wake word model at {path}: {error}")
        return None

    log(f"Wake word ready - say {WAKE_PHRASES[1]!r} to wake it")
    return WakeWord(recognizer)
