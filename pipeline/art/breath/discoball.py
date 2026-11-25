# 02 i am a party: a real mirror ball for beside the title. Rows of square mirror tiles on a sphere (as the real ones
# are built: each row holds as many tiles as its circumference allows), a dark room with a few hard lights, rendered
# in Cycles; discoball_ink.py cuts the render into the shirt's flat inks.
#   blender -b --factory-startup -P pipeline/art/breath/discoball.py -- <out.png> [px]
import bpy, bmesh, math, sys, mathutils
argv = sys.argv[sys.argv.index("--") + 1:]
OUT = argv[0]; PX = int(argv[1]) if len(argv) > 1 else 800
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
R, T, GAP = 1.0, 0.13, 0.014                       # radius, tile, grout (the grout is never printed; the tiles read by tone)
bm = bmesh.new()
rows = int(math.pi * R / T)
for i in range(rows):
    lat = -math.pi / 2 + (i + 0.5) * math.pi / rows
    n = max(1, int(2 * math.pi * R * math.cos(lat) / T))
    for k in range(n):
        lon = (k + 0.5) * 2 * math.pi / n + (i % 2) * math.pi / n
        nrm = mathutils.Vector((math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)))
        east = mathutils.Vector((-math.sin(lon), math.cos(lon), 0)); north = nrm.cross(east)
        c = nrm * R; h = (T - GAP) / 2
        vs = [bm.verts.new(c + east * a + north * b) for a, b in ((-h, -h), (h, -h), (h, h), (-h, h))]
        bm.faces.new(vs)
me = bpy.data.meshes.new("tiles"); bm.to_mesh(me); NT = len(me.polygons)
ca = me.color_attributes.new("tid", "FLOAT_COLOR", "FACE")
for i in range(NT): ca.data[i].color = (((i + 1) % 256) / 255, ((i + 1) // 256) / 255, 0, 1)
tiles = bpy.data.objects.new("tiles", me); sc.collection.objects.link(tiles)
mirror = bpy.data.materials.new("mirror"); mirror.use_nodes = True
b = mirror.node_tree.nodes["Principled BSDF"]; b.inputs["Metallic"].default_value = 1; b.inputs["Roughness"].default_value = 0.12
b.inputs["Base Color"].default_value = (0.9, 0.9, 0.9, 1); tiles.data.materials.append(mirror)
# the grout: a dark core just under the tiles
bpy.ops.mesh.primitive_uv_sphere_add(radius=R * 0.985, segments=64, ring_count=32); core = bpy.context.object
dark = bpy.data.materials.new("grout"); dark.use_nodes = True
dark.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.01, 0.01, 0.01, 1); core.data.materials.append(dark)
bpy.ops.object.shade_smooth()
# a dark room with a few hard lights for the tiles to throw back
# the room the tiles reflect: patches of light and dark all round (a club: lamps, screens, people, dark walls), so
# every tile throws back something different
w = bpy.data.worlds.new("room"); w.use_nodes = True; wn = w.node_tree.nodes; wl = w.node_tree.links; sc.world = w
tc = wn.new("ShaderNodeTexCoord"); nz = wn.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 5.0
nz.inputs["Detail"].default_value = 3.0; nz.inputs["Roughness"].default_value = 0.6
ramp = wn.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].position = 0.42; ramp.color_ramp.elements[1].position = 0.62
wl.new(tc.outputs["Generated"], nz.inputs["Vector"]); wl.new(nz.outputs["Fac"], ramp.inputs["Fac"])
# and a key light up and to the left of the camera: the tiles facing it blaze, the far side falls to dark, so it reads round
dot = wn.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"; dot.inputs[1].default_value = (-0.55, -0.55, 0.63)
wl.new(tc.outputs["Generated"], dot.inputs[0])
key = wn.new("ShaderNodeMapRange"); key.inputs["From Min"].default_value = -0.2; key.inputs["From Max"].default_value = 1.0
key.inputs["To Min"].default_value = 0.08; key.inputs["To Max"].default_value = 1.6; wl.new(dot.outputs["Value"], key.inputs["Value"])
mul = wn.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs["Factor"].default_value = 1.0
wl.new(ramp.outputs["Color"], mul.inputs[6]); wl.new(key.outputs["Result"], mul.inputs[7])
# a blue wash from low on the right (a screen, a stage light): the tiles facing it throw back the brand blue
dot2 = wn.new("ShaderNodeVectorMath"); dot2.operation = "DOT_PRODUCT"; dot2.inputs[1].default_value = (0.7, -0.35, -0.6)
wl.new(tc.outputs["Generated"], dot2.inputs[0])
bl = wn.new("ShaderNodeMapRange"); bl.inputs["From Min"].default_value = 0.5; bl.inputs["From Max"].default_value = 0.9
wl.new(dot2.outputs["Value"], bl.inputs["Value"])
tint = wn.new("ShaderNodeMix"); tint.data_type = "RGBA"; tint.inputs[7].default_value = (0.42, 0.55, 1.0, 1)
wl.new(bl.outputs["Result"], tint.inputs["Factor"]); wl.new(mul.outputs[2], tint.inputs[6])
wl.new(tint.outputs[2], wn["Background"].inputs["Color"]); wn["Background"].inputs["Strength"].default_value = 1.4
em = bpy.data.materials.new("lamp"); em.use_nodes = True; nt = em.node_tree; nt.nodes.clear()
e = nt.nodes.new("ShaderNodeEmission"); e.inputs["Strength"].default_value = 40; o = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(e.outputs[0], o.inputs[0])
for (x, y, z, s) in [(-3, -6, 4, 1.6), (4, -5, 2.5, 1.0), (-1, -7, -1.5, 0.7), (2.5, -4, 5.5, 0.6), (-5, -2, 0.5, 0.8)]:
    bpy.ops.mesh.primitive_plane_add(size=s, location=(x, y, z)); p = bpy.context.object
    p.rotation_euler = (mathutils.Vector((0, 0, 0)) - p.location).to_track_quat("Z", "Y").to_euler(); p.data.materials.append(em)
