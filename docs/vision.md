# Vision and eye tracking

Humalien's first vision slice runs entirely on the brain. A USB webcam detects
the most prominent face and turns its center into a smoothed gaze target. There
are deliberately no servo commands in this layer yet.

## Coordinate contract

The tracker emits camera-normalized coordinates:

| Value | Meaning |
| --- | --- |
| `x = -1` | Left edge of the camera frame |
| `x = 0` | Horizontal center |
| `x = +1` | Right edge |
| `y = -1` | Top edge of the camera frame |
| `y = 0` | Vertical center |
| `y = +1` | Bottom edge |

Servo direction, neutral pulse, safe travel limits, and the mapping from one
camera target to two independently driven eyes do not belong here. They will be
added in the hardware-control layer after the mechanisms can be powered and
calibrated safely.

## Run the webcam preview

From `brain/`:

```bash
python -m pip install -r requirements.txt
python -m tools.vision_preview --camera 0
```

The green box is the selected face. The yellow dot is the filtered gaze target.
Press `q` or Escape to stop.

Useful options:

```bash
# Try another camera index.
python -m tools.vision_preview --camera 1

# Use a Linux camera path and do not mirror the image.
python -m tools.vision_preview --camera /dev/video2 --no-mirror

# Print the future hardware-control message shape at about 10 Hz.
python -m tools.vision_preview --camera 0 --emit-json
```

Example output:

```json
{"type": "gaze_target", "x": 0.1842, "y": -0.0731, "state": "tracking"}
```

## Loss behavior

Detector misses should not make the eyes twitch. The controller:

1. Smooths movement while a face is visible.
2. Holds the last target for 350 ms after a miss.
3. Eases back to camera center if the face stays lost.

## Detection, and its limits

Detection runs OpenCV's bundled Haar cascades, which need no model download —
a good hardware bring-up baseline.

The frontal cascade is tried first, because a face looking at the robot is both
the common case and the most reliable detection. If it finds nothing, the
profile cascade runs. That cascade is trained on **one** direction only, so if
it also finds nothing the frame is flipped horizontally and it runs again, with
the resulting coordinates mirrored back by `FaceBox.mirrored()`.

Cost: a face looking at you is one cascade pass. A head turned side on is two.
An empty room is three, every frame. That's the expensive case, and it's the one
that runs whenever nobody is there.

**This improves profile tracking. It does not make it good.** Known limits:

- **The three-quarter dead zone.** Somewhere between straight-on and full
  profile, neither cascade fires reliably. Haar cascades are trained on discrete
  poses and don't interpolate between them. Expect a wobble as you rotate
  through roughly 45°, which `HOLDING` will paper over only if you pass through
  it quickly.
- **Profile detection is noisier.** More false positives than frontal.
  `select_primary_face` picks the largest box, which absorbs some of that, but
  not all.
- **Back of the head is not a face.** Turn fully away and tracking is gone. The
  hold-then-recenter behavior is what covers this, and it's the correct
  response — there is genuinely nothing to look at.

### Upgrading the detector

When the dead zone becomes the limiting factor, the fix is a better detector,
not more cascades. OpenCV ships `cv2.FaceDetectorYN` (YuNet): a small CNN,
roughly 340 KB, that handles pose, scale, and lighting far better than Haar and
still runs comfortably on CPU.

The tradeoff is a model file to vendor or fetch, which is why it isn't the
starting point. Nothing else has to change — `detect()` returns `FaceBox`
objects, and the gaze contract above is deliberately independent of how they
were found.
