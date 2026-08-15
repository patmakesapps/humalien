"""Humalien eye mechanism - parametric model.

Run inside Blender:

    exec(open(r"C:\\humalien\\humalien\\cad\\eye_mech.py").read())

Everything is driven by ``P`` and ``BOARDS`` below. Nothing downstream hard-codes
a dimension; change a number there, re-run, and the STLs regenerate.

Units: 1 Blender unit = 1 mm. The scene is set to millimetres on build.

Axes, as seen from behind Humalien looking the way it looks:
    +X  Humalien's right      (so the VL53L1X left eye lives at -X)
    +Y  forward, the gaze direction
    +Z  up

Confidence levels are carried in the data, not in comments, so a part can be
built differently depending on how much its source is trusted. See CONF.
"""

import bpy
import bmesh
import math
import os
from mathutils import Matrix

# ---------------------------------------------------------------------------
# Source confidence. The brief's step two: unverified dimensions get slop.
# ---------------------------------------------------------------------------
# "exact"    - read out of the manufacturer's own CAD/board file
# "proven"   - measured off a holder that already works with the real part
# "drawing"  - read off the manufacturer's mechanical drawing
# "listing"  - only ever found in a shop listing or a forum. Gets lowconf_pad.
CONF_PAD = {"exact": 0.0, "proven": 0.0, "drawing": 0.0, "listing": 1.0}

P = dict(
    # ---------------- print / tolerance policy ----------------
    plate_t         = 3.0,    # general structural plate thickness
    coupon_t        = 2.4,    # 12 layers at 0.2 - stiff enough to offer a board up
    wall            = 2.0,
    board_clear     = 0.5,    # per side, brief step two
    slot_travel     = 1.0,    # total slot travel, i.e. +/-0.5
    m2_free         = 2.2,    # M2 clearance hole
    m3_free         = 3.4,    # M3 clearance hole
    engrave_depth   = 0.6,
    scribe_w        = 0.5,    # width of a zero-clearance nominal scribe line
    scribe_depth    = 0.4,

    # ---------------- eyeball ----------------
    # Cogley's eyeball part measured Ø32.00 in the reference 3mf (Component74).
    eyeball_dia     = 32.0,
    eye_pitch       = 62.0,   # interpupillary, PROVISIONAL - set by the skull

    # ---------------- travel limits ----------------
    # Also enforced in software; the model carries them so nothing can be
    # commanded into a crash. Hard stops get cut once linkage geometry exists.
    pan_limit_deg   = 30.0,
    tilt_limit_deg  = 20.0,

    # ---------------- MG90S ----------------
    # Body from the TowerPro-branded drawing; pocket from Cogley's proven fit.
    servo_body_l    = 22.5,
    servo_body_w    = 12.0,
    servo_body_h    = 22.7,
    servo_total_h   = 35.5,
    servo_tab_span  = 32.5,   # tab tip to tip, from the drawing
    servo_tab_pitch = 28.0,   # hole centres - NOT dimensioned anywhere. Measured
                              # by coupon_mg90s. Treat as listing-grade.
    servo_pocket_l  = 24.03,  # measured off Cogley ε3.2 part CA (MG90S variant)
    servo_pocket_w  = 12.80,
    servo_spline_d  = 4.82,   # Cogley's gauge offers 4.72 and 4.92; midpoint
)

