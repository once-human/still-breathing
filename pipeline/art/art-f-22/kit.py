"""kit.py: camera, pen helpers, hatching, light marks (halo, drizzle, painterly reflections) for 22°.
Everything is in 1200 x 1600 units; the canvas is R px per unit (env R)."""
import os, sys, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hand
from hand import (Art, catmull, cumlen, normals, offset_path, resample, smooth, halftone, composite, save_preview,
                  hexrgb, MINW, R, W, H, TAU, clip_half, P)
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import numpy as np

SEED = 2242
PAL = {'blue': '#3F6FE6', 'green': '#3D9C5E', 'copper': '#D2673A', 'amber': '#F2A33A', 'ice': '#D3E4F0', 'yellow': '#F4CD3A',
       'key': '#EFE6CF'}
ORDER = ('blue', 'green', 'copper', 'amber', 'ice', 'yellow', 'key')
A = Art(seed=SEED, layers=ORDER)
RA = Art(seed=SEED + 1, layers=ORDER)          # reflections, laid on the road at the end under everything that stands
RNG = random.Random(SEED)
OCC = Image.new('L', (W, H), 0)                # everything that stands (knocked silhouettes) hides the wet road
OD = ImageDraw.Draw(OCC)
TITLE = (230, 70, 970, 235)
LINEZ = (380, 1492, 820, 1556)


def clamp(v, a, b):
    return a if v < a else b if v > b else v


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def U(a, b, rng=None):
    return (rng or RNG).uniform(a, b)


# ------------------------------------------------------------------ camera: a footbridge 6.5 m up, the far end squeezed
HC, FL, HY, CX = 6.5, 1050.0, 560.0, 600.0
SQ_Z, SQ = 45.0, 0.5


def ze(z):
    return z if z < SQ_Z else SQ_Z + (z - SQ_Z) * SQ


def S(z):
    """units per metre at depth z"""
    return FL / max(0.6, ze(z))


def warp(x, y):
    return (x + 2.6 * math.sin(y / 173 + 0.6) + 1.8 * math.sin(x / 241 + 2.1),
            y + 2.2 * math.sin(x / 197 + 1.3) + 1.2 * math.sin(y / 131))


def pr(x, y, z):
    s = S(z)
    return warp(CX + x * s, HY - (y - HC) * s)


def prl(pts3, n=1):
    """project a 3D polyline, subdividing each segment n times (long world edges bend with the warp)"""
    out = []
    for i in range(len(pts3) - 1):
        a, b = pts3[i], pts3[i + 1]
        for k in range(n):
            t = k / n
            out.append(pr(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t))
    out.append(pr(*pts3[-1]))
    return out


def wz(z, m, lo=None, hi=7.0):
    """a pen width that is m metres wide at depth z"""
    return clamp(m * S(z), lo or MINW, hi)


# ------------------------------------------------------------------ pen
def ln(pts, w, layer='key', rng=None, wob=0.35, trem=0.3, **kw):
    if len(pts) < 2:
        return
    return A.line(list(pts), max(MINW, w), layer=layer, rng=rng or RNG, wob=wob, trem=trem, **kw)


def edge(a, b, w, layer='key', rng=None, over=(-1.0, 3.0), passes=None, wob=0.3, **kw):
    """a straight edge drawn by hand: long ones in 2-3 passes with a small kink between"""
    rng = rng or RNG
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    if L < 1:
        return
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    e0, e1 = rng.uniform(*over), rng.uniform(*over)
    a2, b2 = (a[0] - ux * e0, a[1] - uy * e0), (b[0] + ux * e1, b[1] + uy * e1)
    n = passes or (1 if L < 140 else 2 if L < 320 else 3)
    cuts = sorted(rng.uniform(0.3, 0.7) if n == 2 else rng.uniform(0.15 + 0.3 * i, 0.4 + 0.3 * i) for i in range(n - 1))
    ts = [0.0] + cuts + [1.0]
    for i in range(n):
        t0, t1 = ts[i], ts[i + 1]
        p0 = lerp(a2, b2, t0 - (0.012 if i else 0))
        p1 = lerp(a2, b2, t1)
        k = rng.gauss(0, 0.9) if i else 0
        p0 = (p0[0] - uy * k, p0[1] + ux * k)
        bw = rng.gauss(0, L * (t1 - t0) * 0.006)
        m = ((p0[0] + p1[0]) / 2 - uy * bw, (p0[1] + p1[1]) / 2 + ux * bw)
        A.line([p0, m, p1], max(MINW, w * rng.uniform(0.9, 1.08)), layer=layer, rng=rng, wob=wob,
               trem=0.25 * min(1, L / 60), a0=0.9, a1=1.6, pv=0.15, **kw)


