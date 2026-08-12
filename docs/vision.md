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

The current detector is OpenCV's bundled frontal-face Haar cascade. It requires
no separate model download, making it a good hardware bring-up baseline. Once
we have representative lighting and head-angle footage, detection can be
upgraded without changing the gaze target or future servo interface.
