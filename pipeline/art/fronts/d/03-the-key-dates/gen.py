#!/usr/bin/env python3
"""
03 the key, with the dates: 01 the key exactly as it is (same seed, same marks), with one addition. From each blue
dot after again.. a hand-drawn leader line runs up above the title to the day it stands for, in the key's note
hand: "sat 12" from the first dot, "sun 13" from the second (12 and 13 December 2026, the two Bengaluru nights).
The canvas grows at the top to make room; the new marks use their own random stream, so every other mark comes
out the same as 01. Left chest, 10.5 cm wide.
    R=1 python3 gen.py (draft)  |  python3 gen.py (print size)
"""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))   # a copy of d/lib, so this folder stands alone
import front as F

TOP = 15.0                              # the room added above the title for the dates
WMM, HMM = 104, 162 + TOP
F.setup(WMM, HMM)
import hand
from hand import Art, hatch_poly

art = Art(seed=401, layers=('green', 'accent', 'key'))
rng = art.rng
X0, SW, SH = 12.0, 21.0, 10.0          # swatch column, swatch size
TX = X0 + SW + 6.0                     # labels start
ROW0, DY = 37.0 + TOP, 14.2
labels = []


def row_y(i):
    return ROW0 + i * DY + rng.uniform(-0.35, 0.35)


def hand_poly(cx, cy, rx, ry, n=9, j=0.12):
    ph = rng.uniform(0, math.tau)
    return [(cx + math.cos(ph + math.tau * k / n) * rx * rng.uniform(1 - j, 1 + j),
             cy + math.sin(ph + math.tau * k / n) * ry * rng.uniform(1 - j, 1 + j)) for k in range(n)]


# ---------------------------------------------------------------- the frame, and the title breaking its top edge
FL, FR, FT, FB = 5.6, WMM - 5.4, 21.5 + TOP, HMM - 6.2
TITLE_X, TITLE_BASE, TITLE_EM = 10.5, 27.5 + TOP, 19.0
t_left, t_right, _ = F.wordmark(art, 'again', TITLE_X, TITLE_BASE, TITLE_EM, rng, layer='key', dot_layer='accent',
                                wght=760, dot_r=0.09, dot_step=0.23)
# the top edge: a stub at the corner, a gap for the title, then on to the far corner
art.line([(FL - 1.2, FT + 0.2), (TITLE_X - 2.2, FT - 0.1)], 1.25, layer='key', wob=0.03, trem=0.03, a0=0.6, a1=1.2)
art.line([(t_right + 2.6, FT - 0.2), ((t_right + FR) / 2, FT + 0.15), (FR + 1.4, FT - 0.1)], 1.25, layer='key',
         wob=0.04, trem=0.05, a0=1.0, a1=0.5)
# the other three edges, each pulled by hand and crossing at the corners
art.line([(FR, FT - 1.6), (FR + 0.3, (FT + FB) / 2), (FR - 0.1, FB + 1.5)], 1.25, layer='key', wob=0.04, trem=0.06,
         a0=0.5, a1=0.9)
art.line([(FR + 1.3, FB + 0.1), ((FL + FR) / 2, FB - 0.25), (FL - 1.0, FB + 0.15)], 1.25, layer='key', wob=0.04,
         trem=0.06, a0=0.5, a1=1.2)
art.line([(FL + 0.15, FB + 1.2), (FL - 0.2, (FT + FB) / 2), (FL, FT - 1.3)], 1.25, layer='key', wob=0.04, trem=0.06,
         a0=0.6, a1=1.0)

# ---------------------------------------------------------------- 1. the halls: a long shed, hatched like the back
y = row_y(0)
poly = [(X0 + 0.2, y + 1.4), (X0 + SW - 0.3, y + 0.6), (X0 + SW + 0.3, y + 9.0), (X0 + 0.6, y + 9.8)]
hatch_poly(art, poly, 'key', angle=0.8, spacing=3.5, w=1.1, gap=(0.0, 0.06))
# a few counter-strokes over its east end, the way the back cross-hatches the roofs
east = [(X0 + SW * 0.62, y + 0.9), (X0 + SW - 0.3, y + 0.6), (X0 + SW + 0.3, y + 9.0), (X0 + SW * 0.64, y + 9.4)]
hatch_poly(art, east, 'key', angle=-0.75, spacing=4.2, w=1.1, gap=(0.05, 0.2))
art.box(poly, 1.15, layer='key', over=(-0.5, 1.3))
labels.append(('the halls', y + SH / 2))

