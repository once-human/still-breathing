# 02 breath, part 1 of 2 (Blender): a December crowd seen from the stage through a heat camera.
#   blender -b -P pipeline/art/breath/crowd.py -- <outdir> [W H spp unique]
# Writes <outdir>/temp.npy (apparent temperature in degrees C per pixel, float16) and <outdir>/scene.json (every
# visible mouth, for the breath in part 2).
#
# The people are not mannequins. Each near person is built on its own from MakeHuman (MPFB, CC0 system assets):
# a South Asian mix of builds, ages 19-35, men and women, their own face shape, hair and clothes, eyebrows and
# eyes. Each stands in a frame of real motion capture (CMU Graphics Lab, free to use) picked for what a crowd
# does at a show: both arms up, one up, bouncing, mid-jump, filming. Friends have an arm round each other, a
# few are on someone's shoulders, some sing with their head back, some film with phones held up.
#
# What the camera sees is the temperature of each surface, worked out from how a body loses heat on a 16 C night:
#   skin: the inner corners of the eyes are the warmest place on a face, the forehead and neck next, cheeks
#         cooler toward the ears, the nose and ear rims cold; hands differ a lot from person to person and the
#         fingertips are colder than the palm
#   cloth: as warm as the skin under it where it touches, cooling toward the air the further it hangs off the
#          body (folds show by themselves); thicker cloth is cooler on the outside
#   hair: warm at the scalp, close to the air at the ends; caps and glasses are cold, glass reads as an opaque
#         cool lens; a filming phone runs hot at its chip
#   every surface also reflects a little: edges facing the open sky read colder
# The barrier, the delay towers and the trees behind are cold; the sky is colder than anything.
import bpy, bmesh, sys, os, math, json, random, time, addon_utils
import numpy as np
from mathutils import Vector, Matrix, Quaternion, noise
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from bpy_extras.object_utils import world_to_camera_view

T0 = time.time()
def log(*a): print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)

addon_utils.enable("io_anim_bvh", default_set=True)
MPS = None
for _n in ("bl_ext.user_default.mpfb", "bl_ext.blender_org.mpfb"):
    try:
        MPS = __import__(_n + ".services", fromlist=["HumanService"]); break
    except ImportError:
        pass
if MPS is None: raise SystemExit("MPFB is not installed")
HumanService, TargetService = MPS.HumanService, MPS.TargetService
MPFB_DATA = os.path.join(os.path.dirname(MPS.__file__), "..", "data")

A = sys.argv[sys.argv.index("--") + 1:]
OUT = A[0]; W = int(A[1]) if len(A) > 1 else 900; H = int(A[2]) if len(A) > 2 else 1200
SPP = int(A[3]) if len(A) > 3 else 24
UNIQUE = int(A[4]) if len(A) > 4 else 70
os.makedirs(OUT, exist_ok=True)
ASSETS = os.environ.get("SB_ASSETS", os.path.expanduser("~/Documents/Projects/sahn-assets"))
CMU, PK = os.path.join(ASSETS, "cmu"), os.path.join(ASSETS, "mh-system", "pack")
rng = random.Random(int(os.environ.get("SEED", 1213)))
T_AIR, T_SKY, T_GROUND = 16.0, -24.0, 17.5
sc = bpy.context.scene
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
upd = bpy.context.view_layer.update


# =====================================================================================================
# the pose bank: frames of real motion capture, sorted by what the arms and feet are doing
# =====================================================================================================
SRC = {}       # clip -> source armature
ROLLS = None
BANK = {"up2": [], "up1": [], "mid": [], "low": [], "air": []}

def import_clip(c):
    global ROLLS
    before = set(bpy.data.objects)
    bpy.ops.import_anim.bvh(filepath=os.path.join(CMU, c + ".bvh"), axis_forward="Y", axis_up="Z", rotate_mode="XYZ",
                            update_scene_fps=False, update_scene_duration=False)
    a = [o for o in bpy.data.objects if o not in before][0]
    a.name = "src_" + c; a.hide_render = True
    if ROLLS is None:
        bpy.context.view_layer.objects.active = a
        bpy.ops.object.mode_set(mode="EDIT"); ROLLS = {b.name: b.roll for b in a.data.edit_bones}
        bpy.ops.object.mode_set(mode="OBJECT")
    return a

def jpos(a, n, tail=False):
    pb = a.pose.bones[n]; return a.matrix_world @ (pb.tail if tail else pb.head)

clips = sorted(f[:-4] for f in os.listdir(CMU) if f.endswith(".bvh"))
for c in clips:
    a = import_clip(c); SRC[c] = a
    f0, f1 = (int(v) for v in a.animation_data.action.frame_range)
    frames = list(range(max(f0 + 20, 2), f1, 9))
    rows = []
    for f in frames:
        sc.frame_set(f)
        # the clips are y-up as imported (the importer is told z-up so the bone rotations copy over as they are)
        hd, lh, rh = jpos(a, "Head", True), jpos(a, "LeftHand", True), jpos(a, "RightHand", True)
        lf, rf, hip, nk = jpos(a, "LeftFoot"), jpos(a, "RightFoot"), jpos(a, "Hips"), jpos(a, "Neck")
        sh = (jpos(a, "LeftArm").y + jpos(a, "RightArm").y) / 2
        hz = lambda p: math.hypot(p.x - nk.x, p.z - nk.z)                 # how far a hand is out from the neck, sideways
        rows.append((f, hd.y, lh.y, rh.y, lf.y, rf.y, sh, (nk - hip).normalized().y, hz(lh), hz(rh), hip.y))
    R = np.array(rows, "f8")
    if not len(R): continue
    foot0 = np.percentile(np.minimum(R[:, 4], R[:, 5]), 10)
    stand = np.percentile(R[:, 1] - foot0, 75)
    for f, hz, lz, rz, lfz, rfz, shz, upz, lo, ro, hipz in R:
        if hz - foot0 < 0.9 * stand or upz < 0.9: continue            # bent over, crouched
        lift, diff = min(lfz, rfz) - foot0, abs(lfz - rfz)
        if diff > 0.07 * stand: continue                              # a kick or an arabesque, not a crowd
        up = [z > hz - 0.02 * stand for z in (lz, rz)]
        out = [o / stand for o in (lo, ro)]
        # a crowd keeps its arms in: up over the head, punching up in front, or down by the sides. arms held
        # straight out to the side (a jumping jack half way, a dancer's line) read as a scarecrow, never as a crowd
        def fits(i):
            z, o = (lz, rz)[i], out[i]
            if up[i]: return o < 0.3
            if z > shz: return o < 0.26
            return o < 0.2 and z < hipz + 0.12 * stand
        if not (fits(0) and fits(1)): continue
        kind = "up2" if all(up) else "up1" if any(up) else "mid" if max(lz, rz) > shz else "low"
        e = (c, int(f), float(lift / stand))
        BANK["air" if lift > 0.05 * stand and kind != "low" else kind].append(e)
