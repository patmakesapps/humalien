"""The bench tool for the v2 eye mechanism: center, aim, sweep, and stop.

    ssh into the Pi, then:  python -m humalien_node.eyes_bench

Written BEFORE the mechanism finished printing, because the assembly sheet
(docs/eye-v2-assembly.md) says to center every servo electrically before
pressing a horn on - which makes this tool a prerequisite of assembly, not
a follow-up to it.

THE CONTRACT WITH THE MECHANISM
-------------------------------
cad/eye.py built every drive 1:1 on purpose - tilt is direct on the shaft,
pan is a parallelogram of equal 11 mm cranks, blink is 14 mm on 14 mm - so
ONE degree at a servo is ONE degree at the eye, and the limits below are
in eye degrees with no ratio table in between:

    tilt   +-16    the gimbal's verified swing
    blink  -55/+10 lid closed at -55, wide at +10
    pan    +-20    the verified pan range

These numbers are the same ones the CAD's clearance sweeps proved. Nothing
here may command past them; if the mechanism binds INSIDE them, that is a
finding about the print, and the number to change lives in cad/eye.py, not
here.

Directions are set at the bench with `invert`, and neutral is trimmed in
microseconds with `trim` - both are expected to be discovered during
assembly and then copied into whatever motion layer brain/gaze.py finally
drives. Until then this file is the single source of the servo map.

SAFETY SHAPE
------------
All channels start LIMP (no pulse) and go limp again on exit or Ctrl+C. A
servo with no pulse holds nothing and hurts nothing. Every move is slewed
at SLEW_DPS instead of jumping, because a 0-to-full-speed step into a
fresh printed linkage is how v1 broke parts.
"""

import sys
import time

CHANNELS = {"tilt": 0, "pan": 1, "blink": 2}    # PCA9685 channel map
LIMITS = {"tilt": (-16.0, 16.0),                # EYE degrees, from the CAD
          "pan": (-20.0, 20.0),
          "blink": (-55.0, 10.0)}
# Pulse clamps per axis. 1000..2000 us is the conservative +-45 deg band;
# blink legitimately needs -55, which is ~890 us, so its floor is lower -
# an MG90S runs to ~600 us without complaint.
PULSE_CLAMP = {"tilt": (1000, 2000),
               "pan": (1000, 2000),
               "blink": (850, 2050)}
US_PER_DEG = 1000.0 / 90.0      # MG90S: ~1000 us across 90 deg
CENTER_US = 1500
SLEW_DPS = 30.0                 # max commanded speed, degrees per second
TICK = 0.02                     # slew update period


class EyeRig:
    """Owns the PCA9685 and the calibration state. Importable by the
    future motion layer; the REPL below is just a face on it."""

    def __init__(self):
        import board
        import busio
        from adafruit_pca9685 import PCA9685
        self.pca = PCA9685(busio.I2C(board.SCL, board.SDA))
        self.pca.frequency = 50
        self.trim = {a: 0 for a in CHANNELS}        # us, added to neutral
        self.sign = {a: 1 for a in CHANNELS}        # +-1, set at the bench
        self.pos = {a: None for a in CHANNELS}      # None = limp
    def _us(self, axis, deg):
        us = CENTER_US + self.trim[axis] + self.sign[axis] * deg * US_PER_DEG
        lo, hi = PULSE_CLAMP[axis]
        return max(lo, min(hi, us))

    def _write(self, axis, us):
        # duty over a 20 ms frame, on the PCA's 16-bit counter
        self.pca.channels[CHANNELS[axis]].duty_cycle = \
            int(us / 20000.0 * 0xFFFF)

    def limp(self, axis=None):
        for a in ([axis] if axis else CHANNELS):
            self.pca.channels[CHANNELS[a]].duty_cycle = 0
            self.pos[a] = None
        print("  limp:", axis or "all")

    def goto(self, axis, deg):
        lo, hi = LIMITS[axis]
        if not lo <= deg <= hi:
            print("  REFUSED: %s %.1f outside %.0f..%.0f" % (axis, deg, lo, hi))
            return
        here = self.pos[axis]
        if here is None:
            # first pulse on a limp servo jumps regardless; start at the
            # target only if it is neutral, else demand a centre first
            if abs(deg) > 0.5:
                print("  REFUSED: %s is limp - `c` to centre it first" % axis)
                return
            here = deg
        step = SLEW_DPS * TICK
        while abs(deg - here) > 1e-6:
            here += max(-step, min(step, deg - here))
            self._write(axis, self._us(axis, here))
            self.pos[axis] = here
            time.sleep(TICK)

    def center(self):
        for a in CHANNELS:
            self._write(a, self._us(a, 0.0))
            self.pos[a] = 0.0
        print("  centred: all at 1500 us + trim. Press horns on NOW if "
              "assembling.")

    def sweep(self, axis):
        lo, hi = LIMITS[axis]
        print("  sweep %s: 0 -> %.0f -> %.0f -> 0" % (axis, lo, hi))
        for target in (lo, hi, 0.0):
            self.goto(axis, target)
            time.sleep(0.3)


HELP = """\
  c                centre all three (do this before horns go on)
  t/p/b <deg>      goto: tilt/pan/blink, in eye degrees, slewed
  sweep <axis>     slow 0 -> min -> max -> 0
  trim <axis> <us> shift an axis's neutral, e.g. `trim pan -20`
  invert <axis>    flip an axis's direction
  off [axis]       go limp (no pulse, no holding torque)
  q                limp everything and quit
"""
AXES = {"t": "tilt", "p": "pan", "b": "blink",
        "tilt": "tilt", "pan": "pan", "blink": "blink"}


def main():
    rig = EyeRig()
    print("eye bench. channels: %s\n%s" % (CHANNELS, HELP))
    try:
        while True:
            try:
                words = input("> ").strip().lower().split()
            except EOFError:
                break
            if not words:
                continue
            cmd, args = words[0], words[1:]
            try:
                if cmd == "q":
                    break
                elif cmd == "c":
                    rig.center()
                elif cmd in AXES and args:
                    rig.goto(AXES[cmd], float(args[0]))
                elif cmd == "sweep" and args:
                    rig.sweep(AXES[args[0]])
                elif cmd == "trim" and len(args) == 2:
                    rig.trim[AXES[args[0]]] += int(args[1])
                    print("  trim %s -> %+d us" % (AXES[args[0]],
                          rig.trim[AXES[args[0]]]))
                    if rig.pos[AXES[args[0]]] is not None:
                        rig.goto(AXES[args[0]], rig.pos[AXES[args[0]]])
                elif cmd == "invert" and args:
                    rig.sign[AXES[args[0]]] *= -1
                    print("  %s direction flipped" % AXES[args[0]])
                elif cmd == "off":
                    rig.limp(AXES[args[0]] if args else None)
                else:
                    print(HELP)
            except (KeyError, ValueError):
                print(HELP)
    finally:
        rig.limp()
        print("all limp. good bench.")


if __name__ == "__main__":
    main()
