# blender -b --factory-startup -P stage.py -- <place> <out.exr> [strip strips] [samples] [width]
# The places behind the person in the shop viewer, each one 360 degree picture rendered in Cycles:
#   studio  a white cyclorama studio: coved floor and soft round corners, softboxes and their stands on the
#           photographer's side, overhead panels on the grid lighting the cyc
#   window  a living room in an Indian flat on a late afternoon: low sun through a wide sliding window, tiled floor,
#           sofa, shelves, plants, a ceiling fan, the building across the road
#   show    a dark hall and its stage: a low deck with an industrial backline, desk lamps, a row of white light bars,
#           a big quiet screen, trusses of beams through haze, arched roof steel, the crowd, front of house behind
# Built from boxes, planes and procedural materials here, nothing photographed.
#
# The picture is what the viewer's camera sees while it walks round the person: for every direction the ray starts
# where that camera stands when it looks that way (2.86 m out, 1.1 m up, scene.ts WEAR_CAMERA), with its own
# 85 mm f/5.6 lens focused on the person, and only things beyond the person are drawn (the person is the viewer's).
# Same equirect as the viewer: u = 0.5 - atan2(x, z) / 2pi in three (+z, Blender -Y, in the middle), v = 0 straight up.
# Lights near the person are the viewer's own lights (scene.ts), at the same place and power, so picture and person
# match; the studio and the room are developed at exposure 1 in the viewer's units (stage_post.py).
# One horizontal strip per call, so the farm can split the frame across runners; stage_post.py stitches them.
import bpy, bmesh, sys, os, math, random
from mathutils import Vector, Matrix

a = sys.argv[sys.argv.index("--") + 1:]
PLACE, OUT = a[0], a[1]
STRIP = int(a[2]) if len(a) > 2 else 0
STRIPS = int(a[3]) if len(a) > 3 else 1
SAMPLES = int(a[4]) if len(a) > 4 else 64
W = int(a[5]) if len(a) > 5 else 4096
assert PLACE in ("studio", "window", "show"), PLACE
FLOOR = 0.35                 # scene.ts FLOOR: three y of the floor the person stands on (Blender z = 0)
RING, EYE = 2.857, 1.1       # the viewer camera's distance from the person and its height above the floor
FOCUS, FSTOP, LENS = 2.8, 5.6, 85.0

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
col = sc.collection
rnd = random.Random(48)


def three(p):
    """three (x, y, z) -> Blender (x, -z, y - FLOOR)"""
    return Vector((p[0], -p[2], p[1] - FLOOR))


# ---------- materials ----------
def mat(name, base=(0.03, 0.03, 0.03), rough=0.6, metal=0.0, emit=None, strength=0.0, spec=0.5, sheen=0.0, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*base, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if "Specular IOR Level" in p.inputs: p.inputs["Specular IOR Level"].default_value = spec
    if sheen: p.inputs["Sheen Weight"].default_value = sheen
    if coat: p.inputs["Coat Weight"].default_value = coat; p.inputs["Coat Roughness"].default_value = 0.08
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


def seen(name, colr, strength):
    """a lamp's face: glows to the camera, but the light itself comes from the area lamp just in front of it, so
    for every other ray it is not there at all (no double light, no shadow on its own lamp)"""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
    lp = nt.nodes.new("ShaderNodeLightPath"); tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (*colr, 1); e.inputs[1].default_value = strength
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(e.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], nt.nodes["Material Output"].inputs[0])
    return m


def node_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    return m, m.node_tree, m.node_tree.nodes["Principled BSDF"]


def mix_rgb(nt, fac, a_, b_):
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"
    if isinstance(fac, float): mx.inputs["Factor"].default_value = fac
    else: nt.links.new(fac, mx.inputs["Factor"])
    for i, c in ((6, a_), (7, b_)):
        if isinstance(c, tuple): mx.inputs[i].default_value = (*c, 1)
        else: nt.links.new(c, mx.inputs[i])
    return mx.outputs[2]


def soft_var(nt, scale, lo, hi):
    """a large, low-contrast unevenness (paint, wear): a factor between lo and hi, no fine noise"""
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = 1.0
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = 0.3; mr.inputs[2].default_value = 0.7
    mr.inputs[3].default_value = lo; mr.inputs[4].default_value = hi
    nt.links.new(n.outputs["Fac"], mr.inputs[0])
    return mr.outputs[0]


def add(ob, m=None):
    if m is not None:
        ob.data.materials.clear(); ob.data.materials.append(m)
    return ob


# every shape goes into one mesh per material (thousands of objects would take ages to build)
BAT = {}
SMOOTH = set()
def bm(m):
    if m not in BAT: BAT[m] = bmesh.new()
    return BAT[m]


def box(x, y, z, sx, sy, sz, m, rot=0.0):
    """a box by its centre and full size"""
    M = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot, 4, "Z") @ Matrix.Diagonal((sx, sy, sz, 1))
    bmesh.ops.create_cube(bm(m), size=1, matrix=M)


_scratch = bpy.data.meshes.new("scratch")
def rbox(x, y, z, sx, sy, sz, m, r=0.03, rot=0.0, seg=3):
    """a box with rounded edges (upholstery, plastic, painted furniture)"""
    t = bmesh.new()
    bmesh.ops.create_cube(t, size=1, matrix=Matrix.Diagonal((sx, sy, sz, 1)))
    bmesh.ops.bevel(t, geom=list(t.verts) + list(t.edges), offset=min(r, sx / 2.1, sy / 2.1, sz / 2.1), segments=seg, affect="EDGES", profile=0.5)
    bmesh.ops.transform(t, matrix=Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot, 4, "Z"), verts=t.verts)
    t.to_mesh(_scratch); t.free(); bm(m).from_mesh(_scratch); SMOOTH.add(m)


def cyl(p0, p1, r, m, verts=12, r2=None):
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    M = Matrix.Translation((p0 + p1) / 2) @ Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
    bmesh.ops.create_cone(bm(m), cap_ends=True, segments=verts, radius1=r, radius2=r if r2 is None else r2, depth=d.length, matrix=M)


def sphere(c, r, m, seg=12, rings=8, s=(1, 1, 1)):
    bmesh.ops.create_uvsphere(bm(m), u_segments=seg, v_segments=rings, radius=r, matrix=Matrix.Translation(c) @ Matrix.Diagonal((*s, 1)))


def surf(f, nu, nv, m, smooth=True):
    """a parametric patch: f(u, v) -> point, u and v in 0..1"""
    b = bm(m)
    vs = [[b.verts.new(f(i / nu, j / nv)) for j in range(nv + 1)] for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nv):
            b.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
    if smooth: SMOOTH.add(m)


def quad(p0, p1, p2, p3, m):
    b = bm(m); b.faces.new([b.verts.new(p) for p in (p0, p1, p2, p3)])


def flush():
    for m, b in BAT.items():
        me = bpy.data.meshes.new(m.name); b.to_mesh(me); b.free()
        if m in SMOOTH: me.shade_smooth()
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


def panel(loc, ex, ey, n, sx, sy, power, colr, face=None, strength=None):
    """a rectangular area lamp (Blender watts: radiance P / (pi A), one-sided, facing n) with an optional face the
    camera sees in its place; ex, ey are its width and height directions"""
    d = bpy.data.lights.new("p", "AREA"); d.shape = "RECTANGLE"; d.size = sx; d.size_y = sy; d.energy = power; d.color = colr
    o = bpy.data.objects.new("p", d); col.objects.link(o)
    R = Matrix((ex, ey, -n)).transposed()
    o.matrix_world = Matrix.Translation(loc) @ R.to_4x4()
    o.visible_camera = False
    if face is not None:
        L = strength if strength is not None else power / (math.pi * sx * sy)
        fm = seen(f"face{len(bpy.data.materials)}", colr, L)
        c = Vector(loc) - n * 0.012
        hx, hy = ex * (sx / 2), ey * (sy / 2)
        quad(c - hx - hy, c + hx - hy, c + hx + hy, c - hx + hy, fm)
    return o


AIM = three((0, FLOOR + 1.1, 0))   # scene.ts light aim for the places: the chest, 1.1 m up


def viewer_light(pos3, size, power, tint):
    """one of scene.ts's lights, converted: the frame is lightFrame()'s (ex along the width, level; ey up; n at the aim)"""
    p = three(pos3)
    n = (AIM - p).normalized()
    ex = Vector((0, 0, 1)).cross(-n).normalized()
    ey = (-n).cross(ex)
    return p, ex, ey, n


SKY = None   # set by a place that has daylight


