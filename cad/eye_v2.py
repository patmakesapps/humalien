"""A bespoke four-servo eye mechanism for Humalien.

Run inside Blender:

    exec(open(r"C:\\Humalien\\cad\\eye_v2.py").read())
    build()          # -> the EYE_v2 collection
    check()          # fit against the head, printability, clearances

Replaces Will Cogley's ε3.2, which is now reference only. Two reasons, and
the licence is the one that actually matters: ε3.2 is **CC BY-NC-SA**, so
none of his geometry could ever ship in this repo and nothing built on it
could ever be commercial. The second is that every one of his plates needs
support material, and nothing else in this project does.

WHAT IT DOES
------------
Four MG90S, against Cogley's six:

| servo | drives                  | on            |
| ----- | ----------------------- | ------------- |
| pan   | both eyes, linked, ±30° | the gimbal    |
| tilt  | both eyes, linked, ±20° | the frame     |
| lid R | right eyelid            | the gimbal    |
| lid L | left eyelid             | the gimbal    |

The two he spends that this does not are per-eye pan, which buys convergence
- eyes crossing to focus close. Real, but subtle, and it doubles the linkage
count. The simplicity is spent on making blink crisp instead.

THE THREE DECISIONS THAT SHAPE EVERYTHING
-----------------------------------------
**A gimbal, not a ball in a socket.** A ball floating in a spherical seat
needs two pushrods pulling on one free body, and they fight each other -
every bit of slop in one shows up as error in the other. A gimbal makes each
axis a defined pivot: the eye rotates about a vertical axle in a yoke, and
the yoke rotates about a horizontal axle in the frame. Nothing is
overconstrained and nothing needs a ball joint.

**The eyeballs are domes, not spheres.** Only the front of the eye is ever
visible through a Ø41 socket, so the back of a sphere is material that has to
be printed, split and seamed for nothing. Worse: a sphere splits into
hemispheres, and with a vertical pan axis the split plane contains both
poles - so the seam lands across the iris and the pivots land on the seam.
A dome cut BACK_CUT behind centre solves all of it at once: one piece, prints
flat-back-down, and the seam is behind the equator where nothing sees it.

Cut 7 mm behind centre on a Ø32 ball the first layer is r=14.4 against a full
16, so the wall leans 13° off vertical - well inside what prints unsupported
- and the dome still covers 218°, enough that the rim stays hidden through
the full ±30° of pan.

**The pan servo rides on the gimbal.** Put it on the fixed frame and its
pushrod has to reach a lever that is tilting away from it, which needs a
joint free in two axes at both ends and turns pan into a function of tilt.
Mounted on the gimbal the linkage is planar and pan and tilt are independent.
It costs the tilt servo the mass of three servos, but they sit close to the
tilt axis, which runs through the eye centres, so most of it is balanced. The
lid servos ride there for the same reason - a lid on the fixed frame would
change its gap to the eye by 5.6 mm across ±20° of tilt.

WHAT IT HAS TO HIT
------------------
Measured from the head, not assumed - see `docs/resume-here.md`:

- eyeball centres at **x = ±31, y = 160, z = 209** (`eye_pitch` is 62)
- Ø41 sockets, raked 25° out and 10° down
- the bay is ~116 mm wide and 30 mm deep at full width (y 130..160), then
  narrows to a 73 mm corridor behind y=125 where the ear hubs pinch in. The
  servos live in that corridor.
- **no supports, anywhere.** Every part prints flat.
"""

import bpy
import bmesh
import math
from mathutils import Matrix, Vector

HEAD_MOUNTS = r"C:\Humalien\cad\head_mounts.py"
COLL = "EYE_v2"

