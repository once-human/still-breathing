# blender -b --factory-startup -P people.py -- <human_base_meshes_bundle.blend> <male|female> <height m> <mh body.blend> <out.blend>
# The people who wear the shop tee: Blender Studio's realistic base bodies (Human Base Meshes v1.4.1, CC0), sculpted
# by hand by artists, with real anatomy (MakeHuman's own body reads soft and game-like next to them). They come with
# no skeleton, so MakeHuman's (the fit pipeline's rig, the same bone names build.py and human.py pose) is fitted
# into them:
#   1. the artist's body, at its first subdivision level (the finer sculpt is baked later as relief), scaled to
#      the person's height, centred, facing -y like MakeHuman
#   2. MakeHuman's body of the same sex is posed until its upper arms, forearms, hands, thighs and shins lie
#      along the artist's (each measured the same way on both: the centres of the limb's cross-sections)
#   3. its surface is drawn onto the artist's surface a little at a time, held smooth (non-rigid ICP: each point
#      goes to the nearest point of the other surface where the two face the same way, and the pull is spread
#      over its neighbours, stiff at first, looser as they meet)
#   4. how far each part of MakeHuman's surface moved carries its joints along (bone ends move as the surface
#      round them did), and its skin weights and regions (lips, ears, nails, scalp) pass to the nearest point
# Out: a .blend with "body" (the artist's mesh, MakeHuman's vertex groups, an armature modifier), "rig" (rest pose =
# the artist's A-pose), "eye.L" / "eye.R" (the artist's eyes, riding on the head bone), "detail" (the full sculpt,
# hidden, for the relief bake). The same objects build.py and human.py read from MakeHuman's bodies.
import bpy, bmesh, sys, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

a = sys.argv[sys.argv.index("--") + 1:]
HBM, SEX, HEIGHT, MH, OUT = a[0], a[1], float(a[2]), a[3], a[4]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
upd = bpy.context.view_layer.update
NAME = f"GEO-body_{SEX}_realistic"

# ---------- 1. the artist's body ----------
with bpy.data.libraries.load(HBM) as (src, dst):
    dst.objects = [n for n in src.objects if n == NAME or n.startswith(NAME + ".eye")]
for o in dst.objects: sc.collection.objects.link(o)
art = bpy.data.objects[NAME]
eyes = [o for o in dst.objects if o is not art]
mr = [m for m in art.modifiers if m.type == "MULTIRES"][0]
# the full sculpt, for the relief bake
det = art.copy(); det.data = art.data.copy(); det.name = "detail"; sc.collection.objects.link(det)
for o, lv in ((art, 1), (det, mr.total_levels)):
    m = [m for m in o.modifiers if m.type == "MULTIRES"][0]
    m.levels = m.render_levels = m.sculpt_levels = lv
    with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o]):
        bpy.ops.object.modifier_apply(modifier=m.name)
for o in [art, det] + eyes:
    o.matrix_world = o.matrix_world.copy()
for e in eyes:
    mw = e.matrix_world.copy(); e.parent = None; e.matrix_world = mw
upd()
P = np.array([art.matrix_world @ v.co for v in art.data.vertices])
zmin, zmax = P[:, 2].min(), P[:, 2].max()
k = HEIGHT / (zmax - zmin)
cx = (P[:, 0].min() + P[:, 0].max()) / 2
M = Matrix.Diagonal((k, k, k, 1)) @ Matrix.Translation((-cx, 0, -zmin))
for o in [art, det] + eyes:
    o.data.transform(M @ o.matrix_world); o.matrix_world = Matrix.Identity(4)
art.name = "body"; art.data.name = "body"
print("artist body", NAME, "verts", len(art.data.vertices), "detail", len(det.data.vertices), "scale", round(k, 4), flush=True)
A = np.array([v.co for v in art.data.vertices])
bmA = bmesh.new(); bmA.from_mesh(art.data); bmA.normal_update()
bvhA = BVHTree.FromBMesh(bmA)
NA = np.array([v.normal for v in bmA.verts])

# ---------- MakeHuman's body of the same sex ----------
with bpy.data.libraries.load(MH) as (src, dst):
    dst.objects = [n for n in src.objects if n in ("body", "rig")]
