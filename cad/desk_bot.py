"""Humalien Desk - first massing and packaging study for the desktop assistant.

A round body, a round head on a headphone-style yoke, two single-axis arms,
and two ring eyes that are LIGHT ONLY - no eye mechanism at all.  Four MG90S
in the whole robot, out of the twelve on the bench.

    pan     one servo on a shelf inside the shoulder, output up.  The yoke
            clamps its spline.  The yoke's flange bears on DB_top over a
            21 mm annulus, so THE SERVO NEVER CARRIES THE HEAD'S WEIGHT - it
            only supplies torque.  An MG90S output bearing will not take
            ~120 g of head as a thrust load, and this annulus is what stops
            it ever seeing one.
    nod     one servo INSIDE the head, on the head's own centre line.  The
            head is a sphere turning about its own centre, so nod is
            weight-neutral AND cannot collide with the body at any angle -
            every point of a sphere stays HEAD_R from the axis.
    arms    one servo each, axis left-right, arm swings fore and aft.  The
            blade is jogged outboard to |x| 86 so it clears the O160 waist.

Eyes are 2x NeoPixel Ring 12B behind a printed diffuser.  Lighting an ARC of
the twelve rather than the whole ring reads as a pupil looking that way, so
gaze direction costs zero servos and zero linkages.  That is the point of
this pivot: the mechanism that killed eye rig 01 is deleted, not redesigned.

Assembly order, which is the thing that has actually failed twice here:

    1.  nod servo slides into its pocket in the head shell.
    2.  bracket + servo go in through the O92 face opening and take two
        screws along +Y, driven straight through that same opening.  No
        screw in this build is driven along an axis you cannot see down.
    3.  head drops between the yoke arms from above - 112 wide into a 116
        gap, 2 mm a side.
    4.  DB_cplr enters from the RIGHT, through the yoke bore, onto the servo
        spline; its shoulder traps in the bore so it is the bearing too.
        DB_pivot enters from the LEFT.  Both insert radially, both have a
        clear driver path from outside.
        (Eye rig 01 died on a continuous shaft through a CLOSED bore that
        needed 23 mm of axial slide against 0.50 available.  This is that
        same joint, built as two parts inserted from opposite ends.)
    5.  arm servos slide into their pockets from inside the dome; their two
        screws come in from OUTSIDE the shoulder, so the heads show as two
        small dots a side.  That is the price of a slide-in pocket on a
        horizontal shaft - an MG90S is always pierced parallel to its own
        output, so the driver has to come from where the shaft points.
    6.  face plate last, over the rings.

Power is two cords out of the back panel, on purpose and not by accident:
the Alitove goes to the barrel jack and feeds ONLY the PCA9685 screw
terminals, and the Pi takes its own USB-C brick through the port window.
The servo rail and the Pi rail never touch except at ground.

Print order, which is Pat's and is the right way round: DB_chassis FIRST,
alone.  It carries the Pi 5, the PCA9685 and both speaker boxes and it stands
on its own feet, so the whole electrical build can be assembled and run on the
bench before any shell geometry is committed to.  Shell, arms and head follow
once the chassis is proven.

Print orientation, all support-free:
    DB_chassis  base down.  Baffles and posts stand vertically off the plate,
                so there is no overhang anywhere in it.
    DB_shell  base down.  Steepest flare is 40 deg off vertical at the foot,
              inside what an A1 bridges dry.
    DB_dome   also base down: it only ever tapers INWARD going up, and its
              cavity has no roof because DB_top is a separate flat ring.
    DB_top    flat.  It is the thrust bearing face, so it wants to be a
              first-layer surface anyway.

    import desk_bot; desk_bot.build(); desk_bot.fits()
    desk_bot.pose(pan=30, nod=-12, arm_l=40, arm_r=-10)

Millimetres throughout.  +Y is the direction the face looks.
"""
import math
import bpy
import bmesh
from mathutils import Vector, Matrix

COLL = "DESK_BOT"
SMOOTH_ANGLE = 35.0
SEGS = 64                       # shells, and anything on the silhouette
FINE = 48                       # holes a finger or an eye finds
PILOT = 20                      # screw pilots - round enough at O2.5

# ---------------------------------------------------------------- the body
# Outer surface as (radius, z), bottom to top.  O160 at the waist.  The body
# is a solid of revolution about Z, which is what lets fits() answer "is this
# board inside the shell" analytically instead of by ray cast - and ray casts
# fired down an axis have lied to this project before.
WALL = 3.0
# O190, up from 180.  Not styling: the half-width has to carry the Pi (42.5)
# plus a gap, plus 21 of speaker box, plus the baffle, and the baffle's own
# corners have to stay inside the barrel out at y 53.  At 180 that closed to
# 0.2 mm, which is not a clearance, it is a coincidence.
# There is now a straight band at r 88 over z 76..90.  A cone has no place
# to put a flat-faced boss: over the 22 mm a servo housing needs, the old
# profile lost 27 mm of radius, so the housing was buried at one end and 14 mm
# proud at the other.  A short cylindrical shoulder fixes that and reads as a
# shoulder rather than as a lump on a cone.
BODY_PROF = [(89.0, 0.0), (94.0, 7.0), (95.0, 20.0), (95.0, 58.0),
             (94.0, 66.0), (94.0, 70.0), (89.0, 74.0), (88.0, 76.0),
             (88.0, 90.0), (82.0, 97.0), (70.0, 104.0), (52.0, 112.0)]
INNER_PROF = [(r - WALL, max(z, WALL)) for r, z in BODY_PROF] + [(49.0, 260.0)]
SPLIT_Z = 66.0                  # shell / dome parting line
BODY_TOP = 112.0

# ------------------------------------------------- the shell/dome joint
# There was no joint.  SPLIT_Z was one plane cut twice - everything above it
# off the shell, everything below it off the dome - leaving a flat 3 mm
# annulus, ID 182, with NOTHING holding it, under a dome that carries both
# arm servos, the pan shelf and the whole head.  The first arm swing walks
# it off.
#
# Three ribs stand up inside the shell and 4 mm into the dome's mouth: they
# locate it on three points, and one radial M3 each holds it down.  The
# screws go in horizontally from outside, which is the ONLY direction that
# stays reachable on the assembled robot - a vertical screw at this radius
# has the dome's own inner wall closing over it by z 104, and the top
# opening is only O104.  That is the eye-rig-01 trap and it is why these
# are not vertical.
#
# The three angles are not styling either.  A rib has to miss the speaker
# grilles (|x| >= 71 below z 67) and the rear access cut (|x| <= 46 behind
# y -58), and 90/225/315 is the set that clears both with the ribs still
# symmetric about the face.
JOIN_A = [math.radians(a) for a in (90.0, 225.0, 315.0)]
JOIN_R = (82.0, 90.0)           # rib inner face, and the register pad OD.
                                # Flat pad, so its corners sit at 90.45 -
                                # 0.55 under the dome's 91.0 bore
JOIN_W = 9.0                    # half width
JOIN_Z = (52.0, 70.0)           # rib foot, and 4 mm proud of the split
JOIN_SCREW_Z = 68.0             # mid-pad, 2 mm above the parting line
JOIN_PILOT, JOIN_CLEAR, JOIN_CBORE = 2.5, 3.4, 6.0

TOP_Z = (112.0, 116.0)          # DB_top, the flat bearing ring
TOP_R = (31.0, 52.0)            # ID 62 for the collar, OD 104

# ----------------------------------------------------------- the wire way
# Servo and NeoPixel wires have to get from the chassis into the head, and
# the parting line is wide open, so the only real obstacles are the pan
# shelf and DB_top.  The shelf already has its two O26 holes at (0, +-38);
# this is the rest of the run, and it is deliberately all at the REAR so
# the whole thing is one straight vertical drop at r 44.5, 270 deg.  Rear
# because that is where a wire is allowed to be seen; the front is the face.
#
# The slot's radius is pinned from both sides: outside the yoke flange's
# O84, so the flange sweeps PAST it at any pan angle instead of closing it,
# and inside DB_top's O97 spigot, so it does not break the register into
# the dome.  That leaves a 6.5 mm band and the slot takes 5 of it.  It also
# misses all three O3.2 mounting holes - see _top, which had to give up
# 270 deg to make room and now sits at 90/210/330.
WIRE_R, WIRE_D = 44.5, 5.0
WIRE_A = [math.radians(230.0 + 10.0 * i) for i in range(9)]
# Out of the head at the REAR of its underside, onto the yoke flange.  The
# flange turns WITH the head, so nothing in this run crosses the nod axis;
# the only relative movement is at DB_top, and the slack there covers it.
WIRE_HEAD_D, WIRE_HEAD_Y = 12.0, 18.0

# ------------------------------------------------------------- the servos
# MG90S / SG90.  Local frame: origin on the output axis in the plane of the
# case top, +x running along the case away from the shaft.
SV_BODY_X, SV_BODY_Y, SV_BODY_Z = (-5.9, 16.9), (-6.1, 6.1), (-22.7, 0.0)
SV_EAR_X, SV_EAR_Z = (-10.6, 21.6), (-7.67, -5.17)      # ears, 2.5 thick
SV_HOLE_X = (-8.274, 19.726)    # 28.0 apart, the SG90 standard
SV_HUB_D, SV_HUB_Z = 5.9, 4.0
SV_FIT = 0.6                    # slip fit round the case.  0.4 is inside
                                # what this printer holds; a servo you have
                                # to force into a pocket is a servo you
                                # cannot get back out.

# MEASURED in grey PLA with the archive's bore_ladder(), not guessed - 4.7
# had to be forced.  Specific to BOTH printer and filament: re-run it on a
# change of either.
HORN_BORE = 4.95
FIT_MIN = 0.15                  # 0.1 a side binds solid in PLA.  This is the
                                # floor, and load-bearing joints want more.

# ---------------------------------------------------------------- the head
HEAD_R = 56.0
HEAD_WALL = 2.5
HEAD_Z = 182.0                  # head centre == nod axis
FACE_Y = 32.0                   # the flat, which is also the O92 face opening
FACE_T = 4.5                    # 3.4 of ring pocket + 1.1 of diffuser
YOKE_X = (58.0, 64.0)           # yoke arm inner and outer faces
NOD_BORE = 8.0
EYE_X, EYE_Z = 21.0, 6.0        # eyes set a little high reads friendly
RING_OD, RING_ID, RING_T = 37.0, 23.3, 3.2      # NeoPixel Ring 12B

