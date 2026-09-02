"""Humalien Desk - first massing and packaging study for the desktop assistant.

A round body, a round head on a headphone-style yoke, two single-axis arms,
and two ring eyes that are LIGHT ONLY - no eye mechanism at all.  Four MG90S
in the whole robot, out of the twelve on the bench.

    pan     one servo on a shelf inside the shoulder, output up.  The yoke
            hub clamps its spline.  The hub's flange bears on DB_top over an
            11 mm annulus, so THE SERVO NEVER CARRIES THE HEAD'S WEIGHT - it
            only supplies torque.  An MG90S output bearing will not take
            ~120 g of head as a thrust load, and this annulus is what stops
            it ever seeing one.
    nod     one servo INSIDE the head, on the head's own centre line.  The
            head is a sphere turning about its own centre, so nod is
            weight-neutral AND cannot collide with the body at any angle -
            every point of a sphere stays HEAD_R from the axis.  Its output
            is bolted to the YOKE through DB_cplr, so what nods the head is
            the servo's own reaction - see "the nod joint" below, because
            for a while this drove nothing at all.
    arms    one servo each, axis left-right, arm swings fore and aft.  The
            blade is jogged outboard to |x| 86 so it clears the O160 waist.

Eyes are 2x NeoPixel Ring 12B behind a printed diffuser.  Lighting an ARC of
the twelve rather than the whole ring reads as a pupil looking that way, so
gaze direction costs zero servos and zero linkages.  That is the point of
this pivot: the mechanism that killed eye rig 01 is deleted, not redesigned.

Assembly order, which is the thing that has actually failed twice here:

    0.  the head tilt servo is FED UP the rear of the body with its lead
        still plugged into the PCA9685 - up through the window in the pan
        shelf and out of the dome's mouth.  Nothing on this run is ever
        unplugged, which is the requirement the rest of it is shaped by: the
        harness is built and dressed inside the shell before any shell
        geometry closes.  Then DB_top drops on OVER THE LEAD, which enters
        its slot sideways through the throat at 270.  That order is not a
        preference - measured on the built mesh, the pass column runs 1,579
        mm3 through DB_top's own annulus, so with the plate on there is no
        way past it, and its free band is 10 mm against a servo needing
        14.2.  See "feeding a SERVO up" for the envelope everything on this
        run is sized from.
    1.  nod servo goes up through the window in the head's underside, with
        the head IN YOUR HANDS and its lead already hanging down the neck,
        and then slides into its pocket in the head shell.  Also an order
        and not a preference: with the head on the yoke that window sits 4.5
        mm above the flange, against a servo 26.7 tall.  Before, not after.
    2.  bracket + servo go in through the O92 face opening and take two
        screws along +Y, driven straight through that same opening.  No
        screw in this build is driven along an axis you cannot see down.
    3.  the two DB_yoke_arm drop onto the hub's tongues from above and take
        one radial M3 each, driven from the REAR.  Then the head drops
        between them - 112 wide into a 116 gap, 2 mm a side.
    4.  DB_cplr enters from the RIGHT, through the yoke bore, onto the servo
        spline, and TWO M2 BOLT ITS CAP TO THE YOKE ARM.  Those two bolts
        are the entire drive: without them the servo turns the coupler in a
        round hole and the head sits still, which is exactly what this file
        built for the first three weeks of the desk bot.
        DB_pivot enters from the LEFT: journal in the yoke, D section into a
        boss inside the head, one M3 x 25 down its own axis into that boss.
        Both insert radially, both have a clear driver path from outside.
        (Eye rig 01 died on a continuous shaft through a CLOSED bore that
        needed 23 mm of axial slide against 0.50 available.  This is that
        same joint, built as two parts inserted from opposite ends - and it
        found a second way to fail that clearance checks cannot see.)
    5.  arm servos slide into their pockets from inside the dome; their two
        screws come in from OUTSIDE the shoulder, so the heads show as two
        small dots a side.  That is the price of a slide-in pocket on a
        horizontal shaft - an MG90S is always pierced parallel to its own
        output, so the driver has to come from where the shaft points.
    6.  face plate last, over the rings.

Power is two cords out of the back panel, on purpose and not by accident:
the Alitove goes to the barrel jack and feeds ONLY the PCA9685 screw
terminals, and the Pi takes its own USB-C brick through the port window.
The servo rail and the Pi rail never touch except at ground.

Print order, which is Pat's and is the right way round: DB_chassis FIRST,
alone.  It carries the Pi 5, the PCA9685 and both speaker boxes and it stands
on its own feet, so the whole electrical build can be assembled and run on the
bench before any shell geometry is committed to.  Shell, arms and head follow
once the chassis is proven.

Print orientation, all support-free:
    DB_chassis  base down.  Baffles and posts stand vertically off the plate,
                so there is no overhang anywhere in it.
    DB_shell  base down.  Steepest flare is 40 deg off vertical at the foot,
              inside what an A1 bridges dry.
    DB_dome   also base down: it only ever tapers INWARD going up, and its
              cavity has no roof because DB_top is a separate flat ring.
    DB_top    flat.  It is the thrust bearing face, so it wants to be a
              first-layer surface anyway.
    DB_yoke_hub   collar face down.  O60 of first layer, 24 mm tall, and the
              one flat in it is the r30 -> r36 bearing eave at z 116.
    DB_yoke_arm   on its -y face.  A flat 14 mm prism, no overhang at all,
              and the layers run ALONG the plane the head bends it in.  Both
              arms are the same STL, turned 180 deg about Z.

Every one of those claims is now checked.  PRINT_ORIENT holds each part to
the orientation it was drawn for and fits() counts the downward-facing area
in it - because DB_yoke was "support-free, base down" in this docstring for
weeks while actually standing 88 mm tall on 135 mm2 of plate under 6,021 mm2
of flat roof, and nothing in the gate could say so.

    import desk_bot; desk_bot.build(); desk_bot.fits()
    desk_bot.pose(pan=30, nod=-12, arm_l=40, arm_r=-10)

Millimetres throughout.  +Y is the direction the face looks.
"""
import math
import bpy
import bmesh
from mathutils import Vector, Matrix

COLL = "DESK_BOT"
SMOOTH_ANGLE = 35.0
SEGS = 64                       # shells, and anything on the silhouette
FINE = 48                       # holes a finger or an eye finds
PILOT = 20                      # screw pilots - round enough at O2.5

# ---------------------------------------------------------------- the body
# Outer surface as (radius, z), bottom to top.  O160 at the waist.  The body
# is a solid of revolution about Z, which is what lets fits() answer "is this
# board inside the shell" analytically instead of by ray cast - and ray casts
# fired down an axis have lied to this project before.
WALL = 3.0
# O190, up from 180.  Not styling: the half-width has to carry the Pi (42.5)
# plus a gap, plus 21 of speaker box, plus the baffle, and the baffle's own
# corners have to stay inside the barrel out at y 53.  At 180 that closed to
# 0.2 mm, which is not a clearance, it is a coincidence.
# There is now a straight band at r 88 over z 76..90.  A cone has no place
# to put a flat-faced boss: over the 22 mm a servo housing needs, the old
# profile lost 27 mm of radius, so the housing was buried at one end and 14 mm
# proud at the other.  A short cylindrical shoulder fixes that and reads as a
# shoulder rather than as a lump on a cone.
BODY_PROF = [(89.0, 0.0), (94.0, 7.0), (95.0, 20.0), (95.0, 58.0),
             (94.0, 66.0), (94.0, 70.0), (89.0, 74.0), (88.0, 76.0),
             (88.0, 90.0), (82.0, 97.0), (70.0, 104.0), (52.0, 112.0)]
INNER_PROF = [(r - WALL, max(z, WALL)) for r, z in BODY_PROF] + [(49.0, 260.0)]
SPLIT_Z = 66.0                  # shell / dome parting line
BODY_TOP = 112.0

# ------------------------------------------------- the shell/dome joint
# There was no joint.  SPLIT_Z was one plane cut twice - everything above it
# off the shell, everything below it off the dome - leaving a flat 3 mm
# annulus, ID 182, with NOTHING holding it, under a dome that carries both
# arm servos, the pan shelf and the whole head.  The first arm swing walks
# it off.
#
# Three ribs stand up inside the shell and 4 mm into the dome's mouth: they
# locate it on three points, and one radial M3 each holds it down.  The
# screws go in horizontally from outside, which is the ONLY direction that
# stays reachable on the assembled robot - a vertical screw at this radius
# has the dome's own inner wall closing over it by z 104, and the top
# opening is only O104.  That is the eye-rig-01 trap and it is why these
# are not vertical.
#
# The three angles are not styling either.  A rib has to miss the speaker
# grilles (|x| >= 71 below z 67) and the rear access cut (|x| <= 46 behind
# y -58), and 90/225/315 is the set that clears both with the ribs still
# symmetric about the face.
JOIN_A = [math.radians(a) for a in (90.0, 225.0, 315.0)]
JOIN_R = (82.0, 90.0)           # rib inner face, and the register pad OD.
                                # Flat pad, so its corners sit at 90.45 -
                                # 0.55 under the dome's 91.0 bore
JOIN_W = 9.0                    # half width
JOIN_Z = (52.0, 70.0)           # rib foot, and 4 mm proud of the split
JOIN_SCREW_Z = 68.0             # mid-pad, 2 mm above the parting line
JOIN_PILOT, JOIN_CLEAR, JOIN_CBORE = 2.5, 3.4, 6.0

TOP_Z = (112.0, 116.0)          # DB_top, the flat bearing ring
TOP_R = (31.0, 52.0)            # ID 62 for the collar, OD 104

# ----------------------------------------------------------- the wire way
# Servo and NeoPixel wires have to get from the chassis into the head, and
# the parting line is wide open, so the only real obstacles are the pan
# shelf and DB_top.  The shelf already has its two O26 holes at (0, +-38);
# this is the rest of the run, and it is deliberately all at the REAR so
# the whole thing is one straight vertical drop at r 44.5, 270 deg.  Rear
# because that is where a wire is allowed to be seen; the front is the face.
#
# The slot's radius is pinned from both sides: outside the yoke flange's
# O84, so the flange sweeps PAST it at any pan angle instead of closing it,
# and inside DB_top's O97 spigot, so it does not break the register into
# the dome.  That leaves a 6.5 mm band and the slot takes 5 of it.  It also
# misses all three O3.2 mounting holes - see _top, which had to give up
# 270 deg to make room and now sits at 90/210/330.
WIRE_R, WIRE_D = 44.5, 5.0
WIRE_A = [math.radians(230.0 + 10.0 * i) for i in range(9)]
# And the slot is open to the RIM at 270, through a throat narrower than
# itself.  That one cut is what lets DB_top be threaded onto a lead that is
# already plugged in at both ends - the plate drops over the loom sideways
# instead of the loom being posted through it.  Narrower than the slot on
# purpose: the loom presses in past 4.0 and then cannot walk back out under
# the yoke arm foot, which sweeps this exact radius at pan +-80.
WIRE_THROAT = 4.0
# Out of the head at the REAR of its underside, onto the yoke flange.  The
# flange turns WITH the head, so nothing in this run crosses the nod axis;
# the only relative movement is at DB_top, and the slack there covers it.
# The size of that opening is NOT a wire dimension any more - see below.

# ------------------------------------------------------------- the servos
# MG90S / SG90.  Local frame: origin on the output axis in the plane of the
# case top, +x running along the case away from the shaft.
SV_BODY_X, SV_BODY_Y, SV_BODY_Z = (-5.9, 16.9), (-6.1, 6.1), (-22.7, 0.0)
SV_EAR_X, SV_EAR_Z = (-10.6, 21.6), (-7.67, -5.17)      # ears, 2.5 thick
SV_HOLE_X = (-8.274, 19.726)    # 28.0 apart, the SG90 standard
SV_HUB_D, SV_HUB_Z = 5.9, 4.0
SV_REACH = 24.0                 # how far a pocket sweeps out of its open
                                # side.  Named because the gate has to read
                                # it: this sweep is the pan pocket's long
                                # dimension, and that is the hole the head
                                # tilt servo is fed through.
SV_FIT = 0.6                    # slip fit round the case.  0.4 is inside
                                # what this printer holds; a servo you have
                                # to force into a pocket is a servo you
                                # cannot get back out.

# MEASURED in grey PLA with the archive's bore_ladder(), not guessed - 4.7
# had to be forced.  Specific to BOTH printer and filament: re-run it on a
# change of either.
HORN_BORE = 4.95
FIT_MIN = 0.15                  # 0.1 a side binds solid in PLA.  This is the
                                # floor, and load-bearing joints want more.

# ------------------------------------------------------- feeding a SERVO up
# The harness is built first and it is never taken apart: Pi, PCA9685 and
# every servo lead wired, dressed and run inside the shell on the bench,
# which is the entire reason DB_chassis prints alone and first.  So the head
# tilt servo does not arrive from the head end with a plug to push onto the
# PCA afterwards.  It arrives from the BOTTOM, already plugged in, and has to
# be fed up the rear of the robot into the head with its lead trailing.  One
# servo, on its own, and only this one: the pan servo is set into the neck by
# hand off the top, and neither arm servo ever leaves the dome.
#
# That makes every opening in the rear run a SERVO dimension, not a wire
# dimension.  As drawn on 30 Aug none of them were: the shelf's hole was
# O26, DB_top's slot 5.0 wide and the head's exit O12, against a servo that
# needs 29.4 across its diagonal.  Three separate stops on a run that has to
# be continuous, and nothing in fits() could say so, because everything here
# had been sized for the 3-core lead and not for the thing on the end of it.
#
# Fed ON END - the case's long axis vertical, so the 32.2 mm ear span runs
# ALONG the direction of travel and costs nothing - an MG90S shows its
# smallest silhouette: the case across, by the case height plus the output
# hub.  The horn comes off for the trip.  The hub does not.
SV_PASS = (SV_BODY_Y[1] - SV_BODY_Y[0],                 # 12.2 across the case
           SV_BODY_Z[1] - SV_BODY_Z[0] + SV_HUB_Z)      # 26.7, base to hub top
PASS_CLR = 2.0                  # SV_FIT is 0.6 and that is a POCKET fit, on a
                                # part you can see, hold square and press.
                                # This is a blind push at arm's length up a
                                # hole inside a closed body, so it gets 1 mm
                                # a side.
PASS_W, PASS_L = SV_PASS[0] + PASS_CLR, SV_PASS[1] + PASS_CLR

# Both openings are STADIUMS, not round holes.  A round hole that swallows
# that silhouette is O31.4 - the diagonal, plus the clearance - and neither
# part has 31.4 to give away.  14.2 x 28.7 is the same passage in 60% of the
# area, and the long axis then goes wherever the part can afford it:
#
#   shelf   long axis TANGENTIAL, at the existing (0, -38).  Radial does not
#           work: the servo has to keep going straight up and out of the
#           dome's own mouth, which is r 49 at z 112, and a radial window at
#           r 38 puts its outer corner at 52.4 - into the dome's wall.
#           Tangential puts that corner at 47.3.
#   head    long axis RADIAL, so the opening reads 14 mm wide seen from
#           behind instead of 29.  It is the only new hole in a surface
#           anyone looks at, and the rear underside - under the head, over
#           the neck - is the cheapest place in this robot to put one.
#
# So the servo takes a quarter turn on its own axis somewhere in the open
# neck between them.  That is a two-handed motion in free air with the head
# not yet on, and it is the price of not cutting a 29 mm slot across the
# back of a sphere.
PASS_SHELF_Y = -38.0            # tangential: PASS_L runs on X here
PASS_HEAD_Y = -22.0             # radial: PASS_L runs on Y here.  -22 and not
                                # -18, so the near edge stays off the head's
                                # bottom pole and the whole window sits on
                                # the part of the sphere that faces the neck

# ---------------------------------------------------------------- the head
HEAD_R = 56.0
HEAD_WALL = 2.5
HEAD_Z = 182.0                  # head centre == nod axis
FACE_Y = 32.0                   # the flat, which is also the O92 face opening
FACE_T = 4.5                    # 3.2 of ring pocket + 1.3 of diffuser
FACE_REBATE_R = 46.1            # the counterbore DB_face drops into
YOKE_X = (58.0, 64.0)           # yoke arm inner and outer faces
NOD_BORE = 8.0
EYE_X, EYE_Z = 21.0, 6.0        # eyes set a little high reads friendly
RING_OD, RING_ID, RING_T = 37.0, 23.3, 3.2      # NeoPixel Ring 12B

# ------------------------------------------------------- seating a ring
# The ring used to drop into a plain blind pocket and NOTHING held it there.
# Three things were missing, and all three are assembly rather than
# clearance, so no margin anywhere in fits() was ever going to report them:
#   - no retention.  Push the face plate on and the rings fall out of it.
#   - no room made for the lead.  A 12B has its pads on the BACK, so the
#     wires leave through the one face the design had nothing to say about,
#     and a tug on them lifts the ring straight out of its pocket.
#   - no clocking.  Nothing said which way round a ring goes in, so the lead
#     could end up on the far side of the plate from the wire pass.
# So: the pocket is now EXACTLY RING_T deep, which puts the ring's back
# flush with the plate's own back face and gives a flat bar something to lie
# on; a scallop in the bore wall clocks the ring and carries the lead out
# inboard-and-down, which is where the pass is; DB_eye_holder holds it in.
RING_APER = 35.5                # The eyes are OPEN.  There used to be 1.3 of
                                # PLA left across the front of each bore and
                                # called a diffuser, which it only is if the
                                # plate is printed in something that passes
                                # light - otherwise the ring is simply walled
                                # in.  A 12B's 5050s sit on a O30.5 pitch and
                                # are 5 square, so they reach O35.5; anything
                                # tighter than this clips them.  Against a
                                # O37 ring that leaves 0.75 a side of
                                # shoulder to seat on, and the clamp is what
                                # pulls it up against that shoulder.
