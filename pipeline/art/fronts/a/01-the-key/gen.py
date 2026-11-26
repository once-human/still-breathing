#!/usr/bin/env python3
"""
01 the key (continued from the first-round draft he liked): the back map's legend, the block a printed sheet carries
in its corner, lifted off the back as an object of its own and titled with the wordmark, the way a survey sheet's key
carries its publisher's name, with the place and the nights under it.

Each swatch is drawn in the back's own marks: a block of the city hatched, a bend of the course (turf inside the
track's double rail), the sea's wave strokes, us as heads from above, the moon (none: both Mumbai nights are moonless,
new moon falls on 9 December 2026), and the sound's broken rings. Under them the north arrow, turned the way the back
is turned (north points right, a little up), and a scale bar true to the back (125 m = 31.75 mm on the 38 cm print).
Labels in the back's note hand. Left chest, 10 cm.
    R=1 python3 gen.py (draft)  |  python3 gen.py (print size)
"""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import front as F

WMM, HMM = 100, 160
F.setup(WMM, HMM, draft_px=9.4)
import hand
from hand import Art, hatch_poly

art = Art(seed=103, layers=('green', 'water', 'ring', 'key'))
rng = art.rng

FX0, FY0, FX1, FY1 = 6.0, 6.0, WMM - 6.0, HMM - 6.0      # the panel
X0, SW, SH = 11.5, 21.0, 11.5                             # swatch column, swatch size
TX = X0 + SW + 6.5                                        # labels start
ROW0, DY = 39.5, 15.0
labels = []


def row_y(i):
    return ROW0 + i * DY + rng.uniform(-0.3, 0.3)


# ------------------------------------------------------------ the title block
TITLE = F.type_mask('fred again', 'brico', 11.5, wght=760)
TX0, TB = 11.0, 19.6
tx_end = TX0 + TITLE.width / hand.R
DOTS = [(tx_end + 2.1 + i * 3.5, TB - 1.2) for i in range(2)]
for x, y in DOTS:
    art.dot(x, y, 1.25, layer='ring')
SUB = F.type_mask('mumbai, 8 + 9 dec', 'shantell', 8.0, wght=720)
art.line([(FX0 + 2.4, 32.4), (WMM / 2, 32.0), (FX1 - 2.2, 32.5)], 1.15, layer='key', wob=0.08, trem=0.12, a0=0.6, a1=1.4)

# ------------------------------------------------------------ 1. the city: two footprints, hatched, drawn edge by edge
y = row_y(0)
for poly, ang in (([(X0 + 0.3, y + 0.6), (X0 + 12.2, y - 0.1), (X0 + 12.5, y + 6.6), (X0 + 7.6, y + 6.9), (X0 + 7.8, y + 12.0), (X0 + 0.6, y + 11.8)], -0.82),
                  ([(X0 + 15.0, y + 2.4), (X0 + 22.4, y + 3.2), (X0 + 21.6, y + 11.6), (X0 + 14.4, y + 10.9)], 0.95)):
    hatch_poly(art, poly, 'key', angle=ang, spacing=2.75, w=1.1, gap=(0.0, 0.04), jit=0.18)
    art.box(poly, 1.15, layer='key', over=(-0.6, 1.6))
labels.append(('the city', y + SH / 2))

# ------------------------------------------------------------ 2. the course: a bend of the track, turf inside its rails
y = row_y(1)
cx, cy, R0 = X0 + SW + 3.0, y + SH + 11.5, 25.5         # the bend's centre sits off the swatch, down-right
ang0, ang1 = math.radians(205), math.radians(258)


def arc(r, a0=ang0, a1=ang1, n=18):
    return [(cx + math.cos(a0 + (a1 - a0) * t / n) * r, cy + math.sin(a0 + (a1 - a0) * t / n) * r) for t in range(n + 1)]