P = dict(
    pitch     = 62.0,       # eyeball centre to centre - matches the sockets
    y         = 160.0,      # eyeball centre
    z         = 209.0,
    ball      = 32.0,       # eyeball diameter
    socket    = 41.0,       # the head's opening, for clearance checks only

    # The dome. BACK_CUT behind centre: bigger hides the rim through more pan
    # but leans the first layers further out. 7.0 gives 13 deg off vertical.
    back_cut  = 7.0,
    shell     = 2.4,        # dome wall - 6 perimeters at 0.4, opaque enough
                            # to hide the pixel yet thin enough to glow

    pan_max   = 30.0,       # degrees each way
    tilt_max  = 20.0,

    # Yoke: stub axles top and bottom into blind sockets in the dome's back
    # face. Snap-fit, no fastener - the arms flex apart to take the eye.
    # Ø3.4, not Ø4. The forehead casing's underside is at z=225 and the top of
    # the eyeball is at z=225 - the same height - so the pan axle at the top
    # pole grazes its corner. A Ø4 axle centred on y=160 spans 158..162 and
    # the casing starts at exactly 162. Ø3.4 clears by 0.3. The real fault is
    # that the casing sits level with the top of the eye, but it is mounted,
    # printed and on plate 5, so the axle gives way instead.
    pin_d     = 3.4,
    pin_len   = 3.6,
    pin_fit   = 0.25,       # per side; the socket is pin_d + 2*fit
    yoke_t    = 4.0,        # arm thickness
    yoke_gap  = 0.6,        # running clearance, dome back face to yoke arm

    # Pan lever: a post off the dome's back face, offset from the pan axis.
    # 11 mm of arm gives +/-5.5 mm of link travel for +/-30 deg, which an
    # MG90S horn covers comfortably without running near its own end stops.
    lever_r   = 11.0,
    lever_t   = 3.0,
    link_t    = 3.0,
    link_d    = 2.6,        # link pin holes

    # Tilt bearings. MEASURED, not chosen: on the tilt axis MOUNT_ZONE runs
    # out between |x|=50 and 52, and the eyeballs reach |x|=47, so 48.5 is
    # the middle of a three-millimetre window. See gimbal().
    casing_y  = 162.0,      # FIT_forehead_casing starts here - measured
    tilt_x    = 48.5,
    trunnion  = 5.0,
    boss_wall = 3.0,
    plate_t   = 4.0,

    # The temple dowel pads, already in both printed head halves. MEASURED
    # off HEAD_CRANIUM by listing surface crossings along +X at z=215:
    #     y=134   solid 41.79..47.19 | VOID 47.19..52.39 | solid 52.39..61.07
    #     y=130   solid 57.79..61.88          (just the 4 mm wall)
    # The void is the Ø5.2 pin bore, so its centre is 49.79 - NOT 57.79, which
    # is only the inner wall face. An earlier probe that walked outward until
    # it hit something found the wall and called it the pad, and the frame
    # built on that number put 107 vertices outside the skin.
    # The pad's cranium-side depth is about 4 mm, y 131..135, so a spigot into
    # it gets 4 mm of engagement and no more.
    pad_x     = 49.79,
    pad_z     = 215.0,
    # The pad runs y 131..147 - measured on BOTH halves by listing crossings
    # along +X at z=215 - and ends by y=148. So the frame cannot sit against
    # it at the parting plane: y=135 is the middle of solid plastic, which is
    # where the first version put a Ø14 disc and got 78 face pairs through
    # HEAD_CRANIUM. It mounts on the FACE side, past the end of the pad.
    pad_face  = 148.0,
    # Ø7, not Ø14. Past the end of the pad the only thing left is the 4 mm
    # wall, which at y=150, z=215 stands at x 52.67..56.89 - so a Ø14 disc
    # centred on the bore at 49.79 reaches 56.79 and is inside it. Ø7 stops
    # at 53.3 and clears.
    # Ø5. The face half's inner wall was mapped ray by ray and it closes in
    # as you go forward: x 53.7 at y=147, 52.7 at 150, 51.5 at 153, 50.5 at
    # 156, and 49.0 by y=162. Ø7 on the bore at 49.79 reaches 53.29 and is
    # through the wall at y=150. Ø5 stops at 52.29 and clears it by 0.3.
    pad_d     = 5.0,
    arm_x     = 47.5,       # arm centre - 49.0 is the wall at y=162
    arm_t     = 3.0,
    # And the spigot goes all the way THROUGH the pad rather than a few mm
    # into it, so it is the head's own temple locating pin as well as the
    # frame's fixing. Ø5 is what head_split drew that bore for. This means
    # the eye frame goes in before the halves close, which it had to anyway.
    spigot    = 4.9,
    spigot_y0 = 130.0,      # back end, in the cranium half
    spigot_y1 = 148.0,      # front end, at the frame

    m3_free   = 3.4,
    m2_free   = 2.2,
    m2_pilot  = 1.7,
)


def _hm():
    ns = {"__name__": "head_mounts", "__file__": HEAD_MOUNTS}
    with open(HEAD_MOUNTS, "r", encoding="utf-8") as fh:
        exec(compile(fh.read(), HEAD_MOUNTS, "exec"), ns)
    return ns


def _sphere(bm, d, loc, segs=48):
    tmp = bmesh.new()
    bmesh.ops.create_uvsphere(tmp, u_segments=segs, v_segments=segs // 2,
                              radius=d / 2.0)
    bmesh.ops.transform(tmp, verts=tmp.verts[:], matrix=Matrix.Translation(loc))
    me = bpy.data.meshes.new("_t")
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    return bm


