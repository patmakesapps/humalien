"""What the eyes must never do: blind anybody, brown out, or freeze."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from humalien_node.pixels import (
    BRIGHTNESS_CEILING,
    BYTE_ORDER,
    CURRENT_BUDGET_MA,
    DEFAULT_MOOD,
    MILLIAMPS_PER_CHANNEL,
    MOODS,
    PIXELS_PER_EYE,
    PIXEL_COUNT,
    Pixels,
    RIPPLE_SECONDS,
    TICK,
)


class FakeLights:
    def __init__(self):
        self.frames = []

    def write(self, data):
        self.frames.append(data)


def milliamps(data):
    return sum(data) * MILLIAMPS_PER_CHANNEL


def run(pixels, seconds, step=TICK):
    """Render for a while and return every frame's bytes."""

    return [
        pixels.encode(pixels.frame(step))
        for _ in range(int(seconds / step))
    ]


class TestTheWireFormat(unittest.TestCase):
    def test_a_frame_is_three_bytes_per_pixel(self):
        self.assertEqual(len(run(Pixels(), TICK * 2)[0]), PIXEL_COUNT * 3)

    def test_the_byte_order_is_grb_not_rgb(self):
        """NEOPIXEL_MAP.md: dim purple is bytes([0, 5, 5]), green first.

        Get this wrong and the brand colour comes out green.
        """

        self.assertEqual(BYTE_ORDER, (1, 0, 2))

    def test_pure_red_lands_in_the_second_byte(self):
        pixels = Pixels(brightness=BRIGHTNESS_CEILING)

        data = pixels.encode([(1.0, 0.0, 0.0)] * PIXEL_COUNT)

        self.assertEqual(data[0], 0)        # green
        self.assertEqual(data[2], 0)        # blue
        self.assertAlmostEqual(
            data[1],                        # red
            255 * BRIGHTNESS_CEILING,
            delta=2,
        )

    def test_the_eyes_are_purple_by_default(self):
        """Blue and red both well lit, green barely. That is the brand."""

        pixels = Pixels(brightness=BRIGHTNESS_CEILING)
        pixels.set(mood="idle")

        brightest = max(run(pixels, 6.0), key=sum)
        green, red, blue = brightest[0::3], brightest[1::3], brightest[2::3]

        self.assertGreater(max(blue), max(green) * 2)
        self.assertGreater(max(red), max(green))

    def test_no_mood_ever_leaves_the_purple_axis(self):
        """Every pixel of every mood, always: blue >= red >= green.

        The whole palette is one violet ramp - EMBER, DEEP, PURPLE, PALE,
        FLARE - and each satisfies that ordering, so every blend and every
        dimming of them does too. An earlier version travelled to cyan for
        listening and magenta for excitement, and the eyes stopped reading as
        one product. This is the rule that keeps them on brand: break it and
        a hue has been introduced, whatever the intention was.
        """

        for name in MOODS:
            pixels = Pixels(brightness=BRIGHTNESS_CEILING)
            pixels.set(mood=name, level=1.0)

            for frame in run(pixels, 10.0):
                for index in range(PIXEL_COUNT):
                    green, red, blue = frame[index * 3: index * 3 + 3]

                    # A byte of slack: these are rounded from floats.
                    self.assertLessEqual(
                        green, red + 1,
                        f"{name} px{index} is greener than it is red",
                    )
                    self.assertLessEqual(
                        red, blue + 1,
                        f"{name} px{index} is redder than it is blue",
                    )


class TestSafety(unittest.TestCase):
    def test_no_mood_can_pull_more_than_the_budget(self):
        for name in MOODS:
            pixels = Pixels(brightness=BRIGHTNESS_CEILING)
            pixels.set(mood=name, level=1.0)

            worst = max(milliamps(frame) for frame in run(pixels, 12.0))

            self.assertLessEqual(
                worst,
                CURRENT_BUDGET_MA + 1.0,
                f"{name} drew {worst:.0f} mA",
            )

    def test_the_current_guard_dims_rather_than_clips(self):
        """Clipping changes which mood you are looking at. Dimming does not."""

        pixels = Pixels(brightness=1.0)

        data = pixels.encode([(1.0, 1.0, 1.0)] * PIXEL_COUNT)
        lit = [value for value in data if value]

        self.assertLessEqual(milliamps(data), CURRENT_BUDGET_MA + 1.0)

        # Every pixel still lit, and all of them equally - a clip would have
        # left some at full and taken others to nothing.
        self.assertEqual(len(lit), PIXEL_COUNT * 3)
        self.assertEqual(len(set(lit)), 1)

    def test_a_brightness_from_the_brain_cannot_exceed_the_ceiling(self):
        pixels = Pixels()
        pixels.set(brightness=99.0)

        self.assertEqual(pixels.brightness, BRIGHTNESS_CEILING)

    def test_a_negative_brightness_is_not_a_negative_pixel(self):
        pixels = Pixels()
        pixels.set(brightness=-5.0)

        self.assertEqual(pixels.brightness, 0.0)
        self.assertEqual(set(run(pixels, 1.0)[-1]), {0})

    def test_an_unknown_mood_is_refused_and_changes_nothing(self):
        pixels = Pixels()
        pixels.set(mood="happy")

        self.assertFalse(pixels.set(mood="smug"))
        self.assertEqual(pixels.mood, "happy")

    def test_clear_really_is_all_zeroes(self):
        """NeoPixels latch. Anything less leaves a face lit in an empty room."""

        lights = FakeLights()
        pixels = Pixels(lights)
        pixels.set(mood="excited", level=1.0)

        run(pixels, 1.0)
        pixels.clear()

        self.assertEqual(lights.frames[-1], bytes(PIXEL_COUNT * 3))