# ---------------------------------------------------------------- the arms
# The arm servo used to stand with its long axis VERTICAL.  Its ears span
# 32.2 mm, the mount boss padded that to 38, and the dome only exists over
# z 66..100 - so the boss ran off both ends of the part and the case pushed
# out through the shoulder skin, where the dome has already narrowed to r 61.
# Laid on its side the servo only needs 12.2 mm of height, which the shoulder
# has in abundance, and it drops to 78 where the dome is still 88 wide.
ARM_AX, ARM_AZ = 90.0, 82.0     # the shoulder face, and the arm axis
SHO_X = (66.0, 90.0)            # housing: inboard end, and the face.  24
                                # deep for a 22.7 case - 23 left 0.2 short
# SHO_R was 9.0.  The ear slot's far corners sit at y +-22.2, and at the
# slot's z extremes a 9.0 cap only reaches 22.01 - so 0.19 mm of the cut fell
# outside the boss, and since the corner is also at r 88.27 against an 88.0
# skin, it came out as a small hole on each side by the arms.  10.0 reaches
# 23.42 and covers it.  ARM_AZ - SHO_R is still 6 mm clear of the split.
SHO_Y, SHO_R = 16.0, 10.0       # obround - box +-SHO_Y, capped by SHO_R ends
SHO_SCREW, SHO_CBORE = 1.7, 4.2   # M2 into PLA, and a head recess
SHO_CBORE_X = 85.0              # head sits here, just clear of the ear at 84.8
ARM_BLADE_X = 110.0             # 15 mm outboard of the O190 waist: at 8
                                # they vanished into the silhouette
ARM_W, ARM_T, ARM_L = 28.0, 12.0, 60.0
ARM_REST = -8.0
ARM_RANGE = (-20.0, 75.0)       # +ve swings FORWARD, same sign both arms
PAN_RANGE = (-80.0, 80.0)
NOD_RANGE = (-22.0, 22.0)

# ------------------------------------------------------- bought-in hardware
# Every number tagged MEASURE is a guess this file is making.  They are the
# only guesses in it, and each is one caliper reading away from being a fact.
PCB_T = 1.6
# The Pi is turned 90 deg from the first pass: its USB-C and HDMI live on one
# LONG edge, and that edge now faces the back panel so the power brick's cord
# has somewhere to go.  Ethernet and the USB-A stacks face a side, unused.
PI_XY = (85.0, 56.0)            # 85 across, 56 fore-aft, USB-C edge REARWARD
PI_Z = 12.0                     # Pi 5 PCB underside.  No UPS under it now.
PI_TALL = 17.0                  # USB-A stack above the PCB
HAT_CLR = 17.5                  # MEASURE: WM8960 PCB above the Pi PCB.  This
HAT_XY = (65.0, 56.5)           # MUST beat PI_TALL or the HAT lands on the
HAT_TALL = 10.0                 # USB stack.  fits() checks it.
SHELF_Z = (92.33, 96.33)        # pan servo ears rest ON this; screws go DOWN
PAN_TOP = 104.0                 # so the case top lands here
# Waveshare 8 ohm 5W speaker set, from the datasheet, not from guessing:
# 100 x 45 x 21 with FOUR 6.5 mm mounting holes on 92 x 36 centres.  Each box
# is sealed and carries its own driver AND its own passive radiator on one
# face, so no enclosure has to be designed around them at all.
#
# 6.5 is far too big to be a screw hole and that is the point - these take a
# ZIP TIE straight through.  Every mount here is a tie, not a fastener.
SPK_BOX = (21.0, 100.0, 45.0)   # depth X, length Y, height Z
SPK_FACE = 68.0                 # the box's front face
SPK_Z = 42.0                    # centre height, in the straight barrel
SPK_DRV_D, SPK_PR_D = 38.0, 38.0
SPK_PITCH = 25.0                # driver and radiator centres, off box centre
SPK_TAB_D = 6.5                 # the speaker's own hole
SPK_TAB_AT, SPK_TAB_Z = 46.0, 18.0          # 92 apart, 36 apart

# The baffle gets a clearance hole behind each of those, plus a return slot
# inboard of it: the tie goes out through the speaker's hole, back in through
# the slot, and cinches behind the baffle.  A tie through one aligned hole is
# a loop that clamps nothing.
TIE_D = 7.0                     # round end, behind the speaker's own O6.5
TIE_SLOT_H = 3.4                # 4.8 x 1.6 tie, with room to thread by hand
TIE_OUT = 5.0                   # how far the keyhole runs OUTBOARD
TIE_EDGE = 4.0                  # material left past the end of the slot
# Two ROUND openings, not one rectangle: a rectangle wide enough for both
# cones eats the corners the tie holes have to live in.
BAFFLE_D = 42.0
PCA_XY = (62.0, 26.0)           # front, low, under the servos it drives
FAN_D, FAN_T = 30.0, 7.0
# The SHT41 reads the ROOM, so it is the one board whose position is set by
# physics rather than packing.  It goes on the chassis at the FRONT, low, in
# the intake, behind its own vent slots - as far from the Pi as the body
# allows and upstream of the fan.  On the rear panel it would have sat in the
# exhaust and reported the Pi's waste heat as room temperature.
SHT_XY = (25.5, 17.6)           # STEMMA QT outline, 1.0 x 0.7 inch
# FOUR corner holes, not two - the photo shows one at each corner and the
# first pass had a pair on one axis.  The SPACING is still MEASURE: Adafruit
# do not publish it and it is ten seconds with calipers.
SHT_HOLE = (20.3, 12.4)
SHT_MNT_Y = 58.0                # the tab it stands on, on DB_chassis
SHT_Z = (14.0, 31.6)
JACK_D, JACK_L = 11.0, 20.0     # the DC pigtail, for the Alitove
REAR_Y = (-64.0, -60.0)         # the service panel, part of DB_chassis
REAR_X, REAR_Z = 44.0, (7.0, 64.0)          # was 34, which put two thirds
                                # of the USB-C inlet behind solid panel.  The
                                # Pi's USB-C sits 11.2 mm in from the far end
                                # of its long edge, i.e. x -35.8..-26.8 here,
                                # so the window has to reach -40 and the panel
                                # has to be wider than the window.          # lands ON the chassis plate:
                                # the panel is part of DB_chassis now, so the
                                # jack, the fan and the port window all arrive
                                # already aligned to the boards behind them

TRAY_Z = (4.0, 8.0)

HEAD_PX = ("PX_ring", "PX_eye")  # ride the nod axis, not the body shell
# The speakers are SUPPOSED to come through the wall - that is what the baffle
# opening is.  Testing them against the round profile just reports the design
# working.  They get their own check instead, against the hole and the tabs.
BAFFLE_PX = ("PX_spk",)


# ----------------------------------------------------------------- shapes
def _box(bm, x0, x1, y0, y1, z0, z1):
    v = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    bmesh.ops.scale(bm, verts=v, vec=(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)))
    bmesh.ops.translate(bm, verts=v,
                        vec=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    return v


def _rodx(bm, r, x0, x1, cy, cz, segs=PILOT):
    v = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                              radius1=r, radius2=r, depth=abs(x1 - x0))["verts"]
    bmesh.ops.rotate(bm, verts=v, cent=(0, 0, 0),
                     matrix=Matrix.Rotation(math.radians(90), 3, "Y"))
    bmesh.ops.translate(bm, verts=v, vec=Vector(((x0 + x1) / 2, cy, cz)))
    return v


def _rody(bm, r, y0, y1, cx, cz, segs=PILOT):
    v = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                              radius1=r, radius2=r, depth=abs(y1 - y0))["verts"]
    bmesh.ops.rotate(bm, verts=v, cent=(0, 0, 0),
                     matrix=Matrix.Rotation(math.radians(-90), 3, "X"))
    bmesh.ops.translate(bm, verts=v, vec=Vector((cx, (y0 + y1) / 2, cz)))
    return v


def _rodz(bm, r, z0, z1, cx, cy, segs=PILOT):
    v = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                              radius1=r, radius2=r, depth=abs(z1 - z0))["verts"]
    bmesh.ops.translate(bm, verts=v, vec=Vector((cx, cy, (z0 + z1) / 2)))
    return v


def _conez(bm, r0, r1, z0, z1, cx, cy, segs=PILOT):
    """Truncated cone on Z.  r0 at z0, r1 at z1."""
    v = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                              radius1=r0, radius2=r1,
                              depth=abs(z1 - z0))["verts"]
    bmesh.ops.translate(bm, verts=v, vec=Vector((cx, cy, (z0 + z1) / 2)))
    return v


def _boxr(bm, r0, r1, half_w, z0, z1, ang):
    """A block lying along the RADIAL direction at `ang`, from r0 out to r1."""
    v = _box(bm, r0, r1, -half_w, half_w, z0, z1)
    bmesh.ops.rotate(bm, verts=v, cent=(0, 0, 0),
                     matrix=Matrix.Rotation(ang, 3, "Z"))
    return v


def _rodr(bm, r, r0, r1, ang, cz, segs=PILOT):
    """A rod lying along the RADIAL direction at `ang`, r0 to r1, at height cz.

    Every screw into the shell/dome joint is radial, and only two of the
    three angles land on an axis, so these cannot be _rodx.
    """
    v = _rodx(bm, r, r0, r1, 0.0, cz, segs)
    bmesh.ops.rotate(bm, verts=v, cent=(0, 0, 0),
                     matrix=Matrix.Rotation(ang, 3, "Z"))
    return v


def _ball(bm, r, cx, cy, cz, segs=64):
    v = bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=segs // 2,
                                  radius=r)["verts"]
    bmesh.ops.translate(bm, verts=v, vec=Vector((cx, cy, cz)))
    return v


