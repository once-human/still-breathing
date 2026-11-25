#!/usr/bin/env python3
"""02 section: the back is the plan, this is the section. A cut along Tumakuru Road at Madavara drawn like an
architect's section by a printmaker: the last train lit on the viaduct, the station concourse lit under it with
people heading out to the grounds, the jam standing still underneath (one auto among the cars), a rain tree over the
footpath, the cut earth hatched below with the piers' footings and a storm drain.
Centre chest, 25 cm. Inks: the back's key and green, plus one yellow for the light and the auto.
R=1 python3 gen.py (draft) | python3 gen.py (final)"""
import os, sys, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'lib'))
from common import canvas, save, INK
DRAFT, UW, UH = canvas(25.0, 17.8)
import hand
from hand import Art, hatch_poly, composite
import people
from PIL import ImageFilter

art = Art(seed=1213, layers=('key', 'green', 'yellow', 'sound'))   # sound left empty (the rings were cut)
rng = random.Random(12)
K, G, Y, S = 'key', 'green', 'yellow', 'sound'
M = 13.0                                   # units per metre
GY = 455.0                                 # the road
RY = GY - 13.5 * M                         # rail level on the viaduct (~280)

def P(pts): return hand.P(pts)
def fill(layer, pts, v=255): art.D[layer].polygon(P(pts), fill=v)

# ---------------------------------------------------------------- the cut: road surface and the earth under it
art.line([(10, GY + 1), (200, GY + 2), (420, GY), (640, GY + 1.5), (776, GY)], 6.0, a0=0.6, a1=1.0)
x = 20.0
while x < 772:                             # the cut earth: free hand strokes down-left, ragged where they stop
    ln = 44 + 16 * math.sin(x / 47.0) + rng.uniform(-8, 10) - (20 if x < 70 or x > 720 else 0)
    if ln > 8:
        art.line([(x, GY + 6), (x - ln * 0.62, GY + 6 + ln * 0.78)], 3.5, a0=0.8, a1=1.4)
    x += rng.uniform(8.0, 10.5)
PIERS = (300.0, 520.0, 700.0)
for px_ in PIERS + (150.0,):              # the footings: pile caps cut clean out of the earth, outlined
    cap = [(px_ - 22, GY + 6), (px_ + 22, GY + 6), (px_ + 22, GY + 24), (px_ - 22, GY + 24)]
    fill(K, cap, 0)
    art.box(cap, 3.6)
    for k in (-12, 0, 12):                # piles going down and stopping
        art.line([(px_ + k, GY + 24), (px_ + k + rng.uniform(-1, 1), GY + 58 + rng.uniform(0, 22))], 3.6, a1=1.2)

for cx_ in (410.0,):                      # the storm drain under the road, a box culvert cut through
    culv = [(cx_ - 26, GY + 14), (cx_ + 26, GY + 14), (cx_ + 26, GY + 40), (cx_ - 26, GY + 40)]
    fill(K, [(cx_ - 31, GY + 9), (cx_ + 31, GY + 9), (cx_ + 31, GY + 45), (cx_ - 31, GY + 45)], 0)
    art.box(culv, 4.2)
    art.line([(cx_ - 20, GY + 33), (cx_ - 6, GY + 31), (cx_ + 8, GY + 33), (cx_ + 20, GY + 31)], 3.5, layer='green' if False else K)
# ---------------------------------------------------------------- piers and the concourse slab
for px_ in PIERS:
    art.line([(px_ - 9, GY), (px_ - 8, 382)], 4.4, a0=0.6)
    art.line([(px_ + 9, GY), (px_ + 8.5, 382)], 4.4, a0=0.6)
