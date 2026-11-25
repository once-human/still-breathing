#!/usr/bin/env python3
"""
01 the key (continued from the liked first-round draft): the back map's own legend, the block a printed map carries
in its corner, now titled with the wordmark, the way a sheet's key carries its publisher's name. Each swatch is drawn in the
back's marks (a hatched block, the turf, the sea's wave lines, the crowd, the foh tent, the rings), labelled in the
back's note hand, with a north arrow turned to the back's rotation (north points right) and a scale bar true to the
back (250 m = 63.5 mm on the 38 cm print). Left chest, 10 cm wide.
    R=1 python3 gen.py (draft)  |  python3 gen.py (print size)
"""
import math, os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import front as F

WMM, HMM = 100, 156
F.setup(WMM, HMM, draft_px=7.0)
import hand
from hand import Art, hatch_poly, ImageFilter

art = Art(seed=103, layers=('green', 'water', 'ring', 'key'))
rng = art.rng
X0, SW, SH = 10.5, 22.0, 12.0          # swatch column left edge, swatch size
TX = X0 + SW + 6.0                    # labels start
ROW0, DY = 30.5, 16.6
labels = []


def row_y(i):
    return ROW0 + i * DY + rng.uniform(-0.4, 0.4)


# 1. the city: one building footprint, hatched, the outline drawn edge by edge
y = row_y(0)
for poly, ang in (([(X0 + 0.5, y + 1.2), (X0 + 12.0, y + 0.4), (X0 + 12.4, y + 7.2), (X0 + 7.6, y + 7.5), (X0 + 7.8, y + 12.6), (X0 + 0.9, y + 12.3)], -0.82),
                  ([(X0 + 15.0, y + 2.8), (X0 + 23.0, y + 3.8), (X0 + 22.0, y + 12.0), (X0 + 14.2, y + 11.2)], 0.95)):
    hatch_poly(art, poly, 'key', angle=ang, spacing=3.0, w=1.1, gap=(0.0, 0.1))
    art.box(poly, 1.15, layer='key')
labels.append(('the city', y + SH / 2))

