import inspect
import json
import unittest

import numpy as np

from conversation import ConversationState
from people import PeopleStore, normalize
from robot_tools import OLLAMA, REALTIME, Robot, tools


def embedding(seed: int) -> np.ndarray:
    return normalize(np.random.default_rng(seed).normal(size=128).astype(np.float32))


class FakeSighting:
    def __init__(self, match=None, area=1000):
        self.match = match
        self.embedding = embedding(0)
        self.detection = type("D", (), {"area": area})()


class FakePerception:
    def __init__(self, store):
        self.store = store

    def enroll(self, name, sighting, **kwargs):
        return self.store.enroll(name, sighting.embedding)


class FakeEyes:
    def __init__(self, store, *, frame=None, sightings=None, stranger=None):
        self.frame = frame
        self.sightings = sightings or []
        self.perception = FakePerception(store)
        self._stranger = stranger
        self.asked_for = None

    @property
    def known(self):
        return [s.match.person for s in self.sightings if s.match is not None]

    def largest_stranger(self, **kwargs):
        return self._stranger

    def clearest_frame(self, *, since=None, until=None):
        self.asked_for = (since, until)
        return self.frame


class FakeRealtime:
    def __init__(self, *, fails=False):
        self.fails = fails
        self.images = []

    async def send_image(self, jpeg):
        if self.fails:
            raise ConnectionError("session gone")

        self.images.append(jpeg)


class FakeDescriber:
    def __init__(self, answer="a red mug"):
        self.answer = answer
        self.asked = None

    def describe(self, frame, question):
        self.asked = question
        return self.answer


class RobotToolsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = PeopleStore(":memory:")
        self.describer = FakeDescriber()

    def tearDown(self):
        self.store.close()

    def build(self, *, realtime=None, vision=OLLAMA, state=None, **kwargs):
        self.eyes = FakeEyes(self.store, **kwargs)

        return Robot(
            eyes=self.eyes,
            store=self.store,
            describer=self.describer,
            state=state or ConversationState(),
            realtime=realtime,
            vision=vision,
        )

    async def run_tool(self, robot, name, arguments=None):
        return json.loads(await tools.execute(robot, name, arguments))

    async def test_every_tool_has_a_handler_that_matches_its_schema(self):
        # The reason the registry exists: a schema and a handler that drifted
        # apart used to fail only when the model called the tool.
        for name, tool in tools.tools.items():
            parameters = inspect.signature(tool["handler"]).parameters
            declared = set(tool["schema"]["properties"])
            accepted = set(parameters) - {"robot"}

            self.assertTrue(declared <= accepted, f"{name} cannot accept {declared}")

            for field in tool["schema"]["required"]:
                self.assertIn(field, parameters, f"{name} is missing {field}")

    async def test_look_passes_the_question_through(self):
        robot = self.build(frame=np.zeros((10, 10, 3), dtype=np.uint8))

        result = await self.run_tool(robot, "look", '{"question": "what colour?"}')

        self.assertTrue(result["success"])
        self.assertEqual(self.describer.asked, "what colour?")
        self.assertEqual(result["data"]["you_can_see"], "a red mug")

    async def test_look_uses_the_frame_from_when_the_question_was_asked(self):
        # The whole point: by the time a tool call lands, the hand being
        # asked about has moved.
        state = ConversationState()
        state.speech_started_at = 100.0
        state.speech_stopped_at = 102.0

        robot = self.build(
            frame=np.zeros((10, 10, 3), dtype=np.uint8),
            state=state,
        )

        await self.run_tool(robot, "look", '{"question": "what colour?"}')

        self.assertEqual(self.eyes.asked_for, (100.0, 102.0))

    async def test_realtime_vision_hands_the_frame_to_the_model(self):
        realtime = FakeRealtime()
        robot = self.build(
            frame=np.zeros((10, 10, 3), dtype=np.uint8),
            realtime=realtime,
            vision=REALTIME,
        )

        result = await self.run_tool(robot, "look", '{"question": "what colour?"}')

        self.assertTrue(result["success"])
        self.assertEqual(len(realtime.images), 1)
        # Ollama was never asked, because the model looked itself.
        self.assertIsNone(self.describer.asked)

    async def test_realtime_failure_falls_back_to_ollama(self):
        realtime = FakeRealtime(fails=True)
        robot = self.build(
            frame=np.zeros((10, 10, 3), dtype=np.uint8),
            realtime=realtime,
            vision=REALTIME,
        )

        result = await self.run_tool(robot, "look", '{"question": "what colour?"}')

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["you_can_see"], "a red mug")
        self.assertEqual(robot.vision, OLLAMA)

    async def test_falling_back_sticks_for_the_rest_of_the_session(self):
        robot = self.build(
            frame=np.zeros((10, 10, 3), dtype=np.uint8),
            realtime=FakeRealtime(fails=True),
            vision=REALTIME,
        )

        await self.run_tool(robot, "look", '{"question": "first"}')
        realtime = robot.realtime = FakeRealtime()

        await self.run_tool(robot, "look", '{"question": "second"}')

        # Still on Ollama, rather than retrying a session that just refused.
        self.assertEqual(realtime.images, [])
        self.assertEqual(self.describer.asked, "second")

    async def test_look_without_a_camera_says_so(self):
        robot = self.build(frame=None)

        result = await self.run_tool(robot, "look", '{"question": "what colour?"}')

        self.assertFalse(result["success"])
        self.assertIn("camera", result["error"])

    async def test_look_requires_a_question(self):
        robot = self.build(frame=np.zeros((10, 10, 3), dtype=np.uint8))

        result = await self.run_tool(robot, "look", "{}")

        self.assertFalse(result["success"])
        self.assertIn("question", result["error"])

    async def test_who_is_here_reports_names_and_memories(self):
        person = self.store.enroll("Pat", embedding(1))
        self.store.add_fact(person.id, "builds robots")

        match = type("M", (), {"person": person, "similarity": 0.9})()
        robot = self.build(sightings=[FakeSighting(match=match)])

        result = await self.run_tool(robot, "who_is_here")

        known = result["data"]["people_you_know"][0]
        self.assertEqual(known["name"], "Pat")
        self.assertEqual(known["you_remember"], ["builds robots"])
        self.assertEqual(result["data"]["unrecognised_faces"], 0)

    async def test_who_is_here_counts_strangers(self):
        robot = self.build(sightings=[FakeSighting(), FakeSighting()])

        result = await self.run_tool(robot, "who_is_here")

        self.assertEqual(result["data"]["people_you_know"], [])
        self.assertEqual(result["data"]["unrecognised_faces"], 2)

    async def test_remember_name_enrolls_the_stranger_in_view(self):
        robot = self.build(stranger=FakeSighting())

        result = await self.run_tool(robot, "remember_name", '{"name": "Derrick"}')

        self.assertTrue(result["success"])
        self.assertEqual([p.name for p in self.store.people()], ["Derrick"])

    async def test_remember_name_refuses_without_a_face(self):
        # Better to say so than to attach the name to the wrong person.
        robot = self.build(stranger=None)

        result = await self.run_tool(robot, "remember_name", '{"name": "Derrick"}')

        self.assertFalse(result["success"])
        self.assertEqual(self.store.people(), [])

    async def test_remember_name_refuses_an_empty_name(self):
        robot = self.build(stranger=FakeSighting())

        result = await self.run_tool(robot, "remember_name", '{"name": "  "}')

        self.assertFalse(result["success"])
        self.assertEqual(self.store.people(), [])


if __name__ == "__main__":
    unittest.main()