log("pose bank", {k: len(v) for k, v in BANK.items()})


# =====================================================================================================
# one person
# =====================================================================================================
HAIR_M = ["short01", "short02", "short03", "short04", "short02", "short04", "short01", "long01"]
HAIR_F = ["long01", "ponytail01", "braid01", "bob01", "bob02", "long01", "ponytail01", "braid01"]
SUIT_M = [f"male_casualsuit0{i}" for i in range(1, 7)]
SUIT_F = ["female_casualsuit01", "female_casualsuit02", "female_sportsuit01"]
FACE_T = ["nose/nose-scale-horiz-incr", "nose/nose-scale-horiz-decr", "nose/nose-flaring-incr", "nose/nose-hump-incr",
          "nose/nose-scale-vert-incr", "nose/nose-point-width-incr", "chin/chin-prominent-incr", "chin/chin-width-incr",
          "chin/chin-width-decr", "cheek/l-cheek-bones-incr", "mouth/mouth-scale-horiz-incr", "mouth/mouth-lowerlip-volume-incr",
          "eyes/r-eye-size-incr", "eyes/l-eye-size-incr", "head/head-oval", "head/head-round", "head/head-square",
          "head/head-fat-incr", "neck/neck-scale-horiz-incr", "ears/r-ear-scale-incr", "ears/l-ear-scale-incr",
          "forehead/forehead-scale-vert-incr", "eyebrows/eyebrows-trans-up"]

def vg_w(obj, name):
    g = obj.vertex_groups.get(name); w = np.zeros(len(obj.data.vertices), "f4")
    if g is None: return w
    gi = g.index
    for v in obj.data.vertices:
        for e in v.groups:
            if e.group == gi: w[v.index] = e.weight; break
    return w

def coords(obj):
    """evaluated world coordinates and normals in the object's own vertex order (topology-changing modifiers off)"""
    off = [m for m in obj.modifiers if m.type in ("MASK", "SUBSURF") and m.show_viewport]
    for m in off: m.show_viewport = False
    dg = bpy.context.evaluated_depsgraph_get(); ev = obj.evaluated_get(dg); me = ev.to_mesh()
    n = len(me.vertices); co = np.empty(n * 3, "f4"); me.vertices.foreach_get("co", co)
    no = np.empty(n * 3, "f4"); me.vertices.foreach_get("normal", no)
    ev.to_mesh_clear()
    for m in off: m.show_viewport = True
    M = np.array(obj.matrix_world, "f4")
    return co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3], no.reshape(-1, 3) @ M[:3, :3].T

def set_attr(obj, name, arr):
    me = obj.data
    if name in me.attributes: me.attributes.remove(me.attributes[name])
    me.attributes.new(name, "FLOAT", "POINT").data.foreach_set("value", np.asarray(arr, "f4"))

def gauss(d, s): return np.exp(-(d * d) / (2 * s * s))

def skin_temps(bm, p):
    """degrees C over the whole skin, rest pose (the body faces -y)"""
    co, no = coords(bm)
    w = lambda n: vg_w(bm, n)
    cen = lambda n: co[w(n) > 0.5].mean(0) if (w(n) > 0.5).any() else None
    head = w("Head"); neck = w("Neck") + w("Neck1")
    eyeL, eyeR = cen("joint-l-eye"), cen("joint-r-eye"); mouth = cen("joint-mouth")
    mid = (eyeL + eyeR) / 2
    T = np.full(len(co), 33.9 + p["core"], "f4")
    T += 0.6 * np.clip(neck, 0, 1)
    face = (head > 0.4) & (co[:, 1] < mid[1] + 0.03)
    # the nose tip: the most forward point between the eyes and the mouth
    band = face & (co[:, 2] < mid[2]) & (co[:, 2] > mouth[2]) & (np.abs(co[:, 0] - mid[0]) < 0.02)
    tip = co[band][np.argmin(co[band][:, 1])] if band.any() else mid + Vector((0, -0.05, -0.04))
    d = lambda c: np.linalg.norm(co - np.asarray(c, "f4"), axis=1)
    lateral = np.abs(co[:, 0] - mid[0]) / 0.075
    T -= face * np.clip(lateral, 0, 1.4) ** 2 * 1.3                                  # cheeks cool toward the ears
    T += face * (co[:, 2] > mid[2] + 0.015) * 0.35                                     # forehead
    for e in (eyeL, eyeR):                                                              # inner canthi: the warmest
        can = np.asarray(e, "f4") + np.array([(mid[0] - e[0]) * 0.55, -0.012, -0.004], "f4")
        T += 1.4 * gauss(d(can), 0.0065) + 0.5 * gauss(d(e), 0.014)
    T -= (3.2 + p["nose"]) * gauss(d(tip), 0.019)                                      # the nose
    T += 0.4 * gauss(d(mouth), 0.012) * (w("lips") > 0.1)
    ears = w("ears") > 0.1
    if ears.any():
        ec = co[ears].mean(0); er = np.linalg.norm(co - ec, axis=1)
        T[ears] = (31.0 + p["core"] - 1.8 * np.clip(er[ears] / 0.035, 0, 1.2) - 0.8 * (co[ears, 2] < ec[2]))
    # arms and hands
    for s in ("Left", "Right"):
        T -= 1.2 * w(s + "Arm") * 0 + 1.4 * w(s + "ForeArm")
        hand = w(s + "Hand"); fing = w(s + "HandFinger1") + w(("L" if s == "Left" else "R") + "Thumb")
        T -= hand * (3.4 - p["hands"]) + np.clip(fing, 0, 1) * (5.2 - p["hands"])        # up in the cold air
    T -= 0.8 * (w("fingernails") > 0.1)
    # slow mottle of the blood under the skin
    mot = np.array([noise.noise(Vector(c) * 22.0) for c in co], "f4")
    T += 0.35 * mot
    return T, co, no, dict(eyeL=eyeL, eyeR=eyeR, mouth=mouth, tip=tip, mid=mid)

