# SIZE=M blender -b -P build.py -- <body.blend> <out.blend>
# Sews the two pattern panels around a real (hidden) body with cloth simulation, then moves the body through
# three poses and keeps the cloth from each: standing (tee_stand), arms up at the show (tee_up), sitting (tee_sit).
import bpy, bmesh, math, sys, os
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
sys.path.insert(0, os.path.dirname(__file__))
from pattern import outline, SEWN, PANEL_W, PANEL_H, L as PL, NECK_W, FRONT_DROP, BACK_DROP, RIB, key_points, ay, SIZE_NAME
ARGS = sys.argv[sys.argv.index("--") + 1:]
BODY, OUT = (ARGS[0], ARGS[1]) if len(ARGS) > 1 else (os.path.join(os.path.dirname(__file__), "body.blend"), ARGS[0])
print("size", SIZE_NAME, "body", BODY)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
TOP = 1.47  # world height (m) of the high shoulder point

# ---------- real body (MakeHuman via MPFB, built by body.py), A-pose at the start ----------
with bpy.data.libraries.load(BODY) as (src, dst):
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
# ---------- FORM=1: a ghost form for the shop view ----------
# The empty tee should look like a tee on a dress form, not like a body is inside it: the torso is swapped for
# smooth superellipse sections (same width and depth as the body at each height, smoothed over 12 cm so no
# chest shape survives). Shoulders, neck and arms stay the body's, so the shoulders and sleeves still sit right.
FORM = bool(os.environ.get("FORM"))
def torso_loop(z, W, me):
    cut = {}
    for e in me.edges:
        p, q = W[e.vertices[0]], W[e.vertices[1]]
        if (p.z - z) * (q.z - z) < 0:
            t = (z - p.z) / (q.z - p.z); c = p.lerp(q, t); cut[e.index] = (c.x, c.y)
    parent = {k: k for k in cut}
    def find(k):
        while parent[k] != k: parent[k] = parent[parent[k]]; k = parent[k]
        return k
    for poly in me.polygons:
        ks = [me.loops[li].edge_index for li in poly.loop_indices if me.loops[li].edge_index in cut]
        for k in ks[1:]: parent[find(k)] = find(ks[0])
    loops = {}
    for k, pt in cut.items(): loops.setdefault(find(k), []).append(pt)
    tors = [l for l in loops.values() if min(p[0] for p in l) < 0 < max(p[0] for p in l)]
    return max(tors, key=len) if tors else None