class TestBeingAlive(unittest.TestCase):
    def test_every_mood_except_off_actually_moves(self):
        for name in MOODS:
            pixels = Pixels(brightness=BRIGHTNESS_CEILING)
            pixels.set(mood=name, level=0.5)

            frames = set(run(pixels, 10.0))

            if name == "off":
                self.assertEqual(len(frames), 1, name)
            else:
                self.assertGreater(len(frames), 20, f"{name} barely moves")

    def test_a_mood_change_sends_a_ripple_round_the_ring(self):
        """It fires on the change, travels, and is gone. Not a loop.

        A wave that ran on a timer would be decoration. Firing it on the
        change is what makes it read as the robot reacting to something.
        """

        pixels = Pixels(brightness=BRIGHTNESS_CEILING)
        pixels.set(mood="idle")

        run(pixels, 4.0)
        settled = sum(run(pixels, 1.0)[-1])

        pixels.set(mood="happy")

        during = [sum(frame) for frame in run(pixels, RIPPLE_SECONDS)]
        after = [sum(frame) for frame in run(pixels, 3.0)[-20:]]

        self.assertGreater(max(during), settled)
        self.assertLess(max(after), max(during))

    def test_the_ripple_travels_rather_than_flashing(self):
        """The top of the ring peaks before the bottom does."""

        pixels = Pixels(brightness=BRIGHTNESS_CEILING)
        pixels.set(mood="idle")
        run(pixels, 3.0)

        pixels.set(mood="excited")
        frames = run(pixels, RIPPLE_SECONDS)

        def peak_at(index):
            values = [sum(f[index * 3: index * 3 + 3]) for f in frames]

            return values.index(max(values))

        # Pixel 0 is twelve o'clock; pixel 6 is the bottom of the same ring.
        self.assertLess(peak_at(0), peak_at(6))

    def test_the_eyes_blink(self):
        pixels = Pixels(brightness=BRIGHTNESS_CEILING)
        pixels.set(mood="idle")

        # The top of each ring goes dark and comes back. Sum over the whole
        # frame is the cheapest way to see a lid pass.
        totals = [sum(frame) for frame in run(pixels, 20.0)]

        self.assertLess(min(totals), max(totals) * 0.5)

    def test_the_eyes_do_not_blink_while_they_are_off(self):
        pixels = Pixels()
        pixels.set(mood="off")

        self.assertEqual({sum(frame) for frame in run(pixels, 20.0)}, {0})

    def test_the_two_eyes_are_not_always_identical(self):
        """A mood that draws both rings the same reads as two gauges."""

        pixels = Pixels(brightness=BRIGHTNESS_CEILING)
        pixels.set(mood="curious")

        differ = 0

        for frame in run(pixels, 6.0):
            half = PIXELS_PER_EYE * 3

            if frame[:half] != frame[half:]:
                differ += 1

        self.assertGreater(differ, 10)

    def test_louder_speech_lights_more_of_the_eye(self):
        def brightest(level):
            pixels = Pixels(brightness=BRIGHTNESS_CEILING)
            pixels.set(mood="speaking", level=level)

            return max(sum(frame) for frame in run(pixels, 6.0))

        self.assertGreater(brightest(1.0), brightest(0.2) * 1.5)

    def test_a_brain_that_stops_talking_does_not_leave_an_eye_stuck_bright(self):
        """The level goes stale on its own, without being told to.

        A brain that dies mid-word sends no "stop" - it simply stops. The
        eyes have to notice by themselves or the robot is left shouting at
        an empty room in full brightness.
        """

        pixels = Pixels(brightness=BRIGHTNESS_CEILING)

        talking = []

        for _ in range(int(2.0 / TICK)):
            pixels.set(mood="speaking", level=1.0)
            talking.append(sum(pixels.encode(pixels.frame(TICK))))

        loud = max(talking)

        # The brain stops dead. No further updates of any kind.
        quiet = max(sum(frame) for frame in run(pixels, 4.0)[-20:])

        self.assertLess(quiet, loud * 0.5)


class TestTheWire(unittest.TestCase):
    def test_an_unchanged_frame_is_not_resent(self):
        """They latch. Holding still should cost nothing on the GPIO."""

        lights = FakeLights()
        pixels = Pixels(lights)
        pixels.set(mood="off")

        for _ in range(50):
            pixels.write(pixels.encode(pixels.frame(TICK)))

        self.assertEqual(len(lights.frames), 1)

    def test_a_changed_frame_is_sent(self):
        lights = FakeLights()
        pixels = Pixels(lights)
        pixels.set(mood="thinking")

        for _ in range(50):
            pixels.write(pixels.encode(pixels.frame(TICK)))

        self.assertGreater(len(lights.frames), 20)

    def test_it_starts_somewhere_sensible_with_no_instructions(self):
        self.assertIn(DEFAULT_MOOD, MOODS)
        self.assertEqual(Pixels().mood, DEFAULT_MOOD)


if __name__ == "__main__":
    unittest.main()
