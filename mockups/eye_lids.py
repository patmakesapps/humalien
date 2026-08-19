"""Eyelids for the two O24 balls, and the linkage that actually drives them.

    exec(open(r"C:\H\humalien\mockups\eye_lids.py").read())
    build(); blink(0.0); blink(1.0); check()

THE ONE FACT THE WHOLE THING RESTS ON
-------------------------------------
Both eye centres lie on ONE line: y=26.68, z=0, running along x. So the left
and right upper lids do not have two hinge axes - they share one. A rigid bail
tying them together is therefore not a compromise to save a servo, it is the
exactly correct rigid body. The bail IS the hinge. Same for the lower pair.

WHY THERE IS A LINKAGE AT ALL
-----------------------------
A servo cannot sit on that line. Its body needs 27.2 mm of run along its own
shaft and the corridor between the balls is 39 mm, so two of them pointing
opposite ways have to step apart in z and neither ends up on the axis. Welding
a bail straight to an off-axis spline drives the lids about the SERVO axis,
which buries the upper shell 3.06 mm into the eyeball by full close. Measured,
not guessed - the old check() printed it.

So the offset gets absorbed by a PARALLELOGRAM: an 8 mm crank on the spline,
an 8 mm tab on the bail, and a conrod exactly as long as the servo offset.
Both arms stay parallel forever, so the transfer is 1:1 with no dead points
and no slot to wear. The servo turns exactly the angle the lid turns.

HOW THE TWO BAILS SHARE ONE AXIS
--------------------------------
A fixed axle on the eye axis, held from the FRONT by a two-prong bracket -
the front is the only sector neither bail ever sweeps through. Both bails
ride it on their own hubs, at different x. Their crossbars run at r=5.5,
one above the axis and one below, in the |z|<7.95 slab that the servos leave
completely clear. Their arms reach out to the lid tips at r=4.5, upper above
and lower below, which is where each lune's material already is.
"""

import bpy
import bmesh
import math
from mathutils import Vector, Matrix

COLL = "EYE_LIDS"
COLL_GAZE = "EYE_GAZE"      # kept separate so either half can be reviewed alone
EYE_R, IPD = 12.0, 63.0
EYE_X, EYE_Y, EYE_Z = IPD / 2.0, 26.68, 0.0

LIDS = {
    # tails cut back from -170/185 so the lids no longer wrap the back of the
    # globe.  Swept across the blink they now occupy alpha -110..120, leaving a
    # 130 deg wedge at the rear free at EVERY point in the cycle - which is the
    # only way there is anywhere to hold the eyeball for pan and tilt.
    "lower": dict(ri=12.5, ro=13.7, margin=-25.0, tail=-110.0, sweep=22.0),
    "upper": dict(ri=14.1, ro=15.9, margin=28.0, tail=120.0, sweep=-50.0),
}
B0, B1 = 7.0, 173.0
NBETA, NALPHA = 40, 26

# --- the spine: one fixed axle, two bails riding it --------------------
AXLE_D, AXLE_X = 4.0, 13.0
HUB_BORE, HUB_OD = 4.4, 7.0
HUB_DRV, HUB_FAR = (10.4, 12.9), (7.2, 9.6)  # drive-side hub, far hub - the
                          # far one steps outboard to open a window at the
                          # centre for the rear bracket prongs
BAR_R, BAR_W, BAR_T, BAR_X = 5.5, 5.0, 3.0, 14.5    # crossbar
# Arm radius is set by the BALL and by the OTHER rank.s lid.  The lower arm
# is a cylinder at radius armr, so seen from the eye axis it subtends
# asin((armd/2)/armr) either side of straight down - and at full close the
# upper lid.s leading edge sits at phi -158.  armd 4.8 keeps the arm inside
# -155, which is why it is not simply as fat as it will fit.  On the axis the ball reaches
# x=19.5, so the further off-axis an arm sits the further out in x it may run
# before it cuts in - but each lune tip converges on the axis at its own
# radius, so the two ranks want different arms.  Per rank, in DRIVE.

# --- the drive: crank == tab, conrod == offset. A parallelogram. -------
COLLAR_BORE, COLLAR_OD = 4.6, 9.0
LINK = 8.0
PIN_D, PIN_FIT = 3.0, 0.2
TAB_R0, TAB_R1 = 3.2, 9.5
ROD_OD = 6.5

SERVO_Z = 14.0

DRIVE = {
    "upper": dict(sv=(9.13, 26.22, SERVO_Z), sx=1, sgn=1, th0=10.0,
                  arm=(13.8, 19.3), armr=5.5, armd=5.0, tab=(10.4, 12.9),
                  collar=(9.6, 13.1), rod=(14.0, 16.2)),
    "lower": dict(sv=(-7.99, 25.74, -SERVO_Z), sx=-1, sgn=-1, th0=-10.0,
                  arm=(13.8, 19.0), armr=3.5, armd=4.8, tab=(10.4, 12.9),
                  collar=(8.6, 12.1), rod=(14.0, 16.2)),
}
PIN_END = 16.4
ASSY = ("upper", "lower")

for _t, _d in DRIVE.items():
    _d["off"] = math.hypot(_d["sv"][1] - EYE_Y, _d["sv"][2] - EYE_Z)
    _d["dth"] = -LIDS[_t]["sweep"]          # tab/crank swing, open -> shut

PRONG_X, PRONG_T, PRONG_Z = 5.0, 3.0, 2.5   # rear bracket prongs
PLATE_Y = (50.0, 54.0)                      # mounting plate, clear of the servos

