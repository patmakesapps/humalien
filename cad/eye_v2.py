"""A bespoke four-servo eye mechanism for Humalien.

Run inside Blender:

    exec(open(r"C:\\Humalien\\cad\\eye_v2.py").read())
    build()          # -> the EYE_v2 collection
    check()          # fit, printability, clearance - through the WHOLE range
    reach()          # what each servo can actually deliver, tilt by tilt
    pose(tilt=-16, pan=30, lid=0)   # put it somewhere and look at it

Replaces Will Cogley's e3.2, which is now reference only. Two reasons, and
the licence is the one that actually matters: e3.2 is **CC BY-NC-SA**, so
none of his geometry could ever ship in this repo and nothing built on it
could ever be commercial. The second is that every one of his plates needs
support material, and nothing else in this project does.

WHAT IT DOES
------------
Four MG90S, against Cogley's six:

| servo | drives                  |
| ----- | ----------------------- |
| pan   | both eyes, linked, +-30 |
| tilt  | both eyes, linked, +-16 |
| lid R | right eyelid, 52 deg    |
| lid L | left eyelid, 52 deg     |

The two he spends that this does not are per-eye pan, which buys convergence
- eyes crossing to focus close. Real, but subtle, and it doubles the linkage
count. The simplicity is spent on making blink crisp instead.

All four are on the FIXED frame, which settles a contradiction this file used
to carry: it said pan and both lids "ride on the gimbal", and then placed all
four servos in the y=126 plane, 34 mm behind the tilt axis, where riding on
the gimbal would swing them +-11.7 mm every time the eyes looked up. What
that costs is cross-coupling - tilt moves the far end of every pushrod - and
that is a linear, repeatable, hysteresis-free error on a machine with a Pi
and sixteen PWM channels. It is mixed out in software. `reach()` prints how
much of each servo's travel goes on it.

THE FIVE DECISIONS THAT SHAPE EVERYTHING
----------------------------------------
**A gimbal, not a ball in a socket.** A ball floating in a spherical seat
needs two pushrods pulling on one free body, and they fight each other -
every bit of slop in one shows up as error in the other. A gimbal makes each
axis a defined pivot and nothing is overconstrained.

**The eyeballs are domes, not spheres.** Only the front is ever visible
through a O41 socket, so the back of a sphere is material printed, split and
seamed for nothing - and a sphere's split plane contains both pan poles, so
the seam lands across the iris. A dome cut BACK_CUT behind centre is one
piece, prints flat-back-down, and seams where nothing sees it.

**Each eye hangs on ONE journal, underneath.** This is the change that
unlocked everything else, and it was forced by a part that is already
printed. A yoke gripping the ball at both poles needs an arm over the top,
at radius >= 20 from the tilt axis - and `FIT_forehead_casing` is solid
across the full width from z=225 up, which is exactly the top of the ball.
At 20 of tilt that arm swings to y=168.4, six millimetres inside the
casing. There is no length of arm that avoids it: to stay clear at every
tilt angle an arm at radius 20.4 has to end by y=154.7, and the pole it has
to reach is at y=160. So the top of the eye is left empty and the dome runs
on a single O10 x 9 journal in the cradle below it, with its pan lever at
eye-centre height where the linkage wants it.

That journal is also what sets the tilt range at +-16 rather than +-20: it
hangs 26 mm below the tilt axis, a point that far below swings forward by
sin(tilt) x 26, and the cheek's inner wall is at y=172.7. Slop is the price
- 0.3 mm of running clearance over 9 mm of journal is about 2 degrees of
wobble in the eye, and it is the loosest thing in the mechanism.

**The tilt bearings are in the corridor between the eyes, not outboard.**
48.5 was measured against the eyeball and never against the eyelid. A lid is
a shell OVER the ball, outer O35.6, so it reaches x=48.8 - through the
bearing. The outboard slot on the tilt axis is 3.86 mm wide (ball at 47.0,
MOUNT_ZONE out at 50.86) and it has to hold a boss AND a journal AND their
running clearance. The corridor between the two lids is 26.4 mm and holds
all of it comfortably.

**One shaft, three concentric members.** The frame carries a O5 shaft along
the tilt axis; the gimbal's two tubes turn on it; each eyelid's hub turns on
the OUTSIDE of the tube next to it. Frame, gimbal and lid all share one
axis, which is not a trick - the lid has to stay concentric with the ball,
and the ball's centre is on the tilt axis, so they were always the same
line. Riding the lid on the gimbal also makes it tilt with the eye for free,
which is what a real lid does.

WHAT IT HAS TO HIT
------------------
Measured from the head, not assumed - see `docs/resume-here.md`:

- eyeball centres at **x = +-31, y = 160, z = 209** (`eye_pitch` is 62)
- O41 sockets, raked 25 out and 10 down. The ball does NOT fill them.
- `FIT_forehead_casing` is solid over x -47..47 from **z=225** up, at
  y 162..167. The top of the eyeball is z=225. See `casing_relief()`.
- the bay is generous below and forward of the eyes - the zone reaches
  y=178 at x=31, z=186 - and pinches to a 74 mm corridor behind y=126,
  where the servos live.
- **no supports, anywhere.** Print orientations are in each part's docstring.

THE LANES
---------
Nothing here dodges anything. The parts are stacked in depth, and where two
of them have to share a depth they are separated in height instead:

    y 153..176   domes and eyelids            (the moving spheres)
    y 152..167   the gimbal cradle and tubes  (astride the eye centres)
    y 147..151   the pan bar,   z 181..195    (behind the whole gimbal)
    y 147..151   the frame's arch, z 226..234 (same depth, 30 mm higher)
    y 120..132   the four servos              (in the 74 mm corridor)

The frame's arch is where it is because it has nowhere else to go. Behind it
the temple pad boss is solid from x=41.8 outward over z 206..223, so a frame
at y 138..142 cannot reach the pad bore at all - the bore is only open
through the pad itself. In front of it the eyeballs start: panned 30 degrees,
a dome swings its back rim to y=146.7. Four millimetres, and the arch fills
them.

The one thing that crosses a lane is the frame's mast, which reaches the tilt
axis at x=0 from the arch behind it. It goes over the pan bar - whose swept
top is z=200 - and comes down to the shaft in the corridor between the eyes,
where no eyeball ever is.

WHAT IS STILL OPEN
------------------
**The forehead casing has to give 2.2 mm.** `check()` will FAIL on it until
somebody decides. It is the only clash left and it is not fixable in the
mechanism - see `casing_relief()` for the arithmetic. The part is on plate 5
and unprinted, so this is a decision rather than a problem.

**The eyeball does not fill its socket.** A O32 ball in a O41 opening raked
25 out and 10 down leaves a crescent you can see the mechanism through -
worst at the lower-outboard corner. That is what `eye_bezel_R/L` were for,
and the brief retired them on the grounds that the openings became "smooth
O41 circles". They did; the ball still does not fill them. Bezel, bigger
ball, or smaller opening - the renders make the choice obvious and none of
the three is drawn yet.

**The dome's print orientation is unresolved**, and the claim that it prints
flat-back-down is wrong. Back-face-down puts the pan lever 4 mm below the
bed and lays the O10 journal boss on its side as a cantilever. Neither is
printable as drawn. The likely answer is to split the lever and boss off as
a separate part that presses into the dome, but that has not been drawn.
"""

import bpy
import bmesh
import math
from mathutils import Matrix, Vector

HEAD_MOUNTS = r"C:\Humalien\cad\head_mounts.py"
COLL = "EYE_v2"

P = dict(
    pitch     = 62.0,       # eyeball centre to centre - matches the sockets
    y         = 160.0,      # eyeball centre, and the tilt axis
    z         = 209.0,
    ball      = 32.0,       # eyeball diameter
    socket    = 41.0,       # the head's opening, for clearance checks only

    # The dome. BACK_CUT behind centre: bigger hides the rim through more pan
    # but leans the first layers further out. 7.0 gives 13 deg off vertical.
    back_cut  = 7.0,
    shell     = 2.4,        # dome wall - 6 perimeters at 0.4, opaque enough
                            # to hide the pixel yet thin enough to glow

    pan_max   = 30.0,       # degrees each way
    tilt_max  = 16.0,       # not 20, and the cheek is what sets it: a
                            # point Dz below the tilt axis swings forward
                            # by sin(tilt)*Dz, the pan journal housing sits
                            # 27 mm below it, and MOUNT_ZONE runs out at
                            # y=172.7 where the cheek's inner wall is -
                            # asked of HEAD_FACE, not of MOUNT_ZONE, which
                            # has been 3-6 mm optimistic every time

    # --- the pan bearing: one journal, underneath ------------------------
    # The dome has no top pivot at all; see the header. The boss is as long
    # as the space between the bottom of the ball (z=193) and how far the
    # cradle can hang without swinging out through the cheek at full tilt.
    # A point Dz below the axis moves 0.342*Dz forward at 20 deg, and the
    # zone at x=31 runs out at y=178, so the cradle floor cannot go below
    # z=178 however much a longer journal would be liked.
    pan_d     = 10.0,       # boss on the dome
    pan_fit   = 0.30,       # diametral running clearance in the cradle
    pan_z0    = 183.0,      # bore floor
    pan_z1    = 192.0,      # cradle top; the dome's underside is z=193
    pan_hub   = 13.0,       # journal housing OD - round, not a block, because
                            # a block's outboard-front corner is what swings

    # Pan lever: a post off the dome's back face, offset from the pan axis,
    # with the link pin hanging BELOW it so the pan bar can sit clear of the
    # lever's own body. 11 mm of arm gives +-5.5 mm of travel for +-30 deg.
    lever_r   = 11.0,
    lever_t   = 3.0,
    pin_drop  = 16.0,       # how far the link pin hangs below the eye line
    # Sized for 2 mm steel rod - a bicycle spoke. +0.3 for a joint that has
    # to pivot freely, against the +0.2 this project uses for an M2 free
    # hole and +0.4 for an M3: a pivot wants to be looser than a fastener
    # but not sloppy. If a printed one rattles, take the next to 2.15.
    #
    # Only THREE of these holes take wire - the two servo pushrods and the
    # tilt one. The eyeball-to-bar joints are printed pins on the domes.
    link_d    = 2.30,
    link_t    = 3.0,

    # --- the tilt bearing: one shaft, two tubes, lids on the outside -----
    shaft_d   = 5.0,
    shaft_x   = 14.6,       # the shaft runs +-this; the balls start at 15.0
    shaft_fit = 0.4,        # diametral, tube bore over the shaft
    tube_od   = 9.0,
    tube_x0   = 3.0,        # tube inboard end - the mast is inside this
    tube_x1   = 14.8,       # tube outboard end - the ball starts at 15.0
    mast_hx   = 2.4,        # frame mast half-width
    web_x0    = 3.2,        # gimbal web, tube down to cradle
    web_x1    = 6.8,

    # --- the gimbal cradle ----------------------------------------------
    cradle_y0 = 154.0,
    cradle_y1 = 166.0,
    cradle_z0 = 180.0,
    cradle_z1 = 190.0,
    bar_hx    = 23.0,       # cross bar half-width; the journals take over

    # --- the frame -------------------------------------------------------
    # The arch sits at y 145.5..149.5, in the four millimetres between the
    # front of the temple pad and the back of the eyeballs, and that is the
    # only place it fits. Behind it, the pad boss is solid from x=41.8
    # outward over z 206..223 - measured, by listing surface crossings - so
    # a frame at y 138..142 cannot reach the pad bore at all; the bore is
    # only open through the pad itself. In front of it the eyeballs start:
    # a dome panned 30 degrees swings its back rim to y=146.7.
    #
    # And it is high, z 224..232, because an eyelid parked open reaches back
    # to y=149.7 at z=223.2 as it passes over the top of the eye.
    arch_y0   = 147.5,
    arch_y1   = 151.5,
    arch_z0   = 226.0,      # the bar itself rides high, over the eyeballs -
    arch_z1   = 234.0,      # and at 224 it was what limited how far the
                            # eyelids could open, because a lid parked past
                            # 41 degrees swings its trailing edge back to
                            # y=151 and up to z=224.4 as it clears the top
                            # of the eye. Two millimetres of bar bought
                            # fifteen degrees of eyelid.
    arch_z_lo = 214.0,      # ...and a web in the middle brings it down to
                            # the mast, in the corridor where no eyeball is
    arch_web  = 12.0,       # half-width of that web
    arch_hx   = 52.0,
    plate_hx  = 3.0,        # temple plate, x 45.3..51.3
    mast_y1   = 164.0,      # the mast leans forward and down 29 degrees
    mast_z    = 216.0,      # its centre where it leaves the web. Chosen
                            # so the mast's centreline passes through the
                            # tilt axis: at 218 it passed 2.2 mm above,
                            # which put the O5.2 shaft bore tangent to
                            # the mast's own underside and left a
                            # 4.8 x 0.5 mm hole in the part
    boss_d    = 10.0,       # the shaft boss on the mast. 9.0 left the
                            # leaning mast's lower corner sitting almost
                            # exactly on the boss's surface, and the
                            # union came back with one 4.8 x 0.5 mm face
                            # missing - a near-tangent boolean, which is
                            # the same fault as a coplanar one

    # The temple dowel pads, already in both printed head halves. MEASURED
    # off HEAD_CRANIUM by listing surface crossings along +X at z=215:
    #     y=134   solid 41.79..47.19 | VOID 47.19..52.39 | solid 52.39..61.07
    # The void is the O5.2 pin bore, so its centre is 49.79 - NOT 57.79,
    # which is only the inner wall face. An earlier probe that walked
    # outward until it hit something found the wall and called it the pad,
    # and the frame built on that number put 107 vertices outside the skin.
    # MEASURED again, 15 Aug, because the earlier figures were a guess at
    # the ends: the pad runs y 133..145, not 131..147, and its bore is a
    # O5.2 hole at x 47.19..52.39, z 212.4..217.6 over that whole length.
    pad_x     = 49.79,
    pad_z     = 215.0,
    pad_bore  = 5.2,
    pad_face  = 147.0,      # the pad ends here; the frame sits in front
    plate_y1  = 151.3,
    # The peg is a SEPARATE part, and that is a printing decision rather
    # than a mechanical one. The frame prints flat on its arch, which puts
    # +y upwards - and a spigot reaching back to y=130 would then point
    # straight down into the bed. A peg pressed in afterwards also does the
    # head's own job: those pad bores exist to locate the two halves on a
    # pin, and one peg now does both.
    peg_fwd   = 4.4,        # forward of the pad the wall closes to x=52.2,
                            # so the section that passes through the frame
                            # has to be thinner than the one in the bore
    peg_d     = 5.0,        # a shade under the O5.2 pad bore; the press
                            # fit comes from print tolerance, not from
                            # modelling 0.05 mm of interference and then
                            # having every collision test report it
    peg_y0    = 134.0,
    peg_head  = 6.5,

    casing_y  = 162.0,      # FIT_forehead_casing starts here - measured
    casing_z  = 225.0,      # and is solid from here up, full width

    # --- the eyeball, split three ways so every piece prints ------------
    # One piece it could not be. The pan lever reaches 4 mm BEHIND the back
    # face, so the ball cannot sit on it; the bearing boss hangs 16 mm BELOW
    # the ball, so it cannot sit on that either; and those two point at right
    # angles, so no orientation solves both. `printability()` says so in
    # numbers rather than in argument.
    #
    #   eye_dome   shell, iris, pupil, and a O10.4 bore up its bottom pole.
    #              Prints on its flat back face, nothing behind it, nothing
    #              below it.
    #   eye_stem   a O22.8 spigot into the dome's back opening, carrying the
    #              pan lever and the pixel's pad. Prints spigot-face down,
    #              and every layer after the first is SMALLER than the one
    #              below - so it cannot overhang at all.
    #   eye_axle   a plain O10 rod. Glues into the dome, turns in the cradle.
    #
    # The torque path is servo -> wire -> lever -> stem -> glue -> dome ->
    # axle, and the glue joint is the full O23 wall of the back opening.
    stem_spig = 22.8,      # into the back opening, which is O23.32
    stem_t    = 3.0,       # how far the spigot reaches into the cavity
    axle_d    = 10.0,
    axle_fit  = 0.4,       # diametral, in the dome's bore
    axle_z0   = 177.0,     # bottom of the rod
    axle_z1   = 203.0,     # top, buried in the dome's plug

    m2_free   = 2.2,
)

