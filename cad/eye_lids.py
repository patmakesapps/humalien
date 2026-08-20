"""Eyelids, hung on the eye rig's tilt frame.

They ride the FRAME, not the base.  The frame turns about the line through
both eye centres, so a lid pivoting on that same line sweeps the ball at a
constant radius through the whole of tilt.  Hang them off the base instead
and the ball rotates 20 deg under a lid built loose enough to survive the
worst angle, which means it gapes at every other one.

Pan does not enter into it: a sphere turning about its own centre is the same
sphere, so a lid only ever has to clear a static ball.

Each lid pivots on its OWN stub, outboard of its ball.  The obvious
alternative - one shaft down the corridor between the eyes with arms reaching
out over each ball - is what the archive rig did, and it is why those lids
broke: a straight shaft cannot be on the axis and clear two 24 mm balls, so
the arms get forced through the lune.  That left the nubs and a 1.9 mm2 weld
neck.  Nothing here crosses the lune.

The two uppers are tied by a plain rod through both cranks.  Both cranks
point the same way, so their pins are coaxial and the tie is simply a shaft -
no linkage, no dead point, and the two lids cannot get out of step.

    import eye_lids; eye_lids.build(); eye_lids.blink(0.0)
"""
import math
import bpy
import bmesh
from mathutils import Vector, Matrix

import eye_rig as R

COLL = "EYE_LIDS"

AX_Y, AX_Z = R.EYE_Y, R.EYE_Z   # the lid axis IS the eye centreline
LID_RI, LID_RO = 12.6, 14.2     # 0.6 off a ball that ends at 12
LID_X = (21.0, 45.5)            # capped clear of the frame's webs inboard,
                                # and of the bearing bracket outboard
# The hub starts at 43.8 because the BALL reaches 43.5 - a hub any further in
# is a Ø10 boss sitting on the axis inside the sphere.  Past x 44.1 the inner
# sphere has ended, so the shell is solid there and the hub blends into 1.7 mm
# of it rather than clinging to a 0.2 mm rim.
# The lid is all bore and no stub.  A pin sticking out of it was the one
# feature stopping the part lying flat on a bed, and it made the lid longer
# for nothing - the frame can carry the pin just as well.
HUB_D, HUB_X = 10.0, (43.8, 50.0)
BORE_D = 5.2
# The two sector planes meet exactly ON the lid axis.  Run them through the
# solid nose of the shell and the solver has a knife edge to resolve, which
# it does not: it returned 60 open edges and a negative volume.  So the
# sector is only cut inboard of here, and the nose stays a plain dome for the
# hub to blend into.
SECTOR_X = 44.0

# Angles about the axis: 0 straight ahead, +90 straight up.
UP_SHUT, UP_SWEEP, UP_TAIL = -8.0, 38.0, 115.0

# The tie sits BEHIND the brow, not over the eyes.  At 110 deg it starts
# above the back of the ball and swings further back as the lids open, so
# nothing crosses the line of sight.  Radius 18 clears the shell by 1.3.
# 100, not 110: at 110 the tie's envelope reached y 44.45 at full open and
# clipped the servo bracket's foot, which has to sit on the spine at y 43.
CRANK_A, CRANK_R, CRANK_W = 100.0, 18.0, 7.0
# The tie runs 3 mm PAST the outer face of each crank, so there is something
# for a clip to grab.  Ending it flush inside the bore gave it nothing to be
# retained by and it would have walked straight out.
TIE_D, TIE_X = 5.0, 53.0

SMOOTH_ANGLE = R.SMOOTH_ANGLE

