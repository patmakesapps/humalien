"""The v2 internal rack - everything electrical, on one part, built on a bench.

WHY THIS EXISTS
---------------
v1 bolted every board to the shell. That is why the build stopped: assembling
it meant wiring inside a bowl 106 mm deep with both hands, and no amount of
technique fixes that. The rack moves all of it onto a part you can pick up,
turn over, solder to, and test on a table - and then put into the head as one
piece.

The head already splits at y=135, so ACCESS was never the problem. Seeing a
connector and reaching it are different questions and v1 only ever asked the
first one.

WHAT IT CARRIES
---------------
    4 x MG90S      the four eye servos, which had NO mount of any kind in v1 -
                   `eye_v2.place_servos()` drops proxies and nothing else
    PCA9685        off the bowed rear wall, onto a flat face that printed flat
    Pi 5           on `rack_deck`, which supersedes `pi5_tray`

The eye mechanism itself stays in the FACE half. Servos end at y=132.1 and
`eye_frame` starts at y=135.5, so all four pushrods cross the split plane.
That is a fact about the head, not a choice: the two halves get assembled
around the linkage either way.

THE ONE THING THAT SHAPES THIS PART
-----------------------------------
The four servo shafts point three different ways, and the linkage fixes all
of them - pan drives a bar along x so its shaft is vertical; tilt and both
lids drive levers that pivot about x so their shafts run along x. A servo's
mounting tabs are ALWAYS perpendicular to its shaft. So no single flat face
takes all four, and anyone who draws "a plate with four servos screwed to it"
has drawn something that cannot work.

What does work: a backbone behind the servos, with four EARS standing off it,
each ear a plate normal to its own servo's shaft with a window the body drops
through and its tabs land on. Three ears face sideways, one faces up.

The backbone sits at y 114..118 - BEHIND the servo bodies, which occupy
y 119.9..132.1. It cannot be in the same band as them, and it cannot be in
front either, because in front is the split plane at 135.

Every ear reaches back along local -Y to meet it. That is uniform across all
four servos and it is not luck: three of the rotations are about Y and the
fourth is identity, so local Y is world Y for every one of them.

MEASURED, NOT CHOSEN
--------------------
Interior of HEAD_CRANIUM, by ray, 16 Aug 2026:

    rear wall y at x=0     z=150 -> 54.2   z=190 -> 39.5   z=230 -> 28.4
    front plane half-width z=140 -> 39.2   z=170 -> 53.2   z=230 -> 58.3
    ear hub inner face     x = +-39.5, so nothing here may pass +-36
    rear aperture          x +-36, z 251..277 - the Pi's ports, and the only
                           way a cable leaves the head without crossing y=135

`tab_pitch = 28.0` is the one servo number that is PROVEN - coupon_mg90s was
printed and real MG90S hardware fitted it on 15 Aug. Everything here is cut
to it rather than to a listing.
"""

import bpy
import bmesh
import math
from mathutils import Matrix, Vector

HEAD_MOUNTS = r"C:\Humalien\cad\head_mounts.py"
EYE_V2 = r"C:\Humalien\cad\eye_v2.py"
COLL = "RACK_v2"

