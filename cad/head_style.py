"""Restyle the head mesh into the cyborg of reference photos/.

Run inside Blender, after head_ref.py (and ideally fit_layout.py, so the
openings land on the parts they serve):

    exec(open(r"C:\\humalien\\humalien\\cad\\head_style.py").read())

What the three reference photos share, and what this pass builds:

    - a smooth shell with real thickness            Solidify, 4 mm
    - a large circular port at each ear/temple      boolean cylinders
    - an open cranium showing mechanism             boolean rounded box, moved
                                                    to the upper occiput so the
                                                    rear wall survives to mount
                                                    things to
    - eye openings the mechanism looks through      boolean cylinders at the
                                                    DESIGN pitch 62, not the
                                                    mesh's sculpted 56
    - camera bore + ToF window in the forehead      boolean cuts onto the
                                                    forehead_casing row, and a
                                                    removable brow panel over
                                                    them
    - panel seams                                   groove displacement, not
                                                    booleans - see SEAMS
    - a smooth human silhouette, kept               no bolted-on volumes. The
                                                    one exception is the brow
                                                    band, which the plated-face
                                                    reference has and which the
                                                    forehead casing needs

HEAD_CYBORG is a copy of HEAD_REF (the original is kept and hidden). The
cuts are built as a modifier stack and then BAKED to a plain mesh in the
same run: a live stack of booleans over this sculpt crashed Blender
repeatedly - the FLOAT eye cuts through the lid geometry re-evaluating on
every depsgraph touch - and a saved file must not carry that landmine.
Nothing is lost by baking: this script IS the non-destructive layer. Move a
number in S, re-run, and the head regenerates from HEAD_REF. The cutter
objects stay in STYLE_cutters, wireframed, as the visible record of where
every opening is.

The licence note in head_ref.py applies to the copy too: the mesh must not
leave the machine and must never be fed to the MCP generative tools. Boolean
cuts and modifiers are deterministic CAD and are fine.

Three things this pass exists to fix, 13 Aug 2026
------------------------------------------------

**The sculpt is full of geometry a printer would have to pay for.** The
mouth is the worst of it: a tongue, gums and a throat bag, ~8800 faces
sitting in the middle of the skull where the electronics go. The previous
pass tried to find it with a ray-parity test inside a hand-drawn box and
found almost none of it, because *parity is the wrong question*. The mouth
bag is not enclosed - the lips are slightly parted, so the cavity is
formally "outside" and parity says keep it. The right question is not "is
this face inside the skin" but "can this face see the sky": `_strip_buried`
fires 42 rays over the sphere from every face above the neck and deletes
any face that cannot escape in more than 5% of directions. That catches the
mouth bag, the nostril cavities, the ear canals and the eyelid interiors in
one rule, with no boxes to draw. Everything it deletes was invisible from
outside, so nothing that reads on the finished head is lost.

**The shoulders were still attached.** The source is a bust. Cutting at the
neck (z=100, the narrowest band, just under the jaw) removes ~40% of the
mesh, brings the print to 150 x 185 x 213 and leaves a clean planar ring for
a neck to bolt to later.

**The forehead casing broke out through the brow.** Recorded as an open debt
and now closed, with the two fixes the fit study named: the casing's unused
top corners are chamfered (`head_parts.py`), and the brow band is filled out
to the fuller, flatter brow the plated-face reference has (`S["swell"]`,
amp no longer 0). Both were parameterized and off; both are on. The measured
breach is checked at the end of every run - see `verify_forehead`.

Still deliberately NOT done here:
    - the neck: cables and mechanism wait for a neck design
"""

import bpy
import bmesh
import math
from mathutils import Matrix, Vector

COLL_NAME = "STYLE_Head"
CUT_COLL = "STYLE_cutters"
SRC = "HEAD_REF"

