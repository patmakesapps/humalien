# Humalien Docs

Humalien is a cyborg head: 3D printed parts with a skin-like texture, driven by
a natural voice conversation you can interrupt and talk over.

| Doc | What's in it |
| --- | --- |
| [architecture.md](architecture.md) | How the brain and the node split the work, and why |
| [voice-pipeline.md](voice-pipeline.md) | Why the robot was answering itself, and how it's fixed |
| [hardware.md](hardware.md) | Pi 5, Waveshare hat, audio devices, echo cancellation |
| [vision.md](vision.md) | USB webcam face tracking and the gaze-target contract |

## The two machines

```
┌──────────────────────────┐          ┌──────────────────────────┐
│  BRAIN                   │          │  NODE                    │
│  brain/                  │          │  node/                   │
│                          │◄────────►│                          │
│  Asus laptop → Jetson    │  ws://   │  Raspberry Pi 5          │
│  All the logic           │  :8765   │  Microphone + speaker    │
└──────────────────────────┘          └──────────────────────────┘
          │
          │ wss://
          ▼
   OpenAI Realtime API
```

The node is a dumb pipe. Every decision lives in the brain. That's what makes
swapping the Asus for a Jetson Orin Nano a non-event.

## Running it

**On the Pi:**

```bash
cd node
python -m humalien_node.server
```

**On the brain:**

```bash
cd brain
cp .env.example .env        # then fill in OPENAI_API_KEY
python voice_core.py
```

**Without a Pi** (testing on a laptop with headphones), run the simulator
instead of the Pi node, and point `HUMALIEN_PI_URL` at `ws://127.0.0.1:8765`:

```bash
cd brain
python tools/list_audio_devices.py   # pick your real mic, not a loopback
python tools/desktop_node.py
```

To preview face tracking with a USB webcam, see [vision.md](vision.md).

## Tests

```bash
cd brain
$env:PYTHONPATH = "."          # PowerShell; use export on Linux
python tests/test_audio_adapter.py
python tests/test_playback.py
```
