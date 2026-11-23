#!/usr/bin/env python3
"""
Direction A - "the ground you stood on"
Printmaker-style top-down map of Mahalaxmi Race Course, Mumbai, drawn from real
OpenStreetMap geometry (osm.json: fetched once from Overpass, cached, reused).

Pillow only. Seeded, re-runnable (~40 s on 4 cores).
    python3 gen.py            -> full 3600x4800 render (R=3 px per unit)
    R=1.5 python3 gen.py      -> draft (files get a -draft suffix)

Units: layout lives in a 1200 x 1600 unit space; px = unit * R.
Every ink is its own binary layer (key / green / blue / red). Layers are
built from hand-like vector marks (wobbling strokes, uneven stipple, hatching
with uneven spacing), thinned out object-by-object toward the edge of the
map, then given ink spread + grain, cleaned to a minimum feature size,
misregistered and composited with a binary alpha.
"""
import json, math, os, random, time
from PIL import Image, ImageDraw, ImageFilter, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
R = float(os.environ.get('R', '3'))
UW, UH = 1200, 1600
W, H = int(round(UW * R)), int(round(UH * R))
SUFFIX = '' if R >= 3 else '-draft'
SEED = 9122026
T0 = time.time()


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


# --------------------------------------------------------------------------
# projection: lon/lat -> local metres (cos-lat corrected) -> rotate -> units
# --------------------------------------------------------------------------
LAT_C, LON_C = 18.984293, 72.820206          # centroid of the race track
MLAT = 110574.0
MLON = 111320.0 * math.cos(math.radians(LAT_C))
ROT = math.radians(-78.0)                    # west is (nearly) up: the sea on top
SCALE = 0.80                                 # units per metre
CX, CY = 610.0, 1115.0                       # where the track centroid lands
cosR, sinR = math.cos(ROT), math.sin(ROT)

_wr = random.Random(SEED + 1)
WARP = []
for _ in range(5):                            # slow "drawn by eye" distortion of the whole map
    ang = _wr.uniform(0, math.tau)
    lam = _wr.uniform(160, 520)
    WARP.append((math.cos(ang) * math.tau / lam, math.sin(ang) * math.tau / lam,
                 _wr.uniform(0, math.tau), _wr.uniform(0, math.tau), _wr.uniform(0.5, 1.4)))


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
# geometry + raster helpers
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


def px(pts):
    return [(x * R, y * R) for x, y in pts]


MINW = 2.6   # units: 7.8 px at print res, above the 6 px minimum


def stroke(d, pts, width, rng, amp=0.5, step=4.0, wvar=0.18, fill=255):
    """a pen stroke: wobble + pressure (width) changing in short runs, round caps"""
    if len(pts) < 2:
        return
    p = px(jitter_path(densify(pts, step), rng, amp))
    i = 0
    while i < len(p) - 1:
        n = rng.randint(3, 9)
        run = p[i:i + n + 1]
        w = max(width * (1 + rng.uniform(-wvar, wvar)), MINW) * R
        d.line(run, fill=fill, width=max(1, int(round(w))), joint='curve')
        r = w / 2
        for (x, y) in (run[0], run[-1]):
            d.ellipse([x - r, y - r, x + r, y + r], fill=fill)
        i += n


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


def dot(d, x, y, r, fill=255, squash=1.0, rng=None):
    X, Y, rr = x * R, y * R, r * R
    d.ellipse([X - rr, Y - rr * squash, X + rr, Y + rr * squash], fill=fill)


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
log('loading osm.json')
osm = json.load(open(os.path.join(HERE, 'osm.json')))
EL = osm['elements']
BY = {(e['type'], e['id']): e for e in EL}


def geoms_of(e):
    if 'geometry' in e:
        return [e['geometry']]
    return [m['geometry'] for m in e.get('members', []) if m.get('geometry') and m.get('role') in ('outer', '')]


def P(geom):
    return [proj(p['lat'], p['lon']) for p in geom if p]


buildings, roads, rails, platforms, coast, water, parks, golf, sand = [], [], [], [], [], [], [], [], []
ROAD_W = {'motorway': 15, 'trunk': 14, 'primary': 12, 'secondary': 10, 'tertiary': 8,
          'motorway_link': 8, 'trunk_link': 8, 'primary_link': 7, 'secondary_link': 7, 'tertiary_link': 6,
          'residential': 5.5, 'unclassified': 5.5, 'living_street': 4.5, 'service': 3.6,
          'pedestrian': 4.5, 'construction': 5}
