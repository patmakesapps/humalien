# Resume here — end of 15 Aug 2026

Everything below is verified in the file, not remembered. Start with **What to
do next**; the rest is why.

## 15 Aug in one line

The ear hub bosses that broke off the printer were **never attached** — the
hub exported as five separate solids — and that, a sealed screw hole, a stale
casing in the assembly and a missing plate are all now fixed. **Plate 5 is
exported and ready to print.**

## State of the file

`Humalien_v1.blend` is saved and is the **source of truth** for the head
geometry. Two backups sit beside it: `Humalien_v1.preplug.blend` (before the
old screw holes were filled) and `Humalien_v1.prehubfix.blend` (before any of
the ear hub work).

There is **no backup from before the 15 Aug boss fix**, and that is worth
knowing rather than discovering. One was written, but `ear_hub_repair.build()`
took it *after* repairing rather than before, so the file it produced was a
copy of the fixed state under a name that said otherwise. It was deleted
rather than left to mislead. Nothing of value went with it: the only geometry
that changed was the two ear hubs, and what they used to be is fully described
below and in `cad/ear_hub_repair.py`. `Humalien_v1.prehubfix.blend` is still
the meaningful rollback point.

`HEAD_CRANIUM` and `HEAD_CYBORG` are marked protected. `head_style.build()`,
`head_split.build()` and `head_mounts.build()` now **refuse to run** and print
what they would have destroyed. Pass `force=True` if you mean it — and mean it,
because `HEAD_CRANIUM` carries the irreproducible `USERFIX` edit at both ear
ports plus six hand-made hole plugs. `fit_layout` and `eye_mech` still run
freely.

`head_mounts.build()` also no longer defaults to `save=True`. It used to write
the `.blend` to disk twice per run before anyone had looked at the result.

## What to do next

0. **Print plate 5.** `exports/plate5/` — both ear hubs and the re-cut
   `forehead_casing`. This is the plate that unblocks everything else.
   Then the head halves, plates 1 and 2, one print each.

   When the hubs come off: the bosses should be part of the disc, with a
   visible cone at the base of each. If any of them is a loose peg again,
   stop — that means the file being sliced is not `exports/plate5/`.

1. **All five plates are exported.** 3, 4 and 5 are printed or ready; 1 and 2
   are waiting in `exports/plate1/` and `exports/plate2/`. To re-export any:

   ```python
   exec(open(r"C:\Humalien\cad\export_plate.py").read())
   verify(1)            # plate copies still match the real parts?
   export_plate(1)      # -> exports/plate1/
   ```

   Naming is `<part>_x<qty>.stl`, and the `_xN` is the quantity to set in the
   slicer, not bodies in the file.

   **The two halves will not share a plate.** 134 mm and 122 mm side by side
   is exactly 256, with no clearance and no skirt. Two prints, and at
   209.2 + 130.4 cm³ - about 425 g of PLA - budget a day each, not a day for
   both.

   **Do not commit plates 1 or 2.** `.gitignore` holds them out; they are cut
   from the No-AI-licence sculpt.
2. **Print the coupons** (they are on plate 4) before bolting anything to a
   real board. `pi5_tray`, `pca9685_mount` and `forehead_casing` are all built
   to dimensions the coupons exist to prove.
3. **The eye mechanism** is the open design question. See below.

## The five plates

| Plate | Holds | Status |
| --- | --- | --- |
| 1 | `HEAD_CRANIUM` | exported 14 Aug, 209.2 cm³, 134 × 215 × 111 mm |
| 2 | `HEAD_FACE` | exported 14 Aug, 130.4 cm³, 122 × 208 × 74 mm |
| 3 | `pi5_tray`, `pca9685_mount`, both `eye_bezel`, both `tray_rail`, 4× `cable_anchor` | **printed 13 Aug**, STLs in `exports/plate3/` |
| 4 | both `ear_spine`, all 5 coupons | **printed 14 Aug**, STLs in `exports/plate4/` |
| 5 | both `ear_hub`, `forehead_casing` | **the reprint plate** — exported 15 Aug to `exports/plate5/` |