if FORM:
    for m in body.modifiers: m.show_viewport = False          # base-mesh order, so faces can be picked by index
    dg = bpy.context.evaluated_depsgraph_get(); bm_ = body.evaluated_get(dg).to_mesh()
    W = [body.matrix_world @ v.co for v in bm_.vertices]
    H_ = max(w.z for w in W) - min(w.z for w in W); z0 = min(w.z for w in W)
    secs, z = [], z0 + 0.40 * H_
    while z < z0 + 0.86 * H_:
        l = torso_loop(z, W, bm_)
        if not l: break
        xs = [p[0] for p in l]; ys = [p[1] for p in l]
        a = (max(xs) - min(xs)) / 2
        if secs and a > secs[-1][2] * 1.25: break                # the arms join the loop: the armpit
        secs.append([z, (max(xs) + min(xs)) / 2, a, (max(ys) + min(ys)) / 2, (max(ys) - min(ys)) / 2])
        z += 0.01
    body.evaluated_get(dg).to_mesh_clear()
    def smooth(k, r=6):
        vals = [s_[k] for s_ in secs]; out = []
        for i in range(len(vals)):
            ws = [(math.exp(-((j - i) / (r / 2)) ** 2), vals[j]) for j in range(max(0, i - r), min(len(vals), i + r + 1))]
            out.append(sum(w * v for w, v in ws) / sum(w for w, _ in ws))
        for i, v in enumerate(out): secs[i][k] = v
    for k in (1, 2, 3, 4): smooth(k)
    # heavy cotton doesn't follow a body in under the chest or in at the waist: it falls straight from the
    # fullest point above. So the form is the hull from the top down: no section's front, back or sides sit
    # inside any section above it (the cloth bridges every hollow, as it does on a real ghost mannequin)
    fr, bk, lt, rt = 1e9, -1e9, 1e9, -1e9
    for s_ in reversed(secs):
        _, cx, a, cy, b = s_
        fr, bk, lt, rt = min(fr, cy - b), max(bk, cy + b), min(lt, cx - a), max(rt, cx + a)
        s_[1], s_[2], s_[3], s_[4] = (lt + rt) / 2, (rt - lt) / 2, (fr + bk) / 2, (bk - fr) / 2
    zt = secs[-1][0]
    print("form", round(secs[0][0], 3), "to", round(zt, 3), "sections", len(secs))
    # drop the body's torso between those heights (arms and everything above stay)
    bmb = bmesh.new(); bmb.from_mesh(body.data); bmb.verts.ensure_lookup_table()
    def in_torso(i):
        w = W[i]
        if not (secs[0][0] - 0.005 <= w.z <= zt): return False
        s_ = secs[min(len(secs) - 1, max(0, round((w.z - secs[0][0]) / 0.01)))]
        return abs(w.x - s_[1]) <= s_[2] + 0.006
    kill = [f for f in bmb.faces if all(in_torso(v.index) for v in f.verts)]
    bmesh.ops.delete(bmb, geom=kill, context="FACES"); bmb.to_mesh(body.data); bmb.free()
    for m in body.modifiers: m.show_viewport = True
    N, EXP = 64, 2.4
    fv, ff = [], []
    for zi, cx, a, cy, b in secs:
        for k in range(N):
            t = 2 * math.pi * k / N; c, s_ = math.cos(t), math.sin(t)
            fv.append((cx + a * math.copysign(abs(c) ** (2 / EXP), c), cy + b * math.copysign(abs(s_) ** (2 / EXP), s_), zi))
    for r in range(len(secs) - 1):
        for k in range(N): ff.append((r * N + k, r * N + (k + 1) % N, (r + 1) * N + (k + 1) % N, (r + 1) * N + k))
    ff.append(tuple(range(N))[::-1])
    fm = bpy.data.meshes.new("form"); fm.from_pydata(fv, [], ff); fm.update()
    formob = bpy.data.objects.new("form", fm); sc.collection.objects.link(formob)
    formob.modifiers.new("col", "COLLISION"); formob.collision.thickness_outer = 0.003; formob.collision.cloth_friction = 6
    formob.hide_render = True
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
        uvs.append((u * 0.5 + (0 if front else 0.5), ay(y) / PANEL_H))   # neck-anchored: prints sit still across sizes
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
# ---------- poses after the drape settles ----------
STAND, UP, SIT = 200, 300, 430
ARM_UP = -50                                       # 50 deg above the horizon: hands up when the drop lands
for side in ("L", "R"):
    pose_arm(side, ARM_DOWN, STAND); pose_arm(side, ARM_UP, 265); pose_arm(side, ARM_UP, UP)
    pose_arm(side, ARM_DOWN, 345)
