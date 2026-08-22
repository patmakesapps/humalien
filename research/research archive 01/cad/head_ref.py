"""Bring the female head reference mesh into the scene, oriented and scaled.

The mesh itself is NOT in this repo and must not be. It is a royalty-free
asset under a **No AI** licence: free to use in the build, not free to
redistribute, and explicitly not to be fed to generative 3D tools. That last
clause matters here because the Blender MCP server exposes Hyper3D / Rodin /
Hunyuan generators - never point them at this mesh. Importing, measuring,
scaling and cutting it is deterministic CAD and is fine.

Point SRC at wherever the .obj lives and run:

    exec(open(r"C:\\humalien\\humalien\\cad\\head_ref.py").read())

That keeps the *result* reproducible without the asset ever entering git.
"""

import bpy
from mathutils import Matrix

SRC = r"C:\Users\PatrickKearney\Downloads\female_human_head.obj"
COLL_NAME = "REF_Head"

# Anthropometric anchor. Head breadth is the cleanest of the three - height
# depends on where you call the chin and depth on where you call the occiput.
# 150 mm sits between female (~145) and male (~152) adult means.
TARGET_HEAD_WIDTH = 150.0


def _coll():
    c = bpy.data.collections.get(COLL_NAME)
    if c:
        for ob in list(c.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(c)
    c = bpy.data.collections.new(COLL_NAME)
    bpy.context.scene.collection.children.link(c)
    return c


def load():
    coll = _coll()
    before = set(bpy.data.objects)
    # import with no axis conversion; the source is Y-up / Z-forward and lying
    # on its back, which no preset maps correctly
    bpy.ops.wm.obj_import(filepath=SRC, global_scale=1.0,
                          forward_axis='Y', up_axis='Z')
    ob = [o for o in bpy.data.objects if o not in before][0]
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    coll.objects.link(ob)
    ob.name = "HEAD_REF"

    # native (x=right, y=up, z=forward) -> humalien (x=right, y=forward, z=up).
    # The X flip keeps the transform a rotation rather than a mirror; the mesh
    # is symmetric about X so it costs nothing.
    ob.data.transform(Matrix(((-1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1))))
    ob.matrix_world = Matrix.Identity(4)

    pts = [v.co.copy() for v in ob.data.vertices]
    midx = (min(p.x for p in pts) + max(p.x for p in pts)) / 2
    ob.data.transform(Matrix.Translation((-midx, 0, 0)))

    # find the neck: the narrowest X band between the shoulders and the head
    pts = [v.co.copy() for v in ob.data.vertices]
    zlo = min(p.z for p in pts)
    zhi = max(p.z for p in pts)
    neck_z, neck_w = None, None
    for i in range(10, 20):
        z0 = zlo + (zhi - zlo) * i / 40.0
        z1 = zlo + (zhi - zlo) * (i + 1) / 40.0
        sl = [p for p in pts if z0 <= p.z < z1]
        if not sl:
            continue
        w = max(p.x for p in sl) - min(p.x for p in sl)
        if neck_w is None or w < neck_w:
            neck_z, neck_w = z0, w

    head = [p for p in pts if p.z >= neck_z]
    hw = max(p.x for p in head) - min(p.x for p in head)
    s = TARGET_HEAD_WIDTH / hw
    ob.data.transform(Matrix.Scale(s, 4))

    pts = [v.co.copy() for v in ob.data.vertices]
    head = [p for p in pts if p.z >= neck_z * s]
    info = {
        "scale_mm_per_unit": s,
        "head_width": max(p.x for p in head) - min(p.x for p in head),
        "head_depth": max(p.y for p in head) - min(p.y for p in head),
        "neck_to_crown": max(p.z for p in pts) - neck_z * s,
        "neck_cut_z": neck_z * s,
        "crown_z": max(p.z for p in pts),
        "nose_tip_y": max(p.y for p in pts),
    }
    for k, v in info.items():
        print("  %-20s %.2f" % (k, v))
    return ob, info


if __name__ == "__main__":
    load()
