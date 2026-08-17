# Eye v2 — print and assembly sheet

Built from `cad/eye.py`. STLs in `exports/eye/`, one per part, already in
their gated print orientation — do not rotate them in the slicer.

**If you sliced before the pan fix (2026-08-17, parallelogram + dogleg):
re-slice `eye_gimbal_x1.stl` and `eye_link_pan_x1.stl`. The other eleven
are unchanged.**

## Slicer settings the gate requires

| part | setting |
|---|---|
| eye_lid_r, eye_lid_l | supports ON + brim |
| eye_gimbal | supports ON |
| everything else | no support, no brim |

## Hardware

- 3× MG90S + the horns and screws from their bags. Pan and blink each use
  a **single-arm horn**; drill a 1.5 mm hole at exactly **11 mm** from
  center (pan) and **14 mm** (blink) if the stock holes don't land there —
  those radii are the gear ratios.
- ~6× **M2×8 machine screws + nylock nuts** — the printed-to-printed
  pivots (strap↔tab, strap↔crank, bar↔levers). Tighten to just-free.
- Servo-bag **self-tappers** — horn-to-strap pivots (thread into the horn,
  strap swivels on the shank) and all servo mounting into Ø1.7 pilots.
- 4× **M2 self-tappers** — spine pads into the lid boss faces.
- ~~1× long tilt clamp screw~~ — **VOID (2026-08-17).** The access bore
  dead-ends inside the lid hinge stub; there is no through-hole and never
  was. The tilt joint needs no screw at all — see step 7. No store trip.

## First plate: small parts, then commit

Print the small stuff first and fit-check before the long prints:
pins, straps, spine, tilt pin, pan bar.

- M2 slides free through any Ø2.2 hole; self-tapper bites firmly in Ø1.7.
- Pin key flat seats in the ball bore without force.
- Ø5 tilt pin spins freely in the base upright's left bore.

## Assembly order

1. **Pins into balls** — key flat sets the phase; no glue.
2. **Balls into the gimbal journals** — pin rides top and bottom bores.
3. **Pan bar to both levers** — M2 + nylock, just-free.
4. **Lids onto their hinge stubs** — slide from inboard, before the spine.
5. **Spine to the lids** — pads against the inboard boss faces, 2× M2
   self-tappers per side over the bar. This locks both lids in phase.
6. **Tilt servo into the right base upright** — body through the pocket,
   tabs screwed to the outer face. **Center it electrically (1500 µs)
   now** — after step 7 the pocket fixes the phase forever.
7. **Gimbal onto the tilt drive** — with the servo centred, press the
   horn onto the spline pointing **straight up**, then slide the gimbal
   right so the horn drops into the boss pocket: arm in the slot, hub in
   the recess. **No clamp screw** — the Ø3 dimple in the recess floor is
   a dead end, not a hole. Left side: printed tilt pin through the
   upright into the boss, head outboard; dab of glue on the head if it
   walks. Once the pin is in, the gimbal has ~1 mm of side play against
   a 2.1 mm-deep slot, so the horn is captive — that geometry, not a
   screw, is what holds the joint together.
8. **Pan servo** up through the shelf window (body up, horn down), tabs
   screwed up into the pilots. Center at 1500 µs, then press the horn on
   pointing **straight back, parallel to the eye levers** — this is the
   parallelogram; one spline tooth off and the travel is offset. Dogleg
   strap onto horn and tab.
9. **Blink servo** into the bracket, shaft toward the right eye. Center,
   then horn pointing **forward at the lids, ~7° above level**. Strap up
   to the spine crank.
10. **First power**: software limits BEFORE moving — tilt ±16°, pan ±20°,
    blink −55°/+10° — and run slow. The mechanism was verified clash-free
    exactly inside those numbers, not outside them.

## Servo channels (PCA9685)

ch0 tilt · ch1 pan · ch2 blink — codified in `node/humalien_node/eyes_bench.py`
along with the eye-degree limits, which are the same numbers the CAD's
clearance sweeps verified.

**Centering and testing**: on the Pi, `python -m humalien_node.eyes_bench`.
`c` centres all three (that's steps 6 and 8's "center electrically first"),
`sweep tilt` etc. runs a slow limit-to-limit pass, `invert`/`trim` sort out
direction and neutral at the bench, `off` goes limp. Everything is
slew-limited to 30°/s and starts limp — a fresh linkage never gets a
full-speed step.
