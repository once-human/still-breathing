# blender -b --factory-startup -P stage.py -- <place> <out.exr> [strip strips] [samples] [width]
# The places behind the person in the shop viewer, each one 360 degree picture rendered in Cycles:
#   studio, window   the old built rooms; the viewer now uses real photographs of real rooms (photo_place.py)
#   show    the night in the round at Alexandra Palace (Fred again.. and Thomas Bangalter, USB002, Feb 2026), built
#           from that night's photographs as reference: the Great Hall dark round it, a canopy of sheer white cloth
#           in rings of swags (simulated as real cloth by canopy.py), the long low stage with the table and its desk
#           lamps, a crowd on the stage, search lights, beams through haze; the crowd all round is every fitted body
#           (public/tee/fit) in its simulated tee, standing or with arms up, Indian skin, hair, jeans
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


PH = os.path.expanduser("~/.cache/polyhaven")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def screen_mat(name, art, strength):
    """an LED wall showing one of the shop's artworks (pipeline/art): its lines glow, the rest is the screen's black"""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(art, check_existing=True); t.extension = "CLIP"
    e = nt.nodes.new("ShaderNodeEmission")
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"
    nt.links.new(t.outputs["Alpha"], mx.inputs["Factor"]); mx.inputs[6].default_value = (0.004, 0.004, 0.005, 1)
    nt.links.new(t.outputs["Color"], mx.inputs[7]); nt.links.new(mx.outputs[2], e.inputs[0]); e.inputs[1].default_value = strength
    d = nt.nodes.new("ShaderNodeBsdfDiffuse"); d.inputs[0].default_value = (0.01, 0.01, 0.01, 1)
    ad = nt.nodes.new("ShaderNodeAddShader"); nt.links.new(e.outputs[0], ad.inputs[0]); nt.links.new(d.outputs[0], ad.inputs[1])
    nt.links.new(ad.outputs[0], nt.nodes["Material Output"].inputs[0])
    return m


