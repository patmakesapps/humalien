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

## Detection

Detection is **YuNet**, a small CNN (227 KB), via `cv2.FaceDetectorYN`. It
replaced the Haar cascade chain that came before it.

That earlier version tried the frontal cascade, then the profile cascade, then
the profile cascade again on a flipped frame. It worked, but it had a
three-quarter dead zone — somewhere between straight-on and full profile,
neither cascade fired, because Haar cascades are trained on discrete poses and
don't interpolate between them. It also cost up to three passes per frame, with
the worst case being an empty room.

YuNet covers the rotation smoothly in one pass. Two independent reasons forced
the swap:

1. **Pose.** It handles head turn as a continuum, so the dead zone goes away.
2. **Landmarks.** It emits five facial landmarks, which SFace needs to align a
   crop before embedding it. Haar gives you a bounding box and nothing else, so
   recognition was not possible on top of it.

Measured at about **14 ms per 640×480 frame** on a laptop CPU — roughly 70 fps
of headroom, and recognition doesn't need to run at frame rate anyway.

The cost is a model file. Run `python tools/fetch_models.py` once per machine;
`brain/models/` is gitignored. A missing model raises with that instruction
rather than failing obscurely.

`FaceBox.mirrored()` survives from the cascade era. Detection no longer needs
it, but it's tested and it's the right primitive if you ever flip a frame.

### Still true

- **Back of the head is not a face.** Turn fully away and tracking is gone. The
  hold-then-recenter behavior covers this, and it's the correct response —
  there is genuinely nothing to look at.
- **The gaze contract is independent of the detector.** `Detection.box` is a
  `FaceBox` exactly as before, so `gaze.py` did not change when the detector was
  replaced, and won't if it's replaced again.

## Recognition and memory

Detection answers *where is a face*. Knowing *whose* face, remembering them
tomorrow, and answering questions about what the camera sees are covered in
[people.md](people.md).
