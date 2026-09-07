import unittest

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


if __name__ == "__main__":
    unittest.main()
