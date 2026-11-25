# Hair for people.py's bodies, grown by human.py into the skin's mesh (so it shares the skin's UV square and maps;
# skin.py paints its strands). Our own, from the head itself (no hair asset):
#   - a shell over the scalp: the scalp's faces lifted off the head along their normals by the hair's depth, which
#     runs to nothing at its edge (just under the skin there, so the painted hairline carries on past it)
#   - him: a short textured crop, about 1 cm on top, the sides and back faded to the skin (skin.py's painted
#     fade), loose tufts on top; the strands from the crown forward and out
#   - her: sleek, pulled back from the hairline into a low bun at the back of the head (hair about 6 mm deep);
#     the bun a rounded knot with the coil's groove running round it, its strands wound in toward the middle
#   the depth eases in over 2 cm from the hair's edge (measured over the head), so it rises out of the painted
#   hairline with no step
# Each vertex of the hair carries the way its strands lie ("flow", along the surface) for skin.py.
import heapq, math
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
    kl = b.verts.layers.float.get("hairk") or b.verts.layers.float.new("hairk")      # 0 at the hair's edge, 1 full
    eyeZ = (eyeL.z + eyeR.z) / 2
    ears = [Vector() for _ in range(2)]; cnt = [0, 0]
    for v in b.verts:
        if wt(v[SRC], "ears") > 0.5:
            k = 0 if v.co.x > 0 else 1; ears[k] += v.co; cnt[k] += 1
    ears = [e / max(1, c) for e, c in zip(ears, cnt)]
    head = [v for v in b.verts if v.co.z > mouth.z - 0.03 and abs(v.co.x) < 0.14]
    top = max(head, key=lambda v: v.co.z).co.copy()

    # the hair's depth at each vertex of the head (metres; 0 = none), before it is eased in from its edge
    def depth(v):
        p = v.co; s = wt(v[SRC], "scalp")
        if s < 0.5: return 0.0
        if she: return 0.006
        d = 0.0095 * sm(eyeZ + 0.07, eyeZ + 0.1, p.z)          # the sides and back faded to the skin
        return d * (1 + 0.15 * noise.noise(p * 70.0) + 0.07 * noise.noise(p * 160.0))   # loose tufts

    D = {v.index: depth(v) for v in head}
    shell = [f for f in b.faces if all(D.get(v.index, 0.0) > 0.0 for v in f.verts)]
    # eased in from the edge over the surface (2 cm), so it rises out of the painted hairline with no step
    inshell = set(shell); sv = {v for f in shell for v in f.verts}
    edge = {v for f in shell for e in f.edges if sum(1 for g in e.link_faces if g in inshell) == 1 for v in e.verts}
    G = {v: (0.0 if v in edge else math.inf) for v in sv}
    pq = [(0.0, v.index, v) for v in edge]; heapq.heapify(pq)
    while pq:
        d, _, v = heapq.heappop(pq)
        if d > G[v]: continue
        for e in v.link_edges:
            o = e.other_vert(v)
            if o in G and d + e.calc_length() < G[o]: G[o] = d + e.calc_length(); heapq.heappush(pq, (G[o], o.index, o))
    FULL = 0.006 if she else 0.0095
    for v in sv: D[v.index] *= sm(0.0, 0.02, G[v])
    # the bun's middle (hers): low at the back of the head, at about the bottom of the ears
    if she:
        zb = (ears[0].z + ears[1].z) / 2 - 0.012
        back = max((v for v in head if abs(v.co.z - zb) < 0.012 and abs(v.co.x) < 0.02), key=lambda v: v.co.y)
        bn = Vector((0, 1, -0.35)).normalized()
        bc = back.co + bn * 0.013
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
            nv[fl] = flow_at(v.co, v.normal); nv[kl] = min(1.0, D[v.index] / FULL); vmap[v.index] = nv
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
        # the bun: hair wound into a low knot, a rounded mound flattened against the head (3 cm out each side,
        # 2.6 cm up and down, 2 cm off the head), the coil showing as a groove running round it to the middle;
        # its strands wind round it, drawn in toward the middle
        Ra, Rx, Rv, NU, NV = 0.023, 0.034, 0.03, 40, 18
        tx = Vector((1, 0, 0)); tv = bn.cross(tx).normalized()
        def at(ph, th):
            q = bc + bn * (math.cos(th) * Ra) + (tx * (math.cos(ph) * Rx) + tv * (math.sin(ph) * Rv)) * math.sin(th)
            nrm = (bn * (math.cos(th) / Ra) + (tx * (math.cos(ph) / Rx) + tv * (math.sin(ph) / Rv)) * math.sin(th)).normalized()
            q += nrm * (0.0014 * math.sin(2.0 * ph + 9.0 * th + 0.8 * noise.noise(q * 40.0)) + 0.0012 * noise.noise(q * 70.0))
            around = (tx * (-math.sin(ph) * Rx) + tv * (math.cos(ph) * Rv)).normalized()
            inward = -(bn * (-math.sin(th) * Ra) + (tx * (math.cos(ph) * Rx) + tv * (math.sin(ph) * Rv)) * math.cos(th)).normalized()
            return q, (around * math.cos(math.radians(28)) + inward * math.sin(math.radians(28))).normalized()
        Rm = (Rx + Rv) / 2
        def vert(q, f):
            v = b.verts.new(q); v[SRC] = -1; v[fl] = f; v[kl] = 1.0; return v
        pole = vert(*at(0.0, 0.0))
        rows = [[vert(*at(2 * math.pi * i / NU, math.pi * 0.62 * (j + 1) / NV)) for i in range(NU)] for j in range(NV)]
        bun = []
        def face(vs, uvs):
            nf = b.faces.new(vs)
            for l, (u_, w_) in zip(nf.loops, uvs): l[uvl].uv = (u_ * Rm + 3.0, w_ * Rm + 3.0)
            nf[hl] = 1; nf.smooth = True; bun.append(nf)
        dth = math.pi * 0.62 / NV
        for i in range(NU):
            i2 = (i + 1) % NU; a0, a1 = 2 * math.pi * i / NU, 2 * math.pi * (i + 1) / NU
            face([pole, rows[0][i], rows[0][i2]], [((a0 + a1) / 2, 0.0), (a0, dth), (a1, dth)])
            for j in range(NV - 1):
                face([rows[j][i], rows[j + 1][i], rows[j + 1][i2], rows[j][i2]],
                     [(a0, dth * (j + 1)), (a0, dth * (j + 2)), (a1, dth * (j + 2)), (a1, dth * (j + 1))])
        bmesh.ops.recalc_face_normals(b, faces=bun)
        bun[0].normal_update()
        if bun[0].normal.dot(bn) < 0:                        # the outer pole faces away from the head
            bmesh.ops.reverse_faces(b, faces=bun)
        # its open side, 0.62 of the way round, lies under the hair on the head
        new += bun
    b.normal_update()
    return len(new), len(under)
