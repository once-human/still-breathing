# BAND=<k> blender -b --factory-startup -P canopy.py -- <out.npz> [test]
# The show's fabric canopy (stage.py), hung as real cloth and kept moving: a sheer white sheet between each pair of
# rigging lines, gathered at its four pick-up points. Rings of these swags round the decks make the canopy: high over
# the decks, down low in a trough round the stage, rising again over the crowd (after the shape of the canopy at Fred
# again..'s USB002 nights, Alexandra Palace, 2026).
# It breathes: after it settles, every pick-up rises and falls on its winch line in a slow wave that runs round the
# hall and out from the decks, with a second, quicker swell over it, and the cloth follows, swinging and filling.
# Every swag of a band (the ring between two rings of pick-ups) is its own sheet, with its own fullness and gathers,
# simulated together, so neighbours share their pick-ups and no two hang alike. One band per call: the farm runs the
# bands side by side (stage.yml, job "canopy").
# The motion is periodic (LOOP seconds); one loop is kept after two to get going, so its end runs into its start.
#   s<i>_v  (FRAMES, n, 3) float16: the swag's vertices every frame of the loop, FPS a second, round the deck centre
#           at (0, 0) (frame 0 is the still the panoramas are rendered with)
#   s<i>_f  (m, 4) int32 quads; and K (band), N (swags), RINGS (r, z) the pick-up rings, LOOP, FPS
#   P       (FRAMES, 2, N) float32: how far each pick-up of the band's inner and outer ring is lifted, every frame
import bpy, sys, os, math, random
import numpy as np
from mathutils import Vector, Matrix

a = sys.argv[sys.argv.index("--") + 1:]
OUT = a[0]; TEST = len(a) > 1 and a[1] == "test"
K = int(os.environ.get("BAND", "0"))
N = 16                                           # rigging lines round the decks
# pick-up rings round the deck centre: (radius m, height m). High over the decks, a trough round the stage where the
# swags hang lowest, rising again over the crowd to the outer rigging; low enough that from in the crowd the swags
# across the hall hang just over the heads, as they did
RINGS = [(3.5, 8.0), (7.0, 6.0), (11.0, 4.3), (15.0, 4.4), (20.0, 4.8), (26.0, 5.6), (33.0, 6.6)]
LOOP, FPS, SIM_FPS = 10.0, 12, 24                # one breath: 10 s, kept at 12 frames a second
LIFT = [0.30, 0.42, 0.50, 0.50, 0.46, 0.40, 0.34]  # how far each ring of pick-ups rises and falls, m
CELL = 0.08                                      # cloth grid spacing at rest, m (stage.py smooths it once more)
SETTLE = 20 if TEST else 110                     # frames: gathered by 30, settled by SETTLE
LOOPS = 0.1 if TEST else 3                       # two loops to get going, the third kept
END = SETTLE + int(LOOPS * LOOP * SIM_FPS)
th = 2 * math.pi / N


def lift(ring, line, f):
    """a pick-up's height offset at simulation frame f: still while the cloth settles, then the wave, eased in over
    the first loop. One slow swell running out from the decks and once round the hall, and a smaller one at twice
    the rate the other way, so the canopy never moves in step; periodic in LOOP"""
    t = (f - 1 - SETTLE) / SIM_FPS
    if t <= 0: return 0.0
    ease = 0.5 - 0.5 * math.cos(math.pi * min(1.0, t / LOOP))
    tau = t / LOOP; az = line / N
    w = 0.8 * math.sin(2 * math.pi * (tau - 0.12 * ring - az)) + 0.28 * math.sin(2 * math.pi * (2 * tau - 0.21 * ring + 2 * az) + 1.1)
    return LIFT[ring] * ease * w