# left of the station the bare viaduct: one pier with its cap
art.line([(140, GY), (141, 312), (128, 302)], 4.4, a0=0.6)
art.line([(160, GY), (159, 312), (174, 302)], 4.4, a0=0.6)
# the deck under the train, running out of the station to the left
art.line([(60, RY + 2), (240, RY + 2.5), (560, RY + 1.5), (776, RY + 2)], 5.4, a0=0.8)
art.line([(70, RY + 18), (240, RY + 19), (776, RY + 18)], 4.2)
x = 92.0
while x < 770:
    art.line([(x, RY + 6), (x + rng.uniform(-1, 1), RY + 14)], 3.4, a0=0.5, a1=0.6); x += rng.uniform(34, 44)

# ---------------------------------------------------------------- the concourse: a lit glass box under the platform
CT, CB, CX0 = RY + 34, 382.0, 236.0
art.line([(CX0, CT), (500, CT + 1), (776, CT)], 4.6, a0=0.6)
art.line([(CX0 - 4, CB), (500, CB + 1.2), (776, CB)], 5.0, a0=0.6)
art.line([(CX0, CT - 2), (CX0 + 1, CB + 2)], 4.2)
x = CX0 + 8
while x < 700:                            # lit panes between solid wall strips
    w_ = rng.uniform(64, 78)
    x1 = min(x + w_, 708)
    fill(Y, [(x, CT + 5), (x1, CT + 5), (x1, CB - 3), (x, CB - 3)])
    art.line([(x1 + 2, CT + 2), (x1 + 2 + rng.uniform(-0.6, 0.6), CB - 2)], 3.6, a0=0.5, a1=0.6)
    art.line([(x1 + 10, CT + 2), (x1 + 10 + rng.uniform(-0.6, 0.6), CB - 2)], 3.6, a0=0.5, a1=0.6)
    x = x1 + 12
# the open end: the way out to the footbridge and the grounds, one walking through it
fill(Y, [(722, CT + 5), (766, CT + 5), (766, CB - 3), (722, CB - 3)])
art.line([(722, CT + 2), (721, CB - 2)], 4.0)
prng = random.Random(5)
x = CX0 + 22
while x < 750:                            # everyone heading the same way: out, toward the grounds
    grp = prng.choice((1, 2, 2, 3))
    for g in range(grp):
        if x + g * 15 > 756:
            break
        people.mini(art, x + g * 15, CB - 4, prng.uniform(33, 39), prng, face=1, layer=K, stride=prng.uniform(0.5, 1.0))
    x += grp * 15 + prng.uniform(18, 40)

# ---------------------------------------------------------------- the platform canopy
ROOF = RY - 92
art.line([(200, ROOF + 14), (420, ROOF + 4), (770, ROOF - 4), (774, ROOF + 6)], 6.4, a0=0.6, a1=1.6)
art.line([(212, ROOF + 22), (520, ROOF + 10), (776, ROOF + 5)], 3.8)
for cx in (262.0, 420.0, 590.0, 752.0):
    art.line([(cx, ROOF + 20 - (cx - 200) * 0.03), (cx + 0.5, RY - 56)], 3.8, a1=1.2)

# ---------------------------------------------------------------- the last train, lit
TOP, BOT = RY - 50, RY - 4
WT, WB = TOP + 8, TOP + 27
CAR = 21.0 * M
NOSE = 744.0
def heads(a, b):
    hx = a + rng.uniform(2, 5)
    while hx < b - 3:
        if rng.random() < 0.88:
            r = rng.uniform(3.1, 4.0)
            hy = WT + r + rng.uniform(2.5, 5.5)
            art.D[K].ellipse([(hx - r) * hand.R, (hy - r * 1.1) * hand.R, (hx + r) * hand.R, (hy + r * 1.1) * hand.R], fill=255)
            sw = r * rng.uniform(1.6, 2.0)
            fill(K, [(hx - sw, WB), (hx - sw * 0.9, hy + r + 3), (hx, hy + r + 0.5), (hx + sw * 0.9, hy + r + 3), (hx + sw, WB)])
        hx += 2 * 3.6 + rng.uniform(3.4, 5.5)
