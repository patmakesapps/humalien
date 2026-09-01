import asyncio
import time

import numpy as np


PI_SAMPLE_RATE = 48_000
PI_CHANNELS = 2
PI_SAMPLE_WIDTH = 2

BYTES_PER_SECOND = PI_SAMPLE_RATE * PI_CHANNELS * PI_SAMPLE_WIDTH

# How far ahead of the speaker the node is allowed to run.
LEAD_SECONDS = 0.15

# Grace period after the last sample before the robot counts as silent.
# Covers the small buffer still sitting inside aplay on the Pi.
TAIL_SECONDS = 0.25


def level(audio: bytes) -> float:
    """Loudness of one chunk of PCM16, as 0.0 to 1.0.

    Root mean square rather than peak: peak tracks the sharpest click in the
    chunk, which makes an arm driven from it twitch on consonants instead of
    following the shape of the sentence.
    """

    if len(audio) < 2:
        return 0.0

    samples = np.frombuffer(audio[: len(audio) // 2 * 2], dtype="<i2")

    if samples.size == 0:
        return 0.0

    # float64 first: squaring int16 overflows, and a silent chunk squared in
    # int16 is indistinguishable from a loud one.
    rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))

    return min(1.0, rms / 32768.0)


class PacedPlayback:
    """Release model audio to the node at the speed it is spoken.

    The Realtime API delivers a whole response far faster than it can be
    played. Forwarding that straight to the node buries several seconds of
    speech in the speaker buffer, which makes interruption impossible and
    hides the fact that the robot is still talking.

    Draining at wall-clock rate keeps at most LEAD_SECONDS in flight, so
    ``clear`` really does stop the robot and ``is_speaking`` really does
    mean sound is coming out of the head.
    """

    def __init__(self, websocket, on_level=None):
        self.websocket = websocket
        self.chunks = asyncio.Queue()
        self.playing_until = 0.0

        # Called with the loudness of each chunk, 0.0 to 1.0, at the moment
        # that chunk is released. See `is_speaking` for why this is the only
        # place in the brain where the audio and the wall clock agree.
        self.on_level = on_level

        # Bytes actually released to the node. Compared against the node's
        # own count, this says whether audio was lost in the brain, on the
        # wire, or inside ALSA.
        self.sent = 0

    @property
    def sent_seconds(self) -> float:
        return self.sent / BYTES_PER_SECOND

    def push(self, audio: bytes) -> None:
        if audio:
            self.chunks.put_nowait(audio)

    def clear(self) -> None:
        dropped = 0

        while not self.chunks.empty():
            dropped += len(self.chunks.get_nowait())

        self.playing_until = 0.0

        return dropped

    @property
    def is_speaking(self) -> bool:
        """True while sound is actually coming out of the head.

        This is the signal to drive a jaw servo from, and the reason to
        resist `response.output_audio.delta`. Those events describe the
        model generating audio, which finishes roughly ten times sooner
        than the speaker finishes playing it. A jaw wired to them stops
        moving mid-sentence while the head keeps talking.

        For a jaw that opens with volume rather than on and off, take an
        RMS envelope of each chunk in `run` as it is released. That is
        the moment the audio and the clock line up.
        """

        if not self.chunks.empty():
            return True

        return time.monotonic() < self.playing_until + TAIL_SECONDS

    async def run(self) -> None:
        while True:
            audio = await self.chunks.get()
            now = time.monotonic()

            # Start a fresh clock if the speaker has already fallen silent.
            if self.playing_until < now:
                self.playing_until = now

            self.playing_until += len(audio) / BYTES_PER_SECOND

            await self.websocket.send(audio)

            self.sent += len(audio)

            if self.on_level is not None:
                self.on_level(level(audio))

            # Stay a little ahead of the speaker, never further.
            ahead = self.playing_until - time.monotonic()

            if ahead > LEAD_SECONDS:
                await asyncio.sleep(ahead - LEAD_SECONDS)
