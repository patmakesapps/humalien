"""The control path end to end, with fake hardware on both sides.

This is the wiring that cannot be checked from a laptop any other way: that
connecting engages the body and lights the eyes, that pose and mood frames on
the same socket as the audio reach them, and that losing the brain leaves the
head parked, the servos limp, and the eyes dark.
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
from humalien_node.arms import ARM_REST, Arms, CHANNELS
from humalien_node.pixels import PIXEL_COUNT, Pixels


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


class FakePixels:
    def __init__(self):
        self.frames = []

    def write(self, data):
        self.frames.append(data)


class TestControlPath(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._real = (server.start_microphone, server.start_speaker)
        server.start_microphone = FakeProcess
        server.start_speaker = FakeProcess

        self.driver = FakeDriver()
        self.arms = Arms(self.driver)

        self.lights = FakePixels()
        self.pixels = Pixels(self.lights)

    async def asyncTearDown(self):
        server.start_microphone, server.start_speaker = self._real

    async def talk(self, send=()):
        """Run the real handler, say things to it, and return."""

        async def handler(websocket):
            await server.handle_connection(
                websocket,
                arms=self.arms,
                pixels=self.pixels,
            )

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
                    self.pixels.mood,
                )

            # Long enough for the head to park on the way out.
            await asyncio.sleep(1.0)
            return yielded

    async def test_connecting_engages_the_body_at_rest(self):
        target, position, _ = await self.talk()

        self.assertEqual(target["arm_l"], ARM_REST)
        self.assertEqual(position["arm_r"], ARM_REST)
        self.assertEqual(position["pan"], 0.0)
        self.assertEqual(position["nod"], 0.0)

    async def test_a_pose_frame_moves_the_arms(self):
        target, position, _ = await self.talk(
            send=[{"type": "pose", "arm_l": 45.0, "arm_r": 30.0}]
        )

        self.assertEqual(target["arm_l"], 45.0)
        self.assertEqual(target["arm_r"], 30.0)

        # Slewed toward the target, and on its way there.
        self.assertGreater(position["arm_l"], ARM_REST)
        self.assertLessEqual(position["arm_l"], 45.0)

    async def test_a_pose_frame_moves_the_head(self):
        target, _, _ = await self.talk(
            send=[{"type": "pose", "pan": 8.0, "nod": 3.0}]
        )

        self.assertEqual(target["pan"], 8.0)
        self.assertEqual(target["nod"], 3.0)

    async def test_an_out_of_range_pose_is_clamped_not_obeyed(self):
        target, _, _ = await self.talk(
            send=[{"type": "pose", "arm_l": 900.0, "pan": 90.0, "nod": -90.0}]
        )

        self.assertEqual(target["arm_l"], 75.0)
        self.assertEqual(target["pan"], 14.4)
        self.assertEqual(target["nod"], -3.6)

    async def test_an_eyes_frame_sets_the_mood(self):
        _, _, mood = await self.talk(
            send=[{"type": "eyes", "mood": "excited", "level": 0.8}]
        )

        self.assertEqual(mood, "excited")

    async def test_the_eyes_are_lit_before_the_brain_says_anything(self):
        await self.talk()

        self.assertTrue(self.lights.frames)

    async def test_rubbish_on_the_control_channel_is_survivable(self):
        target, _, mood = await self.talk(
            send=[
                {"type": "pose", "jaw": 40.0},        # no such axis
                {"type": "eyes", "mood": "smug"},     # no such mood
                {"type": "nonsense"},
                {"type": "pose", "arm_r": 20.0},      # still works after
                {"type": "eyes", "mood": "happy"},
            ]
        )

        self.assertEqual(target["arm_r"], 20.0)
        self.assertEqual(mood, "happy")
        self.assertNotIn("jaw", target)

    async def test_losing_the_brain_leaves_the_servos_limp(self):
        await self.talk()

        self.assertEqual(
            sorted(set(self.driver.released)),
            sorted(CHANNELS.values()),
        )

        for axis in self.arms.position:
            self.assertIsNone(self.arms.position[axis], axis)

    async def test_losing_the_brain_parks_the_head_before_releasing_it(self):
        """A head released off-centre has to be jumped back on next engage.

        The eye wiring runs through the nod joint, so that jump is the one
        move worth this much trouble to avoid.
        """

        await self.talk(send=[{"type": "pose", "nod": 20.0, "pan": 12.0}])

        # The last pulse written to each head channel before it was released.
        self.assertAlmostEqual(self.driver.written[1], 1500, delta=2)
        self.assertAlmostEqual(self.driver.written[2], 1500, delta=2)

    async def test_losing_the_brain_puts_the_eyes_out(self):
        await self.talk(send=[{"type": "eyes", "mood": "excited"}])

        self.assertEqual(self.lights.frames[-1], bytes(PIXEL_COUNT * 3))


if __name__ == "__main__":
    unittest.main()
