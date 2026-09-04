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

    {"type": "eyes", "mood": "listening", "level": 0.3,
     "color": "green", "gaze": -0.4}

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
import colorsys
import math
import random
import time
from dataclasses import dataclass


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

# Purple remains the factory identity. A person can now choose one shared hue
# for both eyes; the renderer keeps the animation language consistent instead
# of turning every conversational state into a different status-light color.
PURPLE = (0.58, 0.18, 1.00)

EMBER = (0.16, 0.02, 0.38)      # the bottom of a breath, barely on
DEEP = (0.30, 0.05, 0.75)       # resting purple
PALE = (0.80, 0.60, 1.00)       # a lit highlight, still unmistakably violet
FLARE = (0.93, 0.86, 1.00)      # the top of a reaction. Never a resting state

COLOR_VALUES = {
    "purple": PURPLE,
    "red": (1.00, 0.03, 0.01),
    "amber": (1.00, 0.32, 0.01),
    "yellow": (1.00, 0.72, 0.02),
    "green": (0.02, 1.00, 0.10),
    "teal": (0.02, 0.85, 0.55),
    "cyan": (0.02, 0.72, 1.00),
    "blue": (0.03, 0.16, 1.00),
    "pink": (1.00, 0.10, 0.55),
    "white": (1.00, 1.00, 1.00),
}

EYE_COLORS = tuple(COLOR_VALUES)
DEFAULT_COLOR = "purple"

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
#
# Rarer and quicker than the first version, which blinked every few seconds
# and became the thing you watched instead of the mood underneath. A blink
# should be something noticed afterwards, not during.
BLINK_EVERY = (5.5, 13.0)
BLINK_SECONDS = 0.13

# How far the lid actually gets. Not all the way: on a 12 pixel ring a full
# close lands as a hard off-frame, and at this speed leaving a trace of light
# reads softer while still reading as a blink.
BLINK_DEPTH = 0.15

# How far the lid edge is smeared across the ring, in degrees. With only 12
# pixels a hard edge closes in four visible steps; this makes it a sweep.
LID_SOFTNESS = 45.0

# --------------------------------------------------------------- the ripple

# A wave that runs from the top of each ring down both sides and fades out.
# It fires when the mood CHANGES, not on a timer, so it reads as the robot
# reacting to something rather than as decoration playing to itself.
RIPPLE_SECONDS = 0.85
RIPPLE_WIDTH = 60.0
RIPPLE_GAIN = 0.55

# Appearance changes are meant to feel like the same face changing its mind,
# not a GPIO value snapping from one state to another.
COLOR_TRANSITION_SECONDS = 0.30

MANUAL_WINK_SECONDS = 0.24
CELEBRATE_SECONDS = 1.60
CELEBRATE_WIDTH = 72.0

# Face tracking moves this highlight, not the whole eye. It is deliberately
# small enough that gaze is felt before it is noticed.
GAZE_SHIFT_DEGREES = 58.0
GAZE_GAIN = 0.16

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


@dataclass(frozen=True)
class Palette:
    ember: tuple
    deep: tuple
    base: tuple
    pale: tuple
    flare: tuple


def make_palette(base):
    return Palette(
        ember=scale(base, 0.16),
        deep=scale(base, 0.48),
        base=base,
        pale=mix(base, (1.0, 1.0, 1.0), 0.48),
        flare=mix(base, (1.0, 1.0, 1.0), 0.82),
    )


def mix_palette(a, b, amount):
    return Palette(
        ember=mix(a.ember, b.ember, amount),
        deep=mix(a.deep, b.deep, amount),
        base=mix(a.base, b.base, amount),
        pale=mix(a.pale, b.pale, amount),
        flare=mix(a.flare, b.flare, amount),
    )


PALETTES = {name: make_palette(color) for name, color in COLOR_VALUES.items()}

# Preserve the hand-tuned purple ramp exactly when no preference was chosen.
PALETTES["purple"] = Palette(EMBER, DEEP, PURPLE, PALE, FLARE)


def angle_of(index):
    """Where a pixel sits on its own ring, in degrees clockwise from the top.

    Both eyes are addressed in the same coordinates, so a mood can talk about
    "the bottom of the ring" without caring which twelve pixels it means.
    """

    return (PIXEL_ZERO_DEGREES + 30.0 * (index % PIXELS_PER_EYE)) % 360.0


def from_top(index):
    """How far a pixel is from twelve o'clock, 0 at the top, 180 at the bottom.

    Shared by the lid and the ripple: both travel from the top down BOTH
    sides at once, which is the only motion a ring can make that reads as
    coming from somewhere rather than going round.
    """

    return abs((angle_of(index) + 180.0) % 360.0 - 180.0)


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


