# blender -b --factory-startup -P body.py -- out.blend [height_cm chest_cm]
# Real human body (MakeHuman / MPFB, CC0 assets) with the default rig, sized to a target height and chest girth.
import bpy, sys, math, addon_utils
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
OUT = a[0]; H = float(a[1]) if len(a) > 1 else 170.0; CHEST = float(a[2]) if len(a) > 2 else 94.0
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService

def build(macro):
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    b = HumanService.create_human(macro_detail_dict=macro)
    return b
def girth_at(ob, z):
    # convex-ish girth: slice the evaluated torso at height z, hull perimeter of the points near the plane
    dg = bpy.context.evaluated_depsgraph_get(); me = ob.evaluated_get(dg).to_mesh()
    pts = []
    for e in me.edges:
        p, q = ob.matrix_world @ me.vertices[e.vertices[0]].co, ob.matrix_world @ me.vertices[e.vertices[1]].co
        if (p.z - z) * (q.z - z) < 0:
            t = (z - p.z) / (q.z - p.z); c = p.lerp(q, t)
            if abs(c.x) < 0.2: pts.append((c.x, c.y))   # torso only, arms excluded
    ob.evaluated_get(dg).to_mesh_clear()
    pts = sorted(set(pts))
    if len(pts) < 3: return 0
    def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    h = lo[:-1] + up[:-1]
    return sum(math.dist(h[i], h[(i + 1) % len(h)]) for i in range(len(h))) * 100
def measure(b):
    dg = bpy.context.evaluated_depsgraph_get(); me = b.evaluated_get(dg).to_mesh()   # shape keys + helper mask applied
    zs = [(b.matrix_world @ v.co).z for v in me.vertices]; b.evaluated_get(dg).to_mesh_clear()
    top = max(zs) - min(zs); h = top * 100
    # chest girth at nipple level (73 % of height); higher slices start cutting into the deltoids
    best = girth_at(b, top * 0.73)
    return h, best

macro = TargetService.get_default_macro_info_dict()
macro.update({"gender": 1.0, "age": 0.5, "muscle": 0.5, "weight": 0.55, "proportions": 0.5, "height": 0.5})
# South Asian: MakeHuman has no Indian base, so blend its three ethnic shape sets
# (caucasian skull/limb proportions, softer asian torso, a little african) and set the measurements from Indian data
macro["race"] = {"asian": 0.3, "caucasian": 0.55, "african": 0.15}
# fit height then chest with a few secant steps
for it in range(6):
    b = build(macro); h, c = measure(b)
    print(f"iter {it}: height {h:.1f} chest {c:.1f}  (h={macro['height']:.3f} w={macro['weight']:.3f})", flush=True)
    if abs(h - H) < 0.6 and abs(c - CHEST) < 0.8: break
    macro["height"] = min(1, max(0, macro["height"] + (H - h) / 105))
    macro["weight"] = min(1, max(0, macro["weight"] + (CHEST - c) / 12))   # weight moves chest girth only ~3 cm per unit
rig = HumanService.add_builtin_rig(b, "default")
b.name = "body"; rig.name = "rig"
print("bones", [bn.name for bn in rig.data.bones][:60])
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("saved", OUT, "height", round(h, 1), "chest", round(c, 1))
