HALF_DUPLEX = "half_duplex"
OPEN = "open"


class HalfDuplexGate:
    """Stop listening while the robot is speaking.

    With no echo cancellation the microphone hears the speaker, and the
    Realtime API ends up answering its own voice. Closing the microphone
    during playback removes that loop completely. The cost is barge-in:
    the robot cannot be interrupted while it talks.
    """

    name = HALF_DUPLEX

    def __init__(self, playback):
        self.playback = playback

    @property
    def is_open(self) -> bool:
        return not self.playback.is_speaking


class OpenGate:
    """Always listen, and let semantic VAD handle turn taking.

    Only safe when the microphone signal already has the speaker removed
    from it, e.g. the PipeWire echo-cancel source on the Pi. See
    docs/hardware.md.
    """

    name = OPEN

    def __init__(self, playback):
        self.playback = playback

    @property
    def is_open(self) -> bool:
        return True


class SleepableGate:
    """Any gate, plus a mute the conversation can ask for.

    Sleep and half duplex close the microphone for unrelated reasons - one
    because somebody asked, one because the robot is talking over itself -
    and both have to be able to close it independently. Wrapping rather
    than adding a flag to each gate keeps that from becoming two booleans
    every gate has to remember to check.
    """

    def __init__(self, inner, state):
        self.inner = inner
        self.state = state

    @property
    def name(self) -> str:
        return f"{self.inner.name} (sleepable)"

    @property
    def is_open(self) -> bool:
        return self.inner.is_open and not self.state.asleep

    @property
    def room_only(self) -> bool:
        """Whether the microphone is hearing the room rather than us.

        Sleep is the one closed gate whose audio is still worth listening
        to, but only the half of it that is not the robot's own voice
        coming back through the speaker.
        """

        return self.inner.is_open


GATES = {
    HALF_DUPLEX: HalfDuplexGate,
    OPEN: OpenGate,
}


def build_mic_gate(name: str, playback) -> HalfDuplexGate | OpenGate:
    if name not in GATES:
        supported = ", ".join(sorted(GATES))
        raise ValueError(
            f"Unknown microphone gate {name!r}. Supported: {supported}"
        )

    return GATES[name](playback)