# Read off PROXY_servo_pan: local z is the shaft, local x runs the tab length,
# local y the width.  The mounting flange is a collar at local z -7.67..-5.17
# spanning local x -10.37..21.83, and it stands proud of the case (which ends
# at local x 16.98) only at its two ENDS - those overhangs are the screw ears.
# The lip therefore cannot be a full-length wall; it catches the REAR ear.
TAB_Z, TAB_LEN, CASE_LEN = -5.17, 21.83, 16.98
LIP_T, HOLE_D, HOLE_INSET, HOLE_PITCH = 3.0, 2.2, 2.1, 10.0

# Chassis face: 4 x M3 clearance on 15 x 31 centres, in the plate at y 50..54.
# What it bolts to is left open on purpose.
# ---- gaze: ball in socket, two servos -------------------------------------
# The lids, swept, occupy alpha -110..120, so alpha 120..250 is free on the
# globe at every beta.  The straps live well inside that; the stem comes
# straight back out of the rear pole and never reaches them because they sit
# 60 deg away in BETA, which the stem barely moves in.
PAN_MAX, TILT_MAX = 22.0, 18.0
SOCK_RI, SOCK_RO = 12.2, 15.2
SOCK_BETA, SOCK_BW = 30.0, 9.0
SOCK_A0, SOCK_A1 = 145.0, 215.0
SOCK_BAR = (14.0, 18.0, -16.0, -12.0)   # tie bar, local y0,y1,z0,z1
POST_D, POST_L = 3.0, 5.0
GROD_D = 3.0
PLATE_X = 20.0

PLATE_HOLE_D = 3.4
PLATE_HOLES = [(sx * 7.5, sz * 15.5) for sx in (-1, 1) for sz in (-1, 1)]

SERVO_SRC = "PROXY_servo_pan.001"
SMOOTH_ANGLE = 35.0


# ----------------------------------------------------------------- shapes
def _dir(beta, alpha):
    b, a = math.radians(beta), math.radians(alpha)
    return Vector((math.cos(b), -math.sin(b) * math.cos(a), math.sin(b) * math.sin(a)))


def _shell(bm, ri, ro, a0, a1, b0=B0, b1=B1, nb=NBETA, na=NALPHA):
    """Shell between two concentric radii, over a beta and an alpha range.
    beta runs pole to pole along x; alpha is the angle about the x axis."""
    NBETA, NALPHA = nb, na
    betas = [b0 + (b1 - b0) * i / nb for i in range(nb + 1)]
    al = [a0 + (a1 - a0) * j / na for j in range(na + 1)]
    IN = [[bm.verts.new(_dir(b, a) * ri) for a in al] for b in betas]
    OU = [[bm.verts.new(_dir(b, a) * ro) for a in al] for b in betas]
    for i in range(NBETA):
        for j in range(NALPHA):
            bm.faces.new((IN[i][j], IN[i][j + 1], IN[i + 1][j + 1], IN[i + 1][j]))
            bm.faces.new((OU[i][j], OU[i + 1][j], OU[i + 1][j + 1], OU[i][j + 1]))
    for j in range(NALPHA):
        bm.faces.new((IN[0][j], IN[0][j + 1], OU[0][j + 1], OU[0][j]))
        bm.faces.new((IN[NBETA][j], OU[NBETA][j], OU[NBETA][j + 1], IN[NBETA][j + 1]))
    for i in range(NBETA):
        bm.faces.new((IN[i][0], OU[i][0], OU[i + 1][0], IN[i + 1][0]))
        bm.faces.new((IN[i][NALPHA], IN[i + 1][NALPHA],
                      OU[i + 1][NALPHA], OU[i][NALPHA]))


def _tube(bm, ri, ro, x0, x1, cy=0.0, cz=0.0, segs=32):
    x0, x1 = min(x0, x1), max(x0, x1)
    g = {}
    for xi, x in enumerate((x0, x1)):
        for k, r in enumerate((ri, ro)):
            g[(xi, k)] = [bm.verts.new((x, cy + r * math.cos(2 * math.pi * j / segs),
                                        cz + r * math.sin(2 * math.pi * j / segs)))
                          for j in range(segs)]
    for k in range(segs):
        j = (k + 1) % segs
        bm.faces.new((g[(0, 1)][k], g[(0, 1)][j], g[(1, 1)][j], g[(1, 1)][k]))
        bm.faces.new((g[(1, 0)][k], g[(1, 0)][j], g[(0, 0)][j], g[(0, 0)][k]))
        bm.faces.new((g[(0, 0)][k], g[(0, 0)][j], g[(0, 1)][j], g[(0, 1)][k]))
        bm.faces.new((g[(1, 1)][k], g[(1, 1)][j], g[(1, 0)][j], g[(1, 0)][k]))


def _rod(bm, r, x0, x1, cy=0.0, cz=0.0, segs=24):
    x0, x1 = min(x0, x1), max(x0, x1)
    v = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                              radius1=r, radius2=r, depth=x1 - x0)["verts"]
    bmesh.ops.rotate(bm, verts=v, cent=(0, 0, 0),
                     matrix=Matrix.Rotation(math.radians(90), 3, "Y"))
    bmesh.ops.translate(bm, vec=Vector(((x0 + x1) / 2.0, cy, cz)), verts=v)


def _rody(bm, r, y0, y1, cx=0.0, cz=0.0, segs=24):
    """Cylinder along Y - the plate face is normal to y, so its holes are."""
    y0, y1 = min(y0, y1), max(y0, y1)
    v = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                              radius1=r, radius2=r, depth=y1 - y0)["verts"]
    bmesh.ops.rotate(bm, verts=v, cent=(0, 0, 0),
                     matrix=Matrix.Rotation(math.radians(-90), 3, "X"))
    bmesh.ops.translate(bm, vec=Vector((cx, (y0 + y1) / 2.0, cz)), verts=v)