for o in dst.objects: sc.collection.objects.link(o)
mh = [o for o in dst.objects if o.type == "MESH"][0]; rig = [o for o in dst.objects if o.type == "ARMATURE"][0]
mh.name = "mh"; rig.name = "rig"
for m in mh.modifiers:
    if m.type == "MASK": m.show_viewport = False
VG = {g.index: g.name for g in mh.vertex_groups}
bodyg = mh.vertex_groups["body"].index
BODY = np.array([v.index for v in mh.data.vertices if any(g.group == bodyg and g.weight > 0.5 for g in v.groups)])
inb = np.full(len(mh.data.vertices), -1); inb[BODY] = np.arange(len(BODY))
EDGES = np.array([(inb[e.vertices[0]], inb[e.vertices[1]]) for e in mh.data.edges if inb[e.vertices[0]] >= 0 and inb[e.vertices[1]] >= 0])
TRIS = []
for p in mh.data.polygons:
    ix = [inb[i] for i in p.vertices]
    if min(ix) < 0: continue
    for t in range(1, len(ix) - 1): TRIS.append((ix[0], ix[t], ix[t + 1]))
TRIS = np.array(TRIS)
kmh = HEIGHT / (max(v.co.z for v in mh.data.vertices) - min(v.co.z for v in mh.data.vertices))
rig.scale = (kmh, kmh, kmh); mh.parent = None
mh.scale = (kmh, kmh, kmh)
upd()


def mh_points():
    dg = bpy.context.evaluated_depsgraph_get(); ev = mh.evaluated_get(dg); me = ev.to_mesh()
    X = np.array([mh.matrix_world @ me.vertices[i].co for i in BODY]); ev.to_mesh_clear(); return X


def centre(X, sel):
    return X[sel].mean(0)


def limbs(X, s, shoulder, hip_x):
    """the limb axes of one side, measured on the surface: centres of the arm's points by distance from the
    shoulder, and of the leg's by height"""
    side = X[:, 0] * s
    arm = side > abs(shoulder[0]) + 0.05
    d = np.linalg.norm(X - shoulder, axis=1)
    L = HEIGHT / 1.75
    u0, u1 = centre(X, arm & (d > 0.12 * L) & (d < 0.16 * L)), centre(X, arm & (d > 0.22 * L) & (d < 0.26 * L))
    f0, f1 = centre(X, arm & (d > 0.36 * L) & (d < 0.40 * L)), centre(X, arm & (d > 0.48 * L) & (d < 0.52 * L))
    hand = arm & (d > 0.6 * L) & (d < 0.72 * L)
    h0, h1 = centre(X, hand & (d < 0.64 * L)), centre(X, hand & (d > 0.68 * L))
    H = X[hand] - X[hand].mean(0)
    hn = np.linalg.svd(H, full_matrices=False)[2][2]
    leg = (side > 0.02) & (X[:, 2] < 0.47 * HEIGHT)
    t0, t1 = centre(X, leg & (np.abs(X[:, 2] - 0.42 * HEIGHT) < 0.01)), centre(X, leg & (np.abs(X[:, 2] - 0.32 * HEIGHT) < 0.01))
    s0, s1 = centre(X, leg & (np.abs(X[:, 2] - 0.22 * HEIGHT) < 0.01)), centre(X, leg & (np.abs(X[:, 2] - 0.10 * HEIGHT) < 0.01))
    n = lambda v: v / np.linalg.norm(v)
    hm = n(h1 - h0); hn = n(hn - hm * (hn @ hm))
    if np.cross(hm, hn)[1] * s < 0: hn = -hn
    return dict(upper=n(u1 - u0), fore=n(f1 - f0), hand=hm, hnorm=hn, thigh=n(t1 - t0), shin=n(s1 - s0))


def turn(pb, q):
    upd(); Mb = rig.matrix_world @ pb.matrix
    R = q.to_matrix() @ Mb.to_3x3()
    Mn = Matrix.LocRotScale(Mb.translation, R.to_quaternion(), Mb.to_scale())
    pb.matrix = rig.matrix_world.inverted() @ Mn; upd()