# =====================================================================================================================
def build_studio():
    """A white cyc studio. The cyc wraps three sides (behind the person and both sides) with a 0.9 m coved floor and
    round vertical corners; the fourth side is the studio itself: softboxes on stands, a tether cart, V-flats, a rail."""
    global ZC
    XS, YB, YF, R_, ZT = 4.6, 4.2, -7.2, 0.9, 5.6
    ZC = ZT
    # cyc paint: a clean, slightly warm white, dead matte; the floor is the same paint walked on, a touch greyer
    m, nt, p = node_mat("cyc"); p.inputs["Roughness"].default_value = 0.92
    p.inputs["Specular IOR Level"].default_value = 0.3
    nt.links.new(mix_rgb(nt, soft_var(nt, 0.35, 0.0, 1.0), (0.80, 0.792, 0.772), (0.815, 0.806, 0.787)), p.inputs["Base Color"])
    CYC = m
    # the floor is the same paint walked on: greyer and a little scuffed, a soft sheen; under every lamp in the
    # studio at once it would burn out at the wall's white
    m, nt, p = node_mat("cycfloor"); p.inputs["Roughness"].default_value = 0.78
    p.inputs["Specular IOR Level"].default_value = 0.3
    nt.links.new(mix_rgb(nt, soft_var(nt, 0.6, 0.0, 1.0), (0.5, 0.494, 0.48), (0.545, 0.538, 0.522)), p.inputs["Base Color"])
    FLR = m
    M_WALL = mat("wall", (0.74, 0.735, 0.72), 0.9, spec=0.3)
    M_CEIL = mat("ceiling", (0.03, 0.03, 0.031), 0.9)
    M_STEEL = mat("steel", (0.06, 0.06, 0.065), 0.45, metal=1.0)
    M_FAB = mat("fabric", (0.012, 0.012, 0.013), 0.9, spec=0.2)
    M_STAND = mat("stand", (0.04, 0.04, 0.042), 0.4, metal=0.8)
    M_CHROME = mat("chrome", (0.7, 0.7, 0.72), 0.2, metal=1.0)
    M_BAG = mat("sandbag", (0.09, 0.075, 0.05), 0.95, spec=0.2)
    M_WOOD = mat("applebox", (0.38, 0.25, 0.14), 0.7)
    M_FOAM = mat("foam", (0.82, 0.82, 0.8), 0.85)
    M_PLASTIC = mat("plastic", (0.02, 0.02, 0.022), 0.35)
    M_DOOR = mat("door", (0.36, 0.36, 0.355), 0.5)
    M_TAPE = mat("tape", (0.02, 0.02, 0.02), 0.6)
    M_EXIT = emission("exit", (0.15, 1.0, 0.35), 2.0)
    M_SCREEN = emission("laptop", (0.82, 0.86, 0.92), 0.55)
    flat_floor = lambda u, v: Vector((-XS + R_ + u * (2 * XS - 2 * R_), YF + v * (YB - R_ - YF), 0))
    surf(flat_floor, 4, 8, FLR, False)
    # the coves, floor to wall (quarter cylinders), and where two coves meet (a sphere's eighth)
    surf(lambda u, v: Vector((-XS + R_ + u * (2 * XS - 2 * R_), YB - R_ + R_ * math.sin(v * math.pi / 2), R_ - R_ * math.cos(v * math.pi / 2))), 4, 16, CYC)
    for s in (-1, 1):
        surf(lambda u, v, s=s: Vector((s * (XS - R_ + R_ * math.sin(v * math.pi / 2)), YF + u * (YB - R_ - YF), R_ - R_ * math.cos(v * math.pi / 2))), 8, 16, CYC)
        surf(lambda u, v, s=s: Vector((s * (XS - R_) + s * R_ * math.sin(v * math.pi / 2) * math.sin(u * math.pi / 2),
                                       YB - R_ + R_ * math.sin(v * math.pi / 2) * math.cos(u * math.pi / 2),
                                       R_ - R_ * math.cos(v * math.pi / 2))), 16, 16, CYC)
        # the round vertical corner and the side wall
        surf(lambda u, v, s=s: Vector((s * (XS - R_ + R_ * math.sin(u * math.pi / 2)), YB - R_ + R_ * math.cos(u * math.pi / 2), R_ + v * (ZT - R_))), 16, 4, CYC)
        surf(lambda u, v, s=s: Vector((s * XS, YF + u * (YB - R_ - YF), R_ + v * (ZT - R_))), 8, 4, CYC)
    surf(lambda u, v: Vector((-XS + R_ + u * (2 * XS - 2 * R_), YB, R_ + v * (ZT - R_))), 4, 4, CYC)
    # the photographer's end: a plain wall with a door and its exit sign, a light switch
    box(0, YF - 0.1, ZT / 2, 2 * XS + 0.4, 0.2, ZT, M_WALL)
    box(2.6, YF + 0.02, 1.08, 1.2, 0.06, 2.16, M_DOOR)
    for dx in (-0.63, 0.63): box(2.6 + dx, YF + 0.04, 1.1, 0.06, 0.08, 2.2, M_STEEL)
    box(2.6, YF + 0.04, 2.2, 1.32, 0.08, 0.06, M_STEEL)
    cyl((2.6 - 0.45, YF + 0.06, 1.05), (2.6 - 0.45, YF + 0.16, 1.05), 0.02, M_CHROME, 8)
    box(2.6, YF + 0.03, 2.48, 0.36, 0.05, 0.14, M_EXIT)
    box(1.55, YF + 0.02, 1.25, 0.09, 0.02, 0.12, mat("switch", (0.75, 0.75, 0.73), 0.4))
    box(0, (YB + YF) / 2, ZT + 0.1, 2 * XS + 0.4, YB - YF + 0.4, 0.2, M_CEIL)
    # the lighting grid: pipes on drop rods under the black ceiling
    for y in [YF + 1.2 + i * 1.5 for i in range(8)]:
        cyl((-XS + 0.4, y, ZT - 0.45), (XS - 0.4, y, ZT - 0.45), 0.024, M_STEEL, 8)
        for x in (-3, 0, 3): cyl((x, y, ZT - 0.45), (x, y, ZT), 0.01, M_STEEL, 6)
    for x in (-3, 3): cyl((x, YF + 0.8, ZT - 0.4), (x, YB - 1.0, ZT - 0.4), 0.024, M_STEEL, 8)

    # cyc lights: soft panels hung from the grid, washing the walls evenly from above, so the cove and the corners
    # fall off softly by themselves (the only shading the cyc has)
    def cyclight(x, y, tx, ty):
        loc = Vector((x, y, ZT - 0.75)); aim = Vector((tx, ty, 1.3))
        n = (aim - loc).normalized(); ex = Vector((0, 0, 1)).cross(-n).normalized(); ey = (-n).cross(ex)
        panel(loc, ex, ey, n, 1.0, 0.5, CYCW, (1.0, 0.975, 0.94), face=True)
        Rm = Matrix((ex, ey, -n)).transposed().to_4x4()
        bmesh.ops.create_cube(bm(M_PLASTIC), size=1, matrix=Matrix.Translation(loc - n * 0.1) @ Rm @ Matrix.Diagonal((1.08, 0.58, 0.16, 1)))
        cyl(loc - n * 0.1, (x, y, ZT - 0.45), 0.015, M_STEEL, 6)
    for x in (-2.4, 0, 2.4): cyclight(x, YB - 1.9, x, YB)
    for s in (-1, 1):
        for y in (1.4, -1.6, -4.4): cyclight(s * (XS - 1.9), y, s * XS, y)

    # the photographer's lights: scene.ts STUDIO, with their softboxes, stands and sandbags
    for name, pos3, size, power, tint in STUDIO_LIGHTS:
        p, ex, ey, n = viewer_light(pos3, size, power, tint)
        panel(p, ex, ey, n, size[0], size[1], power, tint, face=True)
        sx, sy = size
        # the box: black fabric from the diffuser back to the speed ring, the head behind it
        back = p - n * (0.32 + 0.25 * max(sx, sy))
        corners = [p + ex * (i * sx / 2) + ey * (j * sy / 2) - n * 0.02 for i, j in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        rear = [back + ex * (i * 0.13) + ey * (j * 0.13) for i, j in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        for k in range(4):
            quad(corners[k], corners[(k + 1) % 4], rear[(k + 1) % 4], rear[k], M_FAB)
        quad(*rear, M_FAB)
        cyl(back, back - n * 0.28, 0.1, M_STAND, 16)
        if name == "top":   # the top light hangs from the grid
            cyl(back - n * 0.14, (p.x, p.y, ZT - 0.45), 0.02, M_STEEL, 8)
            continue
        # a stand: centre column down to the floor, three legs, a sandbag on one
        foot = Vector((back.x, back.y, 0)) - n.to_2d().to_3d().normalized() * 0.15
        top = back - n * 0.14 - Vector((0, 0, 0.12))
        cyl(top, Vector((foot.x, foot.y, 0.55)), 0.016, M_STAND, 8)
        cyl(back - n * 0.14, top, 0.02, M_STAND, 8)
        for k in range(3):
            t = k * 2 * math.pi / 3 + 0.4
            cyl((foot.x, foot.y, 0.6), (foot.x + 0.55 * math.cos(t), foot.y + 0.55 * math.sin(t), 0.02), 0.012, M_STAND, 6)
        rbox(foot.x + 0.4 * math.cos(0.4), foot.y + 0.4 * math.sin(0.4), 0.06, 0.34, 0.2, 0.1, M_BAG, r=0.04, rot=0.4)

    # the floor at the photographer's end: a tether cart with a laptop, apple boxes, a stool, a C-stand and flag,
    # V-flats, a rail with the next looks on it, a taped mark where the model stands
    cx, cy_ = -2.3, -4.6
    box(cx, cy_, 0.98, 0.9, 0.6, 0.03, M_PLASTIC)
    box(cx, cy_, 0.45, 0.85, 0.55, 0.02, M_PLASTIC)
    for dx in (-0.42, 0.42):
        for dy in (-0.27, 0.27):
            cyl((cx + dx, cy_ + dy, 0.06), (cx + dx, cy_ + dy, 0.98), 0.012, M_CHROME, 8)
            sphere((cx + dx, cy_ + dy, 0.04), 0.035, M_PLASTIC, 8, 6)
    box(cx, cy_ - 0.05, 1.005, 0.34, 0.24, 0.016, mat("laptop", (0.5, 0.5, 0.52), 0.3, metal=0.9))
    lid = Matrix.Translation((cx, cy_ + 0.07, 1.013)) @ Matrix.Rotation(math.radians(-15), 4, "X")
    bmesh.ops.create_cube(bm(mat("lid", (0.5, 0.5, 0.52), 0.3, metal=0.9)), size=1, matrix=lid @ Matrix.Translation((0, 0, 0.11)) @ Matrix.Diagonal((0.34, 0.008, 0.22, 1)))
    bmesh.ops.create_cube(bm(M_SCREEN), size=1, matrix=lid @ Matrix.Translation((0, -0.0045, 0.11)) @ Matrix.Diagonal((0.32, 0.001, 0.2, 1)))
    for i, (x, y, z, r) in enumerate(((1.9, -3.9, 0.1, 0.1), (1.9, -3.9, 0.3, 0.1), (2.5, -3.7, 0.1, 0.8))):
        box(x, y, z, 0.5, 0.3, 0.2, M_WOOD, rot=r)
    sx_, sy_ = 2.9, -4.9                                           # stool
    cyl((sx_, sy_, 0.74), (sx_, sy_, 0.78), 0.18, M_PLASTIC, 24)
    for k in range(4):
        t = k * math.pi / 2 + 0.3
        cyl((sx_ + 0.12 * math.cos(t), sy_ + 0.12 * math.sin(t), 0.74), (sx_ + 0.24 * math.cos(t), sy_ + 0.24 * math.sin(t), 0), 0.012, M_CHROME, 6)
    cyl((sx_, sy_, 0.3), (sx_, sy_, 0.31), 0.17, M_CHROME, 24)
    # C-stand with a black flag, off the key side
    fx, fy = -2.2, -2.2
    cyl((fx, fy, 0), (fx, fy, 1.9), 0.014, M_CHROME, 8)
    for k in range(3):
        t = k * 2 * math.pi / 3
        cyl((fx, fy, 0.05), (fx + 0.45 * math.cos(t), fy + 0.45 * math.sin(t), 0.05 + 0.04 * k), 0.01, M_CHROME, 6)
    cyl((fx, fy, 1.85), (fx + 0.7, fy - 0.3, 1.9), 0.012, M_CHROME, 6)
    box(fx + 0.95, fy - 0.4, 1.9, 0.6, 0.02, 0.45, M_FAB, rot=-0.4)
    # V-flats: two 1.2 x 2.4 m foam boards taped along one edge, white side out
    for (vx, vy, rot) in ((-3.6, -5.8, 0.75), (-3.6, -5.8, -0.75 + math.pi / 2)):
        M = Matrix.Translation((vx, vy, 1.2)) @ Matrix.Rotation(rot, 4, "Z") @ Matrix.Translation((0.6, 0, 0))
        bmesh.ops.create_cube(bm(M_FOAM), size=1, matrix=M @ Matrix.Diagonal((1.2, 0.05, 2.4, 1)))
    # a clothes rail with the next looks
    rx, ry = 3.5, -6.3
    for dx in (-0.7, 0.7):
        cyl((rx + dx, ry, 0.05), (rx + dx, ry, 1.65), 0.013, M_CHROME, 8)
        cyl((rx + dx, ry - 0.25, 0.05), (rx + dx, ry + 0.25, 0.05), 0.013, M_CHROME, 8)
    cyl((rx - 0.7, ry, 1.65), (rx + 0.7, ry, 1.65), 0.013, M_CHROME, 8)
    for i in range(7):
        x = rx - 0.55 + i * 0.17 + rnd.uniform(-0.02, 0.02)
        tone = (0.014, 0.014, 0.014) if i % 3 else (0.78, 0.77, 0.74)
        rbox(x, ry, 1.25, 0.04, 0.52, 0.72, mat(f"look{i}", tone, 0.9, sheen=0.3), r=0.015, rot=math.pi / 2 + rnd.uniform(-0.06, 0.06))
    # the mark on the floor for the model, and a few strips of tape where lights stood before
    for (x, y, sx, sy) in ((0, 0.35, 0.3, 0.05), (0, 0.35, 0.05, 0.25), (-1.4, -1.9, 0.24, 0.05), (1.6, -1.7, 0.05, 0.22)):
        box(x, y, 0.0015, sx, sy, 0.003, M_TAPE)


def build_window():
    """A living room in an Indian flat, late afternoon. A wide aluminium sliding window ahead of the person and to
    their right (the balcony and the building across the road beyond it) lets the low sun in across their front and
    in long warm stripes over the tiles toward the sofa behind them. Vitrified tiles, warm white walls, a bookshelf
    and a split AC on the far side, a dining corner by the window and the door behind the camera."""
    global ZC, SKY
    X0, X1, Y0, Y1, ZT = -3.2, 3.8, -4.2, 3.4, 3.0
    WY0, WY1, WZ0, WZ1 = -3.9, -0.5, 0.45, 2.6                       # the window opening, ahead of the person, to their right
    ZC = ZT
    # vitrified tiles, 60 x 60 cm, warm ivory, polished (they mirror the window softly), hairline grout
    m, nt, p = node_mat("tiles"); p.inputs["Roughness"].default_value = 0.14
    p.inputs["Specular IOR Level"].default_value = 0.5
    br = nt.nodes.new("ShaderNodeTexBrick"); br.offset = 0.0; br.squash = 1.0
    br.inputs["Scale"].default_value = 1.0; br.inputs["Brick Width"].default_value = 0.6; br.inputs["Row Height"].default_value = 0.6
    br.inputs["Mortar Size"].default_value = 0.0025; br.inputs["Mortar Smooth"].default_value = 0.3
    br.inputs["Color1"].default_value = (0.56, 0.5, 0.42, 1); br.inputs["Color2"].default_value = (0.585, 0.525, 0.44, 1)
    br.inputs["Mortar"].default_value = (0.36, 0.32, 0.27, 1); br.inputs["Bias"].default_value = 0.0
    tc = nt.nodes.new("ShaderNodeTexCoord"); nt.links.new(tc.outputs["Object"], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], p.inputs["Base Color"])
    rg = nt.nodes.new("ShaderNodeMapRange"); rg.inputs[3].default_value = 0.45; rg.inputs[4].default_value = 0.14
    nt.links.new(br.outputs["Fac"], rg.inputs[0]); nt.links.new(rg.outputs[0], p.inputs["Roughness"])
    TILE = m
    m, nt, p = node_mat("paint"); p.inputs["Roughness"].default_value = 0.88; p.inputs["Specular IOR Level"].default_value = 0.3
    nt.links.new(mix_rgb(nt, soft_var(nt, 0.5, 0.0, 1.0), (0.73, 0.69, 0.61), (0.75, 0.71, 0.63)), p.inputs["Base Color"])
    PAINT = m
    M_CEIL = mat("ceiling", (0.79, 0.78, 0.75), 0.9, spec=0.3)
    M_SKIRT = mat("skirting", (0.42, 0.37, 0.31), 0.25)
    M_ALU = mat("alu", (0.82, 0.8, 0.77), 0.35, metal=0.0, spec=0.6)          # powder-coated white frame
    M_GRILL = mat("grill", (0.06, 0.06, 0.06), 0.5, metal=0.6)
    M_OUTWALL = mat("outwall", (0.62, 0.55, 0.44), 0.9)
    M_OUTWIN = mat("outwin", (0.04, 0.045, 0.05), 0.2, spec=0.8)
    M_GROUND = mat("ground", (0.16, 0.15, 0.12), 0.95)
    M_LEAF = mat("leaf", (0.06, 0.1, 0.03), 0.6, spec=0.35)
    M_LEAF2 = mat("leaf2", (0.09, 0.13, 0.04), 0.6, spec=0.35)
    M_BARK = mat("bark", (0.09, 0.07, 0.05), 0.9)
    M_POT = mat("terracotta", (0.42, 0.18, 0.09), 0.85)
    M_SOFA = mat("linen", (0.34, 0.3, 0.25), 0.95, spec=0.25, sheen=0.4)
    M_CUSH1 = mat("mustard", (0.46, 0.3, 0.07), 0.95, sheen=0.4)
    M_CUSH2 = mat("rust", (0.3, 0.1, 0.05), 0.95, sheen=0.4)
    M_CUSH3 = mat("ivory", (0.66, 0.62, 0.54), 0.95, sheen=0.4)
    m, nt, p = node_mat("teak"); p.inputs["Roughness"].default_value = 0.45
    wv = nt.nodes.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 6.0; wv.inputs["Distortion"].default_value = 4.0
    wv.inputs["Detail"].default_value = 1.0; wv.bands_direction = "X"
    nt.links.new(mix_rgb(nt, wv.outputs["Fac"], (0.17, 0.085, 0.04), (0.23, 0.12, 0.06)), p.inputs["Base Color"])
    TEAK = m
    M_BRASS = mat("brass", (0.8, 0.58, 0.28), 0.3, metal=1.0)
    M_BLACK = mat("black", (0.015, 0.015, 0.015), 0.5)
    M_WHITE = mat("appliance", (0.8, 0.8, 0.78), 0.3)
    M_FAN = mat("fan", (0.74, 0.72, 0.68), 0.35)
    m, nt, p = node_mat("dhurrie"); p.inputs["Roughness"].default_value = 0.98; p.inputs["Sheen Weight"].default_value = 0.5
    wv = nt.nodes.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "Y"; wv.wave_profile = "SAW"
    wv.inputs["Scale"].default_value = 3.0
    st = nt.nodes.new("ShaderNodeMath"); st.operation = "GREATER_THAN"; st.inputs[1].default_value = 0.82; nt.links.new(wv.outputs["Fac"], st.inputs[0])
    tc = nt.nodes.new("ShaderNodeTexCoord"); nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
    nt.links.new(mix_rgb(nt, st.outputs[0], (0.55, 0.48, 0.37), (0.2, 0.17, 0.14)), p.inputs["Base Color"])
    RUG = m
    m, nt, p = node_mat("sheer"); nt.nodes.remove(p)
    tl = nt.nodes.new("ShaderNodeBsdfTranslucent"); tl.inputs[0].default_value = (0.86, 0.84, 0.8, 1)
    df = nt.nodes.new("ShaderNodeBsdfDiffuse"); df.inputs[0].default_value = (0.82, 0.8, 0.76, 1)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    a1 = nt.nodes.new("ShaderNodeMixShader"); a1.inputs[0].default_value = 0.45; nt.links.new(df.outputs[0], a1.inputs[1]); nt.links.new(tl.outputs[0], a1.inputs[2])
    a2 = nt.nodes.new("ShaderNodeMixShader"); a2.inputs[0].default_value = 0.4; nt.links.new(a1.outputs[0], a2.inputs[1]); nt.links.new(tr.outputs[0], a2.inputs[2])
    nt.links.new(a2.outputs[0], nt.nodes["Material Output"].inputs[0])
    SHEER = m
    BOOKS = [mat(f"book{i}", c, 0.7) for i, c in enumerate(((0.32, 0.08, 0.05), (0.06, 0.1, 0.18), (0.5, 0.44, 0.33), (0.12, 0.16, 0.1),
                                                           (0.6, 0.56, 0.48), (0.04, 0.04, 0.04), (0.42, 0.26, 0.08)))]

    # ---- the room shell ----
    surf(lambda u, v: Vector((X0 + u * (X1 - X0), Y0 + v * (Y1 - Y0), 0)), 1, 1, TILE, False)
    box((X0 + X1) / 2, (Y0 + Y1) / 2, ZT + 0.1, X1 - X0 + 0.4, Y1 - Y0 + 0.4, 0.2, M_CEIL)
    box((X0 + X1) / 2, Y1 + 0.1, ZT / 2, X1 - X0 + 0.4, 0.2, ZT, PAINT)         # behind the sofa
    box(X1 + 0.1, (Y0 + Y1) / 2, ZT / 2, 0.2, Y1 - Y0 + 0.4, ZT, PAINT)         # right (shelves)
    # behind the camera: the wall with the door to the hall
    DX0, DX1 = 1.5, 2.5
    box((X0 + DX0) / 2, Y0 - 0.1, ZT / 2, DX0 - X0, 0.2, ZT, PAINT)
    box((DX1 + X1) / 2, Y0 - 0.1, ZT / 2, X1 - DX1, 0.2, ZT, PAINT)
    box((DX0 + DX1) / 2, Y0 - 0.1, (2.2 + ZT) / 2, DX1 - DX0, 0.2, ZT - 2.2, PAINT)
    for x in (DX0 + 0.04, DX1 - 0.04): box(x, Y0 + 0.01, 1.1, 0.08, 0.06, 2.2, TEAK)
    box((DX0 + DX1) / 2, Y0 + 0.01, 2.2, DX1 - DX0, 0.06, 0.08, TEAK)
    # the hall beyond the door, dim
    box((DX0 + DX1) / 2, Y0 - 1.6, 0, 1.6, 3, 0.02, TILE)
    box((DX0 + DX1) / 2, Y0 - 3.1, ZT / 2, 1.6, 0.1, ZT, PAINT)
    box(DX0 - 0.3, Y0 - 1.6, ZT / 2, 0.1, 3, ZT, PAINT); box(DX1 + 0.3, Y0 - 1.6, ZT / 2, 0.1, 3, ZT, PAINT)
    box((DX0 + DX1) / 2, Y0 - 1.6, ZT, 1.6, 3, 0.1, M_CEIL)
    # the window wall, round the opening
    box(X0 - 0.1, (Y0 + WY0) / 2, ZT / 2, 0.2, WY0 - Y0 + 0.2, ZT, PAINT)
    box(X0 - 0.1, (WY1 + Y1) / 2, ZT / 2, 0.2, Y1 - WY1 + 0.2, ZT, PAINT)
    box(X0 - 0.1, (WY0 + WY1) / 2, WZ0 / 2, 0.2, WY1 - WY0, WZ0, PAINT)
    box(X0 - 0.1, (WY0 + WY1) / 2, (WZ1 + ZT) / 2, 0.2, WY1 - WY0, ZT - WZ1, PAINT)
    box(X0 + 0.02, (WY0 + WY1) / 2, WZ0 - 0.01, 0.1, WY1 - WY0 + 0.1, 0.03, mat("granite", (0.05, 0.045, 0.045), 0.15))   # the sill
    # skirting tiles all round (not under the window wall's opening side, not across the door)
    for (x, y, sx, sy) in (((X0 + X1) / 2, Y1 - 0.006, X1 - X0, 0.012), (X1 - 0.006, (Y0 + Y1) / 2, 0.012, Y1 - Y0),
                           ((X0 + DX0) / 2, Y0 + 0.006, DX0 - X0, 0.012), ((DX1 + X1) / 2, Y0 + 0.006, X1 - DX1, 0.012),
                           (X0 + 0.006, (Y0 + Y1) / 2, 0.012, Y1 - Y0)):
        box(x, y, 0.05, sx, sy, 0.1, M_SKIRT)
    # the sliding window: a white aluminium frame, three shutters (the middle one slid open behind the left),
    # a transom; no glass in the open part, a faint sheet where the shutters overlap
    fx = X0 - 0.12
    for y in (WY0 + 0.03, WY1 - 0.03): box(fx, y, (WZ0 + WZ1) / 2, 0.1, 0.06, WZ1 - WZ0, M_ALU)
    for z in (WZ0 + 0.03, WZ1 - 0.03, 2.08): box(fx, (WY0 + WY1) / 2, z, 0.1, WY1 - WY0, 0.05, M_ALU)
    for y in (WY0 + (WY1 - WY0) / 3, WY0 + 2 * (WY1 - WY0) / 3): box(fx + 0.03, y, (WZ0 + 2.08) / 2, 0.04, 0.05, 2.08 - WZ0, M_ALU)
    # the safety grill outside (plain square bars, as most flats have), on the balcony side
    for z in [WZ0 + 0.3 + i * 0.36 for i in range(4)]:
        cyl((X0 - 0.3, WY0, z), (X0 - 0.3, WY1, z), 0.008, M_GRILL, 6)
    # sheer curtains bunched at both ends, on a rod
    cyl((X0 + 0.12, WY0 - 0.5, 2.62), (X0 + 0.12, WY1 + 0.5, 2.62), 0.012, M_BRASS, 8)
    for (ya, yb) in ((WY0, WY0 + 0.45), (WY1 - 0.3, WY1 + 0.35)):
        surf(lambda u, v, ya=ya, yb=yb: Vector((X0 + 0.12 + 0.05 * math.sin(u * 22) + 0.01 * math.sin(v * 9 + u * 40), ya + u * (yb - ya), 0.03 + v * 2.57)), 80, 6, SHEER)

    # ---- outside: the balcony, a neem tree, the building across the road, the ground four floors down ----
    surf(lambda u, v: Vector((-4.9 + u * 1.7, Y0 + v * (2.1 - Y0), -0.02)), 1, 1, TILE, False)
    box(-4.95, -1.05, 0.48, 0.15, 6.3, 0.96, M_OUTWALL)
    box(-4.95, -1.05, 0.97, 0.22, 6.35, 0.04, M_OUTWALL)
    box(-4.05, Y0 + 0.08, 1.5, 1.7, 0.15, 3.0, M_OUTWALL); box(-4.05, 2.1, 1.5, 1.7, 0.15, 3.0, M_OUTWALL)
    box(-4.05, -1.05, ZT + 0.1, 1.8, 6.4, 0.2, M_OUTWALL)
    for (x, y, h) in ((-4.6, -3.6, 0.7), (-4.6, -2.9, 0.45), (-4.6, 1.6, 0.6)):   # pots on the parapet's foot
        cyl((x, y, 0), (x, y, 0.32), 0.15, M_POT, 16, r2=0.19)
        for k in range(9):
            sphere((x + rnd.uniform(-0.15, 0.15), y + rnd.uniform(-0.15, 0.15), 0.32 + rnd.uniform(0.05, h)), rnd.uniform(0.08, 0.14), M_LEAF2, 8, 6)
    surf(lambda u, v: Vector((-60 + u * 80, -40 + v * 80, -12.5)), 1, 1, M_GROUND, False)
    # the building across the road: cream plaster, rows of windows and balcony slabs
    BX = -21.0
    box(BX - 4, 9, 1, 8, 30, 27, M_OUTWALL)
    for fz in range(-12, 13, 3):
        box(BX + 0.25, 9, fz + 0.05, 0.6, 30, 0.12, M_OUTWALL)
        for wy in range(-4, 23, 4):
            box(BX + 0.02, wy, fz + 1.4, 0.06, 1.6, 1.3, M_OUTWIN)
    # neem trees on the road between: trunks, and canopies of many small leaf clusters
    for (tx, ty, th) in ((-10.5, 5.5, 9.0), (-12.5, 12.0, 8.0), (-9.5, -7.5, 8.5), (-13.5, -1.5, 7.0)):
        cyl((tx, ty, -12.5), (tx, ty, th - 3.5), 0.28, M_BARK, 10, r2=0.18)
        for k in range(220):
            r_ = rnd.uniform(0, 3.4); t = rnd.uniform(0, 2 * math.pi); z = rnd.uniform(-2.4, 2.4) * (1 - r_ / 4.5)
            sphere((tx + r_ * math.cos(t), ty + r_ * math.sin(t), th - 1.5 + z), rnd.uniform(0.18, 0.4), M_LEAF if k % 3 else M_LEAF2, 8, 5)

    # ---- the sofa wall, behind the person in the front view ----
    sx0, sx1, sy = -1.5, 1.0, Y1 - 0.48
    rbox((sx0 + sx1) / 2, sy, 0.24, sx1 - sx0, 0.9, 0.3, M_SOFA, r=0.05)               # base
    rbox((sx0 + sx1) / 2, sy + 0.05, 0.46, sx1 - sx0 - 0.36, 0.78, 0.16, M_SOFA, r=0.06)  # seat cushions (one long)
    rbox((sx0 + sx1) / 2, Y1 - 0.12, 0.62, sx1 - sx0, 0.22, 0.56, M_SOFA, r=0.07)       # back
    for x in (sx0 + 0.09, sx1 - 0.09): rbox(x, sy, 0.42, 0.18, 0.9, 0.38, M_SOFA, r=0.06)   # arms
    for x in (sx0 + 0.12, sx1 - 0.12):
        for y in (sy - 0.38, sy + 0.38): cyl((x, y, 0), (x, y, 0.09), 0.02, TEAK, 8, r2=0.014)
    for (x, m_, rot) in ((sx0 + 0.42, M_CUSH1, 0.12), (sx0 + 0.82, M_CUSH3, -0.05), (sx1 - 0.4, M_CUSH2, -0.15)):
        M = Matrix.Translation((x, Y1 - 0.33, 0.72)) @ Matrix.Rotation(math.radians(-14), 4, "X") @ Matrix.Rotation(rot, 4, "Y")
        t = bmesh.new(); bmesh.ops.create_cube(t, size=1, matrix=Matrix.Diagonal((0.44, 0.13, 0.44, 1)))
        bmesh.ops.bevel(t, geom=list(t.verts) + list(t.edges), offset=0.06, segments=3, affect="EDGES")
        bmesh.ops.transform(t, matrix=M, verts=t.verts); t.to_mesh(_scratch); t.free(); bm(m_).from_mesh(_scratch); SMOOTH.add(m_)
    # a print over the sofa: an ink-wash of hills on cotton paper, in a thin teak frame
    m, nt, p = node_mat("print"); p.inputs["Roughness"].default_value = 0.9
    tc = nt.nodes.new("ShaderNodeTexCoord"); sp = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sp.inputs[0])
    wv = nt.nodes.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 1.2; wv.inputs["Distortion"].default_value = 2.0; wv.bands_direction = "X"
    nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
    hill = nt.nodes.new("ShaderNodeMath"); hill.operation = "MULTIPLY_ADD"; hill.inputs[1].default_value = 0.18
    nt.links.new(wv.outputs["Fac"], hill.inputs[0]); hill.inputs[2].default_value = -0.12
    gt = nt.nodes.new("ShaderNodeMath"); gt.operation = "LESS_THAN"; nt.links.new(sp.outputs["Z"], gt.inputs[0]); nt.links.new(hill.outputs[0], gt.inputs[1])
    nt.links.new(mix_rgb(nt, gt.outputs[0], (0.74, 0.71, 0.64), (0.22, 0.24, 0.23)), p.inputs["Base Color"])
    px, pz = (sx0 + sx1) / 2 + 0.05, 1.62
    t = bpy.data.meshes.new("print"); o = bpy.data.objects.new("print", t); col.objects.link(o)
    tb = bmesh.new(); bmesh.ops.create_cube(tb, size=1, matrix=Matrix.Diagonal((0.78, 0.01, 0.56, 1))); tb.to_mesh(t); tb.free()
    o.location = (px, Y1 - 0.025, pz); o.data.materials.append(m)
    for (dx, dz, w_, h_) in ((0, 0.3, 0.84, 0.03), (0, -0.3, 0.84, 0.03), (-0.405, 0, 0.03, 0.63), (0.405, 0, 0.03, 0.63)):
        box(px + dx, Y1 - 0.025, pz + dz, w_, 0.03, h_, TEAK)
    # side table with a lamp at the left end; a tall areca palm in a pot at the right
    cyl((sx0 - 0.35, Y1 - 0.35, 0), (sx0 - 0.35, Y1 - 0.35, 0.55), 0.024, TEAK, 8)
    cyl((sx0 - 0.35, Y1 - 0.35, 0.55), (sx0 - 0.35, Y1 - 0.35, 0.58), 0.24, TEAK, 24)
    cyl((sx0 - 0.35, Y1 - 0.35, 0.58), (sx0 - 0.35, Y1 - 0.35, 0.92), 0.06, mat("ceramic", (0.5, 0.42, 0.32), 0.3), 16, r2=0.03)
    cyl((sx0 - 0.35, Y1 - 0.35, 0.9), (sx0 - 0.35, Y1 - 0.35, 1.12), 0.17, mat("shade", (0.75, 0.68, 0.55), 0.9), 24, r2=0.12)
    ax, ay = sx1 + 0.55, Y1 - 0.4
    cyl((ax, ay, 0), (ax, ay, 0.42), 0.18, M_POT, 20, r2=0.23)
    for k in range(14):                                            # palm fronds: arcs of small leaves
        t0 = k * 2.4; lean = rnd.uniform(0.25, 0.6); ln = rnd.uniform(1.0, 1.5)
        prev = Vector((ax, ay, 0.42))
        for s in range(1, 9):
            f = s / 8
            pt = Vector((ax + math.cos(t0) * lean * f * ln, ay + math.sin(t0) * lean * f * ln, 0.42 + ln * (f - 0.35 * f * f) * 1.2))
            cyl(prev, pt, 0.008, M_LEAF2, 5); prev = pt
            for sd in (-1, 1):
                q = pt + Vector((-math.sin(t0) * sd * 0.16, math.cos(t0) * sd * 0.16, -0.06))
                cyl(pt, q, 0.012, M_LEAF, 4, r2=0.003)
    # rug and coffee table between the person and the sofa (the floor at the bottom of the front view)
    box(-0.3, 1.95, 0.004, 2.6, 1.8, 0.008, RUG)
    rbox(-0.3, 1.95, 0.4, 1.1, 0.6, 0.04, TEAK, r=0.01)
    for dx in (-0.48, 0.48):
        for dy in (-0.24, 0.24): box(-0.3 + dx, 1.95 + dy, 0.19, 0.04, 0.04, 0.38, TEAK)
    rbox(-0.55, 1.9, 0.44, 0.28, 0.2, 0.04, BOOKS[0], r=0.004, rot=0.1)
    rbox(-0.55, 1.9, 0.475, 0.25, 0.18, 0.03, BOOKS[4], r=0.004, rot=-0.05)
    cyl((-0.05, 2.0, 0.42), (-0.05, 2.0, 0.5), 0.07, M_BRASS, 20, r2=0.11)

    # ---- the right wall: bookshelf, a cane chair, the split AC high up, switchboards ----
    bx, by0, by1 = X1 - 0.18, -0.6, 1.3
    for z in (0.02, 0.42, 0.82, 1.22, 1.62, 2.0): box(bx, (by0 + by1) / 2, z, 0.34, by1 - by0, 0.03, TEAK)
    for y in (by0, (by0 + by1) / 2, by1): box(bx, y, 1.01, 0.34, 0.03, 2.0, TEAK)
    for z in (0.035, 0.435, 0.835, 1.235, 1.635):
        y = by0 + 0.04
        while y < by1 - 0.06:
            if abs(y - (by0 + by1) / 2) < 0.04: y += 0.05; continue
            w_ = rnd.uniform(0.025, 0.05); h_ = rnd.uniform(0.2, 0.3)
            if rnd.random() < 0.1: y += rnd.uniform(0.1, 0.25); continue
            box(bx + 0.02, y + w_ / 2, z + h_ / 2, rnd.uniform(0.15, 0.22), w_, h_, BOOKS[rnd.randrange(len(BOOKS))])
            y += w_ + 0.003
    cyl((bx, by1 - 0.3, 2.02), (bx, by1 - 0.3, 2.2), 0.07, M_POT, 12, r2=0.09)
    for k in range(10):
        sphere((bx + rnd.uniform(-0.1, 0.1), by1 - 0.3 + rnd.uniform(-0.15, 0.15), 2.15 - rnd.uniform(0, 0.6)), 0.05, M_LEAF2, 8, 5, s=(1, 1, 1.6))
    rbox(X1 - 0.13, -2.1, 2.45, 0.24, 0.98, 0.3, M_WHITE, r=0.04)                     # split AC
    box(X1 - 0.255, -2.1, 2.33, 0.01, 0.8, 0.03, M_BLACK)
    box(X1 - 0.01, -3.1, 1.2, 0.02, 0.2, 0.12, M_WHITE)                              # switchboards
    box(DX0 - 0.25, Y0 + 0.01, 1.2, 0.2, 0.02, 0.12, M_WHITE)
    # a cane chair turned toward the window
    ch = Matrix.Translation((2.75, -1.5, 0)) @ Matrix.Rotation(0.6, 4, "Z")
    M_CANE = mat("cane", (0.42, 0.3, 0.16), 0.7)
    for (dx, dy) in ((-0.3, -0.3), (0.3, -0.3), (-0.3, 0.3), (0.3, 0.3)):
        a_ = ch @ Vector((dx, dy, 0)); b_ = ch @ Vector((dx * 0.9, dy * 0.9, 0.42))
        cyl(a_, b_, 0.02, TEAK, 8)
    M = ch @ Matrix.Translation((0, 0, 0.44)) @ Matrix.Diagonal((0.64, 0.62, 0.05, 1)); bmesh.ops.create_cube(bm(M_CANE), size=1, matrix=M)
    M = ch @ Matrix.Translation((0, 0.3, 0.75)) @ Matrix.Rotation(math.radians(-12), 4, "X") @ Matrix.Diagonal((0.62, 0.04, 0.6, 1)); bmesh.ops.create_cube(bm(M_CANE), size=1, matrix=M)

    # ---- behind the camera: the dining corner, a console with a brass lamp ----
    tx, ty = -1.0, -3.25
    rbox(tx, ty, 0.75, 1.4, 0.8, 0.04, TEAK, r=0.01)
    for dx in (-0.62, 0.62):
        for dy in (-0.32, 0.32): box(tx + dx, ty + dy, 0.37, 0.05, 0.05, 0.74, TEAK)
    for dx in (-0.35, 0.35):
        for side in (-1, 1):
            cx_, cy2 = tx + dx, ty + side * 0.62
            box(cx_, cy2, 0.45, 0.42, 0.42, 0.04, TEAK)
            for ex_ in (-0.18, 0.18):
                for ey_ in (-0.18, 0.18): box(cx_ + ex_, cy2 + ey_, 0.22, 0.03, 0.03, 0.44, TEAK)
            box(cx_, cy2 + side * 0.19, 0.72, 0.42, 0.03, 0.5, TEAK)
    cyl((tx, ty, ZT), (tx, ty, 2.1), 0.004, M_BLACK, 6)
    cyl((tx, ty, 2.1), (tx, ty, 1.88), 0.04, M_BRASS, 20, r2=0.2)
    box(-2.4, Y0 + 0.2, 0.8, 0.9, 0.35, 0.04, TEAK)
    for x in (-2.8, -2.0): box(x, Y0 + 0.2, 0.4, 0.04, 0.3, 0.8, TEAK)
    cyl((-2.6, Y0 + 0.2, 0.82), (-2.6, Y0 + 0.2, 0.86), 0.06, M_BRASS, 16)
    cyl((-2.6, Y0 + 0.2, 0.86), (-2.6, Y0 + 0.2, 1.08), 0.012, M_BRASS, 8)
    cyl((-2.6, Y0 + 0.2, 1.08), (-2.6, Y0 + 0.2, 1.12), 0.05, M_BRASS, 16, r2=0.065)
    cyl((-2.15, Y0 + 0.2, 0.82), (-2.15, Y0 + 0.2, 1.0), 0.06, M_POT, 12, r2=0.075)
    for k in range(12):                                            # money plant trailing over the edge
        sphere((-2.15 + rnd.uniform(-0.2, 0.2), Y0 + 0.2 + rnd.uniform(-0.12, 0.12), 1.0 - rnd.uniform(0, 0.5)), 0.04, M_LEAF2, 8, 5)
    # wall clock
    cyl((0.4, Y0 + 0.005, 2.1), (0.4, Y0 + 0.035, 2.1), 0.16, TEAK, 32)
    cyl((0.4, Y0 + 0.035, 2.1), (0.4, Y0 + 0.04, 2.1), 0.145, mat("dial", (0.76, 0.74, 0.7), 0.4), 32)
    # a tall rubber plant by the window, a ceiling fan over the room, a round LED light (off)
    cyl((-2.75, 2.45, 0), (-2.75, 2.45, 0.38), 0.17, M_POT, 20, r2=0.21)
    for k in range(26):
        h = rnd.uniform(0.5, 1.7); t = rnd.uniform(0, 2 * math.pi); r_ = rnd.uniform(0.05, 0.35)
        sphere((-2.75 + r_ * math.cos(t), 2.45 + r_ * math.sin(t), 0.38 + h), 0.09, M_LEAF, 10, 6, s=(1, 0.35, 1.5))
    cyl((-2.75, 2.45, 0.38), (-2.75, 2.45, 1.9), 0.015, M_BARK, 6)
    fx_, fy_ = 0.3, 0.6
    cyl((fx_, fy_, ZT), (fx_, fy_, ZT - 0.35), 0.012, M_FAN, 8)
    cyl((fx_, fy_, ZT - 0.33), (fx_, fy_, ZT - 0.45), 0.13, M_FAN, 24, r2=0.11)
    for k in range(3):
        t = k * 2 * math.pi / 3 + 0.3
        box(fx_ + 0.42 * math.cos(t), fy_ + 0.42 * math.sin(t), ZT - 0.42, 0.62, 0.11, 0.008, M_FAN, rot=t)
    cyl((0.3, -2.4, ZT), (0.3, -2.4, ZT - 0.03), 0.15, M_WHITE, 32)

    # ---- daylight: a late-afternoon sun low over the road, a clear sky that is warm at the horizon ----
    sun = bpy.data.lights.new("sun", "SUN"); sun.energy = SUN_E; sun.color = SUN_TINT; sun.angle = math.radians(0.55)
    so = bpy.data.objects.new("sun", sun); col.objects.link(so)
    so.rotation_mode = "QUATERNION"; so.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(SUN_DIR)
    SKY = True


