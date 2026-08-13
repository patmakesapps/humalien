# Eye design brief

A brief for modelling Humalien's own eye mechanism, as opposed to the reference
one being printed to prove the servos out. Read [parts.md](parts.md) for what
exists and [hardware.md](hardware.md) for why eyes come first.

## The job

Design a two-eye animatronic mechanism for a printed cyborg head, driven by
MG90S servos over a PCA9685, consuming the normalized gaze targets that
`brain/gaze.py` already produces.

Neither eyeball carries anything but a light. **The camera and the VL53L1X both
live in the forehead**, side by side on one plate — `forehead_casing` — which
keeps face position usable as an absolute signal instead of an error signal to
null out, and keeps the distance reading steady instead of swinging with gaze.

> **Superseded, 13 Aug 2026.** This brief was written around a different
> idea: *the left eyeball contains a VL53L1X, so Humalien measures distance to
> whatever it is looking at.* That was the difference that "drove the whole
> design", and it drove a lot of this document — the eyeball diameter, the
> wiring, the whole section on wires crossing a moving joint. It is dead. The
> sensor moved to the forehead casing next to the camera and has been built
> that way since; the paragraphs it touched are corrected in place below and
> marked like this one.
>
> What retiring it buys, which is more than tidiness:
>
> - **The eyeball is unblocked.** It was waiting on VL53L1X board dimensions
>   nobody publishes any more. Both eyes are now plain Ø32 printed balls.
> - **Nothing crosses the eye joint but the pixel's three wires.** The hard
>   problem this brief spends a section on mostly evaporates.
> - **Eyeball diameter is a free choice again.** Ø32 came from Cogley's part,
>   not from a board that had to fit inside it.
> - `coupon_vl53l1x` still earns its print — it now proves the slot in the
>   forehead casing instead of a pocket in an eyeball.

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

**SKU confirmed.** ASIN `B0CLXZ29F9`, sold by UCTRONICS, *"...Low Distortion
M12 Lens **Without** Microphones"* — matching [parts.md](parts.md), and matching
the title of the datasheet the table above is built from. Arducam publish that
datasheet through uctronics.com, which is their own store, so the drawing and
the listing are the same part. Arrives 14 Aug 2026.

### What counts as the source of truth

Worth writing down, because it caused a wrong call here. The three are not
interchangeable and each answers a different question:

| Question | Authority |
| --- | --- |
| *Which part is it?* | the order — ASIN and listing title |
| *What are its dimensions?* | the manufacturer's mechanical drawing for that SKU |
| *Is the drawing right, and did the printer hit it?* | the fit coupon |

The order settles identity and nothing else. A listing's dimension text is
listing-grade and gets the `listing` treatment. The drawing settles nominal
dimensions but not tolerance and not what a printer will actually produce, which
is the coupon's job. Nothing skips a rung: a confirmed SKU does not make the
drawing verified, and a drawing does not make the print correct.

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

> **What is and is not trustworthy in that source.** In the LumaBot model the
> **hole depths and sizes are known to be wrong**; the **dimensions are
> correct**. Everything taken above is slot geometry — groove faces, groove
> depth, groove thickness, groove height — and not a single screw hole, so it
> all sits on the trustworthy side of that line. Its fastener schedule (Ø3.38
> clearance, Ø2.59 and Ø2.49 pilots, 6.5 and 10 mm deep) was **not** used
> anywhere; the M3 fixings on these parts are our own slotted holes. Worth
> writing down, because the next person to open that file for reference needs
> to know which half of it to believe.

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

**Decided: the ToF moves to the forehead**, beside the camera, using the
CQRobot board as it stands, on one plate with the camera — see
`forehead_casing` below.

That gives up the one thing which made the left eye different from every
reference mechanism online — distance to *whatever it is looking at*. Range and
gaze now decouple: the sensor measures straight ahead while the eyes track. Say
so plainly rather than pretend otherwise. In exchange it costs nothing, buys no
new parts, and [hardware.md](hardware.md) already argued the distance sensor
"wants to look where the face looks", which a forehead mount satisfies exactly.

If the coupling is ever wanted back, the bare-carrier option above reopens it
without disturbing anything else — that is the merit of keeping the sensor's
mount a separate part rather than merging it into the camera plate.

**The connector is the constraint, not the sensor.** The 6-way JST sits on the
*same face as the sensor* and stands proud of it, wires and all. Anything
covering the board fouls the connector long before it gets near the optics.
That — not modesty about the field of view — is the real reason the proven
CQRobot holder leaves its whole front face open.

This was got wrong once: the first version of the casing had a modest 20 × 22
window sized for the sensor, which the connector would have collided with on
first assembly. The rule that came out of it is worth keeping: **when copying a
proven part, copy the reason, not just the dimension.** The open face was
recorded and then not carried across, because the measurement was taken and the
question "why is it like that" was not asked.

So the face of the board is left completely clear, and it is held by its two
vertical edges alone — 1.5 mm of material in front and 1.5 mm behind, forming a
C-channel each side.

### Which way it loads decides whether it needs screws

**Down.** The board drops into the channel and lands on a closed shelf, and
gravity holds it there. Nothing else is needed.