inner = arc(R0 - 9.0)
turf = arc(R0 - 2.2) + arc(R0 - 9.6)[::-1]
art.blob(turf, 'green', jit=0.02, gap=0.0, shift=0.25, n=60, scale=(0.99, 1.01))
for k in range(5):     # a few pale grass marks carved out of the turf, along the bend
    a = ang0 + (ang1 - ang0) * (0.15 + 0.17 * k) + rng.uniform(-0.03, 0.03)
    r = R0 - 6.0 + rng.uniform(-1.2, 1.2)
    p = (cx + math.cos(a) * r, cy + math.sin(a) * r)
    t = a + math.pi / 2
    art.carve([p, (p[0] + math.cos(t) * 1.9, p[1] + math.sin(t) * 1.9)], 1.2, layer='green')
art.line(arc(R0 - 0.2, ang0 - 0.03, ang1 + 0.03), 1.15, layer='key', wob=0.06, trem=0.06, a0=0.6, a1=1.4)
art.line(arc(R0 - 2.5, ang0 - 0.01, ang1 + 0.01), 1.15, layer='key', wob=0.06, trem=0.06, a0=0.6, a1=1.4)
labels.append(('the course', y + SH / 2))

# ------------------------------------------------------------ 3. the sea: three rows of the back's wave strokes
y = row_y(2)
for r in range(3):
    xx = X0 + rng.uniform(-0.3, 1.0) + (2.6 if r == 1 else 0)
    while xx < X0 + SW - 3:
        L = rng.uniform(4.6, 6.8)
        n = 8
        pts = [(xx + L * t / n, y + 1.9 + r * 3.7 + 0.6 * math.sin(t / n * math.tau * 1.5 + r)) for t in range(n + 1)]
        art.line(pts, 1.15, layer='water', wob=0.07, trem=0.04, a0=1.0, a1=2.0)
        xx += L + rng.uniform(1.8, 2.8)
labels.append(('the sea', y + SH / 2))

# ------------------------------------------------------------ 4. us: heads from above, packed, thinning to one side
y = row_y(3)
pts = []
tries = 0
while len(pts) < 26 and tries < 8000:
    tries += 1
    px_, py_ = X0 + rng.uniform(0.9, SW - 0.9), y + rng.uniform(0.9, SH - 0.9)
    if rng.random() < ((px_ - X0) / SW) ** 1.5 * 0.85:
        continue
    if all((px_ - qx) ** 2 + (py_ - qy) ** 2 > 2.9 ** 2 for qx, qy in pts):
        pts.append((px_, py_))
for px_, py_ in pts:
    art.dot(px_, py_, rng.uniform(0.95, 1.12), layer='key')
labels.append(('us', y + SH / 2))

# ------------------------------------------------------------ 5. the moon: none. A pencilled circle, broken, left empty
y = row_y(4)
mx, my, mr = X0 + SW / 2 - 2.0, y + SH / 2, 5.2
a = rng.uniform(0, math.tau)
for k in range(9):
    a0 = a + k * math.tau / 9
    a1 = a0 + math.tau / 9 * 0.62
    ctrl = [(mx + math.cos(a0 + (a1 - a0) * u) * mr, my + math.sin(a0 + (a1 - a0) * u) * mr) for u in (0, 0.5, 1)]
    art.line(ctrl, 1.1, layer='key', wob=0.05, trem=0.0, a0=0.5, a1=0.8)
labels.append(('no moon', y + SH / 2))

# ------------------------------------------------------------ 6. the sound: a stage block, three rings breaking open
y = row_y(5)
sx, sy = X0 + 1.6, y + SH / 2 + 0.2
art.fill([(sx - 0.9, sy - 2.4), (sx + 1.0, sy - 2.3), (sx + 0.9, sy + 2.4), (sx - 1.0, sy + 2.3)], 'ring')
for r, span in ((5.2, 1.0), (9.7, 0.66), (14.2, 0.46)):
    n = 9
    for half in (((-span, -0.06), (0.09, span)) if r > 6 else ((-span, span),)):
        ctrl = [(sx + math.cos(half[0] + (half[1] - half[0]) * t / n) * r,
                 sy + math.sin(half[0] + (half[1] - half[0]) * t / n) * r) for t in range(n + 1)]
        art.line(ctrl, 1.2, layer='ring', wob=0.05, trem=0.08, a0=1.0, a1=2.4)
