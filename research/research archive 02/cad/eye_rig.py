"""The simplest rig that gives both eyeballs pan and tilt.

Four printed parts, and two pins per eye.  Nothing else.

    tilt   one frame carrying both eyes, hinged on the line through the two
           eye centres.  Because that line IS the eye axis, the frame turning
           and the eyeballs turning are the same motion - no linkage, and the
           fork sits exactly as far off the ball at 20 deg as it does at 0.
    pan    each ball on a vertical pin through its own centre, the two tied by
           one flat link.  The link only ever translates, so both eyes turn by
           the same angle: a parallelogram, no dead point.

The eyes are eye_L and eye_R already in the scene - r 12.0, at x +-31.5,
y 26.68.  This file does not build them and does not move their origins.

    import eye_rig; eye_rig.build(); eye_rig.look(pan=15, tilt=-10)

No servos yet, on purpose.  Get the joint right, then drive it.
"""
import math
import bpy
import bmesh
from mathutils import Vector, Matrix

COLL = "EYE_RIG"

EYE_R = 12.0
EYE_X, EYE_Y, EYE_Z = 31.5, 26.68, 0.0

# The eye is its own printed part and it drops on from above.  There is no
# arm over the top of the ball, so the whole top is free for lids later, and
# a ball with a pin already through it - which could never have been threaded
# into a fork 26 mm wide - is not a thing that has to happen.
#
# The pole ends in a cross.  A round press fit in printed plastic creeps and
# then slips; a cross takes the torque on four flanks and cannot.  The collar
# under it sets the height, and the matching flat on the ball is also the only
# decent first layer a sphere is ever going to get.
PIN_D, BORE_D = 6.0, 6.2        # the pole, and the fork bore it turns in
PIN_Z = -28.5                   # pole starts at the bottom of the lever
COLLAR_D, COLLAR_Z = 10.0, (-13.0, -11.0)   # cone, so it prints without support
CROSS_T, CROSS_W = 2.4, 6.0
CROSS_Z = (-11.0, -3.2)         # 7.8 mm up inside a ball that ends at -12
SOCK_CL = 0.2                   # slip fit of cross in socket
PUPIL_D, PUPIL_DEEP = 6.0, 2.0  # a dish at the front, to pour gloss black into

FORK_Z, FORK_T, FORK_W = 13.5, 8.0, 16.0    # ONE arm now, and 8 mm of bore:
FORK_Y = (22.0, 46.0)                       # it is the only bearing there is

WEB_Y = (43.0, 46.0)            # spine, behind balls that end at y 38.68
BAR_X, BAR_Z = 36.0, 5.0
# The tilt webs are widened to 5.5 and dropped to the shelf's height, which
# makes them the thing the shelf screws INTO: 19 mm of material front to back,
# 5.5 mm across, so an M2 goes straight in level with 2 mm of wall each side.
# 0.5 clear of the pillar at |x| 5 and of the tilt rod at |x| 11.5.
TILT_X = (5.5, 11.0)
SHAFT_D, SHAFT_X = 5.0, 18.0    # shaft runs out to 18 to carry the tilt lever

LEV_R = 5.32                    # lever reaches FORWARD, past the pillar
# The lever is the FLOOR of this part, and both its pins point UP.  With the
# link hung underneath instead, the only thing the pole could stand on to
# print was two 2.5 mm pins of unequal length - it would not even sit level.
# Everything now rises off one flat face and it prints upright, unsupported.
# The stack sits 1 mm higher than it wants to, because at pan +25 / tilt +20
# the RIGHT lever swings back and down across SV_tilt's top face at z -29.9.
LEV_Z = (-28.5, -25.5)
LNK_Z = (-25.0, -22.0)          # the link rides ON TOP of the lever now
PIN_TOP = -22.0                 # both pins end here, 0.5 under the fork boss
LNK_PIN_D = 2.5
# The pan drive arm reaches further back than the link arm reaches forward.
# It has to: the rod now runs at the pole's own height, and a 8 mm eye on a
# 5.32 mm arm would swing straight through the Ø6 pole.  9 mm clears it by 2,
# and the longer arm asks MORE of the servo's travel, which is free accuracy.
PAN_LEV_R = 9.0
TAIL_X = (5.5, 11.0)            # the tail is a fork: the pillar passes between

# The pillar is an L, not a post.  The link is a full-width bar at a fixed
# height, so it sweeps a 19 mm band of y as the frame tilts and NOTHING fixed
# can stand in that band: a post there gets sawn in half by its own clearance
# slot.  So the leg stands behind the sweep (which tops out at y 31.4) and the
# arm reaches forward over it, at the height of the axis, to the bore.
# The leg threads a 6 mm gap: the link sweeps up to y 33.3 in front of it, and
# the shelf's own corner swings back to y 39.5 behind it.  So it is thin where
# things pass, and gets its foot back lower down where nothing does.
PIL_X, PIL_Y, PIL_Z = 5.0, (34.5, 38.5), (-42.0, 5.0)
PIL_FOOT_Y, PIL_FOOT_Z = (28.0, 38.5), (-42.0, -30.0)   # forward: the pan rod
                                                        # swings through behind
ARM_Y, ARM_Z = (21.0, 38.5), (-5.0, 5.0)
DECK_X, DECK_Y, DECK_Z = 45.0, (18.0, 60.0), (-46.0, -42.0)

# --- servos ------------------------------------------------------------
# An MG90S is 32.2 x 12.1 x 27.2 over its ears.  Nothing that size fits
# between two balls 63 mm apart, so neither servo goes inside the frame.
#
# The PAN servo rides the frame, on a tail behind the eyes.  It has to: a pan
# drive anchored to the base would read every degree of tilt as pan, because
# the link it pushes swings with the frame.  Paying for that in structure is
# cheaper than paying for it in a software fudge that drifts.
# The TILT servo sits on the deck underneath, which is why the deck dropped to
# z -42 - a servo lying flat is 12.1 mm and the link swings down to z -23.
SERVO_SRC = "PROXY_servo_pan.001"
SV_PAN = dict(p=(0.0, 55.0, -16.72), shaft=(0, 0, -1), body=(1, 0, 0))
SV_TILT = dict(p=(-19.78, 34.0, -35.95), shaft=(1, 0, 0), body=(0, 1, 0))
# The servo cradle is its OWN part, bolted on.  Left in the frame it hung off
# the back at a different height and facing a different way, so there was no
# face to lay the frame on.  Taken off, the frame's whole back is one plane.
# -11 at the inboard end is where the tilt rod swings past; 25 at the other is
# 0.5 clear of the spine web.
SHELF_X, SHELF_Y = (-11.0, 25.0), (46.0, 64.0)
# The posts stand UP to the height of the tilt webs and the screws go in
# level, which is the whole point: a screw driven up from underneath needs a
# hole and a counterbore through the plate's bottom face, and that face is
# the one the part prints on.  Level screws leave it untouched.
POST_Y, POST_TOP = (46.0, 48.5), 3.5
MNT_X, MNT_Z = 8.25, 0.0
# The plate stops at y 46 and nothing reaches past it.  The posts straddle
# the pillar at |x| 5.5..11 so they clear it, but the plate is 36 wide and
# does not: running it forward to 43 put 48 mm3 through the leg at full
# down-look.

# The MG90S itself, measured off the proxy.  The ears are always normal to the
# output shaft, so the pan servo (shaft down) bolts down through horizontal
# ears, and the tilt servo (shaft sideways) bolts sideways through vertical
# ones.  That is not a choice, it is what the servo is.
SV_BODY_X, SV_BODY_Y = (-6.324, 16.976), 6.05   # case, incl. the shaft flange
SV_EAR_Z = (-7.67, -5.17)                       # the ear slab, 2.5 thick
SV_HOLE_X = (-8.274, 19.726)                    # 28.0 apart, the SG90 standard
SV_SCREW_D = 1.7                # pilot for the M2 self-tapper it ships with
SV_FIT = 0.4                    # slip fit round the case
MNT_T = 4.0                     # meat under a screw - 2.5 mm of ear is not it

