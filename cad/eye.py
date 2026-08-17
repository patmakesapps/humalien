"""The v2 eye. Drawn from the ball outward, on an empty scene.

    exec(open(r"C:\\Humalien\\cad\\eye.py").read())
    build(); printcheck(); export_stls()

WHY THIS IS NOT eye_v2.py
-------------------------
`cad/eye_v2.py` is v1's second eye design and it is kept for its measurements,
not its shapes. It was printed, assembled, and it broke; what it taught is in
`cad/checks.py` and in the numbers restated below.

The thing it got wrong was not geometry. It was that FOUR SERVOS SAT ON THE
FIXED FRAME, 34 mm behind the tilt axis, because that was the only place the
skull left for them - so every axis was driven through a hand-bent wire
pushrod, and tilting the eyes moved the far end of all four.

Count what that cost in degrees, because it is the whole argument for this
rewrite. A 2.0 mm rod in a 2.30 mm hole, on an 11 mm lever, is 1.6 degrees of
lash per joint. Every pushrod has two. That is ~3.2 degrees per rod against a
tilt range of 32 degrees total - a tenth of the travel is backlash you cannot
command, before the 2 degrees of journal wobble the old file already called
"the loosest thing in the mechanism".

TWO DECISIONS MADE THIS SIMPLE, AND BOTH ARE PAT'S
--------------------------------------------------
1. **The eyes never move independently.** They always look the same direction.
   So the two lid servos collapse into one blink servo, and the eyes are
   mechanically ganged rather than separately driven.

2. **Chassis first, head second.** The mechanism is drawn to what it needs and
   the head is made to fit it - not the reverse. This is what lets the pan and
   blink servos ride ON the gimbal, which is what deletes the cross-coupling
   instead of mixing it out in software.

Target: tilt direct-drive with ZERO linkage, pan and blink with one short
link each. As built that is SIX pin joints against v1's twelve - four in
the pan train (horn, tab, two levers), two in the blink train - and every
one is an M2 screw in a printed bore, not a wire in a drilled hole.

THE BALL, AND WHY IT IS SHAPED LIKE THIS
----------------------------------------
v1 split the eyeball into dome + stem + axle because two of its features
pointed at right angles: a pan lever reaching 4 mm behind the back face and a
bearing boss hanging 16 mm below. No orientation printed both.

That boss hung BELOW because a yoke gripping both poles needs an arm above the
eye, and the forehead casing was solid from z=225 - which is exactly the top
of the ball. A head constraint, not a mechanism one. Off the head it is gone,
so this eye runs on a proper TWO-POINT pan bearing, top and bottom, instead of
one cantilevered journal underneath. That single change is what removes the
2 degrees of wobble.

So the ball is:

  - a O32 sphere, truncated to a flat back. The socket only ever shows the
    front, and the flat is what it prints on: 670 mm2 of bed against an
    804 mm2 shadow, 83%.
  - one vertical bore, teardropped, for a separate pin. The journals CANNOT be
    printed onto the ball - laid back-down they stick out sideways, which is a
    horizontal cantilever and is precisely how v1's parts broke.
  - the pan lever as a fin lying IN the back plane. Printed back-down that
    plane is the first layer, so the lever grows off the bed instead of
    hanging over it. It is also part of the ball, so it cannot be glued on out
    of phase the way v1's stem could.

The pin is one rod through both poles rather than two stubs, because it IS the
bearing axis and coaxiality matters more than print convenience. It prints
standing on end, which has no overhang at all.

NUMBERS CARRIED OVER, WITH THEIR PROVENANCE
-------------------------------------------
  pitch 62.0        eye centres at x = +-31. Set by the head's sockets and
                    confirmed against the geometry, not the constant.
  fit 0.40          diametral. PROVEN on this printer - v1's joints at
                    0.30..0.60 all went together by hand and the single one
                    at 0.20 had to be driven in with a hammer.
  link_d 2.30       2 mm steel rod plus 0.3. The rod is a bicycle spoke;
                    filament buckles at 6.5 N against 13 N of servo stall.
  ball_d 32.0       unchanged. Deliberately NOT grown to swallow a NeoPixel
                    ring - light is deferred, and the plan of record is to
                    fix the ring at the socket so nothing electrical ever
                    crosses the gimbal. See docs/v2-brief.md.
"""

import bpy
import bmesh
import math
import os
from mathutils import Matrix, Vector

HEAD_MOUNTS = r"C:\Humalien\cad\head_mounts.py"
CHECKS = r"C:\Humalien\cad\checks.py"
COLL = "EYE"

