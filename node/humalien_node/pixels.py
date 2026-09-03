"""The eyes: two NeoPixel rings, a mood, and a renderer that runs on the Pi.

    from humalien_node.pixels import Pixels, Pi5NeoPixelDriver

WHY THE ANIMATION LIVES HERE AND NOT IN THE BRAIN
-------------------------------------------------
The same split as humalien_node.arms. The brain says WHAT the robot feels;
this file decides what that looks like, frame by frame, at 40 Hz on the
machine holding the LEDs.

Sending rendered frames over the websocket instead would put 40 messages a
second of pixel data on the same socket as the audio, and every one of them
would be a chance for network jitter to turn a smooth breath into a stutter.
A mood is one small message that stays true until it changes; a frame is
perishable. So the wire carries

    {"type": "eyes", "mood": "listening", "level": 0.3}

and everything below is local.

WHAT THE HARDWARE ACTUALLY WANTS
--------------------------------
node/NEOPIXEL_MAP.md, bench-identified 2026-09-03:

  * Two Adafruit NeoPixel Ring 12B boards, 12 pixels each, chained into one
    logical run of 24 on BCM GPIO13 (physical pin 33).
  * The Pi 5 driver is `adafruit_raspberry_pi5_neopixel_write` on `board.D13`.
  * The raw byte order is GRB, not RGB. One dim purple pixel is
    bytes([0, 5, 5]) - green byte first.
  * Pixels 0-11 are the first ring, 12-23 the second. Which physical eye is
    first was not recorded, so FIRST_RING_IS_LEFT below is a guess; getting
    it wrong mirrors the animation and nothing worse.
  * NeoPixels latch. The last frame written stays lit until another frame
    arrives or the power goes. That is why the server clears them on the way
    out rather than simply stopping - a dead brain must not leave a face
    staring at an empty room.

BRIGHTNESS AND CURRENT
----------------------
NEOPIXEL_MAP.md warns that 24 pixels at full white is about 1.44 A, and that
48 per lit channel was uncomfortably bright on a BARE ring at the bench.
These rings sit behind printed diffusers, which is a different thing, so
BRIGHTNESS starts low and is live-tunable from the brain and from
`pixel_bench`. Two independent guards sit under it: a hard ceiling on the
brightness scale, and a current budget that dims a whole frame rather than
letting a bright mood pull more than the supply is rated for.
"""

import asyncio
import math
import random
import time


# ------------------------------------------------------------- the hardware

PIXELS_PER_EYE = 12
PIXEL_COUNT = PIXELS_PER_EYE * 2

# NEOPIXEL_MAP.md: the byte order on the wire is GRB, not RGB.
BYTE_ORDER = (1, 0, 2)

# Which logical block is the robot's own left eye. Not yet recorded - the
# post-solder test in NEOPIXEL_MAP.md is what settles it. Wrong only mirrors
# the animation left-to-right.
FIRST_RING_IS_LEFT = True

# Pixel 0's position on the ring, measured clockwise from twelve o'clock.
# Set it from the bench `clock` command, which lights one pixel at a time.
PIXEL_ZERO_DEGREES = 0.0

# Frame rate. Fast enough that a sweep looks continuous, slow enough to leave
# the Pi to the audio, which is the job that actually cannot drop work.
TICK = 0.025

# --------------------------------------------------------------- the colours

# The brand. Every mood is a move away from this and back to it.
PURPLE = (0.58, 0.18, 1.00)

# Where the moods travel to. Kept few and named, rather than a hue wheel: a
# small palette that always reads as the same robot beats a rainbow.
DEEP = (0.30, 0.05, 0.75)       # the low end of a breath
CYAN = (0.25, 0.65, 1.00)       # attention, listening
MAGENTA = (1.00, 0.18, 0.85)    # excitement
WARM = (1.00, 0.45, 0.85)       # pleased
WHITE = (1.00, 0.92, 1.00)      # a flare, never a resting state

# Scales the whole frame. NEOPIXEL_MAP.md's bench note is the reason this is
# low: raise it with `bright` on the bench, then paste what you land on here.
BRIGHTNESS = 0.20

# A brightness value can arrive from the brain. This is the most it is ever
# allowed to be, whatever it asks for.
BRIGHTNESS_CEILING = 0.60

# Roughly 20 mA per channel at full, per NEOPIXEL_MAP.md's 1.44 A figure for
# 24 pixels of white. The budget is what the frame is allowed to draw; a
# frame over it is scaled down as a whole, so its shape survives.
MILLIAMPS_PER_CHANNEL = 20.0 / 255.0
CURRENT_BUDGET_MA = 900.0

# ---------------------------------------------------------------- the level

