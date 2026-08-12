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