for i in range(4):
    x1 = NOSE - CAR * i
    x0 = x1 - CAR + 4
    if x1 < 30:
        break
    xs = max(x0, 30.0)
    if i == 0:
        art.line([(xs, TOP), (x1 - 26, TOP), (x1 - 10, TOP + 3), (x1 - 2, TOP + 14), (x1 + 1, BOT - 3), (x1 - 3, BOT)], 4.4, a0=0.8)
        fill(K, [(x1 - 23, TOP + 5), (x1 - 11, TOP + 4.5), (x1 - 3, TOP + 15), (x1 - 2, WB), (x1 - 20, WB)])
        art.blob([(x1 - 26, WB + 4), (x1, WB + 4), (x1 + 0.5, BOT - 3), (x1 - 26, BOT - 3)], G, jit=0.01, gap=0)
        art.dot(x1 - 6, BOT - 8, 2.8, layer=Y)
    else:
        art.line([(xs, TOP + 0.5), (x1 - 3, TOP)], 4.2, a0=0.8)
        art.line([(x1 - 2, TOP + 2), (x1 - 1.5, BOT - 2)], 3.8)
    art.line([(xs + 4, BOT), (x1 - 6, BOT + 0.5)], 4.4, a0=0.6)
    edge = x1 - (28 if i == 0 else 6)
    gs = max(xs + 2, 40.0)
    art.blob([(gs, WB + 4), (x1 - (26 if i == 0 else 2), WB + 4.5), (x1 - (26 if i == 0 else 2), WB + 11), (gs, WB + 10.5)], G, jit=0.01, gap=0, n=50)
    for d in range(4):
        dx = x0 + 17 + d * 68
        a, b = (dx + 21, min(dx + 64, edge))
        if dx > 34 and dx + 17 < edge:     # a door: two leaves
            art.line([(dx, TOP + 5), (dx, BOT - 2)], 3.4, a0=0.5)
            art.line([(dx + 17, TOP + 5), (dx + 17, BOT - 2)], 3.4, a0=0.5)
        if b - a > 12 and a > 34:
            fill(Y, [(a, WT), (b, WT), (b, WB), (a, WB)])
            art.box([(a, WT), (b, WT), (b, WB), (a, WB)], 3.4, over=(-0.8, 1.4))
            heads(a + 1, b - 1)
art.line([(40, RY - 1), (760, RY - 1.5)], 3.6, a1=6)
art.line([(760, RY - 2), (764, RY - 22), (772, RY - 22)], 4.2)              # the buffer stop
art.line([(752, RY - 18), (774, RY - 18.5)], 5.2, a0=0.5, a1=0.5)