RING_FIT = 0.3                  # per side, ring OD into its bore.  A drop
                                # in, deliberately - a 12B is a routed PCB and
                                # a press fit on one is a ring you cannot get
                                # back out without levering on the LEDs
RING_T_BAND = (2.9, 3.5)        # what a "3.2 thick" ring ACTUALLY measures.
                                # 1.6 of PCB and a 1.6 LED, both with their
                                # own tolerance, and clones are worse
RING_SINK = 0.4                 # the bore is cut this much deeper than a
                                # NOMINAL ring.  Without it the bore is
                                # exactly RING_T and a ring on the thick side
                                # of the band stands 0.3 proud of the plate's
                                # own back face - so the holder lands on the
                                # ring instead of on the plate and never
                                # pulls down square.  Measured, not guessed:
                                # see the grip check in fits()
FACE_DIFF = FACE_T - RING_T - RING_SINK         # what is left in front of
                                # the ring, and since RING_APER opens it,
                                # all of it is the seating shoulder
FACE_BACK = FACE_Y - FACE_T      # the plate's back face - what the holder
                                 # seats on, which is NOT where the ring's
                                 # back lands once RING_SINK is in
RING_SEAT = FACE_Y - FACE_DIFF - RING_T         # where a NOMINAL ring's
                                                # back lands: RING_SINK
                                                # behind the plate's face
RING_LEAD_A = 45.0              # the lead scallop, off straight down, inboard
RING_LEAD_R = 3.0
# ------------------------------------------------------------ the holder
# A bar across the ring was the first go and it was the wrong shape.  Two
# feet at 180 deg press a 1.6 mm PCB at two points, and they do nothing at
# all about the other thing a bar cannot do: light.  The ring backs onto an
# open head, so whatever does not leave through the front leaves into the
# shell and comes back out of every other opening in the robot.
#
# So the holder is an ANNULUS with a raised land, and the land is the whole
# design.  It bears on the PCB's outer rim the whole way round - even
# pressure, a light seal, and the one band on the back of a 12B where there
# is guaranteed to be no solder.  Everything inboard of HOLD_ID is simply
# open, and that is where the lead goes: straight back into the head,
# unbent and untouched by anything.  The four notches are for a ring whose
# pads sit further out than they should, so the wire escapes UNDER the land
# instead of being pinched by it.
HOLD_OD = 40.0                  # capped by the OTHER eye: the centres are
                                # 2 * EYE_X = 42 apart, so past 42 here and
                                # the two holders foul each other
HOLD_ID = 32.4                  # the open middle - the lead's way out
HOLD_LAND_OD = 36.4             # the land is HOLD_ID -> here.  2 mm of it,
                                # sat on the PCB rim inside its O36.8 edge
HOLD_T = 2.5                    # body thickness, behind the plate
HOLD_LIFT = 0.9                 # how far the land stands proud of the
                                # holder's face.  This is the whole answer to
                                # "too tight vs falls out": it has to reach
                                # the THINNEST ring in RING_T_BAND, and it
                                # only ever has to flex for the thickest.
                                # Grip = t - (FACE_T - FACE_DIFF - HOLD_LIFT)
                                # so it is positive across the whole band and
                                # never asks the lugs for more than HOLD_LIFT
HOLD_SCREW_R = 23.0             # the two M2.5, above and below the eye
HOLD_TAB = (10.0, 15.0, 27.0)   # lug: wide, and from/to off the eye centre
HOLD_TIE_Z, RING_TIE = 31.0, (7.0, 2.4)         # the strain relief, on the
                                # LOWER lug only - which is why the two lugs
                                # are different lengths and the part still
                                # serves both eyes as one STL
HOLD_NOTCH_R = 1.8              # four wire escapes through the land
HOLD_NOTCH_A = (45.0, 135.0, 225.0, 315.0)
M25_PILOT, M25_CLEAR = 1.10, 1.40       # radii, M2.5 into PLA

# ---------------------------------------------------------- the camera pod
# Every number in this first block came off forehead_casing - the part Pat
# printed and actually fitted the camera to.  Read out of that mesh on
# 1 Sep 2026.  They are measurements, not choices, and they do not get tidied:
#     window   19.0 x 19.0, r2.0 corners, straight through
#     pocket   39.0 x 39.0, r2.5 corners, 1.8 deep off the INNER face
#     screws   O2.90 on a 28 x 28 square, 3.2 from the OUTER face down to the
#              pocket floor - so they land in the board and the heads show
# All four are concentric on one centre.  The plate is 5.0 thick and that IS
# the stack: 3.2 of wall in front of the board, 1.8 of board recess behind.
CAM_T = 5.0
CAM_WIN, CAM_WIN_R = 19.0, 2.0
CAM_POCK, CAM_POCK_R, CAM_POCK_D = 39.0, 2.5, 1.8
CAM_SCREW, CAM_SCREW_R = 28.0, 1.45
CAM_BOARD = (32.0, 32.0, 1.6)   # what goes in the pocket, and its lead

# PARKED 1 Sep 2026.  The numbers above stay because they are the only
# MEASURED ones there are; everything below them was wrong and is gone:
#   - the camera is an Arducam UC-852 Rev.A, not the generic 32 x 32 board
#     with an M12 holder CAM_BOARD guesses at.  It does not drop into a plain
#     square recess, which is why the pocket is not the whole story: the TWO
#     SLOTS in the tested part are load bearing, and they were thrown away as
#     "the distance sensor" on the first pass through that mesh.
#   - and the lens under the eyes read as a mouth, which is not wanted.
# The tested shape is in the scene as ARDUCAM_Case (52.96 x 58 x 5) - the old
# forehead_casing with the camera section booleaned out.  Start from THAT
# mesh next time, slots and all, instead of rebuilding it from dimensions.

# ------------------------------------------------------------ the nod joint
# This joint had no drive path at all.  Measured 30 Aug 2026: EVERY mating
# surface in it was a plain round cylinder - r3.85 shaft in an r4 bore, at
# the yoke AND at the head, on BOTH sides.  So the servo turned DB_cplr,
# DB_cplr turned in a round hole, and the head did not move.  Nothing was
# keyed to anything: the head was not even rotationally LOCATED, it was a
# ball hanging on two slip pins.
#
# It read as working in the viewport for one reason only - build() parented
# DB_cplr to E_nod, so pose() swung the coupler along with the head.  The rig
# was asserting a fix the geometry did not have, and fits() measured the
# clearances at this joint and passed them, because clearance answers the
# same for a joint that drives and a joint that spins.  That is eye rig 01
# again in a different part: a check that cannot fail is not a check.
#
# The torque path has to CLOSE, and it closes like this:
#
#   RIGHT, the drive.  The servo case is screwed into the head.  Its spline
#   turns DB_cplr, and DB_cplr's cap is BOLTED FLAT to the yoke arm's outer
#   face with two M2.  The coupler is therefore part of the yoke - it is
#   ground - and the servo's reaction is what nods the head.  Bolts rather
#   than a key on purpose: 2.2 kg.cm on a O12 bolt circle is 21.6 N a screw,
#   nothing in M2 shear, and a plain round shank means the servo can be
#   CENTRED before the coupler is clocked.  A D would have to be clocked
#   first and centred second, which is the wrong way round on a servo.
#
#   LEFT, the idler.  DB_pivot is the mirror image: keyed to the HEAD by a D
#   section into a boss inside the shell, and free in the yoke as a plain
#   journal.  It is hollow, and one M3 runs down its axis into that boss - so
#   its only driver path is straight along -x from outside the robot, which
#   is the rule this build has kept since eye rig 01.  Its collar and its cap
#   sandwich the yoke arm with 0.3 of end float, and that is also the only
#   thing locating the head axially.  The coupler must stay FREE to slide or
#   the two fight each other over the same 0.3.
NOD_JNL = NOD_BORE / 2 - FIT_MIN        # r3.85 journal in an r4 bore
NOD_SPLINE = (YOKE_X[0] - 3.0, YOKE_X[0] - 3.0 + SV_HUB_Z)      # 55.0 .. 59.0
                                        # read off _nod_m, not typed in: the
                                        # servo's output plane and the top of
                                        # its hub.  The coupler's socket ends
                                        # at the second number and its shank
                                        # starts at the first, so the shank
                                        # can never bury itself in the case
NOD_CAP_R, NOD_CAP_T = 8.0, 3.0         # cap, outboard of the yoke arm.
                                        # 8, not 9: the arm is 14 wide,
                                        # so the cap is 1 mm proud a
                                        # side and the bolts still land
                                        # in the post rather than on air
NOD_BOLT_R = 6.0                        # M2 bolt circle radius in that cap.
                                        # 6 - 0.85 clears the r4 nod bore by
                                        # 1.15, and leaves 1.75 of cap edge
NOD_FLOAT = 0.3                         # head end float, cap to collar
NOD_KEY = 3.0                           # the D's flat, off the axis.  It
                                        # faces -y, which is UP when the head
                                        # prints face down - so the D is the
                                        # key AND it is what stops the bore's
                                        # crown drooping.  One feature, two
                                        # problems
NOD_KEY_X = (48.0, 55.0)                # the D, |x|.  7 mm of key
NOD_BOSS_R, NOD_BOSS_X = 8.0, (42.0, 55.0)      # the boss it goes into
NOD_SPOT_R, NOD_SPOT_X = 9.5, 55.0      # a FLAT spotface for the collar to
                                        # bear on.  A sphere is a hopeless
                                        # thrust face; at r9.5 the sphere is
                                        # only 55.19 out, so a floor at 55.0
                                        # cleans up into a real annulus
M2_PILOT, M2_CLEAR = 0.85, 1.25         # radii, M2 into PLA
M3_PILOT, M3_CLEAR = 1.25, 1.70         # radii, M3 into PLA

# ---------------------------------------------------------------- the yoke
# It was ONE part, and it did not print.  Measured on the built mesh, 30 Aug
# 2026: 88 mm tall standing on 135 mm2 of first layer - the O14 sleeve alone,
# nothing else touching the plate - under 6,021 mm2 of downward faces at a
# dead 90 deg.  Three stacked flat roofs (23 mm off the sleeve at z 108.5,
# 12 mm off the collar at 116, the 22 mm shelf cantilever at 119) and two
# 6 x 14 posts standing 71 mm unbraced, 11.8 : 1.  Inverting it does not
# help - 6,065 mm2, the three roofs merged into one 5,091 mm2 slab.
#
# Split three ways, and every piece prints support-free:
#
#   DB_yoke_hub   collar face down.  The O14 sleeve is gone: the collar is
#                 r30 the whole way, which is what DB_top's O62 bore allows
#                 anyway, so the first layer is O60 instead of O14.  The
#                 flange is a 45 deg frustum, not a step.  What is left is
#                 ONE unavoidable flat: the r30 -> r36 eave at z 116, 1,244
#                 mm2, and it is unavoidable because a thrust flange over a
#                 bore has to step out somewhere and r30 is the largest
#                 thing that fits through DB_top.  It is a continuous eave
#                 anchored on its inner edge with 6 mm of flange above it to
#                 recover in, not a bridge over air.
#   DB_yoke_arm   lying on its -y face.  The silhouette is a flat 14 mm
#                 prism, so there is no overhang anywhere in it - and the
#                 layers now run ALONG the plane the head's weight and the
#                 nod reaction bend it in, instead of across it.  That is
#                 the strongest orientation available for the one member
#                 carrying the head; standing it up was the weakest.  Both
#                 arms are the SAME STL, printed twice and turned 180 deg
#                 about Z - which is why every feature in _yoke_arm is
#                 symmetric in y.
#
# The joint is a tongue on the hub into a socket in the arm, with one radial
# M3 driven from the REAR - the shell/dome rib trick, for the same reason:
# on the assembled robot it is the only direction still reachable.  The head
# is what caps the heights here.  It is a sphere about the nod axis, so it
# does not move with nod at all, and the binding corner is the INBOARD one:
# at x 29 the sphere is 59.1 away, which is what puts the arm foot's roof at
# z 131 and not higher.
YOKE_COLLAR_R, YOKE_COLLAR_Z = 30.0, (104.0, 116.0)
YOKE_FLANGE_R, YOKE_FLANGE_Z = (36.0, 42.0), (116.0, 122.0)
YOKE_TONGUE_X, YOKE_TONGUE_Y, YOKE_TONGUE_Z = (30.0, 42.0), 4.0, (122.0, 128.0)
YOKE_FOOT_X, YOKE_FOOT_Z = 29.0, 131.0          # inboard end, and the roof
YOKE_W = 7.0                                    # half width, arm and post
YOKE_FIT = 0.15                                 # tongue into socket
YOKE_SCREW = (36.0, 125.0)                      # the M3, at |x| and z

# ---------------------------------------------------------------- the arms
# The arm servo used to stand with its long axis VERTICAL.  Its ears span
# 32.2 mm, the mount boss padded that to 38, and the dome only exists over
# z 66..100 - so the boss ran off both ends of the part and the case pushed
# out through the shoulder skin, where the dome has already narrowed to r 61.
# Laid on its side the servo only needs 12.2 mm of height, which the shoulder
# has in abundance, and it drops to 78 where the dome is still 88 wide.
# ARM_AZ was 82.0.  The arm root sweeps an 11.31 mm envelope about this axis
# - the jog box's corners, not the hub - and at 82 that dipped to z 70.69,
# where the dome's skin is still flaring out at r 93.14 against an arm face
# at x 91.  6 mm3 buried at EVERY angle in ARM_RANGE, which is why posing the
# arm never showed it: both bodies are symmetric about this axis, so the
# interference does not move.  Only a sweep finds it.
#
# 84.5 lifts the envelope bottom to 73.19, where the skin is at 90.01, and
# leaves 0.99 mm.  Raising the AXIS rather than slimming the arm is deliberate
# and was decided with two arms already on the printer: the arm's mesh is
# built relative to ARM_AZ and pivoted on it, so its STL is unchanged by this
# and the printed parts stay valid.  Moving the arm outboard instead does NOT
# work - the spline only reaches x 94, so an arm starting there grips nothing.
#
# The cost is that the boss now reaches z 94.5 and merges into the pan shelf
# at 92.33.  That union is checked, not assumed.
ARM_AX, ARM_AZ = 90.0, 84.5     # the shoulder face, and the arm axis
SHO_X = (66.0, 90.0)            # housing: inboard end, and the face.  24
                                # deep for a 22.7 case - 23 left 0.2 short
# SHO_R was 9.0.  The ear slot's far corners sit at y +-22.2, and at the
# slot's z extremes a 9.0 cap only reaches 22.01 - so 0.19 mm of the cut fell
# outside the boss, and since the corner is also at r 88.27 against an 88.0
# skin, it came out as a small hole on each side by the arms.  10.0 reaches
# 23.42 and covers it.  ARM_AZ - SHO_R is still 6 mm clear of the split.
SHO_Y, SHO_R = 16.0, 10.0       # obround - box +-SHO_Y, capped by SHO_R ends
SHO_SCREW, SHO_CBORE = 1.7, 4.2   # M2 into PLA, and a head recess
SHO_CBORE_X = 85.0              # head sits here, just clear of the ear at 84.8
ARM_BLADE_X = 110.0             # 15 mm outboard of the O190 waist: at 8
                                # they vanished into the silhouette
ARM_W, ARM_T, ARM_L = 28.0, 12.0, 60.0
# Anything within this radius of the arm axis has to clear the dome's flare,
# and the flare is what bit.  Measured 30 Aug 2026 by sweeping ARM_RANGE: the
# old 11.0 hub and the old +-8 root swept an 11.31 envelope - the box corners,
# not the hub - dipping to z 70.69, where the dome's skin is still at r 93.14
# against an arm face at x 91.  6 mm3 buried at EVERY angle in the range.  Not
# a swing clash: it is constant, because both are symmetric about that axis,
# so posing the arm will never show it and only a sweep finds it.
# The dome clears r 91 only above z 72.4, so the envelope has to come in to
# 9.6.  8.5 and 6.0 give 1.4 mm.
# Moving the arm outboard instead does NOT work and is worth writing down: the
# spline only reaches x 94, so an arm starting there grips nothing.  Raising
# ARM_AZ to 85 works geometrically but runs the boss into the pan shelf at
# z 92.33.  Shrinking the root is the local fix.
# REVERTED to 11.0 / 8.0 on 30 Aug 2026: two of these were already on the
# printer when the shrink went in.  The clash is the arm root against the
# DOME's flare, and the dome is not printed - so it gets fixed on the dome
# side, where plastic has not been committed yet.  Fix the part that is still
# a file, not the part that is already a solid.
ARM_HUB_R, ARM_ROOT = 11.0, 8.0
ARM_REST = -8.0
ARM_RANGE = (-20.0, 75.0)       # +ve swings FORWARD, same sign both arms
PAN_RANGE = (-80.0, 80.0)
NOD_RANGE = (-22.0, 22.0)

# ------------------------------------------------------- bought-in hardware
# Every number tagged MEASURE is a guess this file is making.  They are the
# only guesses in it, and each is one caliper reading away from being a fact.
PCB_T = 1.6
# The Pi is turned 90 deg from the first pass: its USB-C and HDMI live on one
# LONG edge, and that edge now faces the back panel so the power brick's cord
# has somewhere to go.  Ethernet and the USB-A stacks face a side, unused.
PI_XY = (85.0, 56.0)            # 85 across, 56 fore-aft, USB-C edge REARWARD
PI_Z = 12.0                     # Pi 5 PCB underside.  No UPS under it now.
PI_TALL = 17.0                  # USB-A stack above the PCB
HAT_CLR = 17.5                  # MEASURE: WM8960 PCB above the Pi PCB.  This
HAT_XY = (65.0, 56.5)           # MUST beat PI_TALL or the HAT lands on the
HAT_TALL = 10.0                 # USB stack.  fits() checks it.
SHELF_Z = (92.33, 96.33)        # pan servo ears rest ON this; screws go DOWN
PAN_TOP = 104.0                 # so the case top lands here
# The shelf's underside is a 166 mm disc arriving 26 mm up in open air -
# 17,500 mm2 of downward-facing area, and the servo seat is dead in the
# middle of it, which is exactly where a bridge sags most.  This drops the
# shelf straight down to the parting line under the servo, so the seat prints
# off the PLATE instead of off a bridge, and what is left of the shelf spans
# an anchored 68 mm gap rather than cantilevering 83 mm from the wall.
#
# Both limits are hard: y stops short of the shelf's two O26 holes at
# (0, +-38), one of which is the wire way, and x stays well inboard of the
# arm pockets, which reach x 42.7.
PED_X, PED_Y = 11.5, (-15.0, 24.0)
PED_TOP = 95.0                  # dies INSIDE the shelf's 92.33..96.33, so the
                                # union overlaps in volume and shares no face
