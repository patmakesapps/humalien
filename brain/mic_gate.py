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