E = dict(
    pitch     = 62.0,       # eye centres at x = +-31
    ball_d    = 32.0,
    # The flat back. 6.6 leaves a O29.1 face - 83% of the ball's own shadow -
    # and keeps the ball 22.6 deep, which is what v1's dome measured and
    # printed cleanly.
    back_cut  = 6.6,

    # --- the pan axis -----------------------------------------------------
    pin_d     = 6.0,        # O6 not O5: the journal is the bearing now, and
                            # a 44 mm rod at O5 is an 8.8:1 column to print
    fit       = 0.40,       # diametral, everywhere. See the docstring.
    # --- how far the pin actually goes -----------------------------------
    # It does NOT come out of the top of the ball, and there are two reasons.
    #
    # Cosmetic first: a hole at the top pole is visible the moment the lid
    # opens, and the top pole is the one part of the sphere the lid cannot
    # hide. The bore is blind, so the ball reads as a ball.
    #
    # Mechanical second: there is no upper bearing to reach. A journal at the
    # top pole and an upper eyelid want the same space - the lid hinges on
    # the tilt axis and parks over the top of the ball, exactly where that
    # journal would be. That is why v1 hung each eye on one journal
    # underneath, and it was right for that reason if not for its length.
    #
    # So: one LOWER journal, and long. v1's 2 degrees of wobble came from
    # 0.3 mm of clearance over 9 mm; off the head there is room below the eye
    # that never existed inside it.
    #
    #    9 mm (v1)   ~2.5 deg        25 mm   ~0.9 deg
    #
    pin_top   = 12.0,       # how far above the ball centre the bore reaches;
                            # 4 mm of solid sphere left above it
    journal   = 25.0,       # below the ball, and this is the bearing
    key_flat  = 1.0,        # a flat down the pin, and the same in the bore

    # --- the pan lever, which lives on the PIN and not on the ball --------
    # It has to reach BACKWARD from the pan axis, and its link pin has to
    # stand VERTICAL - parallel to the axis the eye turns about - or the
    # four-bar is not planar and the joint binds instead of pivoting.
    #
    # That is why it cannot be part of the ball. The ball prints on its flat
    # back, so the back plane is the first layer; a lever lying IN that plane
    # can only reach sideways or down, never backward. Hung straight down it
    # had a 6.6 mm moment arm - the offset to the back plane - where it wants
    # 11, and its pin came out horizontal.
    #
    # On the bottom of the pin it is an L: rod standing on end, arm flat on
    # the bed as the first four layers, and the link hole runs straight up
    # the print axis. Nothing overhangs and the pin hole is vertical because
    # the print made it so.
    lever_r   = 11.0,       # how far back the link pin sits from the pan axis
    lever_t   = 4.0,        # arm thickness, and its first-layer height
    lever_w   = 8.0,
    # No wire anywhere in this mechanism. A printed link 8 x 4 buckles at
    # about 590 N against 13 N of servo stall; a 1.75 mm filament rod buckles
    # at 6.5 and a hand-bent steel one needs a craft shop. Wide beats round,
    # and an M2 screw through a printed boss is a better pivot than a Z-bend.
    bar_w     = 8.0,        # the pan bar, across the eyes
    bar_t     = 4.0,
    # BELOW the levers, not level with them. At -43 the bar occupied
    # z -45..-41 and so did the lever it pins to - the same 4 mm slab, two
    # parts in it, which renders as z-fighting and assembles as neither.
    # The lever runs -45..-41, so the bar sits -49.5..-45.5 with 0.5 clear
    # and one M2 passes down through both.
    bar_z     = -47.5,
    bar_y     = -11.0,      # = lever_r, so the bar sits on the pin centres
    drive_y   = -22.0,      # the servo link's pin, back from the bar

    # --- the base: what the gimbal swings in, and what stands on a bench ---
    base_x    = 72.0,       # uprights, outboard of the gimbal's 68
    base_t    = 6.0,
    # The floor was at -84 because the pan servo hung shaft-up to z=-77 - and
    # then swung with the gimbal, which took its corner to -85 at 16 degrees
    # of tilt and straight through the floor the -77 figure had been read at.
    # A hanging servo's depth has to be measured SWUNG, not parked.
    # The servo is now INVERTED (body up, horn down - see SERVOS), so the
    # deepest swung point of the whole gimbal assembly is the pan bar's own
    # corner at about -52. The floor clears that by 6 and the uprights got
    # 20 mm shorter, which they spend on stiffness.
    base_z0   = -64.0,      # floor underside
    base_z1   = -58.0,      # floor top
    base_top  = 14.0,       # 10 cleared the boss; 14 clears the tilt servo's
                            # upper tab pilot at z=+8 with meat above it
    base_y0   = -34.0,
    base_y1   = 26.0,
    # The tilt servo lives IN the right upright: a rectangular pocket the
    # body drops through from outboard, tabs screwed to the outer face, so
    # the output shaft is COAXIAL with the tilt axis. That is what
    # "direct-drive with zero linkage" means mechanically; anywhere else the
    # servo needs a linkage between two non-parallel axes, which binds.
    srv_cut_w = 12.4,       # body pocket, srv_w + 0.4
    srv_cut_z0 = -17.5,     # body pocket: srv_h below the shaft axis, plus
    srv_cut_z1 = 6.3,       # the O12.1 collar round the shaft above it
    # The horn pocket in the gimbal's RIGHT tilt boss. The servo horn drops
    # into an arm-shaped slot and torque goes through the slot walls, not
    # through screws. v2.1 (2026-08-17, at the bench): v2 cut this pocket
    # at x 61.4..63.5, but the horn, pressed fully home on the mounted
    # servo, has its plate out at ~65 - the spline bottoms in the hub long
    # before the arm can reach. Pat tried the print; it simply does not
    # go. The boss now reaches x=67.0 and the slot is deep enough that any
    # plate plane from 63.4 to ~66.2 engages at least a millimetre of
    # wall: the horn self-locates on the spline and the pocket meets it
    # where it is. No centre screw either - the old access bore dead-ended
    # inside the lid hinge stub and could never pass one; captivity does
    # the job (1.0 mm axial float between the uprights vs the engagement).
    horn_slot_w = 6.2,      # MG90S single-arm horn is 5.3-6.0 at the root
    horn_slot_deep = 3.6,   # deep on purpose - swallows the 1.7 plate
                            # wherever the real spline stack lands it
    horn_hub_d  = 7.6,      # clearance over the O7 hub and the spline

    # --- the lid spine and its joint to the lids --------------------------
    # The spine bolts to the END FACES of the lids' inboard bosses - two M2
    # self-tappers each side into a face that is now SOLID (the inboard bore
    # is gone; only the outboard bore survives, because only the outboard
    # end has a bearing to ride). Two screws off-axis = the phase is set by
    # the geometry, which is the same argument as the pan pin's key flat.
    pad_t     = 3.0,        # spine end pad; thread engagement is in the LID
    pad_gap   = 0.1,        # pad face short of the boss face; screws close it
    head_d    = 4.6,        # M2 pan head countersunk into the pad face
    head_t    = 1.6,

    # --- horn radii, which ARE the drive ratios ---------------------------
    # Pan: the servo shaft sits `lever_r` BEHIND the pin it drives, so the
    # small-angle gain is exactly that offset - 11 mm of offset against
    # 11 mm of eye lever is 1:1. (The shaft was previously drawn COAXIAL
    # with the pin, which is a singular linkage: at centre, rotating the
    # horn transmits nothing at all.)
    pan_horn_r = 11.0,
    # Blink: the crank sweeps ~55 deg on r14, so a 14 mm horn is ~1:1.
    blink_horn_r = 14.0,

    # MG90S, from the datasheet, and the tab pitch is the one number here
    # that is PROVEN - coupon_mg90s was printed and real servos fitted it.
    srv_l     = 22.5,
    srv_w     = 12.0,
    srv_h     = 22.7,
    srv_tab_pitch = 28.0,
    srv_tab_l = 32.2,
    srv_tab_t = 2.5,
    srv_tab_up = 16.0,
    srv_shaft_d = 5.5,
    srv_shaft_up = 4.5,
    srv_shaft_off = 6.0,

    # --- the iris, so there is something to look at ----------------------
    # Both are a sphere clipped by a cylinder, and that is not a stylistic
    # choice. A FLAT-ended cylinder cannot put a controlled step into a ball:
    # sunk deep enough to leave a 0.5 mm step it only reaches r=3.97, so a
    # "O15 iris" comes out O7.9 and the depth runs away at the centre.
    # Against a sphere the depth is the same everywhere and the cylinder only
    # decides how wide.
    iris_d    = 15.0,
    iris_deep = 0.4,
    pupil_d   = 6.5,
    pupil_deep = 1.0,       # total from the ball's surface

    # --- the lids, which are ONE part for both eyes -----------------------
    # They hinge on the tilt axis, and the tilt axis runs through BOTH eye
    # centres - so a single piece spanning the pair has one hinge, one link,
    # and no way for the two lids to fall out of sync, because they are the
    # same object. They stay concentric with the balls for free.
    lid_clr   = 0.35,       # running clearance over the ball
    # 2.0, not 1.2. The wall thickness IS the hinge: where the shell crosses
    # the tilt axis at the poles it is solid, and that solid cap is the only
    # material the pivot boss has to weld to. A 1.2 wall gives 1.2 mm of it.
    lid_wall  = 2.0,
    # The band, in degrees about the tilt axis, measured from straight ahead
    # (+Y) turning up toward +Z. Parked open it sits up and forward; blinking
    # rotates it down over the front.
    # An eyelid open covers the top of the ball and wraps over the back; it
    # does not perch above it. 55 is where the front edge sits when open,
    # 185 takes it over the top and just past the back pole. Closing rotates
    # the whole shell forward about the tilt axis until that front edge
    # reaches the bottom of the eye.
    #
    # v1 of this file used 40..105 - a 65-degree band floating above the ball
    # on radial spokes. Rendered, it read as a cap with fins, which is what
    # Pat called a disaster and he was right.
    lid_lo    = 55.0,
    lid_hi    = 185.0,
    # 12, not 8. The boss's outer end face is the ONLY flat face this part
    # has - everything else is sphere - so it is what the lid prints on. At
    # O8 with a O5.4 bore through it that face is a 27 mm2 annulus holding up
    # a 702 mm2 shadow, which is 4% and tips over. At O12 it is 90 mm2.
    hinge_boss_d = 12.0,
    hinge_x0  = 16.3,       # where it may start: the ball itself ends at
                            # x offset 16.0, plus running clearance. It was
                            # 15.9 when the inboard boss had a bore for the
                            # ball's pole tip to sit inside; the boss is
                            # solid now, so the whole of it stands clear.
    lid_gap   = 0.8,        # plates start this far outboard of the inner
                            # sphere, so no boolean lands tangent to it
    hinge_d   = 5.0,        # stub pins from the gimbal; bore is +fit
    bar_d     = 9.0,        # the spine joining the two lids, on the axis
    crank_r   = 14.0,       # blink link pin, back from the hinge axis
    crank_t   = 4.0,
    crank_w   = 8.0,
    boss_d    = 13.0,       # inboard boss the spine bolts to
    boss_t    = 6.0,        # 6 mm of thread engagement, not 3 mm of plate
    boss_pitch = 7.0,       # the two screws, either side of the axis
    pilot_d   = 1.7,        # M2 self-tapper pilot in PLA
    # --- the gimbal, i.e. the tilt frame ---------------------------------
    house_d   = 12.0,       # journal housing OD around a O6.4 bore
    gim_t     = 6.0,        # frame section
    gim_h     = 14.0,       # cross member depth - see cross_z
    # The cross member's bottom face is EXTRUDED DOWN to meet the journal
    # housings at z = -40.5 rather than the whole bar being lowered - the top
    # stays at -26.5 and the member gets deeper, which also makes it stiffer
    # in the direction it carries the eyes.
    #
    # The point is the first layer: the housings, the cross member, both arms
    # and both posts now bottom out on ONE plane, so the frame prints on a
    # flat face instead of balancing on two circles.
    #
    #     -33.5 +- 7.0  ->  z -40.5 .. -26.5
    cross_z   = -33.5,
    # The lid grew when it was rebuilt - its hinge boss now reaches x=55 -
    # so the posts moved out with it. Set from the part, not chosen.
    arm_x     = 62.0,       # post 59..65, tilt boss 56..68
    lid_pin_d = 5.0,        # stub from the post inboard into the lid's bore
    lid_pin_x0 = 48.0,      # outboard of the ball, which ends at x=47
    tilt_boss_d = 14.0,
    tilt_pin_d  = 5.0,

    screw_d   = 2.2,        # M2 clearance - the joints are screws now, not
                            # 2 mm wire. A printed link 8 x 3 buckles at
                            # 248 N against 13 N of servo stall; a 1.75 mm
                            # rod buckles at 6.5. Wide beats round.
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


def _teardrop(bm, d, length, loc, axis='Z', up=(0.0, 1.0, 0.0), apex=1.35):
    """A roof over a bore so its ceiling does not droop when printed lying
    down. Added ABOVE the bore; the bore itself is untouched.

    `up` is the direction the PRINT goes up, expressed in part coordinates.
    Getting that wrong is not cosmetic - v1 carried a teardrop pointing +y on
    a part whose print-up was -z, which left the bore with a drooping ceiling
    AND a pointless lobe out of its side.
    """
    u = Vector(up).normalized()
    ax = {'X': Vector((1.0, 0.0, 0.0)), 'Y': Vector((0.0, 1.0, 0.0)),
          'Z': Vector((0.0, 0.0, 1.0))}[axis]
    u = (u - ax * u.dot(ax)).normalized()
    r = d / 2.0
    tmp = bmesh.new()
    bmesh.ops.create_cone(tmp, cap_ends=True, cap_tris=False, segments=3,
                          radius1=r * apex, radius2=r * apex, depth=length)
    ang = math.atan2(u.y, u.x) if axis == 'Z' else 0.0
    bmesh.ops.rotate(tmp, verts=tmp.verts[:], cent=(0, 0, 0),
                     matrix=Matrix.Rotation(ang - math.pi / 2.0, 3, ax))
    if axis == 'X':
        bmesh.ops.rotate(tmp, verts=tmp.verts[:], cent=(0, 0, 0),
                         matrix=Matrix.Rotation(math.radians(90), 3, 'Y'))
    elif axis == 'Y':
        bmesh.ops.rotate(tmp, verts=tmp.verts[:], cent=(0, 0, 0),
                         matrix=Matrix.Rotation(math.radians(-90), 3, 'X'))
    bmesh.ops.transform(tmp, verts=tmp.verts[:],
                        matrix=Matrix.Translation(loc))
    me = bpy.data.meshes.new("_t")
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    return bm


def _union(hm, coll, name, prims):
    """One boolean per primitive. Merging primitives into a single cutter
    bmesh is the nested-cutter trap and v1 hit it four separate times."""
    base = hm["_link"](coll, name, hm["_mesh"](name, prims[0]))
    for i, bm in enumerate(prims[1:]):
        ob = hm["_link"](coll, "_U%d_%s" % (i, name), hm["_mesh"]("_U%d" % i, bm))
        hm["boolean"](base, ob, 'UNION')
        bpy.data.objects.remove(ob, do_unlink=True)
    return base


def _cut_each(hm, coll, ob, prims, name):
    for i, bm in enumerate(prims):
        hm["_apply"](coll, ob, bm, "%s_%d" % (name, i), 'DIFFERENCE')
    return ob


def ball(hm, coll, sx):
    """One eyeball: truncated sphere, pan bore, and the lever fin.

    Built at the eye's own centre so the part's origin IS the rotation centre
    - which is what every later check wants to pose about.
    """
    cx = sx * E["pitch"] / 2.0
    r = E["ball_d"] / 2.0
    prims, add = _prims()

    bm = add()
    _sphere(bm, E["ball_d"], (cx, 0.0, 0.0))
    ob = _union(hm, coll, "eye_ball_%s" % ("R" if sx > 0 else "L"), prims)

    cuts, cadd = _prims()
    # the flat back
    bm = cadd()
    hm["_box"](bm, (60.0, 40.0, 60.0), (cx, -E["back_cut"] - 20.0, 0.0))
    # The pan bore. BLIND at the top - it stops at pin_top and leaves solid
    # sphere above it - and open at the bottom where the pin goes in.
    # Printed back-down the print's up is the part's +Y, which is what `up`
    # says, and the bore runs horizontally in the print so it wants a roof.
    depth = E["pin_top"] + r + 4.0
    bm = cadd()
    hm["_cyl"](bm, E["pin_d"] + E["fit"], depth,
               (cx, 0.0, E["pin_top"] - depth / 2.0), 'Z', segs=32)
    bm = cadd()
    _teardrop(bm, E["pin_d"] + E["fit"], depth,
              (cx, 0.0, E["pin_top"] - depth / 2.0),
              'Z', up=(0.0, 1.0, 0.0), apex=1.35)
    # The key flat, on the BACK of the bore so it never meets the teardrop's
    # apex on the front. Without it the pin is round, the joint is glue
    # alone, and the lever's phase relative to the iris is set by hand -
    # which is the mistake v1's stem invited and got away with twice.
    bm = cadd()
    k = E["pin_d"] / 2.0 + E["fit"] / 2.0
    hm["_box"](bm, (E["pin_d"], E["key_flat"], E["ball_d"] + 8.0),
               (cx, -k + E["key_flat"] / 2.0, 0.0))
    _cut_each(hm, coll, ob, cuts, "_CUT_ball")

    # The iris and pupil, cut LAST and one at a time. Each cutter is a
    # cylinder minus a smaller sphere, so what comes away is a shell of even
    # thickness and the recess floor stays spherical.
    for dia, deep, tag in ((E["iris_d"], E["iris_deep"], "iris"),
                           (E["pupil_d"], E["pupil_deep"], "pupil")):
        cyl = bmesh.new()
        hm["_cyl"](cyl, dia, r * 2.0, (cx, r / 2.0, 0.0), 'Y', segs=48)
        inner = bmesh.new()
        _sphere(inner, E["ball_d"] - 2.0 * deep, (cx, 0.0, 0.0))
        cyl_ob = hm["_link"](coll, "_C_%s" % tag, hm["_mesh"]("_C_%s" % tag, cyl))
        in_ob = hm["_link"](coll, "_S_%s" % tag, hm["_mesh"]("_S_%s" % tag, inner))
        hm["boolean"](cyl_ob, in_ob, 'DIFFERENCE')
        bpy.data.objects.remove(in_ob, do_unlink=True)
        hm["boolean"](ob, cyl_ob, 'DIFFERENCE')
        bpy.data.objects.remove(cyl_ob, do_unlink=True)
    return ob


def pin(hm, coll, sx):
    """The pan axis AND the pan lever, as one L-shaped part.

    Printed standing on end: the rod has no overhang at any height, and the
    lever arm is the first four layers rather than something reaching out of
    mid-air. The link hole then runs straight up the print axis, which is
    both the direction the linkage needs it and the only direction a hole
    prints perfectly round.

    The flat down the rod keys it to the ball, so the lever's phase is set by
    the geometry instead of by how carefully it was glued.
    """
    cx = sx * E["pitch"] / 2.0
    z0 = -(E["ball_d"] / 2.0 + E["journal"] + E["lever_t"])   # bottom of all
    z1 = E["pin_top"] - 0.5     # 0.5 short of the blind bore's own floor, so
                                # the pin seats on the ball's bottom face and
                                # not on the end of a hole it cannot see
    prims, add = _prims()
    bm = add()
    hm["_cyl"](bm, E["pin_d"], z1 - z0, (cx, 0.0, (z0 + z1) / 2.0), 'Z',
               segs=32)
    # the arm, reaching back from the axis
    bm = add()
    hm["_box"](bm, (E["lever_w"], E["lever_r"] + E["lever_w"] / 2.0,
                    E["lever_t"]),
               (cx, -(E["lever_r"] + E["lever_w"] / 2.0) / 2.0,
                z0 + E["lever_t"] / 2.0))
    ob = _union(hm, coll, "eye_pin_%s" % ("R" if sx > 0 else "L"), prims)

    cuts, cadd = _prims()
    # The key flat runs ONLY over the length that is buried in the ball. Run
    # the length of the pin it would flatten one side of the journal, and the
    # journal is the bearing - a bearing with a flat on it is a bearing with
    # a gap in it.
    r = E["ball_d"] / 2.0
    bm = cadd()
    hm["_box"](bm, (E["pin_d"], E["key_flat"], E["pin_top"] + r),
               (cx, -E["pin_d"] / 2.0 + E["key_flat"] / 2.0,
                (E["pin_top"] - r) / 2.0))
    bm = cadd()     # the link hole, vertical, straight up the print axis
    hm["_cyl"](bm, E["screw_d"], E["lever_t"] * 4.0,
               (cx, -E["lever_r"], z0 + E["lever_t"] / 2.0), 'Z', segs=24)
    _cut_each(hm, coll, ob, cuts, "_CUT_pin")
    return ob


def weld_all(coll=None, tol=1e-4, verbose=False):
    """remove_doubles at 1e-4 on every part, with the volume checked either
    side and the weld rolled back if it moves.

    Booleans leave coincident vertices - a face landing exactly on another
    face's plane produces two verts at the same coordinate and a triangle
    with no area between them. Blender calls the mesh perfectly healthy: the
    shells are closed and every edge is used twice. What it does do is break
    shading, because a zero-area triangle has no meaningful normal, and that
    is the black wedge you see on a boss.

    v1 scored three candidate fixes on an exported STL and this one won
    outright - 0 degenerate triangles, every edge shared exactly twice, and
    the volume identical to four decimal places. Rebuilding the geometry with
    an overshoot and a flat trim was worse on both counts and moved the
    volume by 78.7 mm3.

    The rollback is not paranoia. A weld tolerance large enough to catch real
    coincidence is also large enough to eat a genuine 0.1 mm feature, so the
    volume is the guard.
    """
    def volume(ob):
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        v = bm.calc_volume(signed=True)
        bm.free()
        return abs(v)

    c = coll or bpy.data.collections.get(COLL)
    if c is None:
        return 0
    n = 0
    for o in list(c.objects):
        if o.type != 'MESH' or o.name.startswith("PROXY"):
            continue
        before = volume(o)
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=tol)
        me = o.data.copy()
        bm.to_mesh(me)
        bm.free()
        keep, o.data = o.data, me
        after = volume(o)
        if abs(after - before) > 1e-3:
            o.data = keep                       # rolled back
            if verbose:
                print("    %s: weld moved volume %.4f mm3 - rolled back"
                      % (o.name, after - before))
            continue
        bpy.data.meshes.remove(keep)
        n += 1
    if verbose:
        print("  welded %d parts, volume unchanged" % n)
    return n