def ripple_at(index, age):
    """The wave a mood change sends round the ring. 0 once it has passed.

    Runs from the top down both sides at once, because a ring has no centre
    to spread from - the top is the only point both halves share.
    """

    if age < 0.0 or age > RIPPLE_SECONDS:
        return 0.0

    through = age / RIPPLE_SECONDS
    front = 180.0 * through
    away = abs(from_top(index) - front)

    if away >= RIPPLE_WIDTH:
        return 0.0

    edge = 0.5 * (1.0 + math.cos(math.pi * away / RIPPLE_WIDTH))

    # Fades as it travels, so it dies out rather than stopping at the bottom.
    return RIPPLE_GAIN * edge * (1.0 - through)


# ----------------------------------------------------------------- the moods
#
# Each takes the time the mood has been running, the smoothed level, which
# eye it is drawing (-1 for the robot's left, +1 for its right), and the
# active palette, then returns 12 colours. Returning per-eye is what lets a
# mood be asymmetric - a cocked head, one eye leading the other - which is
# most of what separates a face from a status light.
#
# The house style, after the first version was judged too busy: these mostly
# BREATHE rather than rotate. A ring with something travelling round it pulls
# the eye and never lets go, which is right for `thinking`, where the motion
# means work is happening, and wrong for everything the robot does all day.
# Stillness that swells is the resting state; movement is reserved for moods
# that have earned it.


def mood_off(t, level, eye, palette):
    return [(0.0, 0.0, 0.0)] * PIXELS_PER_EYE


def mood_idle(t, level, eye, palette):
    """Waiting. One slow breath, the whole ring together, nothing moving."""

    depth = breathe(t, 6.5, 0.13, 0.30)

    return [scale(mix(palette.ember, palette.base, 0.55), depth)] * PIXELS_PER_EYE


def mood_listening(t, level, eye, palette):
    """Somebody is talking. The ring holds still and answers their voice.

    Deliberately the least animated mood in the set. It is on for as long as
    anybody is speaking, so anything that travels round the ring here becomes
    the thing people watch instead of a robot paying attention.
    """

    under = breathe(t, 4.2, 0.86, 1.0)
    lit = (0.17 + 0.55 * level) * under

    return [
        scale(mix(palette.deep, palette.pale, 0.30 + 0.45 * level), lit)
    ] * PIXELS_PER_EYE


def mood_thinking(t, level, eye, palette):
    """Working on it. A comet runs the ring - the one mood that travels.

    Kept, and kept moving, because here the motion is the message: it is the
    gap between a question landing and an answer starting, and a still ring
    through that gap reads as a robot that did not hear you.

    Deliberately NOT mirrored. Two eyes chasing opposite ways reads as
    confusion; chasing together reads as one mechanism spinning up.
    """

    head = (t * 210.0) % 360.0

    return [
        scale(
            mix(
                palette.deep,
                palette.pale,
                0.35 + 0.5 * arc(i, head, 120.0, softness=2.0),
            ),
            0.12 + 0.52 * arc(i, head, 120.0, softness=2.0),
        )
        for i in range(PIXELS_PER_EYE)
    ]


def mood_speaking(t, level, eye, palette):
    """The robot is talking. The whole eye swells with its own voice.

    The ring stays whole rather than opening an arc: the voice is already
    carrying the sentence, and an eye that changes shape per syllable fights
    it. This just gets brighter and fuller when the voice does.
    """

    swell = breathe(t, 1.6, 0.88, 1.0)

    return [
        scale(
            mix(palette.deep, palette.pale, 0.25 + 0.45 * level),
            (0.15 + 0.62 * level) * swell,
        )
    ] * PIXELS_PER_EYE


def mood_excited(t, level, eye, palette):
    """Fast, bright, and all the way up the purple axis.

    The first version sparkled random pixels white. It was too much, and the
    sparkle was the part doing it - noise reads as a fault on a face. Speed
    and brightness carry this instead.
    """

    pulse = breathe(t, 0.5, 0.35, 1.0)

    return [
        scale(
            mix(palette.base, palette.pale, 0.35 + 0.6 * pulse),
            0.26 + 0.58 * pulse,
        )
    ] * PIXELS_PER_EYE


def mood_happy(t, level, eye, palette):
    """Pleased. The lit part sinks to the bottom of the ring - a squint.

    A human smile closes the eyes from below. Lighting only the lower arc is
    the same trick, and it is the one mood people name without being told.
    """

    lift = breathe(t, 3.0, 0.0, 9.0)

    return [
        scale(
            mix(palette.base, palette.pale, 0.5),
            0.09 + 0.66 * arc(i, 180.0 - lift, 95.0),
        )
        for i in range(PIXELS_PER_EYE)
    ]


