"""The gates. Every one of these was bought with a broken part.

This is the part of v1 that survives into v2 unchanged, and it is deliberately
NOT the geometry. The shapes were all redrawn; these were not, because each
one is the answer to a specific thing that came off the printer wrong and no
amount of redrawing makes the question go away.

    printcheck / _print_stats   eye_frame laid "flat on its arch" touched the
                                bed with 0.0 mm2 of a 2236 mm2 shadow - 104 mm
                                of part balanced on one 4.8 mm edge. It had no
                                overhang problem worth the name and was
                                completely unprintable.

    aircheck / _air_stats       the first eye mechanism was printed, assembled
                                and snapped in three places, and printcheck had
                                returned READY for all of it. It measured how a
                                part SITS. Nothing measured what a part HANGS
                                OVER. The threshold is derived from the seven
                                STLs that were actually printed: worst survivor
                                9.4 mm2, best casualty 24.6, so the limit is 15.

    print_clean                 eight of nine parts left Blender not watertight
                                and it had gone unnoticed because the plate
                                before them happened to be clean.

    weld_debt                   42 coincident vertices on a mesh Blender called
                                perfectly healthy, which exported as 84
                                zero-area triangles. The obvious detector -
                                weld a copy, count non-manifold edges - always
                                returns zero, because remove_doubles tidies the
                                collapsed faces away as it goes.

    loose_parts                 each ear hub exported as FIVE separate solids
                                and every health check passed, because four
                                disconnected closed shells are four perfectly
                                healthy closed shells.

    chirality                   volume, bounding box and a vertex-to-centroid
                                fingerprint are ALL identical between a part and
                                its mirror image, so nothing else this project
                                measures can tell a copy from a reflection.

    _inside_test                point-in-solid by ray parity, majority of three
                                skew directions. The closest-point-and-normal
                                version reports hundreds of false positives on a
                                sculpt with concave features.

Extracted verbatim from eye_plate.py, export_plate.py and ear_hub_repair.py
when those were retired on 16 Aug 2026. Retyped code is code with new bugs in
it, so this was moved by script rather than by hand.

`_print_stats` and `_air_stats` take (name, rotation) and are plate-agnostic.
The v1 callers walked a hard-coded PARTS table; `gate()` below takes any list
of (name, rotation) instead.
"""

import bpy
import bmesh
import math
from mathutils import Matrix, Vector


# +Y up: the part's own +Y becomes the print's +Z.
Y_UP = Matrix.Rotation(math.radians(90), 4, 'X')
Y_DOWN = Matrix.Rotation(math.radians(-90), 4, 'X')
X_UP = Matrix.Rotation(math.radians(-90), 4, 'Y')
X_DOWN = Matrix.Rotation(math.radians(90), 4, 'Y')      # the mirror of X_UP
Z_DOWN = Matrix.Rotation(math.radians(180), 4, 'X')     # the part's -Z is up
FLAT = Matrix.Identity(4)




# A first layer is judged against the part's OWN shadow, never against a flat
# mm2 threshold. A O5 peg on its end contacts 19.5 mm2 and that is the whole
# of it - 100% - while eye_frame laid on its arch contacted 0.0 of a 2236 mm2
# shadow. An absolute limit calls the first one a failure and, set low enough
# to pass it, calls the second one a pass. The ratio separates them cleanly.
MIN_BED_FRAC = 0.15
# Between this and MIN_BED_FRAC a part is standing on a small but real face,
# which is what a brim is for: it buys bed adhesion and changes no geometry.
# Below it, or on less than BRIM_MIN_MM2 of actual face, the contact is a line
# or a point and no brim saves it - eye_frame on its arch touched 0.0 mm2.
BRIM_BED_FRAC = 0.10
BRIM_MIN_MM2 = 40.0
# What actually sags is near-horizontal roof, not steep wall. A hollow sphere
# printed open-side-down has hundreds of mm2 past 45 degrees and prints
# perfectly, because each layer oversails the one below it by a fraction of a
# millimetre the whole way up; a flat ceiling the same area drops onto
# nothing. So the limit is on area within ROOF_CONE of straight down, and the
# 45-degree figure is reported beside it rather than judged.
# and it is the largest CONNECTED, COPLANAR patch that is judged, not the
# total. Total area fails a horizontal O9 tube, whose underside is 63 mm2
# within 20 degrees of down and which prints perfectly, for the same reason
# the domes do: it is curved, so every layer oversails the one below it by a
# fraction of a millimetre. A patch is what drops onto nothing. Measured
# against the gimbal's own pre-fix STL this reads 565 mm2 in ONE patch out of
# 790 total - so it is a sharper test than the total was, not a looser one,
# and it would have failed that part on its own.
MAX_ROOF = 100.0
ROOF_CONE = 20.0
ROOF_COPLANAR = 5.0     # degrees; faces within this of each other are one patch


