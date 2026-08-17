"""The open-faced bench chassis: the whole robot, assembled face-up on a slab.

    exec(open(r"C:\\Humalien\\cad\\bench.py").read())
    build(); printcheck(); export_stls()

WHY THIS EXISTS
---------------
Pat's call, 17 Aug 2026: build and wire the hardware on an open chassis
where there is room to work, THEN make the head mesh house what actually
exists - not the reverse. That is the same law eye.py already lives by
("chassis first, head second") applied one level up. v1 bolted boards to
the inside of a bowl 106 mm deep and the build stopped there; rack.py then
moved the electronics onto one carryable part, but shaped it to a cranium
interior measured by ray - still the head telling the hardware where to
live. This part is the bench telling the truth first.

ONE FRAME, SHARED
-----------------
Everything here is drawn IN eye.py's world frame: the deck's top face is
z=-64 because that is where eye_base's floor bottom already is. So "where
does the PCA9685 sit relative to the eyes" is not a diagram anyone
maintains - it is the coordinates in this file, and the head rework reads
them directly.

WHAT IT CARRIES
---------------
    eye_base    dropped into a raised-rim bay, +0.3 clearance, held by four
                edge tabs - M2 self-tappers driven horizontally into the
                floor slab's edge faces. No holes in eye_base needed, which
                matters because eye_base is on the printer as this is drawn.
    PCA9685     behind the bay on 4 mm bosses. Holes +-27.94 x +-9.525,
                M2.5 - rack.py's numbers, from the Adafruit .brd.
    Pi 5        beside the PCA on 6 mm bosses, long axis along x so the
                USB/Ethernet stack faces +x (open air) and USB-C/HDMI face
                -y (open air). Holes 58 x 49. The four O3.2 through-holes
                around it take the v1 pi5_tray's side fixings instead, if
                the Pi stays on its tray.
    cables      a channel between bay and boards, y -37..-59, with paired
                O4 zip holes - servo leads west to the PCA, and the power
                module ties down in the same field.

THE ONE CLEARANCE THAT SHAPED IT
--------------------------------
The mechanism OVERHANGS its own floor: at full tilt the pan horn and strap
sweep back and down behind the bay. Rotating every overhanging corner
through +-16 deg puts the farthest reach at y=-57.7 - so both boards start
at y=-59.3 and nothing on the bench is allowed forward of that line taller
than the deck rim. The PCA's header pins, its tallest feature, clear the
swept envelope by 15 mm at the closest pose.

The deck is 160 x 152. It needs a bed that prints 165 square; if that is a
lie about the printer, the fallback is splitting at y=-40 with a lap
joint, and the person splitting it should re-run the gate, not eyeball it.
"""

import bpy
import bmesh
import math
import os
from mathutils import Matrix, Vector

HEAD_MOUNTS = r"C:\Humalien\cad\head_mounts.py"
CHECKS = r"C:\Humalien\cad\checks.py"
COLL = "BENCH"

B = dict(
    # --- the slab ---------------------------------------------------------
    x0=-80.0, x1=80.0,
    y0=-122.0, y1=30.0,
    z_top=-64.0,            # eye_base floor bottom. THE shared number.
    plate_t=4.0,

    # --- the eye bay ------------------------------------------------------
    bay_clr=0.3,            # around the 150 x 60 floor, per side
    rim_w=2.5,
    rim_h=1.5,
    tab_w=10.0, tab_t=3.0, tab_h=6.5,   # edge tabs; screw at mid-floor
    tab_x=55.0,

    # --- boards -----------------------------------------------------------
    pca_cx=-45.0, pca_cy=-72.0,         # board 62.2 x 25.4, y -84.7..-59.3
    pca_hx=27.94, pca_hy=9.525,         # rack.py / Adafruit .brd
    pca_boss_d=7.0, pca_boss_h=4.0,
    pi_cx=32.0, pi_cy=-87.5,            # board 85 x 56, y -115.5..-59.5
    pi_hx=29.0, pi_hy=24.5,             # 58 x 49, Pi 5
    pi_boss_d=8.0, pi_boss_h=6.0,
    tray_hx=30.0, tray_hy=27.0,         # v1 pi5_tray side fixings, O3.2
    tray_hole=3.2,
    pilot_d=2.2,            # M2.5 self-tap in PLA
    pilot_deep=7.5,
    m2_pilot=2.2,           # M2 clearance-ish pilot through the edge tabs

    # --- cable channel ----------------------------------------------------
    zip_d=4.0,
    zip_y=(-44.0, -54.0),   # a pair per station = one strap
    zip_xs=(-68.0, -48.0, -28.0, 0.0, 28.0, 48.0, 68.0),
)


