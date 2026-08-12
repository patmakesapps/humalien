import asyncio
import unittest

from playback import BYTES_PER_SECOND, PacedPlayback


class FakeWebsocket:
    def __init__(self):
        self.sent = []

    async def send(self, audio):
        self.sent.append(audio)


def seconds_sent(websocket) -> float:
    return sum(len(chunk) for chunk in websocket.sent) / BYTES_PER_SECOND


class PacedPlaybackTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.websocket = FakeWebsocket()
        self.playback = PacedPlayback(self.websocket)

    async def drain_for(self, seconds: float) -> None:
        runner = asyncio.create_task(self.playback.run())

        await asyncio.sleep(seconds)

        runner.cancel()
        await asyncio.gather(runner, return_exceptions=True)

    def push_seconds(self, seconds: float, chunks: int = 10) -> None:
        chunk = bytes(int(BYTES_PER_SECOND * seconds) // chunks)

        for _ in range(chunks):
            self.playback.push(chunk)

    async def test_silent_until_audio_arrives(self):
        self.assertFalse(self.playback.is_speaking)

    async def test_holds_audio_back_instead_of_dumping_it(self):
        # The Realtime API hands us a whole response at once. If we passed
        # that straight through, the node would bury a second of speech in
        # the speaker buffer and could no longer be interrupted.
        self.push_seconds(1.0)

        await self.drain_for(0.05)

        self.assertLess(seconds_sent(self.websocket), 0.6)
        self.assertTrue(self.playback.is_speaking)

    async def test_clear_stops_the_robot(self):
        self.push_seconds(1.0)

        await self.drain_for(0.05)

        self.playback.clear()

        self.assertTrue(self.playback.chunks.empty())
        self.assertFalse(self.playback.is_speaking)

        # Nothing further reaches the node once the queue is dropped.
        already_sent = seconds_sent(self.websocket)

        await self.drain_for(0.05)

        self.assertEqual(seconds_sent(self.websocket), already_sent)


if __name__ == "__main__":
    unittest.main()
