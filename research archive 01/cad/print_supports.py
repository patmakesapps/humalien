"""Find geometry that would print into thin air, and stand a pillar under it.

Run inside Blender against an object already in its PRINT orientation (the
PR_* copies in the `print ready` collection), not against the model-space
part:

    ns = {}
    exec(compile(open(r"C:\\Humalien\\cad\\print_supports.py").read(),
                 "print_supports", "exec"), ns)
    ns["build"]("PR_HEAD_FACE")

What went wrong, 16 Aug 2026
---------------------------

The face came off the printer with its three forehead-casing bosses snapped
off and dragged around the plate as loose rings. The mesh was NOT at fault -
PR_HEAD_FACE is one connected shell and the bosses are properly welded to it.
The fault is orientation, and nothing in the pipeline was looking for it.

The face is laid rim-down, which maps model +Y onto print +Z. The casing
bosses run along model +Y, from the casing's mounting face at y=167 forward
to the brow. So in the print their FREE END is the LOW end, and it lands at
print z = 32.00 mm with the shell it hangs from 16 to 28 mm ABOVE it:

    casing_R   model (34.95, 167.00, 231.07)   free end z 32.00   Ø15   170.96 mm2
    casing_C   model (-0.01, 167.00, 228.99)   free end z 32.00   Ø10    73.07 mm2
    casing_L   model (-35.06, 167.00, 231.10)  free end z 32.00   Ø15   170.96 mm2

Probed one layer up, there is material on the boss ring (12/12 samples) and
nothing at all around it out to r=25 mm (0/24). That is the definition of an
island: a ring of plastic extruded into space with no layer beneath it and
nothing at its own height to anchor either end. It curls, sticks to the
nozzle, and gets dragged. Slicer bridging cannot save it - a bridge needs two
anchored ends and this has none.

Why this is supports and not a CAD change
-----------------------------------------

The volume directly under those bosses is the forehead casing's own envelope
(96 x 58 x 5, front face at y=167). A gusset, a flare, or any downward-
growing buttress would sit exactly where the casing has to go. Reorienting is
worse: flipping the face puts its curved outer surface on the plate with
almost no contact patch. The geometry is right; only the print needs help.

Why printed-in and not slicer auto-support
------------------------------------------

Auto-support would also pack the whole concave interior, because 22181 of the
face's 26465 downward faces have air beneath them. Almost all of those are
the dome's own sloped ceiling, which already prints fine - the shell in the
14 Aug run came off clean. Supporting them costs hours and leaves the inside
of the face to be dug out. Three modelled pillars support the three places
that actually fail and nothing else, and they slice under the existing
profile with supports switched OFF.

The two checks that matter
--------------------------

**Flat, not merely downward.** Filtering on normal.z < -0.95 separates island
starts from the dome's rake. At -0.70 the scan returns 82 clusters and buries
the three that matter.

**Island, not bridge.** A flat unsupported face is fine if material at its own
height runs down to the bed somewhere it is JOINED to - that is a bridge.

Probing a ring of points around the cluster does not answer that question, and
the first version of this file did exactly that and got it wrong. A ring probe
asks "is there supported material near me", and near is not joined: casing_L
came back a bridge because an unrelated feature 7.5 mm away was supported,
while its own mirror image casing_R came back an island. Two identical parts
classifying differently is the tell. `_anchored` floods the material at the
island's own height instead, stepping only through points that are inside the
mesh, so it can only ever reach material the island is actually continuous
with. Seed it from the cluster's face centres and never from its centroid -
the centroid of a boss end is inside the M3 pilot bore, which is air.
"""

import bpy
import bmesh
import math
from mathutils import Vector

COLL = "PRSUP_%s"
FLAT = -0.95        # normal.z below this is a flat downward face
GAP = 0.20          # air under the supported face - one 0.2 mm layer, as a
                    # slicer's own top-Z-distance does, so it lifts off clean
FOOT_H = 4.0        # flare height
FOOT_R = 4.0        # extra radius at the bed; with FOOT_H this is 45 degrees,
                    # which builds up from the plate unsupported
