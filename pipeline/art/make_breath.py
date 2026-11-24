# 03 breath (Bengaluru, black): the crowd as a thermal camera on the stage sees it. Part 1 of 2, runs in Blender:
#   blender -b --factory-startup -P art/make_breath.py -- <outdir> [W H samples]
# Builds a crowd from the five simulated Indian bodies (bodies/*.blend), poses every one (hands up, one hand up,
# a phone up, arms down), and renders a TEMPERATURE image: each pixel's value is how warm that surface reads
# (skin hot, cotton and denim cooler, hair cooler, grazing angles cooler, far rows cooler through the air).
# Also writes every mouth's position on the image, so part 2 (breath_post.py) can draw each breath.
import bpy, sys, os, math, json, random
from mathutils import Vector, Euler, Quaternion
from bpy_extras.object_utils import world_to_camera_view

A = sys.argv[sys.argv.index("--") + 1:]
OUT = A[0]; W = int(A[1]) if len(A) > 1 else 1500; H = int(A[2]) if len(A) > 2 else 2000
SPP = int(A[3]) if len(A) > 3 else 24
os.makedirs(OUT, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__)); BODIES = os.path.join(HERE, "..", "bodies")
rng = random.Random(1213)   # 12 + 13 December

sc = bpy.context.scene
for o in list(bpy.data.objects): bpy.data.objects.remove(o)

# ---------- the five bodies ----------
src = []
for name in ("m163", "m170", "m177", "f155", "f162"):
    with bpy.data.libraries.load(os.path.join(BODIES, f"{name}.blend")) as (df, dt):
        dt.objects = [n for n in df.objects if n in ("body", "rig")]
    objs = {o.name.split(".")[0]: o for o in dt.objects}
    body, rig = objs["body"], objs["rig"]
    body.name, rig.name = f"src_{name}", f"srcrig_{name}"
    bones = rig.data.bones; zs = [v.co.z for v in body.data.vertices]
    src.append(dict(name=name, body=body, rig=rig,
                    hip=bones["upperleg01.L"].head_local.z, sh=bones["upperarm01.L"].head_local.z,
                    top=max(zs), half=abs(bones["upperarm01.L"].head_local.x) - 0.02))
    # what each patch of skin is wearing, painted once in the rest pose so it moves with the arms:
    # an oversized cotton tee (torso to the base of the neck, sleeves ending above the elbow), jeans, shoes,
    # hair on the crown, and the nose tip (always the coolest part of a face on a thermal camera)
    import numpy as np
    co = np.array([v.co for v in body.data.vertices]); x, y, z = co[:, 0], co[:, 1], co[:, 2]
    hip = bones["upperleg01.L"].head_local.z; neck = bones["neck01"].head_local.z
    sL = np.array(bones["upperarm01.L"].head_local); eL = np.array(bones["lowerarm01.L"].head_local)
    def along(sh, el):
        d = el - sh; L = np.linalg.norm(d); return ((co - sh) @ (d / L)) / L
    sR = sL * np.array([-1, 1, 1]); eR = eL * np.array([-1, 1, 1])
    side = np.where(x >= 0, along(sL, eL), along(sR, eR))
    on_arm = np.abs(x) > abs(sL[0]) - 0.01
    base = np.full(len(co), 1.0)                                            # skin
    base[(z < hip + 0.02)] = 0.4                                            # jeans
    base[z < 0.08] = 0.3                                                    # shoes
    sh_z = bones["upperarm01.L"].head_local.z
    tee = (z >= hip - 0.07) & (((z < neck + 0.035) & ~on_arm) | (on_arm & (side < 0.62) & (z < sh_z + 0.12)))
    base[tee] = 0.52
    head = z > neck + 0.06
    base[head & (z > max(zs) - 0.08) & (y > np.percentile(y[head], 30))] = 0.62      # hair, crown and back
    front = head & (z < max(zs) - 0.1)
    if front.any():
        nose = front & (y < np.percentile(y[front], 2.5))
        base[nose] = 0.8
    a = body.data.attributes.new("base", "FLOAT", "POINT"); a.data.foreach_set("value", base.astype("f4"))