# 2. the course: the turf as one loose green screen, carved through with a few pale grass marks
y = row_y(1)
turf = [(X0, y + 1.0), (X0 + SW, y + 0.2), (X0 + SW + 0.4, y + SH - 0.5), (X0 + 0.5, y + SH + 0.3)]
art.blob(turf, 'green', jit=0.04, gap=0.0, shift=0.3)
for k in range(10):
    cx, cy = X0 + 2.5 + (k % 5) * 3.6 + rng.uniform(-0.6, 0.6), y + 6.6 + (k // 5) * 3.6 + rng.uniform(-0.5, 0.5)
    a = rng.uniform(-0.5, 0.5)
    art.carve([(cx, cy), (cx + math.cos(a) * 1.7, cy + math.sin(a) * 1.7)], 1.2, layer='green')
for off in (0.0, 2.3):   # the track's rails, the back's black double line, bending across the turf
    art.line([(X0 - 0.5, y + 3.6 + off), (X0 + SW * 0.5, y + 2.4 + off), (X0 + SW + 0.5, y + 4.4 + off * 1.1)], 1.15, layer='key', wob=0.1, trem=0.1, a0=0.6, a1=1.0)
labels.append(('the course', y + SH / 2))

# 3. the sea: three rows of short wave lines, the way the back draws open water
y = row_y(2)
for r in range(3):
    xx = X0 + rng.uniform(-0.5, 1.5) + (2.5 if r == 1 else 0)
    while xx < X0 + SW - 3:
        L = rng.uniform(4.5, 7.0)
        n = 7
        pts = [(xx + L * t / n, y + 1.8 + r * 3.6 + 0.55 * math.sin(t / n * math.tau * 1.5 + r)) for t in range(n + 1)]
        art.line(pts, 1.15, layer='water', wob=0.08, trem=0.05, a0=1.0, a1=2.0)
        xx += L + rng.uniform(1.6, 3.0)
labels.append(('the sea', y + SH / 2))

# 4. us: the crowd as the back draws it from above, heads packed tight, thinning at one edge
y = row_y(3)
pts = []
tries = 0
while len(pts) < 30 and tries < 6000:
    tries += 1
    px, py = X0 + rng.uniform(0.6, SW - 0.6), y + rng.uniform(0.6, SH - 0.6)
    edge = (px - X0) / SW
    if rng.random() < edge ** 1.4 * 0.9:
        continue
    if all((px - qx) ** 2 + (py - qy) ** 2 > 2.7 ** 2 for qx, qy in pts):
        pts.append((px, py))
for px_, py_ in pts:
    art.dot(px_, py_, rng.uniform(0.85, 1.05), layer='key')
labels.append(('us', y + SH / 2))

# 5. meet here: the foh tent from above, a pitched roof (a square and its ridge), guy lines
y = row_y(4)
cx, cy = X0 + SW / 2, y + SH / 2
s = 3.8
tent = [(cx - s, cy - s * 0.95), (cx + s, cy - s), (cx + s * 1.03, cy + s * 0.96), (cx - s * 0.97, cy + s)]
art.box(tent, 1.15, layer='key')
art.line([tent[0], tent[2]], 1.1, layer='key', wob=0.06, trem=0.0, a0=0.6, a1=1.2)    # the canopy's four seams
art.line([tent[1], tent[3]], 1.1, layer='key', wob=0.06, trem=0.0, a0=0.6, a1=1.2)
for k in range(10):   # the meeting circle, pencilled round it in short dashes
    t0 = k / 11 * math.tau + 0.2
    ctrl = [(cx + math.cos(t0 + u * 0.3) * 10.5, cy + math.sin(t0 + u * 0.3) * 6.6) for u in (0, 0.5, 1)]
    art.line(ctrl, 1.1, layer='key', wob=0.08, trem=0.0, a0=0.5, a1=0.8)
labels.append(('meet here', y + SH / 2))

# 6. the sound: three rings, broken, a stage block at their heart
y = row_y(5)
sx, sy = X0 + 2.2, y + SH / 2 + 0.3
art.line([(sx, sy - 2.0), (sx + 0.2, sy + 2.0)], 1.6, layer='key', wob=0.05, trem=0.0, a0=0.6, a1=0.8)
for r, span in ((5.0, 1.05), (9.5, 0.62), (14.0, 0.42)):
    n = 9
    for half in ((-span, -0.05), (0.08, span)) if r > 6 else ((-span, span),):
        ctrl = [(sx + math.cos(half[0] + (half[1] - half[0]) * t / n) * r,
                 sy + math.sin(half[0] + (half[1] - half[0]) * t / n) * r) for t in range(n + 1)]
        art.line(ctrl, 1.2, layer='ring', wob=0.06, trem=0.1, a0=1.0, a1=2.4)
labels.append(('the sound', y + SH / 2))

# the north arrow (the back is turned so north points right, a little up) and the scale bar
y = row_y(6) + 2.0
nx_, ny_ = 0.978, -0.208
ax, ay = X0 + 2.0, y + 2.5
tip = (ax + nx_ * 16, ay + ny_ * 16)
art.line([(ax, ay), tip], 1.2, layer='key', wob=0.05, trem=0.05, a0=0.6, a1=0.6)
px_, py_ = -ny_, nx_
for s_ in (1, -1):
    art.line([tip, (tip[0] - nx_ * 3.6 + px_ * s_ * 2.0, tip[1] - ny_ * 3.6 + py_ * s_ * 2.0)], 1.15, layer='key',
             wob=0.04, trem=0.0, a0=0.6, a1=1.4)
N_AT = (tip[0] + 4.2, tip[1] - 0.4)
# scale bar true to the back: 125 m there = 31.75 mm (0.254 mm per metre on the 38 cm print)
yb = y + 12.5
bx0, bx1 = X0, X0 + 63.5 * 0.5
art.line([(bx0, yb), (bx1, yb + 0.3)], 1.2, layer='key', wob=0.05, trem=0.05, a0=0.6, a1=0.6)
for k in range(5):
    xx = bx0 + (bx1 - bx0) * k / 4
    hgt = 2.6 if k in (0, 4) else 1.6
    art.line([(xx, yb - hgt), (xx + 0.1, yb + 0.2)], 1.1, layer='key', wob=0.03, trem=0.0, a0=0.4, a1=0.4)
for k in (0, 2):
    xx = bx0 + (bx1 - bx0) * k / 4
    art.fill([(xx, yb - 1.4), (xx + (bx1 - bx0) / 4, yb - 1.35), (xx + (bx1 - bx0) / 4, yb + 0.1), (xx, yb + 0.1)], 'key')

# the title rule, under the wordmark: one long hand line, a little bowed
art.line([(8.6, 22.6), (WMM / 2, 22.3), (WMM - 8.4, 22.8)], 1.15, layer='key', wob=0.08, trem=0.12, a0=0.6, a1=1.4)
TITLE = F.type_mask('fred again', 'brico', 11.0, wght=780)
TX0, TB = 11.0, 17.0
tx_end = TX0 + TITLE.width / hand.R
for i in range(2):
    art.dot(tx_end + 2.0 + i * 3.4, TB - 1.15, 1.15, layer='ring')

# the panel: a box round the whole key, drawn by hand, corners crossing
frame = [(6.0, 6.2), (WMM - 6.4, 5.9), (WMM - 6.0, HMM - 6.3), (6.2, HMM - 6.0)]
art.box(frame, 1.25, layer='key', over=(0.5, 3.0))

order = ('green', 'water', 'ring', 'key')
inks = art.finish(order=order, shifts={'green': (0.3, -0.2), 'water': (-0.25, 0.2), 'ring': (0.15, 0.3)}, trim=False)

# lettering after the print physics, in the back's note hand
TS = 11.2
for txt, yy in labels:
    m = F.embolden(F.text_mask(txt, TS, rot=rng.uniform(-1.6, 1.0)))
    inks['key'].paste(255, (int(TX * hand.R), int(yy * hand.R - m.height / 2 - 0.6 * hand.R)), m)
m = F.embolden(F.text_mask("n", TS, rot=0))
inks['key'].paste(255, (int(N_AT[0] * hand.R), int(N_AT[1] * hand.R - m.height / 2 - 0.8 * hand.R)), m)
m = F.embolden(F.text_mask("125 m", TS * 0.92, rot=-1))
inks['key'].paste(255, (int((bx1 + 4.0) * hand.R), int(yb * hand.R - m.height / 2 - 1.2 * hand.R)), m)
F.ink_type(inks, 'key', TITLE, TX0, TB - TITLE.info['base'])
F.finish_out(art, inks, order, __file__)
F.write_placement(__file__, 'left chest', 10, 15, inner_edge_cm=4)
