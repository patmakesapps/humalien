"""The bench tool for the desk bot's eyes: moods, brightness, ring order.

    ssh into the Pi, then:  python -m humalien_node.pixel_bench

This is also where node/NEOPIXEL_MAP.md's post-solder test lives, as `order`.
Run that first on a freshly soldered pair: it lights the first ring red and
the second blue, and whichever eye comes up red is logical pixels 0-11. Set
FIRST_RING_IS_LEFT in pixels.py from what you see, and record it in
NEOPIXEL_MAP.md, which still says the order was never established.

START DIM
---------
NEOPIXEL_MAP.md found 48 per lit channel uncomfortably bright on a BARE
ring. These sit behind printed diffusers, which is a different thing, so the
default here is low and `bright` walks it up. Whatever you land on goes into
BRIGHTNESS in pixels.py, or into HUMALIEN_EYE_BRIGHTNESS in brain/.env if you
would rather set it from the brain.

Nothing here can exceed BRIGHTNESS_CEILING, and no frame may draw more than
CURRENT_BUDGET_MA however bright a mood asks to be.

The eyes are cleared on the way out. They latch: a bench that simply exited
would leave the last frame lit until the power went.
"""

import sys
import time

from humalien_node.pixels import (
    BRIGHTNESS_CEILING,
    CURRENT_BUDGET_MA,
    FIRST_RING_IS_LEFT,
    EYE_COLORS,
    MILLIAMPS_PER_CHANNEL,
    MOODS,
    PIXELS_PER_EYE,
    PIXEL_COUNT,
    Pi5NeoPixelWrite,
    Pixels,
    TICK,
)


HELP = """\
  <mood>            show one: %s
  level <0..1>      how loud the robot is pretending to be
  bright <0..%.2f>  the whole frame, live
  color <name>      shared eye color: %s
  wink <eye>        wink the robot's own left or right eye
  celebrate <kind> brief gold or rainbow ripple
  cycle             every mood in turn, a few seconds each
  order             NEOPIXEL_MAP.md's post-solder test - which eye is first
  clock             light one pixel at a time, to find PIXEL_ZERO_DEGREES
  draw              what the current mood is drawing, per pixel, as numbers
  off               all 24 pixels dark
  q                 clear and quit
""" % (
    ", ".join(name for name in MOODS if name != "off"),
    BRIGHTNESS_CEILING,
    ", ".join(EYE_COLORS),
)


def play(pixels, seconds):
    """Render for a while, at the rate the server would."""

    for _ in range(max(1, int(seconds / TICK))):
        pixels.write(pixels.encode(pixels.frame(TICK)))
        time.sleep(TICK)


def raw(pixels, colors, seconds=0.0):
    """Put exact colours up, bypassing the moods. For the wiring tests."""

    pixels.write(pixels.encode(colors))

    if seconds:
        time.sleep(seconds)


def order(pixels):
    """NEOPIXEL_MAP.md's post-solder test, at the brightness it asks for."""

    print("  first ring RED, second ring BLUE. Look at the robot.")
    print("")

    red = [(1.0, 0.0, 0.0)] * PIXELS_PER_EYE
    blue = [(0.0, 0.0, 1.0)] * PIXELS_PER_EYE

    was = pixels.brightness

    # NEOPIXEL_MAP.md: 5 per lit channel is the bench value, and 48 was
    # uncomfortable. 5/255 is what that means as a scale.
    pixels.brightness = 5.0 / 255.0
    raw(pixels, red + blue, seconds=6.0)
    pixels.brightness = was

    print("  Which eye was RED - the robot's own left or right?")
    print("")
    print("  RED on its LEFT   ->  FIRST_RING_IS_LEFT = True")
    print("  RED on its RIGHT  ->  FIRST_RING_IS_LEFT = False")
    print("")
    print("  pixels.py currently says FIRST_RING_IS_LEFT = %s" %
          FIRST_RING_IS_LEFT)
    print("  Record the answer in node/NEOPIXEL_MAP.md - it still says the")
    print("  order was never established.")
    print("")
    print("  If only ONE ring lit: power down and check the second ring's")
    print("  5 V, the common ground, and first DOUT to second DIN.")


