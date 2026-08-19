"""Two human eyeballs, anatomically sized. A mockup, not a mechanism.

    exec(open(r"C:\\H\\humalien\\mockups\\eyeball.py").read())
    build()
    look(pan=12, tilt=-4)
    health()

WHAT THIS IS FOR
----------------
Clean-sheet start, 19 Aug 2026. Everything before this is in
`research archive 01/` and cannot be built on: the head shells were cut from
a sculpt under a No AI licence, so no geometry that touches it can ship in a
product. This file is the first part of the replacement, and it is original
geometry from five numbers and an arc - nothing traced, nothing imported.

It is a MOCKUP. It is the right SIZE and the right SHAPE, so a head drawn
around it will be a head that fits a real human eye. It is not the printed
part: there is no seat, no horn boss, no bore for a shaft, no clearance.
Those get added when there is a mechanism to add them to, and NOT before -
that is the same "chassis first" rule the archive got right, run one step
earlier.

THE FIVE NUMBERS, AND WHY THEY ARE NOT STYLING
----------------------------------------------
Adult eyeballs are the most size-invariant organ in the body. They reach
full size at about age 13 and vary by roughly 1 mm across the whole adult
population - less than the tolerance on a 0.4 mm nozzle. So these are
constants:

    axial length      24.20 mm      cornea apex to rear pole
    sclera radius     11.60 mm      the white ball itself, O23.2
    corneal radius     7.80 mm      a TIGHTER arc than the ball. This one
                                    detail is what makes an eye read as an
                                    eye instead of as a painted marble
    limbus diameter   11.70 mm      where cornea meets sclera
    IPD               63.00 mm      adult mean; female ~62, male ~64

Everything else here is DERIVED from those. The corneal sphere's centre is
not chosen - it is wherever it has to be for a 7.8 mm arc to pass through
the limbus ring on an 11.6 mm ball. Change the limbus diameter and the
cornea re-solves itself, apex and all. Two numbers that would otherwise be
free to drift apart are one number. `report()` prints the solve, including
the axial length it lands on, which is the check that the five agree.

The pupil is the exception and is genuinely variable: 2 mm in bright light,
8 mm in the dark. 4.0 is the mid-light default. `build(7.0)` is the dilated
look, and it is worth seeing both before a head is drawn around this - a
wide pupil reads dramatically less synthetic.

FOUR PARTS PER EYE, AND WHY THE SCLERA HAS A HOLE IN IT
--------------------------------------------------------
    sclera    the white ball, with a O11.7 bore sunk into its front to a
              floor at y=8.4. The bore is what makes the iris visible: a
              plain white ball behind a clear cornea shows WHITE where the
              iris should be. Real sclera is opaque and stops at the limbus,
              and a bore is the geometric way to say that.
    cornea    a 0.55 mm meniscus shell over the bore, standing 1.06 mm proud
              of the sclera's own front pole. Transparent.
    iris      an annulus in the bore, dished 0.2 mm back toward the pupil.
    pupil     a black plug, not a disc - it reaches back to the bore floor,
              so it stays black at 40 degrees off-axis instead of showing
              white ball through the hole.

HOW IT IS BUILT
---------------
One helper: `_revolve`, a lathe. Every part is a closed profile in (r, y)
turned about the gaze axis. No booleans, no modifiers, no solidify - so
there are no boolean failures, no modifier stack to bake before saving, and
every part is watertight by construction rather than by inspection. The
archive lost real time to booleans crashing Blender on the head sculpt;
this is the answer to that, and `health()` proves it rather than assuming.

FRAME
-----
Millimetres. Gaze is +Y, up is +Z, pan about Z, tilt about X. Eye centres at
(+-31.5, 0, 0). This is the archive's convention, kept deliberately: the
servo and board dimensions in there are still good, and a shared frame is
what keeps them readable.
"""

import bpy
import bmesh
import math
from mathutils import Matrix, Vector

COLL = "MOCKUP"         # Pat's scratch collection. Shared - see _coll()

# --- the constants -------------------------------------------------------
AXIAL_REF = 24.20       # published schematic-eye value, checked against below
R_SCLERA  = 11.60
R_CORNEA  = 7.80
LIMBUS_D  = 11.70
IPD       = 63.00

