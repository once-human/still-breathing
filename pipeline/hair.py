# Hair for people.py's bodies, grown by human.py into the skin's mesh (so it shares the skin's UV square and maps;
# skin.py paints its strands). Our own, from the head itself (no hair asset):
#   - a shell over the scalp: the scalp's faces lifted off the head along their normals by the hair's depth, which
#     runs to nothing at its edge (just under the skin there, so the painted hairline carries on past it)
#   - him: a textured quiff: longer on top, swept up off the forehead and back (cards.py lifts it), the sides
#     and back faded to the skin (skin.py's painted fade)
#   - her: a bob, open: parted in the middle, over the head with some body, falling straight from the head's
#     widest to just under the jaw (a little longer toward the face), the ends turned under, framing the face
#   the depth eases in over 2 cm from the hair's edge (measured over the head; 9 mm along his forehead, where the
#   quiff grows from the hairline itself), so it rises out of the painted hairline with no step
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
    cy = (ears[0].y + ears[1].y) / 2

    def front(p):
        """1 over the forehead, 0 from the temples round: where his hair grows full right from the hairline"""
        th = math.degrees(math.atan2(abs(p.x), -(p.y - cy)))
        return 1.0 - sm(45.0, 70.0, th)

    def depth(v):
        p = v.co; s = wt(v[SRC], "scalp")
        if s < 0.5: return 0.0
        if she: return 0.006
        # the sides and back faded to the skin; over the forehead the quiff grows full from the hairline itself
        # (a band of short hair under it read as a cap's edge with the quiff set on top)
        d = 0.011 * max(front(p), sm(eyeZ + 0.055, eyeZ + 0.085, p.z))
        return d * (1 + 0.15 * noise.noise(p * 70.0) + 0.07 * noise.noise(p * 160.0))   # loose tufts

    D = {v.index: depth(v) for v in head}
    # (hers is a bob, built below on its own: no shell)
    shell = [] if she else [f for f in b.faces if all(D.get(v.index, 0.0) > 0.0 for v in f.verts)]
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
    for v in sv: D[v.index] *= sm(0.0, 0.02 if she else 0.02 - 0.011 * front(v.co), G[v])
    crown = top + Vector((0, 0.035, -0.012))

    def flow_at(p, n):
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
        # her bob: open hair, parted in the middle, over the head and falling straight from its widest to just
        # under the jaw (a little longer toward the face), the ends turned under; it frames the face, and over the
        # forehead it comes down to the skin at the hairline. Built from the head itself: rays in to the head from
        # all round, the hair standing off it by its body, and below the head's widest it hangs (never in nearer).
        from mathutils.bvhtree import BVHTree
        bvh = BVHTree.FromBMesh(b)
        tl = b.verts.layers.float.get("tail") or b.verts.layers.float.new("tail")     # 1: the hanging part
        earZ = (ears[0].z + ears[1].z) / 2
        C = Vector((0.0, (ears[0].y + ears[1].y) / 2 + 0.006, earZ + 0.012))
        OFF = 0.012
        def inward(o, d):
            hit = bvh.ray_cast(o + d * 0.3, -d, 0.3)
            return hit[0]
        NPHI, NA = 80, 24
        A_ = [math.radians(6 + 84 * k / (NA - 1)) for k in range(NA)]          # from near the top down to level
        rows = {}
        # the hairline: a rounded arch over the forehead, lower toward the temples, never a ruled line (it wanders
        # a few millimetres)
        hz_ = lambda ph: (eyeZ + 0.056 - 0.026 * sm(0.0, math.radians(64), abs(ph))
                          + 0.0022 * math.sin(7.0 * ph + 0.4) + 0.0013 * math.sin(17.0 * ph + 2.1) + 0.0007 * math.sin(31.0 * ph))
        face_w = lambda ph: sm(math.radians(66), math.radians(52), abs(ph))  # 1 over the face
        cols = []
        for jj in range(NPHI):
            ph = -math.pi + 2 * math.pi * jj / NPHI                            # 0: the front (-y)
            hd = Vector((math.sin(ph), -math.cos(ph), 0.0))
            w_ = face_w(ph); hz = hz_(ph)
            col = []; edge_done = False
            # the dome
            for a in A_:
                d = (Vector((0, 0, 1)) * math.cos(a) + hd * math.sin(a)).normalized()
                q = inward(C, d)
                if q is None: col.append(None); continue
                off = OFF * (1 - w_ * (1 - sm(hz, hz + 0.028, q.z)))
                if w_ > 0.5 and q.z < hz - 0.002:              # the face: the hair stops at the hairline, exactly
                    if col and col[-1] is not None and col[-1][2] > hz and not edge_done:
                        lo, hi = A_[len(col) - 1], a
                        for _ in range(12):                     # the ray that meets the head on the hairline
                            mid = 0.5 * (lo + hi)
                            dm = (Vector((0, 0, 1)) * math.cos(mid) + hd * math.sin(mid)).normalized()
                            qm = inward(C, dm)
                            if qm is None or qm.z < hz: hi = mid
                            else: lo = mid
                        dm = (Vector((0, 0, 1)) * math.cos(lo) + hd * math.sin(lo)).normalized(); qm = inward(C, dm)
                        if qm is not None: col.append((qm - dm * 0.0004, dm, qm.z)); edge_done = True; continue   # just under the skin: no rim
                    col.append(None); continue
                col.append((q + d * max(off, 0.0007), d, q.z))
            # below the head's widest it hangs straight, to just under the jaw (longer toward the face), ends under
            if w_ < 0.5 and col and col[-1] is not None:
                p_last = col[-1][0]; R = (p_last - Vector((0, C.y, p_last.z))).xy.length
                zend = mouth.z - 0.018 - 0.026 * (0.5 + 0.5 * math.cos(ph))
                z = p_last.z; NC = 12
                for k in range(1, NC + 1):
                    zk = p_last.z + (zend - p_last.z) * k / NC
                    q = inward(Vector((0, C.y, zk)), hd)
                    if q is not None:
                        R = max(R, (q - Vector((0, C.y, zk))).xy.length + OFF * 0.75)
                    tuck = 0.007 * sm(0.75, 1.0, k / NC)
                    pk = Vector((0, C.y, zk)) + hd * (R - tuck)
                    col.append((pk, hd, -1.0))
            cols.append(col)
        top_q = inward(C, Vector((0, 0, 1)))
        pole = b.verts.new(top_q + Vector((0, 0, OFF))); pole[SRC] = -1; pole[fl] = Vector((1, 0, 0)); pole[kl] = 1.0; pole[tl] = 0.0
        V = []
        for jj, col in enumerate(cols):
            ph = -math.pi + 2 * math.pi * jj / NPHI; hz = hz_(ph)
            vs = []
            for i_, c in enumerate(col):
                if c is None: vs.append(None); continue
                pt, d, zs = c
                v = b.verts.new(pt); v[SRC] = -1
                hang = zs < -0.5
                sx = 1.0 if pt.x >= 0 else -1.0
                front = max(0.0, -d.y)
                v[fl] = Vector((0, 0, -1)) if hang else along_surface(Vector((sx * (0.35 + 0.9 * front), 0.0, -1.0)), d)
                v[kl] = 1.0 if hang else (sm(hz - 0.002, hz + 0.02, zs) if face_w(ph) > 0.01 else 1.0)
                v[tl] = 1.0 if hang else 0.0
                vs.append(v)
            V.append(vs)
        bobf = []
        L_ = lambda jj: 0.09 * 2 * math.pi * jj / NPHI
        def face(vs, uvs):
            nf = b.faces.new(vs)
            for l, (u_, w_) in zip(nf.loops, uvs): l[uvl].uv = (u_ + 3.0, w_ + 3.0)
            nf[hl] = 1; nf.smooth = True; bobf.append(nf)
        for jj in range(NPHI):
            j2 = (jj + 1) % NPHI
            a, c_ = V[jj], V[j2]
            if a and c_ and a[0] is not None and c_[0] is not None:
                face([pole, a[0], c_[0]], [(L_(jj + 0.5), 0.0), (L_(jj), 0.01), (L_(jj + 1), 0.01)])
            for i_ in range(min(len(a), len(c_)) - 1):
                q4 = [a[i_], a[i_ + 1], c_[i_ + 1], c_[i_]]
                uv4 = [(L_(jj), 0.01 * (i_ + 1)), (L_(jj), 0.01 * (i_ + 2)), (L_(jj + 1), 0.01 * (i_ + 2)), (L_(jj + 1), 0.01 * (i_ + 1))]
                miss = [k for k, x in enumerate(q4) if x is None]
                if not miss: face(q4, uv4)
                elif len(miss) == 1:                     # where the hairline steps a row: a triangle, no notch
                    face([x for x in q4 if x is not None], [u for x, u in zip(q4, uv4) if x is not None])
        for f in bobf:                                   # every face's front away from the head
            f.normal_update()
            c0 = f.calc_center_median()
            if f.normal.dot(Vector((c0.x, c0.y - C.y, 0.0 if c0.z < C.z else c0.z - C.z))) < 0: f.normal_flip()
        new += bobf
    b.normal_update()
    return len(new), len(under)
