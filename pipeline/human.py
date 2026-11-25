# blender -b --factory-startup -P human.py -- pipeline/bodies/m170.blend public/tee/fit/m170-M/stand.glb public/tee/human/m170-stand.glb
# The person who wears the shop tee: the same MakeHuman body (MPFB, CC0) the tee was sewn onto and simulated on,
# in the same standing pose, so the tee sits exactly as it was simulated. What makes it a person, not a form:
#   - standing easy, below the sleeves and above the collar (so the simulated tee is untouched): elbows a little
#     bent, the left more than the right; relaxed hands, fingers together and curling more toward the little
#     finger, the thumb along the index finger; the head turned and tipped a few degrees
#   - painted skin (per vertex, linear albedo): an even Indian brown with a slow mottle, warmer lips and ears,
#     lighter palms and nails, a close-cropped beard shadow, darker brows, a short buzz cut
#   - black jeans: MakeHuman's own tights helper, loosened into a straight leg and smoothed of muscle
#   - eyes from the eye helpers (sclera, iris, pupil)
# Skin under the tee and the jeans is cut away (it can never be seen, and can never poke through the cloth).
# Out: one GLB, materials named "skin", "jeans", "eyes" (the viewer and render.py pick their surfaces by them),
# COLOR_0 albedo, subdivided once.
# People.py's bodies (Blender Studio's sculpted base meshes with MakeHuman's rig: no helpers, no joint cubes) go
# the same way, with: the artist's eyes (eye.L / eye.R, painted sclera, iris, pupil); landmarks from the rig's
# bones and the eyes; trousers from trousers.py when TROUSERS=<trousers.blend> (TROUSERS_RGB="r,g,b" linear,
# dark raw indigo by default), the leg skin under them cut and the feet kept; the visible skin's UV islands
# (spread over the sculpt's 24 UDIM tiles) packed into one square, the face given twice the texels; no
# subdivision (the sculpt's first level is already fine enough).
import bpy, bmesh, sys, math, os
from mathutils import Vector, Matrix, Quaternion, noise
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

a = sys.argv[sys.argv.index("--") + 1:]
BODY, TEE, OUT = a[0], a[1], a[2]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

with bpy.data.libraries.load(BODY) as (src, dst):
    dst.objects = [n for n in src.objects if n in ("body", "rig", "eye.L", "eye.R")]
for o in dst.objects: sc.collection.objects.link(o)
body, rig = bpy.data.objects["body"], bpy.data.objects["rig"]
ART_EYES = [bpy.data.objects[n] for n in ("eye.L", "eye.R") if n in bpy.data.objects]
HBM = "helper-tights" not in body.vertex_groups      # people.py's bodies: the artist's sculpt, no helpers
upd = bpy.context.view_layer.update


# ---------- the stand pose, exactly as build.py sets it (arms 64 degrees below horizontal) ----------
def arm_target(side, deg_below, fwd=0.06):
    s = 1 if side == "L" else -1
    return Vector((s * math.cos(math.radians(deg_below)), -fwd, -math.sin(math.radians(deg_below)))).normalized()


def pose_arm(side, deg_below):
    pb = rig.pose.bones["upperarm01." + side]; bn = pb.bone
    full = (rig.data.bones["upperarm02." + side].tail_local - bn.head_local).normalized()
    qw = full.rotation_difference(arm_target(side, deg_below))
    R = bn.matrix_local.to_quaternion()
    pb.rotation_mode = "QUATERNION"; pb.rotation_quaternion = R.inverted() @ qw @ R


for side in ("L", "R"):
    pose_arm(side, 64)
upd()


# ---------- below the sleeves: a person standing easy ----------
def turn(pb, q):
    """turn a pose bone by the world rotation q about its head (the rig sits at the origin, unrotated)"""
    upd()
    M = pb.matrix.copy()
    R = q.to_matrix() @ M.to_3x3()
    pb.matrix = Matrix.LocRotScale(M.translation, R.to_quaternion(), M.to_scale())
    upd()


def aim(pb, want, end=None):
    """point a bone (or the chain from it to `end`) along a world direction"""
    upd()
    head = pb.head.copy(); tail = (rig.pose.bones[end].tail if end else pb.tail).copy()
    turn(pb, (tail - head).normalized().rotation_difference(want.normalized()))


def spin(pb, axis, deg):
    """turn a bone (and everything after it) about a world axis through its head"""
    turn(pb, Quaternion(axis.normalized(), math.radians(deg)))


def bdir(name):
    upd(); pb = rig.pose.bones[name]
    return (pb.tail - pb.head).normalized()


