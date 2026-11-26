#!/usr/bin/env python3
"""
01 the key (continued from the first-round draft he liked): the back map's legend, the block a printed sheet carries
in its corner, lifted off the back as an object of its own and titled with the wordmark, the way a survey sheet's key
carries its publisher's name, with the place and the nights under it.

Each swatch sits in its own hand-ruled cell, as on a printed legend, and is drawn in the back's own marks: blocks of
the city hatched, a bend of the course (turf inside the track's double rail), the sea's wave strokes, us as heads from
above, the moon (none: both Mumbai nights are moonless, new moon falls on 9 December 2026), and the sound (the stage
and its broken rings, cut by the cell as the back's rings are cut by the sheet). A ruled block at the foot holds the
north arrow, turned the way the back is turned (north points right, a little up), and a scale bar true to the back
(125 m = 31.75 mm on the 38 cm back print). Left chest, 10 cm.
    R=1 python3 gen.py (draft)  |  python3 gen.py (print size)
"""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import front as F

WMM, HMM = 100, 160
F.setup(WMM, HMM, draft_px=9.4)
import hand
from hand import Art, hatch_poly
from PIL import Image, ImageDraw

art = Art(seed=103, layers=('green', 'water', 'ring', 'key'))
rng = art.rng

FX0, FY0, FX1, FY1 = 6.0, 6.0, WMM - 6.0, HMM - 6.0      # the panel
CX0, CW, CH = 12.0, 22.0, 12.0                            # the swatch cells: left edge, width, height
TX = CX0 + CW + 7.0                                       # labels start
ROW0, DY = 40.0, 15.4
LABEL = ('shantell', 8.0, 720)                            # one face for the labels and the subtitle
labels, cells = [], []


SNAP = {}


def cell(i):
    """start swatch i: remember the layers, so whatever this swatch draws outside its cell can be taken back"""
    y = ROW0 + i * DY
    c = (CX0, y, CX0 + CW, y + CH)
    cells.append(c)
    SNAP.update({k: art.L[k].copy() for k in art.layers})
    return c


def done(label, yy):
    """end the swatch: keep its marks only inside its own cell (inset 0.6 mm from the ruling)"""
    x0, y0, x1, y1 = cells[-1]
    outside = Image.new('L', (hand.W, hand.H), 255)
    ImageDraw.Draw(outside).rectangle([int((x0 + 0.6) * hand.R), int((y0 + 0.6) * hand.R),
                                       int((x1 - 0.6) * hand.R), int((y1 - 0.6) * hand.R)], fill=0)
    for k in art.layers:
        art.L[k].paste(SNAP[k], (0, 0), outside)
    labels.append((label, yy))


# ------------------------------------------------------------ the title block
TITLE = F.type_mask('fred again', 'brico', 11.5, wght=760)
TX0, TB = 11.0, 19.6
tx_end = TX0 + TITLE.width / hand.R
for i in range(2):
    art.dot(tx_end + 2.1 + i * 3.5, TB - 1.2, 1.2, layer='ring')
SUB = F.type_mask('mumbai, 8 + 9 dec', *LABEL)
art.line([(FX0 + 2.4, 32.4), (WMM / 2, 32.0), (FX1 - 2.2, 32.5)], 1.15, layer='key', wob=0.08, trem=0.12, a0=0.6, a1=1.4)

# ------------------------------------------------------------ 1. the city: small blocks, hatched, as the back's are
x0, y0, x1, y1 = cell(0)
for poly, ang in (([(x0 + 2.4, y0 + 2.3), (x0 + 10.2, y0 + 1.9), (x0 + 10.5, y0 + 6.6), (x0 + 6.6, y0 + 6.8), (x0 + 6.8, y0 + 9.9), (x0 + 2.6, y0 + 9.8)], -0.82),
                  ([(x0 + 12.8, y0 + 3.0), (x0 + 19.6, y0 + 3.5), (x0 + 19.1, y0 + 9.7), (x0 + 12.5, y0 + 9.3)], 0.95)):
    hatch_poly(art, poly, 'key', angle=ang, spacing=2.7, w=1.1, gap=(0.0, 0.04), jit=0.12)
    art.box(poly, 1.1, layer='key', over=(-0.4, 0.9))
done('the city', (y0 + y1) / 2)

# ------------------------------------------------------------ 2. the course: a bend of the track, turf inside its rails
x0, y0, x1, y1 = cell(1)
cx, cy, R0 = x1 + 2.0, y1 + 10.0, 21.0
ang0, ang1 = math.radians(196), math.radians(266)