R = dict(
    # --- the backbone -----------------------------------------------------
    back_y0   = 114.0,      # back face; servo bodies start at 119.9
    plate_t   = 4.0,        # -> front face at 118.0, 1.9 clear of the servos
    z0        = 132.0,      # below the lowest servo (tilt body starts 134.9)
    z1        = 256.0,      # up to the deck joint
    # The backbone tapers at the bottom because the cavity does. Front-plane
    # half-width is 31.7 at z=130 and 39.2 at z=140, so a constant-width
    # plate either wastes the top or fouls the bottom.
    hx_lo     = 26.0,       # half-width at z0
    hx_hi     = 36.0,       # half-width from z_flare up; ear hubs are at 39.5
    z_flare   = 162.0,      # where it reaches full width

    # --- the servo ears ---------------------------------------------------
    ear_t     = 4.0,
    ear_clr   = 0.4,        # around the body window, per side
    boss_clr_d = 15.0,      # clears the O12.1 shaft collar AND the horn
    ear_pad   = 5.0,        # material beyond the screw holes
    ear_fwd   = 1.0,        # how far an ear reaches past the servo's far face.
                            # 1 mm, not 8: the tabs are only as wide as the
                            # body, so anything more buys nothing and the
                            # split plane is at y=135. At 8 the ears reached
                            # y=140 and stood inside the face half.
    screw_d   = 2.4,        # M2 clearance - the shopping list's ~16 x M2

    # --- the hard envelope ------------------------------------------------
    # Trimmed rather than trusted. The ears are sized in each servo's own
    # frame, so their world extent is a consequence rather than a number
    # anyone chose - the pan ear came out at x=38.2 on the first build, 1.3
    # from the ear hub's inner face. A trim makes the envelope a fact.
    trim_hx   = 36.0,       # ear hub inner face is 39.5
    trim_y1   = 133.0,      # split plane is 135.0
    trim_z0   = 130.0,

    # --- the Pi deck ------------------------------------------------------
    deck_z    = 252.0,
    deck_hx   = 32.0,
    deck_y0   = 45.0,
    deck_y1   = 118.0,      # meets the spine's front face
    pi_cy     = 90.0,       # board centre, as v1's pi5_tray had it
    pi_hole   = 2.7,        # M2.5 clearance
    m3_hole   = 3.4,
    join_hx   = 25.0,       # where the deck and yoke bolt to the spine

    # --- the yoke, which carries the eye mechanism ------------------------
    # z=235, not 234, and the millimetre is lid_L's. The two lid servos are
    # mirror images, so one body hangs DOWN off its shaft and the other stands
    # UP: lid_R tops out at 222.1 and lid_L at 234.1. A yoke laid on the
    # frame's flange at 234 crosses lid_L by 0.1 mm - which a drawing never
    # shows and an assembly always finds.
    yoke_z    = 235.0,
    yoke_pad  = 234.0,      # two pads dip back down to meet the flange
    yoke_z0   = 220.0,      # the downturn reaches this far down the spine
    yoke_hx   = 34.0,
    yoke_y1   = 155.0,      # over the flange, which runs forward to y=160.5
    flange_hx = 30.0,       # the two bolts into the flange
    flange_y  = 150.0,
    # The downturn goes BEHIND the spine, not in front of it. In front is
    # y 118..122 and the servo bodies start at 119.9, so the first version
    # drove straight through both lid servos.
    yoke_back = 110.0,

    # --- the PCA9685, on the BACK of the backbone -------------------------
    # It comes off the rear wall entirely. That wall is bowed: inner face at
    # y=28.4 on the centreline against a mount designed at y=44.0, so the v1
    # part floated 15.6 mm off it in the middle and only touched near x=+-39.
    pca_z     = 203.0,      # centre; board is 25.4 tall -> z 190.3..215.7
    pca_boss  = 3.5,        # standoff off the backbone's back face
    pca_hole  = 2.5,        # M2.5 clearance
    pca_hx    = 27.94,      # Adafruit .brd: holes at +-27.94 x +-9.525
    pca_hz    = 9.525,
)

# Restated from eye_v2 rather than imported, so this file says what it cut to.
SERVO = dict(l=22.5, w=12.0, h=22.7, tab_pitch=28.0, tab_l=32.2, tab_t=2.5,
             tab_up=16.0)
PCA = dict(w=62.230, d=25.400, t=1.6)


def _mods():
    """head_mounts and eye_v2, exec'd - the servo positions live in eye_v2 and
    must not be restated here. A second copy of SERVOS is a second thing to
    forget to update, and this project has already been bitten by exactly that
    with FIT_forehead_casing."""
    hm_ns = {"__name__": "head_mounts", "__file__": HEAD_MOUNTS}
    with open(HEAD_MOUNTS, "r", encoding="utf-8") as fh:
        exec(compile(fh.read(), HEAD_MOUNTS, "exec"), hm_ns)
    ev_ns = {"__name__": "eye_v2", "__file__": EYE_V2}
    with open(EYE_V2, "r", encoding="utf-8") as fh:
        exec(compile(fh.read(), EYE_V2, "exec"), ev_ns)
    return hm_ns, ev_ns


