"""Begin restyling the head mesh into the cyborg of reference photos/.

Run inside Blender, after head_ref.py (and ideally fit_layout.py, so the
openings land on the parts they serve):

    exec(open(r"C:\\humalien\\humalien\\cad\\head_style.py").read())

What the three reference photos share, and what this pass builds:

    - a smooth shell with real thickness            Solidify, 4 mm
    - a large circular port at each ear/temple      boolean cylinders
    - an open rear cranium showing mechanism        boolean rounded box
    - eye openings the mechanism looks through      boolean cylinders at the
                                                    DESIGN pitch 62, not the
                                                    mesh's sculpted 56
    - camera bore + ToF window in the forehead      boolean cuts onto the
                                                    forehead_casing row
    - a visor band across the brow and temples      boolean UNION before the
                                                    solidify, so it merges
                                                    with the skin and shells
                                                    hollow; swallows the
                                                    stock casing the female
                                                    scan could not, and is
                                                    the first piece of the
                                                    sci-fi helmet direction

HEAD_CYBORG is a copy of HEAD_REF (the original is kept and hidden). The
cuts are built as a modifier stack and then BAKED to a plain mesh in the
same run: a live stack of seven booleans over this sculpt crashed Blender
repeatedly - the FLOAT eye cuts through the lid geometry re-evaluating on
every depsgraph touch - and a saved file must not carry that landmine.
Nothing is lost by baking: this script IS the non-destructive layer. Move a
number in S, re-run, and the head regenerates from HEAD_REF. The cutter
objects stay in STYLE_cutters, wireframed, as the visible record of where
every opening is.

The licence note in head_ref.py applies to the copy too: the mesh must not
leave the machine and must never be fed to the MCP generative tools. Boolean
cuts and modifiers are deterministic CAD and are fine.

Still deliberately NOT done here, recorded as debts in fit_layout.py:
    - eye sockets remodelled to the design pitch (the scan's sit at 56)
    - panel seams / face-cranium split lines beyond the band's own crease
    - the neck: cables and mechanism wait for a neck design
"""

import bpy
import bmesh
import math
from mathutils import Matrix

COLL_NAME = "STYLE_Head"
CUT_COLL = "STYLE_cutters"
SRC = "HEAD_REF"

S = dict(
    wall        = 4.0,                  # docs/eye-design-brief.md head budget
    ear_port    = dict(y=95.0, z=204.0, dia=66.0),   # ear centroid, fit_layout
    rear_open   = dict(y0=12.0, y1=55.0, z0=162.0, z1=256.0, r=18.0),
    eye         = dict(pitch=62.0, z=209.0, dia=30.0),  # iris stays visible at +-30 deg pan
    cam_bore    = dict(x=22.0, z=257.5, dia=16.0),   # lens barrel is 14.0
    tof_window  = dict(x=-32.0, z=257.0, w=24.0, h=28.0, r=3.0),
    # The visor band: a designed volume unioned into the skin BEFORE the
    # solidify, so it merges where it emerges and shells hollow like
    # everything else - the intersection crease reads as a helmet seam. The
    # casing stays completely stock (decided 13 Aug: parts keep their
    # corners; styling does the work). The front face is a plan ARC, not a
    # plane: a flat face sat behind the forehead's own bulge and read as
    # inset glass with skin poking through it. The arc stands ~5 proud at
    # centre (skin 195.2) and still covers the casing corners at +-48 with
    # margin (arc y=177.4 there, needs 171). First element of the
    # sci-fi-helmet direction; the segmented cranium panels come next.
    brow        = dict(x_half=56.0, y_back=150.0, y_front=200.0, y_end=165.0,
                       z0=228.0, z1=296.0),
)

SHELL_RGBA = (0.82, 0.79, 0.74, 1.0)
DARK_RGBA = (0.05, 0.05, 0.06, 1.0)


def _mat(name, rgba, rough):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Roughness"].default_value = rough
    m.diffuse_color = rgba
    return m


def _reset():
    for cn in (CUT_COLL, COLL_NAME):
        c = bpy.data.collections.get(cn)
        if c:
            for ob in list(c.objects):
                bpy.data.objects.remove(ob, do_unlink=True)
            bpy.data.collections.remove(c)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    coll = bpy.data.collections.new(COLL_NAME)
    bpy.context.scene.collection.children.link(coll)
    cuts = bpy.data.collections.new(CUT_COLL)
    coll.children.link(cuts)
    return coll, cuts


def _obj(name, bm, coll, mat):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    me.materials.append(mat)
    coll.objects.link(ob)
    return ob


