"""Give every part in the head something to bolt to, and build the parts the
head itself needs.

Run inside Blender AFTER head_style.py has built HEAD_CYBORG and HEAD_SKIN,
and after fit_layout.py has placed FIT_Assembly. head_style.py must have been
exec'd into the same namespace, because `S` and `eye_axis` come from it:

    ns = {}
    for f in ("head_style", "head_mounts"):
        exec(compile(open(r"C:\\humalien\\humalien\\cad\\%s.py" % f).read(),
                     f, "exec"), ns)
        ns["build"]() if f == "head_style" else ns["build"](ns["S"],
                                                            ns["eye_axis"])

Before this pass every part in the fit study was floating. The layout was
honest about it - "the skull-side fixings on the parts are slotted precisely
because these numbers are guesswork until a head shell exists" - but a head
shell exists now, so the guessing is over.

The rule this file follows
--------------------------

**A screw is only worth drawing if a hand can reach it.** That one test
decides most of what follows, and it is why head_split.py exists: with the
face off, the cranium is an open bowl and every fixing below is reachable
from the front. Nothing here asks a screwdriver to turn a corner.

Two patterns, and the choice between them is about which side of the skin
the hand is on:

    boss      A post standing on the shell's inner surface, reaching out to
              meet the part's own mounting face; the screw goes in from the
              part's side. Used where the part is near a wall and the inside
              is open - the PCA9685 on the rear wall, the cable anchors, the
              forehead casing off the brow.

    through   A clearance hole in the skin, with the part behind it carrying
              the thread, so the screw head sits on the outside of the head.
              Used where a part cannot be reached from inside once fitted -
              the ear hubs, the tray rails. Visible fasteners are not a
              compromise: every reference photo is covered in them.

No boss length is guessed. Each is raycast from the part's fixing point to
the shell's inner surface, so the post is exactly as long as the gap it
crosses, and a re-run after a styling change re-measures instead of
re-guessing. The same trick shapes parts: build a lug deliberately too long,
subtract the head, and it comes back trimmed to the skin's curvature.

The parts this file builds
--------------------------

`ear_hub`       The port module the fit study left as PROXY_ear_hub_TBD: a
                Ø65 plug carrying the NeoPixel ring in a recess, the grille
                through its middle, the speaker on two posts behind it, and
                three arms reaching out to the shell.

                It fits from INSIDE, and it has to. The head's surface around
                the ear varies by 20 mm in depth across the Ø66 port, so
                there is no flat collar that could ever sit on that skin; and
                any arm long enough to reach the shell is wider than the bore
                it would have to pass through. Once the head splits, fitting
                from inside costs nothing - the cranium is an open bowl.

`eye_bezel`     Closes the 4.5 mm annulus between the Ø41 socket and the Ø32
                eyeball. Without it the eye reads as a ball dropped down a
                hole; with it, as an eye in a socket. Its front face is set
                from the shallowest point on the socket rim, measured, since
                the skin over the socket is not flat.

                A removable forehead panel was built here too and then
                deleted. The reasoning is kept in head_style.S under
                `brow_band`: the forehead drops 20 mm from the centreline to
                the temple across the width that panel wanted, and on a
                surface that steep its landing pads sit behind the skin in
                the middle and break out through it at the edges. The brow
                band is a groove now, and the camera is serviced by taking
                the face off, which is four screws either way.

`tray_rail`     A ledge each side for the Pi 5 tray. The tray's four slotted
                fixings sound like four bosses and cannot be: at tray height
                the skull is 120 mm across and the nearest floor is 100 mm
                below, so a post under a corner would be a 100 mm spike.
                Ledges off the side walls are what the geometry allows,
                and eye_mech's pi5_tray gained four side fixings to land on
                them.

Booleans are batched and baked: everything being added to the shell is
joined and unioned once, everything being cut is joined and subtracted once,
and the file saves between stages. A live stack of booleans over this sculpt
has taken Blender down before. They run on the MANIFOLD solver - see
`boolean` for the three separate ways EXACT failed on this shell.

Two traps in here cost more time than the geometry did, and both are silent:
a boolean whose cutter object the depsgraph has not seen evaluates against
nothing, and a boolean on an object in a hidden collection bakes the mesh it
already had. Neither raises. `_bake` and `_ensure_evaluable` exist for them.
"""