def arc(r, a0=ang0, a1=ang1, n=20):
    return [(cx + math.cos(a0 + (a1 - a0) * t / n) * r, cy + math.sin(a0 + (a1 - a0) * t / n) * r) for t in range(n + 1)]


art.blob(arc(R0 - 2.6) + arc(R0 - 10.5)[::-1], 'green', jit=0.02, gap=0.0, shift=0.2, n=60, scale=(0.99, 1.01))
for k in range(4):     # pale grass marks carved out of the turf, along the bend
    a = ang0 + (ang1 - ang0) * (0.2 + 0.2 * k) + rng.uniform(-0.03, 0.03)
    r = R0 - 6.6 + rng.uniform(-1.0, 1.0)
    p = (cx + math.cos(a) * r, cy + math.sin(a) * r)
    t = a + math.pi / 2
    art.carve([p, (p[0] + math.cos(t) * 1.9, p[1] + math.sin(t) * 1.9)], 1.2, layer='green')
art.line(arc(R0 + 0.2, ang0 - 0.05, ang1 + 0.05), 1.15, layer='key', wob=0.05, trem=0.05, a0=0.6, a1=1.4)
art.line(arc(R0 - 2.1, ang0 - 0.05, ang1 + 0.05), 1.15, layer='key', wob=0.05, trem=0.05, a0=0.6, a1=1.4)
done('the course', (y0 + y1) / 2)

# ------------------------------------------------------------ 3. the sea: three rows of the back's wave strokes
x0, y0, x1, y1 = cell(2)
for r in range(3):
    xx = x0 + 1.6 + rng.uniform(-0.3, 0.6) + (2.4 if r == 1 else 0)
    while xx < x1 - 5:
        L = rng.uniform(4.2, 5.8)
        n = 8
        pts = [(xx + L * t / n, y0 + 2.6 + r * 3.4 + 0.55 * math.sin(t / n * math.tau * 1.5 + r)) for t in range(n + 1)]
        art.line(pts, 1.12, layer='water', wob=0.06, trem=0.03, a0=1.0, a1=2.0)
        xx += L + rng.uniform(1.6, 2.4)
done('the sea', (y0 + y1) / 2)

# ------------------------------------------------------------ 4. us: heads from above, packed, thinning to one side
x0, y0, x1, y1 = cell(3)
pts = []
tries = 0
while len(pts) < 24 and tries < 9000:
    tries += 1
    px_, py_ = x0 + rng.uniform(2.0, CW - 2.0), y0 + rng.uniform(2.0, CH - 2.0)
    if rng.random() < ((px_ - x0) / CW) ** 1.5 * 0.85:
        continue
    if all((px_ - qx) ** 2 + (py_ - qy) ** 2 > 2.7 ** 2 for qx, qy in pts):
        pts.append((px_, py_))
for px_, py_ in pts:
    art.dot(px_, py_, rng.uniform(0.92, 1.08), layer='key')
done('us', (y0 + y1) / 2)

# ------------------------------------------------------------ 5. the moon: none. A pencilled circle, broken, left empty
x0, y0, x1, y1 = cell(4)
mx, my, mr = (x0 + x1) / 2, (y0 + y1) / 2, 4.2
a = rng.uniform(0, math.tau)
for k in range(6):
    a0 = a + k * math.tau / 6
    a1 = a0 + math.tau / 6 * 0.55
    art.line([(mx + math.cos(a0 + (a1 - a0) * u) * mr, my + math.sin(a0 + (a1 - a0) * u) * mr) for u in (0, 0.5, 1)],
             1.1, layer='key', wob=0.04, trem=0.0, a0=0.5, a1=0.8)
done('no moon', (y0 + y1) / 2)

# ------------------------------------------------------------ 6. the sound: the stage, and its rings swept one way,
# broken where the hand lifted, running out past the cell's edge the way the back's run off the sheet
x0, y0, x1, y1 = cell(5)
sx, sy = x0 + 3.6, y1 - 3.0
art.fill([(sx - 1.8, sy - 1.1), (sx + 1.9, sy - 1.3), (sx + 2.0, sy + 1.1), (sx - 1.7, sy + 1.2)], 'ring')
for k, r in enumerate((5.6, 10.2, 15.0, 19.8)):
    a = math.radians(-100) + rng.uniform(-0.1, 0.1)
    end = math.radians(15)
    while a < end:
        b = min(end, a + rng.uniform(0.45, 0.8) * (8 / r) ** 0.4)
        n = 10
        art.line([(sx + math.cos(a + (b - a) * t / n) * r, sy + math.sin(a + (b - a) * t / n) * r) for t in range(n + 1)],
                 1.15, layer='ring', wob=0.05, trem=0.05, a0=1.0, a1=2.2)
        a = b + rng.uniform(0.1, 0.22)
