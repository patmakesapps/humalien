"""The control path end to end, with fake hardware on both sides.

This is the wiring that cannot be checked from a laptop any other way:
that connecting engages the arms, that a pose frame on the same socket as
the audio reaches them, and that losing the brain leaves them limp.
"""

import asyncio
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from websockets.asyncio.client import connect
from websockets.asyncio.server import serve

from humalien_node import server
from humalien_node.arms import Arms, CHANNELS, REST


class FakePipe:
    def __init__(self):
        self.written = b""

    def read(self, size):
        # Slow silence. Returning b"" would end the mic task and tear the
        # connection down before the test could say anything.
        time.sleep(0.05)
        return b"\x00" * size

    def readline(self):
        time.sleep(0.05)
        return b""

    def write(self, data):
        self.written += data

    def flush(self):
        pass


class FakeProcess:
    def __init__(self):
        self.stdout = FakePipe()
        self.stdin = FakePipe()
        self.stderr = FakePipe()
        self.terminated = False

    def poll(self):
        return None if not self.terminated else 0

    def terminate(self):
        self.terminated = True

    def wait(self):
        return 0

    def kill(self):
        self.terminated = True


class FakeDriver:
    def __init__(self):
        self.written = {}
        self.released = []

    def write(self, channel, microseconds):
        self.written[channel] = microseconds

    def release(self, channel):
        self.released.append(channel)


class TestControlPath(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._real = (server.start_microphone, server.start_speaker)
        server.start_microphone = FakeProcess
        server.start_speaker = FakeProcess

        self.driver = FakeDriver()
        self.arms = Arms(self.driver)

    async def asyncTearDown(self):
        server.start_microphone, server.start_speaker = self._real

    async def talk(self, send=()):
        """Run the real handler, say things to it, and return."""

        async def handler(websocket):
            await server.handle_connection(websocket, arms=self.arms)

        async with serve(handler, "127.0.0.1", 0) as running:
            port = running.sockets[0].getsockname()[1]

            async with connect(f"ws://127.0.0.1:{port}") as ws:
                await asyncio.wait_for(ws.recv(), timeout=5)   # node_status

                for message in send:
                    await ws.send(json.dumps(message))

                await asyncio.sleep(0.3)

                yielded = (
                    dict(self.arms.target),
                    dict(self.arms.position),
                )

            await asyncio.sleep(0.2)
            return yielded

    async def test_connecting_engages_the_arms_at_rest(self):
        target, position = await self.talk()

        self.assertEqual(target["arm_l"], REST)
        self.assertEqual(position["arm_r"], REST)

    async def test_a_pose_frame_moves_the_arms(self):
        target, position = await self.talk(
            send=[{"type": "pose", "arm_l": 45.0, "arm_r": 30.0}]
        )

        self.assertEqual(target["arm_l"], 45.0)
        self.assertEqual(target["arm_r"], 30.0)

        # Slewed toward the target, and on its way there.
        self.assertGreater(position["arm_l"], REST)
        self.assertLessEqual(position["arm_l"], 45.0)

    async def test_an_out_of_range_pose_is_clamped_not_obeyed(self):
        target, _ = await self.talk(
            send=[{"type": "pose", "arm_l": 900.0}]
        )

        self.assertEqual(target["arm_l"], 75.0)

    async def test_rubbish_on_the_control_channel_is_survivable(self):
        target, _ = await self.talk(
            send=[
                {"type": "pose", "pan": 40.0},        # uncalibrated axis
                {"type": "nonsense"},
                {"type": "pose", "arm_r": 20.0},      # still works after
            ]
        )

        self.assertEqual(target["arm_r"], 20.0)
        self.assertNotIn("pan", target)

    async def test_losing_the_brain_leaves_the_arms_limp(self):
        await self.talk()

        self.assertEqual(
            sorted(self.driver.released[-2:]),
            sorted(CHANNELS.values()),
        )
        self.assertIsNone(self.arms.position["arm_l"])


if __name__ == "__main__":
    unittest.main()
