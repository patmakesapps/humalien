# Shopping list — fasteners, wire, filament

For the Michaels run, 16 Aug 2026. **The wire and the filament are at Michaels.
The screws are not** — Michaels is a craft store and does not stock metric
machine screws in any size this build uses. Those come from Lowe's, Home
Depot or Amazon.

Counts below are read out of the CAD, not remembered. Lengths are calculated
and **not one of them has been test-fitted**, which is why the recommendation
is an assortment rather than exact sizes — see [What is still a guess](#what-is-still-a-guess).

---

## 1. At Michaels tomorrow

### The 2 mm pushrod wire — this is the one to not forget

The eye mechanism needs **four pushrods** bent from 2 mm steel wire. Michaels
carries exactly the right stock:

> **K&S Music Wire, .078″ × 36″, 3-pack — model KS505**, about $8.46
> [michaels.com](https://www.michaels.com/product/music-wire-078-x-36in-3pc-167123106313682950)

**.078″ = 1.98 mm**, which is the 2 mm the holes are cut for. `link_d` in
`cad/eye_v2.py` is 2.30 — 2 mm rod plus 0.3 of clearance, because a pivot
wants to be looser than a fastener but not sloppy.

**One 3-pack is far more than enough.** The four rods are:

| rod | length |
| --- | --- |
| `eye_rod_tilt` | 49.6 mm |
| `eye_rod_lid_L` | 44.9 mm |
| `eye_rod_lid_R` | 44.9 mm |
| `eye_rod_pan` | 34.2 mm |

174 mm of rod in total. Allow ~20 mm per rod for the Z-bends at each end and
it is still under 260 mm — a **single 36″ length is more than three times
what the mechanism needs**, and the 3-pack gives you nine attempts at bending
four rods. Buy it anyway; getting a clean Z-bend takes practice and this is
the cheapest part of the whole build.

*Do not substitute craft/floral/aluminium armature wire.* It is soft enough to
bend under servo load, which turns every pushrod into a spring and the
linkage into mush. Music wire is spring steel and that is the point.

**Backup if they are out:** a **bicycle spoke** is ~2 mm steel and works —
that is the substitute already named in the CAD comments. Any bike shop, or
the bike section at Walmart/Target, and usually under a dollar.

### Filament

Everything still to print, as solid volume straight from the exported STLs:

| plate | volume | ~PLA solid |
| --- | --- | --- |
| Plate 1 — `HEAD_CRANIUM` | 209.2 cm³ | 259 g |
| Plate 2 — `HEAD_FACE` | 130.4 cm³ | 162 g |
| Plate 5 — casing + PCA mount (reprint) | 21.7 cm³ | 27 g |
| Eye plate — 14 pieces | 39.1 cm³ | 48 g |
| **total** | **400 cm³** | **~496 g solid** |

At normal wall counts and 15–20 % infill the real figure lands around
**300–400 g**, so **one 1 kg spool covers everything left with room for a
failed print**. The two head halves are the bulk of it — the entire eye
mechanism is under 50 g.

Buy two spools of the same colour if you care about the halves matching, since
dye lots drift.

---

## 2. The screws — Lowe's, Home Depot or Amazon

### What the build needs

| What it fastens | Size | Qty | Length | Goes into |
| --- | --- | --- | --- | --- |
| **Ear hubs → shell** | **M3** | **6** | 12–16 mm | self-taps into a Ø2.6 pilot in the hub arm, through a Ø3.4 clearance hole in the shell |
| Pi 5 → `pi5_tray` | M2.5 | 4 | 12–16 mm **+ nuts** | Ø2.9 clearance through a 5 mm standoff — needs a nut, not a self-tap |
| PCA9685 → `pca9685_mount` | M2 | 4 | 8–10 mm **+ nuts** | Ø2.2 slots |
| Arducam B0385 → `forehead_casing` | M2 | 4 | 6–8 mm **+ nuts** | Ø2.2 slots |
| `pi5_tray` + `pca9685_mount` → shell | M3 | 4–6 | 10–16 mm | Ø3.4 slots; exact count not pinned until the shell exists |
| MG90S servos ×4 | M2 | 8 | ~8 mm | self-tap. **MG90S normally ship with their own screws** — check the bag first |
| VL53L1X | — | — | — | **no fasteners.** It drops down a channel onto a shelf and gravity holds it |

**Rough totals: ~12 × M3, 4 × M2.5, ~16 × M2, plus nuts and washers for the
M2 and M2.5.**

### What to actually buy

**Get one assortment kit rather than seven bags.** Nothing here has been
offered up to a real board yet, the shell is not printed, and the ear-hub
screws pass through a wall measured at 4.07, 5.34 and 4.15 mm at three
different points — so the right length is genuinely not known yet, and a kit
costs about what two wrong bags would.

> **160 pc M2/M2.5/M3/M4/M5 stainless kit, with nuts and washers** —
> [amazon.com](https://www.amazon.com/160pcs-Stainless-Screws-Assortment-Storage/dp/B074FH9SXQ)
>
> This single kit covers all three sizes this build uses and includes the nuts
> and washers the board mounts need.

**If you want the M3s in hand this week**, both big-box stores carry them —
but note the counts, several are 2-piece bags:

- Lowe's, Hillman **M3-0.5 × 10 mm, 12-count** —
  [lowes.com](https://www.lowes.com/pd/Hillman-3mm-0-5-x-10mm-Phillips-Drive-Machine-Screws-12-Count/999994826)
- Lowe's, Hillman **M3-0.5 × 20 mm, 12-count** —
  [lowes.com](https://www.lowes.com/pd/Hillman-3mm-0-5-x-20mm-Phillips-Drive-Machine-Screws-12-Count/999994828)
- Home Depot **M3 machine screws** (mostly 3-piece bags) —
  [homedepot.com](https://www.homedepot.com/b/Hardware-Fasteners-Screws-Machine-Screws/M3/Metric/N-5yc1vZc27iZ1z0sc32Z1z0sfzw)

**Neither store reliably stocks M2 or M2.5.** Big-box metric fastener drawers
usually start at M3. Order those online.

---

## What is still a guess

Worth knowing before you spend, because this project's rule is that a
dimension is unverified until a printed part has been offered up to the real
thing:

- **Every screw length here is calculated, not proven.** The ear-hub screws
  are the least certain: shell thickness varies 4.07–5.34 mm at the three
  arm positions, so 12 mm and 16 mm may both be needed. This is the argument
  for the kit.
- **The board hole sizes come from drawings, not calipers.** `coupon_pca9685`
  and `coupon_b0385` are printed and exist precisely to settle this — offer
  them up to the real boards before you commit to a screw size. Ten minutes,
  and it is the only reason those coupons were printed.
- **The MG90S screws are probably already in the servo bags.** Do not buy M2
  for them until you have checked.
- **Nothing needs M4 or larger**, and nothing needs a tap — every printed
  thread in this build is self-tapping into PLA.

## What you do *not* need

- **Speaker screws.** The speakers are glued on and `ear_spine` is retired,
  so the hub's two blind M3 threads at z=204±24 are unused. This was 4 × M3 ×
  10 on the old list.
- **Anything for the eyeballs.** The eye mechanism uses no fasteners at all —
  glue joints, printed pins, and the four wire pushrods above.

---

*Sources checked 15 Aug 2026. The Michaels product page would not load when I
checked it, so the price and stock come from search results — worth a look at
the shelf rather than trusting it. Everything else was read off the live
listings.*
