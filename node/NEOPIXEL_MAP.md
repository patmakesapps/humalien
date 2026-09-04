# Desk bot NeoPixel map

Bench-identified on 2026-09-03. The eyes are two Adafruit NeoPixel Ring 12B
boards behind the printed face diffusers. Each eye has 12 RGB pixels, for 24
pixels in one logical data chain.

## Wiring

- Raspberry Pi physical header pin 33 is BCM GPIO13. It is the NeoPixel data
  output and connects to `DIN` on the first eye ring.
- First ring `DOUT` connects to second ring `DIN`.
- `DOUT` carries data only. Both rings still require 5 V and ground: connect
  first-ring 5 V to second-ring 5 V and first-ring ground to second-ring
  ground, or run equivalent power wires directly to both rings.
- The Pi, both rings, and any external 5 V LED supply must share ground.
- Never connect 5 V to physical pin 33 / GPIO13.
- Budget up to about 1.44 A for 24 pixels at worst-case full white. Use a
  regulated 5 V supply rated for at least 2 A rather than powering this load
  through a GPIO pin.

The first ring occupies logical pixels 0–11 and the ring connected to its
`DOUT` occupies pixels 12–23. Which physical eye is first is not yet recorded;
identify it with the low-brightness test below after resoldering.

## Pi 5 data format

The working Pi 5 driver is `adafruit_raspberry_pi5_neopixel_write`, using
`board.D13`. The raw byte order observed working is GRB, so one dim purple
pixel is `bytes([0, 5, 5])`, not RGB order.

NeoPixels latch the last frame and keep displaying it until power is removed
or another frame is sent. A process does not need to remain running after a
successful write.

## Post-solder test

Start dim. The earlier value 48 per lit channel was uncomfortably bright; use
5 per channel for bench work.

1. Send 12 dim red pixels followed by 12 dim blue pixels:
   `bytes([0, 5, 0]) * 12 + bytes([0, 0, 5]) * 12`.
2. Record whether red is the physical left or right eye; that establishes the
   permanent logical ring order.
3. If only the first ring lights, power down and check second-ring 5 V, common
   ground, and first-ring `DOUT` to second-ring `DIN`, including data direction
   and solder continuity.
4. Once both rings respond, send dim purple to all 24 pixels:
   `bytes([0, 5, 5]) * 24`.
5. End every bench test by clearing all 24 pixels:
   `bytes([0, 0, 0]) * 24`.

The first eye ring was proven working on GPIO13. The second did not light in
the initial chain test because it was not independently powered; it is being
resoldered before the next test. Do not record left/right order from that
failed test.


## The driver, its permissions, and its licence

`pip install -r node/requirements.txt` brings in
`adafruit-blinka-raspberry-pi5-neopixel`, which provides the
`adafruit_raspberry_pi5_neopixel_write` module this code imports. It is the
only route that works on a Pi 5: the RP1 offers no PWM/DMA path the older
`rpi_ws281x` libraries can use, so this one drives the pixels over PIO.

That means it needs **`/dev/pio0`**, not just GPIO. If that file is owned
`root:root`, add to `/etc/udev/rules.d/99-com.rules`:

```
SUBSYSTEM=="*-pio", GROUP="gpio", MODE="0660"
```

and reboot. If it does not exist at all, the Pi 5 firmware predates PIO
support. Either way the node logs `No NeoPixels, running blind-faced` and
carries on with its voice and its arms - a missing driver costs the robot its
face, never its speech.

### Licence flag

This package is **GPL-2.0-only**. Every other dependency here is permissive.
It is imported rather than vendored, but Humalien is a commercial product and
an image that ships it carries copyleft obligations the rest of the stack does
not. Worth a decision before hardware leaves the building rather than after.

If that decision goes against it, the replacement is a small one: the module
is touched in exactly one place, `Pi5NeoPixelWrite` in `humalien_node/pixels.py`,
which is nine lines and takes raw GRB bytes. Everything above it - the moods,
the blink, the current budget - is ours and stays.

## Runtime driver — added 2026-09-03

`humalien_node/pixels.py` renders the eyes; `humalien_node/pixel_bench.py`
walks them by hand. The post-solder test above is `order` in that bench.

### The brain sends a mood, not pixels

The animation runs on the Pi at 40 Hz. The brain sends one small message
whenever the answer changes, on the same websocket as the audio:

```json
{"type":"eyes","mood":"listening","level":0.31,"brightness":0.2}
```

Rendered frames over the wire would put 40 messages a second of pixel data
next to the speech and hand every one of them a chance to stutter. A mood
stays true until it changes; a frame is perishable. `brightness` is optional
and is sent once, on the first frame, so a value being tuned at the bench is
not overwritten twenty times a second.

The moods are `idle`, `listening`, `thinking`, `speaking`, `excited`,
`happy`, `curious`, `surprised`, `confused`, `sleepy` and `off`.
`brain/mood.py` picks between them; `brain/tests/test_mood.py` asserts the
two lists have not drifted apart, because the node silently ignores a mood it
does not know.

`listening` and `speaking` scale with `level` — the microphone's loudness and
the robot's own playback envelope respectively. The node smooths that between
messages and decays it after half a second of silence, so a brain that dies
mid-word cannot leave an eye stuck at full brightness.

The eyes blink on their own, every 2.6–7 s, as a lid sweeping down the ring
and back. It is not driven from the brain and it does not need to be.

### Brightness and current

`BRIGHTNESS` starts at 0.20 and is hard-capped at 0.60 whatever the brain
asks for. Above that sits a current budget: any frame that would draw more
than 900 mA is scaled down **as a whole**, so its shape survives — clipping
the brightest pixels would change which mood you are looking at, and dimming
does not.

At the default no mood comes close: the brightest, `excited`, draws about
180 mA of the 900. Raise it with `bright` at the bench and paste back what
looks right through the diffusers. The 48-per-channel figure above was
measured on a bare ring and is not the same thing.

### Still to record

- Which physical eye is logical pixels 0–11. Run `order` and set
  `FIRST_RING_IS_LEFT` in `pixels.py`. Getting it wrong only mirrors the
  animation, so it is not urgent — but it is still unrecorded.
- Where pixel 0 sits on the face. Run `clock` and set `PIXEL_ZERO_DEGREES`.
  Everything angular — the blink, the `happy` squint, the rotating arcs —
  is measured clockwise from twelve o'clock and assumes that value.
