# Eye rig — first print

Built from `cad/eye_rig.py` and `cad/eye_lids.py`. STLs in `eye rig/`, one
per part, **already laid on the face they should print on** — don't rotate
them in the slicer.

Three MG90S servos: pan, tilt, blink. Two eyeballs, upper lids only.

---

## The fits

Four numbers in this build are fits. **Two of them have now been measured on
a real printer** — 22 Aug 2026, grey PLA — and two still cannot be tested
until the rig is together.

Both measured numbers are printer- and filament-specific. On a different
machine, or in a different colour, check them again before committing to a
plate. Twenty minutes of printing against hours for the big parts.

### 1. Horn onto the spline — `HORN_BORE = 4.95`, in `cad/eye_rig.py`

**Measured, not guessed.** 4.7 had to be forced on and 5.2 dropped on and
spun; a ladder of 4.75 / 4.85 / 4.95 / 5.05 pucks went onto a real spline and
4.95 was the one that fit.

The horn presses on so the 21 teeth cut their own splines in the plastic,
held by the servo's own screw. That makes it **one-way**: too small and you
split the hub getting it on, too large and it strips under load. The useful
window turned out to be about half a millimetre wide, which is why guessing
in 0.1 steps cost two prints before the ladder settled it in one.

To re-measure on another printer or another filament:

    eye_rig.bore_ladder(folder="C:/some/where")

Four hub pucks, no arm and no pin, about ten minutes on a 60 mm square. Bumps
on the rim count the size — one bump is the smallest — so they can't be mixed
up coming off the bed. Press each onto a spline, keep the one that starts
square and needs the screw to seat it, set `HORN_BORE` to it, and rebuild.

### 2. Snap eye over its pin — `ROD_MOUTH = 2.75`, in `cad/eye_rig.py`

Every pushrod ends in a C that clips over a Ø3.0 printed pin. Bore is Ø3.3,
mouth is 2.75 — **0.25 mm of interference**, so it snaps on and stays on.

The rod has no pin to test against on its own; clip it onto any Ø3 rod, a
drill shank, or the pin on `RIG_horn_tilt` once that's printed.

- It should need a deliberate push and then hold, and then swivel freely on
  the pin once it is seated. 2.75 was confirmed good on the first print.
- Cracks going on → mouth too tight, raise `ROD_MOUTH`.
- Slides on with no click, or falls off → lower it.

Loose to *swivel* is correct. Loose to *get on* is the failure.

Both mouths on a rod face **opposite ways** on purpose, so no single sideways
shove releases both ends.

### 3 and 4 — the two you can't test cheaply

The eye's pole (Ø6.0 in a Ø6.2 fork bore) and the lid pivot (Ø5.0 pin in a
Ø5.2 hub bore) both live in large parts. Print them as-is and expect to ream:

- The **pan bores print on their side** in the frame, so they will be out of
  round on top. Reaming them is worth doing anyway — it halves the eye's
  0.54 mm of pupil loll.

---

## Then the rest

Six parts want a **brim**; the others don't need one.

| part | on the bed | brim |
|---|---|---|
| `RIG_base` | 3660 mm² | |
| `RIG_frame` | 1594 | |
| `RIG_shelf` | 302 | |
| `LID_up_L` | 276 | |
| `RIG_rod_pan` | 251 | |
| `RIG_rod_tilt` | 246 | |
| `RIG_link` | 211 | |
| `LID_mount` | 206 | |
| `LID_rod` | 190 | |
| `LID_up_R` | 149 | |
| `LID_tie` | 138 | |
| `LID_horn` | 121 | |
| `RIG_pins_L` | 94 | yes |
| `RIG_horn_tilt` | 93 | yes |
| `RIG_horn_pan` | 72 | yes |
| `RIG_pins_R` | 54 | yes |
| `eye_L`, `eye_R` | 47 each | yes |

All 18 fit one 220 × 220 bed in 194 mm of depth if you want them together.

### Supports

Only one place needs them, and it matters:

**`RIG_frame` — the tilt shaft.** Laid on its back, the Ø5 shaft bridges
**16 mm unsupported at 19.3 mm above the bed**, and that span is exactly what
rides in the pillar bore. A bridged cylinder droops at precisely the wrong
place. Support it, and expect to clean it up and check it turns freely.

If it comes out bad, the fix is making the shaft a separate printed rod
through Ø5.2 bores, printed upright so it's round. That's a real change to
the frame, not a tweak — worth knowing before you decide it's acceptable.

---

## Hardware

- **3 × MG90S** with their own horns' screws (the horns themselves are
  printed — `RIG_horn_pan`, `RIG_horn_tilt`, `LID_horn`).
- **M2 self-tappers** into Ø1.7 pilots, for every servo and bracket:
  - 2 down through the pan servo's ears into `RIG_shelf`
  - 2 sideways through the tilt servo's ears into `RIG_base`'s posts
  - 2 sideways through the lid servo's ears into `LID_mount`
  - 2 up through `RIG_shelf`'s posts into the frame's tilt webs
  - 1 down through `LID_mount`'s foot into the lid bracket rail
- Nothing else. No music wire, no ball links, no bearings — every pivot is a
  printed pin in a printed bore or a snap-on eye.

---

## Assembly order

The eyes have to go in before anything blocks the fork, and the lid brackets
have to be clear when the eyes drop in.

1. **Eyes into the forks.** Slide each ball in from the front — there is no
   arm over the top any more, so it goes straight in.
2. **Poles up from underneath.** Push `RIG_pins_L/R` up through the lower
   fork bore, through the ball, until the collar seats on the ball's flat.
   The cross takes the drive; the collar sets the height.
3. **Link** across both front lever pins.
4. **Pan servo** into `RIG_shelf` — it slides in from the *back*, ears land
   on the rails, two screws down. Then `RIG_shelf` up onto the frame.
5. **Tilt servo** into the base — slides in from the *side* onto its two
   posts, two screws sideways.
6. **Horns and rods.** Press each horn on, then clip the rods.
7. **Lids** onto the bracket pins, then `LID_tie` through both cranks. It
   runs 3 mm past each crank face — retain it there.
8. **Lid servo** into `LID_mount`, then the mount onto the lid bracket rail.

---

## Numbers worth knowing

**Tilt is exact.** The frame crank and the horn crank are both 8 mm and
parallel, so the servo angle *is* the tilt angle, 1:1 over ±20°.

**Pan and blink are not.** Both are slider-cranks. Call
`eye_rig.servo_angles(pan, tilt)` and `eye_lids.servo_angle(t)` to get the
commands — they solve the linkage rather than interpolating, so the
non-linearity is a lookup in firmware, not a fudge that drifts.

Blink runs about **+36° shut to −31° open**. Regenerate the pan table from
`servo_angles()` before you write firmware; the pan lever changed length
late and any number written down before that is stale.

**Slop, as designed:**

| where | how much |
|---|---|
| pupil, from the pole in its 8 mm bore | ~0.54 mm (0.27 if reamed to 0.05 clearance) |
| lid edge, from the 6.2 mm pivot | ~0.55 mm |

**Two clearances I'd watch on assembly:**

- `RIG_shelf`'s post sits **0.45 mm** off the pan servo's case.
- `LID_rod` passes **2.50 mm** from the frame's crossbar at full blink.

---

## Not in this build

**Lower lids.** `_lower()` is still in `cad/eye_lids.py` and one line from
coming back. It's parked because a 1.6 mm curved shell has no flat face in
any orientation — 31.6 mm² of bed against 84 mm² of overhang — and every
shape that gave it one stopped looking like a lid. Options when we revisit:
print it with supports and accept the cleanup, or make it part of the frame
so it needs no fasteners at all.

---

## What the checks do and don't cover

`eye_rig.check()` and `eye_lids.check()` sweep 21 pan/tilt poses and 25
blink/eye combinations, confirm every part is one closed solid with positive
volume, and measure each servo against its cradle.

They do **not** catch a bore that is the wrong size for its pin — an
oversized hole *reduces* interference, so both the clash sweep and the
watertight test pass happily. One shipped that way and was caught by eye.
Check the fits above by hand; the harness won't do it for you.
