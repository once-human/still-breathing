# blender -b --factory-startup -P trousers.py -- <body.blend> <out.blend>
# Straight-leg trousers for the people who wear the shop tee (human.py puts them on in place of the tights): cut
# from MakeHuman's tights helper (its crotch and seat already have a tailor's shape), let out to a straight leg,
# then hung on the standing body with cloth simulation so they drape as cotton twill does: a little slack at the
# seat and the crotch, the leg falling straight from the front of the thigh, the extra length breaking over the shoe.
# Mid rise: the waistband sits 4 cm over the hip joint, well under the tee's hem. Legs as build.py stands them.
# Out: object "trousers" (Blender metres, the body's own frame), vertex group "waist" (the band).
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

# the body with its helpers (the mask hides them), at rest: the legs stand as build.py stands them
for m in body.modifiers:
    if m.type == "MASK": m.show_viewport = False
dg = bpy.context.evaluated_depsgraph_get()
me = bpy.data.meshes.new_from_object(body.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
P = [body.matrix_world @ v.co for v in me.vertices]
VG = {g.name: g.index for g in body.vertex_groups}
W = [dict() for _ in me.vertices]
for v in body.data.vertices:
    for g in v.groups: W[v.index][g.group] = g.weight
wt = lambda i, n: W[i].get(VG[n], 0.0) if n in VG else 0.0
LEG = [VG[g] for g in VG if g.startswith(("pelvis.", "upperleg", "lowerleg", "foot.", "toe"))] + [VG["root"]]
leg = lambda i: sum(W[i].get(g, 0.0) for g in LEG)
jp = [P[i] for i in range(len(P)) if wt(i, "joint-pelvis") > 0.5]
pelvis = sum(jp, Vector()) / len(jp)
ank = [P[i] for i in range(len(P)) if wt(i, "joint-l-ankle") > 0.5 or wt(i, "joint-r-ankle") > 0.5]
ankle = sum(ank, Vector()) / max(1, len(ank))
WAIST = pelvis.z + 0.04
HEM = ankle.z - 0.035              # the hem breaks over the top of the shoe
print("pelvis", round(pelvis.z, 3), "waist", round(WAIST, 3), "hem", round(HEM, 3), flush=True)

# ---------- cut from the body's own skin (closed through the crotch and the seat), waist to hem ----------
ARM = [VG[g] for g in VG if g.startswith(("clavicle", "shoulder", "upperarm", "lowerarm", "wrist", "finger", "metacarpal"))]
arm = lambda i: sum(W[i].get(g, 0.0) for g in ARM)
helper = [VG[g] for g in VG if g.startswith("helper")]
skin = lambda i: not any(W[i].get(g, 0.0) > 0 for g in helper)
bm = bmesh.new(); bm.from_mesh(me)
keep = lambda f: all(skin(v.index) and arm(v.index) < 0.05 and HEM < P[v.index].z < WAIST for v in f.verts)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if not keep(f)], context="FACES")
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
# only the one piece round the hips and legs (nothing stray)
bm.verts.ensure_lookup_table()
seen, best = set(), []
for v0 in bm.verts:
    if v0.index in seen: continue
    comp, st = [], [v0]; seen.add(v0.index)
    while st:
        v = st.pop(); comp.append(v)
        for e in v.link_edges:
            o = e.other_vert(v)
            if o.index not in seen: seen.add(o.index); st.append(o)
    if len(comp) > len(best): best = comp
keepv = set(v.index for v in best)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keepv], context="VERTS")
for v in bm.verts: v.co = body.matrix_world @ v.co
bm.normal_update()
crotch = min((v.co.z for v in bm.verts if abs(v.co.x) < 0.012), default=pelvis.z - 0.1)
print("trouser verts", len(bm.verts), "crotch", round(crotch, 3), flush=True)

