# fast clay check of the drape (workbench), front and side
import bpy, sys, math
out = sys.argv[sys.argv.index("--") + 1]
sc = bpy.context.scene; sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "SINGLE"
sc.display.shading.single_color = (0.6, 0.6, 0.62); sc.display.shading.show_cavity = True
sc.render.resolution_x, sc.render.resolution_y = 700, 800
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 50
for name, loc in (("front", (0, -2.6, 1.12)), ("side", (2.6, -0.2, 1.12)), ("back", (0, 2.6, 1.12))):
    cam.location = loc
    d = __import__("mathutils").Vector((0, 0, 1.12)) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{out}-{name}.png"; bpy.ops.render.render(write_still=True)