def pline(poly, w, layer='key', rng=None, closed=True, skip=0.0, **kw):
    """a polygon drawn edge by edge; skip = chance an edge is left out (lost edges)"""
    rng = rng or RNG
    n = len(poly)
    for i in range(n if closed else n - 1):
        if skip and rng.random() < skip:
            continue
        edge(poly[i], poly[(i + 1) % n], w, layer, rng, **kw)


def knock(poly, m=1.5, layers=None):
    if len(poly) < 3:
        return
    pp = P(poly)
    for k in (layers or ORDER):
        A.D[k].polygon(pp, fill=0)
        if m > 0:
            A.D[k].line(pp + [pp[0]], fill=0, width=max(1, int(2 * m * R)), joint='curve')
    if layers is None:
        OD.polygon(pp, fill=255)


def knock_line(pts, w, layers=None):
    pp = P(pts)
    for k in (layers or ORDER):
        A.D[k].line(pp, fill=0, width=max(1, int(w * R)), joint='curve')
        r = w * R / 2
        for x, y in (pp[0], pp[-1]):
            A.D[k].ellipse((x - r, y - r, x + r, y + r), fill=0)
    if layers is None:
        OD.line(pp, fill=255, width=max(1, int(w * R)), joint='curve')


def knock_ell(x, y, rx, ry, layers=None):
    for k in (layers or ORDER):
        A.D[k].ellipse(((x - rx) * R, (y - ry) * R, (x + rx) * R, (y + ry) * R), fill=0)
    if layers is None:
        OD.ellipse(((x - rx) * R, (y - ry) * R, (x + rx) * R, (y + ry) * R), fill=255)


def fillp(poly, layer):
    if len(poly) > 2:
        A.D[layer].polygon(P(poly), fill=255)


def blob(poly, layer, rng=None, **kw):
    if len(poly) > 2:
        kw.setdefault('gap', 0.12)
        kw.setdefault('shift', 1.0)
        kw.setdefault('jit', 0.05)
        A.blob(list(poly), layer, rng=rng or RNG, **kw)


def ell(cx, cy, rx, ry, n=20, rot=0.0, a0=0.0, a1=TAU, rng=None, j=0.0):
    rng = rng or RNG
    out = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        rr = 1 + (rng.gauss(0, j) if j else 0)
        x, y = math.cos(a) * rx * rr, math.sin(a) * ry * rr
        out.append((cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot)))
    return out


def dot(x, y, r, layer='key', rng=None):
    A.dot(x, y, max(r, MINW * 0.6), layer=layer, rng=rng or RNG)


def bbox(poly):
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def pip(x, y, poly):
    ins = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi:
            ins = not ins
        j = i
    return ins


def cen(poly):
    return sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)


def grow(poly, m):
    cx, cy = cen(poly)
    out = []
    for x, y in poly:
        d = math.hypot(x - cx, y - cy) or 1
        out.append((x + (x - cx) / d * m, y + (y - cy) / d * m))
    return out


def seg_in_poly(p0, p1, poly):
    ts = []
    n = len(poly)
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        d = dx * ey - dy * ex
        if abs(d) < 1e-9:
            continue
        ax, ay = a[0] - p0[0], a[1] - p0[1]
        t = (ax * ey - ay * ex) / d
        u = (ax * dy - ay * dx) / d
        if 0 <= u < 1:
            ts.append(t)
    ts.sort()
    return [(ts[i], ts[i + 1]) for i in range(0, len(ts) - 1, 2)]