labels.append(('the sound', y + SH / 2))

# ------------------------------------------------------------ north arrow (north points right, a little up) and scale
y = row_y(6) + 1.5
nx_, ny_ = 0.978, -0.208
ax, ay = X0 + 0.5, y + 3.2
tip = (ax + nx_ * 17, ay + ny_ * 17)
art.line([(ax, ay), tip], 1.2, layer='key', wob=0.05, trem=0.05, a0=0.6, a1=0.6)
px_, py_ = -ny_, nx_
for s_ in (1, -1):
    art.line([tip, (tip[0] - nx_ * 3.8 + px_ * s_ * 2.1, tip[1] - ny_ * 3.8 + py_ * s_ * 2.1)], 1.15, layer='key',
             wob=0.04, trem=0.0, a0=0.6, a1=1.4)
N_AT = (tip[0] + 2.4, tip[1] - 1.4)

# the scale: a survey bar, two lines with alternate quarters filled, ticks at the ends
yb = y + 12.6
bx0, bx1, bh = X0, X0 + 31.75, 3.0
art.line([(bx0, yb - bh), (bx1, yb - bh + 0.15)], 1.1, layer='key', wob=0.03, trem=0.03, a0=0.5, a1=0.5)
art.line([(bx0, yb), (bx1, yb + 0.15)], 1.1, layer='key', wob=0.03, trem=0.03, a0=0.5, a1=0.5)
for k in range(5):
    xx = bx0 + (bx1 - bx0) * k / 4
    ext = 1.6 if k in (0, 4) else 0.0
    art.line([(xx, yb - bh - ext), (xx + 0.05, yb + 0.1)], 1.1, layer='key', wob=0.02, trem=0.0, a0=0.4, a1=0.4)
for k in (0, 2):
    xx = bx0 + (bx1 - bx0) * k / 4
    art.fill([(xx, yb - bh), (xx + (bx1 - bx0) / 4, yb - bh + 0.1), (xx + (bx1 - bx0) / 4, yb + 0.1), (xx, yb)], 'key')

# ------------------------------------------------------------ the panel: a box drawn by hand, corners crossing
frame = [(FX0, FY0 + 0.2), (FX1 - 0.4, FY0 - 0.1), (FX1, FY1 - 0.3), (FX0 + 0.2, FY1)]
art.box(frame, 1.25, layer='key', over=(0.5, 2.6))

order = ('green', 'water', 'ring', 'key')
inks = art.finish(order=order, shifts={'green': (0.3, -0.2), 'water': (-0.25, 0.2), 'ring': (0.15, 0.3)}, trim=False)

# ------------------------------------------------------------ lettering, after the print physics
F.ink_type(inks, 'key', TITLE, TX0, TB - TITLE.info['base'])
F.ink_type(inks, 'key', SUB, TX0 + 0.4, 27.6 - SUB.info['base'])
TS = 11.2
for txt, yy in labels:
    m = F.embolden(F.text_mask(txt, TS, rot=rng.uniform(-1.4, 0.9)))
    inks['key'].paste(255, (int(TX * hand.R), int(yy * hand.R - m.height / 2 - 0.6 * hand.R)), m)
m = F.embolden(F.text_mask('n', TS, rot=0))
inks['key'].paste(255, (int(N_AT[0] * hand.R), int(N_AT[1] * hand.R - m.height / 2)), m)
m = F.embolden(F.text_mask('125 m', TS * 0.92, rot=-1))
inks['key'].paste(255, (int((bx1 + 4.0) * hand.R), int((yb - bh / 2) * hand.R - m.height / 2 - 0.6 * hand.R)), m)
F.finish_out(art, inks, order, __file__)
F.write_placement(__file__, 'left chest', 10, 15, inner_edge_cm=4)
