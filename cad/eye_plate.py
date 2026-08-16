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

TEN FILES, TWELVE PIECES
------------------------
`eye_peg` was retired on 16 Aug 2026 - the frame carries its own temple
spigots now, so the mount is one printed part instead of three. See
`eye_v2.peg`, which is kept uncalled with the reason in it.

The axles and the stems are symmetric about their own centre plane, so left
and right are the same object and each exports once with a quantity of two.
`chirality()` is what says so - and it has to, because
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
GAP = 10.0          # between parts. Was 5, which packed the pegs and axles
                    # close enough that their labels ran into each other -
                    # there is 100 mm of bed spare, so it is free to spend.
PACK_W = 190.0      # wrap to a new row here rather than at the bed's edge.
                    # Packed to the full 256 it came out 251 wide, which
                    # fits and leaves nowhere for a skirt; there is plenty
                    # of depth spare, so spend it.

# The eye plate sits in the row with the numbered plates, on the grid
# `export_plate` and `print_layout` share, in the slot after plate 6.
#
# It is still not one of them, and cannot become one by sitting there:
# `census()` only ever looks inside the `print ready` collection, and every
# object here lives in `eye plate` instead. Position is what census reads,
# but only for objects it can already see, and it can never see these.
#
# It was parked 1000 mm off to one side with no bed, no title and no part
# labels, which is what made it read as scratch geometry rather than a
# plate. The furniture below is copied off `PRBED_plate6`, `PRTITLE_plate6`
# and `PRLABEL_PR_ear_hub_R` rather than guessed at.
PLATE_GAP = 60.0
GRID_ORIGIN_X = 320.0
SLOT = 7                                # the position in the row, not a plate number
BED_CX = GRID_ORIGIN_X + BED / 2.0 + (SLOT - 1) * (BED + PLATE_GAP)
ORIGIN = Vector((BED_CX - BED / 2.0, -BED / 2.0, 0.0))

# Straight off the existing plates, so the two sets cannot drift apart.
COL_BED = (0.25, 0.55, 0.95, 1.0)
COL_LABEL = (0.9, 0.9, 0.9, 1.0)
TITLE_SIZE = 12.0
LABEL_SIZE = 6.0            # 7 on the other plates, but their parts are
                            # bigger and further apart
TITLE_Y = 138.0             # 10 mm clear of the bed's top edge
LABEL_DROP = 4.0            # below the part's own front edge
TITLE = "EYE PLATE  -  256 x 256 bed"

# +Y up: the part's own +Y becomes the print's +Z.
Y_UP = Matrix.Rotation(math.radians(90), 4, 'X')
Y_DOWN = Matrix.Rotation(math.radians(-90), 4, 'X')
X_UP = Matrix.Rotation(math.radians(-90), 4, 'Y')
X_DOWN = Matrix.Rotation(math.radians(90), 4, 'Y')      # the mirror of X_UP
Z_DOWN = Matrix.Rotation(math.radians(180), 4, 'X')     # the part's -Z is up
FLAT = Matrix.Identity(4)