# ---------- temperature material ----------
def temp_material():
    m = bpy.data.materials.new("temp"); m.use_nodes = True; nt = m.node_tree; N, L = nt.nodes, nt.links
    for n in list(N): N.remove(n)
    out = N.new("ShaderNodeOutputMaterial"); em = N.new("ShaderNodeEmission"); L.new(em.outputs[0], out.inputs[0])
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    def attr(nm):
        a = N.new("ShaderNodeAttribute"); a.attribute_type = "OBJECT"; a.attribute_name = nm; return a.outputs["Fac"]
    def op(kind, a, b):
        n = N.new("ShaderNodeMath"); n.operation = kind
        for i, v in enumerate((a, b)):
            if isinstance(v, (int, float)): n.inputs[i].default_value = v
            else: L.new(v, n.inputs[i])
        return n.outputs[0]
    def mix(fac, a, b):   # fac ? b : a
        n = N.new("ShaderNodeMix"); n.data_type = "FLOAT"
        for sock, v in ((n.inputs[0], fac), (n.inputs[2], a), (n.inputs[3], b)):
            if isinstance(v, (int, float)): sock.default_value = v
            else: L.new(v, sock)
        return n.outputs[0]
    base = N.new("ShaderNodeAttribute"); base.attribute_type = "GEOMETRY"; base.attribute_name = "base"
    warm = attr("warm")                                            # people differ a little
    t = base.outputs["Fac"]
    t = op("MULTIPLY", t, warm)
    # a surface seen edge-on reads cooler (emissivity falls off at grazing angles)
    lw = N.new("ShaderNodeLayerWeight"); lw.inputs[0].default_value = 0.5
    t = op("MULTIPLY", t, op("ADD", 0.58, op("MULTIPLY", op("POWER", op("SUBTRACT", 1, lw.outputs["Facing"]), 0.7), 0.42)))
    # the air between: far rows read cooler
    cam = N.new("ShaderNodeCameraData")
    t = op("MULTIPLY", t, op("ADD", 0.62, op("MULTIPLY", 0.38, op("EXPONENT", op("DIVIDE", cam.outputs["View Distance"], -16), 0))))
    L.new(t, em.inputs["Strength"]); em.inputs["Color"].default_value = (1, 1, 1, 1)
    return m
TEMP = temp_material()
for s in src:
    s["body"].data.materials.clear(); s["body"].data.materials.append(TEMP)

# ---------- poses ----------
def aim(rig, bone, world_dir):
    """Point a bone along a direction given in the rig's own space."""
    pb = rig.pose.bones[bone]; bn = pb.bone
    end = {"upperarm01": "upperarm02", "lowerarm01": "lowerarm02"}[bone.split(".")[0]] + "." + bone.split(".")[1]
    full = (rig.data.bones[end].tail_local - bn.head_local).normalized()
    q = full.rotation_difference(Vector(world_dir).normalized()); R = bn.matrix_local.to_quaternion()
    pb.rotation_mode = "QUATERNION"; pb.rotation_quaternion = R.inverted() @ q @ R
def arm(rig, side, d):
    s = 1 if side == "L" else -1; aim(rig, "upperarm01." + side, (s * d[0], d[1], d[2]))
POSES = {   # (left, right) upper-arm directions in body space (x out to the side, -y forward, z up)
    "both_up": lambda r: ((r.uniform(0.25, 0.5), r.uniform(-0.25, 0.05), 1), (r.uniform(0.25, 0.5), r.uniform(-0.25, 0.05), 1)),
    "one_up": lambda r: ((r.uniform(0.15, 0.4), r.uniform(-0.3, 0), 1), (0.35, 0.02, -1)),
    "phone": lambda r: ((0.12, -0.75, r.uniform(0.35, 0.7)), (0.35, 0.02, -1)),
    "down": lambda r: ((0.33, 0.0, -1), (0.33, 0.02, -1)),
}
WEIGHTS = [("both_up", 0.42), ("one_up", 0.24), ("phone", 0.14), ("down", 0.2)]
def pick(r):
    x = r.random()
    for k, w in WEIGHTS:
        if x < w: return k
        x -= w
    return "down"

