# Desk bot servo map

Bench-identified on 2026-08-31. The PCA9685 is at `0x40` and runs at 50 Hz.
Electrical neutral is 1500 µs.

| PCA9685 channel | Physical movement | Desk-bot axis | Direction from neutral |
| --- | --- | --- | --- |
| 0 | right arm | `arm_r` | forward raises the pulse |
| 1 | neck rotation | `pan` | left raises the pulse; right lowers it |
| 2 | head nod | `nod` | up lowers the pulse; down raises it |
| 3 | left arm | `arm_l` | forward lowers the pulse |

The raw arm tests reached 2500 µs on the right and 556 µs on the left
without observed binding. Those are bench observations, not software travel
limits. The horns were re-indexed afterward, so commanded servo angle and
physical arm pose still need calibration.

The neck was electrically centered at 1500 µs, then tested without observed
binding to 2000 µs (+45°, left) and 1000 µs (−45°, right). Those are
bench-proven electrical limits only. Runtime `pan` is deliberately held to
the much narrower 1340–1660 µs envelope observed on the assembled robot —
see below.

## Head motion verified on the assembled robot

Verified by observation on 2026-09-03. Both tests used the nominal MG90S
conversion of 1000 µs per 90 degrees. The pulse widths are the primary record;
the degree values are estimates until the mechanisms are measured with a
protractor.

### Neck rotation (`pan`, channel 1)

- Electrical zero: 1500 µs.
- Narrow motion observed working: 1340–1660 µs, nominally ±14.4 degrees.
- Positive/raised pulse turns the head left; reduced pulse turns it right.
- Proven slow rate: 2 µs every 50 ms = 40 µs/s, nominally 3.6 degrees/s.
- Observed test path: 1500 -> 1660, hold 0.4 s, 1660 -> 1340,
  hold 0.4 s, 1340 -> 1500, hold 0.5 s, then release.
- The earlier 1000–2000 µs bench sweep did not bind, but speech gestures should
  start with the much narrower 1340–1660 µs envelope above.

### Head nod (`nod`, channel 2)

- Electrical zero: 1500 µs.
- Motion observed and approved: 1460–1540 µs, nominally ±3.6 degrees.
- Physical up is a lower pulse. Keep the CAD convention that positive `nod`
  means up, so this axis needs an electrical sign of -1.
- Proven slow rate: 2 µs every 50 ms = 40 µs/s, nominally 3.6 degrees/s.
- Exact approved path: 1500 -> 1540, hold 0.4 s, 1540 -> 1460,
  hold 0.4 s, 1460 -> 1500, hold 0.5 s.
- Upward positions were then walked under direct observation through 1420 µs
  and 1278 µs to 1056 µs. The assembled mechanism reached 1056 µs cleanly,
  nominally 40 degrees up. The observer explicitly set this as the maximum:
  **do not command below 1056 µs / above +40 degrees.**
- The final 1500 µs output may be left active when the head must hold zero;
  release the channel when holding torque is not needed.
- Only the small downward endpoint at 1540 µs (nominally -3.6 degrees) is
  approved. A later standalone attempt to repeat full nods toward 1944 µs was
  stopped after erratic motion. Do not reuse that script or treat 1944 µs as
  a calibrated downward endpoint.
- `cad/desk_bot.py` still says `NOD_RANGE = (-22, 22)`. That symmetric model is
  stale relative to the assembled mechanism: upward travel has been observed
  to +40 degrees, while equivalent downward travel has **not** been approved.
  Do not turn the CAD value into a symmetric runtime limit.

## Speech and body-motion integration — done 2026-09-03

All four axes are now driven. The handoff that used to live here is
implemented; what follows is what was built, so the next person does not have
to read the code to find out what is enforced where.

`brain/playback.py` computes the RMS level of each audio chunk at the moment
that chunk is released to the hardware node. `brain/voice_core.py` fans that
one envelope out to `brain/gestures.py`, which shapes all four axes, and to
`brain/mood.py`, which drives the eyes. It is deliberately not taken from
Realtime API audio-delta events, which run ahead of audible speech.

### The wire

One socket carries audio as bytes and everything else as text, so motion
cannot drift against the speech it belongs to.

```json
{"type":"pose","arm_l":12.0,"arm_r":8.0,"pan":4.0,"nod":2.0}
{"type":"eyes","mood":"listening","level":0.31}
{"type":"limp"}
```

Any subset of axes may appear in a `pose`. An unknown axis or mood is logged
and ignored rather than taking the connection down.

### What the node enforces

`humalien_node/arms.py` carries a per-axis table — channel, sign, limits,
rest, speed, acceleration, trim and its own pulse clamp. The head limits are
the pulses observed above, not the CAD ranges:

| axis | limits | pulses | top speed | acceleration |
| --- | --- | --- | --- | --- |
| `arm_l` / `arm_r` | -20..+75 deg | 600..2400 us | 100 deg/s | 600 deg/s² |
| `pan` | ±14.4 deg | 1340..1660 us | 144 deg/s | 398 deg/s² |
| `nod` | -3.6..+40 deg | 1056..1540 us | 108 deg/s | 237 deg/s² |

