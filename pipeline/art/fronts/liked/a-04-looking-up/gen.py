#!/usr/bin/env python3
"""
04 looking up: the back looks down on the course; this one lies on the infield and looks up, east, at 10 pm on
8 December 2026. New moon is on the 9th, so the nights are moonless. Positions are computed for Mahalaxmi
(18.98 N, 72.82 E) at 16:30 UT: Orion stands about 40 degrees up in the east, Aldebaran and the Pleiades above him,
Sirius 18 degrees up in the east-south-east, Procyon just over the towers, Capella high to the north-east.
City haze leaves only the bright ones, so only stars to about magnitude 3.5 are drawn.
A printmaker's star chart in a fish-eye: the zenith above the print, the horizon a curved bowl along the bottom,
everything vertical (towers, the stage roof's truss, the rain trees round the course) leaning in toward the zenith.
Centre chest, 22 cm.    R=1 python3 gen.py (draft)  |  python3 gen.py (print size)
"""
import math, os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import front as F

WMM, HMM = 220, 206
F.setup(WMM, HMM, draft_px=4.5)
import hand
from hand import Art, hatch_poly

art = Art(seed=404, layers=('green', 'water', 'ring', 'key'))
rng = art.rng

# ---------------------------------------------------------------- the sky at 22:00 IST, 8 Dec 2026, Mahalaxmi
LAT, LON = 18.98, 72.82
UT = datetime.datetime(2026, 12, 8, 16, 30)
jd = (UT - datetime.datetime(2000, 1, 1, 12)).total_seconds() / 86400
LST = (280.46061837 + 360.98564736629 * jd + LON) % 360
STARS = {   # name: (RA deg, Dec deg, magnitude)
    'sirius': (101.29, -16.72, -1.46), 'capella': (79.17, 46.00, 0.08), 'rigel': (78.63, -8.20, 0.13),
    'procyon': (114.83, 5.22, 0.34), 'betelgeuse': (88.79, 7.41, 0.50), 'aldebaran': (68.98, 16.51, 0.85),
    'elnath': (81.57, 28.61, 1.65), 'bellatrix': (81.28, 6.35, 1.64), 'alnilam': (84.05, -1.20, 1.69),
    'alnitak': (85.19, -1.94, 1.77), 'saiph': (86.94, -9.67, 2.06), 'mintaka': (83.00, -0.30, 2.23),
    'iota_ori': (83.86, -5.91, 2.77), 'meissa': (83.78, 9.93, 3.39), 'menkalinan': (89.88, 44.95, 1.90),
    'alcyone': (56.87, 24.11, 2.87), 'atlas': (57.29, 24.05, 3.62), 'electra': (56.22, 24.11, 3.70),
    'maia': (56.46, 24.37, 3.87), 'merope': (56.58, 23.95, 4.18), 'taygeta': (56.30, 24.47, 4.30),
    'theta2_tau': (67.17, 15.87, 3.40), 'gamma_tau': (64.95, 15.63, 3.65), 'epsilon_tau': (67.15, 19.18, 3.53),
    'delta_tau': (65.73, 17.54, 3.76), 'zeta_tau': (84.41, 21.14, 3.00), 'mirzam': (95.67, -17.96, 1.98),
    'alhena': (99.43, 16.40, 1.93), 'gomeisa': (111.79, 8.29, 2.89),
}


def altaz(ra, dec):
    la, de = math.radians(LAT), math.radians(dec)
    H = math.radians(LST - ra)
    alt = math.asin(math.sin(la) * math.sin(de) + math.cos(la) * math.cos(de) * math.cos(H))
    az = math.atan2(-math.sin(H) * math.cos(de), math.cos(la) * math.sin(de) - math.sin(la) * math.cos(de) * math.cos(H))
    return math.degrees(alt), math.degrees(az) % 360


# the chart: zenith above the print, east-by-south straight down, north to the left (we face east, looking up)
ZX, ZY, RH, AZC = 110.0, -30.0, 226.0, 101.0


def sky(alt, az):
    r = (90.0 - alt) / 90.0 * RH
    th = math.radians(az - AZC)
    return ZX + r * math.sin(th), ZY + r * math.cos(th)


S = {}
for k, (ra, dec, mag) in STARS.items():
    a, z = altaz(ra, dec)
    S[k] = (sky(a, z), mag, a)


def inside(p, m=6):
    return m < p[0] < WMM - m and m < p[1] < HMM - m


# ---------------------------------------------------------------- altitude circles: faint, broken, like a chart's grid
for alt in (30, 60):
    r = (90 - alt) / 90 * RH
    a = -1.2
    while a < 1.2:
        b = a + rng.uniform(0.07, 0.16)
        arc = [(ZX + r * math.sin(a + (b - a) * t / 6), ZY + r * math.cos(a + (b - a) * t / 6)) for t in range(7)]
        arc = [p for p in arc if inside(p, 8)]
        if len(arc) > 2:
            art.line(arc, 1.1, layer='water', wob=0.1, trem=0.1, a0=0.8, a1=1.2)
        a = b + rng.uniform(0.05, 0.09)

