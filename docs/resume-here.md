# Resume here — end of 15 Aug 2026

Everything below is verified in the file, not remembered. Start with **What to
do next**; the rest is why.

## 15 Aug in one line

The ear hub bosses that broke off the printer were **never attached** — the
hub exported as five separate solids. That, a sealed screw hole, a camera
pocket the Arducam could not seat in, PCA9685 standoffs fouling the pin tails,
and a stale casing in the assembly are all fixed. **`eye_pitch` turned out to
be settled at 62 all along, so the head halves are unblocked**, and the eye
mechanism is now a bespoke design rather than Cogley's.

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

0. **Print plate 5** — `forehead_casing` and `pca9685_mount`, the two parts
   that need running again. Then the head halves, plates 1 and 2, one print
   each; nothing gates them any more.

1. **All six plates are exported.** 3, 4 and 6 are printed; 5 is the reprint
   plate; 1 and 2 are waiting. To re-export any:

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
3. **The eye mechanism is drawn and passes its checks through the whole
   range.** `forehead_casing` has been relieved 2 mm for the eyelids, so
   **plate 5 must be re-exported before printing**. Cogley's ε3.2 is
   reference only.

## The six plates

| Plate | Holds | Status |
| --- | --- | --- |
| 1 | `HEAD_CRANIUM` | 209.2 cm³, 134 × 215 × 111 mm — **not printed, and no longer blocked** |
| 2 | `HEAD_FACE` | 130.4 cm³, 122 × 208 × 74 mm — **not printed, and no longer blocked** |
| 3 | `pi5_tray`, both `eye_bezel`, both `tray_rail`, 4× `cable_anchor` | **printed 13 Aug** |
| 4 | both `ear_spine`, all 5 coupons | **printed 14 Aug** |
| 5 | `forehead_casing`, `pca9685_mount` | **the reprint plate** — 15 Aug |
| 6 | both `ear_hub` | **printed 15 Aug**, after the boss fix |

**Plate 5 is the only one waiting.** `forehead_casing` because its camera
pocket would not accept the Arducam, and `pca9685_mount` because its standoffs
fouled the board's pin tails. They sit 14.3 mm apart.

Parts were **moved** between plates rather than copied, so no part appears on
two plates and no plate says "print me" twice. `exports/` is one folder per
plate, current geometry only — the superseded files were deleted, because git
history already holds every one of them and all they did in the working tree
was make it ambiguous which STL to print.

**The two ear hubs grew.** The root flare took them from 74.4 to 84.4 mm
across, and they had been hand-placed 82.4 mm apart on plate 4 — so on the old
layout they would now **overlap by 2 mm**. Moving them to plate 6 was
necessary, not tidiness.

The plate layout lives in the `print ready` collection and includes a hand
arrangement: `ear_hub_L` was moved to sit with `ear_hub_R`. That position is in
the `.blend` only. There is no script left that rebuilds the collection, on
purpose — the one that did was deleted so it could not overwrite the layout.

**Checked before you ask:** all 31 `FIT_`/`PR_` copies are the same geometry
as the part they copy, compared by a fingerprint that ignores position and
rotation — vertex and face counts, scale, and the sorted vertex-to-centroid
distances in local coordinates. A vertex count alone would pass two different
parts that happen to have the same number of points. Every part is a closed,
manifold solid, and every exported STL is one connected shell with every edge
shared exactly twice and zero degenerate triangles.

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

## The eye bay, measured — superseded 15 Aug

This section used to argue about whether the eye mechanism would fit and
where its bearings could go. It is all settled now; the answers, and the
measurements they came from, are under **The eye mechanism** below.

Two things from it are still worth carrying:

- **The temple pad bore is at x = ±49.79**, not 57.79. 57.79 is the inner
  wall face, which is what a probe walking outward until it hits something
  finds. A frame built on it put 107 vertices outside the skin. The pad runs
  **y 133..146** and its bore is Ø5.2 at **z 212.4..217.6** over that whole
  length — re-measured 15 Aug, because the earlier y-extents were a guess.
- **Cut slots disjoint, or one at a time.** The old eye plate's slots came
  back as skewed slivers because each was three overlapping solids in one
  batched cutter. That is the nested-cutter trap, and the eye mechanism has
  now hit it a fourth time.

## The speaker, and what it retired — 15 Aug