# ---------- the crowd: rows from the barrier back, facing the stage (+y is toward the stage) ----------
people = []
for row in range(18):
    y = 5.2 + row * 0.6 + rng.uniform(-0.12, 0.12)
    halfw = 2.8 + row * 0.55
    x = -halfw + rng.uniform(0, 0.45)
    while x < halfw:
        s = rng.choice(src)
        rig = s["rig"].copy(); body = s["body"].copy(); sc.collection.objects.link(rig); sc.collection.objects.link(body)
        body.parent = rig; body.modifiers["Armature"].object = rig
        rig.location = (x, y, 0); rig.rotation_euler = (0, 0, rng.uniform(-0.35, 0.35))   # bodies face -y, the stage
        k = rng.uniform(0.97, 1.03); rig.scale = (k, k, k)
        L_, R_ = POSES[pick(rng)](rng)
        if rng.random() < 0.5: L_, R_ = R_, L_
        arm(rig, "L", L_); arm(rig, "R", R_)
        for key in ("hip", "sh", "top", "half"): body[key] = s[key]
        body["warm"] = rng.uniform(0.93, 1.04)
        people.append((rig, s)); x += rng.uniform(0.5, 0.68)

# the ground: trampled grass at night, a little warmer than the air
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0)); g = bpy.context.object
gm = bpy.data.materials.new("ground"); gm.use_nodes = True; e = gm.node_tree.nodes.new("ShaderNodeEmission")
e.inputs["Strength"].default_value = 0.14; gm.node_tree.links.new(e.outputs[0], gm.node_tree.nodes["Material Output"].inputs[0])
g.data.materials.append(gm)

# ---------- camera: on the stage lip, 3.4 m up, looking down into the crowd ----------
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0.4, 0.2, 4.2); cam.data.lens = 34; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.rotation_euler = (Vector((0, 11.5, 1.0)) - cam.location).to_track_quat("-Z", "Y").to_euler()

sc.world = bpy.data.worlds.new("w"); sc.world.use_nodes = True; sc.world.node_tree.nodes["Background"].inputs[1].default_value = 0
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = SPP; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 0; sc.render.threads_mode = "FIXED"; sc.render.threads = int(os.environ.get("THREADS", 3))
sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.image_settings.file_format = "OPEN_EXR"; sc.render.image_settings.color_depth = "32"
sc.view_layers[0].use_pass_z = True
sc.render.image_settings.use_preview = False
sc.render.filepath = os.path.join(OUT, "temp.exr")
bpy.context.view_layer.update()

# mouths on the image, for the breath
mouths = []
for rig, s in people:
    hb = rig.pose.bones["head"]; head = rig.matrix_world @ hb.head; up = (rig.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
    fwd = (rig.matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
    m = head + fwd * 0.1 - up * 0.03
    p = world_to_camera_view(sc, cam, m); p2 = world_to_camera_view(sc, cam, m + up * 1.0)
    if 0 <= p.x <= 1 and 0 <= p.y <= 1 and p.z > 0:
        mouths.append({"u": p.x, "v": 1 - p.y, "depth": (m - cam.location).length, "px_per_m": abs(p2.y - p.y) * H,
                       "fx": (world_to_camera_view(sc, cam, m + fwd * 0.3).x - p.x) * W})
json.dump({"w": W, "h": H, "mouths": mouths, "people": len(people)}, open(os.path.join(OUT, "mouths.json"), "w"))
print("people", len(people), "mouths", len(mouths), flush=True)
bpy.ops.render.render(write_still=True)
# hand the temperatures to part 2 as a plain numpy array (no EXR reader needed outside Blender)
import numpy as np
ex = bpy.data.images.load(sc.render.filepath); px = np.empty(W * H * 4, "f4"); ex.pixels.foreach_get(px)
np.save(os.path.join(OUT, "temp.npy"), px.reshape(H, W, 4)[::-1, :, 0].copy())
print("saved", sc.render.filepath, flush=True)