# Nobody hangs both arms the same: the left elbow is a little more bent, the right hand hangs nearer straight.
# A relaxed hand: the fingers close up side by side and curl more toward the little finger (index about 50 deg
# over its three joints, little finger about 90), the thumb lies along the side of the index finger.
EASE = {"L": dict(fore=(0.05, -0.3, -1), wrist=(-0.03, -0.16, -1), curl=1.12, thumb=0.85),
        "R": dict(fore=(0.04, -0.13, -1), wrist=(0.0, -0.08, -1), curl=0.9, thumb=0.8)}
CURL = {2: (16, 17, 8), 3: (20, 21, 10), 4: (24, 25, 12), 5: (28, 27, 14)}    # MCP, PIP, DIP, degrees
for side, s in (("L", 1), ("R", -1)):
    e = EASE[side]
    aim(rig.pose.bones["lowerarm01." + side], Vector((s * e["fore"][0], e["fore"][1], e["fore"][2])), "lowerarm02." + side)
    if HBM: continue       # the artist sculpted the hands relaxed: they stay as made (the fitted finger bones are rough)
    aim(rig.pose.bones["wrist." + side], Vector((s * e["wrist"][0], e["wrist"][1], e["wrist"][2])))
    upd()
    B = rig.pose.bones
    # the palm's normal from the knuckles and the wrist; the palm faces the thigh
    w0, i0, p0 = B["wrist." + side].head.copy(), B["finger2-1." + side].head.copy(), B["finger5-1." + side].head.copy()
    palm = (p0 - i0).cross(i0 - w0).normalized()
    if palm.dot(Vector((-s, 0, 0))) < 0: palm = -palm
    # fingers together: each turns most of the way to lie beside the middle finger
    mid = bdir(f"finger3-1.{side}")
    for f in (2, 4, 5):
        d = bdir(f"finger{f}-1.{side}")
        a_ = d - palm * d.dot(palm); m_ = mid - palm * mid.dot(palm)
        ang = math.degrees(a_.angle(m_, 0.0)) * (1 if a_.cross(m_).dot(palm) > 0 else -1)
        spin(B[f"finger{f}-1.{side}"], palm, ang * 0.65)
    # curl, about one axis per finger (the knuckle line), joint by joint from the knuckle out
    for f, angs in CURL.items():
        ax = bdir(f"finger{f}-1.{side}").cross(palm)
        for j, deg in enumerate(angs, 1):
            spin(B[f"finger{f}-{j}.{side}"], ax, deg * e["curl"] * (1 + 0.06 * math.sin(f * 2.3 + j + s)))
    # thumb: in toward the side of the index finger, the pad turned to it, both joints a little bent
    t0 = B["finger1-1." + side]
    upd(); cur = (B["finger1-3." + side].tail - t0.head).normalized()
    side_of_index = (B["finger2-1." + side].head + B["finger2-2." + side].head) / 2 + palm * 0.008
    want = (side_of_index - t0.head).normalized()
    turn(t0, Quaternion().slerp(cur.rotation_difference(want), e["thumb"]))
    tax = bdir(f"finger1-2.{side}").cross(palm)
    spin(B["finger1-2." + side], tax, 8 * e["curl"]); spin(B["finger1-3." + side], tax, 20 * e["curl"])
upd()
# the head: turned a few degrees to his right and tipped a touch, above the collar (neck02 up), so the tee is untouched
for name, yaw, roll in (("neck02", -1.5, 0.6), ("neck03", -1.5, 0.6), ("head", -2.5, 1.0)):
    spin(rig.pose.bones[name], Vector((0, 0, 1)), yaw); spin(rig.pose.bones[name], Vector((0, -1, 0)), roll)
upd()

# ---------- the posed mesh, helpers and all ----------
for m in body.modifiers:
    if m.type == "MASK": m.show_viewport = False
dg = bpy.context.evaluated_depsgraph_get()
ev = body.evaluated_get(dg)
me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
mw = body.matrix_world
P = [mw @ v.co for v in me.vertices]
VG = {g.name: g.index for g in body.vertex_groups}
W = [dict() for _ in me.vertices]
for v in body.data.vertices:          # same vertex order: the armature only moves vertices
    for g in v.groups: W[v.index][g.group] = g.weight