SMOOTH_ANGLE = 35.0


def smooth_all(angle=None, coll=None, verbose=False):
    """Shade everything smooth, BY ANGLE. Runs at the end of every build().

    Not plain shade-smooth. Every face here is already flagged smooth and it
    still renders faceted, because from Blender 4.1 the flag on its own is
    not what does it - smoothing is a modifier now. And smoothing everything
    flat is the wrong answer anyway: it rounds the corners off the brackets
    as well as the balls, so a printed lever ends up looking like a bar of
    soap. By angle, the spheres and bores go smooth and every edge sharper
    than 35 degrees stays an edge.
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


def _rbox(bm, dims, loc, rot=None):
    """A box that can be rotated. `_box` is axis-aligned only, and v1's first
    eyelid crank was built with it - so the arm came out as a box lying along
    +y whatever angle it was asked for, and the pin was bored 5 mm outside
    it, in mid-air."""
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


def _wedge(bm, cx, deg, keep_above):
    """Half-space cutter bounded by a plane through the tilt axis at `deg`.

    Angles are measured about X from +Y (straight ahead) toward +Z (up), so
    the band is described the way you would describe an eyelid: 40 degrees is
    low on the front of the ball, 105 is just past the top.
    """
    R = Matrix.Rotation(math.radians(deg), 4, 'X')
    off = R @ Vector((0.0, 0.0, 100.0 if keep_above else -100.0))
    _rbox(bm, (400.0, 400.0, 200.0),
          (cx + off.x, off.y, off.z), R)
    return bm


def lid_shell(hm, coll, sx):
    """One upper eyelid: a spherical shell cut by two planes THROUGH the tilt
    axis, with a pivot boss where it crosses that axis at each pole.

    This is the shape every working animatronic lid has, and the reason is
    geometric rather than stylistic. Cut a concentric shell with planes that
    contain the hinge axis and its two side edges run down onto that axis by
    themselves - the convergence IS the hinge. There is nothing to bolt on.

    What was here before was a 65-degree band floating above the ball, carried
    to the hinge on radial spokes, because I built it from the middle outward
    instead of from the axis. Rendered, it read as a cap with fins.

    Angles are measured about X from straight ahead (+Y) turning up (+Z):

        55   the front edge when the lid is open
       185   over the top and just past the back pole

    Closing rotates the whole shell forward about the tilt axis until that
    front edge reaches the bottom of the eye - about 55 degrees of travel.
    """
    r_in = E["ball_d"] / 2.0 + E["lid_clr"]
    r_out = r_in + E["lid_wall"]
    cx = sx * E["pitch"] / 2.0
    tag = "R" if sx > 0 else "L"

    prims, add = _prims()
    bm = add()
    _sphere(bm, r_out * 2.0, (cx, 0.0, 0.0))
    ob = _union(hm, coll, "eye_lid_%s" % tag, prims)

    cuts, cadd = _prims()
    bm = cadd()
    _sphere(bm, r_in * 2.0, (cx, 0.0, 0.0))
    for deg, above in ((E["lid_lo"], False), (E["lid_hi"], True)):
        bm = cadd()
        _wedge(bm, cx, deg, above)
    _cut_each(hm, coll, ob, cuts, "_CUT_lid_%s" % tag)

    # The pivot bosses, added after the wedges so each is a full circle. They
    # start at hinge_x0 because inboard of that the ball is in the way: at a
    # radius of 4 the ball's surface is 15.5 from its centre.
    adds, aadd = _prims()
    for ox in (1, -1):
        bm = aadd()
        L = 24.0 - E["hinge_x0"]
        hm["_cyl"](bm, E["hinge_boss_d"], L,
                   (cx + ox * (E["hinge_x0"] + L / 2.0), 0.0, 0.0), 'X',
                   segs=32)
    for i, bm in enumerate(adds):
        o2 = hm["_link"](coll, "_A%d_%s" % (i, tag), hm["_mesh"]("_A%d" % i, bm))
        hm["boolean"](ob, o2, 'UNION')
        bpy.data.objects.remove(o2, do_unlink=True)

    # ONE bore, outboard, where the gimbal's stub pin is. The inboard boss
    # used to be bored too, for a spine pin that no longer exists - the spine
    # now bolts to this boss's END FACE, so the face stays solid and the two
    # M2 pilots go into solid material instead of into a O5.4-cored annulus
    # a pilot hole would have broken through.
    bores, badd = _prims()
    bm = badd()
    hm["_cyl"](bm, E["hinge_d"] + E["fit"], 40.0,
               (cx + sx * 18.0, 0.0, 0.0), 'X', segs=32)
    # Spine screw pilots, in the inboard end face. NOT at (0, +-3.5): the
    # spine's own bar sits on the axis, so screws there could never be
    # driven. The pair sits ABOVE the bar at (y +-2.8, z +3.2) - 4.6 mm from
    # the axis, which leaves 0.9 mm of boss wall outside a O1.7 pilot, and
    # 5.6 mm apart, which is what locks the lid's phase to the spine's.
    for dy in (1, -1):
        bm = badd()
        hm["_cyl"](bm, E["pilot_d"], 6.6,
                   (cx - sx * 20.9, dy * 2.8, 3.2), 'X', segs=20)
    _cut_each(hm, coll, ob, bores, "_BORE_lid_%s" % tag)
    return ob


def lid_spine(hm, coll):
    """The bar that gangs the two lids, and carries the blink crank.

    Bolted to the END FACES of the lids' inboard bosses - the previous
    version reached for inboard bolt bosses the rebuilt lids no longer have,
    which is why it sat parked. The lids' inboard boss faces are at x=+-7.0
    (measured from the built parts, not chosen), so the spine spans the 14 mm
    between them: an 8 mm bar, a 12x12 pad each end with `pad_gap` of
    daylight to the boss face, and two M2 clearance holes per pad aligned
    with the pilots the lids now carry at (y+-2.8, z+3.2).

    THE CRANK PIN IS BORED ALONG X. The previous crank bored it along Z, and
    that is not a detail - the lids rotate about the X axis, so a blink
    four-bar is planar in Y-Z and every one of its pins must be parallel to
    X or the linkage binds instead of pivoting. Same law, third application.

    The bar and crank stop at z=+0.5 while the pads rise to +6: the screws
    pass OVER the bar at z=3.2, so each one can be driven from the middle of
    the spine outward with a straight driver. On the axis they could never
    be installed - the bar itself is in the way.

    Prints flat on z=-6: bar, pads and crank all bottom on one plane, and
    the crank pin's bore comes out horizontal at O2.2, which needs no
    teardrop at that size.
    """
    prims, add = _prims()
    bm = add()                                          # the bar
    hm["_box"](bm, (8.0, E["bar_d"], 6.5), (0.0, 0.0, -2.75))
    for sx in (1, -1):                                  # end pads
        bm = add()
        hm["_box"](bm, (E["pad_t"], 12.0, 12.0),
                   (sx * (7.0 - E["pad_gap"] - E["pad_t"] / 2.0), 0.0, 0.0))
    bm = add()                                          # the crank, down-back
    hm["_box"](bm, (E["crank_t"], 14.0, 6.5), (0.0, -11.0, -2.75))
    ob = _union(hm, coll, "eye_lid_spine", prims)

    cuts, cadd = _prims()
    for dy in (1, -1):      # M2 clearance, straight through both pads
        bm = cadd()
        hm["_cyl"](bm, E["screw_d"], 18.0, (0.0, dy * 2.8, 3.2), 'X', segs=20)
    bm = cadd()             # the blink link pin, ALONG X - see the docstring
    hm["_cyl"](bm, E["screw_d"], E["crank_t"] * 4.0,
               (0.0, -14.0, -2.75), 'X', segs=20)
    _cut_each(hm, coll, ob, cuts, "_CUT_spine")
    return ob


def _lids_one_piece(hm, coll):
    """Superseded - kept uncalled, with the reason in lid_shell().

    Shape: a spherical band over each ball, carried to the hinge by a flat
    side plate either side of it, with a spine down the middle joining the
    two. The plates are what make it buildable - a band alone tapers to
    nothing at the poles of the tilt axis, so there is no material there to
    put a hinge in.

    The plates sit `lid_gap` outboard of the INNER sphere on purpose. Landing
    them on it exactly is a tangent boolean, and a face landing 0.0 mm from a
    cylinder's surface is how v1's frame lost a 4.8 x 0.5 mm face.

    Hinged at the OUTBOARD plates, x = +-49, so the bearing span is 98 mm
    rather than the 24 mm a centre hinge would give. The spine can then be
    solid, because nothing has to pass down the axis through it.
    """
    r_in = E["ball_d"] / 2.0 + E["lid_clr"]
    r_out = r_in + E["lid_wall"]
    half = E["pitch"] / 2.0
    px0 = r_in + E["lid_gap"]                 # plate inner face, from eye centre
    px1 = px0 + E["lid_plate"]

    # 1. the bands and the plates that carry them
    prims, add = _prims()
    for sx in (1, -1):
        cx = sx * half
        bm = add()
        _sphere(bm, r_out * 2.0, (cx, 0.0, 0.0))
        for ox in (1, -1):
            bm = add()
            hm["_cyl"](bm, r_out * 2.0, E["lid_plate"],
                       (cx + ox * (px0 + px1) / 2.0, 0.0, 0.0), 'X', segs=64)
    ob = _union(hm, coll, "eye_lids", prims)

    # 2. hollow the bands, then take the angular band out of them
    cuts, cadd = _prims()
    for sx in (1, -1):
        bm = cadd()
        _sphere(bm, r_in * 2.0, (sx * half, 0.0, 0.0))
    for deg, above in ((E["lid_lo"], False), (E["lid_hi"], True)):
        bm = cadd()
        _wedge(bm, 0.0, deg, above)
    _cut_each(hm, coll, ob, cuts, "_CUT_lids")

    # 3. spine, hinge hubs and crank go on AFTER the wedges, never before.
    # A half-space through the tilt axis does not know what it is cutting:
    # the spine sits ON the axis and the crank at 180 degrees, so the upper
    # wedge would have taken the crank off entirely and split the spine down
    # its length. They are unioned on once the band is the right shape.
    adds, aadd = _prims()
    bm = aadd()
    hm["_cyl"](bm, E["bar_d"], 2.0 * (half - px0), (0.0, 0.0, 0.0), 'X',
               segs=32)
    for sx in (1, -1):      # a full hub round each outboard bore, because a
                            # 65-degree sector is not enough material to put
                            # a bearing in
        bm = aadd()
        hm["_cyl"](bm, E["hinge_d"] + 5.0, E["lid_plate"],
                   (sx * (half + (px0 + px1) / 2.0), 0.0, 0.0), 'X', segs=32)
    bm = aadd()             # the crank, reaching back for the blink link
    hm["_box"](bm, (E["crank_w"], E["crank_r"] + E["crank_w"] / 2.0,
                    E["crank_t"]),
               (0.0, -(E["crank_r"] + E["crank_w"] / 2.0) / 2.0, 0.0))
    for i, bm in enumerate(adds):
        o2 = hm["_link"](coll, "_A%d" % i, hm["_mesh"]("_A%d" % i, bm))
        hm["boolean"](ob, o2, 'UNION')
        bpy.data.objects.remove(o2, do_unlink=True)

    # 4. the bores
    cuts2, cadd2 = _prims()
    for sx in (1, -1):
        bm = cadd2()
        hm["_cyl"](bm, E["hinge_d"] + E["fit"], E["lid_plate"] * 4.0,
                   (sx * (half + (px0 + px1) / 2.0), 0.0, 0.0), 'X', segs=32)
    bm = cadd2()
    hm["_cyl"](bm, E["screw_d"], E["crank_t"] * 4.0,
               (0.0, -E["crank_r"], 0.0), 'Z', segs=24)
    _cut_each(hm, coll, ob, cuts2, "_BORE_lids")
    return ob


def gimbal(hm, coll):
    """The tilt frame. Every member is axis-aligned, on purpose.

    The first version used diagonal arms swept from the cross member out to
    the tilt pivots, and a sign error sent the right-hand arm up and INBOARD -
    2.8 mm through the eyeball. I fixed the sign and the clash survived, which
    meant my model of the part was wrong rather than my arithmetic. Diagonals
    have to be reasoned about; boxes can be read off.

    So it is a table: two journal housings under the eyes, a cross member
    joining them, two horizontal arms reaching outboard, two vertical posts,
    and the tilt bosses on top of those. Six numbers, all of them checkable
    by eye.

    THE TWO SIDES ARE NOT MIRRORS. The left post carries a plain O5.4 tilt
    bore and rides the printed tilt pin; the right post's boss face is cut
    back to x=63.5 and carries a HORN POCKET, because the tilt servo's shaft
    IS the right-hand pivot - that is what direct drive means. The horn
    drops into an arm-shaped slot and torque goes through the slot's walls.
    No clamp screw: the joint is captive by geometry (1.0 mm float vs the
    slot engagement) - see the v2.1 note on the pocket dims in E for why
    the pocket sits at x 63.4..67.2 and nowhere shallower.

    The gimbal also carries both riding servos, because that is the design's
    core decision: pan and blink move WITH tilt, so tilt cannot drag on
    their linkages. The pan servo hangs inverted under a shelf reaching back
    off the cross member; the blink servo bolts to a plate hung beside the
    right journal housing.

    Clearances, from the parts as drawn:
        ball          reaches x = +-47
        lid + boss    reaches x = +-52
        posts         55..61 left, 57.4..63.4 right - clear of both
        arms          at z = -33.5, below the ball's underside at -16
        housing       stops at z = -17; the pan lever occupies -45..-41
        shelf         z -31..-27; the pan link and horn live below -40.9
        blink plate   x 22..28, y -32..-20: 6.5 clear of the O12 housing
    """
    r = E["ball_d"] / 2.0
    half = E["pitch"] / 2.0
    jz0 = -(r + E["journal"]) + 0.5          # -40.5, clear of the lever
    jz1 = -(r + 1.0)                         # -17
    az = E["cross_z"]                        # the arm/cross plane
    prims, add = _prims()

    for sx in (1, -1):
        bm = add()                           # journal housing
        hm["_cyl"](bm, E["house_d"], jz1 - jz0,
                   (sx * half, 0.0, (jz0 + jz1) / 2.0), 'Z', segs=48)
        bm = add()      # horizontal arm, out to the post. Runs 1 mm INTO
        # the cross member: butted at x=31 exactly, the shared end face is
        # a doubled face buried inside the housing, which is what the weld
        # kept tripping on.
        hm["_box"](bm, (E["arm_x"] - half + 1.0, E["gim_t"], E["gim_h"]),
                   (sx * (half - 1.0 + E["arm_x"]) / 2.0, 0.0, az))
        # The post and boss, per side. The right POST still stops at
        # x=63.4, but the BOSS runs on to x=67.0, because that is where
        # the horn actually is: plate at ~65 once the spline bottoms in
        # the hub (v2 stopped the boss at 63.5 and cut the pocket at
        # 61.4..63.5 - unreachable; see the v2.1 note in E). The boss face
        # keeps 2.55 to the servo's O12.1 collar at 69.55 and 2.0 to the
        # upright's inner wall at 69.0, and it is coaxial with the tilt
        # axis, so the sweep cannot change either number.
        # Post tops are NOT at z=7: the O14 boss's top tangent is exactly
        # there, and a tangent union is degenerate geometry - it is the
        # three coincident vertices the weld guard kept rolling back on.
        # The left post runs 1 mm PAST the tangent; the right post stops
        # BELOW the horn slot, which would otherwise shave it into a pair
        # of 0.1 mm blades, and the boss alone carries the pocket.
        if sx > 0:
            bm = add()
            hm["_box"](bm, (E["gim_t"], E["gim_t"], 36.0),
                       (60.4, 0.0, -22.5))
            bm = add()
            hm["_cyl"](bm, E["tilt_boss_d"], 11.0, (61.5, 0.0, 0.0), 'X',
                       segs=32)
        else:
            bm = add()
            hm["_box"](bm, (E["gim_t"], E["gim_t"], abs(az) + E["gim_h"] + 1.0),
                       (-E["arm_x"], 0.0, az / 2.0 + 0.5))
            bm = add()
            hm["_cyl"](bm, E["tilt_boss_d"], E["gim_t"] * 2.0,
                       (-E["arm_x"], 0.0, 0.0), 'X', segs=32)
        bm = add()                           # stub the lid hinges on
        L = E["arm_x"] - E["gim_t"] / 2.0 - E["lid_pin_x0"]
        hm["_cyl"](bm, E["lid_pin_d"], L,
                   (sx * (E["lid_pin_x0"] + L / 2.0), 0.0, 0.0), 'X', segs=32)
    bm = add()                               # cross member
    hm["_box"](bm, (2.0 * half, E["gim_t"], E["gim_h"]), (0.0, 0.0, az))
    # The pan servo shelf. The servo hangs INVERTED under it - body up
    # through the window, horn pointing down - which is what let the floor
    # rise 20 mm: nothing of the pan drive reaches below the pan bar any
    # more. Tabs screw UP into the shelf either side of the window. The
    # window sits 22 LEFT of the tab pin for the parallelogram (see
    # SERVOS), so a wing carries the shelf out to x=-46: narrower in y
    # than the main slab because the left arm lives at y +-4, and lapped
    # 2 mm into the slab in x with the SAME z extents - the arm/member
    # joint above already proves that union welds clean.
    bm = add()
    hm["_box"](bm, (39.5, 42.0, 4.0), (-6.25, -21.0, -29.05))
    bm = add()
    hm["_box"](bm, (22.0, 22.0, 4.0), (-35.0, -31.0, -29.05))
    # The blink servo bracket: an arm off the cross member and the right
    # journal housing, and a plate whose face the servo tabs screw to. The
    # BODY of an MG90S carries on 14.75 mm past its own tabs, so the plate
    # gets a pass-through window exactly like the shelf does, and the arm
    # stops 0.5 short of the body's flank. The plate's foot sits on z=-40.5
    # with everything else, so the print's first layer stays one plane.
    bm = add()      # runs 2.5 mm INTO the plate, and 1 mm WIDER than it,
    # so no two of their faces are coplanar - coincident planes are what
    # the weld guard keeps rolling back on
    hm["_box"](bm, (8.0, 22.5, E["gim_h"]), (25.0, -8.25, az))
    bm = add()
    hm["_box"](bm, (6.0, 18.0, 32.5), (25.0, -26.0, -24.25))
    ob = _union(hm, coll, "eye_gimbal", prims)

    cuts, cadd = _prims()
    for sx in (1, -1):
        bm = cadd()                          # pan bearing
        hm["_cyl"](bm, E["pin_d"] + E["fit"], 60.0,
                   (sx * half, 0.0, (jz0 + jz1) / 2.0), 'Z', segs=32)
    bm = cadd()                              # tilt pivot bore, LEFT only
    hm["_cyl"](bm, E["tilt_pin_d"] + E["fit"], E["gim_t"] * 6.0,
               (-E["arm_x"], 0.0, 0.0), 'X', segs=32)
    # The horn pocket, RIGHT: arm slot at 63.4..67.2 (through the new boss
    # face at 67.0), and a hub/spline recess running deeper to 61.5. Both
    # open outboard; the slot's extra depth is the tolerance that lets the
    # horn sit wherever the real spline stack puts it. The v2 centre-screw
    # access bore is GONE - it dead-ended inside the lid hinge stub (the
    # stub owns the axis inboard of the boss) and could never pass a screw.
    bm = cadd()
    hm["_box"](bm, (3.8, E["horn_slot_w"], 21.0), (65.3, 0.0, 6.5))
    bm = cadd()
    hm["_cyl"](bm, E["horn_hub_d"], 5.7, (64.35, 0.0, 0.0), 'X', segs=32)
    # the shelf window the pan servo body passes up through, and its pilots
    bm = cadd()
    hm["_box"](bm, (23.0, 12.5, 6.0), (-28.0, -33.0, -29.0))
    for px in (-42.0, -14.0):
        bm = cadd()
        hm["_cyl"](bm, E["pilot_d"], 6.0, (px, -33.0, -29.0), 'Z', segs=20)
    # The blink servo opening - a SLOT open to the plate's front edge,
    # not a closed window. The closed v2.1 window only admitted the body
    # by an x-slide from inboard, and the shelf slab owns that corridor:
    # Pat stood there with the servo and nowhere to come from. Open at
    # the front, the servo DROPS IN from -y at its final x and the tabs
    # screw to the same face. Pat hand-cut the printed gimbal to match.
    bm = cadd()
    hm["_box"](bm, (8.0, 18.2, 23.0), (25.0, -28.9, -25.0))
    # tab pilots: O1.9 and THROUGH the plate - sideways O1.7 blind holes
    # skin over in FDM (see the base's tilt pilots for the full story)
    for pz in (-39.0, -11.0):
        bm = cadd()
        hm["_cyl"](bm, 1.9, 10.0, (25.0, -26.0, pz), 'X', segs=20)
    _cut_each(hm, coll, ob, cuts, "_CUT_gimbal")
    return ob


def pan_bar(hm, coll):
    """The link that gangs the two eyes. This is what makes it a mechanism.

    Both pan levers pin to one bar, so the eyes cannot disagree - which is
    the whole point of deciding they never move independently. The bar, the
    two levers and the gimbal form a parallelogram: the bar translates
    sideways and both eyes turn by the same angle.

    All three pin axes stand VERTICAL, parallel to the axes the eyes turn
    about, because a four-bar whose joints are not parallel binds instead of
    pivoting. That is not an aesthetic choice and it is the thing I got
    wrong the first time.

    Prints flat on its back with the drive tab in the first layers.
    """
    half = E["pitch"] / 2.0
    prims, add = _prims()
    bm = add()
    hm["_box"](bm, (2.0 * half + E["bar_w"], E["bar_w"], E["bar_t"]),
               (0.0, E["bar_y"], E["bar_z"]))
    bm = add()      # the tab the servo link pins to
    hm["_box"](bm, (E["bar_w"], E["bar_y"] - E["drive_y"] + E["bar_w"],
                    E["bar_t"]),
               (0.0, (E["bar_y"] + E["drive_y"]) / 2.0, E["bar_z"]))
    ob = _union(hm, coll, "eye_pan_bar", prims)

    cuts, cadd = _prims()
    for sx in (1, -1):          # to the two levers
        bm = cadd()
        hm["_cyl"](bm, E["screw_d"], E["bar_t"] * 4.0,
                   (sx * half, E["bar_y"], E["bar_z"]), 'Z', segs=24)
    bm = cadd()                 # to the servo link
    hm["_cyl"](bm, E["screw_d"], E["bar_t"] * 4.0,
               (0.0, E["drive_y"], E["bar_z"]), 'Z', segs=24)
    _cut_each(hm, coll, ob, cuts, "_CUT_pan_bar")
    return ob


def _strap(hm, coll, name, p0, p1, w, t, axis, via=None):
    """A flat drilled link between two pin positions.

    `axis` is the PIN direction, and both pins of one strap share it - that
    is the planarity rule again: 'Z' for the pan link, which lies in the
    horizontal plane, 'X' for the blink link, which stands in Y-Z. Prints
    flat on its own face. Solid PLA, 8 x 4 buckles at ~590 N and the
    narrowest strap here is good for over 100 N against 13 N of stall.

    `via` (Z-plane straps only) doglegs the plate through a waypoint: a
    coupler is a plate and a plate can have any plan shape, so it routes
    AROUND what it would otherwise sweep through. The two segments lap at
    the waypoint with identical z faces, the union this build already
    proves clean.
    """
    a, b = Vector(p0), Vector(p1)
    prims, add = _prims()
    if axis == 'Z':
        pts = [a] + ([Vector((via[0], via[1], a.z))] if via else []) + [b]
        for s, e in zip(pts, pts[1:]):
            d = e - s
            bm = add()
            _rbox(bm, (d.length + w, w, t), (s + e) / 2.0,
                  Matrix.Rotation(math.atan2(d.y, d.x), 4, 'Z'))
    else:
        d = b - a
        bm = add()
        _rbox(bm, (t, d.length + w, w), (a + b) / 2.0,
              Matrix.Rotation(math.atan2(d.z, d.y), 4, 'X'))
    ob = _union(hm, coll, name, prims)
    cuts, cadd = _prims()
    for p in (a, b):
        bm = cadd()
        hm["_cyl"](bm, E["screw_d"], t * 4.0, p, axis, segs=20)
    _cut_each(hm, coll, ob, cuts, "_CUT_" + name)
    return ob


def _horn_pins():
    """Both drive horns' link pins at neutral, in world coordinates.
    links() hangs the straps on these and place_horns() draws the horns to
    them, so the straps and the horns cannot disagree.

    The pan horn points BACK along -Y at neutral, parallel to the eye
    levers - the parallelogram's whole point (see SERVOS). The blink pin
    sits where a 14 mm horn is PERPENDICULAR to the link line at neutral -
    mid-travel, best leverage both ways - solved via
    acos(horn_r/|shaft->crank|) rather than eyeballed.
    """
    pan = SERVOS["pan"]["loc"]
    p_pan = Vector((pan[0], pan[1] - E["pan_horn_r"], -42.15))

    blk = SERVOS["blink"]["loc"]
    crank = Vector((-14.0, -2.75))                  # the spine's pin, in Y-Z
    shaft = Vector((blk[1], blk[2]))
    sc = crank - shaft
    ang = math.acos(min(1.0, E["blink_horn_r"] / sc.length))
    u = sc.normalized()
    ca, sa = math.cos(-ang), math.sin(-ang)
    h = shaft + E["blink_horn_r"] * Vector((u.x * ca - u.y * sa,
                                            u.x * sa + u.y * ca))
    return p_pan, Vector((5.5, h.x, h.y)), Vector((5.5, crank.x, crank.y))


def links(hm, coll):
    """Both drive links, their pin positions derived from SERVOS and E so
    the linkage and the parts cannot drift apart.

    PAN, horizontal plane, pins vertical. The strap is the parallelogram's
    coupler: horn pin to tab pin, and it TRANSLATES with the bar rather
    than swinging. It DOGLEGS through (-10,-40): in the strap's own frame
    the servo hub sweeps an 11 mm arc about the horn pin, and a straight
    plate would pass 4.7 mm from the hub's centre at look-left 20 - a
    1.9 mm bite out of its edge. The dogleg keeps 2.0 mm of air at the
    worst pose. It lives at z -43.4..-40.9: above the horn's arm, below
    the servo body, clearing the tab's top face by 1.1.

    BLINK, Y-Z plane, pins along X.
    """
    p_pan, p_blk, p_crank = _horn_pins()
    out = [_strap(hm, coll, "eye_link_pan",
                  p_pan, (0.0, E["drive_y"], -42.15), 6.0, 2.5, 'Z',
                  via=(-10.0, -40.0)),
           _strap(hm, coll, "eye_link_blink", p_crank, p_blk, 8.0, 4.0, 'X')]
    return out


def base(hm, coll):
    """What the gimbal swings in, and what stands on the bench.

    Two uprights outboard of the gimbal, on a floor the mechanism can be
    bolted to and picked up by. This is the part that makes the rig testable
    without a head - which is the whole point of building the mechanism
    first.

    The LEFT upright carries a plain bearing bore for the printed tilt pin.
    The RIGHT upright IS the tilt servo mount: a rectangular pocket the
    MG90S body drops through from outboard, tabs screwed to the outer face,
    which puts the output shaft dead on the tilt axis. The gimbal is then
    driven by its right pivot with no linkage at all.
    """
    prims, add = _prims()
    bm = add()                          # floor
    hm["_box"](bm, (2.0 * E["base_x"] + E["base_t"],
                    E["base_y1"] - E["base_y0"], E["base_z1"] - E["base_z0"]),
               (0.0, (E["base_y0"] + E["base_y1"]) / 2.0,
                (E["base_z0"] + E["base_z1"]) / 2.0))
    for sx in (1, -1):                  # uprights
        bm = add()
        hm["_box"](bm, (E["base_t"], E["srv_h"], E["base_top"] - E["base_z1"]),
                   (sx * E["base_x"], 0.0,
                    (E["base_z1"] + E["base_top"]) / 2.0))
        bm = add()                      # boss round the tilt bearing
        hm["_cyl"](bm, E["tilt_boss_d"] + 4.0, E["base_t"],
                   (sx * E["base_x"], 0.0, 0.0), 'X', segs=32)
    ob = _union(hm, coll, "eye_base", prims)

    cuts, cadd = _prims()
    bm = cadd()                             # tilt pin bearing, LEFT
    hm["_cyl"](bm, E["tilt_pin_d"] + E["fit"], E["base_t"] * 4.0,
               (-E["base_x"], 0.0, 0.0), 'X', segs=32)
    bm = cadd()                             # servo body pocket, RIGHT
    hm["_box"](bm, (8.0, E["srv_cut_w"], E["srv_cut_z1"] - E["srv_cut_z0"]),
               (E["base_x"], 0.0, (E["srv_cut_z0"] + E["srv_cut_z1"]) / 2.0))
    # Servo tab pilots, outer face - THROUGH the wall and O1.9, not the
    # first print's blind O1.7: a sideways hole that small is ~8 sagging
    # layers and seals over in FDM. Pat met bare plastic where the sheet
    # promised pilots and recovered by drilling through the servo's own
    # tab holes. Vertical pilots keep O1.7; sideways ones get the bump
    # and a clear exit so both mouths read as holes.
    for pz in (-20.0, 8.0):
        bm = cadd()
        hm["_cyl"](bm, 1.9, E["base_t"] * 2.0, (72.0, 0.0, pz), 'X', segs=20)
    # Bench tab-screw pilots in the floor's edge faces. The deck's tabs
    # (bench.py, tab_x=30) drive M2 self-tappers into these edges, and
    # the first print had nothing there - "No holes in eye_base needed"
    # was a lie Pat paid for at the bench, tapper skating on bare PLA.
    # O1.9 horizontal blind holes may still skin over; the deck's own
    # tab hole guides a 1.5 mm drill straight into them if so.
    for sx in (1, -1):
        for ye in (E["base_y0"], E["base_y1"]):
            bm = cadd()
            hm["_cyl"](bm, 1.9, 12.0, (sx * 30.0, ye, -61.0), 'Y', segs=16)
    _cut_each(hm, coll, ob, cuts, "_CUT_base")
    return ob


def servo_proxy(hm, coll, name, loc, rot=None):
    """A solid MG90S where one has to go. Not a printed part - a placeholder
    that has to FIT, so the flow can be checked before anything is cut.

    Origin is the CENTRE OF THE OUTPUT SHAFT at the top face of the body,
    because that is the point a linkage is designed around - not the centre
    of the box, which is where a proxy placed by eye ends up and why it then
    disagrees with the horn by 6 mm.
    """
    prims, add = _prims()
    bm = add()
    hm["_box"](bm, (E["srv_l"], E["srv_w"], E["srv_h"]),
               (-E["srv_shaft_off"], 0.0, -E["srv_h"] / 2.0))
    bm = add()
    hm["_box"](bm, (E["srv_tab_l"], E["srv_w"], E["srv_tab_t"]),
               (-E["srv_shaft_off"], 0.0, -E["srv_h"] + E["srv_tab_up"]))
    bm = add()
    hm["_cyl"](bm, E["srv_shaft_d"] * 2.2, 4.0, (0.0, 0.0, -2.0), 'Z')
    bm = add()
    hm["_cyl"](bm, E["srv_shaft_d"], E["srv_shaft_up"],
               (0.0, 0.0, E["srv_shaft_up"] / 2.0), 'Z')
    ob = _union(hm, coll, name, prims)
    if rot is not None:
        ob.data.transform(rot)
    ob.data.transform(Matrix.Translation(Vector(loc)))
    ob.color = (0.85, 0.2, 0.2, 1.0)
    return ob


# Where each servo goes, and what it drives. All three are MG90S, and the
# rule that placed every one of them is the same rule three times over: THE
# SHAFT MUST BE PARALLEL TO THE AXIS IT DRIVES. Tilt and blink rotate about
# X, so those two shafts point along X; pan rotates about Z, so that shaft
# is vertical. The first draft had all three shaft-up, which meant two of
# them could not drive their axis through any linkage that does not bind.
#
#   tilt   IN the right base upright, shaft along -X, COAXIAL with the tilt
#          axis. The shaft is the right-hand pivot and the horn bolts into a
#          pocket in the gimbal's boss: direct drive, zero linkage, exactly
#          as the file's own target line says.
#   pan    on the GIMBAL, hung INVERTED under the shelf - body up through
#          the window, horn underneath, 22 mm to the LEFT of the tab pin
#          with its arm pointing BACK. Horn arm and eye levers are then
#          PARALLEL cranks of equal radius 11 on a rigid coupler - a
#          parallelogram, exactly 1:1 at EVERY angle, dead points at
#          +-45 deg against +-20 of travel. It sat directly BEHIND the
#          tab first, and that four-bar solved to 6.6:1 near look-right
#          20 deg, two degrees short of locking over-centre; coaxial
#          with the pin - where it started - is the terminal case of the
#          same disease, zero motion at centre. Inverting it is what let
#          the floor rise 20 mm - nothing of the pan drive reaches below
#          the pan bar, swung or parked.
#   blink  on the GIMBAL, shaft along -X beside the right eye, horn in the
#          Y-Z plane with the spine's crank, one strap between them.
#
# Pan and blink ride with tilt on purpose: that is what stops tilt from
# pulling on them, which in v1 was a cross-coupling error mixed out in
# software rather than designed out of the metal.
SERVOS = {
    # Shaft positions, not body positions - the proxy's origin IS the output
    # shaft, because that is the point a linkage is designed around.
    "tilt":  dict(loc=(69.55, 0.0, 0.0),    axis='-X'),
    "pan":   dict(loc=(-22.0, -33.0, -39.0), axis='flip'),
    "blink": dict(loc=(14.0, -26.0, -19.0), axis='-X'),
}


def place_servos(hm, coll):
    rots = {None: None,
            'X': Matrix.Rotation(math.radians(90), 4, 'Y'),
            '-X': Matrix.Rotation(math.radians(-90), 4, 'Y'),
            'flip': Matrix.Rotation(math.radians(180), 4, 'X')}
    out = []
    for name, s in SERVOS.items():
        out.append(servo_proxy(hm, coll, "PROXY_servo_" + name,
                               s["loc"], rots[s["axis"]]))
    return out


def place_horns(hm, coll):
    """The stock nylon horns for pan and blink, drawn where they must POINT
    AT NEUTRAL - which is assembly information, not decoration: centre the
    servo FIRST, then press the horn on aimed like this, or the whole
    linkage runs offset. Without these the straps' far holes float in
    space, because the part that ties them to the shaft comes out of the
    servo bag, not the printer.

    Drawn deliberately thin: just the arm plate at the spline tip, kept
    0.1-0.2 clear of shaft and strap so no proxy ever touches a printed
    part. The O2 pin is the M2 linkage screw, through the strap's bore.
    The tilt horn DOES get a proxy now (v2.1). Through v2 it had none -
    "it lives inside the pocket and would never be seen" - and unseen is
    exactly how that coupling shipped broken twice; Pat's first question
    at the bench was where the third horn went. Drawn at the MEASURED
    stack (spline tip x 65.05), plate thinned to 1.2 so one proxy can
    clear the slot floor on one side and the spline tip on the other.
    """
    p_pan, p_blk, _ = _horn_pins()
    out = []

    prims, add = _prims()               # pan: plate under the strap, arm -Y
    pan = SERVOS["pan"]["loc"]
    bm = add()
    hm["_box"](bm, (5.0, E["pan_horn_r"] + 6.0, 1.6),
               (pan[0], (pan[1] + p_pan.y) / 2.0, -44.4))
    bm = add()      # hub disc on the spline tip, 1.4 not 1.6: its faces
    # must sit INSIDE the plate, never coplanar with it - the weld trap
    hm["_cyl"](bm, 7.2, 1.4, (pan[0], pan[1], -44.4), 'Z', segs=24)
    bm = add()                          # the linkage screw, up through
    hm["_cyl"](bm, 2.0, 4.2, (p_pan.x, p_pan.y, -42.7), 'Z', segs=16)
    ob = _union(hm, coll, "PROXY_horn_pan", prims)
    ob.color = (0.92, 0.92, 0.88, 1.0)
    out.append(ob)

    prims, add = _prims()               # blink: plate outside the strap
    blk = Vector((SERVOS["blink"]["loc"][1], SERVOS["blink"]["loc"][2]))
    tip = Vector((p_blk.y, p_blk.z))
    d = tip - blk
    mid = (blk + tip) / 2.0
    bm = add()
    _rbox(bm, (1.6, d.length + 6.0, 5.0), (8.5, mid.x, mid.y),
          Matrix.Rotation(math.atan2(d.y, d.x), 4, 'X'))
    bm = add()      # hub disc, 1.4 for the same never-coplanar reason
    hm["_cyl"](bm, 7.2, 1.4, (8.5, blk.x, blk.y), 'X', segs=24)
    bm = add()
    hm["_cyl"](bm, 2.0, 5.9, (6.15, p_blk.y, p_blk.z), 'X', segs=16)
    ob = _union(hm, coll, "PROXY_horn_blink", prims)
    ob.color = (0.92, 0.92, 0.88, 1.0)
    out.append(ob)

    prims, add = _prims()               # tilt: arm UP, in the boss slot
    # The one horn with no strap and no pin: it IS the drive. Plate in
    # the slot at the measured plane - 0.15 to the slot floor at 63.4,
    # 0.3 to the spline tip at 65.05, 0.45 to each slot wall.
    bm = add()
    hm["_box"](bm, (1.2, 5.3, 19.0), (64.15, 0.0, 9.5))
    bm = add()      # hub disc, faces inside the plate - the weld trap
    hm["_cyl"](bm, 7.2, 1.0, (64.15, 0.0, 0.0), 'X', segs=24)
    ob = _union(hm, coll, "PROXY_horn_tilt", prims)
    ob.color = (0.92, 0.92, 0.88, 1.0)
    out.append(ob)
    return out


def tilt_pin(hm, coll):
    """The LEFT tilt pivot: one O5 rod through the base upright into the
    gimbal's boss, headed outboard. The right pivot is the servo shaft, so
    only one of these exists. Prints standing on its head - 100% of its own
    shadow. Held by the head on one side and the boss's grip on the other;
    if it walks in service, a dab of glue at the head is the fix, not a
    redesign."""
    prims, add = _prims()
    bm = add()
    hm["_cyl"](bm, E["tilt_pin_d"], 19.6, (-65.7, 0.0, 0.0), 'X', segs=32)
    bm = add()      # head, overlapping the rod 0.5 - a butt is three shells
    hm["_cyl"](bm, 9.0, 2.6, (-76.4, 0.0, 0.0), 'X', segs=32)
    return _union(hm, coll, "eye_tilt_pin", prims)


# The origin of every moving part is put ON the axis it turns about, so the
# mechanism can be posed by setting a rotation rather than by solving one.
PIVOTS = {
    "eye_ball_R": (31.0, 0.0, 0.0), "eye_ball_L": (-31.0, 0.0, 0.0),
    "eye_pin_R":  (31.0, 0.0, 0.0), "eye_pin_L":  (-31.0, 0.0, 0.0),
    "eye_lid_R":  (31.0, 0.0, 0.0), "eye_lid_L":  (-31.0, 0.0, 0.0),
    "eye_lid_spine": (0.0, 0.0, 0.0),
    "eye_gimbal": (0.0, 0.0, 0.0),
}


def set_origins():
    """Move each part's origin onto its own pivot, without moving the mesh."""
    n = 0
    for name, piv in PIVOTS.items():
        ob = bpy.data.objects.get(name)
        if ob is None:
            continue
        delta = Vector(piv) - ob.location
        ob.data.transform(Matrix.Translation(-delta))
        ob.location = Vector(piv)
        n += 1
    return n


