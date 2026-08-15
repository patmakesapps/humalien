"""The eye mechanism's own print plate, and its own export folder.

Run inside Blender, after `eye_v2.build()`:

    exec(open(r"C:\\Humalien\\cad\\eye_plate.py").read())
    build()        # lay every eye part out on one bed, in print orientation
    verify()       # the copies still match the parts they came from
    export()       # -> exports/eye/<part>_xN.stl

WHY THIS IS SEPARATE FROM export_plate.py
-----------------------------------------
`export_plate` reads a part's plate number back from the x position of its
`PR_` copy in the `print ready` collection, on a grid it shares with
`print_layout`. Adding the eye parts to that grid would mean touching a
layout that carries a hand arrangement nothing rebuilds - the ear hubs were
moved by hand and that position lives in the `.blend` only.

So the eye plate lives in its own collection, far off to one side, with its
own prefix. `export_plate.census()` cannot see it and cannot be confused by
it. What it does borrow is `print_clean()`, because the repairs that file
learned - zero-area slits from coplanar boolean seams, shells that were
never actually unioned - apply here exactly as they did to plate 4.

ELEVEN FILES, FOURTEEN PIECES
----------------------------
The axles, the pegs and the stems are symmetric about their own centre
plane, so left and right are the same object and each exports once with a
quantity of two. `chirality()` is what says so - and it has to, because
volume, bounding box and a vertex-to-centroid fingerprint are all identical
between a part and its mirror image, so none of the checks this project
already had could tell a copy from a reflection.

The eyelids are genuinely handed: the band runs from x 13.2 to 43 on one
side of its own hub.

The domes are exported as two files even though they are almost certainly
symmetric - every feature on them is either revolved about the eye axis or
lies on it. `chirality()` calls them handed, but that is the UV sphere's
tessellation rather than its shape, and one wasted print is cheaper than
being wrong about it.

ORIENTATION
-----------
Every rotation here comes from `eye_v2.printability()` rather than from
judgement: it reports the downward-facing area past 45 degrees and how far
above the bed it starts, and the orientation in this table is the one that
made that number smallest. Four parts come out with nothing overhanging at
all; the rest carry only the undersides of external round bosses, where a
flattened first millimetre costs nothing - the eyelid hangs on the TOP of
its tube, and the tilt shaft is glued.
"""

import bpy
import bmesh
import math
import os
from mathutils import Matrix, Vector

EXPORTS = r"C:\Humalien\exports\eye"
EXPORT_PLATE = r"C:\Humalien\cad\export_plate.py"
COLL = "eye plate"
PREFIX = "EP_"

BED = 256.0
MARGIN = 6.0        # from the bed's edge
GAP = 5.0           # between parts
PACK_W = 190.0      # wrap to a new row here rather than at the bed's edge.
                    # Packed to the full 256 it came out 251 wide, which
                    # fits and leaves nowhere for a skirt; there is plenty
                    # of depth spare, so spend it.
ORIGIN = Vector((3000.0, 0.0, 0.0))     # well clear of every other plate

# +Y up: the part's own +Y becomes the print's +Z.
Y_UP = Matrix.Rotation(math.radians(90), 4, 'X')
Y_DOWN = Matrix.Rotation(math.radians(-90), 4, 'X')
X_UP = Matrix.Rotation(math.radians(-90), 4, 'Y')
FLAT = Matrix.Identity(4)

# name, quantity, rotation, why it is that way up
PARTS = [
    ("eye_frame",    1, Y_UP,   "flat on its arch; nothing behind it to foul"),
    ("eye_gimbal",   1, Y_UP,   "flat in its own plane, both bores roofed"),
    ("eye_pan_bar",  1, Y_UP,   "flat"),
    ("eye_dome_R",   1, Y_UP,   "back face down - the only face it has"),
    ("eye_dome_L",   1, Y_UP,   "back face down"),
    ("eye_lid_R",    1, Y_UP,   "back down"),
    ("eye_lid_L",    1, Y_UP,   "back down"),
    ("eye_stem_R",   2, Y_DOWN, "spigot face down; every layer smaller than "
                                "the one below it. Symmetric, so one file "
                                "serves both sides"),
    ("eye_axle_R",   2, FLAT,   "standing on end - the only way to get a "
                                "round journal; L and R are the same part"),
    ("eye_shaft",    1, X_UP,   "standing on end"),
    ("eye_peg_R",    2, Y_UP,   "standing on end; L and R are the same part"),
]