Plate 5 is the three parts that have to be printed again: the two ear hubs
because their bosses were never attached, and `forehead_casing` because the
hand edit to its camera cable exit had never reached the part the exporter
reads. Both hubs are 84.4 × 81.6 × 20.6 mm and the casing 96 × 58 × 5; on a
256 bed they sit 7.6 mm and 30.2 mm apart with 39.8 mm to the nearest edge.

`ear_hub` and `forehead_casing` were **moved off** plates 4 and 3 rather than
copied, so no part appears on two plates and no plate says "print me" twice.
The STLs they leave behind are superseded, so they were moved to
`exports/plate3/superseded/` and `exports/plate4/superseded/` — kept, because
they are the record of what actually came off the bed, but out of the folder
you drag into a slicer.

**The two ear hubs grew.** The root flare took them from 74.4 to 84.4 mm
across, and on plate 4 they had been hand-placed 82.4 mm apart — so on the old
layout they would now **overlap by 2 mm**. Moving them was necessary, not
tidiness.

`exports/` is one folder per plate — `exports/plate3/`, `exports/plate4/`.
Everything in `plate3/` is exactly the files that were printed on 13 Aug,
moved rather than regenerated, so it stays a record of what came off the bed.

The plate layout lives in the `print ready` collection and includes a hand
arrangement: `ear_hub_L` was moved to sit with `ear_hub_R`. That position is in
the `.blend` only. There is no script left that rebuilds the collection, on
purpose — the one that did was deleted so it could not overwrite the layout.

**Checked before you ask:** all 22 plate copies are the same geometry as the
part in the assembled head, compared by a fingerprint that ignores position and
rotation. Every part is a closed, manifold solid — zero open edges, zero
non-manifold edges.

## What 15 Aug found, and fixed

All of it is in `cad/ear_hub_repair.py`, which is re-runnable and proves its
own result. `head_mounts.ear_hubs()` is corrected too, so a clean rebuild now
produces the same geometry — but the repair had to be applied to the objects
already in the file, because `head_mounts.build()` rebuilds `HEAD_CRANIUM` and
that carries the irreproducible `USERFIX` edit and six hand-made plugs.

**The bosses were never attached.** Each hub exported as **five separate
solids**: the Ø65 plug, three free-floating Ø13 posts standing 0.461 mm clear
of its rim, and a sealed bubble. They printed as loose pegs on the bed, held
by nothing but first-layer squish. One line caused it — the arms were clipped
with `INTERSECT` against `MOUNT_ZONE`, and the zone has the Ø66 ear port
subtracted out of it. An arm is Ø13 on a r=36 circle, so it spans r 29.5..42.5
and its overlap with the Ø65 plug is a lens at r 29.5..32.5: every millimetre
of it inside r=33, every millimetre inside the port cutter. The clip deleted
exactly the material that welded each boss on. The old comment said the arms
sat "well outside the Ø66 bore" — true of the axis, false of the body.

**Nothing could have caught it.** Four disconnected closed shells are four
perfectly healthy closed shells, so the health check read 0 open / 0
non-manifold; the volume was right because no material was missing, only the
join; and `verify()` compared a plate copy against a source that was equally
wrong. `_one_solid()` in head_mounts.py is the check that was missing, and
`ear_hub_repair.report()` prints it for any part.

**Every boss now has a root flare.** Welding it back on was necessary and not
sufficient: the lens where a Ø13 post meets a Ø65 disc is 21.5 mm², three
millimetres deep, and the M3 is tightened along the print's Z axis — a pure
interlayer pull on the joint's thinnest section. The flare is a 45° frustum
from Ø23 to Ø13 over 5 mm and takes that section to **116.3 mm²**, 5.4×. It
is self-supporting, and at 5 mm it stays inside the plug's own 8 mm thickness,
so it can never reach the front face, show in the ear port, or foul the
NeoPixel ring. Ø23 is set by the 15.75 mm from the 290° boss to the z−24 blind
thread, not by taste.

Checked afterwards, per vertex rather than trusted to a boolean: **0 flare
vertices outside the skin, 0 buried in the shell wall**, on both hubs. The only
faces that overlap `HEAD_CRANIUM` are the arm tips, which are flush against the
inner wall by design, and hub and spine still share the plane x=39.5 exactly —
hub min x 39.500, spine max x 39.500, so they can touch and never interpenetrate.

