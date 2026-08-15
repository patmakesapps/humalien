"""Corner reliefs in the forehead_casing's camera pocket, so a square-cornered
B0385 actually drops in.

Run inside Blender:

    exec(open(r"C:\\Humalien\\cad\\casing_repair.py").read())
    report()        # measures the pocket, changes nothing
    build()         # cuts the reliefs

Then re-export whichever plate the casing is on.

WHY A REPAIR AND NOT A REBUILD
------------------------------
`eye_mech.forehead_casing()` is corrected too, so a clean rebuild produces
this. But the object in the file carries a **hand edit** - an enlarged S4B-ZR
cable exit - which no script reproduces, so the fix has to be cut into the
part that is already there. Same reasoning as `ear_hub_repair.py`.

WHAT WAS WRONG
--------------
The pocket is cut as a rounded rectangle, radius `corner_r + board_clear` =
2.0 + 0.5 = 2.5 mm, because `BOARDS["b0385"]["corner_r"]` is 2.0 off Arducam's
dimension drawing. The board in hand has **square** corners.

Measured in the mesh, the pocket's corner reaches a diagonal 18.77 mm from
centre (17.0 to the arc centre, plus 2.5/sqrt(2)). A 38 mm square board's
corner is at 19.00. **The board is 0.33 mm proud at all four corners** - which
is why it would not seat, and why only two screws went in.

THE FIX, AND WHY IT IS THIS ONE
-------------------------------
Four corner reliefs: Ø3.0 blind bores at the pocket's own bounding-box
corners, (cam_x +/- 19.5, row_y +/- 19.5).

Not "set corner_r to 0". That would demand the drawing be wrong in a specific
way, and it puts a sharp internal corner in the print - which a 0.4 mm nozzle
cannot cut anyway, so it leaves an unpredictable radius exactly where the fit
is decided. A relief removes the failure mode without having to know the
board's true corner radius: it swallows a square corner with 0.79 mm to spare,
and if the board turns out to be radiused after all it changes nothing. That
is the whole point of a dog-bone, and it is standard practice in any pocket
that has to accept a milled or routed part.

The straight walls from -18.0 to +18.0 survive, so the board is still located
on 36 mm of edge per side. Only the corners open up.

Depth: cut from z=3.0, which is 0.2 mm - one layer - BELOW the pocket floor at
z=3.2. Deliberately not level with it. A cutter face exactly coplanar with the
face it emerges through is what sealed a blind hole over in the ear hub and
left 42 coincident vertices in another; 0.2 mm of overshoot costs nothing and
is cut through material that is being removed anyway.
"""

import bpy
import bmesh
from mathutils import Vector

EYE_MECH = r"C:\Humalien\cad\eye_mech.py"
HEAD_MOUNTS = r"C:\Humalien\cad\head_mounts.py"
PART = "forehead_casing"
PR_COLL = "print ready"
FIT = "FIT_forehead_casing"

RELIEF_D = 3.0          # Ø3 swallows a square corner with 0.79 mm to spare
FLOOR_DROP = 0.2        # one layer below the pocket floor, so nothing is coplanar
WELD = 1e-4


def _em():
    """eye_mech's P and BOARDS, so no number here is a second copy of one."""
    ns = {"__name__": "eye_mech", "__file__": EYE_MECH}
    with open(EYE_MECH, "r", encoding="utf-8") as fh:
        exec(compile(fh.read(), EYE_MECH, "exec"), ns)
    return ns


def _pocket(ns):
    """(centre x, centre y, floor z, half width) of the camera pocket.

    Read from eye_mech's own numbers, then CONFIRMED against the mesh by
    `report()` - the part has been hand edited, so the file is the authority
    on what is actually there.
    """
    cam = ns["BOARDS"]["b0385"]
    pw, pd = ns["pocket_size"](cam)
    t = 5.0
    depth = cam["t"] + 0.2
    return -22.0, 3.5, t - depth, pw / 2.0, pd / 2.0


