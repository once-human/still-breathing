# blender -b --factory-startup -P stage.py -- <out.exr> [strip strips] [samples] [width]
# The show, as a 360 degree environment for the shop viewer: a dark hall, a low stage with an industrial backline,
# a few warm desk lamps and a row of white light bars, a big quiet screen, a truss of cool beams through haze,
# the crowd, and the hall behind (front of house, balcony). Built from boxes and planes here, nothing photographed.
# The camera stands where the person in the viewer stands, at chest height, facing the stage (Blender -Y).
# One horizontal strip per call, so the farm can split the frame across runners; stage_post.py stitches them.
import bpy, bmesh, sys, math, random
from mathutils import Vector, Matrix

a = sys.argv[sys.argv.index("--") + 1:]
OUT = a[0]
STRIP = int(a[1]) if len(a) > 1 else 0
STRIPS = int(a[2]) if len(a) > 2 else 1
SAMPLES = int(a[3]) if len(a) > 3 else 96
W = int(a[4]) if len(a) > 4 else 4096
EYE = 1.2   # camera height above the floor (the viewer's chest-height camera)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
col = sc.collection
rnd = random.Random(48)


# ---------- materials ----------
def mat(name, base=(0.03, 0.03, 0.03), rough=0.6, metal=0.0, emit=None, strength=0.0, spec=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*base, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if "Specular IOR Level" in p.inputs: p.inputs["Specular IOR Level"].default_value = spec
    if emit:
        p.inputs["Emission Color"].default_value = (*emit, 1)
        p.inputs["Emission Strength"].default_value = strength
    return m


def emission(name, colr, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (*colr, 1); e.inputs[1].default_value = strength
    nt.links.new(e.outputs[0], nt.nodes["Material Output"].inputs[0])
    return m


M_BLACK = mat("black", (0.012, 0.012, 0.012), 0.85)
M_FLOOR = mat("floor", (0.035, 0.034, 0.032), 0.32)               # sealed concrete: a soft sheen of the stage
M_STAGE = mat("stage", (0.02, 0.02, 0.02), 0.55)
M_CASE = mat("case", (0.025, 0.025, 0.026), 0.45)
M_ALU = mat("alu", (0.6, 0.6, 0.62), 0.35, metal=1.0)
M_TRUSS = mat("truss", (0.35, 0.35, 0.37), 0.4, metal=1.0)
M_CLOTH = mat("crowd", (0.03, 0.028, 0.027), 0.8)
M_SKIN = mat("skin", (0.12, 0.07, 0.045), 0.5)
M_WOOD = mat("desk", (0.06, 0.04, 0.03), 0.5)
M_SHADE = mat("shade", (0.05, 0.05, 0.05), 0.4, metal=0.6)
M_BULB = emission("bulb", (1.0, 0.62, 0.3), 60)
M_PHONE = emission("phone", (0.82, 0.88, 1.0), 2.2)
M_EXIT = emission("exit", (0.15, 1.0, 0.35), 3.0)
M_TUBE = emission("tube", (0.9, 0.94, 1.0), 9.0)


def add(ob, m=None):
    if m is not None:
        ob.data.materials.clear(); ob.data.materials.append(m)
    return ob


# every box, cylinder and sphere goes into one mesh per material (thousands of objects would take ages to build)
BAT = {}
def bm(m):
    if m not in BAT: BAT[m] = bmesh.new()
    return BAT[m]


def box(x, y, z, sx, sy, sz, m=M_BLACK, rot=0.0):
    """a box by its centre and full size"""
    M = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot, 4, "Z") @ Matrix.Diagonal((sx, sy, sz, 1))
    bmesh.ops.create_cube(bm(m), size=1, matrix=M)


def cyl(p0, p1, r, m, verts=12, r2=None):
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    M = Matrix.Translation((p0 + p1) / 2) @ Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
    bmesh.ops.create_cone(bm(m), cap_ends=True, segments=verts, radius1=r, radius2=r if r2 is None else r2, depth=d.length, matrix=M)


def sphere(c, r, m, seg=12, rings=8):
    bmesh.ops.create_uvsphere(bm(m), u_segments=seg, v_segments=rings, radius=r, matrix=Matrix.Translation(c))


def flush():
    for m, b in BAT.items():
        me = bpy.data.meshes.new(m.name); b.to_mesh(me); b.free()
        o = bpy.data.objects.new(m.name, me); col.objects.link(o); me.materials.append(m)
    BAT.clear()


def light(kind, loc, aim, power, colr, size=0.1, spot=None, blend=0.25):
    d = bpy.data.lights.new("l", kind); d.energy = power; d.color = colr
    if kind in ("POINT", "SPOT"): d.shadow_soft_size = size
    if kind == "AREA": d.size = size
    if kind == "SPOT": d.spot_size = math.radians(spot); d.spot_blend = blend; d.show_cone = False
    o = bpy.data.objects.new("l", d); col.objects.link(o); o.location = loc
    if aim is not None:
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = Vector((0, 0, -1)).rotation_difference((Vector(aim) - Vector(loc)).normalized())
    return o


# ---------- the hall ----------
HX, Y0, Y1, HZ = 22.0, -26.0, 38.0, 17.0
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, (Y0 + Y1) / 2, 0)); fl = bpy.context.object
fl.scale = (2 * HX, Y1 - Y0, 1); add(fl, M_FLOOR)
box(0, (Y0 + Y1) / 2, HZ + 0.2, 2 * HX, Y1 - Y0, 0.4)            # ceiling
box(-HX - 0.2, (Y0 + Y1) / 2, HZ / 2, 0.4, Y1 - Y0, HZ)           # side walls
box(HX + 0.2, (Y0 + Y1) / 2, HZ / 2, 0.4, Y1 - Y0, HZ)
box(0, Y0 - 0.2, HZ / 2, 2 * HX, 0.4, HZ)                         # behind the stage
box(0, Y1 + 0.2, HZ / 2, 2 * HX, 0.4, HZ)                         # back of the hall
# roof steel: a few dark beams catch the haze light
for y in range(int(Y0) + 4, int(Y1), 8):
    box(0, y, HZ - 0.5, 2 * HX, 0.3, 0.8, M_TRUSS)

