"""Fit study: place the printed parts inside the head reference mesh.

Run inside Blender, AFTER eye_mech.py has built HUMALIEN and head_ref.py has
built REF_Head:

    exec(open(r"C:\\humalien\\humalien\\cad\\fit_layout.py").read())

Rebuilds the FIT_Assembly collection from scratch every run. Three kinds of
object live in it, told apart by name:

    FIT_*    linked duplicates of the real printed parts (same mesh data as
             HUMALIEN, so a re-run of eye_mech.py followed by a re-run of this
             script picks up part changes)
    PROXY_*  boards and bought parts the printed parts hold, built from the
             same dimensions BOARDS in eye_mech.py carries. Sources noted per
             proxy; the speaker is listing-grade and its numbers are
             placeholders - see BOARDS["speaker"].
    CHECK_*  gauges for the envelope rules in docs/eye-design-brief.md

Axes as in eye_mech.py: +X Humalien's right, +Y forward (gaze), +Z up.
Units: 1 unit = 1 mm.

Every position here is PROVISIONAL by design - the skull-side fixings on the
parts are slotted precisely because these numbers are guesswork until a head
shell exists to offer them up to. The layout only has to be collision-clean
and honest about where the envelope fights the mesh.

Placement numbers measured off HEAD_REF on 13 Aug 2026 (breadth 150, nose tip
y=209 z=177, nasion z=213, ear centroid y=91-102 z=202-205, eye-zone shell
front y=179.3):

    eye line      z=209, just below the nasion at 213
    eye centres   (+-31, 160, 209): pitch 62 from P["eye_pitch"]. The glow
                  comes from a pixel INSIDE each eyeball (13 Aug decision),
                  through a translucent printed iris - nothing static sits
                  in front of the eye at all
    ear rings     the NeoPixel rings (shipping) live behind the ear ports as
                  accent rings around the speaker grilles, back face |x|=56
    casing        upright, boards facing +Y, front face y=167, aperture row
                  z=257.5. Bottom edge z=225 clears the eyeball tops (an
                  eyeball point forward of y=167 exists only below z=223.4)
                  and the ring backs sit at 172.5, 5.5 clear of the face.
    pi5 tray      flat, long axis fore-aft, plate z=256..259, board centre
                  y=90: hat-height stack stays clear of the rear dome
    pca9685       upright against the rear wall (inner y=28..32 over its
                  span), board facing forward at y=32..40
    speakers      one behind each ear, driver facing out through the future
                  ear port; LISTING-GRADE dims, zone markers not fit parts
"""

import bpy
import bmesh
import math
from mathutils import Matrix, Euler

COLL_NAME = "FIT_Assembly"

# ---------------------------------------------------------------------------
# design choices for this layout (everything else derives from parts)
# ---------------------------------------------------------------------------
L = dict(
    eye_pitch    = 62.0,     # = P["eye_pitch"] in eye_mech.py, provisional
    eye_z        = 209.0,    # nasion 213 measured; pupils sit just below
    eye_y        = 160.0,    # ring front face = 160+19.2 = 179.2, shell 179.3
    eyeball_dia  = 32.0,     # Cogley Component74, measured
    ring_od      = 36.830,   # Adafruit .brd, exact
    ring_id      = 23.368,
    ring_t       = 6.7,
    earring_x    = 56.6,     # ring back face; front at 63.3, sitting 0.3
                             # proud of the ear hub's face, recessed behind
                             # the Ø66 port mouth. Its rim crosses the raw
                             # skin below the ear, but every such point is
                             # inside the port bore (ring r 18.4 vs port
                             # r 33, concentric), so on the styled head it
                             # lives in the opening - see EXPECTED_OUT
    earhub_x     = 47.5,     # ear_hub outer face; the part is REAL now and
                             # lives in MOUNT_Parts, built by head_mounts.py.
                             # The PROXY_ear_hub_TBD disc that used to stand
                             # in for it is gone.
    iris         = dict(d=12.0, t=1.6),
                             # translucent printed iris window the eye pixel
                             # glows through; sits on the eyeball front pole

    casing_y     = 162.0,    # back face; plate 5 thick -> front face 167
    casing_z     = 254.0,    # plate centre; spans z 225..283, row at 257.5

    tray_y       = 90.0,     # tray/board centre; plate z below
    tray_z       = 256.0,    # plate 256..259, standoffs to 264, board to 265.6

    pca_y        = 44.0,     # back face: rear wall inner reaches 41.4 at the
                             # plate's x=39 corners; the bowed wall gets
                             # printed bosses under the slots like any fixing
    pca_z        = 230.0,    # spans z 209..251

    # The speaker is no longer a zone marker floating near a wall - it bolts
    # to the back of the ear_hub, on the two posts head_mounts puts there,
    # so its position is now set by the hub and not guessed. Outer face at
    # |x|=29.5, which is the post face; the module hangs inboard from there.
    # Dimensions are still LISTING and the flange pitch is still assumed.
    spk_wall_x   = 29.5,
    spk_y        = 95.0,     # concentric with the ear port
    spk_z        = 204.0,
    spk_roll     = 0.0,      # it sits on the hub, so it follows the hub

    ear_port     = (95.0, 204.0, 66.0),  # (y, z, dia) for the styling pass
)

