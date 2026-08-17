# Humalien v2 — the brief

Opened 16 Aug 2026, at the point where v1 was assembled far enough to fail
honestly. Everything below is measured off `Humalien_v1.blend` or off parts
that were physically printed and held. Nothing here is an opinion about how
it should have been done.

## What v1 actually proved

v1 was not wrong about shape. Every failure it produced was about **building**
— printing it, assembling it, wiring it, servicing it. Five of them, and they
are all the same mistake wearing different clothes.

| # | What broke | The measurement |
| --- | --- | --- |
| 1 | Slender members printed as unsupported cantilevers | mast 80.7 mm² on air, cranks 24.6 mm², casing bosses landing 16–28 mm below the shell they hang from |
| 2 | The servos have no mount at all | `place_servos()` drops four **proxies**; no bracket part exists in any plate |
| 3 | The camera can only see two thirds of its frame | forehead column spans x −20..+18, lens barrel spans x 15..29 — **3 mm of the lens is behind solid face**, blocked from 12° inboard, ~30 % of frame |
| 4 | The PCA9685 does not sit where it was placed | rear wall is bowed: inner face at y=28.4 on the centreline, mount back face designed at y=44.0 — **15.6 mm of air** at the middle, contact only near x=±39 |
| 5 | It cannot be wired | every board bolts to the shell, so assembly means working inside a 106 mm deep bowl with both hands |

**#1 is solved and stays solved.** `aircheck()` inside `printcheck()`, threshold
15 mm² derived from the seven STLs that were actually printed. Do not relax it.

**#5 is the one that stopped the build.** The other four are parts. This one is
the architecture.

## The single change v2 makes

> **Nothing electrical bolts to the shell. Everything mounts to one rack that
> is built, wired and tested on the bench, and goes into the head as a unit.**

That is the whole of it. Every other change below follows from it.

The head already splits front/back at **y=135**, so access was never the
problem — the cranium opens like a bowl and you can see everything in it. The
problem is that seeing it and *reaching it with two hands and a connector* are
different, and v1 only ever checked the first. A rack moves all the fiddly work
to a bench where the part can be turned over.

### What the rack has to hold

| | where it is now | notes |
| --- | --- | --- |
| Pi 5 | tray at z 256..264, y 43.5..136.5 | already a separate part; becomes the rack's top deck |
| PCA9685 | 62.2 × 25.4, nominally y 42..50, z 209..251 | comes off the bowed wall entirely |
| 4 × MG90S | x −35.5..+35.5, y 119.9..132.1, z 134.9..234.1 | one 12 mm slab — see the spine below |
| eye mechanism | frame at y 135.5..166 | **stays in the face half**; joined to the rack only by the four pushrods |

### The envelope it has to live in

Measured inside `HEAD_CRANIUM`, rear inner wall by ray:

| z | depth available (135 − rear wall) |
| --- | --- |
| 150 | 80.8 mm |
| 195 | 98.3 mm |
| 225 | **106.5 mm** — the deepest point |
| 285 | 85.6 mm |

Interior half-width at the servo plane is ±50 at z=150, opening to ±57 by
z=170. The servo block is only ±35.5, so there is ~15 mm each side for the
rack's legs.

**Two openings already exist and both are useful:**

- **The neck**, open from z=98.3. At z=105 the bore runs y 26..113 and at
  least x ±30 — roughly 60 × 87 mm. Big enough to pass a loom, and probably a
  rack.
- **A rear aperture at x ±36, z 251..277** — 72 × 26 mm, lens-shaped. This is
  the Pi's port cutout. It is also the only place a cable can leave the head
  without crossing the split, which makes it the natural exit for the loom.

## Part by part

### The servo spine — new, never existed

One member standing in the y≈126 plane carrying all four servos.

The catch, and it is not negotiable: **the four shafts point three different
ways**, because the linkage fixes them. Pan drives a bar along x so its shaft
is vertical; tilt and both lids drive levers that pivot about x so their shafts
run along x. A servo's tabs are always perpendicular to its shaft, so **no
single flat face takes all four**. The spine carries four short ears, three
facing sideways and one facing up, each bolted through the real tab holes at
`tab_pitch = 28.0` — the one servo number that is proven, against
`coupon_mg90s` on 15 Aug.

Anchor it in **two** places: down onto the material at y≈126, z 110..122, and
outward to the side walls at z 150..170. A 100 mm plate held only at its bottom
edge is a cantilever, and this project has already snapped one.

`HEAD_CRANIUM` is protected and carries the irreproducible `USERFIX` edit plus
six hand-made plugs, so the spine wedges and bonds rather than bolting through
the sculpt.

### `forehead_casing` — camera moves outboard