wt = lambda i, name: W[i].get(VG[name], 0.0) if name in VG else (1.0 if HBM and name == "body" else 0.0)
joint = lambda name: sum((P[i] for i in range(len(P)) if wt(i, name) > 0.5), Vector()) / max(1, sum(1 for i in range(len(P)) if wt(i, name) > 0.5))
B_ = rig.pose.bones
bone = lambda n: rig.matrix_world @ B_[n].head
if HBM:
    # no joint cubes: the eyes' own centres, the bones' heads, the lips' middle for the mouth
    EYEC = {}
    for o in ART_EYES:
        ev_ = o.evaluated_get(dg); m_ = ev_.to_mesh()
        EYEC[o.name] = sum((o.matrix_world @ v.co for v in m_.vertices), Vector()) / len(m_.vertices); ev_.to_mesh_clear()
    HIPZ = (bone("upperleg01.L").z + bone("upperleg01.R").z) / 2
    JOINT = {"joint-l-eye": EYEC["eye.L"], "joint-r-eye": EYEC["eye.R"], "joint-jaw": bone("jaw"), "joint-head": bone("head"),
             "joint-pelvis": Vector((0, (bone("upperleg01.L").y + bone("upperleg01.R").y) / 2, HIPZ)),
             "joint-mouth": joint("lips")}
    joint = lambda name: JOINT[name]

# ---------- the tee, to find the skin it covers ----------
bpy.ops.import_scene.gltf(filepath=TEE)
tee_obs = [o for o in bpy.context.selected_objects if o.type == "MESH"]
tb = bmesh.new()
for o in tee_obs:
    t = o.data.copy(); t.transform(o.matrix_world); tb.from_mesh(t)
tee_bvh = BVHTree.FromBMesh(tb)
edges = [e for e in tb.edges if len(e.link_faces) == 1]      # hem, sleeve ends, collar
kd_open = KDTree(max(1, len(edges)))
for i, e in enumerate(edges): kd_open.insert((e.verts[0].co + e.verts[1].co) / 2, i)
kd_open.balance()
for o in tee_obs: bpy.data.objects.remove(o)


def poking(c, n):
    """skin that has come out through the cloth: the tee is just beneath it"""
    hit = tee_bvh.ray_cast(c - n * 0.0005, -n, 0.015)
    return hit[0] is not None and hit[1].dot(n) > 0


def openings(b):
    es = [e for e in b.edges if len(e.link_faces) == 1]      # hem, sleeve ends, collar
    kd = KDTree(max(1, len(es)))
    for i, e in enumerate(es): kd.insert((e.verts[0].co + e.verts[1].co) / 2, i)
    kd.balance(); return kd


def covered(c, n, bvh=None, kd=None, near=0.07):
    bvh = bvh or tee_bvh; kd = kd or kd_open
    if kd.find(c)[2] < near: return False                     # near an opening it can be seen
    t1, t2 = n.orthogonal().normalized(), None
    t2 = n.cross(t1)
    for d in (n, (n + t1 * 0.85).normalized(), (n - t1 * 0.85).normalized(), (n + t2 * 0.85).normalized(), (n - t2 * 0.85).normalized()):
        hit = bvh.ray_cast(c + n * 0.002, d, 0.2)
        if hit[0] is None: return False
    return True


def settle(b, below=9.0):
    """anything that ended up just outside the cloth goes back under it (4 mm in)"""
    moved = 0
    for v in b.verts:
        if v.co.z > below: continue
        hit = tee_bvh.ray_cast(v.co + v.normal * 0.0005, -v.normal, 0.03)
        if hit[0] is not None and hit[1].dot(v.normal) > 0:
            v.co = hit[0] - v.normal * 0.004; moved += 1
    b.normal_update()
    return moved