# Waveshare 8 ohm 5W speaker set, from the datasheet, not from guessing:
# 100 x 45 x 21 with FOUR 6.5 mm mounting holes on 92 x 36 centres.  Each box
# is sealed and carries its own driver AND its own passive radiator on one
# face, so no enclosure has to be designed around them at all.
#
# 6.5 is far too big to be a screw hole and that is the point - these take a
# ZIP TIE straight through.  Every mount here is a tie, not a fastener.
SPK_BOX = (21.0, 100.0, 45.0)   # depth X, length Y, height Z
SPK_FACE = 68.0                 # the box's front face
SPK_Z = 42.0                    # centre height, in the straight barrel
SPK_DRV_D, SPK_PR_D = 38.0, 38.0
SPK_PITCH = 25.0                # driver and radiator centres, off box centre
SPK_TAB_D = 6.5                 # the speaker's own hole
SPK_TAB_AT, SPK_TAB_Z = 46.0, 18.0          # 92 apart, 36 apart

# The baffle gets a clearance hole behind each of those, plus a return slot
# inboard of it: the tie goes out through the speaker's hole, back in through
# the slot, and cinches behind the baffle.  A tie through one aligned hole is
# a loop that clamps nothing.
TIE_D = 7.0                     # round end, behind the speaker's own O6.5
TIE_SLOT_H = 3.4                # 4.8 x 1.6 tie, with room to thread by hand
TIE_OUT = 5.0                   # how far the keyhole runs OUTBOARD
TIE_EDGE = 4.0                  # material left past the end of the slot
# Two ROUND openings, not one rectangle: a rectangle wide enough for both
# cones eats the corners the tie holes have to live in.
BAFFLE_D = 42.0
PCA_XY = (62.0, 26.0)           # front, low, under the servos it drives
FAN_D, FAN_T = 30.0, 7.0
# The SHT41 reads the ROOM, so it is the one board whose position is set by
# physics rather than packing.  It goes on the chassis at the FRONT, low, in
# the intake, behind its own vent slots - as far from the Pi as the body
# allows and upstream of the fan.  On the rear panel it would have sat in the
# exhaust and reported the Pi's waste heat as room temperature.
SHT_XY = (25.5, 17.6)           # STEMMA QT outline, 1.0 x 0.7 inch
# FOUR corner holes, not two - the photo shows one at each corner and the
# first pass had a pair on one axis.  The SPACING is still MEASURE: Adafruit
# do not publish it and it is ten seconds with calipers.
SHT_HOLE = (20.3, 12.4)
SHT_MNT_Y = 58.0                # the tab it stands on, on DB_chassis
SHT_Z = (14.0, 31.6)
JACK_D, JACK_L = 11.0, 20.0     # the DC pigtail, for the Alitove
REAR_Y = (-64.0, -60.0)         # the service panel, part of DB_chassis
REAR_X, REAR_Z = 44.0, (7.0, 64.0)          # was 34, which put two thirds
                                # of the USB-C inlet behind solid panel.  The
                                # Pi's USB-C sits 11.2 mm in from the far end
                                # of its long edge, i.e. x -35.8..-26.8 here,
                                # so the window has to reach -40 and the panel
                                # has to be wider than the window.          # lands ON the chassis plate:
                                # the panel is part of DB_chassis now, so the
                                # jack, the fan and the port window all arrive
                                # already aligned to the boards behind them

TRAY_Z = (4.0, 8.0)

HEAD_PX = ("PX_ring", "PX_eye")  # ride the nod axis, not the body shell
# The speakers are SUPPOSED to come through the wall - that is what the baffle
# opening is.  Testing them against the round profile just reports the design
# working.  They get their own check instead, against the hole and the tabs.
BAFFLE_PX = ("PX_spk",)


# ----------------------------------------------------------------- shapes
def _box(bm, x0, x1, y0, y1, z0, z1):
    v = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    bmesh.ops.scale(bm, verts=v, vec=(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)))
    bmesh.ops.translate(bm, verts=v,
                        vec=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    return v


def _rodx(bm, r, x0, x1, cy, cz, segs=PILOT):
    v = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                              radius1=r, radius2=r, depth=abs(x1 - x0))["verts"]
    bmesh.ops.rotate(bm, verts=v, cent=(0, 0, 0),
                     matrix=Matrix.Rotation(math.radians(90), 3, "Y"))
    bmesh.ops.translate(bm, verts=v, vec=Vector(((x0 + x1) / 2, cy, cz)))
    return v


def _rody(bm, r, y0, y1, cx, cz, segs=PILOT):
    v = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                              radius1=r, radius2=r, depth=abs(y1 - y0))["verts"]
    bmesh.ops.rotate(bm, verts=v, cent=(0, 0, 0),
                     matrix=Matrix.Rotation(math.radians(-90), 3, "X"))
    bmesh.ops.translate(bm, verts=v, vec=Vector((cx, (y0 + y1) / 2, cz)))
    return v


def _rodz(bm, r, z0, z1, cx, cy, segs=PILOT):
    v = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                              radius1=r, radius2=r, depth=abs(z1 - z0))["verts"]
    bmesh.ops.translate(bm, verts=v, vec=Vector((cx, cy, (z0 + z1) / 2)))
    return v


def _stadz(bm, w, l, z0, z1, cx, cy, ang=0.0, segs=FINE):
    """A stadium prism on Z: `w` across, `l` end to end, long axis on +-y
    and then turned `ang` about its own centre.

    Swept as ONE convex solid, the way _dx is, and not built as a box plus
    two rods.  Three operands sharing two tangent faces is the exact shape of
    every mesh bug in this file's history - see the note in _svpocket_ops
    about what EXACT does with a pair of coincident cylinders.  A stadium is
    convex, so it can be one operand, so it is one.
    """
    r, e = w / 2.0, max(0.0, (l - w) / 2.0)
    m = max(6, segs // 2)
    prof = [(r * math.cos(math.pi * i / m), e + r * math.sin(math.pi * i / m))
            for i in range(m + 1)]
    prof += [(r * math.cos(math.pi + math.pi * i / m),
              -e + r * math.sin(math.pi + math.pi * i / m))
             for i in range(m + 1)]
    ca, sa = math.cos(ang), math.sin(ang)
    prof = [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in prof]
    a = [bm.verts.new((x, y, z0)) for x, y in prof]
    b = [bm.verts.new((x, y, z1)) for x, y in prof]
    for i in range(len(prof)):
        j = (i + 1) % len(prof)
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(list(reversed(a)))
    bm.faces.new(b)
    return a + b


def _rrecty(bm, w, h, r, y0, y1, cx, cz, segs=FINE):
    """A rounded-rectangle prism swept on Y: `w` on x, `h` on z, corner
    radius `r`.  Convex, so it is ONE operand - same reason as _stadz.

    Everything the camera needs is this shape: forehead_casing's window, its
    board pocket and the pad they sit in are all rounded rectangles cut and
    swept along the lens axis, and that axis is +y here.
    """
    a, b = w / 2.0 - r, h / 2.0 - r
    m = max(2, segs // 8)
    prof = []
    for ox, oz, a0 in ((a, b, 0.0), (-a, b, 90.0),
                       (-a, -b, 180.0), (a, -b, 270.0)):
        for i in range(m + 1):
            t = math.radians(a0 + 90.0 * i / m)
            prof.append((cx + ox + r * math.cos(t), cz + oz + r * math.sin(t)))
    lo = [bm.verts.new((x, y0, z)) for x, z in prof]
    hi = [bm.verts.new((x, y1, z)) for x, z in prof]
    for i in range(len(prof)):
        j = (i + 1) % len(prof)
        bm.faces.new((lo[i], hi[i], hi[j], lo[j]))
    bm.faces.new(list(reversed(lo)))
    bm.faces.new(hi)
    return lo + hi


def _conez(bm, r0, r1, z0, z1, cx, cy, segs=PILOT):
    """Truncated cone on Z.  r0 at z0, r1 at z1."""
    v = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                              radius1=r0, radius2=r1,
                              depth=abs(z1 - z0))["verts"]
    bmesh.ops.translate(bm, verts=v, vec=Vector((cx, cy, (z0 + z1) / 2)))
    return v


def _boxr(bm, r0, r1, half_w, z0, z1, ang):
    """A block lying along the RADIAL direction at `ang`, from r0 out to r1."""
    v = _box(bm, r0, r1, -half_w, half_w, z0, z1)
    bmesh.ops.rotate(bm, verts=v, cent=(0, 0, 0),
                     matrix=Matrix.Rotation(ang, 3, "Z"))
    return v


def _rodr(bm, r, r0, r1, ang, cz, segs=PILOT):
    """A rod lying along the RADIAL direction at `ang`, r0 to r1, at height cz.

    Every screw into the shell/dome joint is radial, and only two of the
    three angles land on an axis, so these cannot be _rodx.
    """
    v = _rodx(bm, r, r0, r1, 0.0, cz, segs)
    bmesh.ops.rotate(bm, verts=v, cent=(0, 0, 0),
                     matrix=Matrix.Rotation(ang, 3, "Z"))
    return v


def _dx(bm, r, flat, x0, x1, cy, cz, segs=FINE):
    """A rod on X with one chord taken off it, `flat` from the axis, on -y.

    The whole nod bug was a round shaft in a round bore, and a D is the
    cheapest thing that is not one: it cannot come loose the way a grub screw
    can, it needs no second part, and it prints.  The flat faces -y because
    that is UP when the head prints face down, so the same feature that keys
    the pivot is also what stops the bore's crown drooping.

    Built as a swept profile rather than as (cylinder minus box), because
    every one of these is a boolean operand already and handing EXACT one
    less thing to do at a glancing angle is worth the twenty lines.
    """
    phi = math.asin(max(-1.0, min(1.0, flat / r)))
    n = max(8, segs)
    prof = [(cy + r * math.sin(t), cz + r * math.cos(t))
            for t in (-phi + (math.pi + 2 * phi) * i / n for i in range(n + 1))]
    a = [bm.verts.new((x0, y, z)) for y, z in prof]
    b = [bm.verts.new((x1, y, z)) for y, z in prof]
    for i in range(n):
        bm.faces.new((a[i], a[i + 1], b[i + 1], b[i]))
    bm.faces.new((a[n], a[0], b[0], b[n]))      # the flat
    bm.faces.new(list(reversed(a)))
    bm.faces.new(b)
    return a + b


def _ball(bm, r, cx, cy, cz, segs=64):
    v = bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=segs // 2,
                                  radius=r)["verts"]
    bmesh.ops.translate(bm, verts=v, vec=Vector((cx, cy, cz)))
    return v


def _revolve(bm, prof, segs=SEGS):
    """Lathe `prof` [(r, z), ...] about Z, capping both ends with a fan.

    Caps get a centre vertex instead of one n-gon: a 64-gon survives
    recalc_face_normals fine, but the EXACT boolean solver is happier with
    triangles and these shells are nothing but booleans."""
    rings = [[bm.verts.new((r * math.cos(2 * math.pi * i / segs),
                            r * math.sin(2 * math.pi * i / segs), z))
              for i in range(segs)] for r, z in prof]
    for a, b in zip(rings, rings[1:]):
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((a[i], a[j], b[j], b[i]))
    for ring, z, up in ((rings[0], prof[0][1], False),
                        (rings[-1], prof[-1][1], True)):
        c = bm.verts.new((0.0, 0.0, z))
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((c, ring[i], ring[j]) if up else (c, ring[j], ring[i]))


def _frame_m(shaft, body):
    """Orientation with local z on `shaft` and local x on `body`."""
    z = Vector(shaft).normalized()
    x = Vector(body)
    x = (x - z * x.dot(z)).normalized()
    return Matrix((x, z.cross(x), z)).transposed().to_4x4()


def _sv_m(p, shaft, body):
    return Matrix.Translation(Vector(p)) @ _frame_m(shaft, body)


def _servo(bm, m, fit=0.0):
    """Case, ears and hub as one overlapping solid, placed by `m`."""
    v = _box(bm, SV_BODY_X[0] - fit, SV_BODY_X[1] + fit,
             SV_BODY_Y[0] - fit, SV_BODY_Y[1] + fit,
             SV_BODY_Z[0] - fit, SV_BODY_Z[1])
    v += _box(bm, SV_EAR_X[0] - fit, SV_EAR_X[1] + fit,
              SV_BODY_Y[0] - fit, SV_BODY_Y[1] + fit,
              SV_EAR_Z[0] - fit, SV_EAR_Z[1] + fit)
    if fit == 0.0:
        v += _rodz(bm, SV_HUB_D / 2, 0.0, SV_HUB_Z, 0.0, 0.0)
    bmesh.ops.transform(bm, matrix=m, verts=v)


