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

## Measure first, model second

**Every dimension below is provisional.** Boards from different vendors differ,
and listing photos lie. Before modelling anything that touches a real part, put
calipers on it and record the measurement in this file. If a caliper reading
disagrees with a number here, the caliper wins — correct the doc.

| Part | Provisional | What actually matters |
| --- | --- | --- |
| MG90S servo | ~22.8 × 12.2 × 22.5 mm body, ~32.5 mm across mounting tabs | Tab hole spacing and diameter, output shaft height above the tabs, horn thickness |
| CQRobot VL53L1X | small breakout, six-wire cable | Board outline, mounting hole positions, how far the sensor window sits proud of the board, cable exit direction |
| Arducam B0385 | ~38 × 38 mm | Board outline, mounting hole pattern, lens barrel diameter and how far it protrudes, USB connector position and cable strain |
| PCA9685 | ~62.5 × 25.4 mm | Outline and mounting holes, header height once soldered |

The VL53L1X is the constraining part. Its board sets the minimum eyeball
diameter, and the eyeball diameter sets everything else. Measure it first and
design outward from it.

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

1. A parametric Blender model where eyeball diameter, servo dimensions and
   travel limits are variables, not baked-in numbers. The VL53L1X board is going
   to change size when it gets replaced with a bare module.
2. STLs oriented for printing, one file per unique part, with quantities.
3. Assembly notes: order of operations, and which fasteners go where.
4. A fastener BOM. **None of these are currently owned** — M2 screws, possibly
   heat-set inserts. Cogley's mechanism will reveal what is actually needed once
   it is assembled, which is another reason to build it first.
5. A wiring plan for the left eyeball specifically — wire gauge, service loop
   path, strain relief, and where the six wires terminate.

## What the reference build is for

Cogley's mechanism is being printed and assembled first, on purpose. It answers
questions this design would otherwise be built on top of untested:

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