# --- what this file missed the first time ---------------------------------
# `printcheck()` returned READY for a plate on which two members broke on
# first assembly: the frame's mast and both eyelid cranks. Both were slender
# things printed as unsupported cantilevers, and neither test above can see
# that, for two different reasons.
#
#   the crank  a 3 x 18 mm slab lying FLAT, 3.9 mm above the bed, with
#              nothing under it but air. 24.6 mm2 - and MAX_ROOF is 100.
#   the mast   an 80.7 mm2 slope 23 degrees off horizontal, starting 17.3 mm
#              up. ROOF_CONE is 20, so it was never even counted.
#
# What both have in common, and what NOTHING here was measuring, is that
# there was no material underneath them. Area is not the question; a 68 mm2
# ledge over a wall is a ledge and a 25 mm2 one over nothing is a failure.
#
# So: down-facing area whose straight-down ray misses the rest of the part,
# grouped into connected COPLANAR patches, and the coplanarity is what makes
# one number enough. A cantilever's underside is one flat face and stays one
# patch however big it gets; a sphere's flank or a cylinder's belly is
# hundreds of faces at slightly different angles and falls apart into
# nothing. That is the same argument the roof test makes, and it is why the
# dome - which is 104 mm2 of down-facing surface over open air, and prints
# perfectly - scores 3.
#
# The threshold is not taste. It is what separates the seven STLs that were
# actually printed, five of which came out fine:
#
#     biggest connected ON-AIR patch, mm2          ceiling(20)   past 55(35)
#       eye_frame   BROKE - the mast                      0.0          80.7
#       eye_lid_R   BROKE - the crank                    24.6          24.6
#       eye_gimbal  printed fine                          6.9           9.4
#       eye_stem_R  printed fine                          7.6           7.6
#       eye_dome_R  printed fine                          0.0           3.2
#       eye_pan_bar printed fine                          0.0           0.0
#       eye_axle_R  printed fine                          0.0           0.0
#
# 9.4 is the worst part that survived and 24.6 the best that did not, so 15
# sits with a 1.6x margin on both sides. The two cone angles collapse into
# one once patches are grouped tightly, so only the 35-degree one is kept -
# it is the usual "support past 55 degrees of overhang" line, and a flat
# ceiling is inside it anyway.
AIR_SKIRT = 1.5         # the first 1.5 mm is carried by the first layers
                        # and the brim; below this a step is not a cantilever
AIR_MAX = 15.0          # mm2, largest connected coplanar patch over nothing
AIR_CONE = 35.0         # degrees off straight down = 55 degrees of overhang
AIR_COPLANAR = 5.0      # and this is the load-bearing one - see above
# Overhang within this of the top is exempt: on the domes it is the hollow's
# own ceiling, which no orientation turns downward and which closes over a
# cavity nothing prints into.
TOP_BAND = 3.0


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


