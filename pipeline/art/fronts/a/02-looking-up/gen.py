#!/usr/bin/env python3
"""
02 looking up (continued from the liked first-round draft, cut back to a chest piece): the back looks down on the course; this one lies on the infield and looks up, east, at 10 pm on
8 December 2026. New moon is on the 9th, so the nights are moonless. Positions are computed for Mahalaxmi
(18.98 N, 72.82 E) at 16:30 UT: Orion stands about 40 degrees up in the east, Aldebaran and the Pleiades above him,
Sirius 18 degrees up in the east-south-east, Procyon just over the towers, Capella high to the north-east.
City haze leaves only the bright ones, so only stars to about magnitude 3.5 are drawn.
A printmaker's star chart in a fish-eye: the zenith above the print, the horizon a curved bowl along the bottom,
everything vertical (towers, the stage roof's truss, the rain trees round the course) leaning in toward the zenith.
Cut back for the chest: two altitude arcs, Orion and the
stars round him, the towers and the rain trees in the bowl, and the name set along the horizon's curve under them.
Centre chest, 17 cm.    R=1 python3 gen.py (draft)  |  python3 gen.py (print size)
"""
import math, os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import front as F

WMM, HMM = 172, 194
F.setup(WMM, HMM, draft_px=4.5)
import hand
from hand import Art, hatch_poly
from PIL import Image, ImageDraw, ImageFilter

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
K = 0.78
ZX, ZY, RH, AZC = 86.0, -23.4, 226.0 * K, 101.0


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
       ('mintaka', 'rigel'), ('aldebaran', 'elnath'), ('aldebaran', 'zeta_tau')]   # Orion, and the bull's two horns


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
    if not (inside(p) and alt > 9):
        continue
    if k in ('mintaka', 'alnilam', 'alnitak'):
        star(p, 3.0)
    elif k in ('alcyone', 'atlas', 'electra'):
        star(p, 2.6)                      # the Pleiades kept as the three a city sky still shows
    elif mag < 2.2:
        star(p, mag)
    elif any(k in pair for pair in FIG):
        star(p, 3.0)                      # a figure's corner: a plain dot, so no dashed line ends in nothing

# ---------------------------------------------------------------- the horizon: everything leans to the zenith
def radial(az, alt0, alt1):
    return sky(alt0, az), sky(alt1, az)


# the towers east of the course (any that would stand under a bright star are left out, so the star has clear sky) (Lower Parel side), over the trees: tall slabs, hatched, lit windows left as paper
for az0, wdeg, top in [(AZC + 8.6, 3.4, 15.5), (AZC + 13.4, 2.6, 19.5), (AZC + 19.6, 3.8, 12.0), (AZC + 3.6, 2.2, 10.2),
                       (AZC + 24.2, 2.6, 14.6), (AZC - 7.2, 2.4, 12.4),
                       (AZC - 12.5, 3.0, 14.2), (AZC - 17.6, 2.4, 17.4), (AZC - 22.4, 3.2, 10.6)]:
    a0, a1 = az0 - wdeg / 2, az0 + wdeg / 2
    for k_, ((ra_, de_, mg_)) in STARS.items():   # never under a bright star: the tower stops well short of it
        al_, az_ = altaz(ra_, de_)
        if mg_ < 1.0 and a0 - 3.5 < az_ < a1 + 3.5 and 4 < al_ < top + 5:
            top = -1
    if top < 0:
        continue
    poly = [sky(4.6, a0), sky(top, a0), sky(top + rng.uniform(-0.3, 0.3), a1), sky(4.6, a1)]
    if not all(-4 < p[0] < WMM + 4 for p in poly):
        continue
    hatch_poly(art, poly, 'key', angle=math.atan2(ZY - poly[0][1], ZX - poly[0][0]) + rng.gauss(0, 0.04), spacing=2.7, w=1.1, gap=(0.0, 0.2))
    art.box(poly[:3] + poly[3:], 1.2, layer='key', over=(-0.5, 1.8))
    for _ in range(int(wdeg * 1.6)):   # a few lit windows (knocked out of the hatching)
        wa = rng.uniform(a0 + 0.5, a1 - 0.5); wh = rng.uniform(5.5, top - 1.2)
        c = sky(wh, wa)
        art.knock([(c[0] - 0.8, c[1] - 0.8), (c[0] + 0.8, c[1] - 0.8), (c[0] + 0.8, c[1] + 0.8), (c[0] - 0.8, c[1] + 0.8)], layers=('key',))

# the rain trees round the course perimeter, in front of everything. A rain tree is an umbrella: a crown much wider
# than tall, its top a run of soft domes, its underside flat, a short forked trunk under it. Each crown is a loose
# green screen with a paper gap round it where it overlaps the next, its domes inked in short strokes.
crowns = []
az = AZC - 26
while az < AZC + 26:
    edge = abs(az - AZC) / 26
    h = rng.uniform(3.6, 5.0) - 1.0 * edge
    rad = rng.uniform(7.6, 10.2) * (1 - 0.4 * edge ** 2)          # smaller toward the ends, where the drawing stops
    crowns.append((az, h, rad))
    az += rng.uniform(3.6, 4.8) * (1 + 0.25 * edge)