# ---------------------------------------------------------------- 2. the ground: the grass as one loose screen, worn bare in patches
y = row_y(1)
turf = [(X0 - 0.2, y + 0.9), (X0 + SW * 0.5, y + 0.2), (X0 + SW + 0.4, y + 0.8), (X0 + SW + 0.1, y + SH - 0.1),
        (X0 + SW * 0.45, y + SH + 0.4), (X0 + 0.3, y + SH - 0.2)]
art.blob(turf, 'green', jit=0.05, gap=0.0, shift=0.25)
for cx, cy, rx, ry in ((X0 + 5.0, y + 4.2, 2.0, 1.4), (X0 + 12.6, y + 6.6, 2.6, 1.6), (X0 + 17.4, y + 3.0, 1.5, 1.2)):
    art.fill(hand_poly(cx, cy, rx, ry), 'green', value=0)
labels.append(('the ground', y + SH / 2))

# ---------------------------------------------------------------- 3. us: heads from above, in clumps
y = row_y(2)
pts = []
for gx, gy, n in ((X0 + 3.6, y + 4.6, 5), (X0 + 11.2, y + 3.6, 6), (X0 + 18.0, y + 6.6, 4)):
    tries = 0
    k = 0
    while k < n and tries < 2000:
        tries += 1
        px_, py_ = gx + rng.gauss(0, 2.4), gy + rng.gauss(0, 1.9)
        if not (X0 - 0.4 < px_ < X0 + SW + 0.6 and y + 0.6 < py_ < y + SH - 0.2):
            continue
        r = rng.uniform(0.95, 1.4)
        if all(math.hypot(px_ - qx, py_ - qy) > r + qr + 1.2 for qx, qy, qr in pts):
            pts.append((px_, py_, r))
            k += 1
for px_, py_, r in pts:
    art.dot(px_, py_, r, layer='key')
labels.append(('us', y + SH / 2))

# ---------------------------------------------------------------- 4. the sound: the stage, three rings breaking up as they go
y = row_y(3)
sx, sy = X0 + 1.2, y + SH / 2 + 0.2
art.fill([(sx - 1.0, sy - 2.0), (sx + 1.1, sy - 2.1), (sx + 1.2, sy + 2.0), (sx - 0.9, sy + 2.1)], 'key')
for r, span, w in ((5.4, 0.92, 1.35), (10.0, 0.6, 1.25), (14.8, 0.42, 1.2)):
    halves = ((-span, -0.07), (0.12, span)) if r > 12 else ((-span, span),)
    for h0, h1 in halves:
        n = 8
        ctrl = [(sx + math.cos(h0 + (h1 - h0) * t / n) * r, sy + math.sin(h0 + (h1 - h0) * t / n) * r)
                for t in range(n + 1)]
        art.line(ctrl, w, layer='accent', wob=0.05, trem=0.08, a0=1.6, a1=2.4)
labels.append(('the sound', y + SH / 2))

# ---------------------------------------------------------------- 5. the last train: in at the buffer, the end of the line
y = row_y(4)
R1, R2 = y + 3.2, y + 7.0
BUF = X0 + SW - 0.6
for ry in (R1, R2):
    art.line([(X0 - 1.5, ry + 0.25), (X0 + SW * 0.5, ry), (BUF, ry - 0.1)], 1.1, layer='key', wob=0.04, trem=0.04,
             a0=3.0, a1=0.3)
xx = X0 + 0.6
while xx < X0 + 5.0:                     # sleepers, only where the train isn't
    art.line([(xx, R1 - 1.5), (xx + 0.1, R2 + 1.5)], 1.1, layer='key', wob=0.02, trem=0.0, a0=0.2, a1=0.2)
    xx += rng.uniform(3.6, 4.0)
