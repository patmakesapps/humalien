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

`tools/` holds things you run by hand, not part of the robot:

- `desktop_node.py` — stands in for the Pi so you can test on a laptop
- `list_audio_devices.py` — find the right input/output device indices
- `realtime_smoke_test.py` — confirm the API key and model work
- `audio_roundtrip.py` — record 3 s through the Pi and play it back

### Node — `node/`

`humalien_node/server.py` is a WebSocket server that spawns `arecord` and
`aplay` against the Waveshare hat and shuttles raw PCM in both directions.
That's the whole thing, and it should stay that way.

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

## Why the node stays dumb

It's tempting to push work down to the Pi — flush commands, buffer management, a
local VAD. Resist it. Every piece of state that lives on the Pi is state the
brain has to stay in sync with over a network link, and the failure modes are
miserable to debug across two machines.

The current design needs **zero** control protocol between brain and node. The
brain never has to tell the Pi to stop talking, because it never gave the Pi more
than ~150 ms of audio in the first place. That's the whole trick.

## What's not built yet

The obvious next layer is servos — jaw, neck, eyes. The hook is already in
`voice_core.py`: the two `# Future: send mouth.speaking` comments mark where
the brain learns the robot started and stopped talking.

When that lands, it should be a JSON control message on the *existing* socket,
handled by a new module on the node alongside audio. `PacedPlayback.is_speaking`
is the correct signal to drive a jaw from — it tracks real playback, not
generation.
