# blender -b --factory-startup -P canopy.py -- <out.npz> [test]
# The show's fabric canopy (stage.py), hung as real cloth: a sheer white sheet between each pair of rigging lines,
# gathered at its four pick-up points and left to fall. Rings of these swags round the decks make the canopy: high
# over the decks, down low in a trough round the stage, rising again over the crowd (after the shape of the canopy
# at Fred again..'s USB002 nights, Alexandra Palace, 2026). Every band of the ring is simulated twice with its own
# gathers and fullness; stage.py turns copies of them round the ring.
# Run on the farm (stage.yml, job "canopy"); writes the settled cloth of every band as one .npz:
#   b<k>v<j>_v (n, 3) float32 vertices, for the swag centred on the +Y axis round the deck centre at (0, 0)
#   b<k>v<j>_f (m, 4) int32 quads, and N (swags per ring), RINGS (r, z) the pick-up rings
import bpy, sys, math, random
import numpy as np
from mathutils import Vector, Matrix

a = sys.argv[sys.argv.index("--") + 1:]
OUT = a[0]; TEST = len(a) > 1 and a[1] == "test"
N = 16                                           # rigging lines round the decks
# pick-up rings round the deck centre: (radius m, height m). High over the decks, a trough round the stage
# where the swags hang lowest, rising again over the crowd to the outer rigging
RINGS = [(3.5, 8.0), (7.0, 6.0), (11.0, 4.9), (15.0, 5.0), (20.0, 5.6), (26.0, 6.6), (33.0, 8.0)]
VARIANTS = 2
CELL = 0.09                                      # cloth grid spacing at rest, m
END = 30 if TEST else 110                        # frames: gathered by 30, settled by the end
rnd = random.Random(2026)
th = 2 * math.pi / N
res = {"N": np.int32(N), "RINGS": np.array(RINGS, np.float32)}

for k in range(1 if TEST else len(RINGS) - 1):
    (r0, z0), (r1, z1) = RINGS[k], RINGS[k + 1]
    for j in range(1 if TEST else VARIANTS):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = bpy.context.scene; sc.frame_start, sc.frame_end = 1, END
        ft = rnd.uniform(1.14, 1.26)             # fullness across and along: the extra cloth that falls in folds
        fr = rnd.uniform(1.06, 1.16)
        L = 2 * r1 * math.sin(th / 2) * ft
        B = math.hypot(r1 - r0, z1 - z0) * fr
        nu = max(8, min(150, round(L / CELL))) if not TEST else 20
        nv = max(6, min(90, round(B / CELL))) if not TEST else 10
        # the sheet at rest: flat, level, over the band, before it is hung
        zt = max(z0, z1) + 0.3; ym = (r0 + r1) / 2
        verts = [((i / nu - 0.5) * L, ym + (v / nv - 0.5) * B, zt) for v in range(nv + 1) for i in range(nu + 1)]
        faces = [(v * (nu + 1) + i, v * (nu + 1) + i + 1, (v + 1) * (nu + 1) + i + 1, (v + 1) * (nu + 1) + i)
                 for v in range(nv) for i in range(nu)]
        me = bpy.data.meshes.new("swag"); me.from_pydata(verts, [], faces)
        ob = bpy.data.objects.new("swag", me); sc.collection.objects.link(ob)
        pin = ob.vertex_groups.new(name="pin")
        # the four pick-ups: (sheet corner i, v) -> where it is hung (the rigging point round the ring)
        corners = [((0, 0), (r0, z0, -1)), ((nu, 0), (r0, z0, 1)), ((0, nv), (r1, z1, -1)), ((nu, nv), (r1, z1, 1))]
        for (ci, cv), (r, z, s) in corners:
            d0 = rnd.uniform(0.25, 0.6)          # how much of each edge is gathered into the pick-up
            gi, gv = max(1, round(d0 / (L / nu))), max(1, round(d0 / (B / nv)))
            idx = set()
            for t in range(gi + 1): idx.add(cv * (nu + 1) + abs(ci - t))
            for t in range(gv + 1): idx.add(abs(cv - t) * (nu + 1) + ci)
            idx = sorted(idx)
            g = ob.vertex_groups.new(name=f"c{ci}{cv}"); g.add(idx, 1.0, "REPLACE"); pin.add(idx, 1.0, "REPLACE")
            c = sum((Vector(verts[i]) for i in idx), Vector()) / len(idx)
            e = bpy.data.objects.new(f"e{ci}{cv}", None); sc.collection.objects.link(e)
            e.location = c; e.keyframe_insert("location", frame=1); e.keyframe_insert("scale", frame=1)
            ang = math.pi / 2 + s * th / 2
            e.location = (r * math.cos(ang), r * math.sin(ang), z); e.scale = (0.04, 0.04, 0.04)
            e.keyframe_insert("location", frame=30); e.keyframe_insert("scale", frame=30)
            sc.frame_set(1)
            h = ob.modifiers.new(f"h{ci}{cv}", "HOOK"); h.object = e; h.vertex_group = g.name
            h.matrix_inverse = Matrix.Translation(c).inverted(); h.center = c; h.falloff_type = "NONE"
        cl = ob.modifiers.new("cloth", "CLOTH"); s_ = cl.settings
        s_.quality = 10; s_.mass = 0.02; s_.air_damping = 2.0
        s_.tension_stiffness = 40; s_.compression_stiffness = 40; s_.shear_stiffness = 8; s_.bending_stiffness = 0.012
        s_.tension_damping = 5; s_.compression_damping = 5; s_.shear_damping = 5; s_.bending_damping = 0.3
        s_.vertex_group_mass = "pin"; s_.pin_stiffness = 1.0
        cl.collision_settings.use_collision = False; cl.collision_settings.use_self_collision = False
        cl.point_cache.frame_start, cl.point_cache.frame_end = 1, END
        for f in range(1, END + 1): sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get(); em = ob.evaluated_get(dg).to_mesh()
        co = np.empty(len(em.vertices) * 3, np.float32); em.vertices.foreach_get("co", co)
        res[f"b{k}v{j}_v"] = co.reshape(-1, 3); res[f"b{k}v{j}_f"] = np.array(faces, np.int32)
        zz = co.reshape(-1, 3)[:, 2]
        print(f"band {k} ({r0}->{r1} m) variant {j}: {nu}x{nv}, hangs {zz.min():.2f}..{zz.max():.2f} m", flush=True)

np.savez_compressed(OUT, **res)
print("saved", OUT)