cam = bpy.data.cameras.new("cam"); cam.type = "ORTHO"; cam.ortho_scale = 2.08
co = bpy.data.objects.new("cam", cam); co.location = (0, -10, 0.6); sc.collection.objects.link(co)
co.rotation_euler = (mathutils.Vector((0, 0, 0)) - co.location).to_track_quat("-Z", "Y").to_euler(); sc.camera = co
sc.render.engine = "CYCLES"; sc.cycles.samples = 48; sc.cycles.device = "CPU"
sc.render.resolution_x = sc.render.resolution_y = PX; sc.render.film_transparent = True
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"; sc.render.filepath = OUT
sc.view_settings.view_transform = "Standard"
bpy.ops.render.render(write_still=True); print("ball ok", OUT)
# second pass: which tile each pixel belongs to (flat id colours, no filtering, no colour management), so the ink step
# can give every tile exactly one tone taken from its own reflection
idm = bpy.data.materials.new("tid"); idm.use_nodes = True; nt = idm.node_tree; nt.nodes.clear()
at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "tid"; e = nt.nodes.new("ShaderNodeEmission")
o = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(at.outputs["Color"], e.inputs["Color"]); nt.links.new(e.outputs[0], o.inputs[0])
tiles.data.materials[0] = idm
blk = bpy.data.materials.new("blk"); blk.use_nodes = True; nt = blk.node_tree; nt.nodes.clear()
e = nt.nodes.new("ShaderNodeEmission"); e.inputs["Color"].default_value = (0, 0, 0, 1); o = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(e.outputs[0], o.inputs[0])
core.data.materials[0] = blk
for ob in sc.objects:
    if ob.name.startswith("Plane"): ob.hide_render = True
w2 = bpy.data.worlds.new("none"); w2.use_nodes = True; w2.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1); sc.world = w2
sc.cycles.samples = 1; sc.cycles.use_denoising = False; sc.cycles.filter_width = 0.01; sc.cycles.max_bounces = 0
sc.render.dither_intensity = 0; sc.view_settings.view_transform = "Raw"; sc.render.filepath = OUT.replace(".png", "-id.png")
bpy.ops.render.render(write_still=True); print("ids ok", sc.render.filepath, NT)