rng.shuffle(crowns)
for az, h, rad in crowns:
    c = sky(h, az)
    dx, dy = ZX - c[0], ZY - c[1]
    L = math.hypot(dx, dy); ux, uy = dx / L, dy / L          # toward the zenith: "up" for this tree
    nd = rng.randint(4, 5)
    ph = [rng.uniform(-0.25, 0.25) for _ in range(nd + 1)]
    poly = []
    for i in range(48):
        t = math.pi * 2 * i / 48
        across, upc = math.cos(t), math.sin(t)
        if upc > 0:      # the top: a run of domes
            k = (across + 1) / 2 * nd
            j = min(nd - 1, int(k))
            bump = math.sin((k - j) * math.pi) ** 0.6
            rr_up = rad * 0.72 * (0.74 + 0.26 * bump + ph[j] * 0.15)
            px_, py_ = across * rad, upc * rr_up
        else:            # the underside: nearly flat, a little sag
            px_, py_ = across * rad * 0.96, upc * rad * 0.26
        poly.append((c[0] + px_ * -uy + py_ * ux, c[1] + px_ * ux + py_ * uy))
    halo = [(c[0] + (x - c[0]) * 1.12, c[1] + (y - c[1]) * 1.16) for x, y in poly]
    art.knock(halo, layers=('green', 'key'))
    art.blob(poly, 'green', jit=0.02, gap=0.0, shift=0.35, n=60, scale=(0.98, 1.0))
    # the domes inked: short strokes along the top, some left out
    top = [p for p in hand.catmull(poly + poly[:1], closed=True, step=0.7) if (p[0] - c[0]) * ux + (p[1] - c[1]) * uy > rad * 0.12]
    top.sort(key=lambda p: (p[0] - c[0]) * -uy + (p[1] - c[1]) * ux)
    j = 0
    while j < len(top) - 3:
        n = rng.randint(6, 11)
        seg = top[j:j + n]
        if len(seg) > 3 and rng.random() < 0.75:
            art.line(seg[::2], 1.15, layer='key', wob=0.06, trem=0.06, a0=0.8, a1=1.8)
        j += n + rng.randint(1, 4)
    # the trunk: a short fork from the underside down to the ground, on the bigger trees
    if False:   # forked trunks read as cartoon Ys at chest size: the crowns stand on the horizon instead
        base = (c[0] - ux * rad * 0.16, c[1] - uy * rad * 0.16)
        foot = (base[0] - ux * 3.6 + rng.uniform(-0.3, 0.3), base[1] - uy * 3.6)
        for side in (-1, 1):
            arm = (base[0] + side * -uy * rad * 0.32, base[1] + side * ux * rad * 0.32)
            mid = (foot[0] + (base[0] - foot[0]) * 0.45, foot[1] + (base[1] - foot[1]) * 0.45)
            art.line([foot, mid, arm], 1.15, layer='key', wob=0.05, trem=0.0, a0=0.8, a1=1.6)

# the name, set along the horizon's curve under the trees (each letter upright to the zenith), dots in ring blue
NAME, NSIZE = 'fred again', 15.0
RT = (90 + 6.8) / 90 * RH                        # a little under the horizon
f = F.font('brico', NSIZE, 800)
adv = [f.getlength(c) / hand.R for c in NAME]
DSTEP, DR = 4.9, 1.75
total = sum(adv) + 1.0 + DSTEP + DR * 2
s0 = -total / 2
letters = []
for c, a in zip(NAME, adv):
    if c != ' ':
        th = (s0 + a / 2) / RT
        letters.append((c, th))
    s0 += a
dot_th = [(s0 + 1.0 + DR + i * DSTEP) / RT for i in range(2)]
for th in dot_th:
    r = RT - DR
    art.dot(ZX + r * math.sin(th), ZY + r * math.cos(th), DR, layer='ring')

order = ('green', 'water', 'ring', 'key')
inks = art.finish(order=order, shifts={'green': (0.4, -0.3), 'water': (-0.3, 0.3), 'ring': (0.25, 0.4)}, trim=False)
for k, (p, mag, alt) in S.items():
    print(f'{k:12s} alt {alt:5.1f}  at {p[0]:6.1f} {p[1]:6.1f}') if mag < 1.0 else None
def curve_text(layer, text, fnt, size, r, grow=3):
    """set text along the circle of radius r round the zenith, centred under it, each letter upright to the zenith"""
    adv_ = [fnt.getlength(c) / hand.R for c in text]
    s_ = -sum(adv_) / 2
    S_ = int(size * 2.2 * hand.R)
    for c, a in zip(text, adv_):
        th = (s_ + a / 2) / r
        s_ += a
        if c == ' ':
            continue
        im = Image.new('L', (S_, S_), 0)
        ImageDraw.Draw(im).text((S_ / 2, S_ / 2), c, font=fnt, fill=255, anchor='ms')   # baseline-middle at the centre
        im = im.rotate(math.degrees(th), resample=Image.BICUBIC).point(lambda p: 255 if p >= 128 else 0)
        if grow:
            im = im.filter(ImageFilter.MaxFilter(grow))
        x, y = ZX + r * math.sin(th), ZY + r * math.cos(th)
        inks[layer].paste(255, (int(x * hand.R - S_ / 2), int(y * hand.R - S_ / 2)), im)


S_ = int(NSIZE * 2.2 * hand.R)
for c, th in letters:
    im = Image.new('L', (S_, S_), 0)
    ImageDraw.Draw(im).text((S_ / 2, S_ / 2), c, font=f, fill=255, anchor='ms')
    im = im.rotate(math.degrees(th), resample=Image.BICUBIC).point(lambda p: 255 if p >= 128 else 0).filter(ImageFilter.MaxFilter(3))
    x, y = ZX + RT * math.sin(th), ZY + RT * math.cos(th)
    inks['key'].paste(255, (int(x * hand.R - S_ / 2), int(y * hand.R - S_ / 2)), im)
# the chart's caption under the name: where, when, which way
CAP = '8 dec, 10 pm, looking east'
curve_text('ring', CAP, F.font('shantell', 8.6, 800), 8.6, RT + 13.4, grow=0)
F.finish_out(art, inks, order, __file__)
F.write_placement(__file__, 'centre chest', 17, 11)