import bpy
import bmesh
import math
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

COLL = "MOUNT_Parts"
HEAD = "HEAD_CYBORG"
SKIN = "HEAD_SKIN"

M = dict(
    m3_free   = 3.4,      # clearance for an M3
    m3_pilot  = 2.6,      # self-tapping pilot in PLA for an M3
    m2_pilot  = 1.7,
    boss_d    = 10.0,
    wall      = 4.0,

    ear       = dict(y=95.0, z=204.0, bore=66.0,
                     plug_d=65.0,        # 0.5 clearance in the Ø66 bore
                     plug_t=8.0,
                     face_x=47.5,        # outer face, behind the deepest rim
                     ring_od=37.6,       # 36.83 + fit
                     ring_t=6.9,         # 6.7 + fit
                     grille=22.0,        # aperture under the ring's Ø23.4 ID
                     arm_r=36.0,         # screw circle, outside the Ø66 bore
                     arm_d=13.0,
                     arm_a=(90.0, 210.0, 330.0),   # deg, 0 = +y
                     spk_pitch=72.0,     # LISTING - flange holes unmeasured
                     spk_post=6.0,
                     spine=(16.0, 90.0, 4.0)),

    # idia was 33.6, which measured 1.29 mm from the eyeball at its closest -
    # no intersection, but too close to look right and too close to trust
    # once there is a real gimbal in there instead of a perfect sphere.
    # 35.6 puts 2.3 mm all round and still closes most of the 4.5 mm annulus
    # the Ø41 socket leaves around a Ø32 ball.
    eye       = dict(pitch=62.0, y=160.0, z=209.0, socket=41.0,
                     od=40.4, idia=35.6, t=6.0, ball=32.0, recess=1.5),

    # Pi 5 tray: plate z 256..259, slots at (0,131.5) (0,48.5) (+-27, 90)
    tray      = dict(z=256.0, slot_x=27.0, slot_y=(60.0, 120.0),
                     rail_y0=54.0, rail_y1=126.0, rail_t=6.0, rail_x0=22.0,
                     screw_y=(70.0, 110.0)),
)

# Every fixing that gets a boss: (label, world point on the part's mounting
# face, unit direction from that point towards the shell, screw size).
#
# forehead_casing  three slots along the plate's bottom strip, front face
#                  y=167; posts run forward to the brow and the screw goes
#                  in from behind, which is open once the face is off
# pca9685_mount    four corner slots, back face y=42, posts back to the rear
#                  wall. That wall bows 13 mm across the plate, which is
#                  exactly why these are measured one by one
# cable_anchor     two on the rear wall, two on the side walls
#
# `lift` raises the point the ray is fired from without moving the screw.
# The casing's two outer fixings sit at z=229 and the Ø41 eye socket reaches
# z=229.5, so at x=±35 a ray fired forward leaves through the eye opening and
# finds no shell at all. Fired 4 mm higher it lands on the brow, and a Ø15
# post still puts 6 mm of material around a pilot drilled at the true
# height. The alternative was raising the whole casing 2 mm, which spends
# the brow clearance that was just bought back.
BOSSES = [
    ("casing_R",   Vector(( 35.0, 167.0, 229.0)), Vector((0, 1, 0)),  "m3",
     dict(lift=Vector((0, 0, 4.0)), dia=15.0)),
    ("casing_C",   Vector((  0.0, 167.0, 229.0)), Vector((0, 1, 0)),  "m3", {}),
    ("casing_L",   Vector((-35.0, 167.0, 229.0)), Vector((0, 1, 0)),  "m3",
     dict(lift=Vector((0, 0, 4.0)), dia=15.0)),
    ("pca_RT",     Vector(( 34.1,  42.0, 245.7)), Vector((0, -1, 0)), "m3", {}),
    ("pca_LT",     Vector((-34.1,  42.0, 245.7)), Vector((0, -1, 0)), "m3", {}),
    ("pca_RB",     Vector(( 34.1,  42.0, 214.3)), Vector((0, -1, 0)), "m3", {}),
    ("pca_LB",     Vector((-34.1,  42.0, 214.3)), Vector((0, -1, 0)), "m3", {}),
    ("anchor_1",   Vector((  7.6,  35.0, 240.0)), Vector((0, -1, 0)), "m2", {}),
    ("anchor_2",   Vector(( -7.6,  35.0, 240.0)), Vector((0, -1, 0)), "m2", {}),
    ("anchor_3",   Vector(( 40.0,  92.0, 164.4)), Vector((1, 0, 0)),  "m2", {}),
    ("anchor_4",   Vector((-40.0,  92.0, 164.4)), Vector((-1, 0, 0)), "m2", {}),
]
# The tray's own front and rear fixings, at (0, 131.5) and (0, 48.5), get
# nothing. There is no wall behind the rear one - that is where the cranial
# opening is - and the shell in front of the other one is the forehead,
# 62 mm away. The tray hangs off its four side fixings on the two rails
# instead, which is why eye_mech.pi5_tray gained four of them.