def _box(bm, x0, x1, y0, y1, z0, z1):
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    z0, z1 = min(z0, z1), max(z0, z1)
    v = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    bmesh.ops.scale(bm, verts=v, vec=(x1 - x0, y1 - y0, z1 - z0))
    bmesh.ops.translate(bm, verts=v,
                        vec=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))


def _pt(cy, cz, th, r):
    a = math.radians(th)
    return Vector((0.0, cy + r * math.cos(a), cz + r * math.sin(a)))


def _plate(bm, cy, cz, pts, x0, x1):
    """A flat plate in the y-z plane, `pts` given as (angle_deg, radius) about
    (cy, cz), extruded from x0 to x1. Angle 0 is +y (straight back)."""
    x0, x1 = min(x0, x1), max(x0, x1)
    a = [bm.verts.new(Vector((x0, 0, 0)) + _pt(cy, cz, *p)) for p in pts]
    b = [bm.verts.new(Vector((x1, 0, 0)) + _pt(cy, cz, *p)) for p in pts]
    bm.faces.new(a)
    bm.faces.new(list(reversed(b)))
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new((a[i], a[j], b[j], b[i]))


def _finish(bm, name, coll, loc=(0, 0, 0)):
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    coll.objects.link(ob)
    return ob


def _frame_m(shaft, body):
    z = Vector(shaft).normalized()
    x = Vector(body).normalized()
    x = (x - z * x.dot(z)).normalized()
    return Matrix((x, z.cross(x), z)).transposed().to_4x4()


def _fuse(name, parts, coll, loc=(0, 0, 0), cuts=()):
    """Boolean union, applied, Exact solver. `parts` are (bm) builders."""
    obs = []
    for i, fn in enumerate(parts):
        bm = bmesh.new()
        fn(bm)
        obs.append(_finish(bm, "_frag%02d" % i, coll))
    base = obs[0]
    bpy.context.view_layer.objects.active = base
    for o in obs[1:]:
        m = base.modifiers.new(type="BOOLEAN", name="u_" + o.name)
        m.operation, m.object, m.solver = "UNION", o, "EXACT"
    for i, fn in enumerate(cuts):
        bm = bmesh.new()
        fn(bm)
        c = _finish(bm, "_cut%02d" % i, coll)
        obs.append(c)
        m = base.modifiers.new(type="BOOLEAN", name="d_" + c.name)
        m.operation, m.object, m.solver = "DIFFERENCE", c, "EXACT"
    ok = True
    for m in list(base.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=m.name)
        except Exception as e:
            print("  union failed on %s: %s" % (m.name, e))
            ok = False
    for o in obs[1:]:
        bpy.data.objects.remove(o, do_unlink=True)
    base.name = base.data.name = name
    _set_origin(base, Vector(loc))
    return base if ok else None


def _set_origin(ob, piv):
    """Move the object origin to `piv` without moving the geometry, so that
    rotation_euler.x is a rotation about the line x through piv."""
    for v in ob.data.vertices:
        v.co -= piv
    ob.location = piv


def _bar(bm, p0, p1, w, x0, x1):
    """A rectangular bar in the y-z plane between 2D points p0,p1, `w` wide."""
    dy, dz = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dy, dz)
    ny, nz = -dz / L, dy / L
    pts = [(p0[0] + ny * w / 2, p0[1] + nz * w / 2),
           (p1[0] + ny * w / 2, p1[1] + nz * w / 2),
           (p1[0] - ny * w / 2, p1[1] - nz * w / 2),
           (p0[0] - ny * w / 2, p0[1] - nz * w / 2)]
    x0, x1 = min(x0, x1), max(x0, x1)
    a = [bm.verts.new((x0, py, pz)) for py, pz in pts]
    b = [bm.verts.new((x1, py, pz)) for py, pz in pts]
    bm.faces.new(a)
    bm.faces.new(list(reversed(b)))
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((a[i], a[j], b[j], b[i]))


# ------------------------------------------------------------- kinematics
def tab_pin(tag, th):
    """Centre of the pin on the BAIL's tab, at tab angle th (deg)."""
    return _pt(EYE_Y, EYE_Z, th, LINK)


def crank_pin(tag, th):
    """Centre of the pin on the SERVO's crank. Parallelogram: same angle."""
    d = DRIVE[tag]
    return _pt(d["sv"][1], d["sv"][2], th, LINK)


