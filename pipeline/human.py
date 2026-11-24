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
import bpy, bmesh, sys, math
from mathutils import Vector, Matrix, Quaternion, noise
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

a = sys.argv[sys.argv.index("--") + 1:]
BODY, TEE, OUT = a[0], a[1], a[2]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

with bpy.data.libraries.load(BODY) as (src, dst):
    dst.objects = [n for n in src.objects if n in ("body", "rig")]
for o in dst.objects: sc.collection.objects.link(o)
body, rig = bpy.data.objects["body"], bpy.data.objects["rig"]
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
wt = lambda i, name: W[i].get(VG[name], 0.0) if name in VG else 0.0
joint = lambda name: sum((P[i] for i in range(len(P)) if wt(i, name) > 0.5), Vector()) / max(1, sum(1 for i in range(len(P)) if wt(i, name) > 0.5))

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


def covered(c, n):
    if kd_open.find(c)[2] < 0.07: return False                 # near an opening it can be seen
    t1, t2 = n.orthogonal().normalized(), None
    t2 = n.cross(t1)
    for d in (n, (n + t1 * 0.85).normalized(), (n - t1 * 0.85).normalized(), (n + t2 * 0.85).normalized(), (n - t2 * 0.85).normalized()):
        hit = tee_bvh.ray_cast(c + n * 0.002, d, 0.2)
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
LEG = [VG[g] for g in VG if g.startswith(("pelvis.", "upperleg", "lowerleg", "foot.", "toe"))] + [VG["root"]]
leg = lambda i: sum(W[i].get(g, 0.0) for g in LEG)


def is_skin(f):
    ix = [v.index for v in f.verts]
    if not all(wt(i, "body") > 0.5 for i in ix): return False
    if all(P[i].z < CUT and leg(i) > 0.5 for i in ix): return False     # inside the jeans
    c = sum((P[i] for i in ix), Vector()) / len(ix)
    n = (P[ix[1]] - P[ix[0]]).cross(P[ix[2]] - P[ix[0]]).normalized()
    return not covered(c, n) and not poking(c, n)


skin, SRC = part("skin", is_skin)
skin.normal_update()
print("skin faces", len(skin.faces), "settled", settle(skin, CUT + 0.15), flush=True)
# painted skin, linear albedo
BASE = Vector((0.26, 0.14, 0.085))           # an even Indian brown
lipsC = Vector((0.19, 0.075, 0.062)); hairC = Vector((0.011, 0.009, 0.008)); palmC = Vector((0.46, 0.29, 0.2))
nailC = Vector((0.5, 0.33, 0.27))
eyeL, eyeR = joint("joint-l-eye"), joint("joint-r-eye"); mouth = joint("joint-mouth"); jaw = joint("joint-jaw")
head = joint("joint-head")
print("eyes", round(eyeL.z, 3), "mouth", round(mouth.z, 3), flush=True)
fwd = Vector((0, -1, 0))
lay = skin.verts.layers.float_color.new("albedo") if hasattr(skin.verts.layers, "float_color") else None
skin.normal_update()


def smooth(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t)