COL_MOUNT = (0.85, 0.45, 0.10, 1.0)
COL_HUB = (0.10, 0.10, 0.12, 1.0)


# ---------------------------------------------------------------------------
# primitives - all append into a caller-owned bmesh, so a whole batch of
# added or removed geometry ends up as one object and one boolean
# ---------------------------------------------------------------------------
def _mesh(name, bm):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def _link(coll, name, me, color=COL_MOUNT):
    ob = bpy.data.objects.new(name, me)
    ob.color = color
    coll.objects.link(ob)
    return ob


def _merge(bm, tmp):
    me = bpy.data.meshes.new("_t")
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    return bm


def _cyl(bm, d, length, loc, axis='Z', d2=None, segs=48, direction=None):
    tmp = bmesh.new()
    bmesh.ops.create_cone(tmp, cap_ends=True, radius1=d / 2,
                          radius2=(d if d2 is None else d2) / 2,
                          depth=length, segments=segs)
    if direction is not None:
        bmesh.ops.transform(
            tmp, verts=tmp.verts[:],
            matrix=Vector((0, 0, 1)).rotation_difference(
                Vector(direction).normalized()).to_matrix().to_4x4())
    elif axis in ('X', 'Y'):
        bmesh.ops.transform(tmp, verts=tmp.verts[:],
                            matrix=Matrix.Rotation(math.radians(90), 4,
                                                   'Y' if axis == 'X' else 'X'))
    bmesh.ops.transform(tmp, verts=tmp.verts[:], matrix=Matrix.Translation(loc))
    return _merge(bm, tmp)


def _box(bm, dims, loc):
    tmp = bmesh.new()
    bmesh.ops.create_cube(tmp, size=1.0)
    bmesh.ops.scale(tmp, vec=dims, verts=tmp.verts[:])
    bmesh.ops.transform(tmp, verts=tmp.verts[:], matrix=Matrix.Translation(loc))
    return _merge(bm, tmp)