The speaker is a **Waveshare 8 Ω 5 W, 100 × 45 × 21 mm**, the one bundled with
the WM8960 Audio HAT. `BOARDS["speaker"]` said 70 × 30 × 16 and was marked
`conf = "listing"` with *"UNMEASURED … placeholders and nothing is built to
them yet"* — except two things were: `ear_spine`'s 80 mm height and its 72 mm
post pitch. The real part is 100 mm long, so it never could have bolted to
those posts, and its mounting holes are too small for a screw anyway.

**Decision: the speakers are glued on, and `ear_spine` is retired.** The spine
existed only to carry the speaker on two Ø9 posts. With adhesive it has no
job.

What that means in practice:

- The speaker goes on the **back face of `ear_hub`**, which is a good glue
  surface: flat at x=39.5, and the root flares made it lobed rather than a
  plain Ø65 disc, so it is about 95 mm across at the widest.
- The hub's two blind M3 threads at z=204±24 are now **unused**. Harmless —
  they are 6.5 mm deep in an 8 mm plug and break out nowhere.
- Both spines are already printed, so nothing was wasted. They are still on
  plate 4 and still in the file, just hidden.
- Fitting check, since the speaker is much bigger than planned: glued to the
  spine plane at x=29.5 a 21 mm speaker reaches in to x≈8.5, so the pair sit
  **~17 mm apart** at the centreline and clear each other. They are at y≈95,
  well behind the eye bay at y≈131, so they do not fight the eye mechanism.
  **Watch the top edge** — 100 mm centred on the ear line reaches z≈254 and
  the Pi tray is at z=256. Glue a few mm low.

## eye_pitch is 62, and the head is unblocked — 15 Aug

**Settled. It was never really open**, it was only unrecorded. `head_style.S`
has carried the answer all along:

```python
eye = dict(pitch=62.0, y=160.0, z=209.0, dia=41.0,
           rake_out=25.0, rake_down=10.0)
```

The sockets were cut on that, so the head is already a pitch-62 head. The
"sculpted sockets at 56" note was stale.

Confirmed against the geometry rather than taken from the constant. Sweeping
−y rays across `HEAD_FACE` and comparing each hit against `HEAD_SOLID` — a
gap in the face where the solid silhouette has material is an opening —
clusters into four openings: the two eye sockets at **x = ±34.0, 36 wide ×
40 tall, centred z = 205.6**, and the two ear ports at ±67.

Those numbers *are* pitch 62, seen through the rake. The openings sit at ±34
rather than ±31 because 25° of outward rake carries the skin aperture
outboard of the ball centre; the projected width is 36 against 41·cos 25° =
37.2; and the centre falls at z 205.6 rather than 209 because of the 10° of
downward rake.

**Consequences:**

- **Plates 1 and 2 no longer wait on anything.** The head can be printed
  whenever. It was the last thing gating them.
- `HEAD_CRANIUM` does not need re-cutting, so the `USERFIX` hand edit and the
  six hand-made plugs are not at risk.
- The eye mechanism has a hard target: **two Ø32 eyeballs centred at
  x = ±31, y = 160, z = 209**, in Ø41 sockets raked 25° out and 10° down.

Two traps if anyone re-measures this. A −y ray at the socket passes clean
through `HEAD_FACE` and hits nothing, which is indistinguishable from being
off the head entirely — test against `HEAD_SOLID` first to know where the
head *is*. And the openings have to be clustered before they are measured,
or the ear ports get averaged in with the eyes and the answer comes out as
92.6 mm.

## The eye mechanism — complete and moving, 15 Aug

**Cogley's ε3.2 is reference only. It will not be printed.** Two reasons: it
is **CC BY-NC-SA**, so none of his geometry can ship here and nothing built on
it can be commercial; and every one of his plates needs support material,
which nothing else in this project does.

`cad/eye_v2.py` — `build()` makes the `EYE_v2` collection, `check()` proves it,
`reach()` says what each servo can actually deliver, `pose()` puts it anywhere
in its range.

**Four servos**, against his six: pan and tilt each linked across both eyes,
plus one lid per eye so they can wink independently.

### Ten parts, all healthy