# The iris and pupil on the front of each eyeball.
#
# `dia` is a shallow step cut into the front face, so the eye reads as an eye
# with the power off. `pupil` is the same shell thinned from the INSIDE to
# `wall`, so the 5050 pixel lights that circle and the rest of the ball stays
# opaque - nothing is drilled through, and nothing needs a second material.
#
# 0.9 mm is two perimeters at 0.4 plus a whisker. Thinner glows better and
# starts to show the pixel's own shape through it; thicker glows evenly and
# dimmer. It is the number most worth printing a test of.
IRIS = dict(
    dia   = 15.0,       # the iris step; 0 turns it off
    step  = 0.4,        # how deep that step is, everywhere across it
    pupil = 6.5,        # the lit circle; 0 turns it off
    wall  = 0.9,        # what the shell is thinned to there
)

# The eyelid. It lives in the 4.5 mm annulus between the O32 ball and the
# O41 socket. Angles are measured from straight ahead, positive upwards.
#
# CLOSED + SPAN + PARK is capped at 114 degrees and that is not taste. Past
# it the lid's trailing edge swings back far enough to reach the pan bar:
# the rearmost point of a band that ends at angle t is y = 160 + 17.8*cos t,
# and the bar's front face at full pan is y=151.97.
LID = dict(
    gap       = 0.35,       # running clearance over the ball
    shell     = 1.2,        # 32.7 inner, 35.1 outer, in a O41 socket
    closed    = -26.0,      # lower edge when shut, below straight ahead
    span      = 90.0,
    park      = 52.0,       # how far it swings up to open. Parked, the lid's
                            # lower edge sits 35 degrees above straight
                            # ahead - clear of the iris, and low enough on
                            # the ball to still read as an eyelid rather
                            # than as nothing at all.
    # Trimmed at |x| = 43, and this is the socket's doing rather than the
    # mechanism's. The annulus between ball and skin was mapped all round
    # the eye: 4.1 mm straight ahead, 2.3 at 20 deg inboard, and ZERO by
    # 40 deg outboard, where the 25 deg of outward rake lays the skin down
    # almost tangent to the ball. The dome itself already stands 0.21 mm
    # proud out there. A shell over it stands proud by its own thickness,
    # and no thickness of lid avoids that - only not being there does.
    trim_x    = 43.0,
    hub_od    = 13.0,
    hub_fit   = 0.6,        # diametral, over the gimbal tube
    hub_x0    = 7.4,
    hub_x1    = 14.8,
    crank_r   = 14.0,       # long enough that the pushrod leaves well clear
                            # of the tilt tube it would otherwise cross
    crank_t   = 3.0,
    # The pin sits at the SAME x as its servo's shaft, and that is not
    # tidiness. Both joints are hinges about X - the lid turns about the tilt
    # axis, the horn about the servo's shaft - so a straight rigid rod can
    # only connect them if it lies in a plane perpendicular to X. Offset
    # along their own axis, the two hinges cannot take a straight rod at all:
    # it arrives at the boss on the skew and binds. It was stepped out to
    # 16.3 to dodge the gimbal's tilt tube, back when the crank was shorter
    # and the rod passed close to the axis; at crank_r 14 the rod never gets
    # nearer than 12 mm to the axis and the tube's radius is 4.5.
    pin_x0    = 11.3,
    pin_x1    = 14.3,
    crank_a   = 250.0,      # where the crank points with the lid shut -
                            # straight down, which is both clear of the pan
                            # bar behind it and square to its own pushrod
    crank_x0  = 11.3,
    crank_x1  = 14.3,
)


def _hm():
    ns = {"__name__": "head_mounts", "__file__": HEAD_MOUNTS}
    with open(HEAD_MOUNTS, "r", encoding="utf-8") as fh:
        exec(compile(fh.read(), HEAD_MOUNTS, "exec"), ns)
    return ns


def _sphere(bm, d, loc, segs=48):
    tmp = bmesh.new()
    bmesh.ops.create_uvsphere(tmp, u_segments=segs, v_segments=segs // 2,
                              radius=d / 2.0)
    bmesh.ops.transform(tmp, verts=tmp.verts[:], matrix=Matrix.Translation(loc))
    me = bpy.data.meshes.new("_t")
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    return bm


def _rbox(bm, dims, loc, rot=None):
    """A box that can be rotated. `_box` is axis-aligned only, and the first
    eyelid crank was built with it - so the "arm" came out as a 12 mm box
    lying along +y whatever angle it was asked for, and the link pin was
    then bored 5 mm outside it, in mid-air."""
    tmp = bmesh.new()
    bmesh.ops.create_cube(tmp, size=1.0)
    bmesh.ops.scale(tmp, vec=dims, verts=tmp.verts[:])
    if rot is not None:
        bmesh.ops.transform(tmp, verts=tmp.verts[:], matrix=rot)
    bmesh.ops.transform(tmp, verts=tmp.verts[:], matrix=Matrix.Translation(loc))
    me = bpy.data.meshes.new("_t")
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    return bm


def _prims():
    """A list you append primitives to, and the maker that appends them."""
    out = []

    def add():
        out.append(bmesh.new())
        return out[-1]
    return out, add


def _cut_each(hm, coll, ob, prims, name, op='DIFFERENCE'):
    """One boolean per primitive, never a pile of them in one cutter mesh.

    This is the nested-cutter trap, and this file has now hit it four times.
    Two overlapping solids merged into a single cutter bmesh are not a
    solid - they are two shells sharing a volume - and the boolean against
    them does not give the union of what they cut. The frame's peg socket
    came back with 155 non-manifold edges from exactly this, a O5.2 bore and
    the slot mouth that opens it, merged.
    """
    for i, bm in enumerate(prims):
        hm["_apply"](coll, ob, bm, "%s_%d" % (name, i), op)
    return ob


def _add_each(hm, coll, ob, prims, name):
    return _cut_each(hm, coll, ob, prims, name, 'UNION')


def _union(hm, coll, name, prims):
    """Build one solid out of a list of primitive bmeshes, one boolean each.

    Not "merge them all into a single bmesh and self-union afterwards". That
    is how `gimbal()` first came out as SEVENTEEN closed shells sharing a
    volume, and a self-union on that left 120 non-manifold edges rather than
    fixing it - EXACT does not reliably resolve a dozen coincident faces in
    one pass. One union per primitive is slower to run and always correct,
    and it is what `head_mounts` does for the same reason.
    """
    base = hm["_link"](coll, name, hm["_mesh"](name, prims[0]))
    for i, bm in enumerate(prims[1:]):
        ob = hm["_link"](coll, "_U%d_%s" % (i, name), hm["_mesh"]("_U%d" % i, bm))
        hm["boolean"](base, ob, 'UNION')
        bpy.data.objects.remove(ob, do_unlink=True)
    return base


def _solidify(ob):
    """Weld, then self-union, so a part built from overlapping primitives is
    ONE solid rather than a pile of shells sharing a volume.

    Rolled back if it moves the bounding box, because EXACT has destroyed
    parts in this file before.
    """
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
    bm.to_mesh(ob.data)
    bm.free()
    box = [Vector((min(v.co[i] for v in ob.data.vertices) for i in range(3))),
           Vector((max(v.co[i] for v in ob.data.vertices) for i in range(3)))]
    keep = ob.data.copy()
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.intersect_boolean(operation='UNION', use_self=True,
                                       solver='EXACT')
        bpy.ops.object.mode_set(mode='OBJECT')
    except RuntimeError as exc:
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass
        ob.data = keep
        print("    %s: self-union failed (%s) - kept as built" % (ob.name, exc))
        return ob
    now = [Vector((min(v.co[i] for v in ob.data.vertices) for i in range(3))),
           Vector((max(v.co[i] for v in ob.data.vertices) for i in range(3)))]
    if (not ob.data.vertices or
            max((now[0] - box[0]).length, (now[1] - box[1]).length) > 0.01):
        ob.data = keep
        print("    %s: self-union moved it - rolled back" % ob.name)
    else:
        bpy.data.meshes.remove(keep)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
    bm.to_mesh(ob.data)
    bm.free()
    return ob