def _rrect(bm, w, h, r, length, loc, plane='XZ'):
    """Rounded rect in the given plane, extruded along the third axis."""
    r = max(0.01, min(r, w / 2 - 0.01, h / 2 - 0.01))
    pts = []
    segs = 8
    for (ox, oy, a0) in ((w / 2 - r, h / 2 - r, 0.0),
                         (-(w / 2 - r), h / 2 - r, 90.0),
                         (-(w / 2 - r), -(h / 2 - r), 180.0),
                         (w / 2 - r, -(h / 2 - r), 270.0)):
        for i in range(segs + 1):
            a = math.radians(a0 + 90.0 * i / segs)
            pts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    tmp = bmesh.new()
    if plane == 'XZ':                          # extruded along Y
        bot = [tmp.verts.new((px, -length / 2, py)) for (px, py) in pts]
        top = [tmp.verts.new((px, length / 2, py)) for (px, py) in pts]
    else:                                      # 'YZ', extruded along X
        bot = [tmp.verts.new((-length / 2, px, py)) for (px, py) in pts]
        top = [tmp.verts.new((length / 2, px, py)) for (px, py) in pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        tmp.faces.new((bot[i], bot[j], top[j], top[i]))
    tmp.faces.new(bot[::-1])
    tmp.faces.new(top)
    bmesh.ops.transform(tmp, verts=tmp.verts[:], matrix=Matrix.Translation(loc))
    return _merge(bm, tmp)


# ---------------------------------------------------------------------------
def _ensure_evaluable(ob):
    """Un-hide whatever collection `ob` is in, and its view-layer entry.

    A collection with hide_viewport set, or excluded from the view layer, is
    not evaluated - so a boolean modifier on an object inside it bakes to
    the mesh it already had, reports success, and changes nothing. The
    forehead casing and the Pi tray live in HUMALIEN, which gets hidden any
    time somebody wants a clean look at the shell, and both edits below
    silently did nothing until that was noticed.
    """
    for c in ob.users_collection:
        c.hide_viewport = False

    def walk(lc):
        if lc.collection in set(ob.users_collection):
            lc.exclude = False
            lc.hide_viewport = False
        for ch in lc.children:
            walk(ch)
    walk(bpy.context.view_layer.layer_collection)
    ob.hide_set(False)
    bpy.context.view_layer.update()
    return ob


def _bake(ob):
    # Not optional. A cutter created earlier in the same script run is not in
    # the depsgraph until the view layer is updated, and a boolean modifier
    # pointed at an object the depsgraph has never seen evaluates against
    # nothing: INTERSECT returns an empty mesh and DIFFERENCE returns the
    # target untouched, both silently. That cost an hour.
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    baked = bpy.data.meshes.new_from_object(ob.evaluated_get(dg),
                                            preserve_all_data_layers=True,
                                            depsgraph=dg)
    old = ob.data
    ob.modifiers.clear()
    ob.data = baked
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return baked


def boolean(target, cutter, op='DIFFERENCE', solver='MANIFOLD'):
    """MANIFOLD, not EXACT.

    EXACT was the default here and it failed three different ways on this
    shell in one afternoon: it deleted a 3688-vertex panel down to nothing
    against a cutter whose countersink cone shared a cylindrical surface
    with its own clearance hole, it reduced the ear hub to 110 vertices, and
    it turned a 135k head into 2016 vertices on a union with twelve
    disjoint posts. All three survive MANIFOLD, which Blender 5 added for
    exactly this and which both inputs here qualify for - the shell tests
    manifold with zero boundary and zero non-manifold edges, and every
    cutter is a closed primitive.
    """
    mod = target.modifiers.new(op, 'BOOLEAN')
    mod.operation = op
    mod.solver = solver
    mod.object = cutter
    _bake(target)
    return target


def _apply(coll, target, bm, name, op):
    """One batched boolean: turn a bmesh into an object, use it, drop it.

    An empty cutter is refused rather than run. A boolean against an empty
    mesh does not no-op - it returns rubble, and it took a run where every
    boss silently failed to measure, leaving an empty batch, to turn a 138k
    head into 781 vertices.
    """
    if not bm.verts:
        bm.free()
        print("    %s: EMPTY, boolean skipped" % name)
        return
    ob = _link(coll, name, _mesh(name, bm))
    boolean(target, ob, op)
    bpy.data.objects.remove(ob, do_unlink=True)


class Probe:
    """Ray queries against the shell and against the single-surface skin.

    `inner` walks out from a point inside the head to the shell, which is
    what a boss has to reach. `skin` does the same against HEAD_SKIN, which
    is where a pad or a countersink has to sit relative to.
    """

    def __init__(self):
        # Same trap as _bake. If head_style.build() ran earlier in this same
        # script, the depsgraph still holds whatever HEAD_CYBORG was before
        # it, and every ray fired at it misses a head that no longer exists.
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        self.trees = {}
        for name in (HEAD, SKIN):
            ob = bpy.data.objects[name]
            bm = bmesh.new()
            bm.from_object(ob, dg)
            bm.transform(ob.matrix_world)
            self.trees[name] = BVHTree.FromBMesh(bm)
            bm.free()

    def hit(self, which, origin, direction, dist=400.0):
        loc, nrm, idx, d = self.trees[which].ray_cast(
            Vector(origin), Vector(direction).normalized(), dist)
        return loc, d

    def inner(self, origin, direction):
        return self.hit(HEAD, origin, direction)

    def skin(self, origin, direction):
        return self.hit(SKIN, origin, direction)


# ---------------------------------------------------------------------------
# stage 1 - the brow panel, carved out of the shell before anything else
#           touches it
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# parts that are shaped by the shell
# ---------------------------------------------------------------------------
def ear_hubs(probe, coll, head):
    e = M["ear"]
    fx = e["face_x"]
    body = bmesh.new()
    _cyl(body, e["plug_d"], e["plug_t"], (fx - e["plug_t"] / 2, e["y"], e["z"]), 'X')
    # Each arm is measured to its own bit of wall. Running them long and
    # letting the shell trim them only works for the part of an arm that is
    # INSIDE the wall - anything that reaches past the outer surface is in
    # free air, nothing subtracts it, and it comes out as a 24 mm spike
    # through the side of the head. So each arm stops 2 mm past the inner
    # surface and the subtract tidies the last 2 mm.
    for a in e["arm_a"]:
        ay = e["y"] + e["arm_r"] * math.cos(math.radians(a))
        az = e["z"] + e["arm_r"] * math.sin(math.radians(a))
        # half a millimetre SHORT of the inner surface. Overshooting and
        # letting the subtract trim the arm looks tidier until you notice
        # that the wall is slanted here, so the far side of a flat Ø13 end
        # face pushes 4 mm past the outer skin and comes back as a loose
        # island floating outside the head.
        loc, d = probe.inner((0.0, ay, az), (1, 0, 0))
        end = (loc.x if loc else fx) - 0.5
        start = fx - e["plug_t"]
        _cyl(body, e["arm_d"], end - start, ((start + end) / 2, ay, az), 'X')
    # spine across the back of the plug, carrying the two speaker posts
    sw, sh, st = e["spine"]
    _box(body, (st, sw, sh), (fx - e["plug_t"] - st / 2 + 0.01, e["y"], e["z"]))
    for sz in (-1, 1):
        _cyl(body, 9.0, e["spk_post"] + st,
             (fx - e["plug_t"] - st / 2 - e["spk_post"] / 2, e["y"],
              e["z"] + sz * e["spk_pitch"] / 2), 'X')
    hub = _link(coll, "ear_hub_R", _mesh("ear_hub_R", body), COL_HUB)
    boolean(hub, head)                    # trims arms and spine to the shell

    hcut = bmesh.new()
    # anything the arms left sticking forward inside the bore
    _cyl(hcut, e["bore"], 80.0, (fx + 40.0, e["y"], e["z"]), 'X')
    # ring recess, then the aperture through the middle
    _cyl(hcut, e["ring_od"], e["ring_t"] * 2, (fx, e["y"], e["z"]), 'X')
    _cyl(hcut, e["grille"], 80.0, (fx - 20.0, e["y"], e["z"]), 'X')
    for a in e["arm_a"]:
        ay = e["y"] + e["arm_r"] * math.cos(math.radians(a))
        az = e["z"] + e["arm_r"] * math.sin(math.radians(a))
        _cyl(hcut, M["m3_pilot"], 34.0, (fx - 2.0, ay, az), 'X', segs=24)
    for sz in (-1, 1):
        _cyl(hcut, M["m3_pilot"], 16.0,
             (fx - e["plug_t"] - 4.0, e["y"],
              e["z"] + sz * e["spk_pitch"] / 2), 'X', segs=24)
    _apply(coll, hub, hcut, "_CUT_hub", 'DIFFERENCE')

    left = hub.copy()
    left.data = hub.data.copy()
    left.name = "ear_hub_L"
    left.data.name = "ear_hub_L"
    left.data.transform(Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0)))
    if hasattr(left.data, "flip_normals"):
        left.data.flip_normals()
    coll.objects.link(left)
    left.color = COL_HUB
    print("  ear_hub_R/L: %d verts, Ø%.0f plug, ring recess Ø%.1f, 3 x M3"
          % (len(hub.data.vertices), e["plug_d"], e["ring_od"]))
    return hub, left