def plane(c, w, h, m, face):
    """an upright rectangle with UVs (0..1 across, 0..1 up), centre c, facing `face` (a level direction)"""
    f = Vector(face).normalized(); rt = Vector((0, 0, 1)).cross(f).normalized()
    me = bpy.data.meshes.new("pl"); hw, hh = rt * (w / 2), Vector((0, 0, h / 2)); c = Vector(c)
    me.from_pydata([c - hw - hh, c + hw - hh, c + hw + hh, c - hw + hh], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(); [setattr(uv.data[i], "uv", q) for i, q in enumerate(((0, 0), (1, 0), (1, 1), (0, 1)))]
    o = bpy.data.objects.new("pl", me); col.objects.link(o); me.materials.append(m); return o


def crowd_materials():
    """the people: Indian skin tones, dark hair, jeans or dark trousers, shoes, each person their own (Object Info
    random, per instance); the tee in the shop's colours, most of the crowd in black"""
    def ramp(nt, fac, stops, constant=False):
        r = nt.nodes.new("ShaderNodeValToRGB"); nt.links.new(fac, r.inputs[0]); cr = r.color_ramp
        if constant: cr.interpolation = "CONSTANT"
        while len(cr.elements) < len(stops): cr.elements.new(0.5)
        for el, (pos, c) in zip(cr.elements, stops): el.position = pos; el.color = (*c, 1)
        return r.outputs[0]
    def hashed(nt, rnd_out, k):
        mu = nt.nodes.new("ShaderNodeMath"); mu.operation = "MULTIPLY"; mu.inputs[1].default_value = k
        fr = nt.nodes.new("ShaderNodeMath"); fr.operation = "FRACT"
        nt.links.new(rnd_out, mu.inputs[0]); nt.links.new(mu.outputs[0], fr.inputs[0]); return fr.outputs[0]
    m, nt, p = node_mat("people")
    oi = nt.nodes.new("ShaderNodeObjectInfo"); ca = nt.nodes.new("ShaderNodeVertexColor"); ca.layer_name = "mask"
    sp = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(ca.outputs["Color"], sp.inputs[0])
    skin = ramp(nt, oi.outputs["Random"], [(0, (0.075, 0.03, 0.012)), (0.45, (0.2, 0.09, 0.04)), (1, (0.42, 0.21, 0.1))])
    legs = ramp(nt, hashed(nt, oi.outputs["Random"], 7.31), [(0, (0.022, 0.03, 0.055)), (0.45, (0.01, 0.01, 0.012)), (0.75, (0.05, 0.055, 0.06)), (0.9, (0.16, 0.13, 0.08))], True)
    hair = ramp(nt, hashed(nt, oi.outputs["Random"], 3.77), [(0, (0.008, 0.006, 0.005)), (0.85, (0.03, 0.018, 0.01))], True)
    shoe = ramp(nt, hashed(nt, oi.outputs["Random"], 11.9), [(0, (0.012, 0.012, 0.012)), (0.6, (0.6, 0.6, 0.58)), (0.8, (0.08, 0.06, 0.05))], True)
    c = mix_rgb(nt, sp.outputs[1], skin, legs); c = mix_rgb(nt, sp.outputs[0], c, hair); c = mix_rgb(nt, sp.outputs[2], c, shoe)
    nt.links.new(c, p.inputs["Base Color"])
    rough = nt.nodes.new("ShaderNodeMath"); rough.operation = "MULTIPLY_ADD"; rough.inputs[1].default_value = 0.35; rough.inputs[2].default_value = 0.5
    nt.links.new(sp.outputs[1], rough.inputs[0]); nt.links.new(rough.outputs[0], p.inputs["Roughness"])
    p.inputs["Sheen Weight"].default_value = 0.15
    t, ntt, pt = node_mat("crowd tee")
    oi2 = ntt.nodes.new("ShaderNodeObjectInfo")
    tee = ramp(ntt, hashed(ntt, oi2.outputs["Random"], 2.13), [(0, (0.012, 0.012, 0.012)), (0.68, (0.62, 0.6, 0.55)), (0.84, (0.12, 0.12, 0.12)), (0.93, (0.07, 0.07, 0.04))], True)
    ntt.links.new(tee, pt.inputs["Base Color"]); pt.inputs["Roughness"].default_value = 0.9; pt.inputs["Sheen Weight"].default_value = 0.4
    return m, t


def arm_axes(vs, top):
    """each arm of a body in the fit's rest A-pose: the shoulder joint and the arm's direction (to the wrist)"""
    out = []
    for side in (-1, 1):
        arm = [c for c in vs if side * c.x > 0.3 * top / 1.71 and c.z > 0.45 * top]
        tip = max(arm, key=lambda c: side * c.x)                                       # the fingertips
        sh = Vector((side * 0.165 * top / 1.71, sum(c.y for c in arm) / len(arm), 0.81 * top))
        d = (tip - sh); d.y = 0; d.normalize()
        out.append((side, sh, d))
    return out


def relax_arms(me, arms, drop=20.0):
    """lower the arms by `drop` degrees about the shoulder (toward the sides, as people stand), with a weight that
    fades in from the armpit like a skin's; the body and its tee get the same field, so the sleeve stays on the arm"""
    for v in me.vertices:
        c = v.co.copy()
        for side, sh, d in arms:
            q = c - sh; t = q.x * d.x + q.z * d.z
            if t <= -0.02: continue
            perp = (Vector((q.x, 0, q.z)) - Vector((d.x, 0, d.z)) * t).length
            w = min(1.0, max(0.0, (t + 0.02) / 0.1)) * (1 - min(1.0, max(0.0, (perp - 0.1) / 0.05)))
            if w <= 0: continue
            R = Matrix.Rotation(math.radians(side * drop * w), 3, "Y")
            v.co = sh + R @ q
    me.update()


def crowd_kinds():
    """every fitted body (public/tee/fit: 19 bodies and sizes) standing and with arms up, each in its own simulated
    tee, as collections to instance. The body gets a 'mask' (hair, legs, shoes) from where its vertices are."""
    people, tee_m = crowd_materials()
    hair_m = mat("hair", (0.01, 0.008, 0.006), 0.45, sheen=0.5)
    fit = os.path.join(ROOT, "public", "tee", "fit")
    kinds = {"stand": [], "up": []}
    for v in sorted(os.listdir(fit)):
        if v.startswith("form") or not os.path.exists(os.path.join(fit, v, "body-stand.glb")): continue
        for pose in kinds:
            k = bpy.data.collections.new(f"{v}-{pose}")
            arms = None
            for f, m in ((f"body-{pose}.glb", people), (f"{pose}.glb", tee_m)):
                before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=os.path.join(fit, v, f))
                new = set(bpy.data.objects) - before
                for o in new:
                    if o.type != "MESH": continue
                    o.data = o.data.copy(); o.data.transform(o.matrix_world); o.parent = None; o.matrix_world = Matrix()
                    for c in list(o.users_collection): c.objects.unlink(o)
                    k.objects.link(o); o.data.materials.clear(); o.data.materials.append(m)
                    if pose == "stand" and m is tee_m: relax_arms(o.data, arms)
                    b = bmesh.new(); b.from_mesh(o.data)
                    if m is tee_m:   # the sim's few stretched triangles at the armpits: drop them
                        bmesh.ops.delete(b, geom=[e for e in b.edges if e.calc_length() > 0.03], context="EDGES")
                        b.to_mesh(o.data); b.free(); o.data.shade_smooth(); continue
                    b.free()
                    vs = [vv.co for vv in o.data.vertices]
                    top = max(c.z for c in vs if abs(c.x) < 0.12)
                    if pose == "stand": arms = arm_axes(vs, top); relax_arms(o.data, arms)
                    front = min(c.y for c in vs if c.z > top - 0.25 and abs(c.x) < 0.1)
                    s = top / 1.71
                    a = o.data.color_attributes.new("mask", "FLOAT_COLOR", "POINT")
                    hair = []
                    for i, c in enumerate(vs):
                        hairy = abs(c.x) < 0.125 and (c.z > top - 0.075 or (c.z > top - 0.17 and c.y > front + 0.075) or (c.z > top - 0.21 and c.y > front + 0.12))
                        legs = 0.085 < c.z < 0.57 * top and abs(c.x) < 0.22 * s
                        a.data[i].color = (float(hairy), float(legs), float(c.z <= 0.085), 1)
                        hair.append(hairy)
                    o.data.shade_smooth()
                    # hair with its own volume over the skull: the hair part of the head pushed out along its
                    # normals, fuller on top, so heads have a hair line and a silhouette, not a bald dome
                    idx = {}; verts = []; faces = []
                    for f_ in o.data.polygons:
                        if all(hair[i] for i in f_.vertices):
                            for i in f_.vertices:
                                if i not in idx:
                                    v_ = o.data.vertices[i]; up_ = max(0.0, min(1.0, (v_.co.z - (top - 0.21)) / 0.21))
                                    idx[i] = len(verts); verts.append(v_.co + v_.normal * (0.008 + 0.022 * up_))
                            faces.append([idx[i] for i in f_.vertices])
                    hm = bpy.data.meshes.new("hair"); hm.from_pydata(verts, [], faces); hm.shade_smooth(); hm.materials.append(hair_m)
                    k.objects.link(bpy.data.objects.new("hair", hm))
                for o in new:
                    if o.type != "MESH": bpy.data.objects.remove(o)
            kinds[pose].append(k)
    return kinds