# ---------------------------------------------------------------------------
# the parts
# ---------------------------------------------------------------------------
def eyeball(hm, coll, sx):
    """One eye: a O32 dome, hollow, on a single journal underneath.

    Prints flat-back-down: the back face is at y = centre - back_cut, so the
    first layer is a disc of r = sqrt(r^2 - back_cut^2) and the wall leans
    outward by 13 degrees at back_cut 7. The pan boss then points sideways
    in the print, which is why it is a plain cylinder with no shoulder.
    """
    side = "R" if sx > 0 else "L"
    cx, cy, cz = sx * P["pitch"] / 2.0, P["y"], P["z"]
    r = P["ball"] / 2.0

    bm = bmesh.new()
    _sphere(bm, P["ball"], (cx, cy, cz))
    ob = hm["_link"](coll, "eye_dome_%s" % side,
                     hm["_mesh"]("eye_dome_%s" % side, bm))

    # cut the back off, and hollow it for the 5050 pixel
    cut = bmesh.new()
    hm["_box"](cut, (80.0, 40.0, 80.0), (cx, cy - P["back_cut"] - 20.0, cz))
    hm["_apply"](coll, ob, cut, "_CUT_eye_back_%s" % side, 'DIFFERENCE')

    hollow = bmesh.new()
    _sphere(hollow, P["ball"] - 2 * P["shell"], (cx, cy, cz))
    hm["_box"](hollow, (80.0, 40.0, 80.0), (cx, cy - P["back_cut"] - 20.0, cz))
    hm["_apply"](coll, ob, hollow, "_CUT_eye_hollow_%s" % side, 'DIFFERENCE')

    add = bmesh.new()
    # Meat at the bottom pole for the axle to glue into. The dome is hollow
    # to 2.4 mm, so there is nothing to bore; this plug fills the bottom of
    # the cavity up to z=203 and gives the joint 10 mm of length. The 5050
    # sits at z 205..213, clear above it.
    hm["_cyl"](add, 14.0, 10.0, (cx, cy, cz - 11.0), 'Z')
    lob = hm["_link"](coll, "_EYEADD_%s" % side, hm["_mesh"]("_EYEADD_%s" % side, add))
    hm["boolean"](ob, lob, 'UNION')
    bpy.data.objects.remove(lob, do_unlink=True)

    # ---- the iris and the pupil -------------------------------------------
    #
    # Straight ahead, along +Y, and NOT along the socket's axis. The socket
    # is raked 25 out and 10 down; the eyeball is not. An eye that looked
    # down its own socket would be permanently cross-eyed and staring at the
    # floor - the rake carries the OPENING outboard, not the gaze.
    #
    # The iris is a shallow step, so the eye reads as an eye with the power
    # off. The pupil is not a hole: it is the same shell thinned to PUPIL_W,
    # so the 5050 inside lights it and the rest of the ball stays opaque.
    # Cut from the inside, which is why nothing shows on the surface.
    # Both are a SPHERE clipped by a cylinder, not a flat-ended cylinder.
    # A flat cutter cannot put a controlled step into a ball: sunk far enough
    # to leave a 0.5 mm step it only reaches r=3.97, so a "O15 iris" came out
    # O7.9 and the depth ran away at the centre. Against a sphere the depth
    # is the same everywhere, and the cylinder just decides how wide.
    # the axle's bore, up the bottom pole into that plug
    bore = bmesh.new()
    hm["_cyl"](bore, P["axle_d"] + P["axle_fit"], 16.0,
               (cx, cy, P["axle_z1"] - 8.0 + 1.0), 'Z', segs=48)
    hm["_apply"](coll, ob, bore, "_CUT_axlebore_%s" % side, 'DIFFERENCE')

    # The two cuts are opposite ways round, and getting that backwards is
    # what a first attempt did: it hollowed the iris out from the INSIDE and
    # left a 0.4 mm skin over the whole disc, which read as "iris depth 0.4"
    # in every measurement and split the dome into two shells.
    #
    #   iris  - take `step` off the OUTSIDE:  cylinder MINUS the sphere
    #   pupil - thin from the INSIDE:         sphere INTERSECT the cylinder
    #
    if IRIS["dia"] > 0.0:
        bm = bmesh.new()
        hm["_cyl"](bm, IRIS["dia"], 60.0, (cx, cy + 30.0, cz), 'Y', segs=64)
        tmp = hm["_link"](coll, "_IRIS_%s" % side, hm["_mesh"]("_IRIS_%s" % side, bm))
        ball = bmesh.new()
        _sphere(ball, 2.0 * (r - IRIS["step"]), (cx, cy, cz), segs=96)
        bob = hm["_link"](coll, "_IRISBALL_%s" % side,
                          hm["_mesh"]("_IRISBALL_%s" % side, ball))
        hm["boolean"](tmp, bob, 'DIFFERENCE')
        bpy.data.objects.remove(bob, do_unlink=True)
        hm["boolean"](ob, tmp, 'DIFFERENCE')
        bpy.data.objects.remove(tmp, do_unlink=True)
    if IRIS["pupil"] > 0.0:
        bm = bmesh.new()
        _sphere(bm, 2.0 * (r - IRIS["step"] - IRIS["wall"]), (cx, cy, cz),
                segs=96)
        tmp = hm["_link"](coll, "_PUPIL_%s" % side,
                          hm["_mesh"]("_PUPIL_%s" % side, bm))
        clip = bmesh.new()
        hm["_cyl"](clip, IRIS["pupil"], 60.0, (cx, cy + 10.0, cz), 'Y', segs=64)
        cob = hm["_link"](coll, "_PUPILCLIP_%s" % side,
                          hm["_mesh"]("_PUPILCLIP_%s" % side, clip))
        hm["boolean"](tmp, cob, 'INTERSECT')
        bpy.data.objects.remove(cob, do_unlink=True)
        hm["boolean"](ob, tmp, 'DIFFERENCE')
        bpy.data.objects.remove(tmp, do_unlink=True)
    return ob


def eye_stem(hm, coll, sx):
    """The eyeball's back plug: the pan lever, and the pixel's pad.

    Glues into the dome's back opening. It exists because the lever cannot
    be part of the dome - it reaches 4 mm behind the dome's back face, which
    is the only face the dome can be printed on.

    Prints SPIGOT-FACE DOWN, and that orientation is the point of the shape:
    the first layer is the full O22.8 disc and every layer above it is
    smaller than the one below, so there is no overhang anywhere in the part
    by construction rather than by luck.
    """
    side = "R" if sx > 0 else "L"
    cx, cy, cz = sx * P["pitch"] / 2.0, P["y"], P["z"]
    back = cy - P["back_cut"]                      # the dome's back face
    prims, _p = _prims()

    # the spigot, reaching forward into the cavity. Its front face is the
    # pad the 5050 glues to.
    bm = _p()
    hm["_cyl"](bm, P["stem_spig"], P["stem_t"],
               (cx, back + P["stem_t"] / 2.0, cz), 'Y', segs=64)
    # the lever, reaching back to the pan bar's pin
    bm = _p()
    hm["_box"](bm, (P["lever_t"] * 2, P["stem_t"] + P["lever_r"] - P["back_cut"],
                    P["lever_t"] * 2),
               (cx, (back + P["stem_t"] + cy - P["lever_r"]) / 2.0, cz))
    ob = _union(hm, coll, "eye_stem_%s" % side, prims)

    cuts, _c = _prims()
    cut = _c()
    hm["_cyl"](cut, P["link_d"], 20.0, (cx, cy - P["lever_r"], cz), 'Z',
               segs=24)
    # and a bite out of the spigot's lower front edge, where the axle's top
    # comes up past it into the dome's plug. Only the bottom 1 mm of the
    # axle's back surface is in the way, and the bite is entirely below
    # z=203 - well clear of the 5050's pad at z 205..213.
    cut = _c()
    hm["_cyl"](cut, P["axle_d"] + 1.2, 50.0, (cx, cy, P["axle_z1"] - 20.0),
               'Z', segs=48)
    _cut_each(hm, coll, ob, cuts, "_CUT_stem_%s" % side)
    return ob


def eye_axle(hm, coll, sx):
    """The eyeball's own shaft. Glues into the dome, turns in the cradle.

    A plain rod, so it prints standing on end - the only way to get a round
    journal out of an FDM printer. 10 mm of it is buried in the dome's
    bottom plug and the rest runs in the gimbal's bore.
    """
    side = "R" if sx > 0 else "L"
    bm = bmesh.new()
    hm["_cyl"](bm, P["axle_d"], P["axle_z1"] - P["axle_z0"],
               (sx * P["pitch"] / 2.0, P["y"],
                (P["axle_z0"] + P["axle_z1"]) / 2.0), 'Z', segs=48)
    ob = hm["_link"](coll, "eye_axle_%s" % side,
                     hm["_mesh"]("eye_axle_%s" % side, bm))
    ob.color = (0.78, 0.78, 0.80, 1.0)
    return ob


def gimbal(hm, coll):
    """Everything that rotates about the tilt axis: cradle, tubes, yoke.

    Turns on the frame's O5 shaft through two tubes at |x| 3.0..14.8, and
    carries the two eyelids on the OUTSIDE of those same tubes.

    Nothing in it reaches above the tilt axis, which is deliberate - the
    frame's mast has to come in over the top to reach x=0, so the two parts
    own opposite sides of the corridor and can never meet.

    Prints flat with +y upward: the whole part lives in a 14 mm slab either
    side of y=160, so it lies down on the bed. Both bearing axes end up
    horizontal in that orientation, which is why the tube bore and the pan
    bores are all sized with a diametral running clearance rather than a
    tight one.
    """
    ty, tz = P["y"], P["z"]
    prims, _p = _prims()

    cy0, cy1 = P["cradle_y0"], P["cradle_y1"]
    cz0, cz1 = P["cradle_z0"], P["cradle_z1"]

    # the cross bar between the two journals
    bm = _p()
    hm["_box"](bm, (2 * P["bar_hx"], cy1 - cy0, cz1 - cz0),
               (0.0, (cy0 + cy1) / 2.0, (cz0 + cz1) / 2.0))
    # a journal housing under each eye. ROUND, not a block: at 20 deg of
    # tilt a point Dz below the axis swings 0.342*Dz forward, so the
    # outboard-front corner of a box reaches y=178.5 at x=39 where the zone
    # runs out at 173.5. A cylinder has no corner there and clears.
    for sx in (-1, 1):
        cx = sx * P["pitch"] / 2.0
        bm = _p()
        hm["_cyl"](bm, P["pan_hub"], P["pan_z1"] - (P["pan_z0"] - 2.0),
                   (cx, ty, (P["pan_z1"] + P["pan_z0"] - 2.0) / 2.0), 'Z')
        # tie it to the cross bar
        bm = _p()
        hm["_box"](bm, (abs(cx) - P["bar_hx"] + 2.0, cy1 - cy0, cz1 - cz0),
                   (sx * (abs(cx) + P["bar_hx"] - 2.0) / 2.0,
                    (cy0 + cy1) / 2.0, (cz0 + cz1) / 2.0))
        # web from the cross bar up to the tube
        bm = _p()
        hm["_box"](bm, (P["web_x1"] - P["web_x0"], cy1 - cy0 - 2.0,
                        tz - cz0),
                   (sx * (P["web_x0"] + P["web_x1"]) / 2.0,
                    (cy0 + cy1) / 2.0, (tz + cz0) / 2.0))
        # the tube: the gimbal's own journal on the shaft, and the eyelid's
        # journal on its outside
        bm = _p()
        hm["_cyl"](bm, P["tube_od"], P["tube_x1"] - P["tube_x0"],
                   (sx * (P["tube_x0"] + P["tube_x1"]) / 2.0, ty, tz), 'X')

    # The tilt lever: a lug hanging BELOW the cross bar on the centreline.
    # Off the back of it, where it started, it sat at y 150.5..155.5 and the
    # pan bar's dipped middle is at 147..151 - so the two met at every tilt
    # angle, and so did the tilt pushrod.
    bm = _p()
    hm["_box"](bm, (10.0, 6.0, 10.0), (TILT_X, 156.0, cz0 - 4.0))
    ob = _union(hm, coll, "eye_gimbal", prims)

    cut = bmesh.new()
    # the two pan bores
    for sx in (-1, 1):
        hm["_cyl"](cut, P["pan_d"] + P["pan_fit"],
                   P["pan_z1"] + 2.0 - P["pan_z0"],
                   (sx * P["pitch"] / 2.0, ty,
                    (P["pan_z1"] + 2.0 + P["pan_z0"]) / 2.0), 'Z', segs=32)
    # the shaft bore, straight through both tubes
    hm["_cyl"](cut, P["shaft_d"] + P["shaft_fit"], 2 * P["tube_x1"] + 4.0,
               (0.0, ty, tz), 'X', segs=32)
    # the tilt link pin
    hm["_cyl"](cut, P["link_d"], 30.0,
               (TILT_X, 156.0, P["cradle_z0"] - 6.0), 'X', segs=24)
    hm["_apply"](coll, ob, cut, "_CUT_gimbal", 'DIFFERENCE')
    return ob


def frame(hm, coll):
    """The fixed bulkhead. One part, spanning both temple pads.

    It was two parts before, because "anything spanning between them would
    have to cross the eye bay at the height of the eyeballs". That is true
    at y=160 and false at y=140 - the domes are cut off at y=153 and the
    eyelids cannot reach further back than y=152.8, so behind the pan bar
    the bay is empty all the way across. The arch lives there.

    Prints flat on the arch, +y upward. Everything else stands off that
    plane in the +y direction: the pad plates 9 mm, the mast 22 mm, and the
    mast leans only 19 degrees off vertical on its way down to the shaft
    boss. There is nothing on the -y side at all, which is why the temple
    pegs are separate parts.
    """
    ty, tz = P["y"], P["z"]
    prims, _p = _prims()

    ay0, ay1 = P["arch_y0"], P["arch_y1"]
    az0, az1 = P["arch_z0"], P["arch_z1"]

    # The bar rides high, at z 224..232, and it has to: an eyeball panned 30
    # degrees swings its back rim out to |x|=44.6 at this depth, and reaches
    # z=219.8 doing it. Everything between |x|=15 and 47 is eyeball here.
    bm = _p()
    hm["_box"](bm, (2 * P["arch_hx"], ay1 - ay0, az1 - az0),
               (0.0, (ay0 + ay1) / 2.0, (az0 + az1) / 2.0))
    # ...and in the corridor between the eyes, where there is no eyeball, a
    # web brings it back down to where the mast can leave at a shallow
    # angle. This is what the frame gets for printing flat: the whole x-z
    # outline is the part's footprint, so shaping it costs nothing.
    bm = _p()
    hm["_box"](bm, (2 * P["arch_web"], ay1 - ay0 - 1.0, az1 - 2.0 - P["arch_z_lo"]),
               (0.0, (ay0 + ay1) / 2.0, (az1 - 2.0 + P["arch_z_lo"]) / 2.0))
    for sx in (-1, 1):
        # The temple plate: a tongue hanging off the bar down to the pad
        # bore, x 44..51.5 - outboard of the 42.6 that a panned eyeball
        # reaches, inboard of the 52.6 where the face half's wall is.
        bm = _p()
        hm["_box"](bm, (2 * P["plate_hx"], ay1 - ay0 - 1.0, az0 + 2.0 - (P["pad_z"] - 6.0)),
                   (sx * (P["pad_x"] - 1.5), (ay0 + ay1) / 2.0,
                    (az0 + 2.0 + P["pad_z"] - 6.0) / 2.0))
    # The mast, leaning forward and down from the web to the shaft. It has
    # to cross the whole bay in depth, from behind the eyes to the tilt axis
    # between them, and it is the one part of the frame that is not flat -
    # so its angle is the print's business: 29 degrees off vertical when the
    # part lies on its arch.
    dz = P["mast_z"] - tz
    dy = P["mast_y1"] - P["arch_y0"]
    bm = _p()
    _rbox(bm, (2 * P["mast_hx"], math.hypot(dy, dz) + 2.0, 8.0),
          (0.0, (P["arch_y0"] + P["mast_y1"]) / 2.0, (P["mast_z"] + tz) / 2.0),
          Matrix.Rotation(math.atan2(-dz, dy), 4, 'X'))
    bm = _p()
    hm["_cyl"](bm, P["boss_d"], 2 * P["mast_hx"], (0.0, ty, tz), 'X')
    ob = _union(hm, coll, "eye_frame", prims)

    cuts, _c = _prims()
    cut = _c()
    hm["_cyl"](cut, P["shaft_d"] + 0.2, 2 * P["mast_hx"] + 4.0,
               (0.0, ty, tz), 'X', segs=32)
    for sx in (-1, 1):
        cut = _c()
        # The peg socket is open outboard on purpose. The pad bore's centre
        # is 49.79 and the face half's inner wall is 2.9 mm outboard of it,
        # so there is no room for a wall on that side - the head's own wall
        # closes the slot instead.
        hm["_cyl"](cut, P["peg_fwd"] + 0.2, P["plate_y1"] - P["arch_y0"] + 4.0,
                   (sx * P["pad_x"], (P["plate_y1"] + P["arch_y0"]) / 2.0,
                    P["pad_z"]), 'Y', segs=24)
        # The mouth is 4.2 across against a 5.2 bore, so the peg snaps in
        # and stays. Cut the mouth the full 5.2 and its faces are tangent to
        # the bore, which is a coplanar-surface boolean by another name - it
        # left the frame with 15 open and 9 non-manifold edges.
        cut = _c()
        hm["_box"](cut, (6.0, P["plate_y1"] - P["arch_y0"] + 4.0, 3.6),
                   (sx * (P["pad_x"] + 3.0),
                    (P["plate_y1"] + P["arch_y0"]) / 2.0, P["pad_z"]))
    _cut_each(hm, coll, ob, cuts, "_CUT_frame")
    return ob


