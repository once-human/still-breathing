# Hair for people.py's bodies, grown by human.py into the skin's mesh (so it shares the skin's UV square and maps;
# skin.py paints its strands). Our own, from the head itself (no hair asset):
#   - a shell over the scalp: the scalp's faces lifted off the head along their normals by the hair's depth, which
#     runs to nothing at its edge (just under the skin there, so the painted hairline carries on past it)
#   - him: a short textured crop, about 1.3 cm on top, the sides and back faded to the skin (skin.py's painted
#     fade), loose tufts on top; the strands from the crown forward and out
#   - her: sleek, pulled back from the hairline into a low bun at the back of the head (hair about 6 mm deep);
#     the bun a coil of hair, its strands wound round it
# Each vertex of the hair carries the way its strands lie ("flow", along the surface) for skin.py.
import math
import bmesh
from mathutils import Vector, noise


def sm(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t)


def along_surface(d, n):
    d = d - n * d.dot(n)
    return d.normalized() if d.length > 1e-9 else n.orthogonal().normalized()


def grow(b, SRC, wt, she, eyeL, eyeR, mouth):
    """b: the skin (posed, metres); SRC: its layer of the body's vertex index; wt(i, group). Adds the hair's faces
    to b, marked by the face layer "hair" = 1, with a vertex layer "flow". Returns (hair faces, skin faces cut)."""
    b.verts.ensure_lookup_table(); b.faces.ensure_lookup_table()
    uvl = b.loops.layers.uv.active
    hl = b.faces.layers.int.get("hair") or b.faces.layers.int.new("hair")
    fl = b.verts.layers.float_vector.get("flow") or b.verts.layers.float_vector.new("flow")
    eyeZ = (eyeL.z + eyeR.z) / 2
    ears = [Vector() for _ in range(2)]; cnt = [0, 0]
    for v in b.verts:
        if wt(v[SRC], "ears") > 0.5:
            k = 0 if v.co.x > 0 else 1; ears[k] += v.co; cnt[k] += 1
    ears = [e / max(1, c) for e, c in zip(ears, cnt)]
    head = [v for v in b.verts if v.co.z > mouth.z - 0.03 and abs(v.co.x) < 0.14]
    top = max(head, key=lambda v: v.co.z).co.copy()

    # the hair's depth at each vertex of the head (metres; 0 = none)
    def depth(v):
        p = v.co; s = wt(v[SRC], "scalp")
        if s < 0.3: return 0.0
        dy = p.y - mouth.y
        front = 1 - sm(0.05, 0.1, dy)                       # the face side of the head
        earD = min(((p - e) * Vector((1, 1, 0.7))).length for e in ears)
        if she:
            hz = eyeZ + 0.046
            d = 0.0065 * (1 - front * (1 - sm(hz, hz + 0.022, p.z)))
            d *= sm(mouth.z - 0.02, mouth.z + 0.02, p.z) * sm(0.022, 0.04, earD)
        else:
            hz = eyeZ + 0.054
            d = 0.013 * (1 - front * (1 - sm(hz, hz + 0.026, p.z)))
            d *= sm(eyeZ + 0.068, eyeZ + 0.105, p.z)          # the sides and back faded to the skin
            d *= 1 + 0.28 * noise.noise(p * 70.0) + 0.12 * noise.noise(p * 160.0)   # tufts
        return max(0.0, d * sm(0.3, 0.6, s))

    D = {v.index: depth(v) for v in head}
    shell = [f for f in b.faces if all(D.get(v.index, 0.0) > 0.0 for v in f.verts)]
    # the bun's middle (hers): low at the back of the head, at about the bottom of the ears
    if she:
        zb = (ears[0].z + ears[1].z) / 2 - 0.012
        back = max((v for v in head if abs(v.co.z - zb) < 0.012 and abs(v.co.x) < 0.02), key=lambda v: v.co.y)
        bn = Vector((0, 1, -0.35)).normalized()
        bc = back.co + bn * 0.02
    crown = top + Vector((0, 0.035, -0.012))

    def flow_at(p, n):
        if she: return along_surface(bc - p, n)
        d = along_surface(p - crown, n)
        return (d + Vector((0, -0.25, 0))).normalized()     # combed a little forward

    # the shell: a copy of those faces, lifted
    vmap = {}
    for f in shell:
        for v in f.verts:
            if v.index in vmap: continue
            d = D[v.index] - 0.0006                         # at the edge just under the skin
            nv = b.verts.new(v.co + v.normal * d); nv[SRC] = -1
            nv[fl] = flow_at(v.co, v.normal); vmap[v.index] = nv
    new = []
    for f in shell:
        nf = b.faces.new([vmap[v.index] for v in f.verts])
        for l_new, l_old in zip(nf.loops, f.loops): l_new[uvl].uv = l_old[uvl].uv
        nf[hl] = 1; nf.smooth = True; new.append(nf)
    # the skin under the hair is never seen: cut it
    under = [f for f in shell if all(D[v.index] > 0.003 for v in f.verts)]
    bmesh.ops.delete(b, geom=under, context="FACES_ONLY")
    loose = [v for v in b.verts if not v.link_faces]
    bmesh.ops.delete(b, geom=loose, context="VERTS")

    if she:
        # the bun: a coil, a little flattened against the head; strands wound round it at 35 degrees
        R, r, NU, NV = 0.026, 0.016, 48, 16
        ax = bn; t1 = ax.cross(Vector((1, 0, 0))).normalized(); t2 = ax.cross(t1)
        ring = []
        for i in range(NU):
            th = 2 * math.pi * i / NU
            c0 = bc + (t1 * math.cos(th) + t2 * math.sin(th)) * R
            rad = (t1 * math.cos(th) + t2 * math.sin(th))
            row = []
            for j in range(NV):
                ph = 2 * math.pi * j / NV
                q = c0 + (rad * math.cos(ph) + ax * math.sin(ph) * 0.8) * r
                q += (q - bc).normalized() * 0.0015 * noise.noise(q * 90.0)
                v = b.verts.new(q); v[SRC] = -1
                tang = (-t1 * math.sin(th) + t2 * math.cos(th))
                tw = (-rad * math.sin(ph) + ax * math.cos(ph))
                v[fl] = (tang * math.cos(math.radians(35)) + tw * math.sin(math.radians(35))).normalized()
                row.append(v)
            ring.append(row)
        for i in range(NU):
            for j in range(NV):
                i2, j2 = (i + 1) % NU, (j + 1) % NV
                nf = b.faces.new([ring[i][j], ring[i2][j], ring[i2][j2], ring[i][j2]])
                # UVs in metres (packing evens the scale); the seams are where i or j wraps
                us = [i, i + 1, i + 1, i]; vs = [j, j, j + 1, j + 1]
                for l, u_, w_ in zip(nf.loops, us, vs):
                    l[uvl].uv = (u_ * 2 * math.pi * R / NU + 2.0, w_ * 2 * math.pi * r / NV + 2.0)
                nf[hl] = 1; nf.smooth = True; new.append(nf)
        bmesh.ops.recalc_face_normals(b, faces=new[-NU * NV:])     # a closed coil: all of it facing out
    b.normal_update()
    return len(new), len(under)