COURSE_ID, TRACK_REL, HAJI_ALI = 1289073486, 7107871, 53355635
haji = None
for e in EL:
    t = e.get('tags', {})
    if e['id'] in (COURSE_ID, TRACK_REL):
        continue
    gs = geoms_of(e)
    if not gs:
        continue
    if e['id'] == HAJI_ALI:
        haji = P(gs[0])
    if 'building' in t:
        for g in gs:
            pts = P(g)
            if len(pts) > 2:
                buildings.append(pts)
    elif t.get('highway') in ROAD_W:
        for g in gs:
            roads.append((ROAD_W[t['highway']], P(g)))
    elif t.get('railway') in ('rail', 'yard', 'disused') and t.get('tunnel') != 'yes':
        for g in gs:
            rails.append((t.get('service'), P(g)))
    elif t.get('railway') == 'platform':
        for g in gs:
            platforms.append(P(g))
    elif t.get('natural') == 'coastline':
        for g in gs:
            coast.append(P(g))
    elif t.get('natural') == 'water':
        for g in gs:
            pts = P(g)
            if len(pts) > 2:
                water.append(pts)
    elif t.get('leisure') == 'golf_course':
        for g in gs:
            golf.append(P(g))
    elif (t.get('leisure') in ('park', 'garden', 'pitch') or
          t.get('landuse') in ('grass', 'forest', 'recreation_ground') or
          t.get('natural') in ('wood', 'grassland', 'scrub')):
        for g in gs:
            pts = P(g)
            if len(pts) > 2:
                parks.append(pts)
    elif t.get('natural') == 'sand':
        for g in gs:
            pts = P(g)
            if len(pts) > 2:
                sand.append(pts)

course = P(BY[('way', COURSE_ID)]['geometry'])
rings = sorted([P(m['geometry']) for m in BY[('relation', TRACK_REL)]['members']], key=poly_area)
ring_in, ring_mid, ring_out = rings          # sand track inside, turf track outside (with chute)
log(f'{len(buildings)} buildings, {len(roads)} roads, {len(rails)} rails, {len(coast)} coast ways')

# the stage: north-east end of the infield, the crowd stretching back toward the sea
ic = centroid(ring_in)
ax = math.radians(25.4)                       # track long axis, metres space (east = 0)
a_can = (math.cos(ax) * cosR - math.sin(ax) * sinR, -(math.cos(ax) * sinR + math.sin(ax) * cosR))
half_long = max((x - ic[0]) * a_can[0] + (y - ic[1]) * a_can[1] for x, y in ring_in)
STAGE = (ic[0] + a_can[0] * (half_long - 44), ic[1] + a_can[1] * (half_long - 44))
FACING = (-a_can[0], -a_can[1])               # from the stage into the crowd
NORMAL = (-FACING[1], FACING[0])
fx, fy = FACING
nx_, ny_ = NORMAL
sx, sy = STAGE
FOH = (sx + fx * 250, sy + fy * 250)
log('stage at', [round(c) for c in STAGE])

# --------------------------------------------------------------------------
# low-res fields: sea mask (flood fill against the coastline), coast distance
# --------------------------------------------------------------------------
PAD = 260
LR = 1.0
LW, LH = int((UW + 2 * PAD) * LR), int((UH + 2 * PAD) * LR)


def lpx(pts):
    return [((x + PAD) * LR, (y + PAD) * LR) for x, y in pts]


bar = Image.new('L', (LW, LH), 0)
bd = ImageDraw.Draw(bar)
for c in coast:
    bd.line(lpx(c), fill=255, width=3)
for la, lo in [(18.9838, 72.8108), (18.990, 72.806), (18.986, 72.8045), (18.982, 72.8070)]:
    sx_, sy_ = lpx([proj(la, lo)])[0]
    if 0 <= sx_ < LW and 0 <= sy_ < LH and bar.getpixel((int(sx_), int(sy_))) == 0:
        ImageDraw.floodfill(bar, (int(sx_), int(sy_)), 128)
sea_l = bar.point(lambda p: 255 if p == 128 else 0)
land_l = NOT(sea_l)
crop = tuple(int(c) for c in (PAD * LR, PAD * LR, (PAD + UW) * LR, (PAD + UH) * LR))
SEA = thr(sea_l.crop(crop).resize((W, H), Image.BILINEAR), 128)
LAND = NOT(SEA)
BATH_LO = land_l.filter(ImageFilter.GaussianBlur(40 * LR)).crop(crop)          # 1 px per unit
BATH = BATH_LO.resize((W, H), Image.BICUBIC)
LAND_LO = land_l.crop(crop)
log('sea mask done')

# --------------------------------------------------------------------------
# density: where the hand kept drawing. The map thins out object by object
# toward a ragged edge, and goes quiet where the type will sit.
# --------------------------------------------------------------------------
rng = random.Random(SEED)
DLR = 0.25
DW, DH = int(UW * DLR), int(UH * DLR)
dens = Image.new('L', (DW, DH), 0)
bc = (600, 812)
harm = [(rng.uniform(0.03, 0.07), k, rng.uniform(0, math.tau)) for k in (2, 3, 5, 7, 11)]
blob = []
for i in range(720):
    th = i / 720 * math.tau
    rx, ry, ne = 520, 720, 3.0
    c_, s_ = math.cos(th), math.sin(th)
    base = (abs(c_) ** ne + abs(s_) ** ne) ** (-1 / ne)
    rr = base * (1 + sum(a / (1 + 0.25 * k) * math.sin(k * th + ph) for a, k, ph in harm))
    blob.append(((bc[0] + rx * rr * c_) * DLR, (bc[1] + ry * rr * s_) * DLR))
ImageDraw.Draw(dens).polygon(blob, fill=255)
TYPE_ZONES = {   # units: x, y, w, h  (also used for the manifest)
    'wordmark': (300, 44, 820, 150),
    'city': (300, 262, 400, 190),
    'dates': (690, 1478, 450, 74),
}
calm = Image.new('L', (DW, DH), 0)
cd = ImageDraw.Draw(calm)
for name, (x, y, w, h) in TYPE_ZONES.items():
    v = {'wordmark': 120, 'city': 105, 'dates': 190}[name]
    cd.rounded_rectangle([(x - 10) * DLR, (y - 10) * DLR, (x + w + 10) * DLR, (y + h + 10) * DLR], radius=int(40 * DLR), fill=v)
