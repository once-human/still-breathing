# blender -b <sim.blend> -P export.py -- <outdir> [proxy]
# Web export of one body + size from build.py, for every pose it kept (tee_stand, tee_up, tee_sit):
#   <pose>.glb       the tee: outer fabric + plain inner shell, ambient occlusion baked into the vertices
#   body-<pose>.glb  the body in that pose, for fit mode
#   fit.json         what the fit looks like on this body, in centimetres, measured on the simulation
#   proxy.glb        (with "proxy") the sewn tee before smoothing, the cloth mesh the live mirror simulates
import bpy, bmesh, sys, os, json, math
from mathutils import Vector
A = sys.argv[sys.argv.index("--") + 1:]
OUT = A[0]; PROXY = "proxy" in A[1:]; os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene; body = bpy.data.objects["body"]; rig = bpy.data.objects["rig"]
chair = bpy.data.objects.get("chair")
POSES = [p for p in ("stand", "up", "sit") if f"tee_{p}" in bpy.data.objects]
sys.path.insert(0, os.path.dirname(bpy.data.filepath)); sys.path.insert(0, os.path.dirname(__file__))
from pattern import SIZE, SIZE_NAME
size = sc.get("size", SIZE_NAME)

def verts(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(dg).to_mesh(); v = [ob.matrix_world @ x.co for x in me.vertices]; ob.evaluated_get(dg).to_mesh_clear(); return v
def hull_len(pts):
    pts = sorted(set(pts))
    def cr(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    h = lo[:-1] + up[:-1]; return sum(math.dist(h[i], h[(i + 1) % len(h)]) for i in range(len(h)))
import resource
def mem(tag): print("mem", tag, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024, "MB peak", flush=True)
mem("loaded")
def go(frame): sc.frame_set(frame); bpy.context.view_layer.update()

# ---------- the body, measured the way a tailor would: standing, arms out of the way ----------
go(1)   # the file is saved on the sitting frame, where the rig is lowered onto the stool: measure from frame 1
rig.data.pose_position = "REST"; bpy.context.view_layer.update(); BR = verts(body)
rig.data.pose_position = "POSE"; bpy.context.view_layer.update()
zs = [v.z for v in BR]; H = max(zs) - min(zs); zc = min(zs) + 0.73 * H
band = lambda V, z, xmax: [(v.x, v.y) for v in V if abs(v.z - z) < 0.006 and abs(v.x) < xmax]
body_chest = hull_len(band(BR, zc, 0.2)) * 100
waist_rest = min(zs) + 0.56 * H          # where a pair of jeans sits (low hip), about
fit = {"size": size, "body": {"height_cm": round(H * 100), "chest_cm": round(body_chest)},
       "chest_ease_cm": round(SIZE["chest"] * 2 - body_chest), "poses": {}}

def front_hem(V):  # lowest point of the tee near the centre front / centre back
    f = [v for v in V if abs(v.x) < 0.06 and v.y < 0]; b = [v for v in V if abs(v.x) < 0.06 and v.y > 0]
    return min(v.z for v in f), min(v.z for v in b)

stand_hem = None
def close_edges(bm, passes=8):
    """The open edges (hem, sleeve ends, neck) run on unbroken, as sewn: where a seam's first stitch sits a
    little above the edge, the two panel corners poke out as a notch. Any sharp turn along an open edge is
    eased back onto the line of its neighbours (and the cloth just inside follows half way)."""
    bv = [v for v in bm.verts if v.is_boundary]
    nb = {v: [e.other_vert(v) for e in v.link_edges if e.is_boundary] for v in bv}
    moved = 0
    for _ in range(passes):
        for v in bv:
            ns = nb[v]
            if len(ns) != 2: continue
            a, c = ns[0].co, ns[1].co
            u, w = (a - v.co), (c - v.co)
            if u.length < 1e-9 or w.length < 1e-9: continue
            if u.normalized().dot(w.normalized()) < -0.5: continue      # straighter than 120 degrees: leave it
            d = (a + c) / 2 - v.co
            v.co += d; moved += 1
            for e in v.link_edges:
                o = e.other_vert(v)
                if not o.is_boundary: o.co += d * 0.5
    print("edges closed", moved, flush=True)

for pose in POSES:
    tee = bpy.data.objects[f"tee_{pose}"]; go(tee["frame"])
    BV, TV = verts(body), verts(tee)
    lift = rig.location.z
    hf, hb = front_hem(TV)
    p = {}
    if pose == "stand":
        cz = [v.z for v in BV if abs(v.x) < 0.012 and 0.45 < v.z - lift < 1.0]
        # on the ghost form the body's torso is gone: take the crotch from the hip joints instead
        crotch = min(cz) if cz else (rig.matrix_world @ rig.pose.bones["upperleg01.L"].head).z - 0.08
        elbow = rig.matrix_world @ rig.pose.bones["lowerarm01.L"].head
        shoulder = rig.matrix_world @ rig.pose.bones["upperarm01.L"].head
        sleeve = [v for v in TV if v.x > 0.22]
        end = min(sleeve, key=lambda v: (v - elbow).length)
        seam = max((v for v in TV if v.x > 0.1 and v.z > shoulder.z - 0.15), key=lambda v: v.x - 2 * abs(v.z - shoulder.z))
        stand_hem = hf
        p = {"hem_below_crotch_cm": round((crotch - hf) * 100), "sleeve_above_elbow_cm": round((end - elbow).length * 100),
             "hem_vs_waistband_cm": round((hf - waist_rest) * 100)}
    elif pose == "up":
        p = {"hem_rise_cm": round((hf - stand_hem) * 100) if stand_hem is not None else None,
             "hem_vs_waistband_cm": round((hf - waist_rest) * 100)}
    else:
        p = {"back_hem_vs_waistband_cm": round((hb - (waist_rest + lift)) * 100),
             "front_hem_vs_waistband_cm": round((hf - (waist_rest + lift)) * 100),
             "seat_cm": round(sc.get("seat", 0) * 100)}
    p["frame"] = tee["frame"]; p["lift_m"] = round(lift, 4)
    fit["poses"][pose] = p

print("FIT", json.dumps(fit), flush=True); mem("measured"); json.dump(fit, open(os.path.join(OUT, "fit.json"), "w"), indent=1)

# ---------- per pose: AO into the vertices, thickness, smoothing, GLB ----------
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 96
sc.render.threads_mode = "FIXED"; sc.render.threads = os.cpu_count() or 2
sc.world = sc.world or bpy.data.worlds.new("w")
inner = bpy.data.materials.new("inner"); outer = bpy.data.materials.new("outer")
body.hide_render = True
if chair: chair.hide_render = True
def select_only(ob):
    for o in sc.objects: o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
def glb(path, **kw):
    args = dict(filepath=path, use_selection=True, export_apply=True, export_yup=True, export_materials="PLACEHOLDER",
                export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7,
                export_skins=False, export_animations=False, export_morph=False)
    args.update(kw)
    try: bpy.ops.export_scene.gltf(**args)
    except TypeError:   # older exporters: no vertex colour switch
        args.pop("export_vertex_color", None); bpy.ops.export_scene.gltf(**args)

def close_edges(bm, passes=8):
    """The open edges (hem, sleeve ends, neck) run on unbroken, as sewn: where a seam's first stitch sits a
    little above the edge, the two panel corners poke out as a notch. Any sharp turn along an open edge is
    eased back onto the line of its neighbours (and the cloth just inside follows half way)."""
    bv = [v for v in bm.verts if v.is_boundary]
    nb = {v: [e.other_vert(v) for e in v.link_edges if e.is_boundary] for v in bv}
    moved = 0
    for _ in range(passes):
        for v in bv:
            ns = nb[v]
            if len(ns) != 2: continue
            a, c = ns[0].co, ns[1].co
            u, w = (a - v.co), (c - v.co)
            if u.length < 1e-9 or w.length < 1e-9: continue
            if u.normalized().dot(w.normalized()) < -0.5: continue      # straighter than 120 degrees: leave it
            d = (a + c) / 2 - v.co
            v.co += d; moved += 1
            for e in v.link_edges:
                o = e.other_vert(v)
                if not o.is_boundary: o.co += d * 0.5
    print("edges closed", moved, flush=True)

for pose in POSES:
    tee = bpy.data.objects[f"tee_{pose}"]; go(tee["frame"])
    for o in sc.objects:
        if o.name.startswith("tee"): o.hide_render = o is not tee
    bm = bmesh.new(); bm.from_mesh(tee.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0008)
    close_edges(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(tee.data); bm.free()
    if PROXY and pose == "stand":
        select_only(tee); glb(os.path.join(OUT, "proxy.glb"), export_draco_mesh_compression_enable=False)
    ca = tee.data.color_attributes.new("ao", "FLOAT_COLOR", "POINT")
    tee.data.color_attributes.active_color = ca
    try: tee.data.color_attributes.render_color_index = tee.data.color_attributes.active_color_index
    except Exception: pass
    select_only(tee)
    sc.render.bake.target = "VERTEX_COLORS"
    print("bake", pose, len(tee.data.vertices), "verts", flush=True)
    bpy.ops.object.bake(type="AO")
    print("baked", pose, flush=True); mem("baked " + pose)
    tee.data.materials.clear(); tee.data.materials.append(outer); tee.data.materials.append(inner)
    so = tee.modifiers.new("thick", "SOLIDIFY"); so.thickness = 0.0032; so.offset = 0; so.use_even_offset = True; so.material_offset = 1
    if "stiff" in tee.vertex_groups: so.vertex_group = "stiff"; so.thickness_vertex_group = 0.5
    sub = tee.modifiers.new("sub", "SUBSURF"); sub.levels = 1
    # plain Catmull-Clark: the limit-surface evaluator needs ~3 GB on this mesh and killed 7 GB CI runners
    sub.use_limit_surface = False
    glb(os.path.join(OUT, f"{pose}.glb"), export_vertex_color="ACTIVE"); print("tee glb", pose, flush=True); mem("tee glb " + pose)
    # the body in this pose (armature applied), for fit mode
    body.hide_render = False; select_only(body)
    glb(os.path.join(OUT, f"body-{pose}.glb"), export_materials="NONE")
    body.hide_render = True
    print("exported", pose, flush=True); mem("body glb " + pose)
print("done", OUT)
