#!/usr/bin/env python3
"""
hand.py: a pen that behaves like a hand, spot-colour screens, and honest print physics.
Pillow + numpy only. Lifted from the generators of the pieces in examples/ and made general.

Units: you draw in a unit space (default 1200 x 1600); the canvas is R px per unit (R=1 draft, R=3 full 3600 x 4800).

    from hand import Art, hatch_poly, halftone, clean, spread, grain, misregister, composite, save_preview
    art = Art(seed=7, layers=('key', 'amber', 'red'))
    art.line([(100, 100), (300, 140), (520, 90)], w=4)           # a pressure-varying brush line
    art.box([(400, 400), (700, 410), (690, 700), (405, 690)], 3) # a shape drawn edge by edge, corners overshooting
    art.blob([(420, 420), (680, 430), (670, 680), (420, 670)], 'amber')   # a loose spot-colour fill on its own screen
    inks = art.finish(order=('amber', 'red', 'key'), shifts={'amber': (3, 2), 'red': (-2, 3)})
    rgba = composite(inks, {'key': '#EFE6CF', 'amber': '#F0A640', 'red': '#E4432D'}, order=('amber', 'red', 'key'))
    rgba.save('art-black.png'); save_preview(rgba, '#151515', 'preview-black.png')

Everything here makes imperfection STRUCTURAL (how a mark is made), never a filter on top.
"""
import math, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

TAU = math.tau
R = float(os.environ.get('R', '3'))          # px per unit
UW, UH = int(os.environ.get('UW', 1200)), int(os.environ.get('UH', 1600))
W, H = int(round(UW * R)), int(round(UH * R))
MINW = float(os.environ.get('MINW', 3.4))    # minimum stroke width in units (3.4 u = ~10 px at R=3 = ~1 mm on a 38 cm print)


# ----------------------------------------------------------------- geometry
def smooth(t):
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return t * t * (3 - 2 * t)


def hexrgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def cumlen(pts):
    s = [0.0]
    for i in range(1, len(pts)):
        s.append(s[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
    return s


def normals(pts):
    n, out = len(pts), []
    for i in range(n):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy) or 1.0
        out.append((-dy / d, dx / d))
    return out


def catmull(pts, closed=False, step=1.4):
    """Catmull-Rom spline through pts, sampled every ~step units"""
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
        k = max(1, int(math.hypot(p2[0] - p1[0], p2[1] - p1[1]) / step))
        for j in range(k):
            t = j / k; t2 = t * t; t3 = t2 * t
            out.append(tuple(0.5 * (2 * p1[c] + (-p0[c] + p2[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t2 +
                                    (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t3) for c in (0, 1)))
    out.append(out[0] if closed else pts[-1])
    return out


def resample(pts, n):
    s = cumlen(pts)
    L = s[-1] or 1.0
    out, j = [], 0
    for i in range(n):
        t = L * i / n
        while j < len(s) - 2 and s[j + 1] < t:
            j += 1
        u = (t - s[j]) / ((s[j + 1] - s[j]) or 1.0)
        out.append((pts[j][0] + (pts[j + 1][0] - pts[j][0]) * u, pts[j][1] + (pts[j + 1][1] - pts[j][1]) * u))
    return out


def offset_path(pts, d):
    return [(p[0] + n[0] * d, p[1] + n[1] * d) for p, n in zip(pts, normals(pts))]


def clip_half(poly, nx, ny, c):
    """keep the part of a polygon with nx*x + ny*y <= c"""
    out, n = [], len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        da, db = nx * a[0] + ny * a[1] - c, nx * b[0] + ny * b[1] - c
        if da <= 0:
            out.append(a)
        if (da <= 0) != (db <= 0):
            t = da / (da - db)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def P(pts):
    """units -> px"""
    return [(x * R, y * R) for x, y in pts]


# ----------------------------------------------------------------- the pen
class Art:
    """A stack of binary ink layers (L images, 0/255) and a pen that draws on them like a hand."""

    def __init__(self, seed=1, layers=('key',)):
        self.layers = tuple(layers)
        self.L = {k: Image.new('L', (W, H), 0) for k in self.layers}
        self.D = {k: ImageDraw.Draw(v) for k, v in self.L.items()}
        self.rng = random.Random(seed)
        self.inside = None          # optional fn(x, y) -> bool: where the drawing still exists (vignette / ragged edge)
        self.marks = {}             # named points for the manifest

    # -- paths
    def hand(self, ctrl, closed=False, wob=0.6, trem=0.5, rng=None, step=1.4):
        """a hand-drawn version of the path through ctrl: jittered control points, spline, slow tremor"""
        rng = rng or self.rng
        c = [(x + rng.gauss(0, wob), y + rng.gauss(0, wob)) for x, y in ctrl]
        d = catmull(c, closed, step)
        if trem > 0 and len(d) > 4:
            s = cumlen(d)
            amp = trem * min(1.0, s[-1] / 50.0)
            comps = [(amp * rng.uniform(0.35, 1.0), TAU / rng.uniform(18, 95), rng.uniform(0, TAU)) for _ in range(3)]
            out = []
            for (x, y), (nx, ny), si in zip(d, normals(d), s):
                off = sum(a * math.sin(f * si + p) for a, f, p in comps)
                out.append((x + nx * off, y + ny * off))
            if closed:
                out[-1] = out[0]
            d = out
        return d

    # -- ink
    def _render(self, pts, w, layer, a0, a1, pv, rng, erase=False):
        """a pressure-varying stroke: swells and thins (pv), blob at the start (a0), taper at the lift (a1)"""
        runs = [pts]
        if self.inside:
            runs, cur = [], []
            for p in pts:
                if self.inside(*p):
                    cur.append(p)
                else:
                    if len(cur) > 1:
                        runs.append(cur)
                    cur = []
            if len(cur) > 1:
                runs.append(cur)
        draw, fill = self.D[layer], (0 if erase else 255)
        for run in runs:
            n = len(run)
            if n < 2:
                continue
            s = cumlen(run)
            L = s[-1] or 1e-6
            r0, r1 = min(L * 0.35, a0 * w), min(L * 0.45, a1 * w)
            f1, f2 = rng.uniform(0.7, 2.0), rng.uniform(2.5, 5.5)
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
            Pp = P(run)
            N = normals(Pp)
            Lp = [(Pp[i][0] + N[i][0] * ws[i], Pp[i][1] + N[i][1] * ws[i]) for i in range(n)]
            Rp = [(Pp[i][0] - N[i][0] * ws[i], Pp[i][1] - N[i][1] * ws[i]) for i in range(n)]
            CH = 9
            for a in range(0, n - 1, CH):
                b = min(n - 1, a + CH)
                draw.polygon(Lp[a:b + 1] + Rp[a:b + 1][::-1], fill=fill)
                if a > 0:
                    r = ws[a]
                    draw.ellipse((Pp[a][0] - r, Pp[a][1] - r, Pp[a][0] + r, Pp[a][1] + r), fill=fill)
            for i in (0, n - 1):
                r = ws[i]
                draw.ellipse((Pp[i][0] - r, Pp[i][1] - r, Pp[i][0] + r, Pp[i][1] + r), fill=fill)

    def ink(self, path, w, layer=None, closed=False, a0=1.6, a1=3.5, pv=0.2, redraw=0.0, rng=None, close_frac=None, erase=False):
        """ink an already-hand path. closed shapes stop short or run past their start; redraw = chance of a re-drawn pass"""
        rng = rng or self.rng
        layer = layer or self.layers[0]
        pts = list(path)
        if closed and len(pts) > 6:
            pts = pts[:-1]
            n = len(pts)
            k = rng.randrange(n)
            pts = pts[k:] + pts[:k]
            f = close_frac if close_frac is not None else rng.uniform(0.92, 1.07)
            if f < 1:
                pts = pts[:max(2, int(n * f))]
            else:
                ex = int(n * (f - 1))
                cx, cy = sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n
                pts = pts + [(x + (x - cx) * 0.035 * (i + 1) / max(ex, 1), y + (y - cy) * 0.035 * (i + 1) / max(ex, 1))
                             for i, (x, y) in enumerate(pts[:ex])]
        self._render(pts, w, layer, a0, a1, pv, rng, erase)
        if redraw and rng.random() < redraw and len(pts) > 12:
            n = len(pts)
            a = rng.randrange(0, n // 2)
            b = min(n, a + rng.randint(max(3, n // 5), max(4, n // 2)))
            seg = offset_path(pts[a:b], rng.choice((-1, 1)) * rng.uniform(0.5, 0.9) * w)
            self._render(seg, w * 0.72, layer, 1.0, 2.0, pv, rng, erase)

    def line(self, ctrl, w, layer=None, rng=None, wob=0.5, trem=0.4, closed=False, **kw):
        """the everyday call: a hand-drawn brush line through control points (units)"""
        rng = rng or self.rng
        p = self.hand(ctrl, closed=closed, wob=wob, trem=trem, rng=rng)
        self.ink(p, w, layer=layer, closed=closed, rng=rng, **kw)
        return p

    def carve(self, ctrl, w, layer=None, rng=None, **kw):
        """linocut: a gouge mark taken OUT of a layer (tapered both ends)"""
        rng = rng or self.rng
        p = self.hand(ctrl, wob=kw.pop('wob', 0.4), trem=kw.pop('trem', 0.3), rng=rng)
        self.ink(p, w, layer=layer, rng=rng, a0=kw.pop('a0', 2.5), a1=kw.pop('a1', 3.5), erase=True, **kw)

    def box(self, corners, w, layer=None, rng=None, over=(-1.2, 3.5), bow=0.01, wob=0.3, **kw):
        """polygon drawn edge by edge: corners overshoot or fall short, edges bow a little"""
        rng = rng or self.rng
        n = len(corners)
        for i in range(n):
            a, b = corners[i], corners[(i + 1) % n]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy) or 1
            ux, uy = dx / L, dy / L
            e0, e1 = rng.uniform(*over), rng.uniform(*over)
            a2, b2 = (a[0] - ux * e0, a[1] - uy * e0), (b[0] + ux * e1, b[1] + uy * e1)
            bw = rng.gauss(0, L * bow)
            m = ((a2[0] + b2[0]) / 2 - uy * bw, (a2[1] + b2[1]) / 2 + ux * bw)
            p = self.hand([a2, m, b2], wob=wob, trem=0.25 * min(1, L / 40), rng=rng)
            self.ink(p, w, layer=layer, rng=rng, a0=0.8, a1=1.5, pv=0.12, **kw)

    def dot(self, x, y, r, layer=None, rng=None):
        """a hand dot: an irregular 9-gon, never smaller than the minimum feature"""
        rng = rng or self.rng
        layer = layer or self.layers[0]
        r = max(r, MINW * 0.55)
        if self.inside and not self.inside(x, y):
            return
        ph = rng.uniform(0, TAU)
        pts = []
        for i in range(9):
            a = ph + TAU * i / 9
            rr = r * rng.uniform(0.82, 1.12)
            pts.append(((x + math.cos(a) * rr) * R, (y + math.sin(a) * rr * rng.uniform(0.85, 1.0)) * R))
        self.D[layer].polygon(pts, fill=255)

    def fill(self, poly, layer=None, value=255):
        """a hard fill (use blob for anything that should look printed by hand)"""
        if len(poly) > 2:
            self.D[layer or self.layers[0]].polygon(P(poly), fill=value)

    def add(self, layer, mask):
        """merge a mask (e.g. from halftone()) into a layer IN PLACE. Never assign art.L[k] = ...: the pen keeps drawing on
        the old image."""
        self.L[layer].paste(255, (0, 0), mask)

    def knock(self, poly, layers=None):
        """knock a shape out of layers (a silhouette in front of light)"""
        if len(poly) > 2:
            for k in (layers or self.layers):
                self.D[k].polygon(P(poly), fill=0)

    def blob(self, poly, layer, rng=None, scale=(0.95, 1.03), jit=0.08, shift=1.6, gap=0.35, n=34):
        """a loose spot-colour fill: wobbled, slightly scaled and shifted, sometimes leaving a gap on one side"""
        rng = rng or self.rng
        if len(poly) < 3:
            return
        pts = resample(list(poly) + [poly[0]], n)
        cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        size = max(max(xs) - min(xs), max(ys) - min(ys), 1)
        sc, j = rng.uniform(*scale), jit * size * 0.25
        pts = [(cx + (x - cx) * sc + rng.gauss(0, j), cy + (y - cy) * sc + rng.gauss(0, j)) for x, y in pts]
        pts = catmull(pts, closed=True, step=max(1.0, size / 60))
        dx, dy = rng.gauss(0, shift), rng.gauss(0, shift)
        pts = [(x + dx, y + dy) for x, y in pts]
        if rng.random() < gap:
            a = rng.uniform(0, TAU)
            nx, ny = math.cos(a), math.sin(a)
            pr = [nx * x + ny * y for x, y in pts]
            pts = clip_half(pts, nx, ny, min(pr) + (max(pr) - min(pr)) * rng.uniform(0.74, 0.93))
        if len(pts) > 2:
            self.D[layer].polygon(P(pts), fill=255)

    def masked(self, poly, layer, painter):
        """paint marks only inside poly: painter(art) draws onto a scratch Art sharing this rng"""
        tmp = Art(0, (layer,))
        tmp.rng = self.rng
        painter(tmp)
        m = Image.new('L', (W, H), 0)
        ImageDraw.Draw(m).polygon(P(poly), fill=255)
        self.L[layer].paste(255, (0, 0), ImageChops.multiply(m, tmp.L[layer]))

    def tube(self, ctrl, widths, rng=None, wob=0.6, trem=0.4):
        """outline of a limb: a hand spine with widths along it -> (spine, left edge, right edge)"""
        rng = rng or self.rng
        sp = self.hand(ctrl, wob=wob, trem=trem, rng=rng)
        s = cumlen(sp)
        L, k = s[-1] or 1, len(widths) - 1
        left, right = [], []
        for (x, y), (nx, ny), si in zip(sp, normals(sp), s):
            t = si / L * k
            i = min(int(t), k - 1)
            u = t - i
            ww = (widths[i] * (1 - u) + widths[i + 1] * u) / 2
            left.append((x + nx * ww, y + ny * ww))
            right.append((x - nx * ww, y - ny * ww))
        return sp, left, right

    def brush(self, ctrl, w, layer=None, rng=None, bristles=None, dry=0.35, **kw):
        """a dry brush: several bristle strokes side by side that break up toward the end (gouache, poster paint)"""
        rng = rng or self.rng
        sp = self.hand(ctrl, wob=kw.pop('wob', 0.5), trem=kw.pop('trem', 0.4), rng=rng)
        nb = bristles or max(2, int(w / (MINW * 1.1)))
        for b in range(nb):
            off = (b / max(nb - 1, 1) - 0.5) * w * 0.9 + rng.gauss(0, w * 0.04)
            seg = offset_path(sp, off)
            cut = 1 - dry * rng.random() * (1.4 if abs(off) > w * 0.3 else 0.6)
            seg = seg[:max(3, int(len(seg) * cut))]
            self.ink(seg, max(MINW, w / nb * rng.uniform(1.1, 1.5)), layer=layer, rng=rng, a0=0.6, a1=2.5, pv=0.25)

    # -- finishing
    def finish(self, order=None, shifts=None, minpx=None, trim=True, spread_amt=0.18):
        """ink spread on every edge, misregistration, later inks trim earlier ones, minimum-feature clean-up"""
        order = order or self.layers
        shifts = shifts or {}
        k = minpx or _kernel()
        rng = random.Random(self.rng.random())
        inks = {}
        for name in order:
            m = spread(self.L[name], rng, amt=spread_amt)
            m = misregister(m, *shifts.get(name, (0, 0)))
            inks[name] = m
        if trim:   # knockout: an ink printed later covers what's under it
            for i, a in enumerate(order):
                for b in order[i + 1:]:
                    inks[a] = ImageChops.subtract(inks[a], inks[b])
        for name in order:
            inks[name] = clean(inks[name], k)
        return inks


# ----------------------------------------------------------------- marks on fields
def hatch_poly(art, poly, layer, angle, spacing, w=None, rng=None, jit=0.35, gap=(0.0, 0.25)):
    """hand hatching clipped to poly: uneven spacing and angle, broken strokes"""
    rng = rng or art.rng
    w = w or MINW
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    rad = math.hypot(max(xs) - min(xs), max(ys) - min(ys)) / 2 + 4
    def painter(t):
        d = -rad
        while d < rad:
            a = angle + rng.gauss(0, 0.03)
            ux, uy = math.cos(a), math.sin(a)
            nx, ny = -uy, ux
            p0 = (cx + nx * d - ux * rad, cy + ny * d - uy * rad)
            p1 = (cx + nx * d + ux * rad, cy + ny * d + uy * rad)
            g0, g1 = rng.uniform(*gap), 1 - rng.uniform(*gap)
            q0 = (p0[0] + (p1[0] - p0[0]) * g0, p0[1] + (p1[1] - p0[1]) * g0)
            q1 = (p0[0] + (p1[0] - p0[0]) * g1, p0[1] + (p1[1] - p0[1]) * g1)
            t.line([q0, ((q0[0] + q1[0]) / 2, (q0[1] + q1[1]) / 2), q1], w, layer=layer, wob=0.4, trem=0.3)
            d += spacing * (1 + rng.uniform(-jit, jit))
    art.masked(poly, layer, painter)


def halftone(tone, cell=9.0, angle=0.3, rng=None, jitter=0.12, min_r=None):
    """coarse hand-set halftone from a tone field (L image at canvas size, 0..255): dots on a rotated, slightly irregular
    grid, radius from tone. Dots below the minimum feature are dropped, not shrunk. Returns a binary L image."""
    rng = rng or random.Random(3)
    min_r = min_r or MINW * 0.55
    out = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(out)
    t = np.asarray(tone, dtype=np.float32) / 255.0
    ca, sa = math.cos(angle), math.sin(angle)
    span = int(math.hypot(UW, UH) / cell) + 2
    cx, cy = UW / 2, UH / 2
    for i in range(-span // 2, span // 2 + 1):
        for j in range(-span // 2, span // 2 + 1):
            u, v = i * cell + rng.gauss(0, cell * jitter), j * cell + rng.gauss(0, cell * jitter)
            x, y = cx + u * ca - v * sa, cy + u * sa + v * ca
            if not (0 <= x < UW and 0 <= y < UH):
                continue
            val = t[min(H - 1, int(y * R)), min(W - 1, int(x * R))]
            r = cell * 0.62 * math.sqrt(val)
            if r < min_r:
                continue
            r *= rng.uniform(0.9, 1.08)
            d.ellipse(((x - r) * R, (y - r) * R, (x + r) * R, (y + r) * R), fill=255)
    return out


# ----------------------------------------------------------------- print physics
def noise(cell_u, rng, sigma=64):
    """smooth noise with feature size ~cell_u units, canvas size"""
    nw, nh = max(2, int(W / (cell_u * R))), max(2, int(H / (cell_u * R)))
    random.seed(rng.random())
    return Image.effect_noise((nw, nh), sigma).convert('L').resize((W, H), Image.BICUBIC)


def thr(img, t=128):
    return img.point(lambda p: 255 if p >= t else 0)


def spread(mask, rng, blur_u=0.38, amt=0.18, cell=1.6):
    """ink spread: soften the edge, push it with paper-tooth noise, re-threshold (edges stop being vector-perfect)"""
    b = mask.filter(ImageFilter.GaussianBlur(blur_u * R))
    return thr(Image.blend(b, noise(cell, rng, 70), amt), 128)


def grain(mask, rng, density=0.12, cell=None, starve_cell=70, starve=0.4):
    """riso/screen grain: holes in solids, more where the ink ran dry. Holes are kept coarse enough to print."""
    cell = cell or MINW * 1.4
    mix = Image.blend(noise(cell, rng, 55), noise(starve_cell, rng, 60), starve)
    t = int(128 - 75 * (0.5 - density) * 2)
    return ImageChops.subtract(mask, mix.point(lambda p: 255 if p < t * 0.66 else 0))


def _kernel():
    """odd kernel a little under the minimum stroke, so marks drawn at exactly MINW survive the opening"""
    k = max(3, int(MINW * R * 0.9))
    return k if k % 2 else k - 1


def clean(mask, k=None):
    """morphological opening a little under the minimum feature: removes specks and slivers the printer cannot hold"""
    k = k or _kernel()
    m = mask.filter(ImageFilter.MinFilter(k)).filter(ImageFilter.MaxFilter(k))
    return m


def misregister(mask, dx_u, dy_u):
    out = Image.new('L', mask.size, 0)
    out.paste(mask, (int(round(dx_u * R)), int(round(dy_u * R))))
    return out


def margin(mask, px=40):
    m = Image.new('L', mask.size, 0)
    ImageDraw.Draw(m).rectangle([px, px, mask.width - px, mask.height - px], fill=255)
    return ImageChops.multiply(mask, m)


def composite(inks, palette, order):
    """knockout composite: later inks on top. Binary alpha. palette: {ink: '#hex'}"""
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for k in order:
        out.paste(hexrgb(palette[k]) + (255,), (0, 0), margin(inks[k]))
    return out


def composite_overprint(inks, palette, order, paper='#FFFFFF'):
    """riso on paper: inks multiply where they cross. Binary alpha from the union of inks."""
    out = Image.new('RGB', (W, H), hexrgb(paper))
    alpha = Image.new('L', (W, H), 0)
    for k in order:
        layer = Image.new('RGB', (W, H), (255, 255, 255))
        m = margin(inks[k])
        layer.paste(hexrgb(palette[k]), (0, 0), m)
        out = ImageChops.multiply(out, layer)
        alpha = ImageChops.lighter(alpha, m)
    out.putalpha(alpha)
    return out


def save_preview(rgba, ground, path, size=(900, 1200)):
    bg = Image.new('RGBA', rgba.size, hexrgb(ground) + (255,))
    bg.alpha_composite(rgba)
    bg.convert('RGB').resize(size, Image.LANCZOS).save(path)
