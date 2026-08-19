# Architecture

## The split

Two machines, one rule: **the node is a dumb pipe, the brain owns every
decision.**

The node's entire job is to turn a microphone into bytes on a socket, and bytes
on a socket into sound. It has no idea what a conversation is, when the robot is
speaking, or that OpenAI exists. That matters because the brain is going to move
— Asus laptop today, Jetson Orin Nano later — and the node should not care.

### Brain — `brain/`

| File | Job |
| --- | --- |
| `voice_core.py` | The conversation loop. Wires everything together. |
| `realtime_client.py` | Opens the Realtime session, sends/receives events. |
| `playback.py` | Releases the model's audio at the speed it is spoken. |
| `mic_gate.py` | Decides whether the microphone is listening right now. |
| `audio_adapter.py` | 48 kHz stereo ↔ 24 kHz mono resampling. |
| `vision.py` | YuNet face detection for the USB camera. |
| `gaze.py` | Servo-independent target coordinates and smoothing. |
| `recognizer.py` | SFace embeddings — turns a face into a unit vector. |
| `people.py` | SQLite store of who Humalien has met and what it knows. |
| `perception.py` | Who is in the room right now. Detect, embed, match. |
| `describe.py` | Answers a question about the current frame, on request. |
| `eyes.py` | Runs the camera alongside the conversation, on a worker thread. |
| `tool_registry.py` | Declares, validates and runs tools under one error contract. |
| `robot_tools.py` | What Humalien can do besides talk: look, who_is_here, remember_name. |

`tools/` holds things you run by hand, not part of the robot:

- `desktop_node.py` — stands in for the Pi so you can test on a laptop
- `list_audio_devices.py` — find the right input/output device indices
- `realtime_smoke_test.py` — confirm the API key and model work
- `audio_roundtrip.py` — record 3 s through the Pi and play it back
- `vision_preview.py` — preview face tracking and normalized gaze targets
- `people_preview.py` — live recognition, naming, and looking
- `fetch_models.py` — download the YuNet and SFace ONNX models

### Node — `node/`

`humalien_node/server.py` is a WebSocket server that spawns `arecord` and
`aplay` against the Waveshare hat and shuttles raw PCM in both directions.
That's the whole thing, and it should stay that way.

Its entire dependency list is `websockets`, and it imports nothing from
`brain/`. That is the measure of whether the node is still dumb — if that list
grows, something has leaked downward. See [running.md](running.md) for what
must never be installed on the Pi.

## Audio formats

The Pi runs at its hat's native rate; the model has its own. The brain converts.

```
Pi          48 kHz  stereo  S16_LE   (Waveshare hat native)
Model       24 kHz  mono    PCM16    (Realtime API)
```

Going up, the brain averages the hat's two microphone channels into mono. Going
down, it copies the model's mono into both speaker channels. `soxr` does the
rate conversion as a *streaming* resampler, so it holds state between chunks —
which is why `audio_adapter.py` instances are per-response, not global.

## Data flow

```
mic → arecord → ws bytes → PiToModelAudio → mic gate → input_audio_buffer.append
                                                              │
                                                       semantic VAD decides
                                                       the turn is over
                                                              ▼
speaker ← aplay ← ws bytes ← PacedPlayback ← ModelToPiAudio ← response.output_audio.delta
```

The two interesting boxes are `mic gate` and `PacedPlayback`. Both exist for one
reason: without them the robot hears itself and answers itself. See
[voice-pipeline.md](voice-pipeline.md).

Vision is a second, entirely independent path. It never touches the node:

```
                        ┌→ select_primary_face → GazeController → GazeTarget
webcam → YuNet detect ──┤                                          (x, y, state)
                        └→ SFace embed → PeopleStore.match → Sighting
                                                              (who, confidence)
```

One detection pass feeds both. Gaze wants *where* a face is; recognition wants
*whose* it is. Neither involves a language model, which is why both can run
continuously — see [people.md](people.md).

Looking is the exception, and it's deliberately pull-only: `describe.py` runs a
vision model over a single frame when the conversation asks, never on a timer.
That one decision is what keeps the cost bounded.

## Why the node stays dumb

It's tempting to push work down to the Pi — flush commands, buffer management, a
local VAD. Resist it. Every piece of state that lives on the Pi is state the
brain has to stay in sync with over a network link, and the failure modes are
miserable to debug across two machines.

The current design needs **zero** control protocol between brain and node. The
brain never has to tell the Pi to stop talking, because it never gave the Pi more
than ~150 ms of audio in the first place. That's the whole trick.

## Vision before servos

The first eye-tracking slice stays on the brain. It turns a face in the webcam
frame into normalized `x` and `y` gaze targets, but it does not know about PWM,
servo reversal, or mechanical limits. That boundary lets the camera pipeline be
tested now and the actuator mapping be calibrated later without rewriting it.

See [vision.md](vision.md) for the target contract and preview command.

## What's not built yet

Servos — jaw, neck, eyes. Two signals are already waiting for them, produced
independently and for different reasons:

| Signal | Source | Drives |
| --- | --- | --- |
| `mouth.speaking` | `PacedPlayback.is_speaking` | Jaw |
| `gaze_target` | `GazeController.update()` | Eyes, later neck |

The hook for the first is marked in `voice_core.py` by the two
`# Future: send mouth.speaking` comments. The second already emits its wire
shape today — `tools/vision_preview.py --emit-json` prints exactly the message
the control layer will consume.

Both should land as JSON control messages on the **existing** socket, handled by
one new module on the node alongside audio. One control channel, two producers —
not two channels.

`PacedPlayback.is_speaking` is the correct signal to drive a jaw from precisely
because it tracks real playback rather than generation. A jaw driven off
`response.output_audio.delta` would finish moving several seconds before the
speaker went quiet, which is the same underlying bug that made the robot answer
itself.
