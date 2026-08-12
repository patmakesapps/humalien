# Hardware

## Current setup

| Part | Role | Status |
| --- | --- | --- |
| Raspberry Pi 5 | Voice node, sensors | In use |
| Waveshare audio hat | Mics + speaker out | In use |
| USB webcam | Face tracking for the eyes | Prototype, on the brain |
| Asus laptop | Brain | In use |
| Jetson Orin Nano | Brain | Planned replacement |
| 3D printed head | Chassis, skin-like texture | In progress |
| Eye / jaw / neck servos | Motion | Not started |
| PCA9685 | Servo PWM over I²C | Planned |
| VL53L1X | Distance / presence | Planned |
| SHT31 | Temperature, humidity | Planned |

## Build order

Eyes first, then jaw, then neck. Not because eyes are easiest — because
they close a loop that already exists in software.

`gaze.py` has produced normalized `x`/`y` targets since the first vision
commit, smoothed, with hold-and-recentre behaviour, and nothing consumes them.
Eyes are that consumer. Building them turns a tested contract into something
that moves, and it does it with two micro servos and almost no load.

The real reason though: **eyes are the cheapest way to find out whether the
gaze pipeline feels right.** Recognition runs at 4 Hz, smoothing is
exponential with a 0.12 s constant, and none of that has ever driven a physical
thing. Whether it reads as alive or as a twitching machine is not answerable
from the code. Two servos on a bench answers it in an afternoon, and any tuning
that comes out of it applies to the neck later.

They also de-risk the entire motion stack on the cheap parts — PCA9685 wiring,
I²C addressing, calibration, travel limits, rate limiting, and the brain-to-node
motion protocol are all identical when the neck arrives. Learn them where a
mistake costs a $4 servo rather than a printed neck.

**The one thing that cannot wait for the neck:** head *weight*. It sets the
neck torque, and torque sets the whole mechanical design. So while eyes are
being built, keep a running weight estimate — including the silicone, which is
heavier than people expect. Do not print a finished head before a neck test rig
has lifted a dummy mass of the same weight.

## Motion and power

### The rule that matters most

**Never power servos from the Pi's 5 V rail.** A micro servo pulls around
700 mA stalled, a neck servo 2–3 A, and those spikes will brown out a Pi 5 and
corrupt its filesystem. This is the most common way builds like this die.

Servos get their own supply, sharing a **common ground** with the Pi, and a
1000 µF electrolytic across the servo rail near the driver to absorb the
transients.

### Rails

```
19V brick (100W+)
   ├── Jetson Orin Nano        19V direct, ~25W peak, needs active cooling
   ├── buck -> 5V 8A           Pi 5, audio hat, speakers
   └── buck -> 6V high current servos only, own ground return to a star point
```

On the bench, two separate wall supplies with grounds tied is uglier and far
easier to debug. Consolidate later.

**Add a servo power cutoff** — a MOSFET or relay the Pi enables *after* boot,
once it has written known-good positions. Servos snap to wherever they think
they are the instant they get power, which is how printed linkages get
destroyed on first plug-in.

### Servos

| Job | Load | Class |
| --- | --- | --- |
| Eyes, eyelids, jaw | grams | Micro, metal gear — MG90S |
| Neck yaw and pitch | the whole head | High torque digital, ~20 kg·cm — DS3218 class |

Pitch is harder than yaw because of the moment arm, and silicone skin adds
several hundred grams that land entirely on the neck.

**Drive them from a PCA9685 over I²C, not Pi GPIO.** Software PWM on a Pi 5
jitters and servos visibly twitch. The PCA9685 gives 16 channels of hardware
PWM for a few pounds and shares the I²C bus with the sensors.

This also fits the split the software already has. `gaze.py` deliberately knows
nothing about servos; the brain decides *where to look* and the node converts
that to PWM. The node keeps executing rather than deciding.

### Sensors

All I²C, all on the Pi, all off the audio hat's pass-through header:

| Sensor | Part | Why |
| --- | --- | --- |
| Servo PWM | PCA9685 | Hardware PWM, 16 channels |
| Distance | VL53L1X | Time-of-flight. No echo timing, no 5 V logic, shares the bus |
| Temp, humidity | SHT31 | I²C rather than DHT22's bit-banged protocol |

The distance sensor belongs in the head facing forward — it is a presence and
approach sensor, so it wants to look where the face looks.

**The temperature sensor will lie to you.** Mounted inside a sealed head full
of Pi, servos and an amplifier, it measures the head, not the room. If room
conditions are what you want, it needs venting or a home in the base.

## The neck is the real design problem

Every wire crossing the neck joint is a wear point, so the question is what has
to cross at all.

If the Pi lives in the head, only power crosses — it reaches the brain over
WiFi. That is a strong argument for putting it up top despite the heat.

Which leaves the camera, and settles the question left open above. Vision runs
on the brain, but the camera has to be in the head:

- **USB through the neck** keeps the current architecture. Workable if rotation
  is limited to roughly ±90–120° with a service loop; USB 2.0 webcam cable is
  thin and takes flex well.
- **CSI camera on the Pi, streaming to the brain** means only power crosses,
  but the node stops being a dumb pipe and there is a video stream to maintain.

The USB run with limited rotation is the better trade. A head that turns 100°
each way is plenty, and the node stays dumb.

## Skin

Platinum-cure silicone poured into a printed mould. **Ecoflex 00-30/00-50** for
genuinely soft skin, **Dragon Skin** where it has to survive moving parts.

Three things that catch people out:

- **Cure inhibition.** Platinum silicone refuses to cure against sulfur clays,
  latex, some superglues, and occasionally PLA additives. Test a small pour on
  the actual filament before committing to a face mould.