def smooth(e0, e1, x):
    t = min(1, max(0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t)
# ---------- let out: ease over the hips, the muscle smoothed away ----------
for v in bm.verts:
    v.co += v.normal * (0.007 + 0.012 * smooth(crotch + 0.03, crotch - 0.08, v.co.z))
for _ in range(16):
    bmesh.ops.smooth_vert(bm, verts=[v for v in bm.verts if not v.is_boundary], factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
bm.normal_update()
# ---------- a straight leg: round each leg's own straight axis, out to a profile that runs from the thigh to the hem
TALL = max(p.z for p in P) > 1.7
HEM_R = 0.064 if TALL else 0.058          # 40 / 36.5 cm round the hem
TOPZ = crotch - 0.05
for side in (1, -1):
    vs = [v for v in bm.verts if v.co.x * side > 0.004 and v.co.z < crotch]
    def centre(z, d=0.01):
        r = [v.co for v in vs if abs(v.co.z - z) < d]
        return sum(r, Vector()) / len(r)
    c0, c1 = centre(TOPZ), centre(HEM + 0.03)
    ax = (c0 - c1)
    ring = [v for v in vs if abs(v.co.z - TOPZ) < 0.01]
    r0 = max((v.co - c0).xy.length for v in ring)
    for v in vs:
        t = (v.co.z - c1.z) / ax.z                     # 1 at the thigh, 0 at the hem
        c = c1 + ax * t
        d = (v.co - c).xy; r = d.length
        if r < 1e-4: continue
        R = HEM_R + (r0 - HEM_R) * max(0.0, min(1.0, t)) ** 1.6
        up = smooth(crotch - 0.02, crotch - 0.12, v.co.z)   # blends in below the crotch
        straight = smooth(TOPZ - 0.05, TOPZ - 0.2, v.co.z)  # from mid thigh down the leg falls as a round tube
        want = (1 - straight) * max(r, R) + straight * R
        v.co.xy = c.xy + d / r * (r + (want - r) * up)
bm.normal_update()
for _ in range(4):
    bmesh.ops.smooth_vert(bm, verts=[v for v in bm.verts if not v.is_boundary], factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
bm.normal_update()

tm = bpy.data.meshes.new("trousers"); bm.to_mesh(tm); bm.free()
tr = bpy.data.objects.new("trousers", tm); sc.collection.objects.link(tr)
# fine enough to fold (about 8 mm between points): the helper is a skin-tight low-poly suit
sd = tr.modifiers.new("sd", "SUBSURF"); sd.levels = 2; sd.use_limit_surface = False
bpy.context.view_layer.objects.active = tr; bpy.ops.object.modifier_apply(modifier="sd")
tm = tr.data
wg = tr.vertex_groups.new(name="waist")
wg.add([v.index for v in tm.vertices if v.co.z > WAIST - 0.025], 1.0, "REPLACE")
for p in tm.polygons: p.use_smooth = True

# ---------- hang them: the body is the form, the band is held at the waist ----------
col = body.modifiers.new("col", "COLLISION")
body.collision.thickness_outer = 0.003; body.collision.cloth_friction = 12
cl = tr.modifiers.new("cloth", "CLOTH"); s = cl.settings; c = cl.collision_settings
s.quality = 10; s.mass = 0.35; s.air_damping = 1.5
s.tension_stiffness = s.compression_stiffness = 50; s.shear_stiffness = 30; s.bending_stiffness = 30   # cotton twill: it holds a tube
s.vertex_group_mass = "waist"; s.pin_stiffness = 1
c.distance_min = 0.003; c.use_self_collision = True; c.self_distance_min = 0.003; c.collision_quality = 4
sc.frame_start, sc.frame_end = 1, 48
cl.point_cache.frame_start, cl.point_cache.frame_end = 1, 48
for f in range(1, 49):
    sc.frame_set(f)
    if f % 8 == 0: print("frame", f, flush=True)
dg = bpy.context.evaluated_depsgraph_get()
done = bpy.data.meshes.new_from_object(tr.evaluated_get(dg), depsgraph=dg)
tr.modifiers.clear(); tr.data = done
body.modifiers.remove(col)
# the waist group survives on the new mesh by vertex order
wg = tr.vertex_groups.get("waist") or tr.vertex_groups.new(name="waist")
for o in [o for o in sc.objects if o is not tr]: bpy.data.objects.remove(o)
sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("saved", OUT, len(tr.data.vertices), "verts", flush=True)