art.line([(BUF + 0.4, y + 0.9), (BUF + 0.7, y + 9.3)], 1.8, layer='key', wob=0.02, trem=0.0, a0=0.3, a1=0.3)
# the train from above: three solid cars nose to tail, the front one rounded, a hair short of the buffer
tx0, tx1 = X0 + 7.2, BUF - 1.3
ty0, ty1 = y + 2.4, y + 7.8
art.knock([(tx0 - 0.5, ty0 - 0.6), (tx1 + 0.5, ty0 - 0.6), (tx1 + 0.5, ty1 + 0.6), (tx0 - 0.5, ty1 + 0.6)], ['key'])
GAPC = 1.15
cl = (tx1 - tx0 - 2 * GAPC) / 3
for c in range(3):
    a0 = tx0 + c * (cl + GAPC) + rng.uniform(-0.1, 0.1)
    a1 = a0 + cl
    if c < 2:
        car = [(a0, ty0 + 0.1), (a1, ty0), (a1 + 0.05, ty1), (a0, ty1 - 0.1)]
    else:   # the cab: its nose rounded
        car = [(a0, ty0 + 0.1), (a1 - 1.4, ty0), (a1 - 0.3, ty0 + 0.8), (a1, ty0 + 2.0), (a1, ty1 - 2.0),
               (a1 - 0.3, ty1 - 0.8), (a1 - 1.4, ty1), (a0, ty1 - 0.1)]
    art.fill(car, 'key')
labels.append(('the last train', y + SH / 2))

# ---------------------------------------------------------------- 6. the jam: the road's two edges, both lanes full and standing
y = row_y(5)
art.line([(X0 - 1.0, y + 0.9), (X0 + SW * 0.5, y + 0.6), (X0 + SW + 1.0, y + 0.8)], 1.1, layer='key', wob=0.05,
         trem=0.05, a0=2.4, a1=2.4)
art.line([(X0 - 1.0, y + 9.4), (X0 + SW * 0.5, y + 9.6), (X0 + SW + 1.0, y + 9.3)], 1.1, layer='key', wob=0.05,
         trem=0.05, a0=2.4, a1=2.4)
for lane_y, x_start in ((y + 3.4, X0 - 0.2), (y + 6.9, X0 + 1.4)):
    xx = x_start
    while xx < X0 + SW - 1.0:
        L = rng.uniform(2.6, 3.6) if rng.random() > 0.2 else rng.uniform(4.4, 5.2)   # cars, now and then a bus
        hw = rng.uniform(0.85, 1.0)
        a = rng.uniform(-0.06, 0.06)
        ca, sa = math.cos(a), math.sin(a)
        cx, cy = xx + L / 2, lane_y + rng.uniform(-0.2, 0.2)
        car = [(cx + ca * dx - sa * dy, cy + sa * dx + ca * dy) for dx, dy in
               ((-L / 2, -hw), (L / 2 - 0.3, -hw), (L / 2, -hw + 0.4), (L / 2, hw - 0.4), (L / 2 - 0.3, hw),
                (-L / 2, hw))]
        art.fill(car, 'key')
        xx += L + rng.uniform(1.2, 1.8)
labels.append(('the jam', y + SH / 2))

# ---------------------------------------------------------------- 7. the lake: its shore in the line, water in rows of short strokes
y = row_y(6)
art.line([(X0 - 0.6, y + 1.6), (X0 + 4.0, y + 0.6), (X0 + 11.0, y + 1.3), (X0 + 16.5, y + 0.4),
          (X0 + SW + 0.6, y + 1.2)], 1.15, layer='key', wob=0.1, trem=0.1, a0=1.0, a1=1.6)
for r in range(3):
    xx = X0 + rng.uniform(0.0, 1.4) + (2.6 if r == 1 else 0.6 * r)
    while xx < X0 + SW - 3.5:
        L = rng.uniform(3.8, 6.0)
        n = 6
        pts_ = [(xx + L * t / n, y + 4.4 + r * 2.7 + 0.42 * math.sin(t / n * math.tau * 1.3 + r)) for t in range(n + 1)]
        art.line(pts_, 1.1, layer='accent', wob=0.05, trem=0.04, a0=0.9, a1=1.5)
        xx += L + rng.uniform(2.0, 3.2)
labels.append(('the lake', y + SH / 2))

# ---------------------------------------------------------------- the foot: the back's north, and a scale bar true to the back
yf = ROW0 + 7 * DY + 9.0
nx_, ny_ = F.NORTH
ax, ay = X0 + 1.0, yf + 6.2
L = 12.5
tip = (ax + nx_ * L, ay + ny_ * L)
art.line([(ax, ay), (ax + nx_ * (L - 2.6), ay + ny_ * (L - 2.6))], 1.3, layer='key', wob=0.03, trem=0.03, a0=0.8, a1=0.3)
px_, py_ = -ny_, nx_
head = [tip, (tip[0] - nx_ * 4.2 + px_ * 1.9, tip[1] - ny_ * 4.2 + py_ * 1.9),
        (tip[0] - nx_ * 3.2, tip[1] - ny_ * 3.2), (tip[0] - nx_ * 4.2 - px_ * 1.9, tip[1] - ny_ * 4.2 - py_ * 1.9)]