def shaft(hm, coll):
    """The tilt shaft. A separate part, and it has to be.

    The gimbal has two coaxial bores with a gap between them and the frame's
    mast sits in that gap, so the gimbal can never be threaded onto a shaft
    that is already there. Assemble gimbal into frame, line the bores up,
    push the shaft through. It prints standing on end, which is the only
    orientation in this whole mechanism that gives a truly round journal.
    """
    bm = bmesh.new()
    hm["_cyl"](bm, P["shaft_d"], 2 * P["shaft_x"], (0.0, P["y"], P["z"]), 'X',
               segs=32)
    ob = hm["_link"](coll, "eye_shaft", hm["_mesh"]("eye_shaft", bm))
    ob.color = (0.75, 0.75, 0.78, 1.0)
    return ob


def peg(hm, coll, sx):
    """Temple peg: locates the frame, and the two head halves, on one pin."""
    side = "R" if sx > 0 else "L"
    prims, _p = _prims()
    # Each section overlaps the next by 1 mm. Butted exactly, the union
    # found no intersection and the peg came out as three shells.
    bm = _p()
    hm["_cyl"](bm, P["peg_d"], P["pad_face"] - P["peg_y0"],
               (sx * P["pad_x"], (P["pad_face"] + P["peg_y0"]) / 2.0,
                P["pad_z"]), 'Y', segs=32)
    # No head on it, and that is the wall's doing rather than a choice. The
    # face half closes to x=52.2 by y=151.5, and the bore's centre is 49.79
    # - so there are 2.4 mm to play with and a flange needs more. The frame
    # is retained by its socket instead, which is a snap: the mouth is
    # 3.6 across on a 4.6 bore, so the peg goes in and stays.
    bm = _p()
    hm["_cyl"](bm, P["peg_fwd"], P["plate_y1"] + 0.5 - (P["pad_face"] - 1.0),
               (sx * P["pad_x"], (P["plate_y1"] + 0.5 + P["pad_face"] - 1.0) / 2.0,
                P["pad_z"]), 'Y', segs=32)
    ob = _union(hm, coll, "eye_peg_%s" % side, prims)
    ob.color = (0.75, 0.75, 0.78, 1.0)
    return ob


def eyelid(hm, coll, sx):
    """One upper eyelid: a spherical shell on a hub round the gimbal's tube.

    Built SHUT and posed open, so one mesh serves both and `check()` can ask
    the same question at every angle in between.

    It pivots on the tilt axis because it has to: a shell that stays 0.4 mm
    off a ball has to turn about that ball's centre, and the ball's centre
    is on the tilt axis. Riding it on the gimbal's tube rather than on the
    frame means it tilts with the eye and does not have to be told to - a
    lid on the fixed frame would change its gap to the eye by 5.6 mm across
    +-20 degrees of tilt.

    The hub is a plain bore, not a snap. It cannot fall off: inboard it
    meets the gimbal's web, and outboard the shell itself would have to go
    eccentric to the ball it wraps, which the ball will not allow. Slide it
    on before the eyeball goes in.
    """
    side = "R" if sx > 0 else "L"
    cx, cy, cz = sx * P["pitch"] / 2.0, P["y"], P["z"]
    ri = P["ball"] / 2.0 + LID["gap"]
    ro = ri + LID["shell"]

    bm = bmesh.new()
    _sphere(bm, ro * 2, (cx, cy, cz), segs=64)
    ob = hm["_link"](coll, "eye_lid_%s" % side, hm["_mesh"]("eye_lid_%s" % side, bm))
    cut = bmesh.new()
    _sphere(cut, ri * 2, (cx, cy, cz), segs=64)
    hm["_apply"](coll, ob, cut, "_CUT_lid_in_%s" % side, 'DIFFERENCE')

    # Trim to a band. Angles run from straight ahead, positive upward, and
    # both cutting planes contain the X axis - so the band is a zone about
    # the tilt axis and covers the eye evenly whatever the socket's rake.
    t0 = math.radians(LID["closed"])
    t1 = math.radians(LID["closed"] + LID["span"])
    for k, n in enumerate((Vector((0.0, math.sin(t0), -math.cos(t0))),
                           Vector((0.0, -math.sin(t1), math.cos(t1))))):
        cut = bmesh.new()
        # At the ORIGIN in the mesh, because matrix_world below is what
        # places it. Built at (cx, cy, cz) as well, it got the eye centre
        # applied twice and landed half a head away, so both plane cuts
        # silently did nothing and the "band" came out a full sphere shell.
        hm["_box"](cut, (80.0, 80.0, 80.0), (0.0, 0.0, 0.0))
        me = bpy.data.meshes.new("_t")
        cut.to_mesh(me)
        cut.free()
        tmp = bpy.data.objects.new("_CUT_lid_%d_%s" % (k, side), me)
        coll.objects.link(tmp)
        tmp.matrix_world = (Matrix.Translation(Vector((cx, cy, cz)) + n * 40.0)
                            @ Vector((0, 0, 1)).rotation_difference(n).to_matrix().to_4x4())
        hm["boolean"](ob, tmp, 'DIFFERENCE')
        bpy.data.objects.remove(tmp, do_unlink=True)

    adds, _a = _prims()
    # the hub, on the gimbal tube
    add = _a()
    hm["_cyl"](add, LID["hub_od"], LID["hub_x1"] - LID["hub_x0"],
               (sx * (LID["hub_x0"] + LID["hub_x1"]) / 2.0, cy, cz), 'X',
               segs=32)
    # The crank, and it is a dog-leg rather than a straight arm.
    #
    # Its root has to be on the hub, at |x| under 14.8, and its pin has to
    # be outboard of the gimbal's tube, which ends at 14.8 - otherwise the
    # pushrod coming back from the pin runs straight through the tube. So
    # the arm starts inboard, and steps out to |x| 15..17.5 once it is far
    # enough from the axis to be clear of the eyeball, whose surface at
    # x=17.5 is only 8.6 mm from the tilt axis.
    a = math.radians(LID["crank_a"])
    kx = sx * (LID["crank_x0"] + LID["crank_x1"]) / 2.0
    px = sx * (LID["pin_x0"] + LID["pin_x1"]) / 2.0
    ca, sa = math.cos(a), math.sin(a)
    add = _a()
    # Long enough to run 2 mm PAST the pin boss rather than up to it. Ending
    # at r=11 with the boss starting at r=11 is a coplanar butt, not an
    # intersection, and the lid came out as two shells the moment the
    # dog-leg that used to bridge them was removed.
    arm = LID["crank_r"] + 4.0
    _rbox(add, (LID["crank_x1"] - LID["crank_x0"], arm, LID["crank_t"]),
          (kx, cy + ca * (arm / 2.0 - 2.0), cz + sa * (arm / 2.0 - 2.0)),
          Matrix.Rotation(a, 4, 'X'))
    # 0.4 shorter than the tab it sits on, so its end caps land strictly
    # inside the tab's faces. Made the same length, the two are coplanar and
    # the union leaves the crank ringed with non-manifold edges.
    add = _a()
    hm["_cyl"](add, LID["crank_t"] + 3.0, LID["pin_x1"] - LID["pin_x0"] - 0.4,
               (px, cy + ca * LID["crank_r"], cz + sa * LID["crank_r"]),
               'X', segs=24)
    _add_each(hm, coll, ob, adds, "_LIDADD_%s" % side)

    cuts, _c = _prims()
    # The bore runs out to x=17, past the hub's own end at 14.8. Stopped
    # exactly on it, the bore's end cap was coplanar with the hub's and the
    # lid came out with 113 non-manifold edges.
    cut = _c()
    hm["_cyl"](cut, P["tube_od"] + LID["hub_fit"], 17.0 - 4.0,
               (sx * (4.0 + 17.0) / 2.0, cy, cz), 'X', segs=32)
    cut = _c()
    hm["_cyl"](cut, P["link_d"], 20.0,
               (px, cy + ca * LID["crank_r"], cz + sa * LID["crank_r"]),
               'X', segs=24)
    # and the outboard trim - see LID['trim_x']
    cut = _c()
    hm["_box"](cut, (40.0, 90.0, 90.0), (sx * (LID["trim_x"] + 20.0), cy, cz))
    _cut_each(hm, coll, ob, cuts, "_CUT_lid_%s" % side)
    ob.color = (0.85, 0.65, 0.4, 1.0)
    return ob


def pan_bar(hm, coll):
    """The bar that makes both eyes pan together.

    Each dome's lever hangs a vertical pin 11 mm behind its pan axis and 8
    below the eye line. One bar joins both pins, so shoving it along X
    swings both levers. +-30 degrees needs +-5.5 mm of travel.

    It sits at y 147..151, behind the whole gimbal - the cradle starts at
    154 - which is the reason it does not have to dodge anything.
    """
    ty, tz = P["y"], P["z"]
    py = ty - P["lever_r"]
    pz = tz - P["pin_drop"]
    dip = 12.0               # deep enough that both eyelid pushrods clear
                            # it at 16 degrees of down-tilt, when the bar
                            # swings up and back toward them
    prims, _p = _prims()
    # The two ends, carrying the eye pins and the servo pin
    for sx in (-1, 1):
        bm = _p()
        hm["_box"](bm, (P["pitch"] / 2.0 + 6.0 - 28.0, 4.0, P["link_t"] + 2.0),
                   (sx * (P["pitch"] / 2.0 + 6.0 + 28.0) / 2.0, py, pz))
    # ...and a middle that drops 8 mm out of the way.
    #
    # Straight across, the bar sat at z 190.5..195.5 right where both eyelid
    # pushrods have to come back from their cranks, and it took them out at
    # every tilt angle. It cannot go lower as a whole - the eye levers hang
    # off it - and it cannot go higher without meeting the gimbal. So the
    # middle, which is only a beam joining two pins, gets out of the way.
    bm = _p()
    hm["_box"](bm, (60.0, 4.0, P["link_t"] + 2.0), (0.0, py, pz - dip))
    for sx in (-1, 1):
        bm = _p()
        hm["_box"](bm, (5.0, 4.0, dip + P["link_t"] + 2.0),
                   (sx * 28.5, py, pz - dip / 2.0))
    # And a lug hanging below the dip for the servo's own pushrod.
    #
    # Pinned straight into the dip, the rod ran along the underside of the
    # bar and fouled it by 0.84 mm at full pan and down-tilt - which the
    # overlap test could never report, because a rod in its own pin hole is
    # in ALLOWED. `clearances()` found it. Six millimetres of lug puts the
    # joint clear of the bar's body and the rod approaches from open air.
    bm = _p()
    hm["_box"](bm, (8.0, 4.0, PAN_LUG + P["link_t"] + 2.0),
               (SERVOS["pan"]["drive"][0], py,
                pz - dip - PAN_LUG / 2.0 + (P["link_t"] + 2.0) / 2.0))
    bar = _union(hm, coll, "eye_pan_bar", prims)
    cut = bmesh.new()
    for sx in (-1, 1):
        hm["_cyl"](cut, P["link_d"], 20.0,
                   (sx * P["pitch"] / 2.0, py, pz), 'Z', segs=24)
    hm["_cyl"](cut, P["link_d"], 20.0,
               (SERVOS["pan"]["drive"][0], py, pz - dip - PAN_LUG),
               'Z', segs=24)
    hm["_apply"](coll, bar, cut, "_CUT_pan_bar", 'DIFFERENCE')
    return bar