# ---------------------------------------------------------------------------
# Boards. Every number here has a URL against it in docs/eye-design-brief.md.
# ---------------------------------------------------------------------------
BOARDS = dict(
    pca9685 = dict(
        label   = "PCA9685",
        conf    = "exact",          # Adafruit's own Eagle .brd
        w       = 62.230,
        d       = 25.400,
        t       = 1.60,
        corner_r= 3.175,
        hole_d  = 2.50,
        hx      = 55.880,           # mounting hole pitch, X
        hy      = 19.050,           # mounting hole pitch, Y
        under   = 3.5,              # clearance needed under the board for pin tails
    ),
    b0385 = dict(
        label   = "B0385",
        conf    = "drawing",        # Arducam datasheet, overall dimension diagram
        w       = 38.0,
        d       = 38.0,
        t       = 1.60,
        corner_r= 2.0,
        hole_d_outer = 2.60,        # R=1.30 on the drawing
        pitch_outer  = 34.0,
        hole_d_inner = 2.80,        # R=1.40 on the drawing
        pitch_inner  = 28.0,
        lens_holder  = 18.0,        # square M12 holder footprint, scaled off the drawing
        lens_holder_h= 7.0,         # "Lens Holder Height 7mm"
        lens_barrel_d= 14.0,        # Ø14 +/-0.05
        lens_len     = 13.2,
        conn_w       = 7.56,        # S4B-ZR 4-pin, from the drawing
        conn_d       = 3.81,
        conn_x       = 8.24,        # from the left edge
        conn_y       = 3.47,        # from the bottom edge
        under        = 3.0,
    ),
    vl53l1x = dict(
        label   = "VL53L1X",
        # Was `listing` and the weakest row in the design: CQRobot's wiki and
        # product page are both 404 and the surviving listings disagreed,
        # 28.5x23 against 26x23. Settled by measuring a CQRobot holder already
        # in service on two robots - LumaBot V2, 04_distance_sensor_mount.
        # Its retention slot is 23.600 x 29.100 x 2.100. At the +0.6 fit that
        # mount uses on both axes that is a 23.0 x 28.5 x 1.6 board, which is
        # two round numbers landing on one of the two competing listings. The
        # 26 mm listings are wrong.
        conf    = "proven",
        w       = 28.5,
        d       = 23.0,
        t       = 1.60,
        corner_r= 1.5,
        hole_d  = 3.00,
        # Hole POSITIONS remain unknown - and no longer matter. The proven
        # holder does not use them: it retains the board in a slot, no screws.
        # That is the better answer inside an eyeball anyway, where every gram
        # sits on a lever arm the servo has to accelerate.
        # All five measured off the holder, and all five used directly. Do NOT
        # re-derive any of them from board nominals: slot_t came out 2.100
        # where 1.6 + 0.2 of "clearance" would have said 1.800, and that 0.3 is
        # the difference between a board that slides in and one that does not.
        slot_w  = 23.600,           # measured, groove face to groove face
        slot_h  = 29.100,           # measured, groove z span
        slot_t  = 2.100,            # measured, PCB groove thickness
        slot_open = 21.600,         # measured, opening between the case walls
        slot_lip  = 1.000,          # measured, groove depth per side
        # The 6-way JST sits on the SAME face as the sensor and stands proud of
        # it, wires and all. That is the actual reason the proven holder leaves
        # its whole front open - not modesty about the field of view. Anything
        # covering the board fouls the connector before it ever reaches the
        # sensor. Height is UNMEASURED: no calipers, and it is not in any
        # drawing. 9.0 is a deliberate over-estimate for a vertical JST plus a
        # gentle wire bend, and it is a keep-out the face shell must respect.
        conn_keepout = 9.0,
    ),
    pi5 = dict(
        label   = "Raspberry Pi 5",
        conf    = "exact",          # Raspberry Pi's own mechanical drawing
        w       = 85.0,
        d       = 56.0,
        t       = 1.6,
        hole_d  = 2.7,              # board hole; takes M2.5
        hx      = 58.0,
        hy      = 49.0,
        hole_inset = 3.5,           # from the two datum edges
        # The pattern is NOT centred on the board. Holes sit 3.5 mm in from one
        # long and one short edge, so their centre is 10.0 mm off the board
        # centre along the length. Getting this wrong puts every hole out by
        # 10 mm and it is invisible until the board will not drop on.
        under   = 3.0,              # clearance under the board for solder tails
    ),
    speaker = dict(
        label   = "8 ohm 5 W module",
        # UNMEASURED. Enclosed plastic modules, already in hand, with a
        # mounting flange and a screw hole at each end - visible in the photo -
        # so they bolt down rather than needing a clamp or a printed baffle.
        # Numbers below are placeholders and nothing is built to them yet.
        conf    = "listing",
        w       = 70.0,
        d       = 30.0,
        t       = 16.0,
        flange_holes = 2,
    ),
    neopixel12 = dict(
        label   = "NeoPixel Ring 12",
        conf    = "exact",          # Adafruit's own Eagle .brd, as with the PCA9685
        od      = 36.830,           # layer 20 outer arc, r=18.415
        id      = 23.368,           # layer 20 inner circle, r=11.684
        led_pcd = 29.464,           # 12 LEDs on r=14.732, 30 deg apart, first at 12 o'clock
        n_led   = 12,
        t       = 6.7,              # product page envelope incl. components - not from the .brd
        # There are NO mounting holes in the board file. It has to be trapped by
        # a lip or a bezel; there is nothing to screw to.
    ),
)

EXPORT_DIR = r"C:\humalien\humalien\exports"
COLL_NAME = "HUMALIEN"

# Quantities for the printed set. Kept next to the builders so it cannot drift.
QUANTITIES = {
    "coupon_pca9685": 1,
    "coupon_b0385": 1,
    "coupon_vl53l1x": 1,
    "coupon_mg90s": 1,
    "coupon_neopixel12": 1,
    "forehead_casing": 1,
    "pi5_tray": 1,
    "pca9685_mount": 1,
    "cable_anchor": 6,
}


# ===========================================================================
# geometry helpers
# ===========================================================================

def _coll():
    c = bpy.data.collections.get(COLL_NAME)
    if c is None:
        c = bpy.data.collections.new(COLL_NAME)
        bpy.context.scene.collection.children.link(c)
    return c