def eyeball(hm, coll, sx):
    """One eye: a Ø32 dome, hollow, with pan axle sockets and a lever.

    Prints flat-back-down. The back face is at y = centre - back_cut, so the
    first layer is a disc of r = sqrt(r^2 - back_cut^2) and the wall leans
    outward by atan(back_cut / (r - that)) - 13 degrees at back_cut 7.
    """
    side = "R" if sx > 0 else "L"
    cx, cy, cz = sx * P["pitch"] / 2.0, P["y"], P["z"]
    r = P["ball"] / 2.0

    bm = bmesh.new()
    _sphere(bm, P["ball"], (cx, cy, cz))
    ob = hm["_link"](coll, "eye_dome_%s" % side,
                     hm["_mesh"]("eye_dome_%s" % side, bm))

    # cut the back off, and hollow it for the 5050 pixel
    cut = bmesh.new()
    hm["_box"](cut, (80.0, 40.0, 80.0), (cx, cy - P["back_cut"] - 20.0, cz))
    hm["_apply"](coll, ob, cut, "_CUT_eye_back_%s" % side, 'DIFFERENCE')

    hollow = bmesh.new()
    _sphere(hollow, P["ball"] - 2 * P["shell"], (cx, cy, cz))
    hm["_box"](hollow, (80.0, 40.0, 80.0), (cx, cy - P["back_cut"] - 20.0, cz))
    hm["_apply"](coll, ob, hollow, "_CUT_eye_hollow_%s" % side, 'DIFFERENCE')

    # Pan axle sockets, blind, at the POLES, drilled along Z.
    #
    # Along Z and not along Y, and the first draft of this file got it wrong
    # in a way worth recording: sockets on the back face pointing backwards
    # give an axle along Y, and an eye on a Y axle does not pan, it ROLLS.
    # The pan axis is vertical by definition, so the axle has to run through
    # the top and bottom of the ball.
    #
    # The dome is hollow to 2.4 mm, so there is no meat at the poles to drill
    # into. These two plugs put it there without filling the cavity the 5050
    # pixel needs - they occupy only the outer 6 mm at each pole.
    add = bmesh.new()
    for sz in (-1, 1):
        # Kept INSIDE the sphere. A Ø12 boss centred at the pole sticks out
        # of a Ø32 ball above z = r - sqrt(r^2 - 6^2), and that 1.2 mm of
        # proud plastic was touching the forehead casing, whose underside is
        # at exactly z=225 - the same height as the top of the eyeball.
        hm["_cyl"](add, P["pin_d"] + 2 * P["yoke_t"], 8.0,
                   (cx, cy, cz + sz * (r - 6.0)), 'Z')
    # The pan lever points BACKWARD along -y, not sideways.
    #
    # Sideways was wrong and not just untidy. Linked pan needs both levers
    # offset the SAME way, so with a sideways lever one eye's lever ends up
    # outboard - at x=42 for the right eye - and HEAD_FACE has wall there
    # from x=44.5 at y=144. It went straight through the skull.
    #
    # Backward is symmetric and behind everything: the pin lands at
    # (cx, y - lever_r, z), rotating the eye about its vertical axis still
    # sweeps that pin in +/-x, and a bar along X still drives both eyes
    # together. Same linkage, no part of it outboard of the eyeball.
    hm["_box"](add, (P["lever_t"] * 2, P["lever_r"] - P["back_cut"] + 2.0,
                     P["lever_t"] * 2),
               # Overlapping the dome's back face, not butted against it.
               # Butted, the lever's front face landed exactly on y=153 - the
               # back plane - and a coincident face is not an intersection,
               # so the lever unioned as a SECOND SHELL and the eyeball came
               # out in two pieces. It reaches 2 mm into the dome now.
               (cx, cy - (P["lever_r"] + P["back_cut"] - 2.0) / 2.0, cz))
    # And a rib across the back opening to actually anchor it.
    #
    # The lever alone was a FREE-FLOATING SHELL, and reaching further into
    # the dome would never have fixed it: the dome is hollow, so its back is
    # an annulus from r=11.7 to r=16, and the lever sits on the axis at
    # r<4.2 - straight through the hole in the middle, touching nothing.
    # Pushing it deeper just pushes it further into the cavity.
    #
    # The rib spans to r=14, which is past the inner surface at this depth
    # (12.2 at y=154), so it lands in shell material on both sides. It also
    # leaves the opening clear above and below for the pixel and its wires.
    hm["_box"](add, (28.0, 3.0, P["lever_t"] * 2),
               (cx, cy - P["back_cut"] + 1.5, cz))
    lob = hm["_link"](coll, "_EYEADD_%s" % side, hm["_mesh"]("_EYEADD_%s" % side, add))
    hm["boolean"](ob, lob, 'UNION')
    bpy.data.objects.remove(lob, do_unlink=True)

    cut2 = bmesh.new()
    for sz in (-1, 1):
        # blind, drilled inward from each pole along the pan axis
        depth = P["pin_len"] + 0.6
        hm["_cyl"](cut2, P["pin_d"] + 2 * P["pin_fit"], depth,
                   (cx, cy, cz + sz * (r - depth / 2.0 + 0.01)), 'Z', segs=24)
    hm["_cyl"](cut2, P["link_d"], 20.0,
               (cx, cy - P["lever_r"], cz), 'Z', segs=24)
    hm["_apply"](coll, ob, cut2, "_CUT_eye_holes_%s" % side, 'DIFFERENCE')
    return ob