# ------------------------------------------------------------ scene plumbing
def _mat(name, rgba, rough=0.5, emit=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    if b:
        b.inputs["Base Color"].default_value = rgba
        b.inputs["Roughness"].default_value = rough
        for k in ("Emission Color", "Emission"):
            if k in b.inputs:
                b.inputs[k].default_value = rgba
        if "Emission Strength" in b.inputs:
            b.inputs["Emission Strength"].default_value = emit
    m.diffuse_color = rgba
    return m


def _dejunk(bm, name, frac=1e-3):
    """Delete shells the solver left floating loose inside the part.

    A DIFFERENCE that passes clean through thin material sometimes comes back
    with the cut cylinder's own wall as a separate closed shell.  Four were
    adrift in the dome - two in the pan shelf, two in the right shoulder -
    each one exactly where a servo screw goes, and none of them shows up
    until the part is sliced.  Nothing under `frac` of the biggest shell by
    bounding box is a feature of a 190 mm robot.
    """
    seen, isl = set(), []
    for v in bm.verts:
        if v in seen:
            continue
        stack, grp = [v], []
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            grp.append(x)
            for e in x.link_edges:
                o = e.other_vert(x)
                if o not in seen:
                    stack.append(o)
        isl.append(grp)
    if len(isl) < 2:
        return 0

    def vol(g):
        c = [v.co for v in g]
        return ((max(v.x for v in c) - min(v.x for v in c) + 0.1)
                * (max(v.y for v in c) - min(v.y for v in c) + 0.1)
                * (max(v.z for v in c) - min(v.z for v in c) + 0.1))

    big = max(vol(g) for g in isl)
    junk = [v for g in isl if vol(g) < big * frac for v in g]
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
        print("   %s: dropped %d loose verts of boolean junk" % (name, len(junk)))
    return len(junk)


def _seal(bm, name):
    """Close any boundary loop left in a finished part.

    A part with a boundary edge is not a solid, and every part in this file
    gets printed.  These are nearly always slivers: EXACT drops a facet where
    two surfaces meet at a glancing angle, and five of them have been sitting
    in the shell's floor since long before the joint went in - one per intake
    hole, 0.2 mm wide, invisible in the viewport and fatal to a slicer.

    It reports the BIGGEST loop it closed on purpose.  Sealing a 3-edge
    sliver is a repair; sealing a 24-edge loop means something upstream tore
    a real hole and the seal is hiding it.  Watch that number.
    """
    bnd = [e for e in bm.edges if len(e.link_faces) < 2]
    if not bnd:
        return 0
    bset = set(bnd); seen = set(); big = 0
    for e in bnd:
        if e in seen:
            continue
        stack, n = [e], 0
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            n += 1
            for v in x.verts:
                for e2 in v.link_edges:
                    if e2 in bset and e2 not in seen:
                        stack.append(e2)
        big = max(big, n)
    made = len(bmesh.ops.holes_fill(bm, edges=bnd, sides=0).get("faces", []))
    left = sum(1 for e in bm.edges if len(e.link_faces) < 2)
    print("   %s: sealed %d face(s) over %d open edges, biggest loop %d, %d left"
          % (name, made, len(bnd), big, left))
    return made


def _obj(name, coll, parts, cuts=(), mat=None, loc=(0, 0, 0),
         add=(), bore=()):
    """Four phases, in order: union `parts`, subtract `cuts`, union `add`,
    subtract `bore`.

    The last two exist because a hollow shell is (outer - inner), and ANY
    internal feature unioned before that subtraction is deleted by it.  The
    dome's servo shelf was in `parts` for a week and never once appeared in
    the mesh; the shelf ribs survived only where they poked out through the
    skin, which is exactly what they looked like.  Internal geometry goes in
    `add`, after the cavity has been cut.
    """
    obs = []
    ops = ([None] + ["UNION"] * (len(parts) - 1)
           + ["DIFFERENCE"] * len(cuts) + ["UNION"] * len(add)
           + ["DIFFERENCE"] * len(bore))
    for i, fn in enumerate(list(parts) + list(cuts) + list(add) + list(bore)):
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
        m.operation = ops[i]
        # use_self stays ON.  It was turned off on 30 Aug 2026 on the
        # reasoning that no operand self-intersects any more - which is true,
        # and was still wrong.  The flag is not only about the operand: EXACT
        # uses it for the ACCUMULATED base mesh too, and the base goes through
        # states no single operand describes.  Measured cost of turning it
        # off: DB_dome came back with 379 open edges and DB_shell with 45.
        # The speed came from collapsing the modifier_apply loop below, not
        # from this.  Leave it alone.
        m.use_self = True
        m.use_hole_tolerant = True
    # Evaluate the stack ONCE rather than calling modifier_apply per modifier.
    # The boolean work is identical - same modifiers, same order - but every
    # bpy.ops call was forcing a full depsgraph update of the whole scene and
    # an undo push, and DB_chassis alone stacks 55 of them.
    if len(obs) > 1:
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(base.evaluated_get(dg))
        base.modifiers.clear()
        stale, base.data = base.data, me
        bpy.data.meshes.remove(stale)
    for o in obs[1:]:
        bpy.data.objects.remove(o, do_unlink=True)
    bm = bmesh.new()
    bm.from_mesh(base.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-4, edges=bm.edges[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    _dejunk(bm, name)
    if _seal(bm, name):
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(base.data)
    bm.free()
    base.name = base.data.name = name
    if mat:
        base.data.materials.clear()
        base.data.materials.append(mat)
    piv = Vector(loc)
    for v in base.data.vertices:
        v.co -= piv
    base.location = piv
    return base


def _prof_r(prof, z):
    """Radius of a lathed profile at height z, or None if z is off the ends."""
    if z < prof[0][1] - 1e-9 or z > prof[-1][1] + 1e-9:
        return None
    for (r0, z0), (r1, z1) in zip(prof, prof[1:]):
        if z0 - 1e-9 <= z <= z1 + 1e-9:
            if abs(z1 - z0) < 1e-9:
                return max(r0, r1)
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return prof[-1][0]


# ------------------------------------------------------------------- parts
def _shell(coll, mat):
    """Body, floor to the parting line.  Side grilles, rear access, feet."""
    cuts = [lambda bm: _revolve(bm, INNER_PROF),
            lambda bm: _box(bm, -120, 120, -120, 120, SPLIT_Z, 260)]
    # side-firing speaker grilles, five slots a side
    # Each speaker fires through its own opening; its corner tabs bolt to
    # DB_chassis behind, not to the shell, so the shell carries no load.
    for sx in (1, -1):
        cuts.append(lambda bm, s=sx: _box(
            bm, s * (SPK_FACE + 3.0), s * 140.0, -54.0, 54.0,
            SPK_Z - 25.0, SPK_Z + 25.0))
    # rear access: ports, cables, and the fan's exhaust all leave here
    cuts.append(lambda bm: _box(bm, -46, 46, -120, -58, 12, 60))
    # The other half of the chassis mount: clearance and a counterbore, so
    # the screw head finishes flush with the floor and the robot still sits
    # flat on the desk.
    for a in CH_MOUNT_A:
        cx, cy = CH_MOUNT_AT * math.cos(a), CH_MOUNT_AT * math.sin(a)
        cuts.append(lambda bm, x=cx, y=cy: _rodz(bm, 1.7, -1.0, WALL + 1.0,
                                                 x, y))
        cuts.append(lambda bm, x=cx, y=cy: _rodz(bm, 3.2, -1.0, 1.6, x, y))
    # Front intake, straight onto the SHT41.  These are the slots that make
    # the humidity reading mean anything: without them it measures the inside
    # of a sealed box with a Pi 5 in it.
    for i in range(5):
        zc = 13.0 + i * 5.0
        cuts.append(lambda bm, z=zc: _box(bm, -26.0, 26.0, 60.0, 140.0,
                                          z - 1.5, z + 1.5))
    # intake ring under the foot, so the fan has somewhere to pull from
    for i in range(8):
        a = 2 * math.pi * i / 8
        cuts.append(lambda bm, a=a: _rodz(
            bm, 4.0, -1.0, 5.0, 34 * math.cos(a), 34 * math.sin(a)))
    # The dome joint.  These go in `add`, not `parts`: the pads stand 4 mm
    # proud of SPLIT_Z and the parting cut in `cuts` would eat them whole.
    add, bore = [], []
    for a in JOIN_A:
        # The rib and the pad are deliberately DIFFERENT on every axis:
        # 82..93 vs 83..90 radially, half-width 9 vs 8, and z 52..64 vs
        # 60..70.  Measured on 30 Aug 2026 with the shell built both ways -
        # ribs on, 85 open edges; ribs off, 15 - and every one of those 70
        # traced to the two boxes sharing faces.  Both started at r 82 and
        # both used JOIN_W, so over their overlap the two side faces and the
        # inner face were exactly coplanar, and EXACT drops coplanar unions.
        # Overlap them in VOLUME, never on a face.
        add.append(lambda bm, a=a: _boxr(bm, JOIN_R[0], 93.0, JOIN_W,
                                         JOIN_Z[0], SPLIT_Z - 2.0, a))
        add.append(lambda bm, a=a: _boxr(bm, JOIN_R[0] + 1.0, JOIN_R[1],
                                         JOIN_W - 1.0, SPLIT_Z - 6.0,
                                         JOIN_Z[1], a))
        bore.append(lambda bm, a=a: _rodr(bm, JOIN_PILOT / 2, JOIN_R[0] - 1.0,
                                          JOIN_R[1] + 1.0, a, JOIN_SCREW_Z))
    return _obj("DB_shell", coll, [lambda bm: _revolve(bm, BODY_PROF)], cuts,
                mat, add=add, bore=bore)


def _dome(coll, mat):
    """Shoulder.  Carries the pan shelf and both arm housings.

    Note the phase each feature is in: the skin is parts/cuts, everything
    INSIDE it is add/bore.  Put the shelf in `parts` and the cavity cut eats
    it whole.
    """
    parts = [lambda bm: _revolve(bm, BODY_PROF)]
    cuts = [lambda bm: _revolve(bm, INNER_PROF),
            lambda bm: _box(bm, -140, 140, -140, 140, -20, SPLIT_Z),
            lambda bm: _box(bm, -140, 140, -140, 140, BODY_TOP, 260)]

    # The shelf is a CONE, not a disc: over its 4 mm of height the wall loses
    # 3.4 mm of radius, so a flat disc meets it on one thin line and a cone
    # meets it all the way round.
    add = [lambda bm: _conez(bm, 84.0, 80.6, SHELF_Z[0], SHELF_Z[1], 0, 0,
                             SEGS),
           # pedestal: carries the servo seat down to the parting line
           lambda bm: _box(bm, -PED_X, PED_X, PED_Y[0], PED_Y[1],
                           SPLIT_Z, PED_TOP)]
    for sx in (1, -1):
        add.append(lambda bm, s=sx: _box(
            bm, s * SHO_X[0], s * SHO_X[1], -SHO_Y, SHO_Y,
            ARM_AZ - SHO_R, ARM_AZ + SHO_R))
        for ey in (-SHO_Y, SHO_Y):
            add.append(lambda bm, s=sx, y=ey: _rodx(
                bm, SHO_R, s * SHO_X[0], s * SHO_X[1], y, ARM_AZ, FINE))
        # Skirt: carries the housing straight down to the parting line.  The
        # boss used to stop at ARM_AZ - SHO_R and leave a 613 mm2 ceiling in
        # open air on each side, plus the whole lower half of both end caps.
        # Standing it on the plate is the natural fix - no support, no bridge.
        #
        # Inset 2 and 1 mm in x and 1 mm in y from the housing ON PURPOSE, so
        # it overlaps the boss in VOLUME and shares no face with it.  Two
        # boxes that share a face is exactly what shredded the join ribs.
        # Below z 72 this is inside the body's own flare, so the inset costs
        # nothing anyone can see.
        add.append(lambda bm, s=sx: _box(
            bm, s * (SHO_X[0] + 2.0), s * (SHO_X[1] - 1.0),
            -(SHO_Y + SHO_R - 1.0), SHO_Y + SHO_R - 1.0,
            SPLIT_Z, ARM_AZ + 2.0))

    bore = _svpocket_ops(_sv_m((0, 0, PAN_TOP), (0, 0, 1), (0, 1, 0)), "-y")
    # Both stay O26.  DB_dome IS PRINTED - see "feeding a SERVO up" - and
    # neither of these holes may grow, so the servo does not use them.  It
    # goes up the pan servo's own pocket instead, which is already 37.4 x
    # 24.0 through this same shelf and costs the part nothing.
    bore += [lambda bm: _rodz(bm, 13.0, SHELF_Z[0] - 1, SHELF_Z[1] + 1, 0, 38,
                              FINE),
             lambda bm: _rodz(bm, 13.0, SHELF_Z[0] - 1, SHELF_Z[1] + 1, 0, -38,
                              FINE)]
    # Arm servos slide into the housings from inboard and are held by two
    # SCREWS, not by anything springy: M2 in from the shoulder face, head
    # counterbored below the surface, through the ear, into solid housing
    # behind it.  The arm hub covers both heads.
    for sx in (1, -1):
        bore += _svpocket_ops(_arm_m(sx), "-z")
        bore.append(lambda bm, s=sx: _rodx(          # spline / hub clearance
            bm, 5.5, s * 80.0, s * 104.0, 0.0, ARM_AZ, FINE))
        # The O1.7 pilot is NOT cut here.  _svpocket_ops already drills both,
        # on this exact axis, and runs them out past the face to |x| 104.
        # Cutting them a second time put two cylinders of identical diameter
        # and different segment counts - 20 from the pocket, 48 from FINE -
        # on one axis, 0.01 mm apart.  EXACT turned that pair into ten
        # zero-width slivers and dropped them, which is the torn triangle in
        # the shoulder skin, and left both pilots behind as floating tubes.
        for hy in SV_HOLE_X:
            bore.append(lambda bm, s=sx, y=hy: _rodx(
                bm, SHO_CBORE / 2, s * SHO_CBORE_X, s * 94.0, y, ARM_AZ,
                FINE))
    # the other half of the shell joint: clearance and a head recess, so the
    # three screws finish below the skin rather than standing off it
    for a in JOIN_A:
        bore.append(lambda bm, a=a: _rodr(bm, JOIN_CLEAR / 2, 89.0, 96.0, a,
                                          JOIN_SCREW_Z, FINE))
        bore.append(lambda bm, a=a: _rodr(bm, JOIN_CBORE / 2, 92.0, 96.0, a,
                                          JOIN_SCREW_Z, FINE))
    return _obj("DB_dome", coll, parts, cuts, mat, add=add, bore=bore)


def _top(coll, mat):
    """The flat bearing ring.  Prints flat, so the face the head rides on is
    a first layer rather than a stack of curved perimeters."""
    parts = [lambda bm: _rodz(bm, TOP_R[1], TOP_Z[0], TOP_Z[1], 0, 0, SEGS),
             lambda bm: _rodz(bm, 48.5, TOP_Z[0] - 3.0, TOP_Z[0], 0, 0, SEGS)]
    cuts = [lambda bm: _rodz(bm, TOP_R[0], TOP_Z[0] - 4, TOP_Z[1] + 1, 0, 0,
                             SEGS)]
    # 90/210/330, not 30/150/270.  The wire slot below owns the rear now and
    # a fixing at 270 sat in the middle of it.
    for i in range(3):
        a = 2 * math.pi * i / 3 + math.pi / 2
        cuts.append(lambda bm, a=a: _rodz(
            bm, 1.6, TOP_Z[0] - 4, TOP_Z[1] + 1,
            44 * math.cos(a), 44 * math.sin(a)))
    # the wire way, as an arc slot: nine overlapping O5 holes over 80 deg
    for a in WIRE_A:
        cuts.append(lambda bm, a=a: _rodz(
            bm, WIRE_D / 2, TOP_Z[0] - 4, TOP_Z[1] + 1,
            WIRE_R * math.cos(a), WIRE_R * math.sin(a), FINE))
    # and the throat out to the rim at 270, through the spigot as well as the
    # plate.  THIS is why DB_top does not have to pass a servo: it is the one
    # part on the run that is fitted after the servo is already up, so it
    # threads onto the lead sideways.  Its free band is 6.5 mm - r 42 for the
    # yoke flange's sweep, r 48.5 for the spigot - and a servo needs 14.2, so
    # there was never a version of this plate with a hole big enough in it.
    cuts.append(lambda bm: _boxr(bm, WIRE_R - WIRE_D / 2, TOP_R[1] + 2.0,
                                 WIRE_THROAT / 2, TOP_Z[0] - 4, TOP_Z[1] + 1,
                                 math.radians(270.0)))
    return _obj("DB_top", coll, parts, cuts, mat)


def _yoke_hub(coll, mat):
    """Collar, thrust flange, and the two tongues the arms socket onto.

    The flange is the thrust bearing: it, not the servo, is what the head
    stands on.  Printed collar face down, and every face in it is either
    vertical, upward, or at 45 - except the r30 -> r36 eave at z 116, which
    is the bearing step itself and cannot go anywhere else.
    """
    cr, cz = YOKE_COLLAR_R, YOKE_COLLAR_Z
    fr, fz = YOKE_FLANGE_R, YOKE_FLANGE_Z
    parts = [lambda bm: _rodz(bm, cr, cz[0], cz[1], 0, 0, SEGS),
             # 45 deg, not a step: fr[1] - fr[0] == fz[1] - fz[0] and that
             # is not a coincidence, it is the constraint
             lambda bm: _conez(bm, fr[0], fr[1], fz[0], fz[1], 0, 0, SEGS)]
    for sx in (1, -1):
        parts.append(lambda bm, s=sx: _box(
            bm, s * YOKE_TONGUE_X[0], s * YOKE_TONGUE_X[1],
            -YOKE_TONGUE_Y, YOKE_TONGUE_Y, YOKE_TONGUE_Z[0],
            YOKE_TONGUE_Z[1]))
    cuts = [lambda bm: _rodz(bm, HORN_BORE / 2, cz[0] - 1.0, TOP_Z[0], 0, 0)]
    for sx in (1, -1):
        # the M3 threads the tongue right through - 8 mm of it
        cuts.append(lambda bm, s=sx: _rody(
            bm, M3_PILOT, -YOKE_TONGUE_Y - 1.0, YOKE_TONGUE_Y + 1.0,
            s * YOKE_SCREW[0], YOKE_SCREW[1]))
    return _obj("DB_yoke_hub", coll, parts, cuts, mat, loc=(0, 0, TOP_Z[0]))


def _yoke_arm(coll, mat, sx, tag):
    """One arm: socket, foot, post, nod hub.  Printed lying on its -y face.

    Every feature here is symmetric in y and antisymmetric in x, so the two
    arms are the SAME STL turned 180 deg about Z.  That is worth keeping:
    the M3 has to enter from the rear on BOTH sides, which a blind hole on
    one face would break the moment the part is turned round.  It is a
    through hole for that reason and no other.
    """
    parts = [lambda bm: _box(bm, sx * YOKE_FOOT_X, sx * YOKE_X[1],
                             -YOKE_W, YOKE_W, YOKE_FLANGE_Z[1], YOKE_FOOT_Z),
             # no round hub round the bore.  There was one, r10, and it
             # made the part 20 mm wide where everything else is 14 - so
             # printed on its -y face the arm stood on the hub's TANGENT
             # LINE, 15.7 mm2 of it, with 586 mm2 of slab hanging 3 mm off
             # the plate.  The post already covers the bore (z 131..192
             # against a bore at 182 +-4) and both M2 (182 +-6), so the hub
             # was meat for its own sake and it cost the whole first layer.
             lambda bm: _box(bm, sx * YOKE_X[0], sx * YOKE_X[1],
                             -YOKE_W, YOKE_W, YOKE_FOOT_Z, HEAD_Z + 10.0)]
    cuts = [
        # the socket, open downward so the arm drops onto the tongue
        lambda bm: _box(bm, sx * (YOKE_TONGUE_X[0] - YOKE_FIT),
                        sx * (YOKE_TONGUE_X[1] + 1.0),
                        -YOKE_TONGUE_Y - YOKE_FIT, YOKE_TONGUE_Y + YOKE_FIT,
                        YOKE_TONGUE_Z[0] - YOKE_FIT,
                        YOKE_TONGUE_Z[1] + YOKE_FIT),
        lambda bm: _rody(bm, M3_CLEAR, -YOKE_W - 1.0, YOKE_W + 1.0,
                         sx * YOKE_SCREW[0], YOKE_SCREW[1]),
        # the nod bore stays ROUND on both sides.  The head has to turn on
        # this one and the pivot has to turn in that one
        lambda bm: _rodx(bm, NOD_BORE / 2, sx * 40.0, sx * 80.0, 0.0, HEAD_Z,
                         FINE)]
    # and the two M2 the coupler's cap bolts to.  They are the drive: this
    # is the only thing in the robot stopping the nod servo spinning its own
    # coupler in a round hole.  Through, so the same STL serves both arms
    for dz in (NOD_BOLT_R, -NOD_BOLT_R):
        cuts.append(lambda bm, d=dz: _rodx(
            bm, M2_PILOT, sx * (YOKE_X[0] - 1.0), sx * (YOKE_X[1] + 1.0),
            0.0, HEAD_Z + d))
    return _obj("DB_yoke_arm_" + tag, coll, parts, cuts, mat,
                loc=(0, 0, TOP_Z[0]))


def _head(coll, mat):
    """A sphere, opened at the face.  The O92 opening IS the access hole -
    there is no head split, and the nod servo goes in through it."""
    parts = [lambda bm: _ball(bm, HEAD_R, 0, 0, HEAD_Z),
             lambda bm: _svboss(bm, _nod_m())]
    cuts = [lambda bm: _ball(bm, HEAD_R - HEAD_WALL, 0, 0, HEAD_Z)]
    cuts += _svpocket_ops(_nod_m(), "+x")
    cuts += [
        lambda bm: _box(bm, -70, 70, FACE_Y, 90, HEAD_Z - 70, HEAD_Z + 70),
        # rebate the face plate in flush
        lambda bm: _rody(bm, FACE_REBATE_R, FACE_Y - FACE_T, FACE_Y + 1,
                         0.0, HEAD_Z, SEGS),
        # The servo's door, out of the underside at the REAR and in line
        # with the slot in DB_top, so the whole run is one drop behind the
        # robot.  This was O12 and it was a wire hole; the servo it feeds
        # could not get through it, so the head could only ever be built
        # around a lead that was unplugged at the other end.  Long axis
        # RADIAL: 14 mm wide seen from behind, not 29.
        lambda bm: _stadz(bm, PASS_W, PASS_L, HEAD_Z - HEAD_R - 6.0,
                          HEAD_Z - 34.0, 0.0, PASS_HEAD_Y)]
    for sx in (1, -1):
        cuts.append(lambda bm, s=sx: _rodx(
            bm, NOD_BORE / 2, s * 40.0, s * 70.0, 0.0, HEAD_Z, FINE))
    # a FLAT for the pivot's collar to thrust against.  The sphere at r9.5 is
    # 55.19 out, so a floor at 55.0 cleans up into a real annulus instead of
    # a collar balancing on a curve
    cuts.append(lambda bm: _rodx(bm, NOD_SPOT_R, -(NOD_SPOT_X + 2.0),
                                 -NOD_SPOT_X, 0.0, HEAD_Z, FINE))
    # AFTER the cavity, or the cavity deletes it: the boss the pivot keys
    # into and the M3 threads into.  r8 at x 55 is 55.6 from the head centre,
    # so it is buried in the wall rather than poking out of it
    add = [lambda bm: _rodx(bm, NOD_BOSS_R, -NOD_BOSS_X[1], -NOD_BOSS_X[0],
                            0.0, HEAD_Z, FINE)]
    bore = [lambda bm: _dx(bm, NOD_BORE / 2, NOD_KEY + FIT_MIN,
                           -(NOD_SPOT_X + 1.0), -(NOD_KEY_X[0] - 0.5),
                           0.0, HEAD_Z),
            lambda bm: _rodx(bm, M3_PILOT, -(NOD_KEY_X[0] + 1.0),
                             -(NOD_BOSS_X[0] - 1.0), 0.0, HEAD_Z)]
    return _obj("DB_head", coll, parts, cuts, mat, loc=(0, 0, HEAD_Z),
                add=add, bore=bore)


def _face(coll, mat, lens):
    """Face plate: one bore per eye, RING_T deep exactly, opened out to
    RING_APER in front so the LEDs are not looking at a wall.

    The ring goes in from BEHIND, LEDs first, and lands flush with the
    plate's own back face - flush, so DB_eye_holder has a flat to sit on.
    What it actually seats against is the shoulder RING_APER leaves, and
    what holds it there is the holder's land.
    """
    bore_r = (RING_OD + 2 * RING_FIT) / 2
    floor_y = FACE_Y - FACE_DIFF                    # the shoulder's back
    back_y = FACE_Y - FACE_T                        # the plate's back face

    parts = [lambda bm: _rody(bm, 45.9, back_y, FACE_Y, 0.0, HEAD_Z, SEGS)]
    cuts, bore = [], []
    for s_ in (1, -1):
        ex, ez = s_ * EYE_X, HEAD_Z + EYE_Z
        # the ring's bore, and then the eye itself, straight through
        cuts.append(lambda bm, ex=ex, ez=ez: _rody(
            bm, bore_r, back_y - 1.0, floor_y, ex, ez, SEGS))
        cuts.append(lambda bm, ex=ex, ez=ez: _rody(
            bm, RING_APER / 2, floor_y - 0.5, FACE_Y + 1.0, ex, ez, SEGS))
        # a scallop in the bore wall.  It clocks the ring - there is one way
        # round it will sit - and it is the escape for a lead that comes off
        # the OUTER edge of the pads rather than the inner.  Mirrored, so
        # both eyes send their leads inboard and down, toward the wire pass.
        t = math.radians(270.0 - s_ * RING_LEAD_A)
        cuts.append(lambda bm, ex=ex, ez=ez, t=t: _rody(
            bm, RING_LEAD_R, back_y - 1.0, floor_y,
            ex + bore_r * math.cos(t), ez + bore_r * math.sin(t), FINE))
        # the two M2.5 the holder pulls down on.  BLIND from the back: 3.5 of
        # thread with 1.0 of plate left in front, so nothing shows through
        for dz in (HOLD_SCREW_R, -HOLD_SCREW_R):
            bore.append(lambda bm, ex=ex, ez=ez, dz=dz: _rody(
                bm, M25_PILOT, back_y - 1.0, back_y + 3.5, ex, ez + dz))
    return _obj("DB_face", coll, parts, cuts, mat, loc=(0, 0, HEAD_Z),
                bore=bore)


def _eye_proxies(coll, lens):
    """The ring where it ends up, and the light that comes out of the hole."""
    for s_, tag in ((1, "L"), (-1, "R")):
        ex, ez = s_ * EYE_X, HEAD_Z + EYE_Z
        _obj("PX_eye_" + tag, coll,
             [lambda bm, ex=ex, ez=ez: _rody(
                 bm, RING_APER / 2 - 0.2, RING_SEAT + RING_T - 0.2,
                 RING_SEAT + RING_T, ex, ez, SEGS)], [], lens,
             loc=(0, 0, HEAD_Z))
        _obj("PX_ring_" + tag, coll,
             [lambda bm, ex=ex, ez=ez: _rody(
                 bm, RING_OD / 2, RING_SEAT, RING_SEAT + RING_T, ex, ez,
                 SEGS)],
             [lambda bm, ex=ex, ez=ez: _rody(
                 bm, RING_ID / 2, RING_SEAT - 1.0, RING_SEAT + RING_T + 1.0,
                 ex, ez, SEGS)], lens, loc=(0, 0, HEAD_Z))


def _eye_holder(coll, mat, s_, tag):
    """The annulus that holds one ring in.

    Two M2.5 into the face plate, a land standing HOLD_LIFT proud that bears
    on the PCB's outer rim all the way round, and an open middle the lead
    goes straight out through.  The land is what preloads the ring, seals the
    light and takes up the ring-to-ring thickness scatter; the body never
    touches the PCB at all.

    Both eyes take the SAME STL - the long lug goes down on each.
    """
    ex, ez = s_ * EYE_X, HEAD_Z + EYE_Z
    y0 = FACE_BACK - HOLD_T
    tw, t0, t1 = HOLD_TAB
    parts = [lambda bm: _rody(bm, HOLD_OD / 2, y0, FACE_BACK, ex, ez, SEGS),
             # the land runs BACK into the body rather than sitting on its
             # face - flush it shares a whole plane with it and the part
             # comes back non-manifold, which is what the lugs get right
             lambda bm: _rody(bm, HOLD_LAND_OD / 2, FACE_BACK - HOLD_T / 2,
                              FACE_BACK + HOLD_LIFT, ex, ez, SEGS)]
    # the lugs.  They OVERLAP the disc from t0 rather than butting onto it -
    # butting them on flush shares a whole face plane, which is what makes
    # a part come back non-manifold - see the note in _stadz
    for dz, end in ((1, t1), (-1, HOLD_TIE_Z)):
        parts.append(lambda bm, dz=dz, end=end: _box(
            bm, ex - tw / 2, ex + tw / 2, y0, FACE_BACK,
            ez + dz * t0, ez + dz * end))
    cuts = [lambda bm: _rody(bm, HOLD_ID / 2, y0 - 1.0,
                             FACE_BACK + HOLD_LIFT + 1.0, ex, ez, SEGS)]
    for dz in (HOLD_SCREW_R, -HOLD_SCREW_R):
        cuts.append(lambda bm, dz=dz: _rody(
            bm, M25_CLEAR, y0 - 1.0, FACE_BACK + 1.0, ex, ez + dz))
    # the wire escapes, cut through the land at its own mid radius
    mid = (HOLD_ID + HOLD_LAND_OD) / 4
    for a in HOLD_NOTCH_A:
        t = math.radians(a)
        cuts.append(lambda bm, t=t: _rody(
            bm, HOLD_NOTCH_R, FACE_BACK - 0.5, FACE_BACK + HOLD_LIFT + 0.5,
            ex + mid * math.cos(t), ez + mid * math.sin(t), FINE))
    # and the tie, on the long lug: the pull comes off four solder joints
    tiw, tih = RING_TIE
    cuts.append(lambda bm: _box(
        bm, ex - tiw / 2, ex + tiw / 2, y0 - 1.0, FACE_BACK + 1.0,
        ez - (HOLD_TIE_Z + HOLD_SCREW_R) / 2 - tih / 2,
        ez - (HOLD_TIE_Z + HOLD_SCREW_R) / 2 + tih / 2))
    return _obj("DB_eye_holder_" + tag, coll, parts, cuts, mat,
                loc=(0, 0, HEAD_Z))


def _arm(coll, mat, sx, tag):
    """Hub on the spline, a jog outboard, then the blade.  The jog is the
    whole reason the arm can hang past the O160 waist without touching it."""
    bx = ARM_BLADE_X * sx
    parts = [lambda bm: _rodx(bm, ARM_HUB_R, sx * (ARM_AX + 1.0),
                              sx * (ARM_AX + 11.0), 0.0, ARM_AZ, FINE),
             lambda bm: _box(bm, sx * (ARM_AX + 1.0), bx + sx * ARM_T / 2,
                             -ARM_ROOT, ARM_ROOT, ARM_AZ - ARM_ROOT,
                             ARM_AZ + ARM_ROOT),
             lambda bm: _box(bm, bx - ARM_T / 2, bx + ARM_T / 2,
                             -ARM_W / 2, ARM_W / 2,
                             ARM_AZ - ARM_L, ARM_AZ),
             lambda bm: _rodx(bm, ARM_W / 2, bx - ARM_T / 2, bx + ARM_T / 2,
                              0.0, ARM_AZ - ARM_L, FINE)]
    cuts = [lambda bm: _rodx(bm, HORN_BORE / 2, sx * (ARM_AX - 2.0),
                             sx * (ARM_AX + 8.0), 0.0, ARM_AZ)]
    return _obj("DB_arm_" + tag, coll, parts, cuts, mat,
                loc=(sx * ARM_AX, 0, ARM_AZ))


def _svboss(bm, m, pad=3.0, back=7.0, front=1.0):
    """Solid meat around a servo pocket, so the two screws have something to
    thread into.  Without it an ear screw goes through 3 mm of shell and out
    the other side."""
    v = _box(bm, SV_EAR_X[0] - pad, SV_EAR_X[1] + pad,
             SV_BODY_Y[0] - pad, SV_BODY_Y[1] + pad,
             SV_EAR_Z[0] - back, front)
    bmesh.ops.transform(bm, matrix=m, verts=v)


def _svpocket_ops(m, open_dir, reach=SV_REACH, through=1.0):
    """A servo holder with ONE open side.

    Two nested boxes, not one, and the difference matters:

      case  the case footprint, run from below the base right THROUGH the
            mounting face.  The old single box stopped at the ear plane, so
            the top 4.8 mm of the case - exactly the part sitting in the
            shoulder face - was never cut, and the servo was buried in solid
            material.  Point-sampling put 15% of the case inside the dome.
      ear   the ear footprint, and ONLY across the 2.5 mm the ears occupy.
            The old box used the ear width over the whole depth, which left
            a 32 mm slot where a 22.8 mm case goes and gave the ears nothing
            to seat against.

    What is left between them is the step the ears bear on, and the material
    the two screws thread into.  Both boxes sweep out of `open_dir` so the
    servo still slides in.

    The pilots run along local z because that is the only axis an MG90S is
    ever pierced on.  Wherever local z points is where the driver has to come
    from - worth reading off each caller before anything prints.

    Returns a LIST of operands, one convex solid each.  These used to be drawn
    into ONE bmesh, which handed EXACT a self-intersecting difference operand.
    It coped with the outline and silently no-opped inside it: measured on 30
    Aug 2026, the top 4.7 mm of EVERY servo case was still solid material -
    the arms in the dome and the nod in the head - and so were both ear tips.
    That is the same 4.8 mm the note above says was fixed; cutting the box to
    `through` fixed the box and not the solver.  Separate convex cuts are the
    same volume and there is nothing left for it to get wrong.
    """
    # `reach` was 70, and 70 is not a clearance, it is a hole saw.  The slot
    # only has to open into the cavity the servo is fed from - 24 clears the
    # arm boss's inboard face at |x| 66 with 11 to spare, and reaches the head
    # face opening for the nod.  At 70 the pan pocket ran out to x 76.7 at
    # z 105, where the dome's skin is at r 67.8, and tore a 9 mm hole in the
    # shoulder.  It was invisible until the merged operand above was split:
    # EXACT had been silently no-opping most of this cut, so nobody found out
    # the sweep was wrong.  A fix that works reveals what the bug was hiding.
    i = {"+x": 1, "-x": 0, "+y": 3, "-y": 2, "+z": 5, "-z": 4}[open_dir]
    case = [SV_BODY_X[0] - SV_FIT, SV_BODY_X[1] + SV_FIT,
            SV_BODY_Y[0] - SV_FIT, SV_BODY_Y[1] + SV_FIT,
            SV_BODY_Z[0] - SV_FIT, through]
    ear = [SV_EAR_X[0] - SV_FIT, SV_EAR_X[1] + SV_FIT,
           SV_BODY_Y[0] - SV_FIT, SV_BODY_Y[1] + SV_FIT,
           SV_EAR_Z[0] - SV_FIT, SV_EAR_Z[1] + SV_FIT]
    ops = []
    for box in (case, ear):
        b = list(box)
        b[i] += reach if i % 2 else -reach
        ops.append(lambda bm, b=b: bmesh.ops.transform(
            bm, matrix=m, verts=_box(bm, *b)))
    for hx in SV_HOLE_X:
        ops.append(lambda bm, hx=hx: bmesh.ops.transform(
            bm, matrix=m, verts=_rodz(bm, 1.7 / 2, 14.0,
                                      SV_EAR_Z[0] - 8.0, hx, 0.0)))
    return ops


def _arm_m(sx):
    """Shaft outward along x, case laid down with its long axis fore-aft."""
    return _sv_m((sx * ARM_AX, 0, ARM_AZ), (sx, 0, 0), (0, 1, 0))


def _nod_m():
    return _sv_m((YOKE_X[0] - 3.0, 0, HEAD_Z), (1, 0, 0), (0, 1, 0))


def _proxies(coll, pcb, metal, spk):
    """Every bought part, at the size it actually is.  These exist so fits()
    has something to be wrong about."""
    out = []
    B = lambda n, xy, z0, z1, c, mt, cy=0.0: out.append(_obj(
        n, coll, [lambda bm: _box(bm, c - xy[0] / 2, c + xy[0] / 2,
                                  cy - xy[1] / 2, cy + xy[1] / 2, z0, z1)],
        [], mt))
    B("PX_pi5", PI_XY, PI_Z, PI_Z + PCB_T + PI_TALL, 0.0, pcb)
    B("PX_wm8960", HAT_XY, PI_Z + PCB_T + HAT_CLR,
      PI_Z + PCB_T + HAT_CLR + PCB_T + HAT_TALL, 0.0, pcb, cy=-10.0)
    out.append(_obj("PX_pca9685", coll,
                    [lambda bm: _box(bm, -PCA_XY[0] / 2, PCA_XY[0] / 2,
                                     34.0, 34.0 + PCA_XY[1], 40.0, 44.0)],
                    [], pcb))
    out.append(_obj("PX_sht41", coll,
                    [lambda bm: _box(bm, -SHT_XY[0] / 2, SHT_XY[0] / 2,
                                     SHT_MNT_Y + 3.0, SHT_MNT_Y + 8.0,
                                     SHT_Z[0], SHT_Z[1])],
                    [], pcb))
    out.append(_obj("PX_fan", coll,
                    [lambda bm: _rody(bm, FAN_D / 2, REAR_Y[1],
                                      REAR_Y[1] + FAN_T, 0.0, 47.0)],
                    [], metal))
    out.append(_obj("PX_jack", coll,
                    [lambda bm: _rody(bm, JACK_D / 2, REAR_Y[0],
                                      REAR_Y[0] + JACK_L, 24.0, 44.0)],
                    [], metal))
    for s, tag in ((1, "L"), (-1, "R")):
        d, ln, h = SPK_BOX
        x0, x1 = s * (SPK_FACE - d), s * SPK_FACE
        parts = [lambda bm, a=x0, b=x1: _box(
            bm, a, b, -ln / 2, ln / 2, SPK_Z - h / 2, SPK_Z + h / 2)]
        cuts = []
        for ty in (-1, 1):                      # its four 6.5 mm holes
            for tz in (-1, 1):
                cuts.append(lambda bm, a=x0, b=x1, ty=ty, tz=tz: _rodx(
                    bm, SPK_TAB_D / 2, a - 1.0, b + 1.0,
                    ty * SPK_TAB_AT, SPK_Z + tz * SPK_TAB_Z, FINE))
        parts.append(lambda bm, b=x1, s=s: _rodx(       # the domed driver
            bm, SPK_DRV_D / 2, b, b + s * 2.5, SPK_PITCH, SPK_Z, SEGS))
        parts.append(lambda bm, b=x1, s=s: _rodx(       # the passive radiator
            bm, SPK_PR_D / 2, b, b + s * 1.2, -SPK_PITCH, SPK_Z, SEGS))
        out.append(_obj("PX_spk_" + tag, coll, parts, cuts, spk))
    return out


def _servos(coll, mat):
    """The four MG90S, where they actually sit."""
    frames = {
        "SV_pan": _sv_m((0, 0, PAN_TOP), (0, 0, 1), (0, 1, 0)),
        "SV_nod": _nod_m(),
        "SV_arm_L": _arm_m(1),
        "SV_arm_R": _arm_m(-1),
    }
    return {n: _obj(n, coll, [lambda bm, m=m: _servo(bm, m)], [], mat)
            for n, m in frames.items()}


# ------------------------------------------------------------ the chassis
# The plate sits DIRECTLY on the shell's 3 mm floor, so the chassis needs no
# feet of its own - flat on the bench before the shell exists, flat on the
# floor after.  Everything that stands on the plate starts at CH_Z[0] and
# passes through it, so the union has real overlap to work with instead of
# two coincident faces.
CH_R, CH_Z = 76.0, (3.0, 7.0)
# The mounting interface is printed in NOW rather than discovered later: four
# bosses on a O120 bolt circle, pilot-drilled from below.  The shell's floor
# gets clearance and a counterbore on the same circle and four M3 come UP from
# underneath - the one direction on this robot that is always reachable, with
# no board, servo or speaker anywhere near the driver.
CH_MOUNT_R, CH_MOUNT_AT = 4.5, 60.0
CH_MOUNT_TOP, CH_MOUNT_PILOT = 16.0, 2.5   # 13 mm of thread for an M3
CH_MOUNT_A = [math.radians(45 + 90 * i) for i in range(4)]

BAF_X = (SPK_FACE, SPK_FACE + 3.0)          # the wall the speakers tie to
BAF_Y, BAF_TOP = 55.0, 68.0     # 5.5 mm of wall past each tie hole
BAF_FOOT_Y, BAF_FOOT_Z = 44.0, 16.0         # narrower where the body tucks in

# Pi 5 mounting holes: 58 x 49, 3.5 in from each edge.  They are NOT centred
# on the 85 mm axis - 23.5 mm of board hangs past the second pair, which is
# the USB-A and Ethernet end.  Getting this backwards mirrors the whole stack.
PI_HOLE_X = (-PI_XY[0] / 2 + 3.5, -PI_XY[0] / 2 + 3.5 + 58.0)
PI_HOLE_Y = (-24.5, 24.5)
POST_D, POST_PILOT = 7.0, 2.2   # M2.5 self-tapper into printed PLA
# Datasheet, not guessed: 2.20 x 0.75 inch centres, 2.5 mm holes.
PCA_HOLE = ((-27.94, 27.94), (37.5, 56.55))


def _chassis(coll, mat):
    """Pi 5, PCA9685, SHT41 and both speaker boxes on one printed frame that
    stands on its own, plus the rear service panel fused into it.

    This is the part that gets printed and populated BEFORE any shell exists,
    so every fault in it is found with a screwdriver rather than after a
    two-hour shell print.  It is also the only structural part: the speakers
    tie to its baffles and the shell just wraps it.
    """
    z0 = CH_Z[0]
    parts = [lambda bm: _rodz(bm, CH_R, z0, CH_Z[1], 0, 0, SEGS)]
    for a in CH_MOUNT_A:
        parts.append(lambda bm, a=a: _rodz(
            bm, CH_MOUNT_R, z0, CH_MOUNT_TOP,
            CH_MOUNT_AT * math.cos(a), CH_MOUNT_AT * math.sin(a), FINE))
    for hx in PI_HOLE_X:
        for hy in PI_HOLE_Y:
            parts.append(lambda bm, x=hx, y=hy: _rodz(
                bm, POST_D / 2, z0, PI_Z, x, y, FINE))
    for hx in PCA_HOLE[0]:
        for hy in PCA_HOLE[1]:
            parts.append(lambda bm, x=hx, y=hy: _rodz(
                bm, POST_D / 2, z0, 40.0, x, y, FINE))
    for sx in (1, -1):
        parts.append(lambda bm, s=sx: _box(
            bm, s * BAF_X[0], s * BAF_X[1], -BAF_Y, BAF_Y,
            BAF_FOOT_Z, BAF_TOP))
        parts.append(lambda bm, s=sx: _box(
            bm, s * BAF_X[0], s * BAF_X[1], -BAF_FOOT_Y, BAF_FOOT_Y,
            z0, BAF_FOOT_Z))
        for gy in (-30.0, 30.0):            # gussets, or the baffle waves
            parts.append(lambda bm, s=sx, y=gy: _box(
                bm, s * 54.0, s * BAF_X[0], y - 1.5, y + 1.5, z0, 30.0))
    # SHT41 stands on its own tab at the front, facing out through the
    # shell's intake slots.
    parts.append(lambda bm: _box(bm, -16.0, 16.0, SHT_MNT_Y, SHT_MNT_Y + 3.0,
                                 z0, SHT_Z[1] + 2.5))
    # the rear service panel, fused in rather than screwed on
    parts.append(lambda bm: _box(bm, -REAR_X, REAR_X, REAR_Y[0], REAR_Y[1],
                                 z0, REAR_Z[1]))

    cuts = []
    for a in CH_MOUNT_A:
        cuts.append(lambda bm, a=a: _rodz(
            bm, CH_MOUNT_PILOT / 2, z0 - 1.0, CH_MOUNT_TOP - 2.0,
            CH_MOUNT_AT * math.cos(a), CH_MOUNT_AT * math.sin(a)))
    for hx in PI_HOLE_X:
        for hy in PI_HOLE_Y:
            cuts.append(lambda bm, x=hx, y=hy: _rodz(
                bm, POST_PILOT / 2, CH_Z[1], PI_Z + 1.0, x, y))
    for hx in PCA_HOLE[0]:
        for hy in PCA_HOLE[1]:
            cuts.append(lambda bm, x=hx, y=hy: _rodz(
                bm, POST_PILOT / 2, CH_Z[1], 41.0, x, y))
    for sx in (1, -1):
        for ty in (-1, 1):
            cuts.append(lambda bm, s=sx, ty=ty: _rodx(   # driver / radiator
                bm, BAFFLE_D / 2, s * 55.0, s * 90.0,
                ty * SPK_PITCH, SPK_Z, SEGS))
            for tz in (-1, 1):
                cuts.append(lambda bm, s=sx, ty=ty, tz=tz: _rodx(
                    bm, TIE_D / 2, s * 55.0, s * 90.0,
                    ty * SPK_TAB_AT, SPK_Z + tz * SPK_TAB_Z, FINE))
                # the keyhole runs OUTBOARD, away from the opening: inboard
                # it clipped the O42 rim and left a jagged edge
                cuts.append(lambda bm, s=sx, ty=ty, tz=tz: _box(
                    bm, s * 55.0, s * 90.0,
                    min(ty * SPK_TAB_AT, ty * (SPK_TAB_AT + TIE_OUT)),
                    max(ty * SPK_TAB_AT, ty * (SPK_TAB_AT + TIE_OUT)),
                    SPK_Z + tz * SPK_TAB_Z - TIE_SLOT_H / 2,
                    SPK_Z + tz * SPK_TAB_Z + TIE_SLOT_H / 2))
    for hx in (-SHT_HOLE[0] / 2, SHT_HOLE[0] / 2):
        for hz in (-SHT_HOLE[1] / 2, SHT_HOLE[1] / 2):
            cuts.append(lambda bm, x=hx, z=hz: _rody(
                bm, 1.1, SHT_MNT_Y - 1.0, SHT_MNT_Y + 4.0, x,
                (SHT_Z[0] + SHT_Z[1]) / 2 + z))
    cuts.append(lambda bm: _box(bm, -40.0, 20.0, REAR_Y[0] - 1, REAR_Y[1] + 1,
                                12.0, 32.0))                # USB-C and HDMI
    cuts.append(lambda bm: _rody(bm, FAN_D / 2 - 1.0, REAR_Y[0] - 1,
                                 REAR_Y[1] + 1, 0.0, 47.0, FINE))
    cuts.append(lambda bm: _rody(bm, (JACK_D + 0.3) / 2, REAR_Y[0] - 1,
                                 REAR_Y[1] + 1, 24.0, 44.0, FINE))
    for i in range(4):
        cuts.append(lambda bm, i=i: _rody(
            bm, 1.3, REAR_Y[0] - 1, REAR_Y[1] + 1,
            12.0 * (1 if i < 2 else -1), 47.0 + 12.0 * (1 if i % 2 else -1)))
    # loom: everything crosses the plate somewhere, so give it one big slot
    cuts.append(lambda bm: _box(bm, -20.0, 20.0, -52.0, -38.0,
                                z0 - 1, CH_Z[1] + 1))
    return _obj("DB_chassis", coll, parts, cuts, mat)


def build():
    for ob in list(bpy.data.objects):
        if ob.name.startswith(("DB_", "PX_", "SV_", "E_")):
            bpy.data.objects.remove(ob, do_unlink=True)
    old = bpy.data.collections.get(COLL)
    if old:
        bpy.data.collections.remove(old)
    coll = bpy.data.collections.new(COLL)
    bpy.context.scene.collection.children.link(coll)

    shell = _mat("DB_shell_mat", (0.82, 0.83, 0.85, 1.0), 0.42)
    accent = _mat("DB_accent_mat", (0.16, 0.17, 0.20, 1.0), 0.35)
    pcb = _mat("PX_pcb_mat", (0.05, 0.32, 0.16, 1.0), 0.65)
    metal = _mat("PX_metal_mat", (0.42, 0.44, 0.48, 1.0), 0.30)
    spk = _mat("PX_spk_mat", (0.10, 0.10, 0.11, 1.0), 0.80)
    lens = _mat("PX_lens_mat", (0.25, 0.75, 1.00, 1.0), 0.20, emit=6.0)
    horn = _mat("SV_mat", (0.10, 0.10, 0.12, 1.0), 0.55)

    _shell(coll, shell)
    _dome(coll, shell)
    _top(coll, accent)
    yoke = [_yoke_hub(coll, accent)]
    yoke += [_yoke_arm(coll, accent, s, t) for s, t in ((1, "L"), (-1, "R"))]
    head = _head(coll, shell)
    face = _face(coll, shell, lens)
    _eye_proxies(coll, lens)
    hold = {t: _eye_holder(coll, accent, s, t)
            for s, t in ((1, "L"), (-1, "R"))}
    _chassis(coll, accent)
    arms = {t: _arm(coll, shell, s, t) for s, t in ((1, "L"), (-1, "R"))}
    sv = _servos(coll, horn)
    _proxies(coll, pcb, metal, spk)

    # the two nod inserts, which is where eye rig 01 died - and where this
    # build had quietly repeated it until 30 Aug 2026
    #
    # DRIVE.  Round shank all the way, so the servo can be centred before
    # anything is clocked, and the cap takes two M2 into the yoke arm's outer
    # face.  Those two screws ARE the key.  Note what is not here: no
    # shoulder bearing on the head.  The head has no material on this axis to
    # bear on - _svpocket_ops opens it from x 31.7 right out to 56 - so the
    # right-hand support is the servo's own output bearing, carrying half of
    # 120 g RADIALLY.  That is a different load from the pan thrust this file
    # refuses to put on a servo, and 0.6 N radial is inside an MG90S bushing.
    cplr = _obj("DB_cplr", coll,
                [lambda bm: _rodx(bm, NOD_JNL, NOD_SPLINE[0], YOKE_X[1],
                                  0.0, HEAD_Z, FINE),
                 lambda bm: _rodx(bm, NOD_CAP_R, YOKE_X[1],
                                  YOKE_X[1] + NOD_CAP_T, 0.0, HEAD_Z, FINE)],
                [lambda bm: _rodx(bm, HORN_BORE / 2, NOD_SPLINE[0] - 1.0,
                                  NOD_SPLINE[1], 0.0, HEAD_Z)]
                + [lambda bm, d=d: _rodx(bm, M2_CLEAR, YOKE_X[1] - 1.0,
                                         YOKE_X[1] + NOD_CAP_T + 1.0,
                                         0.0, HEAD_Z + d)
                   for d in (NOD_BOLT_R, -NOD_BOLT_R)],
                accent, loc=(0, 0, HEAD_Z))
    # IDLER.  Journal in the yoke, D into the head, collar and cap sandwiching
    # the arm with NOD_FLOAT between them - which is the only thing locating
    # the head along its own axis.  Hollow: one M3 x 25 down the middle, and
    # the only way to reach its head is from outside along -x.
    _obj("DB_pivot", coll,
         [lambda bm: _rodx(bm, NOD_JNL, -YOKE_X[1],
                           -(YOKE_X[0] - NOD_FLOAT), 0.0, HEAD_Z, FINE),
          lambda bm: _rodx(bm, NOD_CAP_R, -(YOKE_X[0] - NOD_FLOAT),
                           -NOD_SPOT_X, 0.0, HEAD_Z, FINE),
          lambda bm: _dx(bm, NOD_JNL, NOD_KEY, -NOD_KEY_X[1], -NOD_KEY_X[0],
                         0.0, HEAD_Z),
          lambda bm: _rodx(bm, NOD_CAP_R, -(YOKE_X[1] + NOD_CAP_T),
                           -YOKE_X[1], 0.0, HEAD_Z, FINE)],
         [lambda bm: _rodx(bm, M3_CLEAR, -(YOKE_X[1] + NOD_CAP_T + 1.0),
                           -(NOD_KEY_X[0] - 0.5), 0.0, HEAD_Z)],
         accent, loc=(0, 0, HEAD_Z))

    # ------------------------------------------------------------- rigging
    def empty(name, loc):
        e = bpy.data.objects.new(name, None)
        e.empty_display_type, e.empty_display_size = "PLAIN_AXES", 18.0
        e.location = loc
        coll.objects.link(e)
        return e

    e_pan = empty("E_pan", (0, 0, TOP_Z[0]))
    e_nod = empty("E_nod", (0, 0, HEAD_Z))
    e_arm = {t: empty("E_arm_" + t, (s * ARM_AX, 0, ARM_AZ))
             for s, t in ((1, "L"), (-1, "R"))}
    # matrix_world is stale until the depsgraph runs, and every parent
    # inverse below is read off it.  Without this the head, the yoke and both
    # arms each get their own offset applied TWICE and fly off the body.
    bpy.context.view_layer.update()

    def kid(ob, parent):
        ob.parent = parent
        ob.matrix_parent_inverse = parent.matrix_world.inverted()

    # DB_cplr belongs to E_PAN, not E_nod.  It is bolted to the yoke arm, so
    # it is ground - it does NOT turn with the head, and parenting it as if
    # it did is what made the old joint look like it worked.  If this line
    # ever moves back under e_nod, the drive-path check below stops meaning
    # anything, because the rig will be asserting the answer again.
    for ob in yoke + [e_nod, cplr]:
        kid(ob, e_pan)
    for ob in (head, face, hold["L"], hold["R"], sv["SV_nod"],
               bpy.data.objects["PX_ring_L"],
               bpy.data.objects["PX_ring_R"], bpy.data.objects["PX_eye_L"],
               bpy.data.objects["PX_eye_R"],
               bpy.data.objects["DB_pivot"]):
        kid(ob, e_nod)
    for t in "LR":
        kid(arms[t], e_arm[t])

    n = smooth(coll)
    pose()
    print("built %d objects in %s, %d shaded at %.0f deg"
          % (len(coll.objects), COLL, n, SMOOTH_ANGLE))
    return fits()


def smooth(coll=None, angle=SMOOTH_ANGLE):
    thresh = math.radians(angle)
    obs = [o for o in (coll or bpy.data.collections[COLL]).objects
           if o.type == "MESH"]
    for ob in obs:
        me = ob.data
        bm = bmesh.new()
        bm.from_mesh(me)
        for e in bm.edges:
            e.smooth = not (len(e.link_faces) == 2
                            and e.calc_face_angle(0.0) > thresh)
        bm.to_mesh(me)
        bm.free()
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        me.update()
    return len(obs)


def pose(pan=0.0, nod=0.0, arm_l=ARM_REST, arm_r=ARM_REST):
    """Angles in degrees.  +pan looks left, +nod looks UP, +arm swings
    FORWARD on both sides (so the two servos want opposite horn mappings -
    that belongs in the node, not in the geometry)."""
    for name, axis, deg in (("E_pan", 2, pan), ("E_nod", 0, -nod),
                            ("E_arm_L", 0, arm_l), ("E_arm_R", 0, arm_r)):
        e = bpy.data.objects.get(name)
        if e:
            r = [0.0, 0.0, 0.0]
            r[axis] = math.radians(deg)
            e.rotation_euler = r
    bpy.context.view_layer.update()


# -------------------------------------------------------------------- gate
def _aabb(ob):
    ws = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(v.x for v in ws), min(v.y for v in ws),
                    min(v.z for v in ws))),
            Vector((max(v.x for v in ws), max(v.y for v in ws),
                    max(v.z for v in ws))))


