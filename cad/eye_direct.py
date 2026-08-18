"""Direct-drive eyes, PAN ONLY. Every axis IS a servo output shaft.

    exec(open(r"C:\\Users\\PatrickKearney\\Downloads\\humalien\\cad\\eye_direct.py").read())
    build()
    pose(pan=25)
    fitcheck()

WHAT THIS FIXES, AND IT IS ONE THING
------------------------------------
In `cad/eye.py` the pan torque reaches the eyeball through a 1.0 mm printed
key flat, in a bore cut 0.40 mm oversize, at a 3 mm radius, in PLA. Every
part upstream of that flat can turn exactly as commanded and the ball still
does not move - which is what the bench showed. `cad/eye_v2.py` adds four
pushrods and twelve pin joints on top of the same idea.

So the rule here is: NOTHING PRINTED TRANSMITS TORQUE THROUGH A FIT.

The eyeball is not pushed by a mechanism. It is bolted to a servo horn. The
horn comes out of the servo bag injection-moulded to the spline, the centre
screw clamps it axially, and two self-tappers through the horn's own arm
holes tie it into a seat in the bottom of the ball:

    spline -> moulded horn -> 2 screws in shear -> ball

Three printed parts, two servos, two horns. No pin, no bore, no key flat,
no journal, no running fit, no link, no pushrod, no printed slot.

WHY THERE IS NO TILT HERE - PAT'S CALL, 18 AUG
----------------------------------------------
Tilt was a third servo lying on the tilt axis outboard of the eyes, turning
a yoke that carried everything. It is gone, and not coming back in that
form, because the head was measured against it:

  - Interior half-width at the eye line is about 55 mm. A servo with its
    shaft on the tilt axis outboard of the yoke needs its body out to
    x ~ 73. It cannot fit, and no trimming changes that.
  - The yoke's support arms were inside the shell walls at EVERY angle,
    level included. It was never a swing problem, it was a size problem.
  - A tilting yoke has to fit through its whole SWEEP, not just its rest
    position. At 16 degrees up the bottom of the arms lunged 22 mm forward,
    past the front of the eyeballs.

Deleting tilt deletes all three at once. Nothing here moves except two balls
spinning about their own centres, and a sphere rotating about its centre
sweeps no new volume - so the bracket is a STATIC part that only has to fit
once, which is the reason it can be cut to the shell at all. When tilt
returns it will be a servo between the eyes on the axis, or a linkage,
decided against a rig that has been printed and proven.

WHAT IS UNVERIFIED
------------------
`HORN["hole_r"]` - the radius of the horn's arm holes - is NOT measured. It
comes out of the servo bag, not the printer, so it cannot be derived.
`coupon()` prints a plate carrying nothing but that bolt circle. Print it,
offer it to a real horn, correct `hole_r`, THEN print a ball.

`EYE_Y` is Pat's hand registration against the printed shells. The shell
depth registration itself is still open item 1 in docs/resume-here.md.

Coordinates: gaze is +Y, pan about Z. Millimetres.
"""

import bpy
import bmesh
import math
from mathutils import Matrix, Vector

HEAD_MOUNTS = r"C:\Users\PatrickKearney\Downloads\humalien\cad\head_mounts.py"
COLL = "EYE_DIRECT"

# Registration. Pat positioned the rig by hand against HEAD_FACE/HEAD_CRANIUM
# on 18 Aug; this is the offset measured back off the scene. At this depth the
# ball front sits 4-10 mm behind brow, nose and cheek, and both balls clear
# both shells completely.
EYE_Y = 23.85

P = dict(
    pitch      = 62.0,
    ball_d     = 32.0,
    back_cut   = 6.6,
    iris_d     = 11.0,
    iris_deep  = 0.8,
    pupil_d    = 5.5,
    pupil_deep = 1.6,
)