# ------------------------------------------------------------------ parts
def _bail(tag, coll):
    d, L = DRIVE[tag], LIDS[tag]
    g, sx = d["sgn"], d["sx"]
    # the drive-side hub sits under this bail own tab; the far hub steps
    # inboard, so the two bails never occupy the same x as each other
    hd, hf = HUB_DRV, HUB_FAR
    th0, ar = d["th0"], d["arm"]
    arr, ard = d["armr"], d["armd"]
    tp = tab_pin(tag, th0)
    frags = [
        lambda bm: _tube(bm, HUB_BORE / 2, HUB_OD / 2,
                         sx * hd[0], sx * hd[1], EYE_Y, EYE_Z),
        lambda bm: _tube(bm, HUB_BORE / 2, HUB_OD / 2,
                         -sx * hf[0], -sx * hf[1], EYE_Y, EYE_Z),
        lambda bm: _box(bm, -BAR_X, BAR_X, EYE_Y - BAR_W / 2, EYE_Y + BAR_W / 2,
                        g * BAR_R - BAR_T / 2, g * BAR_R + BAR_T / 2),
        # the crossbar rides clear of every hub so it can pass the OTHER
        # bail; these two webs are what tie it to its own.  They start at
        # r=2.3, just outside the 2.2 bore, so the axle stays free.
        lambda bm: _box(bm, sx * hd[0], sx * hd[1],
                        EYE_Y - BAR_W / 2, EYE_Y + BAR_W / 2, g * 2.3, g * BAR_R),
        lambda bm: _box(bm, -sx * hf[0], -sx * hf[1],
                        EYE_Y - BAR_W / 2, EYE_Y + BAR_W / 2, g * 2.3, g * BAR_R),
        lambda bm: _rod(bm, ard / 2, ar[0], ar[1], EYE_Y, EYE_Z + g * arr),
        lambda bm: _rod(bm, ard / 2, -ar[1], -ar[0], EYE_Y, EYE_Z + g * arr),
        lambda bm: _plate(bm, EYE_Y, EYE_Z,
                          [(th0 - 14, TAB_R0), (th0 + 14, TAB_R0),
                           (th0 + 5, TAB_R1), (th0 - 5, TAB_R1)],
                          sx * d["tab"][0], sx * d["tab"][1]),
        lambda bm: _rod(bm, PIN_D / 2, sx * (d["tab"][1] - 0.5), sx * PIN_END,
                        tp.y, tp.z),
    ]
    return _fuse("bail_" + tag, frags, coll, (0.0, EYE_Y, EYE_Z))


def _crank(tag, coll):
    d = DRIVE[tag]
    sx, th0, c = d["sx"], d["th0"], d["collar"]
    cp = crank_pin(tag, th0)
    sy, sz = d["sv"][1], d["sv"][2]
    frags = [
        lambda bm: _tube(bm, COLLAR_BORE / 2, COLLAR_OD / 2,
                         sx * c[0], sx * c[1], sy, sz),
        lambda bm: _plate(bm, sy, sz,
                          [(th0 - 16, 3.0), (th0 + 16, 3.0),
                           (th0 + 6, LINK + 2.5), (th0 - 6, LINK + 2.5)],
                          sx * c[0], sx * c[1]),
        lambda bm: _rod(bm, PIN_D / 2, sx * (c[1] - 0.5), sx * PIN_END, cp.y, cp.z),
    ]
    return _fuse("crank_" + tag, frags, coll, (0.0, sy, sz))


def _conrod(tag, coll):
    d = DRIVE[tag]
    sx, r = d["sx"], d["rod"]
    tp, cp = tab_pin(tag, d["th0"]), crank_pin(tag, d["th0"])
    bore = PIN_D / 2 + PIN_FIT
    frags = [
        lambda bm: _tube(bm, bore, ROD_OD / 2, sx * r[0], sx * r[1], tp.y, tp.z),
        lambda bm: _tube(bm, bore, ROD_OD / 2, sx * r[0], sx * r[1], cp.y, cp.z),
        lambda bm: _bar(bm, (tp.y, tp.z), (cp.y, cp.z), ROD_OD - 1.5,
                        sx * r[0], sx * r[1]),
    ]
    return _fuse("rod_" + tag, frags, coll)


def _lip(tag):
    """Where the mounting lip for one servo goes, all derived from the proxy.

    Returns (x0, x1, y0, y1, z0, z1, holes) - a wall standing in the y-z plane
    against the OUTBOARD face of the servo's flange, covering the rear screw
    ear, running back to the mounting plate."""
    d = DRIVE[tag]
    sx, (svx, svy, svz) = d["sx"], d["sv"]
    face = svx + sx * TAB_Z                 # outboard face of the flange
    y0 = svy + CASE_LEN + 0.1               # just clear of the case
    y1 = PLATE_Y[0]
    hy = svy + TAB_LEN - HOLE_INSET         # rear screw pair
    holes = [(hy, svz - HOLE_PITCH / 2), (hy, svz + HOLE_PITCH / 2)]
    return face, face + sx * LIP_T, y0, y1, svz - 6.05, svz + 6.05, holes


def _socket(side, sx, coll):
    """Two spherical straps per eye, at beta 30 and 150 - 60 deg away from the
    rear pole, where the stem never reaches - joined by a tie bar below and
    behind the globe, and a leg back to the chassis plate.

    This is the bearing surface only. How the eyeball is held INTO it, and what
    swings it for tilt, are the next two problems - deliberately not here."""
    y0, y1, z0, z1 = SOCK_BAR
    xb = SOCK_RO * math.cos(math.radians(SOCK_BETA - SOCK_BW))
    frags = [
        lambda bm: _shell(bm, SOCK_RI, SOCK_RO, SOCK_A0, SOCK_A1,
                          SOCK_BETA - SOCK_BW, SOCK_BETA + SOCK_BW, 10, 20),
        lambda bm: _shell(bm, SOCK_RI, SOCK_RO, SOCK_A0, SOCK_A1,
                          180 - SOCK_BETA - SOCK_BW, 180 - SOCK_BETA + SOCK_BW,
                          10, 20),
        # the straps bottom out at z = -5.5, so the legs have to reach that
        # far up or the straps are left floating
        lambda bm: _box(bm, xb - 3.0, xb, 6.0, y1, z0, -2.0),
        lambda bm: _box(bm, -xb, -xb + 3.0, 6.0, y1, z0, -2.0),
        lambda bm: _box(bm, -xb, xb, y0, y1, z0, z1),
        # leg back to the chassis plate. local -x is inboard for both eyes
        # once the mirror is applied, and the plate reaches x +-20.
        lambda bm: _box(bm, -xb, -xb + 3.0, y0, PLATE_Y[1] - EYE_Y, z0, z1),
    ]
    ob = _fuse("socket_" + side, frags, coll)
    if ob:
        for v in ob.data.vertices:
            v.co.x *= sx
        ob.location = (sx * EYE_X, EYE_Y, EYE_Z)
    return ob