# sitting on a stool: thighs forward, shins down, the whole body lowered until the feet are back on the floor
def bone_dir(a, b): return (rig.data.bones[b].tail_local - rig.data.bones[a].head_local)
hip = rig.data.bones["upperleg01.L"].head_local; knee = rig.data.bones["lowerleg01.L"].head_local
ankle = rig.data.bones["foot.L"].head_local
shin = (ankle - knee).length
drop = hip.z - (ankle.z + shin)                    # thigh level, shin upright, foot where it stood
def key_leg(side, frame, sit):
    up1, lo1 = rig.pose.bones["upperleg01." + side], rig.pose.bones["lowerleg01." + side]
    for pb in (up1, lo1): pb.rotation_mode = "QUATERNION"
    if not sit:
        up1.rotation_quaternion = (1, 0, 0, 0); lo1.rotation_quaternion = (1, 0, 0, 0)
    else:
        s_ = 1 if side == "L" else -1
        R1 = up1.bone.matrix_local.to_quaternion()
        thigh0 = bone_dir("upperleg01." + side, "upperleg02." + side).normalized()
        qt = thigh0.rotation_difference(Vector((s_ * 0.12, -1, -0.04)).normalized())   # knees a little apart
        up1.rotation_quaternion = R1.inverted() @ qt @ R1
        R2 = lo1.bone.matrix_local.to_quaternion()
        shin0 = bone_dir("lowerleg01." + side, "lowerleg02." + side).normalized()
        qs = (qt @ shin0).rotation_difference(Vector((s_ * 0.05, 0.08, -1)).normalized())
        cur = qt @ R2
        lo1.rotation_quaternion = cur.inverted() @ qs @ cur
    up1.keyframe_insert("rotation_quaternion", frame=frame); lo1.keyframe_insert("rotation_quaternion", frame=frame)
for side in ("L", "R"): key_leg(side, 330, False); key_leg(side, 400, True)
rig.location = (0, 0, 0); rig.keyframe_insert("location", frame=330)
rig.location = (0, 0, -drop); rig.keyframe_insert("location", frame=400)
for fc in (rig.animation_data.action.fcurves if hasattr(rig.animation_data.action, "fcurves") else []):
    for kp in fc.keyframe_points: kp.interpolation = "BEZIER"
# the stool: under the seat, behind the knees
seat = hip.z - drop - 0.11
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0.04, seat - 0.225)); chair = bpy.context.active_object
chair.name = "chair"; chair.scale = (0.46, 0.42, 0.45); bpy.ops.object.transform_apply(scale=True)
chair.modifiers.new("col", "COLLISION"); chair.collision.thickness_outer = 0.004; chair.collision.cloth_friction = 8
chair.hide_render = True
print("sit drop", round(drop, 3), "seat", round(seat, 3))

STIFF = [i for i, (x, y, z) in enumerate(verts) if hem_w(x * 100, (z - TOP) * 100 + PL, y < 0)]
def snap(name, fr):
    """Keep this frame's cloth as its own object: sewing edges dropped, seam pairs that met are welded."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tee.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); ob["frame"] = fr
    vg2 = ob.vertex_groups.get("stiff") or ob.vertex_groups.new(name="stiff"); vg2.add(STIFF, 1.0, "REPLACE")
    bm = bmesh.new(); bm.from_mesh(me)
    loose = [e for e in bm.edges if not e.link_faces]
    pairs = [(e.verts[0], e.verts[1]) for e in loose]
    bmesh.ops.delete(bm, geom=loose, context="EDGES")
    tm = {}
    for a, b in pairs:
        if (a.co - b.co).length < 0.015 and a not in tm and b not in tm: a.co = (a.co + b.co) / 2; tm[b] = a
    bmesh.ops.weld_verts(bm, targetmap=tm)
    bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    print("snap", name, "frame", fr, "welded", len(tm), "of", len(pairs), flush=True)

END = SIT
if os.environ.get("SMOKE"): END = STAND = UP = SIT = 4      # pipeline check: a few frames, every pose snapped
if FORM: END = STAND; UP = SIT = -1                         # the shop tee only stands
cl.point_cache.frame_start = 1; cl.point_cache.frame_end = END; sc.frame_start = 1; sc.frame_end = END
import time
t0 = time.time()
for fr in range(1, END + 1):
    sc.frame_set(fr)
    if fr % 10 == 0: print("frame", fr, round(time.time() - t0), "s", flush=True)
    if fr == STAND: snap("tee_stand", fr)
    if fr == UP: snap("tee_up", fr)
    if fr == SIT: snap("tee_sit", fr)
sc["size"] = SIZE_NAME; sc["seat"] = seat
tee.hide_render = True; tee.hide_viewport = True
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("saved", OUT)