def _revolve(bm, prof, segs=SEGS):
    """Lathe `prof` [(r, z), ...] about Z, capping both ends with a fan.

    Caps get a centre vertex instead of one n-gon: a 64-gon survives
    recalc_face_normals fine, but the EXACT boolean solver is happier with
    triangles and these shells are nothing but booleans."""
    rings = [[bm.verts.new((r * math.cos(2 * math.pi * i / segs),
                            r * math.sin(2 * math.pi * i / segs), z))
              for i in range(segs)] for r, z in prof]
    for a, b in zip(rings, rings[1:]):
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((a[i], a[j], b[j], b[i]))
    for ring, z, up in ((rings[0], prof[0][1], False),
                        (rings[-1], prof[-1][1], True)):
        c = bm.verts.new((0.0, 0.0, z))
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((c, ring[i], ring[j]) if up else (c, ring[j], ring[i]))


def _frame_m(shaft, body):
    """Orientation with local z on `shaft` and local x on `body`."""
    z = Vector(shaft).normalized()
    x = Vector(body)
    x = (x - z * x.dot(z)).normalized()
    return Matrix((x, z.cross(x), z)).transposed().to_4x4()


def _sv_m(p, shaft, body):
    return Matrix.Translation(Vector(p)) @ _frame_m(shaft, body)


def _servo(bm, m, fit=0.0):
    """Case, ears and hub as one overlapping solid, placed by `m`."""
    v = _box(bm, SV_BODY_X[0] - fit, SV_BODY_X[1] + fit,
             SV_BODY_Y[0] - fit, SV_BODY_Y[1] + fit,
             SV_BODY_Z[0] - fit, SV_BODY_Z[1])
    v += _box(bm, SV_EAR_X[0] - fit, SV_EAR_X[1] + fit,
              SV_BODY_Y[0] - fit, SV_BODY_Y[1] + fit,
              SV_EAR_Z[0] - fit, SV_EAR_Z[1] + fit)
    if fit == 0.0:
        v += _rodz(bm, SV_HUB_D / 2, 0.0, SV_HUB_Z, 0.0, 0.0)
    bmesh.ops.transform(bm, matrix=m, verts=v)