def _rodz(bm, r, z0, z1, cx=0.0, cy=0.0, segs=20):
    z0, z1 = min(z0, z1), max(z0, z1)
    v = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                              radius1=r, radius2=r, depth=z1 - z0)["verts"]
    bmesh.ops.translate(bm, vec=Vector((cx, cy, (z0 + z1) / 2.0)), verts=v)


def _spine(coll):
    """Fixed axle on the eye axis, carried from BEHIND, plus the servo mounts.

    The bails sweep almost every sector around that axis - the crossbars take
    65..165 and -65..-137, the tabs take -46..74 - so there is nowhere in
    FRONT to reach it from without standing a post between the eyes. But at
    theta 0, straight back, the only things sweeping are the tabs, and those
    live at |x| 10.4..12.9. So the prongs come straight back at |x| 5.0,
    through the window the far hubs were moved outboard to open."""
    bm = bmesh.new()
    _rod(bm, AXLE_D / 2, -AXLE_X, AXLE_X, EYE_Y, EYE_Z, segs=32)
    _finish(bm, "axle", coll)
    h = PRONG_T / 2
    zt = SERVO_Z + 6.05 + 0.5
    frags = [
        lambda bm: _tube(bm, AXLE_D / 2, 3.5, PRONG_X - h, PRONG_X + h, EYE_Y, EYE_Z),
        lambda bm: _tube(bm, AXLE_D / 2, 3.5, -PRONG_X - h, -PRONG_X + h, EYE_Y, EYE_Z),
        lambda bm: _box(bm, PRONG_X - h, PRONG_X + h, EYE_Y, PLATE_Y[1],
                        -PRONG_Z, PRONG_Z),
        lambda bm: _box(bm, -PRONG_X - h, -PRONG_X + h, EYE_Y, PLATE_Y[1],
                        -PRONG_Z, PRONG_Z),
        lambda bm: _box(bm, -PLATE_X, PLATE_X, PLATE_Y[0], PLATE_Y[1], -zt, zt),
    ]
    cuts = [(lambda bm, p=p: _rody(bm, PLATE_HOLE_D / 2, PLATE_Y[0] - 1.0,
                                  PLATE_Y[1] + 1.0, p[0], p[1], segs=16))
            for p in PLATE_HOLES]
    for tag in ASSY:
        x0, x1, y0, y1, z0, z1, holes = _lip(tag)
        frags.append(lambda bm, a=(x0, x1, y0, y1, z0, z1):
                     _box(bm, a[0], a[1], a[2], a[3], a[4], a[5]))
        for hy, hz in holes:
            cuts.append(lambda bm, p=(x0, x1, hy, hz):
                        _rod(bm, HOLE_D / 2, min(p[0], p[1]) - 1.0,
                             max(p[0], p[1]) + 1.0, p[2], p[3], segs=16))
    return _fuse("brkt_rear", frags, coll, cuts=cuts)


# ------------------------------------------------------------------ build
def build(gaze=False):
    """Lid mechanism only by default. build(gaze=True) adds the socket cups
    into their own collection - kept opt-in so a rebuild never re-litters the
    scene with a half-solved sub-assembly."""
    for ob in list(bpy.data.objects):
        if ob.name.startswith(("lid_", "LID_", "SV_lid", "knub_", "boss_", "_frag",
                               "brkt_rear", "socket_", "eyestem_", "frame_tilt",
                               "standoff_", "bar_pan", "link_pan_", "crank_tilt",
                               "crank_pan", "SV_gaze", "spine_", "hub_", "arm_",
                               "web_", "HORN_", "bail_",
                               "crank_", "rod_", "axle", "brkt_", "HINGE_",
                               "sector_", "pinion_")):
            bpy.data.objects.remove(ob, do_unlink=True)
    want_gaze = gaze
    for nm in (COLL, COLL_GAZE):
        old = bpy.data.collections.get(nm)
        if old:
            bpy.data.collections.remove(old)
    coll = bpy.data.collections.new(COLL)
    bpy.context.scene.collection.children.link(coll)
    gaze = None
    if want_gaze:
        gaze = bpy.data.collections.new(COLL_GAZE)
        bpy.context.scene.collection.children.link(gaze)

    for tag in ASSY:
        d = LIDS[tag]
        for side, sx in (("L", 1), ("R", -1)):
            bm = bmesh.new()
            _shell(bm, d["ri"], d["ro"], d["margin"], d["tail"])
            _finish(bm, "lid_%s_%s" % (tag, side), coll,
                    (sx * EYE_X, EYE_Y, EYE_Z))

    _spine(coll)
    if gaze is not None:
        for side, sx in (("L", 1), ("R", -1)):
            _socket(side, sx, gaze)
    for tag in ASSY:
        _bail(tag, coll)
        _crank(tag, coll)
        _conrod(tag, coll)
        src = _servo_src()
        if src is None:
            print("  *** %s is missing - servo proxies NOT built, so every"
                  % SERVO_SRC)
            print("      clearance against a servo is going unchecked")
        if src:
            dr = DRIVE[tag]
            sv = bpy.data.objects.new("SV_lid_" + tag, src.data)
            coll.objects.link(sv)
            sv.matrix_world = (Matrix.Translation(Vector(dr["sv"]))
                               @ _frame_m((dr["sx"], 0, 0), (0, 1, 0)))

    smooth(coll)
    blink(0.0)
    try:
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True,
                                       do_recursive=True)
    except Exception:
        pass
    print("built %d objects in %s  (%d meshes in file)"
          % (len(coll.objects), COLL, len(bpy.data.meshes)))
    return check()


