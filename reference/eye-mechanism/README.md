# Reference eye mechanism

Will Cogley's **Animatronic Eye Mechanism ε3.2**, kept here as a measuring
reference for the bespoke design described in
[docs/eye-design-brief.md](../../docs/eye-design-brief.md).

- [MakerWorld 1184807](https://makerworld.com/en/models/1184807-animatronic-eye-mechanism-e3-2)
- [Printables 1220172](https://www.printables.com/model/1220172-animatronic-eye-mechanism-e31)

Released 2025-03-07. Six SG90 or MG90S micro servos for the pair.

## The file is deliberately not committed

`EyeMech_ε3.2_All_Plates_-_BambuStudio.3mf`, ~10 MB, is git-ignored. It is
Cogley's work, not ours, and committing it to this repo would redistribute it
under whatever licence he chose rather than ours. Download it yourself from
either link above — it is free — and drop it in this folder.

Take **dimensions and approach** from it freely. Do not copy geometry wholesale
into anything published.

## Which plates to print

The download contains five plates, and two of them are for the wrong servo:

| Plate | Contents | Print? |
| --- | --- | --- |
| 01 | `SG90 - A` | No |
| 02 | `SG90 - B` | No |
| 03 | `MG90s - A` | **Yes** |
| 04 | `MG90s - B` | **Yes** |
| 05 | small part | **Yes** |

This build uses **MG90S** servos — see [docs/parts.md](../../docs/parts.md) — so
plates 01 and 02 get deleted. The two variants exist because the servo bodies
differ dimensionally; printing the SG90 plates would waste roughly half the
19.4 h quoted for the full set and produce parts the servos do not fit.

Cogley's own profile is 0.2 mm layer, 2 walls, 15% infill. Check the printer
selected in Bambu Studio matches the machine actually being used before slicing.