# --- the linkage, all of it printed --------------------------------------
# No music wire and no ball links, because there are none in the drawer.  A
# pushrod here is a flat bar with a snapped-on eye at each end: it prints on
# its side, so the layers run along the load, and it clips over a plain
# printed pin.  The two mouths face OPPOSITE ways, so no single sideways
# shove can pop both ends off at once.
#
# Measured off the MG90S proxy: the case face and the boss it wears.
SHAFT_OFF, CASE_FACE, SHAFT_TIP = -0.274, 0.28, 4.78

PIN_L_D = 3.0                   # every linkage pin, same as the pan pins
ROD_T, ROD_W = 3.0, 6.0
ROD_EYE_D, ROD_BORE = 8.0, 3.3          # 0.3 loose on the pin: it must swivel
ROD_MOUTH = 2.75                        # 0.25 under the pin: THE number to
                                        # tune on the printer.  Too tight and
                                        # the C cracks; too loose and it walks.
HORN_T, HORN_GAP = 3.5, 0.2
HORN_HUB_D, HORN_ARM_W = 9.0, 7.0
HORN_BORE = 4.95                # MEASURED, not guessed.  4.7 had to be forced
                                # and 5.2 dropped on and spun, so a ladder of
                                # 4.75/4.85/4.95/5.05 pucks went onto a real
                                # spline: 4.95 is the one that fits.  It is
                                # printer-specific - reprint the ladder before
                                # trusting it on a different machine.

TILT_CRANK = 8.0                # equal cranks -> a parallelogram, so the tilt
PAN_CRANK = 5.0                 # servo angle IS the tilt angle, exactly
TILT_ROD_X = -13.0              # rod plane: 0.5 clear of the web at x -11
TILT_LEV_X = (-18.0, -15.0)     # the lever web, outboard of both tilt webs
TILT_PIN_X = (-15.0, -11.0)
TILT_HORN_PIN, PAN_HORN_PIN = 5.5, 6.0
PAN_ROD_Z = -23.5               # rod rides over the lever, beside the link
NOTCH_X, NOTCH_Y = (-20.0, -10.0), (38.0, 50.0)   # deck, under the tilt horn

# --- eyelid bearings -----------------------------------------------------
# The lids pivot on the eye centreline, which inside |x| 19.5..43.5 is buried
# in a ball.  So the pin lives OUTBOARD of each eye, on an arm off the spine,
# and the lid is a plain bore that drops onto it.
LID_BRK_X = (50.5, 53.5)
LID_PIN_D, LID_PIN_X = 5.0, (43.6, 53.5)
LID_ARM_Z = 4.0

PAN_LIMIT, TILT_LIMIT = 25.0, 20.0
SMOOTH_ANGLE = 35.0


# ----------------------------------------------------------------- shapes
def _box(bm, x0, x1, y0, y1, z0, z1):
    v = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    bmesh.ops.scale(bm, verts=v, vec=(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)))
    bmesh.ops.translate(bm, verts=v,
                        vec=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))


def _rodx(bm, r, x0, x1, cy, cz, segs=24):
    v = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                              radius1=r, radius2=r, depth=abs(x1 - x0))["verts"]
    bmesh.ops.rotate(bm, verts=v, cent=(0, 0, 0),
                     matrix=Matrix.Rotation(math.radians(90), 3, "Y"))
    bmesh.ops.translate(bm, verts=v, vec=Vector(((x0 + x1) / 2, cy, cz)))


def _rody(bm, r, y0, y1, cx, cz, segs=24):
    v = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                              radius1=r, radius2=r, depth=abs(y1 - y0))["verts"]
    bmesh.ops.rotate(bm, verts=v, cent=(0, 0, 0),
                     matrix=Matrix.Rotation(math.radians(-90), 3, "X"))
    bmesh.ops.translate(bm, verts=v, vec=Vector((cx, (y0 + y1) / 2, cz)))


def _rodz(bm, r, z0, z1, cx, cy, segs=24):
    v = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                              radius1=r, radius2=r, depth=abs(z1 - z0))["verts"]
    bmesh.ops.translate(bm, verts=v, vec=Vector((cx, cy, (z0 + z1) / 2)))


def _conez(bm, r0, r1, z0, z1, cx, cy, segs=24):
    v = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                              radius1=r0, radius2=r1, depth=abs(z1 - z0))["verts"]
    bmesh.ops.translate(bm, verts=v, vec=Vector((cx, cy, (z0 + z1) / 2)))


def _frame_m(shaft, body):
    """Orientation matrix: local z onto `shaft`, local x onto `body`.  The
    proxy is drawn with z as its output shaft and x along its case."""
    z = Vector(shaft).normalized()
    x = Vector(body).normalized()
    x = (x - z * x.dot(z)).normalized()
    return Matrix((x, z.cross(x), z)).transposed().to_4x4()