def _hm():
    ns = {"__name__": "head_mounts", "__file__": HEAD_MOUNTS}
    with open(HEAD_MOUNTS, "r", encoding="utf-8") as fh:
        exec(compile(fh.read(), HEAD_MOUNTS, "exec"), ns)
    return ns


def _prims():
    out = []

    def add():
        out.append(bmesh.new())
        return out[-1]
    return out, add


def _union(hm, coll, name, prims):
    base = hm["_link"](coll, name, hm["_mesh"](name, prims[0]))
    for i, bm in enumerate(prims[1:]):
        ob = hm["_link"](coll, "_U%d_%s" % (i, name),
                         hm["_mesh"]("_U%d" % i, bm))
        hm["boolean"](base, ob, 'UNION')
        bpy.data.objects.remove(ob, do_unlink=True)
    return base


def _cut_each(hm, coll, ob, prims, name):
    for i, bm in enumerate(prims):
        hm["_apply"](coll, ob, bm, "%s_%d" % (name, i), 'DIFFERENCE')
    return ob


def deck(hm, coll):
    """The one printed part. Everything grows UP from a flat 4 mm plate and
    every riser overlaps 1 mm INTO it - a riser standing tangent on the
    plate's top face is a butt joint, and a butt is three shells."""
    zt = B["z_top"]
    zb = zt - B["plate_t"]
    prims, add = _prims()
    bm = add()
    hm["_box"](bm, (B["x1"] - B["x0"], B["y1"] - B["y0"], B["plate_t"]),
               ((B["x0"] + B["x1"]) / 2.0, (B["y0"] + B["y1"]) / 2.0,
                (zb + zt) / 2.0))

    # bay rim: four bars overlapping at the corners, tops coplanar - the
    # proven box-lap union, not a butt
    bx = 75.0 + B["bay_clr"]            # bay inner half-width
    by0, by1 = -34.0 - B["bay_clr"], 26.0 + B["bay_clr"]
    rw, rh = B["rim_w"], B["rim_h"]
    for (dx, dy, w, h) in (
            (0.0, by1 + rw / 2.0, 2.0 * (bx + rw), rw),      # front
            (0.0, by0 - rw / 2.0, 2.0 * (bx + rw), rw),      # back
            (bx + rw / 2.0, (by0 + by1) / 2.0, rw, by1 - by0 + 2.0 * rw),
            (-bx - rw / 2.0, (by0 + by1) / 2.0, rw, by1 - by0 + 2.0 * rw)):
        bm = add()
        hm["_box"](bm, (w, h, rh + 1.0), (dx, dy, zt + (rh - 1.0) / 2.0))

    # edge tabs, front and back pair - they straddle the rim where they
    # stand, which is a lap, and their screws bite the floor's edge faces
    for sy, yc in ((1, by1 + B["tab_t"] / 2.0), (-1, by0 - B["tab_t"] / 2.0)):
        for sx in (1, -1):
            bm = add()
            hm["_box"](bm, (B["tab_w"], B["tab_t"], B["tab_h"] + 1.0),
                       (sx * B["tab_x"], yc, zt + (B["tab_h"] - 1.0) / 2.0))

    # board bosses
    for sx in (1, -1):
        for sy in (1, -1):
            bm = add()
            hm["_cyl"](bm, B["pca_boss_d"], B["pca_boss_h"] + 1.0,
                       (B["pca_cx"] + sx * B["pca_hx"],
                        B["pca_cy"] + sy * B["pca_hy"],
                        zt + (B["pca_boss_h"] - 1.0) / 2.0), 'Z', segs=24)
            bm = add()
            hm["_cyl"](bm, B["pi_boss_d"], B["pi_boss_h"] + 1.0,
                       (B["pi_cx"] + sx * B["pi_hx"],
                        B["pi_cy"] + sy * B["pi_hy"],
                        zt + (B["pi_boss_h"] - 1.0) / 2.0), 'Z', segs=24)
    ob = _union(hm, coll, "bench_deck", prims)

    cuts, cadd = _prims()
    # lightening windows - under the bay the floor covers them, elsewhere
    # they stay clear of every boss by 4+
    for wx, wy, ww, wh in ((-45.0, -4.0, 36.0, 40.0),
                           (0.0, -4.0, 36.0, 40.0),
                           (45.0, -4.0, 36.0, 40.0),
                           (B["pi_cx"], B["pi_cy"], 40.0, 30.0),
                           (B["pca_cx"], B["pca_cy"], 36.0, 10.0)):
        bm = cadd()
        hm["_box"](bm, (ww, wh, B["plate_t"] * 3.0), (wx, wy, zt - 2.0))
    # pilots down the bosses, 1.5 into the plate for full bite
    for sx in (1, -1):
        for sy in (1, -1):
            for cx, cy in ((B["pca_cx"] + sx * B["pca_hx"],
                            B["pca_cy"] + sy * B["pca_hy"]),
                           (B["pi_cx"] + sx * B["pi_hx"],
                            B["pi_cy"] + sy * B["pi_hy"])):
                bm = cadd()
                hm["_cyl"](bm, B["pilot_d"], B["pilot_deep"],
                           (cx, cy, zt + B["pi_boss_h"]
                            - B["pilot_deep"] / 2.0 + 0.01), 'Z', segs=16)
            bm = cadd()     # v1 tray side fixings, straight through
            hm["_cyl"](bm, B["tray_hole"], B["plate_t"] * 3.0,
                       (B["pi_cx"] + sx * B["tray_hx"],
                        B["pi_cy"] + sy * B["tray_hy"], zt - 2.0), 'Z',
                       segs=20)
    # tab screw pilots, horizontal, at mid-floor height z=-61
    for yc in (by1 + B["tab_t"] / 2.0, by0 - B["tab_t"] / 2.0):
        for sx in (1, -1):
            bm = cadd()
            hm["_cyl"](bm, B["m2_pilot"], B["tab_t"] * 4.0,
                       (sx * B["tab_x"], yc, -61.0), 'Y', segs=16)
    # zip pairs down the cable channel
    for x in B["zip_xs"]:
        for y in B["zip_y"]:
            bm = cadd()
            hm["_cyl"](bm, B["zip_d"], B["plate_t"] * 3.0,
                       (x, y, zt - 2.0), 'Z', segs=16)
    _cut_each(hm, coll, ob, cuts, "_CUT_deck")
    return ob