def mood_curious(t, level, eye, palette):
    """Interested. The two eyes sit at different heights, and drift slowly.

    Asymmetry is the whole point - it is what a cocked head looks like from
    the front, and it costs one term.
    """

    tilt = eye * (24.0 + 8.0 * math.sin(2.0 * math.pi * t / 4.5))

    return [
        scale(
            mix(palette.deep, palette.base, 0.7),
            0.11 + 0.55 * arc(i, 180.0 + tilt, 115.0),
        )
        for i in range(PIXELS_PER_EYE)
    ]


def mood_surprised(t, level, eye, palette):
    """A flare that decays. Wide open, then settling back to purple."""

    flash = math.exp(-t / 0.45)

    return [
        scale(mix(palette.base, palette.flare, 0.85 * flash), 0.26 + 0.66 * flash)
    ] * PIXELS_PER_EYE


def mood_confused(t, level, eye, palette):
    """The eyes disagree with each other, slowly.

    A slow wobble in opposite directions rather than the counter-rotating
    arcs this used to be. Same idea - the two sides not agreeing - without
    two things travelling in a face that is supposed to be holding still.
    """

    wobble = eye * 30.0 * math.sin(2.0 * math.pi * t / 2.6)
    dim = breathe(t, 2.6, 0.75, 1.0)

    return [
        scale(
            mix(palette.ember, palette.base, 0.6),
            (0.10 + 0.44 * arc(i, 180.0 + wobble, 130.0)) * dim,
        )
        for i in range(PIXELS_PER_EYE)
    ]


def mood_sleepy(t, level, eye, palette):
    """Almost out. A dim sliver at the bottom, fading in and out."""

    depth = breathe(t, 7.5, 0.04, 0.18)

    return [
        scale(
            mix(palette.ember, palette.base, 0.45),
            depth * arc(i, 180.0, 75.0),
        )
        for i in range(PIXELS_PER_EYE)
    ]


def mood_angry(t, level, eye, palette):
    """A hard red brow: bright at the top and weighted toward the nose."""

    pulse = breathe(t, 1.35, 0.78, 1.0)
    center = 326.0 if eye < 0 else 34.0

    return [
        scale(
            mix(palette.deep, palette.base, 0.72),
            (0.10 + 0.64 * arc(i, center, 112.0)) * pulse,
        )
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
    "angry": mood_angry,
    "sleepy": mood_sleepy,
}