art.fill(head, 'key')
N_AT = (tip[0] + nx_ * 3.6 + 0.4, tip[1] + ny_ * 3.6)

yb = yf + 3.2
bx0 = X0 + 15.5
bx1 = bx0 + 100 * F.MM_PER_M
seg = (bx1 - bx0) / 4
art.line([(bx0, yb - 1.45), (bx1, yb - 1.35)], 1.1, layer='key', wob=0.03, trem=0.03, a0=0.3, a1=0.3)
art.line([(bx0, yb + 1.45), (bx1, yb + 1.55)], 1.1, layer='key', wob=0.03, trem=0.03, a0=0.3, a1=0.3)
for k in (0, 2):
    xx = bx0 + seg * k
    art.fill([(xx, yb - 1.7), (xx + seg, yb - 1.65), (xx + seg, yb + 1.8), (xx, yb + 1.75)], 'key')
for k in range(5):
    xx = bx0 + seg * k
    hgt = 3.4 if k in (0, 4) else 1.7
    art.line([(xx, yb - hgt), (xx + 0.1, yb + 1.7)], 1.1, layer='key', wob=0.02, trem=0.0, a0=0.3, a1=0.3)

# ---------------------------------------------------------------- the dates: a leader line up from each dot
import random
rd = random.Random(1212)
R_DOT = max(0.8, 0.09 * TITLE_EM)
dot2 = (t_right - R_DOT, TITLE_BASE - R_DOT)
dot1 = (dot2[0] - 0.23 * TITLE_EM, dot2[1])
LABEL_BASE = 9.0 + 0.6 * TOP                     # the dates' baseline, above the title
ends = [(dot1[0] - 7.0, LABEL_BASE + 3.2), (dot2[0] + 7.5, LABEL_BASE + 3.2)]
for (dx, dy), (ex, ey), bow in zip((dot1, dot2), ends, (-1, 1)):
    sx, sy = dx + rd.uniform(-0.2, 0.2), dy - R_DOT - 1.5            # a clear millimetre and a half off the dot
    mid = (sx + (ex - sx) * 0.35 + bow * 0.8, sy + (ey - sy) * 0.55)   # each bows a little outward, the way a hand pulls it
    art.line([(sx, sy), mid, (ex, ey)], 1.15, layer='key', rng=rd, wob=0.05, trem=0.06, a0=0.4, a1=1.4)

order = ('green', 'accent', 'key')
inks = art.finish(order=order, shifts={'green': (0.3, -0.25), 'accent': (0.15, 0.25)}, trim=False)

# lettering after the print physics, in the back's note hand; each label set a little differently, as a hand would
TS = 8.6
for txt, yy in labels:
    m = F.text_mask(txt, TS * rng.uniform(0.97, 1.03), rot=rng.uniform(-1.6, 1.1))
    inks['key'].paste(255, (int((TX + rng.uniform(-0.3, 0.4)) * hand.R),
                            int((yy + rng.uniform(-0.3, 0.3)) * hand.R - m.height / 2)), m)
m = F.text_mask('n', TS * 1.05, rot=-30 + rng.uniform(-3, 3))
inks['key'].paste(255, (int(N_AT[0] * hand.R - m.width / 2), int(N_AT[1] * hand.R - m.height / 2)), m)
m = F.text_mask('100 m', TS * 0.92, rot=-1)
inks['key'].paste(255, (int((bx1 + 3.2) * hand.R), int(yb * hand.R - m.height / 2 - 0.2 * hand.R)), m)
DS = 9.4                                         # the dates a touch larger than the entries, so they read at print size
for txt, (ex, ey), side in (('sat 12', ends[0], -1), ('sun 13', ends[1], 1)):
    m = F.text_mask(txt, DS, rot=rd.uniform(-1.2, 0.8))
    cx_ = ex + side * 2.0                             # the line ends under the date's near half
    x_px = cx_ * hand.R - (m.width * 0.72 if side < 0 else m.width * 0.28)
    inks['key'].paste(255, (int(x_px), int(LABEL_BASE * hand.R - m.height * 0.62)), m)
inks['key'] = hand.clean(inks['key'])
F.save(art, inks, order, __file__)