def report():
    ns = _em()
    cx, cy, fz, hw, hd = _pocket(ns)
    ob = bpy.data.objects[PART]
    floor = [v.co for v in ob.data.vertices
             if abs(v.co.z - fz) < 0.01 and abs(v.co.x - cx) < hw + 5
             and abs(v.co.y - cy) < hd + 5]
    print("camera pocket, from the mesh:")
    if not floor:
        print("  no floor found at z=%.2f - has the part changed?" % fz)
        return
    print("  floor z=%.2f, x %.2f..%.2f, y %.2f..%.2f"
          % (fz, min(p.x for p in floor), max(p.x for p in floor),
             min(p.y for p in floor), max(p.y for p in floor)))
    board = ns["BOARDS"]["b0385"]["w"] / 2.0
    worst = None
    for sx in (-1, 1):
        for sy in (-1, 1):
            q = [p for p in floor if (p.x - cx) * sx > 0 and (p.y - cy) * sy > 0]
            if not q:
                continue
            best = max(q, key=lambda p: (p.x - cx) * sx + (p.y - cy) * sy)
            reach = max(abs(best.x - cx), abs(best.y - cy))
            short = board - reach
            worst = short if worst is None else max(worst, short)
            print("  corner %+d%+d reaches %.2f, a square board needs %.2f  -> "
                  "%s by %.2f mm" % (sx, sy, reach, board,
                                     "SHORT" if short > 0 else "clear", abs(short)))
    return worst


def _health(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    o = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    n = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    v = len(bm.verts)
    bm.free()
    return o, n, v


def weld_debt(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    n0 = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=WELD)
    d = n0 - len(bm.verts)
    bm.free()
    return d


def shells(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    seen, n = set(), 0
    for v in bm.verts:
        if v in seen:
            continue
        n += 1
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
    bm.free()
    return n


def build(save=False):
    ns = _em()
    cx, cy, fz, hw, hd = _pocket(ns)
    ob = bpy.data.objects[PART]

    short = report()
    if short is not None and short <= 0:
        print("  pocket already clears a square board - nothing to do")
        return False

    # head_mounts' boolean, not a hand-rolled one. The first version of this
    # function built the modifier itself and the DIFFERENCE returned the part
    # UNTOUCHED, 1342 verts in and 1342 out, with no error - because
    # `new_from_object` was called without `depsgraph=dg`, so it evaluated
    # against a cutter the depsgraph had never seen. That exact trap is
    # written up on `_bake` in head_mounts.py, which is reason enough to use
    # the helper that already handles it rather than a second copy of it.
    hm = {"__name__": "head_mounts", "__file__": HEAD_MOUNTS}
    with open(HEAD_MOUNTS, "r", encoding="utf-8") as fh:
        exec(compile(fh.read(), HEAD_MOUNTS, "exec"), hm)

    # Ø3 at each bounding-box corner of the pocket, from one layer under the
    # floor up clear of the top face. Four disjoint cutters, so one batch is
    # safe - it is nested cutters this project has been bitten by, not these.
    cut = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            hm["_cyl"](cut, RELIEF_D, 6.0,
                       (cx + sx * hw, cy + sy * hd, fz - FLOOR_DROP + 3.0),
                       'Z', segs=32)
    # Into WORLD space, because a boolean modifier works there and this part
    # does not sit at the origin - `forehead_casing` is parked at x=519.46
    # with the rest of the HUMALIEN row. Built in local coordinates the four
    # cutters landed half a metre away from the part and the DIFFERENCE
    # returned it untouched, silently, which looks identical to the depsgraph
    # bug above and is not it. The ear hub never showed this because its
    # matrix_world is identity and its mesh is already in world coordinates.
    bmesh.ops.transform(cut, verts=cut.verts[:], matrix=ob.matrix_world)

    before = _health(ob)
    hm["_apply"](bpy.context.scene.collection, ob, cut, "_CUT_relief",
                 'DIFFERENCE')

    # weld, for the same reason the ear hub needed it
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=WELD)
    bm.to_mesh(ob.data)
    bm.free()

    after = _health(ob)
    print("  %s: %d -> %d verts, open %d->%d, non-manifold %d->%d, "
          "%d shell, weld debt %d"
          % (PART, before[2], after[2], before[0], after[0], before[1],
             after[1], shells(ob), weld_debt(ob)))
    report()

    # keep every copy of the part in step - the assembly and the plate layout
    for name in (FIT, "PR_" + PART):
        c = bpy.data.objects.get(name)
        if c is None:
            continue
        m = c.matrix_world.copy()
        old = c.data
        c.data = ob.data.copy()
        c.data.name = name
        c.matrix_world = m
        if old.users == 0:
            bpy.data.meshes.remove(old)
        print("  %s refreshed, transform kept" % name)

    if save:
        bpy.ops.wm.save_mainfile()
        print("  saved %s" % bpy.data.filepath)
    else:
        print("  NOT saved. build(save=True) when you have looked at it.")
    return True