def clock(pixels):
    """One pixel at a time, so PIXEL_ZERO_DEGREES can be set by eye."""

    print("  lighting one pixel per ring at a time, 0 to %d."
          % (PIXELS_PER_EYE - 1))
    print("  Watch the LEFT eye and note where pixel 0 sits on its face.")
    print("  PIXEL_ZERO_DEGREES is that position, clockwise from 12 o'clock.")
    print("")

    for index in range(PIXELS_PER_EYE):
        colors = [(0.0, 0.0, 0.0)] * PIXEL_COUNT
        colors[index] = (1.0, 1.0, 1.0)
        colors[index + PIXELS_PER_EYE] = (1.0, 1.0, 1.0)

        print("  pixel %d" % index)
        raw(pixels, colors, seconds=1.2)


def draw(pixels):
    """What the current mood is putting out, as numbers rather than light."""

    data = pixels.encode(pixels.frame(TICK))

    print("  mood %s, color %s, level %.2f, brightness %.2f"
          % (pixels.mood, pixels.color, pixels.level, pixels.brightness))
    print("  eye  px   G   R   B")

    for index in range(PIXEL_COUNT):
        green, red, blue = data[index * 3: index * 3 + 3]
        eye = "1st" if index < PIXELS_PER_EYE else "2nd"

        print("  %s  %2d %3d %3d %3d"
              % (eye, index % PIXELS_PER_EYE, green, red, blue))

    print("  draw %.0f mA of a %.0f mA budget"
          % (sum(data) * MILLIAMPS_PER_CHANNEL, CURRENT_BUDGET_MA))


def cycle(pixels):
    print("  every mood in turn. ctrl-c to stop.")

    try:
        for name in MOODS:
            if name == "off":
                continue

            print("  %s" % name)
            pixels.set(mood=name)
            play(pixels, 4.0)

    except KeyboardInterrupt:
        print("\n  stopped")


def main():
    try:
        driver = Pi5NeoPixelWrite()
    except Exception as error:
        print("No NeoPixels: %s" % error)
        print("Is this the Pi 5, and is adafruit_raspberry_pi5_neopixel_write")
        print("installed? See node/NEOPIXEL_MAP.md.")
        return 1

    pixels = Pixels(driver)

    print("eye bench. %d pixels on GPIO13, %d per eye."
          % (PIXEL_COUNT, PIXELS_PER_EYE))
    print("brightness %.2f (ceiling %.2f). start dim.\n%s"
          % (pixels.brightness, BRIGHTNESS_CEILING, HELP))

    try:
        while True:
            try:
                words = input("> ").strip().lower().split()
            except EOFError:
                break

            if not words:
                continue

            command, args = words[0], words[1:]

            try:
                if command == "q":
                    break

                elif command in MOODS:
                    pixels.set(mood=command)
                    print("  %s. ctrl-c to stop." % command)

                    try:
                        while True:
                            play(pixels, 1.0)
                    except KeyboardInterrupt:
                        print("\n  stopped")

                elif command == "level" and args:
                    pixels.set(level=float(args[0]))
                    print("  level %.2f" % pixels.level)
                    play(pixels, 1.0)

                elif command == "bright" and args:
                    pixels.set(brightness=float(args[0]))
                    print("  brightness %.3f  ->  paste into pixels.py:"
                          % pixels.brightness)
                    print("  BRIGHTNESS = %.3f" % pixels.brightness)
                    play(pixels, 1.0)

                elif command == "color" and args and args[0] in EYE_COLORS:
                    pixels.set(color=args[0])
                    print("  both eyes -> %s" % args[0])
                    play(pixels, 1.0)

                elif command == "wink" and args and args[0] in ("left", "right"):
                    pixels.set(effect={"name": "wink", "eye": args[0]})
                    play(pixels, 0.5)

                elif command == "celebrate" and args and args[0] in (
                    "gold",
                    "rainbow",
                ):
                    pixels.set(
                        effect={"name": "celebrate", "style": args[0]}
                    )
                    play(pixels, 2.0)

                elif command == "cycle":
                    cycle(pixels)

                elif command == "order":
                    order(pixels)

                elif command == "clock":
                    clock(pixels)

                elif command == "draw":
                    draw(pixels)

                else:
                    print(HELP)

            except (KeyError, ValueError, IndexError):
                print(HELP)

    finally:
        # They latch. Exiting without this leaves the last frame lit.
        pixels.clear()
        print("eyes dark. good bench.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
