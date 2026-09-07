import asyncio
import sys
import unittest
import unittest.mock

import camera
from camera import Camera, choose, in_preference_order, requested


ARDUCAM = Camera(1, "Arducam OV9782 USB Camera")
WEBCAM = Camera(0, "USB2.0 HD IR UVC WebCam")
CAPTURE_CARD = Camera(2, "Elgato Cam Link")


class ChoosingTests(unittest.TestCase):
    def test_prefers_the_arducam_over_the_built_in_webcam(self):
        self.assertEqual(choose(found=[WEBCAM, ARDUCAM]), ARDUCAM)

    def test_finds_the_arducam_wherever_it_lands_in_the_list(self):
        found = [WEBCAM, CAPTURE_CARD, ARDUCAM]

        self.assertEqual(choose(found=found), ARDUCAM)

    def test_falls_back_to_the_webcam_when_the_arducam_is_unplugged(self):
        self.assertEqual(choose(found=[WEBCAM, CAPTURE_CARD]), WEBCAM)

    def test_falls_back_to_index_zero_when_nothing_can_be_named(self):
        # No pygrabber on Windows, or a platform with no enumeration at all.
        self.assertEqual(choose(found=[]).source, 0)

    def test_the_webcam_stays_on_the_list_behind_the_arducam(self):
        # A listed but busy Arducam must not leave Humalien blind.
        order = in_preference_order(found=[WEBCAM, ARDUCAM])

        self.assertEqual([c.source for c in order], [1, 0])

    def test_matching_ignores_case(self):
        self.assertEqual(choose(found=[WEBCAM, Camera(1, "ARDUCAM B0332")]).source, 1)


class ExplicitRequestTests(unittest.TestCase):
    def test_a_pinned_index_wins_over_the_arducam(self):
        self.assertEqual(choose("0", found=[WEBCAM, ARDUCAM]).source, 0)

    def test_a_pinned_index_becomes_a_number(self):
        self.assertEqual(requested("2").source, 2)

    def test_a_pinned_path_stays_a_string(self):
        self.assertEqual(requested("/dev/video2").source, "/dev/video2")

    def test_a_pinned_device_is_never_silently_swapped(self):
        # If somebody named a device, failing is better than using another.
        order = in_preference_order("/dev/video9", found=[WEBCAM, ARDUCAM])

        self.assertEqual([c.source for c in order], ["/dev/video9"])


class WorkerThreadTests(unittest.TestCase):
    """The bug that made the robot use the laptop webcam all evening.

    Eyes opens its camera on a worker thread. On Windows the names come from
    DirectShow, DirectShow is COM, and COM is per-thread - so enumeration
    there died with "CoInitialize has not been called", the failure was
    swallowed, and camera.py fell back to index 0 without a word. Every
    check ran from a script, on the main thread, and passed.
    """

    @unittest.skipUnless(sys.platform == "win32", "COM is a Windows problem")
    def test_the_same_cameras_are_found_off_the_main_thread(self):
        if not camera.attached():
            self.skipTest("no cameras attached to this machine")

        async def from_a_worker():
            return await asyncio.to_thread(camera.attached)

        self.assertEqual(
            [c.name for c in asyncio.run(from_a_worker())],
            [c.name for c in camera.attached()],
        )

    @unittest.skipUnless(sys.platform == "win32", "COM is a Windows problem")
    def test_the_preferred_camera_is_still_preferred_off_the_main_thread(self):
        if not camera.attached():
            self.skipTest("no cameras attached to this machine")

        async def from_a_worker():
            return await asyncio.to_thread(choose)

        self.assertEqual(asyncio.run(from_a_worker()).name, choose().name)


class QuietFailureTests(unittest.TestCase):
    """Falling back to index 0 is right. Doing it silently is not.

    A silent fallback is a different camera, pointing somewhere else, for a
    whole session - which is exactly how the COM bug above went unnoticed.
    """

    @unittest.skipUnless(sys.platform == "win32", "the DirectShow path")
    def test_being_unable_to_read_the_names_is_said_out_loud(self):
        try:
            from pygrabber import dshow_graph
        except ImportError:
            self.skipTest("pygrabber is not installed")

        def broken():
            raise OSError("CoInitialize has not been called")

        said = []

        with unittest.mock.patch.object(dshow_graph, "FilterGraph", broken):
            found = camera._windows_cameras(said.append)

        self.assertEqual(found, [])
        self.assertEqual(len(said), 1)
        self.assertIn("CoInitialize", said[0])

    @unittest.skipUnless(sys.platform == "win32", "the DirectShow path")
    def test_a_failure_still_leaves_a_camera_to_open(self):
        try:
            from pygrabber import dshow_graph
        except ImportError:
            self.skipTest("pygrabber is not installed")

        def broken():
            raise OSError("nope")

        with unittest.mock.patch.object(dshow_graph, "FilterGraph", broken):
            order = in_preference_order()

        self.assertEqual([c.source for c in order], [0])


if __name__ == "__main__":
    unittest.main()
