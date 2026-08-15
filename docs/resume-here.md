# Resume here — end of 13 Aug 2026

Everything below is verified in the file, not remembered. Start with **What to
do next**; the rest is why.

## State of the file

`Humalien_v1.blend` is saved and is the **source of truth** for the head
geometry. Two backups sit beside it: `Humalien_v1.preplug.blend` (before the
old screw holes were filled) and `Humalien_v1.prehubfix.blend` (before any of
the ear hub work).

`HEAD_CRANIUM` and `HEAD_CYBORG` are marked protected. `head_style.build()`,
`head_split.build()` and `head_mounts.build()` now **refuse to run** and print
what they would have destroyed. Pass `force=True` if you mean it — and mean it,
because `HEAD_CRANIUM` carries the irreproducible `USERFIX` edit at both ear
ports plus six hand-made hole plugs. `fit_layout` and `eye_mech` still run
freely.

`head_mounts.build()` also no longer defaults to `save=True`. It used to write
the `.blend` to disk twice per run before anyone had looked at the result.

## What to do next

1. **All four plates are exported.** 3 and 4 are printed; 1 and 2 are waiting
   in `exports/plate1/` and `exports/plate2/`. To re-export any of them:

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

## The four plates

| Plate | Holds | Status |
| --- | --- | --- |
| 1 | `HEAD_CRANIUM` | exported 14 Aug, 209.2 cm³, 134 × 215 × 111 mm |
| 2 | `HEAD_FACE` | exported 14 Aug, 130.4 cm³, 122 × 208 × 74 mm |
| 3 | `pi5_tray`, `forehead_casing`, `pca9685_mount`, both `eye_bezel`, both `tray_rail`, 4× `cable_anchor` | **printed 13 Aug**, STLs in `exports/plate3/` |
| 4 | both `ear_hub`, both `ear_spine`, all 5 coupons | exported 14 Aug to `exports/plate4/` |

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

`coupon_mg90s` is the valuable one. That 28.0 is the weakest number in the
whole CAD file.

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

## Still open, unchanged from 13 Aug

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
