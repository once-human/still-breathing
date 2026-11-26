"""lib_r18.py: round 18, after OWNER-REVIEW-2 and REVIEW-2.

- lamps: no rings; light falls as a coarse AM halftone (45 degree grid, dot size follows the light, merging solid at
  the core) in a cone under the head and a pool on the ground, always BEHIND what stands in it
- reflections: one column per light, at the light's own x, as wide as the light, nothing else on the road
- drizzle: one slant (top-left to bottom-right), tapered strokes, only where light is behind it; splashes in puddles
- the sky: one big deep-blue cloud bank in lobed flat masses with woodcut cuts, a few long white beams that light the
  cloud where they hit it, strobe stars on the truss
- the show: a DJ set. one long table of gear in front of a big LED screen with grainy halftone footage, one figure
- the metro: a straight box girder on single T-cap piers, the train on it
- the clock: a real cast-iron post
"""
from kit import *
from lib_life import *
from lib_v3 import *
import lib_v3

RAIN2 = math.pi / 2 - math.radians(13.5)     # the one slant: falling from top-left to bottom-right
PITCH = 12.0                                 # halftone pitch in units (36 px at full res)
POOLS = []                                   # halftone light: dicts(kind, tone, bbox, ink, k)
CONES = []                                   # lamp cones for the drizzle: (poly, tone)
CANOPY = Image.new('L', (W, H), 0)           # every leaf mass outline (so the sky never shows through the leaves)
CD = ImageDraw.Draw(CANOPY)

_lobed = lib_v3.lobed


def lobed_rec(*a, **k):
    out = _lobed(*a, **k)
    if len(out) > 2:
        CD.polygon(P(out), fill=255)
    return out


lib_v3.lobed = lobed_rec


# ============================================================ inverse camera (ground plane, ignoring the small warp)
def ground_of(x, y):
    s = (y - HY) / HC
    if s <= 0.5:
        return None
    zz = FL / s
    z = zz if zz < SQ_Z else SQ_Z + (zz - SQ_Z) / SQ
    return (x - CX) / s, z


# ============================================================ HALFTONE LIGHT
def _arr(img):
    return np.asarray(img)


def _win(arr, x, y, r):
    x0, x1 = max(0, int((x - r) * R)), min(W, int((x + r) * R) + 1)
    y0, y1 = max(0, int((y - r) * R)), min(H, int((y + r) * R) + 1)
    if x0 >= x1 or y0 >= y1:
        return False
    return bool(arr[y0:y1, x0:x1].any())


def dot_r(t, p=PITCH):
    """dot radius for tone t: nothing under tmin; from the smallest printable dot to the largest that keeps a
    printable gap; above tmerge the dots grow into their neighbours and the screen goes solid"""
    tmin, tmerge = 0.13, 0.8
    if t < tmin:
        return 0.0
    rmin = MINW * 0.64
    rmax = (p - MINW * 1.35) / 2 / 1.1
    if t >= tmerge:
        return p * 0.78
    f = (t - tmin) / (tmerge - tmin)
    return rmin + (rmax - rmin) * f ** 0.85


def grid45(bb, p=PITCH):
    x0, y0, x1, y1 = bb
    q = p / math.sqrt(2)
    i0, i1 = int(math.floor((x0 + y0) / (2 * q))) - 1, int(math.ceil((x1 + y1) / (2 * q))) + 1
    j0, j1 = int(math.floor((y0 - x1) / (2 * q))) - 1, int(math.ceil((y1 - x0) / (2 * q))) + 1
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            x, y = (i - j) * q, (i + j) * q
            if x0 <= x <= x1 and y0 <= y <= y1:
                yield x, y


def pool_ground(cx, cz, rxm, rzm, k=1.0, ink='amber', p=PITCH, power=1.6):
    """a pool of light on the wet ground, in world metres (true perspective). Dots only: the biggest just under the
    printable gap at the centre, shrinking to the smallest at the rim (a solid core on the ground reads as a paint blob)"""
    def tone(x, y):
        g = ground_of(x, y)
        if g is None:
            return 0.0
        d = math.hypot((g[0] - cx) / rxm, (g[1] - cz) / rzm)
        return min(0.79, k * max(0.0, 1 - d ** power))
    xa, xb = pr(cx - rxm * 1.05, 0, cz - rzm)[0], pr(cx + rxm * 1.05, 0, cz - rzm)[0]
    ya, yb = pr(cx, 0, cz + rzm * 1.05)[1], pr(cx, 0, cz - rzm * 1.05)[1]
    POOLS.append(dict(kind='ground', tone=tone, bbox=(xa, ya, xb, yb), ink=ink, p=p))


def pool_cone(apex, a0, ground_y, a1, k=1.0, vmax=0.7, ink='amber', p=PITCH, snap=None, dvmax=None):
    """the light in the air under a lamp head: a trapezoid from the lens (half width a0) to the ground (a1)"""
    ax, ay = apex
    Lc = max(1.0, ground_y - ay)
    dv = dvmax or vmax

    def tone(x, y):
        v = (y - ay) / Lc
        if v < 0 or v > dv:
            return 0.0
        half = a0 + (a1 - a0) * v
        lat = abs(x - ax) / half
        if lat >= 1:
            return 0.0
        return k * (1 - v / dv) ** 1.1 * (1 - lat ** 2.2)
    poly = [(ax - a0, ay), (ax + a0, ay), (ax + a1, ground_y), (ax - a1, ground_y)]
    POOLS.append(dict(kind='air', tone=tone, bbox=(ax - a1, ay, ax + a1, ay + Lc * dv), ink=ink, p=p, snap=snap))
    CONES.append((poly, tone, ay, Lc * vmax, snap))


def pool_canopy(cx, cy, rx, ry, k=0.9, ink='amber', p=PITCH):
    """the lamp lights the leaves just above it: dots on the belly of the canopy"""
    def tone(x, y):
        d = math.hypot((x - cx) / rx, (y - cy) / ry)
        return k * max(0.0, 1 - d ** 1.4)
    POOLS.append(dict(kind='canopy', tone=tone, bbox=(cx - rx, cy - ry, cx + rx, cy + ry), ink=ink, p=p))


def pool_tops(poly, tone, bb, ink='amber', p=PITCH):
    """the light landing on the tops of the people standing in a cone: dots on heads and shoulders only"""
    POOLS.append(dict(kind='top', tone=tone, bbox=bb, ink=ink, p=p, poly=poly))


def lay_pools(rng, kinds=None):
    """lay every halftone light. air dots sit behind everything (never on a line or a standing thing), ground dots go
    under everything that stands, canopy dots land only on leaves, top dots only on the tops of people"""
    occ = _arr(OCC)
    used = np.zeros((H, W), dtype=bool)
    for kk in ORDER:
        used |= _arr(A.L[kk]) > 0
    key = _arr(A.L['key']) > 0
    nonamber = np.zeros((H, W), dtype=bool)
    for kk in ORDER:
        if kk != 'amber':
            nonamber |= _arr(A.L[kk]) > 0
    colr = (_arr(A.L['copper']) > 0) | (_arr(A.L['green']) > 0) | (_arr(A.L['ice']) > 0)
    can = _arr(CANOPY) > 0
    n = 0
    for P_ in POOLS:
        p = P_['p']
        kind = P_['kind']
        if kinds is not None and kind not in kinds:
            continue
        for x, y in grid45(P_['bbox'], p):
            t = P_['tone'](x, y)
            r = dot_r(t, p)
            if r <= 0:
                continue
            jx, jy = x + rng.gauss(0, p * 0.05), y + rng.gauss(0, p * 0.05)
            if kind == 'air':
                near = P_.get('_near')
                if near is None:
                    snap = P_.get('snap')
                    near = occ > 0 if snap is None else (occ > 0) & ~(np.asarray(snap) > 0)
                    P_['_near'] = near
                if _win(near, jx, jy, r + MINW * 1.1) or _win(used, jx, jy, r + MINW * 1.1) or \
                        _win(can, jx, jy, r + MINW * 0.6):
                    continue
            elif kind == 'ground':
                if _win(occ, jx, jy, r + MINW * 0.9):
                    continue
                if _win(used, jx, jy, r + MINW * 0.9):
                    continue
            elif kind == 'canopy':
                if not _win(can, jx, jy, 0.5) or _win(key, jx, jy, r + MINW):
                    continue
            elif kind == 'top':
                r = min(r, 3.2)
                iy, ix = min(H - 1, int(jy * R)), min(W - 1, int(jx * R))
                if not colr[iy, ix]:
                    continue
                if occ[max(0, int((jy - 34) * R)), ix]:
                    continue
                if _win(key, jx, jy, r + MINW * 0.75):
                    continue
            dot(jx, jy, r, P_['ink'], rng)
            n += 1
    return n


# ============================================================ LAMPS: a head, and the light below it
def street_lamp4(x, z, rng, h=8.2, arm=1.8, head=1.5, pool=(2.2, 3.0), cone=1.0, canopy=None, kpool=1.0, cw=None,
                 tops=None):
    side = -1 if x < 0 else 1
    hx = x - side * arm
    LAMPS.append((hx, h - 0.3, z))
    s = S(z)
    cwid = cw or clamp(0.5 * s * head * 0.55, 8, 26)
    light(hx, h - 0.3, z, 'amber', wm=0.0, k=1.0, core='key')
    LIGHTS[-1]['cw'] = cwid
    LIGHTS[-1]['skip'] = (pr(hx, 0, z - pool[1] * 0.25)[1] if pool else None)

    def draw():
        g, t = pr(x, 0, z), pr(x, h + 0.15, z)
        w = clamp(0.15 * s, MINW, 6.5)
        knock_line([g, t], w + 3)
        edge(g, t, w, 'key', rng, over=(-0.5, 0.5))
        # a cast collar near the foot and a small bracket under the arm
        for f in (0.06, 0.09):
            p_ = pr(x, h * f, z)
            ln([(p_[0] - w * 1.1, p_[1]), (p_[0] + w * 1.1, p_[1])], MINW, 'key', rng, wob=0.05)
        a0, a1, hd = pr(x, h + 0.1, z), pr(x - side * arm * 0.5, h + 0.5, z), pr(hx, h, z)
        ln([a0, a1, hd], max(MINW, w * 0.8), 'key', rng, wob=0.2)
        br = [pr(x, h - 0.9, z), pr(x - side * arm * 0.35, h + 0.25, z)]
        ln(br, MINW, 'key', rng, wob=0.1)
        hw = clamp(0.55 * s * head * 0.8, 8, 40)
        hh = clamp(0.16 * s * head * 0.8, 4.5, 12)
        cx, cy = hd
        house = [(cx - hw, cy - hh * 0.2), (cx - hw * 0.6, cy - hh), (cx + hw * 0.6, cy - hh), (cx + hw, cy - hh * 0.2),
                 (cx + hw * 0.7, cy + hh * 0.55), (cx - hw * 0.7, cy + hh * 0.55)]
        knock(grow(house, 3.0), 1.0)
        lens = [(cx - hw * 0.86, cy), (cx + hw * 0.86, cy), (cx + hw * 0.6, cy + hh * 1.05), (cx - hw * 0.6, cy + hh * 1.05)]
        fillp(lens, 'amber')
        knock_ell(cx, cy + hh * 0.45, hw * 0.5, hh * 0.42, layers=('amber',))
        A.D['key'].ellipse(((cx - hw * 0.44) * R, (cy + hh * 0.45 - hh * 0.34) * R, (cx + hw * 0.44) * R,
                            (cy + hh * 0.45 + hh * 0.34) * R), fill=255)
        pline(house[:4], max(MINW, w * 0.7), 'key', rng, closed=False)
        if cone and s > 20:
            gy = pr(hx, 0, z)[1]
            a1_ = abs(pr(hx + pool[0] * 0.9, 0, z)[0] - pr(hx, 0, z)[0])
            pool_cone((cx, cy + hh * 1.05), hw * 0.62, gy, a1_, k=min(1.0, cone * 1.25), vmax=0.6, snap=OCC.copy(), dvmax=0.3)
            if canopy:
                pool_canopy(cx + canopy[0], cy - canopy[1], canopy[2], canopy[3], k=0.9)
            if tops:
                for bb in tops:
                    pool_tops(None, lambda xx, yy, ap=(cx, cy), gy=gy, a1=a1_: 1.0 if abs(xx - ap[0]) <
                              a1 * (yy - ap[1]) / max(1, gy - ap[1]) + hw else 0.0, bb)
        if pool:
            pool_ground(hx, z - pool[1] * 0.15, pool[0], pool[1], k=kpool)
    return draw