def proxies(hm, coll):
    """The boards as colored slabs, so placement is something you LOOK at.
    Not printed, not gated - the same convention as eye.py's servos."""
    zt = B["z_top"]
    out = []

    prims, add = _prims()               # Pi 5: board + the USB/Eth stack
    zb = zt + B["pi_boss_h"]
    bm = add()
    hm["_box"](bm, (85.0, 56.0, 1.6), (B["pi_cx"], B["pi_cy"], zb + 0.8))
    bm = add()
    hm["_box"](bm, (18.0, 48.0, 14.0),
               (B["pi_cx"] + 37.0, B["pi_cy"], zb + 1.6 + 7.0))
    ob = _union(hm, coll, "PROXY_pi5", prims)
    ob.color = (0.15, 0.55, 0.2, 1.0)
    out.append(ob)

    prims, add = _prims()               # PCA9685: board + servo header comb
    zb = zt + B["pca_boss_h"]
    bm = add()
    hm["_box"](bm, (62.2, 25.4, 1.6), (B["pca_cx"], B["pca_cy"], zb + 0.8))
    bm = add()
    hm["_box"](bm, (56.0, 10.0, 9.0),
               (B["pca_cx"], B["pca_cy"] + 5.0, zb + 1.6 + 4.5))
    ob = _union(hm, coll, "PROXY_pca9685", prims)
    ob.color = (0.15, 0.3, 0.7, 1.0)
    out.append(ob)
    return out