def gimbal(hm, coll):
    """The tilt frame: everything that rotates about the horizontal axis.

    Carries both yokes, and later the pan servo, the pan link and the two lid
    brackets. It pivots on trunnions at |x| = TILT_X.

    TILT_X is 48.5 and it is measured, not chosen. On the tilt axis
    (y=160, z=209) `MOUNT_ZONE` runs out somewhere between |x|=50 and 52, and
    the eyeballs reach |x|=47, so the bearings have a three-millimetre window
    to live in. That is thin for a beam and ample for a bearing, and putting
    them there rather than in the middle buys a 97 mm bearing span carrying a
    62 mm wide gimbal - the pair cannot yaw. Central bearings were the
    alternative and would have been a 20 mm span on the same load.
    """
    ty, tz = P["y"], P["z"]
    # The cross bar sits BELOW the eye line, not behind it. Behind, it fouled
    # two things at once: the socket boss, which comes inboard to x=44.5 by
    # y=144, and the pan link, which has to live at y=149 where the lever
    # pins are. Below the eyes both problems disappear - the wall there is at
    # x 52.8 and the link is nowhere near.
    bar_y = ty - 8.0
    bar_z = tz - 20.0
    prims = []

    def _p():
        prims.append(bmesh.new())
        return prims[-1]

    bm = _p()
    # the cross bar, and the trunnions on the tilt axis
    hm["_box"](bm, (2 * P["tilt_x"], 6.0, 8.0), (0.0, bar_y, bar_z))
    for sx in (-1, 1):
        bm = _p()
        # Wide enough to REACH the trunnion. At 8 wide it stopped 0.5 mm
        # short of it and the trunnion came out as a free cylinder - the bar
        # cannot do the job itself because it sits at y 147..153 and the
        # trunnion is on the tilt axis at y=160, so they never touch.
        # Two pieces, not one block, and the split is forced by where the
        # wall is. The face half closes to x=49.19 at y=159, z=196 - the
        # tightest point in the bay - but at z=209 there is no wall at all,
        # because that is the socket opening. So the structure stays BACK at
        # y<=155 while it is low, and only reaches forward to the tilt axis
        # up at eye height where the opening gives it room.
        hm["_box"](bm, (9.0, 6.0, abs(tz - bar_z) + 4.0),
                   (sx * (P["tilt_x"] - 4.5), bar_y, (tz + bar_z) / 2.0))
        bm = _p()
        hm["_box"](bm, (3.0, ty - bar_y + 3.0, 8.0),
                   (sx * P["tilt_x"], (bar_y + ty) / 2.0 + 1.5, tz))
        # The trunnion is 3 mm long, and that is the whole window. Between the
        # eyeball at |x|=47 and the edge of MOUNT_ZONE at 50 there are three
        # millimetres, so the bearing is short by necessity rather than
        # choice. It carries a light gimbal on a 97 mm span, which is what
        # makes 3 mm of engagement enough - the pair cannot yaw, so the
        # trunnions see almost pure radial load.
        hm["_cyl"](bm, P["trunnion"], 3.0,
                   (sx * P["tilt_x"], ty, tz), 'X')
    # a yoke at each eye: two arms reaching forward to the ball's poles
    r = P["ball"] / 2.0
    for sx in (-1, 1):
        cx = sx * P["pitch"] / 2.0
        for sz in (-1, 1):
            bm = _p()
            zarm = tz + sz * (r + P["yoke_gap"] + P["yoke_t"] / 2.0)
            # Arm: from the bar forward to the pole, over the top of the
            # ball - and STOPPING at casing_y. FIT_forehead_casing occupies
            # y 162..167 and z 225..283, and the top of the eyeball is at
            # z=225, so there is no room above the ball where the casing is.
            # The arm only has to reach the pole at y=160 anyway; the first
            # version ran to y=166 and put 37 faces through the casing.
            a_y0, a_y1 = bar_y - 3.0, P["casing_y"] - 1.0
            hm["_box"](bm, (P["yoke_t"] * 2, a_y1 - a_y0, P["yoke_t"]),
                       (cx, (a_y0 + a_y1) / 2.0, zarm))
            # the post joining that arm back down to the bar
            hm["_box"](bm, (P["yoke_t"] * 2, 6.0, abs(zarm - bar_z)),
                       (cx, bar_y, (zarm + bar_z) / 2.0))
            # The stub axle, pointing inward along the pan axis. It has to
            # span from the arm's underside all the way into the ball's pole
            # socket - the first version stopped 0.4 mm short of the arm and
            # came out as a free-floating cylinder, which is how the gimbal
            # first built as SEVEN shells rather than one.
            a_in = zarm - sz * P["yoke_t"] / 2.0          # arm's inner face
            a_out = tz + sz * (r - P["pin_len"])          # into the socket
            hm["_cyl"](bm, P["pin_d"], abs(a_in - a_out),
                       (cx, ty, (a_in + a_out) / 2.0), 'Z')
    return _union(hm, coll, "eye_gimbal", prims)


