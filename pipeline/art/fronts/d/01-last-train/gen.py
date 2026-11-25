#!/usr/bin/env python3
"""01 last train: the last Green Line train in at Madavara, side-on along the viaduct, its nose at the buffer stop
where the line ends, packed with people against the lit windows. Collarbone, 17 cm. Ink line + spot green.
R=1 python3 gen.py (draft) | python3 gen.py (final, art.png at 94.5 px/cm)"""
import os, sys, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'lib'))
from common import canvas, save, INK
DRAFT, UW, UH = canvas(17.6, 7.0)
import hand
from hand import Art, composite

art = Art(seed=1212, layers=('key', 'green'))
rng = random.Random(7)
K, G = 'key', 'green'
M = 16.0                                  # units per metre (5 mm)

def lod(x):                               # the drawing stops toward the left, object by object
    return max(0.0, min(1.0, (x - 30) / 230))

def cut(poly):                            # knock a shape out of the key (light through glass)
    art.D[K].polygon(hand.P(poly), fill=0)

# ---------------------------------------------------------------- viaduct deck
DT, DB = 150.0, 172.0
art.line([(96, DT + 1), (180, DT + 1.6), (360, DT - 0.4), (528, DT + 0.5)], 5.2, a0=1.0)
art.line([(150, DB), (300, DB + 1.2), (526, DB - 0.4)], 4.6)
x = 70.0
while x < 520:                            # parapet panel joints on the deck's face
    if rng.random() < 0.15 + 0.85 * lod(x):
        if x > 170: art.line([(x, DT + 6), (x + rng.uniform(-1, 1), DB - 4)], 3.4, a0=0.6, a1=1.2)
    x += rng.uniform(40, 52)
# a pier, going down out of the picture
art.line([(392, DB + 3), (406, DB + 12), (406, 205)], 4.4, a1=5)        # the pier: its cap flaring out, then down
art.line([(450, DB + 3), (434, DB + 12), (435, 200)], 4.4, a1=5)
art.line([(410, DB + 20), (431, DB + 18)], 3.4)

# ---------------------------------------------------------------- the buffer stop where the line ends
BX = 524.0
art.line([(BX - 12, DT - 2), (BX - 9, 126), (BX - 3, 126)], 4.2, a0=0.6)            # the frame rising from the rail end
art.line([(BX + 1, DT - 2), (BX - 1, 128)], 4.4, a0=0.6)
art.line([(BX - 20, 132), (BX + 2, 131)], 5.6, a0=0.5, a1=0.5)                      # the beam with its buffer heads
art.dot(BX - 20, 132, 4.2)
art.line([(BX - 10, DT - 3), (BX, 134)], 3.4)

# ---------------------------------------------------------------- the train
TOP, BOT = 86.0, 146.0
WT, WB = 97.0, 121.0                      # window band
NOSE = 500.0
CAR = 21.0 * M                            # 336 u

def heads_in(x0, x1):
    """packed standing passengers against the lit glass: dark heads and shoulders, a hand on the rail, gaps between"""
    hx = x0 + (rng.uniform(3, 6) if x1 - x0 > 20 else (x1 - x0) / 2)
    r = 4.0
    while hx < x1 - 3:
        if rng.random() < 0.9:
            r = rng.uniform(3.6, 5.0)
            hy = WT + r + rng.uniform(3.4, 6.5)
            art.D[K].ellipse([(hx - r) * hand.R, (hy - r * 1.12) * hand.R, (hx + r) * hand.R, (hy + r * 1.12) * hand.R], fill=255)
            sw = r * rng.uniform(1.6, 2.1)
            art.D[K].polygon(hand.P([(hx - sw, WB), (hx - sw * 0.9, hy + r + 3.5), (hx - 2, hy + r + 0.8), (hx + 2, hy + r + 0.8),
                                     (hx + sw * 0.9, hy + r + 3.5), (hx + sw, WB)]), fill=255)
            if rng.random() < 0.3:            # an arm up to the grab rail
                ax = hx + rng.choice((-1, 1)) * rng.uniform(4.5, 6.5)
                art.line([(ax, hy + 5), (ax + rng.uniform(-1, 1), WT + 2)], 3.5, a0=0.5, a1=0.8)
        hx += (2 * r + rng.uniform(3.8, 6.0)) if x1 - x0 > 20 else 99