**The +z spine screw had no hole.** Its blind thread is cut 6.5 mm into the
8 mm plug by a cutter whose back cap landed exactly ON the plug's back face.
Coplanar cutter, coplanar result: at z+24 the boolean capped it over, leaving
a sealed Ø2.6 × 6.5 void inside the plug (−34.1 mm³, inward-facing) and
nothing for the screw to go into. The identical cutter at z−24 resolved
correctly, which is how it survived a review. Blind cutters now start 2 mm
behind the face; depth into the plug is unchanged. Both threads now read as
open holes 39.5 → 46.0 with 1.5 mm of plug left in front.

**A defect class this project could not see.** The flare's base cap is
coplanar with the plug's back face and its top rim tangent to the Ø13 shaft,
so the union left **42 coincident vertices** — which exported as 84 zero-area
triangles and 72 edges shared by four or six faces, on a mesh Blender called
perfectly healthy. `print_clean()` cannot catch it: it returns early on
anything already reading 0 open / 0 non-manifold, which this did.

Three fixes were tried and scored on the exported STL. A plain
`remove_doubles` at 1e-4 won outright — 0 degenerate triangles, every edge
shared exactly twice, **volume identical at 23649.20 mm³ to four decimals**.
Rebuilding the flare with an overshoot and a flat trim was worse on both
counts and moved the volume by 78.7 mm³. `weld_debt()` in ear_hub_repair.py
is the detector, and it has to be phrased as *how many vertices a weld would
merge*: the obvious version — weld a copy and count non-manifold edges —
always returns zero, because bmesh's remove_doubles tidies the collapsed
faces away as it goes.

`print_clean()`'s trigger was deliberately **not** loosened to catch this
generally. Letting more parts into that path is what tore both head halves
apart the last time, and the fix belongs in the geometry, not in the exporter.

**The assembly was showing a stale casing.** `FIT_forehead_casing` still held
the old 2366-vertex part. All 31 `FIT_`/`PR_` copies are now checked against
their sources and all 31 agree.

**The exported files are verified from the files, not from Blender.** All
three plate-5 STLs: one connected shell, every edge shared exactly twice, zero
degenerate triangles, and the two hubs bit-identical to each other at
23649.20 mm³.

## Where the hand edits actually live

`forehead_casing`'s hand edit was on **`PR_forehead_casing`, the plate copy** —
and `export_plate()` reads the *source*. A re-export would have quietly
printed the old part again. This is worth generalising: **a hand edit is only
safe on the object the exporter reads.**

How it was settled, since guessing wrong would have destroyed the edit: the
source matched `exports/plate3/forehead_casing_x1.stl` exactly — 4760
triangles, 17910.5 mm³ — so the source was untouched since 13 Aug, and all ten
other plate-3 copies matched their sources, so no rebuild had been through.
The difference is one 19 × 17 mm patch at the S4B-ZR camera cable exit: 1070
vertices of detail replaced by 33, 592 mm³ of material removed, swallowing the
engraved `B0385` lettering that sat inside it. An enlarged cable opening.

The edit is now on the source, and it is clean — one solid, watertight, zero
degenerate faces. The as-printed geometry is kept as the hidden object
**`forehead_casing_asprinted_13aug`**, so this is reversible.

## What changed on 13 Aug, and why it matters tomorrow

**The ear hub bolts somewhere new.** `arm_a` moved from `(90, 210, 330)` to
`(50, 170, 290)`. The 210° position had only 2.59 mm of reach and built as a
0.07 mm disc buried in the shell wall with a pilot drilled into nothing. The
whole 190–260° quadrant is dead — the skull closes onto the hub's back plane
there. 90° was separately wrong: `spk_pitch/2` and `arm_r` are both 36.0, so
the speaker post sat on that exact axis.

**The shell was re-cut to match.** Six new Ø3.4 holes at the new angles, six
old ones plugged with cylinders measured to each wall (4.07, 5.34 and 4.15 mm —
they differ, which is why they were measured). Those plugs exist in the
`.blend` only; a clean rebuild never makes the old holes.

**The ear hub is now two parts.** Split on the plug's back plane at x=39.5:

| Part | Extent | Prints on | Support |
| --- | --- | --- | --- |
| `ear_hub` | x 39.5..60.1 | its Ø65 back face, 3226 mm² | none |
| `ear_spine` | x 29.5..39.5 | its 16 × 80 face, 1368 mm² | none |