CORNEA_T  = 0.55        # central corneal thickness, 0.52-0.58 in adults
ACD       = 3.00        # anterior chamber: inner cornea to iris front

PUPIL_D   = 4.00        # the one real variable. 2 bright, 4 mid, 8 dark
IRIS_RGB  = (0.16, 0.34, 0.46)      # blue-grey. hazel: (0.34, 0.24, 0.12)

SEGS = 96               # lathe resolution
ARC  = 40               # points per curved profile run

# --- everything below is derived -----------------------------------------
R_LIMBUS = LIMBUS_D / 2.0

# Where the sclera surface is at the limbus radius. Both surfaces meet here.
Y_LIMBUS = math.sqrt(R_SCLERA ** 2 - R_LIMBUS ** 2)

# The corneal sphere's centre: solved, not chosen. It is wherever an R_CORNEA
# arc has to be centred to pass through (R_LIMBUS, Y_LIMBUS).
CORNEA_CY = Y_LIMBUS - math.sqrt(R_CORNEA ** 2 - R_LIMBUS ** 2)
CORNEA_RI = R_CORNEA - CORNEA_T             # inner surface radius
APEX_Y    = CORNEA_CY + R_CORNEA            # front of the whole eye
AXIAL     = APEX_Y + R_SCLERA               # total length, for the check

BORE_FLOOR = 8.40                           # floor of the scleral bore
IRIS_FRONT = CORNEA_CY + CORNEA_RI - ACD    # iris front face, from ACD
IRIS_T     = 0.60
IRIS_DISH  = 0.20                           # front slopes back to the hole
IRIS_R     = R_LIMBUS - 0.15                # just inside the bore wall


def _names():
    return ["eye_%s_%s" % (p, s) for s in ("R", "L")
            for p in ("sclera", "cornea", "iris", "pupil")]


def _coll():
    """Get COLL, creating it if needed, and clear ONLY this file's parts.

    COLL is shared - Pat keeps other mockup pieces in it. So rebuilding must
    delete the eight objects this file owns BY NAME and nothing else. The
    obvious version of this function wipes the whole collection, which would
    silently take his other parts with it every time `build()` is re-run.
    """
    c = bpy.data.collections.get(COLL)
    if c is None:
        c = bpy.data.collections.new(COLL)
        bpy.context.scene.collection.children.link(c)
    for n in _names():
        ob = bpy.data.objects.get(n)
        if ob is not None:
            bpy.data.objects.remove(ob, do_unlink=True)
    return c