def lamp_pool_only(x, z, rxm, rzm, k=0.8):
    pool_ground(x, z, rxm, rzm, k=k)


# ============================================================ REFLECTIONS: one column per light, under it, its width
def column(x, y0, y1, w0, w1, ink, rng, core=None, k=1.0, ymax=1458, brk=0.14, art=None, th0=None):
    """stacked tapered horizontal strokes into one broken vertical column, as wide as its light, widening a little
    toward the viewer, wobbling and breaking up as it comes"""
    art = art or RA
    y = y0 + rng.uniform(0, 3)
    ph, ph2 = rng.uniform(0, TAU), rng.uniform(0, TAU)
    yend = min(y1, ymax)
    span = max(1.0, yend - y0)
    while y < yend:
        t = (y - y0) / span
        wd = w0 + (w1 - w0) * t
        th = (th0 or clamp(0.13 * wd, MINW, 5.6)) * rng.uniform(0.9, 1.2) * (1 - 0.18 * t)
        th = max(MINW, th)
        prof = smooth(min(1.0, t * 6 + 0.35))
        hl = wd * 0.5 * prof * rng.uniform(0.55, 1.05) * k
        cx = x + wd * 0.16 * (0.6 * math.sin(y * 0.05 + ph) + 0.4 * math.sin(y * 0.13 + ph2)) + rng.gauss(0, wd * 0.05)
        if rng.random() > brk + 0.5 * t * t and hl > th * 0.85:
            pts = [(cx - hl, y + rng.gauss(0, 0.4)), (cx + rng.uniform(-0.15, 0.15) * hl, y + rng.gauss(0, th * 0.25)),
                   (cx + hl, y + rng.gauss(0, 0.4))]
            art.line(pts, th, layer=ink, rng=rng, wob=0.3, trem=0.15, a0=1.4, a1=2.4, pv=0.3)
            if core and t < 0.5 and rng.random() < 0.5 and hl * 0.42 > MINW:
                c = rng.uniform(-0.15, 0.15) * hl
                art.line([(cx + c - hl * 0.38, y + 0.3), (cx + c + hl * 0.38, y - 0.3)], max(MINW, th * 0.8), layer=core,
                         rng=rng, wob=0.2, trem=0.1, a0=1.2, a1=2.0, pv=0.2)
        y += (th + MINW * 1.9) * rng.uniform(1.0, 1.3) * (1 + 0.9 * t * t)


def reflect_anchored(lights, rng, ymax=1458):
    n = 0
    for L in lights:
        if L.get('norefl'):
            continue
        gx, gy = pr(L['x'], 0, L['z'])
        my = pr(L['x'], -L['h'], L['z'])[1]
        if gy > ymax - 10:
            continue
        w0 = L.get('cw') or clamp(L['wm'] * S(L['z']), 6.0, 80.0)
        w1 = L.get('cw1') or w0 * 1.35
        length = (my - gy) * rng.uniform(1.35, 1.8) * min(1.8, L.get('stretch', 1.0)) + w0
        length = max(length, (ymax - gy) * L.get("reach", 0.24) * rng.uniform(0.85, 1.15))
        if L.get('y1'):
            length = L['y1'] - gy
        y0 = L.get('skip') or gy + clamp(0.06 * S(L['z']), 1.0, 8.0)
        core = L.get('core') if w0 > 12 else None
        column(gx, y0, gy + length, w0, w1, L['ink'], rng, core=core, k=L['k'] if L['k'] < 1 else 1.0, ymax=ymax,
               brk=L.get('brk', 0.14))
        n += 1
    return n


# ============================================================ DRIZZLE: one slant, tapered, only in the light
def rain_stroke(x, y, l, ink, rng, art=None, w=None):
    art = art or A
    ux, uy = math.cos(RAIN2), math.sin(RAIN2)
    art.line([(x, y), (x + ux * l * 0.5, y + uy * l * 0.5), (x + ux * l, y + uy * l)], w or MINW * 1.12, layer=ink,
             rng=rng, wob=0.0, trem=0.0, a0=1.3, a1=1.6, pv=0.0)