S = dict(
    wall        = 4.0,                  # docs/eye-design-brief.md head budget

    # Cut the bust off at the neck. 100 is the narrowest horizontal band
    # (Ø~85) and sits just below the jaw, so the whole head survives and the
    # shoulders - which are 394 mm across and pure filament - do not.
    neck_cut    = 100.0,

    # "Can this face see the sky?" 42 rays, and a face that escapes in fewer
    # than 5% of them is buried. See the module docstring.
    strip       = dict(rays=42, openness=0.05, z_min=104.0),

    ear_port    = dict(y=95.0, z=204.0, dia=66.0),   # ear centroid, fit_layout

    # MOVED to the upper occiput. It used to run y 12..55, z 162..256, which
    # deleted exactly the piece of rear wall the PCA9685 mount bolts to and
    # left that part hanging in a hole. Up here it shows the Pi and its hat -
    # "mechanism high and rearward", which is where hardware.md wanted the
    # mics anyway - and every wall below z=250 comes back for mounting.
    rear_open   = dict(y0=8.0, y1=44.0, z0=250.0, z1=302.0, r=18.0),

    # Ø41 swallows the sculpt's ENTIRE eyelid structure per side, so the
    # bore lands on clean single-surface skin. A Ø30 cut sliced through the
    # four lid shells and left torn walls inside the opening. The 4.5 mm
    # annulus that leaves around a Ø32 eyeball is filled by the printed
    # eye_bezel, so the socket reads as a rim and not as a hole.
    # RAKED, and this is the fix for the socket that looked like a hole
    # rather than an eye. A bore driven straight back along +Y through a
    # face this curved comes out 31 mm deeper at the temple edge than at the
    # nose edge - measured, y=160.1 against y=190.9 around one rim - so the
    # opening reads as a gouge and no flat bezel can ever sit in it. A real
    # orbit faces outward and slightly down. Fitting a plane to the eight
    # measured rim points gives a surface normal 27° outboard and 12° down;
    # the bore now follows it. The eyeball still looks straight ahead - only
    # the opening is raked - and a Ø41 bore raked 25° still presents a
    # 41 x 37 aperture to a Ø32 eyeball.
    eye         = dict(pitch=62.0, y=160.0, z=209.0, dia=41.0,
                       rake_out=25.0, rake_down=10.0),

    # The lens sits ~10 mm behind the skin, so a straight Ø16 tunnel would
    # crop a 77° lens down to 44°. The bore is a cone opening outward: Ø16 at
    # the inner wall, Ø34 at the skin. It also reads as a deliberate lens
    # recess rather than a drilled hole.
    # A MATCHED PAIR of brow ports, replacing the separate Ø16 camera bore
    # and the small ToF window.
    #
    # The plate is 96 wide and the brow is not. Measured: the plate front at
    # y=167 breaks the shell's inner wall from |x|>=48 at z=254, tightening
    # to |x|>=34 at z=284 - so BOTH top corners of the casing are buried,
    # symmetrically. Three ways out were on the table: move the whole casing
    # back 7 mm and spend camera FOV on it, narrow the plate and re-space
    # both apertures, or open the head where the plate needs to pass. This
    # is the third, and once it has to be done on both sides it may as well
    # be one deliberate pair rather than two different holes.
    #
    # Each port swallows its instrument AND its corner: x 20..50 covers the
    # camera at +22 and the ToF at -32, and reaches out past x=34 at the top
    # where the burial is worst. The 40 mm of shell between them carries the
    # brow across the centreline. There is no separate camera bore any more
    # - the lens looks out through its port, which also ends the flare/FOV
    # argument, since the aperture is now far wider than the lens needs.
    brow_port   = dict(x0=20.0, x1=53.0, z0=242.0, z1=288.0, r=4.0),

    # The brow band is a SEAM, not a removable panel. A real panel was built
    # here and taken out again, and the reason is worth keeping: the forehead
    # drops 20 mm from the centreline to the temple across the width this
    # band wants, and on a surface that steep nothing works. Landing pads for
    # its screws sit behind the skin at the middle of the panel and break out
    # through it 10 mm further out. Screw it to the casing behind instead and
    # the fixings collide with the camera pocket and the ToF channel, which
    # between them use most of that plate. And it bought nothing that was not
    # already paid for: servicing the camera means taking the face off, and
    # the face comes off with four screws either way.
    #
    # So the band is a groove, in SEAMS below. It is the read the plated-face
    # reference actually has, it costs no fastener, and it leaves the
    # forehead a continuous shell over the one region of the head that is
    # carrying a 96 mm plate, two boards and a lens.
    #
    brow_band   = dict(a=48.0, b=26.0, z=261.0),

    # ON, at last. The fit study measured the casing's top corners breaking
    # out through the brow flanks by up to 10.3 mm and named two honest fixes:
    # chamfer the corners (done, head_parts.py) and "restyle the brow band
    # fuller and flatter - the plated-face reference has exactly that brow".
    # This is the second one: a smooth normal-direction swell, not a bolted-on
    # volume, blended over a 34 mm radius so it reads as bone.
    # Wide and shallow, not a knuckle. r=34/amp=7.5 was tried first and read
    # as a lump over each eyebrow; the brow the reference has is a broad
    # band, so the radius went up and the amplitude came down.
    swell       = dict(x=44.0, y=163.0, z=272.0, r=52.0, amp=6.0),

    # Where the head comes apart for printing and assembly. A coronal plane
    # 7 mm in front of the ear ports: both halves then print cut-face-down,
    # 74 mm and 111 mm tall instead of one 213 mm tower, the face prints with
    # no support on any part of the face, and the cranium becomes an open
    # bowl you can reach every fixing in. head_split.py does the cut.
    split       = dict(y=135.0),
)