(r0, z0), (r1, z1) = RINGS[K], RINGS[K + 1]
rnd = random.Random(2026 + 97 * K)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.frame_start, sc.frame_end = 1, END
sc.render.fps = SIM_FPS
keep = list(range(END - int(LOOP * SIM_FPS) + 1, END + 1, SIM_FPS // FPS)) if not TEST else [END]
swags = []
for i in range(2 if TEST else N):
    ft = rnd.uniform(1.07, 1.15)                 # fullness across and along: the extra cloth that falls in folds
    fr = rnd.uniform(1.03, 1.08)
    L = 2 * r1 * math.sin(th / 2) * ft
    B = math.hypot(r1 - r0, z1 - z0) * fr
    nu = max(8, min(170, round(L / CELL))) if not TEST else 16
    nv = max(6, min(100, round(B / CELL))) if not TEST else 8
    # the sheet at rest: flat, level, over its place in the band, before it is hung; built on the +Y axis, turned
    zt = max(z0, z1) + 0.3; ym = (r0 + r1) / 2
    R = Matrix.Rotation(i * th, 4, "Z")
    verts = [tuple(R @ Vector(((u / nu - 0.5) * L, ym + (v / nv - 0.5) * B, zt))) for v in range(nv + 1) for u in range(nu + 1)]
    faces = [(v * (nu + 1) + u, v * (nu + 1) + u + 1, (v + 1) * (nu + 1) + u + 1, (v + 1) * (nu + 1) + u)
             for v in range(nv) for u in range(nu)]
    me = bpy.data.meshes.new(f"swag{i}"); me.from_pydata(verts, [], faces)
    ob = bpy.data.objects.new(f"swag{i}", me); sc.collection.objects.link(ob)
    pin = ob.vertex_groups.new(name="pin")
    # the four pick-ups: (sheet corner u, v) -> its rigging line (round the ring) and ring
    corners = [((0, 0), (i, 0)), ((nu, 0), (i + 1, 0)), ((0, nv), (i, 1)), ((nu, nv), (i + 1, 1))]
    for (cu, cv), (line, rr) in corners:
        r, z = (r0, z0) if rr == 0 else (r1, z1); ring = K + rr
        d0 = rnd.uniform(0.25, 0.55)             # how much of each edge is gathered into the pick-up
        gu, gv = max(1, round(d0 / (L / nu))), max(1, round(d0 / (B / nv)))
        idx = set()
        for t in range(gu + 1): idx.add(cv * (nu + 1) + abs(cu - t))
        for t in range(gv + 1): idx.add(abs(cv - t) * (nu + 1) + cu)
        idx = sorted(idx)
        g = ob.vertex_groups.new(name=f"c{cu}{cv}"); g.add(idx, 1.0, "REPLACE"); pin.add(idx, 1.0, "REPLACE")
        c = sum((Vector(verts[j]) for j in idx), Vector()) / len(idx)
        e = bpy.data.objects.new(f"e{i}{cu}{cv}", None); sc.collection.objects.link(e)
        e.location = c; e.keyframe_insert("location", frame=1); e.keyframe_insert("scale", frame=1)
        ang = math.pi / 2 + (line - 0.5) * th   # the rigging lines sit between the swags' centres
        e.location = (r * math.cos(ang), r * math.sin(ang), z); e.scale = (0.04, 0.04, 0.04)
        e.keyframe_insert("location", frame=30); e.keyframe_insert("scale", frame=30)
        for f in range(SETTLE + 1, END + 1):    # the winch line: the pick-up's height every frame of the breathing
            e.location = (r * math.cos(ang), r * math.sin(ang), z + lift(ring, line % N, f)); e.keyframe_insert("location", frame=f)
        sc.frame_set(1)
        h = ob.modifiers.new(f"h{cu}{cv}", "HOOK"); h.object = e; h.vertex_group = g.name
        h.matrix_inverse = Matrix.Translation(c).inverted(); h.center = c; h.falloff_type = "NONE"
    cl = ob.modifiers.new("cloth", "CLOTH"); s_ = cl.settings
    # a light sheer synthetic: little weight, soft to bend so its folds are round, slowed by the air it pushes
    s_.quality = 7; s_.mass = 0.015; s_.air_damping = 1.6
    s_.tension_stiffness = 30; s_.compression_stiffness = 30; s_.shear_stiffness = 6; s_.bending_stiffness = 0.04
    s_.tension_damping = 5; s_.compression_damping = 5; s_.shear_damping = 5; s_.bending_damping = 0.4
    s_.vertex_group_mass = "pin"; s_.pin_stiffness = 1.0
    cl.collision_settings.use_collision = False; cl.collision_settings.use_self_collision = False
    cl.point_cache.frame_start, cl.point_cache.frame_end = 1, END
    swags.append((ob, faces, nu, nv))

res = {"K": np.int32(K), "N": np.int32(N), "RINGS": np.array(RINGS, np.float32), "LOOP": np.float32(LOOP), "FPS": np.int32(FPS)}
anim = [[] for _ in swags]
keepset = set(keep); first = None; before = keep[0] - int(LOOP * SIM_FPS)
for f in range(1, END + 1):
    sc.frame_set(f)
    if f in keepset or f == before:
        dg = bpy.context.evaluated_depsgraph_get()
        for n_, (ob, *_r) in enumerate(swags):
            em = ob.evaluated_get(dg).to_mesh()
            c_ = np.empty(len(em.vertices) * 3, np.float32); em.vertices.foreach_get("co", c_)
            ob.evaluated_get(dg).to_mesh_clear()
            if f in keepset: anim[n_].append(c_.reshape(-1, 3).astype(np.float16))
            elif n_ == 0: first = c_.reshape(-1, 3)
    if f % 60 == 0: print("frame", f, "of", END, flush=True)
for n_, (ob, faces, nu, nv) in enumerate(swags):
    res[f"s{n_}_v"] = np.stack(anim[n_]); res[f"s{n_}_f"] = np.array(faces, np.int32)
    zz = res[f"s{n_}_v"][0, :, 2].astype(np.float32)
    print(f"band {K} swag {n_}: {nu}x{nv}, hangs {zz.min():.2f}..{zz.max():.2f} m", flush=True)
if first is not None and not TEST:
    # the loop closes: the kept loop's first frame against the same moment a loop earlier
    seam = np.abs(res["s0_v"][0].astype(np.float32) - first).max()
    step = np.abs(res["s0_v"][1].astype(np.float32) - res["s0_v"][0].astype(np.float32)).max()
    print(f"band {K}: loop seam {seam:.3f} m (one frame's travel {step:.3f} m)")
# the pick-ups' heights over the loop, for the rigging lines (stage.py): (frames, 2 rings (inner, outer), N lines)
res["P"] = np.array([[[lift(K + rr, l, f) for l in range(N)] for rr in (0, 1)] for f in keep], np.float32)
np.savez_compressed(OUT, **res)
print("saved", OUT, len(keep), "frames")
