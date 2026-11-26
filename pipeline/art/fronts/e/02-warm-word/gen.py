#!/usr/bin/env python3
"""
02 i am a party, front 02: "warm word". Centre chest, about 22 cm.
fred again.. drawn by hand in the back's cream, and round it the warmth it gives off, the way the back's camera sees
the crowd but drawn as two lines only: an orange isotherm close in, a violet one further out. Heat rises, so the lines
sit low and close under the letters (1.5 mm) and stand well off above them (about 6 mm), lifting in three soft plumes
over the f, the d and the i, where the strokes reach up. The further out, the smoother: the orange still knows the
letters' shapes, the violet is one slow outline. The orange swells where the heat gathers and thins where it is close
to the letters. Between the letters each line runs into one shape; the counters stay dark.
    python3 gen.py        (ROUND=n keeps round-n.png)
"""
import math, os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import efront as E

WMM, HMM = 236, 84
h, art = E.boot(WMM, HMM, seed=202, layers=('violet', 'orange', 'cream'))
import letters as L
import numpy as np
from PIL import Image, ImageDraw

PX = E.PXMM
XH, CORE, TR, SX = 15.0, 3.6, 0.07, 0.94
x0 = (WMM - L.width('fred again..', XH, CORE, TR, SX)) / 2
y0 = 54.0
marks = L.write(art, 'fred again..', x0, y0, XH, CORE, 'cream', rng=random.Random(7), lay=random.Random(41), track=TR,
                sx=SX, dot_r=CORE * 0.62, a0=0.0, a1=0.0, pv=0.1, wob=XH * 0.01, trem=XH * 0.007, rot_j=2.0,
                base_j=0.045)

# ---- the heat field, worked at a quarter of print resolution (it is smooth by nature), then read back at full size
S = 4
Wp, Hp = art.L['cream'].size
w4, h4 = Wp // S, Hp // S
c4 = np.asarray(art.L['cream'].resize((w4, h4), Image.BILINEAR), np.float32) / 255.0
px4 = PX / S                                         # px per mm at the working size


def blur(a, sigma_mm):
    s = sigma_mm * px4
    r = int(3 * s) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / s) ** 2)
    k /= k.sum()
    a = np.apply_along_axis(lambda v: np.convolve(v, k, mode='same'), 0, a)
    return np.apply_along_axis(lambda v: np.convolve(v, k, mode='same'), 1, a)


def rising(a, up_mm, steps=14, keep=0.45):
    """the source smeared upward: each copy a little higher and a little weaker (warm air rising off the strokes)"""
    out = a.copy()
    for k in range(1, steps + 1):
        d = int(round(up_mm * px4 * k / steps))
        sh = np.zeros_like(a)
        sh[:-d or None] = a[d:]
        out = np.maximum(out, sh * (1 - (1 - keep) * k / steps))
    return out


src = rising(c4, 5.5)
yy, xx = np.mgrid[0:h4, 0:w4].astype(np.float32) / px4
for m, up in ((marks[0], 1.0), (marks[3], 0.9), (marks[9], 0.8)):          # plumes over the f, the d, the i
    top_x, top_y = m['T']((0.3 if m['ch'] == 'f' else 0.83 if m['ch'] == 'd' else 0.06, -1.6))
    src = np.maximum(src, 0.55 * up * np.exp(-(((xx - top_x) / 4.0) ** 2 + ((yy - top_y + 4.0) / 6.5) ** 2)))
del yy, xx
F_in = blur(src, 2.6)                                 # close in: still knows the letters
F_out = blur(rising(c4, 9.0, keep=0.5), 4.6)          # further out: one slow outline


def up(F):
    return np.asarray(Image.fromarray(np.clip(F * 255, 0, 255).astype(np.uint8)).resize((Wp, Hp), Image.BICUBIC))