def build_show():
    """The show (the picture the viewer has had since the start), with arched roof steel and rows of light battens
    over the crowd, and the hard front lights the person is lit by placed where they really hang."""
    global ZC
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
    M_BATTEN = emission("batten", (1.0, 0.8, 0.6), 1.6)

    HX, Y0, Y1, HZ = 22.0, -26.0, 38.0, 17.0
    ZC = HZ
    surf(lambda u, v: Vector((-HX + u * 2 * HX, Y0 + v * (Y1 - Y0), 0)), 1, 1, M_FLOOR, False)
    box(0, (Y0 + Y1) / 2, HZ + 0.2, 2 * HX, Y1 - Y0, 0.4, M_BLACK)            # ceiling
    box(-HX - 0.2, (Y0 + Y1) / 2, HZ / 2, 0.4, Y1 - Y0, HZ, M_BLACK)           # side walls
    box(HX + 0.2, (Y0 + Y1) / 2, HZ / 2, 0.4, Y1 - Y0, HZ, M_BLACK)
    box(0, Y0 - 0.2, HZ / 2, 2 * HX, 0.4, HZ, M_BLACK)                         # behind the stage
    box(0, Y1 + 0.2, HZ / 2, 2 * HX, 0.4, HZ, M_BLACK)                         # back of the hall
    # the roof: iron arches across the hall every 8 m, springing from the walls (a Victorian exhibition hall),
    # with purlins along it; they only show where the haze is lit
    for y in range(int(Y0) + 4, int(Y1), 8):
        prev = None
        for k in range(25):
            t = math.pi * k / 24
            pt = Vector((HX * math.cos(t), y, 10.5 + (HZ - 0.6 - 10.5) * math.sin(t)))
            if prev is not None:
                cyl(prev, pt, 0.18, M_TRUSS, 8)
                cyl(prev + Vector((0, 0, -0.9)), pt + Vector((0, 0, -0.9 * (0.4 + 0.6 * math.sin(t)))), 0.05, M_TRUSS, 6)
            prev = pt
    for x in (-15, -8, 0, 8, 15):
        z = 10.5 + (HZ - 0.6 - 10.5) * math.sin(math.acos(x / HX))
        cyl((x, Y0, z), (x, Y1, z), 0.08, M_TRUSS, 6)

    # ---------- the stage: low deck, backline of flight cases, a long desk with lamps ----------
    SY0, SY1, SZ = -11.5, -19.5, 1.4
    box(0, (SY0 + SY1) / 2, SZ / 2, 22, SY0 - SY1, SZ, M_STAGE)
    box(0, SY0 + 0.05, SZ / 2, 22, 0.1, SZ, M_BLACK)                  # the dark stage front
    for x in range(-11, 12):                                          # barrier in front of the stage
        box(x, SY0 + 1.6, 0.55, 0.96, 0.08, 1.1, M_ALU)
    box(0, -14.2, SZ + 0.45, 3.4, 0.9, 0.9, M_WOOD)                   # the desk, small screens and pads glow faintly
    for i, x in enumerate((-1.2, -0.45, 0.35, 1.1)):
        box(x, -14.0, SZ + 0.93, 0.5, 0.35, 0.05, M_CASE)
        box(x, -14.1, SZ + 0.97, 0.38, 0.22, 0.01, emission(f"pad{i}", (1.0, 0.55, 0.25) if i % 2 else (0.85, 0.9, 1.0), 1.5))
    for side in (-1, 1):                                              # backline: stacks of flight cases
        for k in range(5):
            x = side * (3.2 + k * 1.45 + rnd.uniform(-0.15, 0.15))
            h = 0
            for j in range(rnd.randint(1, 3)):
                sz = rnd.uniform(0.6, 1.1); sx = rnd.uniform(1.0, 1.35)
                box(x, -16.8 + rnd.uniform(-0.6, 0.6), SZ + h + sz / 2, sx, 0.9, sz, M_CASE)
                for zz in (h, h + sz):
                    box(x, -16.8 + 0.46, SZ + zz, sx + 0.02, 0.03, 0.03, M_ALU)
                h += sz
    LAMPS = [(-1.55, -14.4, SZ + 0.9), (1.55, -14.3, SZ + 0.9), (-5.1, -16.4, SZ + 1.9), (4.6, -16.2, SZ + 2.2), (-8.0, -16.5, SZ + 1.3), (7.9, -16.6, SZ + 1.6)]
    for i, (x, y, z) in enumerate(LAMPS):                             # desk lamps: warm bulbs under small shades
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

    for i in range(14):                                              # a row of plain white tubes across the back
        x = -9.75 + i * 1.5
        cyl((x, -18.2, SZ), (x, -18.2, SZ + 2.6), 0.03, M_TUBE, 10)
    light("AREA", (0, -18.0, SZ + 1.3), (0, -10, SZ + 1.3), 300, (0.9, 0.93, 1.0), size=2)

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
        tgt = (x * 0.55 + rnd.uniform(-2.5, 2.5), rnd.uniform(-9, 4), 0) if i % 2 == 0 else (x * 2.2, rnd.uniform(4, 18), rnd.uniform(9, 15))
        light("SPOT", (x, -12.6, TZ - 0.65), tgt, 9000, (0.88, 0.92, 1.0), size=0.05, spot=3.5, blend=0.25)
    for i in range(7):                                                 # warm pars from the back truss onto the backline
        x = -9 + i * 3
        cyl((x, -18.6, TZ + 0.55), (x, -18.6, TZ + 0.2), 0.12, M_CASE, 16)
        light("SPOT", (x, -18.6, TZ + 0.15), (x * 0.8, -15.5, SZ), 1800, (1.0, 0.58, 0.28), size=0.1, spot=24, blend=0.5)
    for side in (-1, 1):                                               # low cool washes from the stage floor
        light("SPOT", (side * 10.5, -14.5, SZ + 0.4), (side * 2, -15, 4), 1500, (0.8, 0.86, 1.0), size=0.1, spot=30, blend=0.6)
    # the hard front lights the person in the viewer is lit by (scene.ts "show"), as real fixtures where they hang:
    # a warm par on the front truss's end, a cool head over the barrier, a follow spot on a side tower
    for name, pos3, size, power, tint in SHOW_LIGHTS:
        if name == "foh": continue
        p = three(pos3)
        cyl(p + Vector((0, 0, 0.35)), p, 0.16, M_CASE, 16)
        # the same light on the crowd around the person (a spot as wide as the patch the viewer's light paints)
        light("SPOT", p, (0, 0, 1.0), power * 4, tint, size=max(size) / 2, spot=16, blend=0.6)
        if name == "spot":   # its tower: a truss leg from the floor
            for dx in (-0.2, 0.2):
                for dy in (-0.2, 0.2): cyl((p.x + dx, p.y + dy, 0), (p.x + dx, p.y + dy, p.z + 0.2), 0.025, M_TRUSS, 6)
    # rows of warm light battens across the hall over the crowd, dimmed right down: lines in the haze
    for y in range(-9, 19, 4):
        for k in range(6):
            x0 = -13.5 + k * 4.6
            cyl((x0, y, 9.2), (x0 + 3.8, y, 9.2), 0.035, M_BATTEN, 8)
        cyl((-14, y, 9.28), (14, y, 9.28), 0.02, M_TRUSS, 6)
    for (x, y) in ((-9, -2), (9, 6), (0, 16), (-6, 26), (7, 26)):     # house lights, nearly out
        light("POINT", (x, y, HZ - 1.2), None, 120, (1.0, 0.62, 0.34), size=0.3)

    # ---------- front of house, behind the person: the desk, follow spots on a truss, the balcony ----------
    FOH_Y = 21.0
    box(0, FOH_Y, 0.5, 6, 3, 1.0, M_CASE)
    box(0, FOH_Y + 1.2, 1.4, 6, 0.6, 1.8, M_CASE)
    for i, x in enumerate((-2.2, -1.1, 0.0, 1.1, 2.2)):
        box(x, FOH_Y - 0.3, 1.08, 0.7, 0.45, 0.02, emission(f"desk{i}", (0.55, 0.7, 1.0) if i % 2 else (1.0, 0.78, 0.55), 0.8))
    for x in (-2.6, 2.6):
        light("POINT", (x, FOH_Y - 0.5, 1.6), None, 12, (1.0, 0.62, 0.32), size=0.04)
    truss(FOH_Y - 3, 9.5, -8, 8)
    for x in (-5.5, 5.5):                                              # FOH spots: they light the crowd from behind
        cyl((x, FOH_Y - 3, 9.2), (x, FOH_Y - 3.6, 8.9), 0.16, M_CASE, 16)
        light("SPOT", (x, FOH_Y - 3.7, 8.85), (x * 0.3, -2, 1.2), 2400, (1.0, 0.86, 0.7), size=0.08, spot=9, blend=0.4)
    box(0, 31, 5.2, 2 * HX, 1.2, 1.0, M_CASE)                          # balcony front, its lamps, exit signs
    for x in range(-20, 21, 4):
        light("POINT", (x, 30.3, 5.9), None, 6, (1.0, 0.6, 0.3), size=0.05)
    for x in (-17, 17):
        box(x, Y1 - 0.05, 3.2, 0.45, 0.04, 0.2, M_EXIT)
    for side in (-1, 1):
        for y in range(-6, 34, 8):
            light("POINT", (side * (HX - 0.5), y, 5.5), None, 8, (1.0, 0.55, 0.28), size=0.1)

    def person(x, y, h, face, arms):
        s = h / 1.72
        fx, fy = math.cos(face), math.sin(face)
        rx, ry = -fy, fx
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
            face = math.atan2(-14 - y, -x) if rnd.random() < 0.85 else rnd.uniform(-math.pi, math.pi)
            up = rnd.random() < (0.32 if y < 0 else 0.18)
            person(x, y, rnd.uniform(1.55, 1.86), face, up)
            if not up and phones < 22 and rnd.random() < 0.06:
                phones += 1
                fx, fy = math.cos(face), math.sin(face)
                box(x + fx * 0.35, y + fy * 0.35, 1.9, 0.07, 0.008, 0.14, M_PHONE, rot=face + math.pi / 2)

    vm = bpy.data.materials.new("haze"); vm.use_nodes = True; nt = vm.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
    pv_ = nt.nodes.new("ShaderNodeVolumePrincipled"); pv_.inputs["Density"].default_value = 0.022; pv_.inputs["Anisotropy"].default_value = 0.55
    nt.links.new(pv_.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    box(0, (Y0 + Y1) / 2, HZ / 2, 2 * HX - 0.2, Y1 - Y0 - 0.2, HZ - 0.2, vm)


# ---------- the viewer's lights (scene.ts), three coordinates: name, pos, size, power, tint ----------
STUDIO_LIGHTS = [
    ("key", (-0.95, 2.35, 2.4), (1.2, 1.2), 90, (1, 0.985, 0.96)),
    ("fill", (1.5, 1.7, 1.85), (0.9, 1.3), 25, (0.97, 0.98, 1)),
    ("rimL", (-1.8, 2.2, -1.35), (0.35, 1.5), 50, (1, 1, 1)),
    ("rimR", (1.85, 2.2, -1.45), (0.35, 1.5), 50, (1, 1, 1)),
    ("top", (0.6, 3.25, -2.0), (1.0, 1.0), 55, (1, 0.99, 0.97)),
]
CYCW = float(os.environ.get("CYCW", "30"))     # each cyc panel, Blender watts
SHOW_LIGHTS = [
    ("stage", (1.5, 10.35, 12.6), (0.4, 0.4), 6000, (1, 0.8, 0.6)),
    ("beam", (-2.5, 10.35, 12.6), (0.2, 0.2), 2700, (0.86, 0.91, 1)),
    ("spot", (-9.0, 7.0, 4.0), (0.3, 0.3), 1000, (1, 0.72, 0.45)),
    ("foh", (-1.4, 3.5, -3.6), (0.8, 0.8), 480, (1, 0.86, 0.7)),
]
# daylight: the sun's direction (towards it) in three is (-0.696, 0.264, 0.668): front-left, 15 deg up
SUN_DIR = three((-0.696, 0.264 + FLOOR, 0.668)).normalized()
SUN_E = float(os.environ.get("SUNE", "5"))     # W/m2 on a surface facing it (Blender sun strength)
SUN_TINT = (1.0, 0.8, 0.6)
SKY_K = float(os.environ.get("SKYK", "5.0"))   # the sky, exposed for a room lit by it
ZC = 100.0

{"studio": build_studio, "window": build_window, "show": build_show}[PLACE]()
flush()

# ---------- world ----------
sc.world = bpy.data.worlds.new("w"); sc.world.use_nodes = True
nt = sc.world.node_tree; bg = nt.nodes["Background"]
if SKY:
    # a clear sky by elevation: warm, bright haze at the horizon to a soft blue overhead, brighter toward the sun
    tc = nt.nodes.new("ShaderNodeTexCoord"); sp = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Generated"], sp.inputs[0])
    rmp = nt.nodes.new("ShaderNodeValToRGB"); nt.links.new(sp.outputs["Z"], rmp.inputs[0])
    cr = rmp.color_ramp; cr.elements[0].position = 0.0; cr.elements[0].color = (1.9 * SKY_K, 1.75 * SKY_K, 1.55 * SKY_K, 1)
    cr.elements[1].position = 0.6; cr.elements[1].color = (0.55 * SKY_K, 0.78 * SKY_K, 1.25 * SKY_K, 1)
    dp = nt.nodes.new("ShaderNodeVectorMath"); dp.operation = "DOT_PRODUCT"; dp.inputs[1].default_value = SUN_DIR
    nt.links.new(tc.outputs["Generated"], dp.inputs[0])
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 8.0; pw.use_clamp = False
    cl = nt.nodes.new("ShaderNodeMath"); cl.operation = "MAXIMUM"; cl.inputs[1].default_value = 0.0
    nt.links.new(dp.outputs["Value"], cl.inputs[0]); nt.links.new(cl.outputs[0], pw.inputs[0])
    gl = nt.nodes.new("ShaderNodeMath"); gl.operation = "MULTIPLY_ADD"; gl.inputs[1].default_value = 2.5; gl.inputs[2].default_value = 1.0
    nt.links.new(pw.outputs[0], gl.inputs[0])
    mm = nt.nodes.new("ShaderNodeVectorMath"); mm.operation = "SCALE"
    nt.links.new(rmp.outputs["Color"], mm.inputs[0]); nt.links.new(gl.outputs[0], mm.inputs["Scale"])
    nt.links.new(mm.outputs[0], bg.inputs[0]); bg.inputs[1].default_value = 1.0
else:
    bg.inputs[0].default_value = (0.002, 0.002, 0.0025, 1) if PLACE == "show" else (0, 0, 0, 1)

# ---------- LOOK=<yaw>[,white]: a small check of the person in the tee at this place, from the viewer's camera ----------
LOOK = os.environ.get("LOOK")
if LOOK:
    yaw, *tone = LOOK.split(",")
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public", "tee")
    for f in ("human/m170-stand.glb", "fit/m170-M/stand.glb"):
        before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=os.path.join(root, f))
        for o in set(bpy.data.objects) - before:
            if o.type != "MESH": continue
            for slot in o.material_slots:
                pm = slot.material; pm.use_nodes = True; nt_ = pm.node_tree; pb = nt_.nodes.get("Principled BSDF")
                if pb is None: continue
                kind = next((k for k in ("skin", "jeans", "eyes") if k in (pm.name + o.name).lower()), None) if f.startswith("human") else None
                if kind:
                    vc = nt_.nodes.new("ShaderNodeVertexColor"); vc.layer_name = o.data.color_attributes[0].name
                    nt_.links.new(vc.outputs[0], pb.inputs["Base Color"])
                    pb.inputs["Roughness"].default_value = {"skin": 0.5, "jeans": 0.85, "eyes": 0.12}[kind]
                else:   # the tee: plain jersey in black or white
                    for n_ in list(nt_.nodes):
                        if n_.type not in ("BSDF_PRINCIPLED", "OUTPUT_MATERIAL"): nt_.nodes.remove(n_)
                    pb.inputs["Base Color"].default_value = (0.78, 0.77, 0.74, 1) if tone else (0.012, 0.012, 0.012, 1)
                    pb.inputs["Roughness"].default_value = 0.9; pb.inputs["Sheen Weight"].default_value = 0.4
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); col.objects.link(cam); sc.camera = cam
    p0 = Matrix.Rotation(-math.radians(float(yaw)), 3, "Z") @ three((0.2, FLOOR + 1.1, 2.85))
    cam.location = p0; cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = (Matrix.Rotation(-math.radians(float(yaw)), 3, "Z") @ three((0, FLOOR + 0.99, 0)) - p0).to_track_quat("-Z", "Y")
    cam.data.lens = LENS; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 36
    cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = FSTOP; cam.data.dof.focus_distance = FOCUS
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
    sc.cycles.diffuse_bounces = 4; sc.cycles.max_bounces = 8; sc.cycles.blur_glossy = 0.6
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 220, 280, 100
    sc.view_settings.view_transform = "Khronos PBR Neutral"
    sc.render.filepath = OUT; bpy.ops.render.render(write_still=True)
    print("look", OUT); bpy.ops.wm.quit_blender()