pelvis = joint("joint-pelvis")
CUT = pelvis.z + 0.04          # the jeans start here, well inside the tee; the skin below is never seen
print("pelvis", tuple(round(x, 3) for x in pelvis), flush=True)
TROUSERS = os.environ.get("TROUSERS") if HBM else None
HEMZ = -1.0                   # the trousers' hem: the feet below it stay (people.py's bodies only)
if TROUSERS:
    with bpy.data.libraries.load(TROUSERS) as (src, dst):
        dst.objects = ["trousers"]
    tro = dst.objects[0]; sc.collection.objects.link(tro); upd()
    tme = bpy.data.meshes.new_from_object(tro.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    tme.transform(tro.matrix_world); bpy.data.objects.remove(tro)
    tbm = bmesh.new(); tbm.from_mesh(tme)
    tro_bvh, tro_open = BVHTree.FromBMesh(tbm), openings(tbm); tbm.free()
    HEMZ = min(v.co.z for v in tme.vertices) + 0.025
    CUT = max(v.co.z for v in tme.vertices) - 0.01
    print("trousers", len(tme.polygons), "faces, waist", round(CUT, 3), "hem", round(HEMZ, 3), flush=True)
elif HBM:
    CUT = -1.0                 # nothing over the legs: all of them is skin


def part(name, keep):
    """a new mesh of the faces `keep` says yes to, with UVs and point positions from the posed mesh"""
    b = bmesh.new(); b.from_mesh(me)
    b.verts.ensure_lookup_table(); b.faces.ensure_lookup_table()
    src = b.verts.layers.int.new("src")
    for v in b.verts: v.co = P[v.index]; v[src] = v.index
    kill = [f for f in b.faces if not keep(f)]
    bmesh.ops.delete(b, geom=kill, context="FACES")
    loose = [v for v in b.verts if not v.link_faces]
    bmesh.ops.delete(b, geom=loose, context="VERTS")
    return b, src


# ---------- skin ----------
LEG = [VG[g] for g in VG if g.startswith(("pelvis.", "upperleg", "lowerleg", "foot.", "toe"))] + ([VG["root"]] if "root" in VG else [])
leg = lambda i: sum(W[i].get(g, 0.0) for g in LEG)


def is_skin(f):
    ix = [v.index for v in f.verts]
    if not all(wt(i, "body") > 0.5 for i in ix): return False
    c = sum((P[i] for i in ix), Vector()) / len(ix)
    n = (P[ix[1]] - P[ix[0]]).cross(P[ix[2]] - P[ix[0]]).normalized()
    if TROUSERS:                                                        # under trousers.py's trousers
        if c.z < CUT + 0.02 and covered(c, n, tro_bvh, tro_open, 0.03): return False
    elif all(HEMZ < P[i].z < CUT and leg(i) > 0.5 for i in ix): return False     # inside the jeans
    return not covered(c, n) and not poking(c, n)


skin, SRC = part("skin", is_skin)
skin.normal_update()
print("skin faces", len(skin.faces), "settled", settle(skin, CUT + 0.15), flush=True)
if HBM:
    # hair (hair.py): grown into the skin's mesh, so it shares the skin's UV square and maps; split off at the end
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import hair as hair_
    print("hair faces %d, skin under it cut %d" % hair_.grow(skin, SRC, wt, body.get("sex") == "female",
          joint("joint-l-eye"), joint("joint-r-eye"), joint("joint-mouth")), flush=True)
HAIRF = skin.faces.layers.int.get("hair")
FLOW = skin.verts.layers.float_vector.get("flow")
HAIRK = skin.verts.layers.float.get("hairk")


def pack_skin_uvs(b):
    """the sculpt's UVs lie over 24 UDIM tiles, each part empty: the islands left after the cut are brought to an
    even texel size (the face twice as fine), then packed into the one square the maps are baked on"""
    uvl = b.loops.layers.uv.active
    b.faces.ensure_lookup_table(); b.verts.ensure_lookup_table()
    par = list(range(len(b.faces)))
    def find(k):
        while par[k] != k: par[k] = par[par[k]]; k = par[k]
        return k
    for e in b.edges:
        if len(e.link_faces) != 2: continue
        f1, f2 = e.link_faces
        u1 = {l.vert.index: l[uvl].uv for l in f1.loops if l.vert in e.verts}
        u2 = {l.vert.index: l[uvl].uv for l in f2.loops if l.vert in e.verts}
        if all((u1[k] - u2[k]).length < 1e-5 for k in u1): par[find(f1.index)] = find(f2.index)
    isl = {}
    for f in b.faces: isl.setdefault(find(f.index), []).append(f)
    neck = bone("neck01").z
    hl = b.faces.layers.int.get("hair")
    for fs in isl.values():
        a3 = sum(f.calc_area() for f in fs)
        a2 = 0.0
        for f in fs:
            uv = [l[uvl].uv for l in f.loops]
            a2 += abs(sum(uv[i].x * uv[i - 1].y - uv[i - 1].x * uv[i].y for i in range(len(uv)))) / 2
        k = math.sqrt(a3 / max(a2, 1e-12)) * (1.4 if hl and fs[0][hl] else 2.0 if sum(f.calc_center_median().z for f in fs) / len(fs) > neck else 1.0)
        ls = [l for f in fs for l in f.loops]
        c = sum((l[uvl].uv for l in ls), Vector((0, 0))) / len(ls)
        for l in ls: l[uvl].uv = (l[uvl].uv - c) * k + Vector((0.5, 0.5))
    m_ = bpy.data.meshes.new("uvpack"); b.to_mesh(m_)
    o_ = bpy.data.objects.new("uvpack", m_); sc.collection.objects.link(o_)
    bpy.context.view_layer.objects.active = o_
    for x in sc.objects: x.select_set(x is o_)
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(udim_source="CLOSEST_UDIM", rotate=True, scale=True, margin_method="FRACTION", margin=0.012, shape_method="CONCAVE")
    bpy.ops.object.mode_set(mode="OBJECT")
    for f, pf in zip(b.faces, m_.polygons):
        for l, li in zip(f.loops, pf.loop_indices): l[uvl].uv = m_.uv_layers.active.data[li].uv
    bpy.data.objects.remove(o_); bpy.data.meshes.remove(m_)
    print("skin uv islands", len(isl), "packed", flush=True)


if HBM: pack_skin_uvs(skin)
eyeL, eyeR = joint("joint-l-eye"), joint("joint-r-eye"); mouth = joint("joint-mouth"); jaw = joint("joint-jaw")
head = joint("joint-head")
print("eyes", round(eyeL.z, 3), "mouth", round(mouth.z, 3), flush=True)
fwd = Vector((0, -1, 0))


def smooth(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t)


# ---------- the skin's maps: its surface laid out on MakeHuman's UVs, handed to skin.py ----------
# Every visible texel of the skin (2048 square, above the shins: the jeans and the floor hide the rest) gets its
# point on the posed body, its normal, the body's own region weights (lips, ears, nails, scalp, hand) and its
# step across the body per texel; skin.py paints and sculpts from those. The colour lives in the maps, so the
# skin's vertex colour is white.
import numpy as np, json, subprocess, os, tempfile
HANDB = ["wrist", "metacarpal1", "metacarpal2", "metacarpal3", "metacarpal4"] + [f"finger{f}-{j}" for f in range(1, 6) for j in (1, 2, 3)]
skin.verts.ensure_lookup_table()
uvl = skin.loops.layers.uv.active
skin.verts.index_update(); skin.faces.ensure_lookup_table()
VA = np.zeros((len(skin.verts), 15), np.float32)          # P, N, lips, ears, nails, scalp, hand, hair, its flow
for v in skin.verts:
    i = v[SRC]
    VA[v.index, :3] = v.co; VA[v.index, 3:6] = v.normal
    if i < 0:                                           # hair (hair.py)
        VA[v.index, 9] = 1.0; VA[v.index, 11] = 0.02 + 0.98 * v[HAIRK]; VA[v.index, 12:15] = v[FLOW]; continue
    VA[v.index, 6:11] = (wt(i, "lips"), wt(i, "ears"), wt(i, "fingernails"), wt(i, "scalp"),
                         max(wt(i, f"{b_}.{sd}") for b_ in HANDB for sd in ("L", "R")))
RES = 2048
GY, GX, GV = [], [], []
for f in skin.faces:
    L_ = [(l.vert.index, l[uvl].uv.x, l[uvl].uv.y) for l in f.loops]
    for k in range(1, len(L_) - 1):
        t = (L_[0], L_[k], L_[k + 1])
        vi = [q[0] for q in t]
        A = VA[vi]
        if A[:, 2].max() < 0.3: continue
        uu = np.array([q[1] for q in t]) * RES - 0.5; vv = (1 - np.array([q[2] for q in t])) * RES - 0.5   # rows from the top
        det = (uu[1] - uu[0]) * (vv[2] - vv[0]) - (uu[2] - uu[0]) * (vv[1] - vv[0])
        if abs(det) < 1e-12: continue
        x0, x1 = int(max(0, np.floor(uu.min()))), int(min(RES - 1, np.ceil(uu.max())))
        y0, y1 = int(max(0, np.floor(vv.min()))), int(min(RES - 1, np.ceil(vv.max())))
        ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        b1 = ((xs - uu[0]) * (vv[2] - vv[0]) - (uu[2] - uu[0]) * (ys - vv[0])) / det
        b2 = ((uu[1] - uu[0]) * (ys - vv[0]) - (xs - uu[0]) * (vv[1] - vv[0])) / det
        b0 = 1 - b1 - b2
        m = (b0 > -1e-4) & (b1 > -1e-4) & (b2 > -1e-4)
        if not m.any(): continue
        val = b0[m][:, None] * A[0] + b1[m][:, None] * A[1] + b2[m][:, None] * A[2]
        # the step across the body for one texel along the image's x and down its rows
        E1, E2 = A[1, :3] - A[0, :3], A[2, :3] - A[0, :3]
        du1, dv1, du2, dv2 = uu[1] - uu[0], vv[1] - vv[0], uu[2] - uu[0], vv[2] - vv[0]
        Pu = (E1 * dv2 - E2 * dv1) / det; Pv = (E2 * du1 - E1 * du2) / det
        GY.append(ys[m]); GX.append(xs[m])
        GV.append(np.hstack([val[:, :11], np.tile(np.concatenate([Pu, Pv]), (len(val), 1)), val[:, 11:]]).astype(np.float32))
GY, GX, GV = np.concatenate(GY), np.concatenate(GX), np.concatenate(GV)
print("skin texels", len(GY), "of", RES * RES, flush=True)
LM = {k: list(v) for k, v in dict(eyeL=eyeL, eyeR=eyeR, mouth=mouth, jaw=jaw, head=head).items()}
LM["female"] = [1.0 if body.get("sex") == "female" else 0.0]
LM["hbm"] = [1.0 if HBM else 0.0]
for sd in ("L", "R"):
    for n_ in ["lowerarm01", "wrist"] + HANDB[1:]:
        LM[f"{n_}.{sd}"] = [list(B_[f"{n_}.{sd}"].head), list(B_[f"{n_}.{sd}"].tail)]
# SKIN_GBUF=<dir> keeps the hand-over there (to work on skin.py alone)
tmp = os.environ.get("SKIN_GBUF") or tempfile.mkdtemp(); os.makedirs(tmp, exist_ok=True)
np.savez(os.path.join(tmp, "g.npz"), res=RES, ys=GY.astype(np.int16), xs=GX.astype(np.int16), g=GV)
del GV
json.dump(LM, open(os.path.join(tmp, "lm.json"), "w"))
SKIN_OUT = OUT[:-4] if OUT.endswith(".glb") else OUT
subprocess.run(["python3", os.path.join(os.path.dirname(os.path.abspath(__file__)), "skin.py"), tmp, SKIN_OUT], check=True)
if not os.environ.get("SKIN_GBUF"): import shutil; shutil.rmtree(tmp)
lay = skin.verts.layers.float_color.new("albedo")
for v in skin.verts: v[lay] = (1.0, 1.0, 1.0, 1.0)
hairb = None
if HAIRF:                                               # the hair, off the skin's mesh into its own
    hairb = skin.copy()
    bmesh.ops.delete(hairb, geom=[f for f in hairb.faces if not f[hairb.faces.layers.int["hair"]]], context="FACES")
    bmesh.ops.delete(hairb, geom=[v for v in hairb.verts if not v.link_faces], context="VERTS")
    bmesh.ops.delete(skin, geom=[f for f in skin.faces if f[HAIRF]], context="FACES")
    bmesh.ops.delete(skin, geom=[v for v in skin.verts if not v.link_faces], context="VERTS")
# the hair cards over it (cards.py) and their strands (hairtex.py: <out>-hair.webp, beside the skin's maps)
cardb = cardn = None
if hairb:
    import cards as cards_
    SHE_ = body.get("sex") == "female"
    cardb, cardn = cards_.grow(hairb, SHE_, (0.024, 0.016, 0.011) if SHE_ else (0.016, 0.012, 0.0095))
    subprocess.run(["python3", os.path.join(os.path.dirname(os.path.abspath(__file__)), "hairtex.py"), SKIN_OUT + "-hair.webp",
                    "female" if SHE_ else "male"], check=True)

# ---------- jeans: the tights helper, loosened and smoothed ----------
# (people.py's bodies: trousers.py's trousers, if any, painted and settled under the tee)
def is_jeans(f):
    ix = [v.index for v in f.verts]
    # the tights helper is a whole bodysuit: only its legs, below the waist
    if not all(wt(i, "helper-tights") > 0.5 and leg(i) > 0.5 and P[i].z < CUT + 0.02 for i in ix): return False
    # inflated as the jeans will be, nothing under the tee and nothing through it
    c = sum((P[i] for i in ix), Vector()) / len(ix)
    n = (P[ix[1]] - P[ix[0]]).cross(P[ix[2]] - P[ix[0]]).normalized()
    c = c + n * 0.012
    return not covered(c, n) and not poking(c, n)


if HBM:
    jeans = None
    if TROUSERS:
        jeans = bmesh.new(); jeans.from_mesh(tme); jeans.normal_update()
        print("trousers settled", settle(jeans), flush=True)
        rgb = [float(x) for x in os.environ.get("TROUSERS_RGB", "0.012,0.016,0.03").split(",")]
        jl = jeans.verts.layers.float_color.new("albedo")
        for v in jeans.verts:
            c = Vector(rgb) * (1.0 + 0.06 * noise.noise(v.co * 6))
            v[jl] = (c.x, c.y, c.z, 1.0)
else:
  jeans, _ = part("jeans", is_jeans)
  jeans.normal_update()
  crotch = min((v.co.z for v in jeans.verts if abs(v.co.x) < 0.015), default=pelvis.z - 0.12)
  for v in jeans.verts:
      leg = smooth(crotch + 0.04, crotch - 0.06, v.co.z)        # straight-leg ease below the crotch
      v.co += v.normal * (0.008 + 0.022 * leg)
  for _ in range(12):                                           # denim doesn't show the muscle under it
      bmesh.ops.smooth_vert(jeans, verts=[v for v in jeans.verts if not v.is_boundary], factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
  jeans.normal_update()


  print("jeans settled", settle(jeans), flush=True)
  jl = jeans.verts.layers.float_color.new("albedo")
  for v in jeans.verts:
      p = v.co
      c = Vector((0.022, 0.022, 0.025)) * (1.0 + 0.08 * noise.noise(p * 6))
      # a slight wear on the front of the thighs
      c *= 1.0 + 0.35 * smooth(0.3, 0.9, v.normal.dot(fwd)) * smooth(crotch - 0.02, crotch - 0.2, p.z) * smooth(crotch - 0.45, crotch - 0.3, p.z)
      v[jl] = (c.x, c.y, c.z, 1.0)
  print("jeans faces", len(jeans.faces), "crotch", round(crotch, 3), flush=True)

# ---------- eyes ----------
if HBM:
    # the artist's eyeballs, posed with the head; each one's gaze is where its front pole went
    eyes = bmesh.new(); el = eyes.verts.layers.float_color.new("albedo")
    for o in ART_EYES:
        pole = min(o.data.vertices, key=lambda v: (o.matrix_world @ v.co).y).index      # the rest pose looks along -y
        m_ = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get())); m_.transform(o.matrix_world)
        e = EYEC[o.name]; gaze = (m_.vertices[pole].co - e).normalized()
        n0 = len(eyes.verts); eyes.from_mesh(m_); eyes.verts.ensure_lookup_table()
        # finer, for the iris's fibres (round as the eyeball)
        mine = [ed for ed in eyes.edges if ed.verts[0].index >= n0]
        bmesh.ops.subdivide_edges(eyes, edges=mine, cuts=2, use_grid_fill=True, smooth=1.0)
        eyes.verts.ensure_lookup_table()
        side = gaze.orthogonal().normalized(); up = gaze.cross(side)
        for v in eyes.verts[n0:]:
            r_ = (v.co - e).normalized(); d = r_.dot(gaze)
            az = math.atan2(r_.dot(up), r_.dot(side))
            # sclera: off-white, a little pinker and yellower toward the corners where the lids cover it
            sc_ = Vector((0.6, 0.54, 0.48)).lerp(Vector((0.56, 0.43, 0.37)), smooth(0.6, 0.2, d))
            # a dark brown iris (about 11.7 mm across): fibres running out from the pupil, a lighter ring round
            # the pupil (the collarette), darker toward its edge, a dark ring where it meets the white
            fib = 0.5 + 0.5 * math.sin(az * 38 + 2.5 * noise.noise(r_ * 25.0)) * (0.6 + 0.4 * noise.noise(r_ * 60.0))
            ir = Vector((0.05, 0.023, 0.011)) * (0.7 + 0.6 * fib)
            ir = ir.lerp(Vector((0.1, 0.052, 0.022)), 0.6 * smooth(0.955, 0.97, d) * (1 - smooth(0.975, 0.982, d)))
            ir = ir.lerp(Vector((0.018, 0.008, 0.004)), smooth(0.92, 0.885, d))
            c = sc_.lerp(Vector((0.02, 0.009, 0.005)), smooth(0.855, 0.875, d))
            c = c.lerp(ir, smooth(0.875, 0.89, d)).lerp(Vector((0.003, 0.003, 0.003)), smooth(0.984, 0.99, d))
            v[el] = (c.x, c.y, c.z, 1.0)
        bpy.data.meshes.remove(m_)
    eyes.normal_update()