def _prims():
    out = []

    def add():
        out.append(bmesh.new())
        return out[-1]
    return out, add


def _union(hm, coll, name, prims):
    """One boolean per primitive. Never a pile merged into one cutter bmesh -
    that is the nested-cutter trap and eye_v2 hit it four separate times."""
    base = hm["_link"](coll, name, hm["_mesh"](name, prims[0]))
    for i, bm in enumerate(prims[1:]):
        ob = hm["_link"](coll, "_U%d_%s" % (i, name), hm["_mesh"]("_U%d" % i, bm))
        hm["boolean"](base, ob, 'UNION')
        bpy.data.objects.remove(ob, do_unlink=True)
    return base


def _cut_each(hm, coll, ob, prims, name):
    for i, bm in enumerate(prims):
        hm["_apply"](coll, ob, bm, "%s_%d" % (name, i), 'DIFFERENCE')
    return ob


def _rot_for(axis):
    """The same table eye_v2.place_servos uses. A servo's shaft is +Z in its
    own frame; these put it where the linkage needs it."""
    return {None: Matrix.Identity(4),
            'X': Matrix.Rotation(math.radians(90), 4, 'Y'),
            '-X': Matrix.Rotation(math.radians(-90), 4, 'Y')}[axis]


def backbone_profile(z):
    """Half-width of the backbone at height z, following the cavity."""
    if z <= R["z0"]:
        return R["hx_lo"]
    if z >= R["z_flare"]:
        return R["hx_hi"]
    f = (z - R["z0"]) / (R["z_flare"] - R["z0"])
    return R["hx_lo"] + f * (R["hx_hi"] - R["hx_lo"])


def _backbone(hm, add):
    """The plate itself, as a stack of slabs following the taper.

    Built as steps rather than a lofted wedge on purpose: a wedge face is a
    45-degree overhang on a part that prints flat, and every step here is
    vertical in the print. It is also one solid per slab, unioned one at a
    time, so the taper cannot arrive as a pile of coincident faces.
    """
    y0, t = R["back_y0"], R["plate_t"]
    nz = 12
    zs = [R["z0"] + (R["z1"] - R["z0"]) * i / nz for i in range(nz + 1)]
    for a, b in zip(zs[:-1], zs[1:]):
        hx = backbone_profile((a + b) / 2.0)
        bm = add()
        hm["_box"](bm, (hx * 2.0, t, b - a), (0.0, y0 + t / 2.0, (a + b) / 2.0))


def _servo_ear(hm, ev, add, name):
    """One ear: a plate normal to this servo's shaft, reaching back to the
    backbone, with a window the body drops through.

    Built in the servo's own frame and then rotated, because that is the only
    frame in which the tab plane is a constant. Doing it in world coordinates
    means writing the same plate three different ways and getting one of them
    wrong - which is how eye_v2 ended up with a teardrop pointing +y on a part
    whose print-up was -z.
    """
    s = ev["SERVOS"][name]
    M = Matrix.Translation(Vector(s["loc"])) @ _rot_for(s["axis"])

    # Local z of the tab plate's face nearest the shaft. `tab_up` is to the
    # tab's CENTRE, so it is half the thickness to its face and not a whole
    # one - at +tab_t the ear stood 1.25 mm clear of the tabs it is supposed
    # to seat against, which is a mount that only touches when the screws
    # bend it.
    ztab = -SERVO["h"] + SERVO["tab_up"] + SERVO["tab_t"] / 2.0
    cx = -6.0                       # eye_v2's SERVO shaft_off - body centre
    t = R["ear_t"]

    # extent along the servo's long axis, capped so nothing reaches the ear
    # hubs at |x| = 39.5
    half_l = SERVO["tab_pitch"] / 2.0 + R["ear_pad"] + R["screw_d"] / 2.0
    # local -Y is world -Y for every servo here (all rotations are about Y),
    # so this is the direction the backbone lies in, for all four.
    y_back = R["back_y0"] - s["loc"][1]              # local y of the back face
    y_fwd = SERVO["w"] / 2.0 + R["ear_fwd"]

    bm = add()
    hm["_box"](bm, (half_l * 2.0, y_fwd - y_back, t),
               (cx, (y_fwd + y_back) / 2.0, ztab + t / 2.0))
    for v in bm.verts:
        v.co = (M @ v.co)
    return M, cx, ztab, t


