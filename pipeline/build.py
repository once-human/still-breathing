# blender -b -P build.py -- out.blend
# Sews the two pattern panels around a real (hidden) body with cloth simulation, then saves the draped tee.
import bpy, bmesh, math, sys, os
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
sys.path.insert(0, os.path.dirname(__file__))
from pattern import outline, SEWN, PANEL_W, PANEL_H, L as PL, NECK_W, FRONT_DROP, BACK_DROP, RIB, key_points
OUT = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
TOP = 1.47  # world height (m) of the high shoulder point

# ---------- real body (MakeHuman via MPFB, built by body.py), A-pose at the start ----------
with bpy.data.libraries.load(os.path.join(os.path.dirname(__file__), "body.blend")) as (src, dst):
    dst.objects = [n for n in src.objects if n in ("body", "rig")]
for o in dst.objects: sc.collection.objects.link(o)
body, rig = bpy.data.objects["body"], bpy.data.objects["rig"]
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get(); bme = body.evaluated_get(dg).to_mesh()
BV = [body.matrix_world @ v.co for v in bme.vertices]; body.evaluated_get(dg).to_mesh_clear()
# high point shoulder: top of the trapezius where the neck rib sits (x = half neck width)
NECK_Z = (rig.matrix_world @ rig.data.bones["neck01"].head_local).z          # base of the neck
TOP = max(v.z for v in BV if 0.085 < abs(v.x) < 0.10 and abs(v.y) < 0.06 and v.z < NECK_Z + 0.03) + 0.004
torso = [v for v in BV if 0.75 < v.z < TOP - 0.05 and abs(v.x) < 0.17]
YF, YB = min(v.y for v in torso) - 0.035, max(v.y for v in torso) + 0.035
print("HPS z", round(TOP, 3), "panel y", round(YF, 3), round(YB, 3))
col = body.modifiers.new("col", "COLLISION"); body.collision.thickness_outer = 0.003; body.collision.cloth_friction = 6
body.hide_render = True
# arms: A-pose (about 49 deg below horizontal) while sewing, then lowered to a relaxed hollow-man pose
def arm_target(side, deg_below, fwd=0.06):
    s = 1 if side == "L" else -1
    return Vector((s * math.cos(math.radians(deg_below)), -fwd, -math.sin(math.radians(deg_below)))).normalized()
def pose_arm(side, deg_below, frame):
    pb = rig.pose.bones["upperarm01." + side]; bn = pb.bone
    full = (rig.data.bones["upperarm02." + side].tail_local - bn.head_local).normalized()
    qw = full.rotation_difference(arm_target(side, deg_below))
    R = bn.matrix_local.to_quaternion()
    pb.rotation_mode = "QUATERNION"; pb.rotation_quaternion = R.inverted() @ qw @ R
    pb.keyframe_insert("rotation_quaternion", frame=frame)
ARM_DOWN = 64
for side in ("L", "R"):
    pb = rig.pose.bones["upperarm01." + side]; pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = (1, 0, 0, 0); pb.keyframe_insert("rotation_quaternion", frame=1); pb.keyframe_insert("rotation_quaternion", frame=80)
    pose_arm(side, ARM_DOWN, 130)

# ---------- panels ----------
def inside(p, poly):
    x, y = p; c = False
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    return c
def dist_seg(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]; L = ax * ax + ay * ay or 1e-9
    t = max(0, min(1, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / L)); return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)
def panel(front):
    ol = outline(front); poly = [q[0] for q in ol]
    pts = list(poly); step = 1.0
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    j = 0; y = min(ys) + step * 0.6
    while y < max(ys):
        x = min(xs) + (step / 2 if j % 2 else 0)
        while x < max(xs):
            if inside((x, y), poly) and min(dist_seg((x, y), poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))) > step * 0.55:
                pts.append((x, y))
            x += step
        y += step * 0.866; j += 1
    n = len(poly)
    v, e, f, ov, oe, of = delaunay_2d_cdt([Vector(p) for p in pts], [(i, (i + 1) % n) for i in range(n)], [list(range(n))], 1, 1e-6, True)
    # map original outline index -> output vertex index
    o2n = {}
    for ni, olist in enumerate(ov):
        for o in olist: o2n[o] = ni
    seams = {}
    for oi, (p, tag, side, k) in enumerate(ol):
        if tag in SEWN: seams[(tag, side, k)] = o2n[oi]
    return [(q.x, q.y) for q in v], [tuple(t) for t in f], seams
verts, faces, uvs, sew = [], [], [], []
panels = {}
for front in (True, False):
    v2, f2, seams = panel(front); base = len(verts)
    ydepth = YF if front else YB
    for (x, y) in v2:
        verts.append((x / 100, ydepth, TOP + (y - PL) / 100))
        u = (x + PANEL_W / 2) / PANEL_W if front else (-x + PANEL_W / 2) / PANEL_W
        uvs.append((u * 0.5 + (0 if front else 0.5), y / PANEL_H))
    faces += [tuple(base + i for i in t) for t in f2]
    panels[front] = {k: base + i for k, i in seams.items()}
