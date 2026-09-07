import unittest

import system_prompt


PERSONA = "# How you talk\n\nWarm, dry, brief."

FULL_BODY = {
    "camera": "Arducam OV9782 USB Camera",
    "moves": True,
    "eyes": True,
    "tracking": True,
}


def build(**overrides):
    settings = {"persona": PERSONA}
    settings.update(overrides)

    return system_prompt.build(**settings)


class IdentityTests(unittest.TestCase):
    """The transcript this file exists because of.

    Tubby told the person building it that it could not control a robot,
    four times, while following that person's face with its head.
    """

    def test_says_what_tubby_is_before_how_it_talks(self):
        prompt = build()

        self.assertLess(prompt.index("What you are"), prompt.index("How you talk"))

    def test_the_persona_is_still_in_there(self):
        self.assertIn("Warm, dry, brief.", build())

    def test_says_it_is_a_robot_and_that_pat_is_building_it(self):
        prompt = build().lower()

        self.assertIn("you are a robot", prompt)
        self.assertIn("pat built you and is still building you", prompt)

    def test_tells_it_not_to_argue_about_its_own_capabilities(self):
        prompt = build().lower()

        self.assertIn("never argue about what you are", prompt)
        self.assertIn("never recite what you cannot do", prompt)

    def test_the_facts_are_marked_as_outranking_the_character_notes(self):
        # Both halves are one instructions string, so which wins has to be
        # stated - the model has no other way to know.
        self.assertIn("the facts win", build())


class BodyTests(unittest.TestCase):
    def test_names_the_camera_it_will_see_through(self):
        self.assertIn("Arducam OV9782 USB Camera", build(body=FULL_BODY))

    def test_a_brain_with_no_body_is_told_not_to_offer_to_move(self):
        prompt = build(body={"camera": "some webcam"})

        self.assertIn("not connected this run", prompt)
        self.assertNotIn("both arms move, and they are", prompt)

    def test_a_brain_with_no_camera_is_told_it_cannot_see(self):
        prompt = build(body={"moves": True})

        self.assertIn("no working camera", prompt)

    def test_a_body_is_described_as_working_when_it_is(self):
        prompt = build(body=FULL_BODY)

        self.assertIn("both arms move", prompt)
        self.assertNotIn("not connected this run", prompt)


class AbilityTests(unittest.TestCase):
    def test_lists_the_tools_that_were_actually_registered(self):
        prompt = build(tools=["look", "recall", "sleep"])

        self.assertIn("look, recall, sleep", prompt)

    def test_says_there_is_nothing_else_to_invent(self):
        self.assertIn("nothing to invent", build(tools=["look"]))

    def test_a_run_with_no_tools_says_so_rather_than_listing_none(self):
        prompt = build(tools=[])

        self.assertIn("Nothing is wired up this run", prompt)


class MemoryTests(unittest.TestCase):
    """What makes it feel like memory rather than a lookup."""

    def test_what_it_knows_is_in_the_prompt_not_behind_a_tool_call(self):
        prompt = build(memories=[{"id": 4, "text": "Pat is printing a desk bot."}])

        self.assertIn("Pat is printing a desk bot.", prompt)

    def test_carries_the_ids_so_a_memory_can_be_revised_without_fetching(self):
        prompt = build(memories=[{"id": 41, "text": "Something."}])

        self.assertIn("41. Something.", prompt)

    def test_stops_at_the_limit_and_says_how_many_are_left(self):
        many = [{"id": i, "text": f"fact {i}"} for i in range(system_prompt.MEMORY_LIMIT + 5)]

        prompt = build(memories=many)

        self.assertIn("and 5 older ones", prompt)
        self.assertNotIn(f"fact {system_prompt.MEMORY_LIMIT + 4}", prompt)

    def test_an_empty_memory_is_not_described_as_a_full_one(self):
        prompt = build(memories=[])

        self.assertIn("Nothing yet.", prompt)

    def test_never_calls_its_memory_notes_or_records(self):
        prompt = build(memories=[{"id": 1, "text": "x"}]).lower()

        self.assertIn("never talk about it as notes", prompt)


class PeopleTests(unittest.TestCase):
    def test_names_who_it_has_met(self):
        self.assertIn("Pat, Carter", build(people=["Pat", "Carter"]))

    def test_knowing_nobody_is_said_plainly(self):
        self.assertIn("have not met anybody yet", build(people=[]))

    def test_caps_a_long_guest_list(self):
        crowd = [f"person{i}" for i in range(system_prompt.PEOPLE_LIMIT + 3)]

        prompt = build(people=crowd)

        self.assertNotIn(f"person{system_prompt.PEOPLE_LIMIT + 2}", prompt)


class ClockTests(unittest.TestCase):
    def test_states_the_date_so_relative_days_are_not_guessed(self):
        # 6 September 2026 was a Sunday.
        when = __import__("datetime").datetime(2026, 9, 6, 20, 41).timestamp()

        prompt = build(now=when)

        self.assertIn("Sunday 6 September 2026", prompt)
        self.assertIn("8:41 pm", prompt)

    def test_midnight_and_noon_do_not_come_out_as_zero(self):
        datetime = __import__("datetime").datetime

        self.assertIn("12:00 am", build(now=datetime(2026, 9, 6, 0, 0).timestamp()))
        self.assertIn("12:00 pm", build(now=datetime(2026, 9, 6, 12, 0).timestamp()))


if __name__ == "__main__":
    unittest.main()
