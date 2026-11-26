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

WMM, HMM = 100, 62
F.setup(WMM, HMM)
import hand
from hand import Art, offset_path, resample
from PIL import Image, ImageDraw, ImageChops

art = Art(seed=402, layers=('blue', 'accent', 'key'))
rng = art.rng
EM = 15.5

# the word, set and worked by hand, centred a little left of the canvas so the islets have water to the right
m, base_px = F.word_mask('again', EM, rng, wght=760)
ww, wh = m.width / hand.R, m.height / hand.R
bb = m.getbbox()
top_mm, bot_mm = bb[1] / hand.R, bb[3] / hand.R
CX, CY = 42.0, 31.0                      # the island's centre
x0 = CX - ww / 2
base_mm = CY + (base_px / hand.R - (top_mm + bot_mm) / 2)
F.paste(art.L['key'], m, x0, base_mm, 'lb', base_px)

# the island: a soft rounded shape hugging the word, its shore wobbling in a few slow waves, one shallow bay
A, B = ww / 2 + 4.6, (bot_mm - top_mm) / 2 + 4.0
harm = [(k, rng.uniform(0.5, 1.0) / k ** 0.5, rng.uniform(0, math.tau)) for k in (2, 3, 4, 6)]


def shore(t, grow=0.0):
    c, s = math.cos(t), math.sin(t)
    n = 2.5                                   # superellipse: a little flatter than an ellipse
    x = A * math.copysign(abs(c) ** (2 / n), c)
    y = B * math.copysign(abs(s) ** (2 / n), s)
    w = sum(a * math.sin(k * t + p) for k, a, p in harm)
    bay = -2.2 * math.exp(-((t - 4.3) / 0.2) ** 2)   # a bay on the north shore
    r = 1 + (w + bay) / max(A, B) * 1.6
    return CX + x * r, CY + y * r


N = 220
pts = [shore(i / N * math.tau) for i in range(N)]
pts = resample(pts + [pts[0]], 260)[:-1]
# the shore: drawn in two pulls of the pen that don't quite meet, the way a hand draws a coast
start = rng.randrange(len(pts))
ring = pts[start:] + pts[:start]
cut1 = int(len(ring) * rng.uniform(0.52, 0.6))
art.line(ring[2:cut1:3], 1.2, layer='key', wob=0.06, trem=0.12, a0=0.8, a1=2.2)
art.line(ring[cut1 + 3:-4:3], 1.2, layer='key', wob=0.06, trem=0.12, a0=0.8, a1=2.2)


def normal_out(path):
    # offset_path's normals follow the drawing direction; flip so they point away from the centre
    p2 = offset_path(path, 1.0)
    out = sum(math.hypot(q[0] - CX, q[1] - CY) - math.hypot(p[0] - CX, p[1] - CY) for p, q in zip(path, p2))
    return 1.0 if out > 0 else -1.0


SGN = normal_out(pts)

# the islets: the two dots, out in the water at the word's baseline
r_dot = 0.078 * EM
islets = [(CX + A + 6.8, base_mm - r_dot), (CX + A + 6.8 + 0.23 * EM, base_mm - r_dot + 0.15)]
for ix, iy in islets:
    art.dot(ix, iy, r_dot * rng.uniform(0.97, 1.04), layer='accent')

# the echo lines: each further out, spacing widening, each broken into a few runs, more broken further out
offs = [2.5, 5.2, 8.3, 11.8]
for li, d in enumerate(offs):
    path = offset_path(pts, SGN * d)
    path = [(x + rng.uniform(-0.05, 0.05), y) for x, y in path]
    n = len(path)
    i = rng.randrange(n)
    done = 0
    gap_p = 0.1 + 0.25 * li
    while done < n:
        L = int(rng.uniform(26, 70) * (1.0 - 0.1 * li))
        seg = [path[(i + k) % n] for k in range(min(L, n - done))]
        if len(seg) > 6 and rng.random() > gap_p * 0.4:
            art.line(seg[::3] + [seg[-1]], 1.1, layer='blue', wob=0.05, trem=0.06, a0=1.0, a1=1.6)
        step = L + int(rng.uniform(4, 10) * (1 + li * 1.1))
        i, done = (i + step) % n, done + step

# the islets: the water lines part round them
mx = (islets[0][0] + islets[1][0]) / 2
my = (islets[0][1] + islets[1][1]) / 2
half = (islets[1][0] - islets[0][0]) / 2
clear = Image.new('L', art.L['blue'].size, 0)
cd = ImageDraw.Draw(clear)
rx, ry = half + r_dot + 2.4, r_dot + 2.3
cd.ellipse(((mx - rx) * hand.R, (my - ry) * hand.R, (mx + rx) * hand.R, (my + ry) * hand.R), fill=255)
art.L['blue'] = ImageChops.subtract(art.L['blue'], clear)
art.D['blue'] = ImageDraw.Draw(art.L['blue'])

order = ('blue', 'accent', 'key')
inks = art.finish(order=order, shifts={'blue': (-0.2, 0.15), 'accent': (0.15, 0.2)}, trim=False)
F.save(art, inks, order, __file__)