def _finish(name, bm, loc, rotz):
    bm.faces.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if rotz:
        bmesh.ops.rotate(bm, verts=bm.verts[:],
                         matrix=Matrix.Rotation(math.radians(rotz), 3, 'Z'))
    if loc != (0, 0, 0):
        bmesh.ops.translate(bm, vec=loc, verts=bm.verts[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    _coll().objects.link(ob)
    return ob


def prism(name, pts, h, loc=(0, 0, 0), rotz=0.0):
    """Extrude a closed 2D polygon into a solid, centred on z=0."""
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, -h / 2.0)) for (x, y) in pts]
    top = [bm.verts.new((x, y, h / 2.0)) for (x, y) in pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bm.faces.new(bot[::-1])
    bm.faces.new(top)
    return _finish(name, bm, loc, rotz)


def rrect_pts(w, d, r=0.0, segs=8):
    """Rounded-rectangle outline, counter-clockwise."""
    r = max(0.0, min(r, w / 2.0 - 1e-6, d / 2.0 - 1e-6))
    if r <= 1e-6:
        return [(w / 2, d / 2), (-w / 2, d / 2), (-w / 2, -d / 2), (w / 2, -d / 2)]
    cx, cy = w / 2 - r, d / 2 - r
    pts = []
    for (ox, oy, a0) in ((cx, cy, 0.0), (-cx, cy, 90.0),
                         (-cx, -cy, 180.0), (cx, -cy, 270.0)):
        for i in range(segs + 1):
            a = math.radians(a0 + 90.0 * i / segs)
            pts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    return pts


def circle_pts(d, segs=48):
    r = d / 2.0
    return [(r * math.cos(2 * math.pi * i / segs),
             r * math.sin(2 * math.pi * i / segs)) for i in range(segs)]


def stadium_pts(d, travel, segs=16):
    """Slot outline: a circle of diameter d swept through `travel`."""
    r = d / 2.0
    s = max(0.0, travel) / 2.0
    if s < 1e-6:
        return circle_pts(d, segs * 2)
    pts = []
    for i in range(segs + 1):
        a = math.radians(-90.0 + 180.0 * i / segs)
        pts.append((s + r * math.cos(a), r * math.sin(a)))
    for i in range(segs + 1):
        a = math.radians(90.0 + 180.0 * i / segs)
        pts.append((-s + r * math.cos(a), r * math.sin(a)))
    return pts


def plate(name, w, d, t, r=0.0, loc=(0, 0, 0)):
    return prism(name, rrect_pts(w, d, r), t, loc)


def cyl(name, d, h, loc=(0, 0, 0), segs=48):
    return prism(name, circle_pts(d, segs), h, loc)


def slot(name, d, travel, h, loc=(0, 0, 0), rotz=0.0):
    return prism(name, stadium_pts(d, travel), h, loc, rotz)


def _apply_mods(ob):
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def _clean(ob, dist=1e-5):
    """Merge coincident verts left by booleans and fix winding.

    Note: Blender's EXACT solver emits a few zero-area sliver edges wherever a
    font glyph is cut into a face. Verified as inherent to the solver - it is
    unaffected by font choice, by triangulating either input, by union vs
    difference, and by whether this cleanup runs at all. The slivers carry no
    volume and every slicer drops them, so engraved labels are kept. Only the
    engraved faces are affected; the solid itself is manifold."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=dist)
    bm.faces.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


def boolean(target, cutters, op='DIFFERENCE'):
    if not isinstance(cutters, (list, tuple)):
        cutters = [cutters]
    cutters = [c for c in cutters if c is not None]
    for c in cutters:
        m = target.modifiers.new("bool", 'BOOLEAN')
        m.operation = op
        m.solver = 'EXACT'
        m.object = c
    _apply_mods(target)
    for c in cutters:
        bpy.data.objects.remove(c, do_unlink=True)
    return _clean(target)


def cut(target, cutters):
    return boolean(target, cutters, 'DIFFERENCE')


def fuse(target, others):
    return boolean(target, others, 'UNION')


def text_solid(name, body, size, h, loc=(0, 0, 0), rotz=0.0):
    """Extruded text, converted to mesh, for engraving."""
    cu = bpy.data.curves.new(name, type='FONT')
    cu.body = body
    cu.size = size
    cu.extrude = h / 2.0
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    ob = bpy.data.objects.new(name, cu)
    _coll().objects.link(ob)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.convert(target='MESH')
    ob = bpy.context.view_layer.objects.active
    ob.rotation_euler = (0, 0, math.radians(rotz))
    ob.location = loc
    bpy.context.view_layer.update()
    _apply_mods(ob)
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)
    return _clean(ob)


def engrave(target, body, size, top_z, loc_xy, rotz=0.0):
    """Sink text `engrave_depth` into a face whose top sits at top_z."""
    dep = P["engrave_depth"]
    # solid is dep*2 thick and centred on the face, so it sinks exactly dep
    t = text_solid("_txt", body, size, dep * 2.0,
                   (loc_xy[0], loc_xy[1], top_z), rotz)
    return cut(target, [t])


def scribe_rect(target, w, d, r, top_z, center=(0, 0), depth=None, width=None):
    """Cut a thin witness groove at the board's TRUE nominal outline. The pocket
    beside it is deliberately oversize, so without this there is nothing on the
    coupon showing where nominal actually falls.

    Built as one ring solid rather than four overlapping bars - overlapping bars
    leave slivers at the corners and the result is not manifold."""
    depth = P["scribe_depth"] if depth is None else depth
    width = P["scribe_w"] if width is None else width
    cx, cy = center
    outer = prism("_so", rrect_pts(w + width, d + width, max(0.0, r + width / 2)),
                  depth * 2.0, (cx, cy, top_z))
    inner = prism("_si", rrect_pts(w - width, d - width, max(0.0, r - width / 2)),
                  depth * 6.0, (cx, cy, top_z))
    ring = boolean(outer, [inner], 'DIFFERENCE')
    return cut(target, [ring])


def pad_for(board):
    """Extra slop a listing-grade dimension earns, per the brief."""
    return CONF_PAD[board["conf"]]


def pocket_size(board, key_w="w", key_d="d"):
    """Board pocket: nominal + board_clear per side + confidence pad per side."""
    extra = 2.0 * (P["board_clear"] + pad_for(board))
    return board[key_w] + extra, board[key_d] + extra


# ===========================================================================
# fit coupons - these get printed BEFORE anything that mounts a real board
# ===========================================================================

def coupon_pca9685(loc=(0, 0, 0)):
    b = BOARDS["pca9685"]
    t = P["coupon_t"]
    pw, pd = pocket_size(b)
    # margin sized so the labels sit entirely on the rim. Text cut across a
    # pocket wall lands half on the floor and half on the rim, and reads badly.
    W, D = b["w"] + 14, b["d"] + 14
    ob = plate("coupon_pca9685", W, D, t, 3.0, (0, 0, t / 2))
    top = t
    cuts = []
    # the pocket the real part will use
    cuts.append(prism("_p", rrect_pts(pw, pd, b["corner_r"] + P["board_clear"]),
                      2.0, (0, 0, top)))
    # true-position holes, ROUND and nominal: this coupon is the measurement
    for sx in (-1, 1):
        for sy in (-1, 1):
            cuts.append(cyl("_h", b["hole_d"], t * 3,
                            (sx * b["hx"] / 2, sy * b["hy"] / 2, t / 2)))
    ob = cut(ob, cuts)
    ob = scribe_rect(ob, b["w"], b["d"], b["corner_r"], top)
    ob = engrave(ob, "PCA9685", 3.4, top, (0, -D / 2 + 4.0))
    ob = engrave(ob, "62.23x25.40  h2.5 @ 55.88x19.05", 2.4, top, (0, D / 2 - 3.6))
    return ob


def coupon_b0385(loc=(0, 0, 0)):
    b = BOARDS["b0385"]
    t = P["coupon_t"]
    pw, pd = pocket_size(b)
    W, D = b["w"] + 14, b["d"] + 14
    ob = plate("coupon_b0385", W, D, t, 3.0, (0, 0, t / 2))
    top = t
    cuts = [prism("_p", rrect_pts(pw, pd, b["corner_r"] + P["board_clear"]),
                  2.0, (0, 0, top))]
    for sx in (-1, 1):
        for sy in (-1, 1):
            cuts.append(cyl("_ho", b["hole_d_outer"], t * 3,
                            (sx * b["pitch_outer"] / 2, sy * b["pitch_outer"] / 2, t / 2)))
            cuts.append(cyl("_hi", b["hole_d_inner"], t * 3,
                            (sx * b["pitch_inner"] / 2, sy * b["pitch_inner"] / 2, t / 2)))
    # aperture for the M12 lens holder
    ap = b["lens_holder"] + 2 * P["board_clear"]
    cuts.append(prism("_ap", rrect_pts(ap, ap, 2.0), t * 3, (0, 0, t / 2)))
    ob = cut(ob, cuts)
    ob = scribe_rect(ob, b["w"], b["d"], b["corner_r"], top)
    ob = engrave(ob, "B0385", 3.4, top, (0, -D / 2 + 4.0))
    ob = engrave(ob, "34.0 outer  28.0 inner", 2.4, top, (0, D / 2 - 3.6))
    return ob


def coupon_vl53l1x(loc=(0, 0, 0)):
    """Slot-fit coupon for the VL53L1X.

    The board size is no longer in question - see BOARDS. What is still open is
    whether the *proven* 2.100 mm groove reproduces on this printer in this
    material, because a groove that small is exactly where over-extrusion and
    elephant's foot show up. So this carries three: the proven 2.100, one
    tighter, one looser.

    Retention is a slot rather than screws, copying the holder that works. That
    is also the right call for an eyeball - no fasteners, no boss, and nothing
    on the lever arm the servo has to accelerate."""
    b = BOARDS["vl53l1x"]
    trials = [("A", b["slot_t"] - 0.15), ("B", b["slot_t"]), ("C", b["slot_t"] + 0.15)]
    depth = 12.0
    t = depth + 3.0            # 3 mm of floor under the slot
    D = 16.0
    cell = b["slot_w"] + 8.0
    W = cell * len(trials) + 6.0
    ob = plate("coupon_vl53l1x", W, D, t, 3.0, (0, 0, t / 2))
    top = t
    slot_y = 3.5               # slot sits back, leaving the front of the face for labels
    cuts = []
    xs = []
    for i, (letter, th) in enumerate(trials):
        x = -W / 2 + 3.0 + cell * (i + 0.5)
        xs.append((x, letter, th))
        cuts.append(prism("_sl", rrect_pts(b["slot_w"], th, 0.4),
                          depth * 2.0, (x, slot_y, top)))
    ob = cut(ob, cuts)
    for (x, letter, th) in xs:
        ob = engrave(ob, letter, 5.0, top, (x, -4.6))
        ob = engrave(ob, "%.2f" % th, 2.4, top, (x, -0.6))
    ob = engrave(ob, "VL53L1X 23.0x28.5x1.6  slot %.1f wide" % b["slot_w"],
                 2.4, top, (0, D / 2 - 2.2))
    return ob


def coupon_mg90s(loc=(0, 0, 0)):
    """Cogley's idea, rebuilt for our numbers: four trial pockets bracketing
    both the TowerPro nominal body and Cogley's proven ε3.2 pocket. Print it,
    find the one that grips without forcing, and use that clearance."""
    t = 6.0                      # deep enough for the body to actually enter
    trials = [("A", 0.20), ("B", 0.45), ("C", 0.70), ("D", 0.95)]  # per side
    bl, bw = P["servo_body_l"], P["servo_body_w"]
    cell = bl + 2 * 0.95 + 7.0
    W = cell * len(trials) + 6
    D = bw + 20
    ob = plate("coupon_mg90s", W, D, t, 3.0, (0, 0, t / 2))
    top = t
    cuts = []
    xs = []
    for i, (letter, cl) in enumerate(trials):
        x = -W / 2 + 3 + cell * (i + 0.5)
        xs.append((x, letter, cl))
        cuts.append(prism("_sp", rrect_pts(bl + 2 * cl, bw + 2 * cl, 1.0),
                          t * 3, (x, 2.0, t / 2)))
    # pocket C additionally gets true-position tab holes, so a servo can be
    # screwed down and the 28.0 pitch confirmed or corrected.
    xc = xs[2][0]
    for sx in (-1, 1):
        cuts.append(cyl("_tab", P["m2_free"], t * 3,
                        (xc + sx * P["servo_tab_pitch"] / 2, 2.0, t / 2)))
    ob = cut(ob, cuts)
    for (x, letter, cl) in xs:
        ob = engrave(ob, letter, 4.5, top, (x, -D / 2 + 4.0))
        ob = engrave(ob, "+%.2f" % cl, 2.4, top, (x, -D / 2 + 8.6))
    ob = engrave(ob, "MG90S  tab pitch %.1f on C" % P["servo_tab_pitch"],
                 2.8, top, (0, D / 2 - 3.6))
    return ob


def coupon_neopixel12(loc=(0, 0, 0)):
    """Fit coupon for the NeoPixel ring that lights the iris.

    The ring is static in the socket, not carried by the eyeball - see the
    brief. So what this has to prove is that the ring seats in its pocket and
    that the retaining lip actually holds it, because the board file shows no
    mounting holes at all and there is nothing to screw to.

    The lip is the part worth testing: it overhangs the pocket, so it is a
    bridge, and a bridge that droops is a ring that will not seat flat."""
    b = BOARDS["neopixel12"]
    t = P["coupon_t"] + 2.0
    pw = b["od"] + 2 * P["board_clear"]
    W = b["od"] + 14
    ob = plate("coupon_neopixel12", W, W, t, 3.0, (0, 0, t / 2))
    top = t
    pocket_d = 2.2                       # ring PCB plus a little
    lip = 1.5
    cuts = [
        # pocket the ring drops into
        prism("_p", circle_pts(pw, 96), pocket_d * 2.0, (0, 0, top)),
        # window through the middle: lets the ring be pushed back out, and is
        # what the eyeball will look through on the real part
        prism("_w", circle_pts(b["id"] - 2 * lip, 96), t * 3, (0, 0, t / 2)),
    ]
    ob = cut(ob, cuts)
    ob = scribe_rect(ob, b["od"], b["od"], b["od"] / 2, top)
    ob = scribe_rect(ob, b["id"], b["id"], b["id"] / 2, top)
    ob = engrave(ob, "NEO12", 3.4, top, (0, -W / 2 + 4.4))
    ob = engrave(ob, "OD%.2f ID%.2f" % (b["od"], b["id"]), 2.4, top, (0, W / 2 - 4.0))
    return ob


# ===========================================================================
# structural parts - independent of what the reference build will answer
# ===========================================================================

def forehead_casing(loc=(0, 0, 0)):
    """Camera and distance sensor on one plate, side by side in a row.

    Both apertures sit on a single horizontal centreline. That is free
    alignment rather than careful assembly: the B0385's sensor is dead centre
    on its board - 19.00 mm from two adjacent edges on Arducam's drawing - so
    lining the pocket centres up lines the optical axes up.

    Replaces the earlier separate camera_boss and tof_mount. One part, one
    fastener set, and the two cannot drift out of line relative to each other
    because there is no joint between them to drift.

    The camera is trapped by screws through slotted holes. The VL53L1X drops
    down a channel onto a shelf and gravity holds it, so it needs no fastener
    at all. Neither needs support to print."""
    cam = BOARDS["b0385"]
    tof = BOARDS["vl53l1x"]
    t = 5.0
    cam_pw, cam_pd = pocket_size(cam)
    cam_depth = cam["t"] + 0.2
    # Both taken straight off the proven holder rather than derived. See BOARDS.
    cav_d = tof["slot_t"]             # 2.100, not 1.6 + a guess
    lip = tof["slot_lip"]             # 1.000, so the opening lands on 21.600
    lip_t = 1.0                       # material behind the board trapping it

    row_y = 3.5                       # the shared centreline both apertures sit on
    cam_x = -22.0
    tof_x = 32.0
    W = 96.0
    D = 58.0
    ob = plate("forehead_casing", W, D, t, 3.0, (0, 0, t / 2))
    top = t
    cuts = []

    # ---- camera ----
    cuts.append(prism("_cp", rrect_pts(cam_pw, cam_pd, cam["corner_r"] + P["board_clear"]),
                      cam_depth * 2.0, (cam_x, row_y, top)))
    # Corner reliefs, and they are not optional. The pocket is rounded to
    # `corner_r + board_clear` = 2.5 mm because Arducam's drawing gives the
    # board a 2.0 mm corner radius. The board in hand has SQUARE corners.
    # Measured: the pocket reaches a diagonal 18.77 mm from centre, a 38 mm
    # square board's corner is at 19.00, so it stood 0.23 mm proud at all
    # four corners and would not seat - only two screws went in, 15 Aug.
    #
    # A relief rather than `corner_r = 0`, because setting the radius to zero
    # asserts the drawing is wrong in one specific way AND puts a sharp
    # internal corner in the print, which a 0.4 mm nozzle cannot cut - so the
    # fit would be decided by whatever radius the slicer happens to leave.
    # A Ø3 bore at each corner swallows a square corner with 0.79 mm to spare
    # and changes nothing if the board turns out to be radiused after all.
    # The straight walls survive from -18 to +18, so the board is still
    # located on 36 mm of edge per side.
    for sx in (-1, 1):
        for sy in (-1, 1):
            cuts.append(cyl("_cr", 3.0, cam_depth * 2.0,
                            (cam_x + sx * cam_pw / 2, row_y + sy * cam_pd / 2,
                             top)))
    ap = cam["lens_holder"] + 2 * P["board_clear"]
    cuts.append(prism("_ap", rrect_pts(ap, ap, 2.0), t * 3, (cam_x, row_y, t / 2)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            dx = sx * cam["pitch_inner"] / 2
            dy = sy * cam["pitch_inner"] / 2
            cuts.append(slot("_s", P["m2_free"], P["slot_travel"], t * 3,
                             (cam_x + dx, row_y + dy, t / 2),
                             math.degrees(math.atan2(dy, dx))))
    # S4B-ZR cable exit. The drawing puts the connector 8.24 mm from the left
    # edge and 3.47 mm from the BOTTOM edge, so the exit belongs on the bottom
    # wall of the pocket - an earlier version notched the top, which is simply
    # the wrong side of the board. Cut through the full thickness rather than
    # just breaching the pocket wall, because which face the socket stands on
    # is not established: a through slot serves the cable either way.
    conn_cx = cam_x - cam["w"] / 2 + cam["conn_x"] + cam["conn_w"] / 2
    cuts.append(prism("_cn", rrect_pts(cam["conn_w"] + 7.0, 10.0, 1.5), t * 3,
                      (conn_cx, row_y - cam_pd / 2, t / 2)))

    # ---- distance sensor: slides DOWN a channel onto a shelf ----
    # Down, not up and not sideways, and that choice is what removes the
    # fastener. Loaded downwards the board lands on a closed shelf and gravity
    # holds it there. Loaded any other way gravity works to eject it and a screw
    # becomes mandatory - and there is nowhere trustworthy to put one, because
    # the board's mounting hole positions are still unknown.
    #
    # A C-channel each side takes the board's vertical edges only: `lip` of
    # material in front and `lip` behind, so it is trapped front-to-back while
    # nothing at all crosses its face. Fit it CONNECTOR UP, so the wires leave
    # through the same opening the board slid in through and never cross the
    # shelf.
    y_shelf = row_y - tof["slot_h"] / 2.0     # closed bottom the board rests on
    ylen = (D / 2 - y_shelf) + 16.0           # channel runs off the TOP to load
    ycen = y_shelf + ylen / 2.0
    chan = tof["slot_w"] - 2 * lip            # what the channel leaves open
    cuts.append(prism("_cav", rrect_pts(tof["slot_w"], ylen, 0.5), cav_d,
                      (tof_x, ycen, top - lip_t - cav_d / 2.0)))
    cuts.append(prism("_lip", rrect_pts(chan, ylen, 0.5), 8.0,
                      (tof_x, ycen, top + 3.0)))
    # Open right through in front of the board. The sensor is not what sets
    # this - the 6-way JST is on the same face and stands far prouder.
    cuts.append(prism("_win", rrect_pts(chan, ylen, 0.5), t * 3,
                      (tof_x, ycen, t / 2)))

    # ---- skull fixings: a three point strip along the bottom ----
    for mx in (-35.0, 0.0, 35.0):
        cuts.append(slot("_m", P["m3_free"], P["slot_travel"], t * 3,
                         (mx, -D / 2 + 4.0, t / 2), 0.0))

    # ---- top corners chamfered off ----
    # The plate is 96 wide and the brow it sits behind is not. The fit study
    # measured these corners breaking out through the skin by 10.3 mm and
    # named two fixes: a fuller brow band, and taking the corners off. Both
    # were done on 13 Aug - see S["swell"] in head_style.py for the other
    # half - and this is the cut, on the line 6|x| + 3.5y = 332, sized from
    # the list of vertices that were actually still outside. It costs
    # nothing in use: the camera pocket ends at x=-42 and its screws at -36,
    # and the ToF channel ends at x=+43.8 and loses only the top of its
    # lead-in lip, well above the y=17.5 the board reaches.
    for sx in (-1, 1):
        cuts.append(prism("_ch", [(sx * 38.4, 29.0), (sx * 70.0, 29.0),
                                  (sx * 70.0, -25.1)], t * 3, (0, 0, t / 2)))
    ob = cut(ob, cuts)
    ob = engrave(ob, "B0385", 3.0, top - cam_depth, (cam_x, row_y - cam_pd / 2 + 4.4))
    ob = engrave(ob, "VL53L1X", 2.6, top, (tof_x - 4.0, -D / 2 + 11.0))
    return ob


def pi5_tray(loc=(0, 0, 0)):
    """Tray the Raspberry Pi 5 bolts to.

    Holes are ROUND here, not slotted. The slotting policy exists for
    dimensions that have not been verified; this pattern came out of Raspberry
    Pi's own mechanical drawing and the board in hand is a genuine Pi, so there
    is nothing to take up. Slotting it would only let the board rack. The
    skull-side fixings are slotted, because where this lands in the head is
    still guesswork.

    Watch the datum: the Pi's hole pattern is *not* centred on its board. It
    sits 3.5 mm in from one long and one short edge, which puts the pattern
    centre 10.0 mm off the board centre along the length.

    `standoff` is a parameter for a reason. The X1200 UPS pogo-pins onto the
    underside of the Pi and wants roughly 15 mm of room below it, so if that
    option is ever taken this is the number that changes - not the layout."""
    b = BOARDS["pi5"]
    t = P["plate_t"]
    boss_d = 7.0
    standoff = 5.0                    # raise to ~15.0 to sit an X1200 underneath
    margin = 4.0
    W = b["w"] + 2 * margin
    D = b["d"] + 2 * margin
    # hole pattern centre relative to board centre
    dx0 = (b["hole_inset"] + b["hx"] / 2.0) - b["w"] / 2.0
    dy0 = (b["hole_inset"] + b["hy"] / 2.0) - b["d"] / 2.0
    ob = plate("pi5_tray", W, D, t, 3.0, (0, 0, t / 2))
    holes = [(dx0 + sx * b["hx"] / 2.0, dy0 + sy * b["hy"] / 2.0)
             for sx in (-1, 1) for sy in (-1, 1)]
    ob = fuse(ob, [cyl("_b", boss_d, standoff, (hx, hy, t + standoff / 2))
                   for (hx, hy) in holes])
    top = t + standoff
    cuts = [cyl("_h", 2.9, top * 3, (hx, hy, top / 2)) for (hx, hy) in holes]
    # ventilation under the SoC - a Pi 5 runs hot and this tray is a lid to it
    for vx in (-20.0, -8.0, 4.0):
        cuts.append(prism("_v", rrect_pts(6.0, 24.0, 2.5), t * 3, (vx, 0, t / 2)))
    # skull fixings on the mid-edges, clear of the standoffs
    for (mx, my) in ((-(W / 2 - 5.0), 0.0), (W / 2 - 5.0, 0.0),
                     (0.0, -(D / 2 - 5.0)), (0.0, D / 2 - 5.0)):
        cuts.append(slot("_m", P["m3_free"], P["slot_travel"], t * 3,
                         (mx, my, t / 2), 90.0 if abs(mx) > abs(my) else 0.0))
    # Four more along the long edges, added 13 Aug once the head shell
    # existed to offer this up to. Two of the four mid-edge fixings above
    # turned out to be unusable in this skull - one has the cranial opening
    # behind it and the other has 62 mm of air in front of it - which left
    # the tray on a two-point mount, free to pivot about its own long axis.
    # These four land on the tray_rail ledges head_mounts.py puts down each
    # side wall. Clear of the standoffs at local y = +-24.5 and x = -39/19.
    for lx in (-30.0, 30.0):
        for ly in (-27.0, 27.0):
            cuts.append(slot("_m", P["m3_free"], P["slot_travel"], t * 3,
                             (lx, ly, t / 2), 0.0))
    # zip-tie pairs for the loom leaving the GPIO header
    for sy in (-1, 1):
        for dx in (-2.5, 2.5):
            cuts.append(prism("_z", rrect_pts(2.5, 5.0, 1.0), t * 3,
                              (28.0 + dx, sy * (D / 2 - 4.0), t / 2)))
    ob = cut(ob, cuts)
    ob = engrave(ob, "PI5", 3.4, t, (-34.0, 0.0), 90.0)
    return ob


def pca9685_mount(loc=(0, 0, 0)):
    """Plate for the HiLetgo PCA9685. Standoffs lift the board clear of its own
    pin tails; slotted holes because the clone is only dimensionally
    interchangeable with Adafruit's until a coupon says otherwise."""
    b = BOARDS["pca9685"]
    t = P["plate_t"]
    boss_d = 7.0
    boss_h = b["under"]
    margin = 8.0
    W = b["w"] + 2 * margin
    D = b["d"] + 2 * margin
    ob = plate("pca9685_mount", W, D, t, 3.0, (0, 0, t / 2))
    bosses = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            bosses.append(cyl("_b", boss_d, boss_h,
                              (sx * b["hx"] / 2, sy * b["hy"] / 2, t + boss_h / 2)))
    ob = fuse(ob, bosses)
    top = t + boss_h
    cuts = []
    # slotted board fixings, radial
    for sx in (-1, 1):
        for sy in (-1, 1):
            x = sx * b["hx"] / 2
            y = sy * b["hy"] / 2
            cuts.append(slot("_s", P["m2_free"], P["slot_travel"], top * 3,
                             (x, y, top / 2), math.degrees(math.atan2(y, x))))
    # skull fixings at the corners, outboard of the board footprint
    for sx in (-1, 1):
        for sy in (-1, 1):
            cuts.append(slot("_m", P["m3_free"], P["slot_travel"], t * 3,
                             (sx * (W / 2 - 5.0), sy * (D / 2 - 5.0), t / 2), 90.0))
    # zip-tie pairs for the servo looms, on the long edges clear of the board
    for sx in (-1, 1):
        for sy in (-1, 1):
            for dx in (-2.5, 2.5):
                cuts.append(prism("_z", rrect_pts(2.5, 5.0, 1.0), t * 3,
                                  (sx * 18.0 + dx, sy * (b["d"] / 2 + 3.6), t / 2)))
    ob = cut(ob, cuts)
    ob = engrave(ob, "PCA9685", 3.2, t, (0, -D / 2 + 3.0))
    return ob


def cable_anchor(loc=(0, 0, 0)):
    """Zip-tie anchor for routing the six-wire VL53L1X loom and the servo leads.
    Two through-slots and a screw slot; no overhangs, prints flat, no supports.
    Six of these: three per eye is enough to give the service loop a home."""
    t = 3.0
    W, D = 20.0, 12.0
    ob = plate("cable_anchor", W, D, t, 2.0, (0, 0, t / 2))
    cuts = []
    for sx in (-1, 1):
        cuts.append(prism("_ts", rrect_pts(2.5, 7.0, 1.0), t * 3,
                          (sx * 3.0, 0, t / 2)))
    cuts.append(slot("_s", P["m2_free"], P["slot_travel"], t * 3,
                     (W / 2 - 3.6, 0, t / 2), 90.0))
    return cut(ob, cuts)


# ===========================================================================
# build + export
# ===========================================================================

BUILDERS = [
    ("coupon_pca9685", coupon_pca9685),
    ("coupon_b0385", coupon_b0385),
    ("coupon_vl53l1x", coupon_vl53l1x),
    ("coupon_mg90s", coupon_mg90s),
    ("coupon_neopixel12", coupon_neopixel12),
    ("forehead_casing", forehead_casing),
    ("pi5_tray", pi5_tray),
    ("pca9685_mount", pca9685_mount),
    ("cable_anchor", cable_anchor),
]


def clear():
    c = bpy.data.collections.get(COLL_NAME)
    if c:
        for ob in list(c.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(c)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)


def setup_scene():
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 0.001
    sc.unit_settings.length_unit = 'MILLIMETERS'


def lay_out(objs, gap=12.0):
    """Spread parts along X so nothing overlaps, all sitting on z=0."""
    x = 0.0
    for ob in objs:
        pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
        w = max(p.x for p in pts) - min(p.x for p in pts)
        minx = min(p.x for p in pts)
        minz = min(p.z for p in pts)
        ob.location.x += x - minx
        ob.location.z -= minz
        x += w + gap


def export_stls():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    written = []
    for ob in _coll().objects:
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        qty = QUANTITIES.get(ob.name, 1)
        fn = "%s_x%d.stl" % (ob.name, qty)
        path = os.path.join(EXPORT_DIR, fn)
        bpy.ops.wm.stl_export(
            filepath=path,
            export_selected_objects=True,
            global_scale=1.0,
            use_scene_unit=False,   # 1 BU = 1 mm already; slicers assume mm
            forward_axis='Y',
            up_axis='Z',
            apply_modifiers=True,
        )
        written.append((fn, os.path.getsize(path)))
    return written


def build(export=True, force=False):
    guard(collection_contents(COLL_NAME), "eye_mech.build()", force)
    setup_scene()
    clear()
    objs = []
    for name, fn in BUILDERS:
        ob = fn()
        ob.name = name
        objs.append(ob)
        pts = [v.co for v in ob.data.vertices]
        print("built %-18s %6.2f x %6.2f x %6.2f  verts=%d" % (
            name,
            max(p.x for p in pts) - min(p.x for p in pts),
            max(p.y for p in pts) - min(p.y for p in pts),
            max(p.z for p in pts) - min(p.z for p in pts),
            len(pts)))
    lay_out(objs)
    if export:
        for fn, sz in export_stls():
            print("exported %-34s %8d bytes" % (fn, sz))
    return objs


if __name__ == "__main__":
    build()