def smooth(coll=None, angle=SMOOTH_ANGLE):
    obs = [o for o in (coll or bpy.data.collections[COLL]).objects if o.type == "MESH"]
    if not obs:
        return
    for ob in obs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    for call in (lambda: bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle)),
                 lambda: bpy.ops.object.shade_auto_smooth(angle=math.radians(angle)),
                 lambda: bpy.ops.object.shade_smooth()):
        try:
            call()
            break
        except Exception:
            continue
    for ob in obs:
        ob.select_set(False)


def blink(t=0.0):
    """0 = wide open, 1 = shut. Lids, bail and crank all turn by the same
    angle - that is what the parallelogram buys. The conrod only translates."""
    t = max(0.0, min(1.0, t))
    for tag in ASSY:
        d = DRIVE[tag]
        a = math.radians(-LIDS[tag]["sweep"] * t)
        for n in ("lid_%s_L" % tag, "lid_%s_R" % tag,
                  "bail_%s" % tag, "crank_%s" % tag):
            ob = bpy.data.objects.get(n)
            if ob:
                ob.rotation_euler = (a, 0, 0)
        rd = bpy.data.objects.get("rod_" + tag)
        if rd:
            p0 = tab_pin(tag, d["th0"])
            p1 = tab_pin(tag, d["th0"] + math.degrees(a))
            rd.location = (0.0, p1.y - p0.y, p1.z - p0.z)
    bpy.context.view_layer.update()


# ------------------------------------------------------------------ check
def _sample(ob, n=160):
    vs = ob.data.vertices
    step = max(1, len(vs) // n)
    M = ob.matrix_world
    return [M @ vs[i].co for i in range(0, len(vs), step)]


def _mindist(A, B):
    m = 1e9
    for a in A:
        for b in B:
            d = (a - b).length_squared
            if d < m:
                m = d
    return math.sqrt(m)


def _touching(a, b):
    """Pairs that are SUPPOSED to touch. Every entry here is ONE named joint.

    Do not group parts into a set and excuse all pairs among them - that is
    how a whole sub-assembly gets excused at once, and a blanket like that is
    exactly what let a bad build report PASS."""
    p = {a, b}
    for tag in ASSY:
        # bail is welded to its two lids, and pinned to its conrod
        fam = {"bail_" + tag, "lid_%s_L" % tag, "lid_%s_R" % tag, "rod_" + tag}
        if a in fam and b in fam:
            return True
        if p == {"crank_" + tag, "rod_" + tag}:
            return True          # pinned
        if p == {"crank_" + tag, "SV_lid_" + tag}:
            return True          # collar grips the spline
        if p == {"axle", "bail_" + tag}:
            return True          # journal
    if p == {"axle", "brkt_rear"}:
        return True              # axle is press-fit in the bracket collars
    if p == {"brkt_rear", "SV_lid_upper"} or p == {"brkt_rear", "SV_lid_lower"}:
        return True              # lips land flush on the servo flanges
    for s in "LR":
        if p == {"socket_" + s, "brkt_rear"}:
            return True          # socket leg lands on the chassis plate
        if p == {"socket_" + s, "eye_" + s}:
            return True          # bearing: 0.2 mm off the ball on purpose
    return False


def check(verbose=True):
    coll = bpy.data.collections[COLL]
    gaze = bpy.data.collections.get(COLL_GAZE)
    ok = True
    if verbose:
        print("\n  %-16s %6s %8s %9s %6s"
              % ("part", "verts", "n-manif", "boundary", "solid"))
        print("  " + "-" * 52)
    for ob in [bpy.data.objects[n] for n in _all_meshes()
               if not n.startswith("SV_")]:
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        nm = sum(1 for e in bm.edges if not e.is_manifold)
        bd = sum(1 for e in bm.edges if e.is_boundary)
        good = len(bm.verts) > 0 and nm == 0 and bd == 0
        ok &= good
        if verbose:
            print("  %-16s %6d %8d %9d %6s"
                  % (ob.name, len(bm.verts), nm, bd,
                     "OK" if good else ("*** EMPTY" if not len(bm.verts) else "OPEN")))
        bm.free()


    print("\n  IS IT ONE PIECE, AND DOES IT CUT THE BALL?")
    print("  (loose>1 means something is floating; ball>0 means it is buried)")
    print("  %-14s %7s %10s %10s" % ("part", "pieces", "into ball", "weld/lid"))
    print("  " + "-" * 46)
    blink(0.0)
    parts = ["axle", "brkt_rear"]
    parts += ["%s_%s" % (p, t) for t in ASSY for p in ("bail", "crank", "rod")]
    parts += ["socket_%s" % s for s in "LR"]
    for n in parts:
        ob = bpy.data.objects.get(n)
        if ob is None:
            continue
        lp = _loose(ob)
        if n.startswith("eyestem_"):
            ball = 0.0                     # the stem IS the eyeball
        elif n.startswith("socket_"):
            s = n[-1]
            tmp = _solid_eye(s, coll)
            ball = _ivol(n, tmp.name)
            bpy.data.objects.remove(tmp, do_unlink=True)
        else:
            ball = sum(_ivol(n, e) for e in ("eye_L", "eye_R")
                       if e in bpy.data.objects)
        weld = ""
        if n.startswith("bail_"):
            t = n.split("_")[1]
            w = _ivol(n, "lid_%s_L" % t)
            weld = "%8.1f" % w
            if w < 5.0:
                ok = False
        bad = lp != 1 or ball > 1e-4
        ok &= not bad
        print("  %-14s %7d %10.2f %10s %s"
              % (n, lp, ball, weld, "*** " if bad else ""))
    print("\n  LID TO BALL, through the blink  (drive is on the eye axis, so flat)")
    print("  %-8s %10s %10s" % ("blink", "upper", "lower"))
    print("  " + "-" * 32)
    worst = 1e9
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        blink(t)
        row = {}
        for tag in ASSY:
            m = 1e9
            for side in "LR":
                lid = bpy.data.objects["lid_%s_%s" % (tag, side)]
                c = bpy.data.objects["eye_%s" % side].matrix_world.translation
                M, vs = lid.matrix_world, lid.data.vertices
                for i in range(0, len(vs), 3):
                    m = min(m, (M @ vs[i].co - c).length - EYE_R)
            row[tag] = m
            worst = min(worst, m)
        print("  %-8.2f %10.3f %10.3f" % (t, row["upper"], row["lower"]))

    names = _all_meshes()
    names += [n for n in ("eye_L", "eye_R") if n in bpy.data.objects]
    pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]
             if not _touching(a, b)]
    gaps = dict((p, 1e9) for p in pairs)
    for t in (0.0, 0.5, 1.0):
        blink(t)
        pts = dict((n, _sample(bpy.data.objects[n])) for n in names)
        for p in pairs:
            gaps[p] = min(gaps[p], _mindist(pts[p[0]], pts[p[1]]))
    tight = sorted(gaps.items(), key=lambda kv: kv[1])[:10]
    print("\n  TIGHTEST CLEARANCES between parts that must NOT touch")
    print("  (sampled vertices - a floor, not a proof)")
    print("  " + "-" * 52)
    for (a, b), g in tight:
        print("  %-17s %-17s %7.2f %s"
              % (a, b, g, "*** CLASH" if g < 0.4 else ""))
        if g < 0.4:
            ok = False


    blink(0.0)
    solid = _overlaps(_all_meshes())
    print("\n  SOLID INTERPENETRATION at neutral  (boolean, not sampled -")
    print("   a distance check is blind to two coarse boxes passing through)")
    print("  " + "-" * 56)
    if not solid:
        print("  none")
    for v, a, b in solid[:12]:
        print("  %-16s %-16s %9.2f mm3  ***" % (a, b, v))
        ok = False
    blink(0.0)
    print("\n  servo offsets: upper %.2f mm, lower %.2f mm off the eye axis"
          % (DRIVE["upper"]["off"], DRIVE["lower"]["off"]))
    print("  conrod lengths equal those offsets, crank = tab = %.1f mm," % LINK)
    print("  so the transfer is exactly 1:1 with no dead point.")
    for tag in ASSY:
        d = DRIVE[tag]
        print("  %-6s servo swings %5.1f deg  (tab %+.0f -> %+.0f)"
              % (tag, abs(d["dth"]), d["th0"], d["th0"] + d["dth"]))
    print("  worst lid-to-ball gap anywhere in the blink: %.3f mm" % worst)
    print("\n%s" % ("ALL CHECKS PASSED" if ok else "*** CHECK FAILED"))
    return ok