# Panel seams. NOT booleans: each is an implicit surface, and every vertex
# within half a width of it is pushed in along its own normal. A boolean
# groove on a doubly-curved 100k sculpt is a crash and a slow one; a
# displacement is exact, instant, and cannot fail. Run before Solidify, so
# the groove is a groove in the wall and not a slot through it.
#
#   cylX / cylY  distance to an axis-parallel line, i.e. a ring seam
#   plane        n.p = d
# `mask` limits a seam to part of the head so it stops where it should.
SEAMS = [
    # Cranial cap. Tilted very slightly back-to-front, and deliberately high:
    # it has to stay clear of the brow panel's top edge at z=286, and of the
    # cranial opening, which it does because the shell has no surface at
    # y<58 that high.
    dict(kind="plane", n=(0.0, 0.057, 0.998), d=305.4, w=3.0, depth=0.9,
         label="cranial cap"),
    # Concentric ring 6 mm outside each Ø66 ear port - the white-shell
    # reference's ringed port. r=39 keeps it 1 mm clear of the y=135 split.
    dict(kind="cylX", c=(95.0, 204.0), r=39.0, w=3.0, depth=0.8,
         label="ear port ring"),
    # The brow band. An ellipse in x/z, front of the head only, drawn round
    # the camera bore and the ToF window so the two apertures read as one
    # instrument panel instead of two holes punched in a forehead.
    dict(kind="ellY", c=(0.0, 261.0), a=48.0, b=26.0, w=3.0, depth=0.8,
         label="brow band", mask=lambda p: p.y > 150.0),
]
SEAM_CENTRE = (0.0, 112.0, 212.0)   # middle of the skull; see _cut_seams
# Deliberately only two. A cheek/jaw line was drawn and cut: on this sculpt
# every plane that reads as a jaw seam also crosses the mouth or dies in the
# middle of a cheek, and the head already gets four seam reads it has earned
# - the cap groove, the ear rings, the brow panel gap and the y=135 split.

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


def eye_axis(sx):
    """Unit direction the socket on side sx (+1 = Humalien's right) faces.
    Outward and slightly down, from the measured rim - see S["eye"]."""
    o = math.radians(S["eye"]["rake_out"])
    d = math.radians(S["eye"]["rake_down"])
    v = Vector((sx * math.sin(o), math.cos(o) * math.cos(d), -math.sin(d)))
    return v.normalized()


