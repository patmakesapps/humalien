# Eye design brief

A brief for modelling Humalien's own eye mechanism, as opposed to the reference
one being printed to prove the servos out. Read [parts.md](parts.md) for what
exists and [hardware.md](hardware.md) for why eyes come first.

## The job

Design a two-eye animatronic mechanism for a printed cyborg head, driven by
MG90S servos over a PCA9685, consuming the normalized gaze targets that
`brain/gaze.py` already produces.

It differs from every reference mechanism online in one way, and that difference
drives the whole design: **the left eyeball contains a VL53L1X time-of-flight
distance sensor**, so Humalien measures distance to whatever it is looking at.
The right eyeball is a plain printed eye. The camera does not move with the eyes
— it lives in the forehead, which keeps face position usable as an absolute
signal instead of an error signal to null out.

## Dimensions come from datasheets, then get proven by a test print

There are no calipers in this build. Every dimension has to come from the
manufacturer, and every dimension has to be treated as unverified until a
printed part has been offered up to the real board.

**Step one — find the mechanical drawing.** For each part below, search for the
manufacturer's datasheet or product wiki and take dimensions from the mechanical
drawing, not from a listing description or a photo. Record the number *and the
URL you got it from* in the table. A dimension without a source is a guess.

| Part | Where to look | What is needed |
| --- | --- | --- |
| MG90S servo | **Cogley's model first** — see below — then the TowerPro datasheet to cross-check | Body envelope, tab hole spacing and diameter, output shaft height above the tabs, spline size, horn thickness |
| CQRobot VL53L1X | CQRobot product wiki; ST's VL53L1X datasheet for the sensor itself and its optical requirements | Board outline, mounting hole positions, sensor window height above the board, cable connector footprint and exit direction |
| Arducam B0385 | docs.arducam.com — Arducam publish per-SKU mechanical drawings | Board outline, mounting hole pattern, M12 lens holder diameter and protrusion, USB connector position |
| HiLetgo PCA9685 | It is a clone of Adafruit's 16-channel driver; Adafruit publish full dimensions and the boards are dimensionally interchangeable | Outline, mounting holes, header height once soldered |

**Step two — design in slop.** Because nothing is verified, every interface to a
real part gets deliberate tolerance:

- Mounting holes **slotted, not round**, so ±0.5 mm of error is adjustable
  rather than fatal
- Board pockets **+0.5 mm on each side** of the drawing dimension
- Any dimension that came from a forum post rather than a manufacturer gets
  **+1 mm**, and gets flagged in the model as low-confidence

Where a dimension can be taken from Cogley's reference model instead, prefer it
over a datasheet — it is a proven fit rather than a nominal figure. See below.

**Step three — print a fit coupon before printing the part.** For each board,
make a small flat test piece carrying only that board's outline and hole
pattern. It prints in minutes and costs pennies. Offer the real board up to it,
correct the model, and only then print the part that matters. This is the
substitute for calipers, and for mounting patterns it is a better one — it tests
the hole positions *and* the printer's dimensional accuracy in a single shot.

The VL53L1X is the constraining part. Its board sets the minimum eyeball
diameter, and the eyeball diameter sets everything else. Get its drawing first
and design outward from it.

## Hard constraints

**Optical path.** The VL53L1X cannot see through printed plastic, and it cannot
see through an arbitrary clear window either — ST's datasheet has strict cover
glass requirements around thickness, air gap and crosstalk. Design for an **open
aperture** in front of the sensor. If a cover is wanted later for looks, treat
it as a change that requires re-testing the sensor, not a cosmetic detail.

**Wires cross a moving joint.** Six wires leave the left eyeball and the eyeball
rotates. No slip ring — at this scale it is more mechanism than the problem
deserves. Limit travel, use fine silicone-jacket wire, and design an explicit
service loop with somewhere for it to live. Route it through the rotation axis
where possible, because wire twisted about its own axis survives far longer than
wire bent back and forth.

**Mass.** Anything inside the eyeball is mass the servo accelerates on a lever
arm. An MG90S is roughly 2.2 kg·cm at 6 V and the eye needs to move fast enough
to read as alive, not just to arrive. Keep the sensor as close to the rotation
centre as the aperture allows.

**Symmetry is not free.** The right eye is lighter than the left. Either add
matching ballast so both eyes tune identically, or accept per-eye calibration in
software. Decide deliberately and write down which.

