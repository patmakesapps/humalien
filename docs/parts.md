# Parts

What Humalien is made of. Prices are what was seen at the time and will drift.

## In hand

| Part | Role | Notes |
| --- | --- | --- |
| Raspberry Pi 5 | Node — audio and sensors | Lives in the head |
| Waveshare WM8960 Audio HAT | Mics and speaker amp | Two onboard L/R MEMS mics. Pass-through header on top for I²C |
| 2 × speakers, 8 Ω 5 W | Sound out | Grey wired pair, share one white multi-pin connector |
| Adafruit SHT41 | Temperature, humidity | Two STEMMA QT connectors, so it can sit mid-chain |
| Adafruit MSA311 | Accelerometer — tilt and motion | Not a temperature sensor. Knows if the head is knocked, tilted or picked up |
| CQRobot VL53L1X | Distance / presence | I²C `0x29`. Ships with a six-wire cable, not STEMMA |
| Geekworm X1200 | Power / UPS board | To mount beneath the Pi 5 later |
| Pi NoIR camera + ribbon extender | Night vision, later | CSI, so it reaches the Pi and not the brain. See [hardware.md](hardware.md) |
| Asus laptop | Brain | Until the Jetson |

## Decided, not yet bought

| Part | Number | Why this one |
| --- | --- | --- |
| Arducam colour global shutter USB camera | **B0385** (OV9782) | Global shutter freezes motion, 100 fps gives the frame picker candidates, board-level mounts in a head, UVC needs no driver |
| Jetson Orin Nano Super Dev Kit 8 GB | **945-13766-0005-000** | $249 at NVIDIA MSRP. Runs 3–4B VLMs locally |
| NVMe M.2 SSD, 256 GB+ | any | JetPack on SD is miserable |

**Get B0385, not B0332.** B0332 is the OV9281 *monochrome* sensor. It is
cheaper, faster and better in low light, and useless here — "what colour is the
object in my hand" is a question Humalien is expected to answer.

## Planned

| Part | Role |
| --- | --- |
| PCA9685 | 16-channel servo PWM over I²C. Hardware PWM, so no twitch |
| 2 × MG90S | Eye pan and tilt |
| 1 × MG90S | Jaw |
| 2 × DS3218 class, ~20 kg·cm | Neck yaw and pitch. Size after weighing the head |
| Servo power supply, 6 V, several amps | Separate rail. Never the Pi's 5 V |
| M12 lens with IR-cut filter | The B0385 stock lens has none, so colours skew |

## I²C bus

Everything shares one bus off the audio hat's pass-through header.

| Device | Address | Status |
| --- | --- | --- |
| VL53L1X distance | `0x29` | Confirmed |
| SHT41 temp/humidity | `0x44` | Adafruit default, verify with `i2cdetect` |
| MSA311 accelerometer | check | Verify before wiring |
| PCA9685 servo driver | `0x40` | Default, jumper-selectable |

No conflicts among those. Run `i2cdetect -y 1` once everything is connected
and confirm before writing any driver code.

Two connector families are in play. The SHT41 uses **STEMMA QT / Qwiic** and
has two sockets so it can daisy-chain; the VL53L1X ships with a plain six-wire
cable. A Qwiic-to-header adapter will be needed to bring both onto the same
bus, and the Pi 5 has no Qwiic socket of its own.

## Things to check before ordering

- **The WM8960 is a small amplifier.** 5 W speakers on it will be safe but
  quiet. If Humalien cannot be heard across a room, the amp is the limit, not
  the speakers.
- **Jetson pricing.** Reseller bundles run three times MSRP. A $769 kit
  including an SSD, WiFi card and power supply is still worse than $249 plus a
  $30 SSD, unless it is the only stock available.
- **X1200 and the audio hat both want the GPIO header.** Confirm the stacking
  order works before assuming both fit.
- **Head weight** decides neck servos, so do not order those until a dummy mass
  exists. Silicone skin is heavier than it looks. See [hardware.md](hardware.md).
