# blender -b tee-drape.blend -P render.py -- <design> <tee> <view front|back> <out.png> [samples]
# GLB=<tee.glb> blender -b --factory-startup -P render.py -- ...   renders a published fit-pipeline tee instead
#   (already thick and smoothed; textures are the neck-anchored atlases texture.py writes next to this script)
import bpy, bmesh, sys, math
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
design, tee_col, view, out = a[:4]; samples = int(a[4]) if len(a) > 4 else 128
import os
GLB = os.environ.get("GLB")
ROOT = os.path.dirname(os.path.abspath(__file__)) if GLB else os.path.dirname(bpy.data.filepath)   # textures
sc = bpy.context.scene
if GLB:
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    bpy.ops.import_scene.gltf(filepath=GLB)
    parts = [o for o in sc.objects if o.type == "MESH"]
    for o in sc.objects: o.select_set(o in parts)
    bpy.context.view_layer.objects.active = parts[0]
    if len(parts) > 1: bpy.ops.object.join()
    tee = bpy.context.view_layer.objects.active; tee.name = "tee"
    if tee.parent: tee.matrix_world = tee.matrix_world.copy(); tee.parent = None
    for p in tee.data.polygons: p.use_smooth = True
    tee.data.uv_layers[0].name = "UV"
else:
    tee = bpy.data.objects["tee"]
    # clean normals after the seam weld, then cloth thickness and smoothing
    bm = bmesh.new(); bm.from_mesh(tee.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0008)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(tee.data); bm.free()
    for p in tee.data.polygons: p.use_smooth = True
    # hems and rib collar are two layers of fabric: twice the thickness of the single jersey body
    so = tee.modifiers.new("thick", "SOLIDIFY"); so.thickness = 0.0032; so.offset = 0; so.use_even_offset = True
    if "stiff" in tee.vertex_groups: so.vertex_group = "stiff"; so.thickness_vertex_group = 0.5
    sub = tee.modifiers.new("sub", "SUBSURF"); sub.levels = 1; sub.render_levels = 2
# ---- material: cotton jersey + DTG ink ----
m = bpy.data.materials.new("jersey"); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; L = nt.links
for n in list(N): N.remove(n)
o = N.new("ShaderNodeOutputMaterial"); b = N.new("ShaderNodeBsdfPrincipled")
L.new(b.outputs[0], o.inputs[0])
uv = N.new("ShaderNodeUVMap"); uv.uv_map = "UV"
img = N.new("ShaderNodeTexImage"); img.image = bpy.data.images.load(f"{ROOT}/atlas-{design}-{tee_col}.png"); img.interpolation = "Cubic"
ink = N.new("ShaderNodeTexImage"); ink.image = bpy.data.images.load(f"{ROOT}/inkmask-{design}-{tee_col}.png"); ink.image.colorspace_settings.name = "Non-Color"
L.new(uv.outputs[0], img.inputs[0]); L.new(uv.outputs[0], ink.inputs[0])
# heather grain: tiny brightness variation in the yarn
tc = N.new("ShaderNodeTexCoord"); noise = N.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 900; noise.inputs["Detail"].default_value = 2
L.new(tc.outputs["Object"], noise.inputs["Vector"])
grain = N.new("ShaderNodeMapRange"); grain.inputs[3].default_value = 0.93; grain.inputs[4].default_value = 1.06; L.new(noise.outputs[0], grain.inputs[0])
mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1.0
L.new(img.outputs[0], mul.inputs[6]); L.new(grain.outputs[0], mul.inputs[7]); L.new(mul.outputs[2], b.inputs["Base Color"])
# roughness: cotton 0.92, fresh DTG ink 0.6 (cured ink film is smoother than the yarn)
rr = N.new("ShaderNodeMapRange"); rr.inputs[3].default_value = 0.92; rr.inputs[4].default_value = 0.6; L.new(ink.outputs[0], rr.inputs[0]); L.new(rr.outputs[0], b.inputs["Roughness"])
# sheen is the cotton fuzz: only on bare fabric. Over the ink it laid a white haze that washed the print out
sh = N.new("ShaderNodeMapRange"); sh.inputs[3].default_value = 0.35; sh.inputs[4].default_value = 0.0; L.new(ink.outputs[0], sh.inputs[0]); L.new(sh.outputs[0], b.inputs["Sheen Weight"])
b.inputs["Sheen Roughness"].default_value = 0.3
b.inputs["Specular IOR Level"].default_value = 0.25
# knit relief: real single-jersey loop structure (knit.png, 11.4 x 11.1 mm tile) on the panel UVs, plus yarn fuzz
kn = N.new("ShaderNodeTexImage"); kn.image = bpy.data.images.load(f"{ROOT}/knit.png"); kn.image.colorspace_settings.name = "Non-Color"
aw, ah = img.image.size[0] / 40, img.image.size[1] / 40   # atlas in cm (40 px/cm)
mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (aw / 1.14, ah / 1.11, 1)
L.new(uv.outputs[0], mp.inputs[0]); L.new(mp.outputs[0], kn.inputs[0])
mix = N.new("ShaderNodeMix"); mix.data_type = "FLOAT"; mix.inputs[0].default_value = 0.15; L.new(kn.outputs[0], mix.inputs[2]); L.new(noise.outputs[0], mix.inputs[3])
bump = N.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.5; bump.inputs["Distance"].default_value = 0.0003
L.new(mix.outputs[0], bump.inputs["Height"])
# construction relief from texture.py: rib collar ridges, double-needle hems, cover stitches, seams (base 128 = flat)
det = N.new("ShaderNodeTexImage"); det.image = bpy.data.images.load(f"{ROOT}/detail-M.png" if GLB else f"{ROOT}/detail.png"); det.image.colorspace_settings.name = "Non-Color"; det.interpolation = "Cubic"
L.new(uv.outputs[0], det.inputs[0])
bump2 = N.new("ShaderNodeBump"); bump2.inputs["Strength"].default_value = 0.9; bump2.inputs["Distance"].default_value = 0.0012
L.new(det.outputs[0], bump2.inputs["Height"]); L.new(bump.outputs[0], bump2.inputs["Normal"]); L.new(bump2.outputs[0], b.inputs["Normal"])
tee.data.materials.clear(); tee.data.materials.append(m)
for p in tee.data.polygons: p.material_index = 0
# ---- studio: seamless sweep, three softboxes ----
bg = (0.52, 0.515, 0.505) if tee_col == "black" else (0.42, 0.42, 0.425)   # studio grey like Qikink's shots, under Khronos neutral
prof = [(y, 0.0) for y in [-6, -1, 0.3]] + [(0.3 + 0.6 * math.sin(t), 0.6 - 0.6 * math.cos(t)) for t in [k / 10 * math.pi / 2 for k in range(1, 11)]] + [(0.9, 4.0)]
vs, fs = [], []
for i, (y, z) in enumerate(prof):
    vs += [(-6, y + 0.6, z + 0.35), (6, y + 0.6, z + 0.35)]
    if i: fs.append((2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i))
