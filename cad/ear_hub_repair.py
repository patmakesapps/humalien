"""Weld the ear hub's bosses onto its plug, and give them a root to stand on.

Run inside Blender:

    exec(open(r"C:\\Humalien\\cad\\ear_hub_repair.py").read())
    report()        # what is wrong right now, changes nothing
    build()         # repair ear_hub_R, mirror to _L, refresh the plate copies

Then re-export:

    exec(open(r"C:\\Humalien\\cad\\export_plate.py").read())
    verify(4); export_plate(4)

WHY THIS IS A SEPARATE FILE AND NOT A REBUILD
---------------------------------------------
`head_mounts.ear_hubs()` has been corrected too, so a clean rebuild now
produces this geometry directly. But `head_mounts.build()` cannot be run:
it rebuilds `HEAD_CRANIUM`, which carries the `USERFIX` edit at both ear
ports and six hand-made hole plugs that no script reproduces. So the fix has
to be applied to the objects that are already in the file. This script is
that application, written to be re-runnable and to prove its own result.

WHAT WAS WRONG
--------------
**The three bosses were not attached to the plug at all.** Each hub exported
as FIVE separate solids: the Ø65 plug, three free-floating Ø13 posts, and a
sealed bubble (below). The posts stood 0.461 mm clear of the plug's rim.
That is why they came off the bed loose or snapped at a touch - nothing was
holding them but first-layer squish.

The cause is one line in `ear_hubs()`: the arms were clipped with

    boolean(arm_ob, MOUNT_ZONE, 'INTERSECT')

and `MOUNT_ZONE` has every shell opening subtracted out of it, including the
Ø66 ear port. The arms are Ø13 on a r=36 bolt circle, so they span
r 29.5..42.5. Their overlap with the Ø65 plug is a lens at r 29.5..32.5 -
entirely inside r=33, entirely inside the port cutter. The clip deleted
precisely the material that welded each boss to the disc, and left the rest.

The comment that justified the clip said the arms "sit at r=36 well outside
the Ø66 bore". That is true of the arm's AXIS and false of its body, which
is the whole of the bug.

None of the existing checks could see it. Disconnected shells are each still
closed and manifold, so `_health()` read 0 open / 0 non-manifold; `verify()`
compares a plate copy to its source and both were equally wrong; and the
volume was right because no material was missing, only the join. **A part
being one connected solid is now checked explicitly** - see `report()`.

**The +z spine screw had no hole.** The two blind M3 threads are cut 6.5 mm
into the 8 mm plug by a cutter whose back end lands exactly ON the plug's
back face at x=39.5. Coplanar cutter face, coplanar result: at z+24 the
boolean capped it over, leaving a sealed Ø2.6 x 6.5 void inside the plug
(volume -34.1 mm3, inward normals) and no opening for the screw. At z-24 the
same cutter happened to resolve correctly, which is how it went unnoticed.
Fixed by starting the cutter OVERSHOOT mm behind the face so nothing is
coplanar. The depth into the plug is unchanged at 6.5 mm.

WHAT THIS BUILDS
----------------
Welding the boss back on is necessary but not sufficient. The lens where a
Ø13 post meets a Ø65 disc on a r=36 circle is 21.5 mm2, three millimetres
deep at its deepest, and the M3 that goes into that post is tightened along
the print's Z axis - a pure interlayer pull on the joint's weakest section.
So each boss also gets a root flare: a 45 degree frustum from Ø23 at the
plug's back face up to Ø13 over 5 mm.

    bonded cross-section at the back face:  21.5 mm2  ->  116.3 mm2

45 degrees exactly, so it needs no support. 5 mm tall, so it stays inside
the plug's own 8 mm thickness: the flare can never reach the front face,
which means it can never show in the ear port or foul the NeoPixel ring
seated in the Ø37.6 recess.

Every clearance the flare has to respect was measured in the file first, not
assumed:

| against                      | available | flare needs | left over |
| ---------------------------- | --------- | ----------- | --------- |
| shell wall, worst radius      | 7.78 mm  | 5.0 mm     | 2.78 mm  |
| blind thread z-24 (arm 290)   | 15.75 mm | 12.8 mm    | 2.95 mm  |
| ring recess r=18.8            | r 24.5   | -          | 5.7 mm   |
| next boss along               | 62.35 mm | 23.0 mm    | 39.3 mm  |

The shell-wall row is the binding one and it is checked again after the
union, per vertex, against `HEAD_SOLID` - a boss that leaves the head is the
failure this project has already had three times.
"""