# ------------------------------------------------------------ scene plumbing
def _mat(name, rgba, rough=0.5, emit=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    if b:
        b.inputs["Base Color"].default_value = rgba
        b.inputs["Roughness"].default_value = rough
        for k in ("Emission Color", "Emission"):
            if k in b.inputs:
                b.inputs[k].default_value = rgba
        if "Emission Strength" in b.inputs:
            b.inputs["Emission Strength"].default_value = emit
    m.diffuse_color = rgba
    return m


def _dejunk(bm, name, frac=1e-3):
    """Delete shells the solver left floating loose inside the part.

    A DIFFERENCE that passes clean through thin material sometimes comes back
    with the cut cylinder's own wall as a separate closed shell.  Four were
    adrift in the dome - two in the pan shelf, two in the right shoulder -
    each one exactly where a servo screw goes, and none of them shows up
    until the part is sliced.  Nothing under `frac` of the biggest shell by
    bounding box is a feature of a 190 mm robot.
    """
    seen, isl = set(), []
    for v in bm.verts:
        if v in seen:
            continue
        stack, grp = [v], []
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            grp.append(x)
            for e in x.link_edges:
                o = e.other_vert(x)
                if o not in seen:
                    stack.append(o)
        isl.append(grp)
    if len(isl) < 2:
        return 0

    def vol(g):
        c = [v.co for v in g]
        return ((max(v.x for v in c) - min(v.x for v in c) + 0.1)
                * (max(v.y for v in c) - min(v.y for v in c) + 0.1)
                * (max(v.z for v in c) - min(v.z for v in c) + 0.1))

    big = max(vol(g) for g in isl)
    junk = [v for g in isl if vol(g) < big * frac for v in g]
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
        print("   %s: dropped %d loose verts of boolean junk" % (name, len(junk)))
    return len(junk)


def _seal(bm, name):
    """Close any boundary loop left in a finished part.

    A part with a boundary edge is not a solid, and every part in this file
    gets printed.  These are nearly always slivers: EXACT drops a facet where
    two surfaces meet at a glancing angle, and five of them have been sitting
    in the shell's floor since long before the joint went in - one per intake
    hole, 0.2 mm wide, invisible in the viewport and fatal to a slicer.

    It reports the BIGGEST loop it closed on purpose.  Sealing a 3-edge
    sliver is a repair; sealing a 24-edge loop means something upstream tore
    a real hole and the seal is hiding it.  Watch that number.
    """
    bnd = [e for e in bm.edges if len(e.link_faces) < 2]
    if not bnd:
        return 0
    bset = set(bnd); seen = set(); big = 0
    for e in bnd:
        if e in seen:
            continue
        stack, n = [e], 0
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            n += 1
            for v in x.verts:
                for e2 in v.link_edges:
                    if e2 in bset and e2 not in seen:
                        stack.append(e2)
        big = max(big, n)
    made = len(bmesh.ops.holes_fill(bm, edges=bnd, sides=0).get("faces", []))
    left = sum(1 for e in bm.edges if len(e.link_faces) < 2)
    print("   %s: sealed %d face(s) over %d open edges, biggest loop %d, %d left"
          % (name, made, len(bnd), big, left))
    return made


def _obj(name, coll, parts, cuts=(), mat=None, loc=(0, 0, 0),
         add=(), bore=()):
    """Four phases, in order: union `parts`, subtract `cuts`, union `add`,
    subtract `bore`.

    The last two exist because a hollow shell is (outer - inner), and ANY
    internal feature unioned before that subtraction is deleted by it.  The
    dome's servo shelf was in `parts` for a week and never once appeared in
    the mesh; the shelf ribs survived only where they poked out through the
    skin, which is exactly what they looked like.  Internal geometry goes in
    `add`, after the cavity has been cut.
    """
    obs = []
    ops = ([None] + ["UNION"] * (len(parts) - 1)
           + ["DIFFERENCE"] * len(cuts) + ["UNION"] * len(add)
           + ["DIFFERENCE"] * len(bore))
    for i, fn in enumerate(list(parts) + list(cuts) + list(add) + list(bore)):
        bm = bmesh.new()
        fn(bm)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new("%s_f%02d" % (name, i))
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(me.name, me)
        coll.objects.link(o)
        obs.append(o)
    base = obs[0]
    bpy.context.view_layer.objects.active = base
    for i, o in enumerate(obs[1:], start=1):
        m = base.modifiers.new(type="BOOLEAN", name="b%02d" % i)
        m.object, m.solver = o, "EXACT"
        m.operation = ops[i]
        # use_self stays ON.  It was turned off on 30 Aug 2026 on the
        # reasoning that no operand self-intersects any more - which is true,
        # and was still wrong.  The flag is not only about the operand: EXACT
        # uses it for the ACCUMULATED base mesh too, and the base goes through
        # states no single operand describes.  Measured cost of turning it
        # off: DB_dome came back with 379 open edges and DB_shell with 45.
        # The speed came from collapsing the modifier_apply loop below, not
        # from this.  Leave it alone.
        m.use_self = True
        m.use_hole_tolerant = True
    # Evaluate the stack ONCE rather than calling modifier_apply per modifier.
    # The boolean work is identical - same modifiers, same order - but every
    # bpy.ops call was forcing a full depsgraph update of the whole scene and
    # an undo push, and DB_chassis alone stacks 55 of them.
    if len(obs) > 1:
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(base.evaluated_get(dg))
        base.modifiers.clear()
        stale, base.data = base.data, me
        bpy.data.meshes.remove(stale)
    for o in obs[1:]:
        bpy.data.objects.remove(o, do_unlink=True)
    bm = bmesh.new()
    bm.from_mesh(base.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-4, edges=bm.edges[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    _dejunk(bm, name)
    if _seal(bm, name):
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(base.data)
    bm.free()
    base.name = base.data.name = name
    if mat:
        base.data.materials.clear()
        base.data.materials.append(mat)
    piv = Vector(loc)
    for v in base.data.vertices:
        v.co -= piv
    base.location = piv
    return base


def _prof_r(prof, z):
    """Radius of a lathed profile at height z, or None if z is off the ends."""
    if z < prof[0][1] - 1e-9 or z > prof[-1][1] + 1e-9:
        return None
    for (r0, z0), (r1, z1) in zip(prof, prof[1:]):
        if z0 - 1e-9 <= z <= z1 + 1e-9:
            if abs(z1 - z0) < 1e-9:
                return max(r0, r1)
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return prof[-1][0]


# ------------------------------------------------------------------- parts
def _shell(coll, mat):
    """Body, floor to the parting line.  Side grilles, rear access, feet."""
    cuts = [lambda bm: _revolve(bm, INNER_PROF),
            lambda bm: _box(bm, -120, 120, -120, 120, SPLIT_Z, 260)]
    # side-firing speaker grilles, five slots a side
    # Each speaker fires through its own opening; its corner tabs bolt to
    # DB_chassis behind, not to the shell, so the shell carries no load.
    for sx in (1, -1):
        cuts.append(lambda bm, s=sx: _box(
            bm, s * (SPK_FACE + 3.0), s * 140.0, -54.0, 54.0,
            SPK_Z - 25.0, SPK_Z + 25.0))
    # rear access: ports, cables, and the fan's exhaust all leave here
    cuts.append(lambda bm: _box(bm, -46, 46, -120, -58, 12, 60))
    # The other half of the chassis mount: clearance and a counterbore, so
    # the screw head finishes flush with the floor and the robot still sits
    # flat on the desk.
    for a in CH_MOUNT_A:
        cx, cy = CH_MOUNT_AT * math.cos(a), CH_MOUNT_AT * math.sin(a)
        cuts.append(lambda bm, x=cx, y=cy: _rodz(bm, 1.7, -1.0, WALL + 1.0,
                                                 x, y))
        cuts.append(lambda bm, x=cx, y=cy: _rodz(bm, 3.2, -1.0, 1.6, x, y))
    # Front intake, straight onto the SHT41.  These are the slots that make
    # the humidity reading mean anything: without them it measures the inside
    # of a sealed box with a Pi 5 in it.
    for i in range(5):
        zc = 13.0 + i * 5.0
        cuts.append(lambda bm, z=zc: _box(bm, -26.0, 26.0, 60.0, 140.0,
                                          z - 1.5, z + 1.5))
    # intake ring under the foot, so the fan has somewhere to pull from
    for i in range(8):
        a = 2 * math.pi * i / 8
        cuts.append(lambda bm, a=a: _rodz(
            bm, 4.0, -1.0, 5.0, 34 * math.cos(a), 34 * math.sin(a)))
    # The dome joint.  These go in `add`, not `parts`: the pads stand 4 mm
    # proud of SPLIT_Z and the parting cut in `cuts` would eat them whole.
    add, bore = [], []
    for a in JOIN_A:
        # The rib and the pad are deliberately DIFFERENT on every axis:
        # 82..93 vs 83..90 radially, half-width 9 vs 8, and z 52..64 vs
        # 60..70.  Measured on 30 Aug 2026 with the shell built both ways -
        # ribs on, 85 open edges; ribs off, 15 - and every one of those 70
        # traced to the two boxes sharing faces.  Both started at r 82 and
        # both used JOIN_W, so over their overlap the two side faces and the
        # inner face were exactly coplanar, and EXACT drops coplanar unions.
        # Overlap them in VOLUME, never on a face.
        add.append(lambda bm, a=a: _boxr(bm, JOIN_R[0], 93.0, JOIN_W,
                                         JOIN_Z[0], SPLIT_Z - 2.0, a))
        add.append(lambda bm, a=a: _boxr(bm, JOIN_R[0] + 1.0, JOIN_R[1],
                                         JOIN_W - 1.0, SPLIT_Z - 6.0,
                                         JOIN_Z[1], a))
        bore.append(lambda bm, a=a: _rodr(bm, JOIN_PILOT / 2, JOIN_R[0] - 1.0,
                                          JOIN_R[1] + 1.0, a, JOIN_SCREW_Z))
    return _obj("DB_shell", coll, [lambda bm: _revolve(bm, BODY_PROF)], cuts,
                mat, add=add, bore=bore)


def _dome(coll, mat):
    """Shoulder.  Carries the pan shelf and both arm housings.

    Note the phase each feature is in: the skin is parts/cuts, everything
    INSIDE it is add/bore.  Put the shelf in `parts` and the cavity cut eats
    it whole.
    """
    parts = [lambda bm: _revolve(bm, BODY_PROF)]
    cuts = [lambda bm: _revolve(bm, INNER_PROF),
            lambda bm: _box(bm, -140, 140, -140, 140, -20, SPLIT_Z),
            lambda bm: _box(bm, -140, 140, -140, 140, BODY_TOP, 260)]

    # The shelf is a CONE, not a disc: over its 4 mm of height the wall loses
    # 3.4 mm of radius, so a flat disc meets it on one thin line and a cone
    # meets it all the way round.
    add = [lambda bm: _conez(bm, 84.0, 80.6, SHELF_Z[0], SHELF_Z[1], 0, 0,
                             SEGS)]
    for sx in (1, -1):
        add.append(lambda bm, s=sx: _box(
            bm, s * SHO_X[0], s * SHO_X[1], -SHO_Y, SHO_Y,
            ARM_AZ - SHO_R, ARM_AZ + SHO_R))
        for ey in (-SHO_Y, SHO_Y):
            add.append(lambda bm, s=sx, y=ey: _rodx(
                bm, SHO_R, s * SHO_X[0], s * SHO_X[1], y, ARM_AZ, FINE))

    bore = _svpocket_ops(_sv_m((0, 0, PAN_TOP), (0, 0, 1), (0, 1, 0)), "-y")
    bore += [lambda bm: _rodz(bm, 13.0, SHELF_Z[0] - 1, SHELF_Z[1] + 1, 0, 38,
                              FINE),
             lambda bm: _rodz(bm, 13.0, SHELF_Z[0] - 1, SHELF_Z[1] + 1, 0, -38,
                              FINE)]
    # Arm servos slide into the housings from inboard and are held by two
    # SCREWS, not by anything springy: M2 in from the shoulder face, head
    # counterbored below the surface, through the ear, into solid housing
    # behind it.  The arm hub covers both heads.
    for sx in (1, -1):
        bore += _svpocket_ops(_arm_m(sx), "-z")
        bore.append(lambda bm, s=sx: _rodx(          # spline / hub clearance
            bm, 5.5, s * 80.0, s * 104.0, 0.0, ARM_AZ, FINE))
        # The O1.7 pilot is NOT cut here.  _svpocket_ops already drills both,
        # on this exact axis, and runs them out past the face to |x| 104.
        # Cutting them a second time put two cylinders of identical diameter
        # and different segment counts - 20 from the pocket, 48 from FINE -
        # on one axis, 0.01 mm apart.  EXACT turned that pair into ten
        # zero-width slivers and dropped them, which is the torn triangle in
        # the shoulder skin, and left both pilots behind as floating tubes.
        for hy in SV_HOLE_X:
            bore.append(lambda bm, s=sx, y=hy: _rodx(
                bm, SHO_CBORE / 2, s * SHO_CBORE_X, s * 94.0, y, ARM_AZ,
                FINE))
    # the other half of the shell joint: clearance and a head recess, so the
    # three screws finish below the skin rather than standing off it
    for a in JOIN_A:
        bore.append(lambda bm, a=a: _rodr(bm, JOIN_CLEAR / 2, 89.0, 96.0, a,
                                          JOIN_SCREW_Z, FINE))
        bore.append(lambda bm, a=a: _rodr(bm, JOIN_CBORE / 2, 92.0, 96.0, a,
                                          JOIN_SCREW_Z, FINE))
    return _obj("DB_dome", coll, parts, cuts, mat, add=add, bore=bore)


def _top(coll, mat):
    """The flat bearing ring.  Prints flat, so the face the head rides on is
    a first layer rather than a stack of curved perimeters."""
    parts = [lambda bm: _rodz(bm, TOP_R[1], TOP_Z[0], TOP_Z[1], 0, 0, SEGS),
             lambda bm: _rodz(bm, 48.5, TOP_Z[0] - 3.0, TOP_Z[0], 0, 0, SEGS)]
    cuts = [lambda bm: _rodz(bm, TOP_R[0], TOP_Z[0] - 4, TOP_Z[1] + 1, 0, 0,
                             SEGS)]
    # 90/210/330, not 30/150/270.  The wire slot below owns the rear now and
    # a fixing at 270 sat in the middle of it.
    for i in range(3):
        a = 2 * math.pi * i / 3 + math.pi / 2
        cuts.append(lambda bm, a=a: _rodz(
            bm, 1.6, TOP_Z[0] - 4, TOP_Z[1] + 1,
            44 * math.cos(a), 44 * math.sin(a)))
    # the wire way, as an arc slot: nine overlapping O5 holes over 80 deg
    for a in WIRE_A:
        cuts.append(lambda bm, a=a: _rodz(
            bm, WIRE_D / 2, TOP_Z[0] - 4, TOP_Z[1] + 1,
            WIRE_R * math.cos(a), WIRE_R * math.sin(a), FINE))
    return _obj("DB_top", coll, parts, cuts, mat)


def _yoke(coll, mat):
    """Collar, flange, and two arms up to the nod axis.  The flange is the
    thrust bearing: it, not the servo, is what the head stands on."""
    fz = (TOP_Z[1], TOP_Z[1] + 5.0)
    parts = [lambda bm: _rodz(bm, 30.0, TOP_Z[0] - 3.5, fz[0], 0, 0, SEGS),
             lambda bm: _rodz(bm, 42.0, fz[0], fz[1], 0, 0, SEGS),
             # down to the spline: a sleeve round the servo hub
             lambda bm: _rodz(bm, 7.0, PAN_TOP, TOP_Z[0] - 3.5, 0, 0,
                              FINE)]
    for sx in (1, -1):
        # arm: a slab leaning outward from the flange to the nod bore
        parts.append(lambda bm, s=sx: _box(
            bm, s * 26.0, s * YOKE_X[1], -7.0, 7.0, fz[1] - 2.0, fz[1] + 6.0))
        parts.append(lambda bm, s=sx: _box(
            bm, s * YOKE_X[0], s * YOKE_X[1], -7.0, 7.0, fz[1], HEAD_Z + 10.0))
        parts.append(lambda bm, s=sx: _rodx(
            bm, 10.0, s * YOKE_X[0], s * YOKE_X[1], 0.0, HEAD_Z, FINE))
    cuts = [lambda bm: _rodz(bm, HORN_BORE / 2, PAN_TOP - 1, TOP_Z[0], 0, 0)]
    for sx in (1, -1):
        cuts.append(lambda bm, s=sx: _rodx(
            bm, NOD_BORE / 2, s * 40.0, s * 80.0, 0.0, HEAD_Z, FINE))
    return _obj("DB_yoke", coll, parts, cuts, mat, loc=(0, 0, TOP_Z[0]))


def _head(coll, mat):
    """A sphere, opened at the face.  The O92 opening IS the access hole -
    there is no head split, and the nod servo goes in through it."""
    parts = [lambda bm: _ball(bm, HEAD_R, 0, 0, HEAD_Z),
             lambda bm: _svboss(bm, _nod_m())]
    cuts = [lambda bm: _ball(bm, HEAD_R - HEAD_WALL, 0, 0, HEAD_Z)]
    cuts += _svpocket_ops(_nod_m(), "+x")
    cuts += [
        lambda bm: _box(bm, -70, 70, FACE_Y, 90, HEAD_Z - 70, HEAD_Z + 70),
        # rebate the face plate in flush
        lambda bm: _rody(bm, 46.1, FACE_Y - FACE_T, FACE_Y + 1,
                         0.0, HEAD_Z, SEGS),
        # wire way out of the underside, at the REAR, in line with the slot
        # in DB_top so the whole run is one straight drop behind the robot
        lambda bm: _rodz(bm, WIRE_HEAD_D / 2, HEAD_Z - HEAD_R - 6.0,
                         HEAD_Z - 34.0, 0.0, -WIRE_HEAD_Y, FINE)]
    for sx in (1, -1):
        cuts.append(lambda bm, s=sx: _rodx(
            bm, NOD_BORE / 2, s * 40.0, s * 70.0, 0.0, HEAD_Z, FINE))
    return _obj("DB_head", coll, parts, cuts, mat, loc=(0, 0, HEAD_Z))


def _face(coll, mat, lens):
    """Face plate: two ring pockets, 1.1 mm of white PLA left in front of
    each as the diffuser."""
    plate = _obj("DB_face", coll,
                 [lambda bm: _rody(bm, 45.9, FACE_Y - FACE_T, FACE_Y, 0.0,
                                   HEAD_Z, SEGS)],
                 [lambda bm, s=s: _rody(bm, (RING_OD + 0.6) / 2,
                                        FACE_Y - FACE_T - 1, FACE_Y - 1.1,
                                        s * EYE_X, HEAD_Z + EYE_Z, SEGS)
                  for s in (1, -1)],
                 mat, loc=(0, 0, HEAD_Z))
    for s, tag in ((1, "L"), (-1, "R")):
        _obj("PX_eye_" + tag, coll,
             [lambda bm, s=s: _rody(bm, (RING_OD - 3.0) / 2, FACE_Y - 1.15,
                                    FACE_Y + 0.05, s * EYE_X, HEAD_Z + EYE_Z,
                                    SEGS)], [], lens, loc=(0, 0, HEAD_Z))
        _obj("PX_ring_" + tag, coll,
             [lambda bm, s=s: _rody(bm, RING_OD / 2, FACE_Y - FACE_T,
                                    FACE_Y - FACE_T + RING_T,
                                    s * EYE_X, HEAD_Z + EYE_Z, SEGS)],
             [lambda bm, s=s: _rody(bm, RING_ID / 2, FACE_Y - FACE_T - 1,
                                    FACE_Y - FACE_T + RING_T + 1,
                                    s * EYE_X, HEAD_Z + EYE_Z, SEGS)],
             lens, loc=(0, 0, HEAD_Z))
    return plate


def _arm(coll, mat, sx, tag):
    """Hub on the spline, a jog outboard, then the blade.  The jog is the
    whole reason the arm can hang past the O160 waist without touching it."""
    bx = ARM_BLADE_X * sx
    parts = [lambda bm: _rodx(bm, 11.0, sx * (ARM_AX + 1.0),
                              sx * (ARM_AX + 11.0), 0.0, ARM_AZ, FINE),
             lambda bm: _box(bm, sx * (ARM_AX + 1.0), bx + sx * ARM_T / 2,
                             -8.0, 8.0, ARM_AZ - 8.0, ARM_AZ + 8.0),
             lambda bm: _box(bm, bx - ARM_T / 2, bx + ARM_T / 2,
                             -ARM_W / 2, ARM_W / 2,
                             ARM_AZ - ARM_L, ARM_AZ),
             lambda bm: _rodx(bm, ARM_W / 2, bx - ARM_T / 2, bx + ARM_T / 2,
                              0.0, ARM_AZ - ARM_L, FINE)]
    cuts = [lambda bm: _rodx(bm, HORN_BORE / 2, sx * (ARM_AX - 2.0),
                             sx * (ARM_AX + 8.0), 0.0, ARM_AZ)]
    return _obj("DB_arm_" + tag, coll, parts, cuts, mat,
                loc=(sx * ARM_AX, 0, ARM_AZ))


def _svboss(bm, m, pad=3.0, back=7.0, front=1.0):
    """Solid meat around a servo pocket, so the two screws have something to
    thread into.  Without it an ear screw goes through 3 mm of shell and out
    the other side."""
    v = _box(bm, SV_EAR_X[0] - pad, SV_EAR_X[1] + pad,
             SV_BODY_Y[0] - pad, SV_BODY_Y[1] + pad,
             SV_EAR_Z[0] - back, front)
    bmesh.ops.transform(bm, matrix=m, verts=v)


def _svpocket_ops(m, open_dir, reach=24.0, through=1.0):
    """A servo holder with ONE open side.

    Two nested boxes, not one, and the difference matters:

      case  the case footprint, run from below the base right THROUGH the
            mounting face.  The old single box stopped at the ear plane, so
            the top 4.8 mm of the case - exactly the part sitting in the
            shoulder face - was never cut, and the servo was buried in solid
            material.  Point-sampling put 15% of the case inside the dome.
      ear   the ear footprint, and ONLY across the 2.5 mm the ears occupy.
            The old box used the ear width over the whole depth, which left
            a 32 mm slot where a 22.8 mm case goes and gave the ears nothing
            to seat against.

    What is left between them is the step the ears bear on, and the material
    the two screws thread into.  Both boxes sweep out of `open_dir` so the
    servo still slides in.

    The pilots run along local z because that is the only axis an MG90S is
    ever pierced on.  Wherever local z points is where the driver has to come
    from - worth reading off each caller before anything prints.

    Returns a LIST of operands, one convex solid each.  These used to be drawn
    into ONE bmesh, which handed EXACT a self-intersecting difference operand.
    It coped with the outline and silently no-opped inside it: measured on 30
    Aug 2026, the top 4.7 mm of EVERY servo case was still solid material -
    the arms in the dome and the nod in the head - and so were both ear tips.
    That is the same 4.8 mm the note above says was fixed; cutting the box to
    `through` fixed the box and not the solver.  Separate convex cuts are the
    same volume and there is nothing left for it to get wrong.
    """
    # `reach` was 70, and 70 is not a clearance, it is a hole saw.  The slot
    # only has to open into the cavity the servo is fed from - 24 clears the
    # arm boss's inboard face at |x| 66 with 11 to spare, and reaches the head
    # face opening for the nod.  At 70 the pan pocket ran out to x 76.7 at
    # z 105, where the dome's skin is at r 67.8, and tore a 9 mm hole in the
    # shoulder.  It was invisible until the merged operand above was split:
    # EXACT had been silently no-opping most of this cut, so nobody found out
    # the sweep was wrong.  A fix that works reveals what the bug was hiding.
    i = {"+x": 1, "-x": 0, "+y": 3, "-y": 2, "+z": 5, "-z": 4}[open_dir]
    case = [SV_BODY_X[0] - SV_FIT, SV_BODY_X[1] + SV_FIT,
            SV_BODY_Y[0] - SV_FIT, SV_BODY_Y[1] + SV_FIT,
            SV_BODY_Z[0] - SV_FIT, through]
    ear = [SV_EAR_X[0] - SV_FIT, SV_EAR_X[1] + SV_FIT,
           SV_BODY_Y[0] - SV_FIT, SV_BODY_Y[1] + SV_FIT,
           SV_EAR_Z[0] - SV_FIT, SV_EAR_Z[1] + SV_FIT]
    ops = []
    for box in (case, ear):
        b = list(box)
        b[i] += reach if i % 2 else -reach
        ops.append(lambda bm, b=b: bmesh.ops.transform(
            bm, matrix=m, verts=_box(bm, *b)))
    for hx in SV_HOLE_X:
        ops.append(lambda bm, hx=hx: bmesh.ops.transform(
            bm, matrix=m, verts=_rodz(bm, 1.7 / 2, 14.0,
                                      SV_EAR_Z[0] - 8.0, hx, 0.0)))
    return ops


def _arm_m(sx):
    """Shaft outward along x, case laid down with its long axis fore-aft."""
    return _sv_m((sx * ARM_AX, 0, ARM_AZ), (sx, 0, 0), (0, 1, 0))


def _nod_m():
    return _sv_m((YOKE_X[0] - 3.0, 0, HEAD_Z), (1, 0, 0), (0, 1, 0))


def _proxies(coll, pcb, metal, spk):
    """Every bought part, at the size it actually is.  These exist so fits()
    has something to be wrong about."""
    out = []
    B = lambda n, xy, z0, z1, c, mt, cy=0.0: out.append(_obj(
        n, coll, [lambda bm: _box(bm, c - xy[0] / 2, c + xy[0] / 2,
                                  cy - xy[1] / 2, cy + xy[1] / 2, z0, z1)],
        [], mt))
    B("PX_pi5", PI_XY, PI_Z, PI_Z + PCB_T + PI_TALL, 0.0, pcb)
    B("PX_wm8960", HAT_XY, PI_Z + PCB_T + HAT_CLR,
      PI_Z + PCB_T + HAT_CLR + PCB_T + HAT_TALL, 0.0, pcb, cy=-10.0)
    out.append(_obj("PX_pca9685", coll,
                    [lambda bm: _box(bm, -PCA_XY[0] / 2, PCA_XY[0] / 2,
                                     34.0, 34.0 + PCA_XY[1], 40.0, 44.0)],
                    [], pcb))
    out.append(_obj("PX_sht41", coll,
                    [lambda bm: _box(bm, -SHT_XY[0] / 2, SHT_XY[0] / 2,
                                     SHT_MNT_Y + 3.0, SHT_MNT_Y + 8.0,
                                     SHT_Z[0], SHT_Z[1])],
                    [], pcb))
    out.append(_obj("PX_fan", coll,
                    [lambda bm: _rody(bm, FAN_D / 2, REAR_Y[1],
                                      REAR_Y[1] + FAN_T, 0.0, 47.0)],
                    [], metal))
    out.append(_obj("PX_jack", coll,
                    [lambda bm: _rody(bm, JACK_D / 2, REAR_Y[0],
                                      REAR_Y[0] + JACK_L, 24.0, 44.0)],
                    [], metal))
    for s, tag in ((1, "L"), (-1, "R")):
        d, ln, h = SPK_BOX
        x0, x1 = s * (SPK_FACE - d), s * SPK_FACE
        parts = [lambda bm, a=x0, b=x1: _box(
            bm, a, b, -ln / 2, ln / 2, SPK_Z - h / 2, SPK_Z + h / 2)]
        cuts = []
        for ty in (-1, 1):                      # its four 6.5 mm holes
            for tz in (-1, 1):
                cuts.append(lambda bm, a=x0, b=x1, ty=ty, tz=tz: _rodx(
                    bm, SPK_TAB_D / 2, a - 1.0, b + 1.0,
                    ty * SPK_TAB_AT, SPK_Z + tz * SPK_TAB_Z, FINE))
        parts.append(lambda bm, b=x1, s=s: _rodx(       # the domed driver
            bm, SPK_DRV_D / 2, b, b + s * 2.5, SPK_PITCH, SPK_Z, SEGS))
        parts.append(lambda bm, b=x1, s=s: _rodx(       # the passive radiator
            bm, SPK_PR_D / 2, b, b + s * 1.2, -SPK_PITCH, SPK_Z, SEGS))
        out.append(_obj("PX_spk_" + tag, coll, parts, cuts, spk))
    return out


def _servos(coll, mat):
    """The four MG90S, where they actually sit."""
    frames = {
        "SV_pan": _sv_m((0, 0, PAN_TOP), (0, 0, 1), (0, 1, 0)),
        "SV_nod": _nod_m(),
        "SV_arm_L": _arm_m(1),
        "SV_arm_R": _arm_m(-1),
    }
    return {n: _obj(n, coll, [lambda bm, m=m: _servo(bm, m)], [], mat)
            for n, m in frames.items()}


# ------------------------------------------------------------ the chassis
# The plate sits DIRECTLY on the shell's 3 mm floor, so the chassis needs no
# feet of its own - flat on the bench before the shell exists, flat on the
# floor after.  Everything that stands on the plate starts at CH_Z[0] and
# passes through it, so the union has real overlap to work with instead of
# two coincident faces.
CH_R, CH_Z = 76.0, (3.0, 7.0)
# The mounting interface is printed in NOW rather than discovered later: four
# bosses on a O120 bolt circle, pilot-drilled from below.  The shell's floor
# gets clearance and a counterbore on the same circle and four M3 come UP from
# underneath - the one direction on this robot that is always reachable, with
# no board, servo or speaker anywhere near the driver.
CH_MOUNT_R, CH_MOUNT_AT = 4.5, 60.0
CH_MOUNT_TOP, CH_MOUNT_PILOT = 16.0, 2.5   # 13 mm of thread for an M3
CH_MOUNT_A = [math.radians(45 + 90 * i) for i in range(4)]

BAF_X = (SPK_FACE, SPK_FACE + 3.0)          # the wall the speakers tie to
BAF_Y, BAF_TOP = 55.0, 68.0     # 5.5 mm of wall past each tie hole
BAF_FOOT_Y, BAF_FOOT_Z = 44.0, 16.0         # narrower where the body tucks in

# Pi 5 mounting holes: 58 x 49, 3.5 in from each edge.  They are NOT centred
# on the 85 mm axis - 23.5 mm of board hangs past the second pair, which is
# the USB-A and Ethernet end.  Getting this backwards mirrors the whole stack.
PI_HOLE_X = (-PI_XY[0] / 2 + 3.5, -PI_XY[0] / 2 + 3.5 + 58.0)
PI_HOLE_Y = (-24.5, 24.5)
POST_D, POST_PILOT = 7.0, 2.2   # M2.5 self-tapper into printed PLA
# Datasheet, not guessed: 2.20 x 0.75 inch centres, 2.5 mm holes.
PCA_HOLE = ((-27.94, 27.94), (37.5, 56.55))


def _chassis(coll, mat):
    """Pi 5, PCA9685, SHT41 and both speaker boxes on one printed frame that
    stands on its own, plus the rear service panel fused into it.

    This is the part that gets printed and populated BEFORE any shell exists,
    so every fault in it is found with a screwdriver rather than after a
    two-hour shell print.  It is also the only structural part: the speakers
    tie to its baffles and the shell just wraps it.
    """
    z0 = CH_Z[0]
    parts = [lambda bm: _rodz(bm, CH_R, z0, CH_Z[1], 0, 0, SEGS)]
    for a in CH_MOUNT_A:
        parts.append(lambda bm, a=a: _rodz(
            bm, CH_MOUNT_R, z0, CH_MOUNT_TOP,
            CH_MOUNT_AT * math.cos(a), CH_MOUNT_AT * math.sin(a), FINE))
    for hx in PI_HOLE_X:
        for hy in PI_HOLE_Y:
            parts.append(lambda bm, x=hx, y=hy: _rodz(
                bm, POST_D / 2, z0, PI_Z, x, y, FINE))
    for hx in PCA_HOLE[0]:
        for hy in PCA_HOLE[1]:
            parts.append(lambda bm, x=hx, y=hy: _rodz(
                bm, POST_D / 2, z0, 40.0, x, y, FINE))
    for sx in (1, -1):
        parts.append(lambda bm, s=sx: _box(
            bm, s * BAF_X[0], s * BAF_X[1], -BAF_Y, BAF_Y,
            BAF_FOOT_Z, BAF_TOP))
        parts.append(lambda bm, s=sx: _box(
            bm, s * BAF_X[0], s * BAF_X[1], -BAF_FOOT_Y, BAF_FOOT_Y,
            z0, BAF_FOOT_Z))
        for gy in (-30.0, 30.0):            # gussets, or the baffle waves
            parts.append(lambda bm, s=sx, y=gy: _box(
                bm, s * 54.0, s * BAF_X[0], y - 1.5, y + 1.5, z0, 30.0))
    # SHT41 stands on its own tab at the front, facing out through the
    # shell's intake slots.
    parts.append(lambda bm: _box(bm, -16.0, 16.0, SHT_MNT_Y, SHT_MNT_Y + 3.0,
                                 z0, SHT_Z[1] + 2.5))
    # the rear service panel, fused in rather than screwed on
    parts.append(lambda bm: _box(bm, -REAR_X, REAR_X, REAR_Y[0], REAR_Y[1],
                                 z0, REAR_Z[1]))

    cuts = []
    for a in CH_MOUNT_A:
        cuts.append(lambda bm, a=a: _rodz(
            bm, CH_MOUNT_PILOT / 2, z0 - 1.0, CH_MOUNT_TOP - 2.0,
            CH_MOUNT_AT * math.cos(a), CH_MOUNT_AT * math.sin(a)))
    for hx in PI_HOLE_X:
        for hy in PI_HOLE_Y:
            cuts.append(lambda bm, x=hx, y=hy: _rodz(
                bm, POST_PILOT / 2, CH_Z[1], PI_Z + 1.0, x, y))
    for hx in PCA_HOLE[0]:
        for hy in PCA_HOLE[1]:
            cuts.append(lambda bm, x=hx, y=hy: _rodz(
                bm, POST_PILOT / 2, CH_Z[1], 41.0, x, y))
    for sx in (1, -1):
        for ty in (-1, 1):
            cuts.append(lambda bm, s=sx, ty=ty: _rodx(   # driver / radiator
                bm, BAFFLE_D / 2, s * 55.0, s * 90.0,
                ty * SPK_PITCH, SPK_Z, SEGS))
            for tz in (-1, 1):
                cuts.append(lambda bm, s=sx, ty=ty, tz=tz: _rodx(
                    bm, TIE_D / 2, s * 55.0, s * 90.0,
                    ty * SPK_TAB_AT, SPK_Z + tz * SPK_TAB_Z, FINE))
                # the keyhole runs OUTBOARD, away from the opening: inboard
                # it clipped the O42 rim and left a jagged edge
                cuts.append(lambda bm, s=sx, ty=ty, tz=tz: _box(
                    bm, s * 55.0, s * 90.0,
                    min(ty * SPK_TAB_AT, ty * (SPK_TAB_AT + TIE_OUT)),
                    max(ty * SPK_TAB_AT, ty * (SPK_TAB_AT + TIE_OUT)),
                    SPK_Z + tz * SPK_TAB_Z - TIE_SLOT_H / 2,
                    SPK_Z + tz * SPK_TAB_Z + TIE_SLOT_H / 2))
    for hx in (-SHT_HOLE[0] / 2, SHT_HOLE[0] / 2):
        for hz in (-SHT_HOLE[1] / 2, SHT_HOLE[1] / 2):
            cuts.append(lambda bm, x=hx, z=hz: _rody(
                bm, 1.1, SHT_MNT_Y - 1.0, SHT_MNT_Y + 4.0, x,
                (SHT_Z[0] + SHT_Z[1]) / 2 + z))
    cuts.append(lambda bm: _box(bm, -40.0, 20.0, REAR_Y[0] - 1, REAR_Y[1] + 1,
                                12.0, 32.0))                # USB-C and HDMI
    cuts.append(lambda bm: _rody(bm, FAN_D / 2 - 1.0, REAR_Y[0] - 1,
                                 REAR_Y[1] + 1, 0.0, 47.0, FINE))
    cuts.append(lambda bm: _rody(bm, (JACK_D + 0.3) / 2, REAR_Y[0] - 1,
                                 REAR_Y[1] + 1, 24.0, 44.0, FINE))
    for i in range(4):
        cuts.append(lambda bm, i=i: _rody(
            bm, 1.3, REAR_Y[0] - 1, REAR_Y[1] + 1,
            12.0 * (1 if i < 2 else -1), 47.0 + 12.0 * (1 if i % 2 else -1)))
    # loom: everything crosses the plate somewhere, so give it one big slot
    cuts.append(lambda bm: _box(bm, -20.0, 20.0, -52.0, -38.0,
                                z0 - 1, CH_Z[1] + 1))
    return _obj("DB_chassis", coll, parts, cuts, mat)


def build():
    for ob in list(bpy.data.objects):
        if ob.name.startswith(("DB_", "PX_", "SV_", "E_")):
            bpy.data.objects.remove(ob, do_unlink=True)
    old = bpy.data.collections.get(COLL)
    if old:
        bpy.data.collections.remove(old)
    coll = bpy.data.collections.new(COLL)
    bpy.context.scene.collection.children.link(coll)

    shell = _mat("DB_shell_mat", (0.82, 0.83, 0.85, 1.0), 0.42)
    accent = _mat("DB_accent_mat", (0.16, 0.17, 0.20, 1.0), 0.35)
    pcb = _mat("PX_pcb_mat", (0.05, 0.32, 0.16, 1.0), 0.65)
    metal = _mat("PX_metal_mat", (0.42, 0.44, 0.48, 1.0), 0.30)
    spk = _mat("PX_spk_mat", (0.10, 0.10, 0.11, 1.0), 0.80)
    lens = _mat("PX_lens_mat", (0.25, 0.75, 1.00, 1.0), 0.20, emit=6.0)
    horn = _mat("SV_mat", (0.10, 0.10, 0.12, 1.0), 0.55)

    _shell(coll, shell)
    _dome(coll, shell)
    _top(coll, accent)
    yoke = _yoke(coll, accent)
    head = _head(coll, shell)
    face = _face(coll, shell, lens)
    _chassis(coll, accent)
    arms = {t: _arm(coll, shell, s, t) for s, t in ((1, "L"), (-1, "R"))}
    sv = _servos(coll, horn)
    _proxies(coll, pcb, metal, spk)

    # the two nod inserts, which is where eye rig 01 died
    _obj("DB_cplr", coll,
         [lambda bm: _rodx(bm, NOD_BORE / 2 - FIT_MIN, YOKE_X[0] - 4.0,
                           YOKE_X[1], 0.0, HEAD_Z),
          lambda bm: _rodx(bm, 7.0, YOKE_X[1], YOKE_X[1] + 3.0, 0.0, HEAD_Z)],
         [lambda bm: _rodx(bm, HORN_BORE / 2, YOKE_X[0] - 5.0, YOKE_X[0] + 1.0,
                           0.0, HEAD_Z)], accent, loc=(0, 0, HEAD_Z))
    _obj("DB_pivot", coll,
         [lambda bm: _rodx(bm, NOD_BORE / 2 - FIT_MIN, -YOKE_X[1],
                           -(YOKE_X[0] - 8.0), 0.0, HEAD_Z),
          lambda bm: _rodx(bm, 7.0, -(YOKE_X[1] + 3.0), -YOKE_X[1], 0.0,
                           HEAD_Z)], [], accent, loc=(0, 0, HEAD_Z))

    # ------------------------------------------------------------- rigging
    def empty(name, loc):
        e = bpy.data.objects.new(name, None)
        e.empty_display_type, e.empty_display_size = "PLAIN_AXES", 18.0
        e.location = loc
        coll.objects.link(e)
        return e

    e_pan = empty("E_pan", (0, 0, TOP_Z[0]))
    e_nod = empty("E_nod", (0, 0, HEAD_Z))
    e_arm = {t: empty("E_arm_" + t, (s * ARM_AX, 0, ARM_AZ))
             for s, t in ((1, "L"), (-1, "R"))}
    # matrix_world is stale until the depsgraph runs, and every parent
    # inverse below is read off it.  Without this the head, the yoke and both
    # arms each get their own offset applied TWICE and fly off the body.
    bpy.context.view_layer.update()

    def kid(ob, parent):
        ob.parent = parent
        ob.matrix_parent_inverse = parent.matrix_world.inverted()

    for ob in (yoke, e_nod):
        kid(ob, e_pan)
    for ob in (head, face, sv["SV_nod"], bpy.data.objects["PX_ring_L"],
               bpy.data.objects["PX_ring_R"], bpy.data.objects["PX_eye_L"],
               bpy.data.objects["PX_eye_R"], bpy.data.objects["DB_cplr"],
               bpy.data.objects["DB_pivot"]):
        kid(ob, e_nod)
    for t in "LR":
        kid(arms[t], e_arm[t])

    n = smooth(coll)
    pose()
    print("built %d objects in %s, %d shaded at %.0f deg"
          % (len(coll.objects), COLL, n, SMOOTH_ANGLE))
    return fits()


def smooth(coll=None, angle=SMOOTH_ANGLE):
    thresh = math.radians(angle)
    obs = [o for o in (coll or bpy.data.collections[COLL]).objects
           if o.type == "MESH"]
    for ob in obs:
        me = ob.data
        bm = bmesh.new()
        bm.from_mesh(me)
        for e in bm.edges:
            e.smooth = not (len(e.link_faces) == 2
                            and e.calc_face_angle(0.0) > thresh)
        bm.to_mesh(me)
        bm.free()
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        me.update()
    return len(obs)


def pose(pan=0.0, nod=0.0, arm_l=ARM_REST, arm_r=ARM_REST):
    """Angles in degrees.  +pan looks left, +nod looks UP, +arm swings
    FORWARD on both sides (so the two servos want opposite horn mappings -
    that belongs in the node, not in the geometry)."""
    for name, axis, deg in (("E_pan", 2, pan), ("E_nod", 0, -nod),
                            ("E_arm_L", 0, arm_l), ("E_arm_R", 0, arm_r)):
        e = bpy.data.objects.get(name)
        if e:
            r = [0.0, 0.0, 0.0]
            r[axis] = math.radians(deg)
            e.rotation_euler = r
    bpy.context.view_layer.update()


# -------------------------------------------------------------------- gate
def _aabb(ob):
    ws = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(v.x for v in ws), min(v.y for v in ws),
                    min(v.z for v in ws))),
            Vector((max(v.x for v in ws), max(v.y for v in ws),
                    max(v.z for v in ws))))