# --- the drive -----------------------------------------------------------
# The servo's shaft has to lie along x, because the tie moves in the yz plane
# and a pushrod driving it must move in that plane too.  That fixes the ears
# vertical, so it mounts like the tilt servo rather than the pan one.
#
# Where it can go is decided by the tie, which sweeps a band across the FULL
# width of the rig - y 30..45, z 7..19.  Nothing can live in there, so the
# servo sits behind y 46, above the crossbar, on a bracket of its own.
# Driven from a SECOND crank on the left hub, pointing down and back into the
# empty space outboard of the fork arm - not from the tie up top.  Driving the
# tie put the servo 35 mm behind the frame and 18 mm above it on a one-screw
# cantilever, which is the same mast that just came off the frame.
DRV_A, DRV_R, DRV_PIN_D = -140.0, 20.0, 3.0
# Shaft points INBOARD, so the case sits outboard of everything and the horn
# lands where the rod has to run.  Pointing it the other way put the case
# right across the rod's path - 279 mm3 of it.
# y 58 so the ear slab starts at 47.6 - at 56 its front tab clipped the lid
# bracket's rail, which ends at y 46.
SV_LID = dict(p=(48.0, 58.0, -5.0), shaft=(-1, 0, 0), body=(0, 1, 0))
LID_HORN_R, LID_HORN_PIN = 12.0, 4.5
# 41.5, not 39.5: the pan rod swings out to x 38 at full pan, and the drive
# pin has to start outboard of the fork arm, which ends at 37.5.
LID_ROD_X = 41.5
DRIVE_T = 0.5                   # crank set perpendicular to the rod HERE
# Still a П - the ears stand proud of the case in y, so anything spanning
# between them at the ears' own x runs straight through the servo.
MNT_X = (48.17, 53.17)
MNT_BEAM_T, MNT_PAD = 2.5, 4.0
MNT_FOOT_Y, MNT_FOOT_Z = (43.0, 46.0), (-8.5, -5.0)
# the foot is narrower than the plate: the drive crank sweeps out to x 50 and
# came within 0.48 mm of it
MNT_FOOT_X = (50.5, 53.17)

# --- lower lids, fixed ---------------------------------------------------
# A real lower lid moves a millimetre or two, so this one does not move at
# all.  It screws to the FRONT face of the fork arm, which is 24 mm of solid
# material, rather than to its top - the pan pole's collar sits on top and
# leaves nothing to bolt to between x 26.5 and 36.5.
# The same lune as the upper lid, just fixed - it should look like a lid, and
# the upper one already does.  Two flat webs down the FRONT face of the fork
# arm both mount it and give it a face to print on; laid web-down it is only
# 8.6 mm tall, so a brim is enough.
#
# It stops at x 40 because the UPPER lid's hub owns the axis from 43.8 out.
LO_X = (21.0, 40.0)
LO_WEB_X = ((23.0, 26.0), (37.0, 40.0))
LO_WEB_Y, LO_WEB_Z = (19.5, 22.0), (-17.5, -11.5)
LO_SCREW_Z = -16.0


# ----------------------------------------------------------------- shapes
def _sphere_at(bm, cx, r, segs=64):
    bmesh.ops.create_uvsphere(
        bm, u_segments=segs, v_segments=segs // 2, radius=r,
        matrix=Matrix.Translation(Vector((cx, AX_Y, AX_Z))))


def _wedge(bm, deg, x0, x1, big=250.0):
    """Everything on the far side of a plane through the lid axis, between x0
    and x1.  Used as a CUT, so the sector a lid occupies is the shell less
    the two half-spaces outside it - every operation stays a difference."""
    v = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    bmesh.ops.scale(bm, verts=v, vec=(abs(x1 - x0), 2 * big, big))
    bmesh.ops.translate(bm, verts=v, vec=(0.0, 0.0, big / 2))
    bmesh.ops.rotate(bm, verts=v, cent=(0, 0, 0),
                     matrix=Matrix.Rotation(math.radians(-deg), 3, "X"))
    bmesh.ops.translate(bm, verts=v, vec=((x0 + x1) / 2, AX_Y, AX_Z))


def _spin(bm, deg):
    """Swing everything in bm about the lid axis, from straight up to `deg`."""
    bmesh.ops.rotate(bm, verts=bm.verts[:], cent=(0.0, AX_Y, AX_Z),
                     matrix=Matrix.Rotation(math.radians(90.0 - deg), 3, "X"))


