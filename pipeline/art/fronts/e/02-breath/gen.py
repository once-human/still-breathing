# 02 breath: the wearer's own breath leaving the collar and rising over the shoulder in one stream of three exhales,
# warm where it leaves, cooling and tearing apart as it rises. Riso-style: one screen per band, each band its own cut.
#   ulimit -v 2500000; R=2 python3 gen.py     # draft
#   ulimit -v 2500000; python3 gen.py         # final art.png (17 cm at 94 px/cm) + pair.png
import os, sys, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import heat
H = heat.setup(17.0, 8.0)
from PIL import Image, ImageDraw, ImageChops
HERE = os.path.dirname(os.path.abspath(__file__))
rng = random.Random(2)
LAY = ('violet', 'magenta', 'amber', 'cream')
art = H.Art(seed=21, layers=LAY + ('cut',))
art.rng = rng

# One stream, three breaths: the newest just under the neck rib (right, toward the centre front), the one before it
# lifted and overlapping it, the oldest high toward the shoulder, tearing into wisps. Spacing uneven on purpose.
PUFFS = [  # centre, size, heat (0 cold .. 1 just breathed), seed
    ((440, 162), 44, 1.0, 1),
    ((322, 116), 62, 0.6, 2),
    ((168, 90), 64, 0.24, 3),
]
FLOW = (-1.0, -0.42)                       # the way the breath drifts (up and out)
fl = math.hypot(*FLOW); FLOW = (FLOW[0] / fl, FLOW[1] / fl)


def billow(x, y, r, q):
    """one billow: an irregular round, its own hand"""
    m = 15
    ph = q.uniform(0, math.tau)
    pts = []
    for j in range(m):
        a = ph + math.tau * j / m
        rr = r * q.uniform(0.9, 1.07)
        pts.append((x + math.cos(a) * rr * 1.08, y + math.sin(a) * rr * 0.9))
    return H.catmull(pts, closed=True, step=1.5)


def mask_of(polys):
    m = Image.new('L', (H.W, H.H), 0)
    d = ImageDraw.Draw(m)
    for p in polys:
        d.polygon(H.P(p), fill=255)
    return m


def knife(hx, hy, reach, bend, q):
    """a decisive cut across the breath: everything on the mouth side of a nearly straight line `reach` units up
    the flow from the hot point"""
    fx, fy = FLOW
    nx, ny = -fy, fx
    cx, cy = hx + fx * reach, hy + fy * reach
    a = (cx + nx * 200, cy + ny * 200)
    b = (cx - nx * 200, cy - ny * 200)
    mid = (cx + fx * bend * q.uniform(0.6, 1.2), cy + fy * bend * q.uniform(0.6, 1.2))
    back = [(b[0] - fx * 400, b[1] - fy * 400), (a[0] - fx * 400, a[1] - fy * 400)]
    return [a, mid, b] + back


def zone(hx, hy, r, q):
    fa = math.atan2(FLOW[1], FLOW[0])
    pts = [(hx + math.cos(math.tau * j / 20) * r * q.uniform(0.88, 1.1) * (1.0 + 0.45 * max(0, math.cos(math.tau * j / 20 - fa))),
            hy + math.sin(math.tau * j / 20) * r * 0.85 * q.uniform(0.88, 1.1)) for j in range(20)]
    return heat.wobble_shape(pts, q, r * 0.03)


for pi, ((cx, cy), size, h, seed) in enumerate(PUFFS):
    q = random.Random(seed * 17)
    # a few big billows with deep notches between them, heaped on the top side
    lobes = [(cx, cy - size * 0.16, size * 0.6)]
    for a, d, r in ((3.3, 0.72, 0.46), (3.95, 0.66, 0.5), (4.75, 0.52, 0.44), (5.6, 0.74, 0.4), (0.4, 0.62, 0.38),
                    (2.3, 0.5, 0.4)):
        a += q.uniform(-0.18, 0.18)
        lobes.append((cx + math.cos(a) * size * d * 1.2, cy + math.sin(a) * size * d * 0.7, size * r * q.uniform(0.9, 1.1)))
    hx, hy = cx - FLOW[0] * size * 0.75, cy - FLOW[1] * size * 0.75 + size * 0.12   # the side it came from
    if pi == 2:
        lobes = lobes[:5]
    def cool(l):   # 0 at the mouth side .. 1 at the far, cool side of this puff
        return max(0.0, min(1.0, ((l[0] - hx) * FLOW[0] + (l[1] - hy) * FLOW[1]) / (size * 1.8)))
    # violet: the whole breath
    art.add('violet', mask_of([billow(x, y, r, random.Random(seed * 100 + li)) for li, (x, y, r) in enumerate(lobes)]))
    # the warm bands: big on the mouth side (they break through to the breath's own edge there), shrinking toward the
    # cool side so the far edge keeps a wide violet rim; each its own billows, each stopped by its own cut
    for i, (layer, k, need, cut) in enumerate((('magenta', 0.68, 0.15, ('zone', 1.15)), ('amber', 0.5, 0.45, ('knife', 0.75)),
                                                ('cream', 0.36, 0.8, ('zone', 0.5)))):
        if h < need:
            continue
        q2 = random.Random(seed * 1000 + i)
        polys = []
        for li, (x, y, r) in enumerate(lobes):
            c = cool((x, y, r))
            sc = 1.0 - (1.0 - k) * (0.25 + 0.9 * c)
            if sc < 0.3:
                continue
            sx, sy = x + (hx - x) * 0.25 * c, y + (hy - y) * 0.25 * c
            polys.append(billow(sx, sy, r * sc, q2))
        m = mask_of(polys)
        kind, reach = cut
        rch = size * reach * (0.7 + 0.5 * h)
        m = ImageChops.multiply(m, mask_of([knife(hx, hy, rch * 1.2, size * 0.12, q2) if kind == 'knife' else zone(hx, hy, rch, q2)]))
        art.add(layer, m)
    # a carved line along the top edge of the big billow of the two older breaths: one long tapering stroke
    if pi > 0:
        x, y, r = lobes[0]
        a0 = 3.55 + q.uniform(-0.1, 0.1)
        arc = [(x + math.cos(a0 + u) * r * 0.74, y + math.sin(a0 + u) * r * 0.66) for u in (0, 0.5, 1.0, 1.5, 1.9)]
        heat.gouge(art, arc, 4.2, q, a0=2.5, a1=3.5, pv=0.35)

# the oldest breath tears: ragged scraps of it drift off ahead, each a few small billows strung along the drift
for (sx, sy, n, r0, sd) in ((118, 72, 3, 17, 7),):
    q = random.Random(sd)
    bl = [billow(sx + FLOW[0] * j * r0 * 1.0 + q.uniform(-2, 2), sy + FLOW[1] * j * r0 * 0.6 + q.uniform(-5, 5) * (j % 2),
                 r0 * (1 - 0.15 * j) * q.uniform(0.85, 1.1), q) for j in range(n)]
    art.add('violet', mask_of(bl))

order = LAY
inks = heat.finish(art, order, shifts={'magenta': (0.6, -0.4), 'amber': (-0.8, 0.6), 'cream': (0.6, 0.8)}, trim=False)
heat.out(os.environ.get('OUT', 'draft.png'), inks, heat.INK, order, HERE)
if heat.FINAL:
    heat.pair(HERE)