def frame(hm, coll, sx):
    """The fixed bulkhead. Bolts to the temple dowel pads, carries the gimbal.

    The pads are already in both printed head halves - Ø16, straddling the
    y=135 parting plane at z=215, and measured at |x| = 57.8. They exist to
    locate the two halves on a Ø5 pin, and they are the only substantial
    material anywhere near the eye bay: the shell on its own is 4 mm and has
    nothing to fix into. Using them means **the head needs no new holes**,
    which is what let the head halves go on the printer before this part
    existed.
    """
    ty, tz = P["y"], P["z"]
    side = "R" if sx > 0 else "L"
    prims = []

    def _p():
        prims.append(bmesh.new())
        return prims[-1]

    if True:
        # face against the end of the pad
        bm = _p()
        hm["_cyl"](bm, P["pad_d"], P["plate_t"],
                   (sx * P["pad_x"], P["pad_face"] + P["plate_t"] / 2.0,
                    P["pad_z"]), 'Y')
        # the spigot: through the whole pad, so it is the locating pin too
        bm = _p()
        span = P["spigot_y1"] - P["spigot_y0"]
        hm["_cyl"](bm, P["spigot"], span,
                   (sx * P["pad_x"], (P["spigot_y0"] + P["spigot_y1"]) / 2.0,
                    P["pad_z"]), 'Y')
        # arm forward to the bearing, stopping short of the forehead casing
        bm = _p()
        hm["_box"](bm, (P["arm_t"], P["casing_y"] - P["pad_face"], 16.0),
                   (sx * P["arm_x"], (P["pad_face"] + P["casing_y"]) / 2.0,
                    (tz + P["pad_z"]) / 2.0))
        bm = _p()
        hm["_box"](bm, (abs(P["pad_x"] - P["arm_x"]) + P["arm_t"], P["plate_t"], 12.0),
                   (sx * (P["pad_x"] + P["arm_x"]) / 2.0,
                    P["pad_face"] + P["plate_t"] / 2.0, P["pad_z"]))
        # The bearing tab. 3 mm thick, in the same three-millimetre window,
        # and a BOX rather than a disc: a Ø11 boss centred on the tilt axis
        # reaches 5.5 mm forward of it, and the skull is narrowing there - it
        # put 13 vertices 1.86 mm outside the skin at y≈164. The bearing only
        # needs material around the hole, and there is room for it behind the
        # axis but not in front, so the tab stops at y=161 and takes what it
        # needs going backwards.
        bm = _p()
        hm["_box"](bm, (3.0, 11.0, 12.0),
                   (sx * P["tilt_x"], ty - 4.5, tz))
    # Two brackets, not one part. They never meet - anything spanning between
    # them would have to cross the eye bay at the height of the eyeballs - so
    # a single object would always have reported two shells, and "2 shells"
    # is a fault everywhere else in this project. Naming them separately says
    # what is true.
    ob = _union(hm, coll, "eye_frame_%s" % side, prims)
    cut = bmesh.new()
    hm["_cyl"](cut, P["trunnion"] + 0.5, 20.0, (sx * P["tilt_x"], ty, tz),
               'X', segs=24)
    hm["_apply"](coll, ob, cut, "_CUT_frame_%s" % side, 'DIFFERENCE')
    return ob


def _union(hm, coll, name, prims):
    """Build one solid out of a list of primitive bmeshes, one boolean each.

    Not "merge them all into a single bmesh and self-union afterwards". That
    is how `gimbal()` first came out as SEVENTEEN closed shells sharing a
    volume, and a self-union on that left 120 non-manifold edges rather than
    fixing it - EXACT does not reliably resolve a dozen coincident faces in
    one pass. One union per primitive is slower to run and always correct,
    and it is what `head_mounts` does for the same reason.
    """
    base = hm["_link"](coll, name, hm["_mesh"](name, prims[0]))
    for i, bm in enumerate(prims[1:]):
        ob = hm["_link"](coll, "_U%d_%s" % (i, name), hm["_mesh"]("_U%d" % i, bm))
        hm["boolean"](base, ob, 'UNION')
        bpy.data.objects.remove(ob, do_unlink=True)
    return base