# ---------- the stage: low deck, backline of flight cases, a long desk with lamps ----------
SY0, SY1, SZ = -11.5, -19.5, 1.4
box(0, (SY0 + SY1) / 2, SZ / 2, 22, SY0 - SY1, SZ, M_STAGE)
box(0, SY0 + 0.05, SZ / 2, 22, 0.1, SZ, M_BLACK)                  # the dark stage front
# barrier in front of the stage
for x in range(-11, 12):
    box(x, SY0 + 1.6, 0.55, 0.96, 0.08, 1.1, M_ALU)
# the desk (centre), with machines on it: small screens and pads glow faintly
box(0, -14.2, SZ + 0.45, 3.4, 0.9, 0.9, M_WOOD)
for i, x in enumerate((-1.2, -0.45, 0.35, 1.1)):
    box(x, -14.0, SZ + 0.93, 0.5, 0.35, 0.05, M_CASE)
    box(x, -14.1, SZ + 0.97, 0.38, 0.22, 0.01, emission(f"pad{i}", (1.0, 0.55, 0.25) if i % 2 else (0.85, 0.9, 1.0), 1.5))
# backline: stacks of flight cases with aluminium edges, left and right
for side in (-1, 1):
    for k in range(5):
        x = side * (3.2 + k * 1.45 + rnd.uniform(-0.15, 0.15))
        h = 0
        for j in range(rnd.randint(1, 3)):
            sz = rnd.uniform(0.6, 1.1); sx = rnd.uniform(1.0, 1.35)
            box(x, -16.8 + rnd.uniform(-0.6, 0.6), SZ + h + sz / 2, sx, 0.9, sz, M_CASE)
            for zz in (h, h + sz):
                box(x, -16.8 + 0.46, SZ + zz, sx + 0.02, 0.03, 0.03, M_ALU)
            h += sz
# desk lamps: warm bulbs under small shades, on the desk and on the cases
LAMPS = [(-1.55, -14.4, SZ + 0.9), (1.55, -14.3, SZ + 0.9), (-5.1, -16.4, SZ + 1.9), (4.6, -16.2, SZ + 2.2), (-8.0, -16.5, SZ + 1.3), (7.9, -16.6, SZ + 1.6)]
for i, (x, y, z) in enumerate(LAMPS):
    cyl((x, y, z), (x, y, z + 0.45), 0.012, M_SHADE)
    cyl((x, y + 0.01, z + 0.56), (x, y + 0.09, z + 0.42), 0.06, M_SHADE, 24, r2=0.16)
    sphere((x, y + 0.08, z + 0.44), 0.045, M_BULB)
    light("POINT", (x, y + 0.1, z + 0.4), None, 40, (1.0, 0.6, 0.3), size=0.05)

