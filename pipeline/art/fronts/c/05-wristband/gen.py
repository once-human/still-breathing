#!/usr/bin/env python3
"""
01 crowd, front 05: "wristband". Centre chest, about 20 cm.
The woven band everyone had on their wrist both nights, cut off after the show and kept: laid flat in a slow curve,
marigold, again.. again.. again.. woven along it in the dark of the weave, its cream selvedge running along both
edges, the plastic one-way clasp still on one end and a clean scissor cut at the other.
    R=1 python3 gen.py   draft (4.7 px/mm)      python3 gen.py   final (94 px/cm)
"""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import pen

WMM, HMM = 212, 58
h, a = pen.boot(WMM, HMM, seed=1505, layers=('line', 'Y'))
rng = a.rng
BW = 15.0                                   # the band's width

# the band's centre line: a slow S, laid down by hand
ctrl = [(30, 33.5), (70, 27.0), (112, 30.5), (152, 35.0), (196, 27.5)]
path = h.catmull(ctrl, step=0.5)
N = h.normals(path)


def edge(d):
    return [(x + nx * d, y + ny * d) for (x, y), (nx, ny) in zip(path, N)]


top, bot = edge(-BW / 2), edge(BW / 2)
# the cut at the right end: a scissor cut on a slant
cut = 4.0
top[-1] = (top[-1][0] - cut, top[-1][1])
band = top + bot[::-1]
a.fill(band, 'Y')
# the selvedge: a cream thread line just inside each edge, broken where the weave turns it under
for d in (-BW / 2 + 1.75, BW / 2 - 1.75):
    e = edge(d)
    i, n = 0, len(e)
    while i < n - 8:
        ln = int(rng.uniform(26, 60))
        seg = e[i:min(n - 6, i + ln)]
        if len(seg) > 4:
            a.ink(seg, 1.15, layer='line', a0=0.5, a1=0.6, pv=0.08)
            a.knock(sum(([(x + 0, y)] for x, y in []), []))
        i += ln + int(rng.uniform(3, 6))

# the word, woven: again.. three times along the band, knocked out of the marigold so the shirt shows through
S = 10.6
xh = 0.52 * S
s = 18.0
for k in range(3):
    used = pen.along(a, 'Y', 'again', 'bric', S, path, s0=s, weight=800, lift=-xh / 2, erase=True, jit=0.02, turn=0.01,
                     track=0.15)
    s += used + 1.2
    # its two dots in cream, on the band's centre
    for j in range(2):
        d = s + 1.3 + j * 3.4
        i = min(len(path) - 1, int(d / 0.5))
        (x, y), (nx, ny) = path[i], N[i]
        pen.disc(a, x - nx * (0.13 * S) + nx * 0, y - ny * (0.13 * S) - ny * (-0.0), 0.125 * S, 'line', rng=rng)
    s += 9.5 + 14.0

# the clasp at the left end: a cream plastic slider wider than the band, two ridges moulded across it
(cx, cy), (nx, ny) = path[0], N[0]
tx, ty = -ny, nx                            # along the band
L, Wd = 10.0, BW + 4.4
corners = [(cx + tx * u + nx * v, cy + ty * u + ny * v) for u, v in ((-2.0, -Wd / 2), (L, -Wd / 2), (L, Wd / 2), (-2.0, Wd / 2))]
ring = []
for i in range(4):
    p0, p1 = corners[i], corners[(i + 1) % 4]
    ring += [(p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t) for t in (0.12, 0.88)]
body = h.catmull(ring, closed=True, step=0.3)
a.knock(body)
a.fill(body, 'line')
for u in (2.4, 5.6):
    a.carve([(cx + tx * u + nx * (-Wd / 2 + 2.6), cy + ty * u + ny * (-Wd / 2 + 2.6)),
             (cx + tx * u + nx * (Wd / 2 - 2.6), cy + ty * u + ny * (Wd / 2 - 2.6))], 1.2, layer='line', wob=0.05, trem=0,
            a0=0.8, a1=0.8)
# the tail through the clasp, a short stub of band out its far side
stub = [(cx + tx * u + nx * v, cy + ty * u + ny * v) for u, v in ((-2.0, -BW / 2 + 0.6), (-9.0, -BW / 2 + 1.4), (-9.6, BW / 2 - 1.0),
                                                                   (-2.0, BW / 2 - 0.6))]
a.fill(stub, 'Y')

pen.save(a, __file__, order=('Y', 'line'), crops=[(40, 32), (120, 32)],
         placement={'where': 'centre chest', 'top_cm': 12})