def eye_bezels(probe, coll, eye_axis):
    """A ring in each socket, on the socket's own raked axis.

    Where the face sits is measured, not assumed: rays are fired down the
    bore axis onto the shell at twelve points around the rim, and the face
    goes 1.5 mm behind the shallowest of them. Fire them at the SHELL and
    not at HEAD_SKIN - the skin has a hole punched through it wherever the
    eye pre-clean removed the lash cards, and rays aimed there sail straight
    through the head and report the back of the skull.
    """
    e = M["eye"]
    out = []
    for sx, side in ((1, "R"), (-1, "L")):
        ax = eye_axis(sx)
        org = Vector((sx * e["pitch"] / 2.0, e["y"], e["z"]))
        # two vectors spanning the plane the ring lives in
        u = ax.cross(Vector((0, 0, 1)))
        u = (u if u.length > 1e-3 else ax.cross(Vector((1, 0, 0)))).normalized()
        v = ax.cross(u).normalized()
        depths = []
        for a in range(0, 360, 30):
            p = (org + (u * math.cos(math.radians(a))
                        # 1.5 OUTSIDE the bore. Sample inside it and the ray
                        # goes down the open socket and hits the back of the
                        # skull 260 mm later.
                        + v * math.sin(math.radians(a))) * (e["socket"] / 2 + 1.5))
            loc, d = probe.inner(p + ax * 120.0, -ax)
            if loc:
                depths.append(120.0 - d)          # along the axis from org
        rim = min(depths) if depths else 16.0
        face = rim - e["recess"]
        bm = bmesh.new()
        _cyl(bm, e["od"], e["t"], org + ax * (face - e["t"] / 2), direction=ax)
        cut = bmesh.new()
        # Bore Ø33.6 at the FRONT, opening out behind so the ring never
        # fouls the eyeball at full deflection. The taper was the other way
        # round at first, which put a Ø42 mouth exactly where the Ø40.4 ring
        # was and deleted the whole part.
        _cyl(cut, e["ball"] + 10.0, 40.0, org + ax * (face - 20.0 + 0.01),
             direction=ax, d2=e["idia"])
        ob = _link(coll, "eye_bezel_%s" % side,
                   _mesh("eye_bezel_%s" % side, bm), COL_HUB)
        _apply(coll, ob, cut, "_CUT_bez_%s" % side, 'DIFFERENCE')
        out.append(ob)
        if sx == 1:
            print("  eye_bezel_R/L: Ø%.1f in the Ø%.0f socket; rim spread "
                  "%.1f mm along the bore, face %.1f mm out from the eyeball"
                  % (e["od"], e["socket"], max(depths) - min(depths), face))
    return out