# ---------------------------------------------------------------- the figures: pencil-dash lines between the stars
FIG = [('meissa', 'betelgeuse'), ('meissa', 'bellatrix'), ('betelgeuse', 'bellatrix'), ('betelgeuse', 'alnitak'),
       ('bellatrix', 'mintaka'), ('mintaka', 'alnilam'), ('alnilam', 'alnitak'), ('alnitak', 'saiph'),
       ('mintaka', 'rigel'), ('aldebaran', 'theta2_tau'), ('theta2_tau', 'gamma_tau'), ('gamma_tau', 'delta_tau'),
       ('delta_tau', 'epsilon_tau'), ('epsilon_tau', 'elnath'), ('aldebaran', 'zeta_tau')]


def dashes(a, b, layer, w=1.1, dash=(2.6, 4.2), gap=(1.6, 2.6), trim=3.2):
    (x0, y0), (x1, y1) = a, b
    L = math.hypot(x1 - x0, y1 - y0)
    if L < 2 * trim + 2:
        return
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    t = trim
    while t < L - trim:
        d = min(rng.uniform(*dash), L - trim - t)
        if d > 1.2:
            p, q = (x0 + ux * t, y0 + uy * t), (x0 + ux * (t + d), y0 + uy * (t + d))
            art.line([p, ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2), q], w, layer=layer, wob=0.05, trem=0.0, a0=0.6, a1=1.0)
        t += d + rng.uniform(*gap)


for a, b in FIG:
    if inside(S[a][0], 0) and inside(S[b][0], 0):
        dashes(S[a][0], S[b][0], 'ring')
# the old way to find Sirius: follow the belt down and left... here, down and right
bx, by = S['alnitak'][0]
dashes((bx, by), S['sirius'][0], 'water', dash=(1.6, 2.4), gap=(2.6, 3.6), trim=5.0)


# ---------------------------------------------------------------- the stars: hand-drawn marks, size by brightness
def star(p, mag):
    x, y = p
    if mag < 0.0:          # Sirius: eight rays, the long ones uneven, a solid heart
        n, L0, w = 8, 7.4, 1.6
    elif mag < 1.0:
        n, L0, w = 6, 5.6 - mag * 1.0, 1.45
    elif mag < 2.1:
        n, L0, w = 4, 3.6 - (mag - 1) * 0.6, 1.3
    elif mag < 3.0:
        n, L0, w = 4, 2.2, 1.15
    else:
        art.dot(x, y, 0.85 + max(0, 3.9 - mag) * 0.12, layer='key')
        return
    ph = rng.uniform(0, math.pi / n)
    for i in range(n):
        a = ph + math.pi * 2 * i / n + rng.gauss(0, 0.06)
        L = L0 * (1.0 if i % 2 == 0 else 0.62) * rng.uniform(0.85, 1.12)
        art.line([(x - math.cos(a) * 0.4, y - math.sin(a) * 0.4), (x + math.cos(a) * L, y + math.sin(a) * L)], w,
                 layer='key', wob=0.04, trem=0.0, a0=0.5, a1=2.2)
    art.dot(x, y, w * (0.95 if mag < 1 else 0.75), layer='key')


PLE = ('alcyone', 'atlas', 'electra', 'maia', 'merope', 'taygeta')
pc = (sum(S[k][0][0] for k in PLE) / 6, sum(S[k][0][1] for k in PLE) / 6)
for k in PLE:   # the Pleiades drawn spread (x2.3 about their middle) so the six read as six
    (x, y), m, a = S[k]
    S[k] = ((pc[0] + (x - pc[0]) * 2.3, pc[1] + (y - pc[1]) * 2.3), m, max(a, 10))
for k, (p, mag, alt) in S.items():
    if inside(p) and alt > 9:
        star(p, 3.0 if k in ('mintaka', 'alnilam', 'alnitak') or k in PLE else mag)

# ---------------------------------------------------------------- the horizon: everything leans to the zenith
def radial(az, alt0, alt1):
    return sky(alt0, az), sky(alt1, az)


# the towers east of the course (Lower Parel side), over the trees: tall slabs, hatched, lit windows left as paper
for az0, wdeg, top in [(AZC + 9, 2.8, 12.5), (AZC + 13.2, 2.0, 15.4), (AZC + 19.5, 3.4, 9.8), (AZC + 25.5, 2.2, 13.2),
                       (AZC - 12, 2.4, 11.2), (AZC - 16.5, 1.8, 13.6), (AZC + 31, 2.8, 8.6), (AZC + 3.5, 1.6, 7.6)]:
    a0, a1 = az0 - wdeg / 2, az0 + wdeg / 2
    poly = [sky(2.0, a0), sky(top, a0), sky(top + rng.uniform(-0.3, 0.3), a1), sky(2.0, a1)]
    if not all(-4 < p[0] < WMM + 4 for p in poly):
        continue
    hatch_poly(art, poly, 'key', angle=math.atan2(ZY - poly[0][1], ZX - poly[0][0]) + rng.gauss(0, 0.04), spacing=2.5, w=1.1, gap=(0.0, 0.2))
    art.box(poly[:3] + poly[3:], 1.2, layer='key', over=(-0.5, 1.8))
    for _ in range(int(wdeg * 1.6)):   # a few lit windows (knocked out of the hatching)
        wa = rng.uniform(a0 + 0.5, a1 - 0.5); wh = rng.uniform(5.5, top - 1.2)
        c = sky(wh, wa)
        art.knock([(c[0] - 0.8, c[1] - 0.8), (c[0] + 0.8, c[1] - 0.8), (c[0] + 0.8, c[1] + 0.8), (c[0] - 0.8, c[1] + 0.8)], layers=('key',))

