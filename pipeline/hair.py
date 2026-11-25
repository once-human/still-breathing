# Hair for people.py's bodies, grown by human.py into the skin's mesh (so it shares the skin's UV square and maps;
# skin.py paints its strands). Our own, from the head itself (no hair asset):
#   - a shell over the scalp: the scalp's faces lifted off the head along their normals by the hair's depth, which
#     runs to nothing at its edge (just under the skin there, so the painted hairline carries on past it)
#   - him: a textured quiff: longer on top, swept up off the forehead and back (cards.py lifts it), the sides
#     and back faded to the skin (skin.py's painted fade)
#   - her: sleek, pulled back from the hairline into a high ponytail at the back of the crown (hair about 6 mm
#     deep on the head); the ponytail gathered tight where it's tied, full just after, falling over the back of
#     the head and tapering to its ends above the nape, its strands running down it
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
        d = 0.011 * sm(eyeZ + 0.055, eyeZ + 0.085, p.z)        # the sides and back faded to the skin
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
    FULL = 0.006 if she else 0.011
    for v in sv: D[v.index] *= sm(0.0, 0.02, G[v])
    # where her ponytail is tied: high at the back of the crown
    if she:
        zb = eyeZ + 0.07
        back = max((v for v in head if abs(v.co.z - zb) < 0.01 and abs(v.co.x) < 0.02), key=lambda v: v.co.y)
        bn = back.normal.copy()
        bc = back.co + bn * 0.004
    crown = top + Vector((0, 0.035, -0.012))

    def flow_at(p, n):
        if she: return along_surface(bc - p, n)
        # up off the forehead and back over the top, opening out a little to the sides
        return along_surface(Vector((p.x * 1.5, 1.0, 0.35)), n)

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
        # the ponytail: a tube of hair from the tie, out and a little up, then falling under its weight over the
        # back of the head (kept off it), 20 cm long; tight at the tie, full 3 cm on, tapering to its ends
        from mathutils.bvhtree import BVHTree
        bvh = BVHTree.FromBMesh(b)
        tl = b.verts.layers.float.get("tail") or b.verts.layers.float.new("tail")
        L, NS_, NU = 0.2, 40, 18
        def rad(s_):
            if s_ < 0.03: return 0.009 + 0.011 * sm(0.0, 0.03, s_)
            return 0.003 + 0.017 * (1 - (s_ - 0.03) / (L - 0.03)) ** 0.8
        pts = [bc.copy()]; d = (bn + Vector((0, 0, 0.35))).normalized()
        for k in range(1, NS_ + 1):
            s_ = L * k / NS_
            d = (d + Vector((0, 0, -1)) * (0.16 if s_ < 0.08 else 0.1)).normalized()
            q = pts[-1] + d * (L / NS_)
            for _ in range(3):                                 # rests on the back of the head, never in it
                hit = bvh.find_nearest(q)
                if hit[0] is None: break
                gap = rad(s_) * 0.85 + 0.003
                if (q - hit[0]).length < gap and (q - hit[0]).dot(hit[1]) > -1e-4:
                    q = hit[0] + hit[1] * gap
            d = (q - pts[-1]).normalized(); pts.append(q)
        side = Vector((1, 0, 0))
        rings = []
        for k, c in enumerate(pts):
            s_ = L * k / NS_
            T = (pts[min(k + 1, NS_)] - pts[max(k - 1, 0)]).normalized()
            side = (side - T * side.dot(T)).normalized(); up = T.cross(side)
            r = rad(s_); row = []
            for i_ in range(NU):
                a = 2 * math.pi * i_ / NU
                q = c + (side * math.cos(a) + up * math.sin(a) * 0.85) * r
                q += (q - c).normalized() * 0.0012 * noise.noise(q * 60.0) * min(1.0, s_ / 0.02)
                v = b.verts.new(q); v[SRC] = -1; v[fl] = T.copy(); v[kl] = 1.0; v[tl] = 1.0; row.append(v)
            rings.append(row)
        tip = b.verts.new(pts[-1] + (pts[-1] - pts[-2]).normalized() * 0.004)
        tip[SRC] = -1; tip[fl] = (pts[-1] - pts[-2]).normalized(); tip[kl] = 1.0; tip[tl] = 1.0
        pony = []
        circ = 2 * math.pi * 0.015
        def face(vs, uvs):
            nf = b.faces.new(vs)
            for l, (u_, w_) in zip(nf.loops, uvs): l[uvl].uv = (u_ + 3.0, w_ + 3.0)
            nf[hl] = 1; nf.smooth = True; pony.append(nf)
        for k in range(NS_):
            for i_ in range(NU):
                i2 = (i_ + 1) % NU
                u0, u1 = circ * i_ / NU, circ * (i_ + 1) / NU; w0, w1 = L * k / NS_, L * (k + 1) / NS_
                face([rings[k][i_], rings[k][i2], rings[k + 1][i2], rings[k + 1][i_]], [(u0, w0), (u1, w0), (u1, w1), (u0, w1)])
        for i_ in range(NU):
            i2 = (i_ + 1) % NU
            face([rings[NS_][i_], rings[NS_][i2], tip], [(circ * i_ / NU, L), (circ * (i_ + 1) / NU, L), (circ * (i_ + 0.5) / NU, L + 0.004)])
        # every face's front out from the tube's middle
        for f in pony:
            f.normal_update()
            c_ = f.calc_center_median(); k = min(range(len(pts)), key=lambda j: (pts[j] - c_).length)
            if f.normal.dot(c_ - pts[k]) < 0: f.normal_flip()
        new += pony
    b.normal_update()
    return len(new), len(under)