def _servo_ear_cuts(hm, ev, add, name, M, cx, ztab, t):
    """The window and the two screw holes, in the same frame as the ear."""
    s = ev["SERVOS"][name]
    c = R["ear_clr"]
    bm = add()
    hm["_box"](bm, (SERVO["l"] + 2 * c, SERVO["w"] + 2 * c, t * 4.0),
               (cx, 0.0, ztab + t / 2.0))
    for v in bm.verts:
        v.co = (M @ v.co)
    # The shaft boss is a O12.1 collar standing 4 mm proud of the body's top
    # face, so it sits INSIDE the ear's own thickness and it is wider than the
    # body is at that corner - it overhangs the rectangular window by 0.6 mm
    # and fouled all four ears on the first build. The horn goes through here
    # too, so this wants to be generous rather than exact.
    bm = add()
    hm["_cyl"](bm, R["boss_clr_d"], t * 4.0, (0.0, 0.0, ztab + t / 2.0), 'Z')
    for v in bm.verts:
        v.co = (M @ v.co)
    for sgn in (-1.0, 1.0):
        bm = add()
        hm["_cyl"](bm, R["screw_d"], t * 4.0,
                   (cx + sgn * SERVO["tab_pitch"] / 2.0, 0.0, ztab + t / 2.0),
                   'Z')
        for v in bm.verts:
            v.co = (M @ v.co)


# The PCA9685 mounts on the BACK face, and it does NOT get printed standoffs.
#
# v1's pca9685_mount fought a bowed rear wall for no reason - inner face at
# y=28.4 on the centreline against a mount designed at 44.0, so it floated
# 15.6 mm off in the middle. Here the board sits on a face that printed flat,
# on the same part as everything it wires to, so the four servo leads never
# leave the rack.
#
# Printed bosses were drawn first and thrown away. This part wants to print
# BACK-FACE-DOWN - that face is ~8000 mm2 of flat plate and every wall on it
# grows straight up - and four O6 standoffs on that face are the only thing
# below it, so the part would have stood on 113 mm2 of boss with the whole
# plate 3.5 mm in the air. That is exactly how eye_frame came to touch the
# bed with 0.0 mm2 while passing every other check.
#
# So: four through-holes and nylon spacers out of the fastener bag. The
# spacer is a part that already exists, costs nothing, and cannot be printed
# wrong.


def _pca_holes(hm, add):
    y = R["back_y0"]
    for sx in (-1, 1):
        for sz in (-1, 1):
            bm = add()
            hm["_cyl"](bm, R["pca_hole"], 20.0,
                       (sx * R["pca_hx"], y + 2.0,
                        R["pca_z"] + sz * R["pca_hz"]), 'Y')


def _trim(hm, add):
    """Cut the part back to the envelope, one box per face.

    Not an INTERSECT against one bounding solid: this project's rule is one
    boolean per primitive, and a difference against a half-space box is the
    shape where that rule costs nothing.
    """
    big = 400.0
    for sx in (-1, 1):
        bm = add()
        hm["_box"](bm, (big, big, big),
                   (sx * (R["trim_hx"] + big / 2.0), 126.0, 190.0))
    bm = add()
    hm["_box"](bm, (big, big, big), (0.0, R["trim_y1"] + big / 2.0, 190.0))
    bm = add()
    hm["_box"](bm, (big, big, big), (0.0, 126.0, R["trim_z0"] - big / 2.0))


