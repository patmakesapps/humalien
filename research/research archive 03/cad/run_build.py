"""Headless build + gate + export.  No socket, no GUI, no addons.

    "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b \
        --factory-startup -P C:/Humalien/cad/run_build.py

The BlenderMCP socket drops on anything that runs much past two minutes, and
a dropped reply is indistinguishable from a crash - twice it had finished and
once it had not.  This route cannot lose the answer: everything goes to
gate.txt on disk, so the result survives whatever happens to the connection.

Nothing here opens or saves a .blend.  desk_bot.build() reconstructs every
part from the constants at the top of desk_bot.py, so an empty factory scene
is all it needs.
"""
import sys
import io
import os
import contextlib
import traceback

import bpy

CAD = r"C:\Humalien\cad"
LOG = (r"C:\Users\patri\AppData\Local\Temp\claude\C--Humalien"
       r"\cbfc8294-2f7e-4efa-9744-cce0af3927be\scratchpad\gate.txt")

if CAD not in sys.path:
    sys.path.append(CAD)

# factory startup ships a cube, a camera and a light; none of them belong in
# a part file and the cube would land in an export by accident one day
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)

buf = io.StringIO()
ok = None
try:
    import desk_bot
    with contextlib.redirect_stdout(buf):
        ok = desk_bot.build()
        if "--export" in sys.argv:
            names = tuple(a for a in sys.argv[sys.argv.index("--export") + 1:]
                          if not a.startswith("-")) or ("DB_chassis",)
            desk_bot.export_stl(names=names)
except Exception:
    buf.write("\n" + traceback.format_exc())

os.makedirs(os.path.dirname(LOG), exist_ok=True)
with io.open(LOG, "w", encoding="utf-8") as fh:
    fh.write("ok = %s\n\n%s" % (ok, buf.getvalue()))
print("\n=== gate ===")
print(buf.getvalue())
print("ok =", ok)