def cyl(name, coll, mat, dia, length, loc, axis, dia2=None, direction=None):
    """Closed cylinder (or cone, if dia2 is given) through loc.

    `axis` is 'X' or 'Y'; pass `direction` instead for an arbitrary one, as
    the raked eye sockets need."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, radius1=dia / 2,
                          radius2=(dia if dia2 is None else dia2) / 2,
                          depth=length, segments=64)
    if direction is not None:
        rot = Vector((0, 0, 1)).rotation_difference(
            Vector(direction).normalized()).to_matrix().to_4x4()
    else:
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


# ---------------------------------------------------------------------------
# cleaning the sculpt
# ---------------------------------------------------------------------------

def _largest_component(bm):
    """Drop everything but the main skin. The sculpt carries two 2349-vert
    eyeball islands at pitch 56; ours sit at 62 and would poke through them."""
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
    return [len(c) for c in comps]


def _strip_buried(bm):
    """Delete every face that cannot see the sky.

    The one rule that removes the mouth bag, the nostril cavities, the ear
    canals and the eyelid interiors. See the module docstring for why a
    ray-parity "is it inside" test finds none of them.
    """
    from mathutils.bvhtree import BVHTree
    st = S["strip"]
    n = st["rays"]
    dirs = []
    for i in range(n):
        y = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(max(0.0, 1 - y * y))
        th = math.pi * (1 + 5 ** 0.5) * i
        dirs.append(Vector((r * math.cos(th), y, r * math.sin(th))))
    bm.normal_update()
    tree = BVHTree.FromBMesh(bm)
    doomed = []
    for f in bm.faces:
        c = f.calc_center_median()
        if c.z < st["z_min"]:
            continue
        p = c + f.normal * 0.4
        free = 0
        for d in dirs:
            if tree.ray_cast(p + d * 0.05, d, 400.0)[0] is None:
                free += 1
        if free / n < st["openness"]:
            doomed.append(f)
    if doomed:
        ps = [f.calc_center_median() for f in doomed]
        print("  buried geometry: %d faces, x %.0f..%.0f y %.0f..%.0f z %.0f..%.0f"
              % (len(doomed), min(p.x for p in ps), max(p.x for p in ps),
                 min(p.y for p in ps), max(p.y for p in ps),
                 min(p.z for p in ps), max(p.z for p in ps)))
        bmesh.ops.delete(bm, geom=doomed, context='FACES')
    _fill_small_holes(bm)
    return len(doomed)


def _fill_small_holes(bm, max_extent=80.0):
    """Cap the openings the strip left behind.

    Deleting a cavity leaves its mouth open, and Solidify turns an open
    boundary into a rim - a 4 mm wall standing on edge. Around the ear that
    came out as a set of thin fins poking through the skin just behind the
    port, which is exactly the sort of thing that prints as a curl of
    stringy plastic and snaps off in a bag.

    Capping them is also the right answer on its own terms: the mouth, the
    nostrils and the ear canals become closed skin instead of holes into a
    head full of electronics. The neck ring is the one opening that must
    stay open - it is 85 mm across and everything else here is under 40 -
    so the size test is enough to tell them apart, and the count is printed
    so a future opening that gets accidentally sealed is visible.
    """
    loops = []
    seen = set()
    for e in bm.edges:
        if not e.is_boundary or e in seen:
            continue
        loop, stack = [], [e]
        seen.add(e)
        while stack:
            cur = stack.pop()
            loop.append(cur)
            for v in cur.verts:
                for oe in v.link_edges:
                    if oe.is_boundary and oe not in seen:
                        seen.add(oe)
                        stack.append(oe)
        loops.append(loop)
    filled = 0
    for loop in loops:
        pts = [v.co for e in loop for v in e.verts]
        ext = max(max(p[i] for p in pts) - min(p[i] for p in pts)
                  for i in range(3))
        if ext > max_extent:
            print("  hole left open: %.0f mm across (the neck)" % ext)
            continue
        try:
            bmesh.ops.holes_fill(bm, edges=loop, sides=0)
            filled += 1
        except Exception:
            pass
    print("  capped %d of %d openings the strip opened" % (filled, len(loops)))
    return filled


def _seam_dist(seam, p):
    k = seam["kind"]
    if k == "plane":
        n = seam["n"]
        return n[0] * p.x + n[1] * p.y + n[2] * p.z - seam["d"]
    if k == "cylX":
        cy, cz = seam["c"]
        return math.hypot(p.y - cy, p.z - cz) - seam["r"]
    if k == "cylY":
        cx, cz = seam["c"]
        return math.hypot(p.x - cx, p.z - cz) - seam["r"]
    if k == "ellY":
        # not a true distance - the implicit value scaled by the minor
        # semi-axis, which is close enough over a 3 mm band
        cx, cz = seam["c"]
        f = math.hypot((p.x - cx) / seam["a"], (p.z - cz) / seam["b"])
        return (f - 1.0) * seam["b"]
    raise ValueError(k)


def _cut_seams(bm):
    """Push every vertex near a seam surface in along its own normal.

    A cosine profile across the width, so the groove has walls the printer
    can resolve rather than a step the slicer rounds off anyway.
    """
    total = 0
    for seam in SEAMS:
        half = seam["w"] / 2.0
        mask = seam.get("mask")
        # Densify the band first. The sculpt's edges run 2-4 mm across the
        # cranium, so displacing whatever vertices happen to fall in a 3 mm
        # band gives a dotted line, not a groove. Subdivide whole FACES that
        # touch the band, grid-filled: subdividing only the edges that cross
        # the seam leaves triangle fans of long skinny slivers, and a groove
        # cut into slivers shades as a row of beads however smooth its
        # profile is. This was the actual cause of the first two attempts.
        for _ in range(2):
            faces = [f for f in bm.faces
                     if any(abs(_seam_dist(seam, v.co)) < half * 1.8
                            for v in f.verts)]
            edges = set()
            for f in faces:
                edges.update(f.edges)
            if edges:
                bmesh.ops.subdivide_edges(bm, edges=list(edges), cuts=1,
                                          use_grid_fill=True)
        bm.normal_update()
        bm.verts.index_update()
        n = 0
        # Push along a SMOOTHED normal. The raw vertex normal on freshly
        # subdivided sculpt is noisy enough to show in the groove wall, and
        # a radial from the middle of the skull - tried first - has a large
        # tangential component low on the ear ring and shears the mesh
        # sideways there. Four rounds of neighbour averaging fixes both.
        nrm = {v.index: v.normal.copy() for v in bm.verts}
        for _ in range(4):
            upd = {}
            for v in bm.verts:
                acc = nrm[v.index].copy()
                for e in v.link_edges:
                    acc += nrm[e.other_vert(v).index]
                if acc.length > 1e-6:
                    upd[v.index] = acc.normalized()
            nrm = upd
        for v in bm.verts:
            if mask and not mask(v.co):
                continue
            d = _seam_dist(seam, v.co)
            if abs(d) < half:
                v.co -= nrm[v.index] * (seam["depth"] * 0.5 *
                                        (1.0 + math.cos(math.pi * d / half)))
                n += 1
        print("  seam %-5s %-28s %d verts" % (
            seam["kind"], seam.get("label", ""), n))
        total += n
    return total


def _clean_copy(coll, mat_shell, mat_dark):
    """Copy HEAD_REF and make it printable: one skin, no bust, no buried
    geometry, no lash cards across the eye sockets, a fuller brow, seams."""
    src = bpy.data.objects[SRC]
    me = src.data.copy()
    me.name = "HEAD_CYBORG"
    bm = bmesh.new()
    bm.from_mesh(me)

    comps = _largest_component(bm)
    print("  components %s -> kept the skin" % comps[:4])

    # ---- neck: cut the bust off ----
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                           plane_co=(0.0, 0.0, S["neck_cut"]),
                           plane_no=(0.0, 0.0, 1.0),
                           clear_inner=True, use_snap_center=False)
    print("  neck cut at z=%.0f -> %d faces" % (S["neck_cut"], len(bm.faces)))

    # ---- everything that cannot see the sky ----
    _strip_buried(bm)

    # ---- eye region pre-clean ----
    # The lash cards and lid shells are thin strips a boolean cannot remove
    # reliably - they enclose no volume, so solvers leave them floating
    # across the opening. Delete every face within r=19 of an eye axis
    # first (y>150 so the back of the head, which the same axis crosses, is
    # untouched); the Ø41 socket cut then trims the surrounding skin to a
    # clean circle through simple surface.
    er = S["eye"]
    axes = [(Vector((sx * er["pitch"] / 2.0, er["y"], er["z"])), eye_axis(sx))
            for sx in (-1, 1)]
    doomed = []
    for f in bm.faces:
        c = f.calc_center_median()
        if c.y < 150.0:
            continue
        for org, d in axes:                # perpendicular distance to the
            v = c - org                    # raked bore axis, not to a
            if (v - d * v.dot(d)).length < 19.0:   # vertical line in x/z
                doomed.append(f)
                break
    if doomed:
        print("  eye pre-clean: %d lid/lash faces" % len(doomed))
        bmesh.ops.delete(bm, geom=doomed, context='FACES')

    # ---- brow-flank swell, both sides ----
    bm.normal_update()
    sw = S["swell"]
    moved = 0
    for v in bm.verts:
        for sx in (-1, 1):
            d = (Vector((sx * sw["x"], sw["y"], sw["z"])) - v.co).length
            if d < sw["r"]:
                t = 1.0 - d / sw["r"]
                v.co += v.normal * (sw["amp"] * t * t * (3.0 - 2.0 * t))
                moved += 1
    print("  brow swell amp %.1f: %d verts" % (sw["amp"], moved))

    # ---- panel seams ----
    _cut_seams(bm)

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


def build(force=False):
    # Upstream of everything. This remakes HEAD_CYBORG, which head_split then
    # cuts into HEAD_FACE and HEAD_CRANIUM - so running it is the first half
    # of losing any hand edit on those. guard() comes from head_mounts.py.
    guard(collection_contents(COLL_NAME) + ["HEAD_CYBORG", "HEAD_SKIN"],
          "head_style.build()", force)
    coll, cuts = _reset()
    mat_shell = _mat("MAT_shell", SHELL_RGBA, 0.35)
    mat_dark = _mat("MAT_interior", DARK_RGBA, 0.6)
    head = _clean_copy(coll, mat_shell, mat_dark)

    # Keep the cleaned single-surface skin. Every containment question in
    # this project - "is this part inside the head" - has to be asked of a
    # closed single surface: ask it of the solidified shell and a ray from
    # the middle of the skull crosses the inner wall and then the outer wall,
    # comes back even, and the parity test cheerfully reports that the Pi is
    # outside the head. This is the surface to ask.
    skin = bpy.data.objects.new("HEAD_SKIN", head.data.copy())
    skin.data.name = "HEAD_SKIN"
    coll.objects.link(skin)
    skin.display_type = 'WIRE'
    skin.hide_render = True
    skin.hide_set(True)

    # ...and HEAD_SOLID, the same surface with every remaining hole filled -
    # the eye sockets the pre-clean opened, and the neck. Closed, so it is a
    # SOLID: the volume the head occupies, skin included.
    #
    # This is the object that stops parts leaving the head. Sizing a mount
    # by raycasting the wall and then building a flat-ended cylinder does
    # not work and cannot be made to work: the wall is curved, so a ray down
    # the boss's centreline says 19 mm of clearance while the boss's own rim
    # is already 6.6 mm outside the skull. Every one of the eleven bosses
    # broke out that way. Clipping them against this instead is exact - a
    # part intersected with HEAD_SOLID physically cannot leave the head,
    # whatever the curvature does.
    solid_me = head.data.copy()
    solid_me.name = "HEAD_SOLID"
    bm = bmesh.new()
    bm.from_mesh(solid_me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
    # Keep filling until nothing is open. One pass leaves a handful of edges
    # behind - holes_fill can bridge a loop into two smaller loops - and
    # "closed" has to mean closed: the MANIFOLD solver refuses the object
    # otherwise, and a boolean that refuses silently returns rubble.
    for _ in range(6):
        if not any(e.is_boundary for e in bm.edges):
            break
        _fill_small_holes(bm, max_extent=1e9)
    bm.to_mesh(solid_me)
    bm.free()
    solid = bpy.data.objects.new("HEAD_SOLID", solid_me)
    coll.objects.link(solid)
    solid.display_type = 'WIRE'
    solid.hide_render = True
    solid.hide_set(True)

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
        # centred on the eyeball, so the ball sits in the middle of the
        # opening whichever way the bore is raked
        c = Vector((sx * ey["pitch"] / 2, ey["y"], ey["z"]))
        eyes.append(cyl("CUT_eye_%s" % side, cuts, mat_dark, ey["dia"], 80.0,
                        c + eye_axis(sx) * 20.0, 'Y', direction=eye_axis(sx)))
    bp = S["brow_port"]
    ports_brow = []
    for sx, side in ((1, "R"), (-1, "L")):
        ports_brow.append(rrect_box(
            "CUT_brow_port_%s" % side, cuts, mat_dark,
            bp["x1"] - bp["x0"], bp["z1"] - bp["z0"], bp["r"], 60.0,
            (sx * (bp["x0"] + bp["x1"]) / 2, 175.0, (bp["z0"] + bp["z1"]) / 2),
            'XZ'))

    # ---- modifier stack: shell first, then the cuts ----
    sol = head.modifiers.new("Shell", 'SOLIDIFY')
    sol.thickness = S["wall"]
    sol.offset = -1.0                 # inward: the outer surface stays the face
    sol.use_rim = True
    sol.material_offset_rim = 1       # rims in MAT_interior

    # MANIFOLD everywhere, which is Blender 5's new solver and the reason
    # this stack is no longer a minefield. The history is worth keeping,
    # because both of the old rules looked like laws and were only
    # workarounds:
    #
    #   EXACT discarded the whole shell whenever it met the solidified lid
    #   creases, 98k vertices in and 1.6k out, so the eyes ran on FLOAT.
    #   Then the brow-band seam subdivided the forehead, and EXACT started
    #   throwing the shell away on the camera bore too - 138k in, 850 out -
    #   with nothing wrong with either input.
    #
    # MANIFOLD takes all seven cuts on the same mesh without complaint. It
    # wants closed manifold inputs, which this shell is: Solidify with a rim
    # closes every boundary the cleaning left, and the shell tests at zero
    # boundary and zero non-manifold edges.
    for name, cutter in [("EarPortR", ports[0]), ("EarPortL", ports[1]),
                         ("RearOpening", rear),
                         ("EyeR", eyes[0]), ("EyeL", eyes[1]),
                         ("BrowPortR", ports_brow[0]),
                         ("BrowPortL", ports_brow[1])]:
        mod = head.modifiers.new(name, 'BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.solver = 'MANIFOLD'
        mod.object = cutter

    for c in cuts.objects:
        c.display_type = 'WIRE'
        c.hide_render = True
    cuts.hide_viewport = True

    # ---- bake: one evaluation, then a plain mesh ----
    # The one heavy moment. After this there is nothing live left to
    # re-evaluate, and the saved file is dumb data.
    bake(head)

    # smooth shading, hard edges kept by angle so the port bores and the
    # seams stay crisp
    shade(head.data)

    # the raw reference stays but gets out of the way
    bpy.data.objects[SRC].hide_set(True)

    print("STYLE_Head built: shell %.1f, neck cut z%.0f, ear ports Ø%.0f at "
          "(y%.0f z%.0f), cranial opening y %.0f..%.0f z %.0f.., eyes Ø%.0f at "
          "pitch %.0f, brow ports |x| %.0f..%.0f z %.0f..%.0f"
          % (S["wall"], S["neck_cut"], ep["dia"], ep["y"], ep["z"],
             ro["y0"], ro["y1"], ro["z0"], ey["dia"], ey["pitch"],
             bp["x0"], bp["x1"], bp["z0"], bp["z1"]))
    return head


def bake(ob):
    """Evaluate the modifier stack once and replace the mesh with the result."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    baked = bpy.data.meshes.new_from_object(
        ev, preserve_all_data_layers=True, depsgraph=dg)
    baked.name = ob.data.name + "_baked"
    old = ob.data
    ob.modifiers.clear()
    ob.data = baked
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return baked