def gimbal_support(hm):
    """Pat's support box - four plain blocks, not slicer trees and not a
    lattice. Two under the floating pan shelf and wing (footprints stop
    1.5 clear of the blink plate), one on each arm's top face reaching
    up under the O5 hinge stub. Every face keeps a 0.2 release gap to
    the part: grab, twist, they pop off. Lives in PRINT_AIDS (not a
    mechanism part, exempt from health), ships only inside the gimbal's
    STL - slice that one part with supports OFF."""
    boxes = [
        ((66.0, 34.5, 9.25), (-12.5, -24.25, -35.875)),   # shelf + wing
        ((3.25, 34.5, 9.25), (31.125, -24.25, -35.875)),  # right corner
        ((7.0, 4.0, 23.6), (52.0, 0.0, -14.5)),           # under R stub
        ((7.0, 4.0, 23.6), (-52.0, 0.0, -14.5)),          # under L stub
    ]
    old = bpy.data.collections.get("PRINT_AIDS")
    if old:
        for o in list(old.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(old)
    aids = bpy.data.collections.new("PRINT_AIDS")
    bpy.context.scene.collection.children.link(aids)
    bm = bmesh.new()
    for dims, at in boxes:
        ret = bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, verts=ret["verts"], vec=Vector(dims))
        bmesh.ops.translate(bm, verts=ret["verts"], vec=Vector(at))
    me = bpy.data.meshes.new("eye_gimbal_sup")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("eye_gimbal_sup", me)
    aids.objects.link(ob)
    ob.color = (0.55, 0.75, 0.55, 1.0)
    for p in me.polygons:
        p.use_smooth = True
    print("  support blocks: %d" % len(boxes))
    return ob


