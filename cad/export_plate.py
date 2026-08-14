"""Export one print plate as bed-ready STLs, into `exports/plate<N>/`.

Run inside Blender:

    exec(open(r"C:\\Humalien\\cad\\export_plate.py").read())
    export_plate(4)          # one plate
    export_plate()           # every plate that has parts on it

Which parts are on which plate is read from the live `print ready`
collection, not from a list here. That is the point: the layout in the
`.blend` includes hand moves - `ear_hub_L` was dragged between plates once
already - and a list in a file would quietly disagree with what you are
looking at on screen.

Orientation comes from `print_layout.PARTS`, so each file lands already
rotated the way it should be sliced and dropped onto z=0. Import one and it
is on the bed the right way up, no rotating in the slicer.

The exported geometry comes from the ORIGINAL object, not from the plate
copy. The copies are for looking at; if one ever drifts from its source the
STL still gets the real part. `verify()` below is what proves they agree.

Naming is `<part>_x<qty>.stl`, and `_xN` is the quantity to set in the
slicer - the file holds one body. Four `cable_anchor` copies on plate 3
means one `cable_anchor_x4.stl` and you type 4.

**exports/ is git-ignored on purpose.** HEAD_FACE and HEAD_CRANIUM derive
from a head sculpt that is royalty-free under a **No AI** licence: free to
use in this build, not free to redistribute. Everything cut from it inherits
that. See the note at the top of print_layout.py.
"""

import bpy
import bmesh
import os
from mathutils import Matrix, Vector

OUT_ROOT = r"C:\Humalien\exports"
LAYOUT = r"C:\Humalien\cad\print_layout.py"
COLL = "print ready"

# The plate grid the `print ready` layout was built on. A part's plate is
# read back from its x position, so these three numbers have to match the
# ones the layout was written with.
BED, PLATE_GAP, ORIGIN_X = 256.0, 60.0, 320.0


def _rotations():
    """The print orientation table, without importing print_layout's build()."""
    ns = {"__name__": "print_layout", "__file__": LAYOUT, "bpy": bpy}
    with open(LAYOUT, "r", encoding="utf-8") as fh:
        exec(compile(fh.read(), LAYOUT, "exec"), ns)
    # Coupons and anything else not in PARTS print flat as built, so an
    # identity rotation is the right default rather than an error.
    return {name: rot for name, qty, rot, note in ns["PARTS"]}


WELD = 1e-4         # mm; vertices this close are the same vertex
SLIT_TOL = 1e-3     # mm; a boundary loop this flat encloses no volume


def _boundary_loops(bm):
    """Open edges, grouped into the loops they form."""
    seen, loops = set(), []
    for e in bm.edges:
        if len(e.link_faces) != 1 or e in seen:
            continue
        stack, loop = [e], []
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            loop.append(x)
            for v in x.verts:
                for y in v.link_edges:
                    if y not in seen and len(y.link_faces) == 1:
                        stack.append(y)
        loops.append(loop)
    return loops


