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

PIN_D, BORE_D = 3.0, 3.2        # pan pin, and the fork bore it turns in
PIN_Z = (-20.0, 17.0)           # ONE pin, right through the ball.  Printed, the
                                # ball and its pin are a single part, so two
                                # stubs would only be two things to snap off.

FORK_Z, FORK_T, FORK_W = 13.0, 3.0, 9.0     # 1 mm off a ball that ends at 12
FORK_Y = (22.0, 46.0)

WEB_Y = (43.0, 46.0)            # spine, behind balls that end at y 38.68
BAR_X, BAR_Z = 36.0, 5.0
TILT_X = (8.0, 14.0)            # tilt webs, in the corridor free at |x| < 19.5
SHAFT_D, SHAFT_X = 5.0, 14.0

LEV_R = 5.32                    # lever reaches FORWARD, past the pillar
LEV_Z = (-20.0, -17.0)
LNK_Z = (-23.0, -20.0)
LNK_PIN_D = 2.5

PIL_X, PIL_Y, PIL_Z = 5.0, (23.0, 29.0), (-42.0, 8.0)
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
SV_TILT = dict(p=(-19.78, 34.0, -36.0), shaft=(1, 0, 0), body=(0, 1, 0))
SHELF_X, SHELF_Y, SHELF_Z = (-15.0, 26.0), (46.0, 64.0), (-11.55, -9.05)

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


def _rodz(bm, r, z0, z1, cx, cy, segs=24):
    v = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                              radius1=r, radius2=r, depth=abs(z1 - z0))["verts"]
    bmesh.ops.translate(bm, verts=v, vec=Vector((cx, cy, (z0 + z1) / 2)))


def _frame_m(shaft, body):
    """Orientation matrix: local z onto `shaft`, local x onto `body`.  The
    proxy is drawn with z as its output shaft and x along its case."""
    z = Vector(shaft).normalized()
    x = Vector(body).normalized()
    x = (x - z * x.dot(z)).normalized()
    return Matrix((x, z.cross(x), z)).transposed().to_4x4()


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
        lambda bm: _box(bm, -DECK_X, DECK_X, DECK_Y[0], DECK_Y[1],
                        DECK_Z[0], DECK_Z[1]),
    ]
    cuts = [lambda bm: _rodx(bm, (SHAFT_D + 0.2) / 2, -PIL_X - 1, PIL_X + 1,
                             EYE_Y, EYE_Z)]
    return _obj("RIG_base", coll, parts, cuts)


def _frame(coll):
    """One part: two forks, a spine, and the tilt shaft they hang on."""
    parts = []
    for sx in (1, -1):
        x0, x1 = sx * EYE_X - FORK_W / 2, sx * EYE_X + FORK_W / 2
        for sz in (1, -1):
            parts.append(lambda bm, a=x0, b=x1, s=sz: _box(
                bm, a, b, FORK_Y[0], FORK_Y[1],
                s * FORK_Z, s * (FORK_Z + FORK_T)))
        parts.append(lambda bm, a=x0, b=x1: _box(
            bm, a, b, WEB_Y[0], WEB_Y[1], -(FORK_Z + FORK_T), FORK_Z + FORK_T))
        parts.append(lambda bm, s=sx: _box(
            bm, s * TILT_X[0], s * TILT_X[1], EYE_Y, WEB_Y[1],
            -SHAFT_D / 2 - 0.5, SHAFT_D / 2 + 0.5))
    parts.append(lambda bm: _box(bm, -BAR_X, BAR_X, WEB_Y[0], WEB_Y[1],
                                 -BAR_Z, BAR_Z))
    parts.append(lambda bm: _rodx(bm, SHAFT_D / 2, -SHAFT_X, SHAFT_X,
                                  EYE_Y, EYE_Z))
    # the tail, and the shelf the pan servo bolts to
    parts.append(lambda bm: _box(bm, -12.0, 12.0, WEB_Y[1] - 2.0,
                                 SHELF_Y[0] + 2.0, SHELF_Z[0], BAR_Z))
    parts.append(lambda bm: _box(bm, SHELF_X[0], SHELF_X[1],
                                 SHELF_Y[0], SHELF_Y[1],
                                 SHELF_Z[0], SHELF_Z[1]))
    cuts = [lambda bm, s=sx: _rodz(bm, BORE_D / 2, -(FORK_Z + FORK_T + 1),
                                   FORK_Z + FORK_T + 1, s * EYE_X, EYE_Y)
            for sx in (1, -1)]
    cuts.append(lambda bm: _rodz(bm, 4.0, SHELF_Z[0] - 1, SHELF_Z[1] + 1,
                                 SV_PAN["p"][0], SV_PAN["p"][1]))
    return _obj("RIG_frame", coll, parts, cuts, loc=(0.0, EYE_Y, EYE_Z))