# the screen: a big, quiet field of warm light (no picture on it), brighter in the middle, dim at the edges
SCR_Y, SCR_W, SCR_H, SCR_Z = -19.9, 15.0, 8.4, 4.2
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, SCR_Y, SCR_Z + SCR_H / 2), rotation=(math.radians(90), 0, 0))
scr = bpy.context.object; scr.scale = (SCR_W, SCR_H, 1)
m = bpy.data.materials.new("screen"); m.use_nodes = True; nt = m.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["UV"], sep.inputs[0])
# radial falloff from the middle: 1 - ((u-.5)^2*1.6 + (v-.45)^2*2.4)
mu = nt.nodes.new("ShaderNodeMath"); mu.operation = "SUBTRACT"; mu.inputs[1].default_value = 0.5; nt.links.new(sep.outputs[0], mu.inputs[0])
mv = nt.nodes.new("ShaderNodeMath"); mv.operation = "SUBTRACT"; mv.inputs[1].default_value = 0.45; nt.links.new(sep.outputs[1], mv.inputs[0])
pu = nt.nodes.new("ShaderNodeMath"); pu.operation = "MULTIPLY"; nt.links.new(mu.outputs[0], pu.inputs[0]); nt.links.new(mu.outputs[0], pu.inputs[1])
pv = nt.nodes.new("ShaderNodeMath"); pv.operation = "MULTIPLY"; nt.links.new(mv.outputs[0], pv.inputs[0]); nt.links.new(mv.outputs[0], pv.inputs[1])
su = nt.nodes.new("ShaderNodeMath"); su.operation = "MULTIPLY_ADD"; su.inputs[1].default_value = 1.6; nt.links.new(pu.outputs[0], su.inputs[0])
sv = nt.nodes.new("ShaderNodeMath"); sv.operation = "MULTIPLY"; sv.inputs[1].default_value = 2.4; nt.links.new(pv.outputs[0], sv.inputs[0]); nt.links.new(sv.outputs[0], su.inputs[2])
fa = nt.nodes.new("ShaderNodeMath"); fa.operation = "SUBTRACT"; fa.inputs[0].default_value = 1.0; fa.use_clamp = True; nt.links.new(su.outputs[0], fa.inputs[1])
st = nt.nodes.new("ShaderNodeMath"); st.operation = "MULTIPLY_ADD"; st.inputs[1].default_value = 0.55; st.inputs[2].default_value = 0.04; nt.links.new(fa.outputs[0], st.inputs[0])
em = nt.nodes.new("ShaderNodeEmission"); em.inputs[0].default_value = (1.0, 0.86, 0.72, 1); nt.links.new(st.outputs[0], em.inputs[1])
nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs[0])
add(scr, m)
box(0, SCR_Y - 0.15, SCR_Z + SCR_H / 2, SCR_W + 0.4, 0.2, SCR_H + 0.4, M_BLACK)   # its frame

# light bars: a row of plain white tubes standing across the back of the stage
for i in range(14):
    x = -9.75 + i * 1.5
    cyl((x, -18.2, SZ), (x, -18.2, SZ + 2.6), 0.03, M_TUBE, 10)
light("AREA", (0, -18.0, SZ + 1.3), (0, -10, SZ + 1.3), 300, (0.9, 0.93, 1.0), size=2)

# ---------- truss over the stage: cool white beams down through the haze, warm pars on the backline ----------
def truss(y, z, x0, x1):
    s = 0.2
    for dy in (-s, s):
        for dz in (-s, s):
            cyl((x0, y + dy, z + dz), (x1, y + dy, z + dz), 0.025, M_TRUSS, 8)
    n = int((x1 - x0) / 0.5)
    for i in range(n):
        xa, xb = x0 + i * 0.5, x0 + (i + 1) * 0.5
        cyl((xa, y - s, z - s), (xb, y - s, z + s), 0.012, M_TRUSS, 6)
        cyl((xa, y + s, z - s), (xb, y + s, z + s), 0.012, M_TRUSS, 6)
    for x in (x0, x1):                                            # chain hoists up to the roof
        cyl((x, y, z + s), (x, y, HZ - 0.9), 0.01, M_TRUSS, 6)


