#!/usr/bin/env python3
"""
02 the lake: again.. drawn as land in a lake. The word sits on an island whose shore is drawn in the back's line;
round it the water is drawn the way old maps draw water, as echo lines of the shore in the lake's blue, each one a
little further out than the last, breaking up as they go, the way the back's sound rings break up. The two dots are
two islets out in the water, each with its own small echoes. Bengaluru is a city of lakes (the back ends at
Anchepalya's). Left chest, 10 cm wide.
    R=1 python3 gen.py (draft)  |  python3 gen.py (print size)
"""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import front as F

WMM, HMM = 108, 68
F.setup(WMM, HMM)
import hand
import numpy as np
from hand import Art, offset_path, resample
from PIL import Image, ImageDraw, ImageChops

art = Art(seed=402, layers=('blue', 'accent', 'key'))
rng = art.rng
EM = 15.5

# the word, set and worked by hand
m, base_px = F.word_mask('again', EM, rng, wght=760)
ww = m.width / hand.R
bb = m.getbbox()
top_mm, bot_mm = bb[1] / hand.R, bb[3] / hand.R
WX, WY = 45.0, 34.0                      # the word's centre
x0 = WX - ww / 2
base_mm = WY + (base_px / hand.R - (top_mm + bot_mm) / 2)
F.paste(art.L['key'], m, x0, base_mm, 'lb', base_px)

# the island: more land to the west than the word needs, a cove on the north shore, a smaller one to the south-west,
# a broad headland east toward the islets; the whole thing turned a few degrees
CX, CY = WX - 0.8, WY + 0.4
A, B = ww / 2 + 7.0, (bot_mm - top_mm) / 2 + 4.4
TILT = math.radians(-3.5)
harm = [(k, rng.uniform(0.35, 0.7) / k ** 0.45, rng.uniform(0, math.tau)) for k in (2, 3, 5, 7)]


def g(t, c, w):
    d = (t - c + math.pi) % math.tau - math.pi
    return math.exp(-(d / w) ** 2)


def shore(t):
    c, s = math.cos(t), math.sin(t)
    n = 3.0
    x = A * math.copysign(abs(c) ** (2 / n), c)
    y = B * math.copysign(abs(s) ** (2 / n), s)
    w = sum(a * math.sin(k * t + p) for k, a, p in harm)
    feat = (-2.0 * g(t, 4.25, 0.2)       # the north cove
            - 1.4 * g(t, 2.35, 0.16)     # the south-west cove
            + 1.6 * g(t, 3.5, 0.2)       # a headland to the west
            + 1.5 * g(t, 0.3, 0.32)      # a broad headland to the east, toward the islets
            - 0.9 * g(t, 5.7, 0.2))      # a shallow bight on the north-east
    r = 1 + (w + feat) / max(A, B) * 1.5
    px_, py_ = x * r, y * r
    return CX + px_ * math.cos(TILT) - py_ * math.sin(TILT), CY + px_ * math.sin(TILT) + py_ * math.cos(TILT)


N = 400
pts = [shore(i / N * math.tau) for i in range(N)]
pts = resample(pts + [pts[0]], 320)[:-1]
# the shore: two pulls of the pen, one heavier than the other, overlapping a little where they meet
start = rng.randrange(len(pts))
ring = pts[start:] + pts[:start]
cut1 = int(len(ring) * rng.uniform(0.5, 0.58))
art.line(ring[0:cut1:3], 1.45, layer='key', wob=0.05, trem=0.1, a0=0.6, a1=2.6)
art.line(ring[cut1 - 4::3] + ring[:2], 1.15, layer='key', wob=0.05, trem=0.1, a0=1.8, a1=0.8)


def normal_out(path):
    p2 = offset_path(path, 1.0)
    out = sum(math.hypot(q[0] - CX, q[1] - CY) - math.hypot(p[0] - CX, p[1] - CY) for p, q in zip(path, p2))
    return 1.0 if out > 0 else -1.0


SGN = normal_out(pts)
SH = np.array(pts)