# the stage roof, low on the left (the stage is at the course's north-east end): a hatched roof slab on its truss,
# scaffold legs, and a line array hanging off the front corner (a curved column of boxes)
st_a0, st_a1 = AZC - 33, AZC - 17
roof = [sky(15.4, st_a0), sky(17.6, st_a0 + 1.5), sky(17.6, st_a1 - 1.5), sky(15.4, st_a1)]
hatch_poly(art, roof, 'key', angle=0.9, spacing=2.3, w=1.1)
art.box(roof, 1.2, layer='key', over=(-0.4, 1.6))
for h in (13.6, 15.2):
    art.line([sky(h, st_a0 + i * (st_a1 - st_a0) / 6) for i in range(7)], 1.15, layer='key', wob=0.08, trem=0.1)
for i in range(10):
    a = st_a0 + i * (st_a1 - st_a0) / 9
    b = st_a0 + (i + 0.5) * (st_a1 - st_a0) / 9
    if b < st_a1:
        art.line([sky(13.6, a), sky(15.2, b)], 1.1, layer='key', wob=0.04, trem=0.0, a0=0.5, a1=0.8)
for a in (st_a0 + 0.6, st_a1 - 0.6):
    art.line([sky(13.6, a), sky(3.0, a)], 1.3, layer='key', wob=0.06, trem=0.08)
for side, a in ((1, st_a0 + 2.2), (-1, st_a1 - 2.2)):
    for j in range(6):   # the array: boxes hung in a J, splaying out toward the bottom
        h0 = 12.8 - j * 1.25
        da = side * j * j * 0.06
        box = [sky(h0, a + da), sky(h0, a + da + side * 2.2), sky(h0 - 1.0, a + da + side * 2.3), sky(h0 - 1.0, a + da + side * 0.1)]
        art.fill(box, 'key')

# the rain trees round the course perimeter, in front of everything: crowns as loose green screens, their tops
# inked in short scalloped strokes, their feet left ragged where the drawing stops
crowns = []
az = AZC - 44
while az < AZC + 44:
    h = rng.uniform(3.2, 5.6)
    rad = rng.uniform(6.0, 9.5)
    crowns.append((az, h, rad))
    az += rng.uniform(2.0, 3.4)
for az, h, rad in crowns:
    c = sky(h, az)
    dx, dy = ZX - c[0], ZY - c[1]
    L = math.hypot(dx, dy); ux, uy = dx / L, dy / L          # toward the zenith: "up" for this tree
    poly = []
    for i in range(14):
        t = math.pi * 2 * i / 14
        rr = rad * rng.uniform(0.82, 1.08)
        px_, py_ = math.cos(t) * rr, math.sin(t) * rr * 0.72
        poly.append((c[0] + px_ * -uy + py_ * ux, c[1] + px_ * ux + py_ * uy))
    art.knock(poly, layers=('key',))
    art.blob(poly, 'green', jit=0.05, gap=0.25, shift=0.5, n=40)
    top = [p for p in hand.catmull(poly + poly[:1], closed=True, step=0.8) if (p[0] - c[0]) * ux + (p[1] - c[1]) * uy > rad * 0.18]
    if len(top) > 4:
        top.sort(key=lambda p: (p[0] - c[0]) * -uy + (p[1] - c[1]) * ux)
        for j in range(0, len(top), 7):
            seg = top[j:j + rng.randint(5, 9)]
            if len(seg) > 2 and rng.random() < 0.8:
                art.line(seg[::2], 1.15, layer='key', wob=0.1, trem=0.1, a0=0.8, a1=1.8)
    # the trunk: a short stroke down from the crown, toward the ground
    if rng.random() < 0.45:
        foot = (c[0] - ux * rad * 0.95, c[1] - uy * rad * 0.95)
        art.line([(c[0] - ux * rad * 0.5, c[1] - uy * rad * 0.5), foot], 1.15, layer='key', wob=0.1, trem=0.1, a0=0.6, a1=2.0)

order = ('green', 'water', 'ring', 'key')
inks = art.finish(order=order, shifts={'green': (0.4, -0.3), 'water': (-0.3, 0.3), 'ring': (0.25, 0.4)}, trim=False)
for k, (p, mag, alt) in S.items():
    print(f'{k:12s} alt {alt:5.1f}  at {p[0]:6.1f} {p[1]:6.1f}') if mag < 1.0 else None
F.save(art, inks, order, __file__)
