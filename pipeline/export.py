# blender -b tee-drape.blend -P export.py -- <outdir>
# Web export of the draped tee: GLB mesh (outer fabric + plain inner shell), baked ambient occlusion,
# and the fit numbers measured on the hidden body.
import bpy, bmesh, sys, os, json, math
from mathutils import Vector
OUT = sys.argv[sys.argv.index("--") + 1]; os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene; tee = bpy.data.objects["tee"]; body = bpy.data.objects["body"]; rig = bpy.data.objects["rig"]
for o in sc.objects: o.select_set(False)
bm = bmesh.new(); bm.from_mesh(tee.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0008)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(tee.data); bm.free()
for p in tee.data.polygons: p.use_smooth = True

# ---------- fit numbers ----------
dg = bpy.context.evaluated_depsgraph_get()
def verts(ob):
    me = ob.evaluated_get(dg).to_mesh(); v = [ob.matrix_world @ x.co for x in me.vertices]; ob.evaluated_get(dg).to_mesh_clear(); return v
BV, TV = verts(body), verts(tee)
def hull_len(pts):
    pts = sorted(set(pts))
    def cr(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    h = lo[:-1] + up[:-1]; return sum(math.dist(h[i], h[(i + 1) % len(h)]) for i in range(len(h)))
zs = [v.z for v in BV]; H = max(zs) - min(zs); zc = min(zs) + 0.73 * H
# body chest is measured standing in rest pose (arms out of the way), the way a tailor measures it
rig.data.pose_position = "REST"; bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); BR = verts(body)
rig.data.pose_position = "POSE"; bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
band = lambda V, z, xmax: [(v.x, v.y) for v in V if abs(v.z - z) < 0.006 and abs(v.x) < xmax]
body_chest = hull_len(band(BR, zc, 0.2)) * 100
import sys as _s; _s.path.insert(0, os.path.dirname(bpy.data.filepath)); from pattern import SIZE
tee_chest = SIZE["chest"] * 2          # garment chest is cut, not draped: UC22 M = 2 x 55.9 cm
crotch = min(v.z for v in BV if abs(v.x) < 0.012 and 0.55 < v.z < 1.0)
hem = min(v.z for v in TV if abs(v.x) < 0.2)
elbow = rig.matrix_world @ rig.pose.bones["lowerarm01.L"].head
sleeve = [v for v in TV if v.x > 0.25]
sleeve_end = min(sleeve, key=lambda v: (v - elbow).length)   # sleeve opening point nearest the elbow
fit = {"size": "M", "body": {"height_cm": round(H * 100), "chest_cm": round(body_chest)},
       "chest_ease_cm": round(tee_chest - body_chest), "hem_below_crotch_cm": round((crotch - hem) * 100),
       "sleeve_above_elbow_cm": round((sleeve_end - elbow).length * 100)}
print("FIT", json.dumps(fit)); json.dump(fit, open(os.path.join(OUT, "fit.json"), "w"), indent=1)

# ---------- bake ambient occlusion into the atlas UVs (outer surface, body hidden) ----------
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 64
sc.render.threads_mode = "FIXED"; sc.render.threads = 2
img = bpy.data.images.new("ao", 2048, 778, alpha=False)
m = bpy.data.materials.new("bake"); m.use_nodes = True; n = m.node_tree.nodes.new("ShaderNodeTexImage"); n.image = img
m.node_tree.nodes.active = n; tee.data.materials.clear(); tee.data.materials.append(m)
bpy.context.view_layer.objects.active = tee; tee.select_set(True)
sc.render.bake.margin = 8; sc.world = sc.world or bpy.data.worlds.new("w")
bpy.ops.object.bake(type="AO")
img.filepath_raw = os.path.join(OUT, "ao.png"); img.file_format = "PNG"; img.save()

# ---------- mesh: 2-layer hems/collar thickness, smooth once, plain inner shell ----------
inner = bpy.data.materials.new("inner"); tee.data.materials.clear()
outer = bpy.data.materials.new("outer"); tee.data.materials.append(outer); tee.data.materials.append(inner)
so = tee.modifiers.new("thick", "SOLIDIFY"); so.thickness = 0.0032; so.offset = 0; so.use_even_offset = True; so.material_offset = 1
if "stiff" in tee.vertex_groups: so.vertex_group = "stiff"; so.thickness_vertex_group = 0.5
tee.modifiers.new("sub", "SUBSURF").levels = 1
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "tee.glb"), use_selection=True, export_apply=True, export_yup=True,
                          export_materials="PLACEHOLDER", export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7)
print("exported", OUT)