As one piece it had features standing off **both** faces, so no orientation put
a flat surface on the bed. Rejoined with **2 × M3 × 10** at y=95, z=204±24 —
clearance through the 4 mm spine, 6.5 mm blind thread into the 8 mm plug.

## What the plate 4 export turned up, 14 Aug

Eight of the nine parts left Blender **not watertight**, and it had never
shown up because plate 3 happened to be clean. Two separate causes, both now
repaired on the export copy by `export_plate.print_clean()`:

- **Zero-area slits** on four of the five coupons, on `ear_hub`, and on
  `eye_bezel_L`. A coplanar boolean seam left a T-junction — three short
  collinear edges tiling one long one, with a zero-width face missing between
  them. `coupon_mg90s` had seven. They enclose no volume, so nothing prints
  differently, but every slicer stops to repair them.
- **`ear_spine` was three overlapping shells**, not one solid: a box with two
  Ø9 posts pushed through it, merged into one bmesh with no union. That welds
  into 48 edges used more than twice. Fixed with a self-union, rolled back
  automatically if it moves the bounding box.

Checked afterwards straight from the files, not from Blender: all nine
watertight, every edge shared exactly twice, and `ear_spine_L`/`_R` identical
at 5715.3 mm³ despite the union tessellating the mirror differently — which
is the evidence the union did not eat anything.

Worth knowing: `verify()` in that file compares plate copies to source parts
in **local** coordinates on purpose. Doing it in world space reported all nine
plate-4 parts as different when the real disagreement was 8×10⁻⁴ mm of float
noise from the differing transforms and the local distances were bit-identical.

## Assembly order, once plates 3 and 4 are off the bed

**Offer every coupon up to its real board before bolting anything to
anything.** It takes ten minutes and it is the only reason the coupons exist.
Three parts already printed on plate 3 rest on numbers only a coupon can
confirm:

| Coupon | Settles | Already built on it |
| --- | --- | --- |
| `coupon_pca9685` | whether the **HiLetgo** clone matches Adafruit's Eagle board — 62.23 × 25.40, Ø2.5 at 55.88 × 19.05 | `pca9685_mount`, whose holes are slotted *because* this is unproven |
| `coupon_b0385` | the Arducam drawing — 38 × 38, outer pitch 34, inner 28 | `forehead_casing` |
| `coupon_mg90s` | `servo_tab_pitch = 28.0` — **listing-grade, not dimensioned in any drawing** | every servo pocket in the eye mechanism |
| `coupon_vl53l1x` | the slot fit measured off a LumaBot holder | `forehead_casing` |

`coupon_mg90s` is the valuable one. That 28.0 was the weakest number in the
whole CAD file.

**Settled 15 Aug: the servos fit the coupon.** `servo_tab_pitch = 28.0` is
confirmed against real MG90S hardware, so it is now a measured number rather
than a listing guess, and servo pockets can be cut against it.

Then, none of which needs the shell:

- Solder the PCA9685 headers — **the spare first**, that is why it is a 2-pack
- Pi 5 onto `pi5_tray`, with both `tray_rail` and the four `cable_anchor`
- PCA9685 onto `pca9685_mount`
- Camera and VL53L1X onto `forehead_casing`
- `ear_hub` + `ear_spine` joined, 2 × M3 × 10 each side
- Wire it up, `i2cdetect -y 1`, confirm `0x40`, first servo sweep

Blocked until the shell exists: mounting the ear hubs (six M3 through the
shell) and the eye bezels.

**Fasteners are not in [parts.md](parts.md) and nothing has been bought.**
The build needs at minimum 4 × M3 × 10 for the two hub joins, M3 for the six
shell mounts, M3 for the speaker posts, and M2/M2.5 for the boards. This is
the most likely thing to stop an assembly day dead.

## The eye mechanism — the real open question

**The reason it was blocked is stale.** `head_mounts.eye_plate` is kept but
uncalled, and its docstring says there are only 59 mm of clear width at the eye
line because "everything outboard of |x|=29.5 is ear hub". That was measured
against the one-piece hub. Splitting it changed the answer:

```
              x              y              z
ear_hub_R  39.5 .. 60.1  53.0 .. 127.5  163.7 .. 238.1
ear_spine  29.5 .. 39.5  87.0 .. 103.0  163.5 .. 244.5
old hub    29.5 .. 65.5  59.0 .. 131.0
```

Nothing in the ear assembly reaches y ≥ 128 any more. Clear width at the eye
line z=209, inside `MOUNT_ZONE`:

| y | inside the zone |
| --- | --- |
| 125 | 74.0 mm |
| 131 | **120.4 mm** |
| 134 | 118.0 mm |

Against the **~100 mm** the mechanism and its rings need. Both causes of the
original collision are gone: the inboard hub mass, and the old 330° arm which
sat at y=126.2, z=186 — exactly where the plate's side screw at z=188 went, and
which is where those 79 intersecting vertices came from.

**But the space was never the only problem.** Still genuinely unknown, and not
resolvable by measuring the file:

- **Cogley's ε3.2 hole pattern has never been taken.** That is why the plate
  carried a slotted 20 mm grid rather than holes. It stays unknown until the
  reference mechanism is assembled. The brief's rule stands: *do not start
  cutting geometry that depends on those answers before they exist.*
- **`eye_pitch` is unresolved** — sculpted sockets at 56, design value 62. One
  number, and it is a decision, not a calculation.
- **Licence.** Cogley's ε3.2 is CC BY-NC-SA. Measurements are facts and carry
  no licence; geometry does. Nothing of his may end up in this repo.

Two practical notes for whoever draws it:

- At y=131 a temple fixing is only **3 mm** forward of the ear port's edge (the
  Ø66 bore spans y 62..128). Moving the plate to y=133–134 buys clearance and
  costs about 2 mm of width.
- The old plate's slots came back as skewed slivers because each was three
  overlapping solids in one batched cutter. That is the nested-cutter trap this
  file has now hit three times. Cut slots disjoint, or one at a time.

## Still open

- **The SHT41 has no case, and no part in the CAD file at all.** It is in
  parts.md as in-hand, it has an I²C address reserved (`0x44`), and there is
  no `BOARDS` entry and no mount. Two things have to be settled before one can
  be drawn, and neither is a modelling problem:

  1. **Where it goes**, which hardware.md already flags: *"the temperature
     sensor will lie to you. Mounted inside a sealed head full of Pi, servos
     and an amplifier, it measures the head, not the room."* Inside the head
     measuring the head, behind a vent measuring the room, or in the base, are
     three different parts. That is a decision, not a calculation.
  2. **Its dimensions**, which are not in this repo. Every board in `BOARDS`
     carries its source and its confidence — `b0385` off a drawing, `mg90s`
     marked LISTING and given a coupon precisely because it is unproven.
     Nothing should be cut to a remembered figure for the SHT41 either.

  The established move here is a coupon first, the way `coupon_vl53l1x` and
  `coupon_mg90s` were done. It is small, it prints in minutes, and it settles
  the fit before any bracket depends on it.

- Six old ear screw holes: **closed**, no longer open.
- The eyeballs are not modelled. `PROXY_eyeball_R/L` only, Ø32.
- `eye_bezel_R/L` may be vestigial — the brief says the ring-bezel debt died
  when the glow moved inside the eyeball and the eye openings became smooth
  Ø41 circles. Worth checking before printing them again.
- `print_layout.OUT_DIR` still points at `C:\humalien\humalien\print\v1`, a path
  from an older repo layout. Running `print_layout.build()` silently creates
  that folder instead of writing to `exports/`, and it writes every part flat
  in one folder rather than by plate. Use `export_plate.py` instead;
  `print_layout` is now only consulted for its `PARTS` orientation table.
- `eye_bezel_l` has two degenerate slivers 0.0007 mm across, an artifact of the
  raked bezel boolean. `export_plate.py` cleans these on the way out, but the
  file in `exports/plate3/` predates that and still carries them. Harmless -
  below any toolpath - but re-export plate 3 if you print it again.
- The **source parts still carry the defects**; only the exports are cleaned.
  That is deliberate - `Humalien_v1.blend` keeps the geometry that was
  inspected and signed off - but it means the coupons and `ear_spine` will
  need cleaning again on every export, which `export_plate.py` does for you.