ISLAND = Image.new('L', (int(WMM * 4), int(HMM * 4)), 0)
ImageDraw.Draw(ISLAND).polygon([(x * 4, y * 4) for x, y in pts], fill=255)
ISL_A = np.asarray(ISLAND)


def on_land(x, y):
    xi, yi = int(x * 4), int(y * 4)
    return 0 <= xi < ISL_A.shape[1] and 0 <= yi < ISL_A.shape[0] and ISL_A[yi, xi] > 0


def dist_shore(x, y):
    return float(np.sqrt(((SH[:, 0] - x) ** 2 + (SH[:, 1] - y) ** 2).min()))


# the islets: the two dots, out past the east headland, near the word's baseline
r_dot = 0.088 * EM
tip = max(pts, key=lambda p: p[0] + 0.4 * p[1])
islets = [(tip[0] + 6.4, tip[1] - 0.6), (tip[0] + 6.4 + 0.245 * EM, tip[1] - 0.2)]
for ix, iy in islets:
    art.dot(ix, iy, r_dot * rng.uniform(0.97, 1.04), layer='accent')
ISL_CLEAR = r_dot + 2.3


def bend(path):
    """water parts round the islets: points near one are pushed out to a clear radius, so lines bow round them"""
    out = []
    for x, y in path:
        for ix, iy in islets:
            d = math.hypot(x - ix, y - iy)
            if d < ISL_CLEAR + 1.6:
                push = ISL_CLEAR + 1.6 * (d / (ISL_CLEAR + 1.6))
                if d > 1e-6:
                    x, y = ix + (x - ix) / d * max(d, push), iy + (y - iy) / d * max(d, push)
        out.append((x, y))
    return out


# the echo lines: two close to the shore, long runs, the first nearly whole
for li, (d, w) in enumerate(((2.5, 1.3), (5.1, 1.15))):
    path = bend(offset_path(pts, SGN * d))
    n = len(path)
    i = rng.randrange(n)
    done = 0
    while done < n - 10:
        L = int(rng.uniform(60, 140) if li == 0 else rng.uniform(30, 80))
        L = min(L, n - done)
        seg = [path[(i + k) % n] for k in range(L)]
        if len(seg) >= 20:
            art.line(seg[::3] + [seg[-1]], w * rng.uniform(0.95, 1.1), layer='blue', wob=0.05, trem=0.07,
                     a0=1.2, a1=2.0)
        step = L + int(rng.uniform(5, 9) * (1 + li))
        i, done = (i + step) % n, done + step

# the open water: rows of short wave strokes, the way the back draws its lake, thinning out away from the island
rows = np.arange(7.0, HMM - 6.0, 3.2)
for ry in rows:
    x = 6.5 + rng.uniform(0, 4.0)
    while x < WMM - 9.0:
        L = rng.uniform(4.4, 6.6)
        cx, cy = x + L / 2, ry + rng.uniform(-0.35, 0.35)
        d = dist_shore(cx, cy)
        near_isl = min(math.hypot(cx - ix, cy - iy) for ix, iy in islets)
        ends_wet = not on_land(x, cy) and not on_land(x + L, cy) and not on_land(cx, cy)
        keep = (ends_wet and d > 8.2 and near_isl > ISL_CLEAR + 2.4
                and rng.random() < max(0.0, 0.85 - (d - 8.2) / 8.0))
        if keep:
            n = 6
            wl = [(x + L * t / n, cy + 0.42 * math.sin(t / n * math.tau * 1.25 + ry)) for t in range(n + 1)]
            art.line(wl, 1.1, layer='blue', wob=0.05, trem=0.04, a0=0.9, a1=1.5)
            x += L + rng.uniform(2.2, 3.6)
        else:
            x += rng.uniform(2.0, 3.5)

order = ('blue', 'accent', 'key')
inks = art.finish(order=order, shifts={'blue': (-0.2, 0.15), 'accent': (0.15, 0.2)}, trim=False)
F.save(art, inks, order, __file__)