# ---------------------------------------------------------------------------
# the servos, and the linkage that reaches them
# ---------------------------------------------------------------------------
# Body and total height come from the datasheet and agree with what
# eye_mech.P has carried all along - 22.5 x 12 x 22.7, 35.5 total. The tab
# pitch is 28.0 and it is the one number here that is PROVEN: coupon_mg90s
# was printed and the real servos fitted it, 15 Aug.
SERVO = dict(l=22.5, w=12.0, h=22.7, total_h=35.5,
             tab_pitch=28.0, tab_l=32.2, tab_t=2.5, tab_up=16.0,
             shaft_d=5.5, shaft_up=4.5, shaft_off=6.0)

SERVO_Y = 126.0     # all four shafts in one plane, so one plate carries them
PAN_LUG = 6.0       # how far the pan bar's drive pin hangs below the dip
TILT_X  = -4.0      # the tilt lug and its servo share this, and they have
                    # to: both ends of that pushrod are hinges about X

# All four servos are on the FIXED plate, and that settles a contradiction
# this file used to carry. The header said pan and both lids "ride on the
# gimbal"; the servo placement put all four at y=126, which is 34 mm behind
# the tilt axis - a servo there would swing +-11.7 mm every time the eyes
# looked up or down, and the gimbal would have to be a structure 45 mm deep
# to hold it.
#
# What riding on the frame costs is cross-coupling: tilt moves the far end
# of every pushrod, so pan and lid angles change slightly with tilt. That is
# a linear, repeatable, hysteresis-free error on a machine with a Pi and
# sixteen PWM channels, so it is mixed out in software. It is not worth a
# gimbal three times the size.
#
# `horn` is the crank radius on the servo. `drive` is the point on the
# mechanism it pulls, in the neutral pose. `axis` is the shaft direction:
# pan's is vertical because it moves a bar along X; the other three drive
# levers that pivot about X, so their shafts run along X and their horns
# sweep the y-z plane the motion happens in.
#
# The two lid servos are mirror images at the same height, which they were
# not: lid_L used to sit 36 mm lower, and it could only deliver 38.5 of the
# 50 degrees the lid needs once the eyes were tilted up. There was no reason
# for the asymmetry - with the shafts at +-12.8 and both bodies pointing
# outboard they never touch - it was left over from a layout whose shafts
# were at +-28.
#
# Stacked in z rather than spread in x, because the pushrods have to get
# past the frame's arch at y 138..142, z 214..222 and past the pan bar at
# y 147..151. Both of those span the full width, so a rod cannot go round
# them - it goes under. That is what fixes the servo heights, not packing.
SERVOS = {
    "pan":   dict(loc=(24.0, SERVO_Y, P["z"] - P["pin_drop"] - 12.0 - PAN_LUG),
                  axis=None,  horn=13.5,
                  drive=(24.0, P["y"] - P["lever_r"],
                         P["z"] - P["pin_drop"] - 12.0 - PAN_LUG)),
    "tilt":  dict(loc=(TILT_X, SERVO_Y, 145.0), axis='X',   horn=13.6,
                  drive=(TILT_X, 156.0, P["cradle_z0"] - 6.0)),
    "lid_R": dict(loc=(12.8, SERVO_Y, 212.0), axis='-X',  horn=17.0,
                  drive=None),
    "lid_L": dict(loc=(-12.8, SERVO_Y, 212.0), axis='X',  horn=17.0,
                  drive=None),
}


def _lid_pin(sx, opened=0.0):
    """Where a lid's crank pin sits, for a lid `opened` degrees off shut."""
    a = math.radians(LID["crank_a"] + opened)
    return Vector((sx * (LID["pin_x0"] + LID["pin_x1"]) / 2.0,
                   P["y"] + math.cos(a) * LID["crank_r"],
                   P["z"] + math.sin(a) * LID["crank_r"]))


def servo_proxy(hm, coll, name, loc, rot=None):
    """A solid MG90S at `loc`, output shaft up (+Z) unless rotated.

    Origin is the CENTRE OF THE OUTPUT SHAFT at the top face of the body,
    because that is the point a linkage is designed around - not the centre
    of the box, which is where a proxy placed by eye ends up and why it then
    disagrees with the horn by 6 mm.
    """
    s = SERVO
    prims, _p = _prims()
    bm = _p()
    hm["_box"](bm, (s["l"], s["w"], s["h"]), (-s["shaft_off"], 0.0, -s["h"] / 2.0))
    bm = _p()
    hm["_box"](bm, (s["tab_l"], s["w"], s["tab_t"]),
               (-s["shaft_off"], 0.0, -s["h"] + s["tab_up"]))
    bm = _p()
    hm["_cyl"](bm, s["shaft_d"] * 2.2, 4.0, (0.0, 0.0, -2.0), 'Z')
    bm = _p()
    hm["_cyl"](bm, s["shaft_d"], s["shaft_up"], (0.0, 0.0, s["shaft_up"] / 2.0), 'Z')
    ob = _union(hm, coll, name, prims)
    if rot is not None:
        ob.data.transform(rot)
    ob.data.transform(Matrix.Translation(Vector(loc)))
    ob.color = (0.9, 0.2, 0.2, 1.0)
    return ob


def place_servos(hm, coll):
    """Drop the four MG90S proxies where SERVOS says, so every later part is
    drawn against a servo that is really there rather than a remembered one."""
    rots = {None: None,
            'X': Matrix.Rotation(math.radians(90), 4, 'Y'),
            '-X': Matrix.Rotation(math.radians(-90), 4, 'Y')}
    out = []
    for name, s in SERVOS.items():
        for o in list(coll.objects):
            if o.name == "PROXY_servo_" + name:
                bpy.data.objects.remove(o, do_unlink=True)
        out.append(servo_proxy(hm, coll, "PROXY_servo_" + name, s["loc"],
                               rots[s["axis"]]))
    return out


def horn_pin(name, angle_deg):
    """Where a servo's horn pin is, at `angle_deg` off its neutral."""
    s = SERVOS[name]
    o = Vector(s["loc"])
    a = math.radians(angle_deg + s.get("horn0", 0.0))
    r = s["horn"]
    if s["axis"] is None:                 # vertical shaft, horn sweeps x-y
        return o + Vector((r * math.sin(a), -r * math.cos(a), 0.0))
    # shaft along X, horn sweeps y-z
    return o + Vector((0.0, -r * math.cos(a), r * math.sin(a)))


def _rod_targets():
    return [o for o in bpy.data.objects
            if o.type == 'MESH'
            and (o.name.startswith("eye_") or o.name in
                 ("HEAD_FACE", "HEAD_CRANIUM", "FIT_forehead_casing"))
            and not o.name.startswith("eye_rod_")]


def _rod_clearance(name, plist=None, step=4.0):
    """Smallest gap between one pushrod and everything else, joints aside."""
    if not _ROD_L:
        _rods()
    worst = 1e9
    for pz in (plist or poses(coarse=True)):
        pose(*pz)
        far = _drive_points(*pz)[name]
        ang, _e = solve_horn(name, far, _ROD_L[name])
        near = horn_pin(name, ang)
        n = max(6, int((far - near).length / step))
        for i in range(n + 1):
            q = near.lerp(far, i / float(n))
            if (q - far).length < 4.5 or (q - near).length < 4.5:
                continue
            for o in _rod_targets():
                hit, loc, nrm, _i = o.closest_point_on_mesh(
                    o.matrix_world.inverted() @ q)
                if hit:
                    worst = min(worst, ((o.matrix_world @ loc) - q).length
                                - ROD_D / 2.0)
    pose()
    return worst


def phase_horns(verbose=False):
    """Set each servo's neutral horn angle, and it is not a free choice.

    A horn pushing a pushrod transmits nothing when the arm points along the
    rod and everything when it points across it, so the neutral position has
    to be the across-it one. Left at zero, the tilt servo's horn pointed
    straight back down its own rod: it could deliver -5.5..+18 degrees of a
    range that needs +-20, and it read as a linkage that did not fit when it
    was only a linkage that was out of phase.

    There are always two perpendicular solutions, 180 apart. Both transmit
    the same; they put the horn on opposite sides. So both are tried and the
    one with the wider envelope is kept, which also quietly picks the one
    that is not trying to swing the horn into the servo's own body.
    """
    for name, s in SERVOS.items():
        drive = _dof_point(name, 0.0, 0.0)
        best, bscore = 0.0, -1.0
        for a0 in range(0, 360, 1):
            s["horn0"] = float(a0)
            d1 = (horn_pin(name, 0.5) - drive).length
            d0 = (horn_pin(name, -0.5) - drive).length
            score = abs(d1 - d0)
            if score > bscore:
                best, bscore = float(a0), score
        # Two solutions, 180 apart. They transmit identically and cover the
        # same range - and they sweep the pushrod through completely
        # different places. Picking on range alone put the eyelid horns
        # pointing DOWN, which swung both rods through the gimbal's cradle
        # and the pan bar on the way back to the servo. So: require the
        # range, then choose on clearance.
        cands = [best, (best + 180.0) % 360.0]
        need = (P["pan_max"] if name == "pan" else
                P["tilt_max"] if name == "tilt" else LID["park"])
        want = (-need, need) if name in ("pan", "tilt") else (0.0, need)
        scored = []
        for c in cands:
            s["horn0"] = c
            _ROD_L.clear()
            _rods()
            rows = reach(verbose=False, hstep=3.0, dstep=1.0)[name]
            covers = all(lo is not None and lo <= want[0] + 1.0
                         and hi >= want[1] - 1.0 for _t, lo, hi in rows)
            span = sum(0.0 if lo is None else hi - lo for _t, lo, hi in rows)
            scored.append((covers, _rod_clearance(name), span, c))
        scored.sort(key=lambda r: (r[0], round(r[1], 2), r[2]))
        covers, clr, span, pick = scored[-1]
        s["horn0"] = pick
        if verbose:
            print("  %-6s horn neutral %+6.1f deg, rod clears by %.2f mm%s"
                  % (name, pick, clr, "" if covers else "  (RANGE SHORT)"))
    _ROD_L.clear()
    _rods()


def solve_horn(name, target, length, lo=-90.0, hi=90.0):
    """The horn angle that puts the pin `length` from `target`.

    Returns (angle, error). Used for DRAWING a rod in a given pose; a small
    residual error just means the rod is shown a fraction long or short.
    It is NOT the test of whether the linkage works - see `reach()`.
    """
    best, berr = None, 1e9
    a = lo
    while a <= hi:
        err = abs((horn_pin(name, a) - Vector(target)).length - length)
        if err < berr:
            best, berr = a, err
        a += 0.25
    return best, berr


def _dof_point(name, tilt, dof):
    """Where `name`'s drive pin sits, for a given tilt and its own DOF."""
    if name == "pan":
        return _drive_points(tilt, dof, 0.0, 0.0)["pan"]
    if name == "tilt":
        return _drive_points(dof, 0.0, 0.0, 0.0)["tilt"]
    if name == "lid_R":
        return _drive_points(tilt, 0.0, dof, 0.0)["lid_R"]
    return _drive_points(tilt, 0.0, 0.0, dof)["lid_L"]


def reach(horn_limit=70.0, verbose=True, hstep=1.0, dstep=0.5):
    """What each servo can actually deliver, tilt by tilt.

    This replaces a check that asked the wrong question. The old one fixed a
    pose and looked for a horn angle that made the rod exactly the right
    length, and reported FAIL when it could not find one - but a rigid rod
    plus a horn is a one-degree-of-freedom linkage, so for a given tilt the
    driven angle is a FUNCTION of the horn angle, not something you get to
    specify. "Cannot reach tilt -20 with pan 0" was never a fault; it was
    the cross-coupling being measured and misread.

    The real question is whether the range that IS reachable covers what the
    eye needs, at every tilt. So: sweep the horn, solve for the driven
    angle, report the envelope. What the numbers show is how much of each
    servo's travel the Pi has to spend cancelling tilt.
    """
    if not _ROD_L:
        _rods()
    out = {}
    for name, lim in (("pan", P["pan_max"]), ("tilt", P["tilt_max"]),
                      ("lid_R", LID["park"]), ("lid_L", LID["park"])):
        L = _ROD_L[name]
        rows = []
        for tilt in ((0.0,) if name == "tilt" else (-P["tilt_max"], 0.0,
                                                    P["tilt_max"])):
            lo_d, hi_d = None, None
            a = -horn_limit
            while a <= horn_limit:
                pin = horn_pin(name, a)
                best, berr = None, 1e9
                d = (-lim - 20.0) if name != "tilt" else -lim - 10.0
                top = (lim + 20.0) if name != "tilt" else lim + 10.0
                if name in ("lid_R", "lid_L"):
                    d, top = -15.0, lim + 25.0
                while d <= top:
                    err = abs((_dof_point(name, tilt, d) - pin).length - L)
                    if err < berr:
                        best, berr = d, err
                    d += dstep
                if berr < 0.05 + dstep * 0.15:
                    lo_d = best if lo_d is None else min(lo_d, best)
                    hi_d = best if hi_d is None else max(hi_d, best)
                a += hstep
            rows.append((tilt, lo_d, hi_d))
        out[name] = rows
    if verbose:
        print("linkage envelope - what the servo can actually deliver:")
        for name, rows in out.items():
            need = (P["pan_max"] if name == "pan" else
                    P["tilt_max"] if name == "tilt" else LID["park"])
            want = (-need, need) if name in ("pan", "tilt") else (0.0, need)
            allok = True
            for tilt, lo_d, hi_d in rows:
                got = "unreachable" if lo_d is None else \
                    "%+7.1f..%+7.1f" % (lo_d, hi_d)
                good = (lo_d is not None and lo_d <= want[0] + 0.6
                        and hi_d >= want[1] - 0.6)
                allok = allok and good
                print("  %-6s at tilt %+5.1f : %s  (needs %+.0f..%+.0f)  %s"
                      % (name, tilt, got, want[0], want[1],
                         "OK" if good else "SHORT"))
            if not allok:
                print("        ^ %s cannot cover its range at every tilt"
                      % name)
    return out