# ---------- 2. MakeHuman posed along the artist's limbs ----------
for b in rig.pose.bones: b.rotation_mode = "QUATERNION"
for it in range(3):
    for sd, s in (("L", 1), ("R", -1)):
        sh = np.array(rig.matrix_world @ rig.pose.bones["upperarm01." + sd].head)
        LA, LM = limbs(A, s, sh, 0), limbs(mh_points(), s, sh, 0)
        for bone, key in (("upperarm01", "upper"), ("lowerarm01", "fore"), ("upperleg01", "thigh"), ("lowerleg01", "shin")):
            LM = limbs(mh_points(), s, sh, 0)
            turn(rig.pose.bones[f"{bone}.{sd}"], Vector(LM[key]).rotation_difference(Vector(LA[key])))
        LM = limbs(mh_points(), s, sh, 0)
        Fm = Matrix((LM["hand"], LM["hnorm"], np.cross(LM["hand"], LM["hnorm"]))).transposed()
        Fa = Matrix((LA["hand"], LA["hnorm"], np.cross(LA["hand"], LA["hnorm"]))).transposed()
        turn(rig.pose.bones["wrist." + sd], (Fa @ Fm.transposed()).to_quaternion())
    X0 = mh_points()
    print("pose pass", it, "mean gap", round(float(np.mean([bvhA.find_nearest(Vector(p))[3] for p in X0[::7]])), 4), flush=True)
# the trunk: MakeHuman's front and back onto the artist's (a shift in depth)
X0 = mh_points()
mid = (np.abs(X0[:, 0]) < 0.12) & (X0[:, 2] > 0.5 * HEIGHT) & (X0[:, 2] < 0.75 * HEIGHT)
mida = (np.abs(A[:, 0]) < 0.12) & (A[:, 2] > 0.5 * HEIGHT) & (A[:, 2] < 0.75 * HEIGHT)
dy = A[mida, 1].mean() - X0[mid, 1].mean()
rig.location.y += dy; mh.location.y += dy; upd()
X0 = mh_points()

# ---------- 3. non-rigid fit, surface onto surface ----------
nb_i, nb_j = np.concatenate([EDGES[:, 0], EDGES[:, 1]]), np.concatenate([EDGES[:, 1], EDGES[:, 0]])
deg = np.bincount(nb_i, minlength=len(BODY)).astype(float)


def vnormals(X):
    fn = np.cross(X[TRIS[:, 1]] - X[TRIS[:, 0]], X[TRIS[:, 2]] - X[TRIS[:, 0]])
    N = np.zeros_like(X)
    for c in range(3): np.add.at(N, TRIS[:, c], fn)
    return N / (np.linalg.norm(N, axis=1, keepdims=True) + 1e-12)


X = X0.copy()
ITER = 40
for it in range(ITER):
    stiff = 30.0 * (0.04 / 30.0) ** (it / (ITER - 1))          # 30 -> 0.04
    Nm = vnormals(X)
    D = np.zeros_like(X); W = np.zeros(len(X))
    for i in range(len(X)):
        loc, nrm, fi, dist = bvhA.find_nearest(Vector(X[i]))
        if loc is not None and Vector(Nm[i]).dot(nrm) > 0.4:
            D[i] = np.array(loc) - X[i]; W[i] = 1.0
    kd = KDTree(len(X))
    for i, p in enumerate(X): kd.insert(p, i)
    kd.balance()
    for j in range(0, len(A), 2):
        p, i, dist = kd.find(Vector(A[j]))
        if Vector(Nm[i]).dot(Vector(NA[j])) > 0.4:
            D[i] += (A[j] - X[i]) * 0.5; W[i] += 0.5
    Dw = D / np.maximum(W, 1e-9)[:, None]
    S = Dw.copy()
    for _ in range(25):
        nbm = np.zeros_like(S)
        for c in range(3): nbm[:, c] = np.bincount(nb_i, weights=S[nb_j, c], minlength=len(S))
        nbm /= np.maximum(deg, 1)[:, None]
        S = (W[:, None] * Dw + stiff * nbm) / (W[:, None] + stiff)
    X = X + S * 0.8
    if it % 8 == 0 or it == ITER - 1:
        gap = np.array([bvhA.find_nearest(Vector(p))[3] for p in X[::5]])
        print("fit", it, "stiff", round(stiff, 3), "gap mean", round(float(gap.mean()) * 1000, 1), "mm, 95%", round(float(np.percentile(gap, 95)) * 1000, 1), "mm", flush=True)
# last, exactly onto the surface
for i in range(len(X)):
    loc = bvhA.find_nearest(Vector(X[i]))[0]
    if loc is not None: X[i] = np.array(loc)