**Print envelope.** Bambu A1, 256 mm cubed, but that is not the real limit —
part orientation is. Design so no part needs support inside a bearing surface or
a linkage hole, because supports in those places are what make printed
mechanisms bind.

## Motion requirements

| Axis | Travel | Notes |
| --- | --- | --- |
| Pan (both eyes) | ±30° | Linked, so both eyes converge sensibly on the same target |
| Tilt (both eyes) | ±20° | Usually one servo driving both |
| Eyelids | open to closed | Blink, and partial for expression |

`gaze.py` emits normalized `x`/`y` in roughly −1…1, smoothed with a 0.12 s
constant at 4 Hz recognition. The mechanism converts that to angles. Mechanical
travel limits belong in the model *and* in software — the model so nothing can
be commanded into a crash, software so it never tries.

A **hard mechanical stop** at each extreme is worth more than any software
limit, because software limits do not apply during the moment servos get power
and snap to wherever they think they are.

## Deliverables

0. A filled-in dimensions table above, every row carrying the URL it came from.
   This is the first deliverable because everything else is invalid without it.
1. A parametric Blender model where eyeball diameter, servo dimensions and
   travel limits are variables, not baked-in numbers. The VL53L1X board is going
   to change size when it gets replaced with a bare module, and unverified
   dimensions are going to be wrong at least once.
2. STLs oriented for printing, one file per unique part, with quantities.
3. Assembly notes: order of operations, and which fasteners go where.
4. A fastener BOM. **None of these are currently owned** — M2 screws, possibly
   heat-set inserts. Cogley's mechanism will reveal what is actually needed once
   it is assembled, which is another reason to build it first.
5. A wiring plan for the left eyeball specifically — wire gauge, service loop
   path, strain relief, and where the six wires terminate.

## The reference mechanism is a measuring tool

[Will Cogley's Animatronic Eye Mechanism](https://makerworld.com/en/models/1184807-animatronic-eye-mechanism-e3-2)
(also on [Printables](https://www.printables.com/model/1220172-animatronic-eye-mechanism-e31))
is being printed on the Bambu A1 and assembled first. It is free, and MakerWorld
opens straight into Bambu Studio.

**Import it into Blender as reference geometry.** Export the plate from Bambu
Studio as STL or 3MF into `reference/eye-mechanism/`, then bring it into the
scene. This matters more than it sounds: Cogley has already fitted an MG90S,
already chosen linkage geometry that does not bind, already sized an eyeball.
Measuring his servo pocket in Blender is a *better* source than a TowerPro
datasheet, because it is a dimension that has been printed and proven to work
rather than a nominal number with unstated tolerance.

Use it to pull:

- The servo pocket and its clearances, which encode the real fit rather than the
  nominal envelope
- Eyeball diameter and the socket that retains it
- Linkage lengths and pivot spacing that are known not to bind through travel
- Wall thicknesses that print cleanly on this class of printer

**Licensing.** Check the licence on the model page before deriving geometry from
it. Cogley's work is typically shared non-commercially, which is fine for this
build but constrains what could ever be published. Take *dimensions and
approach* freely; copying his geometry wholesale into a redistributed model is a
different thing. Record the licence in this file once confirmed.

The bespoke design departs from it in the ways [parts.md](parts.md) sets out —
the VL53L1X in the left pupil above all — so it is a starting point and a
measuring stick, not a base model to edit.

## What the reference build answers

Assembling it also answers questions this design would otherwise be built on top
of untested:

- Does 4 Hz recognition with a 0.12 s smoothing constant read as alive?
- What travel actually looks right, versus what looks mechanical?
- How much do MG90S servos jitter at hold, and does that need a deadband?
- What does the linkage geometry need to be to avoid binding at the extremes?

Do not start cutting geometry that depends on those answers before they exist.
Structural work — mounting plates, the camera boss in the forehead, the PCA9685
mount, cable routing — is independent of them and can start immediately.

## Things that are already decided

- Camera in the forehead, not in an eye.
- VL53L1X in the left pupil, right eye plain.
- Servos driven from a PCA9685 at `0x40`, on their own 5 V rail, common ground.
- The node executes, the brain decides. Nothing in this mechanism implies logic
  on the Pi beyond converting an angle to a PWM value.