for k, fi in panels[True].items():
    if k in panels[False]: sew.append((fi, panels[False][k]))
print("verts", len(verts), "faces", len(faces), "sewing pairs", len(sew))
me = bpy.data.meshes.new("tee"); me.from_pydata(verts, sew, faces); me.update()
uvl = me.uv_layers.new(name="UV")
for poly in me.polygons:
    for li in poly.loop_indices: uvl.data[li].uv = uvs[me.loops[li].vertex_index]
# front faces must point outward (towards -y for the front panel, +y for the back)
bm = bmesh.new(); bm.from_mesh(me)
for fc in bm.faces:
    c = fc.calc_center_median(); fc.normal_update()
    if (c.y < 0 and fc.normal.y > 0) or (c.y > 0 and fc.normal.y < 0): fc.normal_flip()
bm.to_mesh(me); bm.free()
tee = bpy.data.objects.new("tee", me); sc.collection.objects.link(tee)
# double-needle hems and the rib collar are two layers of fabric: stiffer than the body
_, st, sb, _ = key_points()
def hem_w(x, y, front):
    w = 0.0
    if y < 2.6: w = 1.0
    ax = abs(x)  # sleeve hem: distance to the st-sb line
    dx, dy = sb[0] - st[0], sb[1] - st[1]; ln = math.hypot(dx, dy)
    d = abs((ax - st[0]) * dy - (y - st[1]) * dx) / ln
    if d < 2.6 and ax > 30: w = 1.0
    drop = FRONT_DROP if front else BACK_DROP
    ny = PL - drop * math.sqrt(max(0.0, 1 - (ax / NECK_W) ** 2)) if ax < NECK_W else PL
    if ax < NECK_W + RIB + 0.5 and y > ny - RIB - 0.6 and y > PL - drop - RIB - 1: w = 1.0
    return w
vg = tee.vertex_groups.new(name="stiff")
for i, (x, y, z) in enumerate(verts):
    w = hem_w(x * 100, (z - TOP) * 100 + PL, y < 0)
    if w: vg.add([i], w, "REPLACE")
for p in me.polygons: p.use_smooth = True

cl = tee.modifiers.new("cloth", "CLOTH"); s = cl.settings; c = cl.collision_settings
# 240 GSM single jersey: heavier and stiffer than a basic tee, low shear (knit)
s.quality = 8; s.mass = 0.3; s.air_damping = 2.0
s.tension_stiffness = 15; s.compression_stiffness = 25; s.shear_stiffness = 8; s.bending_stiffness = 2.0
s.vertex_group_structural_stiffness = "stiff"; s.tension_stiffness_max = 40; s.compression_stiffness_max = 40
s.vertex_group_bending = "stiff"; s.bending_stiffness_max = 6
s.tension_damping = 5; s.compression_damping = 5; s.shear_damping = 5; s.bending_damping = 0.5
s.use_sewing_springs = True; s.sewing_force_max = 20.0
c.collision_quality = 4; c.distance_min = 0.004; c.use_self_collision = True; c.self_distance_min = 0.003; c.self_friction = 5
# no gravity while the seams close, then let it hang
s.effector_weights.gravity = 0.0; s.effector_weights.keyframe_insert("gravity", frame=1)
s.effector_weights.keyframe_insert("gravity", frame=60)
s.effector_weights.gravity = 1.0; s.effector_weights.keyframe_insert("gravity", frame=75)
END = 200
cl.point_cache.frame_start = 1; cl.point_cache.frame_end = END; sc.frame_start = 1; sc.frame_end = END
import time
t0 = time.time()
for fr in range(1, END + 1):
    sc.frame_set(fr)
    if fr % 10 == 0: print("frame", fr, round(time.time() - t0), "s", flush=True)
bpy.context.view_layer.objects.active = tee; tee.select_set(True)
bpy.ops.object.modifier_apply(modifier="cloth")
# drop the sewing edges (loose edges) now the seams are closed, weld seam pairs that ended up touching
bm = bmesh.new(); bm.from_mesh(tee.data)
loose = [e for e in bm.edges if not e.link_faces]
pairs = [(e.verts[0], e.verts[1]) for e in loose]
bmesh.ops.delete(bm, geom=loose, context="EDGES")
targetmap = {}
for a, b in pairs:
    if (a.co - b.co).length < 0.015: a.co = (a.co + b.co) / 2; targetmap[b] = a
bmesh.ops.weld_verts(bm, targetmap=targetmap)
bm.to_mesh(tee.data); bm.free()
print("welded", len(targetmap), "of", len(pairs))
sc.frame_set(END)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("saved", OUT)