# The brain sends a loudness with each mood update. Smooth it here so the
# animation stays continuous between messages, and decay it if the messages
# stop - a brain that dies mid-word must not leave an eye stuck bright.
LEVEL_ATTACK = 0.06
LEVEL_RELEASE = 0.25
LEVEL_STALE_AFTER = 0.5

# ---------------------------------------------------------------- the blink

# What makes a face look alive more than any single mood does. A lid sweeps
# down the ring and back up.
BLINK_EVERY = (2.6, 7.0)
BLINK_SECONDS = 0.16

# How far the lid edge is smeared across the ring, in degrees. With only 12
# pixels a hard edge closes in four visible steps; this makes it a sweep.
LID_SOFTNESS = 45.0

# Moods that must not blink: one is off, and the other is a face frozen
# mid-reaction.
NEVER_BLINKS = ("off", "surprised")


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def mix(a, b, amount):
    """Blend two colours. amount 0 gives a, 1 gives b."""

    amount = clamp(amount)

    return tuple(one + (other - one) * amount for one, other in zip(a, b))


def scale(color, amount):
    return tuple(channel * amount for channel in color)


def angle_of(index):
    """Where a pixel sits on its own ring, in degrees clockwise from the top.

    Both eyes are addressed in the same coordinates, so a mood can talk about
    "the bottom of the ring" without caring which twelve pixels it means.
    """

    return (PIXEL_ZERO_DEGREES + 30.0 * (index % PIXELS_PER_EYE)) % 360.0


def arc(index, center, width, softness=1.0):
    """How strongly a pixel belongs to an arc centred at `center` degrees.

    Returns 1 at the centre and falls to 0 by `width` degrees away, on a
    raised cosine. Hard-edged arcs on a 12 pixel ring look like a bar graph;
    this is what makes a sweep read as light rather than as segments.
    """

    away = abs((angle_of(index) - center + 180.0) % 360.0 - 180.0)

    if away >= width:
        return 0.0

    edge = 0.5 * (1.0 + math.cos(math.pi * away / width))

    return edge ** softness


def breathe(t, period, low=0.0, high=1.0):
    """A sine that never quite stops. The shape of something being alive."""

    phase = 0.5 * (1.0 - math.cos(2.0 * math.pi * t / period))

    return low + (high - low) * phase


# ----------------------------------------------------------------- the moods
#
# Each takes the time the mood has been running, the smoothed level, and which
# eye it is drawing (-1 for the robot's left, +1 for its right), and returns
# 12 colours. Returning per-eye is what lets a mood be asymmetric - a cocked
# head, a wink, one eye leading the other - which is most of what separates a
# face from a status light.


def mood_off(t, level, eye):
    return [(0.0, 0.0, 0.0)] * PIXELS_PER_EYE


def mood_idle(t, level, eye):
    """Waiting. A slow breath with a highlight drifting round it."""

    depth = breathe(t, 5.2, 0.16, 0.34)
    sweep = (t * 22.0) % 360.0

    return [
        scale(mix(DEEP, PURPLE, 0.3 + 0.7 * arc(i, sweep, 150.0)), depth)
        for i in range(PIXELS_PER_EYE)
    ]


def mood_listening(t, level, eye):
    """Somebody is talking. The ring leans cyan and answers their voice.

    The rotating highlight is slow and the level term is fast, so the eye
    reads as attentive underneath and responsive on top.
    """

    sweep = (t * 55.0) % 360.0
    lit = 0.22 + 0.55 * level

    return [
        scale(
            mix(
                mix(DEEP, CYAN, 0.35 + 0.45 * level),
                WHITE,
                0.35 * arc(i, sweep, 90.0) * level,
            ),
            lit * (0.55 + 0.45 * arc(i, sweep, 130.0)),
        )
        for i in range(PIXELS_PER_EYE)
    ]


def mood_thinking(t, level, eye):
    """Working on it. A comet runs the ring, both eyes the same way round.

    Deliberately NOT mirrored. Two eyes chasing in opposite directions reads
    as confusion; chasing together reads as one mechanism spinning up.
    """

    head = (t * 300.0) % 360.0

    return [
        scale(
            mix(DEEP, PURPLE, 0.4 + 0.6 * arc(i, head, 110.0, softness=2.2)),
            0.14 + 0.70 * arc(i, head, 110.0, softness=2.2),
        )
        for i in range(PIXELS_PER_EYE)
    ]


def mood_speaking(t, level, eye):
    """The robot is talking. The eye opens with the voice.

    Width as well as brightness follows the envelope, so a loud phrase makes
    the eye look bigger rather than merely brighter.
    """

    width = 70.0 + 110.0 * level
    shimmer = breathe(t, 0.9, 0.85, 1.0)

    return [
        scale(
            mix(PURPLE, WHITE, 0.30 * level),
            (0.16 + 0.72 * level) * shimmer * (0.35 + 0.65 * arc(i, 180.0, width)),
        )
        for i in range(PIXELS_PER_EYE)
    ]