def build(save=False):
    hm = _hm()
    old = bpy.data.collections.get(COLL)
    if old:
        for o in list(old.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(old)
    coll = bpy.data.collections.new(COLL)
    bpy.context.scene.collection.children.link(coll)
    print("bench:")
    ob = deck(hm, coll)
    print("  %-14s %d verts" % (ob.name, len(ob.data.vertices)))
    proxies(hm, coll)
    if save:
        bpy.ops.wm.save_mainfile()
    return coll


def _checks():
    ns = {"__name__": "checks", "__file__": CHECKS}
    with open(CHECKS, "r", encoding="utf-8") as fh:
        exec(compile(fh.read(), CHECKS, "exec"), ns)
    return ns


PLATE = [
    ("bench_deck", "FLAT", False),
]


def printcheck():
    ns = _checks()
    return ns["gate"]([(n, ns[o], s) for n, o, s in PLATE])


def health():
    ok = True
    for o in bpy.data.collections[COLL].objects:
        if o.type != 'MESH':
            continue
        bm = bmesh.new()
        bm.from_mesh(o.data)
        openf = sum(1 for e in bm.edges if len(e.link_faces) < 2)
        nonm = sum(1 for e in bm.edges if len(e.link_faces) > 2)
        seen, shells = set(), 0
        for f in bm.faces:
            if f in seen:
                continue
            shells += 1
            stack = [f]
            while stack:
                g = stack.pop()
                if g in seen:
                    continue
                seen.add(g)
                for e in g.edges:
                    for h in e.link_faces:
                        if h not in seen:
                            stack.append(h)
        bm.free()
        bad = openf or nonm or shells != 1
        print("  %-14s open %d  non-manifold %d  shells %d   %s"
              % (o.name, openf, nonm, shells, "FAIL" if bad else "ok"))
        ok = ok and not bad
    print("HEALTH:", "PASS" if ok else "FAIL")
    return ok


def export_stls(dirpath=r"C:\Humalien\exports\bench"):
    ns = _checks()
    os.makedirs(dirpath, exist_ok=True)
    out = []
    for name, okey, _sup in PLATE:
        src = bpy.data.objects[name]
        me = src.data.copy()
        me.transform(ns[okey] @ Matrix.Translation(src.location))
        zmin = min(v.co.z for v in me.vertices)
        me.transform(Matrix.Translation((0.0, 0.0, -zmin)))
        tmp = bpy.data.objects.new("_EXPORT_" + name, me)
        bpy.context.scene.collection.objects.link(tmp)
        for o in bpy.context.selected_objects:
            o.select_set(False)
        tmp.select_set(True)
        bpy.context.view_layer.objects.active = tmp
        path = os.path.join(dirpath, name.lower() + "_x1.stl")
        bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True)
        bpy.data.objects.remove(tmp, do_unlink=True)
        bpy.data.meshes.remove(me)
        print("  wrote", path)
        out.append(path)
    return out
