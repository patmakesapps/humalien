"""A massing study of the v2 head - scripted clay, not a design.

    exec(open(r"C:\\Humalien\\cad\\head_study.py").read())
    build()

WHAT THIS IS FOR
----------------
One question: does a skull wide enough for the v2 mechanism - +-86 interior
through the eye band, against a human's ~+-75 - still read as a HUMANOID
head once the landmarks are in the right places, or does it read as a box
with eyes? Pat's fear is the box. The argument this study makes is that
humanity lives in the landmarks (eye line, brow, nose bridge, cheek, chin
taper), not in the outline, and the cheapest way to test that argument is
to look at it with the real mechanism showing through the sockets.

It is built from metaballs - blobby, deliberately crude, the digital
equivalent of thumbing clay over an armature. Nothing here is printable
and nothing here is final. If the silhouette convinces, the real face
starts from the fascia plan (or from the original sculpt, grafted); if it
does not convince, we learned it for the cost of a screenshot.

Numbers it is built AGAINST (committed elsewhere, not chosen here):
    eye centres    (+-31, 0, 0), Ø32 balls    cad/eye.py
    skull interior +-86 through z -20..15     the mechanism plus clearance
    casing         z 25.9..83.9 at y 1..6     bench.STATIONS
    speakers       x +-63..84, z 35..80       bench.STATIONS
    sockets        ~Ø36 apertures: v1's Ø41 held Ø41 domes; Ø32 balls
                   want a tighter ring, which also reads more alive

The metaball surface lands where field maths says, not where you ask, so
build() MEASURES the result at the eye band and scales x once to hit the
target - stated width beats wished-for width.
"""

import bpy
import bmesh
import math
from mathutils import Matrix, Vector

COLL = "HEAD_STUDY"
HALF_W = 90.0           # exterior half-width target at the eye band

# name: (centre, radius, (sx, sy, sz))  - ELLIPSOID elements. Sized to
# OVERLAP hard: metaball fields only fuse where they genuinely mingle,
# and the first draft of this table produced eleven separate eggs.
THRESHOLD = 0.4
CLAY = {
    "cranium":  ((0.0, -38.0, 50.0), 62.0, (1.55, 1.45, 1.2)),
    "occiput":  ((0.0, -78.0, 15.0), 48.0, (1.1, 1.0, 1.0)),
    "temple_R": ((46.0, -28.0, 0.0), 40.0, (1.0, 1.2, 1.25)),
    "temple_L": ((-46.0, -28.0, 0.0), 40.0, (1.0, 1.2, 1.25)),
    # flanks cover the upright lane (x to 84 at z -58..14, y -11..11)
    "flank_R":  ((50.0, -8.0, -28.0), 28.0, (0.85, 1.05, 1.15)),
    "flank_L":  ((-50.0, -8.0, -28.0), 28.0, (0.85, 1.05, 1.15)),
    "brow":     ((0.0, 6.0, 34.0), 32.0, (1.9, 0.8, 0.75)),
    # orbits bring the skin FORWARD past the eyeballs, so the sockets are
    # holes in a face rather than a face behind a machine
    "orbit_R":  ((31.0, 10.0, -2.0), 26.0, (1.05, 0.85, 0.95)),
    "orbit_L":  ((-31.0, 10.0, -2.0), 26.0, (1.05, 0.85, 0.95)),
    # glabella: without it the skin dips between the orbits and the whole
    # spine/blink hardware shows through the middle of the face
    "glabella": ((0.0, 12.0, 2.0), 20.0, (0.9, 0.8, 0.9)),
    "cheek_R":  ((30.0, 4.0, -34.0), 28.0, (1.05, 1.0, 1.05)),
    "cheek_L":  ((-30.0, 4.0, -34.0), 28.0, (1.05, 1.0, 1.05)),
    # the lower face is deliberately SHORT - big cranium, compact chin,
    # which clears the bench deck and reads more alien than infant
    "muzzle":   ((0.0, 14.0, -50.0), 28.0, (1.25, 1.0, 1.05)),
    "jaw":      ((0.0, -10.0, -62.0), 34.0, (1.35, 1.25, 0.9)),
    "chin":     ((0.0, 14.0, -78.0), 18.0, (1.15, 1.0, 1.0)),
    "nose":     ((0.0, 32.0, -12.0), 13.0, (0.6, 1.3, 1.8)),
}