def _fuse(a, b):
    """Union b into a and drop b."""
    bpy.context.view_layer.objects.active = a
    m = a.modifiers.new(type="BOOLEAN", name="u")
    m.object, m.solver, m.operation = b, "EXACT", "UNION"
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(b, do_unlink=True)


# ------------------------------------------------------------------ parts
def _lid(name, coll, sx, lead, tail):
    """A lune of a spherical shell, with a hub at its outboard tip.

    The shell converges on the axis at its outboard end all by itself, so the
    hub blends straight into it - no arm, and nothing reaching across the eye.
    Built in two pieces because the sector cuts are planes through the axis
    and would slice the hub off if they were applied to it."""
    cx = sx * R.EYE_X
    x0, x1 = sorted((sx * LID_X[0], sx * LID_X[1]))
    sec = sorted((sx * LID_X[0], sx * SECTOR_X))
    hx = sorted((sx * HUB_X[0], sx * HUB_X[1]))
    # The bore has to go through the SHELL too, not just the hub.  Past x 44.1
    # the inner sphere has ended, so the nose is solid and sits right on the
    # axis - the pin was driving straight through it.
    bore = (min(hx[0], x0) - 1.0, max(hx[1], x1) + 1.0)
    shell = R._obj(
        name, coll,
        [lambda bm: _sphere_at(bm, cx, LID_RO)],
        [lambda bm: _sphere_at(bm, cx, LID_RI),
         lambda bm: _wedge(bm, lead + 180.0, sec[0] - 40, sec[1]),
         lambda bm: _wedge(bm, lead + tail, sec[0] - 40, sec[1]),
         lambda bm: R._box(bm, x0 - 80, x0, AX_Y - 80, AX_Y + 80, -80, 80),
         lambda bm: R._box(bm, x1, x1 + 80, AX_Y - 80, AX_Y + 80, -80, 80),
         lambda bm: R._rodx(bm, BORE_D / 2, bore[0], bore[1], AX_Y, AX_Z)],
        loc=(0.0, AX_Y, AX_Z))

    ct = sorted((sx * (HUB_X[0] + 0.5), sx * HUB_X[1]))
    tip = AX_Z + CRANK_R

    def _crank_bar(bm):
        R._box(bm, ct[0], ct[1], AX_Y - CRANK_W / 2, AX_Y + CRANK_W / 2,
               AX_Z, tip)
        _spin(bm, CRANK_A)

    def _crank_eye(bm):
        R._rodx(bm, CRANK_W / 2, ct[0], ct[1], AX_Y, tip)
        _spin(bm, CRANK_A)

    def _crank_bore(bm):
        R._rodx(bm, BORE_D / 2, ct[0] - 1, ct[1] + 1, AX_Y, tip)
        _spin(bm, CRANK_A)

    def _drv_bar(bm):
        R._box(bm, ct[0], ct[1], AX_Y - CRANK_W / 2, AX_Y + CRANK_W / 2,
               AX_Z, AX_Z + DRV_R)
        _spin(bm, DRV_A)

    def _drv_eye(bm):
        R._rodx(bm, CRANK_W / 2, ct[0], ct[1], AX_Y, AX_Z + DRV_R)
        _spin(bm, DRV_A)

    def _drv_pin(bm):
        # starts at 40, not 38.5: the fork arm widened to x 39.5 and the pin
        # went straight back through it
        R._rodx(bm, DRV_PIN_D / 2, LID_ROD_X - 1.5, ct[0], AX_Y, AX_Z + DRV_R)
        _spin(bm, DRV_A)

    boss_parts = [lambda bm: R._rodx(bm, HUB_D / 2, hx[0], hx[1], AX_Y, AX_Z),
                  _crank_bar, _crank_eye]
    if sx > 0:                       # only the left hub carries the drive
        boss_parts += [_drv_bar, _drv_eye, _drv_pin]
    boss = R._obj(
        name + "_boss", coll,
        boss_parts,
        [_crank_bore,
         lambda bm: R._rodx(bm, BORE_D / 2, hx[0] - 1, hx[1] + 1,
                            AX_Y, AX_Z)],
        loc=(0.0, AX_Y, AX_Z))
    _fuse(shell, boss)
    return shell