# ---------------------------------------------------------------- the jam: side-on, nose to tail, all facing the city
SHAPES = {   # (fraction of length, fraction of height) outline, front at 0
    'sedan': [(0.03, 0.18), (0.0, 0.48), (0.27, 0.58), (0.41, 1.0), (0.72, 1.0), (0.86, 0.62), (1.0, 0.58), (0.99, 0.2)],
    'hatch': [(0.03, 0.18), (0.0, 0.5), (0.25, 0.6), (0.4, 1.0), (0.86, 0.98), (1.0, 0.8), (0.99, 0.2)],
    'suv': [(0.03, 0.18), (0.0, 0.58), (0.22, 0.66), (0.33, 1.0), (0.95, 1.0), (1.0, 0.88), (0.99, 0.2)],
}
DIMS = {'sedan': (4.4, 1.5), 'hatch': (3.8, 1.5), 'suv': (4.6, 1.8)}
def vehicle(x0, kind, rng):
    Lm, Hm = DIMS[kind]
    L, Hh = Lm * M, Hm * M
    base = GY - 3.5
    T = lambda u, v: (x0 + u * L, base - v * Hh)
    pts = [T(u, v) for u, v in SHAPES[kind]]
    fill(K, pts, 0); fill(Y, pts, 0)
    dark = rng.random() < 0.35
    if dark:                               # a dark car: the body is ink, the glass is the paper
        art.blob(pts, K, jit=0.008, gap=0, shift=0.2, n=50)
    art.line(pts + [pts[0]], 3.8, wob=0.4, trem=0.3, a0=0.8)
    # side windows as one dark band split by a pillar, the driver's head against the glass
    if kind == 'sedan':
        win = [T(0.30, 0.6), T(0.42, 0.92), T(0.70, 0.92), T(0.80, 0.62)]
    elif kind == 'hatch':
        win = [T(0.28, 0.62), T(0.41, 0.92), T(0.84, 0.92), T(0.92, 0.66)]
    else:
        win = [T(0.25, 0.66), T(0.35, 0.92), T(0.93, 0.92), T(0.94, 0.66)]
    if dark:
        fill(K, win, 0)
        art.dot(win[1][0] + 6, base - Hh * 0.7, 3.0)
    else:
        art.line(win, 3.4, a0=0.5, a1=0.8, wob=0.3, trem=0.2)
        art.dot(win[1][0] + 6, base - Hh * 0.7, 3.0)                     # the driver, waiting
    for u in (0.19, 0.8):                  # wheels
        wx, wy = T(u, 0.0)
        art.dot(wx, wy - 1, 5.6)
        art.D[K].ellipse([(wx - 1.8) * hand.R, (wy - 2.8) * hand.R, (wx + 1.8) * hand.R, (wy + 0.8) * hand.R], fill=0)
    # the lights: headlights on, a pool of it on the road ahead; tail-lights dark red-less blocks
    hx, hy = T(0.0, 0.44)
    art.blob([(hx - 1, hy - 3), (hx + 5, hy - 3), (hx + 5, hy + 3), (hx - 1, hy + 3)], Y, jit=0.02, gap=0)
    tx, ty = T(1.0, 0.52)
    art.blob([(tx - 6, ty - 3), (tx + 0.5, ty - 3), (tx + 0.5, ty + 3), (tx - 6, ty + 3)], Y, jit=0.02, gap=0)   # tail-lights, braking
    return L

def auto(x0, rng):
    """the Bengaluru auto, side-on, facing left: black canvas hood, yellow front, green body, open sides"""
    L, Hh = 2.9 * M * 1.3, 1.9 * M * 1.3
    base = GY - 3.0
    T = lambda u, v: (x0 + u * L, base - v * Hh)
    body = [T(0.02, 0.16), T(0.0, 0.62), T(0.08, 0.92), T(0.18, 1.0), T(0.86, 1.0), T(1.0, 0.8), T(1.0, 0.2), T(0.95, 0.14)]
    fill(K, body, 0); fill(Y, body, 0)
    # the hood: a heavy black canopy over the top, coming down at the back
    fill(K, [T(0.1, 0.84), T(0.18, 1.0), T(0.86, 1.0), T(1.0, 0.8), T(1.0, 0.42), T(0.8, 0.42), T(0.78, 0.8), T(0.14, 0.8)])
    # yellow front: the cowl round the windscreen and the front panel down to the wheel
    art.blob([T(0.0, 0.18), T(0.2, 0.2), T(0.22, 0.48), T(0.12, 0.5), T(0.1, 0.82), T(0.02, 0.66)], Y, jit=0.01, gap=0, shift=0.3)
    # green: the body from the cowl back, under the open side
    art.blob([T(0.2, 0.16), T(1.0, 0.2), T(1.0, 0.42), T(0.22, 0.42)], G, jit=0.01, gap=0, shift=0.3)
    art.line([T(0.02, 0.16), T(0.0, 0.62), T(0.08, 0.9)], 3.6, a0=0.5)
    art.line([T(0.2, 0.15), T(0.97, 0.17)], 3.5, a0=0.5)
    art.line([T(0.22, 0.42), T(0.24, 0.8)], 3.4)                               # the front pillar of the open side
    hx, hy = T(0.34, 0.62); art.dot(hx, hy, 3.4)                               # driver
    hx, hy = T(0.64, 0.6); art.dot(hx, hy, 3.4)                                # a passenger
    for u, r in ((0.1, 4.4), (0.84, 4.8)):
        wx, wy = T(u, 0.0)
        art.dot(wx, wy - 1, r)
    return L