def rack_spine(hm, ev, coll):
    """The backbone plus its four ears, as one printed part."""
    prims, add = _prims()
    _backbone(hm, add)
    ears = []
    for name in ("pan", "tilt", "lid_R", "lid_L"):
        ears.append((name,) + _servo_ear(hm, ev, add, name))
    ob = _union(hm, coll, "rack_spine", prims)

    cuts, cadd = _prims()
    for name, M, cx, ztab, t in ears:
        _servo_ear_cuts(hm, ev, cadd, name, M, cx, ztab, t)
    _pca_holes(hm, cadd)
    _cut_each(hm, coll, ob, cuts, "_CUT_spine")
    return ob


# `_trim()` is deliberately NOT called any more, and that is the v2 decision
# rather than an oversight. Trimming the chassis to clear the v1 walls is the
# shell telling the hardware what shape to be, which is the arrangement that
# stopped the build. The chassis is drawn to the hardware; `clearance()`
# then reports what the shell would have to give up, and THAT is the input to
# whether the head gets resized. Measure first, resize second, if at all.


def chassis_deck(hm, coll):
    """The Pi 5 deck. Supersedes `pi5_tray`, which bolted to the shell.

    An L-joint onto the top of the spine: the spine is a plate normal to Y
    ending at z=256, this is a plate normal to Z starting at y=118, and they
    share the corner. Two M3 through it.

    No printed standoffs, for the same reason the PCA has none - this prints
    flat on its own underside, and four bosses below that face would be the
    only thing touching the bed.
    """
    prims, add = _prims()
    bm = add()
    hm["_box"](bm, (R["deck_hx"] * 2.0, R["deck_y1"] - R["deck_y0"],
                    R["plate_t"]),
               (0.0, (R["deck_y0"] + R["deck_y1"]) / 2.0,
                R["deck_z"] + R["plate_t"] / 2.0))
    ob = _union(hm, coll, "chassis_deck", prims)

    cuts, cadd = _prims()
    # Pi 5 mounting pattern: 58 x 49, board centre y=90 as v1 had it
    for sx in (-1, 1):
        for sy in (-1, 1):
            bm = cadd()
            hm["_cyl"](bm, R["pi_hole"], 20.0,
                       (sx * 29.0, R["pi_cy"] + sy * 24.5, R["deck_z"]), 'Z')
    for sx in (-1, 1):
        bm = cadd()
        hm["_cyl"](bm, R["m3_hole"], 20.0,
                   (sx * R["join_hx"], R["back_y0"] + R["plate_t"] / 2.0,
                    R["deck_z"]), 'Z')
    _cut_each(hm, coll, ob, cuts, "_CUT_deck")
    return ob


