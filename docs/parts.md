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

## Ordered — eye motion

Everything needed to make eyes move. Order `111-1528335-1842633`, placed
13 Aug 2026, $144.27. Arrives 14 Aug, except the capacitor on 16 Aug.

| Part | Chosen | Price |
| --- | --- | --- |
| PCA9685 servo driver | HiLetgo, 2-pack | $13.99 |
| MG90S micro servos | Beffkkip, 8-pack (6 used, 2 spare) | $23.98 |
| Power supply, 5 V 5 A | ALITOVE, 5.5 × 2.5 mm plug | $15.50 |
| Capacitor, 1000 µF 25 V | Rubycon low-ESR, 10-pack | $6.99 |
| Camera | Arducam **B0385** / OV9782, Amazon `B0CLXZ29F9` | $64.99 |
| Soldering station | YIHUA 926 III, 60 W, with helping hands — bought separately | $39.99 |

Jumper wires already on hand. The ALITOVE supply (`B078RT3ZPS`) ships with a
green female barrel-jack-to-screw-terminal adapter, so the power rail needs no
soldering: barrel plug → screw terminal → two wires → PCA9685 V+ / GND. The
only soldering in this build is the PCA9685's own pin headers.

**The capacitor is not a blocker for first movement.** One or two servos moving
slowly won't spike enough to matter, so printing, soldering and a first sweep can
all happen before it arrives. Fit it before running all six together.

**Soldering lead-free**, which is what the YIHUA kit ships with. Run the iron at
350–370 °C, keep the tip tinned, and heat the pad and pin together for about two
seconds before feeding solder into the joint rather than onto the iron. Lead-free
joints look dull and slightly grainy — that is normal and not a cold joint. Judge
by shape: a concave cone hugging the pin, not a ball sitting on top.

Solder the **spare** PCA9685 first. The 2-pack means the first attempt costs
nothing.

The camera is **B0385, not B0332**. B0332 is the OV9281 *monochrome* sensor,
which looks near-identical in listings — cheaper, faster, better in low light,
and useless here, since "what colour is the object in my hand" is a question
Humalien is expected to answer. Check the listing says OV9782.

## Ordered — eye glow

Two NeoPixel Ring 12s, shipping as of 13 Aug. The plan they were bought for
changed the same day — see the design brief: the eye glow now comes from a
5050 pixel *inside* each printed eyeball, and the rings frame the speaker
grilles in the ear ports instead. They are also the bench-test article for
driving WS2812 from the Pi 5 before any wire crosses an eye joint.

## Next to buy

| Part | Why |
| --- | --- |
| M12 lens with IR-cut filter | The B0385 stock lens has none, so colours skew towards IR |
| Qwiic-to-header adapter | To put the SHT41 and the VL53L1X on the same bus |
| 2 × addressable 5050 mini pixel | One inside each eyeball — the glow-from-within |
| 74AHCT125 level shifter | 3.3 V data into 5 V WS2812 — skip if it was in the ring order |

## Buy when the price is sane

| Part | Number |
| --- | --- |
| Jetson Orin Nano Super Dev Kit 8 GB | **945-13766-0005-000** |
| NVMe M.2 SSD, 256 GB+ | any |

$249 was the announcement price. NVIDIA's own marketplace lists **$399**, and
it is scarce enough that stock trackers exist for it — resellers were asking
$769. Nothing is blocked on this: the Asus is the brain, and everything runs
cloud-side today. The Jetson only buys embeddability and local inference,
neither of which is needed until there is a body. Set an alert on
nowinstock.net or hotstock.io and buy near MSRP.

## Planned, not yet specified

| Part | Role |
| --- | --- |
| 2 × DS3218 class, ~20 kg·cm | Neck yaw and pitch. Size only after weighing the head |
| Servo power for the neck | Separate again, and much beefier than the eyes need |

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

## Eye mechanism

[Will Cogley's Animatronic Eye Mechanism](https://makerworld.com/en/models/1184807-animatronic-eye-mechanism-e3-2)
on MakerWorld, also on
[Printables](https://www.printables.com/model/1220172-animatronic-eye-mechanism-e31).
Free, and MakerWorld opens straight into Bambu Studio for the A1.

Six micro servos: two pan, one tilt, three eyelid. Printing a proven mechanism
first answers whether 4 Hz recognition and a 0.12 s smoothing constant read as
alive, which is the question a custom design would otherwise be built on top of
untested. Model a bespoke one afterwards, reusing the tuning.

Both eyes are plain printed balls. **The camera and the VL53L1X live together
in the forehead**, side by side on `forehead_casing`, which keeps the vision
loop open — a camera that moves with the eye turns face position into an error
signal and needs a nulling loop instead — and keeps the distance reading from
swinging around with gaze.

> Until 13 Aug 2026 this read "the **left pupil** holds the VL53L1X, so
> distance is measured to whatever Humalien is looking at". Moving it to the
> forehead unblocked the eyeball, which had been waiting on board dimensions
> nobody publishes, and cut what crosses each eye joint from six wires to the
> three the 5050 pixel needs. See the note at the top of
> [eye-design-brief.md](eye-design-brief.md).

## Wiring

```
5V 5A supply ──► PCA9685 V+ screw terminal    servo power, separate rail
1000uF cap   ──► across V+ and GND            absorbs the start-up spike
Pi 3.3V/GND  ──► PCA9685 VCC/GND              logic only, tiny draw
Pi SDA/SCL   ──► PCA9685 SDA/SCL              from the audio hat pass-through
Pi GND       ──► supply GND                   COMMON GROUND, not optional
```

The Pi powers the chip. The separate supply powers the servos. They share only
ground.

## Things to check before ordering

- **The WM8960 is a small amplifier.** 5 W speakers on it will be safe but
  quiet. If Humalien cannot be heard across a room, the amp is the limit, not
  the speakers.
- **Jetson pricing.** Reseller bundles run close to twice NVIDIA's own $399. A
  $769 kit including an SSD, WiFi card and power supply is still worse than $399
  plus a $30 SSD, unless it is the only stock available.
- **X1200 and the audio hat both want the GPIO header.** Confirm the stacking
  order works before assuming both fit.
- **Head weight** decides neck servos, so do not order those until a dummy mass
  exists. Silicone skin is heavier than it looks. See [hardware.md](hardware.md).