SEGS = 48
# A pillar no thinner than height/SLENDER. The face's are 32 mm tall on Ø10 to
# Ø15 and never needed this, but the cranium's cable anchors sit 99.8 mm up:
# sized to their island alone they came out Ø5, a 19:1 column for the nozzle to
# knock over every layer. Widening only ever helps the support and is given up
# again if the column would touch the part.
SLENDER = 8.0
# An off-axis ray direction for the inside/outside parity test. NEVER fire
# down an axis: every boss has an M3 pilot on its own centreline, and a ray
# sent down that bore reports the boss as hollow. Same trap as the ear-hub
# arms - see the note in head_mounts.py.
PROBE = Vector((0.37139, 0.55709, 0.74278))


def _inside(ob, p):
    """Parity test: is world point `p` inside `ob`?"""
    inv = ob.matrix_world.inverted()
    cur = inv @ Vector(p)
    d = inv.to_3x3() @ PROBE
    n = 0
    for _ in range(64):
        hit, loc, nrm, idx = ob.ray_cast(cur, d, distance=3000.0)
        if not hit:
            break
        n += 1
        cur = loc + d.normalized() * 1e-4
    return n % 2 == 1


def _nothing_below(ob, p):
    inv = ob.matrix_world.inverted()
    hit, loc, nrm, idx = ob.ray_cast(inv @ (Vector(p) + Vector((0, 0, -0.05))),
                                     inv.to_3x3() @ Vector((0, 0, -1)),
                                     distance=500.0)
    return not hit


BAND = 0.40         # mm of layer to test connectivity across
DROP = 0.20         # how far below the island a component must reach to count
# Islands are grouped by SHARED EDGES, not by distance. Distance grouping
# needs a radius, and no radius works: at 16 mm anchor_1 and anchor_2 (15.2 mm
# apart) merged into one 152 mm2 island and got a single Ø21 pillar centred
# between them that missed the outer edge of both; at 9 mm the grouping became
# order-dependent and split casing_L into 127.60 + 43.36 while its mirror image
# casing_R stayed whole. A boss end is one edge-connected patch of faces and
# two separate bosses never share an edge, so adjacency answers it outright.


def _anchored(faces, zspan, adj, seeds, z0):
    """Does the island's own layer-slab reach material that continues downward?

    Topology, not sampling. Every face whose z-range crosses [z0, z0+BAND] is
    a face the printer lays down in that slab; two of them are joined iff they
    share an edge. Walk the seed faces' component and ask whether anything in
    it descends past z0-DROP. A bridge does, at its ends. A free-standing post
    does not - its only route to the shell is upward, out of the slab.

    The sampled versions of this test were both wrong and wrong in opposite
    directions. A ring probe reports material that is near but not joined, and
    called casing_L a bridge on the strength of a feature 7.5 mm away. A grid
    flood at 0.8 mm steps hops small air gaps in one place and fails to walk a
    thin wall in another; it lost casing_L and invented two islands that are
    plainly ribs. Shared edges cannot do either.
    """
    inband = [i for i, (lo, hi) in enumerate(zspan)
              if lo <= z0 + BAND and hi >= z0]
    if not inband:
        return False
    sel = set(inband)
    seen, stack = set(), [i for i in seeds if i in sel]
    while stack:
        i = stack.pop()
        if i in seen:
            continue
        seen.add(i)
        if zspan[i][0] < z0 - DROP:
            return True
        for j in adj[i]:
            if j in sel and j not in seen:
                stack.append(j)
    return False


