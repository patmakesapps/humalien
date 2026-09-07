"""Which camera Humalien looks through.

The Arducam is the robot's eye. The laptop webcam is only ever a stand-in
for it, and picking between them by index does not work: the indices move.
Unplug the Arducam and it is gone; plug in a capture card, a phone acting as
a webcam, or dock the machine, and everything after it shifts by one. A
number in .env that meant "the Arducam" on Tuesday means "the built-in
webcam pointing at the ceiling" on Wednesday, and nothing in the logs says
so - Humalien just quietly starts seeing the wrong room.

So devices are chosen BY NAME. The Arducam wins whenever it is attached;
anything else is the fallback for when it is not. HUMALIEN_CAMERA still
overrides everything, for the cases a name cannot express (a second Arducam,
a video file, an IP stream).

Names come from the platform, not from OpenCV, which does not expose them:

  Windows  pygrabber, which reads the DirectShow device list. Its ordering
           IS the CAP_DSHOW index space, so a position in that list is
           directly usable.

           It is opened with Media Foundation first anyway, because
           DirectShow will not switch this camera out of YUY2: the Arducam
           runs 1280x800 at 10 fps through CAP_DSHOW and at 31 through
           CAP_MSMF. That assumes both backends enumerate the same devices
           in the same order, which is true of ordinary UVC cameras and is
           the reason CAP_DSHOW stays behind it as the fallback - a
           DirectShow-only device would fail to open under MSMF and be
           picked up there. (MSMF is only ever asked about an index that
           was already found: it takes tens of seconds to fail on one that
           is not there, which makes probing with it unusable.)
  Linux    /dev/v4l/by-id, where the kernel has already done the work. The
           path is passed to OpenCV as-is; it survives a replug, an index
           does not.

Anywhere else, or if that lookup fails, this degrades to plain index 0 -
the same thing the code did before it could read names at all.
"""

import os
import sys
from dataclasses import dataclass
from glob import glob

import cv2


# Substring, matched case-insensitively against the device name. Override
# with HUMALIEN_CAMERA_NAME if the eye is ever something other than an
# Arducam.
PREFERRED = "arducam"


def preference(preferred: str | None) -> str:
    """The name to look for. Read at call time, after .env has loaded."""

    if preferred is not None:
        return preferred

    return os.getenv("HUMALIEN_CAMERA_NAME", PREFERRED)


@dataclass(frozen=True)
class Camera:
    """A capture device, and how to open it."""

    source: int | str
    name: str

    # Tried in order. More than one because the backend that names a device
    # is not always the backend that gets the best out of it.
    backends: tuple[int, ...] = (cv2.CAP_ANY,)

    def open(self, size: tuple[int, int] | None = None) -> cv2.VideoCapture | None:
        """Open the device, asking for a frame size if one is wanted.

        A backend that opens but never delivers a frame is no use, so one
        is taken before the capture is accepted. Cameras that cannot do the
        size asked for quietly give the nearest thing they can; whatever
        arrives, arrives.
        """

        for backend in self.backends:
            capture = cv2.VideoCapture(self.source, backend)

            if capture.isOpened():
                if size is not None:
                    capture.set(cv2.CAP_PROP_FRAME_WIDTH, size[0])
                    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, size[1])

                if capture.grab():
                    return capture

            capture.release()

        return None

    def __str__(self) -> str:
        return f"{self.name} ({self.source})"


def requested(value: int | str) -> Camera:
    """A device somebody named explicitly, by index, path or URL."""

    text = str(value)
    source = int(text) if text.isdigit() else text

    return Camera(source, f"camera {text}")


def _windows_cameras() -> list[Camera]:
    try:
        from pygrabber.dshow_graph import FilterGraph
    except ImportError:
        # Optional dependency. Without it there are no names to match on,
        # and the caller falls back to index 0.
        return []

    try:
        names = FilterGraph().get_input_devices()
    except Exception:
        return []

    return [
        Camera(i, name, (cv2.CAP_MSMF, cv2.CAP_DSHOW))
        for i, name in enumerate(names)
    ]


def _linux_cameras() -> list[Camera]:
    cameras = []

    # index0 is the capture node. A UVC camera also publishes metadata
    # nodes, which open fine and then never return a frame.
    for path in sorted(glob("/dev/v4l/by-id/*-video-index0")):
        name = os.path.basename(path)
        name = name.removeprefix("usb-").removesuffix("-video-index0")

        cameras.append(Camera(path, name.replace("_", " "), (cv2.CAP_V4L2,)))

    return cameras


def attached() -> list[Camera]:
    """Every capture device this machine can name, in platform order."""

    if sys.platform == "win32":
        return _windows_cameras()

    if sys.platform.startswith("linux"):
        return _linux_cameras()

    return []


def in_preference_order(
    explicit: int | str | None = None,
    *,
    preferred: str | None = None,
    found: list[Camera] | None = None,
) -> list[Camera]:
    """Which camera to try, best first. Never empty.

    An explicit request is the whole list - if somebody named a device and
    it does not work, silently using a different one is worse than failing.
    """

    if explicit not in (None, ""):
        return [requested(explicit)]

    found = attached() if found is None else found

    if not found:
        return [Camera(0, "camera 0")]

    wanted = preference(preferred).strip().lower()
    match = [c for c in found if wanted and wanted in c.name.lower()]

    # Everything else stays on the list, in order, as the fallback.
    return match + [c for c in found if c not in match]


def choose(
    explicit: int | str | None = None,
    *,
    preferred: str | None = None,
    found: list[Camera] | None = None,
) -> Camera:
    """The camera Humalien would use right now."""

    return in_preference_order(explicit, preferred=preferred, found=found)[0]


def open_camera(
    explicit: int | str | None = None,
    *,
    preferred: str | None = None,
    size: tuple[int, int] | None = None,
    log=print,
) -> tuple[cv2.VideoCapture | None, Camera | None]:
    """Open the best camera that actually opens.

    A device that is listed but busy - another program holding it, a hub
    that has not settled after a replug - is no more use than one that is
    absent, so it is treated the same way and the next candidate is tried.
    """

    candidates = in_preference_order(explicit, preferred=preferred)

    for camera in candidates:
        capture = camera.open(size)

        if capture is not None:
            return capture, camera

        log(f"{camera} did not open")

    return None, None