def tray_rails(probe, coll, head, shell_cut):
    t = M["tray"]
    rails = []
    for sx, side in ((1, "R"), (-1, "L")):
        # Same rule as the ear-hub arms: size to the measured wall, do not
        # run long and hope the shell trims it. Take the nearest wall over
        # the rail's length so no part of it breaks out.
        zc = t["z"] - t["rail_t"] / 2
        reach = []
        for sy in (t["rail_y0"] + 4.0, (t["rail_y0"] + t["rail_y1"]) / 2,
                   t["rail_y1"] - 4.0):
            loc, d = probe.inner((0.0, sy, zc), (sx, 0, 0))
            if loc:
                reach.append(abs(loc.x))
        outer = (min(reach) if reach else 55.0) + 2.0
        w = outer - t["rail_x0"]
        bm = bmesh.new()
        _box(bm, (w, t["rail_y1"] - t["rail_y0"], t["rail_t"]),
             (sx * (t["rail_x0"] + w / 2), (t["rail_y0"] + t["rail_y1"]) / 2, zc))
        ob = _link(coll, "tray_rail_%s" % side, _mesh("tray_rail_%s" % side, bm))
        boolean(ob, head)                 # outboard end matched to the wall
        rcut = bmesh.new()
        for sy in t["slot_y"]:
            _cyl(rcut, M["m3_pilot"], t["rail_t"] + 6.0,
                 (sx * t["slot_x"], sy, t["z"] - t["rail_t"] / 2), 'Z', segs=24)
        for sy in t["screw_y"]:
            loc, d = probe.skin((sx * 200.0, sy, t["z"] - t["rail_t"] / 2),
                                (-sx, 0, 0))
            if loc is None:
                continue
            _cyl(rcut, M["m3_pilot"], 26.0,
                 (loc.x - sx * 13.0, sy, t["z"] - t["rail_t"] / 2), 'X', segs=24)
            _cyl(shell_cut, M["m3_free"], 30.0,
                 (loc.x - sx * 5.0, sy, t["z"] - t["rail_t"] / 2), 'X', segs=24)
        _apply(coll, ob, rcut, "_CUT_rail_%s" % side, 'DIFFERENCE')
        rails.append(ob)
    print("  tray_rail_R/L: ledge top z=%.0f, 2 tray fixings each at x=±%.0f "
          "y=%s, 2 x M3 through the skin each"
          % (t["z"], t["slot_x"], t["slot_y"]))
    return rails