def _corners(lo, hi):
    return [Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y)
            for z in (lo.z, hi.z)]


# ------------------------------------------------------- print orientation
# The axis that points UP off the plate, and which way, for every part that
# gets printed.  This is not a preference and it is not a slicer setting: it
# is the orientation each part was DRAWN for, and every "no overhang here"
# claim in this file is a claim about one of these.  The census below holds
# them to it.
#
# It exists because the yoke's numbers were a surprise.  Nothing in fits()
# could see that DB_yoke stood 88 mm tall on 135 mm2 of first layer under
# 6,021 mm2 of flat roof - clearance checks cannot, clash checks cannot, and
# the part had been "support-free, base down" in the header docstring for
# weeks.  A claim no check can fail is a claim.
# (axis, sign, budget).  A budget of None means REPORT ONLY - it is a part
# whose orientation this file has never actually verified against a slice,
# and a gate that fails on a number nobody has checked is a gate people learn
# to ignore.  The four parts with a budget are the ones designed here, where
# "no overhang" is a claim being made on purpose and is worth failing on.
PRINT_ORIENT = {
    "DB_chassis":    ("z", +1, None),   # header: base down.  The tray and the
                                        # baffles are BRIDGES on purpose
    "DB_shell":      ("z", +1, None),   # header: base down, 40 deg at the foot
    "DB_dome":       ("z", +1, None),   # header: base down.  The pan shelf is
                                        # a deliberate 68 mm bridge - see PED
    "DB_top":        ("z", +1, None),   # header: flat, bearing face first
    "DB_yoke_hub":   ("z", +1, 1400.0),  # the bearing eave, and nothing else
    "DB_yoke_arm_L": ("y", +1, 150.0),   # on its -y face, one STL for both
    "DB_yoke_arm_R": ("y", +1, 150.0),
    "DB_cplr":       ("x", -1, 50.0),    # cap on the plate
    "DB_pivot":      ("x", +1, 200.0),   # cap on the plate.  The collar's
                                         # annulus is 148 of that and it is
                                         # anchored right round its inner edge
}
SPIN_A = 20.0                   # degrees, and it has to beat the joint's
                                # own backlash: 0.15 of fit on r3.85 is 2.2
                                # deg of free travel, so 6 deg read a keyed
                                # D as free and nearly shipped it
