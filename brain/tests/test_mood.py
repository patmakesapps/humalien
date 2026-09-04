"""The eyes must say what is actually happening, and then stop saying it."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mood import (
    CURIOUS_SECONDS,
    FEELINGS,
    FEEL_SECONDS,
    HEARING_FLOOR,
    LEVEL_DEADBAND,
    MOODS,
    SLEEPY_AFTER,
    Mood,
    EYE_COLORS,
)


STEP = 0.1


def run(mood, seconds, step=STEP, **each):
    """Advance the machine, optionally feeding it something every tick."""

    decided = []

    for _ in range(int(seconds / step)):
        for name, value in each.items():
            getattr(mood, name)(value)

        decided.append(mood.decide(step))

    return decided


def moods(decided):
    return [name for name, _ in decided]


class TestTheVocabulary(unittest.TestCase):
    def test_the_brain_and_the_node_agree_on_the_mood_names(self):
        """Two lists, two machines. A typo here is a silently dead mood.

        The node ignores a mood it does not know, so a name that exists only
        in the brain leaves the eyes on whatever they were showing before.
        """

        node = Path(__file__).resolve().parents[2] / "node" / "humalien_node"

        sys.path.insert(0, str(node.parent))

        from humalien_node.pixels import MOODS as RENDERED

        self.assertEqual(set(MOODS), set(RENDERED))

    def test_the_brain_and_node_agree_on_color_names(self):
        node = Path(__file__).resolve().parents[2] / "node"
        sys.path.insert(0, str(node))

        from humalien_node.pixels import EYE_COLORS as RENDERED_COLORS

        self.assertEqual(set(EYE_COLORS), set(RENDERED_COLORS))

    def test_the_model_cannot_fake_a_fact(self):
        """speaking and listening are observed. off is a hardware state."""

        for forbidden in ("speaking", "listening", "off", "idle"):
            self.assertNotIn(forbidden, FEELINGS)

    def test_every_feeling_is_something_the_node_can_draw(self):
        for feeling in FEELINGS:
            self.assertIn(feeling, MOODS)


class TestWhatTheEyesSay(unittest.TestCase):
    def test_an_empty_room_is_idle(self):
        self.assertEqual(run(Mood(None), 1.0)[-1][0], "idle")

    def test_the_robot_speaking_shows_in_the_eyes(self):
        decided = run(Mood(None), 1.0, speaking=0.7)

        self.assertEqual(decided[-1], ("speaking", 0.7))

    def test_somebody_speaking_shows_in_the_eyes(self):
        decided = run(Mood(None), 1.0, hearing=0.5)

        self.assertEqual(moods(decided)[-1], "listening")
        self.assertGreater(decided[-1][1], 0.0)

    def test_room_noise_does_not_count_as_somebody_speaking(self):
        """The microphone streams silence too, and it never stops.

        Without a floor this pins the eyes in `listening` for the whole
        session - never idle, never curious, never asleep.
        """

        decided = run(Mood(None), 4.0, hearing=HEARING_FLOOR * 0.5)

        self.assertEqual(moods(decided)[-1], "idle")

    def test_working_on_an_answer_shows_in_the_eyes(self):
        mood = Mood(None)
        mood.thinking(True)

        self.assertEqual(run(mood, 1.0)[-1][0], "thinking")

    def test_speaking_beats_thinking(self):
        """The response is still open while the speaker is playing it."""

        mood = Mood(None)
        mood.thinking(True)

        self.assertEqual(moods(run(mood, 1.0, speaking=0.4))[-1], "speaking")

    def test_a_new_face_is_worth_a_look(self):
        mood = Mood(None)
        mood.seen(new=True)

        self.assertEqual(mood.decide(STEP)[0], "curious")

    def test_curiosity_wears_off(self):
        mood = Mood(None)
        mood.seen(new=True)

        self.assertEqual(
            moods(run(mood, CURIOUS_SECONDS + 1.0))[-1],
            "idle",
        )

    def test_a_long_empty_room_goes_to_sleep(self):
        self.assertEqual(
            moods(run(Mood(None), SLEEPY_AFTER + 2.0))[-1],
            "sleepy",
        )

    def test_somebody_walking_in_wakes_it_up(self):
        mood = Mood(None)

        run(mood, SLEEPY_AFTER + 2.0)
        self.assertEqual(mood.decide(STEP)[0], "sleepy")

        mood.seen(new=True)
        self.assertEqual(mood.decide(STEP)[0], "curious")


class TestFeeling(unittest.TestCase):
    def test_the_model_can_show_a_feeling(self):
        mood = Mood(None)

        self.assertTrue(mood.feel("excited"))
        self.assertEqual(mood.decide(STEP)[0], "excited")

    def test_a_feeling_it_cannot_show_is_refused(self):
        mood = Mood(None)

        self.assertFalse(mood.feel("smug"))
        self.assertFalse(mood.feel("speaking"))
        self.assertEqual(mood.decide(STEP)[0], "idle")

    def test_a_feeling_expires(self):
        """A mood the model set and forgot must not colour the whole session.

        There is no reliable moment at which the model takes one back, so it
        has to time out on its own or the robot beams through bad news.
        """

        mood = Mood(None)
        mood.feel("happy")

        self.assertEqual(
            moods(run(mood, FEEL_SECONDS + 1.0))[-1],
            "idle",
        )

    def test_a_feeling_outranks_what_is_happening(self):
        mood = Mood(None)
        mood.thinking(True)
        mood.feel("confused")

        self.assertEqual(moods(run(mood, 1.0, speaking=0.5))[-1], "confused")

    def test_a_feeling_still_moves_with_the_voice(self):
        mood = Mood(None)
        mood.feel("excited")

        self.assertEqual(run(mood, 1.0, speaking=0.6)[-1], ("excited", 0.6))


class TestTheWire(unittest.TestCase):
    def test_holding_still_is_silent(self):
        mood = Mood(None)
        mood.last_sent = ("idle", 0.0, "purple", None)

        self.assertFalse(mood.worth_sending("idle", 0.0))

    def test_a_changed_mood_is_always_worth_sending(self):
        mood = Mood(None)
        mood.last_sent = ("idle", 0.0, "purple", None)

        self.assertTrue(mood.worth_sending("excited", 0.0))

    def test_a_small_level_change_is_not_worth_sending(self):
        mood = Mood(None)
        mood.last_sent = ("speaking", 0.5, "purple", None)

        self.assertFalse(
            mood.worth_sending("speaking", 0.5 + LEVEL_DEADBAND / 2)
        )
        self.assertTrue(
            mood.worth_sending("speaking", 0.5 + LEVEL_DEADBAND * 2)
        )

    def test_a_color_change_is_worth_sending(self):
        mood = Mood(None)
        mood.last_sent = ("idle", 0.0, "purple", None)

        mood.set_color("green")

        self.assertTrue(mood.worth_sending("idle", 0.0))

    def test_tiny_gaze_jitter_is_silent(self):
        mood = Mood(None)
        mood.last_sent = ("idle", 0.0, "purple", 0.4)
        mood.look_at(0.43)

        self.assertFalse(mood.worth_sending("idle", 0.0))


class FakeSocket:
    def __init__(self):
        self.messages = []

    async def send(self, message):
        self.messages.append(json.loads(message))


class TestAppearanceOnTheWire(unittest.IsolatedAsyncioTestCase):
    async def test_color_and_gaze_travel_with_the_mood(self):
        socket = FakeSocket()
        mood = Mood(socket, color="green")
        mood.look_at(-0.75)

        await mood.send("idle", 0.0)

        self.assertEqual(socket.messages[-1]["color"], "green")
        self.assertEqual(socket.messages[-1]["gaze"], -0.75)

    async def test_winks_and_celebrations_are_one_shot_events(self):
        socket = FakeSocket()
        mood = Mood(socket)
        mood.wink("left")
        mood.celebrate("gold")

        await mood.send("idle", 0.0)
        await mood.send("idle", 0.0)
        await mood.send("idle", 0.0)

        effects = [message.get("effect") for message in socket.messages]
        self.assertEqual(
            effects,
            [
                {"name": "wink", "eye": "left"},
                {"name": "celebrate", "style": "gold"},
                None,
            ],
        )


if __name__ == "__main__":
    unittest.main()
