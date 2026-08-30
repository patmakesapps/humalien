"""Build headless and save a fresh .blend to inspect in the GUI.

    blender.exe -b --factory-startup -P cad/make_blend.py -- <out.blend>

Why this exists: the BlenderMCP socket drops on anything past ~2 minutes, and
a full build is well past that.  Rebuilding inside the user's open session is
therefore unreliable, and screenshots are no substitute for being able to
orbit a part.  So the build runs here, where nothing can interrupt it, and
lands in a file that can just be opened.

It will not write desktop_bot_v1.blend.  That is the open session; a headless
process overwriting it is the silent clobber this project has been bitten by
before.
"""
import sys
import bpy

CAD = r"C:\Humalien\cad"
if CAD not in sys.path:
    sys.path.append(CAD)

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
dest = argv[0] if argv else r"C:\Humalien\desk_bot_current.blend"
if dest.lower().replace("/", "\\").endswith("desktop_bot_v1.blend"):
    raise SystemExit("refusing to overwrite the open session file")

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)

import desk_bot
ok = desk_bot.build()
desk_bot.pose(pan=0, nod=0, arm_l=-8, arm_r=-8)

# proxies off by default so the printed parts read clearly; unhide in the
# outliner to check packaging
for ob in bpy.data.collections[desk_bot.COLL].objects:
    ob.hide_set(ob.name.startswith(("PX_", "SV_")))

bpy.ops.wm.save_as_mainfile(filepath=dest, copy=True)
print("gate ok =", ok)
print("saved", dest)