# board dims restated from eye_mech.py BOARDS with their confidence; keep in
# step by eye when either file changes
PI5   = dict(w=85.0, d=56.0, t=1.6)                      # exact, RPi drawing
PCA   = dict(w=62.230, d=25.400, t=1.6)                  # exact, Adafruit .brd
B0385 = dict(w=38.0, t=1.6, holder=18.0, holder_h=7.0,   # drawing, Arducam
             barrel_d=14.0, barrel_proud=6.2)            # 13.2 less the holder
VL53  = dict(w=23.0, h=28.5, t=1.6)                      # proven, LumaBot slot
SPK   = dict(w=30.0, h=70.0, t=16.0)                     # LISTING - placeholder

# orientations ------------------------------------------------------------
# printed flat -> mounted upright, working face forward, load opening up.
# local +z (boards) -> +Y, local +y (channel top) -> +Z, local +x -> -X.
R_FWD = Matrix.Rotation(math.radians(180), 4, 'Z') @ Matrix.Rotation(math.radians(90), 4, 'X')
R_FLAT_90 = Matrix.Rotation(math.radians(90), 4, 'Z')   # tray: long axis fore-aft
R_SIDE_R = Matrix.Rotation(math.radians(-90), 4, 'Y')   # local +z -> -X (right wall)
R_SIDE_L = Matrix.Rotation(math.radians(90), 4, 'Y')    # local +z -> +X (left wall)

COL_PART  = (0.20, 0.65, 0.70, 1.0)
COL_PROXY = (0.90, 0.50, 0.15, 1.0)
COL_CHECK = (0.95, 0.85, 0.20, 1.0)
COL_GLOW  = (0.55, 0.85, 1.00, 1.0)
COL_HUB   = (0.06, 0.06, 0.07, 1.0)


def _mat(name, rgba, emit=0.0):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    if b:
        b.inputs["Base Color"].default_value = rgba
        if "Emission Color" in b.inputs:
            b.inputs["Emission Color"].default_value = rgba
        if "Emission Strength" in b.inputs:
            b.inputs["Emission Strength"].default_value = emit
    m.diffuse_color = rgba
    return m


