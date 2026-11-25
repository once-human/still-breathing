# blender -b tee-drape.blend -P render.py -- <design> <tee> <view front|back> <out.png> [samples]
# GLB=<tee.glb> blender -b --factory-startup -P render.py -- ...   renders a published fit-pipeline tee instead
#   (already thick and smoothed; textures are the neck-anchored atlases texture.py writes next to this script)
# PERSON=<person.glb> SCENE=show ...   the shop shot as the 3D view opens on it: someone wearing the tee (human.py),
#   both lifted by FLOOR, framed by WEAR_CAMERA, lit by the show's lights (src/lib/viewer/scene.ts). The place stays
#   put and the camera walks round it (aNN = the viewer's yaw). Film is transparent; still_post.py lays the
#   stage picture in behind along the pinhole ray, as the path tracer does (its lens blur is already in it).
# PERSON=<person.glb> SCENE=hall ...   the same shot inside the hall itself: stage.py builds the show (its walls,
#   decks, truss, haze, crowd and lights) and the person stands on its floor in the middle (Blender z = 0, as
#   stage.py has it), so the depth, the haze and the lens blur behind them are real, not a picture.
import bpy, bmesh, sys, math
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
design, tee_col, view, out = a[:4]; samples = int(a[4]) if len(a) > 4 else 128
import os
GLB = os.environ.get("GLB")
PERSON = os.environ.get("PERSON"); SHOW = os.environ.get("SCENE") == "show"; HALL = os.environ.get("SCENE") == "hall"
FLOOR = 0.35   # scene.ts FLOOR: the person stands on the floor the fit pipeline's bodies stand on
LIFT = 0.0 if HALL else FLOOR   # stage.py's hall has its floor at z = 0
if HALL and os.environ.get("HALL_BLEND"):
    # the hall built once for the whole turntable (HALL_SAVE below), opened here
    bpy.ops.wm.open_mainfile(filepath=os.environ["HALL_BLEND"])
elif HALL:
    # stage.py's own build of the show, everything before its camera (it starts from an empty scene)
    sp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stage.py")
    code = open(sp).read(); code = code[:code.index("# ---------- LOOK=")]
    argv = sys.argv; sys.argv = [argv[0], "--", "show", out + ".exr"]
    exec(compile(code, sp, "exec"), {"__file__": sp, "__name__": "stage"})
    sys.argv = argv
    if os.environ.get("HALL_SAVE"):   # the farm builds it once (~8 min) and every frame opens it
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=os.environ["HALL_SAVE"], compress=True)
        print("hall saved", os.environ["HALL_SAVE"]); bpy.ops.wm.quit_blender()
if HALL:
    # stage.py keeps 1.9 m clear round the person; the camera walks a 2.8 m ring, so the crowd steps back to 3.6 m
    # (the people only: stage.py's empties that instance a body, and the phone a few of them hold up)
    gone = 0
    for o in list(bpy.data.objects):
        if o.type == "EMPTY" and o.instance_type == "COLLECTION" and o.name.startswith("p") and o.location.xy.length < 3.6:
            bpy.data.objects.remove(o); gone += 1
    for o in [o for o in bpy.data.objects if o.type == "MESH" and any(m and m.name.startswith("phone") for m in o.data.materials)]:
        b_ = bmesh.new(); b_.from_mesh(o.data)
        bmesh.ops.delete(b_, geom=[f for f in b_.faces if (o.matrix_world @ f.calc_center_median()).xy.length < 3.6], context="FACES")
        b_.to_mesh(o.data); b_.free()
    print("cleared round the person", gone, flush=True)