def cloth_temps(obj, body_co, body_T, kd, bvh, clo_top, clo_bottom, hip_z, stretch=0.010):
    co, no = coords(obj)
    T = np.empty(len(co), "f4")
    for i, c in enumerate(co):
        hit = bvh.find_nearest(Vector(c))
        gap = hit[3] if hit[0] is not None else 0.05
        _, j, _ = kd.find(Vector(c))
        clo = clo_top if c[2] > hip_z else clo_bottom
        T[i] = T_AIR + (body_T[j] - T_AIR) / (1.0 + max(0.0, gap - 0.002) / stretch + clo)
    return T

def loosen(o, hipz, chestz, shx, heavy):
    """the system outfits hug the body like a body suit. a real tee or hoodie hangs from the shoulders and the
    chest and falls in soft vertical folds; jeans sit looser below the knee. push the cloth out along its normals"""
    co, no = coords(o)
    Minv = np.array(o.matrix_world.inverted().to_3x3(), "f4")
    seed = Vector((rng.uniform(0, 100), rng.uniform(0, 100), rng.uniform(0, 100)))
    k = 1.45 if heavy else 1.0
    d = np.zeros(len(co), "f4")
    for i, c in enumerate(co):
        x, y, z = c
        if z > hipz - 0.02:
            hang = min(1.0, max(0.0, (chestz - z) / max(0.05, chestz - hipz)))
            sleeve = abs(x) > shx
            push = (0.007 if sleeve else 0.004 + 0.024 * hang) * k
            fold = noise.noise(Vector((x * 7.0, y * 7.0, z * 1.6)) + seed) * (0.009 if not sleeve else 0.005) * k
            if z > chestz + 0.07 and not sleeve: push *= 0.25; fold *= 0.3          # it rests on the shoulders
        else:
            knee = 1.0 if z < 0.55 else 0.4
            push = 0.004 + 0.006 * knee; fold = noise.noise(Vector((x * 9.0, y * 9.0, z * 3.0)) + seed) * 0.004
        d[i] = push + fold
    disp = (no * d[:, None]) @ Minv.T
    me = o.data; lc = np.empty(len(me.vertices) * 3, "f4"); me.vertices.foreach_get("co", lc)
    me.vertices.foreach_set("co", (lc.reshape(-1, 3) + disp).ravel()); me.update()

def hair_temps(obj, kd, body_T, bvh, thick):
    co, no = coords(obj); T = np.empty(len(co), "f4")
    for i, c in enumerate(co):
        hit = bvh.find_nearest(Vector(c)); d = hit[3] if hit[0] is not None else 0.05
        _, j, _ = kd.find(Vector(c))
        T[i] = T_AIR + (body_T[j] - T_AIR) / (1.0 + d / 0.007 + thick)
    return T

def add_asset(bm, path, kind, sub):
    HumanService.add_mhclo_asset(path, bm, asset_type=kind, subdiv_levels=sub, material_type="MAKESKIN")
    return [o for o in bpy.data.objects if o.parent is not None and o.get("_sb") is None and o.type == "MESH" and o not in _seen][-1]

_seen = set()