TZ = 10.5
truss(-12.6, TZ, -11.5, 11.5)
truss(-18.6, TZ + 0.8, -11.5, 11.5)
for i in range(9):                                                 # moving heads on the front truss
    x = -10 + i * 2.5
    cyl((x, -12.6, TZ - 0.25), (x, -12.6, TZ - 0.6), 0.14, M_CASE, 16)
    # every other one down into the crowd, the rest fanned up and out over it
    tgt = (x * 0.55 + rnd.uniform(-2.5, 2.5), rnd.uniform(-9, 4), 0) if i % 2 == 0 else (x * 2.2, rnd.uniform(4, 18), rnd.uniform(9, 15))
    light("SPOT", (x, -12.6, TZ - 0.65), tgt, 9000, (0.88, 0.92, 1.0), size=0.05, spot=3.5, blend=0.25)
for i in range(7):                                                 # warm pars from the back truss onto the backline
    x = -9 + i * 3
    cyl((x, -18.6, TZ + 0.55), (x, -18.6, TZ + 0.2), 0.12, M_CASE, 16)
    light("SPOT", (x, -18.6, TZ + 0.15), (x * 0.8, -15.5, SZ), 1800, (1.0, 0.58, 0.28), size=0.1, spot=24, blend=0.5)
# low cool wash from the stage floor into the haze behind the artist (side light, edge on the backline)
for side in (-1, 1):
    light("SPOT", (side * 10.5, -14.5, SZ + 0.4), (side * 2, -15, 4), 1500, (0.8, 0.86, 1.0), size=0.1, spot=30, blend=0.6)

# house lights over the crowd, nearly out: a warm glow in the haze high up, nothing coloured
for (x, y) in ((-9, -2), (9, 6), (0, 16), (-6, 26), (7, 26)):
    light("POINT", (x, y, HZ - 1.2), None, 120, (1.0, 0.62, 0.34), size=0.3)

# ---------- front of house, behind the person: the desk, follow spots on a truss, the balcony ----------
FOH_Y = 21.0
box(0, FOH_Y, 0.5, 6, 3, 1.0, M_CASE)
box(0, FOH_Y + 1.2, 1.4, 6, 0.6, 1.8, M_CASE)
for i, x in enumerate((-2.2, -1.1, 0.0, 1.1, 2.2)):
    box(x, FOH_Y - 0.3, 1.08, 0.7, 0.45, 0.02, emission(f"desk{i}", (0.55, 0.7, 1.0) if i % 2 else (1.0, 0.78, 0.55), 0.8))
for x in (-2.6, 2.6):                                              # desk lamps at the console
    light("POINT", (x, FOH_Y - 0.5, 1.6), None, 12, (1.0, 0.62, 0.32), size=0.04)
truss(FOH_Y - 3, 9.5, -8, 8)
for x in (-5.5, 5.5):                                              # FOH spots: they light the crowd from behind
    cyl((x, FOH_Y - 3, 9.2), (x, FOH_Y - 3.6, 8.9), 0.16, M_CASE, 16)
    light("SPOT", (x, FOH_Y - 3.7, 8.85), (x * 0.3, -2, 1.2), 2400, (1.0, 0.86, 0.7), size=0.08, spot=9, blend=0.4)
# balcony front with its dim lamps and two green exit signs
box(0, 31, 5.2, 2 * HX, 1.2, 1.0, M_CASE)
for x in range(-20, 21, 4):
    light("POINT", (x, 30.3, 5.9), None, 6, (1.0, 0.6, 0.3), size=0.05)
for x in (-17, 17):
    box(x, Y1 - 0.05, 3.2, 0.45, 0.04, 0.2, M_EXIT)
# house sconces on the side walls, nearly out
for side in (-1, 1):
    for y in range(-6, 34, 8):
        light("POINT", (side * (HX - 0.5), y, 5.5), None, 8, (1.0, 0.55, 0.28), size=0.1)