ROOT = os.path.dirname(os.path.abspath(__file__)) if GLB else os.path.dirname(bpy.data.filepath)   # textures
sc = bpy.context.scene
if GLB:
    if not HALL:
        for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=GLB)
    parts = [o for o in sc.objects if o.type == "MESH" and o not in before]
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
# ---- someone wearing it: skin (its maps beside the GLB, skin.py), jeans and eyes (colours per vertex) ----
person = []
if PERSON:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=PERSON)
    person = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    # the same surfaces as the path tracer's materials 4, 5, 6 (pt.wgsl.ts): F0 0.028 / 0.02 / 0.03 is
    # Specular IOR Level 0.35 / 0.25 / 0.375; the jeans carry the cotton sheen, the skin and eyes none
    LOOK = {"skin": (0.5, 0.35, 0.0), "jeans": (0.85, 0.25, 0.35), "eyes": (0.12, 0.375, 0.0)}
    for po in person:
        if po.parent: po.matrix_world = po.matrix_world.copy(); po.parent = None
        assert po.data.color_attributes, f"{po.name}: no painted colours (COLOR_0)"
        ca = po.data.color_attributes[0].name
        for i, slot in enumerate(po.data.materials):
            # human.py exports placeholder materials, so the glTF has none: the mesh names say which part it is
            nm = ((slot.name if slot else "") + " " + po.name + " " + po.data.name).lower()
            kind = "jeans" if "jean" in nm else "eyes" if "eye" in nm else "skin"
            r, spec, sheen = LOOK[kind]
            pm = bpy.data.materials.new(f"person-{kind}"); pm.use_nodes = True
            pb = pm.node_tree.nodes["Principled BSDF"]
            col = pm.node_tree.nodes.new("ShaderNodeVertexColor"); col.layer_name = ca
            pm.node_tree.links.new(col.outputs["Color"], pb.inputs["Base Color"])
            pb.inputs["Roughness"].default_value = r; pb.inputs["Specular IOR Level"].default_value = spec
            pb.inputs["Sheen Weight"].default_value = sheen; pb.inputs["Sheen Roughness"].default_value = 0.3
            if kind == "skin" and os.path.exists(PERSON[:-4] + "-skin.webp"):
                # the skin's maps (skin.py): colour, relief (R, G; green runs down the image, so it is turned for
                # Blender, whose V runs up) and roughness (B); and real subsurface light, red reaching furthest
                T = pm.node_tree; NN, LL = T.nodes, T.links
                uvn = NN.new("ShaderNodeUVMap"); uvn.uv_map = po.data.uv_layers[0].name
                ai = NN.new("ShaderNodeTexImage"); ai.image = bpy.data.images.load(PERSON[:-4] + "-skin.webp"); ai.interpolation = "Cubic"
                ri = NN.new("ShaderNodeTexImage"); ri.image = bpy.data.images.load(PERSON[:-4] + "-skin-n.webp"); ri.interpolation = "Cubic"
                ri.image.colorspace_settings.name = "Non-Color"
                for im in (ai, ri): LL.new(uvn.outputs[0], im.inputs[0])
                mul = NN.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1.0
                LL.new(col.outputs["Color"], mul.inputs[6]); LL.new(ai.outputs[0], mul.inputs[7]); LL.new(mul.outputs[2], pb.inputs["Base Color"])
                sep = NN.new("ShaderNodeSeparateColor"); LL.new(ri.outputs[0], sep.inputs[0])
                flip = NN.new("ShaderNodeMath"); flip.operation = "SUBTRACT"; flip.inputs[0].default_value = 1.0; LL.new(sep.outputs[1], flip.inputs[1])
                comb = NN.new("ShaderNodeCombineColor"); comb.inputs[2].default_value = 1.0
                LL.new(sep.outputs[0], comb.inputs[0]); LL.new(flip.outputs[0], comb.inputs[1])
                nm = NN.new("ShaderNodeNormalMap"); nm.uv_map = uvn.uv_map; LL.new(comb.outputs[0], nm.inputs["Color"])
                LL.new(nm.outputs[0], pb.inputs["Normal"]); LL.new(sep.outputs[2], pb.inputs["Roughness"])
                pb.subsurface_method = "RANDOM_WALK_SKIN"
                pb.inputs["Subsurface Weight"].default_value = 1.0
                pb.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.2)
                pb.inputs["Subsurface Scale"].default_value = 0.004
            po.data.materials[i] = pm
        po.location.z += LIFT
    tee.location.z += LIFT