def bus(x0, rng):
    """a plain city bus, side-on, its windows lit, no boards"""
    L, Hh = 11.0 * M, 3.0 * M
    base = GY - 3.0
    T = lambda u, v: (x0 + u * L, base - v * Hh)
    body = [T(0.0, 0.08), T(0.0, 1.0), T(1.0, 1.0), T(1.0, 0.08)]
    fill(K, body, 0); fill(Y, body, 0)
    art.box(body, 4.0)
    fill(Y, [T(0.03, 0.5), T(0.97, 0.5), T(0.97, 0.86), T(0.03, 0.86)])
    art.line([T(0.03, 0.5), T(0.97, 0.5)], 3.4); art.line([T(0.03, 0.86), T(0.97, 0.86)], 3.4)
    u = 0.12
    while u < 0.95:
        art.line([T(u, 0.5), T(u, 0.86)], 3.4, a0=0.4, a1=0.5); u += rng.uniform(0.1, 0.13)
    hx = 0.06
    while hx < 0.94:                       # standing passengers
        if rng.random() < 0.7:
            px_, py_ = T(hx, 0.7); art.dot(px_, py_, 3.3)
            fill(K, [(px_ - 5, T(0, 0.5)[1]), (px_ - 4, py_ + 4), (px_ + 4, py_ + 4), (px_ + 5, T(0, 0.5)[1])])
        hx += rng.uniform(0.04, 0.07)
    art.line([T(0.08, 0.1), T(0.08, 0.45), T(0.16, 0.45), T(0.16, 0.1)], 3.5)        # the front door
    for u_ in (0.17, 0.78):
        wx, wy = T(u_, 0.0); art.dot(wx, wy - 1, 6.4)
        art.D[K].ellipse([(wx - 2) * hand.R, (wy - 3) * hand.R, (wx + 2) * hand.R, (wy + 1) * hand.R], fill=0)
    hx, hy = T(0.0, 0.25)
    art.blob([(hx - 1, hy - 3), (hx + 5, hy - 3), (hx + 5, hy + 3), (hx - 1, hy + 3)], Y, jit=0.02, gap=0)
    return L

def bike(x0, rng):
    """a two-wheeler squeezing through, two up, the pillion's arm round the rider"""
    L = 2.0 * M
    base = GY - 3.0
    for u, r in ((0.1, 4.2), (0.88, 4.2)):
        art.dot(x0 + u * L, base - 1, r)
    art.blob([(x0 + 4, base - 6), (x0 + L - 3, base - 7), (x0 + L - 6, base - 13), (x0 + 9, base - 13)], K, jit=0.02, gap=0)
    for k, dx in enumerate((0.34, 0.7)):
        hx = x0 + dx * L
        art.dot(hx, base - 27 + k * 1.5, 3.4)
        fill(K, [(hx - 4, base - 12), (hx - 4.5, base - 23 + k), (hx + 4, base - 23 + k), (hx + 3, base - 12)])
    art.line([(x0 + 0.34 * L - 2, base - 20), (x0 + 2, base - 15)], 3.6)         # the rider's arm to the bars
    art.blob([(x0 - 1, base - 11), (x0 + 4, base - 11), (x0 + 4, base - 6), (x0 - 1, base - 6)], Y, jit=0.02, gap=0)
    return L