# ---------- the crowd: people standing, some with their hands up, a few phones out ----------
def person(x, y, h, face, arms):
    s = h / 1.72
    fx, fy = math.cos(face), math.sin(face)          # facing
    rx, ry = -fy, fx                                 # across the shoulders
    cyl((x, y, 0), (x, y, 1.42 * s), 0.19 * s, M_CLOTH, 10)
    sphere((x, y, 1.58 * s), 0.105 * s, M_SKIN)
    if arms:
        for side in (-1, 1):
            sh = Vector((x + side * 0.2 * s * rx, y + side * 0.2 * s * ry, 1.38 * s))
            out, fwd = rnd.uniform(0.05, 0.3), rnd.uniform(0.0, 0.2)
            hand = sh + Vector((side * out * rx + fwd * fx, side * out * ry + fwd * fy, rnd.uniform(0.55, 0.68) * s))
            cyl(sh, hand, 0.045 * s, M_CLOTH, 6)


phones = 0
for (ya, yb, xa, xb, n) in ((-10.6, -3.6, -12, 12, 230), (3.8, 18.5, -16, 16, 420), (-3.6, 3.8, -16, -4.5, 60), (-3.6, 3.8, 4.5, 16, 60)):
    for _ in range(n):
        x, y = rnd.uniform(xa, xb), rnd.uniform(ya, yb)
        if math.hypot(x, y) < 4.2: continue
        face = math.atan2(-14 - y, -x) if rnd.random() < 0.85 else rnd.uniform(-math.pi, math.pi)   # most face the stage
        up = rnd.random() < (0.32 if y < 0 else 0.18)
        person(x, y, rnd.uniform(1.55, 1.86), face, up)
        if not up and phones < 22 and rnd.random() < 0.06:
            phones += 1
            fx, fy = math.cos(face), math.sin(face)
            box(x + fx * 0.35, y + fy * 0.35, 1.9, 0.07, 0.008, 0.14, M_PHONE, rot=face + math.pi / 2)

# ---------- haze through the whole hall ----------
vm = bpy.data.materials.new("haze"); vm.use_nodes = True; nt = vm.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
pv_ = nt.nodes.new("ShaderNodeVolumePrincipled"); pv_.inputs["Density"].default_value = 0.022; pv_.inputs["Anisotropy"].default_value = 0.55
nt.links.new(pv_.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
box(0, (Y0 + Y1) / 2, HZ / 2, 2 * HX - 0.2, Y1 - Y0 - 0.2, HZ - 0.2, vm)
flush()

# ---------- world, camera, render ----------
sc.world = bpy.data.worlds.new("w"); sc.world.use_nodes = True
sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.002, 0.002, 0.0025, 1)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); col.objects.link(cam); sc.camera = cam
cam.data.type = "PANO"; cam.data.panorama_type = "EQUIRECTANGULAR"
cam.location = (0, 0, EYE)
cam.rotation_euler = (math.radians(90), 0, math.radians(180))     # image centre = the stage (-Y), +X left, up top
r = sc.render
r.engine = "CYCLES"; r.resolution_x = W; r.resolution_y = W // 2; r.resolution_percentage = 100
r.use_border = STRIPS > 1; r.use_crop_to_border = True
r.border_min_x, r.border_max_x = 0, 1
# strip 0 is the top of the picture; Blender's border counts from the bottom
r.border_max_y = 1 - STRIP / STRIPS; r.border_min_y = 1 - (STRIP + 1) / STRIPS
r.image_settings.file_format = "OPEN_EXR"; r.image_settings.color_depth = "16"
r.filepath = OUT
cy = sc.cycles
cy.device = "CPU"; cy.samples = SAMPLES; cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.02
cy.use_denoising = True
cy.max_bounces = 4; cy.diffuse_bounces = 2; cy.glossy_bounces = 2; cy.transmission_bounces = 2; cy.volume_bounces = 1
cy.caustics_reflective = False; cy.caustics_refractive = False
cy.sample_clamp_indirect = 4.0
cy.volume_step_rate = 2.0
r.threads_mode = "AUTO"
bpy.ops.render.render(write_still=True)
# the strip as plain numbers too (top row first, linear rgb, half floats), for stage_post.py outside Blender
import numpy as np
im = bpy.data.images.load(OUT); w, h = im.size
px = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(px)
np.save(OUT.rsplit(".", 1)[0] + ".npy", px.reshape(h, w, 4)[::-1, :, :3].astype(np.float16))
print("saved", OUT, "strip", STRIP, "of", STRIPS, w, "x", h)
