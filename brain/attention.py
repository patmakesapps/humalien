"""Who the robot is looking at, when there is more than one candidate.

gaze.py smooths a face into a stable target. It does not decide WHICH face,
and `select_primary_face` - largest wins, every frame, independently - is the
wrong answer the moment two people sit down together.

THE FAILURE THIS EXISTS TO PREVENT
----------------------------------
Two faces at roughly the same distance measure within a few percent of each
other in area, and which one is "largest" flips on detector noise several
times a second. Feed that to a neck and the head snaps between two people for
as long as they both stay in the room. Smoothing does not fix it: the target
is genuinely alternating, so a smoother just averages it into staring at the
gap between them, which is worse.

The fix is not smoothing but COMMITMENT. Three rules, in order:

  1. Identity. The face nearest to where the target was last frame IS the
     target, regardless of area. Detection order is not stable and area is
     noisy; position is neither.
  2. Hysteresis. Another face has to be clearly bigger - SWITCH_RATIO, not
     merely bigger - before it counts as a challenger at all.
  3. Dwell. It has to stay clearly bigger for SWITCH_DWELL seconds, and the
     last switch has to be MIN_HOLD seconds ago. Somebody leaning forward for
     a moment does not steal the conversation.

Losing the face entirely is handled the same way: LOSE_AFTER seconds of not
finding it before the target is given up, because a detector that drops a
frame is not a person who left.

THE GLANCE
----------
A robot that locks onto one person and never acknowledges anybody else in the
room reads as rude, not attentive. So with other faces present, and only
every GLANCE_EVERY seconds, the target moves deliberately to somebody else
for GLANCE_SECONDS and then comes back. That is a decision on a slow timer,
not the frame-by-frame flicker above - which is the whole difference between
looking around a room and twitching.

Set GLANCE_EVERY to None to switch it off.
"""

import random
from dataclasses import dataclass


# How much bigger another face has to be before it is even a candidate.
# Two people side by side at a desk measure within a few percent of each
# other; this has to sit comfortably outside that.
SWITCH_RATIO = 1.35

# How long it has to stay that much bigger, in seconds.
SWITCH_DWELL = 1.2

# The floor on how often the target may change at all, in seconds, whatever
# the areas say. This is the backstop that guarantees the head cannot hunt
# even if every rule above is somehow satisfied repeatedly.
MIN_HOLD = 2.5

# How far a face may move between polls and still be the same person, as a
# fraction of the frame width. Recognition runs at 4 Hz, so this has to cover
# a quarter second of ordinary movement.
SAME_FACE_WITHIN = 0.25

# How long the target may go unmatched before it is given up, in seconds.
# The detector drops faces constantly; this is what stops a blink in the
# software becoming a head movement.
LOSE_AFTER = 1.0

# The deliberate look at somebody else. None disables it.
GLANCE_EVERY = (9.0, 22.0)
GLANCE_SECONDS = 1.6


@dataclass(frozen=True)
class Attended:
    """The chosen face, and why. `switched` is for logging, not behaviour."""

    face: object
    count: int
    glancing: bool
    switched: bool