# name, quantity, rotation, why it is that way up
PARTS = [
    ("eye_frame",    1, Z_DOWN, "STANDING ON ITS FLANGE. The rotation has "
                                "not changed and its meaning has: the part "
                                "used to balance on the 104 x 4 mm top edge "
                                "of its arch, 416 mm2, with the mast "
                                "sticking out sideways as a 23-degree "
                                "cantilever - which is the member that "
                                "snapped. The flange is now that face, "
                                "about 1300 mm2, and every wall grows "
                                "straight down off it"),
    ("eye_gimbal",   1, Y_UP,   "flat in its own plane, both bores roofed. "
                                "Really flat now: cradle_y0 went 154 -> 153 "
                                "so the floor reaches the tilt lever and "
                                "swallows both journal housings. 100 -> 710 "
                                "mm2 on the bed"),
    ("eye_pan_bar",  1, Y_UP,   "flat; 533 mm2 on the bed"),
    ("eye_dome_R",   1, Y_UP,   "back face down - the only face it has"),
    ("eye_dome_L",   1, Y_UP,   "back face down"),
    ("eye_lid_R",    1, X_UP,   "on its end, not back-down: back-down is a "
                                "crescent edge with zero contact. 0 -> 58 mm2 "
                                "on the bed, overhang 288 -> 160 mm2. Tall "
                                "and narrow, so it wants a brim"),
    ("eye_lid_L",    1, X_DOWN, "on its end, MIRRORED from eye_lid_R. The "
                                "lids are the one genuinely handed pair, so "
                                "the same rotation does not suit both: X_UP "
                                "gives R 58 mm2 and L only 32"),
    ("eye_stem_R",   2, Y_DOWN, "spigot face down; every layer smaller than "
                                "the one below it. Symmetric, so one file "
                                "serves both sides"),
    ("eye_axle_R",   2, FLAT,   "standing on end - the only way to get a "
                                "round journal; L and R are the same part"),
    ("eye_shaft",    1, X_UP,   "standing on end"),
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


def _bed_outline(coll):
    """The 4-vertex wire rectangle the other six plates are drawn on.

    Four verts, four edges, no faces, `display_type='WIRE'` - so it shows the
    bed's edge in the viewport and is invisible to anything that walks
    polygons, including every check in this project.
    """
    x0, y0 = ORIGIN.x, ORIGIN.y
    me = bpy.data.meshes.new("PRBED_eye")
    me.from_pydata([(x0, y0, 0.0), (x0 + BED, y0, 0.0),
                    (x0 + BED, y0 + BED, 0.0), (x0, y0 + BED, 0.0)],
                   [(0, 1), (1, 2), (2, 3), (3, 0)], [])
    me.update()
    ob = bpy.data.objects.new("PRBED_eye", me)
    ob.display_type = 'WIRE'
    ob.color = COL_BED
    coll.objects.link(ob)
    return ob


def _text(coll, name, body, loc, size, color):
    """A flat FONT object, centred, matching PRTITLE_/PRLABEL_ on the others."""
    cu = bpy.data.curves.new(name, type='FONT')
    cu.body = body
    cu.size = size
    cu.align_x = 'CENTER'
    cu.align_y = 'TOP_BASELINE'
    cu.extrude = 0.0
    ob = bpy.data.objects.new(name, cu)
    ob.location = loc
    ob.color = color
    coll.objects.link(ob)
    return ob


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
            placed.append((ob.name, dims, why, name, qty, ob))
            x += dims[0] + GAP
            row_d = max(row_d, dims[1])
    # Centre the packed block in the bed. The shelf packer works from one
    # corner, which left everything hard against the near edge; the other six
    # plates all sit centred, and this is the difference you actually see.
    parts = [o for o in coll.objects if o.type == 'MESH']
    pts = [o.matrix_world @ v.co for o in parts for v in o.data.vertices]
    used_x = used_y = 0.0
    if pts:
        x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
        y0, y1 = min(p.y for p in pts), max(p.y for p in pts)
        used_x, used_y = x1 - x0, y1 - y0
        shift = Matrix.Translation((ORIGIN.x + BED / 2.0 - (x0 + x1) / 2.0,
                                    ORIGIN.y + BED / 2.0 - (y0 + y1) / 2.0,
                                    0.0))
        for o in parts:
            o.matrix_world = shift @ o.matrix_world

    # The furniture, so this reads as a plate rather than as loose geometry.
    _bed_outline(coll)
    _text(coll, "PRTITLE_eye", TITLE,
          (ORIGIN.x + BED / 2.0, TITLE_Y, 0.0), TITLE_SIZE, COL_BED)

    # One label per FILE, not per piece, carrying the quantity - the same
    # `_xN` convention the exported names use. Labelling all fourteen pieces
    # ran "eye_axle_R_1" and "eye_axle_R_2" straight through each other: the
    # parts they name are 10 mm wide and the text is four times that.
    groups = {}
    for nm, d, why, base, qty, ob in placed:
        groups.setdefault(base, [qty, []])[1].append(ob)
    specs = []
    for base, (qty, obs) in groups.items():
        p = [o.matrix_world @ v.co for o in obs for v in o.data.vertices]
        body = base if qty == 1 else "%s  x%d" % (base, qty)
        specs.append([body, base,
                      (min(q.x for q in p) + max(q.x for q in p)) / 2.0,
                      min(q.y for q in p) - LABEL_DROP,
                      len(body) * LABEL_SIZE * 0.52])       # advance width
    # Stack any that would collide. The pegs, the shaft and the axles are
    # 5-10 mm parts sharing a row, and their names are four times that wide,
    # so no packing that fits the bed also fits the text - the labels have to
    # step down out of each other's way.
    specs.sort(key=lambda s: s[2])
    for i, s in enumerate(specs):
        for t in specs[:i]:
            while (abs(s[3] - t[3]) < LABEL_SIZE * 1.2
                   and s[2] - s[4] / 2 < t[2] + t[4] / 2
                   and t[2] - t[4] / 2 < s[2] + s[4] / 2):
                s[3] -= LABEL_SIZE * 1.4
    for body, base, cx, cy, w in specs:
        _text(coll, "PRLABEL_%s%s" % (PREFIX, base), body,
              (cx, cy, 0.0), LABEL_SIZE, COL_LABEL)

    print("eye plate: %d pieces, %d files" % (len(placed), len(PARTS)))
    for nm, d, why, base, qty, ob in placed:
        print("  %-20s %6.1f x %6.1f x %6.1f mm   %s"
              % (nm[len(PREFIX):], d[0], d[1], d[2], why))
    print("  bed used: %.0f x %.0f of %.0f x %.0f mm, centred in slot %d"
          % (used_x, used_y, BED, BED, SLOT))
    if used_x > BED or used_y > BED:
        print("  *** DOES NOT FIT - %.0f x %.0f over ***"
              % (max(0.0, used_x - BED), max(0.0, used_y - BED)))
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
        # Skip the bed outline, the title and the part labels - furniture,
        # not parts, and the bed is a face-less wire rectangle anyway.
        if ob.type != 'MESH' or not ob.name.startswith(PREFIX):
            continue
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


def aircheck():
    """Is anything on this plate printing over open air? One line per file.

    This is the test that was missing when the first mechanism was printed
    and two of its members snapped. See the block comment above AIR_SKIRT
    for what they were and for where these numbers come from.
    """
    print("  %-12s %16s %11s   %s"
          % ("part", "worst patch", "all on air", "verdict"))
    bad = []
    for name, qty, rot, why in PARTS:
        s = _air_stats(name, rot)
        if s is None:
            print("  %-12s MISSING" % name)
            bad.append((name, "no such object"))
            continue
        area, h, total = s
        note = ""
        if area > AIR_MAX:
            note = ("a %.1f mm2 face on air, %.1f mm up (limit %.0f)"
                    % (area, h, AIR_MAX))
        print("  %-12s %8.1f mm2 @%5.1f %7.1f mm2   %s"
              % (name, area, h, total, note or "ok"))
        if note:
            bad.append((name, note))
    print("")
    if bad:
        print("ON AIR - %d of %d files would print a cantilever:" % (len(bad), len(PARTS)))
        for n, note in bad:
            print("   %-14s %s" % (n, note))
    else:
        print("NOTHING ON AIR - every down-facing face has part under it.")
    return not bad


def printcheck(limit=45.0):
    """Is this plate fit to put on a printer? One line per file, then a verdict.

    Two numbers decide it, and the second one alone is not enough - which is
    how the frame got exported. `eye_v2.printability()` measures overhang and
    nothing else, and a part with no overhang at all can still be balanced on
    a knife edge. Bed contact is the one that catches that.

    Overhang at the very top of a part is exempt: on the domes it is the
    hollow's own ceiling, which no orientation can turn downward and which
    closes over a cavity nothing has to be printed into.
    """
    print("  %-12s %18s %9s %8s   %s"
          % ("part", "first layer", "roof", "past 45", "verdict"))
    bad = []
    brims = []
    for name, qty, rot, why in PARTS:
        s = _print_stats(name, rot, limit)
        if s is None:
            print("  %-12s MISSING" % name)
            bad.append((name, "no such object"))
            continue
        bed, air, worst, tall, shadow, roof, flat = s
        frac = bed / shadow if shadow else 0.0
        note = ""
        brim = False
        # The mm2 floor only bites when the fraction is low too. A O5 peg on
        # its end is 19.5 mm2 and that is 100% of it - small is not the same
        # as balanced, and judging it on area alone failed the one shape on
        # this plate that cannot overhang at all.
        if frac < BRIM_BED_FRAC or (frac < MIN_BED_FRAC and bed < BRIM_MIN_MM2):
            note = ("stands on an edge - %.0f of a %.0f mm2 shadow (%.0f%%)"
                    % (bed, shadow, 100.0 * frac))
        elif frac < MIN_BED_FRAC:
            brim = True
            note = ("BRIM - %.0f of a %.0f mm2 shadow (%.0f%%), %.1f mm tall"
                    % (bed, shadow, 100.0 * frac, tall))
        elif flat > MAX_ROOF:
            note = ("a %.0f mm2 flat ceiling, highest %.1f mm up"
                    % (flat, worst))
        print("  %-12s %7.1f of %6.1f mm2 %6.1f mm2 %6.1f mm2   %s"
              % (name, bed, shadow, flat, air, note or "ok"))
        if note and not brim:
            bad.append((name, note))
        elif brim:
            brims.append(name)
    print("")
    if brims:
        print("BRIM REQUIRED in the slicer: %s" % ", ".join(brims))
    if bad:
        print("NOT READY - %d of %d files:" % (len(bad), len(PARTS)))
        for n, note in bad:
            print("   %-14s %s" % (n, note))
    print("")
    # Not optional, and not a separate thing to remember to run. The plate
    # this file cleared on 15 Aug was printed and two members snapped, and
    # the reason it cleared is that everything above measures how a part
    # SITS and nothing measured what it hangs over.
    air = aircheck()
    print("")
    if bad or not air:
        print("NOT READY.")
    else:
        print("READY - every file stands on a real face, nothing sags, and")
        print("nothing is printed over open air.")
    return not bad and air


def gimbal_foot():
    """What eye_gimbal sits on, in numbers rather than in argument.

    SETTLED - `cradle_y0` is 153.0 and this now reports a 710 mm2 first
    layer. Kept because it is the measurement that found the fault and the
    one that would catch it coming back.

    The fault: the cradle floor was at y=154.0 while the tilt lever hung to
    153.0 and both O13 journal housings bulged to 153.5, so 620 mm2 of the
    face that carries both pan bearings sat a millimetre in the air on a
    10 mm lug. Trimming those three flush was the obvious fix and the wrong
    one - it takes the wall under both pan bores from 1.35 to 0.85 mm and
    under the tilt link pin from 1.85 to 0.85. Dropping the floor adds the
    millimetre instead of spending it.
    """
    ob = bpy.data.objects.get("eye_gimbal")
    if ob is None:
        return
    u = Vector((0.0, 1.0, 0.0))
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.transform(bm, verts=bm.verts[:], matrix=ob.matrix_world)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    lo = min(v.co.dot(u) for v in bm.verts)
    foot = [v.co for v in bm.verts if v.co.dot(u) - lo < 0.05]
    steps = sorted({round(v.co.dot(u) - lo, 2) for v in bm.verts})[:4]
    down = [(f.calc_area(), f.calc_center_median().dot(u) - lo)
            for f in bm.faces if f.normal.normalized().dot(u) < -0.7]
    bm.free()
    print("eye_gimbal, printed +Y up:")
    print("  touching the bed : %d verts over x %.1f..%.1f, z %.1f..%.1f"
          % (len(foot), min(p.x for p in foot), max(p.x for p in foot),
             min(p.z for p in foot), max(p.z for p in foot)))
    print("  the steps above  : %s mm" % steps)
    for a, b in ((0.5, 1.2), (1.2, 2.5)):
        s = sum(ar for ar, h in down if a <= h < b)
        print("  %.1f-%.1f mm up     : %7.1f mm2 facing straight down, on air"
              % (a, b, s))
    print("")
    print("  Fixed by cradle_y0 154.0 -> 153.0: the floor was dropped to meet")
    print("  the lever rather than the lever cut back to meet the floor, so")
    print("  no bearing wall got thinner. check() passes at all 29 poses.")


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