SPIN_OK = 0.2                   # mm3.  Not CLASH_OK: that one is sized for
                                # two flat faces meeting, and a shallow D
                                # bites in single-figure mm3
OVERHANG_A = 45.0               # steeper than this off the plate is free
OVERHANG_ROOF = 75.0            # and shallower than this is a ROOF, which is
                                # the number that actually decides a print.
                                # Splitting the two is not cosmetic: a 3 mm
                                # shell wall leaning at 24 deg reads as
                                # 36,000 mm2 of "overhang" and prints fine,
                                # because each layer still lands on 85% of
                                # the one below.  The yoke's 6,021 mm2 were
                                # at a dead 90 and landed on nothing
OVERHANG_WARN = 250.0           # mm2 of ROOF worth mentioning


def _overhang(ob, axis, sign, ok=OVERHANG_A):
    """Downward-facing face area in this part's own print orientation.

    Returns (roof, steep, first-layer contact, worst angle).

    Two numbers, because one is not enough.  ROOF is area shallower than
    OVERHANG_ROOF - the flat and near-flat stuff that lands on air.  STEEP is
    45..75, which is a shell wall leaning over, and a shell wall at 24 deg
    still puts each layer on 85% of the one below.  Reporting them together
    called the dome unprintable and the yoke fine, which is backwards.

    The first-layer number is the other half of the answer on its own: 6,021
    mm2 of roof is survivable on a wide base and fatal on 135 mm2 of it, and
    DB_yoke was the second.
    """
    up = {"x": Vector((sign, 0, 0)), "y": Vector((0, sign, 0)),
          "z": Vector((0, 0, sign))}[axis]
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.transform(ob.matrix_world)
    h = [v.co.dot(up) for v in bm.verts]
    floor = min(h)
    roof, steep, plate, worst = 0.0, 0.0, 0.0, 0.0
    for f in bm.faces:
        d = f.normal.dot(up)
        if d >= -1e-6:
            continue
        a = f.calc_area()
        if sum(v.co.dot(up) for v in f.verts) / len(f.verts) - floor < 0.05:
            plate += a
            continue
        # 90 is a flat roof, 0 is a vertical wall
        over = 90.0 - math.degrees(math.acos(min(1.0, -d)))
        if over > OVERHANG_ROOF:
            roof += a
            worst = max(worst, over)
        elif over > ok:
            steep += a
            worst = max(worst, over)
    bm.free()
    return roof, steep, plate, worst