| part | | |
| --- | --- | --- |
| `eye_dome_R`/`_L` | 2038 v | Ø32 dome, hollow for the 5050 pixel, pan journal underneath, lever and link pin |
| `eye_gimbal` | 840 v | cradle, both pan journals, both tilt tubes, tilt lever |
| `eye_frame` | 284 v | one part now: an arch across both temples, and the mast down to the shaft |
| `eye_shaft` | 64 v | Ø5 × 29, the tilt axis — separate, so the gimbal can be assembled at all |
| `eye_peg_R`/`_L` | 128 v | Ø5 into the temple pad bore, locating the frame and the two head halves |
| `eye_lid_R`/`_L` | 1057 v | spherical band, hub on the gimbal tube, dog-leg crank |
| `eye_pan_bar` | 188 v | links both eye levers, dipped in the middle |

All ten: one shell, watertight, zero open edges, zero non-manifold, zero weld
debt, and inside the head at every pose. **`check()` passes** — no collision
with anything, at any of the twenty-nine poses it sweeps.

Ranges, and every one of them is what the linkage can really deliver rather
than what it was asked for: pan **±30°**, tilt **±16°**, each lid **52°**.

### The check now sweeps the range, and that is the whole point

`check()` used to test the mechanism standing still. Two of the three faults
that mattered were invisible that way, and both appeared the moment it started
posing:

- a yoke arm over the top of the eye swings **into `FIT_forehead_casing`** at
  full tilt — 6 mm in, and no length of arm avoids it;
- the pan bar's ends translate 5.5 mm sideways at full pan, straight into
  where both eyelid pushrods run.

Containment, collision-with-the-head, collision-with-each-other and
collision-through-the-range are four questions. It used to answer two.

### What changed, and why

**Each eye now hangs on ONE journal, underneath.** A yoke gripping both poles
needs an arm at radius ≥ 20 above the tilt axis, and the forehead casing is
solid across the full width from z=225 — which is exactly the top of the ball.
To clear it at every tilt an arm at radius 20.4 would have to end by y=154.7,
and the pole it has to reach is at y=160. So the top of the eye is left empty
and the dome runs on a Ø10 × 9 journal in the cradle below it.

**Tilt is ±16, not ±20**, and the cheek is what sets it. That journal hangs
26 mm below the tilt axis; a point that far below swings forward by
sin(tilt)×26, and the cheek's inner wall is at **y=172.7** — asked of
`HEAD_FACE`, not of `MOUNT_ZONE`, which has been 3–6 mm optimistic every time.
The price is slop: 0.3 mm of clearance over 9 mm of journal is about 2° of
wobble, and it is the loosest thing in the mechanism.

**The tilt bearings moved to the corridor between the eyes.** 48.5 was
measured against the eyeball and never against the eyelid, which is a shell
*over* the ball and reaches x=48.8. The outboard slot on the tilt axis is
3.86 mm wide and has to hold a boss, a journal and their running clearance.
The corridor between the two lids is 26.4 mm.

**One shaft, three concentric members** — frame shaft, gimbal tube, lid hub,
all on the tilt axis. Not a trick: a lid has to stay concentric with the ball,
and the ball's centre is on the tilt axis, so they were always the same line.
Riding the lid on the gimbal also makes it tilt with the eye for free.

**All four servos are on the fixed frame.** The file used to say pan and both
lids rode on the gimbal, and then place all four in the y=126 plane — 34 mm
behind the tilt axis, where riding on the gimbal would swing them ±11.7 mm
every time the eyes looked up. The cost is cross-coupling, which is linear,
repeatable and hysteresis-free, so it is mixed out in software. `reach()`
prints how much of each servo's travel goes on it.

**The frame is one part, at y 147.5..151.5,** and it has nowhere else to go.
Behind it the temple pad boss is solid from x=41.8 outward over z 206..223 —
measured — so a frame further back cannot reach the pad bore at all; the bore
is only open through the pad itself. In front of it the eyeballs start: panned
30°, a dome swings its back rim to y=146.7. Four millimetres, and the arch
fills them.

### The casing relief: decided and cut

**`forehead_casing` gave up 2 mm, and `check()` passes.** The eyelid is a
shell over the ball with 0.35 of running clearance and 1.2 of wall, so its
outer surface is 17.55 from the eye centre against the ball's 16. The ball's
top is z=225. The casing's underside was z=225 and solid from x=−47 to +47 —
checked by ray, not assumed. Thinning the lid does not escape it, and parking
it differently does not either; the band has to pass over the top of the eye.