def _coll():
    c = bpy.data.collections.get(COLL_NAME)
    if c:
        for ob in list(c.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(c)
    for me in list(bpy.data.meshes):
        if me.users == 0 and me.name.startswith(("PROXY_", "CHECK_")):
            bpy.data.meshes.remove(me)
    c = bpy.data.collections.new(COLL_NAME)
    bpy.context.scene.collection.children.link(c)
    return c


def _smooth(me, angle=40.0):
    """Smooth shading with hard edges kept by angle - printed parts stay
    crisp, curved faces stop showing facets."""
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    if hasattr(me, "set_sharp_from_angle"):
        me.set_sharp_from_angle(angle=math.radians(angle))
    me.update()


def _link(coll, ob, color):
    coll.objects.link(ob)
    ob.color = color
    if ob.type == 'MESH':
        _smooth(ob.data)
    return ob


def part(coll, src_name, new_name, loc, rot=None):
    """Linked duplicate of a HUMALIEN part, placed. Shares mesh data."""
    src = bpy.data.objects[src_name]
    ob = src.copy()                       # object copy, same .data
    ob.name = new_name
    ob.matrix_world = Matrix.Translation(loc) @ (rot or Matrix.Identity(4))
    return _link(coll, ob, COL_PART)


def box(coll, name, dims, loc, color=COL_PROXY):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=dims, verts=bm.verts[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    return _link(coll, ob, color)


def sphere(coll, name, dia, loc):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=dia / 2)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    return _link(coll, ob, COL_PROXY)


def cyl(coll, name, dia, length, loc, axis='Y', color=COL_PROXY, mat=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, radius1=dia / 2, radius2=dia / 2,
                          depth=length, segments=48)
    if axis == 'Y':
        rot = Matrix.Rotation(math.radians(90), 4, 'X')
    elif axis == 'X':
        rot = Matrix.Rotation(math.radians(90), 4, 'Y')
    else:
        rot = Matrix.Identity(4)
    bmesh.ops.transform(bm, matrix=rot, verts=bm.verts[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    if mat:
        me.materials.append(mat)
    return _link(coll, ob, color)


def annulus(coll, name, od, idia, t, loc, segs=48):
    """Flat ring, axis +Y, front face at loc.y + t (built from y=0..t)."""
    bm = bmesh.new()
    ro, ri = od / 2, idia / 2
    loops = []
    for y in (0.0, t):
        for r in (ro, ri):
            loops.append([bm.verts.new((r * math.cos(a), y, r * math.sin(a)))
                          for a in [2 * math.pi * i / segs for i in range(segs)]])
    bo, bi, to, ti = loops
    for ring_a, ring_b in ((bo, to), (bi, ti), (bo, bi), (to, ti)):
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((ring_a[i], ring_a[j], ring_b[j], ring_b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    return _link(coll, ob, COL_PROXY)


def build(force=False):
    guard(collection_contents(COLL_NAME), "fit_layout.build()", force)
    coll = _coll()

    # ---- the real printed parts, linked ----
    part(coll, "forehead_casing", "FIT_forehead_casing",
         (0, L["casing_y"], L["casing_z"]), R_FWD)
    part(coll, "pi5_tray", "FIT_pi5_tray",
         (0, L["tray_y"], L["tray_z"]), R_FLAT_90)
    part(coll, "pca9685_mount", "FIT_pca9685_mount",
         (0, L["pca_y"], L["pca_z"]), R_FWD)
    # cable anchors: two on the rear wall for the GPIO loom drop, two low on
    # the side walls where the looms turn down the neck, two parked - anchors
    # only earn a position once a loom exists to hold
    part(coll, "cable_anchor", "FIT_cable_anchor_1", (14, 35, 240), R_FWD)
    part(coll, "cable_anchor", "FIT_cable_anchor_2", (-14, 35, 240), R_FWD)
    # 3 and 4 dropped from z=158 to z=140: at the old height they shared
    # space with the ear hub's speaker spine, which did not exist when they
    # were placed. Low on the side wall is still where the loom turns down
    # towards the neck.
    part(coll, "cable_anchor", "FIT_cable_anchor_3", (38, 92, 140), R_SIDE_R)
    part(coll, "cable_anchor", "FIT_cable_anchor_4", (-38, 92, 140), R_SIDE_L)
    part(coll, "cable_anchor", "FIT_cable_anchor_5_PARKED", (14, 70, 108))
    part(coll, "cable_anchor", "FIT_cable_anchor_6_PARKED", (-14, 70, 108))

    # ---- proxies for what the parts hold ----
    mat_glow = _mat("MAT_glow", COL_GLOW, emit=3.0)
    mat_hub = _mat("MAT_hub", COL_HUB)
    ey, ez = L["eye_y"], L["eye_z"]
    for sx, side in ((-1, "L"), (1, "R")):          # Humalien's left = -X
        x = sx * L["eye_pitch"] / 2
        sphere(coll, "PROXY_eyeball_%s" % side, L["eyeball_dia"], (x, ey, ez))
        # the glow: an addressable 5050 pixel INSIDE the eyeball behind a
        # translucent printed iris window on the front pole. Pixel carrier
        # unbought and unmeasured, hence LISTING
        box(coll, "PROXY_eye_led_%s_LISTING" % side, (8.0, 3.0, 8.0),
            (x, ey - 4.0, ez))
        cyl(coll, "PROXY_iris_%s" % side, L["iris"]["d"], L["iris"]["t"],
            (x, ey + L["eyeball_dia"] / 2 + L["iris"]["t"] / 2 - 0.8, ez),
            'Y', COL_GLOW, mat_glow)
        # the NeoPixel ring, sitting in the recess in the real ear_hub's
        # face. The hub itself is a printed part now, not a proxy disc.
        ring = annulus(coll, "PROXY_neopixel_ear_%s" % side, L["ring_od"],
                       L["ring_id"], L["ring_t"],
                       (sx * (L["earhub_x"] - L["ring_t"]),
                        L["ear_port"][0], L["ear_port"][1]))
        ring.rotation_euler = (0, 0, math.radians(-sx * 90))
        ring.data.materials.append(mat_glow)
        ring.color = COL_GLOW

    # Pi 5 board on its tray standoffs (tray plate 3 + standoff 5)
    bz = L["tray_z"] + 3.0 + 5.0 + PI5["t"] / 2
    box(coll, "PROXY_pi5_board", (PI5["d"], PI5["w"], PI5["t"]),
        (0, L["tray_y"], bz))

    # PCA9685 board on its bosses (plate 3 + boss 3.5), facing forward
    by = L["pca_y"] + 3.0 + 3.5 + PCA["t"] / 2
    box(coll, "PROXY_pca9685_board", (PCA["w"], PCA["t"], PCA["d"]),
        (0, by, L["pca_z"]))

    # camera: board in its pocket (recessed 1.8), holder, barrel. Camera sits
    # at part-local x=-22 -> world +22, on the row at casing_z + 3.5
    cx, rz = 22.0, L["casing_z"] + 3.5
    y0 = L["casing_y"]                              # casing back face
    box(coll, "PROXY_b0385_board", (B0385["w"], B0385["t"], B0385["w"]),
        (cx, y0 + 4.0, rz))
    box(coll, "PROXY_b0385_holder",
        (B0385["holder"], B0385["holder_h"], B0385["holder"]),
        (cx, y0 + 4.8 + B0385["holder_h"] / 2, rz))
    bar = box(coll, "PROXY_b0385_barrel",
              (B0385["barrel_d"], B0385["barrel_proud"], B0385["barrel_d"]),
              (cx, y0 + 11.8 + B0385["barrel_proud"] / 2, rz))

    # VL53L1X standing in its channel at part-local x=+32 -> world -32; board
    # plane centred in the 2.1 groove, world y = back face + 2.95
    box(coll, "PROXY_vl53l1x_board", (VL53["w"], VL53["t"], VL53["h"]),
        (-32.0, y0 + 2.95, L["casing_z"] + 3.2))

    # speakers - LISTING-GRADE placeholder dims, zone markers only. The side
    # wall is a dome, so the module leans with it: top outboard, bottom
    # tucked in
    for sx, side in ((-1, "L"), (1, "R")):
        sp = box(coll, "PROXY_speaker_%s_LISTING" % side,
                 (SPK["t"], SPK["w"], SPK["h"]),
                 (sx * (L["spk_wall_x"] - SPK["t"] / 2), L["spk_y"], L["spk_z"]))
        sp.rotation_euler = (0, math.radians(sx * L["spk_roll"]), 0)

    # ---- gauges ----
    bar = box(coll, "CHECK_100mm_across", (100.0, 2.0, 2.0),
              (0, ey, ez), COL_CHECK)
    bar.display_type = 'WIRE'

    return coll


def report():
    print("FIT_Assembly placements (all provisional, slotted fixings exist for a reason):")
    rows = [
        ("eyeballs Ø32 + pixel", "(+-31, 160, 209)", "glow through the iris window on the front pole"),
        ("ear hub + ring", "in the Ø66 ports, face |x|~63", "hub is the TBD printed part; ring recessed in it, glowing"),
        ("forehead_casing", "y 162..167, z 225..283", "row z=257.5, cam +22 / ToF -32"),
        ("pi5_tray", "y 43.5..136.5, z 256..259", "board top 265.6, hat ~282"),
        ("pca9685_mount", "y 42..50, z 209..251", "against rear wall"),
        ("speakers", "outer face |x|~54.5, z 175..245", "LISTING dims, behind ear ports"),
        ("ear port (styling)", "y=95 z=204 Ø66", "from ear centroid; verify visually"),
    ]
    for name, where, note in rows:
        print("  %-22s %-28s %s" % (name, where, note))


# ---------------------------------------------------------------------------
# containment check: every sampled vertex of every FIT/PROXY object should be
# inside the head skin. Ray parity against the skin only - the mesh carries
# two small sculpted-eyeball components (pitch 56, z~214) that are dropped
# first, both because parity through them misleads and because those sockets
# are exactly what the styling pass remodels.
#
# Breaches listed in EXPECTED_OUT are fine for a recorded reason: either the
# head gets remodelled to serve the part (docs/eye-design-brief.md - "the
# head serves the parts, not the other way round"), or the part lives inside
# an opening the styled head cuts, where a raw-skin check has no meaning.
# Anything else poking out is a layout bug in this file.
# ---------------------------------------------------------------------------
EXPECTED_OUT = {
    "PROXY_eyeball_L": "in the styled socket, which the raw skin does not have",
    "PROXY_eyeball_R": "in the styled socket, which the raw skin does not have",
    "PROXY_iris_L": "on the eyeball front pole, inside the styled socket",
    "PROXY_iris_R": "on the eyeball front pole, inside the styled socket",
    "PROXY_neopixel_ear_L": "concentric inside the Ø66 ear-port bore (r 18.4 vs 33)",
    "PROXY_neopixel_ear_R": "concentric inside the Ø66 ear-port bore (r 18.4 vs 33)",
}
# The brow-flank breach is NOT on this list any more. It was three entries -
# the casing and both boards - carried as an open debt against the day
# somebody decided between a fuller brow and a chamfered plate. Both were
# done on 13 Aug: S["swell"] in head_style.py took 10.3 mm down to 4.6, and
# casing_chamfer() in head_mounts.py removed the corners the rest of it was
# in. If any of the three comes back, it is a regression, so it gets to fail.


def verify(head_name=None):
    """Ask HEAD_SKIN if it exists, and HEAD_REF only if it does not.

    HEAD_SKIN is head_style's cleaned single surface - same closed skin,
    but carrying the neck cut and the brow swell, which is what the parts
    actually have to live inside. Never ask HEAD_CYBORG: it is a solidified
    shell, so a ray from the middle of the skull crosses the inner wall and
    then the outer wall, comes back even, and the parity test reports that
    the Pi is outside the head.
    """
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    if head_name is None:
        head_name = "HEAD_SKIN" if "HEAD_SKIN" in bpy.data.objects else "HEAD_REF"
    print("fit check against %s" % head_name)
    head = bpy.data.objects[head_name]
    bm = bmesh.new()
    bm.from_object(head, dg)
    bm.transform(head.matrix_world)
    bm.verts.ensure_lookup_table()
    visited = [False] * len(bm.verts)
    comps = []
    for v in bm.verts:
        if visited[v.index]:
            continue
        stack = [v]; visited[v.index] = True; comp = []
        while stack:
            cur = stack.pop(); comp.append(cur.index)
            for e in cur.link_edges:
                o = e.other_vert(cur)
                if not visited[o.index]:
                    visited[o.index] = True; stack.append(o)
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    kill = {i for c in comps[1:] for i in c}
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index in kill],
                     context='VERTS')
    tree = BVHTree.FromBMesh(bm)

    D = Vector((0.331, 0.537, 0.774)).normalized()

    def inside(p):
        hits = 0; t0 = 0.0
        for _ in range(24):
            loc, nrm, idx, dist = tree.ray_cast(p + D * (t0 + 0.05), D)
            if loc is None:
                break
            hits += 1
            t0 = (loc - p).dot(D)
        return hits % 2 == 1

    clean = True
    print("fit check (sampled verts outside the skin):")
    for ob in sorted(bpy.data.collections[COLL_NAME].objects,
                     key=lambda o: o.name):
        if ob.type != 'MESH' or ob.name.startswith("CHECK_"):
            continue
        me = ob.evaluated_get(dg).to_mesh()
        verts = me.vertices
        step = max(1, len(verts) // 300)
        worst = 0.0; n_out = 0; wp = None
        for i in range(0, len(verts), step):
            p = ob.matrix_world @ verts[i].co
            if not inside(p):
                n_out += 1
                loc, nrm, idx, dist = tree.find_nearest(p)
                if dist > worst:
                    worst, wp = dist, p
        ob.evaluated_get(dg).to_mesh_clear()
        if n_out == 0:
            continue
        debt = EXPECTED_OUT.get(ob.name)
        tag = "expected - " + debt if debt else "LAYOUT BUG"
        if not debt:
            clean = False
        print("  %-26s %3d out, worst %5.1fmm at (%.0f,%.0f,%.0f)  [%s]" % (
            ob.name, n_out, worst, wp.x, wp.y, wp.z, tag))
    bm.free()
    print("fit check:", "CLEAN (styling debts aside)" if clean else "LAYOUT BUGS ABOVE")
    return clean


# ---------------------------------------------------------------------------
# collision check: does any part pass through any other part?
#
# This should have existed from the first day and did not, and the cost of
# that was a session where `verify()` reported CLEAN while the eye bezel ran
# through the forehead casing, two cable anchors ran through the ear hubs,
# and every boss in the head pushed 1.5 mm into the part it was holding.
# `verify()` only ever asked one question - is this part inside the skin -
# and answered it correctly. Nobody had asked the other one.
#
# Touching is not a fault. Most of these parts are *supposed* to touch: a
# board sits on its standoffs, a tray sits on its rails, a ring sits in its
# recess. So the number that matters is not "do the surfaces overlap" but
# "how far is one part inside the other", and CONTACT lists the pairs where
# any depth at all is by design.
# ---------------------------------------------------------------------------
CONTACT = {
    ("FIT_pi5_tray", "PROXY_pi5_board"): "board on its standoffs",
    ("FIT_pi5_tray", "tray_rail_R"): "tray sits on the rail",
    ("FIT_pi5_tray", "tray_rail_L"): "tray sits on the rail",
    ("FIT_pca9685_mount", "PROXY_pca9685_board"): "board on its bosses",
    ("FIT_forehead_casing", "PROXY_b0385_board"): "board in its pocket",
    ("FIT_forehead_casing", "PROXY_vl53l1x_board"): "board in its channel",
    ("FIT_forehead_casing", "PROXY_b0385_holder"): "lens holder over the pocket",
    ("PROXY_b0385_board", "PROXY_b0385_holder"): "the camera's own stack",
    ("PROXY_b0385_barrel", "PROXY_b0385_holder"): "the camera's own stack",
    ("PROXY_eyeball_R", "PROXY_iris_R"): "iris window set into the front pole",
    ("PROXY_eyeball_L", "PROXY_iris_L"): "iris window set into the front pole",
    ("ear_hub_R", "PROXY_neopixel_ear_R"): "ring in the hub's recess",
    ("ear_hub_L", "PROXY_neopixel_ear_L"): "ring in the hub's recess",
    ("ear_hub_R", "PROXY_speaker_R_LISTING"): "speaker on the hub's posts",
    ("ear_hub_L", "PROXY_speaker_L_LISTING"): "speaker on the hub's posts",
}
# Parts that were cut FROM the shell or trimmed BY it share surfaces with it
# by construction, and a nearest-surface depth test inside a hollow shell is
# meaningless anyway - it measures the distance to the far wall. Skip the
# shell against anything it shaped.
SHELL = ("HEAD_CYBORG", "HEAD_FACE", "HEAD_CRANIUM")
SHAPED_BY_SHELL = ("ear_hub_R", "ear_hub_L", "tray_rail_R", "tray_rail_L",
                   "HEAD_FACE", "HEAD_CRANIUM")

COLLIDE_TOL = 0.15      # mm; below this it is contact, not interference


def collide(verbose=True):
    import itertools
    from mathutils.bvhtree import BVHTree
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    names = [o.name for o in bpy.data.objects
             if (o.name.startswith(("FIT_", "PROXY_"))
                 or o.name in ("ear_hub_R", "ear_hub_L", "eye_bezel_R",
                               "eye_bezel_L", "tray_rail_R", "tray_rail_L")
                 or o.name in SHELL)
             and not o.name.startswith("CHECK_")]
    data = {}
    for n in names:
        ob = bpy.data.objects[n]
        bm = bmesh.new()
        bm.from_object(ob, dg)
        bm.transform(ob.matrix_world)
        bm.normal_update()
        data[n] = (bm, BVHTree.FromBMesh(bm))

    from mathutils import Vector
    # Three directions, majority vote. One ray is not enough on a 180k shell
    # covered in seam grooves and raked bores: a ray that grazes a crease
    # miscounts its crossings, and a single miscount flips the verdict. With
    # one direction this reported the forehead casing 33.8 mm inside the
    # skull and the eyeball 13 mm inside a bezel it clears by 2.2.
    DIRS = [Vector(v).normalized() for v in ((0.331, 0.537, 0.774),
                                             (-0.71, 0.35, 0.61),
                                             (0.45, -0.83, 0.33))]

    def depth(a, b):
        """furthest a vertex of a sits inside the solid b.

        Inside-ness is ray parity, not the sign of the nearest surface
        normal. The normal test is the obvious one and it is wrong on any
        part that is not convex: asked whether the eyeball is inside the eye
        bezel, it finds the nearest surface is the ring's *bore*, whose
        normal points inward, and reports 21.8 mm of interference through a
        2.2 mm gap. Every part here is a closed solid, so parity is exact.
        """
        bma = data[a][0]
        tb = data[b][1]
        worst = 0.0
        vs = bma.verts[:]
        step = max(1, len(vs) // 1500)
        for i in range(0, len(vs), step):
            p = vs[i].co
            votes = 0
            for D in DIRS:
                hits, t0 = 0, 0.0
                for _ in range(40):
                    loc, nrm, idx, d = tb.ray_cast(p + D * (t0 + 0.03), D)
                    if loc is None:
                        break
                    hits += 1
                    t0 = (loc - p).dot(D)
                votes += hits % 2
            if votes < 2:
                continue
            loc, nrm, idx, d = tb.find_nearest(p, 60.0)
            if d is not None and d > worst:
                worst = d
        return worst

    bad = []
    for a, b in itertools.combinations(sorted(names), 2):
        # a part that was cut from the shell or trimmed by it shares
        # surfaces with it by construction
        if (a in SHELL and b in SHAPED_BY_SHELL) or \
           (b in SHELL and a in SHAPED_BY_SHELL):
            continue
        # the whole head and its own two halves are the same geometry
        if a in SHELL and b in SHELL:
            continue
        if not data[a][1].overlap(data[b][1]):
            continue
        note = CONTACT.get((a, b)) or CONTACT.get((b, a))
        d = max(depth(a, b), depth(b, a))
        if note or d <= COLLIDE_TOL:
            if verbose and note:
                print("  contact  %-24s x %-24s %s" % (a, b, note))
            continue
        bad.append((d, a, b))
    for bm, _ in data.values():
        bm.free()
    bad.sort(reverse=True)
    for d, a, b in bad:
        print("  COLLISION %6.2f mm  %-24s x %s" % (d, a, b))
    print("collision check:", "CLEAN" if not bad
          else "%d INTERFERENCES ABOVE" % len(bad))
    return not bad


if __name__ == "__main__":
    build()
    report()
    verify()
    collide()
