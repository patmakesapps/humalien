# Current architecture

Status: current implementation, September 2026.

## Why the runtime is split

The current Raspberry Pi 5 does not have enough memory and compute headroom to
run the complete brain reliably. The laptop therefore runs conversation,
perception, memory, and model coordination, while the Pi remains the physical
hardware node.

```text
Pi 5 hardware node                         Laptop brain
------------------                        ------------
microphone  ─────── binary PCM ─────────> voice core
speaker     <────── binary PCM ────────── OpenAI Realtime client
servos      <────── pose messages ─────── gesture controller
eye rings   <────── mood messages ─────── mood controller
                         WebSocket :8765
```

The hardware node runs
[`node/humalien_node/server.py`](../node/humalien_node/server.py). The brain
connects to `HUMALIEN_PI_URL` in
[`brain/voice_core.py`](../brain/voice_core.py). For laptop-only development,
[`brain/devtools/desktop_node.py`](../brain/devtools/desktop_node.py) provides
the same WebSocket contract using desktop audio devices.

The hardware WebSocket is currently required. The brain opens it before it
opens the OpenAI Realtime session, and the conversation loop does not start
without a reachable hardware node. The supervisor retries after a failure.

## What the hardware WebSocket carries

One ordered connection carries:

- microphone PCM from the node to the brain;
- speaker PCM from the brain to the node;
- servo pose messages;
- eye mood, shared color, gaze, one-shot effect, level, and brightness messages;
- node readiness and control messages such as `limp`.

Keeping speech, movement, and expression on one ordered connection prevents
the physical performance from drifting away from audible speech. The node
still enforces its own servo limits and safe disconnect behavior.

This internal WebSocket must not be confused with the separate encrypted
WebSocket from the brain to the OpenAI Realtime API. Consolidating the robot
can remove the Pi-to-laptop hop; it does not remove the Realtime connection.

## Model-callable tools

Tubby currently exposes twelve tools from
[`brain/robot_tools.py`](../brain/robot_tools.py):

| Tool | Purpose |
| --- | --- |
| `look(question)` | Capture a camera frame and answer a visual question. |
| `who_is_here()` | Privately inspect recognised people and strangers in view. |
| `remember_name(name)` | Associate an introduced name with a visible unfamiliar face. |
| `feel(feeling)` | Temporarily express an emotion through the eyes. |
| `set_eye_color(color, save_as_default?)` | Change both eyes together, optionally persisting the default. |
| `wink(eye)` | Briefly wink the robot's own left or right eye. |
| `celebrate(style?)` | Play a brief gold or rainbow effect across both eyes. |
| `remember(fact, about?)` | Persist a personal or general memory. |
| `recall(about?)` | Retrieve memories, optionally narrowed by text. |
| `revise(id, fact)` | Replace an existing memory. |
| `forget(id)` | Permanently remove an existing memory. |
| `move(part, direction)` | Temporarily command the head or arms. |

Listening, speech playback, face tracking, conversational eye states, and
automatic gesturing are continuous capabilities rather than callable tools.

The node owns the 40 Hz eye renderer. Purple remains the factory default;
chosen colors crossfade over about 300 ms, anger temporarily forces red, and
face tracking moves a subtle highlight with the head's gaze. Both eyes always
share one base color in the current design. Saved defaults are stored in the
`robot_settings` table beside the robot's other SQLite-backed state.

## Tool code boundaries

- [`brain/tool_registry.py`](../brain/tool_registry.py) provides registration,
  schemas, validation, execution, and the common result contract.
- [`brain/robot_tools.py`](../brain/robot_tools.py) contains the capabilities
  the Realtime model can actually call.
- [`brain/devtools`](../brain/devtools) contains human-run diagnostics, setup
  scripts, previews, and the desktop hardware simulator. The registry does not
  scan this directory.

The current explicit registry is appropriate for the small, safety-sensitive
tool set. If the tool count grows substantially, model-facing tools can be
split into explicit modules such as `agent_tools/vision.py`,
`agent_tools/memory.py`, and `agent_tools/embodiment.py`. Registration should
remain explicit until Humalien genuinely needs third-party plugins.

## Date and time limitation

Tubby has internal timers but no dependable model-visible clock. The persona
contains no current timestamp, and no registered tool returns the local date,
time, timezone, or UTC offset. A model answer about "now", "tomorrow", or a
deadline is therefore not authoritative.

The planned solution is a small `clock()` tool returning timezone-aware local
and UTC timestamps. A connection-start timestamp may also be added to session
instructions for general orientation, but the tool remains the source of truth
for exact time and scheduling.