def _pins(side, sx, coll):
    """Top and bottom pin plus the pan lever - what the printed ball carries.
    Kept off eye_L / eye_R so the balls themselves stay untouched."""
    cx = sx * EYE_X
    parts = [
        lambda bm: _rodz(bm, PIN_D / 2, PIN_Z[0], PIN_Z[1], cx, EYE_Y),
        lambda bm: _box(bm, cx - 1.5, cx + 1.5, EYE_Y - LEV_R - 2.0, EYE_Y,
                        LEV_Z[0], LEV_Z[1]),
        lambda bm: _rodz(bm, LNK_PIN_D / 2, LNK_Z[0], LEV_Z[1],
                         cx, EYE_Y - LEV_R),
    ]
    return _obj("RIG_pins_" + side, coll, parts, loc=(cx, EYE_Y, EYE_Z))


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
    link = _link(coll)
    pins = {s: _pins(s, sx, coll) for s, sx in (("L", 1), ("R", -1))}

    _servos(coll, frame)
    link.parent = frame
    link.matrix_parent_inverse = frame.matrix_world.inverted()
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
        link.location = (LEV_R * math.sin(p), LEV_R * (1 - math.cos(p)), 0.0)
    bpy.context.view_layer.update()


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


def _ivol(a, b):
    """Volume of the true solid overlap.  Sampled distance is blind to this."""
    tmp = a.copy()
    tmp.data = a.data.copy()
    bpy.context.scene.collection.objects.link(tmp)
    tmp.matrix_world = a.matrix_world
    m = tmp.modifiers.new(type="BOOLEAN", name="i")
    m.operation, m.object, m.solver = "INTERSECT", b, "EXACT"
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


# What is ALLOWED to touch: a pin in its bore, a pin in its link.
TOUCHING = {
    ("RIG_frame", "RIG_pins_L"), ("RIG_frame", "RIG_pins_R"),
    ("RIG_link", "RIG_pins_L"), ("RIG_link", "RIG_pins_R"),
    ("RIG_pins_L", "eye_L"), ("RIG_pins_R", "eye_R"),
    ("RIG_base", "RIG_frame"),
    ("RIG_frame", "SV_pan"),        # bolted to the shelf
    ("RIG_base", "SV_tilt"),        # sitting on the deck
}


def check(verbose=True):
    coll = bpy.data.collections[COLL]
    names = [o.name for o in coll.objects] + \
            [n for n in ("eye_L", "eye_R") if bpy.data.objects.get(n)]
    ok = True
    if verbose:
        print("\n  IS EACH PART ONE LUMP?")
        for o in coll.objects:
            if o.name.startswith("SV_"):
                continue
            n = _pieces(o)
            print("    %-14s pieces=%d %s" % (o.name, n, "" if n == 1 else "***"))
            ok &= n == 1

    worst = {}
    for pan, tilt in ((0, 0), (PAN_LIMIT, 0), (-PAN_LIMIT, 0),
                      (0, TILT_LIMIT), (0, -TILT_LIMIT),
                      (PAN_LIMIT, TILT_LIMIT), (-PAN_LIMIT, -TILT_LIMIT)):
        look(pan, tilt)
        bpy.context.view_layer.update()
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if (a, b) in TOUCHING or (b, a) in TOUCHING:
                    continue
                v = _ivol(bpy.data.objects[a], bpy.data.objects[b])
                if v > 1e-3:
                    k = (a, b)
                    if v > worst.get(k, (0,))[0]:
                        worst[k] = (v, pan, tilt)
    look(0, 0)

    if verbose:
        print("\n  DOES ANYTHING CRASH, ANYWHERE IN THE TRAVEL?")
        print("  (boolean, at pan +-%.0f and tilt +-%.0f)"
              % (PAN_LIMIT, TILT_LIMIT))
        if not worst:
            print("    nothing touches that should not")
        for (a, b), (v, pan, tilt) in sorted(worst.items(),
                                             key=lambda kv: -kv[1][0]):
            print("    %-14s %-14s %8.2f mm3  at pan %+.0f tilt %+.0f  ***"
                  % (a, b, v, pan, tilt))
        ok &= not worst
        print("\n  %s" % ("ALL CHECKS PASSED" if ok else "*** CHECK FAILED"))
    return ok