def build_person(sex, near, look):
    """build, dress and give temperatures to one person in the rest pose. returns dict of parts"""
    global _seen
    _seen = set(bpy.data.objects)
    p = dict(core=rng.gauss(0, 0.45), nose=rng.uniform(-0.8, 1.6), hands=rng.uniform(-1.6, 1.4))
    macro = TargetService.get_default_macro_info_dict()
    macro.update(gender=1.0 if sex == "m" else 0.0, age=rng.uniform(0.38, 0.6), muscle=rng.uniform(0.35, 0.72),
                 weight=min(0.95, max(0.25, rng.gauss(0.5, 0.14))), height=rng.uniform(0.32, 0.68),
                 proportions=rng.uniform(0.45, 0.85))
    a_ = rng.uniform(0.34, 0.6); af = rng.uniform(0.08, 0.24)
    macro["race"] = {"asian": a_, "african": af, "caucasian": max(0.0, 1 - a_ - af)}
    bm = HumanService.create_human(macro_detail_dict=macro)
    for t in rng.sample(FACE_T, 6):
        f = os.path.join(MPFB_DATA, "targets", t + ".target.gz")
        if os.path.exists(f): TargetService.load_target(bm, f, weight=rng.uniform(0.15, 0.75))
    rig = HumanService.add_builtin_rig(bm, "cmu_mb")
    sub = 1 if near else 0
    parts = {"body": bm, "rig": rig}
    _seen = set(bpy.data.objects)
    HumanService.add_mhclo_asset(os.path.join(PK, "eyes/low-poly/low-poly.mhclo"), bm, asset_type="Eyes", subdiv_levels=0, material_type="MAKESKIN")
    parts["eyes"] = [o for o in bpy.data.objects if o not in _seen]
    eb = f"eyebrow{rng.randint(1, 12):03d}"
    _seen = set(bpy.data.objects)
    HumanService.add_mhclo_asset(os.path.join(PK, f"eyebrows/{eb}/{eb}.mhclo"), bm, asset_type="Eyebrows", subdiv_levels=0, material_type="MAKESKIN")
    parts["brows"] = [o for o in bpy.data.objects if o not in _seen]; parts["brow_name"] = eb
    hair = None if look.get("cap") else rng.choice(HAIR_M if sex == "m" else HAIR_F)
    parts["hair_name"] = hair
    if hair:
        _seen = set(bpy.data.objects)
        HumanService.add_mhclo_asset(os.path.join(PK, f"hair/{hair}/{hair}.mhclo"), bm, asset_type="Hair", subdiv_levels=0, material_type="MAKESKIN")
        parts["hair"] = [o for o in bpy.data.objects if o not in _seen]
    suit = rng.choice(SUIT_M if sex == "m" else SUIT_F)
    _seen = set(bpy.data.objects)
    HumanService.add_mhclo_asset(os.path.join(PK, f"clothes/{suit}/{suit}.mhclo"), bm, asset_type="Clothes", subdiv_levels=sub, material_type="MAKESKIN")
    shoes = f"shoes0{rng.randint(1, 6)}"
    HumanService.add_mhclo_asset(os.path.join(PK, f"clothes/{shoes}/{shoes}.mhclo"), bm, asset_type="Clothes", subdiv_levels=0, material_type="MAKESKIN")
    parts["clothes"] = [o for o in bpy.data.objects if o not in _seen]
    if sub:
        m = bm.modifiers.new("sub", "SUBSURF"); m.levels = 1; m.render_levels = 1
    upd()
    # ---- temperatures, rest pose ----
    T, co, no, lm = skin_temps(bm, p)
    set_attr(bm, "T", T)
    hipz = jpos(rig, "Hips").z
    keep = vg_w(bm, "body") > 0.5
    bv = co[keep]
    kd = KDTree(len(bv))
    for i, c in enumerate(bv): kd.insert(Vector(c), i)
    kd.balance()
    bT = T[keep]
    # a bvh of the visible body surface for distances
    me = bm.data; idx = np.nonzero(keep)[0]; remap = -np.ones(len(co), "i4"); remap[idx] = np.arange(len(idx))
    polys = [tuple(remap[list(pl.vertices)]) for pl in me.polygons if keep[list(pl.vertices)].all()]
    bvh = BVHTree.FromPolygons([Vector(c) for c in bv], polys)
    heavy = rng.random() < 0.3                                         # a hoodie or a jacket over the tee
    chestz = jpos(rig, "LeftArm").z - 0.09; shx = abs(jpos(rig, "LeftArm").x) + 0.04
    for o in parts["clothes"]:
        if "shoes" not in o.name: loosen(o, hipz, chestz, shx, heavy)
    for o in parts["clothes"]:
        if "shoes" in o.name:
            c2, _ = coords(o); set_attr(o, "T", np.full(len(c2), 19.5, "f4") + 0.8 * (c2[:, 2] > 0.06))
        else:
            set_attr(o, "T", cloth_temps(o, bv, bT, kd, bvh, 0.55 if heavy else 0.2, 0.45, hipz))
    for o in parts.get("hair", []):
        thick = {"afro01": 0.9, "long01": 0.55, "bob01": 0.5, "bob02": 0.5, "braid01": 0.45, "ponytail01": 0.4}.get(hair, 0.25)
        set_attr(o, "T", hair_temps(o, kd, bT, bvh, thick))
    for o in parts["eyes"]:
        c2, _ = coords(o); set_attr(o, "T", np.full(len(c2), 34.6 + p["core"], "f4"))
    for o in parts["brows"]:
        c2, _ = coords(o); set_attr(o, "T", np.full(len(c2), 33.2 + p["core"], "f4"))
    # landmarks in the head bone's frame, so they follow the pose
    hb = rig.pose.bones["Head"]; Mi = (rig.matrix_world @ hb.bone.matrix_local).inverted()
    parts["lm"] = {k: Mi @ Vector(v) for k, v in lm.items()}
    parts["p"] = p
    return parts


# =====================================================================================================
# posing
# =====================================================================================================
def set_rolls(rig):
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for b in rig.data.edit_bones:
        if b.name in ROLLS: b.roll = ROLLS[b.name]
    bpy.ops.object.mode_set(mode="OBJECT")

YUP = Matrix.Rotation(math.radians(90), 3, "X")          # the clips are y-up as imported; the people are z-up

TPOSE = {}

def world_rot(a, pb): return (a.matrix_world.to_3x3() @ pb.matrix.to_3x3()).normalized()

def copy_pose(rig, clip, frame):
    """retarget a frame of capture onto a person. each bone turns, in the world, by the same rotation the captured
    bone turned through from the capture's own T pose (frame 1, facing +z in the y-up clip, which is -y here, the
    way the people face at rest): that carries the twist too, so heads and hands turn the right way. then each
    bone is swung the least it takes to point exactly where the captured bone points (the arms rest lower on the
    people than in a T pose)."""
    a = SRC[clip]
    if clip not in TPOSE:
        sc.frame_set(1); TPOSE[clip] = {pb.name: world_rot(a, pb) for pb in a.pose.bones}
    sc.frame_set(frame)
    Y, Yi = YUP, YUP.inverted()
    rest = {b.name: (rig.matrix_world.to_3x3() @ b.matrix_local.to_3x3()).normalized() for b in rig.data.bones}
    for b in rig.data.bones:                                   # parents come before children
        spb = a.pose.bones.get(b.name); pb = rig.pose.bones.get(b.name)
        if spb is None or pb is None: continue
        D = Y @ (world_rot(a, spb) @ TPOSE[clip][b.name].inverted()) @ Yi
        R = D @ rest[b.name]
        h, t = a.matrix_world @ spb.head, a.matrix_world @ spb.tail
        if (t - h).length > 1e-6:
            want = (Y @ (t - h)).normalized(); cur = (R @ Vector((0, 1, 0))).normalized()
            R = cur.rotation_difference(want).to_matrix() @ R
        M = rig.matrix_world @ pb.matrix
        pb.matrix = rig.matrix_world.inverted() @ Matrix.LocRotScale(M.translation, R.to_quaternion(), M.to_scale())
        bpy.context.view_layer.update()