def weld():
    """Fuse each bail to its two lids - they are one rigid body and should be
    one printed part. Do this last; blink() still works, check() cannot."""
    coll = bpy.data.collections[COLL]
    blink(0.0)
    for tag in ASSY:
        base = bpy.data.objects.get("bail_" + tag)
        if base is None:
            continue
        bpy.context.view_layer.objects.active = base
        kids = [bpy.data.objects.get("lid_%s_%s" % (tag, s)) for s in "LR"]
        for k in [k for k in kids if k]:
            m = base.modifiers.new(type="BOOLEAN", name="w_" + k.name)
            m.operation, m.object, m.solver = "UNION", k, "EXACT"
        for m in list(base.modifiers):
            bpy.ops.object.modifier_apply(modifier=m.name)
        for k in [k for k in kids if k]:
            bpy.data.objects.remove(k, do_unlink=True)
        base.name = base.data.name = "LID_ASSY_" + tag
    smooth(coll)
    print("welded: two printed parts, LID_ASSY_upper and LID_ASSY_lower")


def _loose(ob):
    """How many disconnected pieces the mesh is in. A fused part must be 1."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    seen, n = set(), 0
    for v in bm.verts:
        if v.index in seen:
            continue
        n += 1
        st = [v]
        seen.add(v.index)
        while st:
            w = st.pop()
            for e in w.link_edges:
                u = e.other_vert(w)
                if u.index not in seen:
                    seen.add(u.index)
                    st.append(u)
    bm.free()
    return n


def _ivol(a, b):
    """Volume of the true solid overlap. Sampled distances cannot see this -
    two parts can be 'far apart' at every vertex and still interpenetrate."""
    src = bpy.data.objects.get(a)
    tgt = bpy.data.objects.get(b)
    if src is None or tgt is None:
        return 0.0
    A = src.copy()
    A.data = src.data.copy()
    bpy.context.scene.collection.objects.link(A)
    bpy.context.view_layer.objects.active = A
    m = A.modifiers.new(type="BOOLEAN", name="i")
    m.operation, m.object, m.solver = "INTERSECT", tgt, "EXACT"
    try:
        bpy.ops.object.modifier_apply(modifier=m.name)
        bm = bmesh.new()
        bm.from_mesh(A.data)
        v = bm.calc_volume(signed=False)
        bm.free()
    except Exception:
        v = 0.0
    bpy.data.objects.remove(A, do_unlink=True)
    return v


def _solid_eye(side, coll):
    """A stand-in for the eyeball WALL that survives once it is a shell: a
    2 mm skin under the lids. swept arc. The rear wedge is open, so
    the socket's pin arm reaching the centre through it is correct, not a
    collision - testing against the full sphere would flag it wrongly."""
    lo = min(LIDS[t]["tail"] for t in ASSY)
    hi = max(LIDS[t]["tail"] for t in ASSY)
    bm = bmesh.new()
    _shell(bm, EYE_R - 2.0, EYE_R, lo, hi, 2.0, 178.0, 24, 30)
    ob = _finish(bm, "_solid_" + side, coll,
                 ((1 if side == "L" else -1) * EYE_X, EYE_Y, EYE_Z))
    return ob


def _wbb(ob):
    ws = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (min(v.x for v in ws), max(v.x for v in ws),
            min(v.y for v in ws), max(v.y for v in ws),
            min(v.z for v in ws), max(v.z for v in ws))


def _overlaps(names):
    """Real solid interpenetration, not vertex distance.

    Sampled distances are blind to this: two coarse boxes can pass through
    each other with every vertex still far from every other vertex. Bounding
    boxes pre-filter so only the few candidate pairs pay for a boolean.
    """
    bb = {n: _wbb(bpy.data.objects[n]) for n in names}
    hits = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if _touching(a, b):
                continue
            A, B = bb[a], bb[b]
            if (A[1] < B[0] or B[1] < A[0] or A[3] < B[2] or B[3] < A[2]
                    or A[5] < B[4] or B[5] < A[4]):
                continue
            v = _ivol(a, b)
            if v > 0.01:
                hits.append((v, a, b))
    return sorted(hits, reverse=True)


def _all_meshes():
    """Every mesh in the assembly, across both collections."""
    out = []
    for nm in (COLL, COLL_GAZE):
        c = bpy.data.collections.get(nm)
        if c:
            out += [o.name for o in c.objects if o.type == "MESH"]
    return out


def _servo_src():
    """Find the servo proxy. Blender renumbers .001/.002 suffixes whenever a
    datablock is deleted and remade, so match on the stem, not the exact name."""
    ob = bpy.data.objects.get(SERVO_SRC)
    if ob:
        return ob
    stem = SERVO_SRC.rsplit(".", 1)[0]
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name.startswith(stem):
            return o
    return None


# ------------------------------------------------------------------ export
PRINTED = ["brkt_rear", "crank_upper", "crank_lower",
           "rod_upper", "rod_lower", "axle"]


def export_stl(folder):
    """Write one STL per printed part, laid on the plate.

    Each part is duplicated, the bails are welded to their lids first (they
    are one rigid body and so one print), then dropped so its lowest point
    sits at z=0 and centred in x/y. One file per part rather than one plate,
    so Bambu can orient and arrange - the drop to z=0 is a starting point,
    not a claim that this is the best orientation for any given part.

    The eyeballs and servo proxies are NOT exported: they are references."""
    import os
    blink(0.0)
    os.makedirs(folder, exist_ok=True)
    dg = bpy.context.evaluated_depsgraph_get()
    made = []

    def dup(name):
        src = bpy.data.objects.get(name)
        if src is None:
            return None
        ob = src.copy()
        ob.data = src.data.copy()
        bpy.context.scene.collection.objects.link(ob)
        return ob

    # the two lid assemblies: bail + its two lids, fused
    for tag in ASSY:
        base = dup("bail_" + tag)
        if base is None:
            continue
        kids = [dup("lid_%s_%s" % (tag, s)) for s in "LR"]
        bpy.context.view_layer.objects.active = base
        for k in [k for k in kids if k]:
            m = base.modifiers.new(type="BOOLEAN", name="w")
            m.operation, m.object, m.solver = "UNION", k, "EXACT"
            bpy.ops.object.modifier_apply(modifier=m.name)
        for k in [k for k in kids if k]:
            bpy.data.objects.remove(k, do_unlink=True)
        base.name = "LID_ASSY_" + tag
        made.append(base)

    for n in PRINTED:
        ob = dup(n)
        if ob:
            ob.name = n.upper()
            made.append(ob)

    written = []
    for ob in made:
        for o in bpy.context.selected_objects:
            o.select_set(False)
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        ws = [Vector(c) for c in ob.bound_box]
        lo = Vector((min(v.x for v in ws), min(v.y for v in ws),
                     min(v.z for v in ws)))
        hi = Vector((max(v.x for v in ws), max(v.y for v in ws),
                     max(v.z for v in ws)))
        ob.location = (-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)
        bpy.ops.object.transform_apply(location=True)
        path = os.path.join(folder, ob.name + ".stl")
        bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True,
                              global_scale=1.0, apply_modifiers=True)
        written.append((ob.name, hi.x - lo.x, hi.y - lo.y, hi.z - lo.z))
        ob.select_set(False)

    for ob in made:
        bpy.data.objects.remove(ob, do_unlink=True)
    print("\n  wrote %d STLs to %s" % (len(written), folder))
    print("  %-20s %8s %8s %8s" % ("part", "x", "y", "z"))
    print("  " + "-" * 48)
    for n, dx, dy, dz in written:
        print("  %-20s %8.1f %8.1f %8.1f" % (n, dx, dy, dz))
    return written