import bpy
import bmesh
import math
import os
from mathutils import Matrix, Vector

HEAD_MOUNTS = r"C:\Humalien\cad\head_mounts.py"
SOLID = "HEAD_SOLID"
CRANIUM = "HEAD_CRANIUM"
PR_COLL = "print ready"
WELD = 1e-4             # mm; same tolerance export_plate.py welds at

# Ø23 down to Ø13 over 5.0 mm is a 45.0 degree wall - the steepest a printer
# takes without support, and the shallowest worth having. Do not raise
# FLARE_D without re-reading the clearance table above: 23 is set by the
# 15.75 mm from the 290 degree boss to the z-24 blind thread, not by taste.
FLARE_D = 23.0
FLARE_H = 5.0
# A cutter face coplanar with the face it emerges from is what sealed the
# +z blind thread over. Start every blind cutter this far behind the plug's
# back plane; the depth INTO the plug is unchanged.
OVERSHOOT = 2.0

BACKUP = r"C:\Humalien\Humalien_v1.prebossfix.blend"


def _hm():
    """head_mounts' helpers and its `M` table, without running anything.

    The numbers are read from head_mounts rather than repeated here on
    purpose: a boss circle defined twice is a boss circle that will disagree
    with itself. Executing the file only defines functions - `build()` is
    guarded and is not called.
    """
    ns = {"__name__": "head_mounts", "__file__": HEAD_MOUNTS}
    with open(HEAD_MOUNTS, "r", encoding="utf-8") as fh:
        exec(compile(fh.read(), HEAD_MOUNTS, "exec"), ns)
    return ns


# ---------------------------------------------------------------------------
# inspection
# ---------------------------------------------------------------------------
def loose_parts(ob):
    """[(verts, signed volume, (lo, hi))] one per connected component.

    Signed, because a NEGATIVE volume is an inward-facing shell - a sealed
    void inside the solid - and that is a defect this part actually had.
    """
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    seen, out = set(), []
    for v in bm.verts:
        if v in seen:
            continue
        stack, g = [v], []
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            g.append(x)
            for e in x.link_edges:
                o = e.other_vert(x)
                if o not in seen:
                    stack.append(o)
        faces = {f for w in g for f in w.link_faces}
        vol = sum(f.calc_area() * f.normal.dot(f.calc_center_median()) / 3.0
                  for f in faces)
        co = [w.co for w in g]
        lo = Vector((min(c.x for c in co), min(c.y for c in co),
                     min(c.z for c in co)))
        hi = Vector((max(c.x for c in co), max(c.y for c in co),
                     max(c.z for c in co)))
        out.append((len(g), vol, (lo, hi)))
    bm.free()
    out.sort(key=lambda r: -abs(r[1]))
    return out