def iso(F, t, t_in, w_min):
    """one isotherm as a line: the region warmer than t, minus its core. The core is what is both a line's minimum
    width inside the edge and warmer than t_in, so the line never thins below w_min and swells where the heat is spread
    out (above the letters, where the warmth rises slowly)"""
    a = up(F)
    reg = Image.fromarray(np.where(a >= t, 255, 0).astype(np.uint8))
    core_w = h.erode(reg, 2 * int(round(w_min * PX)) + 1)
    hot = Image.fromarray(np.where(a >= t_in, 255, 0).astype(np.uint8))
    core = ImageChops.multiply(core_w, hot)
    return ImageChops.subtract(reg, core)


from PIL import ImageChops
T_OR, T_OR_IN, T_VI, T_VI_IN = (int(v) for v in os.environ.get('TH', '30,52,14,19').split(','))
orange = iso(F_in, T_OR, T_OR_IN, 1.25)
# the orange is the warmth going UP: it is kept only where the heat lies below it (over the letters and the plumes),
# not under the letters or down the narrow gaps between strokes
gy, gx = np.gradient(blur(src, 3.0))
upward = (gy > 0.6 * np.abs(gx)) & (gy > 0.002)
upm = Image.fromarray(np.where(upward, 255, 0).astype(np.uint8)).resize((Wp, Hp), Image.NEAREST)
upm = h.dilate(h.erode(upm, 9), 9)
art.add('orange', ImageChops.multiply(orange, upm))
art.add('violet', iso(F_out, T_VI, T_VI_IN, 1.15))
print('field max', float(F_in.max()), float(F_out.max()))


def grow(m, mm):
    k = 2 * int(round(mm * PX)) + 1
    return h.dilate(m, k)


from PIL import ImageChops
# hard gaps: 1.5 mm of black between the letters and the orange, 1.4 mm between the orange and the violet
art.L['orange'].paste(0, (0, 0), grow(art.L['cream'], 1.5))
art.L['violet'].paste(0, (0, 0), grow(art.L['orange'], 1.4))
art.L['violet'].paste(0, (0, 0), grow(art.L['cream'], 2.5))

# the counters stay dark (open counters found on the letters thickened by 3 mm, then grown back)
K = 2 * int(1.6 * PX) + 1
fat = h.dilate(art.L['cream'], K)
outside = fat.point(lambda p: 0 if p else 255)
ImageDraw.floodfill(outside, (0, 0), 128)
holes = h.dilate(outside.point(lambda p: 255 if p == 255 else 0), K)
for k in ('orange', 'violet'):
    art.L[k].paste(0, (0, 0), holes)


def drop_islands(layer, min_mm=5.0):
    """remove any separate piece of the line smaller than min_mm across (a speck, a sliver)"""
    m = art.L[layer]
    small = m.resize((Wp // 3, Hp // 3), Image.NEAREST)
    a = np.asarray(small) > 0
    seen = np.zeros_like(a)
    H_, W_ = a.shape
    kill = Image.new('L', small.size, 0)
    kd = ImageDraw.Draw(kill)
    for y in range(H_):
        row = a[y]
        for x in np.nonzero(row & ~seen[y])[0]:
            if seen[y, x]:
                continue
            stack, pts = [(y, x)], []
            seen[y, x] = True
            while stack:
                cy, cx = stack.pop()
                pts.append((cy, cx))
                for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                    if 0 <= ny < H_ and 0 <= nx < W_ and a[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            ys, xs = zip(*pts)
            if max(max(ys) - min(ys), max(xs) - min(xs)) * 3 / PX < min_mm:
                for py, px_ in pts:
                    kd.point((px_, py), 255)
    m.paste(0, (0, 0), h.dilate(kill.resize(m.size, Image.NEAREST), 7))


drop_islands('orange')
drop_islands('violet')

E.save(art, __file__, order=('violet', 'orange', 'cream'), trim=False,
       shifts={'violet': (0.1, 0.0), 'orange': (-0.08, 0.0), 'cream': (0, 0)}, crops=[(50, 40), (150, 42)])
