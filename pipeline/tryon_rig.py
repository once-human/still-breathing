# Try-on rig: the tee as it hangs on a real body, skinned to that body's skeleton like a game character.
# The m170 body (MakeHuman/MPFB, default rig) is posed as it stood in the fit simulation (arms 64 deg below the
# horizon), the skeleton is trimmed to the bones a camera can drive (spine, neck, head, clavicles, shoulders, upper
# and lower arms, wrists), the body's skin weights are carried onto the tee and smoothed the way garment weights
# are, and the result is exported with the body itself (trimmed, decimated) as an invisible occluder.
#   blender -b bodies/m170.blend --python tryon_rig.py -- <outer-shell.ply> <out.glb>
import bpy, bmesh, math, sys
from mathutils import Vector

ARGS = sys.argv[sys.argv.index("--") + 1:]
PLY, OUT = ARGS[0], ARGS[1]
body, rig = bpy.data.objects["body"], bpy.data.objects["rig"]
sc = bpy.context.scene

# ---- the stand pose, exactly as build.py set it ----
ARM_DOWN = 64
def arm_target(side, deg_below, fwd=0.06):
    s = 1 if side == "L" else -1
    return Vector((s * math.cos(math.radians(deg_below)), -fwd, -math.sin(math.radians(deg_below)))).normalized()
for side in ("L", "R"):
    pb = rig.pose.bones["upperarm01." + side]; bn = pb.bone
    full = (rig.data.bones["upperarm02." + side].tail_local - bn.head_local).normalized()
    qw = full.rotation_difference(arm_target(side, ARM_DOWN)); R = bn.matrix_local.to_quaternion()
    pb.rotation_mode = "QUATERNION"; pb.rotation_quaternion = R.inverted() @ qw @ R
bpy.context.view_layer.update()

# ---- which bones stay; every other bone hands its weight to its nearest kept ancestor ----
KEEP = {"root", "spine05", "spine04", "spine03", "spine02", "spine01", "neck01", "neck02", "neck03", "head"}
for s in ("L", "R"):
    KEEP |= {f"clavicle.{s}", f"shoulder01.{s}", f"upperarm01.{s}", f"upperarm02.{s}", f"lowerarm01.{s}", f"lowerarm02.{s}", f"wrist.{s}"}
def kept(name):
    b = rig.data.bones[name]
    while b and b.name not in KEEP: b = b.parent
    return b.name if b else "root"

import numpy as np
SMOOTH = 30
def tidy(ob, smooth):
    """Weights averaged over the mesh's own edges (garment weights are soft: cloth isn't flesh), then the four
    strongest kept per vertex and normalised, as a GPU skin wants them."""
    me = ob.data; nv = len(me.vertices); G = list(ob.vertex_groups); W = np.zeros((nv, len(G)), np.float32)
    for v in me.vertices:
        for g in v.groups: W[v.index, g.group] = g.weight
    if smooth:
        E = np.array([e.vertices[:] for e in me.edges], np.int64); a, b = E[:, 0], E[:, 1]
        deg = np.bincount(a, minlength=nv) + np.bincount(b, minlength=nv); deg = np.maximum(deg, 1)[:, None]
        for _ in range(smooth):
            S = np.zeros_like(W); np.add.at(S, a, W[b]); np.add.at(S, b, W[a])
            W = 0.5 * W + 0.5 * S / deg
    top = np.argsort(-W, axis=1)[:, 4:]; np.put_along_axis(W, top, 0, axis=1)
    W[W < 0.01] = 0; W /= np.maximum(W.sum(1, keepdims=True), 1e-6)
    for gi, g in enumerate(G):
        g.remove(list(range(nv)))
        idx = np.nonzero(W[:, gi])[0]
        for i in idx: g.add([int(i)], float(W[i, gi]), "REPLACE")

def select_only(ob):
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
    for o in sc.objects: o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob

# ---- the body: posed shape baked in, helpers gone, weights folded onto the kept bones ----
select_only(body)
if body.data.shape_keys: bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
for m in list(body.modifiers):
    bpy.ops.object.modifier_apply(modifier=m.name)
names = {g.index: g.name for g in body.vertex_groups}
fold = {}
for v in body.data.vertices:
    acc = {}
    for g in v.groups:
        n = names[g.group]
        if n not in rig.data.bones: continue
        k = kept(n); acc[k] = acc.get(k, 0) + g.weight
    fold[v.index] = acc