def facing(rig):
    r = jpos(rig, "RightUpLeg") - jpos(rig, "LeftUpLeg"); r.z = 0
    f = Vector((0, 0, 1)).cross(r.normalized()); f.z = 0
    return f.normalized()

def aim(rig, name, target):
    pb = rig.pose.bones[name]; M = rig.matrix_world @ pb.matrix
    cur = (M.to_3x3() @ Vector((0, 1, 0))).normalized(); want = (target - M.translation).normalized()
    R = cur.rotation_difference(want).to_matrix() @ M.to_3x3()
    pb.matrix = rig.matrix_world.inverted() @ Matrix.LocRotScale(M.translation, R.to_quaternion(), M.to_scale())
    upd()

def ik_arm(rig, side, target, pole):
    up, fo = side + "Arm", side + "ForeArm"
    S = jpos(rig, up); a_ = (jpos(rig, up, True) - S).length; b_ = (jpos(rig, side + "Hand") - jpos(rig, fo)).length
    a_ = (jpos(rig, fo) - S).length
    d = min((target - S).length, (a_ + b_) * 0.985); u = (target - S).normalized()
    x = (a_ * a_ - b_ * b_ + d * d) / (2 * d); h = math.sqrt(max(0.0, a_ * a_ - x * x))
    pw = (pole - u * pole.dot(u)); pw = pw.normalized() if pw.length > 1e-6 else Vector((0, 0, -1))
    E = S + u * x + pw * h
    aim(rig, up, E); aim(rig, fo, S + u * d)

def turn_bone(rig, name, axis_world, ang):
    pb = rig.pose.bones[name]; M = rig.matrix_world @ pb.matrix
    R = Quaternion(axis_world, ang).to_matrix() @ M.to_3x3()
    pb.matrix = rig.matrix_world.inverted() @ Matrix.LocRotScale(M.translation, R.to_quaternion(), M.to_scale())
    upd()


# =====================================================================================================
# baking a posed person into one static mesh
# =====================================================================================================
MAT = {}
def temp_material(name, alpha_img=None):
    if name in MAT: return MAT[name]
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N, L = nt.nodes, nt.links
    for n in list(N): N.remove(n)
    out = N.new("ShaderNodeOutputMaterial"); em = N.new("ShaderNodeEmission")
    at = N.new("ShaderNodeAttribute"); at.attribute_type = "GEOMETRY"; at.attribute_name = "T"
    geo = N.new("ShaderNodeNewGeometry")
    def op(kind, a, b):
        n = N.new("ShaderNodeMath"); n.operation = kind
        for i, v in enumerate((a, b)):
            if isinstance(v, (int, float)): n.inputs[i].default_value = v
            else: L.new(v, n.inputs[i])
        return n.outputs[0]
    dot = N.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"
    L.new(geo.outputs["Normal"], dot.inputs[0]); L.new(geo.outputs["Incoming"], dot.inputs[1])
    cosv = op("ABSOLUTE", dot.outputs["Value"], 0)
    # emissivity falls at grazing angles; what is reflected there is the sky above or the crowd and ground below
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(geo.outputs["Normal"], sep.inputs[0])
    up = op("MAXIMUM", sep.outputs["Z"], 0.0)
    trefl = op("ADD", 20.0, op("MULTIPLY", up, T_SKY - 20.0))
    refl = op("MULTIPLY", 0.03 + 0.0, 1.0)
    refl = op("ADD", 0.02, op("MULTIPLY", 0.13, op("POWER", op("SUBTRACT", 1.0, cosv), 3.0)))
    t = op("ADD", at.outputs["Fac"], op("MULTIPLY", refl, op("SUBTRACT", trefl, at.outputs["Fac"])))
    L.new(op("DIVIDE", op("ADD", t, 30.0), 100.0), em.inputs["Strength"]); em.inputs["Color"].default_value = (1, 1, 1, 1)
    sh = em.outputs[0]
    if alpha_img:
        tex = N.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(alpha_img, check_existing=True)
        tex.image.colorspace_settings.name = "Non-Color"
        tr = N.new("ShaderNodeBsdfTransparent"); mx = N.new("ShaderNodeMixShader")
        L.new(tex.outputs["Alpha"], mx.inputs[0]); L.new(tr.outputs[0], mx.inputs[1]); L.new(sh, mx.inputs[2]); sh = mx.outputs[0]
    L.new(sh, out.inputs[0])
    MAT[name] = m
    return m

SOLID = temp_material("solid")

def asset_texture(kind, name):
    d = os.path.join(PK, kind, name)
    for line in open(os.path.join(d, name + ".mhmat")):
        if line.split()[:1] == ["diffuseTexture"]: return os.path.join(d, line.split()[1])
    return None
hair_texture = lambda hn: asset_texture("hair", hn)

def bake(parts):
    dg = bpy.context.evaluated_depsgraph_get()
    objs = [parts["body"]] + parts["eyes"] + parts["brows"] + parts.get("hair", []) + parts["clothes"]
    news = []
    for o in objs:
        ev = o.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
        me.transform(o.matrix_world)
        me.materials.clear()
        if o in parts.get("hair", []):
            hn = parts["hair_name"]; me.materials.append(temp_material("hair_" + hn, hair_texture(hn)))
        elif o in parts["brows"]:
            bn = parts["brow_name"]; me.materials.append(temp_material("brow_" + bn, asset_texture("eyebrows", bn)))
        else:
            me.materials.append(SOLID)
        n = bpy.data.objects.new("part", me); sc.collection.objects.link(n); news.append(n)
    with bpy.context.temp_override(active_object=news[0], selected_editable_objects=news, selected_objects=news):
        bpy.ops.object.join()
    person = news[0]; person.name = "person"
    for o in objs + [parts["rig"]]:
        me = o.data if o.type == "MESH" else None
        bpy.data.objects.remove(o)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    return person

def head_point(rig, local):
    hb = rig.pose.bones["Head"]; return rig.matrix_world @ hb.matrix @ local

