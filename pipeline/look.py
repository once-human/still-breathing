# VIEW=full|face|hand|back|legs OUTP=<png> PERSON=<person.glb> SCENE=show GLB=<tee stand.glb> \
#   blender -b --factory-startup -P look.py -- <design> <tee> a0 <unused.png> <samples>
# A look check of a person (human.py) on the farm: render.py builds its show scene without rendering (DRY), then a
# close camera on one part of the person, on a plain dark ground, a small picture.
import bpy, os, sys
from mathutils import Vector
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render.py")
os.environ["DRY"] = "1"
__file__ = R
exec(compile(open(R).read(), R, "exec"))
sc = bpy.context.scene; cam = sc.camera
V = os.environ.get("VIEW", "full"); F = 0.35
EYE = float(os.environ.get("EYE_Z", "1.5"))          # the person's eye height above their feet
views = {  # pos, aim, lens
    "full": ((0.2, -2.85, F + 1.1), (0, 0, F + 0.99), 85),
    "face": ((0.25, -1.2, F + EYE), (0, 0, F + EYE - 0.03), 135),
    "hand": ((0.75, -1.1, F + 0.85), (0.27, 0, F + 0.8), 135),
    "back": ((-0.6, 1.3, F + EYE - 0.05), (0, 0, F + EYE - 0.05), 100),
    "legs": ((0.3, -1.6, F + 0.7), (0, 0, F + 0.7), 85),
}
p, a, lens = views[V]
cam.location = p; cam.data.lens = lens; cam.data.dof.use_dof = False
cam.rotation_euler = (Vector(a) - Vector(p)).to_track_quat("-Z", "Y").to_euler()
sc.render.film_transparent = False
sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.055, 1)
sc.render.filepath = os.environ["OUTP"]
bpy.ops.render.render(write_still=True)
