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

1. **Export STLs for plates 1, 2 and 4** as you come to print them. Only plate
   3 is exported. Naming follows `print_layout`: `<part>_x<qty>.stl`, and the
   `_xN` is the quantity to set in the slicer, not bodies in the file.
2. **Print the coupons** (they are on plate 4) before bolting anything to a
   real board. `pi5_tray`, `pca9685_mount` and `forehead_casing` are all built
   to dimensions the coupons exist to prove.
3. **The eye mechanism** is the open design question. See below.

## The four plates

| Plate | Holds | Status |
| --- | --- | --- |
| 1 | `HEAD_CRANIUM` | not exported |
| 2 | `HEAD_FACE` | not exported |
| 3 | `pi5_tray`, `forehead_casing`, `pca9685_mount`, both `eye_bezel`, both `tray_rail`, 4× `cable_anchor` | **printed 13 Aug**, STLs in `exports/` |
| 4 | both `ear_hub`, both `ear_spine`, all 5 coupons | not exported |

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
  that folder instead of writing to `exports/`.
- `eye_bezel_l` exports with two degenerate slivers 0.0007 mm across. Below any
  toolpath, repaired by the slicer on import, but it is a real artifact of the
  raked bezel boolean.
