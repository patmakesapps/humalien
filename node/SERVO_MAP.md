# Desk bot servo map

Bench-identified on 2026-08-31. The PCA9685 is at `0x40` and runs at 50 Hz.
Electrical neutral is 1500 µs.

| PCA9685 channel | Physical movement | Desk-bot axis | Direction from neutral |
| --- | --- | --- | --- |
| 0 | right arm | `arm_r` | forward raises the pulse |
| 1 | neck rotation | `pan` | not calibrated |
| 2 | head nod | `nod` | not calibrated |
| 3 | left arm | `arm_l` | forward lowers the pulse |

The raw arm tests reached 2500 µs on the right and 556 µs on the left
without observed binding. Those are bench observations, not software travel
limits. The horns were re-indexed afterward, so commanded servo angle and
physical arm pose still need calibration.

The active geometry in `cad/desk_bot.py` defines `ARM_RANGE = (-20, 75)` and
uses positive pose angles for forward movement on both arms. The node must
apply the opposite electrical signs shown above. Do not substitute the raw
bench endpoints for the CAD range without completing mechanical calibration.

`humalien_node.eyes_bench` targets the archived three-servo eye mechanism; it
does not contain the desk bot's four-channel map.