x = 18.0
order = ['hatch', 'sedan', 'suv', 'bike', 'hatch', 'gap', 'auto', 'gap', 'sedan', 'hatch', 'bus', 'hatch', 'suv', 'sedan', 'hatch']
vr = random.Random(9)
for kind in order:
    if x > 770:
        break
    if kind == 'gap':
        x += 10; continue
    L = {'auto': auto, 'bus': bus, 'bike': bike}.get(kind, lambda x_, r_: vehicle(x_, kind, r_))(x, vr)
    x += L + vr.uniform(1.5, 4)

# ---------------------------------------------------------------- the rain tree over the footpath, in front of it all
TRX = 96.0
crown = []
for k in range(34):                       # a wide flat umbrella, lumpy at the rim
    t = math.pi + math.pi * k / 33
    rx, ry = 128 * (1 + 0.06 * math.sin(5 * t + 1)), 64 * (1 + 0.1 * math.sin(7 * t))
    crown.append((TRX + 10 + rx * math.cos(t), 308 + ry * 1.45 * math.sin(t) * (1.0 if math.sin(t) < 0 else 0.3)))
under = [(TRX + 138, 308), (TRX + 90, 328), (TRX + 20, 338), (TRX - 50, 330), (TRX - 118, 308)]
cr = crown + under
from PIL import Image, ImageDraw
cm = Image.new('L', (hand.W, hand.H), 0); ImageDraw.Draw(cm).polygon(P(cr), fill=255)
halo = cm.filter(ImageFilter.MaxFilter(int(3 * hand.R) * 2 + 1))
for k in (K, Y, G, S):
    art.L[k].paste(0, (0, 0), halo)
art.blob(cr, G, jit=0.03, gap=0, n=80, scale=(0.98, 1.0))
# leaf clusters: scalloped key edges along the top and the underside, and the branches showing under the crown
for k in range(0, 34, 2):
    a = crown[k]
    art.line([(a[0] - 7, a[1] + 3), (a[0], a[1] - 4), (a[0] + 8, a[1] + 2)], 3.4, a0=0.6, a1=1.0)
for k in range(len(under) - 1):
    a, b = under[k], under[k + 1]
    for j in range(3):
        u = (j + 0.5) / 3
        cx_, cy_ = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
        art.line([(cx_ - 9, cy_ - 2), (cx_, cy_ + 4), (cx_ + 9, cy_ - 1)], 3.4, a0=0.6, a1=1.0)
trunk = [(TRX - 9, GY), (TRX - 6, 400), (TRX - 2, 360), (TRX + 8, 360), (TRX + 10, 400), (TRX + 12, GY)]
fill(K, trunk, 0); fill(Y, trunk, 0)
art.knock(trunk)
art.line([(TRX - 9, GY), (TRX - 6, 400), (TRX - 3, 352)], 4.6, a0=0.6)
art.line([(TRX + 12, GY), (TRX + 10, 400), (TRX + 9, 352)], 4.6, a0=0.6)
for bx, by, ex, ey in ((TRX - 2, 356, TRX - 70, 318), (TRX + 6, 352, TRX + 40, 322), (TRX + 9, 356, TRX + 96, 318), (TRX, 356, TRX - 10, 320)):
    art.line([(bx, by), ((bx + ex) / 2, (by + ey) / 2 + 4), (ex, ey)], 4.0, a0=0.6, a1=2.0)
hatch_poly(art, [(TRX - 6, 440), (TRX - 3, 365), (TRX + 1, 365), (TRX - 1, 440)], K, 1.5, 8.0, w=3.4)

inks = art.finish(order=('yellow', 'green', 'sound', 'key'), shifts={'yellow': (1.4, -0.8), 'green': (-1.0, 1.0), 'sound': (0.8, 0.6)})
pal = {'key': INK['key'], 'green': INK['green'], 'yellow': INK['yellow'], 'sound': INK['sound']}
rgba = composite(inks, pal, order=('yellow', 'green', 'sound', 'key'))
rgba = rgba.crop((0, int(158 * hand.R), rgba.width, rgba.height))   # the empty sky cut away: 12.8 cm tall
save(rgba, HERE, DRAFT)