def _health(ob):
    """(open edges, non-manifold edges, zero-area faces) for one object."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    openE = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    nonm = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    zero = sum(1 for f in bm.faces if f.calc_area() < 1e-9)
    bm.free()
    return openE, nonm, zero


def _bounds(ob):
    pts = [v.co for v in ob.data.vertices]
    if not pts:
        return None
    return (Vector((min(p.x for p in pts), min(p.y for p in pts),
                    min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts),
                    max(p.z for p in pts))))


def print_clean(ob):
    """Make an export copy watertight without touching the source part.

    Two defects show up in this project's parts, and neither is a modelling
    mistake worth chasing back into the CAD:

    **Zero-area slits.** Four-edge loops collapsed onto a line - span
    1.10 x 0.00 x 0.00 - left where a coplanar boolean seam produced a
    T-junction: three short collinear edges tiling one long one, with a
    zero-area face missing between them. Four of the five coupons have them,
    `ear_hub` has two, and `eye_bezel_L` has had them since it was drawn.
    They enclose no volume, but they read as holes and every slicer stops to
    repair them. Filled here - and ONLY when the loop really is a slit, so a
    hole with actual area gets reported as the modelling bug it would be
    rather than quietly papered over.

    **Overlapping shells.** `ear_spine` is a box with two Ø9 posts pushed
    through it, all merged into one bmesh with no union: three closed shells
    sharing a volume, which welds into 48 edges used more than twice. A
    slicer will union it correctly, but it should not have to guess.

    Both are repaired here, on the throwaway copy, so `Humalien_v1.blend`
    keeps the geometry that has been inspected and signed off. The union is
    checked afterwards and rolled back if it moved anything: EXACT has
    destroyed parts in this file before, which is why `boolean()` in
    head_mounts.py uses MANIFOLD.

    Returns (before, after) health tuples.
    """
    before = _health(ob)

    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=WELD)
    bmesh.ops.dissolve_degenerate(bm, dist=WELD, edges=bm.edges[:])

    slits, real = [], 0
    for loop in _boundary_loops(bm):
        pts = [v.co for v in {v for e in loop for v in e.verts}]
        span = sorted(max(p[i] for p in pts) - min(p[i] for p in pts)
                      for i in range(3))
        if span[1] < SLIT_TOL:          # two of three extents are nothing
            slits.extend(loop)
        else:
            real += 1
    if slits:
        bmesh.ops.holes_fill(bm, edges=slits, sides=0)
    if real:
        print("      %d boundary loop(s) with real area - NOT filled, "
              "this is a modelling bug" % real)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()

    if _health(ob)[1] > 0:              # still self-intersecting - union it
        keep = ob.data.copy()
        box = _bounds(ob)
        bpy.context.view_layer.objects.active = ob
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        ob.select_set(True)
        try:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.intersect_boolean(operation='UNION', use_self=True,
                                           solver='EXACT')
            bpy.ops.object.mode_set(mode='OBJECT')
        except RuntimeError as exc:
            print("      self-union failed (%s) - keeping the original" % exc)
            ob.data = keep
        else:
            now = _bounds(ob)
            moved = (now is None or box is None or
                     max((now[0] - box[0]).length, (now[1] - box[1]).length) > 0.01)
            if moved or not ob.data.vertices:
                print("      self-union moved the part - rolled back")
                ob.data = keep
            else:
                bpy.data.meshes.remove(keep)

    return before, _health(ob)


def _base_name(pr_name):
    """PR_cable_anchor_3 -> cable_anchor, PR_ear_hub_R -> ear_hub_R."""
    base = pr_name[3:]
    if len(base) > 2 and base[-2] == "_" and base[-1].isdigit():
        base = base[:-2]
    return base


def census():
    """{plate number: {part: quantity}} read off the live layout."""
    coll = bpy.data.collections.get(COLL)
    if coll is None:
        raise RuntimeError("no %r collection - nothing to export from" % COLL)
    plates = {}
    for ob in coll.objects:
        if not ob.name.startswith("PR_"):
            continue                        # bed outlines, labels, titles
        pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        cx = sum(p.x for p in pts) / len(pts)
        n = int(round((cx - ORIGIN_X - BED / 2) / (BED + PLATE_GAP))) + 1
        base = _base_name(ob.name)
        plates.setdefault(n, {}).setdefault(base, 0)
        plates[n][base] += 1
    return plates


def export_plate(plate=None, out_root=OUT_ROOT):
    """Write `exports/plate<N>/<part>_x<qty>.stl` for one plate, or all."""
    plates = census()
    want = sorted(plates) if plate is None else [plate]
    written = []

    for n in want:
        if n not in plates:
            print("plate %d holds nothing" % n)
            continue
        out_dir = os.path.join(out_root, "plate%d" % n)
        os.makedirs(out_dir, exist_ok=True)
        rows = []

        for base in sorted(plates[n]):
            src = bpy.data.objects.get(base)
            if src is None:
                rows.append((base, plates[n][base], None, None, None,
                             "SOURCE OBJECT MISSING - not exported"))
                continue
            qty = plates[n][base]

            ob = src.copy()
            ob.data = src.data.copy()
            bpy.context.scene.collection.objects.link(ob)
            ob.matrix_world = ROT.get(base, Matrix.Identity(4)) @ src.matrix_world

            # Measure from the VERTICES, not ob.bound_box. bound_box is the
            # object's local box; transforming its eight corners by a
            # rotation that is not about one world axis gives the rotated
            # box, whose axis-aligned extent is bigger than the part. That
            # reported a Ø40 x 6 ring as 56 x 54 x 44 once and made a
            # correct rotation look broken.
            pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
            lo = Vector((min(p.x for p in pts), min(p.y for p in pts),
                         min(p.z for p in pts)))
            hi = Vector((max(p.x for p in pts), max(p.y for p in pts),
                         max(p.z for p in pts)))
            ob.matrix_world = Matrix.Translation(
                (-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)) @ ob.matrix_world

            was, now = print_clean(ob)
            if was != now:
                print("  %-20s repaired: open %d->%d, non-manifold %d->%d, "
                      "zero-area %d->%d" % (base, was[0], now[0], was[1],
                                            now[1], was[2], now[2]))
            # Zero-area faces are not a defect here - they are the faces
            # print_clean() just added to close the slits, and a triangle
            # with no area contributes nothing to any slice plane. Open and
            # non-manifold edges are the two that would really bite.
            if now[0] or now[1]:
                print("  %-20s NOT WATERTIGHT: open %d, non-manifold %d"
                      % (base, now[0], now[1]))

            path = os.path.join(out_dir, "%s_x%d.stl" % (base.lower(), qty))
            for o in bpy.context.view_layer.objects:
                o.select_set(False)
            ob.select_set(True)
            bpy.context.view_layer.objects.active = ob
            bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True,
                                  global_scale=1.0, apply_modifiers=True)
            bpy.data.objects.remove(ob, do_unlink=True)

            dx, dy, dz = hi.x - lo.x, hi.y - lo.y, hi.z - lo.z
            rows.append((base, qty, dx, dy, dz,
                         os.path.basename(path)))
            written.append(path)

        if any(base.startswith("HEAD_") for base in plates[n]):
            print("  NOTE: this plate is cut from the No-AI-licence head")
            print("        sculpt. Print it, do not commit it - .gitignore")
            print("        keeps exports/plate1 and plate2 out of git.")
        print("PLATE %d  ->  %s" % (n, out_dir))
        print("  %-20s qty  footprint          height  file" % "part")
        for base, qty, dx, dy, dz, note in rows:
            if dx is None:
                print("  %-20s %3d  %s" % (base, qty, note))
            else:
                print("  %-20s %3d  %6.1f x %6.1f  %6.1f  %s"
                      % (base, qty, dx, dy, dz, note))
        print("")

    print("%d files written" % len(written))
    return written


SHAPE_TOL = 1e-3        # mm; see the note in _shape()


def _shape(ob):
    """Position- and rotation-invariant identity for a mesh.

    Vertex and face counts, the object's scale, and the sorted distances of
    every vertex from the centroid. Two objects are the same shape, wherever
    they sit and however they are turned, iff all four agree.

    Measured in LOCAL coordinates, and that is the whole trick. Measuring
    after `matrix_world` is mathematically identical - a rotation preserves
    distances - but not numerically: the plate copies carry a different
    transform from their sources, and the arithmetic disagrees in the last
    bits. Doing it in world space made all nine plate-4 parts look different
    at a rounding of 1e-4 mm when the real disagreement was 8e-4 mm of float
    noise and the local distances were bit-identical. Hence local
    coordinates, and hence a tolerance rather than equality: scale is
    checked separately, so local space is not hiding a stretched copy.
    """
    if not ob.data.vertices:
        return (0, 0, (0, 0, 0), ())
    vs = [v.co.copy() for v in ob.data.vertices]
    c = sum(vs, Vector()) / len(vs)
    scale = tuple(round(s, 6) for s in ob.matrix_world.to_scale())
    return (len(vs), len(ob.data.polygons), scale,
            sorted((v - c).length for v in vs))


def _same(a, b):
    if a[:3] != b[:3]:
        return False
    return all(abs(x - y) <= SHAPE_TOL for x, y in zip(a[3], b[3]))


def verify(plate=None):
    """Check every plate copy is still the same shape as its source part.

    The copies are what you inspect on screen; the STLs come from the
    sources. If those two ever disagree you are printing something you have
    not looked at, which is the failure this catches.
    """
    plates = census()
    want = sorted(plates) if plate is None else [plate]
    coll = bpy.data.collections[COLL]
    bad = 0
    checked = 0
    for ob in coll.objects:
        if not ob.name.startswith("PR_"):
            continue
        base = _base_name(ob.name)
        pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        cx = sum(p.x for p in pts) / len(pts)
        n = int(round((cx - ORIGIN_X - BED / 2) / (BED + PLATE_GAP))) + 1
        if n not in want:
            continue
        src = bpy.data.objects.get(base)
        if src is None:
            print("  %-24s SOURCE MISSING" % ob.name)
            bad += 1
            continue
        checked += 1
        fo, fs = _shape(ob), _shape(src)
        if not _same(fo, fs):
            why = ("verts %d vs %d" % (fo[0], fs[0]) if fo[0] != fs[0]
                   else "faces %d vs %d" % (fo[1], fs[1]) if fo[1] != fs[1]
                   else "scale %s vs %s" % (fo[2], fs[2]) if fo[2] != fs[2]
                   else "same counts, different shape")
            print("  %-24s DIFFERS from %-20s %s" % (ob.name, base, why))
            bad += 1
    print("%d plate copies checked, %d mismatches" % (checked, bad))
    return bad == 0


ROT = _rotations()