# ---------------------------------------------------------------------------
# posing - one place that knows how the mechanism moves
# ---------------------------------------------------------------------------
def _tilt_m(deg):
    c = Vector((0.0, P["y"], P["z"]))
    return (Matrix.Translation(c) @ Matrix.Rotation(math.radians(deg), 4, 'X')
            @ Matrix.Translation(-c))


def _pan_m(sx, deg):
    c = Vector((sx * P["pitch"] / 2.0, P["y"], 0.0))
    return (Matrix.Translation(c) @ Matrix.Rotation(math.radians(deg), 4, 'Z')
            @ Matrix.Translation(-c))


def pose(tilt=0.0, pan=0.0, lid_R=None, lid_L=None, lid=None, rods=True):
    """Put the mechanism somewhere. Angles in degrees.

    `lid` is how far open each eyelid is, 0 = shut, LID['park'] = open; pass
    lid_R and lid_L separately to wink. The order of these arguments matters
    and used to be wrong: `poses()` hands over (tilt, pan, lidR, lidL) and
    the third slot was `lid`, so every swept pose silently set both lids to
    the right lid's angle and the two wink poses tested nothing.
    """
    lid_R = LID["park"] if lid_R is None else lid_R
    lid_L = LID["park"] if lid_L is None else lid_L
    if lid is not None:
        lid_R = lid_L = lid
    T = _tilt_m(tilt)
    g = bpy.data.objects.get("eye_gimbal")
    if g:
        g.matrix_world = T
    for sx, side, la in ((1, "R", lid_R), (-1, "L", lid_L)):
        d = bpy.data.objects.get("eye_dome_%s" % side)
        if d:
            d.matrix_world = T @ _pan_m(sx, pan)
        # The 5050 is glued INSIDE the dome, so it goes where the dome goes.
        # Left standing still it was perfectly placed at rest and swept
        # through by its own eyeball at every other angle.
        for nm in ("eye_stem_%s" % side, "eye_axle_%s" % side):
            o = bpy.data.objects.get(nm)
            if o:
                o.matrix_world = T @ _pan_m(sx, pan)
        led = bpy.data.objects.get("PROXY_eye_led_%s_LISTING" % side)
        if led is not None:
            if side not in _LED_REST:
                _LED_REST[side] = led.matrix_world.copy()
            led.matrix_world = T @ _pan_m(sx, pan) @ _LED_REST[side]
        l = bpy.data.objects.get("eye_lid_%s" % side)
        if l:
            l.matrix_world = T @ _tilt_m(la)
    bar = bpy.data.objects.get("eye_pan_bar")
    if bar:
        a = math.radians(pan)
        bar.matrix_world = T @ Matrix.Translation(Vector((
            P["lever_r"] * math.sin(a),
            P["lever_r"] * (1.0 - math.cos(a)), 0.0)))
    if rods:
        _rods(tilt, pan, lid_R, lid_L)
    return dict(tilt=tilt, pan=pan, lid_R=lid_R, lid_L=lid_L)


def _drive_points(tilt, pan, lid_R, lid_L):
    """Where each servo's far end is, in this pose."""
    T = _tilt_m(tilt)
    a = math.radians(pan)
    panpt = (T @ Matrix.Translation(Vector((P["lever_r"] * math.sin(a),
                                            P["lever_r"] * (1 - math.cos(a)),
                                            0.0)))) @ Vector(SERVOS["pan"]["drive"])
    return {
        "pan": panpt,
        "tilt": T @ Vector(SERVOS["tilt"]["drive"]),
        "lid_R": T @ _tilt_m(lid_R) @ _lid_pin(1),
        "lid_L": T @ _tilt_m(lid_L) @ _lid_pin(-1),
    }


_ROD_L = {}
_LED_REST = {}     # where the 5050 proxies sit before anything moves


def _rods(tilt=0.0, pan=0.0, lid_R=None, lid_L=None):
    """Redraw the four pushrods for the current pose, solving each servo.

    The rods are wire links with a Z-bend at each end, not printed parts.
    They are drawn because a rod that fouls the gimbal at one end of its
    travel is exactly the kind of fault that only shows up in a pose.
    """
    hm = _hm()
    coll = bpy.data.collections.get(COLL)
    if coll is None:
        return
    lid_R = LID["park"] if lid_R is None else lid_R
    lid_L = LID["park"] if lid_L is None else lid_L
    if not _ROD_L:
        base = _drive_points(0.0, 0.0, 0.0, 0.0)
        for k, v in base.items():
            _ROD_L[k] = (horn_pin(k, 0.0) - v).length
    pts = _drive_points(tilt, pan, lid_R, lid_L)
    for name, far in pts.items():
        for o in list(coll.objects):
            if o.name == "eye_rod_" + name:
                bpy.data.objects.remove(o, do_unlink=True)
        ang, err = solve_horn(name, far, _ROD_L[name])
        near = horn_pin(name, ang)
        v = far - near
        bm = bmesh.new()
        hm["_cyl"](bm, ROD_D, v.length, tuple((near + far) / 2.0), 'Z',
                   direction=tuple(v.normalized()), segs=16)
        ob = hm["_link"](coll, "eye_rod_%s" % name,
                         hm["_mesh"]("eye_rod_%s" % name, bm))
        ob.color = (0.2, 0.75, 0.95, 1.0)

        # The horn: the white plastic arm that comes in the bag with the
        # servo and clips onto its output shaft. Not drawn at all until now,
        # which made every one of these pictures show a wire running to a
        # bare servo body with nothing joining the two. It is not a printed
        # part and it is not optional - it is what turns shaft rotation into
        # a push on the wire.
        for o in list(coll.objects):
            if o.name == "PROXY_horn_" + name:
                bpy.data.objects.remove(o, do_unlink=True)
        axis = Vector((0.0, 0.0, 1.0)) if SERVOS[name]["axis"] is None \
            else Vector((1.0, 0.0, 0.0))
        o0 = Vector(SERVOS[name]["loc"])
        arm = near - o0
        bm = bmesh.new()
        hm["_cyl"](bm, 8.0, 4.0, tuple(o0 + axis * 1.0), 'Z',
                   direction=tuple(axis), segs=24)          # hub on the shaft
        hm["_cyl"](bm, 5.0, arm.length, tuple(o0 + arm / 2.0 + axis * 1.0),
                   'Z', direction=tuple(arm.normalized()), segs=16)
        hm["_cyl"](bm, 6.0, 2.6, tuple(near + axis * 1.0), 'Z',
                   direction=tuple(axis), segs=20)          # the pin hole boss
        hb = hm["_link"](coll, "PROXY_horn_%s" % name,
                         hm["_mesh"]("PROXY_horn_%s" % name, bm))
        hb.color = (0.94, 0.94, 0.92, 1.0)
        for o in (ob, hb):
            for f in o.data.polygons:
                f.use_smooth = True
    return pts


# ---------------------------------------------------------------------------
def printability(name, up=(0.0, 1.0, 0.0), limit=45.0, verbose=True):
    """How much of a part overhangs, printed with `up` pointing at the sky.

    This project's rule is no supports anywhere, and until now that has been
    argued rather than measured - which is how the eyeball domes came to
    carry a docstring saying they print flat-back-down when no orientation
    prints them at all.

    It is first-order on purpose: it reports downward-facing area steeper
    than `limit` off vertical, and how far above the lowest point that area
    starts. A face that overhangs but sits on the very first layer is a
    chamfer the bed holds up; the same face 10 mm in the air is a support.
    """
    ob = bpy.data.objects.get(name)
    if ob is None:
        return None
    u = Vector(up).normalized()
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.transform(bm, verts=bm.verts[:], matrix=ob.matrix_world)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    lo = min((v.co.dot(u) for v in bm.verts), default=0.0)
    hi = max((v.co.dot(u) for v in bm.verts), default=0.0)
    total = bad = 0.0
    worst_h, worst_a = 0.0, 0.0
    cos_lim = -math.cos(math.radians(90.0 - limit))
    for f in bm.faces:
        a = f.calc_area()
        total += a
        d = f.normal.normalized().dot(u)
        if d >= cos_lim:
            continue                       # not a steep downward face
        h = f.calc_center_median().dot(u) - lo
        if h < 0.6:
            continue                       # sitting on the bed
        bad += a
        ang = math.degrees(math.acos(max(-1.0, min(1.0, -d))))
        if h > worst_h:
            worst_h, worst_a = h, 90.0 - ang
    bm.free()
    frac = bad / total if total else 0.0
    if verbose:
        print("  %-16s %6.1f mm tall, %7.1f mm2 overhangs past %.0f deg (%.1f%%)"
              % (name, hi - lo, bad, limit, 100.0 * frac), end="")
        if bad <= 0.0:
            print("   PRINTS")
        else:
            print(", highest %.1f mm up" % worst_h)
    return dict(height=hi - lo, frac=frac, area=bad, worst_h=worst_h)


def printability_all(up=(0.0, 1.0, 0.0), limit=45.0):
    c = bpy.data.collections.get(COLL)
    if c is None:
        return
    print("printability, +Y up, %.0f deg limit:" % limit)
    for o in sorted(c.objects, key=lambda o: o.name):
        if o.type == 'MESH' and not o.name.startswith("PROXY_") \
                and not o.name.startswith("eye_rod_"):
            printability(o.name, up=up, limit=limit)


SMOOTH_ANGLE = 35.0


def smooth_all(angle=None, coll=None, verbose=False):
    """Shade everything smooth, BY ANGLE.

    Not plain shade-smooth. Every face in these parts is already flagged
    smooth and they still render faceted, because from Blender 4.1 the flag
    on its own is not what does it - smoothing is a modifier now. And plain
    smooth-everything is the wrong answer anyway: it rounds the corners of
    the boxes as well as the spheres, so a printed bracket ends up looking
    like a bar of soap. By angle, the domes and the tubes go smooth and every
    edge sharper than 35 degrees stays an edge.
    """
    angle = SMOOTH_ANGLE if angle is None else angle
    c = coll or bpy.data.collections.get(COLL)
    if c is None:
        return 0
    prev = bpy.context.view_layer.objects.active
    n = 0
    for o in list(c.objects):
        if o.type != 'MESH':
            continue
        for p in o.data.polygons:
            p.use_smooth = True
        try:
            for x in bpy.context.view_layer.objects:
                x.select_set(False)
            bpy.context.view_layer.objects.active = o
            o.select_set(True)
            bpy.ops.object.shade_auto_smooth(angle=math.radians(angle))
            n += 1
        except Exception as exc:
            print("    %s: auto-smooth failed (%s)" % (o.name, exc))
    if prev is not None:
        try:
            bpy.context.view_layer.objects.active = prev
        except Exception:
            pass
    if verbose:
        print("  shaded %d objects smooth by %.0f degrees" % (n, angle))
    return n