# ---------- 4. joints and weights ----------
Dt = X - X0
kd0 = KDTree(len(X0))
for i, p in enumerate(X0): kd0.insert(p, i)
kd0.balance()


def carried(p):
    near = kd0.find_n(Vector(p), 16)
    w = np.array([1 / (d + 0.004) ** 2 for _, _, d in near]); ix = [i for _, i, _ in near]
    return np.array(p) + (Dt[ix] * w[:, None]).sum(0) / w.sum()


upd()
posed = {b.name: (rig.matrix_world @ b.head, rig.matrix_world @ b.tail, (rig.matrix_world.to_3x3() @ b.matrix.to_3x3()).col[2].normalized()) for b in rig.pose.bones}
# the new rest: MakeHuman's skeleton in the artist's pose, each bone end carried as the surface round it was
newrig = bpy.data.objects.new("rig_new", rig.data.copy()); sc.collection.objects.link(newrig)
bpy.context.view_layer.objects.active = newrig
for o in sc.objects: o.select_set(o is newrig)
bpy.ops.object.mode_set(mode="EDIT")
for eb in newrig.data.edit_bones:
    h, t, zax = posed[eb.name]
    eb.head = Vector(carried(h)); eb.tail = Vector(carried(t))
    if (eb.tail - eb.head).length < 1e-4: eb.tail = eb.head + (t - h)
    eb.align_roll(zax)
bpy.ops.object.mode_set(mode="OBJECT")
# weights: each artist vertex takes MakeHuman's at the nearest point of the fitted surface
bvhX = BVHTree.FromPolygons([Vector(p) for p in X], [tuple(t) for t in TRIS])
Wmh = {}
for v in mh.data.vertices:
    if inb[v.index] < 0: continue
    Wmh[inb[v.index]] = {VG[g.group]: g.weight for g in v.groups if g.weight > 1e-4}
SKIP = {"body", "HelperGeometry", "JointCubes", "Left", "Mid", "Right"}
deform = {b.name for b in rig.data.bones if b.use_deform}
groups = {}
for vi, p in enumerate(A):
    loc, nrm, ti, dist = bvhX.find_nearest(Vector(p))
    a_, b_, c_ = TRIS[ti]; pa, pb, pc = X[a_], X[b_], X[c_]
    v0, v1, v2 = pb - pa, pc - pa, np.array(loc) - pa
    d00, d01, d11, d20, d21 = v0 @ v0, v0 @ v1, v1 @ v1, v2 @ v0, v2 @ v1
    den = d00 * d11 - d01 * d01 + 1e-20
    wb = (d11 * d20 - d01 * d21) / den; wc = (d00 * d21 - d01 * d20) / den; wa = 1 - wb - wc
    acc = {}
    for idx, w in ((a_, wa), (b_, wb), (c_, wc)):
        for g, gw in Wmh[idx].items():
            if g in SKIP or g.startswith("joint-") or g.startswith("helper-"): continue
            acc[g] = acc.get(g, 0.0) + gw * max(w, 0.0)
    tot = sum(w for g, w in acc.items() if g in deform) or 1.0
    for g, w in acc.items():
        groups.setdefault(g, []).append((vi, w / tot if g in deform else w))
for g, lst in groups.items():
    vg = art.vertex_groups.new(name=g)
    for vi, w in lst:
        if w > 1e-3: vg.add([vi], min(1.0, w), "REPLACE")
print("groups", len(groups), flush=True)

# ---------- out ----------
bpy.data.objects.remove(mh); bpy.data.objects.remove(rig)
newrig.name = "rig"; newrig.data.name = "rig"
am = art.modifiers.new("Armature", "ARMATURE"); am.object = newrig
for e in eyes:
    e.name = "eye.L" if (sum((e.matrix_world @ v.co).x for v in e.data.vertices) > 0) else "eye.R"
    e.vertex_groups.new(name="head").add(range(len(e.data.vertices)), 1.0, "REPLACE")
    e.modifiers.new("Armature", "ARMATURE").object = newrig
det.hide_render = True; det.hide_viewport = True
for o in [art, det] + eyes:
    for p in o.data.polygons: p.use_smooth = True
art["sex"] = SEX; art["height"] = HEIGHT
bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
print("saved", OUT, flush=True)
