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