class Attention:
    """Picks one face out of a room and then sticks with it.

    Deliberately holds no OpenCV or servo types: it takes anything with
    `.center` and `.area` - gaze.FaceBox does - and returns one of them.
    """

    def __init__(
        self,
        *,
        switch_ratio: float = SWITCH_RATIO,
        switch_dwell: float = SWITCH_DWELL,
        min_hold: float = MIN_HOLD,
        lose_after: float = LOSE_AFTER,
        glance_every=GLANCE_EVERY,
        random_source=None,
    ) -> None:
        self.switch_ratio = switch_ratio
        self.switch_dwell = switch_dwell
        self.min_hold = min_hold
        self.lose_after = lose_after
        self.glance_every = glance_every
        self.random = random_source or random.Random()

        self._center = None            # where the target was, in pixels
        self._seen_at = None           # when it was last actually matched
        self._settled_at = None        # when the target last changed

        self._challenger = None        # centre of the face trying to take over
        self._challenging_since = None

        self._glance_at = None         # when the next glance is due
        self._glance_until = None
        self._returning_to = None      # who to go back to afterwards

    # ------------------------------------------------------------- internals

    def _nearest(self, faces, center, frame_width):
        """The face closest to a remembered point, if any is close enough."""

        if center is None or not faces:
            return None

        reach = SAME_FACE_WITHIN * frame_width

        best = min(
            faces,
            key=lambda face: (
                (face.center[0] - center[0]) ** 2
                + (face.center[1] - center[1]) ** 2
            ),
        )

        away = (
            (best.center[0] - center[0]) ** 2
            + (best.center[1] - center[1]) ** 2
        ) ** 0.5

        return best if away <= reach else None

    def _take(self, face, now, *, glancing=False):
        self._center = face.center
        self._seen_at = now
        self._settled_at = now
        self._challenger = None
        self._challenging_since = None

        return face

    def _schedule_glance(self, now):
        if self.glance_every is None:
            self._glance_at = None
            return

        self._glance_at = now + self.random.uniform(*self.glance_every)

    # ---------------------------------------------------------------- the API

    def update(self, faces, *, frame_width: int, now: float):
        """Choose who to look at. Call it every time vision has an answer.

        `faces` may be empty. Returns None only when there is genuinely
        nobody, which is the signal for the head to go back to drifting.
        """

        if not faces:
            # A detector miss is not an empty room. Hold the target briefly.
            if self._seen_at is not None and now - self._seen_at <= self.lose_after:
                return None

            self._center = None
            self._seen_at = None
            self._glance_until = None
            self._returning_to = None

            return None

        incumbent = self._nearest(faces, self._center, frame_width)

        if incumbent is None:
            # Nothing here is who we were looking at. Take the biggest and
            # start again - this is an arrival, not a contested switch.
            chosen = max(faces, key=lambda face: face.area)
            switched = self._center is not None
            self._take(chosen, now)
            self._schedule_glance(now)

            return Attended(chosen, len(faces), False, switched)

        self._seen_at = now

        others = [face for face in faces if face is not incumbent]

        # ------------------------------------------------------- the glance

        if self._glance_until is not None:
            if now < self._glance_until:
                looking_at = self._nearest(faces, self._center, frame_width)

                if looking_at is not None:
                    self._center = looking_at.center
                    return Attended(looking_at, len(faces), True, False)

            # Over, or the person glanced at has gone. Head back.
            self._glance_until = None
            back = self._nearest(faces, self._returning_to, frame_width)
            self._returning_to = None
            self._schedule_glance(now)

            if back is not None:
                self._take(back, now)
                return Attended(back, len(faces), False, True)

            return Attended(incumbent, len(faces), False, False)

        if self._glance_at is None:
            self._schedule_glance(now)

        elif others and now >= self._glance_at:
            self._returning_to = incumbent.center
            self._glance_until = now + GLANCE_SECONDS

            elsewhere = self.random.choice(others)
            self._center = elsewhere.center

            return Attended(elsewhere, len(faces), True, True)

        # ---------------------------------------------------- the challenge

        if not others:
            self._center = incumbent.center
            self._challenger = None
            self._challenging_since = None

            return Attended(incumbent, len(faces), False, False)

        biggest = max(others, key=lambda face: face.area)
        clearly_bigger = biggest.area > incumbent.area * self.switch_ratio

        if not clearly_bigger:
            # Anything less than a clear win resets the clock. This is what
            # keeps two similar faces from trading the target on noise.
            self._challenger = None
            self._challenging_since = None

        else:
            still_the_same = (
                self._challenger is not None
                and self._nearest([biggest], self._challenger, frame_width)
                is not None
            )

            if not still_the_same:
                self._challenger = biggest.center
                self._challenging_since = now

            held = now - self._challenging_since >= self.switch_dwell
            settled = (
                self._settled_at is None
                or now - self._settled_at >= self.min_hold
            )

            if held and settled:
                self._take(biggest, now)
                self._schedule_glance(now)

                return Attended(biggest, len(faces), False, True)

        self._center = incumbent.center

        return Attended(incumbent, len(faces), False, False)