So there is now a scallop 18 mm wide and 3 mm deep in the bottom rim of each
eye's share of the casing. It is the edge of a panel that runs up to z=283 and
carries nothing down there. Over the eyes the casing now starts at z=227.5;
everywhere else it still starts at 225. Both copies are watertight, and the
source and the plate copy agree by fingerprint.

**Plate 5 has to be re-exported before it is printed.**

`casing_relief()` prints the arithmetic and does nothing; `(apply=True)` cuts.

**Cut the FIT copy, not the source.** The cutter is built in world
coordinates. `FIT_forehead_casing` is in the head where the eyes are;
`forehead_casing` is parked out on the print bed at x=520. A box at x=±31
misses the source completely — it "cut" it and changed nothing, 1567 vertices
in and 1567 out, with no error — while the assembly went quiet because the
copy *had* been cut. `casing_relief()` now cuts the copy that is in the right
place and hands the source that mesh, so the two cannot drift.

### Clearance is a different question from collision

`clearances()` is new, and it earns its place immediately. Overlap tells you
about contact; it says nothing about a rod that misses the eyeball by a tenth
of a millimetre, and these rods are wire, bent by hand, running past printed
spheres. Worse, the pushrods sit in ALLOWED — a rod in its own pin hole is a
joint — so the overlap test was structurally blind to them.

It samples along each rod's axis and asks `closest_point_on_mesh`, ignoring
the last 4.5 mm at each end because that is the joint. First run:

- **`eye_rod_pan` was 0.84 mm INSIDE `eye_pan_bar`** at full pan and
  down-tilt, and had been the whole time. Pinned straight into the dipped
  middle of the bar, the rod ran along the bar's own underside. It now pins to
  a lug hanging 6 mm below the dip, and clears by 4.66 mm.
- the two eyelid rods pass the gimbal with **0.52 mm**. Tight, and known.
- nothing else is closer than 1.8 mm.

### The eye openings: measured, and left alone

`socket_aperture()` reports the opening's radius as **20.48 at its tightest
and 34.21 at its widest** against an eyeball of 16. The gap is not 4.5 mm all
round; it is 4.5 at one edge and 18 at another, because the bore is raked 25°
out and 10° down while the ball is not. That is what you see through the face.

A rim inside the opening was tried and thrown away, and the second of its two
faults is worth carrying forward:

- built as an annulus coaxial with the bore and trimmed against `HEAD_SOLID`,
  it came out standing proud of the cheek **like a lens barrel** — the trim
  did not take;
- its flat annular end face unioned into `HEAD_FACE` as a **single 145-sided
  n-gon**, and every BVH and every slicer triangulates such a face straight
  across its own hole. The model looked right and the exported STL would have
  had a disc across the eye socket. Triangulating to tidy it up is not the
  answer either — the sculpt has 3378 legitimate n-gons and triangulating
  those put 9 non-manifold edges into a printed part for nothing.

`HEAD_FACE` was restored and verified against `PR_HEAD_FACE`, its untouched
plate copy, by the same local-coordinate fingerprint `export_plate.verify()`
uses: 72075 vertices, 67574 faces, identical. Pat's call: leave the openings
alone.

### The dome's print orientation is still wrong

The file claims `eye_dome_R/L` print flat-back-down. They do not, and have not
since the file was written. Back-face-down puts the pan lever 4 mm below the
bed and lays the Ø10 journal boss on its side as an unsupported cantilever;
boss-down starts the sphere as a 90° overhang; boss-up starts it on a point.
Neither is printable as drawn.

The likely answer is to split the lever and the boss off as a separate part
that presses into the dome, which would also let the dome print back-down and
the stem print standing up. Not drawn. **Nothing else in the mechanism has
this problem** — the frame prints flat on its arch, the gimbal flat in its own
plane, the shaft and pegs standing on end.

### The traps, because this geometry invites them

- **The nested-cutter trap, hit a fourth time.** Two overlapping solids merged
  into one cutter bmesh are not a solid, and a boolean against them does not
  give the union of what they cut. The frame's peg socket came back with 155
  non-manifold edges from a Ø5.2 bore and the slot mouth that opens it,
  merged. Everything is now cut and unioned **one primitive at a time**.