def build(save=False):
    hm = _hm()
    old = bpy.data.collections.get(COLL)
    if old:
        for o in list(old.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(old)
    coll = bpy.data.collections.new(COLL)
    bpy.context.scene.collection.children.link(coll)
    print("eye:")
    made = []
    for sx in (1, -1):
        made.append(ball(hm, coll, sx))
    for sx in (1, -1):
        made.append(pin(hm, coll, sx))
    for sx in (1, -1):
        made.append(lid_shell(hm, coll, sx))
    made.append(lid_spine(hm, coll))
    made.append(gimbal(hm, coll))
    made.append(pan_bar(hm, coll))
    made.append(base(hm, coll))
    made.append(tilt_pin(hm, coll))
    made.extend(links(hm, coll))
    for ob in made:
        print("  %-14s %d verts" % (ob.name, len(ob.data.vertices)))
    weld_all(verbose=True)
    smooth_all(verbose=True)
    print("  origins on pivots:", set_origins())
    place_servos(hm, coll)
    place_horns(hm, coll)
    gimbal_support(hm)
    if save:
        bpy.ops.wm.save_mainfile()
    return coll


def _checks():
    ns = {"__name__": "checks", "__file__": CHECKS}
    with open(CHECKS, "r", encoding="utf-8") as fh:
        exec(compile(fh.read(), CHECKS, "exec"), ns)
    return ns


def printcheck():
    """The gate, over every printed part.

    Balls back-face-down, pins on end, straps and bars flat. Each lid
    stands on its OUTBOARD hinge-boss face - the only flat face it has -
    which is X_DOWN for the right lid and X_UP for its mirror. Two parts
    declare SUPPORT, which the gate treats as an explicit per-part statement
    and not a loosened threshold: the lids are thin curved shells, which is
    the shape support exists for, and the gimbal carries the pan shelf 9.5
    mm above its own first layer.
    """
    ns = _checks()
    return ns["gate"]([(n, ns[o], s) for n, o, s in PLATE])


# One table drives the gate AND the exporter, so a part cannot pass
# printcheck in one orientation and reach the slicer in another. Fields:
# object name, its print orientation (a matrix name in checks.py), and
# whether it declares SUPPORT.
PLATE = [
    ("eye_ball_R",     "Y_UP",   False),
    ("eye_ball_L",     "Y_UP",   False),
    ("eye_pin_R",      "FLAT",   False),
    ("eye_pin_L",      "FLAT",   False),
    ("eye_lid_R",      "X_DOWN", True),
    ("eye_lid_L",      "X_UP",   True),
    ("eye_lid_spine",  "FLAT",   False),
    ("eye_gimbal",     "FLAT",   True),
    ("eye_pan_bar",    "FLAT",   False),
    ("eye_base",       "FLAT",   False),
    ("eye_tilt_pin",   "X_UP",   False),
    ("eye_link_pan",   "FLAT",   False),
    ("eye_link_blink", "X_UP",   False),
]


def export_stls(dirpath=r"C:\Humalien\exports\eye"):
    """Every part in PLATE as an STL, already in its GATED orientation with
    its bottom face on z=0 - drop it in the slicer, do not rotate it. The
    _x1 suffix is the print count, the convention v1's plates used."""
    ns = _checks()
    os.makedirs(dirpath, exist_ok=True)
    out = []
    for name, okey, _sup in PLATE:
        src = bpy.data.objects[name]
        me = src.data.copy()
        me.transform(ns[okey] @ Matrix.Translation(src.location))
        sup = bpy.data.objects.get("eye_gimbal_sup")
        if name == "eye_gimbal" and sup:
            # the support blocks ship INSIDE the gimbal's STL as extra
            # shells - so this one part is sliced with supports OFF
            ms = sup.data.copy()
            ms.transform(ns[okey] @ Matrix.Translation(sup.location))
            bx = bmesh.new()
            bx.from_mesh(me)
            bx.from_mesh(ms)
            bx.to_mesh(me)
            bx.free()
            bpy.data.meshes.remove(ms)
            print("  (gimbal STL carries its own support blocks - "
                  "slice it with supports OFF)")
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


def health():
    """Watertight, one shell, no weld debt - asked of every part."""
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
