# Eye rig — what the first assembly found

**Status: dead. Do not print this set.** Archived 22 Aug 2026, after the whole
rig was printed (about 2.5 hours) and assembled far enough to prove it cannot
be assembled.

Everything below is measured off the geometry in `cad/eye_rig.py` and
`cad/eye_lids.py` at the commit this folder was archived at, not remembered.

---

## Three things that are impossible, not tight

These are not tolerance problems. No amount of reaming or filing fixes them.

### 1. `RIG_pins` cannot pass through the fork bore

The fork bore is Ø6.2. The pin has to end up with its lever below the fork and
its collar and cross above it, so on assembly something has to travel through
that bore.

| coming from | what has to fit through Ø6.2 | actual |
|---|---|---|
| below | the collar under the ball | **Ø10.0** |
| above | the lever plate at the bottom | **Ø22.6** swept |

Blocked in both directions. The part was designed as one piece with the fork
permanently in the middle of it — which can only be built if the fork is
open, or the pin is two pieces.

**The fix, when this comes back:** split it. Pole, collar and cross drop in
from above and stop on the fork's top face. A separate lever pushes onto the
Ø6 stub underneath and keys to it — a flat, a cross, or a pin — so it can
still carry the pan drive.

### 2. `RIG_frame` cannot go onto `RIG_base`

The tilt shaft is one continuous Ø5 rod from x −18 to +18. The pillar it turns
in is a **closed** Ø5.2 hole bored through 10 mm of plastic.

- Axial slide needed to thread the shaft out of that hole: **23 mm**
- Axial slide available before a tilt web hits the pillar: **0.50 mm**

**The fix:** the bearing has to open. Either split the pillar into a saddle
and a bolt-on cap, or — better — drop the central pillar entirely and put two
split blocks with caps out at |x| 18, where the shaft already ends. The second
also fixes item 5.

### 3. `LID_tie` cannot turn the second lid

The tie is a **Ø5.0 round rod** in a **Ø5.2 round hole**. A round shaft in a
round hole transmits no torque at all. Confirmed by hand on the printed parts:
blink one lid and the tie spins in its bore while the other lid stays put.

The design note claimed this was fine because "both cranks point the same way,
so their pins are coaxial and the tie is simply a shaft". Coaxial was the
wrong property to care about. Keyed was the one that mattered.

**The fix:** hex or square the tie and broach both crank bores to match.

---

## 4. Every clearance in the rig is too small to print

The design uses 0.2 mm diametral — 0.1 mm a side — on essentially every
running joint. That measures fine in Blender and binds solid in PLA. The
whole rig came off the bed stiff.

| joint | slack per side |
|---|---|
| lid hub on its pivot pin | 0.09 mm |
| link on the lever pins | 0.09 mm |
| pole in the fork bore | 0.10 mm |
| tilt shaft in the pillar | 0.10 mm |
| horn on the rod pin | 0.14 mm |
| **snap eye on its pin** | **0.15 mm** |

The snap eye is the only joint that felt right in the hand, and it is the
loosest one on the rig. That is the calibration: **0.15 a side is the floor
on this printer, and load-bearing joints want more.**

There is a second class of number, parts passing each other rather than
turning in each other. The lid drive pin clears the fork arm by 0.50 mm, and
that vanished too once the plastic was real.

## 5. The frame is back-heavy on a bearing in the middle

- 69 g hangs on the tilt axis, centre of mass **11.2 mm behind** it
- ≈ **770 g·mm** of static torque the tilt servo holds continuously
- carried on **one 10 mm-wide pillar**, in the middle of a 72 mm frame,
  with nothing supporting the ends

Both the pan servo and the lid servo ride the frame, behind the axis. Fixing
the bearing per item 2 with two outboard blocks fixes this at the same time.

## 6. `LID_tie` warped, and the brim rule is why

106 mm long, 138 mm² of bed contact — a strip **1.3 mm wide** holding down
four inches of plastic. `test_prints()` only looks at total contact area and
anything over 100 mm² is told it needs no brim. Wrong rule for long thin
parts; it should be looking at the shape of the contact, not its area.

---

## Why the checks passed all of this

`eye_rig.check()` and `eye_lids.check()` were green on every one of these.
They asked three questions:

1. is each part one closed solid?
2. do the servos fit their cradles?
3. does anything **overlap** anywhere in the travel?

None of those is the question "can a person build this". And overlap gives the
same answer — zero — for 9 mm of daylight and for 0.09 mm.

Two checks were added at the end of this round, and both fire loudly on the
rig as printed. They are in the archived `cad/eye_rig.py`:

- **`clearances()`** — smallest real gap between every pair of parts across
  the pose sweep, with a floor of 0.15 mm for joints and 0.40 mm for parts
  merely passing each other. Sixteen pairs fail.
- **`assembly()`** — tries to pull each part straight out along all six axes.
  A part that cannot come off along any of them was never going on along one
  either. **Seven of twelve parts report TRAPPED**, including `RIG_base`,
  `RIG_frame` and both `RIG_pins`.

`assembly()` over-reports for snap-on parts: the rods and the link clip
sideways over their pins rather than sliding out, so they read TRAPPED without
being broken. Read it as "look at this", not as proof. The frame, base and
pins are the real ones.

**Take this forward:** whatever the next eye rig looks like, run those two
before printing. The overlap test alone will pass a rig you cannot build.

---

## What was actually good

Worth keeping rather than starting from zero:

- **The snap eye.** Ø3.3 bore, 2.75 mouth over a Ø3.0 pin. Went on with a
  deliberate push, held, and swivelled freely. The one joint that worked.
- **`HORN_BORE = 4.95`**, measured on a real spline in grey PLA via
  `bore_ladder()` — print a range of bores at once with bumps on the rim
  counting the size, keep the winner. Cheaper than one guess per print, and
  it is printer- and filament-specific, so re-run it on a change of either.
- **The kinematics.** Tilt is a true 1:1 parallelogram; pan and blink solve
  their linkages rather than interpolating. None of that is what failed.
- **Printing parts in their final orientation** and shipping the bed layout
  with the STLs.