def _carve(a, b):
    """Subtract b from a and drop b."""
    bpy.context.view_layer.objects.active = a
    m = a.modifiers.new(type="BOOLEAN", name="d")
    m.object, m.solver, m.operation = b, "EXACT", "DIFFERENCE"
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(b, do_unlink=True)


def _lower(name, coll, sx):
    """A fixed lower lid that can actually be printed: a block with the ball's
    sphere scooped out of it, bolted to the FRONT face of the fork arm.

    It goes on the front face and not the top because the pan pole's collar
    owns the arm's top from x 26.5 to 36.5, and there is nothing to bolt to
    between."""
    cx = sx * R.EYE_X
    x0, x1 = sorted((sx * LO_X[0], sx * LO_X[1]))
    sec = sorted((sx * LO_X[0], sx * LO_X[1]))
    shell = R._obj(
        name, coll,
        [lambda bm: _sphere_at(bm, cx, LID_RO)],
        [lambda bm: _sphere_at(bm, cx, LID_RI),
         lambda bm: _wedge(bm, LO_LEAD + 180.0, sec[0] - 40, sec[1]),
         lambda bm: _wedge(bm, LO_LEAD + LO_TAIL, sec[0] - 40, sec[1]),
         lambda bm: R._box(bm, x0 - 80, x0, AX_Y - 80, AX_Y + 80, -80, 80),
         lambda bm: R._box(bm, x1, x1 + 80, AX_Y - 80, AX_Y + 80, -80, 80)],
        loc=(0.0, AX_Y, AX_Z))
    webs, cuts = [], []
    for a, b in LO_WEB_X:
        w = sorted((sx * a, sx * b))
        webs.append(lambda bm, p=w: R._box(bm, p[0], p[1], LO_WEB_Y[0],
                                           LO_WEB_Y[1], LO_WEB_Z[0],
                                           LO_WEB_Z[1]))
        cuts.append(lambda bm, p=w: R._rody(bm, (R.SV_SCREW_D + 0.5) / 2,
                                            LO_WEB_Y[0] - 1, LO_WEB_Y[1] + 1,
                                            (p[0] + p[1]) / 2, LO_SCREW_Z))
    foot = R._obj(name + "_web", coll, webs, cuts, loc=(0.0, AX_Y, AX_Z))
    _fuse(shell, foot)
    return shell


def _tie(coll):
    """One rod through both cranks.  Both cranks point the same way, so the
    two pins are coaxial and the tie is a shaft, not a linkage."""
    def _bar(bm):
        R._rodx(bm, TIE_D / 2, -TIE_X, TIE_X, AX_Y, AX_Z + CRANK_R)
        _spin(bm, CRANK_A)

    return R._obj("LID_tie", coll, [_bar], loc=(0.0, AX_Y, AX_Z))


def _arm_at(t, deg, r):
    """Where a crank on the lid hub points, in the yz plane, at blink t."""
    a = math.radians(deg + UP_SWEEP * max(0.0, min(1.0, t)))
    return Vector((AX_Y - r * math.cos(a), AX_Z + r * math.sin(a)))


def _tie_at(t):
    return _arm_at(t, CRANK_A, CRANK_R)


def _drive_pt(t):
    return _arm_at(t, DRV_A, DRV_R)


_S = Vector((SV_LID["p"][1], SV_LID["p"][2]))
_V0 = _drive_pt(DRIVE_T) - _S
_U0 = Vector((-_V0.y, _V0.x)).normalized()
DRIVE_ROD_L = (_V0 - _U0 * LID_HORN_R).length


