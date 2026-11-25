# Hair cards over hair.py's hair: what makes it read as hair and not a painted cap. Called by human.py on the hair
# (its own bmesh, posed, metres, with hair.py's "flow" and "hairk" on each vertex); returns a new bmesh of cards.
# A card is a narrow strip of hairtex.py's strands laid over the head along the way the hair lies: from a point on
# the hair it follows the flow over the surface for its length, conforming to the head as it goes, a little above
# it (each card a layer: the pile builds up), its sides wrapped round the head. The strands' own edges break up the
# silhouette and the hairline, and the light runs along them.
#   - her bob: long cards (7 to 13 cm) from the parting over the head and on down, lying close; sparse cards at
#     the hairline (single strands coming out of the skin), a few loose hairs over the top; layered cards down the
#     hanging part to its ends
#   - him: a quiff: at the front long cards (up to 5.5 cm) rising steeply off the forehead and curling back,
#     shorter and flatter toward the crown, shorter and sparser toward the faded sides
# The cards' normals are the head's (so the pile shades as one mass, not as so many flat strips); their front faces
# away from the head (the viewer draws only the fronts). UVs: hairtex.py's 16 strips across, v from the root (top of
# the picture) to the tip; strips 0-9 the main cards, 10-15 the sparse ones.
import math, random
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

NS = 16


def sm(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t)