def cyl(name, coll, mat, dia, length, loc, axis):
    """Closed cylinder along +X or +Y through loc."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, radius1=dia / 2, radius2=dia / 2,
                          depth=length, segments=64)
    rot = Matrix.Rotation(math.radians(90), 4, 'Y' if axis == 'X' else 'X')
    bmesh.ops.transform(bm, matrix=rot, verts=bm.verts[:])
    bmesh.ops.translate(bm, vec=loc, verts=bm.verts[:])
    return _obj(name, bm, coll, mat)


def rrect_box(name, coll, mat, w, h, r, length, loc, plane='YZ'):
    """Rounded-rect profile in the given plane, extruded through `length`.
    plane 'YZ': profile in y/z, extruded along X (the rear opening).
    plane 'XZ': profile in x/z, extruded along Y (the ToF window)."""
    r = max(0.01, min(r, w / 2 - 0.01, h / 2 - 0.01))
    pts = []
    segs = 8
    for (ox, oy, a0) in ((w / 2 - r, h / 2 - r, 0.0), (-(w / 2 - r), h / 2 - r, 90.0),
                         (-(w / 2 - r), -(h / 2 - r), 180.0), (w / 2 - r, -(h / 2 - r), 270.0)):
        for i in range(segs + 1):
            a = math.radians(a0 + 90.0 * i / segs)
            pts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    bm = bmesh.new()
    if plane == 'YZ':
        bot = [bm.verts.new((-length / 2, px, py)) for (px, py) in pts]
        top = [bm.verts.new((length / 2, px, py)) for (px, py) in pts]
    else:
        bot = [bm.verts.new((px, -length / 2, py)) for (px, py) in pts]
        top = [bm.verts.new((px, length / 2, py)) for (px, py) in pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bm.faces.new(bot[::-1])
    bm.faces.new(top)
    bmesh.ops.translate(bm, vec=loc, verts=bm.verts[:])
    return _obj(name, bm, coll, mat)


def arc_band(name, coll, mat, x_half, y_back, y_front, y_end, z0, z1,
             segs=32):
    """Visor slab: plan profile is an arc front (through (0, y_front) and
    (+-x_half, y_end)) closed by a straight back edge at y_back, extruded
    z0..z1."""
    yc = (y_front ** 2 - y_end ** 2 - x_half ** 2) / (2.0 * (y_front - y_end))
    r = y_front - yc
    a_end = math.asin(x_half / r)
    pts = []
    for i in range(segs + 1):
        a = -a_end + 2.0 * a_end * i / segs
        pts.append((r * math.sin(a), yc + r * math.cos(a)))
    pts.append((x_half, y_back))
    pts.append((-x_half, y_back))
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, z0)) for (x, y) in pts]
    top = [bm.verts.new((x, y, z1)) for (x, y) in pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bm.faces.new(bot[::-1])
    bm.faces.new(top)
    return _obj(name, bm, coll, mat)


def _copy_head_drop_eyeballs(coll, mat_shell, mat_dark):
    """Copy HEAD_REF, delete its two sculpted-eyeball islands (our eyes sit at
    pitch 62; the sculpted pair at 56 would poke through the proxies)."""
    src = bpy.data.objects[SRC]
    me = src.data.copy()
    me.name = "HEAD_CYBORG"
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    visited = [False] * len(bm.verts)
    comps = []
    for v in bm.verts:
        if visited[v.index]:
            continue
        stack = [v]; visited[v.index] = True; comp = []
        while stack:
            cur = stack.pop(); comp.append(cur)
            for e in cur.link_edges:
                o = e.other_vert(cur)
                if not visited[o.index]:
                    visited[o.index] = True; stack.append(o)
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    drop = [v for c in comps[1:] for v in c]
    if drop:
        bmesh.ops.delete(bm, geom=drop, context='VERTS')
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("HEAD_CYBORG", me)
    me.materials.clear()
    me.materials.append(mat_shell)
    me.materials.append(mat_dark)
    ob.color = SHELL_RGBA
    coll.objects.link(ob)
    return ob


def build():
    coll, cuts = _reset()
    mat_shell = _mat("MAT_shell", SHELL_RGBA, 0.35)
    mat_dark = _mat("MAT_interior", DARK_RGBA, 0.6)
    head = _copy_head_drop_eyeballs(coll, mat_shell, mat_dark)

    # ---- cutters (dark material, so every bore reads mechanical) ----
    ep = S["ear_port"]
    ports = []
    for sx, side in ((1, "R"), (-1, "L")):
        ports.append(cyl("CUT_ear_port_%s" % side, cuts, mat_dark,
                         ep["dia"], 60.0, (sx * 67.0, ep["y"], ep["z"]), 'X'))
    ro = S["rear_open"]
    rear = rrect_box("CUT_rear_opening", cuts, mat_dark,
                     ro["y1"] - ro["y0"], ro["z1"] - ro["z0"], ro["r"], 200.0,
                     (0, (ro["y0"] + ro["y1"]) / 2, (ro["z0"] + ro["z1"]) / 2),
                     'YZ')
    ey = S["eye"]
    eyes = []
    for sx, side in ((1, "R"), (-1, "L")):
        eyes.append(cyl("CUT_eye_%s" % side, cuts, mat_dark,
                        ey["dia"], 70.0, (sx * ey["pitch"] / 2, 165.0, ey["z"]), 'Y'))
    cb = S["cam_bore"]
    cam = cyl("CUT_cam_bore", cuts, mat_dark,
              cb["dia"], 60.0, (cb["x"], 175.0, cb["z"]), 'Y')
    tw = S["tof_window"]
    tof = rrect_box("CUT_tof_window", cuts, mat_dark,
                    tw["w"], tw["h"], tw["r"], 60.0, (tw["x"], 175.0, tw["z"]),
                    'XZ')

    # ---- modifier stack: brow union onto the raw skin, then the shell,
    # then the cuts ----
    bb = S["brow"]
    band = arc_band("STYLE_visor_band", cuts, mat_shell,
                    bb["x_half"], bb["y_back"], bb["y_front"], bb["y_end"],
                    bb["z0"], bb["z1"])
    ub = head.modifiers.new("VisorBand", 'BOOLEAN')
    ub.operation = 'UNION'
    ub.solver = 'EXACT'
    ub.object = band

    sol = head.modifiers.new("Shell", 'SOLIDIFY')
    sol.thickness = S["wall"]
    sol.offset = -1.0                 # inward: the outer surface stays the face
    sol.use_rim = True
    sol.material_offset_rim = 1       # rims in MAT_interior

    # The eye cuts run on the FLOAT solver: the sculpted lid creases
    # self-intersect once solidified, and EXACT resolves the winding so badly
    # it discards the whole shell (98k verts in, 1.6k out). FLOAT trims them
    # cleanly; EXACT stays on for every other cut because it makes cleaner
    # seams and those regions are well-behaved.
    for name, cutter in [("EarPortR", ports[0]), ("EarPortL", ports[1]),
                         ("RearOpening", rear),
                         ("EyeR", eyes[0]), ("EyeL", eyes[1]),
                         ("CamBore", cam), ("ToFWindow", tof)]:
        mod = head.modifiers.new(name, 'BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.solver = 'FLOAT' if name.startswith("Eye") else 'EXACT'
        mod.object = cutter

    for c in cuts.objects:
        c.display_type = 'WIRE'
        c.hide_render = True
    cuts.hide_viewport = True

    # ---- bake: one evaluation, then a plain mesh ----
    # The one heavy moment. After this there is nothing live left to
    # re-evaluate, and the saved file is dumb data.
    dg = bpy.context.evaluated_depsgraph_get()
    ev = head.evaluated_get(dg)
    baked = bpy.data.meshes.new_from_object(
        ev, preserve_all_data_layers=True, depsgraph=dg)
    baked.name = "HEAD_CYBORG_baked"
    old = head.data
    head.modifiers.clear()
    head.data = baked
    bpy.data.meshes.remove(old)

    # smooth shading, hard edges kept by angle so the port bores and the
    # visor seam stay crisp
    baked.polygons.foreach_set("use_smooth", [True] * len(baked.polygons))
    if hasattr(baked, "set_sharp_from_angle"):
        baked.set_sharp_from_angle(angle=math.radians(40.0))
    baked.update()

    # the raw reference stays but gets out of the way
    bpy.data.objects[SRC].hide_set(True)

    print("STYLE_Head built: shell %.1f, ear ports Ø%.0f at (y%.0f z%.0f), "
          "rear opening y %.0f..%.0f z %.0f..%.0f, eyes Ø%.0f at pitch %.0f, "
          "cam bore Ø%.0f, ToF window %sx%s" % (
              S["wall"], ep["dia"], ep["y"], ep["z"],
              ro["y0"], ro["y1"], ro["z0"], ro["z1"],
              ey["dia"], ey["pitch"], cb["dia"], tw["w"], tw["h"]))
    return head


if __name__ == "__main__":
    build()