def hatch(poly, layer, ang, sp, w=None, rng=None, jit=0.2, gap=0.05, dang=0.03, wob=0.3, tone=None, maxlen=None,
          bow=0.0, a0=1.0, a1=2.0, minlen=None):
    """continuous hand hatching clipped to poly. tone(x, y) -> 0..1 = chance a piece is drawn."""
    rng = rng or RNG
    w = w or MINW
    x0, y0, x1, y1 = bbox(poly)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rad = math.hypot(x1 - x0, y1 - y0) / 2 + 2
    d = -rad + rng.uniform(0, sp)
    minlen = minlen or w * 1.6
    while d < rad:
        a = ang + rng.gauss(0, dang)
        ux, uy = math.cos(a), math.sin(a)
        nx, ny = -math.sin(ang), math.cos(ang)
        p0 = (cx + nx * d - ux * rad, cy + ny * d - uy * rad)
        p1 = (cx + nx * d + ux * rad, cy + ny * d + uy * rad)
        for t0, t1 in seg_in_poly(p0, p1, poly):
            L = (t1 - t0) * 2 * rad
            if L < minlen:
                continue
            g = gap * L
            t0 += rng.uniform(0, g) / (2 * rad)
            t1 -= rng.uniform(0, g) / (2 * rad)
            pieces = [(t0, t1)]
            if maxlen and L > maxlen:
                k = int(L / maxlen) + 1
                st = (t1 - t0) / k
                pieces = []
                for i in range(k):
                    s0 = t0 + st * i + (rng.uniform(0.02, 0.12) * st if i else 0)
                    pieces.append((s0, t0 + st * (i + 1)))
            for s0, s1 in pieces:
                q0, q1 = lerp(p0, p1, s0), lerp(p0, p1, s1)
                if math.hypot(q1[0] - q0[0], q1[1] - q0[1]) < minlen:
                    continue
                m = lerp(q0, q1, 0.5)
                if tone is not None and rng.random() > tone(*m):
                    continue
                bw = rng.gauss(bow, abs(bow) * 0.3 + 0.3)
                m = (m[0] - uy * bw, m[1] + ux * bw)
                A.line([q0, m, q1], w * rng.uniform(0.92, 1.1), layer=layer, rng=rng, wob=wob, trem=0.2,
                       a0=a0, a1=a1, pv=0.15)
        d += sp * (1 + rng.uniform(-jit, jit))


def carve(pts, w, layer, rng=None):
    """take ink OUT of a layer (a carved line through a solid)"""
    A.ink(A.hand(pts, wob=0.3, trem=0.2, rng=rng or RNG), max(MINW, w), layer=layer, rng=rng or RNG, a0=1.5, a1=2.5,
          erase=True)


# ------------------------------------------------------------------ light marks
LIGHTS = []    # dicts: x, h, z (world) ink, wm (metres of source width), k (strength), core


def light(x, h, z, ink, wm=0.4, k=1.0, core=None, kind='point', stretch=1.0, brk=0.18):
    LIGHTS.append(dict(x=x, h=h, z=z, ink=ink, wm=wm, k=k, core=core, kind=kind, stretch=stretch, brk=brk))


def halo(cx, cy, r, ink, rng=None, rings=2, w=None):
    """mist around a light: broken rings, never a glow"""
    rng = rng or RNG
    w = w or MINW
    for i in range(rings):
        rr = r * (1 + 0.62 * i) * rng.uniform(0.94, 1.06)
        a = rng.uniform(0, TAU)
        tot = 0
        while tot < TAU * rng.uniform(0.62, 0.8):
            span = rng.uniform(0.35, 1.0)
            pts = ell(cx, cy, rr, rr * rng.uniform(0.9, 1.0), n=max(4, int(span * rr / 5)), a0=a, a1=a + span, rng=rng)
            A.line(pts, w * (1 - 0.12 * i), layer=ink, rng=rng, wob=0.25, trem=0.2, a0=1.2, a1=2.2, pv=0.2)
            a += span + rng.uniform(0.25, 0.7)
            tot += span


def drizzle(poly, ink, rng=None, sp=15.0, L=(9, 17), ang=1.75, fade=None, w=None, prob=1.0):
    """fine slanted rain strokes, only inside poly (a lamp cone, a beam). fade(x, y) -> 0..1"""
    rng = rng or RNG
    w = w or MINW
    x0, y0, x1, y1 = bbox(poly)
    ux, uy = math.cos(ang), math.sin(ang)
    y = y0 + rng.uniform(0, sp)
    row = 0
    while y < y1:
        x = x0 + (sp * 0.5 if row % 2 else 0) + rng.uniform(0, sp * 0.5)
        while x < x1:
            px, py = x + rng.gauss(0, sp * 0.25), y + rng.gauss(0, sp * 0.25)
            if pip(px, py, poly):
                f = fade(px, py) if fade else 1.0
                if rng.random() < f * prob:
                    l = rng.uniform(*L) * (0.6 + 0.4 * f)
                    A.line([(px, py), (px + ux * l * 0.5, py + uy * l * 0.5), (px + ux * l, py + uy * l)],
                           w, layer=ink, rng=rng, wob=0.15, trem=0.0, a0=0.6, a1=2.0, pv=0.1)
            x += sp * rng.uniform(0.85, 1.25)
        y += sp * rng.uniform(0.75, 1.0)
        row += 1