def islands(ob, min_area=2.0):
    """Flat downward regions with air below and nothing joined to them at
    their own height that reaches down. Returns [(centre, radius, area)]."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.transform(ob.matrix_world)
    bm.normal_update()
    bm.faces.ensure_lookup_table()

    zspan = [(min(v.co.z for v in f.verts), max(v.co.z for v in f.verts))
             for f in bm.faces]
    adj = [[] for _ in bm.faces]
    for e in bm.edges:
        lf = e.link_faces
        for a in range(len(lf)):
            for b in range(a + 1, len(lf)):
                adj[lf[a].index].append(lf[b].index)
                adj[lf[b].index].append(lf[a].index)

    loose = []
    for f in bm.faces:
        if f.normal.z > FLAT:
            continue
        c = f.calc_center_median()
        if c.z < 0.5:               # sitting on the bed, which is support
            continue
        if _nothing_below(ob, c):
            loose.append((c, f.calc_area(), f.index))

    info = {i: (c, a) for c, a, i in loose}
    lset = set(info)
    cl, seen = [], set()
    for start in info:
        if start in seen:
            continue
        grp, stack = [], [start]
        while stack:
            i = stack.pop()
            if i in seen:
                continue
            seen.add(i)
            grp.append(i)
            for j in adj[i]:
                if j in lset and j not in seen:
                    stack.append(j)
        pts = [info[i][0] for i in grp]
        cl.append({"c": sum(pts, Vector()) / len(pts), "pts": pts, "idx": grp,
                   "a": sum(info[i][1] for i in grp)})

    out = []
    for g in (x for x in cl if x["a"] >= min_area):
        c = g["c"]
        rad = max((p - c).length for p in g["pts"]) if len(g["pts"]) > 1 else 1.0
        if not _anchored(bm.faces, zspan, adj, g["idx"], min(p.z for p in g["pts"])):
            out.append((c.copy(), rad, g["a"]))
    bm.free()
    return out


def _lathe(coll, name, ax, profile):
    """A solid of revolution from a bottom-to-top [(r, z)] profile.

    NOT two extrude_face_region calls on a copied footprint, which is how this
    was written first: the second extrude was handed the side walls along with
    the new cap, and every pillar came out with 72 boundary and 72 non-manifold
    edges - an open tube that reads as a solid until something checks.

    Two entries at the same z with different r make a horizontal shelf. Those
    only ever step INWARD going up, so every shelf faces up and needs nothing
    under it.
    """
    bm = bmesh.new()
    rings = [[bm.verts.new((ax.x + r * math.cos(2 * math.pi * i / SEGS),
                            ax.y + r * math.sin(2 * math.pi * i / SEGS), z))
              for i in range(SEGS)] for (r, z) in profile]
    vb = bm.verts.new((ax.x, ax.y, profile[0][1]))
    vt = bm.verts.new((ax.x, ax.y, profile[-1][1]))
    for i in range(SEGS):
        j = (i + 1) % SEGS
        bm.faces.new((vb, rings[0][j], rings[0][i]))
        for k in range(len(rings) - 1):
            bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
        bm.faces.new((vt, rings[-1][i], rings[-1][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.color = (0.95, 0.15, 0.15, 1.0)
    coll.objects.link(ob)
    return ob


def supports(ob, found):
    """One pillar per island, in its own collection. `ob` is never modified."""
    name = COLL % ob.name.replace("PR_", "").lower()
    old = bpy.data.collections.get(name)
    if old:
        for o in list(old.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(old)
    coll = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(coll)

    def clear(ax, r, z0, z1):
        """Is an r-radius ring about `ax` clear of the part over z0..z1?"""
        steps = max(2, int((z1 - z0) / 3.0) + 1)
        for s in range(steps + 1):
            z = z0 + (z1 - z0) * s / steps
            for k in range(SEGS):
                a = 2 * math.pi * k / SEGS
                if _inside(ob, (ax.x + r * math.cos(a),
                                ax.y + r * math.sin(a), z)):
                    return False
        return True

    # Size the column to the island's own footprint, not to its face-centre
    # radius: `rad` is measured to triangle CENTRES, so it under-reports a Ø15
    # annulus as 6.02. Take the real extent from the enclosed area.
    posts = []
    for c, rad, area in found:
        posts.append({"ax": Vector((c.x, c.y)), "top": c.z - GAP,
                      "need": max(rad + 1.5, math.sqrt(area / math.pi))})
    for p in posts:
        p["R"] = max(p["need"], p["top"] / SLENDER)
        while p["R"] > p["need"] and not clear(p["ax"], p["R"], FOOT_H, p["top"]):
            p["R"] = max(p["need"], p["R"] - 0.5)

    # Merge posts whose columns intersect. Two separate solids sharing space is
    # not a support, it is a self-intersection: the cranium's two cable-anchor
    # posts came out Ø24.95 on 15.17 mm centres, and pca_RT's boss end and the
    # small ledge 5.9 mm above it produced two exactly concentric columns.
    root = list(range(len(posts)))

    def find(a):
        while root[a] != a:
            root[a] = root[root[a]]
            a = root[a]
        return a

    for a in range(len(posts)):
        for b in range(a + 1, len(posts)):
            if (posts[a]["ax"] - posts[b]["ax"]).length < posts[a]["R"] + posts[b]["R"]:
                root[find(a)] = find(b)
    groups = {}
    for i in range(len(posts)):
        groups.setdefault(find(i), []).append(posts[i])

    made = []
    for n, (_, grp) in enumerate(sorted(groups.items())):
        ax = sum((p["ax"] for p in grp), Vector((0, 0))) / len(grp)
        # Radius needed at height z is whatever still encloses every post that
        # reaches at least that high; stepping inward as the shorter ones end.
        levels = sorted({p["top"] for p in grp})
        prof, prev = [], None
        for z in [FOOT_H] + levels:
            live = [p for p in grp if p["top"] >= z - 1e-6]
            if not live:
                continue
            r = max((p["ax"] - ax).length + p["R"] for p in live)
            floor = max((p["ax"] - ax).length + p["need"] for p in live)
            while r > floor and not clear(ax, r, z, max(p["top"] for p in live)):
                r = max(floor, r - 0.5)
            if prev is not None and z > prev[1]:
                prof.append((prev[0], z))       # carry the old radius up...
                prof.append((r, z))             # ...then step in
            else:
                prof.append((r, z))
            prev = (r, z)
        prof.append((prev[0], levels[-1]))
        prof = [p for i, p in enumerate(prof) if i == 0 or p != prof[i - 1]]
        Rf = prof[0][0] + FOOT_R
        while Rf > prof[0][0] and not clear(ax, Rf, 0.05, FOOT_H):
            Rf -= 0.5
        made.append(_lathe(coll, "PRSUP_%02d" % n, ax, [(Rf, 0.0)] + prof))
    return made


MAX_ASPECT = 12.0   # height:diameter beyond which a column will not stand


def verify(ob, sup):
    """The gate. Every island backed, every pillar closed, standing, and alone.

    The overlap and slenderness checks are not decoration. Sizing the cranium's
    posts produced a Ø40 x 100 merged blob of 127 cm3 that still intersected
    its neighbour, and a Ø5.6 x 96 column at 17:1 that the nozzle would knock
    down on the way past. Both were written to an STL and looked plausible in
    the file listing. A gate that only checks the thing it was built for is how
    the floating bosses got to the printer in the first place.
    """
    bad = []
    geo = []
    for s in sup:
        bm = bmesh.new()
        bm.from_mesh(s.data)
        if any(len(e.link_faces) != 2 for e in bm.edges):
            bad.append("%s is not a closed solid" % s.name)
        bm.transform(s.matrix_world)
        bm.normal_update()
        if any(f.normal.z < FLAT and f.calc_center_median().z > 0.01
               for f in bm.faces):
            bad.append("%s has a downward face off the bed" % s.name)
        vs = [v.co for v in bm.verts]
        cx = sum(v.x for v in vs) / len(vs)
        cy = sum(v.y for v in vs) / len(vs)
        h = max(v.z for v in vs)
        rw = max(math.hypot(v.x - cx, v.y - cy) for v in vs if v.z > FOOT_H - 0.01)
        rall = max(math.hypot(v.x - cx, v.y - cy) for v in vs)
        geo.append((s.name, cx, cy, rall))
        if h / (2 * rw) > MAX_ASPECT:
            bad.append("%s is %.0f mm tall on Ø%.1f - %.1f:1, it will not stand"
                       % (s.name, h, 2 * rw, h / (2 * rw)))
        bm.free()
    for a in range(len(geo)):
        for b in range(a + 1, len(geo)):
            na, xa, ya, ra = geo[a]
            nb, xb, yb, rb = geo[b]
            if math.hypot(xa - xb, ya - yb) < ra + rb:
                bad.append("%s and %s intersect each other" % (na, nb))

    left = islands(ob) if not sup else []
    for c, rad, area in left:
        covered = False
        for s in sup:
            si = s.matrix_world.inverted()
            hit, loc, n, i = s.ray_cast(si @ (c + Vector((0, 0, -0.02))),
                                        si.to_3x3() @ Vector((0, 0, -1)),
                                        distance=500.0)
            covered |= hit
        if not covered:
            bad.append("island at (%.1f, %.1f, %.1f) still unsupported"
                       % (c.x, c.y, c.z))
    if bad:
        raise RuntimeError("NOT READY:\n    " + "\n    ".join(bad))
    return True


def build(obj_name):
    ob = bpy.data.objects[obj_name]
    found = islands(ob)
    print("  %s: %d unsupported island(s)" % (obj_name, len(found)))
    for c, rad, area in found:
        print("    (%7.2f, %7.2f, %6.2f)  area %7.2f mm2" % (c.x, c.y, c.z, area))
    sup = supports(ob, found)
    verify(ob, sup)
    print("  %d pillar(s) built, %s untouched (%d verts) - READY TO SLICE"
          % (len(sup), obj_name, len(ob.data.vertices)))
    return sup