else:
  eyes, _ = part("eyes", lambda f: all(wt(v.index, "helper-l-eye") > 0.5 or wt(v.index, "helper-r-eye") > 0.5 for v in f.verts))
  el = eyes.verts.layers.float_color.new("albedo")
  for v in eyes.verts:
    e = eyeL if v.co.x > 0 else eyeR
    d = (v.co - e).normalized().dot(fwd)
    c = Vector((0.62, 0.56, 0.5)).lerp(Vector((0.05, 0.022, 0.012)), smooth(0.9, 0.93, d)).lerp(Vector((0.004, 0.004, 0.004)), smooth(0.975, 0.985, d))
    v[el] = (c.x, c.y, c.z, 1.0)


# ---------- how it moves: weights for the 3D view's idle motion ----------
# The view keeps the person alive with a few slow turns about fixed joints (breath, the head, each arm from the
# shoulder, forearm from the elbow, hand from the wrist; the whole body swaying over the feet). Each vertex
# carries how much of each it follows, from the rig's own skin weights (so the shoulder and the elbow bend as
# they do when posed), in five float attributes (the side, left or right, is the sign of x). The joints go with
# the skin object as extras ("motion", glTF's y-up frame).
def chain(n):
    return {n} | {c.name for c in rig.data.bones[n].children_recursive} if n in rig.data.bones else set()