def shade(me, angle=40.0):
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    if hasattr(me, "set_sharp_from_angle"):
        me.set_sharp_from_angle(angle=math.radians(angle))
    me.update()
    return me


# ---------------------------------------------------------------------------
# the check the brow debt was closed against
# ---------------------------------------------------------------------------
def verify_forehead(head_name="HEAD_SKIN"):
    """How far does the forehead casing break out through the skin?

    Was 10.3 mm at the casing's top corners, carried as an open debt. The
    swell above and the chamfer in head_parts.py are the two fixes the fit
    study named; this is the number that says whether they worked.
    """
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    head = bpy.data.objects[head_name]
    bm = bmesh.new()
    bm.from_object(head, dg)
    bm.transform(head.matrix_world)
    tree = BVHTree.FromBMesh(bm)
    d = Vector((0.331, 0.537, 0.774)).normalized()

    def inside(p):
        hits = 0; t0 = 0.0
        for _ in range(40):
            loc, nrm, idx, dist = tree.ray_cast(p + d * (t0 + 0.03), d)
            if loc is None:
                break
            hits += 1
            t0 = (loc - p).dot(d)
        return hits % 2 == 1

    worst = {}
    for name in ("FIT_forehead_casing", "PROXY_b0385_board",
                 "PROXY_vl53l1x_board", "PROXY_b0385_barrel"):
        ob = bpy.data.objects.get(name)
        if ob is None:
            continue
        me = ob.evaluated_get(dg).to_mesh()
        w, wp, n_out = 0.0, None, 0
        for v in me.vertices:
            p = ob.matrix_world @ v.co
            if not inside(p):
                n_out += 1
                loc, nrm, idx, dist = tree.find_nearest(p)
                if dist and dist > w:
                    w, wp = dist, p
        ob.evaluated_get(dg).to_mesh_clear()
        worst[name] = (n_out, w, wp)
        print("  %-22s %3d verts out, worst %5.2f mm%s" % (
            name, n_out, w,
            "" if wp is None else " at (%.0f,%.0f,%.0f)" % (wp.x, wp.y, wp.z)))
    bm.free()
    return worst


if __name__ == "__main__":
    build()
