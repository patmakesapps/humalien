"""The body must follow the speech, and stop when it does."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gestures import (
    ARM_RANGE,
    BEAT_HZ,
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
import gestures as gestures_module
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

    def test_the_head_never_asks_for_more_than_the_node_can_give(self):
        """The brain must not out-run the servo it is driving.

        The node acceleration-limits every axis, so asking for more than it
        can deliver is not dangerous - it is just a head visibly lagging its
        own gestures, arriving at each pose after the sentence that wanted it.

        These caps are node/humalien_node/arms.py's, walked on the robot and
        approved. This test used to assert a flat 20 deg/s, which was written
        when the node itself capped at 18 and quietly went stale the day that
        changed.
        """

        # PAN_SLEW_DPS and NOD_SLEW_DPS in node/humalien_node/arms.py.
        caps = {"pan": 144.0, "nod": 108.0}

        gestures = Gestures(None)
        poses = run(gestures, 30.0, loudness=1.0, looking=(1.0, -1.0))

        for axis, cap in caps.items():
            worst = max(
                abs(b[axis] - a[axis]) / STEP
                for a, b in zip(poses, poses[1:])
            )

            self.assertLess(
                worst, cap,
                f"{axis} asked for {worst:.1f} deg/s of {cap:.0f} available",
            )

    def test_the_head_actually_moves_vertically(self):
        """The mechanism goes +40 up and -3.6 down, so a nod cannot dip.

        Swinging a little either side of zero - which this did at first -
        spends nearly all its travel on the 3.6 degrees that do not exist,
        and reads as a head that never moves vertically at all. It raises its
        chin while talking and swings around that instead.
        """

        poses = run(Gestures(None), 20.0, loudness=1.0)
        nods = [pose["nod"] for pose in poses]

        self.assertGreater(max(nods) - min(nods), 10.0)
        self.assertGreater(max(nods), 12.0)

    def test_the_head_actually_moves_side_to_side(self):
        poses = run(Gestures(None), 20.0, loudness=1.0)
        pans = [pose["pan"] for pose in poses]

        self.assertGreater(max(pans) - min(pans), 15.0)

    def test_the_head_is_still_quieter_than_the_arms(self):
        """Not by as much as it was, but the hands should still lead."""

        poses = run(Gestures(None), 12.0, loudness=LEVEL_REFERENCE)

        arms = max(abs(p["arm_l"] - ARM_REST) for p in poses)
        head = max(abs(p["nod"]) for p in poses)

        self.assertLess(head, arms / 2.0)

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


def feed_run(gestures, loudnesses, step=STEP):
    """Advance the generator on a changing voice, rather than a flat one."""

    return [gestures.pose(step) for value in loudnesses if not gestures.feed(value)]


def reach(poses):
    """How far forward the arms actually got."""

    return max(max(pose["arm_l"], pose["arm_r"]) for pose in poses)


class TestEmphasis(unittest.TestCase):
    """Every so often a gesture should be bigger than the rest of them.

    Driven from the voice, not the words - nothing reads the transcript. The
    model genuinely gets louder when it is making a point, and that is
    already measured, so emphasis is how far above its own recent baseline
    the envelope has climbed.
    """

    def steady(self, seconds, loudness):
        return [loudness] * int(seconds / STEP)

    def test_getting_louder_mid_sentence_makes_a_bigger_gesture(self):
        quiet = 0.35 * LEVEL_REFERENCE

        settled = feed_run(Gestures(None), self.steady(8.0, quiet))
        excited = feed_run(
            Gestures(None), self.steady(8.0, quiet) + self.steady(2.0, LEVEL_REFERENCE)
        )

        self.assertGreater(reach(excited), reach(settled) + 5.0)

    def test_starting_to_talk_is_not_emphasis(self):
        """Otherwise every reply opens with the big gesture, which is the
        same as having no emphasis at all - just louder throughout."""

        gestures = Gestures(None)

        feed_run(gestures, self.steady(1.0, LEVEL_REFERENCE))

        self.assertLess(gestures.emphasis, 0.25)

    def test_talking_loudly_all_along_settles_back_down(self):
        """Emphasis is relative. Loud is the volume knob; louder is a point."""

        gestures = Gestures(None)

        feed_run(gestures, self.steady(12.0, LEVEL_REFERENCE))

        self.assertLess(gestures.emphasis, 0.2)

    def test_the_moment_passes(self):
        gestures = Gestures(None)
        quiet = 0.35 * LEVEL_REFERENCE

        feed_run(gestures, self.steady(8.0, quiet) + self.steady(1.0, LEVEL_REFERENCE))
        at_the_peak = gestures.emphasis

        feed_run(gestures, self.steady(6.0, quiet))

        self.assertGreater(at_the_peak, 0.4)
        self.assertLess(gestures.emphasis, at_the_peak / 3.0)

    def test_an_emphatic_gesture_is_quicker_as_well_as_bigger(self):
        gestures = Gestures(None)
        quiet = 0.35 * LEVEL_REFERENCE

        feed_run(gestures, self.steady(8.0, quiet))
        before = gestures.phase

        feed_run(gestures, self.steady(2.0, quiet))
        calm = gestures.phase - before

        feed_run(gestures, self.steady(2.0, LEVEL_REFERENCE))
        loud = gestures.phase - (before + calm)

        # Both stretches are two seconds; the emphatic one covers more of
        # the beat cycle, so the hands are moving faster through it.
        self.assertGreater(loud, calm)

    def test_sleeping_forgets_the_moment(self):
        # Otherwise waking up resumes mid-gesture at whatever size the last
        # sentence had reached.
        gestures = Gestures(None)
        quiet = 0.35 * LEVEL_REFERENCE

        feed_run(gestures, self.steady(8.0, quiet) + self.steady(1.0, LEVEL_REFERENCE))
        gestures.sleep(True)

        self.assertEqual(gestures.emphasis, 0.0)

    def test_even_at_full_emphasis_the_arms_stay_inside_the_range(self):
        gestures = Gestures(None)
        quiet = 0.35 * LEVEL_REFERENCE

        poses = feed_run(
            gestures, self.steady(8.0, quiet) + self.steady(6.0, 4.0 * LEVEL_REFERENCE)
        )

        for pose in poses:
            self.assertGreaterEqual(pose["arm_l"], ARM_RANGE[0])
            self.assertLessEqual(pose["arm_l"], ARM_RANGE[1])
            self.assertLessEqual(pose["arm_r"], ARM_RANGE[1])

    def test_emphasis_does_not_make_the_arms_much_harder_to_drive(self):
        """A sudden jump in volume ALREADY asks the arms for about 207 deg/s
        against the 100 node/humalien_node/arms.py can give - that predates
        emphasis and is what the node's acceleration limiting exists to
        smooth. Emphasis rides on top of that spike, so what matters is that
        it does not pile much more onto it: past a point the gesture is
        shaped by how long the servo sits against its limiter rather than by
        anything in this file.
        """

        quiet = 0.35 * LEVEL_REFERENCE
        loud = self.steady(8.0, quiet) + self.steady(6.0, 4.0 * LEVEL_REFERENCE)

        def peak(lift, swing, beat):
            saved = (
                gestures_module.EMPHASIS_LIFT,
                gestures_module.EMPHASIS_SWING,
                gestures_module.EMPHASIS_BEAT,
            )
            (
                gestures_module.EMPHASIS_LIFT,
                gestures_module.EMPHASIS_SWING,
                gestures_module.EMPHASIS_BEAT,
            ) = (lift, swing, beat)
            try:
                poses = feed_run(Gestures(None), loud)

                return max(
                    abs(b[axis] - a[axis]) / STEP
                    for a, b in zip(poses, poses[1:])
                    for axis in ("arm_l", "arm_r")
                )
            finally:
                (
                    gestures_module.EMPHASIS_LIFT,
                    gestures_module.EMPHASIS_SWING,
                    gestures_module.EMPHASIS_BEAT,
                ) = saved

        without = peak(0.0, 0.0, 0.0)
        with_it = peak(
            gestures_module.EMPHASIS_LIFT,
            gestures_module.EMPHASIS_SWING,
            gestures_module.EMPHASIS_BEAT,
        )

        self.assertLess(
            with_it, without * 1.2,
            f"emphasis took the arms from {without:.0f} to {with_it:.0f} deg/s",
        )

class TestAskedForPoses(unittest.TestCase):
    """"Turn your head left" has to survive the gesture generator.

    `pose` rewrites every axis twenty times a second off the speech envelope.
    A commanded pose with no hold is overwritten within one frame, and the
    robot silently ignores what it was asked to do.
    """

    def test_a_commanded_pose_beats_the_speech(self):
        gestures = Gestures(None)
        gestures.command("head", "left")

        wanted = COMMANDED[("head", "left")]["pan"]

        for pose in run(gestures, 2.0, loudness=1.0):
            self.assertAlmostEqual(pose["pan"], wanted, places=3)

    def test_it_holds_through_a_face_it_would_rather_look_at(self):
        gestures = Gestures(None)
        gestures.command("head", "left")

        pose = run(gestures, 2.0, looking=(1.0, 0.0))[-1]

        self.assertAlmostEqual(
            pose["pan"], COMMANDED[("head", "left")]["pan"], places=3
        )

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

        # Visibly past anything the robot reaches on its own, or asking it
        # to look up is indistinguishable from it carrying on talking.
        self.assertGreater(run(asked, 0.5)[-1]["nod"], NOD_RANGE[1] + 5.0)

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