- **Coplanar and near-tangent booleans are the same fault.** A butt joint is
  not an intersection, so the union leaves a second shell — the peg came out
  as three. And a face landing 0.0 mm from a cylinder's surface leaves a hole:
  the frame lost one 4.8 × 0.5 mm face because the mast's centreline passed
  2.2 mm above the tilt axis instead of through it.
- **`MOUNT_ZONE` is not the shell's interior.** It read 3–6 mm wider than
  `HEAD_FACE` at the cheek and again at the temple, both times in the
  direction that hides a clash. Ask the shell.
- **A horn out of phase reads as a linkage that does not fit.** The tilt servo
  could deliver −5.5..+18 of a range needing ±16, and the fault was that its
  horn pointed straight down its own pushrod, where it transmits nothing.
  `phase_horns()` now sets each neutral to the across-the-rod position, and
  tries both of the two solutions.
- **Asking a rigid linkage to hit a pose is the wrong question.** The old
  check fixed (tilt, pan) and looked for a horn angle that made the rod
  exactly the right length, then reported FAIL when it could not find one. A
  horn and a rod are one degree of freedom: for a given tilt the driven angle
  is a *function* of the horn angle. `reach()` sweeps the horn and reports the
  envelope instead.

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
- The eyeballs ARE modelled now — `eye_dome_R/L` in `EYE_v2`. `PROXY_eyeball_R/L` are the placeholders they replace and are kept only as a measuring rule.
- **`eye_bezel_R/L` are not vestigial after all.** The brief retired them
  when the eye openings became smooth Ø41 circles, and the openings did —
  but a Ø32 ball raked 25° out does not fill one, and the renders show a
  crescent you can see the gimbal through. Bezel, bigger ball or smaller
  opening; none of the three is drawn.
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

## The eyes got pupils, and the pixels got somewhere to go — 15 Aug

**Each eyeball now has an iris and a pupil.** `IRIS` in `cad/eye_v2.py`:
a Ø15 disc recessed 0.4 mm into the front of the ball so it reads as an eye
with the power off, and a Ø6.5 circle at its centre where the shell is thinned
from the **inside** to 0.9 mm — two perimeters at 0.4 plus a whisker — so the
5050 lights that circle and the rest of the ball stays opaque. Nothing is
drilled through and no second material is needed.

Both are a **sphere clipped by a cylinder**, and that matters. A flat-ended
cylinder cannot put a controlled step into a ball: sunk far enough to leave a
0.5 mm step it only reaches r=3.97, so a "Ø15 iris" came out Ø7.9 and the
depth ran away at the centre. Against a sphere the depth is the same
everywhere and the cylinder only decides how wide. They also go opposite ways
round — the iris is *cylinder minus sphere* (take material off the outside),
the pupil is *sphere intersect cylinder* (thin it from the inside). Getting
that backwards hollowed the iris out and left a 0.4 mm skin over the whole
disc, which measured as "iris depth 0.4" and split the dome into two shells.

**The 5050 pixels glue to the rib inside each dome.** The rib across the back
opening was there to anchor the pan lever; it is 10 mm tall now so it is also
the pixel's mounting pad, and the pixel sits on its front face square behind
the pupil. `fit_layout` places the proxy at `eye_y - 2.4` to match.

It used to sit **66 faces inside that rib**, and nothing reported it because
`check()` skipped every `PROXY_` object wholesale. It does not any more:
`SKIP_EXCEPT` lets the LED proxies through, because a proxy for something that
lives inside a printed part still has to fit inside it.

Two further things that only showed up once it was being checked:

- **A proxy that moves needs its collision tree rebuilt every pose.** The
  pixels are glued inside the eyeballs, so they tilt and pan with them. Built
  once with the rest of the head, they reported 36 faces of collision at 16°
  of tilt that were not there — a moving dome tested against a tree of where
  the pixel used to be.
- **The pixel is still `LISTING`**: 8 × 3 × 8, unbought and unmeasured, as
  its own comment in `fit_layout` says. There is now a pad it has to fit, so
  this is exactly the case the coupons exist for. Measure the real carrier
  before the rib's 10 mm is trusted.

**Everything shades smooth by angle now.** `smooth_all()` runs at the end of
`build()`, at 35°. Not plain shade-smooth: every face in these parts was
already flagged smooth and they still rendered faceted, because from Blender
4.1 the flag alone is not what does it — and smoothing everything flat would
round the corners off the brackets as well as the balls.
