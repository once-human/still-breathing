#!/usr/bin/env python3
"""
Still Breathing / lineup 01 "again.." -- BENGALURU, design 04 "map"
"the ground you stood on": a printmaker's top-down map of the NICE grounds at
the Bangalore International Exhibition Centre, Madavara, on Tumakuru Road,
drawn from real OpenStreetMap geometry (osm-site.json, cached Overpass extract).

Pillow + numpy. Seeded, re-runnable.
    python3 gen.py            -> full 3600x4800 render (R=3 px per unit)
    R=1.5 python3 gen.py      -> draft (files get a -draft suffix)

Units: layout lives in a 1200 x 1600 unit space; px = unit * R.
Every ink is its own binary layer (key / green / blue / accent), built from
hand-like vector marks: a pressure-varying brush laid along a jittered
Catmull-Rom path (tremor, swell, lift taper, the odd re-drawn pass), uneven
stipple, hatching with uneven spacing. The map thins out object by object to
a ragged edge; then ink spread, minimum-feature clean-up,
misregistration and a binary alpha.
"""
import json, math, os, random, time
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
R = float(os.environ.get('R', '3'))
UW, UH = 1200, 1600
W, H = int(round(UW * R)), int(round(UH * R))
SUFFIX = '' if R >= 3 else '-draft'
SEED = 12122026
TAU = math.tau
T0 = time.time()


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


# --------------------------------------------------------------------------
# projection: lon/lat -> local metres (cos-lat corrected) -> rotate -> units
# Tumakuru Road becomes the long diagonal of the page; the halls sit at the
# top, Anchepalya lake at the foot, the NICE Road runs out bottom-left.
# --------------------------------------------------------------------------
LAT_C, LON_C = 13.05742, 77.47281             # Madavara station
MLAT = 110574.0
MLON = 111320.0 * math.cos(math.radians(LAT_C))
ROT = math.radians(-30.0)
SCALE = 0.78                                  # units per metre
CX, CY = 404.0, 668.0                         # where the station lands
cosR, sinR = math.cos(ROT), math.sin(ROT)

_wr = random.Random(SEED + 1)
WARP = []
for _ in range(5):                            # slow "drawn by eye" distortion of the whole map
    ang = _wr.uniform(0, TAU)
    lam = _wr.uniform(180, 560)
    WARP.append((math.cos(ang) * TAU / lam, math.sin(ang) * TAU / lam,
                 _wr.uniform(0, TAU), _wr.uniform(0, TAU), _wr.uniform(0.6, 1.6)))


def warp(u, v):
    dx = dy = 0.0
    for fx, fy, p1, p2, a in WARP:
        s = fx * u + fy * v
        dx += a * math.sin(s + p1)
        dy += a * math.sin(s + p2)
    return u + dx, v + dy


def proj(lat, lon):
    x = (lon - LON_C) * MLON
    y = (lat - LAT_C) * MLAT
    xr = x * cosR - y * sinR
    yr = x * sinR + y * cosR
    return warp(CX + xr * SCALE, CY - yr * SCALE)


def unproj(u, v):
    xr = (u - CX) / SCALE
    yr = -(v - CY) / SCALE
    x = xr * cosR + yr * sinR
    y = -xr * sinR + yr * cosR
    return LAT_C + y / MLAT, LON_C + x / MLON


# --------------------------------------------------------------------------
# geometry helpers
# --------------------------------------------------------------------------
def densify(pts, step):
    out = [pts[0]]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(L / step))
        for k in range(1, n + 1):
            t = k / n
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    return out


def cumlen(pts):
    s = [0.0]
    for i in range(1, len(pts)):
        s.append(s[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
    return s


def normals(pts):
    n = len(pts)
    out = []
    for i in range(n):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, n - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy) or 1.0
        out.append((-dy / d, dx / d))
    return out


def offset_path(pts, d):
    N = normals(pts)
    return [(p[0] + n[0] * d, p[1] + n[1] * d) for p, n in zip(pts, N)]


def smooth(t):
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return t * t * (3 - 2 * t)


def catmull(pts, closed=False, step=1.4):
    pts = list(pts)
    n = len(pts)
    if n < 2:
        return pts
    if closed:
        P = [pts[-1]] + pts + [pts[0], pts[1]]
    else:
        P = ([(2 * pts[0][0] - pts[1][0], 2 * pts[0][1] - pts[1][1])] + pts +
             [(2 * pts[-1][0] - pts[-2][0], 2 * pts[-1][1] - pts[-2][1])])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        d = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        k = max(1, int(d / step))
        for j in range(k):
            t = j / k
            t2 = t * t
            t3 = t2 * t
            out.append((
                0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
                0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)))
    out.append(out[0] if closed else pts[-1])
    return out


def jitter_path(pts, rng, amp, corr=0.82):
    """perpendicular random-walk wobble: a hand that never quite holds the line"""
    out, off = [], rng.gauss(0, amp)
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        off = off * corr + rng.gauss(0, amp * math.sqrt(1 - corr * corr))
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1.0
        out.append((x - dy / L * off, y + dx / L * off))
    return out


def arclen_split(pts, rng, dash, gap):
    """break a polyline into hand-drawn dashes; dash/gap are (lo, hi) in units"""
    pts = densify(pts, 2.0)
    out, cur, acc = [], [pts[0]], 0.0
    on = True
    target = rng.uniform(*dash)
    for a, b in zip(pts, pts[1:]):
        acc += math.hypot(b[0] - a[0], b[1] - a[1])
        if on:
            cur.append(b)
        if acc >= target:
            if on and len(cur) > 1:
                out.append(cur)
            on = not on
            cur = [b]
            acc = 0.0
            target = rng.uniform(*(dash if on else gap))
    if on and len(cur) > 1:
        out.append(cur)
    return out


def poly_area(pts):
    return 0.5 * abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])))


def centroid(pts):
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def px(pts):
    return [(x * R, y * R) for x, y in pts]


# --------------------------------------------------------------------------
# raster helpers
# --------------------------------------------------------------------------
def blank(v=0):
    return Image.new('L', (W, H), v)


def thr(img, t):
    return img.point(lambda p: 255 if p >= t else 0)


def AND(a, b):
    return ImageChops.multiply(a, b)


def OR(a, b):
    return ImageChops.lighter(a, b)


def SUB(a, b):
    return ImageChops.subtract(a, b)


def NOT(a):
    return a.point(lambda p: 255 - p)


def noise(cell_u, rng, sigma=64):
    """smooth noise with feature size ~cell_u units (full-res L image)"""
    nw = max(2, int(W / (cell_u * R)))
    nh = max(2, int(H / (cell_u * R)))
    random.seed(rng.random())
    n = Image.effect_noise((nw, nh), sigma).convert('L')
    return n.resize((W, H), Image.BICUBIC)


def dilate(img, n):
    for _ in range(n):
        img = img.filter(ImageFilter.MaxFilter(3))
    return img


def erode(img, n):
    for _ in range(n):
        img = img.filter(ImageFilter.MinFilter(3))
    return img


def opening(img, size):
    return img.filter(ImageFilter.MinFilter(size)).filter(ImageFilter.MaxFilter(size))


def rough(mask, rng, blur_u=0.38, amt=0.2, cell=1.6):
    """ink spread: soften the edge, push it around with paper-tooth noise, re-threshold"""
    b = mask.filter(ImageFilter.GaussianBlur(blur_u * R))
    n = noise(cell, rng, sigma=70)
    return thr(Image.blend(b, n, amt), 128)


def grain(mask, rng, density=0.18, cell=1.2, starve_cell=70, starve=0.4):
    """riso grain: holes in solids, more of them where the drum ran dry"""
    fine = noise(cell, rng, sigma=55)
    low = noise(starve_cell, rng, sigma=60)
    mix = Image.blend(fine, low, starve)
    t = int(128 - 75 * (0.5 - density) * 2)
    holes = mix.point(lambda p: 255 if p < t * 0.66 else 0)
    return SUB(mask, holes)


def poly_mask(polys, img=None):
    m = img or blank()
    d = ImageDraw.Draw(m)
    for p in polys:
        if len(p) > 2:
            d.polygon(px(p), fill=255)
    return m


def dot(d, x, y, r, rng=None, squash=1.0, fill=255):
    """a dot pressed by hand: never quite round"""
    r = max(r, 1.3)
    if rng is None:
        X, Y, rr = x * R, y * R, r * R
        d.ellipse([X - rr, Y - rr * squash, X + rr, Y + rr * squash], fill=fill)
        return
    k = 8
    ph = rng.uniform(0, TAU)
    pts = []
    for i in range(k):
        a = ph + TAU * i / k
        rr = r * rng.uniform(0.84, 1.12)
        pts.append(((x + math.cos(a) * rr) * R, (y + math.sin(a) * rr * squash) * R))
    d.polygon(pts, fill=fill)