for g in list(body.vertex_groups): body.vertex_groups.remove(g)
groups = {k: body.vertex_groups.new(name=k) for k in sorted(KEEP)}
for i, acc in fold.items():
    for k, w in acc.items():
        if w > 1e-4: groups[k].add([i], w, "REPLACE")

# ---- the skeleton: a copy of the rig, posed, trimmed, its pose made the rest ----
skel = rig.copy(); skel.data = rig.data.copy(); skel.name = "skel"; sc.collection.objects.link(skel)
select_only(skel)
bpy.ops.object.mode_set(mode="POSE"); bpy.ops.pose.armature_apply(selected=False); bpy.ops.object.mode_set(mode="EDIT")
eb = skel.data.edit_bones
for b in list(eb):
    if b.name not in KEEP: eb.remove(b)
bpy.ops.object.mode_set(mode="OBJECT")
print("bones", [b.name for b in skel.data.bones])

# ---- the tee: the outer shell of the fit simulation's stand frame ----
bpy.ops.wm.ply_import(filepath=PLY)
tee = bpy.context.selected_objects[0]; tee.name = "tee"
me = tee.data
if "Col" in me.color_attributes: me.color_attributes["Col"].name = "ao"
elif len(me.color_attributes): me.color_attributes[0].name = "ao"
# the decoded shell is split at every uv and normal seam: weld it, so the weights (and the skin) are continuous
bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0004)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth = True
print("welded tee verts", len(me.vertices))
# where does it sit against the body? (sanity: the sleeves should wrap the arms)
from mathutils.bvhtree import BVHTree
dg = bpy.context.evaluated_depsgraph_get()
bv = BVHTree.FromObject(body, dg)
ds = sorted(bv.find_nearest(v.co)[3] for v in list(me.vertices)[::50])
print("tee to body m: median", round(ds[len(ds) // 2], 4), "p95", round(ds[int(len(ds) * 0.95)], 4))

# weights: the body's, carried to the nearest point of its surface, then smoothed like garment weights are
select_only(tee)
dt = tee.modifiers.new("w", "DATA_TRANSFER"); dt.object = body
dt.use_vert_data = True; dt.data_types_verts = {"VGROUP_WEIGHTS"}; dt.vert_mapping = "POLYINTERP_NEAREST"
dt.layers_vgroup_select_src = "ALL"; dt.layers_vgroup_select_dst = "NAME"
bpy.ops.object.datalayout_transfer(modifier="w")
bpy.ops.object.modifier_apply(modifier="w")
tidy(tee, smooth=SMOOTH)
am = tee.modifiers.new("skel", "ARMATURE"); am.object = skel; tee.parent = skel

# ---- the occluder: the body from mid-thigh up, light enough to skin every frame ----
select_only(body)
bm = bmesh.new(); bm.from_mesh(body.data)
hip_z = (skel.matrix_world @ skel.data.bones["root"].head_local).z
# forearms and hands are left to the camera picture (the cut-out in the engine is pixel-exact; a webcam's forearm
# estimate isn't, and a 3D one in the wrong place would punch holes in the tee)
fore = {body.vertex_groups[n].index for n in body.vertex_groups.keys() if n.startswith(("lowerarm", "wrist"))}
dl = bm.verts.layers.deform.active
def forearm(v): return dl is not None and sum(w for g, w in v[dl].items() if g in fore) > 0.5
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < hip_z - 0.18 or forearm(v)], context="VERTS")
bm.to_mesh(body.data); bm.free()
dec = body.modifiers.new("dec", "DECIMATE"); dec.ratio = 0.35
bpy.ops.object.modifier_apply(modifier="dec")
tidy(body, smooth=0)
body.data.materials.clear()
am = body.modifiers.new("skel", "ARMATURE"); am.object = skel; body.parent = skel
body.name = "occluder"
print("occluder verts", len(body.data.vertices), "tee verts", len(tee.data.vertices))

# ---- export ----
for o in sc.objects: o.select_set(o in (skel, tee, body))
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True, export_apply=False,
    export_skins=True, export_def_bones=True, export_animations=False, export_morph=False, export_materials="NONE",
    export_normals=True, export_texcoords=True, export_vertex_color="ACTIVE", export_all_vertex_colors=False,
    export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7)
print("exported", OUT)