def grow(hb, she, colour, seed=1618):
    """hb: the hair (bmesh). colour: the hair's linear RGB. Returns (cards bmesh, its normals per vertex)."""
    rnd = random.Random(seed)
    hb.verts.ensure_lookup_table(); hb.faces.ensure_lookup_table(); hb.normal_update()
    fl = hb.verts.layers.float_vector["flow"]; kl = hb.verts.layers.float["hairk"]
    tl = hb.verts.layers.float.get("tail")                   # her ponytail (hair.py)
    # the front of his hair (where the quiff rises) and its back, over the head (not the ponytail)
    ys = [v.co.y for v in hb.verts if v[kl] > 0.5 and not (tl and v[tl] > 0.5)]
    y0, y1 = min(ys), max(ys)
    bvh = BVHTree.FromBMesh(hb)

    def at(p):
        """the nearest point of the hair: (point, normal, flow along the surface, hairk, distance)"""
        q, _, fi, d = bvh.find_nearest(p)
        if q is None: return None
        f = hb.faces[fi]
        ws = [1.0 / ((v.co - q).length + 1e-5) for v in f.verts]; s = sum(ws)
        fw = sum((Vector(v[fl]) * w for v, w in zip(f.verts, ws)), Vector()) / s
        nn = sum((v.normal * w for v, w in zip(f.verts, ws)), Vector()).normalized()
        k = sum(v[kl] * w for v, w in zip(f.verts, ws)) / s
        t = fw - nn * fw.dot(nn)
        if t.length < 1e-6: return None
        return q, nn, t.normalized(), k, d, (sum(v[tl] for v in f.verts) / len(f.verts) if tl else 0.0)

    def trace(p0, L, K):
        pts, p = [], p0
        for _ in range(K + 1):
            r = at(p)
            if r is None or r[4] > 0.004 or r[3] < 0.03: break
            q, n, t, k = r[:4]
            if pts and (q - pts[-1][0]).length < 0.25 * L / K: break      # stalled (at an edge)
            pts.append((q, n, t, k)); p = q + t * (L / K)
        return pts

    # where cards start: anywhere on the hair by area, more toward its edge (the hairline has to be covered by
    # cards that start there)
    faces = [f for f in hb.faces]
    wts = []
    for f in faces:
        k = sum(v[kl] for v in f.verts) / len(f.verts)
        wts.append(f.calc_area() * (1 + (3.0 if she else 1.5) * (1 - k)) * (0.0 if k < 0.02 else 1.0))
    area = sum(f.calc_area() for f in faces)
    # layers deep: how many cards cover a point, on average
    if she: N = int(area * 5.5 / (0.07 * 0.009)) + 25
    else: N = int(area * 4.5 / (0.034 * 0.009))
    cum, s = [], 0.0
    for w in wts: s += w; cum.append(s)

    def seed_point():
        x = rnd.uniform(0, s); lo, hi = 0, len(cum) - 1
        while lo < hi:
            m = (lo + hi) // 2
            if cum[m] < x: lo = m + 1
            else: hi = m
        vs = [v.co for v in faces[lo].verts]
        a, b = rnd.random(), rnd.random()
        if a + b > 1: a, b = 1 - a, 1 - b
        return vs[0] + (vs[1] - vs[0]) * a + (vs[2] - vs[0]) * b

    out = bmesh.new()
    uvl = out.loops.layers.uv.new("UVMap")
    col = out.verts.layers.float_color.new("albedo")
    normals = []
    made = 0
    for c in range(N):
        p0 = seed_point()
        r0 = at(p0)
        if r0 is None: continue
        k0 = r0[3]
        wisp = she and c < 25                                    # her loose hairs over the top
        tail = r0[5] > 0.5
        if she and tail:                                       # her bob's hanging part: down to its ends
            L = rnd.uniform(0.06, 0.12); W = rnd.uniform(0.007, 0.011); K = 10
            sparse = rnd.random() < 0.15
            h0 = rnd.uniform(0.0004, 0.003); lift = 0.0
        elif she:                                              # from the parting over the head, on down
            L = rnd.uniform(0.07, 0.13); W = rnd.uniform(0.006, 0.01); K = 10
            sparse = wisp or k0 < 0.45
            h0 = 0.0015 + rnd.uniform(0, 0.001) if wisp else (0.0007 if k0 < 0.45 else rnd.uniform(0.0004, 0.0013))
            lift = 0.0
        else:
            f = max(0.0, min(1.0, (y1 - p0.y) / (y1 - y0)))     # 1 at the front, 0 at the back
            L = (0.022 + 0.033 * f ** 1.5) * rnd.uniform(0.8, 1.15) * (0.55 + 0.45 * k0); W = rnd.uniform(0.007, 0.011); K = 6
            sparse = k0 < 0.5
            h0 = 0.0006; lift = math.tan(math.radians((12 + 34 * f ** 1.3) * rnd.uniform(0.75, 1.15) * (0.4 + 0.6 * k0)))
        pts = trace(p0, L, K)
        if len(pts) < 3: continue
        arc = [0.0]
        for i in range(1, len(pts)): arc.append(arc[-1] + (pts[i][0] - pts[i - 1][0]).length)
        Lt = arc[-1]
        if Lt < 0.4 * L: continue
        strip = rnd.randrange(10, 16) if sparse else rnd.randrange(0, 10)
        u0, u1 = strip / NS + 0.6 / 1024, (strip + 1) / NS - 0.6 / 1024
        tone = rnd.uniform(0.8, 1.2)
        rows = []
        for i, (q, n, t, k) in enumerate(pts):
            sa = arc[i]; tt = sa / Lt
            side = n.cross(t).normalized()
            w = W * (1 - (0.3 if not she else 0.1) * tt)
            h = h0 + (sa * lift * (1 - 0.5 * tt) if lift else 0.0008 * tt)
            fold = (0.1 if she else 0.14) * w
            row = []
            for a in (-0.5, 0.0, 0.5):
                if a == 0.0:
                    pq, pn = q, n
                else:
                    r = at(q + side * (a * w))
                    pq, pn = (r[0], r[1]) if r else (q + side * (a * w), n)
                hh = h if a == 0.0 else max(0.0004, h - fold)
                v = out.verts.new(pq + pn * hh)
                g = tone * (0.78 + 0.32 * tt)
                v[col] = (colour[0] * g, colour[1] * g, colour[2] * g, 1.0)
                normals.append(pn.copy())
                row.append((v, u0 + (a + 0.5) * (u1 - u0), 1.0 - tt))
            rows.append(row)
        for i in range(len(rows) - 1):
            A, B = rows[i], rows[i + 1]
            for j in range(2):
                quad = [A[j], B[j], B[j + 1], A[j + 1]]          # its front away from the head
                f = out.faces.new([x[0] for x in quad])
                f.smooth = True
                for l, x in zip(f.loops, quad): l[uvl].uv = (x[1], x[2])
        made += 1
    print("hair cards %d (%d verts)" % (made, len(out.verts)), flush=True)
    return out, normals
