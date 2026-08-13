"""Lay every v1 part out for printing and export it on its own.

Run inside Blender after the head pipeline:

    exec(open(r"C:\\humalien\\humalien\\cad\\print_layout.py").read())
    build()

Writes one STL per part into `print/v1/`, each already rotated into the
orientation it should be sliced in and dropped so it sits on z=0. Import a
file, and it is on the bed the right way up.

**`print/` is build output and is git-ignored.** Two reasons, and the first
is not negotiable: HEAD_FACE and HEAD_CRANIUM are derived from the head
sculpt, which is royalty-free under a **No AI** licence - free to use in this
build, not free to redistribute. `.gitignore` already keeps the source mesh
out of git entirely and the same applies to anything cut from it. The second
reason is ordinary: every one of these regenerates from cad/*.py in about a
minute, so committing them would be committing a cache.

Orientation, and why each one
-----------------------------

The rule for the shell halves is the whole reason the head splits at all:
each prints **cut-face-down**. The face piece then has the nose pointing at
the ceiling with nothing on the face overhanging more than about 45 degrees,
which matters because the face is the one surface on this object where finish
is the point. The cranium has only its own dome to worry about.

The small parts come off eye_mech.py already lying flat on their largest
face - that was a design constraint there, not luck - so they pass through
untouched.

The ear hub prints face-down: its outer face is the visible one, the three
arms and the speaker spine point up, and the ring recess ends up as a pocket
rather than an overhang.
"""

import bpy
import os
import math
from mathutils import Matrix, Vector

OUT_DIR = r"C:\humalien\humalien\print\v1"

EYE_RAKE_OUT = 25.0     # keep in step with head_style.S["eye"]
EYE_RAKE_DOWN = 10.0


def _flatten_rake(sx):
    """Rotation laying a raked eye bezel face-down on the bed."""
    o = math.radians(EYE_RAKE_OUT)
    d = math.radians(EYE_RAKE_DOWN)
    ax = Vector((sx * math.sin(o), math.cos(o) * math.cos(d),
                 -math.sin(d))).normalized()
    return ax.rotation_difference(Vector((0, 0, -1))).to_matrix().to_4x4()

# (object, quantity, rotation into print orientation, note)
#
# Rotations are about the world origin and are applied to a throwaway copy;
# nothing in the scene moves.
PARTS = [
    ("HEAD_FACE",     1, Matrix.Rotation(math.radians(-90), 4, 'X'),
     "cut face down, nose up - no support on the face"),
    ("HEAD_CRANIUM",  1, Matrix.Rotation(math.radians(90), 4, 'X'),
     "cut face down, dome up"),
    ("ear_hub_R",     1, Matrix.Rotation(math.radians(90), 4, 'Y'),
     "outer face down, arms and speaker spine up"),
    ("ear_hub_L",     1, Matrix.Rotation(math.radians(-90), 4, 'Y'),
     "mirror of R"),
    # The bezels are built on the RAKED socket axis - 25 degrees outboard,
    # 10 down - so no rotation about a single world axis lays them flat. A
    # plain -90 about X left them 23 mm tall and, tellingly, a different
    # footprint left and right, which is the giveaway that the orientation
    # was wrong rather than merely odd. These map the bore axis itself onto
    # -Z. Keep the two angles in step with head_style.S["eye"].
    ("eye_bezel_R",   1, _flatten_rake(+1), "front face down, on its bore axis"),
    ("eye_bezel_L",   1, _flatten_rake(-1), "mirror of R"),
    ("eye_plate",     1, Matrix.Rotation(math.radians(90), 4, 'X'),
     "flat on its face, slot grid up"),
    ("tray_rail_R",   1, Matrix.Identity(4), "flat, as built"),
    ("tray_rail_L",   1, Matrix.Identity(4), "flat, as built"),
    ("forehead_casing", 1, Matrix.Identity(4), "flat on its plate, as eye_mech built it"),
    ("pi5_tray",      1, Matrix.Identity(4), "flat, standoffs up"),
    ("pca9685_mount", 1, Matrix.Identity(4), "flat, bosses up"),
    ("cable_anchor",  4, Matrix.Identity(4), "flat; print four"),
]

BED = 256.0     # Bambu A1, mm cubed


def build(out_dir=OUT_DIR):
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for name, qty, rot, note in PARTS:
        src = bpy.data.objects.get(name)
        if src is None:
            rows.append((name, qty, None, None, "MISSING FROM THE SCENE"))
            continue

        ob = src.copy()
        ob.data = src.data.copy()
        bpy.context.scene.collection.objects.link(ob)
        ob.matrix_world = rot @ src.matrix_world

        # Drop it onto the bed and centre it. Measure from the VERTICES, not
        # from ob.bound_box: bound_box is the object's local box, and
        # transforming its eight corners by a rotation that is not about a
        # single axis gives you the rotated box, whose axis-aligned extent is
        # bigger than the part. That reported a Ø40 x 6 ring as 56 x 54 x 44
        # and made a correct rotation look broken.
        pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts),
                     min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts),
                     max(p.z for p in pts)))
        ob.matrix_world = Matrix.Translation(
            (-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)) @ ob.matrix_world

        dx, dy, dz = hi.x - lo.x, hi.y - lo.y, hi.z - lo.z
        fits = dx <= BED and dy <= BED and dz <= BED

        path = os.path.join(out_dir, "%s_x%d.stl" % (name.lower(), qty))
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True,
                              global_scale=1.0, apply_modifiers=True)
        bpy.data.objects.remove(ob, do_unlink=True)

        rows.append((name, qty, (dx, dy, dz), fits, note))

    print("print/v1  (%s)" % out_dir)
    print("  %-18s qty  bed footprint      height  fits  note" % "part")
    total = 0
    for name, qty, dims, fits, note in rows:
        if dims is None:
            print("  %-18s %3d  %s" % (name, qty, note))
            continue
        total += qty
        print("  %-18s %3d  %6.1f x %6.1f  %6.1f  %-4s  %s"
              % (name, qty, dims[0], dims[1], dims[2],
                 "yes" if fits else "NO", note))
    print("  %d parts, %d prints, bed is %.0f mm cubed" %
          (len(rows), total, BED))
    return rows