# The TWO-ARM horn out of the bag, used as a BOLTED FLANGE, arms along Y.
# Not the 4-point cross: the body is 12.0 wide in Y and 22.5 long in X, so a
# bolt circle at r=7.5 puts the X-axis holes over the body where no driver
# reaches them. Arms along Y clear the body both sides.
HORN = dict(
    plate_t = 1.6, hub_d = 7.0, hub_h = 4.5,
    arm_r = 9.5, arm_w = 4.5,
    hole_r = 7.5,
    hole_d = 1.7,
    screw_head = 5.0,
)

SRV = dict(
    l = 22.5, w = 12.0, h = 22.7,
    tab_l = 32.2, tab_t = 2.5, tab_up = 16.0, tab_pitch = 28.0,
    shaft_d = 5.5, shaft_up = 4.5, shaft_off = 6.0,
    pocket_w = 12.8, pocket_l = 24.4,
)

FIT = dict(
    tab_pilot = 1.7,
    seat_edge = 2.0,        # material left outboard of a horn screw. THIS is
                            # what sets how deep the ball's seat is cut - it
                            # is not a chosen depth. Cut at a fixed 2.4 the
                            # seat came out O16.77, and the O1.7 pilots at
                            # r=7.5 reached O16.70: the screws broke out of
                            # the rim with 0.03 mm to spare and had nothing
                            # to bite into.
    shell_clear = 2.0,
)

BALL_R    = P["ball_d"] / 2.0
BALL_Z0   = -BALL_R
# The seat is DERIVED, not chosen: cut just deep enough that the horn's screw
# circle lands on solid material with `seat_edge` to spare. So when
# HORN["hole_r"] is corrected against a real horn out of the bag, the ball
# reshapes itself to suit instead of silently breaking out again.
SEAT_R    = HORN["hole_r"] + FIT["tab_pilot"] / 2.0 + FIT["seat_edge"]
if SEAT_R >= BALL_R:
    raise ValueError("a screw circle at r=%.2f will not fit on a O%.1f ball"
                     % (SEAT_R, P["ball_d"]))
SEAT_Z    = -math.sqrt(BALL_R ** 2 - SEAT_R ** 2)
SEAT_CUT  = 2.0 * SEAT_R + 8.0      # cutter: wider than the ball at that height
HORN_Z    = SEAT_Z - HORN["plate_t"]
PAN_SRV_Z = HORN_Z - HORN["hub_h"]
SHELF_Z   = PAN_SRV_Z - SRV["h"] + SRV["tab_up"] - SRV["tab_t"] / 2.0
SHELF_T   = 3.5
BR_Y0     = EYE_Y - 12.0
BR_Y1     = EYE_Y + 14.0

# Mounting tabs. They stand UP off the bracket's top face, at the two rear
# corners - the widest part of the plate. Up, not down, so the bracket still
# prints flat on its underside with nothing hanging below the first layer.
# The holes are drilled now even though the screws going in for the bench are
# pointed self-tappers straight into the shell: when the face is reprinted,
# these positions are what its bosses get designed against.
TAB_H      = 10.0       # how far the fin stands above the top face
TAB_T      = 4.0        # fin thickness, fore-aft
TAB_W      = 7.0        # how far it reaches inboard from its outer face
TAB_HOLE   = 2.6        # clearance for a pointed M2.5 self-tapper
TAB_HOLE_Z = 5.5        # hole height above the top face


def _hm():
    ns = {"__name__": "head_mounts", "__file__": HEAD_MOUNTS}
    with open(HEAD_MOUNTS, "r", encoding="utf-8") as fh:
        exec(compile(fh.read(), HEAD_MOUNTS, "exec"), ns)
    return ns


def _prims():
    out = []

    def add():
        out.append(bmesh.new())
        return out[-1]
    return out, add


def _sphere(bm, d, loc, segs=48):
    tmp = bmesh.new()
    bmesh.ops.create_uvsphere(tmp, u_segments=segs, v_segments=segs // 2,
                              radius=d / 2.0)
    bmesh.ops.transform(tmp, verts=tmp.verts[:],
                        matrix=Matrix.Translation(Vector(loc)))
    me = bpy.data.meshes.new("_s")
    tmp.to_mesh(me)
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    tmp.free()
    return bm