# --------------------------------------------------------------------------
# THE PEN: pressure-varying brush along a jittered Catmull-Rom path
# --------------------------------------------------------------------------
MINW = 2.6   # units: 7.8 px at print res, above the 6 px minimum


def hand(ctrl, rng, wob=0.6, trem=0.5, closed=False, step=1.4):
    c = [(x + rng.gauss(0, wob), y + rng.gauss(0, wob)) for x, y in ctrl]
    d = catmull(c, closed, step)
    if trem > 0 and len(d) > 4:
        s = cumlen(d)
        L = s[-1]
        amp = trem * min(1.0, L / 50.0)
        comps = [(amp * rng.uniform(0.35, 1.0), TAU / rng.uniform(18, 95), rng.uniform(0, TAU)) for _ in range(3)]
        N = normals(d)
        out = []
        for (x, y), (nx, ny), si in zip(d, N, s):
            off = sum(a * math.sin(f * si + p) for a, f, p in comps)
            out.append((x + nx * off, y + ny * off))
        if closed:
            out[-1] = out[0]
        d = out
    return d


def _render(d, pts, w, rng, a0, a1, pv, fill=255):
    n = len(pts)
    if n < 2:
        return
    s = cumlen(pts)
    L = s[-1] or 1e-6
    r0 = min(L * 0.35, a0 * w)
    r1 = min(L * 0.45, a1 * w)
    f1, f2 = rng.uniform(0.7, 2.0), rng.uniform(2.5, 5.5)
    if L > 200:                       # long strokes breathe more often
        f1 *= L / 200
        f2 *= L / 200
    p1, p2 = rng.uniform(0, TAU), rng.uniform(0, TAU)
    base = w * rng.uniform(0.92, 1.08)
    ws = []
    for si in s:
        t = si / L
        p = 1 + pv * (0.65 * math.sin(TAU * f1 * t + p1) + 0.35 * math.sin(TAU * f2 * t + p2))
        if r0 > 0:
            p *= 0.6 + 0.4 * smooth(si / r0)
        if r1 > 0:
            p *= 0.4 + 0.6 * smooth((L - si) / r1)
        ws.append(max(MINW, base * p) * R * 0.5)
    P = [(x * R, y * R) for x, y in pts]
    N = normals(P)
    Lp = [(P[i][0] + N[i][0] * ws[i], P[i][1] + N[i][1] * ws[i]) for i in range(n)]
    Rp = [(P[i][0] - N[i][0] * ws[i], P[i][1] - N[i][1] * ws[i]) for i in range(n)]
    CH = 9
    for a in range(0, n - 1, CH):
        b = min(n - 1, a + CH)
        d.polygon(Lp[a:b + 1] + Rp[a:b + 1][::-1], fill=fill)
        if a > 0:
            r = ws[a]
            d.ellipse((P[a][0] - r, P[a][1] - r, P[a][0] + r, P[a][1] + r), fill=fill)
    for i in (0, n - 1):
        r = ws[i]
        d.ellipse((P[i][0] - r, P[i][1] - r, P[i][0] + r, P[i][1] + r), fill=fill)