The pulse clamp is per axis on purpose: a bad trim or a recalibrated
`US_PER_DEG` cannot walk the neck out into an arm's pulse range.

### Acceleration, and why it is not just a speed limit

The NeoPixel eyes are wired through the neck — power and data run from the Pi
up past the nod joint into the head. A pure speed limit still steps velocity
from zero to the cap in one frame, so the axis leaves and arrives with a snap
however low the cap is. Every axis is therefore acceleration-limited as well,
with a discrete braking curve that arrives at rest instead of being stopped
dead on the last frame.

At these figures pan reaches its cap in 0.36 s and crosses its whole 28.8
degree range in about 0.5 s; nod reaches its cap in 0.46 s and crosses its
43.6 degrees in about 0.9 s. `head_bench`'s `profile` command prints this
before anything moves.

The two acceleration figures are deliberately not round. A flat 80% increase
on the accelerations that matched the approved speeds - 450 and 324 - FAILED
the discrete braking tests in `node/tests/test_arms.py`: at those figures an
axis can no longer bleed its speed off in whole 20 ms frames without a jerk
on the frame it lands. 398 and 237 are the nearby values that keep the
invariant. Do not round them up, and do not relax the tests so that rounder
ones pass - those tests are the reason these numbers can be trusted.

The head is also **parked at neutral before it is released** — on disconnect,
on `limp`, and on the way out of both benches. An axis released off-centre
has to be jumped back the next time it engages, because a limp servo has no
known position to slew from, and that jump is the one move the eye wiring
cannot afford.

### The rates, and what "approved" covers

Walked on the assembled robot and accepted on 2026-09-03.

The first runtime rates here were 18 and 10 deg/s, chosen to be obviously
safe rather than to be right. They were walked up on the bench in stages -
80/60 deg/s, then these - and accepted at 144 and 108. The observed test at
the final profile was:

- nod 0 -> -2 -> +5 -> 0 degrees
- pan 0 -> -5 -> +5 -> 0 degrees
- head parked at neutral, then released

**What that does not cover: full-range travel, and durability over many
cycles.** These rates are approved for short conversational motion, which is
all `brain/gestures.py` ever asks for. Nothing has yet run the head to its
stops repeatedly at this speed.

If it ever looks harsh, lower the ACCELERATION first and the speed second, in
`arms.py`. Walk any change with `python -m humalien_node.head_bench` -
`profile`, then `nod`, `pan`, `sweep`, `talk` - before letting the brain
drive it unattended.

### What the brain shapes

`brain/gestures.py` keeps ordinary speech motion far inside those limits: pan
±4.5 degrees and nod ±2.4 on the speech envelope, on a beat of 0.17 Hz
against the arms' 0.45 Hz, so the head follows phrases rather than syllables.
It runs the head on its own slower envelope (`HEAD_ATTACK`) for the same
reason — the arms' 50 ms attack, applied to a neck, asks for twenty degrees a
second the instant anybody starts talking.

Face tracking adds to that: up to 65% of the way toward whoever is being
talked to, and up to 6 degrees of looking **up** to meet a face above the
camera. That upward figure is the one number here that exceeds this
document's earlier "keep speech nods inside ±3.6 initially" — it is in the
only direction that was ever walked (up, to +40, under observation), it is a
seventh of that travel, and `NOD_TRACK_UP = 0` in `gestures.py` switches it
off without touching anything else.

Nothing ever stops moving completely: with no face and no speech the head
drifts on two incommensurate slow sines, because a head parked dead centre
reads as switched off.

### Who to look at, when there is more than one

`brain/attention.py`. Picking the largest face every frame — which is what
`gaze.select_primary_face` does — flips several times a second between two
people sitting at the same desk, because their measured areas cross over on
detector noise. A neck driven from that hunts between them for as long as
they both stay in the room.

So the target is held by position, not area; a challenger must be 1.35× the
size for 1.2 s, and no switch may happen within 2.5 s of the last one.
`brain/tests/test_attention.py` reproduces the flicker with the naive rule
and asserts zero hunting with the real one.

Every 9-22 seconds, with somebody else present, the head deliberately glances
at them for 1.6 s and comes back. That is a decision on a slow timer, not
frame-by-frame flicker, and it is the difference between looking around a
room and twitching.

### Calibration still owed

`TRIM` is still all zeroes and `US_PER_DEG` is still the nominal MG90S
1000 us per 90 degrees, unmeasured on this mechanism. The arm horns were
re-indexed after the channel map was found, so commanded angle and physical
pose do not yet agree. Both benches have `trim`, `pulse`, `calc` and `save`
for exactly this; `save` prints the line to paste back.

Walk each arm with `python -m humalien_node.arm_bench` and the head with
`python -m humalien_node.head_bench` before letting the brain drive them. The
two tools no longer touch each other's channels.