def car(xf, nose):
    x0, x1 = xf - CAR + 4, xf
    xs = max(x0, 18.0 + rng.uniform(0, 26))
    L = lod((xs + x1) / 2)
    # roof and skirt lines
    if nose:
        art.line([(xs, TOP + 0.5), (x1 - 34, TOP), (x1 - 14, TOP + 3), (x1 - 4, TOP + 16), (x1 + 1, TOP + 36),
                  (x1 + 1, BOT - 4), (x1 - 3, BOT)], 4.4, a0=0.8, a1=1.2)
        # the windscreen, raked, dark
        art.blob([(x1 - 30, TOP + 6), (x1 - 13, TOP + 5), (x1 - 4, TOP + 19), (x1 - 2, WB + 2), (x1 - 26, WB + 2)], K,
                 jit=0.02, shift=0.3, gap=0)
        cut([(x1 - 20, TOP + 10), (x1 - 15, TOP + 9), (x1 - 13, WB - 4), (x1 - 18, WB - 4)])   # the driver, standing
        art.blob([(x1 - 34, WB + 6.5), (x1 + 0.5, WB + 6.5), (x1 + 1, BOT - 3), (x1 - 34, BOT - 3)], G, jit=0.015, gap=0.0)
        art.D[G].ellipse([(x1 - 11) * hand.R, (BOT - 12) * hand.R, (x1 - 4) * hand.R, (BOT - 5) * hand.R], fill=0)   # headlight
        art.box([(x1 - 11.5, BOT - 12.5), (x1 - 3.5, BOT - 12.5), (x1 - 3.5, BOT - 4.5), (x1 - 11.5, BOT - 4.5)], 3.4, over=(-1.5, 0.5))
        art.line([(x1 - 3, BOT + 1), (x1 + 4, BOT + 4)], 3.4)             # coupler
    else:
        art.line([(xs, TOP + rng.uniform(-0.5, 0.5)), ((xs + x1) / 2, TOP - 0.5), (x1 - 3, TOP + 0.5)], 4.2, a0=0.8)
        art.line([(x1 - 2, TOP + 2), (x1 - 1, BOT - 2)], 3.8)
    art.line([(xs + 6 + (rng.uniform(10, 40) if xs < 60 else 0), BOT), ((xs + x1) / 2, BOT + 1), (x1 - 6, BOT)], 4.0, a0=0.6)
    # the Green Line's stripe, one hand-laid band the length of the car, dying out with the drawing
    gs = max(xs + 4, 150.0)
    if x1 - gs > 30:
        art.blob([(gs, WB + 6), (x1 - 2, WB + 6.5), (x1 - 2, WB + 15.5), (gs + 10, WB + 15)], G, jit=0.012, gap=0.0, n=60)
    # four doors a side
    doors = [x0 + 22 + i * 84 for i in range(4)]
    edge = x1 - (36 if nose else 6)
    prev = x0 + 6
    for dx in doors + [None]:
        # window band between doors: lit and packed
        a, b = prev, (dx - 3 if dx is not None else edge)
        a = max(a, 20.0)
        if b - a > 14 and rng.random() < 0.15 + 0.85 * L:
            if lod(a) > 0.18:
                art.box([(a, WT), (b, WT + 0.5), (b, WB), (a, WB - 0.5)], 3.6, over=(-1.0, 2.0))
                heads_in(a + 2, b - 2)
            elif rng.random() < 0.6:
                art.line([(a, WT + 0.5), (b - rng.uniform(4, 20), WT)], 3.4, a0=0.5)
        if dx is None or dx > edge or dx < 20:
            prev = (dx + 24) if dx is not None else prev
            continue
        # the door: two leaves, their windows lit too
        if rng.random() < 0.2 + 0.8 * lod(dx):
            art.line([(dx, TOP + 7), (dx + 0.5, BOT - 2)], 3.6, a0=0.6)
            art.line([(dx + 21, TOP + 7), (dx + 20.5, BOT - 2)], 3.6, a0=0.6)
            if lod(dx) > 0.3:
                art.box([(dx + 5.5, WT + 1), (dx + 15.5, WT + 1), (dx + 15.5, WB - 3), (dx + 5.5, WB - 3)], 3.4, over=(-0.8, 1.2))
                if rng.random() < 0.6:
                    heads_in(dx + 5.5, dx + 16)
        prev = dx + 24
    # wheels on the rail
    for bx in (x0 + 52, x1 - 54):
        if bx < 190 or bx > PL0 - 20:
            continue
        for wx in (bx - 13, bx + 13):
            art.dot(wx, DT - 5, 6.5)
        art.line([(bx - 22, BOT + 2), (bx + 22, BOT + 2.5)], 3.6)

PL0 = 9999.0
car(NOSE, True)
car(NOSE - CAR, False)
art.line([(NOSE - CAR - 1, TOP + 6), (NOSE - CAR + 4, TOP + 6), (NOSE - CAR + 4, BOT - 6), (NOSE - CAR - 1, BOT - 6)], 3.4)  # gangway
art.line([(70, DT - 1.5), (300, DT - 2), (512, DT - 1.6)], 3.6, a0=0.6, a1=8)       # the rail

# ---------------------------------------------------------------- the platform roof: long, shallow, on columns
art.line([(292, 40), (380, 34), (460, 31), (533, 31.5)], 6.0, a0=0.6, a1=2.0)       # the canopy, a long low pitch
art.line([(300, 46.5), (420, 40.5), (533, 39.5)], 3.6, a0=0.5)                       # its underside
for cx in (338.0, 436.0, 528.0):                                                     # posts down to the platform
    art.line([(cx, 44), (cx + 0.6, TOP - 6)], 3.6, a1=1.2)
art.line([(436.5, 58), (476, 57)], 3.4, a0=0.4, a1=0.4)                              # a sign plate between two posts
art.line([(437, 70), (476, 69.5)], 3.4, a0=0.4, a1=0.4)
art.line([(476, 50), (476.5, 70)], 3.4)
inks = art.finish(order=('green', 'key'), shifts={'green': (1.2, 0.8)})
rgba = composite(inks, {'key': INK['key'], 'green': INK['green']}, order=('green', 'key'))
save(rgba, HERE, DRAFT)