def mood_excited(t, level, eye):
    """Fast, bright, and pushed toward magenta, with sparks off the top.

    The sparkle is seeded from the frame time so both eyes glitter on the
    same beats without glittering on the same pixels.
    """

    pulse = breathe(t, 0.34, 0.45, 1.0)
    spark = random.Random(int(t * 26.0) * 7 + int(eye)).random

    out = []

    for i in range(PIXELS_PER_EYE):
        color = mix(PURPLE, MAGENTA, 0.55 + 0.45 * pulse)

        if spark() > 0.86:
            color = mix(color, WHITE, 0.75)

        out.append(scale(color, 0.30 + 0.60 * pulse))

    return out


def mood_happy(t, level, eye):
    """Pleased. The lit part sinks to the bottom of the ring - a squint.

    A human smile closes the eyes from below. Lighting only the lower arc is
    the same trick, and it is the one mood people name without being told.
    """

    lift = breathe(t, 2.4, 0.0, 12.0)

    return [
        scale(
            mix(PURPLE, WARM, 0.65),
            0.10 + 0.75 * arc(i, 180.0 - lift, 95.0),
        )
        for i in range(PIXELS_PER_EYE)
    ]


def mood_curious(t, level, eye):
    """Interested. The two eyes sit at different heights, and drift.

    Asymmetry is the whole point - it is what a cocked head looks like from
    the front, and it costs one term.
    """

    tilt = eye * (26.0 + 10.0 * math.sin(2.0 * math.pi * t / 3.6))

    return [
        scale(
            mix(PURPLE, CYAN, 0.3),
            0.12 + 0.62 * arc(i, 180.0 + tilt, 110.0),
        )
        for i in range(PIXELS_PER_EYE)
    ]


def mood_surprised(t, level, eye):
    """A flare that decays. Wide open, then settling back to purple."""

    flash = math.exp(-t / 0.45)

    return [
        scale(mix(PURPLE, WHITE, 0.8 * flash), 0.28 + 0.68 * flash)
        for i in range(PIXELS_PER_EYE)
    ]


def mood_confused(t, level, eye):
    """The eyes disagree with each other, slowly. Counter-rotating arcs."""

    sweep = (eye * t * 90.0) % 360.0

    return [
        scale(
            mix(DEEP, PURPLE, 0.5),
            0.10 + 0.50 * arc(i, sweep, 100.0),
        )
        for i in range(PIXELS_PER_EYE)
    ]


def mood_sleepy(t, level, eye):
    """Almost out. A dim sliver at the bottom, fading in and out."""

    depth = breathe(t, 6.5, 0.05, 0.20)

    return [
        scale(mix(DEEP, PURPLE, 0.4), depth * arc(i, 180.0, 70.0))
        for i in range(PIXELS_PER_EYE)
    ]


MOODS = {
    "off": mood_off,
    "idle": mood_idle,
    "listening": mood_listening,
    "thinking": mood_thinking,
    "speaking": mood_speaking,
    "excited": mood_excited,
    "happy": mood_happy,
    "curious": mood_curious,
    "surprised": mood_surprised,
    "confused": mood_confused,
    "sleepy": mood_sleepy,
}

DEFAULT_MOOD = "idle"


class Pi5NeoPixelWrite:
    """The real LEDs. Imported lazily so this module loads anywhere.

    NEOPIXEL_MAP.md: on a Pi 5 the working path is
    adafruit_raspberry_pi5_neopixel_write on board.D13, fed raw GRB bytes.
    """

    def __init__(self):
        import board
        from adafruit_raspberry_pi5_neopixel_write import neopixel_write

        self.pin = board.D13
        self._write = neopixel_write

    def write(self, data):
        self._write(self.pin, data)