# ---- TROUSERS=<blend> (trousers.py): the draped trousers in place of the person's own, in real denim: photographed
# denim from Poly Haven (CC0, pipeline/denim, 27 cm of cloth per image): a dark raw indigo under the off-white tee,
# a lighter blue wash under the black one
if PERSON and os.environ.get("TROUSERS"):
    for po in person:
        if "jean" in po.name.lower(): po.hide_render = True
    with bpy.data.libraries.load(os.environ["TROUSERS"]) as (src, dst):
        dst.objects = ["trousers"]
    trz = dst.objects[0]; sc.collection.objects.link(trz); trz.location.z += LIFT
    so_ = trz.modifiers.new("thick", "SOLIDIFY"); so_.thickness = 0.0022; so_.offset = 1
    sd_ = trz.modifiers.new("sub", "SUBSURF"); sd_.levels = sd_.render_levels = 1
    dn = os.path.join(os.path.dirname(os.path.abspath(__file__)), "denim", "denim_fabric_03" if tee_col == "cream" else "denim_fabric_04")
    # UVs at the cloth's own scale: one image = 27 cm of denim (a cube projection, the wales running up the leg)
    bpy.context.view_layer.objects.active = trz
    for o in sc.objects: o.select_set(o is trz)
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project(cube_size=0.27, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    tmat = bpy.data.materials.new("denim"); tmat.use_nodes = True
    TN, TL = tmat.node_tree.nodes, tmat.node_tree.links; tb = TN["Principled BSDF"]
    tuv = TN.new("ShaderNodeUVMap"); tuv.uv_map = trz.data.uv_layers[0].name
    def denim_map(kind, color):
        t = TN.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(f"{dn}-{kind}.jpg"); t.interpolation = "Cubic"
        if not color: t.image.colorspace_settings.name = "Non-Color"
        TL.new(tuv.outputs[0], t.inputs[0]); return t
    TL.new(denim_map("diff", True).outputs[0], tb.inputs["Base Color"])
    TL.new(denim_map("rough", False).outputs[0], tb.inputs["Roughness"])
    nmap = TN.new("ShaderNodeNormalMap"); nmap.uv_map = tuv.uv_map     # nor_gl: Blender's own convention
    TL.new(denim_map("nor", False).outputs[0], nmap.inputs["Color"]); TL.new(nmap.outputs[0], tb.inputs["Normal"])
    tb.inputs["Specular IOR Level"].default_value = 0.25
    tb.inputs["Sheen Weight"].default_value = 0.2; tb.inputs["Sheen Roughness"].default_value = 0.4
    trz.data.materials.clear(); trz.data.materials.append(tmat)
# ---- material: cotton jersey + ink ----
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
# roughness: cotton 0.92, fresh ink 0.6 (cured ink film is smoother than the yarn)
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
def area(name, loc, size, power, tint=(1, 1, 1), aim=(0, 0, 1.12)):
    l = bpy.data.lights.new(name, "AREA"); l.shape = "RECTANGLE"; l.size, l.size_y = size; l.energy = power; l.color = tint
    ob = bpy.data.objects.new(name, l); sc.collection.objects.link(ob); ob.location = loc
    ob.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); return ob
if not HALL: w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
if HALL:
    pass   # the hall's own lights and world (stage.py)
elif SHOW:
    # ---- the show: the place's own lights (scene.ts SCENES "show", three (x, y, z) -> Blender (x, -z, y)), no
    # sweep, the dim hall as the world light. The lamps light the person but are not seen: the picture shows them
    k = 0.6 if tee_col == "cream" else 1.0
    for name, (x, y, z), size, power, tint in [
        ("stage", (1.4, 5.85, 3.0), (0.4, 0.4), 760, (1, 0.8, 0.6)),
        ("beam", (-1.6, 5.85, 3.2), (0.2, 0.2), 360, (0.86, 0.91, 1)),
        ("spot", (-6.0, 4.6, 2.0), (0.3, 0.3), 390, (1, 0.72, 0.45)),
        ("foh", (-1.4, 3.5, -3.6), (0.8, 0.8), 480, (1, 0.86, 0.7)),
    ]:
        # scene.ts aims the places' lights at the chest, 1.1 m over the floor (the floor here is FLOOR up)
        area(name, (x, -z, y), size, power * k, tint, aim=(0, 0, FLOOR + 1.1)).visible_camera = False
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.0015, 0.0015, 0.002, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
else:
    # ---- studio: seamless sweep, three softboxes ----
    bg = (0.52, 0.515, 0.505) if tee_col == "black" else (0.42, 0.42, 0.425)   # studio grey like the maker's shots, under Khronos neutral
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
    k = 1.0 if tee_col == "black" else 0.42   # a light tee needs less light or its folds burn out
    area("key", (-1.5, -1.9, 2.1), (1.4, 1.8), 160 * k, (1, 0.98, 0.95))
    area("fill", (1.9, -1.4, 1.3), (1.2, 1.6), 45 * k, (0.95, 0.97, 1))
    area("rim", (0.6, 1.4, 2.4), (1.0, 1.0), 90 * k)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.03