def instance(k, x, y, rot, s=1.0, z=0.0):
    e = bpy.data.objects.new("p", None); e.instance_type = "COLLECTION"; e.instance_collection = k
    e.location = (x, y, z); e.rotation_euler = (0, 0, rot); e.scale = (s, s, s); col.objects.link(e); return e


def facing(x, y, tx, ty):
    """the turn that points a body's face (its -Y) from (x, y) to (tx, ty)"""
    return math.atan2(tx - x, -(ty - y))


CANOPY = os.environ.get("CANOPY") or os.path.expanduser("~/.cache/stage/canopy.npz")


def canopy_cloth():
    """the canopy's settled cloth (canopy.py): made on the farm before the strips (stage.yml), or here if missing"""
    if not os.path.exists(CANOPY):
        import subprocess
        os.makedirs(os.path.dirname(CANOPY), exist_ok=True)
        subprocess.run([bpy.app.binary_path, "-b", "--factory-startup", "-P",
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), "canopy.py"), "--", CANOPY], check=True)
    import numpy as np
    return dict(np.load(CANOPY))


def fabric_mat():
    """the canopy: a sheer white synthetic, a little glossy, crinkled; light passes through it and glows in it"""
    m = bpy.data.materials.new("canopy"); m.use_nodes = True; nt = m.node_tree; N_ = nt.nodes
    p = N_["Principled BSDF"]
    p.inputs["Base Color"].default_value = (0.84, 0.85, 0.86, 1); p.inputs["Roughness"].default_value = 0.34
    p.inputs["Sheen Weight"].default_value = 0.35; p.inputs["Sheen Roughness"].default_value = 0.4
    tl = N_.new("ShaderNodeBsdfTranslucent"); tl.inputs[0].default_value = (0.82, 0.84, 0.86, 1)
    tp = N_.new("ShaderNodeBsdfTransparent")
    m1 = N_.new("ShaderNodeMixShader"); m1.inputs[0].default_value = 0.55
    nt.links.new(p.outputs[0], m1.inputs[1]); nt.links.new(tl.outputs[0], m1.inputs[2])
    m2 = N_.new("ShaderNodeMixShader"); m2.inputs[0].default_value = 0.6      # how much light the weave stops
    nt.links.new(tp.outputs[0], m2.inputs[1]); nt.links.new(m1.outputs[0], m2.inputs[2])
    nt.links.new(m2.outputs[0], N_["Material Output"].inputs[0])
    # crinkles: the creases a thin synthetic keeps from being packed, a few cm across
    tc = N_.new("ShaderNodeTexCoord"); nz = N_.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 5.0; nz.inputs["Detail"].default_value = 6.0; nz.inputs["Roughness"].default_value = 0.62
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    bp = N_.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.07; bp.inputs["Distance"].default_value = 0.01
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs[0], p.inputs["Normal"]); nt.links.new(bp.outputs[0], tl.inputs["Normal"])
    return m