DEFAULT_MOOD = "idle"
_UNSET = object()


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

        self.color = DEFAULT_COLOR
        default_palette = PALETTES[DEFAULT_COLOR]
        self._palette_name = DEFAULT_COLOR
        self._palette_from = default_palette
        self._palette_to = default_palette
        self._palette_started = 0.0

        self.gaze = None
        self.wink_eye = None
        self.wink_started = None
        self.celebration = None
        self.celebration_started = None

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

    def _current_palette(self):
        through = clamp(
            (self.clock - self._palette_started) / COLOR_TRANSITION_SECONDS
        )
        return mix_palette(self._palette_from, self._palette_to, through)

    def _effective_palette_name(self, mood=None, color=None):
        mood = self.mood if mood is None else mood
        color = self.color if color is None else color
        return "red" if mood == "angry" else color

    def _transition_to(self, name):
        if name == self._palette_name:
            return

        self._palette_from = self._current_palette()
        self._palette_to = PALETTES[name]
        self._palette_started = self.clock
        self._palette_name = name

    def set(
        self,
        mood=None,
        level=None,
        brightness=None,
        color=None,
        gaze=_UNSET,
        effect=None,
    ):
        """Take one update from the brain. Anything unknown is ignored."""

        next_mood = self.mood if mood is None else str(mood)
        next_color = self.color if color is None else str(color)

        if next_mood not in MOODS or next_color not in PALETTES:
            return False

        if effect is not None:
            if not isinstance(effect, dict):
                return False

            name = effect.get("name")

            if name == "wink" and effect.get("eye") not in ("left", "right"):
                return False
            if name == "celebrate" and effect.get("style") not in (
                "gold",
                "rainbow",
            ):
                return False
            if name not in ("wink", "celebrate"):
                return False

        target_palette = self._effective_palette_name(next_mood, next_color)
        self._transition_to(target_palette)

        if next_mood != self.mood:
            self.mood = next_mood
            self.mood_started = self.clock

        self.color = next_color

        if level is not None:
            self.raw_level = clamp(float(level))
            self.since_update = 0.0

        if brightness is not None:
            self.brightness = clamp(float(brightness), 0.0, BRIGHTNESS_CEILING)

        if gaze is not _UNSET:
            self.gaze = None if gaze is None else clamp(float(gaze), -1.0, 1.0)

        if effect is not None:
            if effect["name"] == "wink":
                self.wink_eye = effect["eye"]
                self.wink_started = self.clock
            else:
                self.celebration = effect["style"]
                self.celebration_started = self.clock

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
            shut = 0.5 * (1.0 + math.cos(2.0 * math.pi * through))

            return BLINK_DEPTH + (1.0 - BLINK_DEPTH) * shut

        if self.clock >= self.blink_at:
            self.blinking_since = 0.0

        return 1.0

    def _ripple(self, colors, age, palette):
        """Lay the mood-change wave over one eye's twelve colours."""

        out = []

        for index, color in enumerate(colors):
            wave = ripple_at(index, age)

            if wave <= 0.0:
                out.append(color)
                continue

            # Brightens AND pales, so the wave is visible even where the mood
            # underneath is already near black.
            out.append(
                mix(
                    scale(color, 1.0 + wave),
                    scale(palette.pale, wave),
                    0.55 * wave,
                )
            )

        return out

    def _wink_openness(self, eye):
        if self.wink_started is None or self.wink_eye != eye:
            return 1.0

        age = self.clock - self.wink_started

        if age >= MANUAL_WINK_SECONDS:
            self.wink_started = None
            self.wink_eye = None
            return 1.0

        through = age / MANUAL_WINK_SECONDS
        shut = 0.5 * (1.0 + math.cos(2.0 * math.pi * through))
        return BLINK_DEPTH + (1.0 - BLINK_DEPTH) * shut

    def _gaze_highlight(self, colors, palette, eye):
        if self.gaze is None:
            return colors

        center = 180.0 + eye * self.gaze * GAZE_SHIFT_DEGREES
        return [
            mix(color, palette.pale, GAZE_GAIN * arc(index, center, 92.0))
            for index, color in enumerate(colors)
        ]

    def _celebrate(self, colors):
        if self.celebration_started is None:
            return colors

        age = self.clock - self.celebration_started

        if age >= CELEBRATE_SECONDS:
            self.celebration = None
            self.celebration_started = None
            return colors

        through = age / CELEBRATE_SECONDS
        front = 180.0 * through
        envelope = math.sin(math.pi * through)
        out = []

        for index, color in enumerate(colors):
            away = abs(from_top(index) - front)
            wave = 0.0
            if away < CELEBRATE_WIDTH:
                wave = 0.5 * (
                    1.0 + math.cos(math.pi * away / CELEBRATE_WIDTH)
                )

            if self.celebration == "rainbow":
                hue = (angle_of(index) / 360.0 + 0.45 * through) % 1.0
                accent = colorsys.hsv_to_rgb(hue, 0.92, 1.0)
            else:
                accent = (1.0, 0.55, 0.03)

            out.append(mix(color, scale(accent, 0.88), 0.92 * wave * envelope))

        return out

    def _lid_mask(self, index, openness):
        """A lid closing from the top. 1 is lit, 0 is covered.

        The edge travels past both ends of the ring rather than stopping on
        them, so fully open really is every pixel at full and fully shut
        really is nothing - an eyelid that never quite arrives reads as a
        fault, not a blink.
        """

        if openness >= 0.999:
            return 1.0

        edge = (1.0 - openness) * (180.0 + 2.0 * LID_SOFTNESS) - LID_SOFTNESS

        return clamp((from_top(index) - edge) / LID_SOFTNESS)

    def frame(self, elapsed):
        """One rendered frame: 24 colours, in logical pixel order."""

        self._advance(elapsed)
        openness = self._blink(elapsed)
        palette = self._current_palette()

        render = MOODS.get(self.mood, MOODS[DEFAULT_MOOD])
        age = self.clock - self.mood_started

        left = render(age, self.level, -1, palette)
        right = render(age, self.level, +1, palette)

        # The ripple rides on top of whatever the mood drew, so it reads as
        # the same eye reacting rather than as a second thing happening.
        if age <= RIPPLE_SECONDS and self.mood != "off":
            left = self._ripple(left, age, palette)
            right = self._ripple(right, age, palette)

        left = self._gaze_highlight(left, palette, -1)
        right = self._gaze_highlight(right, palette, +1)
        left = self._celebrate(left)
        right = self._celebrate(right)

        # The right eye is drawn mirrored, so a sweep runs outward from the
        # nose on both sides instead of both eyes turning the same way. Two
        # rings rotating in parallel read as gauges; mirrored reads as a face.
        right = list(reversed(right))

        left_open = min(openness, self._wink_openness("left"))
        right_open = min(openness, self._wink_openness("right"))

        first, second = (
            ((left, left_open), (right, right_open))
            if FIRST_RING_IS_LEFT
            else ((right, right_open), (left, left_open))
        )

        out = []

        for eye, eye_openness in (first, second):
            for index, color in enumerate(eye):
                out.append(scale(color, self._lid_mask(index, eye_openness)))

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