for v in skin.verts:
    i, p, n = v[SRC], v.co, v.normal
    c = BASE.copy()
    # slow mottle: a few percent in value and warmth, never a texture you can see
    m1 = noise.noise(p * 9.0); m2 = noise.noise(p * 23.0 + Vector((3, 1, 7)))
    c *= 1.0 + 0.06 * m1 + 0.025 * m2
    c.x *= 1.0 + 0.03 * noise.noise(p * 14 + Vector((9, 2, 4)))
    # warmer where blood is near the surface: ears, nose tip, cheeks a touch, knuckles
    c = c.lerp(Vector((0.3, 0.13, 0.09)), 0.5 * wt(i, "ears"))
    c = c.lerp(lipsC, smooth(0.15, 0.7, wt(i, "lips")))
    c = c.lerp(nailC, smooth(0.2, 0.8, wt(i, "fingernails")))
    # palms and the inside of the fingers are much lighter than the back of the hand
    hand = max(wt(i, g) for g in [f"{b}.{s}" for s in ("L", "R") for b in ("wrist", "metacarpal1", "metacarpal2", "metacarpal3", "metacarpal4",
               "finger1-1", "finger1-2", "finger1-3", "finger2-1", "finger2-2", "finger2-3", "finger3-1", "finger3-2", "finger3-3",
               "finger4-1", "finger4-2", "finger4-3", "finger5-1", "finger5-2", "finger5-3")] if g in VG)
    if hand > 0.3:
        palm = smooth(0.15, 0.6, n.dot(Vector((-math.copysign(1, p.x), 0, 0))))
        c = c.lerp(palmC, 0.75 * palm * smooth(0.3, 0.8, hand))
    # the head: buzz cut, brows, a close beard shadow
    if p.z > mouth.z - 0.12 and abs(p.x) < 0.13:
        # hairline: MakeHuman's scalp group, firmed up, carried down the back of the head to the nape
        # (behind the ears, above the mouth line) as a short fade
        behind = smooth(0.0, 0.04, p.y - (eyeL.y + 0.07))           # past the ears, toward the back
        nape = smooth(mouth.z - 0.03, mouth.z + 0.02, p.z)
        hair = max(smooth(0.2, 0.55, wt(i, "scalp")), behind * nape) * (1 - smooth(0.1, 0.4, wt(i, "ears")))
        front = smooth(0.2, 0.5, n.dot(fwd))
        # brows: two soft bands just above each eye
        for e in (eyeL, eyeR):
            d = p - e
            brow = smooth(0.012, 0.022, d.z) * (1 - smooth(0.026, 0.034, d.z)) * (1 - smooth(0.025, 0.04, abs(d.x - math.copysign(0.004, e.x)))) * front
            c = c.lerp(hairC * 2.0, 0.85 * brow)
        # beard shadow: chin, jaw line and upper lip, not the lips, not the cheeks high up
        if p.z < eyeL.z - 0.045 and p.z > jaw.z - 0.11:
            onface = smooth(-0.2, 0.25, n.dot(fwd) + 0.3 * smooth(0.0, 0.05, mouth.z - p.z))
            upper = 1 - smooth(eyeL.z - 0.085, eyeL.z - 0.055, p.z) * smooth(0.025, 0.045, abs(p.x))   # stays off the cheekbones
            lip_side = 1 - smooth(0.1, 0.4, wt(i, "lips"))
            beard = onface * upper * lip_side * smooth(0.0, 0.03, p.y - (mouth.y - 0.05))
            c = c.lerp(Vector((0.035, 0.022, 0.016)), 0.55 * beard)
        c = c.lerp(hairC * (1.0 + 0.15 * noise.noise(p * 300)), 0.92 * hair)
    if lay: v[lay] = (c.x, c.y, c.z, 1.0)

# ---------- jeans: the tights helper, loosened and smoothed ----------
def is_jeans(f):
    ix = [v.index for v in f.verts]
    # the tights helper is a whole bodysuit: only its legs, below the waist
    if not all(wt(i, "helper-tights") > 0.5 and leg(i) > 0.5 and P[i].z < CUT + 0.02 for i in ix): return False
    # inflated as the jeans will be, nothing under the tee and nothing through it
    c = sum((P[i] for i in ix), Vector()) / len(ix)
    n = (P[ix[1]] - P[ix[0]]).cross(P[ix[2]] - P[ix[0]]).normalized()
    c = c + n * 0.012
    return not covered(c, n) and not poking(c, n)


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
eyes, _ = part("eyes", lambda f: all(wt(v.index, "helper-l-eye") > 0.5 or wt(v.index, "helper-r-eye") > 0.5 for v in f.verts))
el = eyes.verts.layers.float_color.new("albedo")
for v in eyes.verts:
    e = eyeL if v.co.x > 0 else eyeR
    d = (v.co - e).normalized().dot(fwd)
    c = Vector((0.62, 0.56, 0.5)).lerp(Vector((0.05, 0.022, 0.012)), smooth(0.9, 0.93, d)).lerp(Vector((0.004, 0.004, 0.004)), smooth(0.975, 0.985, d))
    v[el] = (c.x, c.y, c.z, 1.0)


# ---------- out ----------
def obj(name, b):
    m = bpy.data.meshes.new(name); b.to_mesh(m); b.free()
    if m.validate(verbose=False): print("fixed", name)
    for p in m.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, m); sc.collection.objects.link(o)
    mat = bpy.data.materials.new(name); m.materials.append(mat)
    if m.color_attributes: m.color_attributes.active_color = m.color_attributes[0]
    s = o.modifiers.new("sub", "SUBSURF"); s.levels = 1; s.render_levels = 1
    return o


outs = [obj("skin", skin), obj("jeans", jeans), obj("eyes", eyes)]
for o in list(sc.objects):
    if o not in outs: bpy.data.objects.remove(o)
for o in outs: o.select_set(True)
args = dict(filepath=OUT, use_selection=True, export_apply=True, export_yup=True, export_materials="EXPORT",
            export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7, export_vertex_color="NAME", export_vertex_color_name="albedo", export_all_vertex_colors=False,
            export_skins=False, export_animations=False, export_morph=False)
bpy.ops.export_scene.gltf(**args)
print("saved", OUT, {o.name: len(o.data.polygons) for o in outs})