calm = calm.filter(ImageFilter.GaussianBlur(26 * DLR))
# nothing reaches the rectangle of the canvas: a border falloff on every field
border = Image.new('L', (DW, DH), 0)
ImageDraw.Draw(border).rectangle([34 * DLR, 34 * DLR, (UW - 34) * DLR, (UH - 34) * DLR], fill=255)
border = border.filter(ImageFilter.GaussianBlur(18 * DLR))
DENS_L = AND(SUB(dens.filter(ImageFilter.GaussianBlur(60 * DLR)), calm), border)
DENS_RING_L = AND(SUB(dens.filter(ImageFilter.GaussianBlur(90 * DLR)).point(lambda p: min(255, int(p * 1.7))),
                      calm.point(lambda p: p // 2)), border)


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
            if out and out[-1][-1] == seg[0]:
                out[-1].extend(seg[1:])
            else:
                out.append(seg)
    # re-join pieces that touch (arclen_split leaves tiny gaps)
    joined = []
    for seg in out:
        if joined and math.hypot(joined[-1][-1][0] - seg[0][0], joined[-1][-1][1] - seg[0][1]) < 0.3:
            joined[-1].extend(seg[1:])
        else:
            joined.append(seg)
    return joined


DENS = DENS_L.resize((W, H), Image.BICUBIC)
for c in [(0, 0), (UW, 0), (0, UH), (UW, UH)]:
    log('corner', c, [round(v, 4) for v in unproj(*c)])
log('density field done')


# --------------------------------------------------------------------------
# masks of places
# --------------------------------------------------------------------------
def poly_mask(polys):
    m = blank()
    d = ImageDraw.Draw(m)
    for p in polys:
        if len(p) > 2:
            d.polygon(px(p), fill=255)
    return m


COURSE = poly_mask([course])
RIN, RMID, ROUT = poly_mask([ring_in]), poly_mask([ring_mid]), poly_mask([ring_out])
TRACK_BAND = SUB(ROUT, RMID)
SAND_BAND = SUB(RMID, RIN)
BLD = poly_mask(buildings)
ROADS = blank()
rd = ImageDraw.Draw(ROADS)
for w_, pts in roads:
    if len(pts) > 1:
        rd.line(px(pts), fill=255, width=int(w_ * R), joint='curve')
        r_ = w_ * R / 2
        for x, y in (px(pts[:1]) + px(pts[-1:])):
            rd.ellipse([x - r_, y - r_, x + r_, y + r_], fill=255)
RAILCOR = blank()
rcd = ImageDraw.Draw(RAILCOR)
for svc, pts in rails:
    rcd.line(px(pts), fill=255, width=int(12 * R), joint='curve')
WATER = poly_mask(water)
PARKM = OR(poly_mask(parks), poly_mask(golf))
log('place masks done')


# ==========================================================================
# KEY INK — the drawing hand
# ==========================================================================
def hatch_field(angle, spacing, width, rng, wav=0.5):
    img = blank()
    d = ImageDraw.Draw(img)
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    diag = math.hypot(UW, UH) / 2 + 20
    t = -diag
    while t < diag:
        pts, s, off, ph = [], -diag, 0.0, rng.uniform(0, math.tau)
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
HA = hatch_field(-50, 5.8, 2.7, rng)
HB = hatch_field(40, 5.6, 2.7, rng)
log('hatch fields done')

# buildings: each one drawn or skipped by density; small = solid block,
# large = hatched (two directions) with a pen outline
bA, bB, bS, outl = [], [], [], []
for b in buildings:
    c = centroid(b)
    if not keep(c[0], c[1], rng, gamma=1.4):
        continue
    a = poly_area(b)
    if a < 160:
        bS.append(b)
    else:
        (bA if rng.random() < 0.5 else bB).append(b)
        outl.append(b)
KEY_BLD = OR(OR(AND(poly_mask(bA), HA), AND(poly_mask(bB), HB)), poly_mask(bS))
KEY_BLD = OR(KEY_BLD, AND(poly_mask(platforms), HA))
od = ImageDraw.Draw(KEY_BLD)
for b in outl:
    stroke(od, b + b[:1], 2.7, rng, amp=0.3, step=5)
log('buildings done')

# ground: a hand-set halftone screen (rotated grid, jittered, dot size breathing
# with a slow ink-load field) — the roads will be cut through it
KEY_GROUND = blank()
gd = ImageDraw.Draw(KEY_GROUND)
load = Image.effect_noise((UW // 40 + 2, UH // 40 + 2), 60).convert('L').resize((UW, UH), Image.BICUBIC)
g = 9.0
ga = math.radians(28)
cga, sga = math.cos(ga), math.sin(ga)
span = int(math.hypot(UW, UH) / g) + 2
for i in range(-span, span):
    for j in range(-span, span):
        u0, v0 = i * g, j * g
        x = UW / 2 + u0 * cga - v0 * sga + rng.gauss(0, 0.55)
        y = UH / 2 + u0 * sga + v0 * cga + rng.gauss(0, 0.55)
        if not (0 <= x < UW and 0 <= y < UH):
            continue
        if not keep(x, y, rng, gamma=1.5):
            continue
        r = 1.36 + 0.42 * (load.getpixel((int(x), int(y))) / 255.0) + rng.uniform(-0.06, 0.1)
        dot(gd, x, y, r, squash=rng.uniform(0.88, 1.06))
GROUND_REGION = SUB(SUB(SUB(LAND, PARKM), COURSE), WATER)
KEY_GROUND = AND(KEY_GROUND, GROUND_REGION)

# sand / mudflats at the haji ali shore: tight stipple
KEY_SAND = blank()
sdd = ImageDraw.Draw(KEY_SAND)
for _ in range(9000):
    x, y = rng.uniform(0, UW), rng.uniform(0, UH)
    if keep(x, y, rng):
        dot(sdd, x, y, rng.uniform(1.4, 1.8))
KEY_SAND = AND(KEY_SAND, poly_mask(sand))

# the city texture is cut by the roads: the shirt shows through
CITY = OR(OR(KEY_BLD, KEY_GROUND), KEY_SAND)
CITY = SUB(CITY, ROADS)
CITY = SUB(CITY, SUB(RAILCOR, BLD))
log('city texture done')

# railway: the Western line, every track drawn; ties on the running lines
KEY_LINES = blank()
kd = ImageDraw.Draw(KEY_LINES)
for svc, pts in rails:
    if len(pts) < 2:
        continue
    if svc is not None and rng.random() < 0.5:      # the yard, simplified by hand
        continue
    for seg in thin_path(pts, rng, (20, 60), gamma=1.2):
        stroke(kd, seg, 2.6, rng, amp=0.25, step=6, wvar=0.08)
        if svc is None:
            dp = densify(seg, 11.0)
            for i in range(1, len(dp) - 1):
                (x0, y0), (x1, y1) = dp[i - 1], dp[i + 1]
                L = math.hypot(x1 - x0, y1 - y0) or 1
                nx, ny = -(y1 - y0) / L, (x1 - x0) / L
                x, y = dp[i]
                kd.line([((x - nx * 3.4) * R, (y - ny * 3.4) * R), ((x + nx * 3.4) * R, (y + ny * 3.4) * R)],
                        fill=255, width=int(2.6 * R))

# coastline: drawn twice, the second pass drifting off the first
for c in coast:
    for seg in thin_path(c, rng, (30, 90), gamma=0.8):
        stroke(kd, seg, 3.2, rng, amp=0.6, step=4)
    for seg in arclen_split(c, rng, (60, 220), (20, 90)):
        m = seg[len(seg) // 2]
        if keep(m[0], m[1], rng):
            stroke(kd, [(x + 3.4, y - 2.6) for x, y in seg], 2.6, rng, amp=1.1, step=4)

# haji ali: the dargah on its rock, the causeway walk out to it
if haji:
    KEY_LINES = OR(KEY_LINES, AND(poly_mask([haji]), HB))
    kd = ImageDraw.Draw(KEY_LINES)
    stroke(kd, haji + haji[:1], 2.8, rng, amp=0.3, step=3)

# the course fence: a quick dashed line
for seg in arclen_split(course + course[:1], rng, (14, 34), (5, 10)):
    stroke(kd, seg, 2.6, rng, amp=0.3, step=4)

# canal / nalla banks
for wp in water:
    if poly_area(wp) > 400:
        for seg in thin_path(wp + wp[:1], rng, (20, 60)):
            stroke(kd, seg, 2.6, rng, amp=0.4, step=4)
log('lines done')

# the track: three rails, outer two drawn as a confident doubled line
KEY_TRACK = blank()
td = ImageDraw.Draw(KEY_TRACK)
for ring, wdt, n in ((ring_out, 3.8, 2), (ring_mid, 3.3, 2), (ring_in, 2.9, 1)):
    for k in range(n):
        o = (k * 2.8 * rng.choice((-1, 1)), k * 2.2)
        stroke(td, [(x + o[0], y + o[1]) for x, y in ring + ring[:1]], wdt - k * 0.5, rng,
               amp=0.7 + 0.6 * k, step=4, wvar=0.22)
st = blank()
std = ImageDraw.Draw(st)
for _ in range(int(UW * UH / 75)):
    x, y = rng.uniform(0, UW), rng.uniform(0, UH)
    dot(std, x, y, rng.uniform(1.4, 1.75))
KEY_TRACK = OR(KEY_TRACK, AND(st, SAND_BAND))
log('track done')

# ==========================================================================
# THE CROWD — heads, raised hands, phone lights, from above
# ==========================================================================
rng = random.Random(SEED + 20)
KEY_CROWD = blank()
RED = blank()
CROWDZ = blank()
cdw = ImageDraw.Draw(KEY_CROWD)
rdw = ImageDraw.Draw(RED)
czd = ImageDraw.Draw(CROWDZ)
inf_small = RIN.resize((UW, UH), Image.NEAREST)
placed = 0
G = 6.3
row = 0
gy_ = 0.0
toward = math.atan2(-fy, -fx)      # arms reach toward the stage
while gy_ < UH:
    gx_ = (row % 2) * G / 2
    row += 1
    while gx_ < UW:
        x, y = gx_ + rng.uniform(-1.8, 1.8), gy_ + rng.uniform(-1.8, 1.8)
        gx_ += G * rng.uniform(0.9, 1.1)
        if not (0 <= x < UW - 1 and 0 <= y < UH - 1) or inf_small.getpixel((int(x), int(y))) == 0:
            continue
        rx_, ry_ = x - sx, y - sy
        dist = rx_ * fx + ry_ * fy
        lat = abs(rx_ * nx_ + ry_ * ny_)
        if dist < 24 or math.hypot(x - FOH[0], y - FOH[1]) < 17:
            continue
        p = math.exp(-max(0, dist - 70) / 300.0) * math.exp(-max(0, lat - 90 - dist * 0.5) / 60.0)
        p = 0.03 + 0.97 * p
        if rng.random() > p:
            continue
        placed += 1
        if p > 0.32:
            dot(czd, x, y, 5.2)
        X, Y = x * R, y * R
        kind = rng.random()
        hr = rng.uniform(1.5, 1.85)
        if kind < 0.56:                          # a head
            dot(cdw, x, y, hr, squash=rng.uniform(0.85, 1.05))
        elif kind < 0.78:                        # head + one arm up toward the stage
            dot(cdw, x, y, hr)
            a = toward + rng.gauss(0, 0.5)
            side = rng.choice((-1.3, 1.3))
            bx, by = x + math.cos(a + side) * hr * 0.8, y + math.sin(a + side) * hr * 0.8
            L = rng.uniform(3.0, 4.0)
            ex, ey = bx + math.cos(a) * L, by + math.sin(a) * L
            cdw.line([(bx * R, by * R), (ex * R, ey * R)], fill=255, width=int(2.5 * R))
            dot(cdw, ex, ey, 1.35)                # the hand
        elif kind < 0.89:                        # both hands up
            dot(cdw, x, y, hr * 0.95)
            a = toward + rng.gauss(0, 0.35)
            for s_ in (-0.55, 0.55):
                bx, by = x + math.cos(a + s_ * 2.4) * hr * 0.7, y + math.sin(a + s_ * 2.4) * hr * 0.7
                L = rng.uniform(3.0, 3.8)
                ex, ey = bx + math.cos(a + s_ * 0.4) * L, by + math.sin(a + s_ * 0.4) * L
                cdw.line([(bx * R, by * R), (ex * R, ey * R)], fill=255, width=int(2.5 * R))
                dot(cdw, ex, ey, 1.3)
        else:                                    # phone held up: a lit slab + head
            dot(cdw, x, y, hr * 0.9)
            a = toward + rng.gauss(0, 0.5)
            cx_, cy_ = x + math.cos(a) * 4.2, y + math.sin(a) * 4.2
            hw, hh = 1.5 * R, 2.3 * R
            ca_, sa_ = math.cos(a + math.pi / 2), math.sin(a + math.pi / 2)
            quad = [(cx_ * R + ca_ * dx - sa_ * dy, cy_ * R + sa_ * dx + ca_ * dy)
                    for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]
            (rdw if rng.random() < 0.05 else cdw).polygon(quad, fill=255)
    gy_ += G * 0.87
CROWDZ = thr(CROWDZ.filter(ImageFilter.GaussianBlur(5 * R)), 120)
log(f'crowd: {placed} marks')


def rect(cx_, cy_, along_, across, fwd=(fx, fy)):
    ux, uy = fwd
    vx, vy = -uy, ux
    return [(cx_ + ux * a_ + vx * b_, cy_ + uy * a_ + vy * b_) for a_, b_ in
            ((-along_, -across), (along_, -across), (along_, across), (-along_, across))]


# stage (red), its outline drawn by the key pass a little off, screens, FOH
stage_poly = rect(sx - fx * 6, sy - fy * 6, 12, 42)
thrust = rect(sx + fx * 14, sy + fy * 14, 9, 5.5)
rdw.polygon(px(stage_poly), fill=255)
rdw.polygon(px(thrust), fill=255)
off = (2.2, -1.6)
stroke(cdw, [(x + off[0], y + off[1]) for x, y in stage_poly + stage_poly[:1]], 2.7, rng, amp=0.5)
for side in (-1, 1):
    wx, wy = sx + nx_ * side * 56 - fx * 2, sy + ny_ * side * 56 - fy * 2
    cdw.polygon(px(rect(wx, wy, 5, 5)), fill=255)
FOH_POLY = rect(FOH[0], FOH[1], 8, 8)
stroke(cdw, FOH_POLY + FOH_POLY[:1], 2.7, rng, amp=0.3)
dot(rdw, FOH[0], FOH[1], 2.6)
# the walkway / snake from FOH to the stage barrier
for side in (-1, 1):
    seg = [(FOH[0] + nx_ * side * 4 - fx * 9, FOH[1] + ny_ * side * 4 - fy * 9),
           (sx + nx_ * side * 4 + fx * 26, sy + ny_ * side * 4 + fy * 26)]
    for piece in arclen_split(seg, rng, (8, 16), (4, 7)):
        stroke(cdw, piece, 2.6, rng, amp=0.2)
# barricade arc in front of the stage
barr = [(sx + fx * 24 + nx_ * t, sy + fy * 24 + ny_ * t) for t in range(-60, 61, 4)]
barr = [(x + fx * 0.004 * ((i * 4 - 60) ** 2) * -0.6, y + fy * 0.004 * ((i * 4 - 60) ** 2) * -0.6) for i, (x, y) in enumerate(barr)]
stroke(cdw, barr, 2.7, rng, amp=0.3)
log('stage done')

# ==========================================================================
# SOUND RINGS — the one expressive gesture
# ==========================================================================
rng = random.Random(SEED + 30)
RINGS_K = blank()
RINGS_R = blank()
HALO = blank()
rkd, rrd, hd = ImageDraw.Draw(RINGS_K), ImageDraw.Draw(RINGS_R), ImageDraw.Draw(HALO)
radii = []
r_ = 64.0
while r_ < 1500:
    radii.append(r_)
    r_ = r_ * 1.22 + 26
for k, rad in enumerate(radii):
    c0 = (sx + rng.gauss(0, 3) + fx * 6, sy + rng.gauss(0, 3) + fy * 6)
    ph = [rng.uniform(0, math.tau) for _ in range(3)]
    pts = []
    n = int(rad * 0.9) + 60
    th0 = rng.uniform(0, math.tau)
    for i in range(n + 1):
        th = th0 + i / n * math.tau
        rr = rad * (1 + 0.010 * math.sin(3 * th + ph[0]) + 0.006 * math.sin(7 * th + ph[1])) + 3 * math.sin(2 * th + ph[2])
        pts.append((c0[0] + rr * math.cos(th), c0[1] + rr * math.sin(th)))
    dash = (40 + rad * 0.15, 120 + rad * 0.5)
    gap = (8 + rad * 0.02, 30 + rad * 0.12)
    red = True
    for seg in arclen_split(pts, rng, dash, gap):
        # keep only the parts of the ring that fall on the drawn map
        for piece in thin_path(seg, rng, (60, 160), field=DENS_RING_L, gamma=0.55):
            if len(piece) < 4:
                continue
            w = max(2.8, 4.0 - k * 0.12)
            stroke(hd, piece, w + 4.4, rng, amp=0.0, step=6, wvar=0.0)
            stroke(rrd if red else rkd, piece, w, rng, amp=0.9, step=5, wvar=0.25)
log('rings done')

# ==========================================================================
# GREEN INK — turf, the racing band, lawns, golf, gardens
# ==========================================================================
rng = random.Random(SEED + 40)
# mowing stripes along the long axis (subtle: two grain densities)
stripes = blank()
sd = ImageDraw.Draw(stripes)
ca, sa = a_can
nxs, nys = -sa, ca
for k in range(-40, 41, 2):
    o = k * 24
    c1 = (ic[0] + nxs * o, ic[1] + nys * o)
    q = [(c1[0] - ca * 1500 + nxs * -12, c1[1] - sa * 1500 + nys * -12),
         (c1[0] - ca * 1500 + nxs * 12, c1[1] - sa * 1500 + nys * 12),
         (c1[0] + ca * 1500 + nxs * 12, c1[1] + sa * 1500 + nys * 12),
         (c1[0] + ca * 1500 + nxs * -12, c1[1] + sa * 1500 + nys * -12)]
    sd.polygon(px(q), fill=255)
stripes = stripes.filter(ImageFilter.GaussianBlur(1.5 * R))
infield_turf = SUB(RIN, CROWDZ)
TURF_A = grain(blank(255), rng, density=0.04, starve=0.22)
TURF_B = grain(blank(255), rng, density=0.26, starve=0.22)
TURF = OR(AND(AND(thr(stripes, 128), TURF_A), infield_turf), AND(AND(NOT(thr(stripes, 128)), TURF_B), infield_turf))
# crowd edge: the grass shows between the last people
edge_turf = AND(SUB(dilate(CROWDZ, 0), erode(CROWDZ, int(4 * R))), RIN)
TURF = OR(TURF, AND(edge_turf, grain(blank(255), rng, density=0.6)))
GREEN = TURF
# racing band: dense turf
GREEN = OR(GREEN, grain(TRACK_BAND, rng, density=0.16))
# course grounds outside the track: open green hatch (paddock lawns)
# paddock lawns outside the track: little grass tufts, set by hand
lawn = SUB(SUB(SUB(COURSE, ROUT), dilate(BLD, int(1.5 * R))), ROADS)
tufts = blank()
tfd = ImageDraw.Draw(tufts)
lawn_small = lawn.resize((UW, UH), Image.NEAREST)
for _ in range(26000):
    x, y = rng.uniform(0, UW - 1), rng.uniform(0, UH - 1)
    if not lawn_small.getpixel((int(x), int(y))) or not keep(x, y, rng, gamma=0.7):
        continue
    for k in range(rng.choice((2, 3, 3))):
        a = -math.pi / 2 + (k - 1) * 0.5 + rng.gauss(0, 0.15)
        L = rng.uniform(3.2, 4.6)
        bx = x + (k - 1) * 1.6
        tfd.line([(bx * R, y * R), ((bx + math.cos(a) * L) * R, (y + math.sin(a) * L) * R)], fill=255, width=int(2.6 * R))
GREEN = OR(GREEN, AND(tufts, lawn))
# parks & golf: upright grass hatch + lumpy trees, thinned by density
gh = hatch_field(84, 6.8, 2.7, rng, wav=0.9)
PARK_TEX = AND(SUB(PARKM, COURSE), gh)
trees = blank()
trd = ImageDraw.Draw(trees)
for poly in parks + golf:
    a = poly_area(poly)
    if a < 250:
        continue
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    for _ in range(int(a / 700) + 2):
        x, y = rng.uniform(min(xs), max(xs)), rng.uniform(min(ys), max(ys))
        if not keep(x, y, rng):
            continue
        base = rng.uniform(4.5, 8.5)
        for _ in range(6):
            ox, oy = rng.gauss(0, base * 0.45), rng.gauss(0, base * 0.45)
            dot(trd, x + ox, y + oy, base * rng.uniform(0.5, 0.8))
PARK_TEX = OR(PARK_TEX, AND(trees, SUB(PARKM, COURSE)))
PARK_TEX = SUB(PARK_TEX, ROADS)
# density: parks fade with the map
PARK_TEX = AND(PARK_TEX, thr(ImageChops.subtract(DENS, noise(9, rng, 90), 1, 0), 1))
GREEN = OR(GREEN, PARK_TEX)
# the rain trees that line the racecourse perimeter, and a few along the big roads
TREES = blank()
trd2 = ImageDraw.Draw(TREES)
cc = centroid(course)
perim = densify(course + course[:1], 2.0)
t_ = 0.0
i = 0
while i < len(perim):
    x, y = perim[i]
    dx, dy = x - cc[0], y - cc[1]
    L = math.hypot(dx, dy) or 1
    out_ = rng.uniform(5, 12)
    tx, ty = x + dx / L * out_, y + dy / L * out_
    if keep(tx, ty, rng):
        base = rng.uniform(5.0, 8.0)
        for _ in range(rng.randint(5, 8)):
            ox, oy = rng.gauss(0, base * 0.42), rng.gauss(0, base * 0.42)
            dot(trd2, tx + ox, ty + oy, base * rng.uniform(0.48, 0.72))
    i += int(rng.uniform(6, 11))
TREES = SUB(TREES, SUB(COURSE, dilate(BLD, 0)))   # canopy stays outside the fence
GREEN = OR(GREEN, grain(TREES, rng, density=0.1))
GREEN = SUB(GREEN, dilate(KEY_CROWD, 2))
log('green done')

# ==========================================================================
# BLUE INK — the arabian sea: coastal echoes + wobbly wave hatching
# ==========================================================================
rng = random.Random(SEED + 50)
BLUE = blank()
bdw = ImageDraw.Draw(BLUE)
levels = [116, 98, 82, 68, 56, 45, 36, 28, 21]
sea_lo = NOT(LAND_LO.filter(ImageFilter.MaxFilter(7)))
brk_lo = Image.effect_noise((UW // 22 + 2, UH // 22 + 2), 70).convert('L').resize((UW, UH), Image.BICUBIC)
ybox = SEA.getbbox()
y_max = int(ybox[3] / R) + 2 if ybox else UH
for i, L in enumerate(levels):
    inside = thr(BATH_LO, L)
    edge = AND(SUB(inside, inside.filter(ImageFilter.MinFilter(3))), sea_lo)
    data = edge.crop((0, 0, UW, y_max)).tobytes()
    cut = 92 + i * 8
    wob = 0.6 + i * 0.12
    on = set()
    for idx in range(len(data)):
        if data[idx]:
            x, y = idx % UW, idx // UW
            if brk_lo.getpixel((x, y)) >= cut and keep(x, y, rng, field=DENS_RING_L, gamma=1.4):
                on.add((x, y))

    def P2(x, y):
        return ((x + 0.5 + wob * math.sin(y / 23.0 + i * 1.7)) * R, (y + 0.5 + wob * math.sin(x / 29.0 + i * 2.3)) * R)
    for (x, y) in on:
        X, Y = P2(x, y)
        rr = 1.35 * R
        bdw.ellipse([X - rr, Y - rr, X + rr, Y + rr], fill=255)
        for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
            if (x + dx, y + dy) in on:
                bdw.line([(X, Y), P2(x + dx, y + dy)], fill=255, width=int(2.7 * R))
# wave hatching: wobbly ripples, each dash kept or not by density
waves = blank()
wvd = ImageDraw.Draw(waves)
yy = -40.0
while yy < UH * 0.55:
    lam = rng.uniform(13, 19)
    amp = rng.uniform(1.0, 1.7)
    ph = rng.uniform(0, math.tau)
    tilt = -0.055 + rng.uniform(-0.008, 0.008)
    pts = [(x, yy + x * tilt + amp * math.sin(x / lam * math.tau + ph)) for x in range(-20, UW + 20, 2)]
    for seg in arclen_split(pts, rng, (14, 64), (8, 34)):
        m = seg[len(seg) // 2]
        if keep(m[0], m[1], rng, field=DENS_RING_L, gamma=1.6):
            stroke(wvd, seg, 2.7, rng, amp=0.35, step=2, wvar=0.15)
    yy += rng.uniform(11.0, 14.5)
near_coast = thr(BATH, 40)
BLUE = OR(BLUE, AND(SUB(waves, near_coast), SEA))
# inland water (Love Grove nalla, golf ponds): ripples inside the banks
BLUE = OR(BLUE, AND(WATER, OR(waves, hatch_field(-8, 6.0, 2.7, rng, wav=1.2))))
log('blue done')

# ==========================================================================
# assemble: rings cut a halo through everything they cross
# ==========================================================================
CITY = SUB(CITY, dilate(TREES, int(1.2 * R)))
KEY = OR(OR(CITY, KEY_LINES), OR(KEY_TRACK, KEY_CROWD))
KEY = SUB(KEY, HALO)
KEY = OR(KEY, RINGS_K)
GREEN = SUB(GREEN, HALO)
BLUE = SUB(BLUE, HALO)
redh = dilate(RINGS_R, int(1.5 * R))
GREEN, BLUE, KEY = SUB(GREEN, redh), SUB(BLUE, redh), SUB(KEY, SUB(redh, KEY_CROWD))
RED = OR(RED, RINGS_R)

# a ragged outer edge for anything that still runs toward the canvas rectangle
edge_f = Image.new('L', (DW, DH), 0)
ImageDraw.Draw(edge_f).rectangle([44 * DLR, 44 * DLR, (UW - 44) * DLR, (UH - 44) * DLR], fill=255)
edge_f = edge_f.filter(ImageFilter.GaussianBlur(16 * DLR)).resize((W, H), Image.BICUBIC)
EDGE = thr(ImageChops.subtract(edge_f, Image.blend(noise(5, rng, 80), noise(22, rng, 80), 0.6), 1, 0), 1)
KEY, GREEN, BLUE, RED = AND(KEY, EDGE), AND(GREEN, EDGE), AND(BLUE, EDGE), AND(RED, EDGE)

# print physics: ink spread on the edges, grain in solids, minimum feature clean-up
rng = random.Random(SEED + 60)
inks = {}
for name, m in (('key', KEY), ('green', GREEN), ('blue', BLUE), ('red', RED)):
    m = rough(m, rng)
    if name == 'red':
        m = grain(m, rng, density=0.07)
    m = opening(m, max(3, int(round(1.7 * R)) | 1))
    inks[name] = m
    log('ink', name, 'ready')

# misregistration, px at print resolution
MIS = {'key': (0, 0), 'green': (6, -4), 'blue': (-5, 4), 'red': (4, 7)}


def shifted(m, dx, dy):
    dx, dy = int(round(dx * R / 3)), int(round(dy * R / 3))
    out = blank()
    out.paste(m, (dx, dy))
    return out


safe = blank()
ImageDraw.Draw(safe).rectangle([int(14 * R), int(14 * R), W - int(14 * R), H - int(14 * R)], fill=255)
for k in inks:
    inks[k] = AND(shifted(inks[k], *MIS[k]), safe)

PALETTES = {
    'black': {'tee': '#151515', 'key': '#EFE6CF', 'green': '#6DB98A', 'blue': '#6F9FDB', 'red': '#E4432D',
              'mode': 'knockout'},
    'cream': {'tee': '#ECE3CE', 'key': '#22201D', 'green': '#2F7D52', 'blue': '#2F5FA8', 'red': '#D8381F',
              'mode': 'multiply'},
}


def hex2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def composite(pal):
    if pal['mode'] == 'knockout':
        out = Image.new('RGB', (W, H), (0, 0, 0))
        for k in ('green', 'blue', 'key', 'red'):
            out.paste(hex2rgb(pal[k]), (0, 0, W, H), inks[k])
    else:   # overprint: inks multiply where they cross, like riso on paper
        out = Image.new('RGB', (W, H), (255, 255, 255))
        for k in ('green', 'blue', 'key'):
            layer = Image.new('RGB', (W, H), (255, 255, 255))
            layer.paste(hex2rgb(pal[k]), (0, 0, W, H), inks[k])
            out = ImageChops.multiply(out, layer)
        out.paste(hex2rgb(pal['red']), (0, 0, W, H), inks['red'])
    alpha = inks['green']
    for k in ('blue', 'key', 'red'):
        alpha = OR(alpha, inks[k])
    out.putalpha(alpha)
    return out


for name, pal in PALETTES.items():
    art = composite(pal)
    art.save(os.path.join(HERE, f'art-{name}{SUFFIX}.png'), compress_level=6)
    prev = Image.new('RGB', (W, H), hex2rgb(pal['tee']))
    prev.paste(art, (0, 0), art)
    prev.resize((900, 1200), Image.LANCZOS).save(os.path.join(HERE, f'preview-{name}{SUFFIX}.png'))
    log('saved', name)

# geometry the manifest needs (annotation anchors), in units
anch = {
    'stage': [round(sx), round(sy)], 'foh': [round(FOH[0]), round(FOH[1])],
    'haji_ali': [round(c) for c in centroid(haji)] if haji else None,
    'platforms': [round(c) for c in centroid([centroid(p) for p in platforms])] if platforms else None,
    'track_mid': [round(c) for c in centroid(ring_mid)],
}
json.dump({'palettes': PALETTES, 'anchors': anch, 'type_zones': TYPE_ZONES},
          open(os.path.join(HERE, f'render-info{SUFFIX}.json'), 'w'), indent=1)
log('done', anch)