- **It will not bond to PLA.** Design mechanical anchors — undercuts, holes, an
  embedded mesh — or the skin peels away from the substrate.
- **Layer lines transfer.** Print moulds at 0.1 mm and smooth them, or every
  line shows up in the face.

The A1's build volume is 256 mm cubed, so a head will need splitting with
alignment pins. Plan the split lines where a skin seam can hide them.

## Audio device

The node targets ALSA device `hw:2,0` at 48 kHz stereo S16_LE. If the hat lands
on a different card number:

```bash
arecord -l     # capture devices
aplay -l       # playback devices
```

Then update `ALSA_DEVICE` in `node/humalien_node/server.py`.

Sanity check the hardware on its own before involving the brain:

```bash
cd node
python -m humalien_node.audio     # records 3 s, plays it back
```

## Camera

Face tracking currently runs on the **brain**, with a USB webcam plugged into
the laptop. That's the right place for the prototype — OpenCV wants the CPU the
brain has, and it keeps the node dumb.

`opencv-python` is in `brain/requirements.txt`, but it is a large wheel and is
easy to miss if your virtualenv predates it:

```bash
cd brain
python -m pip install -r requirements.txt
python -c "import cv2; print(cv2.__version__)"
```

Pick a camera index by trial — OpenCV numbers them by enumeration order, not by
anything stable:

```bash
python -m tools.vision_preview --camera 0     # then 1, 2, ...
```

See [vision.md](vision.md) for what the preview shows and how loss behaves.

### Where the camera ends up

Open question, worth deciding before the head is closed up. The eyes are in the
head; the brain is not.

- **Camera on the brain** (today) — a USB run from the head to the laptop or
  Jetson. Simplest software, no new protocol, but a cable that has to survive
  the neck.
- **Camera on the Pi** — the node grows a second job and has to stream frames or
  run detection itself. That contradicts "the node is a dumb pipe", and a Pi 5
  doing Haar cascades at 30 fps alongside audio is not free.

Neither is obviously right. What settles it is whether the neck cable can carry
USB, which is a mechanical question, not a software one. The gaze contract in
[vision.md](vision.md) is deliberately independent of the answer.

## Desktop testing

`brain/tools/desktop_node.py` speaks the same protocol as the Pi node using
`sounddevice`, so you can develop the whole conversation loop on a laptop.

```bash
cd brain
python tools/list_audio_devices.py
```

Put the indices in `.env` as `HUMALIEN_DESKTOP_INPUT_DEVICE` and
`HUMALIEN_DESKTOP_OUTPUT_DEVICE`, and point `HUMALIEN_PI_URL` at
`ws://127.0.0.1:8765`.

> **Change that line, don't add a second one.** `.env` is last-value-wins, so
> a duplicate `HUMALIEN_PI_URL` means the bottom one silently decides and
> editing the top one does nothing. See [running.md](running.md).

Also check the device you picked is the right *direction*. An output device set
as the input fails with PortAudio's `Invalid number of channels [-9998]`, which
sounds like a format problem and isn't. `list_audio_devices.py` prints input and
output channel counts so you can tell them apart.

> **Pick a real microphone.** Stereo Mix, "What U Hear", and virtual cables are
> loopback devices — they wire the speaker directly into the model, and it will
> answer itself with no acoustics involved.

## Echo cancellation — unlocking barge-in

The default `half_duplex` microphone gate stops the robot hearing itself by
simply not listening while it talks. That works everywhere and needs nothing
from the hardware, but it means Humalien can't be interrupted.

For real barge-in — talking over the robot the way ChatGPT voice mode lets you —
the speaker has to be subtracted from the microphone signal. **Let the OS do
it.** PipeWire ships a WebRTC echo canceller that exposes an echo-cancelled
virtual source, so this is a config file rather than code.

Create `/etc/pipewire/pipewire.conf.d/99-echo-cancel.conf`:

```
context.modules = [
  { name = libpipewire-module-echo-cancel
    args = {
      library.name = aec/libspa-aec-webrtc
      capture.props = { node.name = "effect_input.echo-cancel" }
      source.props  = { node.name = "humalien_mic" }
      playback.props = { node.name = "effect_output.echo-cancel" }
      sink.props    = { node.name = "humalien_speaker" }
    }
  }
]
```

Restart PipeWire, confirm the source exists, then switch the node's
`ALSA_DEVICE` to the new virtual devices and set `HUMALIEN_MIC_GATE=open` in the
brain's `.env`. No code changes on either side.

```bash
systemctl --user restart pipewire pipewire-pulse
pactl list short sources | grep humalien
```

**Validate, don't assume.** AEC has historically been flaky on some Raspberry Pi
OS builds. If it doesn't hold up, stay on `half_duplex` — a robot that can't be
interrupted is much better than one that argues with itself.

Reference: [PipeWire module-echo-cancel](https://docs.pipewire.org/page_module_echo_cancel.html)

## Physical isolation

AEC works far better when it has less echo to remove. When the head is
assembled:

- Put as much distance as the skull allows between the speaker and the hat's
  microphones.
- Isolate the speaker in its own baffled cavity so vibration doesn't travel
  through the printed frame into the mics.
- A foam gasket around the mic openings costs nothing and helps more than it
  should.
- Aim the speaker away from the microphone axis — downward or forward out of the
  mouth, with the mics higher up.

Every dB of acoustic isolation is a dB the echo canceller doesn't have to fight.

## Network

Brain and node talk over plain WebSocket on port 8765 on the LAN, no TLS, no
auth. Fine for a home network; revisit before this thing goes anywhere else.

Audio upstream is 48 kHz stereo 16-bit = ~192 KB/s. Comfortable on wired or
decent WiFi. If the link ever becomes the bottleneck, the cheapest win is
downmixing to mono on the Pi, which halves it — but don't do that before it's
actually a problem.
