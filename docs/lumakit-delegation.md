# LumaKit delegation

Status: planned after hardware consolidation; not implemented.

## Decision

Tubby will reuse LumaKit for durable background computer work rather than
grow a second general-purpose agent framework inside Humalien.

Humalien remains the embodied conversational system. LumaKit remains the
autonomous work system. A narrow authenticated adapter joins them.

```text
person speaks
     |
Tubby / OpenAI Realtime
     | understands intent and decides whether delegation was requested
     |
delegate_task(...)
     |
authenticated local LumaKit API
     |
durable task store -> task runner -> configured provider/model -> tools
     |
immediate task id                         later status/result
```

## Responsibility boundary

Tubby and Humalien own:

- natural spoken interaction and personality;
- turn-taking and interruption;
- camera perception and recognition;
- personal memory;
- expression, gaze, and movement;
- deciding whether the user explicitly asked for background work;
- presenting task acceptance, status, and results conversationally.

LumaKit owns:

- durable task creation and history;
- autonomous planning and tool loops;
- workspace inspection and coding tools;
- the configured primary and fallback model/provider;
- checkpoints, retries, waiting, and restart recovery;
- filesystem and command safety boundaries;
- protected-action approvals;
- final task status and result.

This boundary avoids duplicate task databases, provider configuration,
approval systems, and recovery logic. It also keeps LumaKit's large general
tool set out of the latency-sensitive Realtime session.

## Planned Tubby tool surface

The first version should remain narrow:

### `clock()`

Return accurate local and UTC time before interpreting relative schedules.

```json
{
  "local_time": "2026-09-04T14:32:10-04:00",
  "timezone": "America/New_York",
  "utc_time": "2026-09-04T18:32:10Z"
}
```

### `delegate_task(...)`

Proposed fields:

- `title` — a short human-readable name;
- `goal` — the complete outcome, context, and constraints;
- `workspace` — a controlled alias, not an arbitrary path;
- `start_at` — optional timezone-aware ISO 8601 start time;
- `due_at` — optional timezone-aware ISO 8601 deadline;
- `notes` — optional additional constraints.

The handler posts the task to LumaKit and returns as soon as it is durably
accepted:

```json
{
  "accepted": true,
  "task_id": 42,
  "status": "planning"
}
```

It must not wait for the delegated job to finish.

### `task_status(task_id)`

Return a concise state suitable for the Realtime model to turn into a short
spoken answer: queued/planning, active, paused, blocked for approval, failed,
cancelled, or complete.

### Later additions

- `list_tasks()` after ownership and result selection are reliable;
- `cancel_task(task_id)` with an explicit user request;
- an approval bridge, if approvals should be possible through Tubby rather
  than LumaKit's existing web or Telegram surfaces;
- completion delivery once unsolicited speech behavior is designed.

The model-facing name should be `delegate_task`, not `create_agent`. The user
is delegating an outcome; whether LumaKit uses one agent session, resumes an
existing one, or changes execution strategy is an implementation detail.

## Realtime function-call lifecycle

OpenAI Realtime supports configuring functions on the session, receiving a
function call and its arguments, executing application code, returning a
`function_call_output` with the same call ID, and requesting the model's next
response. Humalien already follows that lifecycle for its present robot tools.

The delegation call therefore costs only the spoken request, structured tool
selection, and a short acknowledgement on Realtime. Planning, file reads,
edits, builds, tests, and retries occur under LumaKit's configured provider.
Keeping the Realtime session connected still incurs its normal conversational
usage; the delegated reasoning loop does not run on Realtime.

Reference: [OpenAI Realtime function calling](https://developers.openai.com/api/docs/guides/realtime-conversations#function-calling).

## LumaKit integration boundary

Prefer LumaKit's local HTTP API over importing its internal Python modules or
launching a subprocess per request.

The adapter should:

- talk to a long-running LumaKit service on loopback where possible;
- authenticate with LumaKit's installation token in an HTTP header;
- keep that token in local configuration, never in the model-visible schema,
  prompt, task text, logs, or tool result;
- use short connection and response timeouts;
- return a clear unavailable result when LumaKit is stopped;
- let LumaKit select its configured model and fallback;
- treat the returned task ID as the durable identity of the work.

Relevant LumaKit implementation:

- [background task tools](https://github.com/patmakesapps/LumaKit/blob/main/tools/runtime/task_tools.py);
- [durable task runner](https://github.com/patmakesapps/LumaKit/blob/main/core/task_runner.py);
- [task API and authentication](https://github.com/patmakesapps/LumaKit/blob/main/surfaces/web.py);
- [provider selection](https://github.com/patmakesapps/LumaKit/tree/main/core/providers).

If Humalien and LumaKit later run on different machines, loopback assumptions
no longer apply. The connection must then be deliberately secured rather than
merely exposing LumaKit's port on the local network.

## Safety and correctness requirements

### Explicit delegation

`delegate_task` is for work the user actually asks Tubby to perform in the
background. Tubby must not manufacture projects from casual conversation.

### Workspace allowlist

The Realtime model should choose stable aliases such as `humalien` or
`lumakit`. Local configuration maps those aliases to absolute directories.
Unknown or ambiguous workspaces cause a question, not a guessed path.

### Approval preservation

Humalien must never bypass LumaKit's protected-action approvals. A task that
needs approval stays blocked until approval arrives through an authorized
surface.

### Idempotency

Submission needs a client request identifier or equivalent deduplication so a
reconnect or repeated function event cannot create duplicate background jobs.

### Ownership

Tasks should eventually be associated with the recognized person who asked
for them. Until multi-person ownership is designed, delegation should use one
explicit owner identity and avoid exposing another person's task details.

### Honest status

Acceptance means only that LumaKit durably queued the task. Tubby must not say
the task is complete until LumaKit reports a terminal successful result.

## Completion behavior

Start with pull-based status:

> "Tubby, how is that coding task going?"

Tubby calls `task_status` and gives a brief answer. This avoids unexpected
speech and does not require a second event channel.

A later push design can let LumaKit deliver completion or approval events to a
small Humalien inbox. Humalien should queue them until:

- an intended recipient is present;
- the robot is not listening or already speaking;
- the event has not already been delivered;
- announcing it is appropriate for the conversation.

If no one is present, the result remains available for the next conversation.

## Implementation order

1. Complete and validate the single-device hardware deployment.
2. Add timezone-aware `clock()` and tests.
3. Add a small authenticated LumaKit client with mocked contract tests.
4. Add `delegate_task` with workspace aliases, idempotency, and immediate
   acknowledgement.
5. Add `task_status` and test every LumaKit state.
6. Exercise coding tasks using the configured local/cloud Ollama model without
   holding a Realtime tool call open.
7. Validate approval behavior and service outages.
8. Add task ownership and listing if needed.
9. Design push completion as a separate feature.

## Non-goals

- Do not expose LumaKit's full registry to the Realtime model.
- Do not give Realtime a raw shell or arbitrary filesystem paths.
- Do not copy LumaKit's task runner into Humalien.
- Do not make LumaKit responsible for realtime audio, vision, or actuator
  control.
- Do not remove the existing robot-tool safety boundaries.
- Do not begin this integration before hardware consolidation is stable.