def build(save=False):
    hm = _hm()
    old = bpy.data.collections.get(COLL)
    if old:
        for o in list(old.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(old)
    coll = bpy.data.collections.new(COLL)
    bpy.context.scene.collection.children.link(coll)
    print("eye_v2:")
    made = []
    for sx in (1, -1):
        made.append(_solidify(eyeball(hm, coll, sx)))
    for sx in (1, -1):
        made.append(_solidify(eye_stem(hm, coll, sx)))
    for sx in (1, -1):
        made.append(eye_axle(hm, coll, sx))
    made.append(_solidify(gimbal(hm, coll)))
    made.append(_solidify(frame(hm, coll)))
    made.append(shaft(hm, coll))
    for sx in (1, -1):
        made.append(_solidify(peg(hm, coll, sx)))
    for sx in (1, -1):
        made.append(_solidify(eyelid(hm, coll, sx)))
    made.append(_solidify(pan_bar(hm, coll)))
    for ob in made:
        print("  %-14s %d verts" % (ob.name, len(ob.data.vertices)))
    place_servos(hm, coll)
    _ROD_L.clear()
    _LED_REST.clear()
    for side in ("R", "L"):
        led = bpy.data.objects.get("PROXY_eye_led_%s_LISTING" % side)
        if led is not None:
            _LED_REST[side] = led.matrix_world.copy()
    smooth_all(verbose=True)
    print("  servo horns:")
    phase_horns(verbose=True)
    pose()
    if save:
        bpy.ops.wm.save_mainfile()
    return coll


# ---------------------------------------------------------------------------
# verification - the part that decides whether any of this is real
# ---------------------------------------------------------------------------
_DIRS = [Vector(d).normalized() for d in ((0.9137, 0.3184, 0.2513),
                                          (-0.2711, 0.8455, -0.4602),
                                          (0.1877, -0.3391, 0.9219))]

MOVING = ("eye_gimbal", "eye_dome_R", "eye_dome_L", "eye_lid_R", "eye_lid_L",
          "eye_stem_R", "eye_stem_L", "eye_axle_R", "eye_axle_L",
          "eye_pan_bar", "eye_rod_pan", "eye_rod_tilt", "eye_rod_lid_R",
          "eye_rod_lid_L")

# Pairs that are a bearing, a pin in a hole, or a rod in its own eye - the
# only ones allowed to share space.
ALLOWED = {
    ("eye_gimbal", "eye_dome_R"), ("eye_gimbal", "eye_dome_L"),
    ("eye_gimbal", "eye_lid_R"), ("eye_gimbal", "eye_lid_L"),
    ("eye_gimbal", "eye_shaft"), ("eye_frame", "eye_shaft"),
    ("eye_gimbal", "eye_rod_tilt"),
    ("eye_dome_R", "eye_pan_bar"), ("eye_dome_L", "eye_pan_bar"),
    ("eye_pan_bar", "eye_rod_pan"),
    ("eye_lid_R", "eye_rod_lid_R"), ("eye_lid_L", "eye_rod_lid_L"),
    ("eye_frame", "eye_peg_R"), ("eye_frame", "eye_peg_L"),
    ("eye_lid_R", "eye_dome_R"), ("eye_lid_L", "eye_dome_L"),
    ("eye_dome_R", "eye_stem_R"), ("eye_dome_L", "eye_stem_L"),
    ("eye_dome_R", "eye_axle_R"), ("eye_dome_L", "eye_axle_L"),
    ("eye_gimbal", "eye_axle_R"), ("eye_gimbal", "eye_axle_L"),
    ("eye_stem_R", "eye_pan_bar"), ("eye_stem_L", "eye_pan_bar"),
}


def _inside_test(name):
    """Point-in-solid by ray-crossing parity. Skew directions and a majority
    vote, because this geometry is all axis-aligned planes and cylinders and
    an axis-aligned ray lands on tangent surfaces and miscounts."""
    ob = bpy.data.objects.get(name)
    if ob is None:
        return None
    inv = ob.matrix_world.inverted()

    def inside(pw):
        p = inv @ pw
        votes = 0
        for d in _DIRS:
            n, org = 0, p.copy()
            for _ in range(96):
                hit, loc, nrm, _i = ob.ray_cast(org, d, distance=1e6)
                if not hit:
                    break
                n += 1
                org = loc + d * 1e-4
            votes += n % 2
        return votes >= 2
    return inside


def _tree(o):
    from mathutils.bvhtree import BVHTree
    b = bmesh.new()
    b.from_mesh(o.data)
    bmesh.ops.transform(b, verts=b.verts[:], matrix=o.matrix_world)
    t = BVHTree.FromBMesh(b)
    b.free()
    return t


SKIP = ("_", "PR_", "PRBED", "PRTITLE", "PRLABEL", "CUT_", "REF",
        "PROXY_", "CHECK_", "SnapEye", "EyeMech", "Assembly", "Base",
        "Component", "ServoSizing")
# ...except these. A proxy for something that lives INSIDE a printed part
# still has to fit inside it, and blanket-skipping PROXY_ meant the 5050
# pixels sat in the middle of the rib for as long as both existed.
SKIP_EXCEPT = ("PROXY_eye_led_",)
SKIP_EXACT = {"HEAD_SKIN", "HEAD_SOLID", "MOUNT_ZONE", "HEAD_CYBORG",
              "HEAD_CRANIUM_scriptbuild", "HEAD_REF",
              "forehead_casing_asprinted_13aug"}


def poses(coarse=False):
    """The corners of the envelope, plus the middle of each face."""
    t = P["tilt_max"]
    p = P["pan_max"]
    k = LID["park"]
    if coarse:
        return [(0, 0, k, k), (t, 0, k, k), (-t, 0, k, k),
                (0, p, k, k), (0, -p, k, k), (0, 0, 0, 0)]
    out = []
    for ti in (-t, 0, t):
        for pa in (-p, 0, p):
            for li in (0, k / 2.0, k):
                out.append((ti, pa, li, li))
    out.append((t, p, 0, k))       # one wink, at a corner
    out.append((-t, -p, k, 0))
    return out


def check(sweep=True, verbose=False):
    """Prove it: watertight, one solid each, inside the head, nothing fouling
    - and not only in the pose it happens to be sitting in.

    The sweep is the whole point. Every earlier version of this checker
    tested the mechanism standing still, and two of the three faults that
    have mattered were invisible that way: the yoke arm that swings into the
    forehead casing at -20 of tilt, and the eyelid that reaches through the
    outboard bearing. Containment, collision-with-the-head,
    collision-with-each-other and collision-THROUGH-THE-RANGE are four
    questions, and it used to answer two.
    """
    hm = _hm()
    coll = bpy.data.collections.get(COLL)
    if coll is None:
        print("no %s collection - run build() first" % COLL)
        return False
    # HEAD_SOLID, not MOUNT_ZONE. The zone has every shell opening
    # subtracted out of it, the eye sockets included - and the eyeball is
    # SUPPOSED to sit in that opening, so checking a dome against the zone
    # reports the whole visible front of the eye as a fault.
    in_solid = _inside_test("HEAD_SOLID")
    ok = True
    parts = [o for o in sorted(coll.objects, key=lambda o: o.name)
             if o.type == 'MESH' and not o.name.startswith("PROXY_")
             and not o.name.startswith("eye_rod_")]

    print("part health:")
    for ob in parts:
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        openE = sum(1 for e in bm.edges if len(e.link_faces) == 1)
        nonm = sum(1 for e in bm.edges if len(e.link_faces) > 2)
        seen, shells = set(), 0
        for v in bm.verts:
            if v in seen:
                continue
            shells += 1
            st = [v]
            while st:
                x = st.pop()
                if x in seen:
                    continue
                seen.add(x)
                for e in x.link_edges:
                    o = e.other_vert(x)
                    if o not in seen:
                        st.append(o)
        n0 = len(bm.verts)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
        debt = n0 - len(bm.verts)
        bm.free()
        bad = []
        if openE or nonm:
            bad.append("open %d, non-manifold %d" % (openE, nonm))
        if shells != 1:
            bad.append("%d shells" % shells)
        if debt:
            bad.append("weld debt %d" % debt)
        print("  %-14s %5d v, %d shell, open %d, non-manifold %d, weld debt %d  %s"
              % (ob.name, n0, shells, openE, nonm, debt,
                 "OK" if not bad else "FAIL: " + "; ".join(bad)))
        ok = ok and not bad

    # ---- can each servo actually drive what it is bolted to? --------------
    print("")
    if "horn0" not in SERVOS["pan"]:
        phase_horns()
    _ROD_L.clear()
    reach()

    # ---- inside the head, through the range ------------------------------
    #
    # Two different questions wear the same test here, and conflating them
    # would have condemned a perfectly good eyelid.
    #
    # For anything that lives INSIDE the head, a vertex outside HEAD_SOLID
    # is a part through the skull, and it is a fault.
    #
    # The domes and the lids are SEEN, through a O41 hole. Standing proud of
    # the notional skin surface there is not a breach of anything - the hole
    # is open air - it is a cosmetic fact about how far the eye sticks out
    # of the face. So it is measured and printed as a number, and what
    # decides pass or fail for those two is the collision test below,
    # against the shell that is actually printed.
    VISIBLE = ("eye_dome_R", "eye_dome_L", "eye_lid_R", "eye_lid_L")
    print("")
    print("inside the head (every vertex against HEAD_SOLID, worst pose):")
    solid = bpy.data.objects["HEAD_SOLID"]
    si = solid.matrix_world.inverted()
    for ob in parts:
        worst, wp, nout = 0.0, None, 0
        for pz in (poses(coarse=True) if sweep else [(0, 0, LID["park"], LID["park"])]):
            pose(*pz, rods=False)
            out = [ob.matrix_world @ v.co for v in ob.data.vertices
                   if not in_solid(ob.matrix_world @ v.co)]
            if not out:
                continue
            w = 0.0
            for p in out:
                hit, loc, nrm, _i = solid.closest_point_on_mesh(si @ p)
                if hit:
                    w = max(w, ((si @ p) - loc).length)
            if w > worst:
                worst, wp, nout = w, pz, len(out)
        if worst == 0.0:
            print("  %-14s inside at every pose  OK" % ob.name)
        elif ob.name in VISIBLE:
            print("  %-14s stands %.2f mm proud of the face at %s "
                  "(%d of %d vertices) - through the socket, not the shell"
                  % (ob.name, worst, wp, nout, len(ob.data.vertices)))
        else:
            print("  %-14s %d of %d vertices outside, worst %.2f mm at %s  %s"
                  % (ob.name, nout, len(ob.data.vertices), worst, wp,
                     "OK, sub-nozzle" if worst < 0.4 else "FAIL"))
            ok = ok and worst < 0.4
    pose()

    # ---- against the rest of the head, and against each other ------------
    #
    # Everything here is looked up BY NAME inside the loop. The pushrods are
    # deleted and redrawn on every pose, so a list of object references
    # taken before the loop goes stale the first time the mechanism moves -
    # "StructRNA of type Object has been removed" - and a list taken after
    # would quietly count each redrawn rod as a part of the head.
    mine = set(o.name for o in coll.objects if o.type == 'MESH')
    others = [o.name for o in bpy.data.objects
              if o.type == 'MESH' and o.name not in mine
              and o.name not in SKIP_EXACT
              and (o.name.startswith(SKIP_EXCEPT)
                   or not o.name.startswith(SKIP))]
    # Most of the head stands still, so its collision trees are built once.
    # The 5050 pixels do not - they are glued inside the eyeballs and go
    # where the eyeballs go - so theirs are rebuilt every pose. Left in the
    # static set they reported 36 faces of collision at 16 degrees of tilt
    # that were not there: a moving dome tested against a tree of where the
    # pixel used to be.
    moving_others = [n for n in others if n.startswith(SKIP_EXCEPT)]
    otrees = {n: _tree(bpy.data.objects[n]) for n in others
              if n not in moving_others}
    real = sorted(n for n in mine if not n.startswith("PROXY_"))
    plist = poses() if sweep else [(0.0, 0.0, LID["park"], LID["park"])]

    print("")
    print("collisions, swept through the range (%d head parts, %d poses):"
          % (len(others), len(plist)))
    clashes = {}
    for pi, pz in enumerate(plist):
        pose(*pz)
        here = [n for n in real if bpy.data.objects.get(n) is not None]
        mt = {n: _tree(bpy.data.objects[n]) for n in here}
        ot = dict(otrees)
        ot.update({n: _tree(bpy.data.objects[n]) for n in moving_others
                   if bpy.data.objects.get(n) is not None})
        for e in here:
            for o in others:
                if o not in ot:
                    continue
                pairs = mt[e].overlap(ot[o])
                if pairs:
                    k = (e, o)
                    if k not in clashes or len(pairs) > clashes[k][0]:
                        clashes[k] = (len(pairs), pz)
        for i in range(len(here)):
            for j in range(i + 1, len(here)):
                a, b = here[i], here[j]
                if (a, b) in ALLOWED or (b, a) in ALLOWED:
                    continue
                if pi and a not in MOVING and b not in MOVING:
                    continue
                pairs = mt[a].overlap(mt[b])
                if pairs:
                    k = (a, b)
                    if k not in clashes or len(pairs) > clashes[k][0]:
                        clashes[k] = (len(pairs), pz)
    pose()
    if not clashes:
        print("  none, at any pose (bearings and pinned joints excepted)")
    for (a, b), (n, pz) in sorted(clashes.items(), key=lambda kv: -kv[1][0]):
        pose(*pz)
        oa, ob2 = bpy.data.objects.get(a), bpy.data.objects.get(b)
        where = ""
        if oa and ob2:
            pairs = _tree(oa).overlap(_tree(ob2))
            if pairs:
                bm = bmesh.new()
                bm.from_mesh(oa.data)
                bmesh.ops.transform(bm, verts=bm.verts[:],
                                    matrix=oa.matrix_world)
                bm.faces.ensure_lookup_table()
                cs = [bm.faces[i].calc_center_median() for i, _j in pairs]
                where = ("  at x %6.1f..%6.1f y %6.1f..%6.1f z %6.1f..%6.1f"
                         % (min(c.x for c in cs), max(c.x for c in cs),
                            min(c.y for c in cs), max(c.y for c in cs),
                            min(c.z for c in cs), max(c.z for c in cs)))
                bm.free()
        print("  %-14s INTO %-22s %4d faces, tilt %+.0f pan %+.0f lid %.0f/%.0f%s"
              % (a, b, n, pz[0], pz[1], pz[2], pz[3], where))
    pose()
    ok = ok and not clashes
    print("")
    print("check(): %s" % ("PASS" if ok else "FAIL"))
    return ok


# ---------------------------------------------------------------------------
ROD_D = 2.0         # the wire, not the hole


def skew(verbose=True):
    """Does each pushrod actually lie in the plane its two hinges turn in?

    Pat spotted this one on screen before any test did. Every joint in this
    linkage is a hinge, not a ball: the eyelid turns about the tilt axis, the
    servo horn turns about its own shaft, and both of those axes run along X.
    A straight rigid rod can only join two such hinges if it lies in a plane
    perpendicular to X. Offset them along their shared axis and the rod
    arrives at the pin boss on the skew - it looks like it is stabbing
    through the crank, and it would bind.

    The pan rod is the exception and is meant to be: its two hinges are
    VERTICAL - the eye levers hang their pins downward and the pan servo's
    shaft is vertical - so its plane is horizontal and its own out-of-plane
    axis is z, not x.
    """
    if "horn0" not in SERVOS["pan"]:
        phase_horns()
    if not _ROD_L:
        _rods()
    out = {}
    for name in ("pan", "tilt", "lid_R", "lid_L"):
        axis = 2 if SERVOS[name]["axis"] is None else 0    # z for pan, else x
        worst, still = 0.0, 0.0
        for pz in poses():
            far = _drive_points(*pz)[name]
            ang, _e = solve_horn(name, far, _ROD_L[name])
            near = horn_pin(name, ang)
            d = abs((far - near)[axis])
            worst = max(worst, d)
            if pz[0] == 0.0 and pz[1] == 0.0:
                still = max(still, d)
        out[name] = (worst, still, "z" if axis == 2 else "x")
    if verbose:
        print("pushrod skew - how far each rod leaves its hinges' plane:")
        for name, (d, still, ax) in out.items():
            if still > 0.4:
                verdict = ("BUILT WRONG - the two hinges are offset along "
                           "their own axis, move one to match the other")
            elif d > 0.4:
                verdict = ("inherent: %.2f at rest, %.2f at full tilt - needs "
                           "a wire link with a Z-bend, not a rigid rod"
                           % (still, d))
            else:
                verdict = "OK, planar at every pose"
            print("  %-6s %5.2f mm out of plane (along %s)  %s"
                  % (name, d, ax, verdict))
    return out


def clearances(step=4.0, verbose=True):
    """How close does each pushrod get to everything, through the range?

    Overlap and clearance are different questions, and this file only had the
    first. A rod that misses the eyeball by 0.1 mm reports exactly the same as
    one that misses it by four, and only one of them can be built - the rods
    are wire, they are bent by hand, and the eyeball is a printed sphere with
    a printed sphere's tolerances.

    It samples along each rod's axis rather than testing meshes against each
    other, because a rod IS its axis plus a radius, and `closest_point_on_mesh`
    is exact and cheap.
    """
    coll = bpy.data.collections.get(COLL)
    if coll is None:
        print("no %s collection" % COLL)
        return {}
    if "horn0" not in SERVOS["pan"]:
        phase_horns()
    if not _ROD_L:
        _rods()
    against = [o for o in bpy.data.objects
               if o.type == 'MESH'
               and (o.name.startswith("eye_") or o.name in
                    ("HEAD_FACE", "HEAD_CRANIUM", "FIT_forehead_casing"))
               and not o.name.startswith("eye_rod_")]
    out = {}
    t, p, k = P["tilt_max"], P["pan_max"], LID["park"]
    poses_ = []
    ti = -t
    while ti <= t + 0.01:
        pa = -p
        while pa <= p + 0.01:
            li = 0.0
            while li <= k + 0.01:
                poses_.append((ti, pa, li, li))
                li += k / 4.0
            pa += p
        ti += t
    for pz in poses_:
        pose(*pz)
        pts = _drive_points(*pz)
        for name in ("pan", "tilt", "lid_R", "lid_L"):
            far = pts[name]
            ang, _e = solve_horn(name, far, _ROD_L[name])
            near = horn_pin(name, ang)
            n = max(6, int((far - near).length / step))
            # The last 4 mm at each end is inside a pin boss on purpose, so
            # it is not clearance, it is the joint.
            for i in range(n + 1):
                f = i / float(n)
                q = near.lerp(far, f)
                if (q - far).length < 4.5 or (q - near).length < 4.5:
                    continue
                for o in against:
                    inv = o.matrix_world.inverted()
                    hit, loc, nrm, _i = o.closest_point_on_mesh(inv @ q)
                    if not hit:
                        continue
                    d = ((o.matrix_world @ loc) - q).length - ROD_D / 2.0
                    key = (name, o.name)
                    if key not in out or d < out[key][0]:
                        out[key] = (d, pz, q.copy())
    pose()
    if verbose:
        print("pushrod clearance, worst over %d poses "
              "(joint ends excluded):" % len(poses_))
        rows = sorted(out.items(), key=lambda kv: kv[1][0])
        for (rod, obj), (d, pz, q) in rows[:14]:
            flag = "TOUCHING" if d < 0.3 else ("tight" if d < 1.0 else "")
            print("  eye_rod_%-6s vs %-20s %6.2f mm  at tilt %+.0f pan %+.0f "
                  "lid %.0f  (%.1f %.1f %.1f) %s"
                  % (rod, obj, d, pz[0], pz[1], pz[2], q.x, q.y, q.z, flag))
    return out


def _volume(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    v = bm.calc_volume(signed=True)
    bm.free()
    return v


def _health(name, tag=""):
    """open / non-manifold / degenerate, in one line."""
    ob = bpy.data.objects.get(name)
    if ob is None:
        return "%s: missing" % name
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    openE = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    nonm = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    tiny = sum(1 for f in bm.faces if f.calc_area() < 1e-5)
    n = len(bm.verts)
    bm.free()
    return ("%s %s: %d v, open %d, non-manifold %d, near-zero-area faces %d"
            % (name, tag, n, openE, nonm, tiny))


def _eye_axis(sx):
    """The direction the socket on side sx faces.

    Same construction as `head_style.eye_axis`, and the two angles are
    `head_style.S["eye"]["rake_out"]` = 25 and `["rake_down"]` = 10. The
    socket's bore is centred on the eyeball, so this axis runs through the
    ball's centre and therefore through the tilt axis as well - which is why
    a rim coaxial with the bore clears an eyelid concentric with the ball by
    the same amount all the way round.
    """
    o, d = math.radians(25.0), math.radians(10.0)
    return Vector((sx * math.sin(o), math.cos(o) * math.cos(d),
                   -math.sin(d))).normalized()


SOCKET_BORE = 37.6      # the new opening
SOCKET_CUT  = 41.0      # what head_style.S["eye"]["dia"] cut it at
SOCKET_END  = 25.0      # the rim stops on a sphere this far from the eye
                        # centre, so it has no flat annular end face


def socket_aperture(bore_only=True):
    """Measure the eye openings: rays outward from the socket axis until they
    leave HEAD_FACE's material. Reports the radius of the hole, not a guess."""
    face = bpy.data.objects.get("HEAD_FACE")
    if face is None:
        return {}
    inv = face.matrix_world.inverted()
    out = {}
    for sx, side in ((1, "R"), (-1, "L")):
        c = Vector((sx * P["pitch"] / 2.0, P["y"], P["z"]))
        ax = _eye_axis(sx)
        u = ax.cross(Vector((0.0, 0.0, 1.0))).normalized()
        v = ax.cross(u).normalized()
        rs = []
        for k in range(24):
            a = 2.0 * math.pi * k / 24.0
            d = (u * math.cos(a) + v * math.sin(a)).normalized()
            # start on the axis, just inside the skin
            best = None
            for t in (19.0, 21.0, 23.0):
                org = c + ax * t
                hit, loc, nrm, _i = face.ray_cast(inv @ org,
                                                  (inv.to_3x3() @ d).normalized(),
                                                  distance=1e6)
                if hit:
                    r = ((face.matrix_world @ loc) - org).length
                    best = r if best is None else min(best, r)
            if best is not None:
                rs.append(best)
        if rs:
            out[side] = (min(rs), sum(rs) / len(rs), max(rs))
    return out


# A rim inside the eye openings was tried on 15 Aug and thrown away. The
# measurement that prompted it stands and is worth keeping: `socket_aperture()`
# reports the opening's radius as 20.48 at its tightest and 34.21 at its
# widest, against an eyeball of 16 - so the gap is not 4.5 mm all round, it is
# 4.5 at one edge and 18 at another, because the bore is raked 25 out and 10
# down while the ball is not. That is what you see through the face.
#
# The rim itself does not go back in without a different approach. Built as an
# annulus coaxial with the bore and trimmed against HEAD_SOLID, it came out as
# a tube standing proud of the cheek like a lens barrel - the trim did not
# take - and its flat annular end face unioned into HEAD_FACE as a single
# 145-sided n-gon, which every BVH and every slicer triangulates straight
# across the hole. Anyone picking this up again should note that the second
# fault is the more dangerous of the two: the model looked fine and the
# exported STL would have had a disc across the eye socket.
#
# Pat's call, 15 Aug: leave the openings alone.


def casing_relief(apply=False):
    """What the forehead casing has to give up so an upper eyelid can exist.

    NOT run by build(). `forehead_casing` is on plate 5 and waiting to
    print, and this changes it, so it is Pat's call and not the script's.

    The arithmetic is short and there is no way round it. The eyelid is a
    shell over the ball with 0.4 of running clearance and 1.4 of wall, so
    its outer surface is 17.8 from the eye centre against the ball's 16. The
    ball's top is z=225. The casing's underside is z=225, solid from x=-47
    to +47. Wherever the lid's band crosses the top of the eye it stands up
    to 1.69 mm proud of the ball, and that is where the casing is.

    Thinning the lid does not fix it - at 0.9 mm of wall and 0.25 of gap it
    is still 1.15 mm proud, and 0.9 mm is not a lid. Neither does a lower
    lid park position: the band has to pass over the top to get anywhere.

    So: a 2.2 mm scallop in the bottom edge of the casing, 16 mm wide, over
    each eye. It is the bottom rim of a panel that runs to z=283 and carries
    nothing there.
    """
    hm = _hm()
    ob = bpy.data.objects.get("forehead_casing")
    if ob is None:
        print("no forehead_casing in the file")
        return
    ro = P["ball"] / 2.0 + LID["gap"] + LID["shell"]
    print("eyelid outer radius %.1f, ball %.1f, so %.2f mm proud of the ball"
          % (ro, P["ball"] / 2.0, ro - P["ball"] / 2.0))
    print("casing underside z=%.1f, ball top z=%.1f"
          % (P["casing_z"], P["z"] + P["ball"] / 2.0))
    print("relief: z %.1f..%.1f, y %.1f..%.1f, x +-(%.1f..%.1f) each side"
          % (P["casing_z"] - 0.5, P["casing_z"] + 2.2, P["casing_y"] - 1.0,
             168.0, P["pitch"] / 2.0 - 8.0, P["pitch"] / 2.0 + 8.0))
    if not apply:
        print("dry run - call casing_relief(apply=True) to cut it, and then")
        print("re-export plate 5 before printing it")
        return
    # BOTH copies, and that is not belt and braces. `export_plate` reads the
    # source `forehead_casing`; the assembly - and therefore every collision
    # test in this file - sees `FIT_forehead_casing`. Cut one and the part
    # you print is right while the model still says it clashes; cut the
    # other and the model goes quiet while the printed part still fouls.
    # This project has already lost a hand edit to exactly that split.
    # FIT first, and that order is the whole trick. The cutter is built in
    # world coordinates; `FIT_forehead_casing` is in the head where the eyes
    # are, and `forehead_casing` is parked out on the print bed at x=520. A
    # box at x=+-31 misses the source completely - it "cut" it and changed
    # nothing, 1567 vertices in and 1567 out. So cut the copy that is in the
    # right place, then hand the source that mesh.
    done = 0
    for nm in ("FIT_forehead_casing",):
        o = bpy.data.objects.get(nm)
        if o is None:
            print("  %s: not in the file" % nm)
            continue
        n0 = len(o.data.vertices)
        cut = bmesh.new()
        for sx in (-1, 1):
            hm["_box"](cut, (18.0, 12.0, 3.0),
                       (sx * P["pitch"] / 2.0, 164.5, P["casing_z"] + 1.0))
        hm["_apply"](o.users_collection[0], o, cut,
                     "_CUT_casing_relief_%s" % nm, 'DIFFERENCE')
        print("  %-22s %d -> %d vertices" % (nm, n0, len(o.data.vertices)))
        done += 1
    src = bpy.data.objects.get("forehead_casing")
    fit = bpy.data.objects.get("FIT_forehead_casing")
    if done and src is not None and fit is not None:
        old = src.data
        src.data = fit.data.copy()
        bpy.data.meshes.remove(old)
        print("  forehead_casing now carries the same mesh, %d vertices"
              % len(src.data.vertices))
    print("cut. re-export plate 5.")


def report():
    """A short prose summary of where the mechanism stands."""
    coll = bpy.data.collections.get(COLL)
    if coll is None:
        print("nothing built")
        return
    print("EYE_v2, %d objects" % len(coll.objects))
    for o in sorted(coll.objects, key=lambda o: o.name):
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        print("  %-20s %5d v  x %6.1f..%6.1f y %6.1f..%6.1f z %6.1f..%6.1f"
              % (o.name, len(o.data.vertices),
                 min(p.x for p in bb), max(p.x for p in bb),
                 min(p.y for p in bb), max(p.y for p in bb),
                 min(p.z for p in bb), max(p.z for p in bb)))