def truss(p0, p1, m, w=0.4):
    """a square box truss from p0 to p1: four chords, laced on every face"""
    p0, p1 = Vector(p0), Vector(p1); d = (p1 - p0); L = d.length; d.normalize()
    u = d.cross(Vector((0, 0, 1))); u = (u if u.length > 1e-3 else d.cross(Vector((1, 0, 0)))).normalized(); v = d.cross(u)
    cs = [(u * sx + v * sy) * (w / 2) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for c in cs: cyl(p0 + c, p1 + c, 0.024, m, 6)
    n = max(1, int(L / w))
    for i in range(n):
        a_, b_ = p0 + d * (L * i / n), p0 + d * (L * (i + 1) / n)
        for f in range(4):
            c0, c1 = cs[f], cs[(f + 1) % 4]
            cyl(a_ + (c0 if i % 2 else c1), b_ + (c1 if i % 2 else c0), 0.011, m, 4)


def build_show():
    """The night in the round at Alexandra Palace (after Fred again.. and Thomas Bangalter, USB002, 27 Feb 2026),
    built from photographs of that night as reference: the Great Hall dark round it, and in it a canopy of sheer
    white cloth in rings of swags, high over the decks, falling to a trough round the stage, rising over the crowd,
    lit from below and through it by heads on the trusses above, in haze. A long low stage in the middle with the
    table across it (decks, mixer, two desk lamps), its own crowd on the stage behind and round the decks, a
    search light on a tripod behind them, towers at the ends, hangs of speakers; the crowd all round.
    The person stands in the crowd, the decks 6.5 m ahead; the hard front lights they are lit by hang on a bar
    over the front of the stage."""
    global ZC
    M_STAGE = mat("stage", (0.012, 0.012, 0.012), 0.95)          # black stage cloth
    M_CASE = mat("case", (0.022, 0.022, 0.023), 0.45)
    M_ALU = mat("alu", (0.6, 0.6, 0.62), 0.35, metal=1.0)
    M_TRUSS = mat("truss", (0.5, 0.5, 0.52), 0.35, metal=1.0)
    M_BLACK = mat("black truss", (0.02, 0.02, 0.02), 0.4, metal=0.5)
    M_WOOD = mat("desk", (0.05, 0.035, 0.025), 0.5)
    M_CABLE = mat("cable", (0.02, 0.02, 0.02), 0.5)
    M_BULB = emission("bulb", (1.0, 0.62, 0.3), 60)
    M_PHONE = emission("phone", (0.82, 0.88, 1.0), 2.2)
    M_LCD = emission("lcd", (0.55, 0.7, 1.0), 0.9)
    M_EXIT = emission("exit", (0.1, 1.0, 0.35), 5.0)
    CX, CY = 0.0, -6.5                                                 # the deck centre: the middle of everything

    # ---------- the Great Hall: 56 m across, 117 m long, its long walls 13.8 m to the springing of the iron and
    # glass barrel vault, 30.5 m at the crown; painted walls, a wooden floor, ribs across the vault ----------
    HX, Y0, Y1, SPR, CROWN = 28.0, CY - 58.5, CY + 58.5, 13.8, 30.5
    RV = (HX * HX + (CROWN - SPR) ** 2) / (2 * (CROWN - SPR)); ZV = CROWN - RV
    vault = lambda x: ZV + math.sqrt(max(RV * RV - x * x, 0.0))
    ZC = CROWN
    M_WALL = mat("hall walls", (0.3, 0.24, 0.21), 0.85)
    M_FLOOR = mat("hall floor", (0.035, 0.028, 0.022), 0.62)
    M_ROOF = mat("hall roof", (0.05, 0.05, 0.055), 0.6, metal=0.2)
    surf(lambda u, v: Vector((-HX + 2 * HX * u, Y0 + (Y1 - Y0) * v, 0)), 1, 1, M_FLOOR, False)
    for x in (-HX, HX):
        surf(lambda u, v, x=x: Vector((x, Y0 + u * (Y1 - Y0), v * SPR)), 1, 1, M_WALL, False)
    for y in (Y0, Y1):
        surf(lambda u, v, y=y: Vector((-HX + 2 * HX * u, y, v * vault(-HX + 2 * HX * u))), 48, 1, M_WALL, False)
    surf(lambda u, v: Vector((-HX + 2 * HX * u, Y0 + v * (Y1 - Y0), vault(-HX + 2 * HX * u))), 64, 1, M_ROOF)
    for y in [Y0 + 9 * i for i in range(1, int((Y1 - Y0) / 9))]:                    # the iron ribs
        pts = [Vector((-HX + 2 * HX * i / 32, y, vault(-HX + 2 * HX * i / 32) - 0.4)) for i in range(33)]
        for a_, b_ in zip(pts, pts[1:]): cyl(a_, b_, 0.18, M_BLACK, 8)
    for x, side in ((-HX + 0.06, 1), (HX - 0.06, -1)):                             # exit signs, green in the dark
        for y in range(int(Y0) + 12, int(Y1), 16):
            box(x, y, 2.7, 0.06, 0.45, 0.18, M_EXIT)

    # ---------- the stage: long and low across the middle, black, a barrier round it ----------
    SX, SY, SZ = 7.0, 2.6, 1.1
    box(CX, CY, SZ / 2, 2 * SX, 2 * SY, SZ, M_STAGE)
    for k in range(-9, 10):
        for side in (-1, 1):
            box(CX + k * 0.98, CY + side * (SY + 1.3), 0.55, 0.96, 0.08, 1.1, M_ALU)
    for k in range(-3, 4):
        for side in (-1, 1):
            box(CX + side * (SX + 1.3), CY + k * 0.98, 0.55, 0.08, 0.96, 1.1, M_ALU)
    # the table across it, facing the person: decks, mixer, two black desk lamps with warm bulbs
    TY = CY + 0.35
    box(CX, TY, SZ + 0.45, 3.4, 0.8, 0.9, M_WOOD)
    for i, x in enumerate((-1.25, -0.6, 0.0, 0.6, 1.25)):
        box(CX + x, TY, SZ + 0.93, 0.5 if i != 2 else 0.4, 0.38, 0.06, M_CASE)
        box(CX + x, TY + 0.05, SZ + 0.965, 0.34, 0.22, 0.01, emission(f"pad{i}", (1.0, 0.5, 0.2) if i % 2 else (0.85, 0.9, 1.0), 1.4))
    for x in (-1.6, 1.6):
        b = Vector((CX + x, TY - 0.2, SZ + 0.9))
        cyl(b, b + Vector((0, 0, 0.03)), 0.08, M_CASE, 16)
        el = b + Vector((0, 0.18, 0.42)); hd = el + Vector((0, 0.22, 0.02))
        cyl(b, el, 0.01, M_CASE, 6); cyl(el, hd, 0.01, M_CASE, 6)
        cyl(hd + Vector((0, -0.04, 0.06)), hd + Vector((0, 0.06, -0.1)), 0.05, M_CASE, 20, r2=0.13)
        sphere(hd + Vector((0, 0.04, -0.07)), 0.035, M_BULB)
        light("POINT", hd + Vector((0, 0.06, -0.12)), None, 35, (1.0, 0.58, 0.28), size=0.04)
    for x in (-2.1, 2.1):                                             # monitors on poles behind the table
        cyl((CX + x, TY - 0.7, SZ), (CX + x, TY - 0.7, SZ + 1.7), 0.03, M_CASE, 8)
        box(CX + x, TY - 0.7, SZ + 1.95, 0.45, 0.4, 0.55, M_CASE)
    box(CX + 0.9, TY + 0.1, SZ + 1.02, 0.32, 0.01, 0.2, M_LCD)       # a laptop
    # the search light on its tripod behind the decks, looking out over the crowd
    sl = Vector((CX, CY - 1.9, SZ + 3.1))
    for k in range(3):
        a_ = 2 * math.pi * k / 3; cyl((sl.x + 0.8 * math.cos(a_), sl.y + 0.8 * math.sin(a_), SZ), sl - Vector((0, 0, 0.5)), 0.025, M_CASE, 6)
    cyl(sl - Vector((0, 0, 0.5)), sl, 0.05, M_CASE, 8)
    cyl(sl + Vector((0, -0.35, 0.05)), sl + Vector((0, 0.25, 0.08)), 0.42, M_CASE, 32)
    sl_aim = Vector((CX + 0.5, 14.0, 6.5))
    cyl(sl + Vector((0, 0.25, 0.08)), sl + Vector((0, 0.27, 0.08)), 0.38, emission("search lens", (1.0, 0.95, 0.88), 40), 32)
    light("SPOT", sl + Vector((0, 0.3, 0.08)), sl_aim, 9000, (1.0, 0.95, 0.88), size=0.3, spot=9, blend=0.4)
    # towers at the ends of the stage, a block of lights on each
    for side in (-1, 1):
        tx = CX + side * (SX - 0.4)
        for dy in (-1.4, 1.4):
            truss((tx, CY + dy, SZ), (tx, CY + dy, SZ + 4.6), M_BLACK, 0.3)
        truss((tx, CY - 1.4, SZ + 4.6), (tx, CY + 1.4, SZ + 4.6), M_BLACK, 0.3)
        for k, dy in enumerate((-0.9, -0.3, 0.3, 0.9)):
            p = Vector((tx, CY + dy, SZ + 4.2))
            cyl(p, p + Vector((0, 0, 0.3)), 0.12, M_CASE, 12)
            out_ = Vector((CX + side * 13, CY + (dy * 9), 4.0))       # up into the canopy's trough
            light("SPOT", p, out_, 4000, (0.82, 0.88, 1.0) if k % 2 else (0.35, 0.55, 1.0), size=0.1, spot=34, blend=0.7)
        light("SPOT", (tx, CY, SZ + 4.0), (CX, CY, SZ + 1.4), 900, (1.0, 0.58, 0.28), size=0.1, spot=40, blend=0.7)
    # hangs of speakers either side of the stage
    for side in (-1, 1):
        for dy in (-2.2, 2.2):
            x, y = CX + side * (SX + 2.6), CY + dy
            for k in range(11):
                z = 8.6 - k * 0.36; tilt = 0.04 * k
                box(x + side * tilt * 0.3, y, z, 0.65, 1.2, 0.34, M_CASE)
            cyl((x, y, 8.8), (x, y, 16.0), 0.012, M_CABLE, 4)

    # ---------- the canopy: rings of sheer swags round the decks, every pick-up hung on a line to the trusses ----------
    cn = canopy_cloth(); Nn = int(cn["N"]); rings = [tuple(r) for r in cn["RINGS"]]
    fab = fabric_mat()
    for k in range(len(rings) - 1):
        meshes = []
        for j in range(4):
            if f"b{k}v{j}_v" not in cn: break
            vv, ff = cn[f"b{k}v{j}_v"], cn[f"b{k}v{j}_f"]
            me = bpy.data.meshes.new(f"swag{k}{j}"); me.from_pydata(vv.tolist(), [], ff.tolist())
            me.shade_smooth(); me.materials.append(fab); meshes.append(me)
        for i in range(Nn if meshes else 0):
            o = bpy.data.objects.new("swag", meshes[(i + k) % len(meshes)]); col.objects.link(o)
            o.location = (CX, CY, 0); o.rotation_euler = (0, 0, 2 * math.pi * i / Nn)
    TZ = 16.0                                                           # the trusses over the canopy
    for r, z in rings:
        for i in range(Nn):
            a_ = math.pi / 2 + 2 * math.pi * (i + 0.5) / Nn
            cyl((CX + r * math.cos(a_), CY + r * math.sin(a_), z), (CX + r * math.cos(a_), CY + r * math.sin(a_), TZ), 0.006, M_CABLE, 4)
    for i in range(4):                                                  # four trusses crossing over the decks
        a_ = math.pi / 4 + i * math.pi / 2
        truss((CX + 1.0 * math.cos(a_), CY + 1.0 * math.sin(a_), TZ), (CX + 34 * math.cos(a_), CY + 34 * math.sin(a_), TZ), M_TRUSS)
        for t in range(3, 33, 3):                                       # heads under them, beams down through the cloth
            p = Vector((CX + t * math.cos(a_), CY + t * math.sin(a_), TZ - 0.6))
            cyl(p + Vector((0, 0, 0.35)), p, 0.14, M_CASE, 12)
            aa = a_ + rnd.uniform(-0.6, 0.6); far = t + rnd.uniform(-5, 7)
            light("SPOT", p, (CX + far * math.cos(aa), CY + far * math.sin(aa), 0), 4500, (0.88, 0.92, 1.0) if t % 2 else (0.5, 0.65, 1.0), size=0.04, spot=3.5, blend=0.25)
    for i in range(24):                                                 # soft washes down onto the cloth: it glows
        a_ = 2 * math.pi * (i + 0.25) / 24; r = 6 + 20 * ((i * 7) % 24) / 24
        p = Vector((CX + r * math.cos(a_), CY + r * math.sin(a_), TZ - 0.5))
        light("SPOT", p, (p.x, p.y, 0), 3000, (0.86, 0.9, 1.0), size=0.3, spot=70, blend=0.9)
    for side in (-1, 1):                                                # the stage's light back onto the crowd round it
        for y in (CY + 9, CY - 9):
            light("SPOT", (CX + side * (SX - 0.4), CY, SZ + 4.4), (CX + side * 3, y, 1.6), 1500, (1.0, 0.7, 0.45), size=0.1, spot=34, blend=0.7)
    for i in range(10):                                                 # blue washes up onto the cloth from the floor
        a_ = 2 * math.pi * (i + 0.5) / 10; r = 17.5
        p = Vector((CX + r * math.cos(a_), CY + r * math.sin(a_), 0.4))
        box(p.x, p.y, 0.2, 0.4, 0.4, 0.4, M_CASE)
        light("SPOT", p, (CX + (r - 3) * math.cos(a_), CY + (r - 3) * math.sin(a_), 5.5), 1800, (0.25, 0.42, 1.0), size=0.15, spot=60, blend=0.8)

    # ---------- the bar over the front of the stage the person's front lights hang on ----------
    yb = -3.1
    cyl((CX - 3.2, yb, 5.85), (CX + 3.2, yb, 5.85), 0.05, M_BLACK, 8)
    for x in (-3.0, 3.0): cyl((CX + x, yb, 5.85), (CX + x, yb, TZ), 0.006, M_CABLE, 4)

    # ---------- front of house: a riser in the crowd behind the person, its desk, the light over it ----------
    FX, FY = 0.0, 5.8
    box(FX, FY, 0.3, 4.4, 2.6, 0.6, M_CASE)
    box(FX, FY - 0.4, 0.6 + 0.45, 3.6, 0.9, 0.9, M_CASE)
    for i, x in enumerate((-1.3, -0.45, 0.45, 1.3)):
        box(FX + x, FY - 0.5, 1.53, 0.7, 0.03, 0.42, M_LCD if i % 2 else emission(f"lcd{i}", (1.0, 0.78, 0.55), 0.7))
    for x in (-2.3, 2.3):
        for y in (3.6, 7.0):
            cyl((FX + x, y, 0), (FX + x, y, 3.55), 0.05, M_BLACK, 8)
    for y in (3.6, 7.0):
        cyl((FX - 2.3, y, 3.5), (FX + 2.3, y, 3.5), 0.06, M_BLACK, 8)
    for x in (-2.3, 2.3):
        cyl((FX + x, 3.6, 3.5), (FX + x, 7.0, 3.5), 0.06, M_BLACK, 8)
    # a second search light on the riser, looking back at the stage over the heads (it faces the front view)
    s2 = Vector((FX + 1.6, FY + 0.6, 3.9))
    cyl(s2 + Vector((0, 0.3, 0)), s2 + Vector((0, -0.25, -0.02)), 0.36, M_CASE, 32)
    cyl(s2 + Vector((0, -0.25, -0.02)), s2 + Vector((0, -0.27, -0.02)), 0.32, emission("search lens 2", (1.0, 0.94, 0.85), 30), 32)
    light("SPOT", s2 + Vector((0, -0.3, -0.02)), (CX - 1, CY - 1.2, SZ + 2.4), 4500, (1.0, 0.94, 0.85), size=0.25, spot=8, blend=0.4)
    for x in (-6.5, -2.2, 2.2, 6.5):                                  # back truss: light on the crowd from behind
        cyl((x, 12.0, 4.9), (x, 11.7, 4.6), 0.14, M_CASE, 16)
        light("SPOT", (x, 11.7, 4.55), (x * 0.5, rnd.uniform(-1, 6), 1.3), 1400, (1.0, 0.84, 0.66), size=0.08, spot=16, blend=0.5)
    truss((-8, 12.0, 5.0), (8, 12.0, 5.0), M_BLACK, 0.3)
    for x in (-8, 8): cyl((x, 12.0, 5.0), (x, 12.0, TZ), 0.006, M_CABLE, 4)

    # the hard front lights the person in the viewer is lit by (scene.ts "show"), as real fixtures where they hang
    for name, pos3, size, power, tint in SHOW_LIGHTS:
        p = three(pos3)
        cyl(p + Vector((0, 0, 0.35)), p, 0.14, M_CASE, 16)
        light("SPOT", p, (0, 0, 1.0), power * 4, tint, size=max(size) / 2, spot=10, blend=0.6)
        if name == "spot":   # its stand
            for dx in (-0.2, 0.2):
                for dy in (-0.2, 0.2): cyl((p.x + dx, p.y + dy, 0), (p.x + dx, p.y + dy, p.z + 0.2), 0.025, M_BLACK, 6)

    # ---------- the people: the two at the decks, the crowd on the stage round them, the crowd all round ----------
    if os.environ.get("NOCROWD"):   # a quick check of the build: everyone an empty stand-in
        e_ = bpy.data.collections.new("nobody"); kinds = {"stand": [e_] * 10, "up": [e_] * 10}
    else:
        kinds = crowd_kinds()
    pick = lambda up: (lambda kk: kk[rnd.randrange(len(kk))])(kinds["up" if up else "stand"])
    instance(kinds["stand"][3], CX - 0.6, TY - 0.55, facing(0, 0, 0, 1), 1.0, SZ)
    instance(kinds["stand"][8], CX + 0.6, TY - 0.55, facing(0, 0, 0.2, 1), 1.0, SZ)
    n = 0
    for i in range(int(2 * SX / 0.62)):                               # on the stage: behind the decks and at the ends
        for j in range(int(2 * SY / 0.62)):
            x = CX - SX + 0.4 + (i + rnd.uniform(0.15, 0.85)) * 0.62
            y = CY - SY + 0.3 + (j + rnd.uniform(0.15, 0.85)) * 0.62
            if y > TY - 0.9 and abs(x - CX) < 2.6: continue           # the table and the two at it
            if y > CY + 0.9 and abs(x - CX) < 4.5: continue           # the front stays open towards the person
            if abs(abs(x - CX) - (SX - 0.4)) < 0.5: continue          # the towers
            if math.hypot(x - sl.x, y - sl.y) < 1.0 or rnd.random() < 0.2: continue
            instance(pick(rnd.random() < 0.45), x, y, facing(x, y, CX, TY) + rnd.gauss(0, 0.4), rnd.uniform(0.97, 1.04), SZ); n += 1
    deck = lambda x, y: abs(x - CX) < SX + 1.9 and abs(y - CY) < SY + 1.9
    foh = lambda x, y: abs(x - FX) < 2.8 and 3.2 < y < 7.4
    sp_ = three(next(l[1] for l in SHOW_LIGHTS if l[0] == "spot"))
    for k, (x, y) in enumerate(((-0.9, 6.3), (0.9, 6.4))):            # at the desk, facing the decks
        instance(kinds["stand"][k * 5], FX + x, y, 0.0, 1.0)
    phones = 0; step = 0.74; RC = 24.0
    for i in range(int(2 * RC / step)):
        for j in range(int(2 * RC / step)):
            x = CX - RC + (i + rnd.uniform(0.15, 0.85)) * step
            y = CY - RC + (j + rnd.uniform(0.15, 0.85)) * step
            if math.hypot((x - CX) / 1.15, y - CY) > RC: continue
            r0 = math.hypot(x, y)
            if r0 < 1.9 or (r0 < 2.7 and rnd.random() < 0.5): continue
            if deck(x, y) or foh(x, y) or math.hypot(x - sp_.x, y - sp_.y) < 0.9: continue
            if any(math.hypot(x - (CX + s_ * (SX + 2.6)), y - (CY + d_)) < 0.8 for s_ in (-1, 1) for d_ in (-2.2, 2.2)): continue
            up = rnd.random() < (0.45 if math.hypot(x - CX, y - CY) < 12 else 0.25)
            rot = facing(x, y, CX, CY) + rnd.gauss(0, 0.3) if rnd.random() < 0.88 else rnd.uniform(-math.pi, math.pi)
            instance(pick(up), x, y, rot, rnd.uniform(0.97, 1.04)); n += 1
            if not up and phones < 14 and rnd.random() < 0.006:
                phones += 1
                f = Vector((math.sin(rot), -math.cos(rot), 0))
                box(x + f.x * 0.32, y + f.y * 0.32, 1.55, 0.07, 0.008, 0.14, M_PHONE, rot=rot)
    print("crowd", n)

    hz = bpy.data.materials.new("haze"); hz.use_nodes = True; nt = hz.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
    pv_ = nt.nodes.new("ShaderNodeVolumePrincipled"); pv_.inputs["Density"].default_value = float(os.environ.get("HAZE", "0.028"))
    pv_.inputs["Anisotropy"].default_value = 0.55
    nt.links.new(pv_.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    box(CX, CY, 8.0, 2 * HX - 0.2, 64.0, 15.9, hz)


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
    ("stage", (1.4, 5.85, 3.0), (0.4, 0.4), 760, (1, 0.8, 0.6)),
    ("beam", (-1.6, 5.85, 3.2), (0.2, 0.2), 360, (0.86, 0.91, 1)),
    ("spot", (-6.0, 4.6, 2.0), (0.3, 0.3), 390, (1, 0.72, 0.45)),
    ("foh", (-1.4, 3.5, -3.6), (0.8, 0.8), 480, (1, 0.86, 0.7)),
]
# daylight: the sun's direction (towards it) in three is (-0.696, 0.264, 0.668): front-left, 15 deg up
SUN_DIR = three((-0.696, 0.264 + FLOOR, 0.668)).normalized()
SUN_E = float(os.environ.get("SUNE", "6.5"))   # W/m2 on a surface facing it (Blender sun strength)
SUN_TINT = (1.0, 0.8, 0.6)
SKY_K = float(os.environ.get("SKYK", "6.0"))   # the sky, exposed for a room lit by it
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
  if (d2[2] > 1e-4) t0 = min(t0, ({ZC} - o2[2] - 0.06) / d2[2]);   // under anything flush with the ceiling
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
