# Hardware consolidation

Status: planned prerequisite for date/time and LumaKit delegation work.

## Goal

Move the complete Humalien runtime from the present laptop/Pi split onto one
robot-mounted computer with enough memory and sustained compute capacity. The
candidate platforms are:

- a Raspberry Pi 5 with more RAM;
- a Jetson Orin Nano.

After consolidation, microphone capture, speaker playback, camera perception,
conversation coordination, memory, gestures, and eye state should run on the
same device.

## Qualification, not objection

More RAM solves only memory pressure. It does not guarantee inference speed,
audio scheduling, thermal stability, or sufficient CPU/GPU headroom. Hardware
selection must be based on a representative benchmark rather than memory size
alone.

The Jetson offers a stronger acceleration path for local perception and future
local models, but moving away from Raspberry Pi hardware may require new GPIO,
PCA9685, NeoPixel, audio-device, or service integration. The Pi may require
less driver work if it passes the performance gates.

## Do not couple the brain directly to device drivers

The internal WebSocket should be replaced behind a transport contract, not by
embedding ALSA, servo, and pixel details directly into `voice_core.py`.

Conceptually:

```text
voice core / playback / gestures / mood
                 |
          HardwareTransport
           /             \
 LocalHardwareTransport   WebSocketHardwareTransport
 normal consolidated path current split/dev fallback
```

The transport should cover at least:

- reading microphone PCM;
- writing paced speaker PCM;
- sending poses;
- setting eye mood, level, and brightness;
- limping/releasing actuators;
- reporting hardware readiness and failure.

The local implementation may use queues or direct async adapters, but it must
preserve ordering between audible output and the movement/expression driven by
that output.

## What "the WebSocket goes away" means

The normal consolidated path should no longer require the internal
`brain <-> hardware node` WebSocket on port 8765.

It is still useful to retain the WebSocket transport for:

- desktop simulation;
- remote hardware diagnosis;
- comparing a new local transport against the known protocol;
- temporarily splitting the brain and body again after a hardware failure.

The following connections are outside this retirement decision:

- the brain's WebSocket connection to OpenAI Realtime;
- the proposed authenticated local HTTP connection to LumaKit;
- any optional remote administration surface.

## Evaluation gates

Before selecting or cutting over to a platform, test the real workload:

1. Realtime audio capture, resampling, playback, and interruption without
   underruns.
2. Camera capture, face detection/recognition, gaze, and optional preview.
3. Servo and eye updates while audio and vision are busy.
4. Memory usage with all services active and useful reserve remaining.
5. CPU/GPU load and temperature during a multi-hour conversation soak.
6. Reconnect behavior after network, OpenAI, camera, and audio failures.
7. Clean startup and shutdown under the target service manager.
8. Device-driver compatibility for the selected audio, servo, and eye
   hardware.

## Migration sequence

1. Capture baseline latency, memory, temperature, and audio reliability on the
   current split system.
2. Introduce the hardware transport boundary while retaining the existing
   WebSocket implementation.
3. Bring up a local transport on the candidate device.
4. Run both paths against the same behavioral and hardware safety tests.
5. Soak-test the complete consolidated runtime.
6. Make local transport the default only after it reaches functional and
   safety parity.
7. Keep remote transport selectable through configuration.
8. Begin clock and LumaKit delegation work only after the consolidated system
   is stable.

## Acceptance criteria

Consolidation is complete when:

- the robot boots without the laptop;
- conversation, vision, memory, motion, and eyes operate together;
- speech does not starve while vision or background services are busy;
- actuator limits and disconnect behavior remain enforced locally;
- the robot recovers cleanly from expected network and device failures;
- sustained memory and thermal measurements retain safe headroom;
- desktop/remote-node mode remains available as an explicit fallback.