def chirality(name):
    """Is this part its own mirror image, so one file can serve both sides?

    Nothing else this project measures can answer it. A mirror image has the
    same volume, the same bounding box, and the same sorted
    vertex-to-centroid distances as the part it reflects - reflection
    preserves every one of those. So each vertex is tagged with its SIGNED
    offset along x as well, and the question becomes whether negating x
    reproduces the same set.

    It compares meshes, not shapes, so a symmetric part tessellated
    asymmetrically reads as handed. That is the safe direction to be wrong
    in: it costs a file, not a mirrored part.
    """
    o = bpy.data.objects.get(name)
    if o is None:
        return None
    vs = [o.matrix_world @ v.co for v in o.data.vertices]
    n = len(vs)
    if not n:
        return None
    c = Vector((sum(v.x for v in vs) / n, sum(v.y for v in vs) / n,
                sum(v.z for v in vs) / n))
    fwd = sorted((round((v - c).length, 3), round(v.x - c.x, 3)) for v in vs)
    mir = sorted((round((v - c).length, 3), round(-(v.x - c.x), 3)) for v in vs)
    return fwd == mir


def _ep():
    ns = {"__name__": "export_plate", "__file__": EXPORT_PLATE}
    with open(EXPORT_PLATE, "r", encoding="utf-8") as fh:
        exec(compile(fh.read(), EXPORT_PLATE, "exec"), ns)
    return ns


def _oriented(src, rot):
    """A copy of `src`, rotated to print, sitting on z=0 about its own centre.

    Measured from the VERTICES, not from `bound_box`. bound_box is the
    object's LOCAL box, and transforming its eight corners by a rotation
    gives the rotated box, whose axis-aligned extent is larger than the part.
    That reported a O40 x 6 ring as 56 x 54 x 44 once and made a correct
    rotation look broken.
    """
    ob = src.copy()
    ob.data = src.data.copy()
    ob.matrix_world = rot @ src.matrix_world
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts),
                 min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts),
                 max(p.z for p in pts)))
    ob.matrix_world = Matrix.Translation(
        (-(lo.x + hi.x) / 2.0, -(lo.y + hi.y) / 2.0, -lo.z)) @ ob.matrix_world
    return ob, (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z)