# ---- camera ----
ANG = {"front": 0, "back": 180, "q": 35, "side": 90}[view] if not view.startswith("a") else float(view[1:])   # aNN = turntable angle
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 85; cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = 5.6
if PERSON:
    # WEAR_CAMERA in scene.ts, lifted with the person; the person stands still and the camera walks round them
    # (the viewer turns person and place together in front of a fixed camera: the same picture)
    a = math.radians(-ANG); x, y = 0.2, -2.85
    cam.location = (x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a), LIFT + 1.1)
    aim = Vector((0, 0, LIFT + 0.99)); cam.data.dof.focus_distance = 2.8
else:
    tee.rotation_mode = "XYZ"   # the glTF importer leaves objects in quaternion mode, which ignores rotation_euler
    tee.rotation_euler[2] = math.radians(ANG)
    if bpy.data.objects.get("body"): bpy.data.objects["body"].rotation_euler[2] = math.radians(ANG)
    # same camera as CAMERA in src/lib/viewer/scene.ts (three y-up -> Blender z-up), so a frame lines up with the live view
    cam.location = (0.2, -2.85, 1.21); aim = Vector((0, 0, 1.09)); cam.data.dof.focus_distance = 2.75
cam.rotation_euler = (aim - cam.location).to_track_quat("-Z", "Y").to_euler()
# ---- render ----
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
# DEVICE=OPTIX or CUDA renders on the GPU (Colab T4, Kaggle); default CPU (laptop, GitHub runners)
if os.environ.get("DEVICE", "CPU") != "CPU":
    cp = bpy.context.preferences.addons["cycles"].preferences; cp.compute_device_type = os.environ["DEVICE"]; cp.get_devices()
    for d in cp.devices: d.use = d.type != "CPU"
    sc.cycles.device = "GPU"
sc.cycles.samples = samples; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 6
if HALL:   # as stage.py renders the show: few bounces in the dark, one through the haze, adaptive
    cy = sc.cycles; cy.max_bounces = 6; cy.diffuse_bounces = 3; cy.glossy_bounces = 2; cy.transmission_bounces = 2
    cy.volume_bounces = 1; cy.volume_step_rate = 2.0; cy.sample_clamp_indirect = 4.0
    cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.012
    cy.caustics_reflective = cy.caustics_refractive = False
sc.render.threads_mode = "FIXED"; sc.render.threads = int(os.environ.get("THREADS", 3)); sc.view_settings.view_transform = "Khronos PBR Neutral"   # keeps base colours true (AgX desaturated the blue and cream)
sc.render.resolution_x, sc.render.resolution_y = int(os.environ.get("W", 1100)), int(os.environ.get("H", 1400)); sc.render.filepath = out
if os.environ.get("TRANSPARENT") or SHOW:   # web stills: tee only, over the page colour, or the stage laid in behind
    sc.render.film_transparent = True
    if bpy.data.objects.get("sweep"): bpy.data.objects["sweep"].hide_render = True
    sc.render.image_settings.color_mode = "RGBA"
if SHOW:   # the pinhole camera for still_post.py, which looks the stage picture up along each pixel's ray
    import json
    f = (aim - cam.location).normalized()
    json.dump({"pos": list(cam.location), "f": list(f), "tanHalf": 18 / cam.data.lens}, open(out + ".cam.json", "w"))
if not os.environ.get("DRY"): bpy.ops.render.render(write_still=True)