def box_mesh(name, center, axes, half, T):
    """an oriented box (a phone, a rail post) with a temperature per corner function T(local)->C"""
    me = bpy.data.meshes.new(name); bmx = bmesh.new()
    vs = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                l = Vector((sx * half[0], sy * half[1], sz * half[2]))
                vs.append((bmx.verts.new(center + axes[0] * l.x + axes[1] * l.y + axes[2] * l.z), l))
    q = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    for f in q: bmx.faces.new([vs[i][0] for i in f])
    bmx.to_mesh(me); bmx.free()
    set_attr_me(me, "T", [T(l) for _, l in vs]); me.materials.append(SOLID)
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); return o

def set_attr_me(me, name, vals):
    me.attributes.new(name, "FLOAT", "POINT").data.foreach_set("value", np.asarray(vals, "f4"))

def glasses(rig, lm, fwd):
    hb = rig.pose.bones["Head"]; M = rig.matrix_world @ hb.matrix
    out = []
    for k in ("eyeL", "eyeR"):
        e = head_point(rig, lm[k])
        f = (M.to_3x3() @ Vector((0, 0, 1))).normalized()          # the head bone's z points forward on cmu_mb? use mouth
        f = (head_point(rig, lm["tip"]) - (head_point(rig, lm["eyeL"]) + head_point(rig, lm["eyeR"])) / 2)
        f = (f - f.project((head_point(rig, lm["mid"]) - head_point(rig, lm["mouth"])).normalized())).normalized()
        upv = (head_point(rig, lm["mid"]) - head_point(rig, lm["mouth"])).normalized()
        side = upv.cross(f).normalized()
        c = e + f * 0.018
        out.append(box_mesh("lens", c, (side, upv, f), (0.026, 0.019, 0.0025), lambda l: 24.5))
    return out


# =====================================================================================================
# the place: barrier, ground, the field behind, the sky
# =====================================================================================================
def solid_box(name, c, half, T):
    return box_mesh(name, Vector(c), (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))), half, lambda l: T)

def place():
    me = bpy.data.meshes.new("ground"); bmx = bmesh.new()
    vs = [bmx.verts.new(v) for v in ((-80, -2, 0), (80, -2, 0), (80, 140, 0), (-80, 140, 0))]
    bmx.faces.new(vs); bmx.to_mesh(me); bmx.free(); set_attr_me(me, "T", [T_GROUND] * 4); me.materials.append(SOLID)
    g = bpy.data.objects.new("ground", me); sc.collection.objects.link(g)
    # the barrier: a steel crowd barrier, the solid face toward the stage, people leaning on the top bar.
    # galvanised steel reads cold, it mirrors the sky; the top bar is warmer where hands and chests rest on it
    solid_box("barrier_face", (0, 1.72, 0.58), (18, 0.012, 0.58), 6.5)
    solid_box("barrier_top", (0, 1.80, 1.17), (18, 0.05, 0.035), 11.0)
    for x in np.arange(-18, 18.01, 1.0):
        solid_box("brace", (x, 1.95, 0.55), (0.02, 0.22, 0.02), 8.0)
        solid_box("foot", (x, 2.05, 0.015), (0.04, 0.35, 0.015), 13.0)
    # front of house: a scaffold riser under a tarp roof, the desks and their screens warm, the crew in shadow
    fx, fy = -3.0, 33.0
    solid_box("foh_riser", (fx, fy, 0.35), (3.6, 2.8, 0.35), 15.5)
    for dx in (-3.5, -1.2, 1.2, 3.5):
        for dy in (-2.7, 2.7):
            solid_box("foh_pole", (fx + dx, fy + dy, 2.4), (0.024, 0.024, 2.4), 8.5)
    me = bpy.data.meshes.new("foh_roof"); bmx = bmesh.new()
    rv = [bmx.verts.new(v) for v in ((fx - 4, fy - 3.2, 5.0), (fx + 4, fy - 3.2, 5.0), (fx + 4, fy + 3.2, 4.4), (fx - 4, fy + 3.2, 4.4))]
    bmx.faces.new(rv); bmx.to_mesh(me); bmx.free(); set_attr_me(me, "T", [4.5, 4.5, 6.0, 6.0]); me.materials.append(SOLID)
    o = bpy.data.objects.new("foh_roof", me); sc.collection.objects.link(o)
    solid_box("foh_back", (fx, fy + 2.75, 2.6), (3.7, 0.01, 1.9), 9.0)
    for k, dx in enumerate((-2.4, -0.6, 1.4)):
        solid_box("desk", (fx + dx, fy - 1.0, 1.2), (0.75, 0.45, 0.08), 21.0 + k)
        solid_box("screen", (fx + dx, fy - 0.7, 1.55), (0.3, 0.01, 0.2), 33.0 + rng.uniform(-2, 2))
    for k in range(26):
        x = -60 + k * 4.8 + rng.uniform(-1.5, 1.5); hgt = rng.uniform(7, 15)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=rng.uniform(3, 5.5), location=(x, 75 + rng.uniform(-6, 6), hgt))
        t = bpy.context.object; t.scale.z = rng.uniform(0.7, 1.0)
        c2 = np.array([t.matrix_world @ v.co for v in t.data.vertices])
        set_attr_me(t.data, "T", 14.6 + 1.0 * (c2[:, 2] < hgt - 1.5) + np.array([noise.noise(Vector(v) * 0.4) for v in c2]))
        t.data.materials.append(SOLID)
        solid_box("trunk", (x, t.location.y, hgt / 2 - 1), (0.25, 0.25, hgt / 2 - 1), 15.5)


# =====================================================================================================
# the crowd
# =====================================================================================================
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
# from the stage, 4.2 m up, looking down into the crowd: a field of heads and hands, cut at the bottom of the frame,
# the far crowd going soft into the night (the look the first breath had, with real people in it)
cam.location = (0.4, -0.1, 4.2); cam.data.lens = 34; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
look_at = Vector((-0.3, 11.5, 1.0))
q = (look_at - cam.location).to_track_quat("-Z", "Y")
cam.rotation_euler = (q @ Quaternion((0, 0, 1), math.radians(1.6))).to_euler()   # a hand-held tilt
cam.data.dof.use_dof = True; cam.data.dof.focus_distance = 8.0; cam.data.dof.aperture_fstop = 2.4
sc.render.resolution_x, sc.render.resolution_y = W, H
upd()