def _drive_crank(t):
    """(drive pin, servo crank pin) at blink t.  Circle-circle, as for pan."""
    p = _drive_pt(t)
    v = p - _S
    d = v.length
    a = (LID_HORN_R ** 2 - DRIVE_ROD_L ** 2 + d * d) / (2.0 * d)
    h = math.sqrt(max(0.0, LID_HORN_R ** 2 - a * a))
    u = v / d
    return p, _S + u * a + Vector((-u.y, u.x)) * h


def _rod2(name, coll, length, bore_a, bore_b):
    """A pushrod whose two eyes take different pins - the far one rides
    straight on the tie rod itself, so the tie needs no lug."""
    ea, eb = bore_a / 2 + 2.4, bore_b / 2 + 2.4
    t, w = R.ROD_T, R.ROD_W
    parts = [
        lambda bm: R._box(bm, 0.0, length, -w / 2, w / 2, -t / 2, t / 2),
        lambda bm: R._rodz(bm, ea, -t / 2, t / 2, 0.0, 0.0),
        lambda bm: R._rodz(bm, eb, -t / 2, t / 2, length, 0.0),
    ]
    cuts = [
        lambda bm: R._rodz(bm, bore_a / 2, -t, t, 0.0, 0.0),
        lambda bm: R._rodz(bm, bore_b / 2, -t, t, length, 0.0),
        lambda bm: R._box(bm, -(bore_a - 0.55) / 2, (bore_a - 0.55) / 2,
                          0.0, ea + 1.0, -t, t),
        lambda bm: R._box(bm, length - (bore_b - 0.55) / 2,
                          length + (bore_b - 0.55) / 2,
                          -(eb + 1.0), 0.0, -t, t),
    ]
    return R._obj(name, coll, parts, cuts)


def _mount(coll):
    """The lid servo's bracket.  Its own part, bolted down into the spine, so
    the frame keeps the flat back it prints on."""
    holes = [R._sv_pt(SV_LID, hx, 0.0, sum(R.SV_EAR_Z) / 2)
             for hx in R.SV_HOLE_X]
    ys = sorted(h.y for h in holes)
    # the pads stop 0.5 short of the case, or they grow straight into it
    case = R._sv_bounds(SV_LID, R.SV_BODY_X, (-R.SV_BODY_Y, R.SV_BODY_Y),
                        (R.SV_EAR_Z[0],))
    # front pad kept behind y 46.5, or it grows into the lid bracket's arm
    pads = [(max(ys[0] - MNT_PAD, MNT_FOOT_Y[1] + 0.5), case[1][0] - 0.5),
            (case[1][1] + 0.5, ys[1] + MNT_PAD)]
    # over the TOP of the case, wherever that is.  Hard-coding this is how the
    # beam ended up 1.55 mm inside the servo when it moved up 2 mm.
    bz = (case[2][1] + 0.5, case[2][1] + 0.5 + MNT_BEAM_T)
    zlo = MNT_FOOT_Z[0]
    parts = [lambda bm: R._box(bm, MNT_X[0], MNT_X[1], pads[0][0],
                               pads[1][1], bz[0], bz[1]),
             lambda bm: R._box(bm, MNT_FOOT_X[0], MNT_FOOT_X[1],
                               MNT_FOOT_Y[0], MNT_FOOT_Y[1],
                               MNT_FOOT_Z[0], MNT_FOOT_Z[1])]
    for a, b in pads:
        parts.append(lambda bm, p=a, q=b: R._box(bm, MNT_X[0], MNT_X[1],
                                                 p, q, zlo, bz[1]))
    parts.append(lambda bm: R._box(bm, MNT_FOOT_X[0], MNT_FOOT_X[1],
                                   MNT_FOOT_Y[1] - 1, pads[0][1],
                                   zlo, MNT_FOOT_Z[1]))
    cuts = [lambda bm, q=h: R._rodx(bm, R.SV_SCREW_D / 2, MNT_X[0] - 1,
                                    MNT_X[1] + 1, q.y, q.z) for h in holes]
    cuts.append(lambda bm: R._rodz(bm, (R.SV_SCREW_D + 0.5) / 2,
                                   MNT_FOOT_Z[0] - 1, MNT_FOOT_Z[1] + 1,
                                   (MNT_FOOT_X[0] + MNT_FOOT_X[1]) / 2,
                                   (MNT_FOOT_Y[0] + MNT_FOOT_Y[1]) / 2))
    return R._obj("LID_mount", coll, parts, cuts,
                  loc=(MNT_X[0], MNT_FOOT_Y[0], MNT_FOOT_Z[0]))


