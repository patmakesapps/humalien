"""The body must follow the speech, and stop when it does."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gestures import (
    ARM_RANGE,
    ARM_REST,
    COMMANDED,
    HOLD_SECONDS,
    LEVEL_REFERENCE,
    NOD_COMMAND_RANGE,
    NOD_RANGE,
    NOD_TRACK_UP,
    PAN_RANGE,
    Gestures,
)
from playback import level


STEP = 0.05


def run(gestures, seconds, step=STEP, loudness=None, looking=None):
    """Advance the generator, optionally feeding it speech and a face."""

    poses = []

    for _ in range(int(seconds / step)):
        if loudness is not None:
            gestures.feed(loudness)

        if looking is not None:
            gestures.look_at(*looking)

        poses.append(gestures.pose(step))

    return poses


def arms_of(pose):
    return (pose["arm_l"], pose["arm_r"])


class TestLevel(unittest.TestCase):
    def test_silence_is_zero(self):
        self.assertEqual(level(b"\x00\x00" * 480), 0.0)

    def test_a_loud_chunk_reads_louder_than_a_quiet_one(self):
        import numpy as np

        quiet = (np.ones(480, dtype="<i2") * 800).tobytes()
        loud = (np.ones(480, dtype="<i2") * 12000).tobytes()

        self.assertLess(level(quiet), level(loud))

    def test_squaring_does_not_overflow(self):
        import numpy as np

        # Full scale in int16. Squared in int16 this wraps and reads quiet.
        full = (np.ones(480, dtype="<i2") * 32767).tobytes()

        self.assertGreater(level(full), 0.9)

    def test_a_ragged_chunk_does_not_raise(self):
        self.assertEqual(level(b"\x01"), 0.0)
        self.assertIsInstance(level(b"\x00\x00\x00"), float)


class TestArms(unittest.TestCase):
    def test_silence_holds_the_arms_at_rest(self):
        arm_l, arm_r = arms_of(run(Gestures(None), seconds=2.0)[-1])

        self.assertAlmostEqual(arm_l, ARM_REST, places=3)
        self.assertAlmostEqual(arm_r, ARM_REST, places=3)

    def test_speech_lifts_the_arms_forward(self):
        poses = run(Gestures(None), seconds=2.0, loudness=LEVEL_REFERENCE)
        highest = max(max(arms_of(pose)) for pose in poses)

        self.assertGreater(highest, ARM_REST + 10.0)

    def test_the_arms_come_home_when_the_speech_stops(self):
        gestures = Gestures(None)

        run(gestures, seconds=2.0, loudness=LEVEL_REFERENCE)
        arm_l, arm_r = arms_of(run(gestures, seconds=4.0)[-1])

        self.assertAlmostEqual(arm_l, ARM_REST, places=1)
        self.assertAlmostEqual(arm_r, ARM_REST, places=1)

    def test_the_arms_do_not_move_as_one(self):
        """Both arms on the same target reads as a mechanism, not a person."""

        poses = run(Gestures(None), seconds=4.0, loudness=LEVEL_REFERENCE)

        self.assertTrue(
            any(abs(l - r) > 2.0 for l, r in map(arms_of, poses))
        )

    def test_every_pose_is_inside_the_cad_range(self):
        # Far louder than speech ever is, for as long as it takes.
        for pose in run(Gestures(None), seconds=20.0, loudness=1.0):
            for angle in arms_of(pose):
                self.assertGreaterEqual(angle, ARM_RANGE[0])
                self.assertLessEqual(angle, ARM_RANGE[1])

    def test_quiet_speech_gestures_smaller_than_loud_speech(self):
        quiet = run(Gestures(None), 6.0, loudness=LEVEL_REFERENCE * 0.25)
        loud = run(Gestures(None), 6.0, loudness=LEVEL_REFERENCE)

        self.assertLess(
            max(max(arms_of(p)) for p in quiet),
            max(max(arms_of(p)) for p in loud),
        )


class TestHead(unittest.TestCase):
    def test_the_head_never_leaves_the_observed_envelope(self):
        """Whatever the speech and the tracker do, together, for a long time.

        The node clamps this too. Both, on purpose: this file is the one that
        can be wrong, and node/humalien_node/arms.py is the one that matters.
        """

        gestures = Gestures(None)

        for corner in ((-1.0, -1.0), (1.0, 1.0), (-1.0, 1.0), (1.0, -1.0)):
            for pose in run(gestures, 8.0, loudness=1.0, looking=corner):
                self.assertGreaterEqual(pose["pan"], PAN_RANGE[0])
                self.assertLessEqual(pose["pan"], PAN_RANGE[1])
                self.assertGreaterEqual(pose["nod"], NOD_RANGE[0])
                self.assertLessEqual(pose["nod"], NOD_RANGE[1])

    def test_the_head_never_asks_for_a_big_downward_nod(self):
        """SERVO_MAP.md approved -3.6 down and nothing beyond it."""

        gestures = Gestures(None)
        poses = run(gestures, 20.0, loudness=1.0, looking=(0.0, 1.0))

        self.assertGreaterEqual(min(p["nod"] for p in poses), -3.6)

    def test_the_head_moves_gently_even_at_full_volume(self):
        """No step big enough to be a flick, before the node even sees it.

        The node is what enforces this - it acceleration-limits every axis -
        but a brain that asks for a snap and is refused still produces a
        head that lags its own gestures. Better not to ask.
        """

        gestures = Gestures(None)
        poses = run(gestures, 30.0, loudness=1.0, looking=(1.0, -1.0))

        for axis in ("pan", "nod"):
            worst = max(
                abs(b[axis] - a[axis]) / STEP
                for a, b in zip(poses, poses[1:])
            )

            self.assertLess(worst, 20.0, f"{axis} asked for {worst:.1f} deg/s")

    def test_the_head_is_quieter_than_the_arms(self):
        poses = run(Gestures(None), 12.0, loudness=LEVEL_REFERENCE)

        arms = max(abs(p["arm_l"] - ARM_REST) for p in poses)
        head = max(abs(p["nod"]) for p in poses)

        self.assertLess(head, arms / 3.0)

    def test_the_head_turns_toward_a_face(self):
        left = run(Gestures(None), 6.0, looking=(-1.0, 0.0))[-1]
        right = run(Gestures(None), 6.0, looking=(1.0, 0.0))[-1]

        self.assertGreater(left["pan"], 3.0)
        self.assertLess(right["pan"], -3.0)
        self.assertGreater(left["pan"], right["pan"])

    def test_the_head_does_not_centre_a_face_perfectly(self):
        """A robot that nails the centre reads as a security camera."""

        pose = run(Gestures(None), 8.0, looking=(1.0, 0.0))[-1]

        self.assertLess(abs(pose["pan"]), abs(PAN_RANGE[1]) * 0.9)

    def test_a_face_above_the_camera_lifts_the_head(self):
        high = run(Gestures(None), 8.0, looking=(0.0, -1.0))[-1]
        level_with = run(Gestures(None), 8.0, looking=(0.0, 0.0))[-1]

        self.assertGreater(high["nod"], level_with["nod"])
        self.assertLessEqual(high["nod"], NOD_TRACK_UP + 0.01)

    def test_losing_the_face_does_not_freeze_the_head(self):
        """It drifts. A head parked dead centre looks switched off."""

        gestures = Gestures(None)
        run(gestures, 4.0, looking=(1.0, 0.0))
        gestures.stop_looking()

        poses = run(gestures, 40.0)
        spread = max(p["pan"] for p in poses) - min(p["pan"] for p in poses)

        self.assertGreater(spread, 1.0)

    def test_the_head_drifts_before_it_has_ever_seen_anybody(self):
        poses = run(Gestures(None), 40.0)
        spread = max(p["pan"] for p in poses) - min(p["pan"] for p in poses)

        self.assertGreater(spread, 1.0)

    def test_a_stale_face_is_let_go_of(self):
        gestures = Gestures(None)
        run(gestures, 6.0, looking=(1.0, 0.0))

        turned = gestures.pose(STEP)["pan"]
        drifted = run(gestures, 30.0)[-1]["pan"]

        self.assertLess(abs(drifted), abs(turned))


class TestAskedForPoses(unittest.TestCase):
    """"Turn your head left" has to survive the gesture generator.

    `pose` rewrites every axis twenty times a second off the speech envelope.
    A commanded pose with no hold is overwritten within one frame, and the
    robot silently ignores what it was asked to do.
    """

    def test_a_commanded_pose_beats_the_speech(self):
        gestures = Gestures(None)
        gestures.command("head", "left")

        poses = run(gestures, 2.0, loudness=1.0)

        for pose in poses:
            self.assertAlmostEqual(pose["pan"], 10.0, places=3)

    def test_it_holds_through_a_face_it_would_rather_look_at(self):
        gestures = Gestures(None)
        gestures.command("head", "left")

        pose = run(gestures, 2.0, looking=(1.0, 0.0))[-1]

        self.assertAlmostEqual(pose["pan"], 10.0, places=3)

    def test_the_hold_expires_on_its_own(self):
        """It has to. Nothing else ever ends it.

        The model has no reliable moment at which it says "you may move
        again", so a hold that waited for one would freeze the robot in
        whatever position it was last told, for the rest of the session.
        """

        gestures = Gestures(None)
        gestures.command("head", "left")

        run(gestures, HOLD_SECONDS + 1.0, loudness=1.0)

        self.assertEqual(gestures.held, {})

    def test_an_unheld_axis_keeps_gesturing_meanwhile(self):
        gestures = Gestures(None)
        gestures.command("head", "left")

        poses = run(gestures, 2.0, loudness=LEVEL_REFERENCE)
        arms = [pose["arm_l"] for pose in poses]

        self.assertGreater(max(arms) - min(arms), 1.0)

    def test_a_move_this_body_cannot_make_is_refused(self):
        gestures = Gestures(None)

        self.assertIsNone(gestures.command("tail", "up"))
        self.assertIsNone(gestures.command("head", "backwards"))
        self.assertEqual(gestures.held, {})

    def test_every_commanded_pose_is_inside_the_envelope(self):
        for (part, direction), wanted in COMMANDED.items():
            gestures = Gestures(None)
            gestures.command(part, direction)

            pose = run(gestures, 0.5, loudness=1.0)[-1]

            for axis in wanted:
                self.assertAlmostEqual(
                    pose[axis], wanted[axis], places=3,
                    msg=f"{part} {direction} was clamped - it is out of range",
                )

    def test_only_a_hold_unlocks_the_bigger_upward_nod(self):
        """Speech gets the small envelope; being asked gets the larger one.

        Two ranges rather than one, so a bug in the speech envelope can never
        reach the travel that only an explicit request is allowed.
        """

        asked = Gestures(None)
        asked.command("head", "up")

        self.assertGreater(run(asked, 0.5)[-1]["nod"], NOD_RANGE[1])

        # And once it expires, the small envelope is back in force.
        run(asked, HOLD_SECONDS + 1.0, loudness=1.0)

        for pose in run(asked, 5.0, loudness=1.0, looking=(0.0, -1.0)):
            self.assertLessEqual(pose["nod"], NOD_RANGE[1] + 1e-6)

    def test_even_an_asked_for_pose_stays_inside_the_mechanism(self):
        gestures = Gestures(None)

        for (part, direction) in COMMANDED:
            gestures.command(part, direction)

            for pose in run(gestures, 1.0, loudness=1.0):
                self.assertGreaterEqual(pose["nod"], NOD_COMMAND_RANGE[0])
                self.assertLessEqual(pose["nod"], NOD_COMMAND_RANGE[1])
                self.assertGreaterEqual(pose["pan"], PAN_RANGE[0])
                self.assertLessEqual(pose["pan"], PAN_RANGE[1])

            gestures.let_go()

    def test_letting_go_hands_the_body_straight_back(self):
        gestures = Gestures(None)
        gestures.command("head", "left")
        run(gestures, 1.0)

        gestures.let_go()

        self.assertEqual(gestures.held, {})


class TestTheWire(unittest.TestCase):
    def test_holding_still_is_silent_on_the_wire(self):
        gestures = Gestures(None)
        pose = gestures.pose(STEP)
        gestures.last_sent = dict(pose)

        self.assertFalse(gestures.worth_sending(dict(pose)))

    def test_a_small_head_move_is_still_worth_sending(self):
        """The arms' deadband would swallow the head's whole range."""

        gestures = Gestures(None)
        pose = gestures.pose(STEP)
        gestures.last_sent = dict(pose)

        nudged = dict(pose)
        nudged["pan"] += 0.2

        self.assertTrue(gestures.worth_sending(nudged))

    def test_every_axis_is_on_every_frame(self):
        pose = Gestures(None).pose(STEP)

        self.assertEqual(
            sorted(pose),
            ["arm_l", "arm_r", "nod", "pan"],
        )


if __name__ == "__main__":
    unittest.main()