# ---------- the camera: the viewer's camera, walking its ring ----------
osl = OUT.rsplit(".", 1)[0] + ".osl"
open(osl, "w").write(f"""
shader camera(output point position = 0.0, output vector direction = 0.0, output color throughput = 1.0)
{{
  point r = camera_shader_raster_position();
  float phi = (0.5 - r[0]) * M_2PI, e = (r[1] - 0.5) * M_PI;
  vector d = vector(sin(phi) * cos(e), -cos(phi) * cos(e), sin(e));        // Blender world
  point o = point(-{RING} * sin(phi), {RING} * cos(phi), {EYE});
  // the lens: a thin lens focused on the person; the aperture sample Cycles gives is {0.5 / FSTOP:.5f} at most
  point ap = point(0); getattribute("cam:aperture_position", ap);
  vector rt = normalize(cross(d, vector(0, 0, 1))), up = cross(rt, d);
  point o2 = o + (rt * ap[0] + up * ap[1]) * ({LENS / 1000 / (2 * FSTOP)} / {0.5 / FSTOP});
  vector d2 = normalize(o + d * {FOCUS} - o2);
  // only what lies beyond the person: start just short of them, never under the floor or over the ceiling
  float t0 = {0.88 * RING};
  if (d2[2] < -1e-4) t0 = min(t0, (o2[2] - 0.02) / -d2[2]);
  if (d2[2] > 1e-4) t0 = min(t0, ({ZC} - o2[2] - 0.02) / d2[2]);
  point s = o2 + d2 * max(t0, 0.0);
  direction = vector(d2[0], d2[1], -d2[2]);
  position = point(s[0], s[1], -s[2]);
}}
""")
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); col.objects.link(cam); sc.camera = cam
cam.data.type = "CUSTOM"; cam.data.custom_mode = "EXTERNAL"; cam.data.custom_filepath = osl
cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = FSTOP; cam.data.dof.focus_distance = FOCUS
cam.data.clip_start = 0.0005; cam.data.clip_end = 1000.0   # the rays already start where they should
r = sc.render
r.engine = "CYCLES"; r.resolution_x = W; r.resolution_y = W // 2; r.resolution_percentage = 100
r.use_border = STRIPS > 1; r.use_crop_to_border = True
r.border_min_x, r.border_max_x = 0, 1
r.border_max_y = 1 - STRIP / STRIPS; r.border_min_y = 1 - (STRIP + 1) / STRIPS   # strip 0 is the top
r.image_settings.file_format = "OPEN_EXR"; r.image_settings.color_depth = "16"
r.filepath = OUT
cy = sc.cycles
cy.device = "CPU"; cy.shading_system = True
cy.samples = SAMPLES; cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.015
cy.use_denoising = True
cy.caustics_reflective = False; cy.caustics_refractive = False
cy.sample_clamp_indirect = 6.0
if PLACE == "show":
    cy.max_bounces = 4; cy.diffuse_bounces = 2; cy.glossy_bounces = 2; cy.transmission_bounces = 2; cy.volume_bounces = 1
    cy.volume_step_rate = 2.0; cy.sample_clamp_indirect = 4.0
else:   # white rooms are lit mostly by their own walls: let the light go round
    cy.max_bounces = 10; cy.diffuse_bounces = 6; cy.glossy_bounces = 3; cy.transmission_bounces = 6; cy.transparent_max_bounces = 8
    cy.blur_glossy = 0.6
r.threads_mode = "AUTO"
bpy.ops.render.render(write_still=True)
import numpy as np
im = bpy.data.images.load(OUT); w, h = im.size
px = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(px)
np.save(OUT.rsplit(".", 1)[0] + ".npy", px.reshape(h, w, 4)[::-1, :, :3].astype(np.float16))
print("saved", PLACE, OUT, "strip", STRIP, "of", STRIPS, w, "x", h)