# ------------------------------------------------------------------ build
def build():
    for ob in list(bpy.data.objects):
        if ob.name.startswith(("LID_", "SV_lid")):
            bpy.data.objects.remove(ob, do_unlink=True)
    old = bpy.data.collections.get(COLL)
    if old:
        bpy.data.collections.remove(old)
    coll = bpy.data.collections.new(COLL)
    bpy.context.scene.collection.children.link(coll)

    for s, sx in (("L", 1), ("R", -1)):
        _lid("LID_up_" + s, coll, sx, UP_SHUT, UP_TAIL)
    # Lower lids are NOT built. _lower() still works and is one line away from
    # coming back; it is parked because a 1.6 mm curved shell has no flat face
    # to print on, and every shape that gave it one stopped looking like a lid.
    _tie(coll)
    _mount(coll)
    R._horn("LID_horn", coll, LID_HORN_R, LID_HORN_PIN)
    _rod2("LID_rod", coll, DRIVE_ROD_L, R.PIN_L_D + 0.3, TIE_D + 0.3)
    src = bpy.data.objects.get(R.SERVO_SRC)
    if src is not None:
        ob = bpy.data.objects.new("SV_lid", src.data)
        coll.objects.link(ob)
        ob.matrix_world = (Matrix.Translation(Vector(SV_LID["p"]))
                           @ R._frame_m(SV_LID["shaft"], SV_LID["body"]))

    frame = bpy.data.objects.get("RIG_frame")
    if frame:
        for ob in coll.objects:
            ob.parent = frame
            ob.matrix_parent_inverse = frame.matrix_world.inverted()
    R.smooth(coll)
    blink(0.0)
    print("built %d lid parts: %s"
          % (len(coll.objects), ", ".join(o.name for o in coll.objects)))
    return check()


def blink(t=0.0):
    """t = 0 shut, 1 open.  Everything turns about the one axis together.

    Negative, because a rotation of +theta about x carries a point at angle
    alpha to alpha MINUS theta - so the positive-looking version drove the
    lids further shut, and every clearance check passed on the wrong half of
    the travel."""
    b = -math.radians(UP_SWEEP * max(0.0, min(1.0, t)))
    for n in ("LID_up_L", "LID_up_R", "LID_tie"):
        ob = bpy.data.objects.get(n)
        if ob:
            ob.rotation_euler = (b, 0.0, 0.0)

    tie, crank = _drive_crank(t)
    seat, ax = R._servo_axis(SV_LID)
    horn = bpy.data.objects.get("LID_horn")
    if horn:
        horn.matrix_basis = R._place(
            seat + ax * R.HORN_GAP,
            (Vector((0.0, crank.x, crank.y)) - Vector((0.0, _S.x, _S.y))), ax)
    rod = bpy.data.objects.get("LID_rod")
    if rod:
        a = Vector((LID_ROD_X, crank.x, crank.y))
        b3 = Vector((LID_ROD_X, tie.x, tie.y))
        rod.matrix_basis = R._place(a, b3 - a, (1.0, 0.0, 0.0))
    bpy.context.view_layer.update()


def servo_angle(t):
    """Degrees the lid servo must be commanded to, for blink t."""
    _, c = _drive_crank(t)
    v = c - _S
    d = math.degrees(math.atan2(v.y, v.x) - math.atan2(_U0.y, _U0.x))
    return (d + 180.0) % 360.0 - 180.0