Loaded any other way — up from below, or sideways from an edge — gravity works
to eject it and a fastener becomes mandatory. There is nowhere trustworthy to
put one: the board's mounting hole positions are still unknown, which is the
whole reason the slot approach was copied in the first place. So the loading
direction is not a detail, it is what removes the fastener from the design.

An earlier version had it sliding in sideways from the outboard edge with the
channel open at that end, which meant precisely nothing stopped it sliding back
out. It would have hung there. Now the channel is a U: open at the top to load,
closed at the bottom by an 18 mm shelf.

**Fit it connector up.** The wires then leave through the same opening the board
slid in through, and never have to cross the shelf. If belt-and-braces retention
is ever wanted, a zip tie through a `cable_anchor` does it without needing a
hole in the board.

Connector height is **unmeasured** — no calipers, and it is in no drawing.
`conn_keepout` is set to a deliberately generous 9.0 mm to cover a vertical JST
plus a gentle wire bend. It is a **keep-out the face shell has to respect**, and
it is the number to take off the real board when the coupon goes on.

An open window also happens to satisfy the optical rule for free: it cannot clip
the field of view, cannot bounce IR back into the sensor, and means the sensor's
exact position on the board never has to be established.

**Both sit in one row on one plate.** The camera and the sensor are side by
side with their apertures on a single horizontal centreline, 56.2 mm apart. An
earlier version had them as two separate brackets on the reasoning that their
relative position was a skull question; that was wrong. Two brackets is two
chances to be out of line, and alignment here should be a property of the
geometry rather than something to get right at assembly.

It costs nothing to guarantee, because the B0385's sensor is dead centre on its
board — 19.00 mm from two adjacent edges on Arducam's drawing — so lining the
pocket centres up lines the optical axes up. Camera by screws through slotted
holes, sensor dropped down a channel onto a shelf and held by gravity, three M3
fixings along the bottom, no supports anywhere.

The camera's cable exit is a **through slot on the bottom wall** of its pocket.
The drawing puts the S4B-ZR 3.47 mm from the board's bottom edge, so that is the
edge it has to leave by — a first version notched the top, which is simply the
wrong side of the board. It is cut through the full plate thickness rather than
just breaching the pocket wall, because which face the socket stands on is not
established, and a through slot serves the cable either way.

## The eyes light up instead

> **Decision changed — 13 Aug 2026, later the same day.** The light moves
> *inside* the eyeball: one addressable 5050 pixel per eye, aimed at an iris
> printed as a thin translucent window (0.8–1.2 mm clear PETG prints frosted
> — its own diffuser). The glow tracks the pupil at every gaze angle, which
> a static ring cannot do, and it is what "light coming from within" actually
> means. The cost is the thing this section was proud of avoiding: wires
> across the moving joint — 4 from the left eye (5V, GND, DIN, DOUT to chain
> on), 3 into the right. That is exactly the load the left-eye wiring plan
> below was written for before the ToF moved to the forehead; it applies
> verbatim. The rings — already ordered and shipping — are not wasted: one
> goes **behind each Ø66 ear port**, framing the speaker grille as the
> reference photos' glowing hub, and they are the bench-test article for the
> Pi 5 WS2812 chain before any wire is threaded through an eyeball. The
> ring-bezel styling debt dies with the move; the eye openings become smooth
> Ø41 circles. To buy: two 5050 mini pixels, a couple of dollars. Everything
> below stands as the record of the ring design and its numbers, which the
> ear ports now use.