class Pixels:
    """A mood, a level, and a frame renderer. Feed it; run() does the rest."""

    def __init__(self, driver=None, brightness=BRIGHTNESS):
        self.driver = driver
        self.brightness = clamp(brightness, 0.0, BRIGHTNESS_CEILING)

        self.mood = DEFAULT_MOOD
        self.mood_started = 0.0

        self.raw_level = 0.0
        self.level = 0.0

        # Seconds since the brain last said anything, advanced by frame() on
        # the same clock it uses for everything else. Reading the wall clock
        # in here would leave the path that matters - what the eyes do when
        # the brain goes quiet - impossible to test.
        self.since_update = LEVEL_STALE_AFTER

        self.clock = 0.0
        self.blink_at = random.uniform(*BLINK_EVERY)
        self.blinking_since = None

        self.last_written = None

    # ------------------------------------------------------------ the input

    def set(self, mood=None, level=None, brightness=None):
        """Take one update from the brain. Anything unknown is ignored."""

        if mood is not None:
            mood = str(mood)

            if mood not in MOODS:
                return False

            if mood != self.mood:
                self.mood = mood
                self.mood_started = self.clock

        if level is not None:
            self.raw_level = clamp(float(level))
            self.since_update = 0.0

        if brightness is not None:
            self.brightness = clamp(float(brightness), 0.0, BRIGHTNESS_CEILING)

        return True

    # ----------------------------------------------------------- the frame

    def _advance(self, elapsed):
        self.clock += elapsed
        self.since_update += elapsed

        # A brain that stopped talking is not a robot shouting forever.
        target = self.raw_level if self.since_update < LEVEL_STALE_AFTER else 0.0

        tau = LEVEL_ATTACK if target > self.level else LEVEL_RELEASE
        self.level += (target - self.level) * (1.0 - math.exp(-elapsed / tau))

    def _blink(self, elapsed):
        """How open the lid is, 0 shut to 1 open, and when the next one is.

        The lid is a real sweep rather than a fade: `_lid_mask` uses this
        against each pixel's angle, so the ring closes from the top down the
        way an eyelid does.
        """

        if self.mood in NEVER_BLINKS:
            self.blinking_since = None
            return 1.0

        if self.blinking_since is not None:
            self.blinking_since += elapsed

            if self.blinking_since >= BLINK_SECONDS:
                self.blinking_since = None
                self.blink_at = self.clock + random.uniform(*BLINK_EVERY)
                return 1.0

            # Open, shut, open again over the blink, on a cosine so neither
            # end of the movement is abrupt.
            through = self.blinking_since / BLINK_SECONDS

            return 0.5 * (1.0 + math.cos(2.0 * math.pi * through))

        if self.clock >= self.blink_at:
            self.blinking_since = 0.0

        return 1.0

    def _lid_mask(self, index, openness):
        """A lid closing from the top. 1 is lit, 0 is covered.

        The edge travels past both ends of the ring rather than stopping on
        them, so fully open really is every pixel at full and fully shut
        really is nothing - an eyelid that never quite arrives reads as a
        fault, not a blink.
        """

        if openness >= 0.999:
            return 1.0

        from_top = abs((angle_of(index) + 180.0) % 360.0 - 180.0)
        edge = (1.0 - openness) * (180.0 + 2.0 * LID_SOFTNESS) - LID_SOFTNESS

        return clamp((from_top - edge) / LID_SOFTNESS)

    def frame(self, elapsed):
        """One rendered frame: 24 colours, in logical pixel order."""

        self._advance(elapsed)
        openness = self._blink(elapsed)

        render = MOODS.get(self.mood, MOODS[DEFAULT_MOOD])
        age = self.clock - self.mood_started

        left = render(age, self.level, -1)
        right = render(age, self.level, +1)

        # The right eye is drawn mirrored, so a sweep runs outward from the
        # nose on both sides instead of both eyes turning the same way. Two
        # rings rotating in parallel read as gauges; mirrored reads as a face.
        right = list(reversed(right))

        first, second = (left, right) if FIRST_RING_IS_LEFT else (right, left)

        out = []

        for eye in (first, second):
            for index, color in enumerate(eye):
                out.append(scale(color, self._lid_mask(index, openness)))

        return out

    # ----------------------------------------------------------- the output

    def encode(self, colors):
        """Colours to the wire bytes, brightness and current applied.

        The current guard scales the WHOLE frame rather than clipping the
        brightest pixels, because clipping changes which mood you are looking
        at and dimming does not.
        """

        raw = [
            [clamp(channel) * self.brightness * 255.0 for channel in color]
            for color in colors
        ]

        draw = sum(sum(pixel) for pixel in raw) * MILLIAMPS_PER_CHANNEL

        if draw > CURRENT_BUDGET_MA:
            shrink = CURRENT_BUDGET_MA / draw
            raw = [[channel * shrink for channel in pixel] for pixel in raw]

        data = bytearray()

        for pixel in raw:
            for position in BYTE_ORDER:
                data.append(int(clamp(pixel[position], 0.0, 255.0)))

        return bytes(data)

    def write(self, data):
        # NeoPixels latch, so an unchanged frame need not be resent. Holding
        # still costs nothing on the wire and nothing on the GPIO.
        if data == self.last_written:
            return False

        self.last_written = data

        if self.driver is not None:
            self.driver.write(data)

        return True

    def clear(self):
        """Go dark and stay dark. The rings hold whatever was last sent."""

        self.last_written = None
        self.write(bytes(PIXEL_COUNT * 3))

    async def run(self):
        """Render forever, one frame at a time."""

        last = time.monotonic()

        while True:
            await asyncio.sleep(TICK)

            now = time.monotonic()
            elapsed, last = now - last, now

            # A late wake-up must not fast-forward a whole breath.
            self.write(self.encode(self.frame(min(elapsed, TICK * 4))))
