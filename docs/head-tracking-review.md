# Head tracking review and bench plan

Status: code review complete on September 4, 2026. Hardware verification and
tuning are planned for tonight or the next working session. No runtime motion
values were changed during this review.

## What the robot currently does

The head-following path is implemented from camera to servo:

1. `brain/eyes.py` updates face detections about four times per second.
2. `brain/attention.py` selects one face and resists switching on detector
   noise.
3. `brain/gaze.py` smooths the selected face position.
4. `brain/voice_core.py` passes that position to `brain/gestures.py` every
   100 ms.
5. `brain/gestures.py` mixes gaze, speech motion, and idle drift into `pan`
   and `nod` pose messages.
6. The Pi node applies those targets through its acceleration-limited servo
   loop.

Both `HUMALIEN_GESTURES` and `HUMALIEN_TRACK_FACES` default to enabled. The
configuration on the machine running the brain can override either value.

## Important limitation: it does not identify the speaker

The visual attention system does not receive audio direction or an association
between a voice and a face. The phrase "the person Tubby is speaking with"
currently means the face the visual attention system selected, not a person
proven to be speaking.

The first target is generally the largest visible face. Tubby then stays
committed to the face nearest that target's previous position. Recognition and
remembered identity are not used to determine who has the conversational floor.

## What happens when another person appears

A new arrival does not directly command a head turn. With another face visible,
the attention controller schedules a deliberate glance every 9–22 seconds. The
glance lasts 1.6 seconds and then returns to the prior target.

If the glance timer became overdue while only one person was present, a newly
visible second person can receive an almost immediate glance. Otherwise the
glance waits for the remaining random interval.

A second face can permanently take the target when it remains at least 35%
larger for 1.2 seconds and the current target has been held for at least 2.5
seconds. That is a visual prominence change, not speaker detection, and there
is no rule that automatically returns to the actual speaker afterward.

## Why the movement may be difficult to notice

- Runtime pan is limited to ±14.4 degrees.
- Face tracking uses 85% of that range, so its maximum request is about ±12.2
  degrees at the extreme edge of the camera image.
- A face centered at one-quarter or three-quarters of the image requests only
  about 6.1 degrees. A face nearer the middle may produce just 1–3 degrees.
- Face position is smoothed once in `gaze.py` and again over 0.55 seconds in
  `gestures.py`.
- Tracking nod only looks upward. A face at or below the vertical center of the
  image produces no tracking nod because downward mechanical travel has not
  been approved beyond -3.6 degrees.
- Tubby's own audible speech adds slow pan and upward nod motion, but short or
  quiet replies may not build the full envelope before ending.

The Pi's servo loop is fast enough to perform the requested motion. The
deliberately small requests and the target selection policy are more likely to
explain subtle behavior than the node-side speed limits.

## Bench procedure for tonight or the next session

First isolate the head hardware on the Pi:

```text
python -m humalien_node.head_bench
engage
track l
home
track r
home
track u
talk
```

Confirm that `track l` and `track r` turn toward the indicated side rather than
away from it, `track u` visibly raises the head, and `talk` produces observable
but gentle pan/nod motion.

The `track` simulation in `head_bench.py` is stale: it currently uses a 65%
pan gain and 6-degree upward nod, while the live brain uses 85% and 9 degrees.
It remains useful for direction and hardware checks but understates live
tracking movement. Bring those constants back into agreement during the tuning
session.

Then test the real camera-to-servo path:

1. Place person A clearly to one side of the camera image.
2. Confirm the brain logs `Face tracking on`, `Gestures on`, and
   `Looking at a face`.
3. Let that target remain established for at least 22 seconds.
4. Have person B enter well over on the opposite side at roughly the same
   distance and size.
5. Look for `Glancing at somebody else`, a turn toward B for about 1.6 seconds,
   and a return to A.
6. Repeat with each person at the image edges, near the image center, and above
   the camera to separate pan range from nod behavior.

If the attention logs appear but the head does not visibly move, inspect pose
delivery, servo direction, trim, and mechanical response. If the logs do not
appear, inspect the deployed feature flags, camera selection, and face
detection before changing motion amplitudes.

## Questions for the tuning session

- Should a newly arrived face trigger an immediate acknowledgement rather than
  waiting for the periodic glance timer?
- Is ±12.2 degrees enough visible pan for the camera's normal seating layout?
- Should tracking intentionally use more of the verified ±14.4-degree range?
- Should short speech receive a faster or stronger head envelope?
- Is upward-only nod tracking sufficient, or should additional downward travel
  be bench-qualified first?
- Is visual target selection adequate, or does a later version need speaker
  direction or active-speaker association?

The behavior should be tuned from the hardware observations rather than changed
before the bench session.