done('the sound', (y0 + y1) / 2)

# ------------------------------------------------------------ rule the cells
for x0, y0, x1, y1 in cells:
    art.box([(x0, y0), (x1, y0 + rng.uniform(-0.15, 0.15)), (x1, y1), (x0, y1 + rng.uniform(-0.15, 0.15))], 1.1,
            layer='key', over=(-0.3, 0.8), wob=0.12)

# ------------------------------------------------------------ the foot: a ruled block with the north arrow and the scale
YR = ROW0 + 6 * DY + 1.6
art.line([(FX0 + 2.4, YR), (WMM / 2, YR - 0.3), (FX1 - 2.2, YR + 0.2)], 1.15, layer='key', wob=0.08, trem=0.12, a0=0.6, a1=1.4)
# north: a split dart, one half filled, pointing the way the back's north points
nx_, ny_ = 0.978, -0.208
px_, py_ = -ny_, nx_
ax, ay = CX0 + 1.0, YR + 11.0
L, Wd = 15.0, 2.7
tip = (ax + nx_ * L, ay + ny_ * L)
notch = (ax + nx_ * 3.0, ay + ny_ * 3.0)
left = (ax - px_ * Wd, ay - py_ * Wd)
right = (ax + px_ * Wd, ay + py_ * Wd)
art.fill([tip, left, notch], 'key')                 # the filled half
art.box([tip, right, notch], 1.1, layer='key', over=(-0.3, 0.6), wob=0.05)
art.line([left, notch], 1.1, layer='key', wob=0.02, trem=0.0, a0=0.4, a1=0.4)
N_AT = (tip[0] + 2.2, tip[1])
# the scale: a survey bar, two lines with alternate quarters filled, ticks at the ends
yb = YR + 13.6
bx0, bx1, bh = TX + 1.0, TX + 1.0 + 31.75, 2.8
art.line([(bx0, yb - bh), (bx1, yb - bh + 0.12)], 1.1, layer='key', wob=0.03, trem=0.03, a0=0.5, a1=0.5)
art.line([(bx0, yb), (bx1, yb + 0.12)], 1.1, layer='key', wob=0.03, trem=0.03, a0=0.5, a1=0.5)
for k in range(5):
    xx = bx0 + (bx1 - bx0) * k / 4
    ext = 1.4 if k in (0, 4) else 0.0
    art.line([(xx, yb - bh - ext), (xx + 0.05, yb + 0.1)], 1.1, layer='key', wob=0.02, trem=0.0, a0=0.4, a1=0.4)
for k in (0, 2):
    xx = bx0 + (bx1 - bx0) * k / 4
    art.fill([(xx, yb - bh), (xx + (bx1 - bx0) / 4, yb - bh + 0.1), (xx + (bx1 - bx0) / 4, yb + 0.1), (xx, yb)], 'key')

# ------------------------------------------------------------ the panel: a box drawn by hand, corners crossing
frame = [(FX0, FY0 + 0.2), (FX1 - 0.4, FY0 - 0.1), (FX1, FY1 - 0.3), (FX0 + 0.2, FY1)]
art.box(frame, 1.25, layer='key', over=(0.5, 2.6))

order = ('green', 'water', 'ring', 'key')
inks = art.finish(order=order, shifts={'green': (0.3, -0.2), 'water': (-0.25, 0.2), 'ring': (0.15, 0.3)}, trim=False)

# ------------------------------------------------------------ lettering, after the print physics, in one face
F.ink_type(inks, 'key', TITLE, TX0, TB - TITLE.info['base'])
F.ink_type(inks, 'key', SUB, TX0 + 0.4, 27.6 - SUB.info['base'])
XH = 3.9                                   # Shantell's x-height at this size, mm: labels centre on their cell
for txt, yy in labels:
    m = F.type_mask(txt, *LABEL)
    F.ink_type(inks, 'key', m, TX, yy + XH / 2 - m.info['base'])
m = F.type_mask('n', *LABEL)
F.ink_type(inks, 'key', m, N_AT[0], N_AT[1] + XH / 2 - m.info['base'])
m = F.type_mask('125 m', *LABEL)
F.ink_type(inks, 'key', m, bx0, yb - bh - 2.2 - m.info['base'])
F.finish_out(art, inks, order, __file__)
F.write_placement(__file__, 'left chest', 10, 15, inner_edge_cm=4)