def _measure_halfwidth(ob):
    return max(abs(v.co.x) for v in ob.data.vertices
               if -20.0 <= v.co.z <= 15.0 and -60.0 <= v.co.y <= 10.0)


def build():
    old = bpy.data.collections.get(COLL)
    if old:
        for o in list(old.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(old)
    coll = bpy.data.collections.new(COLL)
    bpy.context.scene.collection.children.link(coll)

    mb = bpy.data.metaballs.new("_study_clay")
    mb.resolution = 3.0
    mb.threshold = THRESHOLD
    for name, (co, r, (sx, sy, sz)) in CLAY.items():
        el = mb.elements.new(type='ELLIPSOID')
        el.co = co
        el.radius = r
        el.size_x, el.size_y, el.size_z = sx, sy, sz
    tmp = bpy.data.objects.new("_study_mb", mb)
    coll.objects.link(tmp)

    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    ob = bpy.data.objects.new("head_study", me)
    coll.objects.link(ob)
    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.metaballs.remove(mb)

    w = _measure_halfwidth(ob)
    ob.data.transform(Matrix.Diagonal((HALF_W / w, 1.0, 1.0, 1.0)))
    print("  clay half-width at eye band: %.1f -> scaled x by %.3f"
          % (w, HALF_W / w))

    # socket apertures: Ø36 tunnels the real eyes look through, with a
    # shallow Ø52 dish so the lids read as set into the face
    cuts = bmesh.new()
    for sx in (1, -1):
        t = bmesh.new()
        bmesh.ops.create_cone(t, cap_ends=True, segments=32,
                              radius1=18.0, radius2=18.0, depth=70.0)
        bmesh.ops.rotate(t, verts=t.verts[:], cent=(0, 0, 0),
                         matrix=Matrix.Rotation(math.radians(-90), 3, 'X'))
        bmesh.ops.transform(t, verts=t.verts[:],
                            matrix=Matrix.Translation((sx * 31.0, 30.0, 0.0)))
        tm = bpy.data.meshes.new("_t"); t.to_mesh(tm); t.free()
        cuts.from_mesh(tm); bpy.data.meshes.remove(tm)
        t = bmesh.new()
        bmesh.ops.create_uvsphere(t, u_segments=24, v_segments=12,
                                  radius=24.0)
        bmesh.ops.transform(t, verts=t.verts[:],
                            matrix=Matrix.Translation((sx * 31.0, 40.0, 0.0)))
        tm = bpy.data.meshes.new("_t"); t.to_mesh(tm); t.free()
        cuts.from_mesh(tm); bpy.data.meshes.remove(tm)
    cm = bpy.data.meshes.new("_study_cuts")
    cuts.to_mesh(cm); cuts.free()
    co = bpy.data.objects.new("_study_cuts", cm)
    bpy.context.scene.collection.objects.link(co)
    mod = ob.modifiers.new("CUT", 'BOOLEAN')
    mod.operation, mod.solver, mod.object = 'DIFFERENCE', 'EXACT', co
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.remove(mod)
    old_me = ob.data
    ob.data = me2
    bpy.data.meshes.remove(old_me)
    bpy.data.objects.remove(co, do_unlink=True)
    bpy.data.meshes.remove(cm)

    ob.color = (0.62, 0.60, 0.58, 1.0)
    for p in ob.data.polygons:
        p.use_smooth = True
    print("  head_study: %d verts, exterior +-%.0f at the eye band"
          % (len(ob.data.vertices), HALF_W))
    return ob
