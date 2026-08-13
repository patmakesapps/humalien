"""Cut the head into a face and a cranium so it can be printed and assembled.

Run last, after head_style.py and head_mounts.py:

    exec(open(r"C:\\humalien\\humalien\\cad\\head_style.py").read())
    exec(open(r"C:\\humalien\\humalien\\cad\\head_mounts.py").read())
    exec(open(r"C:\\humalien\\humalien\\cad\\head_split.py").read())
    build()

Why split a head that fits the printer whole
--------------------------------------------

`docs/eye-design-brief.md` established that the head fits an A1 whole -
150 x 185 x 213 against a 256 mm cube - and concluded that splitting had
become "a choice about surface finish, support and where a skin seam can
hide, rather than a limit imposed by the printer". Three things since have
turned that choice into a decision:

**Assembly.** head_mounts is built on one rule - a screw is only worth
drawing if a hand can reach it - and half the fixings in this head only pass
that test with the face off. The forehead casing's three screws go in from
behind. The Pi tray's four go down into the rails from above. The ear hubs
are wider than the port they sit behind and physically cannot be fitted any
other way. A one-piece head would need every one of those done blind through
a Ø66 ear port.

**Support.** Printed whole and upright, the chin, the underside of the nose
and the brow are all overhangs, and the face - the one surface on this object
where finish matters - is printed on its most curved axis. Split at a coronal
plane, both halves print cut-face-down: the face piece is 74 mm tall with the
nose pointing at the ceiling and nothing on the face overhanging more than
about 45 degrees, and the cranium is 111 mm with only its own dome to worry
about. Neither needs support anywhere a tool has to reach.

**The seam is free styling.** At y=135 the parting line runs over the crown,
down in front of each ear port - 7 mm clear of the Ø66 bore - and across the
cheek to the jaw, which is close to where the plated-face reference puts its
own face-plate seam. A seam that has to exist and looks deliberate is worth
more than one that only looks deliberate.

The joint
---------

Four dowel pads straddle the parting plane, placed by raycasting the shell's
inner surface so each one sits on the wall rather than in mid-air. Splitting
leaves half a pad on each piece with a Ø5.2 bore, so a Ø5 pin - printed,
or a length of filament - locates the halves. The pads are Ø16 against a
4 mm wall, which is what makes a 5 mm hole possible at all: the wall on its
own has nothing to drill into.

There are no screws across this joint. Deciding where they go means knowing
how the neck attaches, because the neck plate is the obvious thing to clamp
both halves to, and there is no neck yet. Pins and four M3s through a neck
plate is the intended end state; pins and a bead of glue is what this prints
as today. That is recorded rather than hidden.
"""

import bpy
import bmesh
import math
from mathutils import Matrix, Vector

COLL = "SPLIT_Head"
HEAD = "HEAD_CYBORG"

P = dict(
    y        = 135.0,     # the parting plane
    pad_d    = 16.0,      # dowel pad, on the inner surface, straddling y
    pad_len  = 24.0,
    pin      = 5.2,       # bore; a Ø5 pin
    pin_len  = 40.0,
    # Where to put them: a point inside the head at the parting plane, and
    # the direction to walk until the wall is found. Spread around the rim.
    dowels   = [("crown", Vector((0.0, 135.0, 250.0)), Vector((0, 0, 1))),
                ("temple_R", Vector((0.0, 135.0, 215.0)), Vector((1, 0, 0))),
                ("temple_L", Vector((0.0, 135.0, 215.0)), Vector((-1, 0, 0))),
                ("jaw", Vector((0.0, 135.0, 150.0)), Vector((0, 0, -1)))],
)


def build(head_name=HEAD, keep_whole=True, force=False):
    # This is the function that would have eaten USERFIX_HEAD_CRANIUM: it
    # deletes everything in SPLIT_Head and makes HEAD_FACE and HEAD_CRANIUM
    # fresh from the whole head, every run. The hand edit near both ear ports
    # lives on the mesh it replaces, and nothing in this file could put it
    # back. guard() is defined in head_mounts.py - same shared namespace that
    # already supplies _cyl, _box and _apply to this file.
    guard(collection_contents(COLL) + [head_name],
          "head_split.build()", force)
    head = bpy.data.objects[head_name]
    c = bpy.data.collections.get(COLL)
    if c:
        for ob in list(c.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(c)
    coll = bpy.data.collections.new(COLL)
    bpy.context.scene.collection.children.link(coll)

    import bmesh as _bm
    from mathutils.bvhtree import BVHTree
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    tmp = _bm.new()
    tmp.from_object(head, dg)
    tmp.transform(head.matrix_world)
    tree = BVHTree.FromBMesh(tmp)
    tmp.free()

    # ---- dowel pads, unioned into the whole head before it is cut ----
    add = bmesh.new()
    cut = bmesh.new()
    print("head_split: dowel pads")
    for label, org, d in P["dowels"]:
        loc, nrm, idx, dist = tree.ray_cast(org, d, 400.0)
        if loc is None:
            print("  %-9s NO WALL" % label)
            continue
        # sit the pad just inboard of the inner surface so it merges with it
        centre = loc - d * (P["pad_d"] / 2.0 - 1.0)
        centre.y = P["y"]
        _cyl(add, P["pad_d"], P["pad_len"], centre, 'Y')
        _cyl(cut, P["pin"], P["pin_len"], centre, 'Y', segs=24)
        print("  %-9s wall at %.1f mm, pad at (%.0f, %.0f, %.0f)"
              % (label, dist, centre.x, centre.y, centre.z))

    _apply(coll, head, add, "_ADD_dowels", 'UNION')
    _apply(coll, head, cut, "_CUT_pins", 'DIFFERENCE')

    # ---- the cut ----
    src = head.data
    pieces = []
    for name, sign in (("HEAD_FACE", 1), ("HEAD_CRANIUM", -1)):
        ob = bpy.data.objects.new(name, src.copy())
        ob.data.name = name
        coll.objects.link(ob)
        ob.color = (0.82, 0.79, 0.74, 1.0)
        box = bmesh.new()
        _box(box, (400.0, 400.0, 500.0), (0.0, P["y"] + sign * 200.0, 200.0))
        _apply(coll, ob, box, "_CUT_half_%s" % name, 'INTERSECT')
        me = ob.data
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        if hasattr(me, "set_sharp_from_angle"):
            me.set_sharp_from_angle(angle=math.radians(40.0))
        me.update()
        pieces.append(ob)
        print("  %-13s %6d verts" % (name, len(me.vertices)))

    if keep_whole:
        head.hide_set(True)
    else:
        bpy.data.objects.remove(head, do_unlink=True)
    report(pieces)
    return pieces


def report(pieces):
    print("  print envelope, each half laid cut-face-down on the bed:")
    for ob in pieces:
        bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        dx = max(p.x for p in bb) - min(p.x for p in bb)
        dy = max(p.y for p in bb) - min(p.y for p in bb)
        dz = max(p.z for p in bb) - min(p.z for p in bb)
        print("    %-13s bed %.0f x %.0f, height %.0f  (A1 is 256 cubed)"
              % (ob.name, dx, dz, dy))