def _corners(lo, hi):
    return [Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y)
            for z in (lo.z, hi.z)]


# --------------------------------------------------------------- clashes
# The analytic wall test only ever looked at BOUGHT parts against the body
# PROFILE.  It could not see one printed part cutting into another, and it
# explicitly excused the speakers because they fire through an opening - so
# the one thing it could not check is the one thing that went wrong.
#
# This measures actual intersection VOLUME between real meshes.  Volume, not
# a yes/no: 0.2 mm3 is two surfaces touching and 900 mm3 is a corner buried
# in a wall, and those want different reactions.
CLASH_PAIRS = (
    ("DB_chassis", "DB_shell"), ("DB_chassis", "DB_dome"),
    ("PX_spk_L", "DB_shell"), ("PX_spk_L", "DB_dome"),
    ("PX_spk_R", "DB_shell"), ("PX_spk_R", "DB_dome"),
    ("PX_pi5", "DB_chassis"), ("PX_pca9685", "DB_chassis"),
    ("PX_wm8960", "DB_chassis"), ("PX_sht41", "DB_chassis"),
    ("DB_shell", "DB_dome"), ("DB_top", "DB_dome"),
)
CLASH_OK = 2.0                  # mm3 - below this is two faces meeting


def _ivol(a, b):
    """Volume of a intersected with b, in mm3."""
    tmp = bpy.data.objects.new("_clash_tmp", a.data.copy())
    bpy.context.scene.collection.objects.link(tmp)
    tmp.matrix_world = a.matrix_world.copy()
    m = tmp.modifiers.new(type="BOOLEAN", name="i")
    m.object, m.solver, m.operation = b, "EXACT", "INTERSECT"
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(tmp.matrix_world)
    # Two parts MEETING share a face, and an EXACT intersect of coplanar
    # faces returns an open sheet whose calc_volume is meaningless - it read
    # 73.5 mm3 for the chassis plate simply resting on the shell floor, which
    # is the joint working.  A real interference has thickness in all three
    # axes; contact has none in one of them.
    if bm.verts:
        co = [v.co for v in bm.verts]
        thin = min(max(c[i] for c in co) - min(c[i] for c in co)
                   for i in range(3))
    else:
        thin = 0.0
    if thin < 0.05:
        v = 0.0
    else:
        # calc_volume on an OPEN mesh is meaningless, and an EXACT intersect
        # of two touching solids is often open.  It once reported 4582 mm3
        # inside a bounding box that only holds 2489.  Cap it at the box.
        box = 1.0
        for k in range(3):
            box *= max(c[k] for c in co) - min(c[k] for c in co)
        v = min(bm.calc_volume(signed=False), box)
    bm.free()
    bpy.data.meshes.remove(me)
    d = tmp.data
    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.meshes.remove(d)
    return v


