"""A room with more than one person in it must not make the head hunt."""

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from attention import Attention
from gaze import FaceBox


FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# The vision loop polls at 4 Hz. Everything here runs on that clock.
POLL = 0.25


def face(x, size):
    """A face centred at x, `size` pixels square."""

    return FaceBox(
        x=int(x - size / 2),
        y=int(FRAME_HEIGHT / 2 - size / 2),
        width=int(size),
        height=int(size),
    )


def watch(attention, frames, *, start=100.0):
    """Run a scripted sequence of detections and return what was chosen."""

    chosen = []

    for index, faces in enumerate(frames):
        chosen.append(
            attention.update(
                faces,
                frame_width=FRAME_WIDTH,
                now=start + index * POLL,
            )
        )

    return chosen


def switches(chosen):
    """How many times the target actually changed person."""

    moved = 0
    previous = None

    for attended in chosen:
        if attended is None:
            continue

        here = attended.face.center[0]

        if previous is not None and abs(here - previous) > FRAME_WIDTH * 0.1:
            moved += 1

        previous = here

    return moved


class TestTwoPeople(unittest.TestCase):
    """The case that motivated this file: two people, similar size."""

    def two_of_them(self, seconds, *, jitter=6.0, seed=1):
        """Two faces the same size, with the detector noise that is real.

        Their measured areas cross over constantly. `select_primary_face`
        would return a different one of them several times a second.
        """

        noise = random.Random(seed)
        frames = []

        for _ in range(int(seconds / POLL)):
            frames.append(
                [
                    face(220, 120 + noise.uniform(-jitter, jitter)),
                    face(430, 120 + noise.uniform(-jitter, jitter)),
                ]
            )

        return frames

    def test_the_naive_rule_really_does_flicker(self):
        """Proof the problem exists, so the test below is worth something."""

        from gaze import select_primary_face

        frames = self.two_of_them(30.0)
        naive = [
            type("A", (), {"face": select_primary_face(f)})()
            for f in frames
        ]

        self.assertGreater(switches(naive), 10)

    def test_attention_does_not_hunt_between_them(self):
        # Glancing is a deliberate behaviour with its own test. Off here, so
        # this measures hunting and nothing else.
        attention = Attention(glance_every=None)

        self.assertEqual(switches(watch(attention, self.two_of_them(30.0))), 0)

    def test_it_does_not_hunt_however_noisy_the_detector_is(self):
        for seed in range(8):
            attention = Attention(glance_every=None)
            frames = self.two_of_them(30.0, jitter=14.0, seed=seed)

            self.assertEqual(
                switches(watch(attention, frames)),
                0,
                f"hunted with seed {seed}",
            )

    def test_a_crowd_does_not_make_it_worse(self):
        noise = random.Random(4)
        frames = []

        for _ in range(int(40.0 / POLL)):
            frames.append(
                [
                    face(x, 110 + noise.uniform(-10.0, 10.0))
                    for x in (110, 250, 390, 530)
                ]
            )

        attention = Attention(glance_every=None)

        self.assertEqual(switches(watch(attention, frames)), 0)


class TestSwitching(unittest.TestCase):
    """Sticking with somebody must not mean never changing your mind."""

    def test_somebody_clearly_closer_does_take_over(self):
        held = [[face(220, 120), face(430, 120)]] * int(6.0 / POLL)
        leaning_in = [[face(220, 120), face(430, 260)]] * int(6.0 / POLL)

        attention = Attention(glance_every=None)
        chosen = watch(attention, held + leaning_in)

        self.assertAlmostEqual(chosen[len(held) - 1].face.center[0], 220, delta=2)
        self.assertAlmostEqual(chosen[-1].face.center[0], 430, delta=2)

    def test_a_moment_of_leaning_in_does_not_steal_the_target(self):
        held = [[face(220, 120), face(430, 120)]] * int(6.0 / POLL)

        # Big, but for less than SWITCH_DWELL.
        blip = [[face(220, 120), face(430, 260)]] * 3

        attention = Attention(glance_every=None)
        chosen = watch(attention, held + blip + held)

        self.assertEqual(switches(chosen), 0)

    def test_the_target_survives_the_detector_dropping_frames(self):
        attention = Attention(glance_every=None)

        settled = [[face(220, 120), face(430, 120)]] * int(6.0 / POLL)
        blink = [[]] * 2
        after = [[face(226, 120), face(430, 120)]] * int(4.0 / POLL)

        chosen = watch(attention, settled + blink + after)

        self.assertEqual(switches(chosen), 0)
        self.assertAlmostEqual(chosen[-1].face.center[0], 226, delta=3)

    def test_an_empty_room_gives_up_the_target(self):
        attention = Attention(glance_every=None)

        chosen = watch(
            attention,
            [[face(220, 120)]] * 8 + [[]] * int(4.0 / POLL),
        )

        self.assertIsNone(chosen[-1])

    def test_the_first_face_is_taken_immediately(self):
        attention = Attention(glance_every=None)

        chosen = watch(attention, [[face(220, 120)]])

        self.assertIsNotNone(chosen[0])
        self.assertFalse(chosen[0].switched)


class TestGlancing(unittest.TestCase):
    def test_it_looks_at_somebody_else_and_comes_back(self):
        # A fixed source so the glance lands somewhere the test can find it.
        attention = Attention(
            glance_every=(4.0, 4.0),
            random_source=random.Random(0),
        )

        frames = [[face(220, 120), face(430, 120)]] * int(20.0 / POLL)
        chosen = watch(attention, frames)

        self.assertTrue(
            any(a.glancing for a in chosen),
            "never glanced at the other person",
        )
        self.assertFalse(chosen[-1].glancing)

    def test_it_never_glances_at_somebody_who_is_not_there(self):
        attention = Attention(
            glance_every=(2.0, 2.0),
            random_source=random.Random(0),
        )

        chosen = watch(attention, [[face(220, 120)]] * int(20.0 / POLL))

        self.assertFalse(any(a.glancing for a in chosen))
        self.assertEqual(switches(chosen), 0)


if __name__ == "__main__":
    unittest.main()