GI = {g.index: g.name for g in body.vertex_groups}
HEADS = chain("neck03") | chain("head")
ARMS = {sd: chain("upperarm01." + sd) for sd in "LR"}
FORES = {sd: chain("lowerarm01." + sd) for sd in "LR"}
HANDS = {sd: chain("wrist." + sd) for sd in "LR"}
TORSO = {n for n in ("spine01", "spine02", "spine03", "spine04", "spine05", "breast.L", "breast.R", "pectoral.L",
                     "pectoral.R", "clavicle.L", "clavicle.R", "shoulder01.L", "shoulder01.R") if n in rig.data.bones}
MOT = ("_breath", "_head", "_arm", "_fore", "_hand")


def motion_of(i, co, n):
    w = {GI[g]: x for g, x in W[i].items() if g in GI}
    sd = "L" if co.x > 0 else "R"
    head = sum(x for k, x in w.items() if k in HEADS) + 0.5 * w.get("neck02", 0.0)
    arm = sum(x for k, x in w.items() if k in ARMS[sd]) + 0.35 * w.get("shoulder01." + sd, 0.0)
    fore = sum(x for k, x in w.items() if k in FORES[sd]); hand = sum(x for k, x in w.items() if k in HANDS[sd])
    torso = sum(x for k, x in w.items() if k in TORSO)
    breath = torso * (0.45 + 0.55 * max(0.0, n.dot(fwd)))
    return [min(1.0, x) for x in (breath, head, arm, fore, hand)]