def clashes(verbose=True):
    """Every pair in CLASH_PAIRS, by measured volume."""
    say = (lambda *a: print(*a)) if verbose else (lambda *a: None)
    hidden = [o for o in bpy.data.objects if o.hide_viewport]
    for o in hidden:
        o.hide_viewport = False
    bpy.context.view_layer.update()
    out = []
    for an, bn in CLASH_PAIRS:
        a, b = bpy.data.objects.get(an), bpy.data.objects.get(bn)
        if not a or not b:
            continue
        try:
            v = _ivol(a, b)
        except Exception as e:
            say("   ?? %s x %s: %s" % (an, bn, e))
            continue
        if v > CLASH_OK:
            out.append((v, an, bn))
        say("   %s %-12s x %-10s %9.1f mm3"
            % ("!!" if v > CLASH_OK else "  ", an, bn, v))
    for o in hidden:
        o.hide_viewport = True
    return sorted(out, reverse=True)


def fits(verbose=True):
    """Is every bought part inside the shell, and clear of every other one.

    This is deliberately NOT a mesh overlap test.  Overlap answers the same
    for 9 mm of daylight and 0.09 mm, which is exactly how eye rig 01 passed
    check() and then could not be assembled.  This reports MARGINS, signed,
    and the sign is the verdict.
    """
    bad, warn = [], []
    say = (lambda *a: print(*a)) if verbose else (lambda *a: None)
    say("\n--- packaging ------------------------------------------------")

    inner = [(r, z) for r, z in INNER_PROF if z <= BODY_TOP + 1e-6]
    for ob in sorted(bpy.data.objects, key=lambda o: o.name):
        if (not ob.name.startswith("PX_")
                or ob.name.startswith(HEAD_PX + BAFFLE_PX)):
            continue
        lo, hi = _aabb(ob)
        worst, at = 1e9, None
        for c in _corners(lo, hi):
            rr = _prof_r(inner, c.z)
            if rr is None:
                worst, at = -999.0, "z %.1f is outside the shell" % c.z
                break
            m = rr - math.hypot(c.x, c.y)
            if m < worst:
                worst, at = m, "r %.1f of %.1f at z %.1f" % (
                    math.hypot(c.x, c.y), rr, c.z)
        flag = "  " if worst >= 2.0 else ("!!" if worst < 0 else " ~")
        if worst < 0:
            bad.append("%s pokes through the shell (%s)" % (ob.name, at))
        say("%s %-14s wall margin %+7.1f   %s" % (flag, ob.name, worst, at))

    say("\n--- collisions between bought parts --------------------------")
    px = [o for o in bpy.data.objects
          if o.name.startswith(("PX_", "SV_"))
          and not o.name.startswith(HEAD_PX) and o.name != "SV_nod"]
    for i, a in enumerate(px):
        alo, ahi = _aabb(a)
        for b in px[i + 1:]:
            blo, bhi = _aabb(b)
            gaps = [max(alo[k] - bhi[k], blo[k] - ahi[k]) for k in range(3)]
            g = max(gaps)
            if g < 0:
                bad.append("%s and %s overlap by %.1f" % (a.name, b.name, -g))
                say("!! %-13s x %-13s overlap %.1f" % (a.name, b.name, -g))
    say("   %d pairs checked" % (len(px) * (len(px) - 1) // 2))

    say("\n--- the stack ------------------------------------------------")
    head_room = HAT_CLR - PI_TALL
    say("   HAT over the Pi's USB stack   %+7.1f   %s"
        % (head_room, "MEASURE HAT_CLR at the bench"))
    if head_room < 0.5:
        bad.append("WM8960 lands on the Pi's USB stack (HAT_CLR %.1f vs "
                   "PI_TALL %.1f)" % (HAT_CLR, PI_TALL))
    elif head_room < 4.0:
        warn.append("WM8960 clears the Pi's USB stack by %.1f, and HAT_CLR is "
                    "a GUESS - measure it before anything is cut" % head_room)
    hat_top = PI_Z + PCB_T + HAT_CLR + PCB_T + HAT_TALL
    say("   HAT top to the pan shelf      %+7.1f" % (SHELF_Z[0] - hat_top))
    if SHELF_Z[0] - hat_top < 3.0:
        bad.append("pan shelf sits %.1f over the WM8960 - no loom room"
                   % (SHELF_Z[0] - hat_top))

    say("\n--- speakers on the baffle ------------------------------------")
    _tie_gap = (math.hypot(SPK_TAB_AT - SPK_PITCH, SPK_TAB_Z)
                - BAFFLE_D / 2 - TIE_D / 2)
    _baf_r = math.hypot(BAF_X[1], BAF_Y)
    for label, have, need in (
            ("opening clears the cone     ", BAFFLE_D / 2, SPK_DRV_D / 2 + 1),
            ("tie hole to that opening    ", _tie_gap, 2.0),
            ("wall past the keyhole end   ",
             BAF_Y - SPK_TAB_AT - TIE_OUT, TIE_EDGE),
            ("keyhole slot fits a tie     ", TIE_SLOT_H, 2.0),
            ("keyhole runs AWAY from hole ",
             math.hypot(SPK_TAB_AT + TIE_OUT - SPK_PITCH, SPK_TAB_Z)
             - BAFFLE_D / 2 - TIE_SLOT_H / 2, 2.0),
            ("baffle corner inside barrel ",
             _prof_r(INNER_PROF, SPK_Z) - _baf_r, 1.0),
            ("baffle FOOT inside the barrel",
             _prof_r(INNER_PROF, CH_Z[0])
             - math.hypot(BAF_X[1], BAF_FOOT_Y), 1.0),
            ("speaker back to the Pi      ",
             SPK_FACE - SPK_BOX[0] - PI_XY[0] / 2, 3.0),
            ("box inside the baffle       ", BAF_TOP - CH_Z[0],
             SPK_BOX[2] + 4.0)):
        say("   %s%+7.1f" % (label, have - need))
        if have - need < 0:
            bad.append("speaker: %s short by %.1f" % (label.strip(),
                                                      need - have))

    say("\n--- the shoulder ---------------------------------------------")
    _ear = (abs(SV_EAR_X[0]), SV_EAR_X[1])
    for label, have, need in (
            ("housing covers the ears     ", SHO_Y + SHO_R,
             max(abs(h) for h in SV_HOLE_X) + 4.0),
            ("housing covers the case     ", SHO_R, SV_BODY_Y[1] + 2.0),
            ("housing deep enough for it  ", SHO_X[1] - SHO_X[0],
             abs(SV_BODY_Z[0]) + 0.5),
            ("top of housing under the rim", BODY_TOP - (ARM_AZ + SHO_R),
             2.0),
            ("bottom of it over the split ", (ARM_AZ - SHO_R) - SPLIT_Z, 0.0),
            ("thread behind the ear       ",
             SHO_X[1] + SV_EAR_Z[0] - 58.0, 8.0),
            ("shelf rim into the wall     ",
             84.0 - _prof_r(INNER_PROF, SHELF_Z[0]), 0.5),
            ("shelf rim inside the skin   ",
             _prof_r(BODY_PROF, SHELF_Z[1]) - 80.6, 0.5),
            ("shelf clear of the housing  ",
             (SHELF_Z[0]) - (ARM_AZ + SHO_R), 0.0)):
        say("   %s%+7.1f" % (label, have - need))
        if have - need < 0:
            bad.append("shoulder: %s short by %.1f"
                       % (label.strip(), need - have))

    say("\n--- chassis to shell -----------------------------------------")
    _mb = [(CH_MOUNT_AT * math.cos(a), CH_MOUNT_AT * math.sin(a))
           for a in CH_MOUNT_A]
    _worst, _at = 1e9, ""
    for ob in bpy.data.objects:
        if not ob.name.startswith(("PX_", "SV_")) or ob.name.startswith(
                HEAD_PX) or ob.name == "SV_nod":
            continue
        lo, hi = _aabb(ob)
        if hi.z < CH_Z[0] or lo.z > CH_MOUNT_TOP:
            continue
        for cx, cy in _mb:
            d = max(lo.x - cx, cx - hi.x, lo.y - cy, cy - hi.y)
            if d - CH_MOUNT_R < _worst:
                _worst, _at = d - CH_MOUNT_R, ob.name
    say("   mount boss to the nearest part%+7.1f   %s" % (_worst, _at))
    if _worst < 1.0:
        bad.append("a chassis mount boss fouls %s by %.1f" % (_at, -_worst))
    say("   bolt circle O%.0f, %d x M3 up from under the floor"
        % (CH_MOUNT_AT * 2, len(_mb)))

    say("\n--- motion ---------------------------------------------------")
    # The head is a sphere about the nod axis, so nod can never reach the
    # body.  Its floor is fixed and the number is just the standoff.
    say("   head bottom to DB_top, any nod%+7.1f"
        % ((HEAD_Z - HEAD_R) - (TOP_Z[1] + 5.0)))
    if (HEAD_Z - HEAD_R) - (TOP_Z[1] + 5.0) < 2.0:
        bad.append("head fouls the yoke flange")
    say("   head into the yoke gap        %+7.1f a side"
        % (YOKE_X[0] - HEAD_R))
    if YOKE_X[0] - HEAD_R < FIT_MIN:
        bad.append("head will not pass between the yoke arms")

    worst = 1e9
    for a in range(int(ARM_RANGE[0]), int(ARM_RANGE[1]) + 1, 2):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        for t in (0.0, ARM_L):
            for dx in (-ARM_T / 2, ARM_T / 2):
                for dy in (-ARM_W / 2, ARM_W / 2):
                    y = dy * c - (-t) * s
                    z = ARM_AZ + dy * s + (-t) * c
                    rr = _prof_r(BODY_PROF, z)
                    if rr is None:
                        continue
                    worst = min(worst, math.hypot(ARM_BLADE_X + dx, y) - rr)
    say("   arm blade to the body, swept  %+7.1f" % worst)
    if worst < 2.0:
        bad.append("arm blade clips the body at some angle (%.1f)" % worst)
    tip = ARM_AZ - ARM_L * math.cos(math.radians(ARM_RANGE[0]))
    say("   arm tip to the desk at %+.0f    %+7.1f" % (ARM_RANGE[0], tip))
    if tip < 5.0:
        bad.append("arm hits the desk at %.0f deg" % ARM_RANGE[0])

    say("\n--- printed parts cutting into each other ---------------------")
    for v, an, bn in clashes(verbose):
        bad.append("%s cuts %.0f mm3 into %s" % (an, v, bn))

    say("\n--- what this does NOT check ---------------------------------")
    say("   the speaker BOX size and its tab holes are GUESSES, and they")
    say("   are what DB_chassis is built around - see MEASURE")
    say("   nothing here weighs anything, so no torque is checked")
    say("   no screw path, no loom volume, no heat")
    say("   SHT41 hole SPACING is still a guess - the count is right now,")
    say("   the pitch is not confirmed")
    say("   the CQRobot module and the square one are still NOT in this -")
    say("   tell me what they are and they get mounts too")

    say("\n%s" % ("READY as a mockup - packaging closes"
                  if not bad else "NOT ready:"))
    for b in bad:
        say("   * " + b)
    for w in warn:
        say("   ? " + w)
    return not bad


# ------------------------------------------------------------------ export
STL_DIR = r"C:\Humalien\stl"


def export_stl(folder=STL_DIR, names=("DB_chassis",)):
    """Write each named object to its own STL, in millimetres.

    global_scale stays 1.0 so the numbers in this file land in the slicer
    unchanged - CH_R 76 comes out as a 152 mm plate, not 152 m.

    This never saves the .blend.  Exporting leaves the scene dirty and the
    blend is a convenience here, not the source: build() reconstructs every
    part from the constants at the top of this file.
    """
    import os
    os.makedirs(folder, exist_ok=True)
    out = []
    for n in names:
        ob = bpy.data.objects.get(n)
        if ob is None:
            print("  *** %s is not in the scene - run build() first" % n)
            continue
        was = ob.hide_viewport
        ob.hide_viewport = False
        for o in bpy.data.objects:
            o.select_set(False)
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        path = os.path.join(folder, n + ".stl")
        for call in (
                lambda: bpy.ops.wm.stl_export(
                    filepath=path, export_selected_objects=True,
                    global_scale=1.0, apply_modifiers=True),
                lambda: bpy.ops.export_mesh.stl(
                    filepath=path, use_selection=True,
                    global_scale=1.0, use_mesh_modifiers=True)):
            try:
                call()
                break
            except Exception:
                continue
        ob.select_set(False)
        ob.hide_viewport = was
        bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        dim = tuple(max(v[i] for v in bb) - min(v[i] for v in bb)
                    for i in range(3))
        kb = os.path.getsize(path) // 1024 if os.path.exists(path) else 0
        out.append((path, dim, kb))
        print("  %-28s %5.1f x %5.1f x %5.1f mm   %d KB"
              % (os.path.basename(path), dim[0], dim[1], dim[2], kb))
        if kb == 0:
            print("  *** nothing was written")
    return out