def _health(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    openE = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    nonm = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    bm.free()
    return openE, nonm


# Three skew directions, and a majority vote. NOT axis-aligned, and not one
# ray: this part is nothing but cylinders and planes on the world axes, so an
# axis-aligned ray lands on a tangent surface or runs straight down a pilot
# bore and miscounts. Same trap as the ray_cast note in the project memory.
_DIRS = [Vector(d).normalized() for d in ((0.9137, 0.3184, 0.2513),
                                          (-0.2711, 0.8455, -0.4602),
                                          (0.1877, -0.3391, 0.9219))]


def _inside_test(name):
    """A point-in-solid test for one object, by ray crossing parity.

    `closest_point_on_mesh` and the sign of its normal was tried here first
    and is WRONG on this geometry - it called every vertex of `pi5_tray`
    outside by 641 mm, and inside the hub's own Ø22 grille and Ø37.6 recess
    it reported the concave surface's normal and flagged 82 vertices that
    are 25 mm deep in solid plastic. Parity does not care about concavity.
    Calibrated: a point at (500, 500, 500) reads outside, the head's centre
    reads inside, and `ear_spine` and `tray_rail` read fully inside.
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


def flare_clearance(ob, e):
    """(flare vertices, how many left the skin, how many are in the wall).

    Only the flare is measured. The bosses themselves end FLUSH with the
    shell's inner surface by design, so their end-cap vertices sit exactly on
    it and any inside/outside test of them is a coin toss - checking them
    would report noise as a fault. The flare is the new geometry and the only
    thing this repair could possibly have pushed somewhere it may not go.
    """
    in_skin = _inside_test(SOLID)
    in_wall = _inside_test(CRANIUM)
    if in_skin is None:
        return None, None, None
    back = e["face_x"] - e["plug_t"]
    top = back + FLARE_H
    axes = [_arm_xy(e, a) for a in e["arm_a"]]
    rim = e["plug_d"] / 2.0
    n = out = buried = 0
    for v in ob.data.vertices:
        p = ob.matrix_world @ v.co
        if not (back - 0.1 <= abs(p.x) <= top + 0.1):
            continue
        if math.hypot(p.y - e["y"], p.z - e["z"]) <= rim + 1e-6:
            continue                        # plug material, not flare
        if min(math.hypot(p.y - ay, p.z - az) for ay, az in axes) > FLARE_D / 2 + 0.2:
            continue                        # boss shaft above the flare
        n += 1
        if not in_skin(p):
            out += 1
        if in_wall is not None and in_wall(p):
            buried += 1
    return n, out, buried


def report(names=("ear_hub_R", "ear_hub_L", "ear_spine_R", "ear_spine_L")):
    """Print the state of each part. Changes nothing."""
    for n in names:
        ob = bpy.data.objects.get(n)
        if ob is None:
            print("%-14s MISSING" % n)
            continue
        parts = loose_parts(ob)
        openE, nonm = _health(ob)
        flag = "" if len(parts) == 1 else "   <-- NOT ONE SOLID"
        print("%-14s %d piece(s), open %d, non-manifold %d%s"
              % (n, len(parts), openE, nonm, flag))
        for i, (nv, vol, (lo, hi)) in enumerate(parts):
            note = "  <-- SEALED VOID" if vol < 0 else ""
            print("    piece %d: %4d verts  vol %8.1f mm3  "
                  "x %7.2f..%7.2f  y %7.2f..%7.2f  z %7.2f..%7.2f%s"
                  % (i, nv, vol, lo.x, hi.x, lo.y, hi.y, lo.z, hi.z, note))
    return True


# ---------------------------------------------------------------------------
# the repair
# ---------------------------------------------------------------------------
def _arm_xy(e, a):
    return (e["y"] + e["arm_r"] * math.cos(math.radians(a)),
            e["z"] + e["arm_r"] * math.sin(math.radians(a)))


def _built_arms(ob, e):
    """Which of the three nominal angles this hub actually has a boss at.

    Read off the object rather than recomputed, because `ear_hubs()` drops
    an arm whose raycast found under ARM_MIN of reach, and a flare built at
    an angle with no boss would be a lump of plastic standing in the head on
    its own. An angle counts as present if there is geometry within 2 mm of
    its axis, out beyond the plug's rim.
    """
    fx, r = e["face_x"], e["plug_d"] / 2.0
    got = []
    for a in e["arm_a"]:
        ay, az = _arm_xy(e, a)
        for v in ob.data.vertices:
            p = ob.matrix_world @ v.co
            if abs(p.x) < fx - e["plug_t"] - 0.5:
                continue
            if math.hypot(abs(p.y) - abs(ay), p.z - az) < 2.0 and \
               math.hypot(p.y - e["y"], p.z - e["z"]) > r:
                got.append(a)
                break
    return got


def weld_debt(ob):
    """How many vertices a weld WOULD merge. Reads only, changes nothing.

    This is the detector, and it has to be phrased this way. The obvious
    version - weld a copy and count non-manifold edges - always returns zero,
    because bmesh's remove_doubles deletes the collapsed faces as it goes and
    tidies the evidence away with them. Blender's plain health check is no
    better: two duplicate surfaces stacked exactly on each other both read as
    manifold, since every edge really does have two faces - there are simply
    two of every edge.

    The count of coincident vertices is the thing that survives both. It is
    also exactly what leaks into the STL: the hub carried 42 doubled vertices
    and exported with 84 zero-area triangles and 72 edges shared by four or
    six faces, on a mesh Blender called perfectly healthy.
    """
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    n0 = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=WELD)
    n1 = len(bm.verts)
    bm.free()
    return n0 - n1


def weld(ob):
    """Merge coincident vertices. Volume-preserving, and the only cleanup
    this project has tested as safe on its 99k-vertex sculpts.

    The flare's base cap lands in the same plane as the plug's back face and
    its top rim is tangent to the Ø13 shaft, so the union left duplicate
    geometry along both seams: 42 doubled vertices, 84 zero-area triangles
    and 72 doubled edges in the exported STL. `print_clean()` in
    export_plate.py cannot catch this - it returns early on anything already
    reading 0 open / 0 non-manifold, which this did.

    remove_doubles ONLY. Not dissolve_degenerate, which is what tore the head
    halves apart when print_clean was run unconditionally. Measured on the
    hub: 1425 -> 1383 vertices, 84 zero-area triangles -> 0, 72 bad edges ->
    0, and the volume identical at 23649.20 mm3 to four decimal places.
    """
    v0 = len(ob.data.vertices)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=WELD)
    bm.to_mesh(ob.data)
    bm.free()
    return v0, len(ob.data.vertices)


def _drop_voids(ob):
    """Delete inward-facing sealed shells. Returns how many went."""
    doomed = [p for p in loose_parts(ob) if p[1] < 0]
    if not doomed:
        return 0
    boxes = [b for _, _, b in doomed]
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    kill = []
    for v in bm.verts:
        for lo, hi in boxes:
            if (lo.x - 1e-4 <= v.co.x <= hi.x + 1e-4 and
                    lo.y - 1e-4 <= v.co.y <= hi.y + 1e-4 and
                    lo.z - 1e-4 <= v.co.z <= hi.z + 1e-4):
                kill.append(v)
                break
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(ob.data)
    bm.free()
    return len(doomed)


def repair(name, hm=None, force=False):
    """Weld and flare the bosses on one hub, in place."""
    hm = hm or _hm()
    e = hm["M"]["ear"]
    ob = bpy.data.objects[name]
    fx, pt = e["face_x"], e["plug_t"]
    back = fx - pt                      # 39.5: split plane, and the bed plane
    sx = -1.0 if name.endswith("_L") else 1.0

    n0 = len(loose_parts(ob))
    # Already welded? Then this has run before. Flaring a second time is not
    # harmless: the union is idempotent in shape but not in topology, and the
    # pilot re-cut would run against geometry it has already cut. Nothing in
    # this project should quietly do its work twice.
    if n0 == 1 and not force:
        print("  %-12s already one solid - repaired already, skipped. "
              "repair(force=True) to insist." % name)
        return ob
    voids = _drop_voids(ob)

    arms = _built_arms(ob, e)
    if not arms:
        raise RuntimeError("%s has no bosses to weld - refusing to guess" % name)

    # ---- the flares ----------------------------------------------------
    # Wide end at the plug's back face, narrow end 5 mm up. `_cyl` puts
    # radius2 (d2) at +X, so d is the base and d2 the top for the right hub;
    # the left is mirrored from the finished right, never built twice.
    flare = bmesh.new()
    for a in arms:
        ay, az = _arm_xy(e, a)
        hm["_cyl"](flare, FLARE_D, FLARE_H,
                   (sx * (back + FLARE_H / 2.0), ay, az), 'X',
                   d2=e["arm_d"])
    fob = hm["_link"](bpy.context.scene.collection, "_FLARE_%s" % name,
                      hm["_mesh"]("_FLARE_%s" % name, flare))
    hm["boolean"](ob, fob, 'UNION')
    bpy.data.objects.remove(fob, do_unlink=True)

    # ---- re-cut everything the flare just filled in ---------------------
    # The flare is solid, so the pilots that ran through it are gone. These
    # cutters are all disjoint from each other - the closest pair is the
    # 290 degree boss and the z-24 thread at 15.75 mm - so one batch is safe.
    # Nested cutters are what this file has been bitten by; these are not.
    cut = bmesh.new()
    for a in arms:                      # boss pilots, through
        ay, az = _arm_xy(e, a)
        hm["_cyl"](cut, hm["M"]["m3_pilot"], 34.0, (sx * (fx - 2.0), ay, az),
                   'X', segs=24)
    for sz in (-1, 1):                  # spine screws, blind, NOT coplanar
        depth = 6.5 + OVERSHOOT
        hm["_cyl"](cut, hm["M"]["m3_pilot"], depth,
                   (sx * (back - OVERSHOOT + depth / 2.0), e["y"],
                    e["z"] + sz * e["join_dz"]), 'X', segs=24)
    hm["_apply"](bpy.context.scene.collection, ob, cut, "_CUT_%s" % name,
                 'DIFFERENCE')

    weld(ob)

    try:
        hm["shade"](ob)
    except Exception:
        pass

    n1 = len(loose_parts(ob))
    print("  %-12s %d piece(s) -> %d, %d sealed void(s) removed, "
          "%d flare(s) at %s" % (name, n0, n1, voids, len(arms),
                                 tuple(int(a) for a in arms)))
    return ob


def mirror_onto(src_name, dst_name):
    """Give dst a mirrored copy of src's mesh, keeping dst's object.

    Same construction `ear_hubs()` uses, and for the same reason: the two
    hubs must be the same part, and building each separately is how they
    drift apart.
    """
    src = bpy.data.objects[src_name]
    dst = bpy.data.objects[dst_name]
    old = dst.data
    me = src.data.copy()
    me.name = dst_name
    me.transform(Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0)))
    if hasattr(me, "flip_normals"):
        me.flip_normals()
    dst.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    print("  %-12s mirrored from %s" % (dst_name, src_name))
    return dst


def refresh_plate_copies(bases=("ear_hub_R", "ear_hub_L")):
    """Point the `print ready` copies at the repaired meshes.

    The STLs come from the SOURCE objects, so this does not change what gets
    printed - but a plate copy that still shows the broken part is a plate
    copy that lies to whoever looks at the layout, and `verify()` would
    report it as a mismatch. Transforms are untouched: the hand arrangement
    that moved `ear_hub_L` onto plate 4 lives in those matrices and in
    nothing else.
    """
    coll = bpy.data.collections.get(PR_COLL)
    if coll is None:
        print("  no %r collection - nothing to refresh" % PR_COLL)
        return
    for base in bases:
        src = bpy.data.objects[base]
        for pr in coll.objects:
            if pr.name != "PR_" + base:
                continue
            keep = pr.matrix_world.copy()
            old = pr.data
            pr.data = src.data.copy()
            pr.data.name = pr.name
            pr.matrix_world = keep
            if old.users == 0:
                bpy.data.meshes.remove(old)
            print("  %-12s refreshed, transform kept" % pr.name)


def check(names=("ear_hub_R", "ear_hub_L"), hm=None):
    """Prove the repair. Returns True only if every part passes."""
    hm = hm or _hm()
    e = hm["M"]["ear"]
    ok, vols = True, []
    for n in names:
        ob = bpy.data.objects[n]
        parts = loose_parts(ob)
        openE, nonm = _health(ob)
        nf, out, buried = flare_clearance(ob, e)
        debt = weld_debt(ob)
        vol = sum(p[1] for p in parts)
        vols.append(vol)
        bad = []
        if len(parts) != 1:
            bad.append("%d pieces, NOT ONE SOLID" % len(parts))
        if openE or nonm:
            bad.append("open %d, non-manifold %d" % (openE, nonm))
        if debt:
            bad.append("%d coincident vertices - will export doubled edges "
                       "and zero-area faces" % debt)
        if not nf:
            bad.append("no flare geometry found")
        if out:
            bad.append("%d flare vertices OUTSIDE THE SKIN" % out)
        if buried:
            bad.append("%d flare vertices BURIED IN THE SHELL WALL" % buried)
        print("  %-12s %d piece, open %d, non-manifold %d, weld debt %d, "
              "vol %.1f mm3, %d flare verts (%d out of skin, %d in wall)  %s"
              % (n, len(parts), openE, nonm, debt, vol, nf or 0, out or 0,
                 buried or 0, "OK" if not bad else "FAIL: " + "; ".join(bad)))
        ok = ok and not bad
    # Relative, not absolute. The mirror tessellates the two hubs differently
    # and their volumes differ in the last bits - 2e-5 mm3 on 23649 - which is
    # the same float noise that made `verify()` in export_plate.py report all
    # nine plate-4 parts as different. 1e-6 relative is far tighter than any
    # real difference and far looser than the noise.
    if len(vols) == 2 and abs(vols[0] - vols[1]) > 1e-6 * max(vols):
        print("  the two hubs are NOT the same part: %.4f vs %.4f mm3"
              % (vols[0], vols[1]))
        ok = False
    return ok


def build(save=False, backup=True):
    """Repair both hubs, refresh the plate copies, prove the result.

    `save` defaults to False for the same reason `head_mounts.build()` does:
    nothing that changes geometry should also commit it. Look at the result,
    then call again with save=True - which writes a backup first.
    """
    hm = _hm()
    print("ear_hub_repair:")
    print("  before:")
    report(("ear_hub_R", "ear_hub_L"))
    print("  repairing:")
    repair("ear_hub_R", hm)
    mirror_onto("ear_hub_R", "ear_hub_L")
    refresh_plate_copies()
    print("  after:")
    ok = check(hm=hm)
    if not ok:
        print("  REPAIR FAILED - do not export, do not save")
        return False
    if save:
        if backup and not os.path.exists(BACKUP):
            bpy.ops.wm.save_as_mainfile(filepath=BACKUP, copy=True)
            print("  backup written: %s" % BACKUP)
        bpy.ops.wm.save_mainfile()
        print("  saved %s" % bpy.data.filepath)
    else:
        print("  NOT saved. build(save=True) when you have looked at it.")
    return True