x=22 → **x≈29**. That puts the whole 14 mm barrel inside the open window at
x 20..50 with margin, and takes the blocked angle from 12° out to about 30°.

It is already on the reprint plate, so this costs nothing. **The printed face
does not change** — the column is in the sculpt and the face is fine.

Carry the hand-enlarged S4B-ZR cable opening across when the pocket moves. It
lives on the source object now, and it is not reproducible from script.

### `pca9685_mount` — off the wall, onto the rack

It was fighting a bowed surface for no reason. On the rack it sits on a flat
face that was printed flat.

### Wiring — the part v1 never had

A loom, made on the bench, with connectors at every boundary the head can be
taken apart at:

- rack ↔ head: one bundle out through the rear aperture
- rack ↔ face half: the camera ribbon and the ToF, both of which cross y=135
- servos: four leads to the PCA, all on the rack, never disconnected

Note that **all four pushrods cross the split plane** — servos end at y=132.1,
`eye_frame` starts at y=135.5. The two halves get assembled around the linkage,
so the rods are a mechanical connector and want to be as easy to unpin as the
electrical ones.

## What carries over unchanged

- The head geometry. `Humalien_v1.blend` stays the source of truth and
  `HEAD_CRANIUM`/`HEAD_CYBORG` stay protected.
- The eye mechanism as redesigned on 16 Aug — frame, gimbal, lids, domes,
  stems, axles, shaft, pan bar. It passes `check()` at all 29 poses and
  `printcheck()` including `aircheck()`.
- Every gate: `printcheck()`, `aircheck()`, `verify()`, `chirality()`,
  `clearances()`, `weld_debt()`, `_one_solid()`.
- `eye_pitch = 62`, the ±31/160/209 eyeball targets, and the socket
  measurements.

## Open, and genuinely open

1. **Does the rack go in through the neck, or get sandwiched at the split?**
   The neck bore is big enough on the numbers but has not been checked against
   a rack that does not exist yet. Decide once the rack has a shape.
2. **Where the SHT41 goes** — unchanged from v1, still a placement decision
   about what it is supposed to measure, not a modelling problem.
3. **The eye socket crescent** — a Ø32 ball raked 25° in a Ø41 opening still
   shows a gap. Bezel, bigger ball, or smaller opening; none drawn.

## The NeoPixel rings — measured, parked, not designed around yet

**Deferred 16 Aug 2026.** The eyes must light up eventually; they do not have
to light up before they move reliably. Recorded here so the numbers are not
looked up twice.

Two in hand: **Adafruit NeoPixel Ring 12B, product 1643, barcode P1643E.**
Off Adafruit's own product page, not a reseller:

| | |
| --- | --- |
| outer diameter | **36.8 mm** |
| inner diameter | **23.3 mm** |
| thickness | **6.7 mm** — including the LED domes, so it is a disc not a PCB |
| weight | 3.3 g |
| drive | ~18 mA constant current per channel, one data line, chainable IN→OUT |

Confidence: **listing-grade off the manufacturer.** No calipers in the
workshop, so it has not been confirmed against the parts in hand. Treat it the
way `mg90s` was treated before its coupon — good enough to design against,
not good enough to cut a final bore to.

**The ring does not fit the v1 eyeball.** v1's ball is Ø32 and was drawn around
a single 8 x 3 x 8 mm 5050 pixel that was never bought and never measured. A
Ø36.8 ring is bigger than the ball it was supposed to sit inside. Whatever the
eye becomes, this is a hard input to it.

Three ways out, when it is time:

- **A** — ball grows to about Ø40 and the ring rides inside it. Costs the
  compact mechanism, and every LED wire still crosses the gimbal.
- **B** — the ring stays FIXED at the socket and the ball turns behind it. It
  drops into the Ø41 socket with 4 mm to spare, showing a lit ring with a
  Ø23.3 window and the pupil moving inside that window. **No wires cross the
  gimbal at all**, and it covers the crescent that a Ø32 ball in a Ø41 socket
  leaves. This is the one to beat.
- **C** — a smaller light. Adafruit's 7-LED Jewel is about Ø23 and fits a Ø32
  ball. Costs money and a wait.

**Power, because this is the load that gets forgotten:** two rings at 12 LEDs
x 3 channels x 18 mA is **~1.3 A peak at full white**, sharing a 5 V rail with
four MG90S that pull about 700 mA each stalled. Size the supply for both or
the Pi browns out mid-blink.

## Not open

The pushrods are **2 mm steel**. Filament buckles at 6.5–7.9 N against 10–13 N
of servo stall on three of the four rods; steel is 630–1325 N. A bicycle spoke
is 2.0 mm and free. This was settled with numbers, not preference.