def tray_side_slots():
    """Add four side fixings to pi5_tray.

    The tray shipped with fixings at the middle of all four edges. Two of
    them are unusable in this head (see the note under BOSSES), which left
    the tray on a two-point mount free to pivot about its own long axis.
    Four slots along the long edges, over the rails, is the fix. Cut into
    the existing mesh rather than rebuilt: eye_mech.py's full rebuild has
    taken Blender down twice over this bridge. The source is updated to
    match, so a clean rebuild produces the same part.
    """
    ob = bpy.data.objects.get("pi5_tray")
    if ob is None:
        print("  pi5_tray not in scene - skipping side slots")
        return None
    _ensure_evaluable(ob)
    t = M["tray"]
    cut = bmesh.new()
    for lx in (-30.0, 30.0):
        for ly in (-27.0, 27.0):
            # slotted like every other skull-side fixing: 1 mm of travel
            for dx in (-0.5, 0.5):
                _cyl(cut, M["m3_free"], 40.0, (lx + dx, ly, 0.0), 'Z', segs=24)
            _box(cut, (1.0, M["m3_free"], 40.0), (lx, ly, 0.0))
    # The parts are laid out on a grid by eye_mech.lay_out, so pi5_tray is
    # nowhere near the origin. Booleans work in world space; the slot
    # positions above are part-local, so they have to be carried there.
    me_cut = _mesh("_CUT_tray_slots", cut)
    me_cut.transform(ob.matrix_world)
    ob_cut = bpy.data.objects.new("_CUT_tray_slots", me_cut)
    bpy.context.scene.collection.objects.link(ob_cut)
    boolean(ob, ob_cut)
    bpy.data.objects.remove(ob_cut, do_unlink=True)
    print("  pi5_tray: 4 side fixings added at local (±30, ±27) -> world "
          "(±%.0f, %s)" % (t["slot_x"], t["slot_y"]))
    return ob


# ---------------------------------------------------------------------------
# stage 3 - everything added to and cut from the shell, in two booleans
# ---------------------------------------------------------------------------
def bosses(probe, add, cut):
    rows = []
    for label, pt, d, size, opt in BOSSES:
        lift = opt.get("lift", Vector((0, 0, 0)))
        loc, dist = probe.inner(pt + lift + d * 0.5, d)
        if loc is None or dist > 60.0:
            rows.append((label, None))
            continue
        axis = 'X' if abs(d.x) > 0.5 else ('Y' if abs(d.y) > 0.5 else 'Z')
        length = dist + 5.0
        _cyl(add, opt.get("dia", M["boss_d"]), length,
             pt + lift + d * (length / 2.0 - 1.5), axis)
        pd = M["m3_pilot"] if size == "m3" else M["m2_pilot"]
        plen = dist + 2.0
        _cyl(cut, pd, plen, pt + d * (plen / 2.0 - 1.0), axis, segs=24)
        rows.append((label, dist))
    print("  bosses - gap each post crosses, mm:")
    for label, dist in rows:
        print("    %-11s %s" % (label, "NO SHELL FOUND" if dist is None
                                else "%5.1f" % dist))
    return rows