def ink(d, path, w, rng, a0=1.6, a1=3.5, pv=0.2, redraw=0.0, closed=False, close_frac=None, fill=255):
    pts = list(path)
    if closed and len(pts) > 6:
        pts = pts[:-1]
        n = len(pts)
        k = rng.randrange(n)
        pts = pts[k:] + pts[:k]
        f = close_frac if close_frac is not None else rng.uniform(0.93, 1.07)
        if f < 1:
            pts = pts[:max(2, int(n * f))]
        else:
            pts = pts + pts[:int(n * (f - 1)) + 1]
    _render(d, pts, w, rng, a0, a1, pv, fill)
    if redraw and rng.random() < redraw and len(pts) > 12:
        n = len(pts)
        a = rng.randrange(0, n // 2)
        b = min(n, a + rng.randint(max(3, n // 5), max(4, n // 2)))
        seg = offset_path(pts[a:b], rng.choice((-1, 1)) * rng.uniform(0.5, 0.9) * w)
        _render(d, seg, w * 0.78, rng, 1.0, 2.0, pv, fill)


def pen(d, ctrl, w, rng, wob=0.5, trem=0.4, closed=False, **kw):
    """short hand line through a few control points"""
    p = hand(ctrl, rng, wob=wob, trem=trem, closed=closed)
    ink(d, p, w, rng, closed=closed, **kw)
    return p


def pen_path(d, pts, w, rng, amp=0.5, trem=0.35, step=6.0, **kw):
    """long line along real geometry: densify, random-walk wobble, spline, tremor, pressure"""
    if len(pts) < 2:
        return []
    c = jitter_path(densify(pts, step), rng, amp)
    p = hand(c, rng, wob=0.0, trem=trem)
    ink(d, p, w, rng, **kw)
    return p


def box(d, corners, w, rng, over=(-1.2, 3.5), bow=0.012, wob=0.3, **kw):
    """polygon drawn edge by edge: corners overshoot or fall short"""
    n = len(corners)
    for i in range(n):
        a = corners[i]
        b = corners[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 0.5:
            continue
        ux, uy = dx / L, dy / L
        e0, e1 = rng.uniform(*over), rng.uniform(*over)
        a2 = (a[0] - ux * e0, a[1] - uy * e0)
        b2 = (b[0] + ux * e1, b[1] + uy * e1)
        bw = rng.gauss(0, L * bow)
        m = ((a2[0] + b2[0]) / 2 - uy * bw, (a2[1] + b2[1]) / 2 + ux * bw)
        p = hand([a2, m, b2], rng, wob=wob, trem=0.25 * min(1, L / 40))
        ink(d, p, w, rng, a0=0.8, a1=1.5, pv=0.12, **kw)


def simplify(pts, tol):
    """Douglas-Peucker: the hand draws a building's corners, not its survey points"""
    if len(pts) < 3:
        return pts
    if math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-6:     # closed ring: split at the far corner
        far = max(range(len(pts)), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)
        if far == 0:
            return pts
        return simplify(pts[:far + 1], tol)[:-1] + simplify(pts[far:], tol)
    a, b = pts[0], pts[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1e-9
    dmax, idx = 0.0, 0
    for i in range(1, len(pts) - 1):
        d = abs((pts[i][0] - a[0]) * dy - (pts[i][1] - a[1]) * dx) / L
        if d > dmax:
            dmax, idx = d, i
    if dmax > tol:
        return simplify(pts[:idx + 1], tol)[:-1] + simplify(pts[idx:], tol)
    return [a, b]


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
log('loading osm-site.json')
osm = json.load(open(os.path.join(HERE, 'osm-site.json')))
EL = osm['elements']
BY = {(e['type'], e['id']): e for e in EL}


def P(geom):
    return [proj(p['lat'], p['lon']) for p in geom if p]


def outers(e):
    if 'geometry' in e:
        return [e['geometry']]
    return [m['geometry'] for m in e.get('members', []) if m.get('geometry') and m.get('role') in ('outer', '')]


def inners(e):
    return [m['geometry'] for m in e.get('members', []) if m.get('geometry') and m.get('role') == 'inner']


BIEC_ID, LAKE_REL = 41181489, 5660111
HALLS = {203117246, 203117247, 203117250, 785271991, 785271992, 203117248, 346457408, 445642244, 203117249}
STATION_ID, STATION2_ID = 1240092409, 1240092410
METRO_IDS = (359201105, 1240092403)
ROAD_W = {'trunk': 14, 'primary': 12, 'secondary': 10, 'tertiary': 8.5, 'tertiary_link': 6,
          'residential': 5.2, 'unclassified': 5.4, 'living_street': 4.4, 'service': 3.6,
          'track': 3.4, 'construction': 5}

buildings, roads, motor, links, ponds, orchards, scrub, woods, farmland = [], [], [], [], [], [], [], [], []
halls, station = [], None
for e in EL:
    t = e.get('tags', {})
    gs = outers(e)
    if not gs:
        continue
    if e['id'] in (BIEC_ID, LAKE_REL) or e['id'] in METRO_IDS:
        continue
    if 'building' in t:
        for g in gs:
            pts = P(g)
            if len(pts) < 3:
                continue
            if e['id'] in HALLS:
                halls.append((e['id'], pts))
            elif e['id'] == STATION_ID:
                station = pts
            elif e['id'] == STATION2_ID:
                continue
            else:
                buildings.append(pts)
    elif t.get('highway') == 'motorway':
        for g in gs:
            motor.append((t.get('name', ''), t.get('bridge') is not None, P(g)))
    elif t.get('highway') == 'motorway_link':
        for g in gs:
            links.append((t.get('bridge') is not None, P(g)))
    elif t.get('highway') in ROAD_W:
        for g in gs:
            roads.append((ROAD_W[t['highway']], t['highway'], P(g)))
    elif t.get('natural') == 'water':
        for g in gs:
            ponds.append(P(g))
    elif t.get('landuse') == 'orchard':
        for g in gs:
            orchards.append(P(g))
    elif t.get('natural') == 'scrub':
        for g in gs:
            scrub.append(P(g))
    elif t.get('landuse') in ('forest', 'recreation_ground') or t.get('natural') == 'wood' or \
            t.get('leisure') in ('park', 'garden'):
        for g in gs:
            woods.append(P(g))
    elif t.get('landuse') == 'farmland':
        for g in gs:
            farmland.append(P(g))

biec = P(BY[('way', BIEC_ID)]['geometry'])
lake_rel = BY[('relation', LAKE_REL)]
lake = P(outers(lake_rel)[0])
islands = [P(g) for g in inners(lake_rel)]
metro = [P(BY[('way', i)]['geometry']) for i in METRO_IDS]
log(f'{len(buildings)} buildings, {len(roads)} roads, {len(motor)} motorway, {len(links)} links, '
    f'{len(orchards)} orchards, {len(halls)} hall blocks')

# metro centreline: mean of the two track ways, ordered city -> Madavara (east -> west)
ma, mb = metro
mb_d = densify(mb, 3.0)


def nearest(p, pts):
    return min(pts, key=lambda q: (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2)


METRO_C = [((x + nearest((x, y), mb_d)[0]) / 2, (y + nearest((x, y), mb_d)[1]) / 2) for x, y in densify(ma, 6.0)]
END = METRO_C[-1]                     # the real end of the viaduct, past Madavara: the buffer stop
STATION_C = proj(13.05742, 77.47281)

# --------------------------------------------------------------------------
# the show: stage at the north-east of the open ground, the crowd facing it,
# pouring back toward the gate and the station
# --------------------------------------------------------------------------
STAGE = proj(13.06005, 77.47640)
AIM = proj(13.05830, 77.47450)
fx, fy = AIM[0] - STAGE[0], AIM[1] - STAGE[1]
_L = math.hypot(fx, fy)
fx, fy = fx / _L, fy / _L
nx_, ny_ = -fy, fx
sx, sy = STAGE
FOH = (sx + fx * 150, sy + fy * 150)
GATE = proj(13.05775, 77.47330)       # where the footbridge from the platform comes down at the compound
log('stage', [round(c) for c in STAGE], 'station', [round(c) for c in STATION_C], 'end', [round(c) for c in END])

# --------------------------------------------------------------------------
# density: where the hand kept drawing. The map thins out object by object
# toward a ragged edge, and goes quiet where the type will sit.
# --------------------------------------------------------------------------
rng = random.Random(SEED)
DLR = 0.25
DW, DH = int(UW * DLR), int(UH * DLR)


def dpx(pts):
    return [(x * DLR, y * DLR) for x, y in pts]


TYPE_ZONES = {   # units: x, y, w, h  (also used for the manifest)
    'city': (56, 1268, 420, 146),
    'dates': (782, 70, 360, 62),
}
base = Image.new('L', (DW, DH), 0)
bd = ImageDraw.Draw(base)
bc = (660, 760)
harm = [(rng.uniform(0.04, 0.08), k, rng.uniform(0, TAU)) for k in (2, 3, 4, 5, 7, 11, 13)]
blob = []
for i in range(720):
    th = i / 720 * TAU
    rx, ry, ne = 540, 700, 2.4
    c_, s_ = math.cos(th), math.sin(th)
    b_ = (abs(c_) ** ne + abs(s_) ** ne) ** (-1 / ne)
    rr = b_ * (1 + sum(a / (1 + 0.2 * k) * math.sin(k * th + ph) for a, k, ph in harm))
    blob.append(((bc[0] + rx * rr * c_) * DLR, (bc[1] + ry * rr * s_) * DLR))
bd.polygon(blob, fill=225)
# the land's own spine is drawn hardest: the road corridor, the show ground, the lake
for nm, br, pts in motor:
    bd.line(dpx(pts), fill=255, width=int(150 * DLR))
bd.polygon(dpx(biec), fill=255)
bd.ellipse([(sx - 330) * DLR, (sy - 330) * DLR, (sx + 330) * DLR, (sy + 330) * DLR], fill=255)
dens = base.filter(ImageFilter.GaussianBlur(55 * DLR))
# the south-west runs out: the NICE Road dissolves before it reaches the city name
sw = Image.new('L', (DW, DH), 0)
ImageDraw.Draw(sw).polygon(dpx([(-200, 1180), (380, 1180), (560, 1420), (560, 1800), (-200, 1800)]), fill=255)
sw = sw.filter(ImageFilter.GaussianBlur(70 * DLR))
dens = SUB(dens, sw.point(lambda p: int(p * 0.85)))
calm = Image.new('L', (DW, DH), 0)
cd = ImageDraw.Draw(calm)
for name, (x, y, w, h) in TYPE_ZONES.items():
    v = {'city': 250, 'dates': 250}[name]
    cd.rounded_rectangle([(x - 22) * DLR, (y - 22) * DLR, (x + w + 22) * DLR, (y + h + 22) * DLR],
                         radius=int(40 * DLR), fill=v)
calm = calm.filter(ImageFilter.GaussianBlur(26 * DLR))
border = Image.new('L', (DW, DH), 0)
ImageDraw.Draw(border).rectangle([46 * DLR, 46 * DLR, (UW - 46) * DLR, (UH - 46) * DLR], fill=255)
border = border.filter(ImageFilter.GaussianBlur(20 * DLR))
dn = Image.effect_noise((DW // 10 + 2, DH // 10 + 2), 50).convert('L').resize((DW, DH), Image.BICUBIC)
dens = ImageChops.subtract(ImageChops.add(dens, dn.point(lambda p: p // 5)), Image.new('L', (DW, DH), 22))
DENS_L = AND(SUB(dens, calm), border)
DENS_RING_L = AND(SUB(dens.point(lambda p: min(255, int(p * 1.6))), calm.point(lambda p: int(p * 0.8))), border)


def dval(u, v, field=None):
    f = field or DENS_L
    x = min(max(int(u * DLR), 0), DW - 1)
    y = min(max(int(v * DLR), 0), DH - 1)
    return f.getpixel((x, y)) / 255.0


def keep(u, v, rng, field=None, gamma=1.0, floor=0.0):
    p = dval(u, v, field) ** gamma
    return rng.random() < max(p, floor)


def thin_path(pts, rng, piece=(14, 40), field=None, gamma=1.0):
    """cut a long line into pieces, keep each piece by density at its middle"""
    out = []
    for seg in arclen_split(pts, rng, piece, (0.01, 0.02)):
        m = seg[len(seg) // 2]
        if keep(m[0], m[1], rng, field, gamma):
            if out and math.hypot(out[-1][-1][0] - seg[0][0], out[-1][-1][1] - seg[0][1]) < 0.3:
                out[-1].extend(seg[1:])
            else:
                out.append(seg)
    return out


DENS = DENS_L.resize((W, H), Image.BICUBIC)
for c in [(0, 0), (UW, 0), (0, UH), (UW, UH)]:
    log('corner', c, [round(v, 4) for v in unproj(*c)])
log('density field done')

# --------------------------------------------------------------------------
# masks of places
# --------------------------------------------------------------------------
BIEC = poly_mask([biec])
LAKE = SUB(poly_mask([lake]), poly_mask(islands))
ISLANDS = poly_mask(islands)
PONDS = poly_mask(ponds)
BLD = poly_mask(buildings + [h for _, h in halls] + ([station] if station else []))
GREENS = poly_mask(orchards + scrub + woods + farmland)


def road_mask(items, extra=0.0):
    m = blank()
    rd = ImageDraw.Draw(m)
    for w_, pts in items:
        if len(pts) > 1:
            ww = (w_ + extra) * R
            rd.line(px(pts), fill=255, width=int(ww), joint='curve')
            for x, y in (px(pts[:1]) + px(pts[-1:])):
                rd.ellipse([x - ww / 2, y - ww / 2, x + ww / 2, y + ww / 2], fill=255)
    return m


MOTOR_W, LINK_W = 13.0, 8.0
inner_biec = BIEC.resize((UW, UH), Image.NEAREST)
minor = [(w_, pts) for w_, k, pts in roads
         if not (k in ('service', 'track') and inner_biec.getpixel((int(min(max(centroid(pts)[0], 0), UW - 1)),
                                                                     int(min(max(centroid(pts)[1], 0), UH - 1)))))]
ROADS = road_mask(minor + [(MOTOR_W, p) for _, _, p in motor] + [(LINK_W, p) for _, p in links])
BIG_ROADS = road_mask([(MOTOR_W, p) for _, _, p in motor] + [(LINK_W, p) for _, p in links], extra=6)
METRO_M = road_mask([(13, METRO_C)])
log('place masks done')


# ==========================================================================
# KEY INK -- the drawing hand
# ==========================================================================
def hatch_field(angle, spacing, width, rng, wav=0.5):
    img = blank()
    d = ImageDraw.Draw(img)
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    diag = math.hypot(UW, UH) / 2 + 20
    t = -diag
    while t < diag:
        pts, s, off, ph = [], -diag, 0.0, rng.uniform(0, TAU)
        lam = rng.uniform(30, 60)
        while s <= diag:
            off = off * 0.9 + rng.gauss(0, wav * 0.35)
            n = t + off + wav * math.sin(s / lam + ph)
            pts.append((UW / 2 + ca * s - sa * n, UH / 2 + sa * s + ca * n))
            s += 6
        d.line(px(pts), fill=255, width=max(1, int(round(width * rng.uniform(0.95, 1.12) * R))), joint='curve')
        t += spacing * rng.uniform(0.8, 1.2)
    return img


rng = random.Random(SEED + 10)
HA = hatch_field(-60, 5.6, 2.7, rng)       # the two hatch directions sit on the map's own grain
HB = hatch_field(30, 5.4, 2.7, rng)
HD = hatch_field(-15, 5.0, 2.8, rng, wav=0.3)     # the halls: tighter, a third direction
log('hatch fields done')

KEY = blank()
kd = ImageDraw.Draw(KEY)

# ordinary buildings: each one drawn or skipped by density; small = solid
# pressed block, mid = hatched with a pen outline, the odd one left open
bA, bB, bS = [], [], []
outl = []
for b in buildings:
    c = centroid(b)
    if not keep(c[0], c[1], rng, gamma=0.9):
        continue
    a = poly_area(b)
    if a < 130:
        bS.append(b)
    else:
        (bA if rng.random() < 0.5 else bB).append(b)
        outl.append(b)
KEY_BLD = OR(AND(poly_mask(bA), HA), AND(poly_mask(bB), HB))
sd_ = ImageDraw.Draw(KEY_BLD)
for b in bS:        # small houses: pressed blocks, slightly off their footprint
    o = (rng.gauss(0, 0.5), rng.gauss(0, 0.5))
    sb = simplify(b, 0.8)
    sd_.polygon(px([(x + o[0], y + o[1]) for x, y in sb]), fill=255)
for b in outl:
    sb = simplify(b, 0.9)
    if len(sb) > 2 and sb[0] == sb[-1]:
        sb = sb[:-1]
    if len(sb) < 3:
        continue
    if len(sb) <= 6:
        box(sd_, sb, 2.7, rng, over=(-0.8, 2.2), wob=0.25)
    else:
        pen(sd_, sb, 2.7, rng, wob=0.2, trem=0.25, closed=True)
log('buildings done', len(bS) + len(outl))

# the exhibition halls: bold hatched slabs, each one with a cast shadow and a
# doubled, overshooting outline
HALLK = blank()
hk = ImageDraw.Draw(HALLK)
hall_fill, hall_sh = [], []
SHD = (4.2, 5.4)          # shadow falls south-east on the page
for hid, h in halls:
    sh = simplify(h, 1.2)
    if sh[0] == sh[-1]:
        sh = sh[:-1]
    hall_fill.append(sh)
    hall_sh.append([(x + SHD[0], y + SHD[1]) for x, y in sh])
HALL_M = poly_mask(hall_fill)
SHADOW = SUB(poly_mask(hall_sh), HALL_M)
HALLK = OR(AND(HALL_M, HD), SHADOW)
hk = ImageDraw.Draw(HALLK)
for sh in hall_fill:
    box(hk, sh, 3.6, rng, over=(-0.5, 5.0), wob=0.35)
    if rng.random() < 0.8:
        box(hk, [(x + rng.uniform(-1.5, 1.5), y + rng.uniform(-1.5, 1.5)) for x, y in sh], 2.7, rng,
            over=(-3.0, 2.0), wob=0.5)
# the hall roofs: ribs across the big sheds
for sh in hall_fill:
    if poly_area(sh) < 3000:
        continue
    # long axis of the slab
    best = max(range(len(sh)), key=lambda i: math.hypot(sh[(i + 1) % len(sh)][0] - sh[i][0], sh[(i + 1) % len(sh)][1] - sh[i][1]))
    a, b = sh[best], sh[(best + 1) % len(sh)]
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    m = Image.new('L', (W, H), 0)
    md = ImageDraw.Draw(m)
    k = 0.0
    while k < L:
        p0 = (a[0] + ux * k - uy * 400, a[1] + uy * k + ux * 400)
        p1 = (a[0] + ux * k + uy * 400, a[1] + uy * k - ux * 400)
        md.line(px([p0, p1]), fill=255, width=int(2.8 * R))
        k += rng.uniform(15, 22)
    HALLK = OR(HALLK, AND(m, erode(poly_mask([sh]), int(2.5 * R))))
log('halls done')

# ground: a hand-set halftone screen (rotated grid, jittered, dot size breathing
# with a slow ink-load field) -- the roads will be cut through it
KEY_GROUND = blank()
gd = ImageDraw.Draw(KEY_GROUND)
load = Image.effect_noise((UW // 45 + 2, UH // 45 + 2), 60).convert('L').resize((UW, UH), Image.BICUBIC)
# the tone of the ground follows the settlement: heavy dots where the villages
# crowd in, the screen opening up and dropping out over empty land
built = poly_mask(buildings).resize((UW // 4, UH // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(7))
bmax = max(1, max(built.getdata()))
built = built.point(lambda p: min(255, int(p * 255 / bmax * 2.2))).resize((UW, UH), Image.BICUBIC)
g = 8.2
ga = math.radians(15)
cga, sga = math.cos(ga), math.sin(ga)
span = int(math.hypot(UW, UH) / g) + 2
for i in range(-span, span):
    for j in range(-span, span):
        u0, v0 = i * g, j * g
        x = UW / 2 + u0 * cga - v0 * sga + rng.gauss(0, 0.6)
        y = UH / 2 + u0 * sga + v0 * cga + rng.gauss(0, 0.6)
        if not (0 <= x < UW and 0 <= y < UH):
            continue
        bt = built.getpixel((int(x), int(y))) / 255.0
        if not keep(x, y, rng, gamma=1.6) or rng.random() > 0.5 + 0.5 * bt:
            continue
        r = 1.22 + 0.95 * bt + 0.3 * (load.getpixel((int(x), int(y))) / 255.0) + rng.uniform(-0.08, 0.1)
        dot(gd, x, y, r, squash=rng.uniform(0.86, 1.06))
GROUND_REGION = SUB(SUB(SUB(SUB(blank(255), GREENS), BIEC), LAKE), PONDS)
KEY_GROUND = AND(KEY_GROUND, GROUND_REGION)

# the show ground itself: bare, dusty earth, stippled loose by hand
KEY_DUST = blank()
kdd = ImageDraw.Draw(KEY_DUST)
bx_ = [p[0] for p in biec]
by_ = [p[1] for p in biec]
dust_load = noise(30, rng, 70).resize((UW, UH), Image.BILINEAR)
for _ in range(11000):
    x, y = rng.uniform(min(bx_), max(bx_)), rng.uniform(min(by_), max(by_))
    if not (0 <= x < UW and 0 <= y < UH) or not keep(x, y, rng, gamma=0.8):
        continue
    if rng.random() > dust_load.getpixel((int(x), int(y))) / 255.0 * 1.3:
        continue
    dot(kdd, x, y, rng.uniform(1.3, 1.65), rng)
KEY_DUST = SUB(AND(KEY_DUST, BIEC), dilate(BLD, int(2 * R)))
KEY_GROUND = OR(KEY_GROUND, KEY_DUST)
CITY = OR(KEY_BLD, KEY_GROUND)
CITY = SUB(CITY, ROADS)
CITY = SUB(CITY, dilate(METRO_M, 0))
log('city texture done')

# ---------------------------------------------------------------- the big roads
# Tumakuru Road and the NICE Road: each carriageway's edges pulled as long,
# confident pen lines; the ramps of the interchange loop through them.
KR = blank()
krd = ImageDraw.Draw(KR)


def road_edges(pts, half, w, rng, field_gamma=0.6, amp=0.45, piece=(60, 180)):
    for side in (-1, 1):
        e = offset_path(densify(pts, 4.0), side * half)
        for seg in thin_path(e, rng, piece, gamma=field_gamma):
            if len(seg) > 3:
                pen_path(krd, seg, w, rng, amp=amp, trem=0.3, pv=0.28, redraw=0.35)


def chains(items):
    """join OSM ways that meet end to start into long runs: one pull of the pen each"""
    runs = [list(p) for p in items if len(p) > 1]
    merged = True
    while merged:
        merged = False
        for i in range(len(runs)):
            for j in range(len(runs)):
                if i == j:
                    continue
                a, b = runs[i], runs[j]
                if math.hypot(a[-1][0] - b[0][0], a[-1][1] - b[0][1]) < 0.6:
                    runs[i] = a + b[1:]
                    del runs[j]
                    merged = True
                    break
            if merged:
                break
    return runs


main_runs = chains([p for nm, br, p in motor if 'Nelamangala' in nm])
nice_runs = chains([p for nm, br, p in motor if 'Nelamangala' not in nm])
link_runs = chains([p for br, p in links])
log('road runs', len(main_runs), len(nice_runs), len(link_runs))
for pts in main_runs:
    road_edges(pts, MOTOR_W / 2, 4.0, rng)
for pts in nice_runs:
    road_edges(pts, MOTOR_W / 2, 3.6, rng)
for pts in link_runs:
    road_edges(pts, LINK_W / 2, 3.0, rng, piece=(40, 140))
# the flyovers: whatever passes under a deck is broken off at its parapets,
# and the deck is drawn again on top, with a shadow ticked along one side
bridges = [(MOTOR_W, p) for nm, br, p in motor if br] + [(LINK_W, p) for br, p in links if br]
KR = SUB(KR, road_mask(bridges, extra=7.0))
krd = ImageDraw.Draw(KR)
for w_, pts in bridges:
    dp = densify(pts, 2.0)
    if len(dp) < 2:
        continue
    ux, uy = dp[1][0] - dp[0][0], dp[1][1] - dp[0][1]
    L = math.hypot(ux, uy) or 1
    vx, vy = dp[-1][0] - dp[-2][0], dp[-1][1] - dp[-2][1]
    Lv = math.hypot(vx, vy) or 1
    ext = [(dp[0][0] - ux / L * 4, dp[0][1] - uy / L * 4)] + dp + [(dp[-1][0] + vx / Lv * 4, dp[-1][1] + vy / Lv * 4)]
    for side in (-1, 1):
        e = offset_path(ext, side * w_ / 2)
        pen_path(krd, e, 3.6 if w_ == MOTOR_W else 3.0, rng, amp=0.3, trem=0.2, step=4, a0=0.6, a1=0.8)
    N = normals(ext)
    for k in range(1, len(ext) - 1, 3):
        x, y = ext[k]
        nx, ny = N[k]
        side = 1 if (nx * SHD[0] + ny * SHD[1]) > 0 else -1
        x0, y0 = x + nx * side * (w_ / 2 + 2.2), y + ny * side * (w_ / 2 + 2.2)
        x1, y1 = x + nx * side * (w_ / 2 + 6.0) + 1.0, y + ny * side * (w_ / 2 + 6.0) + 1.2
        pen(krd, [(x0, y0), (x1, y1)], 2.6, rng, wob=0.2, trem=0, a0=0.5, a1=0.8)
# minor roads that matter: the tertiary roads get one edge in pieces
for w_, k, pts in roads:
    if k != 'tertiary':
        continue
    e = offset_path(densify(pts, 4.0), w_ / 2 + 0.5)
    for seg in thin_path(e, rng, (20, 70), gamma=1.3):
        if len(seg) > 3 and rng.random() < 0.6:
            pen_path(krd, seg, 2.6, rng, amp=0.5, trem=0.3)
log('roads done')

# ---------------------------------------------------------------- the lake shore
KL = blank()
kld = ImageDraw.Draw(KL)
for ring in [lake] + islands:
    for seg in thin_path(ring + ring[:1], rng, (40, 120), gamma=0.6):
        if len(seg) > 3:
            pen_path(kld, seg, 3.2, rng, amp=0.6, trem=0.4, pv=0.25)
    for seg in arclen_split(ring + ring[:1], rng, (50, 200), (20, 80)):
        m = seg[len(seg) // 2]
        if keep(m[0], m[1], rng) and len(seg) > 3:
            pen_path(kld, [(x + 2.8, y + 2.4) for x, y in seg], 2.6, rng, amp=1.0, trem=0.5)
for pd in ponds:
    for seg in thin_path(pd + pd[:1], rng, (30, 90)):
        if len(seg) > 3:
            pen_path(kld, seg, 2.8, rng, amp=0.4)

# the BIEC compound wall: a quick dashed line, a hand in a hurry
for seg in arclen_split(biec + biec[:1], rng, (12, 30), (5, 11)):
    m = seg[len(seg) // 2]
    if keep(m[0], m[1], rng, gamma=0.5):
        pen(kld, [seg[0], seg[len(seg) // 2], seg[-1]], 2.7, rng, wob=0.3, trem=0.2)
log('shore + wall done')

# ==========================================================================
# THE CROWD -- heads, raised hands, phone lights, from above; and the stream
# of people still coming off the last train at Madavara
# ==========================================================================
rng = random.Random(SEED + 20)
KC = blank()
ACC = blank()
CZ = blank()
cdw = ImageDraw.Draw(KC)
adw = ImageDraw.Draw(ACC)
czd = ImageDraw.Draw(CZ)
avoid = dilate(OR(HALL_M, poly_mask([b for b in buildings if poly_area(b) > 60])), int(3 * R)).resize((UW, UH), Image.NEAREST)
inside_b = erode(BIEC, int(5 * R)).resize((UW, UH), Image.NEAREST)
toward = math.atan2(-fy, -fx)      # arms reach toward the stage
placed = 0
G = 5.9
row = 0
gy_ = 0.0
lean = noise(40, rng, 60).resize((UW, UH), Image.BILINEAR)   # pockets and clumps in the crowd
while gy_ < UH:
    gx_ = (row % 2) * G / 2
    row += 1
    while gx_ < UW:
        x, y = gx_ + rng.uniform(-1.9, 1.9), gy_ + rng.uniform(-1.9, 1.9)
        gx_ += G * rng.uniform(0.86, 1.14)
        if not (0 <= x < UW - 1 and 0 <= y < UH - 1):
            continue
        if not inside_b.getpixel((int(x), int(y))) or avoid.getpixel((int(x), int(y))):
            continue
        rx_, ry_ = x - sx, y - sy
        dist = rx_ * fx + ry_ * fy
        lat = abs(rx_ * nx_ + ry_ * ny_)
        if dist < 18 or math.hypot(x - FOH[0], y - FOH[1]) < 13:
            continue
        clump = lean.getpixel((int(x), int(y))) / 255.0
        p = (0.82 + 0.18 * clump) * math.exp(-max(0, dist - 120 - 60 * clump) / 120.0) * \
            math.exp(-max(0, lat - 64 - dist * 0.85) / 46.0)
        p = 0.025 + 0.975 * p
        if rng.random() > p:
            continue
        placed += 1
        if p > 0.3:
            dot(czd, x, y, 5.0)
        kind = rng.random()
        hr = rng.uniform(1.45, 1.8)
        if kind < 0.5:                           # a head
            dot(cdw, x, y, hr, rng, squash=rng.uniform(0.85, 1.05))
        elif kind < 0.72:                        # head + one arm up toward the stage
            dot(cdw, x, y, hr, rng)
            a = toward + rng.gauss(0, 0.55)
            side = rng.choice((-1.3, 1.3))
            bx, by = x + math.cos(a + side) * hr * 0.8, y + math.sin(a + side) * hr * 0.8
            L = rng.uniform(2.8, 4.2)
            ex, ey = bx + math.cos(a) * L, by + math.sin(a) * L
            pen(cdw, [(bx, by), (ex, ey)], 2.5, rng, wob=0.2, trem=0, a0=0.3, a1=0.3, pv=0.1)
            dot(cdw, ex, ey, 1.35)
        elif kind < 0.84:                        # both hands up
            dot(cdw, x, y, hr * 0.95, rng)
            a = toward + rng.gauss(0, 0.35)
            for s_ in (-0.55, 0.55):
                bx, by = x + math.cos(a + s_ * 2.4) * hr * 0.7, y + math.sin(a + s_ * 2.4) * hr * 0.7
                L = rng.uniform(2.8, 3.8)
                ex, ey = bx + math.cos(a + s_ * 0.45) * L, by + math.sin(a + s_ * 0.45) * L
                cdw.line([(bx * R, by * R), (ex * R, ey * R)], fill=255, width=int(2.5 * R))
                dot(cdw, ex, ey, 1.3)
        elif kind < 0.92:                        # on someone's shoulders: a bigger double head
            dot(cdw, x, y, hr * 1.25, rng)
            a = toward + rng.gauss(0, 0.4)
            dot(cdw, x + math.cos(a) * 2.6, y + math.sin(a) * 2.6, hr * 0.9, rng)
        else:                                    # phone held up: a lit slab + head
            dot(cdw, x, y, hr * 0.9, rng)
            a = toward + rng.gauss(0, 0.5)
            cx_, cy_ = x + math.cos(a) * 4.0, y + math.sin(a) * 4.0
            hw, hh = 1.45 * R, 2.2 * R
            ca_, sa_ = math.cos(a + math.pi / 2), math.sin(a + math.pi / 2)
            quad = [(cx_ * R + ca_ * dx - sa_ * dy, cy_ * R + sa_ * dx + ca_ * dy)
                    for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]
            (adw if rng.random() < 0.06 else cdw).polygon(quad, fill=255)
    gy_ += G * 0.87
CZ = thr(CZ.filter(ImageFilter.GaussianBlur(5 * R)), 120)
log(f'crowd: {placed} marks')

# the stream: people coming off the train, down from the platform, through the
# gate and across the ground, in twos and threes
stream = [STATION_C, GATE,
          (GATE[0] * 0.6 + FOH[0] * 0.4 + nx_ * 8, GATE[1] * 0.6 + FOH[1] * 0.4 + ny_ * 8),
          (FOH[0] - fx * 20, FOH[1] - fy * 20)]
sp = catmull(stream, step=1.0)
spn = normals(sp)
scum = cumlen(sp)
TRAIL = blank()
ImageDraw.Draw(TRAIL).line(px(sp[int(len(sp) * 0.12):]), fill=255, width=int(19 * R), joint='curve')
TRAIL = SUB(TRAIL, poly_mask([biec]).point(lambda p: 255 - p))
WALK = blank()
wkd = ImageDraw.Draw(WALK)
walkers = 0
i = int(len(sp) * 0.04)
while i < len(sp) * 0.93:
    x, y = sp[i]
    t = scum[i] / scum[-1]
    nx, ny = spn[i]
    for _ in range(rng.choice((1, 2, 2, 3))):
        o = rng.gauss(0, 2.6 + 1.6 * t)
        wx, wy = x + nx * o + rng.gauss(0, 0.8), y + ny * o + rng.gauss(0, 0.8)
        dot(wkd, wx, wy, rng.uniform(1.45, 1.75), rng)
        walkers += 1
    i += int(rng.uniform(4, 9))
KC = OR(SUB(KC, TRAIL), WALK)
cdw = ImageDraw.Draw(KC)
log(f'stream: {walkers} walkers')


def rect(cx_, cy_, along_, across, fwd=(fx, fy)):
    ux, uy = fwd
    vx, vy = -uy, ux
    return [(cx_ + ux * a_ + vx * b_, cy_ + uy * a_ + vy * b_) for a_, b_ in
            ((-along_, -across), (along_, -across), (along_, across), (-along_, across))]


# stage (accent), its outline drawn by the key pass a little off; screens; FOH
stage_poly = rect(sx - fx * 5, sy - fy * 5, 10, 34)
wing = rect(sx + fx * 9, sy + fy * 9, 6, 10)
adw.polygon(px(stage_poly), fill=255)
adw.polygon(px(wing), fill=255)
off = (2.0, -1.8)
box(cdw, [(x + off[0], y + off[1]) for x, y in stage_poly], 2.7, rng, over=(-0.5, 3.0))
TRUSS = blank()
tsd = ImageDraw.Draw(TRUSS)
for t_ in (-22, -7, 8, 23):      # the roof truss, scratched out of the deck
    pen(tsd, [(sx - fx * 15 + nx_ * t_, sy - fy * 15 + ny_ * t_),
              (sx + fx * 5 + nx_ * (t_ + 2), sy + fy * 5 + ny_ * (t_ + 2))], 2.6, rng, wob=0.3, trem=0)
ACC = SUB(ACC, TRUSS)
adw = ImageDraw.Draw(ACC)
for side in (-1, 1):
    wx, wy = sx + nx_ * side * 46 - fx * 2, sy + ny_ * side * 46 - fy * 2
    cdw.polygon(px(rect(wx, wy, 4.5, 4.5)), fill=255)
FOH_POLY = rect(FOH[0], FOH[1], 7, 7)
box(cdw, FOH_POLY, 2.7, rng, over=(-0.5, 2.5))
dot(adw, FOH[0], FOH[1], 2.4)
# barricade in front of the stage: a shallow bow
barr = []
for t in range(-50, 51, 4):
    bow = 0.0045 * t * t
    barr.append((sx + fx * (20 - bow) + nx_ * t, sy + fy * (20 - bow) + ny_ * t))
pen(cdw, barr, 2.7, rng, wob=0.3, trem=0.3)
# the snake from FOH to the barrier
for side in (-1, 1):
    seg = [(FOH[0] + nx_ * side * 4 - fx * 8, FOH[1] + ny_ * side * 4 - fy * 8),
           (sx + nx_ * side * 4 + fx * 22, sy + ny_ * side * 4 + fy * 22)]
    for piece in arclen_split(seg, rng, (7, 14), (4, 7)):
        pen(cdw, [piece[0], piece[-1]], 2.6, rng, wob=0.2, trem=0)
log('stage done')

# ==========================================================================
# GREEN INK -- the metro viaduct, orchards, scrub, the field, the trees
# ==========================================================================
rng = random.Random(SEED + 40)
GREEN = blank()
gnd = ImageDraw.Draw(GREEN)
KM = blank()               # key marks that belong to the metro (shadow of the deck)
kmd = ImageDraw.Draw(KM)

# Namma Metro Green Line, Reach 3C: a doubled deck on piers, coming in from the
# city and stopping dead past Madavara
deck = METRO_C
for side in (-1, 1):
    e = offset_path(deck, side * 4.8)
    for seg in thin_path(e, rng, (90, 260), gamma=0.3):
        if len(seg) > 3:
            pen_path(gnd, seg, 3.3, rng, amp=0.35, trem=0.25, pv=0.2, redraw=0.4)
dp = densify(deck, 2.0)
dn_ = normals(dp)
dc = cumlen(dp)
nxt = 0.0
for (x, y), (nx, ny), s in zip(dp, dn_, dc):
    if s < nxt:
        continue
    nxt = s + rng.uniform(15, 18.5)      # the deck spans, pier to pier
    if dc[-1] - s < 8 or not keep(x, y, rng, gamma=0.4):
        continue
    # pier cap: a tick right across the deck
    pen(gnd, [(x + nx * 8.6, y + ny * 8.6), (x - nx * 8.6, y - ny * 8.6)], 2.9, rng, wob=0.3, trem=0, a0=0.4, a1=0.6)
    # the pier's shadow on the ground, falling south-east (key)
    shx, shy = x + SHD[0] * 1.6, y + SHD[1] * 1.6
    dot(kmd, shx, shy, 1.7, rng)
# deck shadow: a broken key line under the viaduct
for seg in arclen_split(offset_path(deck, 0), rng, (16, 40), (8, 20)):
    m = seg[len(seg) // 2]
    if keep(m[0], m[1], rng, gamma=0.8) and len(seg) > 3:
        pen_path(kmd, [(x + SHD[0] * 1.6, y + SHD[1] * 1.6) for x, y in seg], 2.6, rng, amp=0.3, trem=0.2)
# the buffer stop: a hard bar across the end of the line, braced
ex_, ey_ = END
pdx, pdy = deck[-1][0] - deck[-4][0], deck[-1][1] - deck[-4][1]
Lp = math.hypot(pdx, pdy) or 1
ux, uy = pdx / Lp, pdy / Lp
vx, vy = -uy, ux
BUF = blank()                 # the stop gets clear ground around it
ImageDraw.Draw(BUF).ellipse(px([(ex_ - 22, ey_ - 22), (ex_ + 22, ey_ + 22)]), fill=255)
pen(gnd, [(ex_ + vx * 12 + ux * 1, ey_ + vy * 12 + uy * 1), (ex_ - vx * 12 + ux * 1, ey_ - vy * 12 + uy * 1)], 6.4, rng, wob=0.2, trem=0, a0=0.3, a1=0.4)
for side in (-1, 1):
    pen(gnd, [(ex_ + vx * side * 8 - ux * 1, ey_ + vy * side * 8 - uy * 1),
              (ex_ + vx * side * 4.8 - ux * 15, ey_ + vy * side * 4.8 - uy * 15)], 3.0, rng, wob=0.2, trem=0)
# the last of the deck in key, one more time, heavier: the line ends here
for side in (-1, 1):
    e = offset_path(deck[-8:], side * 4.8)
    pen_path(kmd, [(x + 1.2, y - 1.0) for x, y in e], 2.7, rng, amp=0.3, trem=0, a0=0.3, a1=0.2)
dot(kmd, ex_ + ux * 6, ey_ + uy * 6, 3.4, rng)
# Madavara station: the platform box, hatched in green, drawn over in key
if station:
    st = simplify(station, 1.0)
    if st[0] == st[-1]:
        st = st[:-1]
    GREEN = OR(GREEN, AND(poly_mask([st]), hatch_field(60, 4.6, 2.6, rng)))
    gnd = ImageDraw.Draw(GREEN)
    box(kmd, st, 3.0, rng, over=(-0.5, 4.0))
# the footbridge down to the compound gate
pen(kmd, [STATION_C, ((STATION_C[0] + GATE[0]) / 2 + 1, (STATION_C[1] + GATE[1]) / 2), GATE], 2.7, rng, wob=0.3)
METRO_G = GREEN
GREEN = blank()
log('metro done')

# orchards: rows of hand-dotted trees, every orchard planted on its own angle
ORCH = blank()
od = ImageDraw.Draw(ORCH)
orch_mask = poly_mask(orchards).resize((UW, UH), Image.NEAREST)


def tree(d, x, y, base, rng, n=(4, 7)):
    for _ in range(rng.randint(*n)):
        ox, oy = rng.gauss(0, base * 0.42), rng.gauss(0, base * 0.42)
        dot(d, x + ox, y + oy, base * rng.uniform(0.46, 0.72), rng)


for poly in orchards:
    a = poly_area(poly)
    if a < 200:
        continue
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    ang = rng.uniform(0, math.pi)
    ca_, sa_ = math.cos(ang), math.sin(ang)
    sp_ = rng.uniform(11.0, 12.4)
    c0 = centroid(poly)
    ext = max(max(xs) - min(xs), max(ys) - min(ys))
    rowi = -ext
    while rowi < ext:
        rowj = -ext + rng.uniform(0, sp_)
        drift = rng.gauss(0, 0.6)
        while rowj < ext:
            x = c0[0] + ca_ * rowj - sa_ * rowi + rng.gauss(0, 0.45)
            y = c0[1] + sa_ * rowj + ca_ * rowi + rng.gauss(0, 0.45) + drift
            rowj += sp_ * rng.uniform(0.9, 1.1)
            if not (0 <= x < UW and 0 <= y < UH) or not orch_mask.getpixel((int(x), int(y))):
                continue
            if rng.random() < 0.1 or not keep(x, y, rng, gamma=1.1):
                continue           # a gap in the row: a tree that died, a well, a shed
            tb = rng.uniform(3.3, 4.1)
            tree(od, x, y, tb, rng, (3, 4))
            dot(kmd, x + SHD[0] * 0.8, y + SHD[1] * 0.8, rng.uniform(1.5, 1.9), rng)   # its shadow
        rowi += sp_ * rng.uniform(0.92, 1.08)
GREEN = OR(GREEN, ORCH)

# scrub: scribbled little bushes, sparse
SCR = blank()
scd = ImageDraw.Draw(SCR)
scrub_mask = poly_mask(scrub + farmland).resize((UW, UH), Image.NEAREST)
for _ in range(9000):
    x, y = rng.uniform(0, UW - 1), rng.uniform(0, UH - 1)
    if not scrub_mask.getpixel((int(x), int(y))) or not keep(x, y, rng, gamma=1.2):
        continue
    if rng.random() < 0.5:
        k = rng.choice((2, 3))
        for j in range(k):
            a = -math.pi / 2 + (j - (k - 1) / 2) * 0.55 + rng.gauss(0, 0.15)
            L = rng.uniform(3.0, 4.4)
            bx = x + (j - (k - 1) / 2) * 1.7
            scd.line([(bx * R, y * R), ((bx + math.cos(a) * L) * R, (y + math.sin(a) * L) * R)], fill=255, width=int(2.6 * R))
    else:
        dot(scd, x, y, rng.uniform(1.5, 2.1), rng)
GREEN = OR(GREEN, SCR)

# woods, parks, the school ground: lumpy canopies
WD = blank()
wdd = ImageDraw.Draw(WD)
woods_mask = poly_mask(woods).resize((UW, UH), Image.NEAREST)
for poly in woods:
    a = poly_area(poly)
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    for _ in range(int(a / 90) + 2):
        x, y = rng.uniform(min(xs), max(xs)), rng.uniform(min(ys), max(ys))
        if not (0 <= x < UW and 0 <= y < UH) or not woods_mask.getpixel((int(x), int(y))) or not keep(x, y, rng):
            continue
        tree(wdd, x, y, rng.uniform(4.0, 7.0), rng)
GREEN = OR(GREEN, WD)

# the field: the show ground's grass where the crowd hasn't reached, little tufts
FIELD = SUB(SUB(SUB(BIEC, dilate(BLD, int(2 * R))), ROADS), poly_mask(orchards))
field_s = FIELD.resize((UW, UH), Image.NEAREST)
cz_s = CZ.resize((UW, UH), Image.NEAREST)
TUFT = blank()
tfd = ImageDraw.Draw(TUFT)
tclump = Image.effect_noise((UW // 30 + 2, UH // 30 + 2), 70).convert('L').resize((UW, UH), Image.BICUBIC)
for _ in range(16000):
    x, y = rng.uniform(0, UW - 1), rng.uniform(0, UH - 1)
    if not field_s.getpixel((int(x), int(y))) or cz_s.getpixel((int(x), int(y))):
        continue
    if tclump.getpixel((int(x), int(y))) < 140 or not keep(x, y, rng, gamma=0.8):
        continue
    for k in range(rng.choice((2, 3, 3))):
        a = -math.pi / 2 + (k - 1) * 0.5 + rng.gauss(0, 0.15)
        L = rng.uniform(3.0, 4.4)
        bx = x + (k - 1) * 1.6
        tfd.line([(bx * R, y * R), ((bx + math.cos(a) * L) * R, (y + math.sin(a) * L) * R)], fill=255, width=int(2.6 * R))
GREEN = OR(GREEN, AND(TUFT, FIELD))
# crowd edge: the grass shows between the last people
edge_turf = AND(SUB(CZ, erode(CZ, int(3 * R))), FIELD)
GREEN = OR(GREEN, AND(edge_turf, TUFT))

# rain trees: along the compound wall, along the big road verges, round the lake
TREES = blank()
trd = ImageDraw.Draw(TREES)


def tree_line(path, every, out_rng, base_rng, side_choice=(-1, 1)):
    dp = densify(path, 2.0)
    N = normals(dp)
    i = 0
    while i < len(dp):
        x, y = dp[i]
        nx, ny = N[i]
        side = rng.choice(side_choice)
        o = rng.uniform(*out_rng) * side
        tx, ty = x + nx * o, y + ny * o
        if 0 <= tx < UW and 0 <= ty < UH and keep(tx, ty, rng, gamma=0.9):
            tree(trd, tx, ty, rng.uniform(*base_rng), rng)
        i += int(rng.uniform(*every))


tree_line(biec + biec[:1], (6, 14), (5, 10), (4.0, 6.5), side_choice=(1,))
for nm, br, pts in motor:
    if not br:
        tree_line(pts, (10, 26), (14, 22), (3.6, 5.6))
tree_line(lake + lake[:1], (5, 12), (6, 13), (3.8, 6.2), side_choice=(1,))
for isl in islands:
    c = centroid(isl)
    tree(trd, c[0], c[1], 4.5, rng)
TREES = SUB(TREES, OR(LAKE, BIG_ROADS))
TREES = SUB(TREES, dilate(METRO_M, int(1 * R)))
GREEN = OR(GREEN, TREES)
GREEN = SUB(GREEN, dilate(KC, 2))
log('green done')

# ==========================================================================
# BLUE INK -- Anchepalya lake: shore echoes + ripple hatching
# ==========================================================================
rng = random.Random(SEED + 50)
BLUE = blank()
bdw = ImageDraw.Draw(BLUE)
water_l = poly_mask([lake] + ponds, Image.new('L', (W, H), 0)).resize((UW, UH), Image.BILINEAR)
water_l = SUB(water_l, poly_mask(islands).resize((UW, UH), Image.BILINEAR))
wa = np.asarray(water_l, dtype=np.float32) / 255.0
land_blur = np.asarray(NOT(water_l).filter(ImageFilter.GaussianBlur(22)), dtype=np.float32)
brk = np.asarray(Image.effect_noise((UW // 18 + 2, UH // 18 + 2), 70).convert('L').resize((UW, UH), Image.BICUBIC),
                 dtype=np.float32)
levels = [184, 162, 141, 121, 102, 85, 70]
for i, Lv in enumerate(levels):
    inside = (land_blur < Lv) & (wa > 0.5)
    er = np.zeros_like(inside)
    er[1:-1, 1:-1] = inside[1:-1, 1:-1] & inside[:-2, 1:-1] & inside[2:, 1:-1] & inside[1:-1, :-2] & inside[1:-1, 2:]
    edge = inside & ~er
    cut = 84 + i * 11
    ys_, xs_ = np.nonzero(edge & (brk >= cut))
    on = set()
    for x, y in zip(xs_.tolist(), ys_.tolist()):
        if keep(x, y, rng, gamma=1.0):
            on.add((x, y))
    wob = 0.5 + i * 0.12

    def P2(x, y):
        return ((x + 0.5 + wob * math.sin(y / 21.0 + i * 1.7)) * R, (y + 0.5 + wob * math.sin(x / 27.0 + i * 2.3)) * R)
    for (x, y) in on:
        X, Y = P2(x, y)
        rr = 1.35 * R
        bdw.ellipse([X - rr, Y - rr, X + rr, Y + rr], fill=255)
        for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
            if (x + dx, y + dy) in on:
                bdw.line([(X, Y), P2(x + dx, y + dy)], fill=255, width=int(2.7 * R))
# ripples: short wobbly dashes, each kept or not by density, gaps where the wind isn't
waves = blank()
wvd = ImageDraw.Draw(waves)
lb = Image.fromarray((wa * 255).astype(np.uint8)).getbbox() or (0, 0, UW, UH)
yy = lb[1] - 6.0
while yy < lb[3] + 6:
    lam = rng.uniform(11, 16)
    amp = rng.uniform(0.9, 1.5)
    ph = rng.uniform(0, TAU)
    tilt = 0.16 + rng.uniform(-0.02, 0.02)       # the ripples run with the lake's long axis
    ph2, lam2 = rng.uniform(0, TAU), rng.uniform(60, 140)
    pts = [(x, yy + (x - lb[0]) * tilt + amp * (0.55 + 0.45 * math.sin(x / lam2 + ph2)) * math.sin(x / lam * TAU + ph))
           for x in range(lb[0] - 200, lb[2] + 10, 2)]
    for seg in arclen_split(pts, rng, (8, 40), (7, 34)):
        m = seg[len(seg) // 2]
        if keep(m[0], m[1], rng, gamma=1.5):
            pen_path(wvd, seg, 2.7, rng, amp=0.3, trem=0.15, step=3, pv=0.15)
    yy += rng.uniform(7.6, 10.0)
deep = thr(Image.fromarray(np.clip(255 - land_blur, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), 255 - 118)
WATER_M = SUB(OR(LAKE, PONDS), ISLANDS)
BLUE = OR(BLUE, AND(AND(waves, deep), WATER_M))
log('blue done')

# ==========================================================================
# SOUND RINGS -- the one bright gesture, in the accent
# ==========================================================================
rng = random.Random(SEED + 30)
RINGS = blank()
HALO = blank()
rrd, hd = ImageDraw.Draw(RINGS), ImageDraw.Draw(HALO)
radii = []
r_ = 50.0
while r_ < 1700:
    radii.append(r_)
    r_ = r_ * 1.24 + 30
for k, rad in enumerate(radii):
    c0 = (sx + rng.gauss(0, 3) + fx * 5, sy + rng.gauss(0, 3) + fy * 5)
    ph = [rng.uniform(0, TAU) for _ in range(3)]
    pts = []
    n = int(rad * 0.9) + 60
    th0 = rng.uniform(0, TAU)
    for i in range(n + 1):
        th = th0 + i / n * TAU
        rr = rad * (1 + 0.022 * math.sin(3 * th + ph[0]) + 0.01 * math.sin(7 * th + ph[1])) + 5 * math.sin(2 * th + ph[2])
        pts.append((c0[0] + rr * math.cos(th), c0[1] + rr * math.sin(th)))
    dash = (30 + rad * 0.12, 90 + rad * 0.4)
    gap = (12 + rad * 0.04, 40 + rad * 0.2)
    for seg in arclen_split(pts, rng, dash, gap):
        dr = rng.gauss(0, 2.5)                 # each arc re-drawn on its own, never quite on the last one
        cxp, cyp = c0
        seg = [(x + (x - cxp) / rad * dr, y + (y - cyp) / rad * dr) for x, y in seg]
        for piece in thin_path(seg, rng, (60, 160), field=DENS_RING_L, gamma=0.75):
            if len(piece) < 4:
                continue
            w = max(2.7, 3.7 - k * 0.12)
            p = jitter_path(densify(piece, 5.0), rng, 1.3)
            p = hand(p, rng, wob=0.0, trem=0.4)
            ink(hd, p, w + 4.6, rng, a0=0, a1=0, pv=0.0)
            ink(rrd, p, w, rng, a0=1.2, a1=2.5, pv=0.25)
log('rings done')

# ==========================================================================
# assemble
# ==========================================================================
rng = random.Random(SEED + 55)
CITY = SUB(CITY, dilate(TREES, int(1.2 * R)))
CITY = SUB(CITY, BIG_ROADS)
CITY = SUB(CITY, CZ)
CITY = SUB(CITY, TRAIL)
LINES = OR(OR(KR, KL), KM)
KEYALL = OR(OR(CITY, HALLK), OR(LINES, KC))
DECK = road_mask([(9.6 + 5.0, METRO_C)])
GREEN = SUB(SUB(GREEN, BUF), DECK)
GREEN = OR(GREEN, METRO_G)
KEYALL = SUB(KEYALL, SUB(DECK, KM))
KEYALL = SUB(KEYALL, SUB(BUF, KM))
KEYALL = SUB(KEYALL, HALO)
GREEN = SUB(GREEN, HALO)
BLUE = SUB(BLUE, HALO)
ACCENT = OR(ACC, RINGS)

# a ragged outer edge for anything that still runs toward the canvas rectangle
edge_f = Image.new('L', (DW, DH), 0)
ImageDraw.Draw(edge_f).rectangle([48 * DLR, 48 * DLR, (UW - 48) * DLR, (UH - 48) * DLR], fill=255)
edge_f = edge_f.filter(ImageFilter.GaussianBlur(16 * DLR)).resize((W, H), Image.BICUBIC)
EDGE = thr(ImageChops.subtract(edge_f, Image.blend(noise(5, rng, 80), noise(22, rng, 80), 0.6), 1, 0), 1)
KEYALL, GREEN, BLUE, ACCENT = AND(KEYALL, EDGE), AND(GREEN, EDGE), AND(BLUE, EDGE), AND(ACCENT, EDGE)

# print physics: a little ink spread on the edges, minimum feature clean-up; flat solids
rng = random.Random(SEED + 60)
inks = {}
for name, m in (('key', KEYALL), ('green', GREEN), ('blue', BLUE), ('accent', ACCENT)):
    m = thr(m.filter(ImageFilter.GaussianBlur(0.38 * R)), 128)     # ink spread, flat: no grain, no tooth
    m = opening(m, max(3, int(round(1.7 * R)) | 1))
    inks[name] = m
    log('ink', name, 'ready')

# misregistration, px at print resolution
MIS = {'key': (0, 0), 'green': (6, -4), 'blue': (-5, 5), 'accent': (4, 6)}


def shifted(m, dx, dy):
    dx, dy = int(round(dx * R / 3)), int(round(dy * R / 3))
    out = blank()
    out.paste(m, (dx, dy))
    return out


safe = blank()
ImageDraw.Draw(safe).rectangle([int(14 * R), int(14 * R), W - int(14 * R), H - int(14 * R)], fill=255)
for k in inks:
    inks[k] = AND(shifted(inks[k], *MIS[k]), safe)

PAL = {'tee': '#FFFAE7', 'key': '#22201D', 'green': '#2F7D52', 'blue': '#6E95CE', 'accent': '#2C46BE'}


def hex2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def composite(pal):
    # overprint: inks multiply where they cross, like riso on paper; accent on top
    out = Image.new('RGB', (W, H), (255, 255, 255))
    for k in ('blue', 'green', 'key'):
        layer = Image.new('RGB', (W, H), (255, 255, 255))
        layer.paste(hex2rgb(pal[k]), (0, 0, W, H), inks[k])
        out = ImageChops.multiply(out, layer)
    out.paste(hex2rgb(pal['accent']), (0, 0, W, H), inks['accent'])
    alpha = inks['green']
    for k in ('blue', 'key', 'accent'):
        alpha = OR(alpha, inks[k])
    out.putalpha(alpha)
    return out


art = composite(PAL)
art.save(os.path.join(HERE, f'art-cream{SUFFIX}.png'), compress_level=6)
prev = Image.new('RGB', (W, H), hex2rgb(PAL['tee']))
prev.paste(art, (0, 0), art)
prev.resize((900, 1200), Image.LANCZOS).save(os.path.join(HERE, f'preview-cream{SUFFIX}.png'))
log('saved')

hall_c = centroid([centroid(h) for _, h in halls])
lake_c = centroid(lake)
anch = {
    'stage': [round(sx), round(sy)], 'foh': [round(FOH[0]), round(FOH[1])],
    'station': [round(c) for c in STATION_C], 'end_of_line': [round(c) for c in END],
    'halls': [round(c) for c in hall_c], 'lake': [round(c) for c in lake_c],
    'interchange': [round(c) for c in proj(13.0556, 77.4769)],
    'tumakuru_road': [round(c) for c in proj(13.0600, 77.4640)],
}
json.dump({'palette': PAL, 'anchors': anch, 'type_zones': TYPE_ZONES},
          open(os.path.join(HERE, f'render-info{SUFFIX}.json'), 'w'), indent=1)
log('done', anch)