def _print_stats(name, rot, limit=45.0):
    """(bed contact, unsupported area, how high it starts, height) in the
    orientation this part actually prints, not in a default one.

    The build direction is derived from the part's own row in PARTS. Asking
    `eye_v2.printability()` for all eleven with one direction - which is what
    it does by default - measures four of them the wrong way up and reports
    numbers that belong to nothing.
    """
    ob = bpy.data.objects.get(name)
    if ob is None:
        return None
    u = (rot.to_3x3().transposed() @ Vector((0.0, 0.0, 1.0))).normalized()
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.transform(bm, verts=bm.verts[:], matrix=ob.matrix_world)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    d = {v: v.co.dot(u) for v in bm.verts}
    lo = min(d.values())
    hi = max(d.values())
    tall = hi - lo
    cos_lim = -math.cos(math.radians(90.0 - limit))
    cos_roof = -math.cos(math.radians(ROOF_CONE))
    bed = air = roof = shadow = flat = 0.0
    worst = 0.0
    roof_faces = []
    for f in bm.faces:
        a = f.calc_area()
        nu = f.normal.normalized().dot(u)
        # The part's shadow on the bed. Every vertical line through a closed
        # solid crosses it an even number of times, so summing |a * n.u| over
        # every face counts the silhouette exactly twice.
        shadow += abs(a * nu)
        if max(d[v] for v in f.verts) - lo < 0.15:
            bed += a
        if nu < cos_lim:
            h = f.calc_center_median().dot(u) - lo
            if h < 1.0:
                continue                    # a chamfer the first layers carry
            if h >= tall - TOP_BAND:
                roof += a                   # the top of the part / a cavity
            else:
                air += a
                worst = max(worst, h)
                if nu < cos_roof:           # near-horizontal: this is what sags
                    roof_faces.append(f)

    # Grow the near-horizontal faces into connected coplanar patches and keep
    # the biggest. A curved underside breaks into many small patches; a real
    # ceiling stays one.
    cos_cop = math.cos(math.radians(ROOF_COPLANAR))
    pool = set(roof_faces)
    while pool:
        seed = pool.pop()
        n0 = seed.normal.normalized()
        patch = seed.calc_area()
        stack = [seed]
        while stack:
            f = stack.pop()
            for e in f.edges:
                for g in e.link_faces:
                    if g in pool and g.normal.normalized().dot(n0) >= cos_cop:
                        pool.discard(g)
                        patch += g.calc_area()
                        stack.append(g)
        flat = max(flat, patch)
    bm.free()
    return bed, air, worst, tall, shadow / 2.0, roof, flat


