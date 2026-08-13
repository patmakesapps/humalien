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
    - a smooth human silhouette, kept               NO added volumes. A visor
                                                    band was tried and
                                                    withdrawn: the refs get
                                                    their cyborg from seams,
                                                    hubs and openings. The
                                                    casing corners vs the
                                                    brow flanks stay an open
                                                    debt - chamfer and swell
                                                    both parameterized, both
                                                    off, decision pending

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
    - panel seams and the face/cranium split lines the references show
    - the ear hub as a real printed part (ring + speaker grille + mount)
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
    # Ø41 swallows the sculpt's ENTIRE eyelid structure per side, so the
    # bore lands on clean single-surface skin. A Ø30 cut sliced through the
    # four lid shells and left torn walls inside the opening - the "poor
    # topology in eye sockets". The eyeball reads near-flush in a smooth
    # circular opening, which is the white-shell reference's eye.
    eye         = dict(pitch=62.0, z=209.0, dia=41.0),
    cam_bore    = dict(x=22.0, z=257.5, dia=16.0),   # lens barrel is 14.0
    tof_window  = dict(x=-32.0, z=257.0, w=24.0, h=28.0, r=3.0),
    # The helmet/visor idea is DEAD (13 Aug, withdrawn after looking at the
    # reference photos again: every ref keeps a smooth human silhouette and
    # gets its cyborg from seams, hubs and openings - never added volume).
    # The casing's top corners still breach the brow flanks by ~10 mm; that
    # stays an OPEN debt, recorded in fit_layout.py. Two candidate fixes are
    # parameterized but off: a corner chamfer on the part (written and
    # reverted twice - the part stays stock until decided) and this smooth
    # normal-direction swell at the flanks, parked at amp=0 because nobody
    # asked for added volume. amp~9 centred on the board corners would cover
    # them if that day comes.
    swell       = dict(x=42.0, y=167.0, z=274.0, r=30.0, amp=0.0),
    # Interior junk behind the closed lips - the sculpt's mouth bag. A face
    # in this box whose outward-normal offset point is still INSIDE the
    # closed skin is hidden geometry and goes.
    mouth_bag   = dict(x0=-30.0, x1=30.0, y0=140.0, y1=189.0,
                       z0=122.0, z1=162.0),
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


def _copy_head_drop_eyeballs(coll, mat_shell, mat_dark):
    """Copy HEAD_REF and clean it: drop the two sculpted-eyeball islands
    (our eyes sit at pitch 62; the sculpted pair at 56 would poke through
    the proxies), delete the hidden mouth-bag geometry, and blend the
    subtle brow-flank swell in."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
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

    # ---- mouth bag: delete interior faces ----
    bm.normal_update()
    tree = BVHTree.FromBMesh(bm)
    D = Vector((0.331, 0.537, 0.774)).normalized()

    def _inside(p):
        hits = 0; t0 = 0.0
        for _ in range(24):
            loc, nrm, idx, dist = tree.ray_cast(p + D * (t0 + 0.05), D)
            if loc is None:
                break
            hits += 1
            t0 = (loc - p).dot(D)
        return hits % 2 == 1

    mb = S["mouth_bag"]
    doomed = []
    for f in bm.faces:
        c = f.calc_center_median()
        if (mb["x0"] < c.x < mb["x1"] and mb["y0"] < c.y < mb["y1"]
                and mb["z0"] < c.z < mb["z1"]):
            if _inside(c + f.normal * 0.6):
                doomed.append(f)
    if doomed:
        print("mouth bag: deleting %d interior faces" % len(doomed))
        bmesh.ops.delete(bm, geom=doomed, context='FACES')

    # ---- eye region pre-clean ----
    # The lash cards and lid shells are thin strips a boolean cannot remove
    # reliably - they enclose no volume, so solvers leave them floating
    # across the opening. Delete every face within r=19 of an eye axis
    # first (y>150 so the back of the head, which the same axis crosses, is
    # untouched); the Ø41 socket cut then trims the surrounding skin to a
    # clean circle through simple surface.
    er = S["eye"]
    doomed = []
    for f in bm.faces:
        c = f.calc_center_median()
        if c.y < 150.0:
            continue
        for sx in (-1, 1):
            dx = c.x - sx * er["pitch"] / 2.0
            dz = c.z - er["z"]
            if dx * dx + dz * dz < 19.0 * 19.0:
                doomed.append(f)
                break
    if doomed:
        print("eye pre-clean: deleting %d lid/lash faces" % len(doomed))
        bmesh.ops.delete(bm, geom=doomed, context='FACES')

    # ---- brow-flank swell, both sides ----
    bm.normal_update()
    sw = S["swell"]
    for v in bm.verts:
        for sx in (-1, 1):
            d = (Vector((sx * sw["x"], sw["y"], sw["z"])) - v.co).length
            if d < sw["r"]:
                t = 1.0 - d / sw["r"]
                v.co += v.normal * (sw["amp"] * t * t * (3.0 - 2.0 * t))

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

    # ---- modifier stack: shell first, then the cuts ----
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
