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
binding to 2000 µs (+45°, left) and 1000 µs (−45°, right). These are
bench-proven electrical limits only; runtime pan control is not implemented.

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

## Speech and arm-motion integration handoff

The synchronization path already exists. `brain/playback.py` computes the RMS
level of each audio chunk when that chunk is actually released to the hardware
node. `brain/voice_core.py` sends that level to `Gestures.feed`, and
`brain/gestures.py` turns the smoothed envelope into arm poses. Add head motion
to that same `Gestures` instance; do not drive it from Realtime API audio-delta
events, which run ahead of audible speech.

The wire format can carry all four axes in one frame:

```json
{"type":"pose","arm_l":12.0,"arm_r":8.0,"pan":4.0,"nod":2.0}
```

Implementation constraints for the pairing work:

1. Extend the node-side controller in `humalien_node/arms.py` with per-axis
   channel, center, sign, limits, trim, and slew configuration. The current
   arm-wide constants are not sufficient for the narrower head envelopes.
2. Enforce the head limits on the Pi, not only in `brain/gestures.py`. Use
   `pan` ±14.4 degrees and `nod` -3.6 to +40 degrees as the observed local
   safety limits, backed by the raw pulse ranges above. Keep ordinary speech
   nods inside the much smaller -3.6 to +3.6 degree envelope initially.
3. Keep the head subtler than the arms. Reuse the playback envelope, but use a
   slower/low-amplitude phase for pan and nod so the head follows phrases rather
   than individual syllables.
4. Return both head targets to zero after speech. On disconnect or explicit
   `limp`, release all four channels; holding at zero should be an intentional
   pose, not the failure mode.
5. Update `node/tests/test_arms.py`, `node/tests/test_control.py`, and
   `brain/tests/test_gestures.py` before enabling head axes in normal runtime.

The active geometry in `cad/desk_bot.py` defines `ARM_RANGE = (-20, 75)` and
uses positive pose angles for forward movement on both arms. The node must
apply the opposite electrical signs shown above. Do not substitute the raw
bench endpoints for the CAD range without completing mechanical calibration.

`humalien_node.arms` holds this map for the two arm channels, and is the
only place the sign inversion above is applied - everything upstream of it
speaks in CAD degrees where positive is forward on both arms. Walk each arm
with `python -m humalien_node.arm_bench` before letting the brain drive them.

Channels 1 and 2 are deliberately absent from that module. Channel 1 has a
bench-proven center, sign, and electrical range. Channel 2 now has a verified
direction, an upward maximum, and only a small approved downward envelope;
full downward travel remains uncalibrated. Neither has a runtime controller
yet. An axis that cannot be addressed cannot be driven into a hard stop by a
bug upstream; add each only with the local clamps and tests described above.

`humalien_node.eyes_bench` targets the archived three-servo eye mechanism; it
does not contain the desk bot's four-channel map.
