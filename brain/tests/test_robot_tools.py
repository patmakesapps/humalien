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
        self.captions = []
        self.deleted = []

    async def send_image(self, jpeg, *, item_id, caption):
        if self.fails:
            raise ConnectionError("session gone")

        self.images.append(item_id)
        self.captions.append(caption)

        return item_id

    async def delete_item(self, item_id):
        self.deleted.append(item_id)


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

    def build(
        self,
        *,
        realtime=None,
        vision=OLLAMA,
        state=None,
        mood=None,
        appearance=None,
        **kwargs,
    ):
        self.eyes = FakeEyes(self.store, **kwargs)

        return Robot(
            eyes=self.eyes,
            store=self.store,
            describer=self.describer,
            state=state or ConversationState(),
            realtime=realtime,
            mood=mood,
            appearance=appearance,
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

    async def test_only_one_image_is_ever_in_context(self):
        # Otherwise every look is re-sent with every later turn, and the
        # cost of a long conversation climbs with each glance.
        realtime = FakeRealtime()
        robot = self.build(
            frame=np.zeros((10, 10, 3), dtype=np.uint8),
            realtime=realtime,
            vision=REALTIME,
        )

        await self.run_tool(robot, "look", '{"question": "first"}')
        await self.run_tool(robot, "look", '{"question": "second"}')
        await self.run_tool(robot, "look", '{"question": "third"}')

        self.assertEqual(len(realtime.images), 3)
        # Every picture but the newest has been taken back out.
        self.assertEqual(realtime.deleted, realtime.images[:-1])
        self.assertEqual(robot.showing, realtime.images[-1])

    async def test_the_first_look_deletes_nothing(self):
        realtime = FakeRealtime()
        robot = self.build(
            frame=np.zeros((10, 10, 3), dtype=np.uint8),
            realtime=realtime,
            vision=REALTIME,
        )

        await self.run_tool(robot, "look", '{"question": "what colour?"}')

        self.assertEqual(realtime.deleted, [])

    async def test_the_picture_is_labelled_as_its_own_eyes(self):
        # Without this the model talks about "the image you sent me".
        realtime = FakeRealtime()
        robot = self.build(
            frame=np.zeros((10, 10, 3), dtype=np.uint8),
            realtime=realtime,
            vision=REALTIME,
        )

        await self.run_tool(robot, "look", '{"question": "what colour?"}')

        self.assertIn("your own camera", realtime.captions[0].lower())

    async def test_the_tool_result_says_nothing_worth_reading_out(self):
        realtime = FakeRealtime()
        robot = self.build(
            frame=np.zeros((10, 10, 3), dtype=np.uint8),
            realtime=realtime,
            vision=REALTIME,
        )

        result = await self.run_tool(robot, "look", '{"question": "what colour?"}')

        self.assertEqual(result["data"], {"looked": True})

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


class FakeMood:
    def __init__(self):
        self.colors = []
        self.winks = []
        self.celebrations = []

    def set_color(self, color):
        self.colors.append(color)
        return True

    def wink(self, eye):
        self.winks.append(eye)
        return True

    def celebrate(self, style):
        self.celebrations.append(style)
        return True


class FakeAppearance:
    def __init__(self):
        self.saved = []

    def set_default_eye_color(self, color):
        self.saved.append(color)


class EyeToolTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = PeopleStore(":memory:")
        self.mood = FakeMood()
        self.appearance = FakeAppearance()
        self.robot = Robot(
            eyes=FakeEyes(self.store),
            store=self.store,
            describer=None,
            mood=self.mood,
            appearance=self.appearance,
        )

    def tearDown(self):
        self.store.close()

    async def test_color_changes_both_eyes_without_saving_by_default(self):
        result = await tools.execute(
            self.robot,
            "set_eye_color",
            json.dumps({"color": "green"}),
        )

        self.assertTrue(json.loads(result)["success"])
        self.assertEqual(self.mood.colors, ["green"])
        self.assertEqual(self.appearance.saved, [])

    async def test_default_color_is_saved_only_when_explicit(self):
        await tools.execute(
            self.robot,
            "set_eye_color",
            json.dumps({"color": "blue", "save_as_default": True}),
        )

        self.assertEqual(self.mood.colors, ["blue"])
        self.assertEqual(self.appearance.saved, ["blue"])

    async def test_wink_and_celebrate_reach_the_mood_controller(self):
        await tools.execute(
            self.robot, "wink", json.dumps({"eye": "left"})
        )
        await tools.execute(
            self.robot, "celebrate", json.dumps({"style": "rainbow"})
        )

        self.assertEqual(self.mood.winks, ["left"])
        self.assertEqual(self.mood.celebrations, ["rainbow"])

    async def test_invalid_colors_are_rejected_by_the_tool_schema(self):
        result = await tools.execute(
            self.robot,
            "set_eye_color",
            json.dumps({"color": "infrared"}),
        )

        self.assertFalse(json.loads(result)["success"])
        self.assertEqual(self.mood.colors, [])


class FakeGestures:
    """Just enough of Gestures to see what `move` asked for."""

    def __init__(self, answer=None):
        self.answer = answer
        self.asked = []

    def command(self, part, direction):
        self.asked.append((part, direction))
        return self.answer


class MemoryToolTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = PeopleStore(":memory:")
        self.pat = self.store.enroll("Pat", embedding(1))
        self.sam = self.store.enroll("Sam", embedding(2))

    def tearDown(self):
        self.store.close()

    def robot(self, sightings=()):
        return Robot(
            eyes=FakeEyes(self.store, sightings=list(sightings)),
            store=self.store,
            describer=None,
            state=ConversationState(),
        )

    def seeing(self, person):
        return FakeSighting(match=type("M", (), {"person": person})())

    async def test_remember_keeps_something_general(self):
        await tools.execute(self.robot(), "remember", json.dumps(
            {"fact": "the desk bot lives on the workbench"}
        ))

        kept = self.store.recall("workbench")

        self.assertEqual(len(kept), 1)
        self.assertIsNone(kept[0]["person_id"])

    async def test_remember_files_it_against_a_named_person(self):
        await tools.execute(self.robot(), "remember", json.dumps(
            {"fact": "takes coffee black", "about": "Pat"}
        ))

        self.assertEqual(self.store.recall("coffee")[0]["person_id"], self.pat.id)

    async def test_an_unknown_name_still_keeps_the_memory(self):
        """Losing the fact would be worse than losing who it was about."""

        await tools.execute(self.robot(), "remember", json.dumps(
            {"fact": "Morgan is building a kiln", "about": "Morgan"}
        ))

        kept = self.store.recall("kiln")

        self.assertEqual(len(kept), 1)
        self.assertIsNone(kept[0]["person_id"])

    async def test_one_visible_face_claims_an_unattributed_memory(self):
        robot = self.robot(sightings=[self.seeing(self.pat)])

        await tools.execute(robot, "remember", json.dumps(
            {"fact": "is learning the cello"}
        ))

        self.assertEqual(self.store.recall("cello")[0]["person_id"], self.pat.id)

    async def test_two_visible_faces_do_not_get_a_coin_flip(self):
        """"Remember I take it black" with two people in view is ambiguous.

        Unattached is recoverable - it is still findable. Filed against the
        wrong person is not.
        """

        robot = self.robot(
            sightings=[self.seeing(self.pat), self.seeing(self.sam)]
        )

        await tools.execute(robot, "remember", json.dumps(
            {"fact": "hates coriander"}
        ))

        self.assertIsNone(self.store.recall("coriander")[0]["person_id"])

    async def test_recall_with_nothing_returns_everything(self):
        """The normal call. The model reads the list and picks.

        Deciding which of thirty sentences bears on what somebody just said
        is a language problem, and there is a language model on the other end
        of this call. Anything that pre-filters here is guessing on its
        behalf, worse, with keywords.
        """

        self.store.remember("the neck servo is channel one")
        self.store.remember("is building a kiln")
        self.store.remember("takes coffee black")

        result = await tools.execute(self.robot(), "recall", "{}")
        text = json.dumps(result)

        self.assertIn("channel one", text)
        self.assertIn("kiln", text)
        self.assertIn("coffee", text)

    def test_recall_never_drops_a_row_the_model_might_want(self):
        """A phrase that shares no keyword with a memory still returns it."""

        self.store.remember("is building a kiln in the garage")

        # Nothing here matches "kiln" or "building" by any string rule.
        everything = self.store.recall()

        self.assertEqual(len(everything), 1)

    async def test_recall_hands_back_ids_to_act_on(self):
        self.store.remember("the neck servo is channel one")

        result = json.loads(await tools.execute(self.robot(), "recall", "{}"))

        self.assertIn("id", result["data"]["you_remember"][0])

    async def test_recall_names_who_a_memory_is_about(self):
        self.store.remember("takes coffee black", person_id=self.pat.id)

        result = await tools.execute(self.robot(), "recall", json.dumps(
            {"about": "coffee"}
        ))

        self.assertIn("Pat", json.dumps(result))

    async def test_recall_of_nothing_is_not_an_error(self):
        result = await tools.execute(self.robot(), "recall", json.dumps(
            {"about": "submarines"}
        ))

        self.assertNotIn("error", json.dumps(result).lower())

    async def test_revise_replaces_rather_than_duplicating(self):
        self.store.remember("is building a kiln", person_id=self.pat.id)
        memory_id = self.store.recall()[0]["id"]

        await tools.execute(self.robot(), "revise", json.dumps(
            {"id": memory_id, "fact": "finished the kiln"}
        ))

        kept = self.store.recall()

        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["text"], "finished the kiln")
        self.assertEqual(kept[0]["person_id"], self.pat.id)

    async def test_forget_drops_it(self):
        self.store.remember("takes coffee black")
        memory_id = self.store.recall()[0]["id"]

        await tools.execute(self.robot(), "forget", json.dumps(
            {"id": memory_id}
        ))

        self.assertEqual(self.store.recall(), [])

    async def test_acting_on_a_memory_that_is_not_there_says_so(self):
        for tool, arguments in (
            ("revise", {"id": 999, "fact": "anything"}),
            ("forget", {"id": 999}),
        ):
            result = await tools.execute(
                self.robot(), tool, json.dumps(arguments)
            )

            self.assertIn("recall first", json.dumps(result).lower())


class MoveToolTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = PeopleStore(":memory:")

    def tearDown(self):
        self.store.close()

    def robot(self, gestures):
        return Robot(
            eyes=FakeEyes(self.store),
            store=self.store,
            describer=None,
            state=ConversationState(),
            gestures=gestures,
        )

    async def test_move_reaches_the_gesture_generator(self):
        gestures = FakeGestures(answer={"pan": 10.0})

        await tools.execute(self.robot(gestures), "move", json.dumps(
            {"part": "head", "direction": "left"}
        ))

        self.assertEqual(gestures.asked, [("head", "left")])

    async def test_a_move_the_body_cannot_make_says_so(self):
        result = await tools.execute(
            self.robot(FakeGestures(answer=None)), "move",
            json.dumps({"part": "head", "direction": "down"}),
        )

        self.assertIn("cannot", json.dumps(result).lower())

    async def test_a_brain_with_no_body_does_not_raise(self):
        """A laptop, or gestures switched off. Not worth an apology."""

        result = await tools.execute(self.robot(None), "move", json.dumps(
            {"part": "head", "direction": "left"}
        ))

        self.assertNotIn("error", json.dumps(result).lower())
