import asyncio
import time


PI_SAMPLE_RATE = 48_000
PI_CHANNELS = 2
PI_SAMPLE_WIDTH = 2

BYTES_PER_SECOND = PI_SAMPLE_RATE * PI_CHANNELS * PI_SAMPLE_WIDTH

# How far ahead of the speaker the node is allowed to run.
LEAD_SECONDS = 0.15

# Grace period after the last sample before the robot counts as silent.
# Covers the small buffer still sitting inside aplay on the Pi.
TAIL_SECONDS = 0.25


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

    def __init__(self, websocket):
        self.websocket = websocket
        self.chunks = asyncio.Queue()
        self.playing_until = 0.0

    def push(self, audio: bytes) -> None:
        if audio:
            self.chunks.put_nowait(audio)

    def clear(self) -> None:
        while not self.chunks.empty():
            self.chunks.get_nowait()

        self.playing_until = 0.0

    @property
    def is_speaking(self) -> bool:
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

            # Stay a little ahead of the speaker, never further.
            ahead = self.playing_until - time.monotonic()

            if ahead > LEAD_SECONDS:
                await asyncio.sleep(ahead - LEAD_SECONDS)