# ------------------------------------------------------------------ check
def check(verbose=True):
    # The sweep tilts the frame and expects the eyes and their pins to ride
    # it.  With the parenting cleared for inspection they do not, so the lids
    # swing and the eyes stay put and it reports clashes that are not there -
    # 125 mm3 of one, once.
    for n in ("eye_L", "RIG_pins_L"):
        ob = bpy.data.objects.get(n)
        if ob is not None and ob.parent is None:
            print("  *** %s is unparented - run eye_rig.build() first, or"
                  " every tilt result below is meaningless" % n)
    coll = bpy.data.collections[COLL]
    names = [o.name for o in coll.objects]
    others = [n for n in ("eye_L", "eye_R", "RIG_frame", "RIG_base",
                          "RIG_pins_L", "RIG_pins_R", "RIG_link",
                          "RIG_rod_pan", "RIG_horn_pan", "SV_pan")
              if bpy.data.objects.get(n)]
    ok = True
    if verbose:
        # A lid is a shell cut by planes that meet ON its own axis, which is
        # exactly the case a boolean gives up on - and it gives up quietly,
        # handing back a mess that still looks like a mesh.  Piece count alone
        # passed 60 open edges and a negative volume, so measure both.
        print("\n  IS EACH LID A CLOSED SOLID?")
        for o in coll.objects:
            bm = bmesh.new()
            bm.from_mesh(o.data)
            openn = sum(1 for e in bm.edges if len(e.link_faces) != 2)
            vol = bm.calc_volume(signed=True)
            bm.free()
            n = R._pieces(o)
            bad = openn or vol <= 0 or n != 1
            print("    %-12s pieces=%d  open edges=%-3d  volume=%+9.1f %s"
                  % (o.name, n, openn, vol, "***" if bad else ""))
            ok &= not bad

    # joints, not crashes: a pin in its bore, a horn on its spline.
    allowed = {("LID_up_L", "LID_tie"), ("LID_up_R", "LID_tie"),
               ("LID_horn", "SV_lid"), ("LID_horn", "LID_rod"),
               ("LID_rod", "LID_tie"), ("LID_mount", "RIG_frame"),
               ("LID_mount", "SV_lid")}
    # NOT whitelisted: the bracket against the servo.  Blanketing that pair
    # is what let 169 mm3 of beam sit inside the case unreported.  Measured
    # instead, with only enough tolerance for coplanar ear-on-pad contact.
    if verbose:
        sv = bpy.data.objects.get("SV_lid")
        mt = bpy.data.objects.get("LID_mount")
        if sv and mt:
            v = R._ivol(mt, sv)
            print("\n  DOES THE LID SERVO FIT ITS BRACKET?")
            print("    %7.2f mm3 of case buried %s" % (v, "" if v < 1.0 else "***"))
            ok &= v < 1.0
    worst = {}
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        for pan, tilt in ((0, 0), (25, 20), (-25, -20), (0, 20), (0, -20)):
            blink(t)
            R.look(pan, tilt)
            bpy.context.view_layer.update()
            box = {n: R._aabb(bpy.data.objects[n]) for n in names + others}
            for i, a in enumerate(names):
                for b in names[i + 1:] + others:
                    if (a, b) in allowed or (b, a) in allowed:
                        continue
                    if R._apart(box[a], box[b]):
                        continue
                    v = R._ivol(bpy.data.objects[a], bpy.data.objects[b])
                    if v > 1e-3 and v > worst.get((a, b), (0,))[0]:
                        worst[(a, b)] = (v, t, pan, tilt)
    blink(0.0)
    R.look(0, 0)
    if verbose:
        print("\n  DOES A LID HIT ANYTHING, ANYWHERE?")
        print("  (5 blink positions x 5 eye poses)")
        if not worst:
            print("    nothing touches that should not")
        for (a, b), (v, t, pan, tilt) in sorted(worst.items(),
                                                key=lambda kv: -kv[1][0]):
            print("    %-12s %-12s %8.2f mm3  at blink %.2f pan %+d tilt %+d ***"
                  % (a, b, v, t, pan, tilt))
        ok &= not worst
        print("\n  %s" % ("LIDS PASS" if ok else "*** LIDS FAILED"))
    return ok
