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

### What was actually found — 13 Aug 2026

The confidence column is the column that matters. It is not commentary: it is
encoded in `cad/eye_mech.py` as `CONF_PAD`, and it decides how much slop the
model puts around the number. `exact` and `drawing` get none; `listing` gets
+1 mm per side and is flagged.

**PCA9685 — `exact`.** Adafruit publish the Eagle board file, so this did not
need reading off a drawing at all. Parsed straight out of
[`Adafruit PCA9685 rev C.brd`](https://github.com/adafruit/Adafruit-16-Channel-PWM-Servo-Driver-PCB):

| Dimension | Value | Source |
| --- | --- | --- |
| Board outline | 62.230 × 25.400 mm, 3.175 mm corner radius | Eagle `.brd`, layer 20 |
| Mounting holes | 4 × Ø2.500 mm plated | Eagle `.brd`, `MOUNTINGHOLE_2.5_PLATED` |
| Hole pattern | 55.880 × 19.050 mm, 3.175 mm in from every edge | Eagle `.brd`, element coordinates |
| Board thickness | 1.6 mm nominal | standard 2-layer stackup, assumed |

Cross-checks: the [product page](https://www.adafruit.com/product/815) says
2.5″ × 1″ × 0.1″, and the [fab print](https://learn.adafruit.com/16-channel-pwm-servo-driver/downloads)
annotates "Holes are 2.5mm diameter". Both agree with the board file. The fab
print is dimensioned in inches and is easy to misread — the board file is the
better source and cost less effort.

**Arducam B0385 — `drawing`.** From the
[B0385 datasheet](https://www.uctronics.com/download/Amazon/B0385_OV9782_Global_Shutter_UVC_Camera_Datasheet.pdf),
"Overall Dimension Diagram" on page 4 and the lens diagram beside it:

| Dimension | Value | Source |
| --- | --- | --- |
| Board outline | 38.00 × 38.00 mm | dimension diagram |
| Outer hole pattern | 34.00 × 34.00 mm, R1.30 → Ø2.60 | dimension diagram |
| Inner hole pattern | 28.00 × 28.00 mm, R1.40 → Ø2.80 | dimension diagram |
| Sensor centre | 19.00 mm from two adjacent edges, i.e. board centre | dimension diagram |
| Lens holder height | 7 mm | lens diagram, "Lens Holder Height" |
| Lens barrel | Ø14 ±0.05, 13.2 mm long, M12×0.5 thread over 8.9 mm | lens mechanical drawing, model M27280M07S |
| Connector | S4B-ZR, 7.56 × 3.81 mm, 8.24 mm from left edge, 3.47 mm from bottom | dimension diagram |

Two things worth knowing. The connector is **not** a USB socket — it is a 4-pin
JST S4B-ZR carrying VCC/DM/DP/GND, and the USB plug is on the far end of the
supplied cable. And the M12 holder footprint is drawn but **not dimensioned**;
18 × 18 mm was scaled off the drawing, so the aperture is cut at 19 × 19 and the
coupon carries it.

**MG90S — `drawing` for the body, `listing` for the tab pitch.** TowerPro's own
[product page](https://towerpro.com.tw/product/mg90s-3/) says 22.8 × 12.2 ×
28.5 mm; the [distributor datasheet](https://www.electronicoscaldas.com/datasheet/MG90S_Tower-Pro.pdf)
says 22.5 × 12 × 35.5 mm and carries an actual drawing. They disagree, which is
normal for this part — there are many imitation MG90S.

| Dimension | Value | Source |
| --- | --- | --- |
| Body | 22.5 × 12.0 mm | distributor drawing |
| Overall height | 35.5 mm | distributor drawing |
| Tab span, tip to tip | 32.5 mm | distributor drawing |
| **Tab hole pitch** | **28.0 mm — assumed** | **not dimensioned in any drawing found** |
| Servo pocket, proven | **24.03 × 12.80 mm** | measured off Cogley ε3.2, part `CA` |
| Output spline | 4.72 / 4.92 mm trial sizes | measured off Cogley's `ServoSizingPlate` |

The tab hole pitch is the one number no source gives, and it is the number a
mounting plate is made of. `coupon_mg90s` measures it.

**CQRobot VL53L1X — `proven`. Was the weak point; now the best-sourced row in
the table.** CQRobot's product wiki and product page both return **404**, and
the surviving listings disagreed with each other — 28.5 × 23 against 26 × 23,
with hole positions stated nowhere.

It was settled by measuring a CQRobot holder **already in service on two
robots**: `04_distance_sensor_mount` from LumaBot V2. A part that has held the
real board twice beats every datasheet that does not exist.

| Dimension | Value | How |
| --- | --- | --- |
| Retention slot, width | 23.600 mm | measured, groove face to groove face |
| Retention slot, height | 29.100 mm | measured, groove z span |
| Retention slot, thickness | 2.100 mm | measured, PCB groove |
| **Board** | **23.0 × 28.5 × 1.6 mm** | slot minus the +0.6 fit that mount uses on both axes |

The +0.6 is not an assumption bolted on afterwards — it is the only clearance
that makes *both* axes land on round numbers, and the pair it produces matches
one of the two competing listings exactly. **The 26 mm listings are wrong.**

The holder also answers a question the brief never asked: it uses **no screws**.
The board slides into a slot. That is why the hole positions never mattered, and
it is the better answer inside an eyeball anyway, where every gram sits on a
lever arm a 2.2 kg·cm servo has to accelerate.

`coupon_vl53l1x` changed job accordingly. It no longer asks which outline is
real. It carries three slots — the proven 2.100 plus 1.95 and 2.25 — because a
2.1 mm groove is exactly where over-extrusion and elephant's foot show up, and
that mount was not printed on this machine in this material.

ST's own VL53L1X datasheet still could not be retrieved — `st.com` timed out
repeatedly. Nothing depends on it.

### The eyeball cannot contain this board

Worth stating on its own, because it kills an assumption the whole design was
resting on.

The board is 28.5 × 23.0 mm. Its **diagonal is 36.6 mm**. Cogley's eyeball is
**Ø32**. A rectangle cannot fit inside a sphere smaller than its own diagonal at
any depth or angle, so the CQRobot board does not fit inside a Ø32 eyeball —
not tightly, not at all. Enclosing it needs Ø36.6 internal, so about **Ø41**
once the eyeball has walls. That is nearly twice a human eyeball and well past
what an MG90S will move convincingly on a lever arm.

So one of these has to give, and it is a decision rather than a calculation:

| Option | Cost |
| --- | --- |
| **Bare-module carrier** — a Pololu-class [VL53L1X carrier](https://www.pololu.com/product/3415) is 12.7 × 8.9 mm and drops into Ø32 with room to spare | ~$12 and a part order. Kills the problem outright |
| **Ø41 eyeball** | Stops reading as an eye, and puts real mass on the servo |
| **Sensor out of the eye** — into the forehead beside the camera | Loses "distance to what it is looking at", which was the whole point of the left eye |

The bare carrier is the recommendation, and [hardware.md](hardware.md) already
anticipated the swap. Note the CQRobot board is not wasted either way — it is
the right size to sit in the forehead or the chest.

**None of this blocks the structural work**, which is why the eyeball still is
not modelled.

ST's own VL53L1X datasheet could not be retrieved — `st.com` timed out
repeatedly. The module package is widely quoted as 4.9 × 2.5 × 1.56 mm, but
that figure has **not** been read from ST's document and is not relied on. It
does not block anything: the open-aperture decision below is a design choice
that removes the dependency on ST's cover-glass numbers entirely.

**This is the row that constrains the eyeball, and it is the row with no
source.** That is the single biggest risk in the design, and it is why the
eyeball is not being modelled yet.

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

**Importing it.** Blender 5.0 has no 3MF importer and the add-on hunt is not
worth it — 3MF is a zip of XML. `cad/` does not carry the importer because it is
a one-off, but the shape of it is: read `3D/3dmodel.model`, walk the `<build>`
items, resolve `<component p:path=...>` references into `3D/Objects/*.model`
(Bambu uses the production extension, so the meshes live in separate parts),
and read names out of `Metadata/model_settings.config`. 133 placed objects, 64
distinct meshes, about eighty lines of standard library.

**What it gave up.** Plate contents come from `Metadata/slice_info.config`. They
confirm the plate table in `reference/eye-mechanism/README.md` and sharpen it:
plates 1 and 3 are identical except for a single part, and so are 2 and 4.

| | SG90 plate | MG90S plate | Shared |
| --- | --- | --- | --- |
| A side | 1 — part `AG` | 3 — part `CA` | `AA` `AB` `AC` `AD` |
| B side | 2 — part `BE` | 4 — part `D` | `BA` `BB` `BC` `BD` |

`AG` and `CA` have identical vertex counts and differ by exactly **0.40 mm** in
one axis — the MG90S is that much thicker than the SG90, and it is the only
difference between the two variants of the whole mechanism.

Two things were worth more than the geometry:

- **`ServoSizingPlate`** on plate 5 is not a servo pocket gauge, it is a
  **spline gauge** — a 2.0 mm screw hole opening into trial bores of 4.92 and
  4.72 mm. Print it, see which grips the output spline.
- Cogley's assembly guide, which is inside the `.3mf` at
  `Auxiliaries/Assembly Guide/`, explains the part naming: the letters are
  **servo fit sizes**. You print a fitting block, find the hole that grips your
  particular servo, and print the parts carrying that letter. That is the same
  answer to the same problem this brief has — no calipers, imitation parts, and
  a dimension you cannot trust. `coupon_mg90s` is the same idea with our
  numbers.

The eyeball part (`Component74`) measures **Ø32.00 mm**, truncated to 19.98 mm
across one axis.

**Licensing — confirmed.** The model is
**Creative Commons Attribution – NonCommercial – ShareAlike (CC BY-NC-SA)**.

That came from Printables' own GraphQL API rather than the page, because both
makerworld.com and printables.com return 403 to a plain fetcher:

```bash
curl -s https://api.printables.com/graphql/ -H 'Content-Type: application/json' \
  -d '{"query":"{print(id:1220172){name license{name}}}"}'
# {"data":{"print":{"name":"Animatronic Eye Mechanism ε3.2",
#   "license":{"name":"Creative Commons — Attribution — Noncommercial — Share Alike"}}}}
```

MakerWorld additionally wraps its downloads in their Standard Digital File
Licence, which forbids redistributing the files or a derivative of them.

**ShareAlike is the clause that matters here.** Attribution and NonCommercial
are easy to live with — nothing about this build is commercial. ShareAlike means
that anything that counts as a *derivative* of his geometry would itself have to
be released CC BY-NC-SA. If Humalien's own eye mechanism contained his geometry,
that licence would reach into this repo.

So the line drawn in this document is not just good manners, it is the thing
keeping the licence out: **measurements are facts and carry no licence; geometry
does.** Our model contains zero Cogley geometry. It contains numbers measured
from his model, listed above, and it re-implements the *idea* of his servo
fitting block, which is an idea and not a shape. The reference `.3mf` stays
git-ignored, as `reference/eye-mechanism/README.md` already sets out.

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

## Where this has got to — 13 Aug 2026

### The model

`cad/eye_mech.py`. Run it inside Blender:

```python
exec(open(r"C:\humalien\humalien\cad\eye_mech.py").read())
```

It rebuilds every part from scratch and writes `exports/`. There is no `.blend`
to keep in sync and nothing is modelled by hand — the script *is* the model, so
it diffs and it reviews.

Everything lives in `P` and `BOARDS` at the top. Eyeball diameter, servo
envelope, travel limits, board outlines, clearance policy and slot travel are
all variables; nothing downstream hard-codes a dimension. When the VL53L1X gets
swapped for a bare module — and it will — that is one number and a re-run.

Units are 1 Blender unit = 1 mm, and the scene is set to millimetres on build.
STLs export at `use_scene_unit=False`, which matters: the alternative writes
metres and lands in the slicer a thousand times too small. Exports were read
back and confirmed correct size.

### What exists

**Print the coupons first.** All four together are about 40 g and well under an
hour. None of the parts below them should be printed until the coupon for that
board has been offered up to the real board.

| Part | Qty | Size, mm | Volume | What it is for |
| --- | --- | --- | --- | --- |
| `coupon_pca9685` | 1 | 76 × 39 × 2.4 | 5.5 cm³ | Ø2.5 holes at true 55.88 × 19.05, pocket at +0.5/side, nominal outline scribed |
| `coupon_b0385` | 1 | 52 × 52 × 2.4 | 4.4 cm³ | both hole patterns, 34 × 34 and 28 × 28, plus the lens aperture |
| `coupon_vl53l1x` | 1 | 101 × 16 × 15 | 8.9 cm³ | three retention slots — the proven 2.100 plus 1.95 and 2.25 |
| `coupon_mg90s` | 1 | 132 × 32 × 6 | 17.7 cm³ | four trial pockets A–D at +0.20/+0.45/+0.70/+0.95 per side; C also carries tab holes at the assumed 28.0 pitch |
| `camera_boss` | 1 | 61 × 43 × 5 | 8.9 cm³ | forehead mount for the B0385 |
| `pca9685_mount` | 1 | 78 × 41 × 6.5 | 9.6 cm³ | driver board plate with standoffs |
| `cable_anchor` | 6 | 20 × 12 × 3 | 0.6 cm³ each | zip-tie anchor for the looms |

Volumes are solid volume, so mass at 15% infill will be well under
`volume × 1.24 g/cm³`.

Every part prints **flat on its largest face with no supports** — that was a
design constraint, not an outcome. All pockets, apertures and slots have
vertical walls; the only raised features are the PCA9685 standoffs, which point
up. Nothing needs support inside a bearing surface or a linkage hole, because
there are no bearing surfaces or linkage holes yet.

**Every mounting hole is slotted**, per step two, with 1.0 mm of travel — ±0.5.
The board pockets locate; the slots forgive. That is the right division of
labour: a pocket at +0.5/side holds the board square, and the slots only have to
let the screws find their holes.

The one place slots are deliberately absent is on the coupons, where the holes
are **round and at exact nominal**. A slotted hole cannot tell you whether the
pattern is right, and telling you that is the coupon's entire job.

### Fastener BOM — provisional

Nothing here is owned yet, and this list only covers the parts above. Cogley's
mechanism will settle the rest once assembled.

| Fastener | Qty | Where |
| --- | --- | --- |
| M2 × 8 mm + nut | 4 | PCA9685 to its mount — board holes are Ø2.5, so M2 clears with room |
| M2 × 10 mm + nut | 4 | B0385 to the camera boss, on the inner 28 × 28 pattern |
| M2 × 6 mm | 2 | MG90S tabs, when `coupon_mg90s` confirms the pitch |
| M3 × 10 mm | 6 | camera boss ears and PCA9685 mount corners, into the skull |
| M2 heat-set insert | as needed | only where something is unscrewed repeatedly |

Buy M2 and M3 in a socket-head assortment rather than to this list — the counts
will change the moment anything is offered up.

### Wiring the left eyeball

Six wires leave the eyeball, and the eyeball rotates. Every trick below is worth
less than reducing the number of wires that cross the joint at all:

- `VIN`, `GND`, `SDA`, `SCL` have to cross. Four.
- `XSHUT` only earns its wire if a **second** VL53L1X is ever fitted — they
  share address `0x29` and the only way to run two is to hold one in reset while
  the other is re-addressed. There is one. Pull it high at the eyeball with a
  10 kΩ to VIN and it stops crossing.
- `GPIO1` is the interrupt. Polling over I²C at 4 Hz is nothing, and the gaze
  loop is already timer-driven. Leave it off.

**So four wires cross, not six.** That is a third fewer wear points for the cost
of one resistor, and it is worth doing before any mechanism is designed around
the loom.

The rest:

- **Wire.** 30 AWG silicone-jacket. Silicone flexes an order of magnitude better
  than the PVC on the supplied cable, which is stiff enough to fight the servo
  and to fatigue at the anchor. Keep the supplied connector, re-tail the wire.
- **Route through the rotation axis.** Wire twisted about its own axis survives
  far longer than wire bent back and forth. The pan axis is the one to exploit —
  bring the loom out of the eyeball on the pan centreline so pan becomes pure
  twist. Tilt has to be a bend, but tilt is ±20°, the smaller of the two.
- **Service loop.** A loose helix of roughly one and a half turns, about 20 mm
  across, living behind the eye. Anchored at *both* ends, so the twist
  distributes along the whole free length instead of concentrating where it is
  clamped. An unanchored loop looks tidier and fails sooner.
- **Strain relief.** A `cable_anchor` at each end of the free span. Nothing
  between them touches anything.
- **Terminates** at the audio hat's I²C pass-through header, alongside the SHT41
  and the MSA311. `0x29`, no conflicts — see [parts.md](parts.md).

### The head

A royalty-free female bust mesh is the starting point for the skull, matched to
the cyborg references in `reference photos/` — human face shell, mechanical
cranium, the circular port at the temple, cabling at the neck.

`cad/head_ref.py` imports and scales it. The mesh itself is **not in this repo
and must not be**: its licence is royalty-free **No AI**, which permits using it
in the build but not redistributing it, and explicitly forbids feeding it to
generative 3D tools — worth knowing because the Blender MCP server exposes
Hyper3D, Rodin and Hunyuan generators. Importing, measuring and cutting it is
deterministic CAD and is fine. The script keeps the *result* reproducible
without the asset ever entering git.

The source is Y-up and Z-forward and lying on its back, which no importer preset
maps correctly, so the script does the reorientation itself. It then finds the
neck by looking for the narrowest horizontal band between the shoulders and the
head, and scales on **head breadth = 150 mm** — the cleanest of the three
anthropometric anchors, since height depends on where you call the chin and
depth on where you call the occiput.

| | Scaled | Real adult |
| --- | --- | --- |
| Head breadth | 150.0 mm | 145–152 |
| Head depth | 184.7 mm | ~195 |
| Neck cut to crown | 211.5 mm | — |

**The head fits the A1 whole.** 150 × 185 × 211 against a 256 mm cube. That
softens [hardware.md](hardware.md)'s assumption that a head must be split with
alignment pins — splitting becomes a choice about surface finish, support and
where a skin seam can hide, rather than a limit imposed by the printer.

### Deliberately not built

Linkage geometry, the eyeball, its socket, the eyelids, and the hard stops. All
of them depend on answers the reference build has not produced yet, and the
travel limits in `P` are provisional until it does. The structural work above
does not depend on any of them.

The eyeball is also blocked on the thing this document is most honest about:
its diameter is set by a board whose dimensions no manufacturer publishes any
more. `coupon_vl53l1x` unblocks it for the price of one print.

### Known defect

The engraved coupons carry a handful of zero-area sliver edges — 4 on
`coupon_pca9685`, 8 on `coupon_b0385`, 4 on `coupon_vl53l1x`, 28 on
`coupon_mg90s`. Blender's EXACT boolean solver emits them wherever a font glyph
is cut into a face. This was chased properly and it is inherent to the solver:
unchanged by font, by triangulating either input, by union versus difference,
and by whether the cleanup pass runs at all. They enclose no volume, and slicers
drop them. `camera_boss`, `pca9685_mount` and `cable_anchor` carry no engraving
and are fully manifold. The labels are worth keeping — a coupon with four
unmarked pockets is not a measuring tool.