def _revolve(profile, segs=SEGS):
    """Lathe a CLOSED (r, y) profile about the +Y axis into a solid.

    A point at r=0 is a pole: one vertex, with a triangle fan to its
    neighbour ring. Two poles in a row get NO faces between them, and that
    rule is what lets a shell like the cornea - a convex tip and a concave
    tip, both sitting on the axis and not joined to each other - come out
    watertight from a single closed profile.
    """
    bm = bmesh.new()
    rings, poles = [], []
    for r, y in profile:
        if r < 1e-9:
            rings.append([bm.verts.new((0.0, y, 0.0))])
            poles.append(True)
        else:
            ring = []
            for i in range(segs):
                a = 2.0 * math.pi * i / segs
                ring.append(bm.verts.new((r * math.cos(a), y, r * math.sin(a))))
            rings.append(ring)
            poles.append(False)
    n = len(rings)
    for k in range(n):
        m = (k + 1) % n
        A, B, pa, pb = rings[k], rings[m], poles[k], poles[m]
        if pa and pb:
            continue                            # two separate tips, no bridge
        if pa:
            for i in range(segs):
                bm.faces.new((A[0], B[i], B[(i + 1) % segs]))
        elif pb:
            for i in range(segs):
                bm.faces.new((A[(i + 1) % segs], A[i], B[0]))
        else:
            for i in range(segs):
                j = (i + 1) % segs
                bm.faces.new((A[i], A[j], B[j], B[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def _arc(cy, rad, y0, y1, steps=ARC):
    """Points on a circle of radius `rad` centred at (0, cy), y0 -> y1."""
    out = []
    for i in range(steps + 1):
        y = y0 + (y1 - y0) * (i / float(steps))
        d = rad ** 2 - (y - cy) ** 2
        out.append((math.sqrt(d) if d > 0.0 else 0.0, y))
    return out


def _mesh(coll, name, bm, sx):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.location = (sx * IPD / 2.0, 0.0, 0.0)
    return ob


def _mat(name, rgba, rough=0.4, alpha=1.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    if b:
        b.inputs["Base Color"].default_value = rgba
        b.inputs["Roughness"].default_value = rough
        if "Alpha" in b.inputs:
            b.inputs["Alpha"].default_value = alpha
        if "IOR" in b.inputs and alpha < 1.0:
            b.inputs["IOR"].default_value = 1.376       # cornea, measured
    m.diffuse_color = (rgba[0], rgba[1], rgba[2], alpha)
    if alpha < 1.0:
        # EEVEE renamed this between versions; set whichever exists.
        for attr, val in (("blend_method", 'BLEND'),
                          ("surface_render_method", 'BLENDED'),
                          ("show_transparent_back", False)):
            try:
                setattr(m, attr, val)
            except (AttributeError, TypeError):
                pass
    return m


def _side(sx):
    return "R" if sx > 0 else "L"


SMOOTH_ANGLE = 35.0     # house rule: everything shaded smooth, always


def shade_smooth(objs, angle_deg=SMOOTH_ANGLE):
    """Smooth every face, then let an angle limit put the hard edges back.

    Angle-limited, not blanket-smooth: the sclera is a lathe with a flat bore
    floor and a vertical bore wall in it, and blanket smoothing would smear
    those into the curve. 4.1 dropped `mesh.use_auto_smooth` for a modifier
    driven by an operator, and the operator has been renamed since, so all
    three spellings are tried - this file has to keep working across
    versions.
    """
    for o in objs:
        for p in o.data.polygons:
            p.use_smooth = True
    win = bpy.context.window_manager.windows[0]
    area = next((a for a in win.screen.areas if a.type == 'VIEW_3D'), None)
    if area is None or not objs:
        return "polys only"
    region = next(r for r in area.regions if r.type == 'WINDOW')
    with bpy.context.temp_override(window=win, area=area, region=region,
                                   selected_objects=list(objs),
                                   selected_editable_objects=list(objs),
                                   active_object=objs[0], object=objs[0]):
        for name, kw in (("shade_smooth_by_angle",
                          {"angle": math.radians(angle_deg)}),
                         ("shade_auto_smooth",
                          {"angle": math.radians(angle_deg)}),
                         ("shade_smooth", {})):
            op = getattr(bpy.ops.object, name, None)
            if op is None:
                continue
            try:
                op(**kw)
                return name
            except Exception:
                continue
    return "polys only"


# --- the four parts ------------------------------------------------------
def sclera(coll, sx):
    """The white ball, bored at the front so the iris can be seen."""
    prof = [(0.0, -R_SCLERA)]
    prof += _arc(0.0, R_SCLERA, -R_SCLERA + 1e-6, Y_LIMBUS)[1:]
    prof += [(R_LIMBUS, BORE_FLOOR), (0.0, BORE_FLOOR)]
    return _mesh(coll, "eye_sclera_" + _side(sx), _revolve(prof), sx)


def cornea(coll, sx):
    """A 0.55 mm meniscus shell, outer arc solved onto the limbus ring."""
    inner_y = CORNEA_CY + math.sqrt(CORNEA_RI ** 2 - R_LIMBUS ** 2)
    prof = [(0.0, APEX_Y)]
    prof += _arc(CORNEA_CY, R_CORNEA, APEX_Y - 1e-6, Y_LIMBUS)[1:]
    prof += [(R_LIMBUS, inner_y)]
    prof += _arc(CORNEA_CY, CORNEA_RI, inner_y,
                 CORNEA_CY + CORNEA_RI - 1e-6)[1:]
    prof += [(0.0, CORNEA_CY + CORNEA_RI)]
    return _mesh(coll, "eye_cornea_" + _side(sx), _revolve(prof), sx)


def iris(coll, sx, pupil_d):
    """An annulus, dished back toward the hole."""
    rp = pupil_d / 2.0 + 0.05
    back = IRIS_FRONT - IRIS_T
    prof = [(IRIS_R, IRIS_FRONT), (rp, IRIS_FRONT - IRIS_DISH),
            (rp, back), (IRIS_R, back)]
    return _mesh(coll, "eye_iris_" + _side(sx), _revolve(prof), sx)


def pupil(coll, sx, pupil_d):
    """A plug, not a disc - it reaches the bore floor so it stays black."""
    rp = pupil_d / 2.0
    top = IRIS_FRONT - IRIS_DISH - 0.05
    floor = BORE_FLOOR + 0.05
    prof = [(0.0, top), (rp, top), (rp, floor), (0.0, floor)]
    return _mesh(coll, "eye_pupil_" + _side(sx), _revolve(prof), sx)


_REST = {}


def build(pupil_d=None):
    pd = PUPIL_D if pupil_d is None else float(pupil_d)
    coll = _coll()
    mats = {
        "sclera": _mat("MOCK_sclera", (0.92, 0.90, 0.875, 1.0), 0.36),
        "cornea": _mat("MOCK_cornea", (1.0, 1.0, 1.0, 1.0), 0.03, alpha=0.10),
        "iris":   _mat("MOCK_iris", IRIS_RGB + (1.0,), 0.28),
        "pupil":  _mat("MOCK_pupil", (0.015, 0.015, 0.02, 1.0), 0.22),
    }
    made = []
    for sx in (1, -1):
        for key, fn in (("sclera", sclera), ("cornea", cornea)):
            ob = fn(coll, sx)
            ob.data.materials.append(mats[key])
            made.append(ob)
        for key, fn in (("iris", iris), ("pupil", pupil)):
            ob = fn(coll, sx, pd)
            ob.data.materials.append(mats[key])
            made.append(ob)
    _REST.clear()
    for ob in made:
        _REST[ob.name] = ob.matrix_world.copy()
    how = shade_smooth(made)
    print("%s: 2 eyes, 4 parts each, pupil O%.1f  (smooth %.0f via %s)"
          % (COLL, pd, SMOOTH_ANGLE, how))
    for ob in made:
        print("  %-16s %5d verts" % (ob.name, len(ob.data.vertices)))
    report()
    return coll


def look(pan=0.0, tilt=0.0):
    """Aim both eyes together. pan about Z, tilt about X, degrees."""
    m = (Matrix.Rotation(math.radians(pan), 4, 'Z') @
         Matrix.Rotation(math.radians(tilt), 4, 'X'))
    for name, rest in _REST.items():
        ob = bpy.data.objects.get(name)
        if ob is None:
            continue
        c = Vector(((IPD / 2.0) if name.endswith("_R") else (-IPD / 2.0),
                    0.0, 0.0))
        ob.matrix_world = (Matrix.Translation(c) @ m @
                           Matrix.Translation(-c) @ rest)
    print("look: pan %+.1f  tilt %+.1f" % (pan, tilt))


def report():
    print("  solved from %.2f sclera / %.2f cornea / %.2f limbus / %.2f ACD:"
          % (R_SCLERA, R_CORNEA, LIMBUS_D, ACD))
    print("    limbus ring         r %.2f, y %.3f" % (R_LIMBUS, Y_LIMBUS))
    print("    corneal centre      y %+.3f  (solved onto the limbus)"
          % CORNEA_CY)
    print("    corneal apex        y %.3f" % APEX_Y)
    print("    proud of sclera     %.2f mm" % (APEX_Y - R_SCLERA))
    print("    axial length        %.2f mm  (published %.2f, delta %+.2f)"
          % (AXIAL, AXIAL_REF, AXIAL - AXIAL_REF))
    print("    iris front          y %.3f" % IRIS_FRONT)
    print("    IPD                 %.1f, centres x %+.1f / %+.1f"
          % (IPD, IPD / 2.0, -IPD / 2.0))


def health():
    """Watertight, one shell each. Built to be true; checked anyway."""
    coll = bpy.data.collections.get(COLL)
    if coll is None:
        print("  nothing built")
        return False
    ok = True
    for ob in coll.objects:
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        open_e = sum(1 for e in bm.edges if len(e.link_faces) != 2)
        bad_n = sum(1 for e in bm.edges if len(e.link_faces) > 2)
        bm.free()
        if open_e or bad_n:
            ok = False
        print("  %-16s %s  open %d  non-manifold %d"
              % (ob.name, "OK  " if not (open_e or bad_n) else "FAIL",
                 open_e, bad_n))
    print("  watertight" if ok else "  NOT watertight")
    return ok