With the sensor out, the eyeball is free, and a
[NeoPixel Ring 12](https://www.adafruit.com/product/1643) goes in each eye.
Adafruit publish the board file, so these are `exact`, parsed the same way as
the PCA9685:

| Dimension | Value | Source |
| --- | --- | --- |
| Outer diameter | 36.830 mm | Eagle `.brd`, layer 20 arcs, r = 18.415 |
| Inner diameter | 23.368 mm | Eagle `.brd`, layer 20 circle, r = 11.684 |
| LED pitch circle | Ø29.464, 12 at 30°, first at 12 o'clock | element placements |
| Mounting holes | **none** | there are none in the board file |
| Thickness | 6.7 mm | product page envelope, not from the `.brd` |

### It does not go inside the eyeball either — and that is the good news

Ø36.83 against a Ø32 eyeball. Same collision as the ToF. But the ring should
never have been inside a moving eyeball, and three things fall out once it is
mounted **static in the socket** with the eyeball turning behind it:

- **A sphere rotating about its own centre sweeps no extra volume.** The ring
  cannot collide with the eyeball at any gaze angle, at ±30° pan or anywhere
  else. That is a clearance guarantee for free, and it holds no matter what the
  linkage turns out to be.
- **No wires cross the moving joint. None.** The brief spends a whole section on
  wire crossing a rotating joint being the design's worst wear problem. A static
  ring simply does not have the problem.
- **No mass on the lever arm.** The 3.3 g stays on the skull where the servo
  never has to accelerate it.

The eyeball's front pole looks out through the ring's Ø23.368 hole. Set the ring
plane 12.5 mm forward of the eye centre and a Ø32 sphere measures Ø19.97 there —
**3.4 mm of clearance all round**, with the ring sitting 3.5 mm behind the front
pole. A glowing annulus around a moving eye, which is what
`reference photos/` shows.

Because there are no mounting holes, the ring has to be trapped by a lip.
`coupon_neopixel12` tests exactly that, and the lip is the part worth testing —
it overhangs the pocket, so it is a bridge, and a bridge that droops is a ring
that will not seat flat.

### Two things that will bite

**The Pi 5 cannot drive WS2812 the old way.** `rpi_ws281x` worked by DMA-timing
the BCM2835's PWM peripheral. The Pi 5 moved GPIO onto the RP1 and that path is
gone — this is not a bug to work around, the hardware is different. Working
options, decide before writing any node code:

| Option | Notes |
| --- | --- |
| [PIOLib](https://www.raspberrypi.com/news/piolib-a-userspace-library-for-pio-control/) | Official. Uses the RP1's PIO, so timing is not the CPU's problem |
| [Pi5Neo](https://github.com/vanshksingh/Pi5Neo) | SPI, `spidev` only dependency |
| Adafruit CircuitPython NeoPixel_SPI | SPI, [Adafruit's own Pi 5 guide](https://learn.adafruit.com/circuitpython-on-raspberrypi-linux/using-neopixels-on-the-pi-5) |

**The PCA9685 cannot help.** It is PWM over I²C; WS2812 is a timed one-wire
protocol. This is a genuinely new interface on the Pi, not another channel on a
board that is already there.

Two more, smaller: 3.3 V data into a 5 V WS2812 is marginal — use a 74AHCT125
level shifter or run the ring nearer 4.5 V so its threshold drops. And 24 LEDs
at full white is ~1.44 A, which belongs on the ALITOVE 5 V 5 A servo supply and
never on the Pi. An iris glow at low brightness is a small fraction of that, but
size the rail for the mistake, not the intent.

### Does it connect to what is already owned?

Power yes, data no. This is the only part in the build that does not plug into
something already on the bench.

```
5V 5A ALITOVE ──► ring 5V, both rings        the supply already bought
1000uF cap    ──► across 5V and GND          the one already on order
Pi GPIO10     ──► [74AHCT125] ──► ring1 DIN  SPI0 MOSI, hardware-timed
ring1 DOUT    ──► ring2 DIN                  chainable: one pin drives both eyes
Pi GND ──► supply GND ──► ring GND           COMMON GROUND, not optional
```

The rings chain, so **both eyes run off a single data pin** — 24 pixels on one
line. Nothing on the I²C bus changes and the PCA9685 is untouched.

Adafruit's product copy says the ring "cannot be used with a Linux-based
microcomputer". That warning is about bit-banging a timing-critical protocol
under a non-real-time OS, and it is fair. The answer is to stop bit-banging and
hand the timing to hardware — SPI or the RP1's PIO — which is what all three
libraries above do, and why Adafruit's own Pi 5 guide contradicts their older
product text.

**To buy:** ~~two rings ($8.95 each) and a 74AHCT125 (~$1.50)~~ — the rings
are ordered and shipping as of 13 Aug. Still to buy: two addressable 5050
mini pixels for the eyeballs, and the 74AHCT125 if it was not in that order.

**To verify before wiring:** that SPI0 is actually free. The WM8960 hat takes
I²S on GPIO 18–21 and I²C on 2–3, which should leave GPIO 7–11 alone, but that
is an assumption about a board already in the stack rather than something
checked. `raspi-gpio get` settles it in one command.

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

> **Superseded, 13 Aug 2026.** *"The VL53L1X is the constraining part. Its
> board sets the minimum eyeball diameter, and the eyeball diameter sets
> everything else."* Not any more — the sensor is in the forehead casing.
> Nothing sets the eyeball diameter now except what reads as an eye and what
> the mechanism wants, so Ø32 is a choice rather than a floor.

## Hard constraints

**Optical path.** The VL53L1X cannot see through printed plastic, and it cannot
see through an arbitrary clear window either — ST's datasheet has strict cover
glass requirements around thickness, air gap and crosstalk. Design for an **open
aperture** in front of the sensor. If a cover is wanted later for looks, treat
it as a change that requires re-testing the sensor, not a cosmetic detail.

**Wires cross a moving joint** — but far fewer than this brief was written for.
It used to be six, for the VL53L1X in the left eyeball, and that was the hardest
constraint in the document. With the sensor in the forehead it is **three wires
per eye** for the 5050 pixel, and both eyes are the same. The advice still
holds and is now easy to follow: no slip ring, fine silicone-jacket wire, an
explicit service loop with somewhere to live, routed through the rotation axis
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
5. A wiring plan for each eyeball — wire gauge, service loop path, strain
   relief, and where the pixel's three wires terminate. This used to say "for
   the left eyeball specifically… where the six wires terminate", back when
   the VL53L1X lived in it. Both eyes are the same now and it is a much
   smaller job.

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

The bespoke design departs from it in the ways [parts.md](parts.md) sets out,
so it is a starting point and a measuring stick, not a base model to edit. It
used to depart from it most in putting the VL53L1X in the left pupil; with the
sensor in the forehead the two are now closer than they were, and the reference
is a better measuring stick for it.

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
- **VL53L1X in the forehead too**, on the same plate as the camera, on one
  shared aperture row. Both eyes are plain printed balls, each with a 5050
  pixel behind a translucent iris window. (This line read "VL53L1X in the left
  pupil, right eye plain" until 13 Aug 2026.)
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
| `forehead_casing` | 1 | 96 × 58 × 5 | 18.6 cm³ | camera and distance sensor side by side, apertures on one centreline |
| `pi5_tray` | 1 | 93 × 64 × 8 | 16.9 cm³ | the Pi 5 bolts to it — round board holes, slotted skull fixings |
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

### Wiring the eyeballs

**Three wires per eye**, and both eyes are the same: `5V`, `GND`, `DIN` for the
5050 pixel that lights the iris from inside. The chain can run in one eye and
out the other, so the second eye costs one extra crossing wire, not three.

> **Superseded, 13 Aug 2026.** This section used to be the hardest constraint
> in the brief, titled *"Wiring the left eyeball"*, and it argued six wires
> down to four:
>
> - `VIN`, `GND`, `SDA`, `SCL` have to cross. Four.
> - `XSHUT` only earns its wire if a **second** VL53L1X is ever fitted — they
>   share address `0x29`, and the only way to run two is to hold one in reset
>   while the other is re-addressed. There is one. Pull it high at the eyeball
>   with a 10 kΩ to VIN and it stops crossing.
> - `GPIO1` is the interrupt. Polling over I²C at 4 Hz is nothing, and the gaze
>   loop is already timer-driven. Leave it off.
>
> All of it moot: the sensor is in the forehead casing, where its six-wire
> cable crosses nothing that moves. Kept because the `XSHUT` reasoning is
> still correct and will matter the day a second VL53L1X is fitted anywhere.

The advice that survives is the mechanical half: no slip ring, fine
silicone-jacket wire, an explicit service loop with somewhere to live, and
route through the rotation axis where possible.

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

### The head serves the parts, not the other way round

Worth stating before it gets forgotten, because it is easy to drift the other
way once a nice mesh is in the scene. **The mesh is a styling surface and
nothing more.** It gets remodelled into a cyborg head around the mechanism. It
does not get measured for dimensions the mechanism then has to honour.

Concretely: do **not** derive interpupillary distance by measuring the mesh's
eyes. `eye_pitch` is a design parameter — set by what the mechanism needs and
what reads as human — and the sockets get moved to suit it. Anything measured
off the mesh is a starting proportion, never a constraint.

So the number that matters is the envelope the head has to swallow:

| Demand | Across | From |
| --- | --- | --- |
| Two Ø32 eyeballs at 62 mm pitch | 94.0 mm | eyeball Ø from Cogley, pitch by design |
| Two static Ø36.83 NeoPixel rings at the same pitch | 98.8 mm | Adafruit board file |
| Cogley's longest ε3.2 part | ~99 mm | measured from the reference |

Call it **~100 mm across** for the mechanism and its rings. The head at 150 mm
breadth leaves about 142 mm inside a 4 mm wall, so it fits with room — and the
rings clear each other easily, since 62 mm of pitch against a 36.83 mm ring
leaves 25 mm between them.

That is the check worth repeating whenever the head is restyled: not "does this
look right", but "is there still 100 mm across and 185 mm front to back". If a
styling change ever costs that, the styling loses.

### The rest of what lives in the head

**Raspberry Pi 5 — built.** `pi5_tray`. Straight off
[Raspberry Pi's own mechanical drawing](https://datasheets.raspberrypi.com/rpi5/raspberry-pi-5-mechanical-drawing.pdf):
85 × 56 mm board, four Ø2.7 holes on a 58 × 49 pattern, 3.5 mm in from one long
and one short edge.

**That pattern is not centred on the board.** Its centre sits 10.0 mm off the
board centre along the length. Assume it is centred and every hole is out by
10 mm, which is invisible until the board will not drop on. Verified after
building: holes at (−39, ±24.5) and (19, ±24.5).

Board holes here are **round, not slotted**. The slotting policy is for
dimensions that have not been verified — this one comes from the manufacturer's
own drawing and the board in hand is a genuine Pi, so there is nothing to take
up and slotting would only let it rack. The skull-side fixings *are* slotted,
because where the tray lands in the head is still guesswork. Slot what is
unknown, not everything.

**X1200 UPS — parked, not designed for.** The plan is USB-C charger power for
now, with the X1200 as a later option if it moves to battery. It pogo-pins onto
the Pi's underside rather than taking the 40-pin header, and wants roughly 15 mm
of room below the board. That is why `standoff` in `pi5_tray` is a parameter and
not a literal: taking the option later changes one number, not the layout.

**Jetson Orin Nano — out of scope.** The Asus laptop is the brain over WebSocket
and nothing is designed around a Jetson. If one ever arrives it goes in the head
if it fits or below it if it does not, and that is a decision for then.

### Speakers — placement still open

Two enclosed 8 Ω 5 W modules, in hand. **They have a mounting flange with a
screw hole at each end**, so they bolt straight down — no clamp, and no printed
baffle needed, because the module is its own sealed enclosure. That is worth
knowing before designing anything: the printed part is a *cradle with vibration
isolation*, not an acoustic box.

Dimensions are unmeasured and nothing is built to them yet.

**Decided: one behind each ear.** It puts the drivers out at the sides, furthest
from a centre-mounted mic pair, and closest to where a head actually radiates
sound. The alternative — behind the mouth — is better for the illusion, because
the voice would appear to come from the mouth, but it is worse for echo and it
puts a vibrating enclosure in the most crowded part of the skull. Behind the
ears also gives each module its own pocket in a region with nothing else
competing for space.

The constraint that decided it, and which is worth keeping in view:

> **The microphones are on the WM8960 hat**, which is bolted to the Pi. So mic
> position is not a free choice — it is wherever the Pi goes.
> [hardware.md](hardware.md) advises putting distance between speaker and mics
> and keeping "the mics higher up", but that is not an independent decision. It
> is a constraint on **where the Pi lives**, and it argues for the Pi high and
> rearward in the cranium — which is also exactly where the open-cranium
> references put visible mechanism.

What is still needed before a cradle can be drawn: **length, height and depth of
one module, and the flange hole spacing.** A ruler to ±1 mm is plenty for
packaging — this does not need the coupon treatment, because the module is a
sealed box being bolted down rather than a bare board being located.

### The fit study — 13 Aug 2026

`cad/fit_layout.py`. Run it after `eye_mech.py` and `head_ref.py`; it rebuilds
a `FIT_Assembly` collection that places every structural part inside the head
at its working position — linked duplicates of the printed parts (same mesh
data, so a part rebuild flows through on re-run), `PROXY_*` objects for the
boards and bought parts built from the same numbers `BOARDS` carries, and the
100 mm envelope gauge. The script checks itself: `verify()` ray-casts every
part against the head skin and reports anything poking out, with the known
head-remodelling debts whitelisted so a layout regression cannot hide among
them.

| What | Where (x, y, z in head frame) | Note |
| --- | --- | --- |
| Eyeballs Ø32 | (±31, 160, 209) | pitch 62 from `P`, pupil line just below the nasion at 213 |
| Eye pixel | inside each eyeball | 5050 addressable behind a Ø12 translucent iris window; LISTING until bought |
| Ear hub + ring | in the Ø66 ports, face &#124;x&#124;~63 | hub is a TBD printed part (ring seat + speaker grille); ring recessed in its face |
| `forehead_casing` | upright, boards forward, y 162..167, z 225..283 | aperture row z=257.5; camera at x=+22, ToF at −32; bottom edge clears the eyeball tops by 1.6 |
| `pi5_tray` | flat, long axis fore-aft, y 43.5..136.5, plate z 256..259 | Pi board top 265.6, hat stack ~282, rear corner 3.5 clear of the dome |
| `pca9685_mount` | upright on the rear wall, y 42..50, z 209..251 | the wall bows 13 mm across the plate — the skull prints bosses under the slots |
| Speakers | outer face ~|x| 54.5, z 175..245, leaning 12° with the wall | LISTING-grade dims; re-place when a ruler has met the module |
| Cable anchors | 2 rear wall, 2 side walls, 2 parked | anchors only earn a position once a loom exists |

**What the study found — the places the head must change to serve the parts:**

- **The mesh's own eye sockets sit at pitch 56, centre z≈214.** The design
  pitch is 62 (`P["eye_pitch"]`, provisional). So either the styled sockets
  move ~3 mm outboard per side, or `eye_pitch` drops toward 56 — one number
  either way, and it is a decision, not a calculation. The sculpted eyeball
  components in the mesh were measured for this and then dropped from the
  styled copy.
- **The brow flanks are the one real fight.** The casing's top corners breach
  the skin by up to 10.3 mm at |x|>40, z>265, and the camera board's own
  corner by 3.3 — the female scan's forehead is too curved for a 96-wide flat
  plate high in the brow. Two honest fixes: restyle the brow band fuller and
  flatter (the plated-face reference has exactly that brow), or chamfer the
  casing's spare top corners in a rev — the fixings and pockets don't use
  them. Currently carried as a styling debt, not a part change.
- **The rings need bezels.** A flat Ø36.8 ring against a doubly-curved face
  cannot be flush at the centre and buried at the rim: the outboard rim sits
  ~10 mm proud at x=±49. *Resolved the same day by removing the cause: the
  glow moved inside the eyeball and the rings moved to the ear ports, where
  they sit concentric inside the bore and touch nothing.*
- **Nothing else fights.** Tray, driver mount, speakers and anchors all sit
  inside with margin once placed to the measured walls; the cranium swallows
  the whole electronics stack with the mic hat exactly where hardware.md
  wanted it — high and rearward.

### Styling — 13 Aug 2026, where it settled

`cad/head_style.py`. Builds `STYLE_Head`: `HEAD_CYBORG` is a cleaned copy of
`HEAD_REF` (the original stays, hidden) carrying the reads all three
reference photos share: a 4 mm shell, Ø66 circular ports swallowing the
sculpted ears with the ear-hub module recessed inside, an open cranium, Ø41
eye sockets at the *design* pitch 62, and the camera bore and ToF window on
the forehead casing's row.

It also emits **`HEAD_SKIN`**, the cleaned single surface, hidden. Every
containment question in this project has to be asked of that and not of
`HEAD_CYBORG`: ask a solidified shell whether a point is inside and the ray
crosses the inner wall, then the outer wall, comes back even, and the parity
test reports that the Pi is outside the head.

**No added volumes, with one exception the references justify.** A visor band
was built here and withdrawn: every reference keeps a smooth human silhouette
and gets its cyborg from seams, hubs and openings. The exception is the brow,
below.

Four seam reads, and they are all cheap:

| Read | How |
| --- | --- |
| Cranial cap | groove, a tilted plane near the crown |
| Ear port rings | groove, concentric at r=39 around each Ø66 port |
| Brow band | groove, an ellipse round the camera bore and the ToF window |
| Face / cranium | a real parting line at y=135 — see the split, below |

**Seams are displacement, not booleans.** A boolean groove on a doubly-curved
100k sculpt is a slow crash. Instead each seam is an implicit surface and
every vertex within half a width of it is pushed in along its own normal.
Two failed attempts are recorded in the code because both looked right in
principle: subdividing only the edges that cross the seam leaves triangle
fans of slivers, and a groove cut into slivers shades as a row of beads
however smooth its profile is; and pushing along a radial from the middle of
the skull is smooth but runs tangential low on the ear ring and shears the
mesh sideways there. Grid-subdivide whole faces, push along a
neighbour-averaged normal, and the groove comes out clean.

**The eye sockets are raked, and that is the fix for a socket that read as a
gouge.** A bore driven straight back along +Y through a face this curved
comes out 31 mm deeper at the temple edge of its rim than at the nose edge —
measured, y=160.1 against y=190.9 around one rim — so the opening looks torn
and no flat bezel can ever sit in it. A real orbit faces outward and slightly
down. Fitting a plane to the eight measured rim points gives a surface normal
27° outboard and 12° down; the bore follows it at 25° and 10°. Rim spread
drops from 31 mm to 5.6 mm. The eyeball still looks straight ahead — only the
opening is raked — and a Ø41 bore raked 25° still presents a 41 × 37 aperture
to a Ø32 ball.

**The brow debt is closed.** The fit study measured the forehead casing
breaking out through the brow flanks by up to 10.3 mm and named two honest
fixes: restyle the brow band fuller and flatter, which the plated-face
reference has, or chamfer the plate's spare top corners. Both were
parameterized and off. Both are now on. `S["swell"]` — a normal-direction
swell, wide and shallow, r=52 amp=6.0 — took it to 4.6 mm; r=34 amp=7.5 was
tried first and read as a knuckle over each eyebrow. `casing_chamfer()` took
the rest, on the line 6|x| + 3.5y = 332, sized against the list of vertices
that were actually still outside rather than against a guess: a first attempt
at 368.5 sounded close enough and shaved a 1.6 mm sliver off a corner that
was already radiused. `fit_layout.verify()` now reports **clean**, and the
three brow entries have come off `EXPECTED_OUT` so a regression fails.

### Making it printable — 13 Aug 2026

Three things the sculpt was carrying that a printer would have had to pay
for, all in `head_style.py`.

**The mouth was full of geometry.** A tongue, gums and a throat bag — about
8800 faces sitting in the middle of the skull, exactly where the electronics
go. The previous pass looked for it with a ray-parity test inside a
hand-drawn box and found almost none of it, and the reason is worth keeping:
**parity is the wrong question.** The lips are slightly parted, so the cavity
is formally *outside* the skin and parity votes to keep every face of it. The
right question is whether a face can see the sky. `_strip_buried` fires 42
rays over the sphere from every face above the neck and deletes anything that
escapes in fewer than 5% of directions. That catches the mouth bag, the
nostril cavities, the ear canals and the eyelid interiors under one rule with
no boxes to draw — 10859 faces — and everything it deletes was invisible from
outside.

**Deleting a cavity leaves its mouth open**, and Solidify turns an open
boundary into a rim: a 4 mm wall standing on edge. Around the ear those came
out as thin fins poking through the skin behind the port, which is what
prints as a curl of stringy plastic and snaps off in the bag.
`_fill_small_holes` caps every opening the strip left; the neck ring, at
93 mm across, is the one it is told to leave alone. The mouth, the nostrils
and the ear canals become closed skin rather than holes into a head full of
electronics.

**The shoulders were still attached.** The source is a bust, 394 mm across.
Cutting at the neck — z=100, the narrowest horizontal band, just under the
jaw — takes 40% of the mesh off the print and leaves a clean planar ring for
a neck to bolt to later.

### Mounting — 13 Aug 2026

`cad/head_mounts.py`. Before this, every part in the fit study was floating.
The layout was honest about it — the skull-side fixings are slotted precisely
because the numbers were guesswork until a head shell existed — and now one
does.

**The rule: a screw is only worth drawing if a hand can reach it.** That
single test decides most of the design, and it is what made the split
mandatory. Two patterns, chosen by which side of the skin the hand is on:

- **boss** — a post standing on the shell's inner surface, reaching out to
  meet the part's own mounting face, screw in from the part's side.
- **through** — a clearance hole in the skin with the part behind it carrying
  the thread, so the screw head sits on the outside of the head. Visible
  fasteners are not a compromise; every reference photo is covered in them.

No boss length is guessed. Each is raycast from the part's fixing point to
the shell's inner surface, so a re-run after a styling change re-measures
rather than re-guesses. The same trick shapes parts: build a lug deliberately
too long, subtract the head, and it comes back trimmed to the skin's
curvature — with one caveat that cost a rebuild, that this only tidies the
part of a lug *inside* the wall. Anything reaching past the outer surface is
in free air, nothing subtracts it, and it comes back as a spike.

| Part | How it is held | Gap the fixing crosses |
| --- | --- | --- |
| `forehead_casing` | 3 bosses off the brow, screws from behind | 14.8 / 23.3 / 14.7 mm |
| `pca9685_mount` | 4 bosses off the rear wall | 2.2–2.9 mm — the wall bows |
| `cable_anchor` ×4 | 1 boss each, rear and side walls | 3.4–5.2 mm |
| `pi5_tray` | 4 screws down into two `tray_rail` ledges | — |
| `tray_rail` ×2 | 2 × M3 each through the skin | — |
| `ear_hub` ×2 | 3 × M3 each through the skin, into arms measured to the wall | — |
| `eye_bezel` ×2 | slip fit in the socket | — |

Three new printed parts, all shaped by the shell itself:

**`ear_hub`** is the part the fit study left as `PROXY_ear_hub_TBD`: a Ø65
plug carrying the NeoPixel ring in a recess, the grille through its middle,
the speaker on two posts behind it, and three arms reaching out to the shell.
It fits **from inside**, and it has to — the head's surface around the ear
varies by 20 mm in depth across the Ø66 port, so no flat collar could ever
sit on that skin, and any arm long enough to reach the shell is wider than
the bore it would have to pass through. Once the head splits, fitting from
inside costs nothing. The speaker stops being a zone marker floating near a
wall and becomes a part bolted to a part.

**`eye_bezel`** closes the 4.5 mm annulus between the Ø41 socket and the Ø32
eyeball, so the eye reads as an eye in a socket rather than a ball dropped
down a hole. Its face is set from the shallowest point on the socket rim,
measured along the raked bore axis. Its bore is Ø35.6, which leaves **2.18 mm
to the eyeball** — checked with a BVH overlap test rather than by looking at
it, because at the first size, Ø33.6, it looked like a collision in the
viewport and measured 1.29 mm and zero intersecting faces. It was not
touching, but 1.29 mm is not a number to trust once there is a gimbal in
there instead of a perfect sphere.

**`tray_rail`** is a ledge each side for the Pi 5 tray. Four bosses sound
obvious and are impossible: at tray height the skull is 120 mm across and the
nearest floor is 100 mm below, so a post under a corner would be a 100 mm
spike. Ledges off the side walls are what the geometry allows, and
`eye_mech.pi5_tray` gained four side fixings to land on them — two of its
original four were unusable in this skull, one with the cranial opening
behind it and one with 62 mm of air in front, which had left the tray on a
two-point mount free to pivot about its own long axis.

The cranial opening moved for the same reason. Where it was — y 12..55,
z 162..256 — it deleted exactly the piece of rear wall the PCA9685 bolts to
and left that part hanging in a hole. It is now on the upper occiput, where
it shows the Pi and its hat, which is the "mechanism high and rearward" the
open-cranium reference has and where [hardware.md](hardware.md) wanted the
mics anyway.

### Splitting the head — 13 Aug 2026

`cad/head_split.py`. A coronal plane at **y=135**, 7 mm in front of the ear
ports. This softens a conclusion above: the head does fit an A1 whole, so
splitting was called "a choice about surface finish, support and where a skin
seam can hide". Three things turned the choice into a decision.

**Assembly.** Half the fixings only pass the can-a-hand-reach-it test with
the face off. The casing's three screws go in from behind. The tray's four go
down into the rails from above. The ear hubs are wider than the port they sit
behind and cannot be fitted any other way. A one-piece head would need every
one of those done blind through a Ø66 ear port.

**Support.** Printed whole and upright, the chin, the underside of the nose
and the brow are all overhangs, and the face — the one surface where finish
matters — is printed on its most curved axis. Split, both halves print
cut-face-down:

| | Bed | Height | Note |
| --- | --- | --- | --- |
| `HEAD_FACE` | 122 × 208 | 74 mm | nose pointing up, nothing on the face over ~45° |
| `HEAD_CRANIUM` | 134 × 215 | 111 mm | only its own dome to worry about |

**The seam is free styling.** At y=135 the parting line runs over the crown,
down in front of each ear port and across the cheek to the jaw, close to
where the plated-face reference puts its own face-plate seam.

The joint is four Ø5.2 dowel bores in pads that straddle the plane, each
placed by raycasting the inner surface so it sits on wall rather than in mid
air. The pads are Ø16 against a 4 mm wall, which is what makes a 5 mm hole
possible at all. **There are no screws across this joint yet**, and that is
deliberate rather than forgotten: the obvious thing to clamp both halves to
is the neck plate, and there is no neck. Pins and four M3s through a neck
plate is the intended end state; pins and a bead of glue is what this prints
as today.

### The check that should have existed from day one — 13 Aug 2026

`fit_layout.collide()`. Until this was written, `verify()` was the only check
in the project and it asked exactly one question: *is this part inside the
skin?* It answered that correctly every time. Nobody had asked the other
question, which is whether the parts pass through **each other**, and while
`verify()` was reporting CLEAN the eye bezel was running through the forehead
casing, two cable anchors were running through the ear hubs, and every boss
in the head was pushing 1.5 mm into the part it was supposed to be holding.
It took someone looking at the screen to notice.

Two things make it useful rather than noisy:

**Touching is not a fault.** Most of these parts are meant to touch — a board
on its standoffs, a tray on its rails, a ring in its recess. `CONTACT` names
those pairs, and anything not on it has to clear.

**Inside-ness is ray parity across three directions, not the sign of the
nearest surface normal.** The normal test is the obvious one and it is wrong
on any part that is not convex: asked whether the eyeball is inside the eye
bezel, it finds the nearest surface is the ring's *bore*, whose normal points
inward, and reports 21.8 mm of interference through a 2.2 mm gap. And one ray
is not enough on a 180k shell covered in seam grooves — a ray that grazes a
crease miscounts its crossings, and a single miscount flips the verdict. With
one direction it put the forehead casing 33.8 mm inside the skull. Three
directions and a majority vote, and every number it prints is one you can act
on.

The first honest run found eleven **sealed voids**, one per boss: each pilot
hole started 1 mm proud of a boss that started 1.5 mm proud of the part, so
the hole was entirely enclosed in material. Not a hole at all — a bubble no
screw could reach, and eleven loose islands in a mesh that was otherwise
manifold. Both numbers are now measured from the part's mounting face: the
post starts on it, the pilot starts 4 mm short of it.

### Blender's boolean solver — 13 Aug 2026

Worth writing down, because two rules in this repo looked like laws and were
only workarounds for one solver.

`EXACT` discarded the whole shell whenever it met the solidified lid creases
— 98k vertices in, 1.6k out — which is why the eye cuts ran on `FLOAT`. Then
the brow-band seam subdivided the forehead and `EXACT` started throwing the
shell away on the camera bore too, 138k in and 850 out, with nothing wrong
with either input. In `head_mounts` it deleted a 3688-vertex panel to nothing
against a cutter whose countersink shared a cylindrical surface with its own
clearance hole, reduced the ear hub to 110 vertices, and turned a 135k head
into 2016 on a union with twelve disjoint posts.

**Blender 5's `MANIFOLD` solver takes all of it.** It wants closed manifold
inputs, which everything here is: Solidify with a rim closes every boundary
the cleaning leaves, and the shell tests at zero boundary and zero
non-manifold edges. All seven styling cuts now run on one solver, and faster.

Three more traps, all silent, all now guarded in code:

- A boolean whose cutter object the depsgraph has not seen yet evaluates
  against nothing. `INTERSECT` returns empty and `DIFFERENCE` returns the
  target untouched. Call `bpy.context.view_layer.update()` before every bake.
- A boolean on an object inside a hidden or excluded collection bakes the
  mesh it already had and reports success. The forehead casing and the Pi
  tray live in `HUMALIEN`, which gets hidden any time somebody wants a clean
  look at the shell, and both edits to them did nothing until that was
  noticed.
- A boolean against an *empty* cutter does not no-op. It returns rubble.
- Batching cutters into one mesh is fine while they are **disjoint**. Two
  interpenetrating solids in a single cutter is not: the eye bezel's bore and
  the trim box shared a cutter, and the bore came back at r13.4 instead of
  r17.8 — straight through the eyeball. Batch what does not touch; run
  overlapping cutters one at a time.

### Running the head pipeline

Four scripts, in order, in one Blender session:

```python
ns = {}
for f in ("head_style", "head_mounts"):
    exec(compile(open(r"C:\humalien\humalien\cad\%s.py" % f).read(), f, "exec"), ns)
    ns["build"]() if f == "head_style" else ns["build"](ns["S"], ns["eye_axis"])

fl = {}
exec(compile(open(r"C:\humalien\humalien\cad\fit_layout.py").read(), "fl", "exec"), fl)
fl["build"](); fl["verify"]()

exec(compile(open(r"C:\humalien\humalien\cad\head_split.py").read(), "hs", "exec"), ns)
ns["build"]()
```

About 20 seconds end to end. `head_style` regenerates from `HEAD_REF` every
run, so it is still the non-destructive layer: move a number in `S`, re-run
the four, and everything downstream re-measures itself against the new shell.


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
drop them. `forehead_casing`, `pca9685_mount`, `coupon_neopixel12` and
`cable_anchor` come out fully manifold — `forehead_casing` and `pca9685_mount`
carry labels too, so it is not simply "engraved parts are dirty"; it depends on
how the glyph outlines happen to fall against the geometry underneath. The
labels are worth keeping either way — a coupon with four unmarked pockets is not
a measuring tool.