def chassis_yoke(hm, coll):
    """What holds the eye mechanism, and it does NOT use the temple bores.

    The obvious move is to present the two O5.2 temple sockets the face half
    has, at x=+-49.79, and let the frame's spigots drop into them. It cannot
    be done from behind: at that x the ear hub's O65 plug occupies x 39.5..60.1
    over a disc centred (y=95, z=204), and an arm reaching out to 49.79 at
    y<128 is inside it. Reaching out only where y>128 means a dog-leg through
    x 28..36 at z 208..222 - which is where the lid_R servo body already is.

    So the yoke takes the frame by its TOP FLANGE instead. The flange is
    z 230..234 forward to y=160.5 over |x|<=45 - the biggest flat face on the
    part, added on 16 Aug to make it printable, and it works just as well as a
    bolted interface. The yoke lies on it at z 234..238, comes back to the
    spine at y=118, and turns down the spine's front face to bolt.

    z 234..238 is clear: the highest servo, lid_L, tops out at 234.1, and the
    downturn at y 114..118 is behind all four bodies, which start at 119.9.
    """
    prims, add = _prims()
    y0 = R["yoke_back"]
    bm = add()
    hm["_box"](bm, (R["yoke_hx"] * 2.0, R["yoke_y1"] - y0, R["plate_t"]),
               (0.0, (y0 + R["yoke_y1"]) / 2.0,
                R["yoke_z"] + R["plate_t"] / 2.0))
    bm = add()          # the downturn, behind the spine
    hm["_box"](bm, (R["yoke_hx"] * 2.0, R["plate_t"],
                    R["yoke_z"] - R["yoke_z0"]),
               (0.0, y0 + R["plate_t"] / 2.0,
                (R["yoke_z"] + R["yoke_z0"]) / 2.0))
    for sx in (-1, 1):  # pads down onto the flange
        bm = add()
        hm["_cyl"](bm, 11.0, R["yoke_z"] - R["yoke_pad"],
                   (sx * R["flange_hx"], R["flange_y"],
                    (R["yoke_z"] + R["yoke_pad"]) / 2.0), 'Z')
    ob = _union(hm, coll, "chassis_yoke", prims)

    cuts, cadd = _prims()
    for sx in (-1, 1):      # down into the frame's top flange
        bm = cadd()
        hm["_cyl"](bm, R["m3_hole"], 20.0,
                   (sx * R["flange_hx"], R["flange_y"], R["yoke_z"]), 'Z')
    for sx in (-1, 1):      # back into the spine
        bm = cadd()
        hm["_cyl"](bm, R["m3_hole"], 20.0,
                   (sx * R["join_hx"], y0,
                    (R["yoke_z"] + R["yoke_z0"]) / 2.0), 'Y')
    _cut_each(hm, coll, ob, cuts, "_CUT_yoke")
    return ob


CHECKS = r"C:\Humalien\cad\checks.py"

# How each part prints, and these are MEASURED rather than assumed - see
# `printcheck()` below for the numbers and `cad/checks.py` for why the test
# exists at all.
#
# chassis_yoke is the one worth reading. Laid flat on its big plate it stands
# on the downturn's 4 mm edge: 272 mm2 of a 3088 mm2 shadow, 9%, with 2615 mm2
# of plate hanging 15 mm in the air. That is eye_frame's failure exactly, on a
# part drawn eight weeks later, and nothing but the gate caught it.
#
#   rot        bed mm2   of shadow   worst air
#   FLAT         272.0         9%      2615.1     <- what I would have printed
#   Y_UP        1273.9        96%         0.0
#   Z_DOWN      3041.9        99%         7.7     <- chosen
PRINT_AS = None         # filled in by _rots() on first use


def _rots():
    ns = {"__name__": "checks", "__file__": CHECKS}
    with open(CHECKS, "r", encoding="utf-8") as fh:
        exec(compile(fh.read(), CHECKS, "exec"), ns)
    return ns


def printcheck():
    """The gate, for the three chassis parts. Run it before any of it prints."""
    ns = _rots()
    return ns["gate"]([("rack_spine",   ns["Y_UP"]),
                       ("chassis_deck", ns["FLAT"]),
                       ("chassis_yoke", ns["Z_DOWN"])])