sm = bpy.data.meshes.new("sweep"); sm.from_pydata(vs, [], fs); sw = bpy.data.objects.new("sweep", sm); sc.collection.objects.link(sw)
for p in sm.polygons: p.use_smooth = True
sw.modifiers.new("s", "SUBSURF").levels = 2
smat = bpy.data.materials.new("paper"); smat.use_nodes = True; sp = smat.node_tree.nodes["Principled BSDF"]; sp.inputs["Base Color"].default_value = bg + (1,); sp.inputs["Roughness"].default_value = 0.95
sm.materials.append(smat)
def area(name, loc, size, power, tint=(1, 1, 1)):
    l = bpy.data.lights.new(name, "AREA"); l.shape = "RECTANGLE"; l.size, l.size_y = size; l.energy = power; l.color = tint
    ob = bpy.data.objects.new(name, l); sc.collection.objects.link(ob); ob.location = loc
    ob.rotation_euler = (Vector((0, 0, 1.12)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); return ob
k = 1.0 if tee_col == "black" else 0.42   # a light tee needs less light or its folds burn out
area("key", (-1.5, -1.9, 2.1), (1.4, 1.8), 160 * k, (1, 0.98, 0.95))
area("fill", (1.9, -1.4, 1.3), (1.2, 1.6), 45 * k, (0.95, 0.97, 1))
area("rim", (0.6, 1.4, 2.4), (1.0, 1.0), 90 * k)
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[1].default_value = 0.03
# ---- camera ----
ANG = {"front": 0, "back": 180, "q": 35, "side": 90}[view] if not view.startswith("a") else float(view[1:])   # aNN = turntable angle
tee.rotation_euler[2] = math.radians(ANG)
if bpy.data.objects.get("body"): bpy.data.objects["body"].rotation_euler[2] = math.radians(ANG)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
# same camera as CAMERA in src/lib/viewer/scene.ts (three y-up -> Blender z-up), so a frame lines up with the live view
cam.data.lens = 85; cam.location = (0.2, -2.85, 1.21)
cam.rotation_euler = (Vector((0, 0, 1.09)) - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.dof.use_dof = True; cam.data.dof.focus_distance = 2.75; cam.data.dof.aperture_fstop = 5.6
# ---- render ----
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
# DEVICE=OPTIX or CUDA renders on the GPU (Colab T4, Kaggle); default CPU (laptop, GitHub runners)
if os.environ.get("DEVICE", "CPU") != "CPU":
    cp = bpy.context.preferences.addons["cycles"].preferences; cp.compute_device_type = os.environ["DEVICE"]; cp.get_devices()
    for d in cp.devices: d.use = d.type != "CPU"
    sc.cycles.device = "GPU"
sc.cycles.samples = samples; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 6; sc.render.threads_mode = "FIXED"; sc.render.threads = int(os.environ.get("THREADS", 3)); sc.view_settings.view_transform = "Khronos PBR Neutral"   # keeps base colours true (AgX desaturated the blue and cream)
sc.render.resolution_x, sc.render.resolution_y = int(os.environ.get("W", 1100)), int(os.environ.get("H", 1400)); sc.render.filepath = out
if os.environ.get("TRANSPARENT"):   # web stills: tee only, composited over the page colour in the viewer
    sc.render.film_transparent = True; bpy.data.objects["sweep"].hide_render = True
    sc.render.image_settings.color_mode = "RGBA"
bpy.ops.render.render(write_still=True)
