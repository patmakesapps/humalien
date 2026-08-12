# The voice pipeline

## The bug: Humalien was talking to itself

The symptom was the robot answering its own replies in a loop. Four separate
causes were stacked on top of each other, and only the first is obvious.

### 1. Nothing gated the microphone

`microphone_to_brain` streamed unconditionally, and every byte went into
`input_audio_buffer.append`. Whatever the speaker played and the microphone
heard went straight back into the model's ear. Semantic VAD heard coherent
speech, decided it was the user's turn, and answered.

That's the loop. On headphones it's leakage. Inside a 3D printed skull with a
speaker two inches from the hat's microphones, it is far worse.

### 2. A loopback input device will do it digitally

Worth ruling out before anything else. If the desktop simulator's input device
is Stereo Mix, "What U Hear", or a virtual cable, the speaker is wired straight
into the model with no acoustics involved at all.

```bash
python tools/list_audio_devices.py
```

### 3. The brain didn't know when the robot was actually speaking

This is the deeper one. The Realtime API delivers a response's audio in a
**burst**, far faster than it can be played — a 10 second reply arrives in well
under a second.

The old code forwarded each delta the moment it arrived, and the node wrote it
straight into `aplay`'s stdin. So `response.output_audio.done` fired, the log
said "stopped speaking", and the speaker still had nine seconds queued.

Any microphone gate keyed off those events would open while the robot was
mid-sentence. And there was no way to un-send that audio: an interruption left
the robot talking for seconds.

### 4. No interruption handling at all

Nothing sent `response.cancel`, nothing dropped queued audio. The server's
`interrupt_response` stops *generation*, but audio already in flight downstream
is unaffected by it.

### Bonus: a latent crash

`PiToModelAudio.convert` raised `ValueError` on incomplete stereo frames, and
`np.frombuffer(..., "<i2")` raises on an odd byte count. The node's
`microphone.stdout.read(3840)` reads a pipe with `bufsize=0`, which can return a
short read at **any** byte boundary.

When it did, the task raised, `FIRST_COMPLETED` fired, and the whole voice core
tore down. An odd-length read would also have permanently swapped the left and
right channels.

## The fix: the brain owns the clock

### `PacedPlayback`

The single idea that makes everything else work. Model audio goes into a queue
that drains at **wall-clock rate**, keeping at most ~150 ms in flight to the
node.

Three problems collapse into one solution:

- **Interruption** is ~150 ms instead of ~9 seconds, because that's all that has
  left the building.
- **`is_speaking` becomes truthful.** The queue knows how many samples remain,
  so it knows when sound is actually coming out of the head.
- **No flush protocol is needed.** The Pi never holds enough audio to be worth
  clearing, so `server.py` needs no control channel. (`aplay` is started with a
  short `--buffer-time` to keep its own buffer from undoing this.)

### The microphone gate

`mic_gate.py` holds a swappable policy with one property, `is_open`:

| Gate | Behaviour | Needs |
| --- | --- | --- |
| `half_duplex` | Closed while `playback.is_speaking` | Nothing. **Default.** |
| `open` | Always listening | An echo-cancelled mic source |

`half_duplex` is a hard stop on self-hearing and works everywhere, at the cost of
barge-in: the robot can't be interrupted while it talks.

`open` is where natural conversation comes from, and it is only safe once the
speaker has been subtracted from the microphone signal in hardware or by the OS.
See [hardware.md](hardware.md) for the PipeWire setup. It's a config change on
the Pi plus `HUMALIEN_MIC_GATE=open` — no code change.

While the gate is closed the microphone audio is still fed through the
resampler and discarded, so its internal state stays continuous and reopening
doesn't produce a click.

### Interruption

On `input_audio_buffer.speech_started`, if the robot is speaking, the brain
drops the playback queue, resets the output resampler, and sends
`response.cancel` — but only when a response is actually active, since
cancelling a finished response returns an API error.

Note that `output_audio_buffer.clear` is **WebRTC/SIP only** and unavailable on
the WebSocket transport. That's precisely why the client-side pacer matters.

### Session settings

Two additions worth knowing about:

- **`transcription`** — the input transcript is logged as `User said: "..."`.
  This is the best diagnostic you have for this class of bug: if the robot ever
  starts hearing itself again, you will see it transcribing its own words.
- **`noise_reduction: far_field`** — right choice for a robot heard across a
  room rather than a headset.

`turn_detection` is now explicit about `create_response` and `interrupt_response`
rather than relying on defaults, and `eagerness` is exposed as
`HUMALIEN_VAD_EAGERNESS` (`low` / `medium` / `high` / `auto`). Turn it down if
Humalien starts cutting you off mid-thought.

### Errors no longer kill the robot

`voice_core.py` logs Realtime API errors instead of raising. A stray cancellation
or one unsupported field should not take the head down mid-conversation. The
smoke test still raises, which is what you want there.

## Tuning

| Setting | Where | Default | Effect |
| --- | --- | --- | --- |
| `LEAD_SECONDS` | `playback.py` | `0.15` | Audio in flight. Lower = snappier interruption, more sensitive to network jitter. |
| `TAIL_SECONDS` | `playback.py` | `0.25` | Grace period before the mic reopens. Raise if the tail of Humalien's speech retriggers it. |
| `BUFFER_TIME` | `node/server.py` | `80000` µs | `aplay`'s own buffer. Raise if you hear crackling on the Pi. |
| `HUMALIEN_VAD_EAGERNESS` | `.env` | `auto` | How fast the server decides your turn ended. |

## Verifying it works

1. `python tools/list_audio_devices.py` — confirm the input is a real mic.
2. `python tools/realtime_smoke_test.py` — confirm the key and model.
3. Start the node, then `python voice_core.py`.
4. Watch for `Microphone closed — Humalien is speaking` when it talks, and
   `Microphone open` when it stops.
5. The `User said:` lines should only ever contain **your** words. If Humalien's
   own sentences show up there, the gate isn't holding — check for a loopback
   input device first.