def drizzle_in(poly, tone, ink, rng, sp=22.0, L=(9, 22), prob=1.0, ok=None, snap=None):
    """rain on a scratch layer, kept only on black (never on a trunk, a leaf, a line), so it reads only where light
    is behind it"""
    tmp = Image.new('L', (W, H), 0)
    keep_L, keep_D = A.L[ink], A.D[ink]
    A.L[ink], A.D[ink] = tmp, ImageDraw.Draw(tmp)
    try:
        x0, y0, x1, y1 = bbox(poly)
        ux, uy = math.cos(RAIN2), math.sin(RAIN2)
        placed = {}
        cell = 30.0
        n_try = int((x1 - x0) * (y1 - y0) / (sp * sp) * 3.0) + 1
        for _ in range(n_try):
            px, py = rng.uniform(x0, x1), rng.uniform(y0, y1)
            if not pip(px, py, poly):
                continue
            f = tone(px, py) if tone else 1.0
            if rng.random() >= f * prob or (ok is not None and not ok(px, py)):
                continue
            l = rng.uniform(*L) * (0.6 + 0.4 * min(1, f * 1.5))
            mx, my = px + ux * l / 2, py + uy * l / 2
            gx, gy = int(mx // cell), int(my // cell)
            clash = False
            for ix in range(gx - 2, gx + 3):
                for iy in range(gy - 2, gy + 3):
                    for (qx, qy, ql) in placed.get((ix, iy), ()):
                        dx, dy = mx - qx, my - qy
                        along = abs(dx * ux + dy * uy)
                        perp = abs(-dx * uy + dy * ux)
                        if perp < sp * 0.62 and along < (l + ql) / 2 + sp * 0.9:
                            clash = True
                            break
                    if clash:
                        break
                if clash:
                    break
            if clash:
                continue
            placed.setdefault((gx, gy), []).append((mx, my, l))
            rain_stroke(px, py, l, ink, rng)
    finally:
        A.L[ink], A.D[ink] = keep_L, keep_D
    bx0, by0, bx1, by1 = [int(v * R) for v in bbox(poly)]
    bx0, by0 = max(0, bx0 - 60), max(0, by0 - 60)
    bx1, by1 = min(W, bx1 + 60), min(H, by1 + 60)
    box = (bx0, by0, bx1, by1)
    used = Image.new('L', (bx1 - bx0, by1 - by0), 0)
    for k in ORDER:
        used = ImageChops.lighter(used, A.L[k].crop(box))
    if snap is not None:
        used = ImageChops.lighter(used, ImageChops.subtract(OCC.crop(box), snap.crop(box)))
    else:
        used = ImageChops.lighter(used, OCC.crop(box))
    used = ImageChops.lighter(used, CANOPY.crop(box))
    used = used.filter(ImageFilter.MaxFilter(max(3, int(2.6 * R) | 1)))
    piece = ImageChops.multiply(tmp.crop(box), ImageChops.invert(used))
    A.L[ink].paste(255, box, piece)


def drizzle_cones(rng):
    for poly, tone, ay, Lc, snap in CONES:
        gy = poly[2][1]
        def tf(px, py, poly=poly, ay=ay, gy=gy):
            v = (py - ay) / max(1.0, gy - ay)
            half = (poly[1][0] - poly[0][0]) / 2 + ((poly[2][0] - poly[3][0]) / 2 - (poly[1][0] - poly[0][0]) / 2) * v
            lat = abs(px - (poly[0][0] + poly[1][0]) / 2) / max(1.0, half)
            ramp = clamp((v - 0.46) / 0.14, 0, 1) * clamp(1.0 - 0.9 * (v - 0.6), 0, 1)
            return ramp * clamp((1.0 - lat) * 3, 0, 1) if v < 0.96 else 0.0
        drizzle_in(poly, tf, 'amber', rng, sp=17.0, L=(10, 22), prob=0.95, snap=snap)


def drizzle_glass(poly, rng, sp=24.0, L=(10, 20)):
    """rain in front of lit glass: cream strokes over the amber, never touching a line"""
    am = (_arr(A.L['amber']) > 0) | (_arr(A.L['copper']) > 0)
    ky = _arr(A.L['key']) > 0
    x0, y0, x1, y1 = bbox(poly)
    y = y0 + rng.uniform(0, sp)
    row = 0
    ux, uy = math.cos(RAIN2), math.sin(RAIN2)
    while y < y1:
        x = x0 + (sp * 0.5 if row % 2 else 0)
        while x < x1:
            px, py = x + rng.gauss(0, 4), y + rng.gauss(0, 4)
            l = rng.uniform(*L)
            ex, ey = px + ux * l, py + uy * l
            if pip(px, py, poly) and pip(ex, ey, poly) and rng.random() < 0.7:
                mx, my = (px + ex) / 2, (py + ey) / 2
                if all(am[min(H - 1, int(qy * R)), min(W - 1, int(qx * R))] for qx, qy in ((px, py), (mx, my), (ex, ey))) \
                        and not _win(ky, mx, my, l * 0.38 + MINW * 1.0):
                    rain_stroke(px, py, l, 'key', rng)
            x += sp * rng.uniform(0.9, 1.2)
        y += sp * rng.uniform(0.85, 1.05)
        row += 1


def splash(x, y, s, ink, rng, art=None):
    """a drop landing in a puddle: one short flat dash where it hits, and a crown of three ticks thrown up and out
    above it, each tick clear of the others (no ring: a ring reads as a halo)"""
    art = art or RA
    rx = clamp(0.12 * s, 9, 14)
    art.line([(x - rx, y + 0.4), (x, y + rng.gauss(0, 0.3)), (x + rx, y - 0.4)], MINW * 1.15, layer=ink, rng=rng,
             wob=0.05, trem=0.0, a0=1.4, a1=2.4, pv=0.1)
    base_y = y - MINW * 2.3
    for a, Lk, dx in ((-0.8, 0.8, -0.62), (0.0, 1.0, 0.0), (0.78, 0.78, 0.62)):
        l = clamp(0.11 * s, 10, 15) * Lk * rng.uniform(0.92, 1.08)
        bx = x + dx * rx * 0.75
        ux, uy = math.sin(a), -math.cos(a)
        by = base_y - (0 if dx == 0 else -MINW * 0.4)
        art.line([(bx, by), (bx + ux * l * 0.5, by + uy * l * 0.5), (bx + ux * l, by + uy * l)], MINW * 1.1,
                 layer=ink, rng=rng, wob=0.03, trem=0.0, a0=2.2, a1=0.7, pv=0.05)


# ============================================================ THE SKY: a big deep-blue cloud bank, white beams
def _lobe_mask(lobes, base, draw):
    """a cumulus mass: circles along its top, a flat body down to a wavy base"""
    for cx, cy, r in lobes:
        draw.ellipse(((cx - r) * R, (cy - r * 0.86) * R, (cx + r) * R, (cy + r * 0.86) * R), fill=255)
    xs = [l[0] for l in lobes]
    x0, x1 = min(xs) - lobes[0][2] * 0.6, max(xs) + lobes[-1][2] * 0.6
    ytop = max(l[1] for l in lobes)
    body = [(x0, ytop)] + [(x0 + (x1 - x0) * i / 24, base + 4 * math.sin(i * 0.9) + 2 * math.sin(i * 2.3))
                           for i in range(25)][::-1]
    body = [(x0, ytop), (x1, ytop)] + [(x0 + (x1 - x0) * i / 24, base + 4 * math.sin(i * 0.9) + 2 * math.sin(i * 2.3))
                                       for i in range(24, -1, -1)]
    draw.polygon(P(body), fill=255)


def cloud_bank(masses, rng, beams, ymin=246):
    """the cloud bank drawn into scratch layers (blue, ice, key) for the sky pass: flat deep-blue lobed masses, far to
    near, each cut from the ones behind by a black woodcut gouge; black cuts under the lobes inside each mass; a
    broken cream rim along each lit belly, a few ice hatch strokes where the city lights it from below; where a beam
    hits a belly, a flat ice patch"""
    T = {k: Image.new('L', (W, H), 0) for k in ('blue', 'ice', 'key')}
    D = {k: ImageDraw.Draw(v) for k, v in T.items()}
    masks = []
    for lobes, base in masses:
        m = Image.new('L', (W, H), 0)
        _lobe_mask(lobes, base, ImageDraw.Draw(m))
        masks.append((m, lobes, base))
    # far to near: each nearer mass cuts a black gouge round itself out of what's behind
    for i, (m, lobes, base) in enumerate(masses_sorted := sorted(masks, key=lambda t: t[2])):
        g = m.filter(ImageFilter.MaxFilter(max(3, int(MINW * 1.25 * R) | 1)))
        for k in T:
            T[k].paste(0, (0, 0), g)
        T['blue'].paste(255, (0, 0), m)
        # gouges under the upper lobes inside the mass (the bellies of the cumulus)
        for cx, cy, r in lobes:
            if rng.random() < 0.75:
                a0, a1 = rng.uniform(0.35, 0.6), math.pi - rng.uniform(0.35, 0.6)
                arc = ell(cx, cy, r * 0.97, r * 0.84, n=14, a0=a0, a1=a1, rng=rng)
                arc = [p for p in arc if p[1] < base - MINW * 2.5]
                if len(arc) > 3:
                    pp = A.hand(arc, wob=0.2, trem=0.1, rng=rng)
                    _ink(D['blue'], pp, MINW * 1.15, 0, rng)
        # broken cream rim on the lit belly and ice hatch strokes just above it
        x0 = min(l[0] - l[2] * 0.6 for l in lobes)
        x1 = max(l[0] + l[2] * 0.6 for l in lobes)
        bl = [(x0 + (x1 - x0) * j / 60, base + 4 * math.sin(j * 0.9 * 24 / 60) + 2 * math.sin(j * 2.3 * 24 / 60) + 0.5)
              for j in range(61)]
        j = rng.randint(0, 4)
        while j < len(bl) - 3:
            Ls = rng.randint(4, 10)
            if rng.random() < 0.62:
                seg = bl[j:j + Ls]
                _ink(D['blue'], A.hand([(p[0], p[1] - 0.5) for p in seg], wob=0.1, trem=0.05, rng=rng), MINW * 2.6, 0, rng)
                _ink(D['key'], A.hand([(p[0], p[1] - 0.6) for p in seg], wob=0.15, trem=0.1, rng=rng), MINW * 1.1, 255, rng)
            j += Ls + rng.randint(2, 6)
        yy = base - MINW * 3.2
        for row in range(2):
            xx = x0 + rng.uniform(10, 30)
            while xx < x1 - 30:
                Ls = rng.uniform(16, 38)
                if rng.random() < 0.45 - 0.15 * row:
                    seg = [(xx, yy - row * MINW * 2.4), (xx + Ls / 2, yy - row * MINW * 2.4 + rng.gauss(0, 0.6)),
                           (xx + Ls, yy - row * MINW * 2.4)]
                    _ink(D['blue'], A.hand(seg, wob=0.1, trem=0.05, rng=rng), MINW * 2.6, 0, rng)
                    _ink(D['ice'], A.hand(seg, wob=0.1, trem=0.05, rng=rng), MINW * 1.05, 255, rng)
                xx += Ls + rng.uniform(14, 40)
    return T


def _ink(draw, pts, w, fill, rng):
    """render a hand path straight into a scratch draw (the Art pen, with taper)"""
    keep = A.D.get('_tmp')
    A.D['_tmp'] = draw
    try:
        A._render(pts, w, '_tmp', 1.2, 2.0, 0.15, rng, erase=(fill == 0))
    finally:
        if keep is None:
            del A.D['_tmp']
        else:
            A.D['_tmp'] = keep


def beam3(T, root, ang, top_y, wend, rng, ink='ice', hit=None, n=4):
    """a long thin white beam: a few strokes converging on the head, heavier near it, breaking into dashes as it climbs
    and fading out before top_y; each stroke carves a narrow black slot through the cloud. hit = (t, w, h): a flat
    lit patch where the beam hits a cloud belly"""
    ux, uy = math.sin(ang), -math.cos(ang)
    nx, ny = -uy, ux
    L = (root[1] - top_y) / max(0.2, math.cos(ang))
    end = (root[0] + ux * L, root[1] + uy * L)
    D = {k: ImageDraw.Draw(v) for k, v in T.items()}
    fs = [-1.0, -0.33, 0.33, 1.0][:n] if n == 4 else [-1.0, 0.0, 1.0]
    for f in fs:
        tip = (end[0] + nx * wend * f, end[1] + ny * wend * f)
        t0, t1 = 0.0, rng.uniform(0.32, 0.45) * (1.25 if abs(f) < 0.5 else 1.0)
        while t0 < 0.97:
            a, b = lerp(root, tip, t0), lerp(root, tip, min(0.97, t1))
            w = MINW * max(1.0, (1.55 if abs(f) < 0.5 else 1.3) - 0.9 * t0)
            pp = A.hand([a, lerp(a, b, 0.5), b], wob=0.05, trem=0.05, rng=rng)
            _ink(D['blue'], pp, w + MINW * 1.6, 0, rng)
            _ink(D[ink if (abs(f) > 0.5 or t0 > 0.3) else 'key'], pp, w, 255, rng)
            t0 = t1 + rng.uniform(0.04, 0.08) * (1 + 2.2 * t1)
            t1 = t0 + rng.uniform(0.08, 0.16) * (1.25 - t0)
    poly = [(root[0] + nx * 2, root[1] + ny * 2), (end[0] + nx * wend, end[1] + ny * wend),
            (end[0] - nx * wend, end[1] - ny * wend), (root[0] - nx * 2, root[1] - ny * 2)]
    if hit:
        t, hw, hh = hit
        c = lerp(root, end, t)
        wd = wend * t * 1.0 + 3
        pts = []
        for i in range(20):
            a_ = TAU * i / 20
            rr = 1 + 0.12 * math.sin(3 * a_ + rng.uniform(0, 1))
            pts.append((c[0] + math.cos(a_) * (wd * hw) * rr, c[1] + math.sin(a_) * hh * rr * (0.75 if math.sin(a_) < 0 else 1.0)))
        D['ice'].polygon(P(pts), fill=255)
        D['blue'].polygon(P(grow(pts, MINW * 1.3)), fill=0)
    return poly


def strobe_star(T, x, y, rng, n=7, r0=4.0, r1=(11, 20)):
    D = ImageDraw.Draw(T['key'])
    Db = ImageDraw.Draw(T['blue'])
    D.ellipse(((x - 3.6) * R, (y - 3.2) * R, (x + 3.6) * R, (y + 3.2) * R), fill=255)
    a = rng.uniform(0, TAU)
    for i in range(n):
        aa = a + TAU * i / n + rng.uniform(-0.12, 0.12)
        l = rng.uniform(*r1) * (1.3 if i % 3 == 0 else 1.0)
        p0 = (x + math.cos(aa) * r0, y + math.sin(aa) * r0)
        p1 = (x + math.cos(aa) * (r0 + l), y + math.sin(aa) * (r0 + l))
        pp = A.hand([p0, lerp(p0, p1, 0.5), p1], wob=0.03, trem=0.0, rng=rng)
        _ink(Db, pp, MINW * 2.8, 0, rng)
        keep = A.D.get('_tmp')
        A.D['_tmp'] = D
        A._render(pp, MINW * 1.25, '_tmp', 0.4, 2.6, 0.05, rng)
        del A.D['_tmp']


def sky_drizzle(T, polys, rng, sp=20.0):
    """drizzle inside the beams (ice), on black only"""
    D = ImageDraw.Draw(T['ice'])
    for poly, root, L in polys:
        x0, y0, x1, y1 = bbox(poly)
        y = y0 + rng.uniform(0, sp)
        row = 0
        while y < y1:
            x = x0 + (sp * 0.5 if row % 2 else 0)
            while x < x1:
                px, py = x + rng.gauss(0, 4), y + rng.gauss(0, 4)
                if pip(px, py, poly):
                    d = math.hypot(px - root[0], py - root[1]) / L
                    if rng.random() < 0.9 * (1 - d) and d > 0.06:
                        l = rng.uniform(9, 18)
                        ux, uy = math.cos(RAIN2), math.sin(RAIN2)
                        pp = A.hand([(px, py), (px + ux * l / 2, py + uy * l / 2), (px + ux * l, py + uy * l)], wob=0.05,
                                    trem=0.0, rng=rng)
                        A.D['_tmp'] = D
                        A._render(pp, MINW * 1.1, '_tmp', 1.3, 1.6, 0.05, rng)
                        del A.D['_tmp']
                x += sp * rng.uniform(0.9, 1.2)
            y += sp * rng.uniform(0.8, 1.0)
            row += 1


def lay_sky(T, rng, region=None, gap_u=6.5, drz=None):
    """the sky goes in last: only on black that nothing else claims (ink, standing things, leaves), with a black gap
    of gap_u round all of it, so every leaf edge, the train and the stage roof stand clear of the cloud"""
    sc = 3 if R >= 2.5 else 1
    small = (W // sc, H // sc)
    claim = Image.new('L', (W, H), 0)
    for k in ORDER:
        claim = ImageChops.lighter(claim, A.L[k])
    claim = ImageChops.lighter(claim, OCC)
    claim = ImageChops.lighter(claim, CANOPY)
    cs = claim.resize(small, Image.BOX).point(lambda v: 255 if v > 0 else 0)
    k_ = int(gap_u * R / sc) * 2 + 1
    cs = cs.filter(ImageFilter.MaxFilter(k_ if k_ % 2 else k_ + 1))
    allow = ImageChops.invert(cs.resize((W, H), Image.NEAREST))
    if region is not None:
        allow = ImageChops.multiply(allow, region)
    # drizzle only on black inside the sky scratch (not on the cloud, not on the beam strokes)
    if drz:
        occ_sky = ImageChops.lighter(ImageChops.lighter(T['blue'], T['ice']), T['key'])
        tmp = {'ice': Image.new('L', (W, H), 0)}
        sky_drizzle(tmp, drz, rng)
        used = occ_sky.resize(small, Image.BOX).point(lambda v: 255 if v > 0 else 0)
        used = used.filter(ImageFilter.MaxFilter(int(2.4 * R / sc) * 2 + 1)).resize((W, H), Image.NEAREST)
        T['ice'] = ImageChops.lighter(T['ice'], ImageChops.multiply(tmp['ice'], ImageChops.invert(used)))
    for k, im in T.items():
        piece = ImageChops.multiply(im, allow)
        A.L[k].paste(255, (0, 0), piece)


# ============================================================ THE SHOW: a DJ set, in screen units
def stage_dj(rng, X0=416.0, X1=708.0, YR=398.0, YD=562.0):
    """the stage at NICE Grounds as Fred again.. plays it: a pale flat sheet roof on a scaffold truss with straight legs,
    a line array hanging each side, one big LED screen with his grainy phone footage, and in front of it, alone, one
    long table of gear with one figure bent over it, one hand on a knob, one hand up. Returns the truss y and x span."""
    xc = (X0 + X1) / 2
    # the whole block knocks what's behind
    knock([(X0 - 6, YR - 10), (X1 + 6, YR - 10), (X1 + 6, YD + 16), (X0 - 6, YD + 16)], 0.8)
    # --- the LED screen: the biggest light in the picture
    sx0, sx1, sy0, sy1 = X0 + 58, X1 - 58, YR + 36, YD - 10
    scr = [(sx0, sy0), (sx1, sy0), (sx1, sy1), (sx0, sy1)]
    fillp(scr, 'ice')
    footage_face(sx0, sy0, sx1, sy1, rng)
    pline(scr, MINW * 1.2, 'key', rng, skip=0.0, over=(-0.5, 1.5))
    # --- the truss: two chords and a zig-zag under the roof, straight legs to the deck
    ty0, ty1 = YR + 12, YR + 25
    ln([(X0, ty0), (X1, ty0)], MINW * 1.2, 'key', rng, wob=0.05)
    ln([(X0, ty1), (X1, ty1)], MINW * 1.2, 'key', rng, wob=0.05)
    n = 22
    for i in range(n):
        a_ = (X0 + (X1 - X0) * i / n, ty1)
        b_ = (X0 + (X1 - X0) * (i + 0.5) / n, ty0)
        c_ = (X0 + (X1 - X0) * (i + 1) / n, ty1)
        ln([a_, b_, c_], MINW, 'key', rng, wob=0.03, a0=0.5, a1=0.8)
    for lx in (X0 + 4, X1 - 4):
        for dx in (-5.5, 5.5):
            ln([(lx + dx, ty0), (lx + dx, YD + 14)], MINW * 1.15, 'key', rng, wob=0.04)
        y_ = ty1 + 6
        k_ = 0
        while y_ < YD + 8:
            ln([(lx - 5.5, y_), (lx + 5.5, y_ + 10)], MINW, 'key', rng, wob=0.03, a0=0.5, a1=0.8)
            y_ += 16
            k_ += 1
    # --- the roof: a pale flat sheet, one gently sagging key line along its belly
    sag = [(X0 - 10 + (X1 - X0 + 20) * i / 20, YR + 8 + 3.5 * math.sin(math.pi * i / 20)) for i in range(21)]
    roof = [(X0 - 6, YR - 4), (xc, YR - 9), (X1 + 6, YR - 4)] + sag[::-1]
    roof = [(X0 - 6, YR - 4), (xc - 60, YR - 7), (xc, YR - 8), (xc + 60, YR - 7), (X1 + 6, YR - 4)] + sag[::-1]
    knock(roof, 1.0)
    blob(roof, 'ice', rng, gap=0.0, shift=0.4, jit=0.006)
    # seams of the sheet: carved
    for f in (0.22, 0.5, 0.78):
        xs_ = X0 + (X1 - X0) * f + rng.uniform(-6, 6)
        knock_line([(xs_ - 2, YR - 5), (xs_ + 2, YR + 8)], MINW, layers=('ice',))
    ln(sag, MINW * 1.4, 'key', rng, wob=0.08)
    ln([(X0 - 6, YR - 4), (xc - 60, YR - 7), (xc, YR - 8), (xc + 60, YR - 7), (X1 + 6, YR - 4)], MINW * 1.2, 'key', rng, wob=0.08)
    # --- line arrays, stacked trapezoid boxes, a J curve, hanging from the truss each side of the screen
    for sgn in (-1, 1):
        x_ = (X0 + 30) if sgn < 0 else (X1 - 30)
        y_ = ty1 + 3
        ln([(x_, ty1), (x_, y_)], MINW, 'key', rng)
        for i in range(9):
            hb = 7.6
            tilt = sgn * (0.0 if i < 5 else (i - 4) * 1.4)
            wt, wb = 17.0 - i * 0.2, 15.0 - i * 0.2
            box = [(x_ - wt / 2 + tilt * 0.3, y_), (x_ + wt / 2 + tilt * 0.3, y_), (x_ + wb / 2 + tilt, y_ + hb),
                   (x_ - wb / 2 + tilt, y_ + hb)]
            knock(box, 0.6)
            pline(box, MINW, 'key', rng, over=(-0.3, 0.6))
            y_ += hb + 0.6
    # --- the stage deck: a lit front edge, black face
    ln([(X0 + 14, YD), (X1 - 14, YD)], MINW * 1.5, 'key', rng, wob=0.05)
    ln([(X0 + 18, YD + 13), (X1 - 18, YD + 13)], MINW, 'key', rng, wob=0.05)
    # --- the DJ: a long table of gear and one figure, a black silhouette cut out of the screen
    tw = 104.0
    tx0, tx1 = xc - tw / 2, xc + tw / 2
    ttop = sy1 - 21
    sil = []
    table = [(tx0, ttop), (tx1, ttop), (tx1 - 2, YD), (tx0 + 2, YD)]
    sil.append(table)
    # gear on the table: two decks, the mixer box between, the pad grid, the open laptop lid
    jogs = [(tx0 + 17, ttop), (tx1 - 17, ttop)]
    mixer = [(xc - 9, ttop), (xc - 9, ttop - 6), (xc + 9, ttop - 6), (xc + 9, ttop)]
    lap = [(xc + 18, ttop), (xc + 24, ttop - 15), (xc + 41, ttop - 13), (xc + 37, ttop)]
    pads = [(tx0 + 32, ttop), (tx0 + 32, ttop - 4), (tx0 + 44, ttop - 4), (tx0 + 44, ttop)]
    deckb = [[(jx - 12, ttop), (jx - 12, ttop - 4.5), (jx + 12, ttop - 4.5), (jx + 12, ttop)] for jx, _ in jogs]
    sil += [mixer, lap, pads] + deckb
    # the figure: behind the table, bent over the gear, head bowed, one hand on a knob, one hand up
    fx = xc - 6
    hip = (fx, ttop + 2)
    sh = (fx + 2, ttop - 25)
    head = (fx + 7, ttop - 32)
    body = [(fx - 9, ttop + 1), (fx - 10, ttop - 14), (fx - 7, ttop - 24), (fx + 3, ttop - 28), (fx + 11, ttop - 25),
            (fx + 10, ttop - 12), (fx + 8, ttop + 1)]
    sil.append(body)
    hd = ell(head[0], head[1], 5.4, 6.0, n=16, rot=0.5)
    sil.append(hd)
    # arm down to a knob on the mixer
    arm1 = [(fx + 8, ttop - 22), (fx + 14, ttop - 13), (xc + 3, ttop - 7)]
    # the other arm up
    arm2 = [(fx - 6, ttop - 24), (fx - 13, ttop - 39), (fx - 10, ttop - 55)]
    knock_margin = MINW * 1.4
    for poly in sil:
        knock(grow(poly, knock_margin), 0, layers=('ice',))
    for a in (arm1, arm2):
        knock_line(a, 6.5 + knock_margin * 2, layers=('ice',))
    knock_ell(arm2[-1][0], arm2[-1][1] - 1.5, 3.6 + knock_margin, 4.4 + knock_margin, layers=('ice',))
    knock_ell(arm1[-1][0], arm1[-1][1], 3.2 + knock_margin, 3.0 + knock_margin, layers=('ice',))
    # key-line highlights picking out the gear: the table's top edge, the jog wheels, the laptop lid, the mixer
    ln([(tx0 + 1, ttop + 0.5), (tx1 - 1, ttop + 0.5)], MINW, 'key', rng, wob=0.02)
    for jx, jy in jogs:
        ln(ell(jx, jy - 4.5, 9.5, 2.6, n=12, a0=math.pi * 1.05, a1=math.pi * 1.95, rng=rng), MINW, 'key', rng, wob=0.02)
    ln([lap[1], lap[2]], MINW, 'key', rng, wob=0.02)
    ln([(mixer[1][0] + 1, mixer[1][1]), (mixer[2][0] - 1, mixer[2][1])], MINW, 'key', rng, wob=0.02)
    # a rim of screen light on his raised hand and his bowed head
    ln([(arm2[1][0] - 2.5, arm2[1][1]), (arm2[2][0] - 2.0, arm2[2][1] + 2)], MINW, 'key', rng, wob=0.03)
    ln(ell(head[0], head[1], 6.6, 7.2, n=8, a0=math.pi * 1.15, a1=math.pi * 1.75, rot=0.5, rng=rng), MINW, 'key', rng, wob=0.03)
    # the show's light on the road: one column under the screen
    return dict(truss=(X0, X1, ty0), screen=(sx0, sy0, sx1, sy1), xc=xc)


def footage_face(x0, y0, x1, y1, rng, p=8.6):
    """grainy lo-fi phone footage on the screen: a blown-up face in profile looking left toward the decks, in coarse
    halftone (black dots knocked out of the white), merging to solid black in the shadow; a little grain elsewhere"""
    wq, hq = x1 - x0, y1 - y0
    sc = 2
    mw, mh = int(wq * sc) + 2, int(hq * sc) + 2
    m = Image.new('L', (mw, mh), 0)
    d = ImageDraw.Draw(m)
    # profile (u right, v down) on the right of the screen, facing left
    prof = [(0.66, 0.0), (0.64, 0.14), (0.66, 0.26), (0.655, 0.33), (0.6, 0.49), (0.6, 0.52), (0.645, 0.56),
            (0.635, 0.6), (0.65, 0.63), (0.637, 0.67), (0.655, 0.71), (0.655, 0.8), (0.7, 0.9), (0.74, 1.0),
            (1.0, 1.0), (1.0, 0.0)]
    d.polygon([(u * wq * sc, v * hq * sc) for u, v in prof], fill=255)
    # the eye and the ear as light spots in the dark
    d.ellipse(((0.8 * wq - 4) * sc, (0.42 * hq - 4) * sc, (0.8 * wq + 4) * sc, (0.42 * hq + 4) * sc), fill=90)
    d.ellipse(((0.69 * wq - 3.5) * sc, (0.31 * hq - 2) * sc, (0.69 * wq + 4) * sc, (0.31 * hq + 2) * sc), fill=70)
    # two raised hands in the crowd on the left, small
    for hx_, top in ((0.12, 0.55), (0.25, 0.68)):
        d.polygon([((hx_ - 0.035) * wq * sc, hq * sc), ((hx_ - 0.03) * wq * sc, top * hq * sc),
                   ((hx_ + 0.03) * wq * sc, (top - 0.02) * hq * sc), ((hx_ + 0.035) * wq * sc, hq * sc)], fill=200)
        d.ellipse(((hx_ - 0.045) * wq * sc, (top - 0.16) * hq * sc, (hx_ + 0.045) * wq * sc, (top + 0.02) * hq * sc), fill=200)
    tone = np.asarray(m.filter(ImageFilter.GaussianBlur(5 * sc)), dtype=np.float32) / 255.0
    rmin = MINW * 0.6
    rmax = (p - MINW * 1.3) / 2
    q = p / math.sqrt(2)
    for x, y in grid45((x0 + 2, y0 + 2, x1 - 2, y1 - 2), p):
        u, v = int((x - x0) * sc), int((y - y0) * sc)
        t = float(tone[min(mh - 1, v), min(mw - 1, u)])
        t = t * 0.95 + 0.11 * rng.random()        # the grain of a phone camera in the dark
        if t < 0.2:
            continue
        r = p * 0.78 if t > 0.78 else rmin + (rmax - rmin) * (t - 0.2) / 0.58
        jx, jy = x + rng.gauss(0, 0.5), y + rng.gauss(0, 0.5)
        knock_ell(jx, jy, r, r, layers=('ice',))
    # two scan lines across it
    for f in (0.33, 0.71):
        yy = y0 + hq * f
        knock_line([(x0 + rng.uniform(4, 30), yy), (x1 - rng.uniform(4, 40), yy)], MINW, layers=('ice',))


def crowd_dj(rng, xa, xb, y_top, y_bot):
    """the crowd in front of the stage: a dark band of heads with raised hands and a few phones, rimmed in ice by the
    stage"""
    knock([(xa, y_top - 22), (xb, y_top - 22), (xb, y_bot + 2), (xa, y_bot + 2)], 0)
    rows = 4
    for r in range(rows):
        f = r / (rows - 1)
        hy = y_top + (y_bot - y_top) * (0.2 + 0.7 * f)
        hr = 3.5 + 1.2 * f
        x = xa + rng.uniform(0, hr * 2)
        while x < xb - hr:
            yj = hy + rng.uniform(-1.5, 1.5)
            if rng.random() < 0.82:
                arc = ell(x, yj, hr, hr * 1.1, n=8, a0=math.pi * 1.08, a1=math.pi * 1.92, rng=rng)
                ln(arc, MINW, 'ice' if rng.random() < 0.7 else 'key', rng, wob=0.05)
            if rng.random() < 0.3:
                ex = x + rng.uniform(-0.6, 1.0) * hr
                ey = yj - hr * rng.uniform(3.6, 5.0)
                ln([(x + hr * 1.0, yj + hr * 0.3), (ex, ey)], MINW, 'key', rng, wob=0.05)
                if rng.random() < 0.3:
                    ph = [(ex - 2.0, ey - 6.5), (ex + 2.4, ey - 6.5), (ex + 2.4, ey - 0.5), (ex - 2.0, ey - 0.5)]
                    fillp(ph, 'ice')
            x += hr * 2.7 + rng.uniform(0.5, 2.5)


# ============================================================ THE CLOCK: a real cast-iron street clock
def post_clock2(x, z, rng, hour=1, minute=42):
    s = S(z)
    g = pr(x, 0, z)
    c = pr(x, 3.45, z)
    r = clamp(0.42 * s, 12, 40)
    pw = clamp(0.13 * s, 8, 13)          # the post, ~12 u wide
    yb = g[1]
    collar_y = c[1] + r * 1.12
    # the post knocks a black gutter round itself out of the tree behind
    body = [(c[0] - pw / 2, collar_y), (c[0] + pw / 2, collar_y), (c[0] + pw / 2 + 1.5, yb - 22),
            (c[0] - pw / 2 - 1.5, yb - 22)]
    base = [(c[0] - 15, yb), (c[0] - 15, yb - 9), (c[0] - 11, yb - 12), (c[0] - 11, yb - 20), (c[0] + 11, yb - 20),
            (c[0] + 11, yb - 12), (c[0] + 15, yb - 9), (c[0] + 15, yb)]
    knock(grow(body, 5.0), 1.0)
    knock(grow(base, 5.0), 1.0)
    fillp(body, 'key')
    # a dark fluting carved down the post's shadow side
    knock_line([(c[0] + pw * 0.12, collar_y + 16), (c[0] + pw * 0.18, yb - 30)], MINW, layers=('key',))
    fillp(base, 'key')
    knock_line([(c[0] - 14, yb - 9.5), (c[0] + 14, yb - 9.5)], MINW, layers=('key',))      # moulding line
    ln([(c[0] - 16, yb + 1), (c[0] + 16, yb + 1)], MINW * 1.2, 'key', rng, wob=0.05)
    # collar ring under the face and two scroll brackets
    col = [(c[0] - pw * 0.95, collar_y - 4), (c[0] + pw * 0.95, collar_y - 4), (c[0] + pw * 0.95, collar_y + 4),
           (c[0] - pw * 0.95, collar_y + 4)]
    knock(grow(col, 2.0), 0.5)
    fillp(col, 'key')
    for sg in (-1, 1):
        sc_ = [(c[0] + sg * pw * 0.5, collar_y + 16), (c[0] + sg * pw * 1.5, collar_y + 9), (c[0] + sg * pw * 1.6, collar_y + 2),
               (c[0] + sg * pw * 1.1, collar_y - 1)]
        knock_line(sc_, MINW + 5)
        ln(sc_, MINW, 'key', rng, wob=0.05)
        dot(sc_[-1][0], sc_[-1][1] + 0.5, MINW * 0.75, 'key', rng)
    # the face
    face = ell(c[0], c[1], r, r, n=28, rng=rng)
    knock(grow(face, 3.0), 0)
    blob(face, 'amber', rng, gap=0.0, shift=0.4, jit=0.01)
    ln(face + [face[0]], clamp(0.05 * s, MINW, 4.5), 'key', rng, wob=0.1)
    for i in range(12):
        a = TAU * i / 12
        p0 = (c[0] + math.sin(a) * r * 0.74, c[1] - math.cos(a) * r * 0.74)
        p1 = (c[0] + math.sin(a) * r * (0.9 if i % 3 else 0.95), c[1] - math.cos(a) * r * (0.9 if i % 3 else 0.95))
        knock_line([p0, p1], MINW * (1.25 if i % 3 == 0 else 1.0), layers=('amber',))
    ah = TAU * ((hour % 12) + minute / 60) / 12
    am = TAU * minute / 60
    for a, L, wd in ((ah, 0.5, 1.6), (am, 0.8, 1.25)):
        p1 = (c[0] + math.sin(a) * r * L, c[1] - math.cos(a) * r * L)
        knock_line([c, p1], MINW * wd, layers=('amber',))
    knock_ell(c[0], c[1], MINW * 1.0, MINW * 1.0, layers=('amber',))
    # finial
    ln([(c[0], c[1] - r * 1.02), (c[0], c[1] - r * 1.32)], MINW * 1.3, 'key', rng)
    dot(c[0], c[1] - r * 1.4, MINW * 0.85, 'key', rng)
    return c


# ============================================================ THE METRO PIER: one tall single column, a wide T-cap
def pier3(z, rng):
    import lib_show as LS
    s = S(z)
    xc = LS.vx(z)
    r = 0.9
    yc = 6.9 + LS.LIFT                    # top of the column / underside of the cap
    yt = LS.DB + LS.LIFT                  # top of the cap = soffit of the girder
    g0, g1 = pr(xc - r, 0, z), pr(xc + r, 0, z)
    t0, t1 = pr(xc - r, yc, z), pr(xc + r, yc, z)
    cw = 3.7
    cap = [pr(xc - cw, yc + 0.35, z), pr(xc - cw, yt, z), pr(xc + cw, yt, z), pr(xc + cw, yc + 0.35, z),
           pr(xc + r * 1.25, yc, z), pr(xc - r * 1.25, yc, z)]
    col = [g0, t0, t1, g1]
    knock(grow(col, 1.5), 1.4)
    knock(grow(cap, 1.5), 1.4)
    we = clamp(0.085 * s, MINW, 6.5)
    edge(g0, t0, we, 'key', rng, over=(-0.5, 0.5))
    edge(g1, t1, we * 0.75, 'key', rng, over=(-0.5, 0.5))
    span = max(1, g1[0] - g0[0])

    def tone(px, py):
        f = (px - g0[0]) / span
        return clamp(0.8 - 1.0 * f, 0.0, 1.0) ** 1.3
    hatch(col, 'key', math.pi / 2, clamp(0.14 * s, 9.5, 12), rng=rng, gap=0.05, tone=tone, maxlen=70)
    # the cap: a firm box, its underside lit amber by the street below
    pline(cap[:4], we * 0.9, 'key', rng, closed=False)
    ln([cap[3], cap[4], cap[5], cap[0]], we * 0.8, 'key', rng, wob=0.08)
    for f in (0.35, 0.7):
        a_, b_ = lerp(cap[0], cap[5], f), lerp(cap[3], cap[4], f)
        ln([lerp(a_, b_, 0.04), lerp(a_, b_, 0.96)], MINW * 1.1, 'amber', rng, wob=0.08, a0=1.0, a1=2.0)
    # plinth
    pl = [pr(xc - 1.3, 0, z - 0.9), pr(xc - 1.3, 0.45, z - 0.9), pr(xc + 1.3, 0.45, z - 0.9), pr(xc + 1.3, 0, z - 0.9)]
    knock(pl, 0.5)
    pline(pl, MINW, 'key', rng, skip=0.15)


# ============================================================ round 18b: the cloud as big lobed cumulus, thin beams
def make_mass(x0, x1, base, peak, rng, ymin=256):
    """lobes along the top of one cumulus mass: varied radii, a high middle, small bumps on the big ones"""
    lobes = []
    x = x0 + rng.uniform(20, 34)
    while x < x1 - 20:
        f = (x - x0) / (x1 - x0)
        env = peak * (0.5 + 0.5 * math.sin(math.pi * f) ** 0.8) * rng.uniform(0.86, 1.04)
        r = rng.uniform(30, 60) * (0.7 + 0.45 * math.sin(math.pi * f))
        cy = base - env + r * 0.86
        cy = max(cy, ymin + r * 0.86)
        lobes.append((x, cy, r))
        if r > 42 and rng.random() < 0.7:          # a small bump riding on a big lobe
            a = rng.uniform(-2.3, -0.8)
            rr = r * rng.uniform(0.32, 0.45)
            bx, by = x + math.cos(a) * r * 0.8, cy + math.sin(a) * r * 0.7
            if by - rr * 0.86 >= ymin:
                lobes.append((bx, by, rr))
        x += r * rng.uniform(0.95, 1.35)
    return lobes


def mass_mask(lobes, x0, x1, base):
    m = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(m)
    for cx, cy, r in lobes:
        d.ellipse(((cx - r) * R, (cy - r * 0.86) * R, (cx + r) * R, (cy + r * 0.86) * R), fill=255)
    big = [l for l in lobes if l[2] > 25]
    ytop = sorted(l[1] for l in big)[len(big) // 2] if big else base - 30
    body = [(x0 + 14, ytop), (x1 - 14, ytop)] + [(x0 + (x1 - x0) * i / 30, base + 3.5 * math.sin(i * 0.8) + 2 * math.sin(i * 2.1))
                                                 for i in range(30, -1, -1)]
    d.polygon(P(body), fill=255)
    # round off the two ends of the belly
    for xe, s in ((x0 + 14, -1), (x1 - 14, 1)):
        d.ellipse(((xe - 22) * R, (base - 40) * R, (xe + 22) * R, (base + 2) * R), fill=255)
    return m


def cloud_bank2(specs, rng, beams=()):
    """specs: (x0, x1, base, peak) far to near. Flat deep blue; every nearer mass cut from the ones behind by a black
    gouge; a few short gouges under the big lobes; a broken cream rim on each lit belly and a few ice strokes above it;
    where a beam enters a belly, that part of the belly lit flat ice"""
    T = {k: Image.new('L', (W, H), 0) for k in ('blue', 'ice', 'key')}
    D = {k: ImageDraw.Draw(v) for k, v in T.items()}
    masses = []
    for x0, x1, base, peak in specs:
        lobes = make_mass(x0, x1, base, peak, rng)
        masses.append((mass_mask(lobes, x0, x1, base), lobes, x0, x1, base))
    for m, lobes, x0, x1, base in masses:
        g = m.filter(ImageFilter.MaxFilter(max(3, int(MINW * 1.3 * R) | 1)))
        for k in T:
            T[k].paste(0, (0, 0), g)
        T['blue'].paste(255, (0, 0), m)
        # short gouges at the lower edge of the biggest lobes, where a lobe swells over the next
        big = sorted([l for l in lobes if l[2] > 36], key=lambda l: -l[2])[:4]
        for cx, cy, r in big:
            if cy + r * 0.86 > base - MINW * 4:
                continue
            side = rng.choice((-1, 1))
            a0 = math.pi / 2 + side * rng.uniform(0.25, 0.55)
            arc = ell(cx, cy, r * 0.98, r * 0.84, n=10, a0=a0, a1=a0 + side * rng.uniform(0.7, 1.05), rng=rng)
            _ink(D['blue'], A.hand(arc, wob=0.15, trem=0.1, rng=rng), MINW * 1.15, 0, rng)
        # the lit belly: a broken cream rim and a few ice strokes above it
        bl = [(x0 + 20 + (x1 - x0 - 40) * j / 60, base + 3.5 * math.sin(j * 0.4) + 2 * math.sin(j * 1.05) - 1.2)
              for j in range(61)]
        j = rng.randint(0, 4)
        while j < len(bl) - 3:
            Ls = rng.randint(4, 11)
            if rng.random() < 0.6:
                seg = bl[j:j + Ls]
                _ink(D['blue'], A.hand(seg, wob=0.1, trem=0.05, rng=rng), MINW * 2.6, 0, rng)
                _ink(D['key'], A.hand(seg, wob=0.15, trem=0.1, rng=rng), MINW * 1.1, 255, rng)
            j += Ls + rng.randint(2, 6)
        for row in range(2):
            yy = base - MINW * (3.4 + 2.5 * row)
            xx = x0 + rng.uniform(26, 50)
            while xx < x1 - 50:
                Ls = rng.uniform(18, 40)
                if rng.random() < 0.42 - 0.14 * row:
                    seg = [(xx, yy), (xx + Ls / 2, yy + rng.gauss(0, 0.6)), (xx + Ls, yy)]
                    _ink(D['blue'], A.hand(seg, wob=0.1, trem=0.05, rng=rng), MINW * 2.6, 0, rng)
                    _ink(D['ice'], A.hand(seg, wob=0.1, trem=0.05, rng=rng), MINW * 1.05, 255, rng)
                xx += Ls + rng.uniform(16, 44)
    # where each beam enters a belly: light that patch, flat ice in the cloud's own shape
    for root, ang, top_y, wend in beams:
        ux, uy = math.sin(ang), -math.cos(ang)
        for m, lobes, x0, x1, base in masses[::-1]:
            t = (root[1] - (base - 6)) / max(0.2, -uy) if uy < 0 else -1
            if t <= 0:
                continue
            px, py = root[0] + ux * t, root[1] + uy * t
            if not (x0 + 20 < px < x1 - 20):
                continue
            if T['blue'].getpixel((min(W - 1, int(px * R)), min(H - 1, int(py * R)))) == 0 and \
                    m.getpixel((min(W - 1, int(px * R)), min(H - 1, int(py * R)))) == 0:
                continue
            Ltot = (root[1] - top_y) / max(0.2, math.cos(ang))
            hw = (2 + (wend - 2) * min(1.0, t / Ltot)) * 1.9 + 4
            # the cloud lit where the beam enters it: short ice strokes stacked up the beam, wider than it,
            # each in its own black slot (the same hand as the belly strokes)
            yy = base - 9
            k = 0
            ytop_ = base - rng.uniform(26, 34)
            while yy > ytop_:
                tt = (root[1] - yy) / max(0.2, -uy)
                cx_ = root[0] + ux * tt
                half = hw * (1.25 + 0.3 * k) * rng.uniform(0.85, 1.15)
                if m.getpixel((min(W - 1, int(cx_ * R)), min(H - 1, int(yy * R)))) and half > 6:
                    o_ = rng.uniform(-0.3, 0.3) * half
                    seg = [(cx_ - half + o_, yy), (cx_ + o_ + rng.uniform(-2, 2), yy + rng.gauss(0, 0.6)), (cx_ + half + o_, yy)]
                    _ink(D['blue'], A.hand(seg, wob=0.1, trem=0.05, rng=rng), MINW * 2.6, 0, rng)
                    _ink(D['ice'], A.hand(seg, wob=0.1, trem=0.05, rng=rng), MINW * 1.15, 255, rng)
                yy -= MINW * rng.uniform(2.3, 2.8)
                k += 1
            break
    return T


def beam4(T, root, ang, top_y, wend, rng, n=3):
    """a long thin white beam: three strokes converging on the head, breaking into dashes as they climb and fading out
    before top_y; each stroke carves its own narrow black slot through the blue"""
    ux, uy = math.sin(ang), -math.cos(ang)
    nx, ny = -uy, ux
    L = (root[1] - top_y) / max(0.2, math.cos(ang))
    end = (root[0] + ux * L, root[1] + uy * L)
    D = {k: ImageDraw.Draw(v) for k, v in T.items()}
    for f in ((-1.0, 0.0, 1.0) if n == 3 else (-1.0, 1.0)):
        tip = (end[0] + nx * wend * f, end[1] + ny * wend * f)
        t0, t1 = 0.0, rng.uniform(0.3, 0.42) * (1.3 if f == 0 else 1.0)
        while t0 < 0.95:
            a, b = lerp(root, tip, t0), lerp(root, tip, min(0.95, t1))
            w = MINW * (1.25 - 0.25 * t0 if f == 0 else 1.0)
            pp = A.hand([a, lerp(a, b, 0.5), b], wob=0.04, trem=0.03, rng=rng)
            _ink(D['blue'], pp, w + MINW * 1.5, 0, rng)
            _ink(D['key' if (f == 0 and t0 < 0.35) else 'ice'], pp, w, 255, rng)
            t0 = t1 + rng.uniform(0.035, 0.07) * (1 + 2.6 * t1)
            t1 = t0 + rng.uniform(0.07, 0.15) * (1.3 - t0)
    return [(root[0] + nx * 2, root[1] + ny * 2), (end[0] + nx * wend, end[1] + ny * wend),
            (end[0] - nx * wend, end[1] - ny * wend), (root[0] - nx * 2, root[1] - ny * 2)]


def strobe(x, y, rng, n=7, r0=3.6, r1=(9, 16)):
    """a strobe flash on the truss: a stark star of tapered key strokes, no ring"""
    knock_ell(x, y, r0 + max(r1) + 4, r0 + max(r1) + 4, layers=('ice', 'blue'))
    for k in ('key',):
        pass
    a = rng.uniform(0, TAU)
    knock_ell(x, y, 5.5, 5.0)
    dot(x, y, 3.3, 'key', rng)
    for i in range(n):
        aa = a + TAU * i / n + rng.uniform(-0.12, 0.12)
        l = rng.uniform(*r1) * (1.35 if i % 3 == 0 else 1.0)
        p0 = (x + math.cos(aa) * (r0 + 1.5), y + math.sin(aa) * (r0 + 1.5))
        p1 = (x + math.cos(aa) * (r0 + l), y + math.sin(aa) * (r0 + l))
        knock_line([p0, p1], MINW + 4.0)
        A.line([p0, lerp(p0, p1, 0.5), p1], MINW * 1.15, layer='key', rng=rng, wob=0.03, trem=0.0, a0=0.4, a1=2.6, pv=0.05)


def footage_face2(x0, y0, x1, y1, rng, p=8.4):
    """grainy phone footage on the screen: a blown-up face in profile looking left toward the decks. The profile edge
    is solid black (it has to read), the face behind it a coarse dot screen, a little camera grain on the white"""
    wq, hq = x1 - x0, y1 - y0
    sc = 2
    mw, mh = int(wq * sc) + 2, int(hq * sc) + 2
    m = Image.new('L', (mw, mh), 0)
    d = ImageDraw.Draw(m)
    prof = [(0.70, 0.0), (0.675, 0.12), (0.69, 0.25), (0.685, 0.33), (0.632, 0.48), (0.632, 0.52), (0.676, 0.555),
            (0.668, 0.6), (0.684, 0.63), (0.67, 0.67), (0.69, 0.71), (0.688, 0.8), (0.73, 0.9), (0.76, 1.0),
            (1.0, 1.0), (1.0, 0.0)]
    d.polygon([(u * wq * sc, v * hq * sc) for u, v in prof], fill=255)
    inner = m.filter(ImageFilter.MinFilter(int(11 * sc) | 1))
    # the face's lit cheek: a light hole in the dot screen, and the eye
    hl = Image.new('L', (mw, mh), 0)
    hd = ImageDraw.Draw(hl)
    hd.ellipse(((0.74 * wq) * sc, (0.46 * hq) * sc, (0.88 * wq) * sc, (0.74 * hq) * sc), fill=255)
    hl = hl.filter(ImageFilter.GaussianBlur(6 * sc))
    t_ = (0.92 * np.asarray(m, dtype=np.float32) - 0.42 * np.asarray(inner, dtype=np.float32)
          - 0.3 * np.asarray(hl, dtype=np.float32) * (np.asarray(inner, dtype=np.float32) / 255.0)) / 255.0
    tone = np.asarray(Image.fromarray(np.clip(t_ * 255, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5 * sc)),
                      dtype=np.float32) / 255.0
    rmin = MINW * 0.6
    rmax = (p - MINW * 1.3) / 2
    for x, y in grid45((x0 + 3, y0 + 3, x1 - 3, y1 - 3), p):
        u, v = int((x - x0) * sc), int((y - y0) * sc)
        t = float(tone[min(mh - 1, v), min(mw - 1, u)])
        t = t + 0.14 * rng.random() * (1 - t)       # the grain of a phone camera in the dark
        if t < 0.24:
            continue
        t = min(t, 0.86)
        r = p * 0.8 if t > 0.84 else rmin + (rmax - rmin) * min(1.0, (t - 0.24) / 0.52)
        knock_ell(x + rng.gauss(0, 0.4), y + rng.gauss(0, 0.4), r, r, layers=('ice',))
    # the eye: a dark almond in the dot screen
    ex, ey = x0 + 0.715 * wq, y0 + 0.37 * hq
    knock_ell(ex, ey, 4.2, 2.6, layers=('ice',))
    for f in (0.3, 0.69):
        yy = y0 + hq * f
        knock_line([(x0 + rng.uniform(4, 30), yy), (x0 + wq * 0.6, yy)], MINW, layers=('ice',))


def stage_dj2(rng, X0=398.0, X1=726.0, YR=392.0, YD=566.0):
    """the DJ set, bigger: pale sheet roof, scaffold truss and straight legs, line arrays, a big LED screen with grainy
    footage, two strobes, and in front of the screen one long table of gear with one figure bent over it"""
    xc = (X0 + X1) / 2
    knock([(X0 - 8, YR - 12), (X1 + 8, YR - 12), (X1 + 8, YD + 16), (X0 - 8, YD + 16)], 0.8)
    sx0, sx1, sy0, sy1 = X0 + 54, X1 - 54, YR + 33, YD - 6
    scr = [(sx0, sy0), (sx1, sy0), (sx1, sy1), (sx0, sy1)]
    fillp(scr, 'ice')
    footage_face2(sx0, sy0, sx1, sy1, rng)
    pline(scr, MINW * 1.25, 'key', rng, over=(-0.5, 1.5))
    ty0, ty1 = YR + 11, YR + 25
    ln([(X0, ty0), (X1, ty0)], MINW * 1.2, 'key', rng, wob=0.05)
    ln([(X0, ty1), (X1, ty1)], MINW * 1.2, 'key', rng, wob=0.05)
    n = 22
    for i in range(n):
        a_ = (X0 + (X1 - X0) * i / n, ty1)
        b_ = (X0 + (X1 - X0) * (i + 0.5) / n, ty0)
        c_ = (X0 + (X1 - X0) * (i + 1) / n, ty1)
        ln([a_, b_, c_], MINW, 'key', rng, wob=0.03, a0=0.5, a1=0.8)
    for lx in (X0 + 5, X1 - 5):
        knock([(lx - 9, ty1), (lx + 9, ty1), (lx + 9, YD + 14), (lx - 9, YD + 14)], 0.3)
        for dx in (-6.0, 6.0):
            ln([(lx + dx, ty0), (lx + dx, YD + 14)], MINW * 1.15, 'key', rng, wob=0.04)
        y_ = ty1 + 6
        while y_ < YD + 4:
            ln([(lx - 6, y_), (lx + 6, y_ + 11)], MINW, 'key', rng, wob=0.03, a0=0.5, a1=0.8)
            y_ += 18
    sag = [(X0 - 10 + (X1 - X0 + 20) * i / 20, YR + 8 + 3.5 * math.sin(math.pi * i / 20)) for i in range(21)]
    topl = [(X0 - 8, YR - 4), (xc - 70, YR - 7.5), (xc, YR - 8.5), (xc + 70, YR - 7.5), (X1 + 8, YR - 4)]
    roof = topl + sag[::-1]
    knock(roof, 1.0)
    blob(roof, 'ice', rng, gap=0.0, shift=0.4, jit=0.006)
    for f in (0.2, 0.5, 0.8):
        xs_ = X0 + (X1 - X0) * f + rng.uniform(-6, 6)
        knock_line([(xs_ - 2, YR - 6), (xs_ + 2, YR + 8)], MINW, layers=('ice',))
    ln(sag, MINW * 1.4, 'key', rng, wob=0.08)
    ln(topl, MINW * 1.2, 'key', rng, wob=0.08)
    for sgn in (-1, 1):
        x_ = (X0 + 31) if sgn < 0 else (X1 - 31)
        y_ = ty1 + 3
        ln([(x_, ty1), (x_, y_)], MINW, 'key', rng)
        for i in range(10):
            hb = 7.8
            tilt = sgn * (0.0 if i < 6 else (i - 5) * 1.5)
            wt, wb = 18.0 - i * 0.2, 16.0 - i * 0.2
            box = [(x_ - wt / 2 + tilt * 0.3, y_), (x_ + wt / 2 + tilt * 0.3, y_), (x_ + wb / 2 + tilt, y_ + hb),
                   (x_ - wb / 2 + tilt, y_ + hb)]
            knock(box, 0.6)
            pline(box, MINW, 'key', rng, over=(-0.3, 0.6))
            y_ += hb + 0.6
    ln([(X0 + 16, YD), (X1 - 16, YD)], MINW * 1.5, 'key', rng, wob=0.05)
    ln([(X0 + 20, YD + 13), (X1 - 20, YD + 13)], MINW, 'key', rng, wob=0.05)
    # the strobes: two stark stars on the front of the truss
    for sx_ in (X0 + 62, X1 - 74):
        strobe(sx_, ty0 + 7, rng)
    # ---- the DJ: one long table of gear and one figure, cut black out of the screen
    tw = 112.0
    xd = xc - 4
    tx0, tx1 = xd - tw / 2, xd + tw / 2
    ttop = sy1 - 27
    sil = [[(tx0, ttop), (tx1, ttop), (tx1 - 2, YD), (tx0 + 2, YD)]]
    jogs = [tx0 + 18, tx1 - 18]
    mixer = [(xd - 10, ttop), (xd - 10, ttop - 6.5), (xd + 10, ttop - 6.5), (xd + 10, ttop)]
    lap = [(xd + 20, ttop), (xd + 27, ttop - 17), (xd + 45, ttop - 15), (xd + 41, ttop)]
    pads = [(tx0 + 34, ttop), (tx0 + 34, ttop - 4.5), (tx0 + 47, ttop - 4.5), (tx0 + 47, ttop)]
    sil += [mixer, lap, pads] + [[(jx - 13, ttop), (jx - 13, ttop - 5), (jx + 13, ttop - 5), (jx + 13, ttop)] for jx in jogs]
    # the figure, bent over the gear: shoulders forward, head bowed toward the mixer, left hand up
    fx = xd - 8
    body = [(fx - 12, ttop + 1), (fx - 13, ttop - 17), (fx - 9, ttop - 30), (fx + 4, ttop - 35), (fx + 14, ttop - 31),
            (fx + 13, ttop - 15), (fx + 10, ttop + 1)]
    head = (fx + 10, ttop - 41)
    hd = ell(head[0], head[1], 6.6, 7.4, n=16, rot=0.55)
    neck = [(fx + 3, ttop - 33), (fx + 7, ttop - 38), (fx + 12, ttop - 36), (fx + 10, ttop - 31)]
    sil += [body, hd, neck]
    arm1 = [(fx + 11, ttop - 28), (fx + 19, ttop - 17), (xd + 4, ttop - 8.5)]
    arm2 = [(fx - 8, ttop - 30), (fx - 21, ttop - 45), (fx - 17, ttop - 66)]
    km = 2.2
    for poly in sil:
        knock(grow(poly, km), 0, layers=('ice',))
    for a in (arm1, arm2):
        knock_line(a, 6.0 + km * 2, layers=('ice',))
    knock_ell(arm2[-1][0], arm2[-1][1] - 2.5, 3.8 + km, 5.2 + km, layers=('ice',))
    knock_ell(arm1[-1][0], arm1[-1][1], 3.6 + km, 3.2 + km, layers=('ice',))
    # key-line highlights on the gear and a rim of screen light on him
    ln([(tx0 + 1, ttop + 0.6), (tx1 - 1, ttop + 0.6)], MINW, 'key', rng, wob=0.02)
    for jx in jogs:
        ln(ell(jx, ttop - 5, 10.5, 2.8, n=12, a0=math.pi * 1.05, a1=math.pi * 1.95, rng=rng), MINW, 'key', rng, wob=0.02)
    ln([lap[1], lap[2]], MINW, 'key', rng, wob=0.02)
    ln([(mixer[1][0] + 1, mixer[1][1]), (mixer[2][0] - 1, mixer[2][1])], MINW, 'key', rng, wob=0.02)
    ln([(arm2[1][0] - 5.0, arm2[1][1] + 1), (arm2[2][0] - 4.8, arm2[2][1] + 3)], MINW, 'key', rng, wob=0.03)
    ln(ell(head[0], head[1], 8.0, 8.8, n=8, a0=math.pi * 1.1, a1=math.pi * 1.7, rot=0.55, rng=rng), MINW, 'key', rng, wob=0.03)
    ln([(fx - 11.5, ttop - 4), (fx - 12.5, ttop - 17), (fx - 9.5, ttop - 28)], MINW, 'key', rng, wob=0.03)
    return dict(truss=(X0, X1, ty0), screen=(sx0, sy0, sx1, sy1), xc=xd, roof=YR - 22)


def crowd_dj2(rng, xa, xb, y_top, y_bot):
    """the crowd in front of the stage: a dark band of heads, a few raised hands and phones, rimmed in ice"""
    knock([(xa, y_top - 26), (xb, y_top - 26), (xb, y_bot + 2), (xa, y_bot + 2)], 0)
    rows = 3
    for r in range(rows):
        f = r / (rows - 1)
        hy = y_top + (y_bot - y_top) * (0.25 + 0.65 * f)
        hr = 5.0 + 1.4 * f
        x = xa + rng.uniform(0, hr * 2) + r * hr
        while x < xb - hr:
            yj = hy + rng.uniform(-1.5, 1.5)
            if rng.random() < 0.85:
                arc = ell(x, yj, hr, hr * 1.1, n=8, a0=math.pi * 1.12, a1=math.pi * 1.88, rng=rng)
                ln(arc, MINW, 'ice' if rng.random() < 0.75 else 'key', rng, wob=0.04)
            if rng.random() < 0.22:
                ex = x + rng.uniform(-0.4, 0.8) * hr
                ey = yj - hr * rng.uniform(3.2, 4.4)
                ln([(x + hr * 0.9, yj + hr * 0.2), (ex, ey)], MINW, 'ice', rng, wob=0.04)
                if rng.random() < 0.35:
                    ph = [(ex - 2.4, ey - 7.5), (ex + 2.6, ey - 7.5), (ex + 2.6, ey - 0.8), (ex - 2.4, ey - 0.8)]
                    knock(grow(ph, 1.6), 0)
                    fillp(ph, 'ice')
            x += hr * 2.9 + rng.uniform(0.5, 3.0)


def beam5(T, root, ang, top_y, wend, rng, ink='ice'):
    """a white beam as a long thin wedge cut in segments: narrow and solid at the head, widening, its segments getting
    shorter and the gaps longer as it climbs, the last ones split into two thin strokes; it carves its own black slot
    through the blue"""
    ux, uy = math.sin(ang), -math.cos(ang)
    nx, ny = -uy, ux
    L = (root[1] - top_y) / max(0.2, math.cos(ang))
    D = {k: ImageDraw.Draw(v) for k, v in T.items()}
    t0 = 0.0
    t1 = rng.uniform(0.28, 0.36)
    w0 = 1.9
    while t0 < 0.93:
        t1 = min(t1, 0.95)
        wa, wb = w0 + (wend - w0) * t0, w0 + (wend - w0) * t1
        a, b = (root[0] + ux * L * t0, root[1] + uy * L * t0), (root[0] + ux * L * t1, root[1] + uy * L * t1)
        if t0 < 0.62:
            q = [(a[0] + nx * wa, a[1] + ny * wa), (b[0] + nx * wb, b[1] + ny * wb), (b[0] - nx * wb, b[1] - ny * wb),
                 (a[0] - nx * wa, a[1] - ny * wa)]
            q = A.hand(q + [q[0]], wob=0.12, trem=0.05, rng=rng)
            D['blue'].polygon(P(grow(q, MINW * 1.3)), fill=0)
            D[ink].polygon(P(q), fill=255)
            if t0 < 0.3:       # a cream core near the head
                pp = A.hand([lerp(a, b, 0.05), lerp(a, b, 0.9)], wob=0.03, trem=0.0, rng=rng)
                _ink(D['key'], pp, MINW * 1.0, 255, rng)
        else:                  # high up the beam frays into two thin strokes
            for f in (-0.75, 0.75):
                pa = (a[0] + nx * wa * f, a[1] + ny * wa * f)
                pb = (b[0] + nx * wb * f, b[1] + ny * wb * f)
                pp = A.hand([pa, lerp(pa, pb, 0.5), pb], wob=0.04, trem=0.0, rng=rng)
                _ink(D['blue'], pp, MINW * 2.4, 0, rng)
                _ink(D[ink], pp, MINW, 255, rng)
        t0 = t1 + rng.uniform(0.04, 0.07) * (1 + 2.4 * t1)
        t1 = t0 + rng.uniform(0.1, 0.17) * (1.2 - t0)
    end = (root[0] + ux * L, root[1] + uy * L)
    return [(root[0] + nx * 2, root[1] + ny * 2), (end[0] + nx * wend, end[1] + ny * wend),
            (end[0] - nx * wend, end[1] - ny * wend), (root[0] - nx * 2, root[1] - ny * 2)]


def crowd_dj3(rng, xa, xb, y_top, y_bot):
    """the crowd in front of the stage as the stage light catches it: rows of heads drawn as one bumpy rim line each
    (ice on the front row, cream behind), a few raised arms and phones above; black below each rim"""
    knock([(xa, y_top - 28), (xb, y_top - 28), (xb, y_bot + 2), (xa, y_bot + 2)], 0)
    rows = 3
    for r in range(rows):
        f = r / (rows - 1)
        hy = y_top + (y_bot - y_top) * (0.15 + 0.75 * f)
        hr = 4.6 + 1.6 * f
        x = xa + rng.uniform(0, hr) + (rows - r) * 3
        pts = []
        while x < xb - hr:
            yj = hy + rng.uniform(-1.2, 1.2)
            for a_ in (math.pi * 1.0, math.pi * 1.25, math.pi * 1.5, math.pi * 1.75, math.pi * 2.0):
                pts.append((x + math.cos(a_) * hr, yj + math.sin(a_) * hr * 1.1))
            pts.append((x + hr * 1.35, yj + hr * 0.5))
            if rng.random() < 0.2 and r < 2:
                ex = x + rng.uniform(-0.3, 0.7) * hr
                ey = yj - hr * rng.uniform(3.0, 4.2)
                ln([(x + hr * 0.8, yj - hr * 0.2), (ex, ey)], MINW, 'key', rng, wob=0.04)
                if rng.random() < 0.4:
                    ph = [(ex - 2.5, ey - 8), (ex + 2.7, ey - 8), (ex + 2.7, ey - 1), (ex - 2.5, ey - 1)]
                    knock(grow(ph, 1.6), 0)
                    fillp(ph, 'ice')
            x += hr * 2.7 + rng.uniform(0.3, 2.0)
        # one rim line per row, broken into a few runs
        i = 0
        while i < len(pts) - 3:
            n_ = rng.randint(14, 30)
            ln(pts[i:i + n_], MINW, 'ice' if r == rows - 1 else ('key' if r == 1 else 'ice'), rng, wob=0.05, a0=0.6, a1=1.0)
            i += n_ + rng.randint(1, 3)


def beam6(T, root, ang, top_y, rng, ink='ice', w0=None, w1=None):
    """a thin white beam: one straight stroke from the fixture, solid and narrow at the head, a little wider as it
    climbs, broken into dashes whose gaps grow until it is gone before top_y; it cuts its own black slot through
    the blue so it reads as light in front of the cloud"""
    w0 = MINW * 1.3 if w0 is None else w0
    w1 = MINW * 2.1 if w1 is None else w1
    ux, uy = math.sin(ang), -math.cos(ang)
    nx, ny = -uy, ux
    L = (root[1] - top_y) / max(0.2, math.cos(ang))
    D = {k: ImageDraw.Draw(v) for k, v in T.items()}
    t0, t1 = 0.0, rng.uniform(0.34, 0.42)
    while t0 < 0.9:
        t1 = min(t1, 0.92)
        wa, wb = (w0 + (w1 - w0) * t0) / 2, (w0 + (w1 - w0) * t1) / 2
        if t0 > 0.55:
            wa, wb = wa * 0.8, wb * 0.75
        a = (root[0] + ux * L * t0, root[1] + uy * L * t0)
        b = (root[0] + ux * L * t1, root[1] + uy * L * t1)
        q = [(a[0] + nx * wa, a[1] + ny * wa), (b[0] + nx * wb, b[1] + ny * wb),
             (b[0] - nx * wb, b[1] - ny * wb), (a[0] - nx * wa, a[1] - ny * wa)]
        D['blue'].polygon(P(grow(q, MINW * 1.25)), fill=0)
        D[ink].polygon(P(q), fill=255)
        if t0 < 0.2:
            _ink(D['key'], [lerp(a, b, 0.04), lerp(a, b, 0.92)], MINW * 1.0, 255, rng)
        t0 = t1 + rng.uniform(0.03, 0.05) * (1 + 3.0 * t1)
        t1 = t0 + rng.uniform(0.1, 0.16) * (1.25 - t0)
    end = (root[0] + ux * L, root[1] + uy * L)
    return [(root[0] + nx * 2, root[1] + ny * 2), (end[0] + nx * 8, end[1] + ny * 8),
            (end[0] - nx * 8, end[1] - ny * 8), (root[0] - nx * 2, root[1] - ny * 2)]


# trunks and limbs join the leaf mask: drizzle and sky never fall across a trunk
def _rec_occ(fn):
    def wrapped(*a, **k):
        before = OCC.copy()
        out = fn(*a, **k)
        CANOPY.paste(255, (0, 0), ImageChops.subtract(OCC, before))
        return out
    return wrapped


lib_v3.trunk3 = _rec_occ(lib_v3.trunk3)
_limb3 = lib_v3.limb3
lib_v3.limb3 = _rec_occ(lambda *a, **k: _limb3(*a, **dict(k, under='key')))
trunk3, limb3 = lib_v3.trunk3, lib_v3.limb3
