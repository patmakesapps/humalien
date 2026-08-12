import json
import unittest

import numpy as np

from people import PeopleStore, normalize
from robot_tools import TOOL_DEFINITIONS, RobotTools


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
        self.enrolled = []

    def enroll(self, name, sighting, **kwargs):
        self.enrolled.append(name)
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
        return RobotTools(self.eyes, self.store, self.describer)

    async def test_tool_definitions_are_well_formed(self):
        for tool in TOOL_DEFINITIONS:
            self.assertEqual(tool["type"], "function")
            self.assertTrue(tool["name"])
            self.assertTrue(tool["description"])
            self.assertEqual(tool["parameters"]["type"], "object")

    async def test_unknown_tool_returns_an_error(self):
        tools = self.build()

        result = json.loads(await tools.call("dance", {}))

        self.assertIn("error", result)

    async def test_look_passes_the_question_through(self):
        tools = self.build(frame=np.zeros((10, 10, 3), dtype=np.uint8))

        result = json.loads(await tools.call("look", {"question": "what colour?"}))

        self.assertEqual(self.describer.asked, "what colour?")
        self.assertEqual(result["you_can_see"], "a red mug")

    async def test_look_without_a_camera_says_so(self):
        tools = self.build(frame=None)

        result = json.loads(await tools.call("look", {"question": "what colour?"}))

        self.assertIn("error", result)

    async def test_who_is_here_reports_names_and_memories(self):
        person = self.store.enroll("Pat", embedding(1))
        self.store.add_fact(person.id, "builds robots")

        match = type("M", (), {"person": person, "similarity": 0.9})()
        tools = self.build(sightings=[FakeSighting(match=match)])

        result = json.loads(await tools.call("who_is_here", {}))

        self.assertEqual(result["people_you_know"][0]["name"], "Pat")
        self.assertEqual(result["people_you_know"][0]["you_remember"], ["builds robots"])
        self.assertEqual(result["unrecognised_faces"], 0)

    async def test_who_is_here_counts_strangers(self):
        tools = self.build(sightings=[FakeSighting(), FakeSighting()])

        result = json.loads(await tools.call("who_is_here", {}))

        self.assertEqual(result["people_you_know"], [])
        self.assertEqual(result["unrecognised_faces"], 2)

    async def test_remember_name_enrolls_the_stranger_in_view(self):
        tools = self.build(stranger=FakeSighting())

        result = json.loads(await tools.call("remember_name", {"name": "Derrick"}))

        self.assertEqual(result["saved"], "Derrick")
        self.assertEqual([p.name for p in self.store.people()], ["Derrick"])

    async def test_remember_name_refuses_without_a_face(self):
        # Better to say so than to attach the name to the wrong person.
        tools = self.build(stranger=None)

        result = json.loads(await tools.call("remember_name", {"name": "Derrick"}))

        self.assertIn("error", result)
        self.assertEqual(self.store.people(), [])

    async def test_remember_name_refuses_an_empty_name(self):
        tools = self.build(stranger=FakeSighting())

        result = json.loads(await tools.call("remember_name", {"name": "  "}))

        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
