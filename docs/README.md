# Humalien documentation

These documents describe the current robot architecture and the agreed path
toward a consolidated, agent-capable Tubby. They are design records, not a
claim that the planned work has already been implemented.

- [Current architecture](current-architecture.md) — the split brain/node
  deployment, current model-callable tools, and tool registry boundaries.
- [Hardware consolidation](hardware-consolidation.md) — moving the full
  runtime onto a higher-memory Raspberry Pi 5 or Jetson Orin Nano and retiring
  the internal hardware WebSocket from the normal path.
- [LumaKit delegation](lumakit-delegation.md) — giving Tubby durable background
  agency without building a second general-purpose agent framework.

- [Head tracking review and bench plan](head-tracking-review.md) — the verified
  face-to-servo behavior, current speaker-selection limitation, and the test and
  tuning work planned for tonight or the next session.

## Decision summary

1. The current laptop/Pi split remains in place until replacement hardware is
   selected and passes representative load and endurance tests.
2. Consolidation means one device owns the brain and hardware I/O. It does not
   mean removing every network connection: OpenAI Realtime remains remote, and
   LumaKit remains an authenticated service boundary.
3. Hardware I/O should move behind a transport interface. A future local
   transport becomes the normal path, while the existing WebSocket transport
   remains available for development and recovery.
4. Tubby keeps responsibility for conversation, personality, perception,
   memory, movement, and deciding when to delegate.
5. LumaKit owns durable computer work: planning, coding tools, provider
   selection, persistence, retries, approvals, and completion tracking.
6. Date/time awareness and LumaKit delegation are planned only after the
   consolidated runtime is stable.