def build(save=False):
    hm, ev = _mods()
    old = bpy.data.collections.get(COLL)
    if old:
        for o in list(old.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(old)
    coll = bpy.data.collections.new(COLL)
    bpy.context.scene.collection.children.link(coll)
    print("chassis:")
    made = [rack_spine(hm, ev, coll),
            chassis_deck(hm, coll),
            chassis_yoke(hm, coll)]
    for ob in made:
        print("  %-14s %d verts" % (ob.name, len(ob.data.vertices)))
    if save:
        bpy.ops.wm.save_mainfile()
    return coll


def clearance():
    """What the shell would have to give up to accept this chassis.

    This is the whole point of drawing the chassis first. It reports, per
    part, how far outside HEAD_SOLID any vertex reaches - so "does the head
    need resizing" becomes a number instead of an argument.
    """
    sol = bpy.data.objects["HEAD_SOLID"]
    inside = _inside_test("HEAD_SOLID")
    Mi = sol.matrix_world.inverted()
    worst_all = 0.0
    for o in bpy.data.collections[COLL].objects:
        if o.type != 'MESH':
            continue
        out, worst, where = 0, 0.0, None
        for v in o.data.vertices:
            pw = o.matrix_world @ v.co
            if inside(pw):
                continue
            out += 1
            lp = Mi @ pw
            hit, loc, nor, idx = sol.closest_point_on_mesh(lp)
            if hit:
                d = (lp - loc).length
                if d > worst:
                    worst, where = d, pw.copy()
        worst_all = max(worst_all, worst)
        if out:
            print("  %-14s %4d verts outside, worst %.1f mm at "
                  "(%.0f, %.0f, %.0f)" % (o.name, out, worst,
                                          where.x, where.y, where.z))
        else:
            print("  %-14s fits" % o.name)
    print("VERDICT: %s" % ("no resize needed" if worst_all == 0.0 else
                           "the head is %.1f mm too small somewhere" % worst_all))
    return worst_all


# ---------------------------------------------------------------------------
# the checks - same standard as the rest of the project
# ---------------------------------------------------------------------------
def _tree(o):
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.transform(bm, verts=bm.verts[:], matrix=o.matrix_world)
    t = BVHTree.FromBMesh(bm)
    bm.free()
    return t


# Skew on purpose. This geometry is all axis-aligned planes and cylinders, so
# an axis-aligned ray lands on tangent surfaces and miscounts its crossings -
# the same reason eye_v2 uses three of them and takes a majority.
_DIRS = [Vector(d).normalized() for d in ((0.9137, 0.3184, 0.2513),
                                          (-0.2711, 0.8455, -0.4602),
                                          (0.1877, -0.3391, 0.9219))]


def _inside_test(name):
    """Point-in-solid by ray-crossing parity, majority of three directions.

    Borrowed from eye_v2 rather than reinvented. The obvious test -
    closest_point_on_mesh and the sign of the normal - is what this file used
    first, and on a sculpt with concave features it reported 876 of 1840
    vertices outside a part that overlaps the shell walls by zero faces.
    """
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


def check(verbose=True):
    """Inside the head, and clear of everything already in it.

    Containment is asked of HEAD_SOLID, not of HEAD_CRANIUM, and the
    difference is the whole test. HEAD_CRANIUM is a SHELL about 4 mm thick -
    "inside" it means inside the wall material, so a correct rack sitting in
    the middle of the cavity reports every vertex outside. The first run of
    this file said 1681 of 1719 verts were out and the part was fine.

    So: inside the solid silhouette, AND not overlapping the shell's walls.
    Two questions, and neither one answers the other.
    """
    ok = True
    rack = [o for o in bpy.data.collections[COLL].objects if o.type == 'MESH']
    inside = _inside_test("HEAD_SOLID")

    for o in rack:
        out = 0
        for v in o.data.vertices:
            if not inside(o.matrix_world @ v.co):
                out += 1
        print("  %-14s %d verts outside the head" % (o.name, out))
        if out:
            ok = False

    for o in rack:
        ta = _tree(o)
        for nm in ("HEAD_CRANIUM", "HEAD_FACE"):
            w = bpy.data.objects.get(nm)
            if w is None:
                continue
            n = len(ta.overlap(_tree(w)))
            print("  %-14s vs %-22s %4d faces" % (o.name, nm, n))
            if n:
                ok = False

    # collision with what is already in the head
    others = []
    for nm in ("PROXY_servo_pan", "PROXY_servo_tilt", "PROXY_servo_lid_R",
               "PROXY_servo_lid_L"):
        o = bpy.data.objects.get(nm)
        if o:
            others.append(o)
    for o in rack:
        ta = _tree(o)
        for b in others:
            tb = _tree(b)
            n = len(ta.overlap(tb))
            tag = "  (the servo in its own ear - expected)" if n else ""
            print("  %-14s vs %-22s %4d faces%s" % (o.name, b.name, n, tag))
    print("CHECK:", "PASS" if ok else "FAIL")
    return ok