# ------------------------------------------------------------- drive path
def _spins(name, mate, deg=SPIN_A):
    """Turn `name` about the nod axis and see whether `mate` stops it.

    This is the eye-rig-01 lesson written as a function.  A round shaft in a
    round bore measures a PERFECT clearance and transmits nothing, and no
    amount of measuring gaps will ever say so - the joint that drives and the
    joint that spins have identical margins.  Interference under rotation is
    the difference between them, so that is what gets measured.

    >0 mm3 means the pair is keyed.  0 means it spins.  Which of those is
    right depends on the pair, so this reports and fits() judges.
    """
    a, b = bpy.data.objects.get(name), bpy.data.objects.get(mate)
    if not a or not b:
        return None
    tmp = bpy.data.objects.new("_spin_tmp", a.data.copy())
    bpy.context.scene.collection.objects.link(tmp)
    tmp.matrix_world = (Matrix.Translation((0, 0, HEAD_Z))
                        @ Matrix.Rotation(math.radians(deg), 4, "X")
                        @ Matrix.Translation((0, 0, -HEAD_Z))
                        @ a.matrix_world)
    bpy.context.view_layer.update()
    try:
        v = _ivol(tmp, b)
    finally:
        d = tmp.data
        bpy.data.objects.remove(tmp, do_unlink=True)
        bpy.data.meshes.remove(d)
    return v


# --------------------------------------------------------------- clashes
# The analytic wall test only ever looked at BOUGHT parts against the body
# PROFILE.  It could not see one printed part cutting into another, and it
# explicitly excused the speakers because they fire through an opening - so
# the one thing it could not check is the one thing that went wrong.
#
# This measures actual intersection VOLUME between real meshes.  Volume, not
# a yes/no: 0.2 mm3 is two surfaces touching and 900 mm3 is a corner buried
# in a wall, and those want different reactions.
CLASH_PAIRS = (
    ("DB_chassis", "DB_shell"), ("DB_chassis", "DB_dome"),
    ("PX_spk_L", "DB_shell"), ("PX_spk_L", "DB_dome"),
    ("PX_spk_R", "DB_shell"), ("PX_spk_R", "DB_dome"),
    ("PX_pi5", "DB_chassis"), ("PX_pca9685", "DB_chassis"),
    ("PX_wm8960", "DB_chassis"), ("PX_sht41", "DB_chassis"),
    ("DB_shell", "DB_dome"), ("DB_top", "DB_dome"),
    # the split yoke and the joint it drives.  Every one of these should be
    # ZERO: the tongue is a slip fit in the socket, the arm foot only RESTS
    # on the flange, and each insert is a slip fit in everything it touches.
    # A number here is a part that cannot be assembled, not a tight fit.
    ("DB_yoke_hub", "DB_top"), ("DB_yoke_hub", "DB_head"),
    ("DB_yoke_hub", "DB_yoke_arm_L"), ("DB_yoke_hub", "DB_yoke_arm_R"),
    ("DB_yoke_arm_L", "DB_head"), ("DB_yoke_arm_R", "DB_head"),
    ("DB_cplr", "DB_head"), ("DB_cplr", "DB_yoke_arm_L"),
    ("DB_pivot", "DB_head"), ("DB_pivot", "DB_yoke_arm_R"),
    # everything that lives behind the face plate.  These were built without
    # being in this list, so nothing was measuring them - and the head is the
    # most crowded volume in the robot: a O91.8 plate with two O37.6 bores,
    # two clamp bars, a camera mount and a servo all inside r 53.5.
    ("DB_eye_holder_L", "DB_face"), ("DB_eye_holder_R", "DB_face"),
    ("DB_eye_holder_L", "DB_head"), ("DB_eye_holder_R", "DB_head"),
    ("DB_eye_holder_L", "DB_eye_holder_R"),
    ("DB_face", "DB_head"),
)
CLASH_OK = 2.0                  # mm3 - below this is two faces meeting


def _ivol(a, b):
    """Volume of a intersected with b, in mm3."""
    tmp = bpy.data.objects.new("_clash_tmp", a.data.copy())
    bpy.context.scene.collection.objects.link(tmp)
    tmp.matrix_world = a.matrix_world.copy()
    m = tmp.modifiers.new(type="BOOLEAN", name="i")
    m.object, m.solver, m.operation = b, "EXACT", "INTERSECT"
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(tmp.matrix_world)
    # Two parts MEETING share a face, and an EXACT intersect of coplanar
    # faces returns an open sheet whose calc_volume is meaningless - it read
    # 73.5 mm3 for the chassis plate simply resting on the shell floor, which
    # is the joint working.  A real interference has thickness in all three
    # axes; contact has none in one of them.
    if bm.verts:
        co = [v.co for v in bm.verts]
        thin = min(max(c[i] for c in co) - min(c[i] for c in co)
                   for i in range(3))
    else:
        thin = 0.0
    if thin < 0.05:
        v = 0.0
    else:
        # calc_volume on an OPEN mesh is meaningless, and an EXACT intersect
        # of two touching solids is often open.  It once reported 4582 mm3
        # inside a bounding box that only holds 2489.  Cap it at the box.
        box = 1.0
        for k in range(3):
            box *= max(c[k] for c in co) - min(c[k] for c in co)
        v = min(bm.calc_volume(signed=False), box)
    bm.free()
    bpy.data.meshes.remove(me)
    d = tmp.data
    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.meshes.remove(d)
    return v


def clashes(verbose=True):
    """Every pair in CLASH_PAIRS, by measured volume."""
    say = (lambda *a: print(*a)) if verbose else (lambda *a: None)
    hidden = [o for o in bpy.data.objects if o.hide_viewport]
    for o in hidden:
        o.hide_viewport = False
    bpy.context.view_layer.update()
    out = []
    for an, bn in CLASH_PAIRS:
        a, b = bpy.data.objects.get(an), bpy.data.objects.get(bn)
        if not a or not b:
            continue
        try:
            v = _ivol(a, b)
        except Exception as e:
            say("   ?? %s x %s: %s" % (an, bn, e))
            continue
        if v > CLASH_OK:
            out.append((v, an, bn))
        say("   %s %-12s x %-10s %9.1f mm3"
            % ("!!" if v > CLASH_OK else "  ", an, bn, v))
    for o in hidden:
        o.hide_viewport = True
    return sorted(out, reverse=True)


