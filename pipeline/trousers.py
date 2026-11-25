# blender -b --factory-startup -P trousers.py -- <body.blend> <out.blend>
# Straight-leg trousers for the people who wear the shop tee, hung on the standing body by cloth simulation.
#   1. a shell round the hips and legs: the body grown out by the ease (8 mm over the hips and seat), joined with
#      one straight cone per leg from the upper thigh to the hem (36.5 cm round on him, 33 on her), stopping short of the middle, as one volume,
#      remeshed into one even surface. Over the seat it bridges the cleft; the legs stay apart
#   2. cut at the waist (mid rise, 4 cm over the hip joints, under the tee's hem) and at the hem (ankle length),
#      the muscle smoothed away (denim doesn't show it)
#   3. hung for a second on the body with the band held: it settles on the seat and the thighs and falls from them
# Works on any body with MakeHuman's rig (bones upperleg01, foot): MakeHuman's own or people.py's.
# Out: object "trousers" (Blender metres, the body's frame, standing as build.py stands it).
import bpy, bmesh, sys, math
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
BODY, OUT = a[0], a[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
with bpy.data.libraries.load(BODY) as (src, dst):
    dst.objects = [n for n in src.objects if n in ("body", "rig")]
for o in dst.objects: sc.collection.objects.link(o)
body, rig = bpy.data.objects["body"], bpy.data.objects["rig"]
bpy.context.view_layer.update()
bone = lambda n: rig.matrix_world @ rig.pose.bones[n].head
HIP = (bone("upperleg01.L").z + bone("upperleg01.R").z) / 2
ANKLE = (bone("foot.L").z + bone("foot.R").z) / 2
WAIST, HEM = HIP + 0.04, ANKLE + 0.035      # ankle length: the hem clears the foot, no pooling
dg = bpy.context.evaluated_depsgraph_get()
me = bpy.data.meshes.new_from_object(body.evaluated_get(dg), depsgraph=dg)     # helpers stay masked
me.transform(body.matrix_world)
P = [v.co.copy() for v in me.vertices]
TALL = max(p.z for p in P) > 1.7
HEM_R = 0.058 if TALL else 0.052            # leg opening 36.5 / 33 cm round, a straight jean
H = max(p.z for p in P)
print("hip", round(HIP, 3), "waist", round(WAIST, 3), "hem", round(HEM, 3), flush=True)

# ---------- 1. the shell ----------
bm = bmesh.new(); bm.from_mesh(me); bm.normal_update()
legs = [p for p in P if p.z < HIP - 0.06 and abs(p.x) < 0.25]
crotch = min((p.z for p in P if abs(p.x) < 0.01 and HIP - 0.2 < p.z < HIP), default=HIP - 0.1)   # thighs that touch lower down are not it
crotch = max(crotch, HIP - 0.05 * H)            # a sculpted groin reaches lower than the trouser's crotch seam sits
# over the seat the shell is grown 2.5 cm, remeshed, then pulled back 1.7 cm (a closing): it bridges the cleft of
# the seat as denim does and leaves 8 mm of ease. Down the legs only 1 cm, so the gap between the thighs stays open
seat = lambda z: max(0.0, min(1.0, (z - crotch) / 0.04))
IN = lambda z: 0.017 * seat(z)
for v in bm.verts:
    v.co += v.normal * (0.010 + 0.015 * seat(v.co.z))
TOPZ = crotch - 0.05


def slice_(s, z, d=0.008):
    """one leg's slice at a height: its centre and its reach"""
    pts = []
    while len(pts) < 8 and d < 0.1:            # MakeHuman's shins are long quads: widen the band until it holds a ring
        pts = [p for p in legs if p.x * s > 0.01 and abs(p.z - z) < d]; d *= 1.5
    c = sum(pts, Vector()) / len(pts)
    return c, max((p - c).xy.length for p in pts)


for s in (1, -1):
    c0, r0 = slice_(s, TOPZ); c1, _ = slice_(s, ANKLE + 0.06)
    r0 += 0.012
    N, K = 48, 24
    rings = []
    for k in range(K + 1):
        z = TOPZ + 0.02 + (HEM - 0.02 - TOPZ - 0.02) * k / K
        u = (z - c1.z) / (c0.z - c1.z); c = c1 + (c0 - c1) * u
        R = HEM_R + (r0 - HEM_R) * max(0.0, min(1.0, u)) ** 1.4
        R = min(R, abs(c.x) - 0.006)                 # each leg stops short of the middle: the two never web together
        rings.append([bm.verts.new((c.x + R * math.cos(2 * math.pi * j / N), c.y + R * math.sin(2 * math.pi * j / N), z)) for j in range(N)])
    for k in range(K):
        for j in range(N):
            bm.faces.new((rings[k][j], rings[k][(j + 1) % N], rings[k + 1][(j + 1) % N], rings[k + 1][j]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
sm = bpy.data.meshes.new("shell"); bm.to_mesh(sm); bm.free()
sh = bpy.data.objects.new("shell", sm); sc.collection.objects.link(sh)
rm = sh.modifiers.new("vox", "REMESH"); rm.mode = "VOXEL"; rm.voxel_size = 0.008; rm.adaptivity = 0
dg = bpy.context.evaluated_depsgraph_get()
tm = bpy.data.meshes.new_from_object(sh.evaluated_get(dg), depsgraph=dg)
bpy.data.objects.remove(sh)

# ---------- 2. cut at the waist and the hem, one piece, smoothed ----------
bm = bmesh.new(); bm.from_mesh(tm); bm.normal_update()
for v in bm.verts:
    v.co -= v.normal * IN(v.co.z)
for z, cut_below in ((WAIST, False), (HEM, True)):
    g = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=g, plane_co=(0, 0, z), plane_no=(0, 0, 1), clear_inner=cut_below, clear_outer=not cut_below)
seen, best = set(), []
for v0 in bm.verts:
    if v0 in seen: continue
    comp, st = [], [v0]; seen.add(v0)
    while st:
        v = st.pop(); comp.append(v)
        for e in v.link_edges:
            o = e.other_vert(v)
            if o not in seen: seen.add(o); st.append(o)
    if len(comp) > len(best): best = comp
keep = set(best)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v not in keep], context="VERTS")
inner = [v for v in bm.verts if not v.is_boundary]
for _ in range(14):
    bmesh.ops.smooth_vert(bm, verts=inner, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
bm.normal_update()
tm = bpy.data.meshes.new("trousers"); bm.to_mesh(tm); bm.free()
tr = bpy.data.objects.new("trousers", tm); sc.collection.objects.link(tr)
for p in tm.polygons: p.use_smooth = True
wg = tr.vertex_groups.new(name="waist")
wg.add([v.index for v in tm.vertices if v.co.z > WAIST - 0.02], 1.0, "REPLACE")
print("trouser verts", len(tm.vertices), "crotch", round(crotch, 3), flush=True)

# ---------- 3. hang them on the body, the band held ----------
body.modifiers.new("col", "COLLISION")
body.collision.thickness_outer = 0.004; body.collision.cloth_friction = 10
cl = tr.modifiers.new("cloth", "CLOTH"); s = cl.settings; c = cl.collision_settings
s.quality = 8; s.mass = 0.45; s.air_damping = 2                                                        # 13 oz denim
s.tension_stiffness = s.compression_stiffness = 80; s.shear_stiffness = 40; s.bending_stiffness = 35   # denim holds its shape
s.vertex_group_mass = "waist"; s.pin_stiffness = 1
c.distance_min = 0.004; c.collision_quality = 3
END = 30
sc.frame_start, sc.frame_end = 1, END
cl.point_cache.frame_start, cl.point_cache.frame_end = 1, END
for f in range(1, END + 1):
    sc.frame_set(f)
dg = bpy.context.evaluated_depsgraph_get()
done = bpy.data.meshes.new_from_object(tr.evaluated_get(dg), depsgraph=dg)
tr.modifiers.clear(); old = tr.data; tr.data = done; bpy.data.meshes.remove(old)
for o in [o for o in sc.objects if o is not tr]: bpy.data.objects.remove(o)
sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("saved", OUT, len(tr.data.vertices), "verts", flush=True)
