import inspect
import json
import unittest

import numpy as np

from people import PeopleStore, normalize
from robot_tools import Robot, tools


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

    @property
    def known(self):
        return [s.match.person for s in self.sightings if s.match is not None]

    def largest_stranger(self, **kwargs):
        return self._stranger


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

    def build(self, **kwargs):
        self.eyes = FakeEyes(self.store, **kwargs)
        return Robot(eyes=self.eyes, store=self.store, describer=self.describer)

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