def _prism(bm, pts, z0, z1):
    """A solid from a closed 2D outline. This is how the bracket gets its
    shape: the outline is MEASURED off the shells, not drawn."""
    top = [bm.verts.new((x, y, z1)) for x, y in pts]
    bot = [bm.verts.new((x, y, z0)) for x, y in pts]
    bm.verts.ensure_lookup_table()
    bm.faces.new(top)
    bm.faces.new(bot[::-1])
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((top[i], top[j], bot[j], bot[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def _union(hm, coll, name, prims):
    base = hm["_link"](coll, name, hm["_mesh"](name, prims[0]))
    for i, bm in enumerate(prims[1:]):
        ob = hm["_link"](coll, "_U%d_%s" % (i, name), hm["_mesh"]("_U%d" % i, bm))
        hm["boolean"](base, ob, 'UNION')
        bpy.data.objects.remove(ob, do_unlink=True)
    return base


def _cut(hm, coll, ob, prims, name):
    for i, bm in enumerate(prims):
        hm["_apply"](coll, ob, bm, "%s_%d" % (name, i), 'DIFFERENCE')
    return ob


def _collection():
    old = bpy.data.collections.get(COLL)
    if old:
        for o in list(old.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(old)
    col = bpy.data.collections.new(COLL)
    bpy.context.scene.collection.children.link(col)
    return col


def _horn_holes(hm, bm, centre, axis, r, dia, depth):
    cx, cy, cz = centre
    for t in (-1, 1):
        hm["_cyl"](bm, dia, depth, (cx, cy + t * r, cz), axis, segs=16)
    return bm


def _shell_trees():
    from mathutils.bvhtree import BVHTree
    out = []
    dg = bpy.context.evaluated_depsgraph_get()
    for n in ("HEAD_FACE", "HEAD_CRANIUM"):
        o = bpy.data.objects.get(n)
        if o is None:
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = o.matrix_world
        out.append(BVHTree.FromPolygons(
            [tuple(mw @ v.co) for v in me.vertices],
            [tuple(p.vertices) for p in me.polygons], all_triangles=False))
        ev.to_mesh_clear()
    return out


def interior_halfwidth(trees, y, z, cap=48.0):
    """How far out the head's inner surface sits, at this depth and height."""
    best = None
    for t in trees:
        loc, nor, idx, dist = t.ray_cast(Vector((0.0, y, z)),
                                         Vector((1.0, 0.0, 0.0)), 200.0)
        if loc is not None:
            best = loc.x if best is None else min(best, loc.x)
    return cap if best is None else min(best, cap)


def bracket_outline(trees, steps=13):
    """The bracket's plan view, measured off the shells rather than drawn.
    At each station across its depth take the tighter of the plate's two
    faces, back off by the clearance, and use that half-width."""
    pts_r, pts_l = [], []
    for i in range(steps):
        y = BR_Y0 + (BR_Y1 - BR_Y0) * i / (steps - 1.0)
        hw = min(interior_halfwidth(trees, y, SHELF_Z),
                 interior_halfwidth(trees, y, SHELF_Z - SHELF_T))
        hw = max(hw - FIT["shell_clear"], 12.0)
        pts_r.append((hw, y))
        pts_l.append((-hw, y))
    return pts_r + pts_l[::-1]


def tab_sites(trees):
    """Where the two mounting fins sit. The outer face is taken from the
    shell at the FIN's own height, not the plate's - the wall leans, so the
    room 10 mm up is not the room at the plate. Returns (x, y, side)."""
    y = BR_Y0 + TAB_T / 2.0 + 1.0
    wall = min(interior_halfwidth(trees, y, SHELF_Z + 1.0),
               interior_halfwidth(trees, y, SHELF_Z + TAB_H))
    plate = min(interior_halfwidth(trees, y, SHELF_Z),
                interior_halfwidth(trees, y, SHELF_Z - SHELF_T))
    x = min(wall, plate) - FIT["shell_clear"]
    return [(sx * x, y, sx) for sx in (1, -1)]


def ball(hm, coll, sx):
    """One eyeball. The only feature that matters is the horn seat in the
    bottom: a flat floor, two pilots, and relief for the centre screw."""
    cx = sx * P["pitch"] / 2.0
    prims, add = _prims()
    _sphere(add(), P["ball_d"], (cx, EYE_Y, 0.0))
    ob = _union(hm, coll, "d_ball_%s" % ("R" if sx > 0 else "L"), prims)

    cuts, add = _prims()
    hm["_box"](add(), (60.0, 40.0, 60.0), (cx, EYE_Y - P["back_cut"] - 20.0, 0.0))
    hm["_cyl"](add(), SEAT_CUT, 12.0, (cx, EYE_Y, SEAT_Z - 6.0), 'Z')
    _horn_holes(hm, add(), (cx, EYE_Y, SEAT_Z + 3.0), 'Z',
                HORN["hole_r"], FIT["tab_pilot"], 6.0)
    hm["_cyl"](add(), HORN["screw_head"], 4.0, (cx, EYE_Y, SEAT_Z + 1.5), 'Z')
    for dia, deep in ((P["iris_d"], P["iris_deep"]),
                      (P["pupil_d"], P["pupil_deep"])):
        hm["_cyl"](add(), dia, deep * 2,
                   (cx, EYE_Y + P["ball_d"] / 2.0, 0.0), 'Y')
    _cut(hm, coll, ob, cuts, "ball_cut")
    return ob


def bracket(hm, coll, trees):
    """The one structural part. Static - nothing on it moves - so it fits the
    head once, and its outline is taken FROM the head rather than guessed.
    Both servo pockets open to the BACK: the leads exit the bottom of the
    case and must never be threaded down through the plate."""
    prims, add = _prims()
    _prism(add(), bracket_outline(trees), SHELF_Z - SHELF_T, SHELF_Z)
    sites = tab_sites(trees)
    for tx, ty, sx in sites:
        hm["_box"](add(), (TAB_W, TAB_T, TAB_H + SHELF_T),
                   (tx - sx * TAB_W / 2.0, ty,
                    SHELF_Z + TAB_H / 2.0 - SHELF_T / 2.0))
    ob = _union(hm, coll, "d_bracket", prims)

    cuts, add = _prims()
    for tx, ty, sx in sites:
        hm["_cyl"](add(), TAB_HOLE, TAB_W * 4.0,
                   (tx - sx * TAB_W / 2.0, ty, SHELF_Z + TAB_HOLE_Z),
                   'X', segs=20)
    for sx in (1, -1):
        bx = sx * P["pitch"] / 2.0 - sx * SRV["shaft_off"]
        slot_y1 = EYE_Y + SRV["pocket_w"] / 2.0
        slot_y0 = BR_Y0 - 6.0
        hm["_box"](add(), (SRV["pocket_l"], slot_y1 - slot_y0, 20.0),
                   (bx, (slot_y1 + slot_y0) / 2.0, SHELF_Z))
        for t in (-1, 1):
            hm["_cyl"](add(), FIT["tab_pilot"], 20.0,
                       (bx + t * SRV["tab_pitch"] / 2.0, EYE_Y, SHELF_Z),
                       'Z', segs=16)
        for t in (-1, 1):
            hm["_cyl"](add(), 4.5, 20.0,
                       (sx * P["pitch"] / 2.0, EYE_Y + t * HORN["hole_r"],
                        SHELF_Z), 'Z', segs=20)
    _cut(hm, coll, ob, cuts, "bracket_cut")
    return ob


def coupon(hm, coll):
    """Print this FIRST. A plate carrying the horn bolt circle and nothing
    else - HORN['hole_r'] is the one unmeasured number in the file."""
    cy = EYE_Y - 70.0
    prims, add = _prims()
    hm["_box"](add(), (30.0, 30.0, 3.0), (0.0, cy, SHELF_Z))
    ob = _union(hm, coll, "d_COUPON_horn_bolt_circle", prims)
    cuts, add = _prims()
    hm["_cyl"](add(), 2.0 * SEAT_R, 2.4, (0.0, cy, SHELF_Z + 1.5), 'Z')
    _horn_holes(hm, add(), (0.0, cy, SHELF_Z), 'Z',
                HORN["hole_r"], FIT["tab_pilot"], 10.0)
    hm["_cyl"](add(), HORN["screw_head"], 10.0, (0.0, cy, SHELF_Z), 'Z')
    _cut(hm, coll, ob, cuts, "coupon_cut")
    ob.color = (0.95, 0.75, 0.15, 1.0)
    return ob


def _placements():
    rz180 = Matrix.Rotation(math.radians(180), 4, 'Z')
    return {"pan_R": ((P["pitch"] / 2.0, EYE_Y, PAN_SRV_Z), None),
            "pan_L": ((-P["pitch"] / 2.0, EYE_Y, PAN_SRV_Z), rz180)}


def servo_proxy(hm, coll, name, loc, rot=None):
    """Solid MG90S. Origin is the CENTRE OF THE OUTPUT SHAFT at the top face
    of the body - the convention cad/eye.py uses, so placements compare."""
    prims, add = _prims()
    hm["_box"](add(), (SRV["l"], SRV["w"], SRV["h"]),
               (-SRV["shaft_off"], 0.0, -SRV["h"] / 2.0))
    hm["_box"](add(), (SRV["tab_l"], SRV["w"], SRV["tab_t"]),
               (-SRV["shaft_off"], 0.0, -SRV["h"] + SRV["tab_up"]))
    hm["_cyl"](add(), SRV["shaft_d"] * 2.2, 4.0, (0.0, 0.0, -2.0), 'Z')
    hm["_cyl"](add(), SRV["shaft_d"], SRV["shaft_up"],
               (0.0, 0.0, SRV["shaft_up"] / 2.0), 'Z')
    ob = _union(hm, coll, name, prims)
    if rot is not None:
        ob.data.transform(rot)
    ob.data.transform(Matrix.Translation(Vector(loc)))
    ob.color = (0.85, 0.20, 0.20, 1.0)
    return ob


def horn_proxy(hm, coll, name, loc):
    prims, add = _prims()
    hm["_cyl"](add(), 9.0, HORN["plate_t"],
               (0.0, 0.0, -HORN["plate_t"] / 2.0), 'Z')
    hm["_box"](add(), (HORN["arm_w"], HORN["arm_r"] * 2, HORN["plate_t"]),
               (0.0, 0.0, -HORN["plate_t"] / 2.0))
    hm["_cyl"](add(), HORN["hub_d"], HORN["hub_h"],
               (0.0, 0.0, -HORN["plate_t"] - HORN["hub_h"] / 2.0), 'Z')
    ob = _union(hm, coll, name, prims)
    ob.data.transform(Matrix.Translation(Vector(loc)))
    ob.color = (0.15, 0.55, 0.95, 1.0)
    return ob


def build():
    hm = _hm()
    trees = _shell_trees()
    if not trees:
        print("  !! HEAD_FACE / HEAD_CRANIUM not in the scene - the bracket is"
              " NOT fitted, it falls back to a straight 48 mm half-width")
    col = _collection()
    made = [ball(hm, col, 1), ball(hm, col, -1), bracket(hm, col, trees),
            coupon(hm, col)]
    for ob in made:
        print("  %-28s %4d verts" % (ob.name, len(ob.data.vertices)))
    pl = _placements()
    for key, side in (("pan_R", "R"), ("pan_L", "L")):
        servo_proxy(hm, col, "PROXY_d_servo_pan_" + side, *pl[key])
        horn_proxy(hm, col, "PROXY_d_horn_pan_" + side,
                   (pl[key][0][0], EYE_Y, SEAT_Z))
    smooth_all()
    print("EYE_DIRECT: pan only. 2 servos, 2 horns, 3 printed parts, 0 linkages")
    report()
    return col


def smooth_all(angle=35.0):
    col = bpy.data.collections.get(COLL)
    if col is None:
        return 0
    obs = [o for o in col.objects if o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))
    bpy.ops.object.select_all(action='DESELECT')
    return len(obs)


def pose(pan=0.0):
    """The only motion in the rig. Each ball turns about its OWN vertical
    axis, so its silhouette never changes and it sweeps no new volume."""
    col = bpy.data.collections.get(COLL)
    if col is None:
        raise RuntimeError("run build() first")
    for sx, side in ((1, "R"), (-1, "L")):
        c = Vector((sx * P["pitch"] / 2.0, EYE_Y, 0.0))
        to = Matrix.Translation(c)
        M = to @ Matrix.Rotation(math.radians(pan), 4, 'Z') @ to.inverted()
        for nm in ("d_ball_%s" % side, "PROXY_d_horn_pan_%s" % side):
            o = bpy.data.objects.get(nm)
            if o:
                o.matrix_world = M
    print("pose pan=%+.1f" % pan)


def fitcheck():
    """Does any of it touch the printed shells? That is the whole test."""
    from mathutils.bvhtree import BVHTree
    col = bpy.data.collections.get(COLL)
    dg = bpy.context.evaluated_depsgraph_get()

    def tree(o):
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = o.matrix_world
        t = BVHTree.FromPolygons([tuple(mw @ v.co) for v in me.vertices],
                                 [tuple(p.vertices) for p in me.polygons],
                                 all_triangles=False)
        ev.to_mesh_clear()
        return t
    shells = {n: tree(bpy.data.objects[n])
              for n in ("HEAD_FACE", "HEAD_CRANIUM") if bpy.data.objects.get(n)}
    if not shells:
        print("  no shells in the scene, nothing to check against")
        return
    bad = 0
    for o in sorted(col.objects, key=lambda o: o.name):
        if "COUPON" in o.name:
            continue
        t = tree(o)
        hits = {n: v for n, v in
                ((n, len(t.overlap(s))) for n, s in shells.items()) if v}
        if hits:
            bad += 1
            print("  %-26s TOUCHES %s" % (o.name, hits))
        else:
            print("  %-26s clear" % o.name)
    print("  ->", "FITS" if not bad else "%d part(s) still fouling" % bad)


def report():
    col = bpy.data.collections.get(COLL)
    lo = Vector((1e9,) * 3)
    hi = Vector((-1e9,) * 3)
    for o in col.objects:
        if "COUPON" in o.name:
            continue
        for b in o.bound_box:
            w = o.matrix_world @ Vector(b)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    print("  envelope %.1f x %.1f x %.1f   x %.1f..%.1f  y %.1f..%.1f  z %.1f..%.1f"
          % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z,
             lo.x, hi.x, lo.y, hi.y, lo.z, hi.z))
    print("  eye centres at y=%.2f (Pat's hand registration)" % EYE_Y)
    print("  seat derived from the screw circle: cut at z=%.2f, O%.2f,"
          " %.2f mm outboard of each screw"
          % (SEAT_Z, 2.0 * SEAT_R, FIT["seat_edge"]))
    trees = _shell_trees()
    if trees:
        for tx, ty, sx in tab_sites(trees):
            print("  mount hole %s at world (%.2f, %.2f, %.2f), axis X, O%.1f"
                  % ("R" if sx > 0 else "L", tx - sx * TAB_W / 2.0, ty,
                     SHELF_Z + TAB_HOLE_Z, TAB_HOLE))
    print("  UNVERIFIED: HORN['hole_r'] = %.1f - print coupon() first"
          % HORN["hole_r"])