def weigh(b, src=None, const=None):
    lays = [b.verts.layers.float.new(k) for k in MOT]
    for v in b.verts:
        vals = const if const else (motion_of(v[src], v.co, v.normal) if v[src] >= 0 else [0, 1, 0, 0, 0])
        for l, x in zip(lays, vals): v[l] = x


weigh(skin, SRC)
if hairb: weigh(hairb, const=[0, 1, 0, 0, 0])
if cardb: weigh(cardb, const=[0, 1, 0, 0, 0])
weigh(eyes, const=[0, 1, 0, 0, 0])
if jeans: weigh(jeans, const=[0, 0, 0, 0, 0])
gl = lambda p: [round(p.x, 4), round(p.z, 4), round(-p.y, 4)]
MOTION = {"neck": gl(bone("neck02")), "feet": gl((bone("foot.L") + bone("foot.R")) / 2)}
for sd in "LR":
    MOTION["shoulder." + sd] = gl(bone("upperarm01." + sd)); MOTION["elbow." + sd] = gl(bone("lowerarm01." + sd))
    MOTION["wrist." + sd] = gl(bone("wrist." + sd))


# ---------- out ----------
def obj(name, b, sub=1):
    m = bpy.data.meshes.new(name); b.to_mesh(m); b.free()
    if m.validate(verbose=False): print("fixed", name)
    for p in m.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, m); sc.collection.objects.link(o)
    mat = bpy.data.materials.new(name); m.materials.append(mat)
    if m.color_attributes: m.color_attributes.active_color = m.color_attributes[0]
    if sub: s = o.modifiers.new("sub", "SUBSURF"); s.levels = sub; s.render_levels = sub
    return o


outs = [obj("skin", skin, 0 if HBM else 1)] + ([obj("jeans", jeans, 0 if HBM else 1)] if jeans else []) + [obj("eyes", eyes)] \
    + ([obj("hair", hairb, 0)] if hairb else [])
if cardb:
    co = obj("haircards", cardb, 0)
    co.data.normals_split_custom_set_from_vertices([tuple(n) for n in cardn])
    outs.append(co)
outs[0]["motion"] = json.dumps(MOTION)
for o in list(sc.objects):
    if o not in outs: bpy.data.objects.remove(o)
for o in outs: o.select_set(True)
args = dict(filepath=OUT, use_selection=True, export_apply=True, export_yup=True, export_materials="EXPORT",
            export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7, export_vertex_color="NAME", export_vertex_color_name="albedo", export_all_vertex_colors=False,
            export_skins=False, export_animations=False, export_morph=False, export_attributes=True, export_extras=True)
bpy.ops.export_scene.gltf(**args)
print("saved", OUT, {o.name: len(o.data.polygons) for o in outs})