def build(save=False):
    """Lay every eye part out on one bed, each in the way up it prints."""
    old = bpy.data.collections.get(COLL)
    if old:
        for o in list(old.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(old)
    coll = bpy.data.collections.new(COLL)
    bpy.context.scene.collection.children.link(coll)

    # Shelf packing, tallest footprint first. Crude, and it does not need to
    # be anything else: the whole mechanism is a fraction of one bed.
    made = []
    for name, qty, rot, why in PARTS:
        src = bpy.data.objects.get(name)
        if src is None:
            print("  %-14s MISSING - run eye_v2.build() first" % name)
            continue
        made.append((name, qty, rot, why, src))
    sized = []
    for name, qty, rot, why, src in made:
        ob, dims = _oriented(src, rot)
        bpy.data.objects.remove(ob, do_unlink=True)
        sized.append((dims[1], name, qty, rot, why, src, dims))
    sized.sort(reverse=True)

    x, y, row_d = MARGIN, MARGIN, 0.0
    placed = []
    for depth, name, qty, rot, why, src, dims in sized:
        for i in range(qty):
            if x + dims[0] > PACK_W - MARGIN:
                x, y = MARGIN, y + row_d + GAP
                row_d = 0.0
            ob, _d = _oriented(src, rot)
            ob.name = "%s%s%s" % (PREFIX, name, "" if qty == 1 else "_%d" % (i + 1))
            coll.objects.link(ob)
            ob.matrix_world = Matrix.Translation(
                ORIGIN + Vector((x + dims[0] / 2.0, y + dims[1] / 2.0, 0.0))
            ) @ ob.matrix_world
            placed.append((ob.name, dims, why))
            x += dims[0] + GAP
            row_d = max(row_d, dims[1])
    used_y = y + row_d + MARGIN

    print("eye plate: %d pieces, %d files" % (len(placed), len(PARTS)))
    for nm, d, why in placed:
        print("  %-20s %6.1f x %6.1f x %6.1f mm   %s"
              % (nm[len(PREFIX):], d[0], d[1], d[2], why))
    ext = [o for o in coll.objects]
    if ext:
        pts = [o.matrix_world @ v.co for o in ext for v in o.data.vertices]
        used_x = max(p.x for p in pts) - ORIGIN.x + MARGIN
        used_y = max(p.y for p in pts) - ORIGIN.y + MARGIN
    print("  bed used: %.0f x %.0f of %.0f x %.0f mm"
          % (used_x, used_y, BED, BED))
    if used_y > BED:
        print("  *** DOES NOT FIT - %.0f mm over ***" % (used_y - BED))
    if save:
        bpy.ops.wm.save_mainfile()
    return coll


def _fingerprint(ob):
    """Vertex and face counts, plus the sorted vertex-to-centroid distances,
    in LOCAL coordinates. Position and rotation cannot change it; a different
    shape with the same vertex count can."""
    vs = [v.co for v in ob.data.vertices]
    n = len(vs)
    if not n:
        return (0, 0, ())
    c = Vector((sum(v.x for v in vs) / n, sum(v.y for v in vs) / n,
                sum(v.z for v in vs) / n))
    return (n, len(ob.data.polygons),
            tuple(sorted(round((v - c).length, 4) for v in vs)))


def verify():
    """Does every copy on the plate still match the part it came from?"""
    coll = bpy.data.collections.get(COLL)
    if coll is None:
        print("no %s collection - run build() first" % COLL)
        return False
    ok = True
    for ob in sorted(coll.objects, key=lambda o: o.name):
        base = ob.name[len(PREFIX):]
        if base[-2:-1] == "_" and base[-1].isdigit():
            base = base[:-2]
        src = bpy.data.objects.get(base)
        if src is None:
            print("  %-22s no source object" % ob.name)
            ok = False
            continue
        same = _fingerprint(ob) == _fingerprint(src)
        print("  %-22s %s %s" % (ob.name, "==" if same else "!=", base))
        ok = ok and same
    print("verify(): %s" % ("PASS" if ok else "FAIL"))
    return ok


def export(out_dir=EXPORTS):
    """Write exports/eye/<part>_xN.stl, one file per distinct shape."""
    ep = _ep()
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for name, qty, rot, why in PARTS:
        src = bpy.data.objects.get(name)
        if src is None:
            print("  %-14s MISSING - not exported" % name)
            continue
        ob, dims = _oriented(src, rot)
        bpy.context.scene.collection.objects.link(ob)
        was, now = ep["print_clean"](ob)
        if was != now:
            print("  %-16s repaired: open %d->%d, non-manifold %d->%d, "
                  "zero-area %d->%d" % (name, was[0], now[0], was[1], now[1],
                                        was[2], now[2]))
        if now[0] or now[1]:
            print("  %-16s NOT WATERTIGHT: open %d, non-manifold %d"
                  % (name, now[0], now[1]))
        path = os.path.join(out_dir, "%s_x%d.stl" % (name.lower(), qty))
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True,
                              global_scale=1.0, apply_modifiers=True)
        bpy.data.objects.remove(ob, do_unlink=True)
        written.append((os.path.basename(path), dims, qty))
    print("")
    print("wrote %d files to %s" % (len(written), out_dir))
    for fn, d, qty in written:
        print("  %-28s %6.1f x %6.1f x %6.1f mm   print %d"
              % (fn, d[0], d[1], d[2], qty))
    print("")
    print("the _xN in the name is how many to set in the slicer, not how")
    print("many bodies are in the file.")
    return written