def fits(verbose=True):
    """Is every bought part inside the shell, and clear of every other one.

    This is deliberately NOT a mesh overlap test.  Overlap answers the same
    for 9 mm of daylight and 0.09 mm, which is exactly how eye rig 01 passed
    check() and then could not be assembled.  This reports MARGINS, signed,
    and the sign is the verdict.
    """
    bad, warn = [], []
    say = (lambda *a: print(*a)) if verbose else (lambda *a: None)
    say("\n--- packaging ------------------------------------------------")

    inner = [(r, z) for r, z in INNER_PROF if z <= BODY_TOP + 1e-6]
    for ob in sorted(bpy.data.objects, key=lambda o: o.name):
        if (not ob.name.startswith("PX_")
                or ob.name.startswith(HEAD_PX + BAFFLE_PX)):
            continue
        lo, hi = _aabb(ob)
        worst, at = 1e9, None
        for c in _corners(lo, hi):
            rr = _prof_r(inner, c.z)
            if rr is None:
                worst, at = -999.0, "z %.1f is outside the shell" % c.z
                break
            m = rr - math.hypot(c.x, c.y)
            if m < worst:
                worst, at = m, "r %.1f of %.1f at z %.1f" % (
                    math.hypot(c.x, c.y), rr, c.z)
        flag = "  " if worst >= 2.0 else ("!!" if worst < 0 else " ~")
        if worst < 0:
            bad.append("%s pokes through the shell (%s)" % (ob.name, at))
        say("%s %-14s wall margin %+7.1f   %s" % (flag, ob.name, worst, at))

    say("\n--- collisions between bought parts --------------------------")
    px = [o for o in bpy.data.objects
          if o.name.startswith(("PX_", "SV_"))
          and not o.name.startswith(HEAD_PX) and o.name != "SV_nod"]
    for i, a in enumerate(px):
        alo, ahi = _aabb(a)
        for b in px[i + 1:]:
            blo, bhi = _aabb(b)
            gaps = [max(alo[k] - bhi[k], blo[k] - ahi[k]) for k in range(3)]
            g = max(gaps)
            if g < 0:
                bad.append("%s and %s overlap by %.1f" % (a.name, b.name, -g))
                say("!! %-13s x %-13s overlap %.1f" % (a.name, b.name, -g))
    say("   %d pairs checked" % (len(px) * (len(px) - 1) // 2))

    say("\n--- the stack ------------------------------------------------")
    head_room = HAT_CLR - PI_TALL
    say("   HAT over the Pi's USB stack   %+7.1f   %s"
        % (head_room, "MEASURE HAT_CLR at the bench"))
    if head_room < 0.5:
        bad.append("WM8960 lands on the Pi's USB stack (HAT_CLR %.1f vs "
                   "PI_TALL %.1f)" % (HAT_CLR, PI_TALL))
    elif head_room < 4.0:
        warn.append("WM8960 clears the Pi's USB stack by %.1f, and HAT_CLR is "
                    "a GUESS - measure it before anything is cut" % head_room)
    hat_top = PI_Z + PCB_T + HAT_CLR + PCB_T + HAT_TALL
    say("   HAT top to the pan shelf      %+7.1f" % (SHELF_Z[0] - hat_top))
    if SHELF_Z[0] - hat_top < 3.0:
        bad.append("pan shelf sits %.1f over the WM8960 - no loom room"
                   % (SHELF_Z[0] - hat_top))

    say("\n--- speakers on the baffle ------------------------------------")
    _tie_gap = (math.hypot(SPK_TAB_AT - SPK_PITCH, SPK_TAB_Z)
                - BAFFLE_D / 2 - TIE_D / 2)
    _baf_r = math.hypot(BAF_X[1], BAF_Y)
    for label, have, need in (
            ("opening clears the cone     ", BAFFLE_D / 2, SPK_DRV_D / 2 + 1),
            ("tie hole to that opening    ", _tie_gap, 2.0),
            ("wall past the keyhole end   ",
             BAF_Y - SPK_TAB_AT - TIE_OUT, TIE_EDGE),
            ("keyhole slot fits a tie     ", TIE_SLOT_H, 2.0),
            ("keyhole runs AWAY from hole ",
             math.hypot(SPK_TAB_AT + TIE_OUT - SPK_PITCH, SPK_TAB_Z)
             - BAFFLE_D / 2 - TIE_SLOT_H / 2, 2.0),
            ("baffle corner inside barrel ",
             _prof_r(INNER_PROF, SPK_Z) - _baf_r, 1.0),
            ("baffle FOOT inside the barrel",
             _prof_r(INNER_PROF, CH_Z[0])
             - math.hypot(BAF_X[1], BAF_FOOT_Y), 1.0),
            ("speaker back to the Pi      ",
             SPK_FACE - SPK_BOX[0] - PI_XY[0] / 2, 3.0),
            ("box inside the baffle       ", BAF_TOP - CH_Z[0],
             SPK_BOX[2] + 4.0)):
        say("   %s%+7.1f" % (label, have - need))
        if have - need < 0:
            bad.append("speaker: %s short by %.1f" % (label.strip(),
                                                      need - have))

    say("\n--- the shoulder ---------------------------------------------")
    _ear = (abs(SV_EAR_X[0]), SV_EAR_X[1])
    for label, have, need in (
            ("housing covers the ears     ", SHO_Y + SHO_R,
             max(abs(h) for h in SV_HOLE_X) + 4.0),
            ("housing covers the case     ", SHO_R, SV_BODY_Y[1] + 2.0),
            ("housing deep enough for it  ", SHO_X[1] - SHO_X[0],
             abs(SV_BODY_Z[0]) + 0.5),
            ("top of housing under the rim", BODY_TOP - (ARM_AZ + SHO_R),
             2.0),
            ("bottom of it over the split ", (ARM_AZ - SHO_R) - SPLIT_Z, 0.0),
            ("thread behind the ear       ",
             SHO_X[1] + SV_EAR_Z[0] - 58.0, 8.0),
            ("shelf rim into the wall     ",
             84.0 - _prof_r(INNER_PROF, SHELF_Z[0]), 0.5),
            ("shelf rim inside the skin   ",
             _prof_r(BODY_PROF, SHELF_Z[1]) - 80.6, 0.5),
            ("shelf clear of the housing  ",
             (SHELF_Z[0]) - (ARM_AZ + SHO_R), 0.0)):
        say("   %s%+7.1f" % (label, have - need))
        if have - need < 0:
            bad.append("shoulder: %s short by %.1f"
                       % (label.strip(), need - have))

    say("\n--- chassis to shell -----------------------------------------")
    _mb = [(CH_MOUNT_AT * math.cos(a), CH_MOUNT_AT * math.sin(a))
           for a in CH_MOUNT_A]
    _worst, _at = 1e9, ""
    for ob in bpy.data.objects:
        if not ob.name.startswith(("PX_", "SV_")) or ob.name.startswith(
                HEAD_PX) or ob.name == "SV_nod":
            continue
        lo, hi = _aabb(ob)
        if hi.z < CH_Z[0] or lo.z > CH_MOUNT_TOP:
            continue
        for cx, cy in _mb:
            d = max(lo.x - cx, cx - hi.x, lo.y - cy, cy - hi.y)
            if d - CH_MOUNT_R < _worst:
                _worst, _at = d - CH_MOUNT_R, ob.name
    say("   mount boss to the nearest part%+7.1f   %s" % (_worst, _at))
    if _worst < 1.0:
        bad.append("a chassis mount boss fouls %s by %.1f" % (_at, -_worst))
    say("   bolt circle O%.0f, %d x M3 up from under the floor"
        % (CH_MOUNT_AT * 2, len(_mb)))

    say("\n--- motion ---------------------------------------------------")
    # The head is a sphere about the nod axis, so nothing under it moves with
    # nod at all - which makes the standoff a fixed number, and the only
    # honest way to get it is the worst CORNER rather than the head's bottom
    # pole.  The pole is at z 126 and clears everything below it; the corner
    # that binds is the arm foot's INBOARD top, out at |x| 29.
    worst, at = 1e9, ""
    for label, box in (
            ("yoke arm foot", (YOKE_FOOT_X, YOKE_X[1], -YOKE_W, YOKE_W,
                               YOKE_FLANGE_Z[1], YOKE_FOOT_Z)),
            ("hub tongue   ", (YOKE_TONGUE_X[0], YOKE_TONGUE_X[1],
                               -YOKE_TONGUE_Y, YOKE_TONGUE_Y,
                               YOKE_TONGUE_Z[0], YOKE_TONGUE_Z[1]))):
        x0, x1, y0, y1, z0, z1 = box
        m = min(math.sqrt(x * x + y * y + (HEAD_Z - z) ** 2) - HEAD_R
                for x in (x0, x1) for y in (y0, y1) for z in (z0, z1))
        say("   head to the %s   %+7.1f" % (label, m))
        if m < worst:
            worst, at = m, label.strip()
    if worst < 2.0:
        bad.append("head fouls the %s by %.1f" % (at, 2.0 - worst))
    say("   head into the yoke gap        %+7.1f a side"
        % (YOKE_X[0] - HEAD_R))
    if YOKE_X[0] - HEAD_R < FIT_MIN:
        bad.append("head will not pass between the yoke arms")

    say("\n--- the nod drive path ---------------------------------------")
    # Clearance cannot answer this and never could.  Every pair below used to
    # measure a perfect 0.15 slip fit, and the head still did not move.
    for label, a, b, want in (
            ("cplr keyed to the head?  no ", "DB_cplr", "DB_head", False),
            ("cplr keyed to the yoke?  no ", "DB_cplr", "DB_yoke_arm_L",
             False),
            ("pivot keyed to the head? YES", "DB_pivot", "DB_head", True),
            ("pivot keyed to the yoke? no ", "DB_pivot", "DB_yoke_arm_R",
             False)):
        v = _spins(a, b)
        if v is None:
            continue
        keyed = v > SPIN_OK
        say("   %s  %9.1f mm3 at %2.0f deg  %s"
            % (label, v, SPIN_A, "keyed" if keyed else "free"))
        if keyed != want:
            bad.append("%s x %s comes out %s and must not"
                       % (a, b, "keyed" if keyed else "free"))
    # ...so the ONLY thing grounding the coupler is its two bolts.  They have
    # to land in material at both ends and miss the bore, because if they do
    # not, this joint is back to spinning in place with nothing to show it.
    for label, have, need in (
            ("M2 clears the nod bore     ", NOD_BOLT_R - M2_PILOT,
             NOD_BORE / 2 + 0.5),
            ("M2 inside the cap edge     ", NOD_CAP_R - NOD_BOLT_R, M2_CLEAR),
            ("M2 inside the post end     ",
             10.0 - NOD_BOLT_R - M2_PILOT, 1.0),
            ("cap proud of the arm, a side",
             YOKE_W - NOD_CAP_R, -2.0),
            ("M2 thread in the yoke arm  ", YOKE_X[1] - YOKE_X[0], 4.0),
            ("spline into the coupler    ", NOD_SPLINE[1] - NOD_SPLINE[0],
             3.5),
            ("D key into the head boss   ", NOD_KEY_X[1] - NOD_KEY_X[0], 5.0),
            ("D flat depth               ", NOD_JNL - NOD_KEY, 0.5),
            ("D wall left in the pivot   ", NOD_KEY - M3_CLEAR, 1.0),
            ("M3 thread in the head boss ",
             (NOD_KEY_X[0] - 0.5) - NOD_BOSS_X[0], 4.0),
            ("boss inside the head shell ",
             HEAD_R - math.hypot(NOD_BOSS_X[1], NOD_BOSS_R), 0.2),
            ("spotface makes a real flat ",
             math.sqrt(max(0.0, HEAD_R ** 2 - NOD_SPOT_R ** 2))
             - NOD_SPOT_X, 0.1),
            ("head end float, cap-collar ", NOD_FLOAT, 0.15)):
        say("   %s%+7.1f" % (label, have - need))
        if have - need < 0:
            bad.append("nod drive: %s short by %.1f"
                       % (label.strip(), need - have))
    say("   M3 x 25 down the pivot, head at x -%.0f, driven along -x"
        % (YOKE_X[1] + NOD_CAP_T))
    say("   the head's RIGHT support is the servo's own output bearing:")
    say("   _svpocket_ops opens the shell on that axis from x 31.7 out to 56,")
    say("   so there is nothing left there to journal on.  0.6 N RADIAL,")
    say("   which is not the thrust case this file refuses to put on a servo")

    say("\n--- print orientation ----------------------------------------")
    say("   part            up      plate      roof     steep   worst")
    for name in sorted(PRINT_ORIENT):
        ob = bpy.data.objects.get(name)
        if not ob:
            continue
        axis, sign, budget = PRINT_ORIENT[name]
        roof, steep, plate, wst = _overhang(ob, axis, sign)
        over = budget is not None and roof > budget
        flag = "!!" if over else ("  " if roof <= OVERHANG_WARN else " ~")
        say("%s %-14s %s%s %9.1f %9.1f %9.1f %5.0f deg%s"
            % (flag, name, "+" if sign > 0 else "-", axis, plate, roof, steep,
               wst, "" if budget is None else "   budget %.0f" % budget))
        if over:
            bad.append("%s roofs %.0f mm2 printed %s%s, budget %.0f"
                       % (name, roof, "+" if sign > 0 else "-", axis, budget))
        elif budget is None and roof > OVERHANG_WARN:
            warn.append("%s roofs %.0f mm2 printed %s%s - never sliced, so "
                        "this is reported and not gated"
                        % (name, roof, "+" if sign > 0 else "-", axis))

    worst = 1e9
    for a in range(int(ARM_RANGE[0]), int(ARM_RANGE[1]) + 1, 2):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        for t in (0.0, ARM_L):
            for dx in (-ARM_T / 2, ARM_T / 2):
                for dy in (-ARM_W / 2, ARM_W / 2):
                    y = dy * c - (-t) * s
                    z = ARM_AZ + dy * s + (-t) * c
                    rr = _prof_r(BODY_PROF, z)
                    if rr is None:
                        continue
                    worst = min(worst, math.hypot(ARM_BLADE_X + dx, y) - rr)
    say("   arm blade to the body, swept  %+7.1f" % worst)
    if worst < 2.0:
        bad.append("arm blade clips the body at some angle (%.1f)" % worst)
    tip = ARM_AZ - ARM_L * math.cos(math.radians(ARM_RANGE[0]))
    say("   arm tip to the desk at %+.0f    %+7.1f" % (ARM_RANGE[0], tip))
    if tip < 5.0:
        bad.append("arm hits the desk at %.0f deg" % ARM_RANGE[0])

    say("")
    say("--- feeding the head tilt servo up the rear -------------------")
    # Not a clearance check on a static part: a REACHABILITY check on a
    # motion.  Every stop on this run passed a clearance test happily,
    # because a 5 mm slot is beautifully clear of everything near it and says
    # nothing at all about the 12.2 x 26.7 object that has to go through it.
    # That is eye rig 01 again, one part further up the robot.
    pw, pl = SV_PASS
    say("   an MG90S on end, hub in, horn off      %5.1f x %5.1f" % (pw, pl))
    for nm, w, l in (("DB_dome shelf window", PASS_L, PASS_W),
                     ("DB_head underside window", PASS_W, PASS_L)):
        say("   %-25s %5.1f x %5.1f   %+6.2f"
            % (nm, w, l, min(max(w, l) - pl, min(w, l) - pw)))
        if min(w, l) < pw or max(w, l) < pl:
            bad.append("%s will not pass an MG90S: %.1f x %.1f into %.1f x %.1f"
                       % (nm, pw, pl, w, l))

    # straight up out of the shelf window and out through the dome's mouth.
    # The window is tangential precisely so this number stays positive.
    mouth = INNER_PROF[-1][0]
    corner = math.hypot(PASS_L / 2, abs(PASS_SHELF_Y) + PASS_W / 2)
    say("   shelf window corner r %.1f, dome mouth r %.1f   %+6.2f"
        % (corner, mouth, mouth - corner))
    if mouth - corner < 1.0:
        bad.append("the servo cannot rise straight out of the shelf window: "
                   "its corner is at r %.1f, the dome mouth is r %.1f"
                   % (corner, mouth))
    ped = abs(PASS_SHELF_Y) - PASS_W / 2 - abs(PED_Y[0])
    say("   shelf window to the pan pedestal             %+6.2f" % ped)
    if ped < 2.0:
        bad.append("the shelf window breaks into the pan pedestal (%.1f)" % ped)

    # the head window has to cut CLEAN THROUGH.  A vertical slot in a sphere
    # runs out of sphere fast at the back, and this cut stops at z 148
    far = math.hypot(PASS_W / 2, abs(PASS_HEAD_Y) + PASS_L / 2)
    say("   head window far corner r %.1f of %.1f           %+6.2f"
        % (far, HEAD_R, HEAD_R - far))
    zin = HEAD_Z - math.sqrt(max(0.0, (HEAD_R - HEAD_WALL) ** 2 - far ** 2))
    say("   ... cavity reached at z %.1f, cut ends at %.1f" % (zin, HEAD_Z - 34.0))
    if far > HEAD_R - 4.0 or zin > HEAD_Z - 34.0:
        bad.append("the head window does not break right through the shell at "
                   "its far end (r %.1f, cavity at z %.1f)" % (far, zin))
    # and it must miss the nod servo's boss.  They DO overlap in y - the
    # boss runs back to y -13.6 and the window's near edge is at -7.65 - so
    # the only thing keeping them apart is x, which is what gets measured.
    # Reporting the y gap here would have read +6 and meant nothing.
    boss_x = (YOKE_X[0] - 3.0) + (SV_EAR_Z[0] - 7.0)    # _svboss back=7.0
    nx = boss_x - PASS_W / 2
    say("   head window to the nod servo boss, in x      %+6.2f" % nx)
    if nx < 2.0:
        bad.append("the head window runs into the nod servo boss (%.1f)" % nx)

    # DB_top is the one part on this run that is NOT a pass, and cannot be
    say("   DB_top threads ON over the lead: %.1f throat, %.1f slot"
        % (WIRE_THROAT, WIRE_D))
    if WIRE_THROAT > WIRE_D:
        bad.append("DB_top's throat (%.1f) is wider than its slot (%.1f) - the "
                   "loom walks back out under the yoke sweep"
                   % (WIRE_THROAT, WIRE_D))
    if WIRE_THROAT < 3.0:
        bad.append("DB_top's throat (%.1f) will not pass a 3-core servo lead"
                   % WIRE_THROAT)
    band = TOP_R[1] - YOKE_FLANGE_R[1]
    say("   ... and it never could be one: free band %.1f, servo needs %.1f"
        % (band, PASS_W))

    # ORDER, not clearance.  Both of these came off the mesh, and both are
    # why steps 0 and 1 in the header read the way they do.  Neither is a
    # failure: they are the reason the two parts are fitted when they are.
    hz = HEAD_Z - math.sqrt(HEAD_R ** 2 - (PASS_HEAD_Y + PASS_L / 2) ** 2)
    say("   head window clears the yoke flange by %.1f, servo is %.1f tall"
        % (hz - YOKE_FLANGE_Z[1], pl))
    say("   -> the servo goes into the head BEFORE the head goes on the yoke,")
    say("      and DB_top goes on AFTER the servo is up.  Fit them the other")
    say("      way round and neither one can be done at all.")
    if band >= PASS_W:
        warn.append("DB_top's free band is %.1f now - it COULD take a servo "
                    "window, and the throat is no longer the only option"
                    % band)

    say("")
    say("--- seating the NeoPixel rings --------------------------------")
    bore_r = (RING_OD + 2 * RING_FIT) / 2
    land_in, land_out = HOLD_ID / 2, HOLD_LAND_OD / 2
    for label, have, need in (
            ("bore over the ring OD, a side", RING_FIT, 0.2),
            ("bore deeper than a nominal   ",
             FACE_T - FACE_DIFF - RING_T, 0.2),
            ("aperture clears the 5050s    ", RING_APER - 35.0, 0.0),
            ("shoulder the ring seats on   ", (RING_OD - RING_APER) / 2, 0.5),
            ("... and the ledge it is cut in", bore_r - RING_APER / 2, 0.8),
            ("land inside the PCB rim      ", RING_OD / 2 - land_out, 0.2),
            ("land clear of the bore wall  ", bore_r - land_out, 0.3),
            ("land width on the PCB        ", land_out - land_in, 1.5),
            ("holder preload on the ring   ", HOLD_LIFT, 0.3),
            ("open middle for the lead     ", HOLD_ID, 20.0),
            ("wire escapes under the land  ", HOLD_NOTCH_R * 2 - 2.0, 1.0),
            ("holder body on the plate     ", HOLD_OD / 2 - bore_r, 0.5),
            ("screw into solid plate       ",
             HOLD_SCREW_R - bore_r - M25_PILOT, 2.5),
            ("lead scallop takes a 3-core  ", RING_LEAD_R * 2 - 4.0, 1.0),
            ("tie slot on the long lug     ", RING_TIE[1], 1.6),
            ("holder to the other holder   ", 2 * EYE_X - HOLD_OD, 1.0)):
        say("   %-29s %+7.2f  (needs %.1f)" % (label, have, need))
        if have < need:
            bad.append("eye seat: %s is %.2f, needs %.1f"
                       % (label.strip(), have, need))
    # TOO TIGHT vs FALLS OUT, which is the whole question on this part and
    # is not answered by any single clearance.  The ring seats FRONT face
    # against the shoulder, so where its back ends up depends on how thick
    # that particular ring is - and "3.2" is a nominal, not a measurement.
    # Grip is what the land still has left after the thinnest ring in the
    # band; flex is what the lugs are asked for by the thickest.
    t_lo, t_hi = RING_T_BAND
    depth = FACE_T - FACE_DIFF
    say("   ring thickness taken as %.1f .. %.1f, bore %.1f deep"
        % (t_lo, t_hi, depth))
    for label, have, need in (
            ("bore swallows the thickest   ", depth - t_hi, 0.0),
            ("grip left on the THINNEST    ",
             t_lo - (depth - HOLD_LIFT), 0.15),
            ("grip on a nominal ring       ",
             RING_T - (depth - HOLD_LIFT), 0.3)):
        say("   %-29s %+7.2f  (needs %.1f)" % (label, have, need))
        if have < need:
            bad.append("eye seat: %s is %.2f, needs %.1f"
                       % (label.strip(), have, need))
    say("   %-29s %+7.2f  (worst case)" % ("flex asked of the two lugs   ",
                                           HOLD_LIFT))
    if HOLD_LIFT > 1.2:
        warn.append("the holder has to flex %.1f for a thick ring - that is "
                    "a lot to ask of two M2.5 in PLA" % HOLD_LIFT)

    # and neither holder may run off the edge of the plate it screws to.
    # The disc and the lugs have to be measured separately: their bounding
    # box has a corner at r 52.6 that no part of the holder occupies, and
    # taking that as the answer condemns a part with 3.9 mm to spare.
    _tw, _t0, _t1 = HOLD_TAB
    far = max([math.hypot(EYE_X, EYE_Z) + HOLD_OD / 2]
              + [math.hypot(EYE_X + dx, EYE_Z + dz)
                 for dx in (_tw / 2, -_tw / 2)
                 for dz in (_t1, -HOLD_TIE_Z)])
    say("   %-29s %+7.2f  (needs %.1f)"
        % ("holder inside the plate edge ", 45.9 - far, 1.5))
    if 45.9 - far < 1.5:
        bad.append("DB_eye_holder overhangs DB_face by %.2f" % (far - 45.9))
    say("   the eye is OPEN at O%.1f - the ring seats on the %.2f shoulder,"
        % (RING_APER, (RING_OD - RING_APER) / 2))
    say("   the land presses its rim all round, and the lead leaves straight")
    say("   back out through the O%.1f middle, bent round nothing" % HOLD_ID)

    say("\n--- printed parts cutting into each other ---------------------")
    for v, an, bn in clashes(verbose):
        bad.append("%s cuts %.0f mm3 into %s" % (an, v, bn))

    say("\n--- what this does NOT check ---------------------------------")
    say("   the speaker BOX size and its tab holes are GUESSES, and they")
    say("   are what DB_chassis is built around - see MEASURE")
    say("   nothing here weighs anything, so no torque is checked")
    say("   no screw path, no loom volume, no heat")
    say("   DB_head, DB_face and the two DB_arm have no declared print")
    say("   orientation, so nothing counts their overhangs at all.  The four")
    say("   with a budget in PRINT_ORIENT are the only ones being held to a")
    say("   claim; the rest are reported on the header's word")
    say("   the servo run is checked as OPENINGS, not as a swept path -")
    say("   nothing here walks an MG90S up it and watches what it hits")
    say("   the yoke arm foot sweeps the REAR at pan +-80, over the wire")
    say("   slot at r 44.5 - the loom has to sit inboard of r 29 or")
    say("   outboard of r 64, and nothing here measures that")
    say("   SHT41 hole SPACING is still a guess - the count is right now,")
    say("   the pitch is not confirmed")
    say("   the CQRobot module and the square one are still NOT in this -")
    say("   tell me what they are and they get mounts too")

    say("\n%s" % ("READY as a mockup - packaging closes"
                  if not bad else "NOT ready:"))
    for b in bad:
        say("   * " + b)
    for w in warn:
        say("   ? " + w)
    return not bad


# ------------------------------------------------------------------ export
STL_DIR = r"C:\Humalien\stl"


def export_stl(folder=STL_DIR, names=("DB_chassis",)):
    """Write each named object to its own STL, in millimetres.

    global_scale stays 1.0 so the numbers in this file land in the slicer
    unchanged - CH_R 76 comes out as a 152 mm plate, not 152 m.

    This never saves the .blend.  Exporting leaves the scene dirty and the
    blend is a convenience here, not the source: build() reconstructs every
    part from the constants at the top of this file.
    """
    import os
    os.makedirs(folder, exist_ok=True)
    out = []
    for n in names:
        ob = bpy.data.objects.get(n)
        if ob is None:
            print("  *** %s is not in the scene - run build() first" % n)
            continue
        was = ob.hide_viewport
        ob.hide_viewport = False
        for o in bpy.data.objects:
            o.select_set(False)
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        path = os.path.join(folder, n + ".stl")
        for call in (
                lambda: bpy.ops.wm.stl_export(
                    filepath=path, export_selected_objects=True,
                    global_scale=1.0, apply_modifiers=True),
                lambda: bpy.ops.export_mesh.stl(
                    filepath=path, use_selection=True,
                    global_scale=1.0, use_mesh_modifiers=True)):
            try:
                call()
                break
            except Exception:
                continue
        ob.select_set(False)
        ob.hide_viewport = was
        bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        dim = tuple(max(v[i] for v in bb) - min(v[i] for v in bb)
                    for i in range(3))
        kb = os.path.getsize(path) // 1024 if os.path.exists(path) else 0
        out.append((path, dim, kb))
        print("  %-28s %5.1f x %5.1f x %5.1f mm   %d KB"
              % (os.path.basename(path), dim[0], dim[1], dim[2], kb))
        if kb == 0:
            print("  *** nothing was written")
    return out