def in_view(p, margin=0.08):
    v = world_to_camera_view(sc, cam, Vector(p))
    return -margin < v.x < 1 + margin and -margin < v.y < 1.25 and v.z > 0

# positions: dart throwing, closer together further back (people press toward the front too)
spots = []
grid = {}
def ok(x, y, r):
    gx, gy = int(x / 0.6), int(y / 0.6)
    for i in range(gx - 2, gx + 3):
        for j in range(gy - 2, gy + 3):
            for (a, b) in grid.get((i, j), []):
                if (a - x) ** 2 + (b - y) ** 2 < r * r: return False
    return True
FRONT = 2.12
for k in range(60000):
    y = FRONT + (rng.random() ** 1.25) * 52
    x = rng.uniform(-3 - y * 0.62, 3 + y * 0.62)
    r = 0.43 + 0.15 * min(1, (y - FRONT) / 30)
    if y < FRONT + 0.25: x = round(x / 0.5) * 0.5 + rng.uniform(-0.08, 0.08)
    if not in_view((x, y, 1.6)) or not ok(x, y, r): continue
    spots.append((x, y)); grid.setdefault((int(x / 0.6), int(y / 0.6)), []).append((x, y))
spots.sort(key=lambda s: s[1])
log("spots", len(spots))

def pick_pose(kind):
    lst = BANK[kind] or BANK["mid"] or BANK["low"]
    return rng.choice(lst)

KINDS = [("up2", 0.34), ("up1", 0.2), ("mid", 0.16), ("air", 0.12), ("low", 0.1), ("film", 0.08)]
def pick_kind():
    x = rng.random()
    for k, w in KINDS:
        if x < w: return k
        x -= w
    return "low"

place()
people, lib, mouths = [], [], []
near = [s for s in spots if 3.3 < s[1] < 13]          # the nearest people the camera sees whole enough to matter
plan = []
for i, (x, y) in enumerate(near[:UNIQUE]):
    plan.append(dict(x=x, y=y, sex="m" if rng.random() < 0.56 else "f", kind=pick_kind(), near=True))
# friends: an arm round the shoulder of the one beside them
for i in range(1, len(plan)):
    a, b = plan[i - 1], plan[i]
    if abs(a["y"] - b["y"]) < 0.45 and abs(a["x"] - b["x"]) < 0.75 and rng.random() < 0.3 and "hold" not in a:
        b["hold"] = i - 1
# one on a friend's shoulders, mid-crowd
cand = [i for i, p in enumerate(plan) if 4.5 < p["y"] < 8.5] or [len(plan) - 1]
riders = rng.sample(cand, min(1, len(cand))) if cand else []
for i in riders: plan[i]["carry"] = True; plan[i]["sex"] = "m"

T_FILM = lambda l: 27.0 + 9.0 * max(0.0, (l.y / 0.075 + 1) / 2) ** 2   # hottest at the camera end (the top)
built = []

def ground_lo(parts):
    dg = bpy.context.evaluated_depsgraph_get(); ev = parts["body"].evaluated_get(dg); me = ev.to_mesh()
    lo = min((parts["body"].matrix_world @ v.co).z for v in me.vertices); ev.to_mesh_clear(); return lo

def pose_one(parts, pl, kind, fw_want=None):
    rig = parts["rig"]
    clip, frame, lift = pick_pose("mid" if kind == "film" else kind)
    copy_pose(rig, clip, frame)
    # face the stage, a little either way; some turned to a friend
    want = fw_want or (Vector((rng.uniform(-2, 2), -2, 0)) - Vector((pl["x"], pl["y"], 0)))
    want = Vector((want.x, want.y, 0)).normalized()
    if fw_want is None and rng.random() < 0.08: want = Quaternion((0, 0, 1), rng.choice((-1, 1)) * rng.uniform(1.0, 1.9)) @ want
    f = facing(rig); ang = math.atan2(want.y, want.x) - math.atan2(f.y, f.x)
    rig.rotation_euler.z += ang + (0 if fw_want else rng.gauss(0, 0.12)); upd()
    rig.location.x += pl["x"] - jpos(rig, "Hips").x; rig.location.y += pl["y"] - jpos(rig, "Hips").y; upd()
    fw = facing(rig); rt = fw.cross(Vector((0, 0, 1)))
    if rng.random() < 0.22: turn_bone(rig, "Neck1", rt, -rng.uniform(0.25, 0.45))        # singing, head back
    return dict(clip=clip, frame=frame, lift=lift, fw=fw, rt=rt)

def stand(parts, kind, lift):
    rig = parts["rig"]; rig.location.z += -ground_lo(parts) + (lift * 1.7 if kind == "air" else 0.0); upd()

def finish(parts, look, extra):
    if look.get("glasses"): extra = extra + glasses(parts["rig"], parts["lm"], facing(parts["rig"]))
    person = bake(parts)
    for e in extra:
        with bpy.context.temp_override(active_object=person, selected_editable_objects=[person, e], selected_objects=[person, e]):
            bpy.ops.object.join()
    return person