def _air_stats(name, rot):
    """The largest connected patch of this part that prints over NOTHING.

    Returns (area, height, total) - the biggest coplanar patch, how far up
    it starts, and how much down-facing area is over air altogether. Only
    the first is judged; the third is there because it is the number that
    looks alarming and is not, and seeing them side by side is what makes
    the point that area alone decides nothing.

    "Over nothing" is a ray straight down from each face's own centre. It is
    the cheapest honest version of the question a slicer asks layer by
    layer, and it is exact for the shapes on this plate, which are all
    boxes, cylinders and spheres. What it would get wrong is a face
    overhanging a wall that is beside it rather than beneath it - a bridge
    landing - and there are none of those here.
    """
    src = bpy.data.objects.get(name)
    if src is None:
        return None
    ob, _dims = _oriented(src, rot)
    bpy.context.scene.collection.objects.link(ob)
    # BAKE the orientation into the mesh and clear the matrix. `Object.
    # ray_cast` takes and returns LOCAL coordinates, and `_oriented` puts the
    # print orientation in `matrix_world` - so a face normal read off the
    # bmesh and a ray fired at it are in two different frames. Left that way
    # this reported the pan bar, which prints flat and has no overhang at
    # all, as a 204 mm2 ceiling: it was reading the part's TOP face as
    # down-facing. Triangulate in the same pass, because the part is a
    # boolean result and ray_cast wants triangles it can trust.
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.transform(bm, verts=bm.verts[:], matrix=ob.matrix_world)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()
    ob.matrix_world = Matrix.Identity(4)

    bm = bmesh.new()
    bm.from_mesh(ob.data)
    zs = [v.co.z for v in bm.verts]
    lo, hi = min(zs), max(zs)
    tall = hi - lo
    down = Vector((0.0, 0.0, -1.0))
    cos_cop = math.cos(math.radians(AIR_COPLANAR))
    cos_cone = -math.cos(math.radians(AIR_CONE))
    pool, total = set(), 0.0
    for f in bm.faces:
        if f.normal.normalized().z >= cos_cone:
            continue
        c = f.calc_center_median()
        h = c.z - lo
        # Overhang in the top TOP_BAND is a cavity's own ceiling, which no
        # orientation turns downward - the same exemption the roof test
        # makes, and for the same reason.
        if h < AIR_SKIRT or h >= tall - TOP_BAND:
            continue
        if not ob.ray_cast(c + Vector((0.0, 0.0, -0.05)), down,
                           distance=1e6)[0]:
            pool.add(f)
            total += f.calc_area()
    best, bh = 0.0, 0.0
    while pool:
        seed = pool.pop()
        n0 = seed.normal.normalized()
        area, stack, hs = seed.calc_area(), [seed], [seed.calc_center_median().z]
        while stack:
            f = stack.pop()
            for e in f.edges:
                for g in e.link_faces:
                    if g in pool and g.normal.normalized().dot(n0) >= cos_cop:
                        pool.discard(g)
                        area += g.calc_area()
                        hs.append(g.calc_center_median().z)
                        stack.append(g)
        if area > best:
            best, bh = area, min(hs) - lo
    bm.free()
    bpy.data.objects.remove(ob, do_unlink=True)
    return best, bh, total


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

    # Already a closed solid? Then leave it completely alone.
    #
    # This is not an optimisation, it is the whole safety rule. Run
    # unconditionally, this function DESTROYED both head halves: they went in
    # at 0 open / 0 non-manifold and came out at 212/12434 and 362/8340.
    #
    # The culprit is `dissolve_degenerate`, not the weld - worth knowing,
    # because the weld is the one that looks dangerous. Tested at 0, 1e-6,
    # 1e-5 and 1e-4 on both halves, remove_doubles alone merges at most 27
    # vertices and 2 faces and leaves the volume identical to three decimal
    # places. dissolve_degenerate is what tears a 99k-vertex sculpt apart: it
    # collapses edges that are legitimately that short and every collapse
    # takes the surrounding fan with it.
    #
    # The repairs below are for parts built from overlapping primitives,
    # which is every small part in this project and none of the sculpted
    # ones.
    #
    # A couple of zero-area faces are not worth risking a 99k mesh over: they
    # contribute nothing to any slice plane. Only open boundaries and
    # non-manifold edges justify touching the geometry at all.
    if before[0] == 0 and before[1] == 0:
        return before, before

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




SHAPE_TOL = 1e-3        # mm; see the note in _shape()


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


def gate(parts, limit=45.0):
    """The whole pre-flight, for any list of (name, rotation).

    Returns True only if every part would print. This is what "am I good to
    go" means, and it lives in the repo rather than in anyone's head.
    """
    print("  %-14s %10s %8s %10s   %s"
          % ("part", "bed", "of shadow", "worst air", "verdict"))
    bad = []
    for name, rot in parts:
        ps = _print_stats(name, rot, limit)
        ai = _air_stats(name, rot)
        if ps is None or ai is None:
            print("  %-14s MISSING" % name)
            bad.append((name, "no such object"))
            continue
        bed, unsup, high, tall, shadow = ps[:5]
        frac = bed / shadow if shadow else 0.0
        area, h, total = ai
        notes = []
        if frac < BRIM_BED_FRAC or bed < BRIM_MIN_MM2:
            notes.append("stands on %.1f mm2 of a %.0f shadow" % (bed, shadow))
        elif frac < MIN_BED_FRAC:
            notes.append("needs a brim (%.0f%% of shadow)" % (100 * frac))
        if area > AIR_MAX:
            notes.append("%.1f mm2 on air %.1f mm up (limit %.0f)"
                         % (area, h, AIR_MAX))
        print("  %-14s %8.1f %8.0f%% %9.1f   %s"
              % (name, bed, 100 * frac, area, "; ".join(notes) or "ok"))
        if any("stands on" in n or "on air" in n for n in notes):
            bad.append((name, "; ".join(notes)))
    print("")
    if bad:
        print("NOT READY - %d of %d would not print:" % (len(bad), len(parts)))
        for n, why in bad:
            print("   %-16s %s" % (n, why))
        return False
    print("READY - %d parts." % len(parts))
    return True