def _place(origin, ex, ez):
    """Put a part down: local x onto `ex`, local z onto `ez`, origin at `origin`."""
    ez = Vector(ez).normalized()
    ex = Vector(ex)
    ex = (ex - ez * ex.dot(ez)).normalized()
    m = Matrix((ex, ez.cross(ex), ez)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


def _servo_axis(d):
    """Where the output shaft comes out: the seat face, and which way it points.
    The horn goes on the boss between the case face and the shaft tip."""
    m = _frame_m(d["shaft"], d["body"])
    ax = (m @ Vector((0.0, 0.0, 1.0))).normalized()
    seat = Vector(d["p"]) + (m @ Vector((SHAFT_OFF, 0.0, 0.0))) + ax * CASE_FACE
    return seat, ax


PAN_SEAT, PAN_AX = _servo_axis(SV_PAN)
TILT_SEAT, TILT_AX = _servo_axis(SV_TILT)


def _sv_pt(d, lx, ly, lz):
    """A point on the servo, given in the servo's own coordinates."""
    return Vector(d["p"]) + (_frame_m(d["shaft"], d["body"])
                             @ Vector((lx, ly, lz)))


def _sv_bounds(d, lx, ly, lz):
    """World axis-aligned box round a box given in servo coordinates."""
    pts = [_sv_pt(d, a, b, c) for a in lx for b in ly for c in lz]
    return [(min(q[i] for q in pts), max(q[i] for q in pts)) for i in range(3)]


# --- pan cradle: the ears land on top, the case drops through -------------
_PB = _sv_bounds(SV_PAN, SV_BODY_X, (-SV_BODY_Y, SV_BODY_Y), SV_EAR_Z)
SHELF_Z = (_PB[2][0] - MNT_T, _PB[2][0])        # ear plane sits ON the shelf
PAN_POCKET = ((_PB[0][0] - SV_FIT, _PB[0][1] + SV_FIT),
              (_PB[1][0] - SV_FIT, _PB[1][1] + SV_FIT))
PAN_HOLES = [_sv_pt(SV_PAN, hx, 0.0, sum(SV_EAR_Z) / 2) for hx in SV_HOLE_X]

# --- tilt cradle: two posts off the deck, the ears bolt to their faces -----
_TE = _sv_bounds(SV_TILT, (0.0,), (0.0,), (SV_EAR_Z[1],))       # ear inner face
TILT_MNT_X = (_TE[0][0], _TE[0][0] + MNT_T)
_TB = _sv_bounds(SV_TILT, SV_BODY_X, (-SV_BODY_Y, SV_BODY_Y),
                 (SV_EAR_Z[0],))
_TA = _sv_bounds(SV_TILT, (SV_HOLE_X[0] - 2.1, SV_HOLE_X[1] + 2.1),
                 (0.0,), (0.0,))
TILT_POSTS = [(_TA[1][0] - 4.0, _TB[1][0]), (_TB[1][1], _TA[1][1] + 3.0)]
TILT_HOLES = [_sv_pt(SV_TILT, hx, 0.0, sum(SV_EAR_Z) / 2) for hx in SV_HOLE_X]
# only tall enough to hold its screw - the pan link's arc dips to z -29.3
TILT_MNT_Z = TILT_HOLES[0].z + 4.0

# Tilt is a parallelogram: rod = the distance between the two pivots, forever.
TILT_ROD_L = math.hypot(TILT_SEAT.y - EYE_Y, TILT_SEAT.z - EYE_Z)

# Pan is a slider-crank onto a rearward lever on the left eye.  Set the crank
# perpendicular to the rod at neutral - that is as far from a dead point as it
# gets, and it is the only reason a 5 mm crank can move anything.
_PAN_S = Vector((PAN_SEAT.x, PAN_SEAT.y))
_PAN_V0 = Vector((EYE_X, EYE_Y + PAN_LEV_R)) - _PAN_S
_PAN_U0 = Vector((-_PAN_V0.y, _PAN_V0.x)).normalized()
PAN_ROD_L = (_PAN_V0 - _PAN_U0 * PAN_CRANK).length


def _pan_crank(p):
    """(lever pin, crank pin) for eye pan `p` in radians.  Two circles: the
    crank's, and the rod's swung off the lever pin.  Take the same root every
    time or the horn flips through the servo."""
    pin = Vector((EYE_X - PAN_LEV_R * math.sin(p),
                  EYE_Y + PAN_LEV_R * math.cos(p)))
    v = pin - _PAN_S
    d = v.length
    a = (PAN_CRANK ** 2 - PAN_ROD_L ** 2 + d * d) / (2.0 * d)
    h = math.sqrt(max(0.0, PAN_CRANK ** 2 - a * a))
    u = v / d
    return pin, _PAN_S + u * a + Vector((-u.y, u.x)) * h


def _obj(name, coll, parts, cuts=(), loc=(0, 0, 0)):
    """Union every part, subtract every cut, apply the lot, one mesh out."""
    obs = []
    for i, fn in enumerate(list(parts) + list(cuts)):
        bm = bmesh.new()
        fn(bm)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new("%s_f%02d" % (name, i))
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(me.name, me)
        coll.objects.link(o)
        obs.append(o)
    base = obs[0]
    bpy.context.view_layer.objects.active = base
    for i, o in enumerate(obs[1:], start=1):
        m = base.modifiers.new(type="BOOLEAN", name="b%02d" % i)
        m.object, m.solver = o, "EXACT"
        m.operation = "UNION" if i < len(parts) else "DIFFERENCE"
    for m in list(base.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    for o in obs[1:]:
        bpy.data.objects.remove(o, do_unlink=True)
    base.name = base.data.name = name
    piv = Vector(loc)
    for v in base.data.vertices:
        v.co -= piv
    base.location = piv
    return base


# ------------------------------------------------------------------ parts
def _base(coll):
    """Pillar and deck.  The pillar is the only fixed thing between the balls,
    and it is 10 mm wide in a corridor that is 39 mm wide."""
    parts = [
        lambda bm: _box(bm, -PIL_X, PIL_X, PIL_Y[0], PIL_Y[1],
                        PIL_Z[0], PIL_Z[1]),
        lambda bm: _box(bm, -PIL_X, PIL_X, ARM_Y[0], ARM_Y[1],
                        ARM_Z[0], ARM_Z[1]),
        lambda bm: _box(bm, -PIL_X, PIL_X, PIL_FOOT_Y[0], PIL_FOOT_Y[1],
                        PIL_FOOT_Z[0], PIL_FOOT_Z[1]),
        lambda bm: _box(bm, -DECK_X, DECK_X, DECK_Y[0], DECK_Y[1],
                        DECK_Z[0], DECK_Z[1]),
    ]
    # The tilt cradle.  This servo lies on its side, so its ears stand up and
    # the screws go in sideways: two posts off the deck, one at each end of
    # the case, and the servo slides in from the outside of the head until its
    # ears touch them.  Nothing is in the way of a driver from that side.
    for y0, y1 in TILT_POSTS:
        parts.append(lambda bm, a=y0, b=y1: _box(
            bm, TILT_MNT_X[0], TILT_MNT_X[1], a, b, DECK_Z[1], TILT_MNT_Z))
    cuts = [lambda bm: _rodx(bm, (SHAFT_D + 0.2) / 2, -PIL_X - 1, PIL_X + 1,
                             EYE_Y, EYE_Z),
            # the tilt horn swings below the deck at full down-look
            lambda bm: _box(bm, NOTCH_X[0], NOTCH_X[1], NOTCH_Y[0], NOTCH_Y[1],
                            DECK_Z[0] - 1, DECK_Z[1] + 1)]
    for h in TILT_HOLES:
        cuts.append(lambda bm, q=h: _rodx(bm, SV_SCREW_D / 2,
                                          TILT_MNT_X[0] - 1, TILT_MNT_X[1] + 1,
                                          q.y, q.z))
    return _obj("RIG_base", coll, parts, cuts)


def _frame(coll):
    """One part: two forks, a spine, and the tilt shaft they hang on."""
    parts = []
    for sx in (1, -1):
        x0, x1 = sx * EYE_X - FORK_W / 2, sx * EYE_X + FORK_W / 2
        parts.append(lambda bm, a=x0, b=x1: _box(
            bm, a, b, FORK_Y[0], FORK_Y[1], -(FORK_Z + FORK_T), -FORK_Z))
        # The spine only has to carry the fork arm back to the crossbar. It
        # used to run to +21.5 to meet an upper fork arm that no longer
        # exists, so 16 mm of it was holding nothing up.
        parts.append(lambda bm, a=x0, b=x1: _box(
            bm, a, b, WEB_Y[0], WEB_Y[1], -(FORK_Z + FORK_T), BAR_Z))
        parts.append(lambda bm, s=sx: _box(
            bm, s * TILT_X[0], s * TILT_X[1], EYE_Y, WEB_Y[1],
            -SHAFT_D / 2 - 0.5, SHAFT_D / 2 + 0.5))
    parts.append(lambda bm: _box(bm, -BAR_X, BAR_X, WEB_Y[0], WEB_Y[1],
                                 -BAR_Z, BAR_Z))
    # the eyelid bearings: a rail out along the spine, an arm forward to the
    # centreline, and the pin the lid's hub turns on
    for sx in (1, -1):
        rail = sorted((sx * (EYE_X + FORK_W / 2), sx * LID_BRK_X[1]))
        arm = sorted((sx * LID_BRK_X[0], sx * LID_BRK_X[1]))
        pin = sorted((sx * LID_PIN_X[0], sx * LID_PIN_X[1]))
        parts.append(lambda bm, a=rail: _box(bm, a[0], a[1], WEB_Y[0],
                                             WEB_Y[1], -BAR_Z, BAR_Z))
        parts.append(lambda bm, a=arm: _box(bm, a[0], a[1], EYE_Y, WEB_Y[1],
                                            -LID_ARM_Z, LID_ARM_Z))
        parts.append(lambda bm, a=pin: _rodx(bm, LID_PIN_D / 2, a[0], a[1],
                                             EYE_Y, EYE_Z))
    parts.append(lambda bm: _rodx(bm, SHAFT_D / 2, -SHAFT_X, SHAFT_X,
                                  EYE_Y, EYE_Z))
    # no tail and no shelf: RIG_shelf carries the pan servo and bolts on
    # the tilt lever - just a third web, further out, tying the shaft to the
    # spine.  No cantilever: the pin it carries is in the middle of a gusset.
    parts.append(lambda bm: _box(bm, TILT_LEV_X[0], TILT_LEV_X[1],
                                 EYE_Y, WEB_Y[1], -3.5, 3.5))
    parts.append(lambda bm: _rodx(bm, PIN_L_D / 2, TILT_PIN_X[0], TILT_PIN_X[1],
                                  EYE_Y + TILT_CRANK, EYE_Z))
    cuts = [lambda bm, s=sx: _rodz(bm, BORE_D / 2, -(FORK_Z + FORK_T + 1),
                                   FORK_Z + FORK_T + 1, s * EYE_X, EYE_Y)
            for sx in (1, -1)]
    # two pilots straight in through the back, into the tilt webs
    for s in (1, -1):
        cuts.append(lambda bm, t=s: _rody(bm, SV_SCREW_D / 2, WEB_Y[1] - 9.0,
                                          WEB_Y[1] + 1.0, t * MNT_X, MNT_Z))
    return _obj("RIG_frame", coll, parts, cuts, loc=(0.0, EYE_Y, EYE_Z))


def _pins(side, sx, coll):
    """Top and bottom pin plus the pan lever - what the printed ball carries.
    Kept off eye_L / eye_R so the balls themselves stay untouched.

    The LEFT eye gets a second arm out the back.  That is where the pan servo
    pushes: the link ties the right eye to it, so one servo drives both."""
    cx = sx * EYE_X
    # No forward extension.  It looked like free bed area, but at positive
    # tilt the front of the lever swings DOWN and BACK, and on the right that
    # walks it straight into SV_tilt's top face.  The left lever gets its area
    # from the pan drive arm instead, which reaches back over open deck.
    front = EYE_Y - LEV_R - 2.0
    back = EYE_Y + PAN_LEV_R + 2.0 if side == "L" else EYE_Y + 3.0
    parts = [
        lambda bm: _rodz(bm, PIN_D / 2, PIN_Z, COLLAR_Z[0], cx, EYE_Y),
        lambda bm: _conez(bm, PIN_D / 2, COLLAR_D / 2,
                          COLLAR_Z[0], COLLAR_Z[1], cx, EYE_Y),
        lambda bm: _box(bm, cx - CROSS_W / 2, cx + CROSS_W / 2,
                        EYE_Y - CROSS_T / 2, EYE_Y + CROSS_T / 2,
                        CROSS_Z[0], CROSS_Z[1]),
        lambda bm: _box(bm, cx - CROSS_T / 2, cx + CROSS_T / 2,
                        EYE_Y - CROSS_W / 2, EYE_Y + CROSS_W / 2,
                        CROSS_Z[0], CROSS_Z[1]),
        lambda bm: _box(bm, cx - 2.5, cx + 2.5, front, back,
                        LEV_Z[0], LEV_Z[1]),
        lambda bm: _rodz(bm, LNK_PIN_D / 2, LEV_Z[1], PIN_TOP,
                         cx, EYE_Y - LEV_R),
    ]
    if side == "L":
        parts.append(lambda bm: _rodz(bm, PIN_L_D / 2, LEV_Z[1], PIN_TOP,
                                      cx, EYE_Y + PAN_LEV_R))
    return _obj("RIG_pins_" + side, coll, parts, loc=(cx, EYE_Y, EYE_Z))


def _socket(side, sx, coll):
    """The cutter that turns a plain sphere into a swappable printable eye:
    a flat off the bottom, the cross socket the pole lands in, and the pupil
    dish.  Applied, not left live - see _cut_eye."""
    cx = sx * EYE_X
    t, w = (CROSS_T + SOCK_CL) / 2, (CROSS_W + SOCK_CL) / 2
    top = CROSS_Z[1] + 0.3          # bottom out on the collar, not the tip
    parts = [
        lambda bm: _box(bm, cx - 14, cx + 14, EYE_Y - 14, EYE_Y + 14,
                        -EYE_R - 3, COLLAR_Z[1]),
        lambda bm: _box(bm, cx - w, cx + w, EYE_Y - t, EYE_Y + t,
                        COLLAR_Z[1] - 0.5, top),
        lambda bm: _box(bm, cx - t, cx + t, EYE_Y - w, EYE_Y + w,
                        COLLAR_Z[1] - 0.5, top),
        lambda bm: _rody(bm, PUPIL_D / 2, EYE_Y - EYE_R - 1.0,
                         EYE_Y - EYE_R + PUPIL_DEEP, cx, EYE_Z),
    ]
    return _obj("RIG_socket_" + side, coll, parts, loc=(cx, EYE_Y, EYE_Z))


def _cut_eye(side, sx, coll):
    """Cut the eye for real, and put it back where it belongs first.

    Not a live modifier.  A hidden cutter is dropped from the depsgraph, so a
    boolean pointed at one silently does nothing - which is exactly what
    happened, and the socket never appeared.  Applied geometry cannot lie.

    The sphere you started with is kept as eye_<side>_uncut with a fake user,
    so this is reversible: assign that mesh back and the ball is unmarked."""
    eye = bpy.data.objects.get("eye_" + side)
    if eye is None:
        print("  *** eye_%s is missing - nothing to cut" % side)
        return None
    # Homing matters.  build() used to leave the eye wherever it had been
    # dragged, and then every check that involved it was measuring thin air.
    for m in list(eye.modifiers):       # any cutter from an earlier build
        if m.type == "BOOLEAN":
            eye.modifiers.remove(m)
    eye.parent = None
    eye.location = (sx * EYE_X, EYE_Y, EYE_Z)
    eye.rotation_euler = (0.0, 0.0, 0.0)
    eye.scale = (1.0, 1.0, 1.0)

    keep = bpy.data.meshes.get("eye_%s_uncut" % side)
    if keep is None:
        keep = eye.data.copy()
        keep.name = "eye_%s_uncut" % side
        keep.use_fake_user = True
    eye.data = keep.copy()
    eye.data.name = "eye_%s_cut" % side

    cutter = _socket(side, sx, coll)
    bpy.context.view_layer.objects.active = eye
    m = eye.modifiers.new(type="BOOLEAN", name="socket")
    m.object, m.solver, m.operation = cutter, "EXACT", "DIFFERENCE"
    bpy.ops.object.modifier_move_to_index(modifier=m.name, index=0)
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    return eye


def _link(coll):
    """One flat bar.  It translates and never turns, so both eyes get the same
    angle - and it is the one part here that is trivially printable."""
    y = EYE_Y - LEV_R
    parts = [lambda bm: _box(bm, -(EYE_X + 3), EYE_X + 3, y - 1.5, y + 1.5,
                             LNK_Z[0], LNK_Z[1])]
    cuts = [lambda bm, s=sx: _rodz(bm, (LNK_PIN_D + 0.2) / 2,
                                   LNK_Z[0] - 1, LNK_Z[1] + 1, s * EYE_X, y)
            for sx in (1, -1)]
    return _obj("RIG_link", coll, parts, cuts, loc=(0.0, y, LNK_Z[0]))


def _shelf(coll):
    """The pan servo's cradle, on its own.

    One flat plate with two posts standing off it, so it prints face down
    with no overhang anywhere.  The posts stop under the frame's crossbar and
    take a screw up into 7 mm of it - up, not sideways, because everything on
    the back of the frame is 3 mm thick and 3 mm of PLA is not a thread."""
    parts = [
        lambda bm: _box(bm, SHELF_X[0], SHELF_X[1], SHELF_Y[0], SHELF_Y[1],
                        SHELF_Z[0], SHELF_Z[1]),
    ]
    for s in (1, -1):
        parts.append(lambda bm, t=s: _box(
            bm, t * TAIL_X[0], t * TAIL_X[1], POST_Y[0], POST_Y[1],
            SHELF_Z[1], POST_TOP))
    # the case drops through a slot open at the BACK, so the servo slides in
    # from behind; its ears land on the rails either side and take a screw
    cuts = [lambda bm: _box(bm, PAN_POCKET[0][0], PAN_POCKET[0][1],
                            PAN_POCKET[1][0], SHELF_Y[1] + 1.0,
                            SHELF_Z[0] - 1, SHELF_Z[1] + 1)]
    for h in PAN_HOLES:
        cuts.append(lambda bm, q=h: _rodz(bm, SV_SCREW_D / 2,
                                          SHELF_Z[0] - 1, SHELF_Z[1] + 1,
                                          q.x, q.y))
    for s in (1, -1):
        cuts.append(lambda bm, t=s: _rody(bm, (SV_SCREW_D + 0.5) / 2,
                                          POST_Y[0] - 1.0, POST_Y[1] + 1.0,
                                          t * MNT_X, MNT_Z))
    return _obj("RIG_shelf", coll, parts, cuts,
                loc=(0.0, SHELF_Y[0], SHELF_Z[0]))


def _horn(name, coll, crank, pin_out):
    """A printed servo horn.  Built at the origin: hub on local z, crank along
    local x, drive pin out the far face.  Prints hub-down, no support - the
    only overhang is the pin's own root, which is a 3 mm circle on a flat.

    The bore is UNDER the spline on purpose.  Push it on with the servo screw
    and the 21 teeth cut their own splines in the plastic."""
    parts = [
        lambda bm: _rodz(bm, HORN_HUB_D / 2, 0.0, HORN_T, 0.0, 0.0),
        lambda bm: _box(bm, 0.0, crank, -HORN_ARM_W / 2, HORN_ARM_W / 2,
                        0.0, HORN_T),
        lambda bm: _rodz(bm, HORN_ARM_W / 2, 0.0, HORN_T, crank, 0.0),
        lambda bm: _rodz(bm, PIN_L_D / 2, HORN_T, HORN_T + pin_out, crank, 0.0),
    ]
    cuts = [lambda bm: _rodz(bm, HORN_BORE / 2, -1.0, HORN_T + 1.0, 0.0, 0.0)]
    return _obj(name, coll, parts, cuts)


def _rod(name, coll, length):
    """A printed pushrod: flat bar, a snap eye at each end, mouths opposed.

    It lies on the bed, so every layer line runs down the length of the bar -
    the direction it is loaded.  Stood upright it would be one layer joint in
    tension, which is how printed rods snap."""
    e = ROD_EYE_D / 2
    parts = [
        lambda bm: _box(bm, 0.0, length, -ROD_W / 2, ROD_W / 2,
                        -ROD_T / 2, ROD_T / 2),
        lambda bm: _rodz(bm, e, -ROD_T / 2, ROD_T / 2, 0.0, 0.0),
        lambda bm: _rodz(bm, e, -ROD_T / 2, ROD_T / 2, length, 0.0),
    ]
    cuts = [
        lambda bm: _rodz(bm, ROD_BORE / 2, -ROD_T, ROD_T, 0.0, 0.0),
        lambda bm: _rodz(bm, ROD_BORE / 2, -ROD_T, ROD_T, length, 0.0),
        lambda bm: _box(bm, -ROD_MOUTH / 2, ROD_MOUTH / 2,
                        0.0, e + 1.0, -ROD_T, ROD_T),
        lambda bm: _box(bm, length - ROD_MOUTH / 2, length + ROD_MOUTH / 2,
                        -(e + 1.0), 0.0, -ROD_T, ROD_T),
    ]
    return _obj(name, coll, parts, cuts)


def _servos(coll, frame):
    """Place the two proxies. Nothing is driven yet - this is where they go,
    not how they connect."""
    src = bpy.data.objects.get(SERVO_SRC)
    if src is None:
        print("  *** %s is missing - servos NOT placed, so every clearance"
              % SERVO_SRC)
        print("      against a servo is going unchecked")
        return []
    out = []
    for name, d, par in (("SV_pan", SV_PAN, frame), ("SV_tilt", SV_TILT, None)):
        ob = bpy.data.objects.new(name, src.data)
        coll.objects.link(ob)
        ob.matrix_world = (Matrix.Translation(Vector(d["p"]))
                           @ _frame_m(d["shaft"], d["body"]))
        if par is not None:
            ob.parent = par
            ob.matrix_parent_inverse = par.matrix_world.inverted()
        out.append(ob)
    return out


# ------------------------------------------------------------------ build
def build():
    for ob in list(bpy.data.objects):
        if ob.name.startswith(("RIG_", "SV_")):
            bpy.data.objects.remove(ob, do_unlink=True)
    old = bpy.data.collections.get(COLL)
    if old:
        bpy.data.collections.remove(old)
    coll = bpy.data.collections.new(COLL)
    bpy.context.scene.collection.children.link(coll)

    _base(coll)
    frame = _frame(coll)
    shelf = _shelf(coll)
    link = _link(coll)
    for s, sx in (("L", 1), ("R", -1)):
        _cut_eye(s, sx, coll)
    pins = {s: _pins(s, sx, coll) for s, sx in (("L", 1), ("R", -1))}

    _horn("RIG_horn_tilt", coll, TILT_CRANK, TILT_HORN_PIN)
    _rod("RIG_rod_tilt", coll, TILT_ROD_L)
    horn_p = _horn("RIG_horn_pan", coll, PAN_CRANK, PAN_HORN_PIN)
    rod_p = _rod("RIG_rod_pan", coll, PAN_ROD_L)

    _servos(coll, shelf)
    # the pan drive rides the frame; the tilt drive stands on the base
    for ob in (link, shelf, horn_p, rod_p):
        ob.parent = frame
        ob.matrix_parent_inverse = frame.matrix_world.inverted()
    for s in "LR":
        eye = bpy.data.objects.get("eye_" + s)
        if eye is None:
            print("  *** eye_%s is missing - the rig is built around nothing" % s)
            continue
        eye.parent = frame
        eye.matrix_parent_inverse = frame.matrix_world.inverted()
        pins[s].parent = eye
        pins[s].matrix_parent_inverse = eye.matrix_world.inverted()

    smooth(coll)
    look(0.0, 0.0)
    print("built %d parts in %s: %s"
          % (len(coll.objects), COLL, ", ".join(o.name for o in coll.objects)))
    return check()


PRINTED = ("RIG_base", "RIG_frame", "RIG_shelf", "RIG_link",
           "RIG_pins_L", "RIG_pins_R",
           "RIG_horn_tilt", "RIG_horn_pan", "RIG_rod_tilt", "RIG_rod_pan",
           "eye_L", "eye_R")


UPRIGHT = ("RIG_pins_L", "RIG_pins_R")   # a bearing pole must print ROUND


def _boxed():
    """The 24 axis-aligned orientations, so a part can be laid on any face."""
    seen, out = set(), []
    for i in range(4):
        for j in range(4):
            for k in range(4):
                m = (Matrix.Rotation(math.radians(90 * i), 3, "X")
                     @ Matrix.Rotation(math.radians(90 * j), 3, "Y")
                     @ Matrix.Rotation(math.radians(90 * k), 3, "Z"))
                key = tuple(round(c, 3) + 0.0 for r in m for c in r)
                if key not in seen:
                    seen.add(key)
                    out.append(m.to_4x4())
    return out


def _bed(me, m):
    """How much of this part would actually be stuck to the bed, laid like m.

    Via bmesh, because a boolean leaves big concave n-gons and fanning one of
    those from a single corner counts the overlaps twice - it read the frame's
    back as 2410 mm2 when it is 1537, which is enough to pick a worse face."""
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(m)
    lo = min(v.co.z for v in bm.verts)
    a = sum(f.calc_area() for f in bm.faces
            if all(v.co.z - lo < 0.2 for v in f.verts))
    bm.free()
    return a


PLATE_COLL = "TEST_PRINTS"


def test_prints(folder=None, bed=220.0, gap=6.0, at=(70.0, 95.0), parts=None):
    """Lay every printed part out on a bed, in the orientation it should be
    printed in, and optionally write the STLs.

    The layout in the scene and the files are the same geometry - they are
    generated from the same objects, so what you inspect is what you print."""
    import os
    old = bpy.data.collections.get(PLATE_COLL)
    if old:
        for ob in list(old.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(old)
    coll = bpy.data.collections.new(PLATE_COLL)
    bpy.context.scene.collection.children.link(coll)

    bm = bmesh.new()
    _box(bm, at[0], at[0] + bed, at[1], at[1] + bed, -2.0, 0.0)
    me = bpy.data.meshes.new("PLATE")
    bm.to_mesh(me)
    bm.free()
    plate = bpy.data.objects.new("PLATE_%dx%d" % (bed, bed), me)
    coll.objects.link(plate)
    plate.display_type = "WIRE"

    dg = bpy.context.evaluated_depsgraph_get()
    items = []
    for name in (parts or PRINTED):
        src = bpy.data.objects.get(name)
        if src is None:
            print("  *** %s is missing" % name)
            continue
        me = bpy.data.meshes.new_from_object(src.evaluated_get(dg))
        me.transform(src.matrix_world)
        m = (Matrix.Identity(4) if name in UPRIGHT
             else max(_boxed(), key=lambda r: _bed(me, r)))
        me.transform(m)
        lo = [min(v.co[i] for v in me.vertices) for i in range(3)]
        hi = [max(v.co[i] for v in me.vertices) for i in range(3)]
        me.transform(Matrix.Translation(Vector((-lo[0], -lo[1], -lo[2]))))
        items.append([name, me, hi[0] - lo[0], hi[1] - lo[1], _bed(me, Matrix.Identity(4))])

    items.sort(key=lambda it: -it[3])            # deepest row first
    x, y, row = gap, gap, 0.0
    placed = []
    for name, me, w, d, contact in items:
        if x + w + gap > bed:
            x, y, row = gap, y + row + gap, 0.0
        # the MESH stays at its own origin, so the STL is not carrying the
        # layout offset around; only the object gets moved onto the plate
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        placed.append((name, ob, me, contact, (at[0] + x, at[1] + y)))
        x += w + gap
        row = max(row, d)

    over = y + row + gap
    print("  %d parts laid out on a %.0f x %.0f bed, %.0f mm deep %s"
          % (len(placed), bed, bed, over,
             "" if over <= bed else "*** DOES NOT FIT"))
    print("  part            bed contact   note")
    for name, ob, me, contact, pos in placed:
        note = "" if contact > 100 else ("brim it" if contact > 25 else "*** too small")
        print("    %-14s %8.1f mm2  %s" % (name, contact, note))

    if folder:
        os.makedirs(folder, exist_ok=True)
        for name, ob, me, contact, pos in placed:
            for o in bpy.context.selected_objects:
                o.select_set(False)
            ob.select_set(True)
            bpy.context.view_layer.objects.active = ob
            path = os.path.join(folder, name + ".stl")
            for call in (lambda: bpy.ops.wm.stl_export(
                             filepath=path, export_selected_objects=True),
                         lambda: bpy.ops.export_mesh.stl(
                             filepath=path, use_selection=True)):
                try:
                    call()
                    break
                except Exception:
                    continue
            ob.select_set(False)
        print("  STLs written to %s" % folder)
    for name, ob, me, contact, pos in placed:      # now shuffle onto the plate
        ob.location = (pos[0], pos[1], 0.0)
    smooth(coll)
    return [n for n, _, _, _, _ in placed]


def export_stl(folder, orient=True):
    """One STL per printed part, laid on its best face and dropped to z=0.

    A sphere touches the bed at a POINT, and a pole stood on its own pin is
    not much better - which is how the last set of prints came off.  So each
    part is tried in all 24 axis-aligned orientations and laid on whichever
    puts the most plastic down.  The two poles are exempt: a bearing has to
    print round, so they stay upright and want a brim instead."""
    import os
    os.makedirs(folder, exist_ok=True)
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for name in PRINTED:
        src = bpy.data.objects.get(name)
        if src is None:
            print("  *** %s is missing - not exported" % name)
            continue
        me = bpy.data.meshes.new_from_object(src.evaluated_get(dg))
        me.transform(src.matrix_world)
        best = Matrix.Identity(4)
        if orient and name not in UPRIGHT:
            best = max(_boxed(), key=lambda m: _bed(me, m))
        me.transform(best)
        ob = bpy.data.objects.new("EXPORT_" + name, me)
        bpy.context.scene.collection.objects.link(ob)
        lo = min(v.co.z for v in me.vertices)
        for v in me.vertices:
            v.co.z -= lo
        contact = _bed(me, Matrix.Identity(4))
        for o in bpy.context.selected_objects:
            o.select_set(False)
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        path = os.path.join(folder, name + ".stl")
        for call in (lambda: bpy.ops.wm.stl_export(filepath=path,
                                                   export_selected_objects=True),
                     lambda: bpy.ops.export_mesh.stl(filepath=path,
                                                     use_selection=True)):
            try:
                call()
                break
            except Exception:
                continue
        out.append((name, len(me.polygons), contact))
        ob.select_set(False)
        bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.meshes.remove(me)
    print("\n  %d STLs written to %s" % (len(out), folder))
    for name, tris, contact in out:
        print("    %-14s %5d tris   %7.1f mm2 on the bed %s"
              % (name, tris, contact, "(brim it)" if contact < 25 else ""))
    return out


def smooth(coll=None, angle=SMOOTH_ANGLE):
    obs = [o for o in (coll or bpy.data.collections[COLL]).objects
           if o.type == "MESH"]
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


def look(pan=0.0, tilt=0.0):
    """pan +ve looks to the robot left, tilt +ve looks up.  Both eyes, always
    together - there is no mechanism here that can do anything else."""
    pan = max(-PAN_LIMIT, min(PAN_LIMIT, pan))
    tilt = max(-TILT_LIMIT, min(TILT_LIMIT, tilt))
    p, t = math.radians(pan), math.radians(tilt)
    frame = bpy.data.objects.get("RIG_frame")
    if frame:
        frame.rotation_euler = (t, 0, 0)
    for s in "LR":
        eye = bpy.data.objects.get("eye_" + s)
        if eye:
            eye.rotation_euler = (0, 0, p)
    link = bpy.data.objects.get("RIG_link")
    if link:
        link.location = (LEV_R * math.sin(p),
                         EYE_Y - LEV_R + LEV_R * (1 - math.cos(p)),
                         LNK_Z[0])

    # tilt: equal, parallel cranks, so the rod only ever translates
    ct, st = math.cos(t), math.sin(t)
    horn = bpy.data.objects.get("RIG_horn_tilt")
    if horn:
        horn.matrix_world = _place(TILT_SEAT + TILT_AX * HORN_GAP,
                                   (0.0, ct, st), TILT_AX)
    rod = bpy.data.objects.get("RIG_rod_tilt")
    if rod:
        a = Vector((TILT_ROD_X, EYE_Y + TILT_CRANK * ct,
                    EYE_Z + TILT_CRANK * st))
        b = Vector((TILT_ROD_X, TILT_SEAT.y + TILT_CRANK * ct,
                    TILT_SEAT.z + TILT_CRANK * st))
        rod.matrix_world = _place(a, b - a, (1.0, 0.0, 0.0))

    # pan: solved, because a slider-crank is not a proportion
    pin, crank = _pan_crank(p)
    horn = bpy.data.objects.get("RIG_horn_pan")
    if horn:
        horn.matrix_basis = _place(PAN_SEAT + PAN_AX * HORN_GAP,
                                   (crank - _PAN_S).to_3d(), PAN_AX)
    rod = bpy.data.objects.get("RIG_rod_pan")
    if rod:
        a = Vector((pin.x, pin.y, PAN_ROD_Z))
        b = Vector((crank.x, crank.y, PAN_ROD_Z))
        rod.matrix_basis = _place(a, b - a, (0.0, 0.0, 1.0))
    bpy.context.view_layer.update()


def servo_angles(pan=0.0, tilt=0.0):
    """What you have to command, in degrees, to get that look.  Tilt is exact
    by construction; pan is not proportional and never will be."""
    p = math.radians(max(-PAN_LIMIT, min(PAN_LIMIT, pan)))
    _, c = _pan_crank(p)
    v = c - _PAN_S
    th = math.degrees(math.atan2(v.y, v.x) - math.atan2(_PAN_U0.y, _PAN_U0.x))
    return (th + 180.0) % 360.0 - 180.0, max(-TILT_LIMIT, min(TILT_LIMIT, tilt))


# ------------------------------------------------------------------ check
def _pieces(ob):
    """A printed part must be one connected lump."""
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


def _aabb(ob):
    m = ob.matrix_world
    p = [m @ Vector(c) for c in ob.bound_box]
    return ([min(q[i] for q in p) for i in range(3)],
            [max(q[i] for q in p) for i in range(3)])


def _apart(a, b, pad=0.0):
    """True if the two boxes cannot possibly touch.  An EXACT boolean costs
    real time and a depsgraph flush; most pairs are nowhere near each other.

    `pad` grows both boxes, for callers asking "are these two even near each
    other" rather than "do these two overlap"."""
    return any(a[1][i] + pad < b[0][i] - pad or b[1][i] + pad < a[0][i] - pad
               for i in range(3))


def _ivol(a, b):
    """Volume of the true solid overlap.  Sampled distance is blind to this."""
    tmp = a.copy()
    tmp.data = a.data.copy()
    bpy.context.scene.collection.objects.link(tmp)
    tmp.matrix_world = a.matrix_world
    m = tmp.modifiers.new(type="BOOLEAN", name="i")
    m.operation, m.object, m.solver = "INTERSECT", b, "EXACT"
    # Without this flush the depsgraph can hand back the PREVIOUS evaluation:
    # the first read after any change lags by one call, so a clean rig reports
    # phantom clashes and a real one can read zero.  Measurements that lie are
    # worse than no measurements.
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    me.transform(tmp.matrix_world)
    bm = bmesh.new()
    bm.from_mesh(me)
    vol = abs(bm.calc_volume(signed=True))
    bm.free()
    bpy.data.meshes.remove(me)
    bpy.data.objects.remove(tmp, do_unlink=True)
    return vol


# Two different things, and conflating them cost us two real clashes.
#
# BURIED: parts that are MEANT to occupy the same space, so no amount of
# overlap is wrong.  Only the printed horns, whose bores are deliberately
# under the spline so the teeth cut in.  Skipped entirely.
#
# SEATED: parts that touch, or run in a clearance fit, so a whisker of
# coplanar boolean noise is fine but a real crash is not.  Allowed 1 mm3.
#
# Whitelisting a WHOLE PAIR because one feature of it touches is how
# "RIG_base"/"RIG_frame" hid the frame's tail driving 87 mm3 into the pillar.
BURIED = {
    ("RIG_horn_tilt", "SV_tilt"),
    ("RIG_horn_pan", "SV_pan"),
}
SEATED = {
    ("RIG_frame", "RIG_pins_L"), ("RIG_frame", "RIG_pins_R"),
    ("RIG_link", "RIG_pins_L"), ("RIG_link", "RIG_pins_R"),
    ("RIG_pins_L", "eye_L"), ("RIG_pins_R", "eye_R"),
    ("RIG_base", "RIG_frame"),      # tilt shaft in the pillar bore
    ("RIG_shelf", "RIG_frame"),     # posts seated under the crossbar
    ("RIG_shelf", "SV_pan"), ("RIG_base", "SV_tilt"),
    ("RIG_horn_tilt", "RIG_rod_tilt"), ("RIG_horn_pan", "RIG_rod_pan"),
    ("RIG_rod_tilt", "RIG_frame"), ("RIG_rod_pan", "RIG_pins_L"),
}
LADDER_COLL = "BORE_LADDER"


def bore_ladder(folder=None, sizes=(4.75, 4.85, 4.95, 5.05)):
    """Hub pucks in a range of bore sizes, to find HORN_BORE on a real spline.

    The horn bore is the one number on this rig that cannot be derived - it
    depends on the printer and on the filament, and it is one-way: too small
    splits the hub going on, too large strips under load.  Guessing costs a
    print per guess, so print the whole range at once and keep the winner.

    Each puck carries bumps on its rim counting its place in `sizes` - one
    bump for the smallest - so four identical-looking discs coming off the
    bed cannot be mixed up.  No labels to print and nothing to write down.

        eye_rig.bore_ladder(folder="C:/some/where")

    Press each onto a spline.  Keep the one that starts square and needs the
    servo screw to seat it, then set HORN_BORE to it and rebuild the horns."""
    old = bpy.data.collections.get(LADDER_COLL)
    if old:
        for o in list(old.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(old)
    coll = bpy.data.collections.new(LADDER_COLL)
    bpy.context.scene.collection.children.link(coll)

    names = []
    for i, d in enumerate(sizes, start=1):
        parts = [lambda bm: _rodz(bm, HORN_HUB_D / 2, 0.0, HORN_T, 0.0, 0.0)]
        # 40 deg apart, so neighbouring bumps never touch: at 30 they
        # overlapped and pinched the mesh where they met
        for k in range(i):
            a = math.radians(-60.0 + k * 40.0)
            parts.append(lambda bm, a=a: _rodz(
                bm, 1.25, 0.0, HORN_T,
                math.cos(a) * HORN_HUB_D / 2, math.sin(a) * HORN_HUB_D / 2))
        name = "BORE_%s" % ("%.2f" % d).replace(".", "p")
        _obj(name, coll,
             parts,
             [lambda bm, d=d: _rodz(bm, d / 2, -1.0, HORN_T + 1.0, 0.0, 0.0)])
        names.append(name)
    smooth(coll)
    print("  bore ladder: %s  (bumps count the size, 1 = smallest)"
          % ", ".join("%.2f" % d for d in sizes))
    test_prints(folder=folder, bed=60.0, gap=6.0, at=(0.0, 0.0),
                parts=tuple(names))
    return names


SEAT_TOL = 1.0

# A running joint is SUPPOSED to be close - that is what makes it a joint - so
# it gets its own floor.  Anything else that comes this near is a crash the
# printer has not got round to causing yet.
MIN_GAP = 0.4                   # free parts passing each other
MIN_JOINT = 0.15                # radial slack in a pin-in-bore fit
# Both are printer numbers, not design numbers.  0.1 mm per side measured fine
# in Blender and bound solid in PLA: the lid hub on its pin was 0.09 and the
# whole rig came off the bed stiff.  The one joint that felt right was the
# snap eye, which is 0.15 a side.


def _sample(o, cap=600):
    """World-space vertices of o, thinned to about `cap` of them."""
    vs = o.data.vertices
    step = max(1, len(vs) // cap)
    m = o.matrix_world
    return [m @ vs[i].co for i in range(0, len(vs), step)]


def _gap(a, b):
    """Smallest distance from a's sampled vertices to b's surface.

    Approximate on purpose: vertex-to-surface, not surface-to-surface, so a
    gap between two flat faces with no vertex near the closest point reads a
    little wide.  For pins in bores and slabs passing slabs - which is all
    this rig has - it is the number you want, and it is thousands of times
    cheaper than the boolean the crash test uses."""
    inv = b.matrix_world.inverted()
    best = 1e9
    for w in _sample(a):
        ok, loc, _, _ = b.closest_point_on_mesh(inv @ w)
        if ok:
            best = min(best, (b.matrix_world @ loc - w).length)
    return best


def clearances(verbose=True, names=None):
    """How much room is actually left between parts, in millimetres.

    The crash test answers "do these two overlap", which is the same answer
    for 9 mm of daylight and for 0.09.  That is how a rig that cannot be
    turned by hand passed every check: nothing overlapped.  This asks the
    other question."""
    coll = bpy.data.collections[COLL]
    names = names or ([o.name for o in coll.objects
                       if not o.name.startswith("RIG_socket")] +
                      [n for n in ("eye_L", "eye_R")
                       if bpy.data.objects.get(n)])
    poses = [(p, t) for p in (-PAN_LIMIT, 0.0, PAN_LIMIT)
             for t in (-TILT_LIMIT, 0.0, TILT_LIMIT)]
    tight = {}
    for pan, tilt in poses:
        look(pan, tilt)
        bpy.context.view_layer.update()
        box = {n: _aabb(bpy.data.objects[n]) for n in names}
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if (a, b) in BURIED or (b, a) in BURIED:
                    continue
                if _apart(box[a], box[b], pad=3.0):
                    continue
                d = min(_gap(bpy.data.objects[a], bpy.data.objects[b]),
                        _gap(bpy.data.objects[b], bpy.data.objects[a]))
                k = (a, b)
                if d < tight.get(k, (1e9,))[0]:
                    tight[k] = (d, pan, tilt)
    look(0, 0)

    ok = True
    if verbose:
        print("\n  HOW MUCH ROOM IS LEFT?")
        print("  (joints want >= %.2f mm of slack, everything else >= %.2f)"
              % (MIN_JOINT, MIN_GAP))
    for (a, b), (d, pan, tilt) in sorted(tight.items(), key=lambda kv: kv[1][0]):
        joint = (a, b) in SEATED or (b, a) in SEATED
        floor = MIN_JOINT if joint else MIN_GAP
        bad = d < floor
        ok &= not bad
        if verbose and (bad or d < 3.0):
            print("    %-14s %-14s %5.2f mm  %-7s at pan %+.0f tilt %+.0f %s"
                  % (a, b, d, "joint" if joint else "free", pan, tilt,
                     "***" if bad else ""))
    if verbose and ok:
        print("    everything has room")
    return ok


def _escapes(name, others, step=1.0, reach=60.0):
    """The axes this part can be pulled straight out along, if any.

    A part that cannot be taken off along any straight line was never going
    to be put ON along one either.  This is the check that was missing: the
    crash test only ever looked at the ASSEMBLED pose, so a collar too fat to
    pass its own bore and a shaft trapped between two webs both sailed
    through it, and neither could be built on a bench.

    Conservative in one direction only - it says nothing about parts that
    genuinely need to go in at an angle or in two moves, so read a TRAPPED as
    "look at this", not as proof."""
    o = bpy.data.objects[name]
    home = o.matrix_world.copy()
    out = []
    for ax in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0),
               (0, 0, 1), (0, 0, -1)):
        v = Vector(ax)
        clear = True
        d = step
        while d <= reach and clear:
            o.matrix_world = Matrix.Translation(v * d) @ home
            bpy.context.view_layer.update()
            ab = _aabb(o)
            for n in others:
                if _apart(ab, _aabb(bpy.data.objects[n])):
                    continue
                if _ivol(o, bpy.data.objects[n]) > 0.5:
                    clear = False
                    break
            if not clear:
                break
            # once its box is free of everything, it is out
            if all(_apart(ab, _aabb(bpy.data.objects[n])) for n in others):
                break
            d += step
        o.matrix_world = home
        bpy.context.view_layer.update()
        if clear:
            out.append("%s%s" % ("+-"[v[0] + v[1] + v[2] < 0],
                                 "xyz"[[abs(c) for c in ax].index(1)]))
    return out


def assembly(verbose=True, names=None):
    """Can each part be got on and off the rig at all?"""
    coll = bpy.data.collections[COLL]
    names = names or ([o.name for o in coll.objects
                       if not o.name.startswith(("RIG_socket", "SV_"))] +
                      [n for n in ("eye_L", "eye_R")
                       if bpy.data.objects.get(n)])
    look(0, 0)
    ok = True
    if verbose:
        print("\n  CAN EACH PART BE PUT ON AND TAKEN OFF?")
    for n in names:
        others = [m for m in names if m != n]
        ways = _escapes(n, others)
        bad = not ways
        ok &= not bad
        if verbose:
            print("    %-14s %s" % (n, "*** TRAPPED - cannot come out along"
                                    " any axis" if bad else
                                    "comes out " + ", ".join(ways)))
    return ok


def check(verbose=True):
    coll = bpy.data.collections[COLL]
    # the socket cutters are booleans, not parts - they are SUPPOSED to be
    # inside the ball, and they are not there when it is printed
    names = [o.name for o in coll.objects
             if not o.name.startswith("RIG_socket")] + \
            [n for n in ("eye_L", "eye_R") if bpy.data.objects.get(n)]
    ok = True
    if verbose:
        print("\n  IS EACH PART ONE LUMP?")
        for o in coll.objects:
            if o.name.startswith(("SV_", "RIG_socket")):
                continue
            n = _pieces(o)
            print("    %-14s pieces=%d %s" % (o.name, n, "" if n == 1 else "***"))
            ok &= n == 1

    if verbose:
        # "bolted to it" is whitelisted below, which would hide a servo buried
        # in its own bracket.  So measure it instead of trusting the list.
        print("\n  DO THE SERVOS FIT THEIR CRADLES?")
        for sv, mnt in (("SV_pan", "RIG_shelf"), ("SV_tilt", "RIG_base")):
            a, b = bpy.data.objects.get(sv), bpy.data.objects.get(mnt)
            if not (a and b):
                continue
            v = _ivol(a, b)
            print("    %-8s in %-10s  %7.2f mm3 of case buried %s"
                  % (sv, mnt, v, "" if v < 1.0 else "***"))
            ok &= v < 1.0

    # Sample the WHOLE arc, not just its ends.  Parts swing on circles, so the
    # closest approach is usually somewhere in the middle: the link's lowest
    # point is at tilt +13.5, and testing only +-20 walked straight past it.
    worst = {}
    poses = [(p, t) for p in (-PAN_LIMIT, 0.0, PAN_LIMIT)
             for t in (-TILT_LIMIT, -TILT_LIMIT * 0.66, -TILT_LIMIT * 0.33, 0.0,
                       TILT_LIMIT * 0.33, TILT_LIMIT * 0.66, TILT_LIMIT)]
    for pan, tilt in poses:
        look(pan, tilt)
        bpy.context.view_layer.update()
        box = {n: _aabb(bpy.data.objects[n]) for n in names}
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if (a, b) in BURIED or (b, a) in BURIED:
                    continue
                if _apart(box[a], box[b]):
                    continue
                tol = (SEAT_TOL if (a, b) in SEATED or (b, a) in SEATED
                       else 1e-3)
                v = _ivol(bpy.data.objects[a], bpy.data.objects[b])
                if v > tol:
                    k = (a, b)
                    if v > worst.get(k, (0,))[0]:
                        worst[k] = (v, pan, tilt)
    look(0, 0)

    if verbose:
        print("\n  DOES ANYTHING CRASH, ANYWHERE IN THE TRAVEL?")
        print("  (boolean, %d poses across pan +-%.0f and tilt +-%.0f)"
              % (len(poses), PAN_LIMIT, TILT_LIMIT))
        if not worst:
            print("    nothing touches that should not")
        for (a, b), (v, pan, tilt) in sorted(worst.items(),
                                             key=lambda kv: -kv[1][0]):
            print("    %-14s %-14s %8.2f mm3  at pan %+.0f tilt %+.0f  ***"
                  % (a, b, v, pan, tilt))
        ok &= not worst

    # Both of these exist because every test above passed on a rig that could
    # not be assembled and could not be turned by hand.  Overlap is not fit,
    # and the assembled pose is not the whole story.
    ok &= clearances(verbose)
    ok &= assembly(verbose)

    if verbose:
        print("\n  %s" % ("ALL CHECKS PASSED" if ok else "*** CHECK FAILED"))
    return ok