for i, pl in enumerate(plan):
    look = {"cap": rng.random() < 0.12, "glasses": rng.random() < 0.18}
    kind = "low" if pl.get("carry") else pl["kind"]
    parts = build_person(pl["sex"], True, look); rig = parts["rig"]
    ps = pose_one(parts, pl, kind); fw, rt = ps["fw"], ps["rt"]
    extra = []
    if kind == "film":
        side = rng.choice(("Left", "Right"))
        tgt = jpos(rig, "Head") + fw * 0.34 + Vector((0, 0, 0.12)) + rt * (0.05 if side == "Right" else -0.05)
        ik_arm(rig, side, tgt, Vector((0, 0, -1)) + rt * (0.6 if side == "Right" else -0.6))
    if "hold" in pl and built:
        fr = built[pl["hold"]]
        side = "Left" if fr["x"] < pl["x"] else "Right"
        ik_arm(rig, side, (fr["shL"] if side == "Left" else fr["shR"]) + Vector((0, 0, 0.05)), Vector((0, 0, -1)) - fw * 0.5)
    stand(parts, kind, ps["lift"])
    rider = None
    if pl.get("carry"):
        # someone up on his shoulders: her thighs over his collarbones, her shins down his chest, his hands on her shins
        rl = {"cap": False, "glasses": False}
        rp = build_person("f", True, rl); rr = rp["rig"]
        pose_one(rp, pl, "up2", fw_want=fw)
        seat = jpos(rig, "Neck") + Vector((0, 0, 0.11)) - fw * 0.03
        rr.location += seat - jpos(rr, "Hips"); upd()
        for s_, sg in (("Left", -1), ("Right", 1)):
            hip = jpos(rr, s_ + "UpLeg")
            th = (fw * 0.72 + rt * sg * 0.42 + Vector((0, 0, -0.3))).normalized()
            L1 = (jpos(rr, s_ + "Leg") - hip).length; aim(rr, s_ + "UpLeg", hip + th * L1)
            kn = jpos(rr, s_ + "Leg"); aim(rr, s_ + "Leg", kn + (Vector((0, 0, -1)) + fw * 0.12).normalized())
        for s_ in ("Left", "Right"):
            shin = (jpos(rr, s_ + "Leg") * 0.45 + jpos(rr, s_ + "Foot") * 0.55)
            sg = -1 if s_ == "Left" else 1
            ik_arm(rig, s_, shin + fw * 0.05, Vector((0, 0, -1)) + rt * sg * 0.8)
        rider = rp
    rec = dict(x=pl["x"], y=pl["y"], shL=jpos(rig, "LeftArm") + Vector((0, 0, 0.04)), shR=jpos(rig, "RightArm") + Vector((0, 0, 0.04)),
               mouth=head_point(rig, parts["lm"]["mouth"]), fwd=fw)
    if kind == "film":
        hb = rig.pose.bones[side + "Hand"]
        c = (rig.matrix_world @ hb.tail) + fw * 0.02 + Vector((0, 0, 0.04))
        extra.append(box_mesh("phone", c, (rt, Vector((0, 0, 1)), fw), (0.036, 0.075, 0.004), T_FILM))
    extras_r = []
    if rider:
        rec["mouth2"] = head_point(rider["rig"], rider["lm"]["mouth"])
        rider_obj = finish(rider, rl, [])
        extras_r = [rider_obj]
    person = finish(parts, look, extra + extras_r)
    rec["obj"] = person; built.append(rec); lib.append(person)
    mouths.append(rec["mouth"])
    if "mouth2" in rec: mouths.append(rec["mouth2"])
    log("person", i, pl["sex"], kind, ps["clip"], ps["frame"], len(person.data.vertices), "carry" if rider else "")

# the crowd further back: the same people again, turned and mirrored, never side by side
for (x, y) in spots[len(plan):]:
    if y < 9.5 and len(plan) >= len(near): pass
    src = rng.choice([b["obj"] for b in built if "mouth2" not in b] or lib)
    o = src.copy(); sc.collection.objects.link(o)
    sx = rng.choice((1, -1)); o.scale = (sx, 1, 1)
    # src is baked in world space around its own spot: move it to the new one about its feet
    bx, by = src.matrix_world.translation.x, src.matrix_world.translation.y
    me_c = [b for b in built if b["obj"] is src][0]
    ang = rng.gauss(0, 0.25)
    piv = Vector((me_c["x"], me_c["y"], 0))
    Mv = Matrix.Translation(Vector((x, y, 0))) @ Matrix.Rotation(ang, 4, "Z") @ Matrix.Diagonal((sx, 1, 1, 1)) @ Matrix.Translation(-piv)
    o.matrix_world = Mv
    mouths.append(Mv @ me_c["mouth"])
    if "mouth2" in me_c: mouths.append(Mv @ me_c["mouth2"])
log("crowd", len(spots), "unique", len(lib))

# =====================================================================================================
# render the temperatures
# =====================================================================================================
sc.world = bpy.data.worlds.new("sky"); sc.world.use_nodes = True
bg = sc.world.node_tree.nodes["Background"]; bg.inputs[0].default_value = (1, 1, 1, 1); bg.inputs[1].default_value = (T_SKY + 30) / 100
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = SPP; sc.cycles.use_denoising = False
sc.cycles.max_bounces = 0; sc.cycles.transparent_max_bounces = 12; sc.cycles.filter_width = 1.2
sc.render.threads_mode = "FIXED"; sc.render.threads = int(os.environ.get("THREADS", os.cpu_count() or 2))
sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
sc.render.image_settings.file_format = "OPEN_EXR"; sc.render.image_settings.color_depth = "32"
sc.render.filepath = os.path.join(OUT, "temp.exr")
upd()
vis = []
for m in mouths:
    v = world_to_camera_view(sc, cam, m)
    if 0 <= v.x <= 1 and 0 <= v.y <= 1 and v.z > 0:
        v2 = world_to_camera_view(sc, cam, m + Vector((0, 0, 1)))
        vis.append({"u": v.x, "v": 1 - v.y, "depth": v.z, "px_per_m": abs(v2.y - v.y) * H})
json.dump({"w": W, "h": H, "mouths": vis, "people": len(spots), "unique": len(lib)}, open(os.path.join(OUT, "scene.json"), "w"))
log("render", W, H, SPP)
bpy.ops.render.render(write_still=True)
ex = bpy.data.images.load(sc.render.filepath); px = np.empty(W * H * 4, "f4"); ex.pixels.foreach_get(px)
T = px.reshape(H, W, 4)[::-1, :, 0] * 100 - 30
np.save(os.path.join(OUT, "temp.npy"), T.astype("f2"))
log("done", float(T.min()), float(T.max()))