def reflect_column(x, y0, y1, base, ink, rng=None, core=None, k=1.0, ymax=1468, wob=0.25, thick=None, brk=0.18, art=None):
    """a painterly wet-road reflection: tapered horizontal brush strokes stacked into a long broken vertical streak
    under a light, wobbling, breaking up, widening a little toward the viewer"""
    rng = rng or RNG
    art = art or RA
    y = y0
    ph, ph2 = rng.uniform(0, TAU), rng.uniform(0, TAU)
    span = max(1.0, min(y1, ymax) - y0)
    thick = thick or clamp(base * 0.16, MINW, 6.5)
    while y < min(y1, ymax):
        t = (y - y0) / span
        prof = smooth(min(1.0, t * 4 + 0.15)) * (1.0 - 0.55 * t)
        hl = base * prof * rng.uniform(0.45, 1.25) * k
        cxp = x + base * wob * (0.55 * math.sin(y * 0.045 + ph) + 0.45 * math.sin(y * 0.11 + ph2)) + rng.gauss(0, base * 0.12)
        th = thick * rng.uniform(0.85, 1.3) * (1 - 0.25 * t)
        if rng.random() > brk + 0.4 * t * t and hl > th * 0.9:
            sag = rng.gauss(0, th * 0.35)
            pts = [(cxp - hl, y + rng.gauss(0, 0.5)), (cxp, y + sag), (cxp + hl, y + rng.gauss(0, 0.5))]
            art.line(pts, max(MINW, th), layer=ink, rng=rng, wob=0.3, trem=0.15, a0=1.6, a1=2.6, pv=0.3)
            if core and t < 0.55 and rng.random() < 0.55 and hl * 0.45 > MINW:
                c = rng.uniform(-0.2, 0.2) * hl
                art.line([(cxp + c - hl * 0.4, y + 0.3), (cxp + c + hl * 0.4, y - 0.3)], max(MINW, th * 0.8), layer=core,
                       rng=rng, wob=0.2, trem=0.1, a0=1.2, a1=2.0, pv=0.2)
        y += max(th * 1.45, th + MINW * 1.05) * rng.uniform(1.0, 1.35) * (1 + 1.4 * t * t)


def reflect_light(L, rng=None, ymax=1468):
    """reflection of a registered light in the wet road (the mirror image below the ground point, stretched)"""
    rng = rng or RNG
    gx, gy = pr(L['x'], 0, L['z'])
    mx, my = pr(L['x'], -L['h'], L['z'])
    if gy > ymax:
        return
    base = clamp(L['wm'] * S(L['z']), 4.0, 46.0)
    length = (my - gy) * rng.uniform(1.5, 2.2) * L.get('stretch', 1.0) + base
    y0 = gy + clamp(0.06 * S(L['z']), 1.0, 8.0)
    reflect_column(gx, y0, y0 + length, base, L['ink'], rng, core=L.get('core'), k=L['k'], brk=L.get('brk', 0.18))


def lay_reflections():
    """put the reflections on the road, hidden wherever something stands"""
    inv = ImageChops.invert(OCC)
    for k in ORDER:
        A.L[k].paste(255, (0, 0), ImageChops.multiply(RA.L[k], inv))


# ------------------------------------------------------------------ finishing
def render(out_art, out_prev, mask=None, shifts=None):
    if mask is not None:
        for k in ORDER:
            A.L[k].paste(ImageChops.multiply(A.L[k], mask), (0, 0))
    shifts = shifts or {'blue': (2.2, 1.6), 'green': (1.6, -1.2), 'copper': (1.2, 1.6), 'amber': (-1.4, 1.0), 'ice': (-1.0, -1.4),
                        'yellow': (1.3, 0.9), 'key': (0, 0)}
    inks = A.finish(order=ORDER, shifts=shifts, spread_amt=0.16)
    rgba = composite(inks, PAL, ORDER)
    rgba.save(out_art)
    save_preview(rgba, '#151515', out_prev)
    return rgba