def casing_chamfer():
    """Take the forehead casing's unused top corners off.

    The other half of the brow debt. The fit study measured the casing
    breaking out through the brow flanks by 10.3 mm and named two fixes; the
    brow swell in head_style got that down to 4.6 mm, all of it in the
    plate's two top corners, and this removes them.

    The line is measured, not chosen. Every casing vertex still outside the
    skin was listed with its local coordinates: they run local |x| 42.8..48,
    y 26..29, and the smallest value of 6|x| + 3.5y among them is 348. The
    cut takes 6|x| + 3.5y > 332, which clears the furthest-in of them by
    2.7 mm - 340 was tried first and left a single vertex of the chamfer's
    own new corner 0.4 mm proud. A first attempt used 368.5, which sounded close enough and
    removed a 1.6 mm sliver off a corner that was already radiused - a
    reminder that on a rounded corner the chamfer has to be sized against
    where the material actually is.

    332 costs nothing that is in use. It bites the plate from (38.4, 29) to
    (48, 12.6); the camera pocket stops at local x=-42 and its screws at
    -36, and the ToF channel stops at +43.8 and loses only the top 7 mm of
    its outboard lead-in lip, well above the y=17.5 the board reaches.

    Cut into the existing mesh rather than rebuilt, for the same reason as
    the tray slots; eye_mech.py's source carries the same chamfer so a clean
    rebuild produces the same part.
    """
    ob = bpy.data.objects.get("forehead_casing")
    if ob is None:
        print("  forehead_casing not in scene - skipping chamfer")
        return None
    _ensure_evaluable(ob)
    # half-space 6*|x| + 3.5*y > 332, one per top corner
    n = Vector((6.0, 3.5, 0.0)).normalized()
    ang = math.atan2(n.y, n.x)
    cut = bmesh.new()
    for sx in (1, -1):
        tmp = bmesh.new()
        bmesh.ops.create_cube(tmp, size=1.0)
        bmesh.ops.scale(tmp, vec=(120.0, 120.0, 40.0), verts=tmp.verts[:])
        bmesh.ops.transform(tmp, verts=tmp.verts[:],
                            matrix=Matrix.Rotation(sx * ang, 4, 'Z'))
        c = Vector((sx * 38.4, 29.0, 2.5)) + Vector((sx * n.x, n.y, 0.0)) * 60.0
        bmesh.ops.transform(tmp, verts=tmp.verts[:], matrix=Matrix.Translation(c))
        _merge(cut, tmp)
    me_cut = _mesh("_CUT_chamfer", cut)
    me_cut.transform(ob.matrix_world)
    ob_cut = bpy.data.objects.new("_CUT_chamfer", me_cut)
    bpy.context.scene.collection.objects.link(ob_cut)
    boolean(ob, ob_cut)
    bpy.data.objects.remove(ob_cut, do_unlink=True)
    print("  forehead_casing: top corners chamfered")
    return ob


def ear_screw_holes(cut):
    e = M["ear"]
    for sx in (1, -1):
        for a in e["arm_a"]:
            ay = e["y"] + e["arm_r"] * math.cos(math.radians(a))
            az = e["z"] + e["arm_r"] * math.sin(math.radians(a))
            _cyl(cut, M["m3_free"], 70.0, (sx * 45.0, ay, az), 'X', segs=24)


# ---------------------------------------------------------------------------
def build(S=None, eye_axis=None, save=True):
    head = bpy.data.objects[HEAD]
    c = bpy.data.collections.get(COLL)
    if c:
        for ob in list(c.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(c)
    coll = bpy.data.collections.new(COLL)
    bpy.context.scene.collection.children.link(coll)

    print("head_mounts:")
    probe = Probe()

    shell_cut = bmesh.new()
    ear_hubs(probe, coll, head)
    if eye_axis is not None:
        eye_bezels(probe, coll, eye_axis)
    tray_rails(probe, coll, head, shell_cut)
    tray_side_slots()
    casing_chamfer()
    if save:
        bpy.ops.wm.save_mainfile()

    add = bmesh.new()
    bosses(probe, add, shell_cut)
    ear_screw_holes(shell_cut)
    _apply(coll, head, add, "_ADD_mounts", 'UNION')
    _apply(coll, head, shell_cut, "_CUT_holes", 'DIFFERENCE')

    me = head.data
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    if hasattr(me, "set_sharp_from_angle"):
        me.set_sharp_from_angle(angle=math.radians(40.0))
    me.update()
    print("  head now %d verts" % len(me.vertices))
    if save:
        bpy.ops.wm.save_mainfile()
    return coll