def _solidify(ob):
    """Weld, then self-union, so a part built from overlapping primitives is
    ONE solid rather than a pile of shells sharing a volume.

    `gimbal()` and `frame()` merge boxes and cylinders into a single bmesh
    with no boolean between them, which is fast to write and produces exactly
    the defect `ear_spine` had: 17 closed shells occupying the same space,
    every one of them individually healthy. A slicer will union it correctly
    but it should not have to guess, and nothing downstream can tell the
    difference between that and a part that has genuinely fallen apart.

    Rolled back if it moves the bounding box, because EXACT has destroyed
    parts in this file before.
    """
    import bmesh as _b
    bm = _b.new()
    bm.from_mesh(ob.data)
    _b.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
    bm.to_mesh(ob.data)
    bm.free()
    box = [Vector((min(v.co[i] for v in ob.data.vertices) for i in range(3))),
           Vector((max(v.co[i] for v in ob.data.vertices) for i in range(3)))]
    keep = ob.data.copy()
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.intersect_boolean(operation='UNION', use_self=True,
                                       solver='EXACT')
        bpy.ops.object.mode_set(mode='OBJECT')
    except RuntimeError as exc:
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass
        ob.data = keep
        print("    %s: self-union failed (%s) - kept as built" % (ob.name, exc))
        return ob
    now = [Vector((min(v.co[i] for v in ob.data.vertices) for i in range(3))),
           Vector((max(v.co[i] for v in ob.data.vertices) for i in range(3)))]
    if (not ob.data.vertices or
            max((now[0] - box[0]).length, (now[1] - box[1]).length) > 0.01):
        ob.data = keep
        print("    %s: self-union moved it - rolled back" % ob.name)
    else:
        bpy.data.meshes.remove(keep)
    import bmesh as _c
    bm = _c.new()
    bm.from_mesh(ob.data)
    _c.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def build(save=False):
    hm = _hm()
    old = bpy.data.collections.get(COLL)
    if old:
        for o in list(old.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(old)
    coll = bpy.data.collections.new(COLL)
    bpy.context.scene.collection.children.link(coll)
    print("eye_v2:")
    for sx in (1, -1):
        ob = _solidify(eyeball(hm, coll, sx))
        print("  %-14s %d verts" % (ob.name, len(ob.data.vertices)))
    ob = _solidify(gimbal(hm, coll))
    print("  %-14s %d verts" % (ob.name, len(ob.data.vertices)))
    for sx in (1, -1):
        ob = _solidify(frame(hm, coll, sx))
        print("  %-14s %d verts" % (ob.name, len(ob.data.vertices)))
    if save:
        bpy.ops.wm.save_mainfile()
    return coll


# ---------------------------------------------------------------------------
# verification - the part that decides whether any of this is real
# ---------------------------------------------------------------------------
_DIRS = [Vector(d).normalized() for d in ((0.9137, 0.3184, 0.2513),
                                          (-0.2711, 0.8455, -0.4602),
                                          (0.1877, -0.3391, 0.9219))]


def _inside_test(name):
    """Point-in-solid by ray-crossing parity. Skew directions and a majority
    vote, because this geometry is all axis-aligned planes and cylinders and
    an axis-aligned ray lands on tangent surfaces and miscounts."""
    ob = bpy.data.objects.get(name)
    if ob is None:
        return None
    inv = ob.matrix_world.inverted()

    def inside(pw):
        p = inv @ pw
        votes = 0
        for d in _DIRS:
            n, org = 0, p.copy()
            for _ in range(96):
                hit, loc, nrm, _i = ob.ray_cast(org, d, distance=1e6)
                if not hit:
                    break
                n += 1
                org = loc + d * 1e-4
            votes += n % 2
        return votes >= 2
    return inside


def check():
    """Prove it: watertight, one solid each, inside the head, nothing fouling."""
    import bmesh as _bm
    hm = _hm()
    coll = bpy.data.collections.get(COLL)
    if coll is None:
        print("no %s collection - run build() first" % COLL)
        return False
    # HEAD_SOLID, not MOUNT_ZONE. The zone has every shell opening
    # subtracted out of it, the eye sockets included - and the eyeball is
    # SUPPOSED to sit in that opening, so checking a dome against the zone
    # reports the whole visible front of the eye as a fault. The question
    # that actually matters is whether anything leaves the skin.
    in_zone = _inside_test("HEAD_SOLID")
    ok = True

    print("part health:")
    for ob in sorted(coll.objects, key=lambda o: o.name):
        bm = _bm.new()
        bm.from_mesh(ob.data)
        openE = sum(1 for e in bm.edges if len(e.link_faces) == 1)
        nonm = sum(1 for e in bm.edges if len(e.link_faces) > 2)
        seen, shells = set(), 0
        for v in bm.verts:
            if v in seen:
                continue
            shells += 1
            st = [v]
            while st:
                x = st.pop()
                if x in seen:
                    continue
                seen.add(x)
                for e in x.link_edges:
                    o = e.other_vert(x)
                    if o not in seen:
                        st.append(o)
        n0 = len(bm.verts)
        _bm.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
        debt = n0 - len(bm.verts)
        bm.free()
        bad = []
        if openE or nonm:
            bad.append("open %d, non-manifold %d" % (openE, nonm))
        if shells != 1:
            bad.append("%d shells" % shells)
        if debt:
            bad.append("weld debt %d" % debt)
        print("  %-14s %5d v, %d shell, open %d, non-manifold %d, weld debt %d  %s"
              % (ob.name, n0, shells, openE, nonm, debt,
                 "OK" if not bad else "FAIL: " + "; ".join(bad)))
        ok = ok and not bad

    print("")
    print("inside the head (every vertex against HEAD_SOLID):")
    skin = _inside_test("HEAD_SKIN") or in_zone
    for ob in sorted(coll.objects, key=lambda o: o.name):
        out = [ob.matrix_world @ v.co for v in ob.data.vertices
               if not in_zone(ob.matrix_world @ v.co)]
        if not out:
            print("  %-14s all %d vertices inside  OK"
                  % (ob.name, len(ob.data.vertices)))
            continue
        # how far out, and where - a count on its own says nothing about
        # whether this is a part through the skull or a rounding error
        solid = bpy.data.objects["HEAD_SOLID"]
        si = solid.matrix_world.inverted()
        worst = 0.0
        for p in out:
            hit, loc, nrm, _i = solid.closest_point_on_mesh(si @ p)
            if hit:
                worst = max(worst, ((si @ p) - loc).length)
        print("  %-14s %d of %d vertices outside, worst %.2f mm | "
              "x %6.1f..%6.1f y %6.1f..%6.1f z %6.1f..%6.1f  %s"
              % (ob.name, len(out), len(ob.data.vertices), worst,
                 min(p.x for p in out), max(p.x for p in out),
                 min(p.y for p in out), max(p.y for p in out),
                 min(p.z for p in out), max(p.z for p in out),
                 "OK, sub-nozzle" if worst < 0.4 else "FAIL"))
        ok = ok and worst < 0.4

    # ---- and against every other part in the head --------------------------
    # This is the check the first version of check() did not have, and its
    # absence was caught by looking at the screen rather than by any test:
    # every part can sit correctly inside the head and still pass straight
    # through the part next to it. Containment and collision are different
    # questions.
    from mathutils.bvhtree import BVHTree

    def _tree(o):
        b = _bm.new()
        b.from_mesh(o.data)
        _bm.ops.transform(b, verts=b.verts[:], matrix=o.matrix_world)
        t = BVHTree.FromBMesh(b)
        b.free()
        return t

    # PROXY_eyeball/iris are the placeholders these domes REPLACE, so they
    # share the same space by definition. CHECK_ is a measuring rule.
    SKIP = ("_", "PR_", "PRBED", "PRTITLE", "PRLABEL", "CUT_", "REF",
            "PROXY_", "CHECK_", "SnapEye", "EyeMech", "Assembly", "Base",
            "Component", "ServoSizing")
    SKIP_EXACT = {"HEAD_SKIN", "HEAD_SOLID", "MOUNT_ZONE", "HEAD_CYBORG",
                  "HEAD_CRANIUM_scriptbuild", "HEAD_REF",
                  "forehead_casing_asprinted_13aug"}
    mine = [o for o in coll.objects if o.type == 'MESH']
    tm = {o.name: _tree(o) for o in mine}
    others = [o for o in bpy.data.objects
              if o.type == 'MESH' and o not in mine
              and not o.name.startswith(SKIP) and o.name not in SKIP_EXACT]
    print("")
    print("collisions with the rest of the head (%d parts checked):" % len(others))
    clash = 0
    for o in others:
        t = _tree(o)
        for e in mine:
            pairs = tm[e.name].overlap(t)
            if not pairs:
                continue
            clash += 1
            b = _bm.new()
            b.from_mesh(e.data)
            _bm.ops.transform(b, verts=b.verts[:], matrix=e.matrix_world)
            b.faces.ensure_lookup_table()
            cs = [b.faces[i].calc_center_median() for i, _j in pairs]
            print("  %-14s THROUGH %-22s %4d faces at x %6.1f..%6.1f "
                  "y %6.1f..%6.1f z %6.1f..%6.1f"
                  % (e.name, o.name, len(pairs),
                     min(c.x for c in cs), max(c.x for c in cs),
                     min(c.y for c in cs), max(c.y for c in cs),
                     min(c.z for c in cs), max(c.z for c in cs)))
            b.free()
    if not clash:
        print("  none")
    ok = ok and not clash
    return ok


# ---------------------------------------------------------------------------
# a real MG90S, so servo room is measured rather than hoped for
# ---------------------------------------------------------------------------
# Body and total height come from the datasheet and agree with what
# eye_mech.P has carried all along - 22.5 x 12 x 22.7, 35.5 total. The tab
# pitch is 28.0 and it is the one number here that is PROVEN: coupon_mg90s
# was printed and the real servos fitted it, 15 Aug.
SERVO = dict(l=22.5, w=12.0, h=22.7, total_h=35.5,
             tab_pitch=28.0, tab_l=32.2, tab_t=2.5, tab_up=16.0,
             shaft_d=5.5, shaft_up=4.5, shaft_off=6.0)


# Where the four servos actually go. Found by search rather than by eye:
# every candidate was tested for containment in MOUNT_ZONE, against the other
# three servos, against the mechanism, and against every part already in the
# head. The first hand-placed layout failed on all three counts - tilt had a
# vertical shaft when it drives an X-axis lever, pan and tilt overlapped, and
# the right lid servo went through `tray_rail_R`.
#
# All four shafts land in the y=126 plane, so ONE plate can carry them.
#
# The shaft axis is not a free choice: it has to be parallel to the axis the
# servo drives, or the linkage stops being planar. Pan moves a bar along X so
# its shaft is vertical; tilt and both lids drive levers pivoting about X so
# their shafts run along X.
#
# lid_L sits 10 mm higher than lid_R and its body faces the other way. Not
# elegant, and not arbitrary - it is what clears tilt below it and the tray
# rail above it. Symmetry loses to packing in a bay this tight.
SERVOS = [
    ("pan",   (20.0, 126.0, 205.0), None),   # shaft vertical
    ("tilt",  (-8.0, 126.0, 178.0), 'X'),
    ("lid_R", (28.0, 126.0, 222.0), 'X'),
    ("lid_L", (-28.0, 126.0, 232.0), '-X'),  # mirrored, body faces inboard
]


def place_servos(hm, coll):
    """Drop the four MG90S proxies where SERVOS says, so every later part is
    drawn against a servo that is really there rather than a remembered one."""
    import math as _m
    rots = {None: None,
            'X': Matrix.Rotation(_m.radians(90), 4, 'Y'),
            '-X': Matrix.Rotation(_m.radians(-90), 4, 'Y')}
    out = []
    for name, loc, axis in SERVOS:
        for o in list(coll.objects):
            if o.name == "PROXY_servo_" + name:
                bpy.data.objects.remove(o, do_unlink=True)
        out.append(servo_proxy(hm, coll, "PROXY_servo_" + name, loc, rots[axis]))
    return out


def servo_proxy(hm, coll, name, loc, rot=None):
    """A solid MG90S at `loc`, output shaft up (+Z) unless rotated.

    Origin is the CENTRE OF THE OUTPUT SHAFT at the top face of the body,
    because that is the point a linkage is designed around - not the centre
    of the box, which is where a proxy placed by eye ends up and why it then
    disagrees with the horn by 6 mm.
    """
    s = SERVO
    dx, dy, dz = 0.0, 0.0, 0.0
    prims = []

    def _p():
        prims.append(bmesh.new())
        return prims[-1]

    # body, hanging below the shaft top
    bm = _p()
    hm["_box"](bm, (s["l"], s["w"], s["h"]),
               (dx - s["shaft_off"], dy, dz - s["h"] / 2.0))
    # mounting tabs
    bm = _p()
    hm["_box"](bm, (s["tab_l"], s["w"], s["tab_t"]),
               (dx - s["shaft_off"], dy, dz - s["h"] + s["tab_up"]))
    # output shaft boss
    bm = _p()
    hm["_cyl"](bm, s["shaft_d"] * 2.2, 4.0, (dx, dy, dz - 2.0), 'Z')
    bm = _p()
    hm["_cyl"](bm, s["shaft_d"], s["shaft_up"], (dx, dy, dz + s["shaft_up"] / 2.0), 'Z')
    ob = _union(hm, coll, name, prims)
    if rot is not None:
        ob.data.transform(rot)
    ob.data.transform(Matrix.Translation(Vector(loc)))
    ob.color = (0.9, 0.2, 0.2, 1.0)
    return ob
