"""Headless workbench render, for looking at a part without the socket.

    blender.exe -b --factory-startup -P cad/render.py -- \
        out.png  DB_dome,SV_arm_L  <az> <el> <dist>  <tx> <ty> <tz>

Workbench, not EEVEE: it matches what solid shading looks like in the
viewport, renders in a second or two, and needs no lights or world.

The trap this file exists to avoid: a new camera's clip_end defaults to 100,
the scene is in MILLIMETRES, and anything further than 100 mm away renders a
completely empty frame with no error at all.  clip_end is set to 100000 below
and should stay there.
"""
import sys
import math
import os

import bpy
from mathutils import Vector, Euler

CAD = r"C:\Humalien\cad"
if CAD not in sys.path:
    sys.path.append(CAD)

a = sys.argv[sys.argv.index("--") + 1:]
out = a[0]
show = set(a[1].split(",")) if len(a) > 1 and a[1] != "*" else None
az, el, dist = (float(a[2]), float(a[3]), float(a[4])) if len(a) > 4 \
    else (200.0, 70.0, 320.0)
target = Vector((float(a[5]), float(a[6]), float(a[7]))) if len(a) > 7 \
    else Vector((0.0, 0.0, 80.0))

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)

import desk_bot
desk_bot.build()
desk_bot.pose(pan=0, nod=0, arm_l=-8, arm_r=-8)

for ob in bpy.data.collections[desk_bot.COLL].objects:
    ob.hide_render = show is not None and ob.name not in show

cam_d = bpy.data.cameras.new("cam")
cam_d.clip_start, cam_d.clip_end = 1.0, 100000.0     # mm scene.  Do not remove.
cam_d.lens = 60.0
cam = bpy.data.objects.new("cam", cam_d)
bpy.context.scene.collection.objects.link(cam)
rot = Euler((math.radians(el), 0.0, math.radians(az)), "XYZ")
cam.location = target + (rot.to_matrix() @ Vector((0.0, 0.0, dist)))
cam.rotation_euler = rot
bpy.context.scene.camera = cam

sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light, sh.studio_light = "STUDIO", "Default"
sh.color_type = "MATERIAL"
sh.show_cavity = True
sh.cavity_type = "BOTH"
sc.render.resolution_x, sc.render.resolution_y = 1100, 760
sc.render.film_transparent = False
sc.render.image_settings.file_format = "PNG"
sc.render.filepath = out
os.makedirs(os.path.dirname(out), exist_ok=True)
bpy.ops.render.render(write_still=True)
print("wrote", out)
