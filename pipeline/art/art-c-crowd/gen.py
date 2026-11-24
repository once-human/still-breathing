#!/usr/bin/env python3
"""
still breathing / lineup 01 "again.." -- BENGALURU, design 03 "crowd"
"line drawings of the night", a different night: a cool december night on the
city's north-west edge.  The crowd on the NICE Grounds by BIEC, Madavara, seen
from behind, looking at the stage; behind it the Green Line viaduct ends at
Madavara (the end of the line), the long low exhibition halls, rain trees,
a lorry on Tumakuru Road.

Pen + print physics lifted from the Mumbai "lines" generator: one primitive,
a pressure-varying brush stroke along a jittered Catmull-Rom path, rendered
as filled polygons; spot inks are separate loose screens printed off-register,
with grain, minimum-feature clean-up and binary alpha.

Pillow + numpy-free.  Re-runnable:  python3 gen.py   (SEED=... to vary)
"""
import math, random, json, os, sys, time
from PIL import Image, ImageDraw, ImageFilter, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = int(os.environ.get('SEED', 121326))
S = 3                       # px per unit (units are 1200 x 1600)
UW, UH = 1200, 1600
W, H = UW * S, UH * S
MINW = 2.75                 # min stroke width, units (8.25 px)
TAU = math.tau
LAYERS = ('line', 'Y', 'G', 'B', 'H', 'Hx')   # Y yellow, G green, B accent blue; H/Hx unused on the black tee

PAL = {
    'black': {'tee': '#151515', 'line': '#F1E7D0', 'Y': '#F6B330', 'G': '#56B27C', 'B': '#4C66F5'},
}
# off-register offsets of each screen, in units
SHIFT = {'Y': (3.6, 2.9), 'G': (-3.1, 3.4), 'B': (1.4, -1.1), 'line': (0, 0)}


# ----------------------------------------------------------------- geometry
def hexrgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def smooth(t):
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return t * t * (3 - 2 * t)


def rotp(p, a, c):
    x, y = p[0] - c[0], p[1] - c[1]
    ca, sa = math.cos(a), math.sin(a)
    return (c[0] + x * ca - y * sa, c[1] + x * sa + y * ca)


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


def catmull(pts, closed=False, step=1.4):
    pts = list(pts)
    n = len(pts)
    if n == 1:
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


def resample(pts, n):
    s = cumlen(pts)
    L = s[-1] or 1.0
    out = []
    j = 0
    for i in range(n):
        t = L * i / n
        while j < len(s) - 2 and s[j + 1] < t:
            j += 1
        seg = (s[j + 1] - s[j]) or 1.0
        u = (t - s[j]) / seg
        out.append((pts[j][0] + (pts[j + 1][0] - pts[j][0]) * u, pts[j][1] + (pts[j + 1][1] - pts[j][1]) * u))
    return out


def clip_half(poly, nx, ny, c):
    """keep part of polygon with nx*x+ny*y <= c (Sutherland-Hodgman)"""
    out = []
    n = len(poly)
    for i in range(n):
        a = poly[i]
        b = poly[(i + 1) % n]
        da = nx * a[0] + ny * a[1] - c
        db = nx * b[0] + ny * b[1] - c
        if da <= 0:
            out.append(a)
        if (da <= 0) != (db <= 0):
            t = da / (da - db)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def offset_path(pts, d):
    N = normals(pts)
    return [(p[0] + n[0] * d, p[1] + n[1] * d) for p, n in zip(pts, N)]


def yfill(x):
    """colour stops above where the ink trails off"""
    return ybot(x) - 50 + 9 * math.sin(x * 0.029 + 0.7) + 5 * math.sin(x * 0.11 + 2.0)


OY = 0     # scene units == page units here


def vig_hw(yp, sg=1):
    """half-width of the drawing at page height yp; the left corner rounds off
    sooner than the right, like a page that was held at an angle"""
    y0 = 1010 if sg < 0 else 1110
    if yp < y0:
        return 582.0
    t = min(1.0, (yp - y0) / (660 if sg < 0 else 560))
    return 582.0 * (1 - t ** 2.6) ** (1 / 2.6)


def inside(x, y):
    """scene point -> still on the paper?"""
    yp = y + OY
    if yp > ybot(x):
        return False
    sg = -1 if x < 600 else 1
    return abs(x - 600) <= vig_hw(yp, sg) - 12 + 7 * math.sin(yp * 0.043 + x * 0.013) + 4 * math.sin(yp * 0.19)


def ybot(x):
    """the drawing trails off along this hand-ragged line at the bottom (lower on the right)"""
    return 1546 + 0.035 * (x - 600) + 14 * math.sin(x * 0.0083 + 2.3) + 8 * math.sin(x * 0.041 + 0.9) + 4 * math.sin(x * 0.13)


# ----------------------------------------------------------------- the pen
class Art:
    def __init__(self, seed):
        self.L = {k: Image.new('L', (W, H), 0) for k in LAYERS}
        self.D = {k: ImageDraw.Draw(v) for k, v in self.L.items()}
        self.rng = random.Random(seed)
        self.clip = True
        self.marks = {}          # named points for the manifest

    # -- paths
    def hand(self, ctrl, closed=False, wob=0.6, trem=0.5, rng=None, step=1.4):
        """a hand-drawn version of the path through ctrl: jitter, spline, tremor"""
        rng = rng or self.rng
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

    # -- ink
    def _render(self, pts, w, layer, a0, a1, pv, rng, draw=None, off=(0, 0), clip=None):
        draw = draw or self.D[layer]
        clip = self.clip if clip is None else clip
        runs = [pts]
        if clip:
            runs, cur = [], []
            for p in pts:
                if inside(p[0], p[1]):
                    cur.append(p)
                else:
                    if len(cur) > 1:
                        runs.append(cur)
                    cur = []
            if len(cur) > 1:
                runs.append(cur)
        ox, oy = off
        for run in runs:
            n = len(run)
            if n < 2:
                continue
            s = cumlen(run)
            L = s[-1] or 1e-6
            r0 = min(L * 0.35, a0 * w)
            r1 = min(L * 0.45, a1 * w)
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
                ws.append(max(MINW, base * p) * S * 0.5)
            P = [(x * S - ox, (y + OY) * S - oy) for x, y in run]
            N = normals(P)
            Lp = [(P[i][0] + N[i][0] * ws[i], P[i][1] + N[i][1] * ws[i]) for i in range(n)]
            Rp = [(P[i][0] - N[i][0] * ws[i], P[i][1] - N[i][1] * ws[i]) for i in range(n)]
            CH = 9
            for a in range(0, n - 1, CH):
                b = min(n - 1, a + CH)
                draw.polygon(Lp[a:b + 1] + Rp[a:b + 1][::-1], fill=255)
                if a > 0:
                    r = ws[a]
                    draw.ellipse((P[a][0] - r, P[a][1] - r, P[a][0] + r, P[a][1] + r), fill=255)
            for i in (0, n - 1):
                r = ws[i]
                draw.ellipse((P[i][0] - r, P[i][1] - r, P[i][0] + r, P[i][1] + r), fill=255)

    def ink(self, path, w, layer='line', closed=False, a0=1.6, a1=3.5, pv=0.2, redraw=0.0,
            rng=None, close_frac=None, dup=None, **kw):
        rng = rng or self.rng
        if dup:
            st = rng.getstate()
            self.ink(path, w, layer, closed, a0, a1, pv, redraw, rng, close_frac, **kw)
            rng.setstate(st)
            self.ink(path, w, dup, closed, a0, a1, pv, redraw, rng, close_frac, **kw)
            return
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
                cx = sum(p[0] for p in pts) / n
                cy = sum(p[1] for p in pts) / n
                ext = []
                for i, (x, y) in enumerate(pts[:ex]):
                    g = 0.035 * (i + 1) / max(ex, 1)
                    ext.append((x + (x - cx) * g, y + (y - cy) * g))
                pts = pts + ext
        self._render(pts, w, layer, a0, a1, pv, rng, **kw)
        if redraw and rng.random() < redraw and len(pts) > 12:
            n = len(pts)
            a = rng.randrange(0, n // 2)
            b = min(n, a + rng.randint(max(3, n // 5), max(4, n // 2)))
            seg = offset_path(pts[a:b], rng.choice((-1, 1)) * rng.uniform(0.5, 0.9) * w)
            self._render(seg, w * 0.72, layer, 1.0, 2.0, pv, rng, **kw)

    def line(self, ctrl, w, rng=None, wob=0.5, trem=0.4, layer='line', closed=False, **kw):
        rng = rng or self.rng
        p = self.hand(ctrl, closed=closed, wob=wob, trem=trem, rng=rng)
        self.ink(p, w, layer=layer, closed=closed, rng=rng, **kw)
        return p

    def dot(self, x, y, r, layer='line', rng=None):
        rng = rng or self.rng
        r = max(r, MINW * 0.55)
        if self.clip and not inside(x, y):
            return
        pts = []
        k = 9
        ph = rng.uniform(0, TAU)
        for i in range(k):
            a = ph + TAU * i / k
            rr = r * rng.uniform(0.82, 1.12)
            pts.append(((x + math.cos(a) * rr) * S, (y + OY + math.sin(a) * rr * rng.uniform(0.85, 1.0)) * S))
        self.D[layer].polygon(pts, fill=255)

    def hfill(self, poly):
        if len(poly) > 2:
            self.D['H'].polygon([(x * S, (y + OY) * S) for x, y in poly], fill=255)

    def knock(self, poly, layers=LAYERS):
        if len(poly) < 3:
            return
        p = [(x * S, (y + OY) * S) for x, y in poly]
        for k in layers:
            self.D[k].polygon(p, fill=0)

    def box(self, corners, w, rng=None, over=(-1.2, 3.5), bow=0.01, layer='line', wob=0.3, **kw):
        """polygon drawn edge by edge: corners overshoot or fall short"""
        rng = rng or self.rng
        n = len(corners)
        for i in range(n):
            a = corners[i]
            b = corners[(i + 1) % n]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy) or 1
            ux, uy = dx / L, dy / L
            e0, e1 = rng.uniform(*over), rng.uniform(*over)
            a2 = (a[0] - ux * e0, a[1] - uy * e0)
            b2 = (b[0] + ux * e1, b[1] + uy * e1)
            bw = rng.gauss(0, L * bow)
            m = ((a2[0] + b2[0]) / 2 - uy * bw, (a2[1] + b2[1]) / 2 + ux * bw)
            p = self.hand([a2, m, b2], wob=wob, trem=0.25 * min(1, L / 40), rng=rng)
            self.ink(p, w, layer=layer, rng=rng, a0=0.8, a1=1.5, pv=0.12, **kw)

    # -- spot colour
    def blob(self, poly, layer, rng=None, scale=(0.95, 1.03), jit=0.08, shift=1.6, gap=0.35, n=34):
        rng = rng or self.rng
        if len(poly) < 3 or not layer:
            return
        pts = resample(list(poly) + [poly[0]], n)
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        size = max(max(xs) - min(xs), max(ys) - min(ys), 1)
        sc = rng.uniform(*scale)
        j = jit * size * 0.25
        pts = [(cx + (x - cx) * sc + rng.gauss(0, j), cy + (y - cy) * sc + rng.gauss(0, j)) for x, y in pts]
        pts = catmull(pts, closed=True, step=max(1.0, size / 60))
        dx, dy = rng.gauss(0, shift), rng.gauss(0, shift)
        pts = [(x + dx, y + dy) for x, y in pts]
        if rng.random() < gap:
            a = rng.uniform(0, TAU)
            nx, ny = math.cos(a), math.sin(a)
            pr = [nx * x + ny * y for x, y in pts]
            c = min(pr) + (max(pr) - min(pr)) * rng.uniform(0.74, 0.93)
            pts = clip_half(pts, nx, ny, c)
            if len(pts) > 4:
                pts = resample(pts + [pts[0]], max(12, n))
                pts = [(x + rng.gauss(0, j * 0.6), y + rng.gauss(0, j * 0.6)) for x, y in pts]
        if self.clip:
            lim = rng.uniform(-28, 6)
            pts = [(x, min(y, yfill(x) - OY + lim)) for x, y in pts]
        if len(pts) > 2:
            self.D[layer].polygon([(x * S, (y + OY) * S) for x, y in pts], fill=255)

    def masked(self, poly, layer, painter):
        """paint strokes (painter(draw, off)) only inside poly"""
        P = [(x * S, (y + OY) * S) for x, y in poly]
        x0 = int(max(0, min(p[0] for p in P) - 4)); y0 = int(max(0, min(p[1] for p in P) - 4))
        x1 = int(min(W, max(p[0] for p in P) + 4)); y1 = int(min(H, max(p[1] for p in P) + 4))
        if x1 - x0 < 3 or y1 - y0 < 3:
            return
        m = Image.new('L', (x1 - x0, y1 - y0), 0)
        ImageDraw.Draw(m).polygon([(x - x0, y - y0) for x, y in P], fill=255)
        t = Image.new('L', m.size, 0)
        painter(ImageDraw.Draw(t), (x0, y0))
        self.L[layer].paste(255, (x0, y0), ImageChops.multiply(m, t))

    # -- tube (arms, legs)
    def tube(self, ctrl, widths, lw, rng, wob=0.6, trem=0.4):
        sp = self.hand(ctrl, wob=wob, trem=trem, rng=rng)
        s = cumlen(sp)
        L = s[-1] or 1
        N = normals(sp)
        k = len(widths) - 1
        left, right = [], []
        for (x, y), (nx, ny), si in zip(sp, N, s):
            t = si / L * k
            i = min(int(t), k - 1)
            u = t - i
            ww = (widths[i] * (1 - u) + widths[i + 1] * u) / 2
            left.append((x + nx * ww, y + ny * ww))
            right.append((x - nx * ww, y - ny * ww))
        return sp, left, right


# ----------------------------------------------------------------- hands
def hand_outline(kind, rng, splay=1.0):
    """hand outline in local coords: v across (-0.5..0.5), u along fingers (0 = wrist).
    returns list of ctrl points (open: starts at wrist left, ends wrist right) + extra lines"""
    extra = []
    if kind == 'open':
        fl = [0.36, 0.47, 0.50, 0.42]
        fv = [-0.24, -0.08, 0.08, 0.23]
        pts = [(-0.27, 0.0), (-0.31, 0.22)]
        fw = 0.16
        for i in range(4):
            ang = (i - 1.5) * 0.12 * splay + rng.gauss(0, 0.04)
            bx, by = fv[i], 0.42
            L = fl[i] * rng.uniform(0.9, 1.08)
            tip = (bx + math.sin(ang) * L, by + math.cos(ang) * L)
            pts.append((bx - fw / 2 + math.sin(ang) * 0.05, by + 0.04))
            pts.append((tip[0] - fw * 0.45 * math.cos(ang), tip[1] - 0.05))
            pts.append((tip[0] + math.sin(ang) * 0.04, tip[1] + 0.03))
            pts.append((tip[0] + fw * 0.45 * math.cos(ang), tip[1] - 0.05))
            pts.append((bx + fw / 2 + math.sin(ang) * 0.05, by + 0.02))
        pts += [(0.31, 0.36), (0.47, 0.5), (0.53, 0.47), (0.36, 0.2), (0.27, 0.0)]
        return pts, extra
    if kind == 'fist':
        pts = [(-0.27, 0.0), (-0.32, 0.25), (-0.31, 0.47), (-0.18, 0.56), (0.0, 0.57), (0.18, 0.56), (0.33, 0.45), (0.36, 0.22), (0.27, 0.0)]
        for v in (-0.15, 0.02, 0.17):
            extra.append([(v, 0.56), (v + 0.02, 0.44)])
        return pts, extra
    if kind == 'peace':
        pts = [(-0.27, 0.0), (-0.32, 0.25), (-0.30, 0.44), (-0.12, 0.47),
               (-0.20, 0.95), (-0.12, 1.0), (-0.03, 0.95), (-0.01, 0.5),
               (0.04, 0.95), (0.12, 1.0), (0.19, 0.93), (0.12, 0.46),
               (0.30, 0.42), (0.35, 0.2), (0.27, 0.0)]
        extra.append([(-0.28, 0.44), (-0.05, 0.40)])
        return pts, extra
    if kind == 'point':
        pts = [(-0.27, 0.0), (-0.32, 0.25), (-0.30, 0.45), (-0.06, 0.5), (-0.06, 1.0), (0.03, 1.05), (0.09, 0.98), (0.10, 0.52),
               (0.30, 0.45), (0.35, 0.2), (0.27, 0.0)]
        extra.append([(-0.27, 0.44), (-0.08, 0.40)])
        return pts, extra
    # mitten
    pts = [(-0.27, 0.0), (-0.33, 0.3), (-0.25, 0.62), (0.0, 0.7), (0.22, 0.6), (0.3, 0.4), (0.45, 0.42), (0.36, 0.15), (0.27, 0.0)]
    return pts, extra


# ----------------------------------------------------------------- scene
class Scene(Art):

    # ---- people ---------------------------------------------------------
    def rays(self, x, y, r0, r1, n, rng, w=MINW, layer='Y', skip_down=True):
        """a phone torch seen from behind: light spilling out round the edges, drawn as uneven rays"""
        ph = rng.uniform(0, TAU)
        for i in range(n):
            a = ph + TAU * i / n + rng.gauss(0, 0.12)
            if skip_down and 0.55 < math.sin(a):
                continue
            ra = r0 * rng.uniform(0.9, 1.25)
            rb = r1 * rng.uniform(0.45, 1.0) * (1.15 if i % 2 else 0.8)
            if rb - ra < 4:
                continue
            p0 = (x + math.cos(a) * ra, y + math.sin(a) * ra)
            p1 = (x + math.cos(a) * rb, y + math.sin(a) * rb)
            self.line([p0, ((p0[0] + p1[0]) / 2 + rng.gauss(0, 0.6), (p0[1] + p1[1]) / 2 + rng.gauss(0, 0.6)), p1], w, rng=rng, layer=layer,
                      wob=0.3, trem=0.2, a0=0.5, a1=2.0, pv=0.25)

    def draw_hand(self, pos, ang, size, kind, lw, rng, fill=None):
        """pos = wrist, ang = direction fingers point (radians), size = hand length"""
        ca, sa = math.cos(ang), math.sin(ang)

        def T(v, u):  # local -> world. u along ang, v perpendicular
            return (pos[0] + u * size * ca - v * size * sa, pos[1] + u * size * sa + v * size * ca)
        pts, extra = hand_outline(kind, rng)
        ctrl = [T(v, u) for v, u in pts]
        p = self.hand(ctrl, wob=size * 0.02, trem=size * 0.01, rng=rng, step=1.0)
        self.knock(p)
        self.ink(p, lw, rng=rng, a0=1.0, a1=2.0, redraw=0.08)
        for e in extra:
            self.line([T(v, u) for v, u in e], lw * 0.85, rng=rng, wob=size * 0.01, trem=0)
        return T

    def phone(self, pos, ang, size, lw, rng, screen='G', content=True, rec=False, land=False):
        """phone held up at pos (hand), screen facing us; size = phone height.
        people hold phones near upright (or landscape), whatever the forearm does"""
        fa = ang
        ang = -math.pi / 2 + max(-0.38, min(0.38, (fa + math.pi / 2) * 0.35)) + rng.gauss(0, 0.06)
        ctr = (pos[0] + math.cos(fa) * size * (0.3 if land else 0.42), pos[1] + math.sin(fa) * size * (0.3 if land else 0.42))
        if land:
            ang += math.pi / 2
        ca, sa = math.cos(ang), math.sin(ang)
        pw = size * 0.52

        def T(v, u):  # u along ang (phone long axis), v across
            return (ctr[0] + u * size * ca - v * size * sa, ctr[1] + u * size * sa + v * size * ca)
        hw, hh, r = pw / size / 2, 0.5, 0.07
        ctrl = [(-hw + r, -hh), (hw - r, -hh), (hw, -hh + r), (hw, hh - r), (hw - r, hh), (-hw + r, hh), (-hw, hh - r), (-hw, -hh + r)]
        outline = self.hand([T(v, u) for v, u in ctrl], closed=True, wob=size * 0.008, trem=size * 0.004, rng=rng, step=1.0)
        self.knock(outline)
        inset = 0.06
        scr = [T(-hw + inset, -hh + inset * 1.3), T(hw - inset, -hh + inset * 1.3), T(hw - inset, hh - inset * 1.6), T(-hw + inset, hh - inset * 1.6)]
        if screen:
            self.blob(scr, screen, rng=rng, scale=(0.97, 1.04), jit=0.03, shift=size * 0.015, gap=0.15)
        # thumb + fingers wrapping the sides (we see the screen side)
        if size > 14:
            for sg, us in ((-1, (-0.08, 0.12)), (1, (-0.18, -0.02, 0.14))):
                for u in us:
                    a = T(sg * hw * 0.98, u - 0.04)
                    b = T(sg * (hw + 0.07), u)
                    c = T(sg * hw * 0.98, u + 0.05)
                    q = self.hand([a, b, c], wob=0, trem=0, rng=rng, step=0.8)
                    self.knock(q + [a])
                    self.ink(q, lw * 0.8, rng=rng, a0=0.5, a1=0.8)
        self.ink(outline, lw, closed=True, rng=rng, a0=0.6, a1=1.2, pv=0.1, close_frac=rng.uniform(0.97, 1.05))
        if content and size > 40 and not land:
            # the stage, tiny, on the screen
            k = 0.85
            self.line([T(-0.17 * k, 0.12), T(0.17 * k, 0.12)], lw * 0.7, rng=rng, wob=0.2, trem=0)
            self.line([T(-0.15 * k, 0.12), T(-0.15 * k, -0.12)], lw * 0.7, rng=rng, wob=0.2, trem=0)
            self.line([T(0.15 * k, 0.12), T(0.15 * k, -0.12)], lw * 0.7, rng=rng, wob=0.2, trem=0)
            self.line([T(-0.17 * k, -0.12), T(0.0, -0.135), T(0.17 * k, -0.12)], lw * 0.7, rng=rng, wob=0.2, trem=0)
            x, y = T(0.0, 0.07)
            self.dot(x, y, size * 0.025)
            for a in (-0.5, 0.0, 0.5):
                self.line([T(0.0, -0.13), T(0.12 * math.sin(a) * 2.2, -0.36)], lw * 0.6, rng=rng, wob=0.2, trem=0, layer='Y')
        if rec:
            x, y = T(-hw + 0.12, -hh + 0.11)
            self.dot(x, y, max(size * 0.035, 1.9), layer='B', rng=rng)
        return ctr

    def person(self, cx, cy, w, lw, rng, o=None):
        """a person from behind. cx,cy = head centre, w = head width (units)"""
        o = o or {}
        h = w * (o.get('hr') or rng.uniform(1.07, 1.19))
        tilt = math.radians(o.get('tilt', 0.0))
        piv = (cx, cy + 0.6 * h)

        def HP(x, y):
            return rotp((cx + x * w, cy + y * h), tilt, piv)
        lean = o.get('lean', 0.0)

        def BP(x, y):
            return (cx + (x + lean * (y - 0.6)) * w, cy + y * h)
        sw = o.get('sw', rng.uniform(1.15, 1.42))
        yend = o.get('yend', 3.4)
        det = w >= 26
        big = w >= 60
        wob = 0.014 * w
        tr = 0.010 * w
        hair = o.get('hair') or rng.choice(['short', 'short', 'long', 'long', 'long', 'ponytail', 'bun', 'curly', 'cap', 'buzz', 'braid',
                                             'hood', 'hood', 'hood', 'beanie', 'beanie', 'beanie', 'monkeycap', 'short', 'long'])
        garment = o.get('garment') or rng.choice(['hoodie', 'hoodie', 'hoodie', 'jacket', 'jacket', 'tee', 'shirt', 'kurta', 'shawl', 'muffler',
                                                  'muffler', 'tee', 'jacket'])
        if hair == 'hood':
            garment = 'hoodie'
            o['hood_up'] = True
        if garment == 'shawl' and hair in ('cap', 'buzz'):
            hair = 'long'
        gfill = o.get('gfill', 'auto')
        if gfill == 'auto':
            rr = rng.random()
            gfill = 'Y' if rr < 0.09 else 'G' if rr < 0.22 else None
        o['_gfill'] = gfill
        arms = o.get('arms', {})

        # ---------------- body
        def side(sg):
            raised = sg in arms
            pts = [(sg * 0.235, 0.55), (sg * 0.265, 0.78), (sg * 0.52, 0.895), (sg * sw * 0.86, 0.975), (sg * sw, 1.13),
                   (sg * sw * 1.03, 1.55), (sg * sw * 0.99, 2.3), (sg * sw * 1.01, yend)]
            if raised:
                pts[3] = (sg * sw * 0.86, 0.95)
            return [BP(x + rng.gauss(0, 0.012), y + rng.gauss(0, 0.01)) for x, y in pts]
        Ld = self.hand(side(-1), wob=wob * 0.5, trem=tr, rng=rng)
        Rd = self.hand(side(1), wob=wob * 0.5, trem=tr, rng=rng)
        body = Ld + Rd[::-1]
        if not o.get('nobody'):
            self.knock(body)
            torso = [p for p in Ld if p[1] > cy + 0.80 * h] + [p for p in Rd[::-1] if p[1] > cy + 0.80 * h]
            if gfill and garment not in ('tank', 'shawl'):
                self.blob(torso, gfill, rng=rng, scale=(0.94, 1.02), shift=0.03 * w)
            trail = o.get('trail', True)
            for sg, d in ((-1, Ld), (1, Rd)):
                if trail:
                    ycut = cy + h * (rng.uniform(2.4, 3.2) if w > 45 else rng.uniform(1.8, 2.5))
                    d = [p for p in d if p[1] < ycut]
                    if len(d) < 4:
                        continue
                if rng.random() < 0.25 and det:
                    k = int(len(d) * rng.uniform(0.25, 0.35))
                    self.ink(d[:k + 2], lw, rng=rng, a1=1.5)
                    self.ink(d[k - 1:], lw, rng=rng, a0=1.0)
                else:
                    self.ink(d, lw, rng=rng, redraw=0.3 if big else 0.05)
            self._o = o
            self.garment(garment, BP, w, h, sw, lw, rng, det, big, arms, gfill, o.get('trail', True))

        # ---------------- raised arms (behind the head)
        for sg, kind in arms.items():
            self.raised_arm(sg, kind, cx, cy, w, h, sw, BP, lw, rng, garment, gfill, o)

        # ---------------- head + hair
        self.head_back(HP, cx, cy, w, h, lw, rng, hair, det, big, o)

    def garment(self, g, BP, w, h, sw, lw, rng, det, big, arms, gfill, o_trail=True):
        L = lambda pts, k=1.0, **kw: self.line([BP(x, y) for x, y in pts], lw * k, rng=rng, wob=0.012 * w, trem=0.006 * w, **kw)
        # arm separation / sleeve on hanging arms
        if det:
            for sg in (-1, 1):
                if sg in arms:
                    continue
                L([(sg * sw * 0.80, 1.5), (sg * sw * 0.81, 1.8), (sg * sw * 0.80, rng.uniform(1.95, 2.3))], 0.9, a0=0.6, a1=4.0)
                if g in ('tee', 'kurta') and rng.random() < 0.8 and (w > 45 or not o_trail):
                    L([(sg * sw * 1.05, 1.78), (sg * sw * 0.93, 1.80), (sg * sw * 0.82, 1.83)], 0.85)
        if g == 'tee':
            L([(-0.29, 0.80), (-0.12, 0.88), (0.0, 0.895), (0.14, 0.875), (0.29, 0.80)])
            if big:
                L([(-0.33, 0.86), (0.0, 0.96), (0.32, 0.86)], 0.7)
        elif g == 'hoodie':
            if not self._o.get('hood_up'):
                L([(-0.62, 0.85), (-0.55, 1.12), (-0.25, 1.36), (0.0, 1.42), (0.25, 1.35), (0.55, 1.1), (0.63, 0.85)])
                if det:
                    L([(-0.33, 0.94), (-0.1, 1.12), (0.12, 1.12), (0.32, 0.95)], 0.8)
            if big:
                L([(-sw * 0.95, 2.55), (0, 2.6), (sw * 0.95, 2.55)], 0.7)
        elif g == 'shawl':
            # a shawl over the shoulders, its point hanging down the back; border + fringe
            lx = rng.uniform(-0.12, 0.12)
            ln = rng.uniform(2.1, 2.7)
            out = [(-sw * 1.02, 1.05), (-0.6, 0.86), (0.0, 0.84), (0.6, 0.86), (sw * 1.02, 1.05), (sw * 0.98, 1.7), (lx + 0.3, ln - 0.15), (lx, ln), (lx - 0.3, ln - 0.15), (-sw * 0.98, 1.7)]
            sc = self._o.get('shawlfill', gfill if gfill else rng.choice(['Y', 'G', None, None]))
            if sc:
                self.blob([BP(x, y) for x, y in out], sc, rng=rng, shift=0.03 * w, gap=0.25)
            L([(-sw * 1.02, 1.62), (-sw * 0.5, 1.95), (lx - 0.3, ln - 0.15), (lx, ln)], 1.0, redraw=0.15)
            L([(sw * 1.02, 1.62), (sw * 0.5, 1.95), (lx + 0.3, ln - 0.15), (lx, ln)], 1.0)
            L([(-0.58, 0.88), (0.0, 0.86), (0.6, 0.89)], 0.85)
            if det:
                L([(-sw * 0.92, 1.72), (-sw * 0.45, 2.02), (lx - 0.22, ln - 0.27), (lx, ln - 0.13)], 0.6, a0=0.5, a1=1.0)
                L([(sw * 0.92, 1.72), (sw * 0.45, 2.02), (lx + 0.22, ln - 0.27), (lx, ln - 0.13)], 0.6, a0=0.5, a1=1.0)
                for i in range(7):
                    t = (i + 0.5) / 7
                    for sg in (-1, 1):
                        x0, y0 = sg * sw * 0.5 * (1 - t) + lx * t + sg * 0.3 * t * (1 - t), 1.95 + (ln - 1.95) * t
                        if rng.random() < 0.8:
                            L([(x0, y0 + 0.02), (x0 + sg * 0.02, y0 + 0.13)], 0.55, a0=0.2, a1=0.4)
        elif g == 'muffler':
            mc = self._o.get('mufflerfill', rng.choice(['Y', 'G', 'G', None]))
            band = [(-0.36, 0.72), (0.0, 0.79), (0.36, 0.72), (0.42, 0.86), (0.0, 0.96), (-0.42, 0.86)]
            sgm = rng.choice((-1, 1))
            tl = rng.uniform(1.6, 2.1)
            tail = [(sgm * 0.18, 0.86), (sgm * 0.36, 0.86), (sgm * 0.40, tl), (sgm * 0.14, tl + 0.03)]
            P_ = [BP(x, y) for x, y in band]
            T_ = [BP(x, y) for x, y in tail]
            self.knock(P_); self.knock(T_)
            if mc:
                self.blob(P_, mc, rng=rng, shift=0.02 * w, gap=0.1)
                self.blob(T_, mc, rng=rng, shift=0.02 * w, gap=0.1)
            L(band[:3], 0.9)
            L(band[3:], 0.9)
            L(tail[:3], 0.85)
            L([tail[3], tail[0]], 0.85)
            L([tail[2], tail[3]], 0.8)
            if det:
                for i in range(4):
                    fx = tail[2][0] + (tail[3][0] - tail[2][0]) * (i + 0.5) / 4
                    fy = tl + 0.015 * i
                    L([(fx, fy), (fx + rng.gauss(0, 0.02), fy + 0.14)], 0.55, a0=0.2, a1=0.4)
                if w > 40:
                    for i in range(3):
                        t = 0.3 + 0.2 * i
                        L([(sgm * 0.19, 0.86 + (tl - 0.86) * t), (sgm * 0.37, 0.86 + (tl - 0.86) * t)], 0.5, a0=0.3, a1=0.5)
        elif g == 'shirt':
            L([(-0.29, 0.78), (0.0, 0.84), (0.29, 0.78)])
            L([(-0.47, 0.86), (-0.2, 0.96), (0.0, 0.99), (0.22, 0.95), (0.46, 0.85)])
            if det:
                L([(-sw * 0.93, 1.26), (0.0, 1.33), (sw * 0.93, 1.26)], 0.85)
                L([(-0.05, 1.33), (-0.06, 1.7)], 0.7)
                L([(0.07, 1.33), (0.08, 1.66)], 0.7)
        elif g == 'kurta':
            L([(-0.27, 0.77), (0.0, 0.83), (0.27, 0.77)])
            L([(-0.3, 0.86), (0.0, 0.93), (0.3, 0.86)], 0.9)
            if det:
                for i in range(7):
                    t = (i + 0.5) / 7
                    x = -0.3 + 0.6 * t
                    y = 0.90 + 0.07 * (1 - (2 * t - 1) ** 2) + 0.08
                    px, py = BP(x, y)
                    self.dot(px, py, max(0.022 * w, 1.6), rng=rng)
                L([(-0.45, 1.6), (-0.5, 2.3), (-0.48, 2.9)], 0.7)
                L([(0.4, 1.7), (0.45, 2.6)], 0.7)
        elif g == 'tank':
            L([(-0.40, 0.86), (-0.32, 1.25), (-0.12, 1.42), (0.12, 1.42), (0.32, 1.25), (0.41, 0.86)])
            for sg in (-1, 1):
                L([(sg * 0.66, 0.92), (sg * sw * 0.86, 1.32), (sg * sw * 0.98, 1.62)])
            poly = [BP(x, y) for x, y in [(-0.40, 0.88), (-0.32, 1.25), (0, 1.43), (0.32, 1.25), (0.41, 0.88), (0.66, 0.93), (sw * 0.86, 1.32),
                                          (sw * 1.02, 1.62), (sw * 1.06, 3.3), (-sw * 1.06, 3.3), (-sw * 1.02, 1.62), (-sw * 0.86, 1.32), (-0.66, 0.93)]]
            if gfill:
                self.blob(poly, gfill, rng=rng, shift=0.03 * w)
            if big:
                L([(-0.25, 1.0), (-0.18, 1.18)], 0.7)
                L([(0.22, 1.0), (0.16, 1.2)], 0.7)
        elif g == 'jacket':
            L([(-0.56, 0.83), (-0.35, 1.0), (0.0, 1.07), (0.36, 1.0), (0.57, 0.83)])
            if det:
                L([(-sw * 0.96, 1.32), (-0.4, 1.4), (0.0, 1.58), (0.4, 1.4), (sw * 0.96, 1.32)], 0.85)
                L([(-sw * 0.96, 1.42), (-0.4, 1.5), (0.0, 1.68), (0.4, 1.5), (sw * 0.96, 1.42)], 0.6)

    def raised_arm(self, sg, kind, cx, cy, w, h, sw, BP, lw, rng, garment, gfill, o):
        Sx, Sy = BP(sg * sw * 0.80, 1.04)
        ao = o.get('arm_' + str(sg), {})
        if kind in ('phone', 'torch'):
            wr = ao.get('wrist') or (cx + sg * w * rng.uniform(0.25, 0.65), cy - h * rng.uniform(1.0, 1.45))
            el = ao.get('elbow') or (Sx + sg * w * rng.uniform(0.25, 0.55), (Sy + wr[1]) / 2 + h * 0.15)
        else:
            wr = ao.get('wrist') or (cx + sg * w * rng.uniform(0.55, 1.35), cy - h * rng.uniform(0.95, 1.8))
            el = ao.get('elbow') or (Sx + sg * w * rng.uniform(0.3, 0.75), (Sy + wr[1]) / 2 + h * rng.uniform(0.0, 0.25))
        ws = [0.42 * w, 0.33 * w, 0.25 * w]
        bx, by = Sx - (el[0] - Sx) * 0.18, Sy - (el[1] - Sy) * 0.18
        sp, left, right = self.tube([(bx, by), (Sx, Sy), el, wr], ws, lw, rng, wob=0.01 * w, trem=0.008 * w)
        sil = left + right[::-1]
        self.knock(sil)
        longs = garment in ('hoodie', 'shirt', 'kurta', 'jacket')
        if gfill and garment != 'tank':
            if longs:
                self.blob(sil[:], gfill, rng=rng, shift=0.03 * w, gap=0.5)
            else:
                n = len(left)
                k = int(n * 0.3)
                self.blob(left[:k] + right[:k][::-1], gfill, rng=rng, shift=0.03 * w, gap=0.2)
        self.ink(left, lw, rng=rng, a0=0.5)
        self.ink(right, lw, rng=rng, a0=0.5)
        n = len(sp)
        if w >= 26:
            # sleeve edge / cuff
            k = int(n * (0.82 if longs else 0.33))
            a, b = left[k], right[k]
            m = ((a[0] + b[0]) / 2 + rng.gauss(0, 0.02 * w), (a[1] + b[1]) / 2 + 0.03 * w)
            self.line([a, m, b], lw * 0.85, rng=rng, wob=0.01 * w, trem=0)
            # elbow crease
            k = int(n * 0.55)
            x, y = sp[k]
            self.line([(x - sg * 0.02 * w, y - 0.03 * w), (x + sg * 0.05 * w, y + 0.02 * w)], lw * 0.7, rng=rng, wob=0.004 * w, trem=0)
        # hand
        ex, ey = sp[-1]
        px, py = sp[-4]
        ang = math.atan2(ey - py, ex - px)
        if kind == 'torch':
            psize = ao.get('psize') or w * rng.uniform(0.75, 0.95)
            c = self.phone((ex, ey), ang, psize, lw * 0.9, rng, screen=ao.get('screen', None), content=False, rec=False, land=False)
            self.rays(c[0], c[1] - psize * 0.42, psize * 0.42, psize * ao.get('reach', 1.25), ao.get('nray', 13 if w > 60 else 9), rng,
                      w=lw * 0.8 if w > 60 else MINW)
            if w > 30:
                self.dot(c[0] + rng.gauss(0, 0.04 * psize), c[1] - psize * 0.36, max(psize * 0.06, 2.0), layer='line', rng=rng)
        elif kind == 'phone':
            psize = ao.get('psize') or w * rng.uniform(0.8, 1.0)
            self.phone((ex, ey), ang, psize, lw * 0.9, rng, screen=ao.get('screen', 'Y' if rng.random() < 0.7 else 'G'),
                       content=ao.get('content', True), rec=ao.get('rec', rng.random() < 0.25), land=ao.get('land', w > 30 and rng.random() < 0.12))
        else:
            if w < 55 and kind in ('open', 'peace', 'point'):
                kind = rng.choice(['mitten', 'fist'])
            self.draw_hand((ex, ey), ang, w * (0.55 if kind == 'open' else 0.45), kind, lw * 0.8, rng)
            if ao.get('bangles'):
                for i, t in enumerate((0.82, 0.88, 0.93)):
                    k = int(n * t)
                    a, b = left[k], right[k]
                    m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.035 * w)
                    self.line([a, m, b], lw * 0.7, rng=rng, wob=0.005 * w, trem=0, layer=('B' if i == 1 else 'line'))

    def head_back(self, HP, cx, cy, w, h, lw, rng, hair, det, big, o):
        ear = rng.uniform(0.06, 0.10)
        nz = lambda: rng.gauss(0, 0.012)
        base = [(-0.235, 0.58), (-0.39, 0.37), (-0.48, 0.265), (-0.48 - ear, 0.13), (-0.51, -0.02), (-0.47, -0.27), (-0.30, -0.46), (0.0, -0.53),
                (0.30, -0.46), (0.47, -0.27), (0.51, -0.02), (0.48 + ear, 0.13), (0.48, 0.265), (0.39, 0.37), (0.235, 0.58)]
        base = [(x + nz(), y + nz()) for x, y in base]
        wob = 0.012 * w
        tr = 0.008 * w
        P = lambda pts: [HP(x, y) for x, y in pts]

        def stroke(pts, k=1.0, closed=False, layer='line', hx=False, **kw):
            if hx:
                kw['dup'] = 'Hx'
            return self.line(P(pts), lw * k, rng=rng, wob=wob, trem=tr, closed=closed, layer=layer, **kw)

        def hairtop(y0h):
            return self.hfill(P([(-0.47, y0h - 0.03), (-0.50, -0.04), (-0.46, -0.27), (-0.30, -0.46), (0.0, -0.53), (0.30, -0.46), (0.46, -0.27),
                                 (0.50, -0.04), (0.47, y0h - 0.03), (0.25, y0h + 0.06), (0.0, y0h + 0.09), (-0.25, y0h + 0.06)]))

        def earknock():
            for sg in (-1, 1):
                self.knock(P([(sg * 0.47, -0.03), (sg * (0.5 + ear), 0.13), (sg * 0.48, 0.28), (sg * 0.44, 0.13)]), layers=('H',))

        def sil(pts, closed=True):
            d = self.hand(P(pts), closed=True, wob=0, trem=0, rng=rng)
            self.knock(d)
            return d

        headp = self.hand(P(base), wob=wob * 0.6, trem=tr, rng=rng)
        draw_head = True
        ears = det

        # -- shapes that sit over the back (drawn after the head)
        post = []

        if hair in ('long',):
            ln = o.get('hairlen', rng.uniform(1.0, 1.7))
            wd = rng.uniform(0.56, 0.66)
            outline = [(-0.28, ln), (-wd + 0.02, ln * 0.7), (-wd, 0.45), (-wd + 0.03, 0.0), (-0.5, -0.32), (-0.29, -0.51), (0.0, -0.57),
                       (0.29, -0.51), (0.5, -0.32), (wd - 0.03, 0.0), (wd, 0.45), (wd - 0.02, ln * 0.7), (0.28, ln)]
            tips = [(0.28, ln)]
            k = rng.randint(3, 5)
            for i in range(1, k):
                x = 0.28 - 0.56 * i / k
                tips.append((x + rng.gauss(0, 0.03), ln + (0.08 if i % 2 else -0.04) + rng.gauss(0, 0.03)))
            tips.append((-0.28, ln))
            d = self.hand(P(outline + tips[1:-1][::-1]), closed=True, wob=0, trem=0, rng=rng)
            self.knock(d)
            self.hfill(d)
            stroke(outline, redraw=0.15)
            stroke(tips, 0.85, a0=0.6, a1=1.0)
            if det:
                for i in range(rng.randint(2, 4)):
                    x0 = rng.uniform(-0.25, 0.25)
                    x1 = x0 * 1.3 + rng.uniform(-0.1, 0.1)
                    stroke([(x0 * 0.4, -0.38), (x0, 0.1), (x1, ln * rng.uniform(0.55, 0.9))], 0.7, a0=1.0, a1=3.0, hx=True)
            return
        if hair == 'curly':
            sc = rng.uniform(1.08, 1.2)
            ctrl = [(math.cos(a) * 0.5 * sc, math.sin(a) * 0.5 * sc - 0.04) for a in [TAU * i / 14 for i in range(14)]]
            d = self.hand(P(ctrl), closed=True, wob=0, trem=0, rng=rng)
            self.knock(d)
            self.hfill(d)
            # neck/ear below the curls
            stroke([(-0.235, 0.58), (-0.36, 0.40)], a0=0.5)
            stroke([(0.235, 0.58), (0.36, 0.40)], a0=0.5)
            n = rng.randint(9, 13) if det else 7
            ph = rng.uniform(0, TAU)
            for i in range(n):
                a0_ = ph + TAU * i / n
                a1_ = a0_ + TAU / n * rng.uniform(1.0, 1.25)
                am = (a0_ + a1_) / 2
                r = 0.5 * sc
                pts = [(math.cos(a0_) * r, math.sin(a0_) * r - 0.04), (math.cos(am) * r * 1.13, math.sin(am) * r * 1.13 - 0.04),
                       (math.cos(a1_) * r, math.sin(a1_) * r - 0.04)]
                if math.sin(am) > 0.75:
                    continue
                stroke(pts, 0.9, a0=0.4, a1=0.9, pv=0.1)
            if det:
                for i in range(rng.randint(3, 6)):
                    x, y = rng.uniform(-0.3, 0.3), rng.uniform(-0.35, 0.2)
                    s_ = rng.uniform(0.06, 0.1)
                    stroke([(x - s_, y), (x, y - s_), (x + s_ * 0.6, y + s_ * 0.2)], 0.7, a0=0.4, a1=0.8, hx=True)
            return
        if hair == 'cap':
            col = o.get('capfill', rng.choice(['Y', 'G', None, None, None]))
            dome = [(-0.54, 0.03), (-0.52, -0.25), (-0.32, -0.47), (0.0, -0.55), (0.32, -0.47), (0.52, -0.25), (0.54, 0.03)]
            band = [(0.54, 0.03), (0.0, 0.08), (-0.54, 0.03)]
            # lower head + ears below cap
            lower = [b for b in base if b[1] > -0.03]
            sil(base)
            stroke(lower[:5], a0=0.5)
            stroke(lower[5:], a1=1.0)
            d = self.hand(P(dome + band[1:]), closed=True, wob=0, trem=0, rng=rng)
            self.knock(d)
            if col:
                self.blob(P(dome + band[1:]), col, rng=rng, shift=0.03 * w)
            stroke(dome, redraw=0.15)
            stroke(band, 0.9)
            arch = [(-0.16, 0.06), (-0.14, -0.1), (0.0, -0.17), (0.14, -0.1), (0.16, 0.06)]
            d = self.hand(P(arch), closed=True, wob=0, trem=0, rng=rng)
            self.knock(d, layers=('Y', 'G'))
            if det:
                stroke(arch, 0.85)
                stroke([(-0.1, 0.02), (-0.05, -0.08)], 0.6)
                stroke([(0.0, 0.03), (0.02, -0.1)], 0.6)
                stroke([(0.0, -0.55), (0.0, -0.2)], 0.6)
                stroke([(-0.22, -0.5), (-0.3, -0.2), (-0.3, 0.03)], 0.6)
                stroke([(0.22, -0.5), (0.3, -0.2), (0.3, 0.03)], 0.6)
                x, y = HP(0, -0.55)
                self.dot(x, y, max(0.035 * w, 1.5), rng=rng)
            for sg in (-1, 1):
                stroke([(sg * 0.53, 0.0), (sg * 0.63, 0.06)], 0.85, a0=0.3)
            return
        if hair == 'turban':
            dome = [(-0.53, 0.08), (-0.56, -0.32), (-0.36, -0.62), (0.0, -0.70), (0.36, -0.62), (0.56, -0.32), (0.53, 0.08)]
            rim = [(0.53, 0.08), (0.0, 0.16), (-0.53, 0.08)]
            sil(base)
            lower = [b for b in base if b[1] > 0.05]
            stroke(lower[:3], a0=0.5)
            stroke(lower[-3:], a1=1.0)
            d = self.hand(P(dome + rim[1:]), closed=True, wob=0, trem=0, rng=rng)
            self.knock(d)
            self.blob(P(dome + rim[1:]), o.get('turbanfill', 'Y'), rng=rng, shift=0.03 * w, gap=0.2)
            stroke(dome, redraw=0.2)
            stroke(rim, 0.9)
            if det:
                for i in range(4):
                    t = 0.15 + i * 0.2
                    stroke([(-0.52, 0.05 - t * 0.55), (-0.1, 0.12 - t * 0.6), (0.36 - i * 0.05, -0.58 + i * 0.03)], 0.7, a0=0.5, a1=1.0)
                for i in range(3):
                    t = 0.25 + i * 0.22
                    stroke([(0.52, 0.04 - t * 0.5), (0.15, 0.1 - t * 0.55), (-0.25 + i * 0.05, -0.62 + i * 0.05)], 0.7, a0=0.5, a1=1.0)
            return

        if hair == 'hood':
            # hood up: one soft pointed bag over the head, a seam down the middle
            col = o.get('_gfill')
            pk = rng.uniform(-0.05, 0.05)
            hd = [(-0.66, 0.78), (-0.69, 0.32), (-0.62, -0.18), (-0.42, -0.55), (pk, -0.70), (0.42, -0.55), (0.62, -0.18), (0.69, 0.32), (0.66, 0.78)]
            hd = [(x + nz() * 1.5, y + nz()) for x, y in hd]
            bot = [(0.66, 0.78), (0.3, 0.92), (0.0, 0.95), (-0.3, 0.92), (-0.66, 0.78)]
            d = self.hand(P(hd + bot[1:-1]), closed=True, wob=0, trem=0, rng=rng)
            self.knock(d)
            if col:
                self.blob(P(hd + bot[1:-1]), col, rng=rng, shift=0.03 * w, gap=0.3)
            stroke(hd, redraw=0.2 if big else 0.05)
            stroke(bot, 0.85, a0=0.5)
            if det:
                stroke([(pk, -0.68), (pk * 0.5 + 0.02, -0.1), (0.0, 0.5), (0.02, 0.9)], 0.7, a0=0.4, a1=1.2)
                for sg in (-1, 1):
                    stroke([(sg * 0.5, 0.55), (sg * 0.3, 0.72), (sg * 0.12, 0.86)], 0.55, a0=0.4, a1=1.0)
            return
        if hair in ('beanie', 'monkeycap'):
            col = o.get('capfill', rng.choice(['Y', 'G', 'G', None, None]))
            mc = hair == 'monkeycap'
            if mc:
                # pulled right down: covers the head and neck, ribbed all the way
                cap = [(-0.30, 0.66), (-0.42, 0.45), (-0.55, 0.22), (-0.57, -0.08), (-0.50, -0.34), (-0.31, -0.54), (0.0, -0.61),
                       (0.31, -0.54), (0.50, -0.34), (0.57, -0.08), (0.55, 0.22), (0.42, 0.45), (0.30, 0.66)]
                hem = [(0.30, 0.66), (0.0, 0.70), (-0.30, 0.66)]
            else:
                cap = [(-0.55, 0.02), (-0.55, -0.27), (-0.34, -0.53), (0.0, -0.62), (0.34, -0.53), (0.55, -0.27), (0.55, 0.02)]
                hem = [(0.55, 0.02), (0.0, 0.08), (-0.55, 0.02)]
            cap = [(x + nz(), y + nz()) for x, y in cap]
            if not mc:
                sil(base)
                lower = [b for b in base if b[1] > 0.05]
                stroke(lower[:3], a0=0.5)
                stroke(lower[-3:], a1=1.0)
                if ears:
                    for sg in (-1, 1):
                        stroke([(sg * 0.5, 0.1), (sg * (0.5 + ear * 0.6), 0.16), (sg * 0.505, 0.24)], 0.65, a0=0.4, a1=0.7)
            d = self.hand(P(cap + hem[1:-1]), closed=True, wob=0, trem=0, rng=rng)
            self.knock(d)
            if col:
                self.blob(P(cap + hem[1:-1]), col, rng=rng, shift=0.03 * w, gap=0.2)
            stroke(cap, redraw=0.2 if big else 0.05)
            stroke(hem, 0.85)
            # rolled cuff / ribs
            cy0 = 0.42 if mc else -0.16
            stroke([(-0.555 + (0.08 if mc else 0.0), cy0), (0.0, cy0 + 0.07), (0.555 - (0.08 if mc else 0.0), cy0)], 0.8)
            if det:
                k = rng.randint(6, 9) if w > 40 else 4
                for i in range(k):
                    t = (i + 0.5) / k
                    x = -0.46 + 0.92 * t
                    bow = 0.05 * (1 - (2 * t - 1) ** 2)
                    if mc:
                        stroke([(x * 0.55, -0.55 + 0.05 * abs(x)), (x * 1.05, 0.0), (x * 0.86, cy0 + bow)], 0.5, a0=0.4, a1=1.4)
                        stroke([(x * 0.68, cy0 + 0.05 + bow), (x * 0.62, 0.62)], 0.5, a0=0.2, a1=0.4)
                    else:
                        stroke([(x * 1.08, cy0 + 0.03 + bow), (x * 1.1, 0.04 + bow)], 0.5, a0=0.2, a1=0.4)
                        stroke([(x * 0.6, -0.56 + 0.06 * abs(x)), (x * 1.05, cy0 - 0.03)], 0.45, a0=0.4, a1=1.2)
            if o.get('pompom', rng.random() < (0.55 if mc else 0.35)):
                pr = 0.13 if mc else 0.15
                px_, py_ = rng.gauss(0, 0.03), -0.66 - pr * 0.6
                n = 11
                ring = [(px_ + math.cos(TAU * i / n) * pr * rng.uniform(0.85, 1.15), py_ + math.sin(TAU * i / n) * pr * rng.uniform(0.85, 1.15)) for i in range(n)]
                d = self.hand(P(ring), closed=True, wob=0, trem=0, rng=rng)
                self.knock(d)
                pc = o.get('pomfill', col)
                if pc:
                    self.blob(P(ring), pc, rng=rng, shift=0.02 * w, gap=0.0)
                stroke(ring, 0.8, closed=True, close_frac=1.03)
            return

        # --- heads that show the default outline
        if hair == 'bandana':
            pass
        self.knock(headp + [headp[0]])
        if det and rng.random() < 0.3:
            k = len(headp) // 2 + rng.randint(-4, 4)
            self.ink(headp[:k + 2], lw, rng=rng, a1=1.4)
            self.ink(headp[k - 1:], lw, rng=rng, a0=1.0)
        else:
            self.ink(headp, lw, rng=rng, redraw=0.3 if big else 0.04)
        if ears:
            for sg in (-1, 1):
                stroke([(sg * 0.5, 0.02), (sg * (0.5 + ear * 0.6), 0.1), (sg * 0.505, 0.2)], 0.65, a0=0.4, a1=0.7)
        if o.get('specs'):
            for sg in (-1, 1):
                stroke([(sg * 0.42, -0.04), (sg * 0.53, 0.0), (sg * (0.56 + ear * 0.5), 0.1), (sg * 0.53, 0.24)], 0.75, a0=0.5, a1=0.8, hx=True)

        if hair in ('short', 'buzz', 'bandana', 'topknot'):
            y0 = rng.uniform(0.2, 0.3)
            if hair != 'buzz':
                hairtop(y0 + 0.04)
                earknock()
            hl = [(-0.46, y0 - 0.04), (-0.25, y0 + 0.05), (0.0, y0 + 0.08), (0.24, y0 + 0.05), (0.46, y0 - 0.04)]
            if det:
                k = rng.randint(4, 7)
                for i in range(k):
                    x = -0.38 + 0.76 * (i + rng.uniform(0.2, 0.8)) / k
                    yy = y0 + 0.07 * (1 - (x / 0.46) ** 2) + 0.03
                    stroke([(x, yy - 0.02), (x + rng.gauss(0, 0.02), yy + rng.uniform(0.04, 0.09))], 0.6, a0=0.3, a1=0.6)
            else:
                stroke(hl, 0.8, a0=0.5)
            if hair == 'short' and w >= 45:
                wx, wy = rng.uniform(-0.12, 0.15), rng.uniform(-0.36, -0.22)
                r = 0.07
                sp = [(wx + math.cos(a) * r * (a / 9), wy + math.sin(a) * r * (a / 9) * 0.9) for a in [i * 0.9 for i in range(1, 11)]]
                stroke(sp, 0.65, a0=0.4, a1=1.0, hx=True)
                for i in range(rng.randint(1, 3)):
                    a = rng.uniform(0, TAU)
                    stroke([(wx + math.cos(a) * 0.1, wy + math.sin(a) * 0.08), (wx + math.cos(a + 0.4) * 0.22, wy + math.sin(a + 0.4) * 0.17)], 0.6, a0=0.3, a1=1.0, hx=True)
            if hair == 'buzz' and det:
                for i in range(rng.randint(8, 14)):
                    a = rng.uniform(0, TAU)
                    r = rng.uniform(0, 0.36)
                    x, y = HP(math.cos(a) * r, math.sin(a) * r - 0.12)
                    self.dot(x, y, max(0.016 * w, 1.45), rng=rng)
            if hair == 'topknot':
                c = (rng.uniform(-0.05, 0.05), -0.6)
                ring = [(c[0] + math.cos(a) * 0.14, c[1] + math.sin(a) * 0.11) for a in [TAU * i / 8 for i in range(8)]]
                d = sil(ring)
                self.hfill(d)
                stroke(ring, 0.9, closed=True)
                stroke([(c[0] - 0.12, c[1] + 0.03), (c[0] + 0.1, c[1] - 0.04)], 0.6, hx=True)
            if hair == 'bandana':
                col = o.get('bandfill', rng.choice(['G', 'Y', None]))
                top = [(-0.52, -0.12), (-0.25, -0.05), (0.0, -0.03), (0.25, -0.05), (0.52, -0.12)]
                bot = [(0.53, 0.06), (0.25, 0.12), (0.0, 0.14), (-0.25, 0.12), (-0.53, 0.06)]
                kx = rng.uniform(-0.05, 0.12)
                tails = [[(kx - 0.03, 0.12), (kx - 0.12, 0.35), (kx - 0.15, 0.55)], [(kx + 0.04, 0.12), (kx + 0.14, 0.33), (kx + 0.2, 0.5)]]
                self.knock(P(top + bot), layers=('H', 'Hx'))
                self.blob(P(top + bot), col, rng=rng, shift=0.03 * w, gap=0.15)
                stroke(top, 0.85)
                stroke(bot, 0.85)
                for t in tails:
                    tt = [(x - 0.035, y) for x, y in t] + [(x + 0.035, y) for x, y in t[::-1]]
                    d = self.hand(P(tt), closed=True, wob=0, trem=0, rng=rng)
                    self.knock(d)
                    self.blob(P(tt), col, rng=rng, shift=0.03 * w, gap=0.0)
                    stroke(tt, 0.75, closed=True, close_frac=0.97)
                knot = [(kx - 0.07, 0.04), (kx, -0.02), (kx + 0.08, 0.05), (kx, 0.13)]
                d = self.hand(P(knot), closed=True, wob=0, trem=0, rng=rng)
                self.knock(d)
                self.blob(P(knot), col, rng=rng, shift=0.02 * w, gap=0.0)
                stroke(knot, 0.8, closed=True)
            return

        if hair in ('ponytail', 'bun', 'braid'):
            if hair == 'bun':
                bx, by = rng.uniform(-0.08, 0.08), rng.choice([-0.42, -0.1, 0.05])
                tie = (bx, by + 0.17)
            elif hair == 'ponytail':
                tie = (rng.uniform(-0.06, 0.06), rng.uniform(-0.05, 0.15))
            else:
                tie = (rng.uniform(-0.04, 0.04), 0.4)
            hairtop(0.33)
            earknock()
            if det:
                cands = [(-0.42, -0.25), (-0.15, -0.47), (0.15, -0.47), (0.42, -0.25), (-0.45, 0.15), (0.45, 0.15)]
                rng.shuffle(cands)
                for (x0, y0) in cands[:rng.randint(2, 3)]:
                    t0 = rng.uniform(0.0, 0.25)
                    sx_, sy_ = x0 * 0.92 + (tie[0] - x0) * t0, y0 * 0.92 + (tie[1] - y0) * t0
                    stroke([(sx_, sy_), ((x0 + tie[0]) / 2 * 1.08, (y0 + tie[1]) / 2), (tie[0] + x0 * 0.22, tie[1] + y0 * 0.2)], 0.6, a0=0.6, a1=2.5, hx=True)
            if hair == 'bun':
                r = rng.uniform(0.17, 0.22)
                ring = [(bx + math.cos(a) * r, by + math.sin(a) * r * 0.9) for a in [TAU * i / 9 for i in range(9)]]
                d = sil(ring)
                self.hfill(d)
                stroke(ring, 0.95, closed=True)
                if det:
                    sp = [(bx + math.cos(a) * r * (a / 11), by + math.sin(a) * r * 0.9 * (a / 11)) for a in [i * 1.0 for i in range(2, 12)]]
                    stroke(sp, 0.6, a0=0.3, a1=0.8, hx=True)
                if o.get('gajra'):
                    k = 9
                    for i in range(k):
                        a = TAU * i / k + 0.2
                        x, y = bx + math.cos(a) * (r + 0.08), by + math.sin(a) * (r + 0.07)
                        ring2 = [(x + math.cos(b) * 0.045, y + math.sin(b) * 0.04) for b in [TAU * j / 6 for j in range(6)]]
                        stroke(ring2, 0.6, closed=True)
            else:
                ln = o.get('hairlen', rng.uniform(1.1, 1.6) if hair == 'ponytail' else rng.uniform(1.9, 2.6))
                if hair == 'ponytail':
                    tail = [(tie[0] - 0.05, tie[1]), (tie[0] - 0.17, tie[1] + 0.35), (tie[0] - 0.12, tie[1] + ln * 0.7), (tie[0] + 0.03, tie[1] + ln),
                            (tie[0] + 0.12, tie[1] + ln * 0.6), (tie[0] + 0.12, tie[1] + 0.3), (tie[0] + 0.05, tie[1])]
                    post.append(('tail', tail))
                else:
                    post.append(('braid', ln))
            # tie
            if hair != 'bun':
                ring = [(tie[0] + math.cos(a) * 0.075, tie[1] + math.sin(a) * 0.05) for a in [TAU * i / 7 for i in range(7)]]
                post.append(('tie', ring))

        for kind, data in post:
            if kind == 'tail':
                d = self.hand(P(data), closed=True, wob=0, trem=0, rng=rng)
                self.knock(d)
                self.hfill(d)
                stroke(data[:4], 0.95, a1=2.0)
                stroke(data[3:], 0.95, a0=1.0)
                if det:
                    stroke([(tie[0], tie[1] + 0.15), (tie[0] - 0.03, tie[1] + 0.7)], 0.6, a0=1.0, a1=2.5, hx=True)
            elif kind == 'braid':
                ln = data
                n = int(ln / 0.16)
                x, y = tie
                for i in range(n):
                    sg = 1 if i % 2 else -1
                    yy = y + i * 0.16
                    lobe = [(x + sg * 0.01, yy - 0.02), (x - sg * 0.15, yy + 0.06), (x - sg * 0.06, yy + 0.17), (x + sg * 0.02, yy + 0.16)]
                    d = self.hand(P([(x - 0.15, yy - 0.02), (x + 0.15, yy - 0.02), (x + 0.14, yy + 0.18), (x - 0.14, yy + 0.18)]), closed=True, wob=0, trem=0, rng=rng)
                    self.knock(d)
                    self.hfill(self.hand(P([(x - 0.12, yy - 0.03), (x + 0.12, yy - 0.03), (x + 0.11, yy + 0.19), (x - 0.11, yy + 0.19)]), closed=True, wob=0, trem=0, rng=rng))
                    stroke(lobe, 0.75, a0=0.4, a1=0.8, hx=(0 < i))
                    x += rng.gauss(0, 0.012)
                yy = y + n * 0.16
                if o.get('mallige'):
                    self.mallige(P, tie, ln, w, lw, rng)
                # tassel (paranda)
                if o.get('paranda'):
                    for j in range(5):
                        dx = (j - 2) * 0.03
                        stroke([(x + dx * 0.4, yy), (x + dx * 1.6, yy + 0.32)], 0.7, layer='B', a0=0.3, a1=0.6)
                    stroke([(x - 0.07, yy + 0.0), (x + 0.07, yy + 0.0)], 0.9)
            elif kind == 'tie':
                d = self.hand(P(data), closed=True, wob=0, trem=0, rng=rng)
                self.knock(d)
                if o.get('tiefill'):
                    self.blob(P(data), o['tiefill'], rng=rng, shift=0.01 * w, gap=0.0, scale=(1.05, 1.15))
                stroke(data, 0.8, closed=True)

    def mallige(self, P, tie, ln, w, lw, rng):
        """a string of jasmine pinned across the back of the head, one end hanging down the braid"""
        x0, y0 = tie
        across = [(x0 - 0.36, y0 - 0.34), (x0 - 0.18, y0 - 0.17), (x0 + 0.02, y0 - 0.1), (x0 + 0.2, y0 - 0.14), (x0 + 0.33, y0 - 0.26)]
        down = [(x0 + 0.33, y0 - 0.26), (x0 + 0.27, y0 + 0.12), (x0 + 0.21, y0 + 0.5), (x0 + 0.2, y0 + ln * 0.42), (x0 + 0.23, y0 + ln * 0.6)]
        for path, k0 in ((across, 0), (down, 1)):
            pts = catmull(P(path), False, 0.6)
            s_ = cumlen(pts)
            L = s_[-1]
            step = w * 0.072
            nb = int(L / step)
            N = normals(pts)
            j = 0
            self.ink(pts, MINW, rng=rng, a0=0.5, a1=0.5, pv=0.05)
            for b in range(nb):
                t = (b + 0.5) * step
                while j < len(s_) - 2 and s_[j + 1] < t:
                    j += 1
                (x, y), (nx, ny) = pts[j], N[j]
                for side in (-1, 1):
                    if rng.random() < 0.12:
                        continue
                    a = math.atan2(ny * side, nx * side) + rng.gauss(0, 0.35)
                    ca, sa = math.cos(a), math.sin(a)
                    bl = w * rng.uniform(0.075, 0.095)
                    bw = w * rng.uniform(0.034, 0.042)
                    bx, by = x + ca * w * 0.012, y + sa * w * 0.012
                    shape = [(bx + ca * bl * u - sa * bw * v, by + sa * bl * u + ca * bw * v)
                             for u, v in ((0.0, 0.0), (0.25, -0.9), (0.7, -0.75), (1.0, 0.0), (0.7, 0.75), (0.25, 0.9))]
                    d = self.hand(shape, closed=True, wob=0, trem=0, rng=rng, step=0.8)
                    self.knock(d)
                    if (b + side) % 7 == 3:
                        self.blob(shape, 'Y', rng=rng, scale=(1.0, 1.15), jit=0.02, shift=0.4, gap=0.0, n=12)
                        self.ink(d, MINW, closed=True, rng=rng, a0=0.3, a1=0.4, pv=0.05)
                    elif rng.random() < 0.3:
                        self.D['line'].polygon([(px_ * S, (py_ + OY) * S) for px_, py_ in d], fill=255)
                    else:
                        self.ink(d, MINW, closed=True, rng=rng, a0=0.3, a1=0.4, pv=0.05, close_frac=rng.uniform(0.95, 1.03))

    def ridge(self, y0, xa, xb, w0, rng, depth=1.4, arms=0.1):
        """the far crowd the way it gets drawn by hand: one running line of head
        bumps and shoulder dips, the pen lifted every few heads; now and then an
        arm sticks up out of it with a phone or a torch on the end"""
        ph1, ph2 = rng.uniform(0, TAU), rng.uniform(0, TAU)

        def base(x):
            return y0 + w0 * (0.22 * math.sin(x * 0.021 + ph1) + 0.12 * math.sin(x * 0.067 + ph2))
        x = xa + rng.uniform(0, w0)
        runs, cur, extras = [], [], []
        while x < xb:
            # thin out toward the ends and leave the odd pocket of ground
            edge = abs((x - xa) / (xb - xa) * 2 - 1)
            if rng.random() < 0.03 + max(0.0, edge - 0.75) * 1.6:
                if len(cur) > 3:
                    runs.append(cur)
                cur = []
                x += w0 * rng.uniform(0.8, 2.2)
                continue
            bw = w0 * rng.uniform(0.72, 1.3)
            bh = w0 * rng.uniform(0.42, 0.9)
            b = base(x + bw / 2) + rng.gauss(0, 0.07 * w0)
            kind = rng.random()
            if kind < 0.12:      # hood: a soft point
                cur += [(x, b), (x + bw * 0.12, b - bh * 0.7), (x + bw * 0.5 + rng.gauss(0, 0.05 * bw), b - bh * 1.18), (x + bw * 0.88, b - bh * 0.7)]
            elif kind < 0.2:     # bun on top
                cur += [(x, b), (x + bw * 0.12, b - bh * 0.72), (x + bw * 0.34, b - bh), (x + bw * 0.42, b - bh * 1.32), (x + bw * 0.62, b - bh * 1.3),
                        (x + bw * 0.68, b - bh), (x + bw * 0.88, b - bh * 0.72)]
            elif kind < 0.26:    # cap with a brim
                cur += [(x, b), (x + bw * 0.1, b - bh * 0.75), (x + bw * 0.45, b - bh * 1.02), (x + bw * 0.8, b - bh * 0.82), (x + bw * 1.15, b - bh * 0.7),
                        (x + bw * 0.9, b - bh * 0.55)]
            else:
                cur += [(x, b), (x + bw * 0.1, b - bh * 0.72), (x + bw * 0.5 + rng.gauss(0, 0.06 * bw), b - bh), (x + bw * 0.9, b - bh * 0.72)]
            top = (x + bw * 0.5, b - bh)
            if rng.random() < 0.06:
                extras.append(('cap', (x, b, bw, bh)))
            if rng.random() < arms:
                extras.append(('arm', (x + bw * rng.uniform(0.2, 0.8), b - bh * 0.5, bh)))
            x += bw
            # shoulder dip between heads (sometimes two heads touch)
            if rng.random() < 0.7:
                d = w0 * rng.uniform(0.12, 0.55)
                cur.append((x + d * 0.5, base(x + d * 0.5) + w0 * rng.uniform(0.0, 0.12)))
                x += d
            if len(cur) > rng.randint(14, 30):
                runs.append(cur)
                cur = [(cur[-1][0] + rng.uniform(-2, 1.5), cur[-1][1] + rng.gauss(0, 0.6))]
        if len(cur) > 3:
            runs.append(cur)
        lw = MINW
        for run in runs:
            p = self.hand(run, wob=0.035 * w0, trem=0.05 * w0, rng=rng, step=1.0)
            self.knock(p + [(p[-1][0], y0 + depth * w0), (p[0][0], y0 + depth * w0)])
            for k, data in extras:
                if k == 'cap' and run[0][0] <= data[0] <= run[-1][0]:
                    xx, b, bw, bh = data
                    self.blob([(xx + bw * 0.12, b - bh * 0.62), (xx + bw * 0.5, b - bh * 0.98), (xx + bw * 0.88, b - bh * 0.62), (xx + bw * 0.8, b - bh * 0.35),
                               (xx + bw * 0.2, b - bh * 0.35)], rng.choice(('Y', 'G', 'G')), rng=rng, shift=0.12 * w0, gap=0.0, n=14)
            self.ink(p, lw, rng=rng, a0=0.8, a1=1.6, pv=0.3, redraw=0.15)
        for k, data in extras:
            if k != 'arm':
                continue
            ax, ay, bh = data
            L = w0 * rng.uniform(1.0, 1.9)
            a = -math.pi / 2 + rng.gauss(0, 0.28)
            hx, hy = ax + math.cos(a) * L, ay + math.sin(a) * L
            mid = ((ax + hx) / 2 + rng.gauss(0, 0.12 * w0), (ay + hy) / 2)
            self.knock(offset_path([(ax, ay), mid, (hx, hy)], 0.16 * w0 + 1.5) + offset_path([(ax, ay), mid, (hx, hy)], -0.16 * w0 - 1.5)[::-1])
            self.line([(ax, ay), mid, (hx, hy)], lw, rng=rng, wob=0.03 * w0, trem=0, a0=0.4, a1=0.6)
            q = rng.random()
            if q < 0.3:
                # torch: a bright point, three or four short unequal ticks
                self.dot(hx, hy - 1.5, max(1.6, 0.16 * w0), rng=rng)
                ph = rng.uniform(0, TAU)
                for i in range(rng.randint(3, 4)):
                    aa = ph + TAU * i / 4 + rng.gauss(0, 0.3)
                    r0, r1 = 3.5 + 0.2 * w0, 3.5 + w0 * rng.uniform(0.5, 1.0)
                    self.line([(hx + math.cos(aa) * r0, hy - 1.5 + math.sin(aa) * r0), (hx + math.cos(aa) * r1, hy - 1.5 + math.sin(aa) * r1)], MINW,
                              rng=rng, layer='Y', wob=0.1, trem=0, a0=0.3, a1=0.6)
            elif q < 0.72:
                ph_ = w0 * rng.uniform(0.6, 0.85)
                pw = ph_ * rng.uniform(0.5, 0.62)
                rect = [(hx - pw / 2, hy - ph_), (hx + pw / 2, hy - ph_ - rng.gauss(0, 0.4)), (hx + pw / 2, hy + 1), (hx - pw / 2, hy + 1)]
                self.knock(rect)
                self.blob(rect, 'B' if rng.random() < 0.06 else rng.choice(('Y', 'Y', 'G')), rng=rng, scale=(1.0, 1.15), shift=0.1 * w0, gap=0.0, n=10)
            else:
                self.dot(hx, hy, max(1.7, 0.2 * w0), rng=rng)

    def person_far(self, cx, cy, w, lw, rng):
        """a distant head: a bump, shoulders, maybe an arm with a phone"""
        h = w * 1.12
        sw = rng.uniform(1.15, 1.5)
        body = [(cx - 0.25 * w, cy + 0.55 * h), (cx - sw * w * 0.8, cy + 0.95 * h), (cx - sw * w, cy + 1.3 * h), (cx - sw * w, cy + 3.0 * h),
                (cx + sw * w, cy + 3.0 * h), (cx + sw * w, cy + 1.3 * h), (cx + sw * w * 0.8, cy + 0.95 * h), (cx + 0.25 * w, cy + 0.55 * h)]
        self.knock(body)
        r = rng.random()
        if r < 0.07:
            self.blob(body[1:7], 'Y', rng=rng, shift=0.05 * w, gap=0.3)
        elif r < 0.17:
            self.blob(body[1:7], 'G', rng=rng, shift=0.05 * w, gap=0.3)
        for sg in (-1, 1):
            if rng.random() < 0.85:
                self.line([(cx + sg * 0.35 * w, cy + 0.8 * h), (cx + sg * sw * 0.8 * w, cy + 0.98 * h), (cx + sg * sw * w * 1.02, cy + 1.45 * h)],
                          lw, rng=rng, wob=0.04 * w, trem=0, a0=0.6, a1=1.0)
        # arm up
        if rng.random() < self.far_arm:
            sg = rng.choice((-1, 1))
            sx, sy = cx + sg * sw * w * 0.75, cy + 1.0 * h
            hx, hy = cx + sg * w * rng.uniform(0.4, 1.4), cy - h * rng.uniform(0.9, 1.7)
            ex, ey = (sx + hx) / 2 + sg * w * 0.25, (sy + hy) / 2
            p = self.hand([(sx, sy), (ex, ey), (hx, hy)], wob=0.03 * w, trem=0, rng=rng)
            self.knock(offset_path(p, 0.18 * w) + offset_path(p, -0.18 * w)[::-1])
            self.ink(p, lw, rng=rng, a0=0.5, a1=0.8)
            q = rng.random()
            if q < 0.22:
                self.rays(hx, hy - 0.2 * w, 0.18 * w + 1.0, 0.95 * w + 3.0, rng.randint(4, 6), rng, skip_down=False)
                self.dot(hx, hy - 0.2 * w, max(0.16 * w, 1.6), rng=rng)
            elif q < 0.72:
                ph = w * rng.uniform(0.7, 0.95)
                pw = ph * 0.55
                ang = rng.gauss(0, 0.2)
                ca, sa = math.cos(ang), math.sin(ang)
                cxp, cyp = hx, hy - ph * 0.45
                rect = [(cxp + (u * pw * ca - v * ph * sa) / 2, cyp + (u * pw * sa + v * ph * ca) / 2) for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
                self.knock(rect)
                lay = 'B' if rng.random() < 0.04 else 'G' if rng.random() < 0.3 else 'Y'
                self.blob(rect, lay, rng=rng, scale=(1.0, 1.12), shift=0.04 * w, gap=0.0, n=12)
                if w > 15:
                    self.box(rect, lw * 0.8, rng=rng, over=(-0.5, 1.0), wob=0.1)
            else:
                self.dot(hx, hy - 0.15 * w, max(0.22 * w, 1.6), rng=rng)
        # head
        nz = lambda: rng.gauss(0, 0.02)
        hair = rng.random()
        cold = rng.random()
        if hair < 0.22:  # long hair
            ctrl = [(-0.5, 0.9), (-0.55, 0.3), (-0.5, -0.25), (0.0, -0.55), (0.5, -0.25), (0.55, 0.3), (0.5, 0.9)]
        elif cold < 0.22:  # hood up
            ctrl = [(-0.6, 0.75), (-0.62, 0.1), (-0.45, -0.4), (0.03, -0.72), (0.45, -0.4), (0.62, 0.1), (0.6, 0.75)]
            hair = 0.5
        elif cold < 0.42:  # beanie
            ctrl = [(-0.42, 0.45), (-0.52, 0.0), (-0.52, -0.3), (-0.3, -0.58), (0.0, -0.64), (0.3, -0.58), (0.52, -0.3), (0.52, 0.0), (0.42, 0.45)]
            hair = 0.5
        else:
            ctrl = [(-0.42, 0.45), (-0.52, 0.0), (-0.42, -0.35), (0.0, -0.55), (0.42, -0.35), (0.52, 0.0), (0.42, 0.45)]
        ctrl = [(cx + (x + nz()) * w, cy + (y + nz()) * h) for x, y in ctrl]
        d = self.hand(ctrl, wob=0, trem=0, rng=rng)
        self.knock(d + [(cx, cy + 0.6 * h)])
        if hair < 0.22 or rng.random() < 0.8:
            self.hfill(d + [(cx + 0.3 * w, cy + 0.25 * h), (cx - 0.3 * w, cy + 0.25 * h)] if hair >= 0.22 else d)
        self.ink(d, lw, rng=rng, a0=0.6, a1=0.9, pv=0.15)
        if 0.22 <= cold < 0.42 and hair >= 0.22:
            self.line([(cx - 0.53 * w, cy - 0.12 * h), (cx, cy - 0.06 * h), (cx + 0.53 * w, cy - 0.13 * h)], lw * 0.85, rng=rng, wob=0.02 * w, trem=0)
            if rng.random() < 0.4:
                self.dot(cx + rng.gauss(0, 0.05) * w, cy - 0.72 * h, max(0.17 * w, 1.6), rng=rng)
        elif cold < 0.22 and hair >= 0.22:
            if w > 9:
                self.line([(cx + 0.03 * w, cy - 0.66 * h), (cx + 0.02 * w, cy + 0.1 * h)], MINW, rng=rng, wob=0.02 * w, trem=0, a0=0.3, a1=1.0)
        elif hair > 0.22:
            r2 = rng.random()
            if r2 < 0.14:
                bx, by = cx + rng.gauss(0, 0.08) * w, cy - 0.6 * h
                ring = [(bx + math.cos(a) * 0.2 * w, by + math.sin(a) * 0.17 * w) for a in [TAU * i / 7 for i in range(7)]]
                self.knock(ring)
                self.hfill(ring)
                self.line(ring, lw * 0.9, rng=rng, wob=0.02 * w, trem=0, closed=True, close_frac=1.03)
            elif r2 < 0.26:
                self.line([(cx + 0.05 * w, cy + 0.0), (cx + 0.12 * w, cy + 0.6 * h), (cx + 0.05 * w, cy + 1.1 * h)], lw * 0.9, rng=rng, wob=0.02 * w, trem=0)
            elif r2 < 0.36:
                self.line([(cx - 0.62 * w, cy + 0.05 * h), (cx + 0.6 * w, cy + 0.02 * h)], lw * 0.9, rng=rng, wob=0.02 * w, trem=0)

    # ---- profile heads (the two faces we get to see) ----------------------
    def head_profile(self, cx, cy, w, lw, rng, face=1, back=0.0, mouth=0.0, bindi=False, specs=False, hair='bun',
                     earring=False, gajra=False, smile=False, beard=False, neck=True, capfill=None):
        h = w * 1.13
        a = -face * math.radians(back)
        piv = (cx, cy + 0.55 * h)

        def HP(x, y):
            return rotp((cx + face * x * w, cy + y * h), a, piv)
        P = lambda pts: [HP(x, y) for x, y in pts]
        wob = 0.008 * w
        tr = 0.006 * w

        def stroke(pts, k=1.0, closed=False, layer='line', hx=False, **kw):
            if hx:
                kw['dup'] = 'Hx'
            return self.line(P(pts), lw * k, rng=rng, wob=wob, trem=tr, closed=closed, layer=layer, **kw)
        m = mouth
        face_pts = [(-0.18, 0.66), (-0.30, 0.42), (-0.47, 0.17), (-0.50, -0.08), (-0.42, -0.33), (-0.22, -0.50), (0.05, -0.54), (0.28, -0.45),
                    (0.40, -0.30), (0.445, -0.14), (0.44, -0.06), (0.415, -0.015), (0.47, 0.08), (0.545, 0.165), (0.535, 0.19), (0.47, 0.205),
                    (0.465, 0.245), (0.49, 0.27), (0.455 - m * 0.05, 0.30 + m * 0.02), (0.48, 0.33 + m * 0.09), (0.455, 0.365 + m * 0.1),
                    (0.44, 0.44 + m * 0.1), (0.36, 0.50 + m * 0.09), (0.24, 0.52 + m * 0.07), (0.18, 0.60), (0.17, 0.74)]
        sil = self.hand(P(face_pts), wob=0, trem=0, rng=rng)
        self.knock(sil + [HP(0.0, 0.8), HP(-0.2, 0.8)])
        # hair mass
        if hair == 'bun':
            hm = [(0.36, -0.36), (0.30, -0.47), (0.05, -0.57), (-0.25, -0.53), (-0.45, -0.35), (-0.53, -0.08), (-0.49, 0.18), (-0.34, 0.40),
                  (-0.18, 0.43), (-0.08, 0.30), (-0.02, 0.05), (0.06, -0.12), (0.18, -0.25)]
        elif hair == 'short':
            hm = [(0.38, -0.37), (0.24, -0.52), (0.0, -0.58), (-0.30, -0.52), (-0.50, -0.30), (-0.54, 0.0), (-0.45, 0.28), (-0.30, 0.40),
                  (-0.14, 0.30), (-0.06, 0.08), (0.04, -0.16), (0.20, -0.28)]
        elif hair == 'beanie':
            hm = [(0.44, -0.16), (0.42, -0.38), (0.26, -0.58), (0.0, -0.68), (-0.30, -0.63), (-0.52, -0.42), (-0.58, -0.12), (-0.55, 0.06),
                  (-0.30, 0.0), (0.0, -0.06), (0.25, -0.11)]
        else:  # curly mop
            hm = [(0.40, -0.33), (0.30, -0.55), (0.0, -0.66), (-0.34, -0.60), (-0.58, -0.35), (-0.62, -0.02), (-0.50, 0.26), (-0.34, 0.36),
                  (-0.12, 0.22), (-0.02, 0.02), (0.08, -0.12), (0.22, -0.22)]
        d = self.hand(P(hm), closed=True, wob=0, trem=0, rng=rng)
        self.knock(d)
        self.hfill(d)
        if hair == 'beanie' and capfill:
            self.blob(P(hm), capfill, rng=rng, shift=0.02 * w, gap=0.15)
        # outline: forehead to neck (the face edge)
        k = 7
        stroke(face_pts[k:], 1.0, redraw=0.0, a0=0.6, a1=2.5, pv=0.12)
        stroke(face_pts[:5], 1.0, a0=0.8)
        # jaw + ear
        stroke([(0.30, 0.47 + m * 0.08), (0.12, 0.40), (-0.06, 0.26)], 0.75, a0=0.5, a1=1.5)
        ex, ey = -0.08, 0.06
        self.knock(P([(ex + 0.03, ey - 0.13), (ex - 0.10, ey - 0.11), (ex - 0.12, ey + 0.03), (ex - 0.05, ey + 0.15), (ex + 0.04, ey + 0.14)]), layers=('H', 'Hx'))
        stroke([(ex + 0.02, ey - 0.12), (ex - 0.09, ey - 0.1), (ex - 0.11, ey + 0.03), (ex - 0.05, ey + 0.14), (ex + 0.03, ey + 0.13)], 0.8, a0=0.4, a1=0.8)
        stroke([(ex - 0.01, ey - 0.06), (ex - 0.05, ey + 0.0), (ex - 0.02, ey + 0.06)], 0.6, a0=0.3, a1=0.6)
        # closed eye: a lid curve with lashes
        stroke([(0.27, -0.05), (0.33, -0.02), (0.39, -0.045)], 0.8, a0=0.3, a1=0.6)
        for t in (0.29, 0.335):
            stroke([(t, -0.025), (t - 0.015, 0.02)], 0.55, a0=0.2, a1=0.4)
        stroke([(0.25, -0.13), (0.33, -0.16), (0.42, -0.135)], 0.75, a0=0.4, a1=1.0)
        if smile:
            stroke([(0.41, 0.28), (0.375, 0.31), (0.39, 0.345)], 0.6, a0=0.3, a1=0.5)
            stroke([(0.33, 0.12), (0.36, 0.18)], 0.55)
        if m > 0.3:
            stroke([(0.465, 0.31), (0.42, 0.335), (0.455, 0.375)], 0.6, a0=0.3, a1=0.5)
        if bindi:
            x, y = HP(0.405, -0.165)
            self.dot(x, y, max(0.03 * w, 2.0), layer='B', rng=rng)
        if specs:
            lens = [(0.30, -0.10), (0.44, -0.10), (0.455, 0.0), (0.42, 0.05), (0.31, 0.05), (0.28, -0.03)]
            stroke(lens, 0.75, closed=True, close_frac=1.02)
            stroke([(0.29, -0.06), (0.10, -0.06), (-0.10, -0.05), (-0.15, 0.03), (-0.12, 0.10)], 0.7, a0=0.4, a1=0.8, hx=True)
        if beard:
            for i in range(14):
                x, y = rng.uniform(-0.02, 0.4), rng.uniform(0.25, 0.48)
                if y < 0.25 + (0.4 - x) * 0.1:
                    continue
                X, Y = HP(x, y)
                self.dot(X, Y, max(0.013 * w, 1.4), rng=rng)
        # hair strokes
        if hair == 'bun':
            stroke(hm[:9], 1.0, redraw=0.15)
            stroke(hm[8:] + [hm[0]], 0.85, a0=0.5)
            for i in range(4):
                t = i / 4
                stroke([(0.25 - t * 0.15, -0.45 + t * 0.05), (-0.1 - t * 0.1, -0.35 + t * 0.2), (-0.4, -0.1 + t * 0.15)], 0.6, a0=0.5, a1=1.5, hx=True)
            bx, by, r = -0.56, -0.22, 0.2
            ring = [(bx + math.cos(t) * r, by + math.sin(t) * r) for t in [TAU * i / 9 for i in range(9)]]
            self.knock(self.hand(P(ring), closed=True, wob=0, trem=0, rng=rng))
            stroke(ring, 0.95, closed=True)
            sp = [(bx + math.cos(t) * r * (t / 11), by + math.sin(t) * r * (t / 11)) for t in [i * 1.0 for i in range(2, 12)]]
            self.hfill(self.hand(P(ring), closed=True, wob=0, trem=0, rng=rng))
            stroke(sp, 0.6, a0=0.3, a1=0.8, hx=True)
            if gajra:
                k = 15
                for i in range(k):
                    t = 1.2 + 4.2 * i / k + rng.gauss(0, 0.05)
                    rr = r + 0.06 + rng.uniform(-0.012, 0.012)
                    X, Y = HP(bx + math.cos(t) * rr, by + math.sin(t) * rr)
                    self.knock([(X - 3.4, Y - 3.4), (X + 3.4, Y - 3.4), (X + 3.4, Y + 3.4), (X - 3.4, Y + 3.4)])
                    self.dot(X, Y, 2.0 if i % 2 else 2.5, rng=rng)
        elif hair == 'beanie':
            stroke(hm[:8], 1.0, redraw=0.15)
            stroke(hm[7:] + [hm[0]], 0.9, a0=0.5)
            stroke([(0.43, -0.25), (0.1, -0.2), (-0.25, -0.14), (-0.57, -0.04)], 0.75, a0=0.5, a1=1.0)
            for i in range(8):
                t = (i + 0.5) / 8
                x = 0.40 - 0.95 * t
                yb = -0.12 + 0.17 * t - 0.17 * t * t
                stroke([(x, yb - 0.09), (x - 0.01, yb + 0.02)], 0.5, a0=0.2, a1=0.4)
                if 0 < i < 7:
                    stroke([(x * 0.75 + 0.03, -0.62 + 0.25 * abs(x)), (x * 0.95, yb - 0.13)], 0.45, a0=0.4, a1=1.0)
            for i in range(4):
                y = 0.08 + i * 0.07
                stroke([(-0.5 + i * 0.04, y), (-0.42 + i * 0.05, y + 0.1)], 0.55, a0=0.2, a1=0.5)
        elif hair == 'short':
            stroke(hm[:9], 1.0, redraw=0.1)
            stroke(hm[8:] + [hm[0]], 0.8, a0=0.5)
            if w > 60:
                for i in range(3):
                    t = i / 3
                    stroke([(0.2 - t * 0.2, -0.45 + t * 0.1), (-0.15 - t * 0.1, -0.3 + t * 0.2)], 0.55, a0=0.4, a1=1.2, hx=True)
        else:
            n = 13
            pts = hm[:8]
            dense = catmull(pts, False, 0.02)
            s = cumlen(dense)
            L = s[-1]
            j = 0
            marks = []
            for i in range(n + 1):
                t = L * i / n
                while j < len(s) - 2 and s[j + 1] < t:
                    j += 1
                marks.append(dense[j])
            for i in range(n):
                p0, p1 = marks[i], marks[i + 1]
                mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
                nx, ny = -(p1[1] - p0[1]), (p1[0] - p0[0])
                stroke([p0, (mx + nx * 0.45, my + ny * 0.45), p1], 0.9, a0=0.3, a1=0.8)
            stroke(hm[7:] + [hm[0]], 0.8, a0=0.5)
            for i in range(5):
                x, y = rng.uniform(-0.45, 0.1), rng.uniform(-0.45, 0.15)
                s_ = 0.07
                stroke([(x - s_, y), (x, y - s_), (x + s_ * 0.6, y + s_ * 0.3)], 0.6, a0=0.3, a1=0.7, hx=True)
        if earring:
            x0, y0 = ex - 0.06, ey + 0.15
            stroke([(x0, y0), (x0 - 0.005, y0 + 0.07)], 0.55)
            bell = [(x0 - 0.075, y0 + 0.19), (x0 - 0.05, y0 + 0.1), (x0, y0 + 0.07), (x0 + 0.05, y0 + 0.1), (x0 + 0.075, y0 + 0.19)]
            self.knock(self.hand(P(bell), closed=True, wob=0, trem=0, rng=rng))
            self.blob(P(bell), 'Y', rng=rng, gap=0, shift=0.01 * w)
            stroke(bell, 0.6)
            stroke([(x0 - 0.08, y0 + 0.19), (x0 + 0.08, y0 + 0.19)], 0.6)
            for t in (-0.05, 0.0, 0.05):
                X, Y = HP(x0 + t, y0 + 0.235)
                self.dot(X, Y, max(0.012 * w, 1.4), rng=rng)
        return HP


    # ---- the edge of the city ---------------------------------------------
    # the viaduct recedes to a vanishing point far off to the right
    @staticmethod
    def vg(x):
        yt = 556 + 0.145 * (x - 22)
        yb = 581 + 0.128 * (x - 22)
        return yt, yb, (yb - yt) / 25.0

    @staticmethod
    def vz(z):
        return 1500 - 1440 / z

    @staticmethod
    def vzinv(x):
        return 1440 / (1500 - x)

    def viaduct(self, rng):
        lw = MINW * 1.1
        X0, XE = 24, 474          # where the drawing starts, where the line ends
        # deck: parapet top, deck edge, soffit
        ytl, ybl, _ = self.vg(X0)
        ytr, ybr, _ = self.vg(XE)
        self.knock([(X0, ytl - 4), (XE, ytr - 3), (XE, ybr + 1), (X0, ybl + 1)])
        self.line([(X0 - 2, ytl), (250, self.vg(250)[0] + 0.6), (XE + 1, ytr)], lw * 1.1, rng=rng, wob=0.5, trem=0.6, a0=0.6, a1=1.5, redraw=0.4)
        self.line([(X0 + 3, ytl + 5.5), (300, self.vg(300)[0] + 4.2), (XE - 2, ytr + 3.4)], MINW, rng=rng, wob=0.4, trem=0.5, a0=2.0, a1=6.0)
        self.line([(X0 - 1, ybl), (200, self.vg(200)[1] - 0.5), (XE, ybr)], lw, rng=rng, wob=0.5, trem=0.6, a0=0.5, a1=1.0)
        # end of the line: the deck stops, a buffer stop on it
        self.line([(XE, ytr - 1), (XE + rng.gauss(0, 0.3), ybr + 1)], lw, rng=rng, wob=0.2, trem=0)
        bx = XE - 7
        by = self.vg(bx)[0]
        self.line([(bx - 4, by), (bx - 3, by - 9), (bx + 3, by - 9), (bx + 4, by)], MINW, rng=rng, wob=0.2, trem=0, a0=0.3, a1=0.3)
        self.dot(bx, by - 12, 1.8, layer='Y', rng=rng)
        self.marks['end'] = (XE, ytr)
        # segment joints + piers (perspective spacing)
        k = 0
        while True:
            x = self.vz(1 + 0.06 * k)
            k += 1
            if x > XE - 10:
                break
            yt, yb, sc = self.vg(x)
            self.line([(x + 0.4, yt + 1.5), (x, yb - 1)], MINW, rng=rng, wob=0.2, trem=0, a0=0.3, a1=0.3)
            cw = 8.5 * sc + 1.5
            cap = [(x - 17 * sc, yb), (x + 17 * sc, yb), (x + cw * 0.6, yb + 11 * sc), (x - cw * 0.6, yb + 11 * sc)]
            col = [(x - cw / 2, yb + 10 * sc), (x + cw / 2, yb + 10 * sc), (x + cw / 2 + 0.5, 770), (x - cw / 2 - 0.5, 770)]
            self.knock(cap)
            self.knock(col)
            self.line([cap[0], (x - cw * 0.55, yb + 10 * sc), (x - cw / 2 + rng.gauss(0, 0.3), 770)], lw, rng=rng, wob=0.3, trem=0.4, a0=0.5, a1=3.0)
            self.line([cap[1], (x + cw * 0.55, yb + 10 * sc), (x + cw / 2 + rng.gauss(0, 0.3), 770)], lw, rng=rng, wob=0.3, trem=0.4, a0=0.5, a1=3.0)
            # the side away from the stage lights: a few hand hatches, never the same twice
            if cw > 7:
                nh = rng.randint(1, 3) if sc > 0.75 else rng.randint(0, 1)
                for j in range(nh):
                    hx = x - cw * 0.5 + 2.6 + j * 2.9 + rng.uniform(-0.4, 0.4)
                    if hx > x - 0.5:
                        break
                    y0h = yb + 13 * sc + rng.uniform(0, 14)
                    self.line([(hx, y0h), (hx + rng.gauss(0, 0.3), y0h + rng.uniform(18, 70) * sc)], MINW, rng=rng, wob=0.2, trem=0.2, a0=0.5, a1=3.0)
            # a lamp post on the parapet every other span
            if k % 2 == 0 and x < XE - 30:
                lx = x + rng.uniform(2, 6) * sc
                ly = self.vg(lx)[0]
                lh = 24 * sc + 4
                self.line([(lx, ly - 1), (lx + rng.gauss(0, 0.3), ly - lh), (lx + 5 * sc + 1.5, ly - lh - 1.5)], MINW, rng=rng, wob=0.15, trem=0, a0=0.3, a1=0.4)
                self.dot(lx + 5 * sc + 2.5, ly - lh + 1.2, 1.9, layer='Y', rng=rng)
        self.marks['viaduct'] = (180, self.vg(180)[1])

    def train(self, rng):
        """a green line train coming in to madavara, lit windows, people standing inside"""
        nose = 296
        zn = self.vzinv(nose)
        L = 0.046
        cars = []
        z = zn
        while True:
            z0 = z - L
            xa, xb = self.vz(max(z0, 0.5)), self.vz(z)
            cars.append((max(xa, 26), xb, xa < 26))
            if xa < 26:
                break
            z = z0 - 0.0035
        lw = MINW * 1.05

        def ry(x):   # roof
            yt, yb, sc = self.vg(x)
            return yt - 37 * sc

        for i, (xa, xb, cut) in enumerate(cars):
            ya_t, _, sa = self.vg(xa)
            yb_t, _, sb = self.vg(xb)
            front = i == 0
            body = [(xa, ry(xa) + 2 * sa), (xb - (6 * sb if front else 0), ry(xb) + 2 * sb), (xb, ry(xb) + 9 * sb), (xb + (5 * sb if front else 0), yb_t - 3 * sb),
                    (xb, yb_t - 0.5), (xa, ya_t - 0.5)]
            self.knock(body)
            # roof + skirt
            self.line([(xa + (0 if cut else 2), ry(xa) + 2 * sa), ((xa + xb) / 2, ry((xa + xb) / 2) + 1.5 * sa), (xb - (6 * sb if front else 2), ry(xb) + 2 * sb)],
                      lw, rng=rng, wob=0.4, trem=0.4, a0=0.6, a1=1.2)
            if front:
                self.line([(xb - 6 * sb, ry(xb) + 2 * sb), (xb + 1 * sb, ry(xb) + 8 * sb), (xb + 5 * sb, yb_t - 9 * sb), (xb + 4 * sb, yb_t - 2)],
                          lw, rng=rng, wob=0.3, trem=0.2, a0=0.5, a1=0.8)
                self.dot(xb + 2.5 * sb, yb_t - 7 * sb, 2.1, layer='Y', rng=rng)
                fw = [(xb - 2 * sb, ry(xb) + 8 * sb), (xb + 2 * sb, ry(xb) + 11 * sb), (xb + 3 * sb, ry(xb) + 19 * sb), (xb - 1.5 * sb, ry(xb) + 19 * sb)]
                self.box(fw, MINW, rng=rng, over=(-0.5, 0.8), wob=0.1)
            elif not cut:
                pass
            if not cut:
                self.line([(xa, ry(xa) + 3 * sa), (xa + rng.gauss(0, 0.2), ya_t - 1)], MINW, rng=rng, wob=0.2, trem=0, a0=0.3, a1=0.3)
            # green band (the line's colour) under the windows
            def yat(x, f):
                return ry(x) + (self.vg(x)[0] - ry(x)) * f
            band = [(xa + 1, yat(xa, 0.70)), (xb - 1, yat(xb, 0.70)), (xb - 1, yat(xb, 0.84)), (xa + 1, yat(xa, 0.84))]
            self.blob(band, 'G', rng=rng, scale=(1.0, 1.04), jit=0.01, shift=0.4, gap=0.0, n=40)
            # windows + doors
            n = 5
            for j in range(n):
                u0 = (j + 0.18) / n
                u1 = (j + 0.82) / n
                x0, x1 = xa + (xb - xa) * u0, xa + (xb - xa) * u1
                if x1 - x0 < 4:
                    continue
                win = [(x0, yat(x0, 0.2)), (x1, yat(x1, 0.2)), (x1, yat(x1, 0.58)), (x0, yat(x0, 0.58))]
                if j % 2 == 1:
                    # a door: two leaves, a slit of window
                    self.line([((x0 + x1) / 2, yat((x0 + x1) / 2, 0.16)), ((x0 + x1) / 2 + rng.gauss(0, 0.2), yat((x0 + x1) / 2, 0.97))], MINW, rng=rng, wob=0.15, trem=0, a0=0.3, a1=0.3)
                    self.box([(x0, yat(x0, 0.16)), (x1, yat(x1, 0.16)), (x1, yat(x1, 0.97)), (x0, yat(x0, 0.97))], MINW, rng=rng, over=(-0.4, 0.8), wob=0.1)
                    continue
                if rng.random() < 0.86:
                    self.blob(win, 'Y', rng=rng, scale=(1.0, 1.08), jit=0.02, shift=0.4, gap=0.0, n=16)
                    # someone standing in the light, holding the grab rail
                    if x1 - x0 > 9 and rng.random() < 0.7:
                        hx = x0 + (x1 - x0) * rng.uniform(0.3, 0.7)
                        hy = yat(hx, 0.42)
                        hr = max(2.6, (x1 - x0) * 0.16)
                        sh = [(hx - hr * 2.0, yat(hx, 0.62)), (hx - hr * 1.6, hy + hr * 1.8), (hx - hr * 0.6, hy + hr * 1.3), (hx - hr, hy), (hx, hy - hr * 1.05),
                              (hx + hr, hy), (hx + hr * 0.6, hy + hr * 1.3), (hx + hr * 1.6, hy + hr * 1.8), (hx + hr * 2.0, yat(hx, 0.62))]
                        self.knock(sh, layers=('Y',))
                self.box(win, MINW, rng=rng, over=(-0.6, 1.0), wob=0.1)
        self.marks['train'] = (150, ry(150) - 2)

    def station(self, rng):
        """madavara: the last station, a long box under a shallow curved roof"""
        xa, xb = 306, 462
        lw = MINW * 1.1
        ya, _, sa = self.vg(xa)
        yb_, _, sb = self.vg(xb)
        top_a, top_b = ya - 44 * sa, yb_ - 44 * sb
        bot_a, bot_b = self.vg(xa)[1] + 30 * sa, self.vg(xb)[1] + 30 * sb
        roof = [(xa - 10, top_a + 4), (xa + 40, top_a - 9), ((xa + xb) / 2 + 10, (top_a + top_b) / 2 - 12), (xb - 30, top_b - 8), (xb + 8, top_b + 4)]
        box = [(xa, top_a), (xb, top_b), (xb, bot_b), (xa, bot_a)]
        self.knock(box + [(xb + 8, top_b + 4)] + roof[::-1])
        self.knock(roof + [(xb + 8, top_b + 9)] + [(xa - 10, top_a + 9)])
        self.line(roof, lw * 1.15, rng=rng, wob=0.6, trem=0.6, a0=0.8, a1=1.6, redraw=0.6)
        self.line([(xa - 9, top_a + 9), (xa + 40, top_a - 3), ((xa + xb) / 2 + 10, (top_a + top_b) / 2 - 6), (xb + 7, top_b + 8)], MINW, rng=rng, wob=0.5, trem=0.5)
        self.line([(xa - 10, top_a + 4), (xa - 9, top_a + 9)], MINW, rng=rng, wob=0.1, trem=0)
        self.line([(xb + 8, top_b + 4), (xb + 7, top_b + 8)], MINW, rng=rng, wob=0.1, trem=0)
        # glass wall: mullions, a few lit panes
        k = 13
        for i in range(k + 1):
            t = i / k
            x = xa + (xb - xa) * t
            yt = top_a + (top_b - top_a) * t + 10
            ybot = bot_a + (bot_b - bot_a) * t
            if i in (0, k):
                self.line([(x, yt - 9), (x + rng.gauss(0, 0.3), ybot)], lw, rng=rng, wob=0.2, trem=0.2, a0=0.5, a1=0.8)
            else:
                self.line([(x, yt + rng.uniform(0, 3)), (x + rng.gauss(0, 0.3), ybot - rng.uniform(16, 24))], MINW, rng=rng, wob=0.2, trem=0.2, a0=0.3, a1=1.5)
                if rng.random() < 0.35:
                    x2 = xa + (xb - xa) * (i + 1) / k
                    yy = yt + rng.uniform(3, 9)
                    self.blob([(x + 2, yy), (x2 - 2, yy), (x2 - 2, yy + 9), (x + 2, yy + 9)], 'Y', rng=rng, gap=0.0, shift=0.5, n=10)
        # platform edge + the line's colour on the fascia
        pl_a = self.vg(xa)[0]
        pl_b = self.vg(xb)[0]
        self.line([(xa - 2, pl_a + 1), (xb + 2, pl_b + 1)], lw, rng=rng, wob=0.4, trem=0.4)
        self.line([(xa - 2, bot_a - 14), (xb + 2, bot_b - 13)], MINW, rng=rng, wob=0.4, trem=0.4)
        self.blob([(xa + 2, bot_a - 12), (xb - 2, bot_b - 11), (xb - 2, bot_b - 3), (xa + 2, bot_a - 4)], 'G', rng=rng, gap=0.0, shift=0.5, jit=0.02, n=30)
        self.line([(xa - 2, bot_a), (xb + 2, bot_b)], lw, rng=rng, wob=0.4, trem=0.4, a0=0.5, a1=1.5)
        # stairs down to the road
        s0 = (xb - 14, bot_b)
        s1 = (xb + 24, 742)
        self.knock([s0, (s0[0] + 12, s0[1]), (s1[0] + 12, s1[1]), s1])
        self.line([s0, s1], MINW, rng=rng, wob=0.2, trem=0.2)
        self.line([(s0[0] + 12, s0[1]), (s1[0] + 12, s1[1])], MINW, rng=rng, wob=0.2, trem=0.2)
        for i in range(1, 9):
            t = i / 9
            x = s0[0] + (s1[0] - s0[0]) * t
            y = s0[1] + (s1[1] - s0[1]) * t
            self.line([(x, y), (x + 12, y)], MINW, rng=rng, wob=0.1, trem=0, a0=0.2, a1=0.2)
        self.marks['station'] = ((xa + xb) / 2, top_a - 6)

    def road(self, rng):
        """tumakuru road under the viaduct: a lorry, a couple of headlights"""
        self.line([(26, 741), (160, 742.5), (300, 743)], MINW, rng=rng, wob=0.4, trem=0.5, a0=1.0, a1=4.0)
        x = 30
        while x < 290:
            l = rng.uniform(7, 11)
            self.line([(x, 750.5), (x + l, 750.8)], MINW, rng=rng, wob=0.2, trem=0, a0=0.3, a1=0.3)
            x += l + rng.uniform(7, 11)
        # the lorry: cab right, tarpaulin roped over the load
        x0, gy = 86, 757
        lw = MINW * 1.1
        body = [(x0, gy - 11), (x0, gy - 40), (x0 + 6, gy - 50), (x0 + 30, gy - 54), (x0 + 58, gy - 51), (x0 + 68, gy - 41), (x0 + 68, gy - 11)]
        cab = [(x0 + 70, gy - 11), (x0 + 70, gy - 44), (x0 + 88, gy - 44), (x0 + 99, gy - 32), (x0 + 101, gy - 11)]
        self.knock(body)
        self.knock(cab)
        self.blob([(x0 + 71, gy - 13), (x0 + 71, gy - 43), (x0 + 87, gy - 43), (x0 + 98, gy - 31), (x0 + 99, gy - 13)], 'Y', rng=rng, gap=0.0, shift=0.6, n=20)
        self.line(body, lw, rng=rng, wob=0.4, trem=0.3, a0=0.5, a1=0.8)
        self.line([(x0 + 1, gy - 26), (x0 + 67, gy - 26)], MINW, rng=rng, wob=0.3, trem=0.2)
        for t in (0.2, 0.42, 0.66, 0.86):
            xx = x0 + 68 * t
            self.line([(xx, gy - 50 + 3 * abs(t - 0.45)), (xx + rng.gauss(0, 0.5), gy - 27)], MINW, rng=rng, wob=0.2, trem=0, a0=0.3, a1=0.5)
        # rope criss-cross
        for a, b in (((x0 + 4, gy - 44), (x0 + 34, gy - 28)), ((x0 + 34, gy - 50), (x0 + 64, gy - 29)), ((x0 + 6, gy - 28), (x0 + 34, gy - 51)), ((x0 + 36, gy - 28), (x0 + 63, gy - 46))):
            self.line([a, b], MINW, rng=rng, wob=0.2, trem=0, a0=0.3, a1=0.4)
        self.line(cab, lw, rng=rng, wob=0.3, trem=0.2, a0=0.5, a1=0.8)
        self.box([(x0 + 82, gy - 41), (x0 + 88, gy - 41), (x0 + 96, gy - 32), (x0 + 82, gy - 32)], MINW, rng=rng, over=(-0.4, 0.8), wob=0.1)
        self.line([(x0 + 79, gy - 30), (x0 + 79, gy - 14)], MINW, rng=rng, wob=0.1, trem=0)
        self.line([(x0 - 2, gy - 11), (x0 + 103, gy - 11)], lw, rng=rng, wob=0.3, trem=0.2)
        for wx in (x0 + 14, x0 + 30, x0 + 86):
            ring = [(wx + math.cos(a) * 6.5, gy - 6 + math.sin(a) * 6.5) for a in [TAU * i / 8 for i in range(8)]]
            self.knock(ring)
            self.line(ring, MINW, rng=rng, wob=0.2, trem=0, closed=True, close_frac=1.02)
            self.dot(wx, gy - 6, 1.5, rng=rng)
        # headlight: a short spill forward
        hx, hy = x0 + 101, gy - 19
        self.dot(hx, hy, 2.0, layer='Y', rng=rng)
        for a in (-0.35, -0.05, 0.25):
            self.line([(hx + 5, hy + a * 6), (hx + 22 + rng.uniform(0, 8), hy + a * 22)], MINW, rng=rng, layer='Y', wob=0.3, trem=0, a0=0.4, a1=2.0)
        self.marks['lorry'] = (x0 + 50, gy - 54)
        # an auto coming the other way: yellow hood, green body, the way they run here
        self.auto(250, gy, rng)
        # a car further down, just its lights
        for (hx, hy) in ((300, 748),):
            self.dot(hx, hy, 2.1, layer='Y', rng=rng)
            self.dot(hx + 7, hy + 0.4, 2.1, layer='Y', rng=rng)

    def auto(self, xf, gy, rng):
        """an autorickshaw side-on, nose to the left"""
        xr = xf + 36
        hood = [(xf + 7, gy - 15), (xf + 8, gy - 27), (xf + 14, gy - 31), (xr - 8, gy - 32), (xr - 1, gy - 27), (xr + 1, gy - 14)]
        body = [(xf - 1, gy - 6), (xf, gy - 12), (xf + 5, gy - 16), (xr + 1, gy - 15), (xr + 2, gy - 6)]
        self.knock(hood + [(xr + 2, gy - 4), (xf - 1, gy - 4), (xf, gy - 12)])
        self.blob([(xf + 9, gy - 26), (xf + 14, gy - 30), (xr - 8, gy - 31), (xr - 1, gy - 26), (xr - 1, gy - 22), (xf + 9, gy - 22)], 'Y', rng=rng, gap=0.0,
                  shift=0.5, jit=0.03, n=16)
        self.blob([(xf + 1, gy - 7), (xf + 2, gy - 12), (xf + 6, gy - 15), (xr, gy - 14), (xr + 1, gy - 7)], 'G', rng=rng, gap=0.0, shift=0.5, jit=0.03, n=16)
        self.line(hood, MINW, rng=rng, wob=0.3, trem=0.2, a0=0.5, a1=0.8)
        self.line(body, MINW, rng=rng, wob=0.3, trem=0.2, a0=0.5, a1=0.8)
        self.line([(xf + 8, gy - 27), (xf + 3, gy - 14)], MINW, rng=rng, wob=0.2, trem=0, a0=0.3, a1=0.4)     # windscreen
        self.line([(xr - 12, gy - 31), (xr - 13, gy - 15)], MINW, rng=rng, wob=0.2, trem=0, a0=0.3, a1=0.4)  # the door gap
        for wx in (xf + 6, xr - 5):
            ring = [(wx + math.cos(a) * 4.2, gy - 3.8 + math.sin(a) * 4.2) for a in [TAU * i / 7 for i in range(7)]]
            self.knock(ring)
            self.line(ring, MINW, rng=rng, wob=0.15, trem=0, closed=True, close_frac=1.02)
        self.dot(xf + 1, gy - 12.5, 2.0, layer='Y', rng=rng)
        for a in (-0.25, 0.1):
            self.line([(xf - 4, gy - 12 + a * 4), (xf - 16 - rng.uniform(0, 6), gy - 12 + a * 16)], MINW, rng=rng, layer='Y', wob=0.2, trem=0, a0=0.4, a1=2.0)
        self.marks['auto'] = (xf + 18, gy - 32)

    def low_buildings(self, rng):
        lw = MINW
        for (x0, x1, top) in ((154, 196, 712), (198, 226, 722), (232, 284, 706), (286, 302, 724)):
            pts = [(x0, 740), (x0, top), (x1, top), (x1, 740)]
            self.knock(pts)
            self.box(pts, lw, rng=rng, over=(-1.0, 2.5), bow=0.006)
            # a black water tank on the roof
            if x1 - x0 > 24:
                tx = rng.uniform(x0 + 5, x1 - 16)
                tk = [(tx, top - 10), (tx + 10, top - 10), (tx + 10, top), (tx, top)]
                self.knock(tk)
                self.line([(tx, top), (tx, top - 9), (tx + 2, top - 11), (tx + 8, top - 11), (tx + 10, top - 9), (tx + 10, top)], lw, rng=rng, wob=0.15, trem=0, a0=0.3, a1=0.3)
                self.line([(tx + 0.5, top - 6), (tx + 9.5, top - 6.3)], lw * 0.9, rng=rng, wob=0.1, trem=0, a0=0.2, a1=0.2)
            y = top + 8
            while y < 734:
                for c in range(max(1, int((x1 - x0) / 11))):
                    xx = x0 + 6 + c * 11 + rng.uniform(-1, 1)
                    if xx > x1 - 5:
                        continue
                    q = rng.random()
                    if q < 0.18:
                        self.blob([(xx - 2.6, y - 2.4), (xx + 2.6, y - 2.4), (xx + 2.6, y + 2.4), (xx - 2.6, y + 2.4)], 'Y', rng=rng, gap=0, shift=0.5, n=10)
                    elif q < 0.45:
                        self.line([(xx - 2.2, y), (xx + 2.2, y + rng.gauss(0, 0.3))], MINW, rng=rng, wob=0.15, trem=0, a0=0.2, a1=0.2)
                y += rng.uniform(9, 11)

    def high_mast(self, x, base, top, rng):
        """a highway high-mast lamp over the interchange"""
        self.line([(x - 2.4, base), (x - 0.9, top + 6)], MINW, rng=rng, wob=0.2, trem=0.3, a0=0.5, a1=0.8)
        self.line([(x + 2.4, base), (x + 0.9, top + 6)], MINW, rng=rng, wob=0.2, trem=0.3, a0=0.5, a1=0.8)
        ring = [(x + math.cos(a) * 15, top + math.sin(a) * 4.5) for a in [TAU * i / 10 for i in range(10)]]
        self.line(ring, MINW, rng=rng, wob=0.2, trem=0, closed=True, close_frac=1.0)
        for i, a in enumerate((2.6, 2.0, 1.4, 0.9, 0.45)):
            lx, ly = x + math.cos(a) * 15, top + math.sin(a) * 4.5 + 4
            self.blob([(lx - 2.6, ly - 2), (lx + 2.6, ly - 2), (lx + 2.2, ly + 2.8), (lx - 2.2, ly + 2.8)], 'Y', rng=rng, gap=0.0, shift=0.3, n=8)
        for a in (-0.4, 0.0, 0.4):
            self.line([(x + math.sin(a) * 18, top + 10), (x + math.sin(a) * 34, top + 26)], MINW, rng=rng, wob=0.2, trem=0, layer='Y', a0=0.4, a1=2.0)
        self.marks['mast'] = (x, top)

    def hall(self, xa, xb, eave_a, eave_b, ridge_dy, base, rng, gable=True, vault=False):
        lw = MINW * 1.05
        ga = 30 if gable else 0
        peak = (xa + ga * 0.5, eave_a - ridge_dy)
        ridge_end = (xb, eave_b - ridge_dy * 0.75)
        if vault:
            top = [(xa, eave_a), (xa + (xb - xa) * 0.15, eave_a - ridge_dy * 0.8), ((xa + xb) / 2, (eave_a + eave_b) / 2 - ridge_dy), (xb, eave_b - ridge_dy * 0.9)]
            sil = top + [(xb, base), (xa, base)]
        else:
            sil = [(xa, eave_a + 2), peak, ridge_end, (xb, eave_b), (xb, base), (xa, base)]
        self.knock(sil)
        if vault:
            self.line(top, lw * 1.1, rng=rng, wob=0.5, trem=0.6, redraw=0.4)
            self.line([(xa, eave_a), (xb, eave_b)], lw, rng=rng, wob=0.5, trem=0.6)
            # standing-seam roof ribs
            for i in range(1, 16):
                t = i / 16
                x = xa + (xb - xa) * t
                ye = eave_a + (eave_b - eave_a) * t
                yt = ye - ridge_dy * (0.8 + 0.2 * math.sin(math.pi * t)) * (1 - 0.15 * t)
                self.line([(x + 1.5, yt + 2), (x, ye - 1)], MINW, rng=rng, wob=0.15, trem=0, a0=0.3, a1=0.6)
        else:
            self.line([(xa, eave_a + 2), peak, (xa + ga, eave_a + 1)], lw, rng=rng, wob=0.3, trem=0.2, a0=0.5, a1=1.0)
            self.line([peak, ((peak[0] + xb) / 2, (peak[1] + ridge_end[1]) / 2 - 0.5), ridge_end], lw * 1.1, rng=rng, wob=0.5, trem=0.6, redraw=0.5)
            self.line([(xa + ga, eave_a + 1), ((xa + ga + xb) / 2, (eave_a + eave_b) / 2 + 0.5), (xb, eave_b)], lw, rng=rng, wob=0.5, trem=0.6)
            self.line([(xa, eave_a + 2), (xa + rng.gauss(0, 0.3), base)], lw, rng=rng, wob=0.2, trem=0.2)
            self.line([(xa + ga, eave_a + 1), (xa + ga + rng.gauss(0, 0.3), base)], lw, rng=rng, wob=0.2, trem=0.2)
            # purlins on the roof slope
            for f in (0.35, 0.68):
                self.line([(xa + ga * (1 - f * 0.5), eave_a + 1 - ridge_dy * f), (xb, eave_b - ridge_dy * 0.75 * f)], MINW, rng=rng, wob=0.4, trem=0.5, a0=3.0, a1=8.0)
        x0 = xa + ga
        # cladding ribs, uneven, broken
        x = x0 + rng.uniform(3, 6)
        while x < xb - 3:
            t = (x - xa) / (xb - xa)
            ye = eave_a + (eave_b - eave_a) * t + 3
            if rng.random() < 0.8:
                y1 = base - rng.uniform(0, 10)
                self.line([(x, ye + rng.uniform(0, 4)), (x + rng.gauss(0, 0.3), y1)], MINW, rng=rng, wob=0.2, trem=0.2, a0=0.5, a1=2.5)
            x += rng.uniform(6.5, 10.5) * (1 - 0.25 * t)
        # big shutter doors + lamps under the eave
        for f in rng.sample([0.2, 0.42, 0.63, 0.82], 2):
            dx0 = x0 + (xb - x0) * f
            dw = 20 * (1 - 0.3 * f)
            dt = base - 26 * (1 - 0.2 * f)
            dr = [(dx0, base), (dx0, dt), (dx0 + dw, dt), (dx0 + dw, base)]
            self.knock(dr)
            self.box(dr, MINW, rng=rng, over=(-0.6, 1.5))
            for j in range(1, 4):
                yy = dt + (base - dt) * j / 4
                self.line([(dx0 + 2, yy), (dx0 + dw - 2, yy + rng.gauss(0, 0.3))], MINW, rng=rng, wob=0.1, trem=0, a0=0.2, a1=0.2)
        for f in (0.1, 0.3, 0.55, 0.78, 0.95):
            if rng.random() < 0.75:
                lx = x0 + (xb - x0) * f + rng.uniform(-6, 6)
                ly = eave_a + (eave_b - eave_a) * ((lx - xa) / (xb - xa)) + 7
                self.dot(lx, ly, 2.0, layer='Y', rng=rng)
        self.line([(xa - 3, base), (xb, base + 0.5)], lw, rng=rng, wob=0.4, trem=0.4, a0=1.0, a1=2.0)

    def leaf_edge(self, pts, rng, lw, smin=4.0, smax=13.0, gap=0.1, layer='line'):
        """a leafy edge along pts: one short stroke per scallop, scallops of very
        uneven size and swell, the pen lifting now and then"""
        dense = catmull(pts, False, 0.8)
        s = cumlen(dense)
        Lt = s[-1]
        pos = rng.uniform(0, 3)
        j = 0
        while pos < Lt - 3:
            sl = rng.uniform(smin, smax) * (1.5 if rng.random() < 0.15 else 1.0)
            a, b = pos, min(Lt, pos + sl)
            while j < len(s) - 2 and s[j + 1] < a:
                j += 1
            p0 = dense[j]
            k = j
            while k < len(s) - 2 and s[k + 1] < b:
                k += 1
            p1 = dense[k]
            if rng.random() < gap:
                pos = b + rng.uniform(0.5, 3)
                continue
            mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
            nx, ny = (p1[1] - p0[1]), -(p1[0] - p0[0])
            nn = math.hypot(nx, ny) or 1
            bul = sl * rng.uniform(0.22, 0.58)
            sk = rng.uniform(-0.18, 0.18) * sl      # lean the bump a little
            tx, ty = (p1[0] - p0[0]) / (sl or 1), (p1[1] - p0[1]) / (sl or 1)
            q = [p0, (mx + nx / nn * bul * 0.8 - tx * sl * 0.22 + tx * sk, my + ny / nn * bul * 0.8 - ty * sl * 0.22 + ty * sk),
                 (mx + nx / nn * bul + tx * sk, my + ny / nn * bul + ty * sk),
                 (mx + nx / nn * bul * 0.8 + tx * sl * 0.22 + tx * sk, my + ny / nn * bul * 0.8 + ty * sl * 0.22 + ty * sk), p1]
            self.line(q, lw, layer=layer, rng=rng, wob=0.12, trem=0, a0=0.35, a1=0.7, pv=0.15)
            pos = b + rng.uniform(-1.0, 0.4)

    def rain_tree(self, cx, base, rx, ct, cb, rng, fill=None, lean=0.0, far=False):
        """samanea saman: a wide, low umbrella of clumps on a short forked trunk"""
        lw = MINW
        # the canopy is a few overlapping clumps along a low dome
        k = max(3, int(rx / 17) + rng.randint(0, 2))
        clumps = []
        for i in range(k):
            u = -0.78 + 1.56 * (i + rng.uniform(0.2, 0.8)) / k
            crx = rx * rng.uniform(0.3, 0.46)
            dome = max(0.0, 1 - abs(u) ** 2.0) ** 0.6
            ctop = cb - (cb - ct) * (0.55 + 0.45 * dome) * rng.uniform(0.86, 1.06) + lean * u * 6
            clumps.append((cx + rx * u, ctop, crx, (cb - ctop) * rng.uniform(0.75, 1.0)))
        xs = [cx - rx + 2 * rx * i / 60 for i in range(61)]

        def ytop(x):
            best = None
            for (ux, uy, ur, uh) in clumps:
                d = (x - ux) / (ur * 1.25)
                if abs(d) < 1:
                    y = uy + uh * 0.55 * (1 - math.sqrt(1 - d * d))
                    best = y if best is None else min(best, y)
            return best
        top = [(x, ytop(x)) for x in xs if ytop(x) is not None]
        top = [(x, min(y, cb - 3)) for x, y in top]
        bot = []
        for i in range(17):
            u = 1 - 2 * i / 16
            bot.append((cx + rx * 0.96 * u, cb + 4 * (1 - u * u) + rng.gauss(0, 1.2)))
        canopy = [top[0]] + top[1:-1:2] + [top[-1]] + bot
        # trunk + limbs
        fy = cb + (base - cb) * rng.uniform(0.38, 0.5)
        fx = cx + rng.gauss(0, rx * 0.05)
        tw = max(4.0, rx * 0.075)
        trunk = [(fx - tw * 0.7, fy), (cx - tw + rng.gauss(0, 1), base), (cx + tw + rng.gauss(0, 1), base), (fx + tw * 0.7, fy)]
        self.knock(trunk)
        limbs = []
        nl = rng.randint(3, 6)
        for i in range(nl):
            u = -0.85 + 1.7 * (i + rng.uniform(0.25, 0.75)) / nl
            ex, ey = cx + rx * u * 0.85, cb + 3 * (1 - u * u) + rng.uniform(-3, 3)
            mx, my = fx + (ex - fx) * 0.45 + rng.gauss(0, 2), fy + (ey - fy) * 0.6 - abs(u) * 4
            limbs.append([(fx + u * tw * 0.6, fy + 2), (mx, my), (ex, ey + 2)])
            hl = self.hand(limbs[-1], wob=0, trem=0, rng=rng)
            wd = (2.0 + 2.2 * (1 - abs(u))) * (0.7 if far else 1.0)
            self.knock(offset_path(hl, wd) + offset_path(hl, -wd)[::-1])
        d = self.hand(canopy, closed=True, wob=0, trem=0, rng=rng)
        self.knock(d)
        if fill:
            self.blob(canopy, fill, rng=rng, scale=(0.88, 0.97), jit=0.06, shift=2.2, gap=0.75, n=44)
        self.line([trunk[0], (cx - tw * 0.85 + rng.gauss(0, 1), (fy + base) / 2), trunk[1]], lw * (1.0 if far else 1.15), rng=rng, wob=0.3, trem=0.4, a0=0.6, a1=1.0)
        self.line([trunk[3], (cx + tw * 0.85 + rng.gauss(0, 1), (fy + base) / 2), trunk[2]], lw * (1.0 if far else 1.15), rng=rng, wob=0.3, trem=0.4, a0=0.6, a1=1.0)
        if not far and rng.random() < 0.7:
            # bark: a couple of short splits on the shadow side
            for i in range(rng.randint(2, 3)):
                yy = fy + (base - fy) * rng.uniform(0.2, 0.8)
                self.line([(cx + tw * 0.35, yy), (cx + tw * 0.4 + rng.gauss(0, 0.5), yy + rng.uniform(4, 8))], MINW, rng=rng, wob=0.15, trem=0, a0=0.3, a1=0.5)
        for lm in limbs:
            p = self.hand(lm, wob=0.5, trem=0.3, rng=rng)
            self.ink(p, lw, rng=rng, a0=0.6, a1=1.5, pv=0.25)
            if rng.random() < 0.6 and not far:
                a, b = p[int(len(p) * 0.6)], p[-1]
                self.line([a, (b[0] + rng.uniform(-9, 9), b[1] - rng.uniform(0, 4))], MINW, rng=rng, wob=0.3, trem=0, a0=0.4, a1=0.8)
        # the leafy top, then the lobes of the clumps behind showing through
        self.leaf_edge(top, rng, lw, smin=3.5 if far else 4.0, smax=9.0 if far else 13.0, gap=0.16 if far else 0.08)
        if not far:
            order = sorted(range(k), key=lambda i: clumps[i][1])
            for i in order[:max(1, k - 2)]:
                ux, uy, ur, uh = clumps[i]
                if rng.random() < 0.45:
                    continue
                # the lower rim of a high clump, drawn where it sits over the ones in front
                arc = []
                a0, a1 = rng.uniform(0.15, 0.35) * math.pi, rng.uniform(0.62, 0.88) * math.pi
                for j in range(7):
                    a = a0 + (a1 - a0) * j / 6
                    arc.append((ux + math.cos(a) * ur * 0.95, uy + uh * 0.35 + math.sin(a) * uh * 0.45))
                arc = [(x, y) for x, y in arc if y < cb - 2 and abs(x - cx) < rx * 0.9]
                if len(arc) > 2:
                    self.leaf_edge(arc, rng, lw, smin=3.5, smax=8.0, gap=0.2)
            # leaf ticks in loose clusters, on the lit (upper-left) side of clumps
            for (ux, uy, ur, uh) in clumps:
                for c in range(1 if rng.random() < 0.55 else 0):
                    gx = ux + rng.uniform(-0.55, 0.25) * ur
                    gy = uy + uh * rng.uniform(0.15, 0.5)
                    for t in range(rng.randint(2, 5)):
                        x = gx + rng.gauss(0, ur * 0.18)
                        y = gy + rng.gauss(0, uh * 0.12)
                        if y > cb - 4 or abs(x - cx) > rx * 0.9:
                            continue
                        s_ = rng.uniform(3.0, 5.5)
                        if rng.random() < 0.5:
                            self.line([(x - s_, y), (x - s_ * 0.2, y - s_ * 0.55), (x + s_ * 0.6, y - s_ * 0.1)], MINW, rng=rng, wob=0.2, trem=0, a0=0.3, a1=0.5)
                        else:
                            self.line([(x - s_ * 0.6, y - s_ * 0.5), (x, y), (x + s_ * 0.6, y - s_ * 0.5)], MINW, rng=rng, wob=0.2, trem=0, a0=0.3, a1=0.5)
        # underside: the dark under the umbrella, a few hanging ticks
        for i in range(int(rx / (9 if far else 5))):
            u = rng.uniform(-0.95, 0.95)
            x = cx + rx * 0.96 * u
            y = cb + 4 * (1 - u * u)
            if rng.random() < 0.6:
                self.line([(x - 1.5, y - 1), (x + rng.gauss(0, 1), y + rng.uniform(3, 8))], MINW, rng=rng, wob=0.2, trem=0, a0=0.3, a1=0.5)
        if not far:
            self.line([bot[0], bot[len(bot) // 2], bot[-1]], MINW, rng=rng, wob=0.6, trem=0.6, a0=2.0, a1=6.0, pv=0.35)

    def moon(self, x, y, r, rng, tilt=-0.6):
        """a four-day moon, low in the west"""
        out = []
        for i in range(19):
            a = -math.pi / 2 + math.pi * i / 18
            out.append((math.cos(a) * r, math.sin(a) * r))
        inn = []
        for i in range(19):
            a = math.pi / 2 - math.pi * i / 18
            inn.append((math.cos(a) * r * 0.42, math.sin(a) * r * 0.97))
        ca, sa = math.cos(tilt), math.sin(tilt)
        pts = [(x + px_ * ca - py_ * sa, y + px_ * sa + py_ * ca) for px_, py_ in out + inn]
        d = self.hand(pts, closed=True, wob=0.2, trem=0, rng=rng)
        self.D['line'].polygon([(px_ * S, (py_ + OY) * S) for px_, py_ in d], fill=255)
        self.ink(d, MINW, closed=True, rng=rng, a0=0.3, a1=0.5, close_frac=1.02)
        self.marks['moon'] = (x, y)

    def bat(self, x, y, s, rng, ang=0.0):
        """a flying fox heading out over the rain trees"""
        def T(u, v):
            ca, sa = math.cos(ang), math.sin(ang)
            return (x + (u * ca - v * sa) * s, y + (u * sa + v * ca) * s)
        fl = rng.uniform(-0.15, 0.15)
        for sg in (-1, 1):
            edge = [T(0, -0.05), T(sg * 0.35, -0.3 - fl), T(sg * 0.75, -0.22 - fl), T(sg * 1.05, 0.05)]
            self.line(edge, MINW, rng=rng, wob=0.02 * s, trem=0, a0=0.3, a1=0.5)
            sc = [T(sg * 1.05, 0.05), T(sg * 0.85, 0.02), T(sg * 0.75, 0.14), T(sg * 0.55, 0.06), T(sg * 0.42, 0.18), T(sg * 0.2, 0.1)]
            self.line(sc, MINW, rng=rng, wob=0.01 * s, trem=0, a0=0.3, a1=0.4)
        self.dot(*T(0, 0.05), max(0.13 * s, 1.7), rng=rng)

    # ---- the stage --------------------------------------------------------
    def stage(self, rng):
        lw = 3.0
        cx = STX
        x0, x1 = cx - 112, cx + 108
        deck_top, deck_bot = 771, 790
        m0, m1 = cx - 104, cx + 100     # masts
        top = 662
        # screen
        sx0, sx1, sy0, sy1 = cx - 76, cx + 78, 684, 758
        scr = [(sx0, sy0), (sx1, sy0), (sx1, sy1), (sx0, sy1)]
        self.knock(scr)
        # on the screen: a big hand-drawn sun of light, scan lines
        self.blob([(cx + 2 + math.cos(a) * 21, 717 + math.sin(a) * 19) for a in [TAU * i / 14 for i in range(14)]], 'Y', rng=rng, gap=0.0, shift=0.8, n=30)
        x = sx0 + 6
        while x < sx1 - 4:
            if abs(x - cx - 2) > 26 or rng.random() < 0.25:
                ya = sy0 + rng.uniform(3, 12)
                yb = sy1 - rng.uniform(3, 14)
                self.line([(x, ya), (x + rng.gauss(0, 0.6), yb)], MINW, rng=rng, wob=0.2, trem=0.3, a0=0.4, a1=1.2, pv=0.3)
            x += rng.uniform(6.5, 9.5)
        self.box(scr, lw, rng=rng)
        # masts: narrow ladders
        for mx in (m0, m1):
            pts = [(mx - 4, deck_top), (mx - 4, top), (mx + 4, top), (mx + 4, deck_top)]
            self.knock(pts)
            self.line([(mx - 4, deck_top), (mx - 4 + rng.gauss(0, 0.4), top)], lw, rng=rng, wob=0.3, trem=0.3)
            self.line([(mx + 4, deck_top), (mx + 4 + rng.gauss(0, 0.4), top)], lw, rng=rng, wob=0.3, trem=0.3)
            y = deck_top - 6
            while y > top + 4:
                self.line([(mx - 4, y), (mx + 4, y - rng.uniform(-1, 1.5))], MINW, rng=rng, wob=0.15, trem=0, a0=0.2, a1=0.2)
                y -= rng.uniform(11, 15)
        # the arched roof truss
        def arch(t, off):
            x = (m0 - 16) + (m1 + 16 - (m0 - 16)) * t
            y = top + 2 - 30 * math.sin(math.pi * t) ** 0.85 + off
            return (x, y)
        outer = [arch(i / 24, 0) for i in range(25)]
        inner = [arch(i / 24, 10) for i in range(25)]
        self.knock(outer + inner[::-1])
        self.line(outer[::3] + [outer[-1]], lw, rng=rng, wob=0.4, trem=0.5, redraw=0.6)
        self.line(inner[::3] + [inner[-1]], lw * 0.9, rng=rng, wob=0.4, trem=0.5)
        k = 26
        for i in range(k):
            t0, t1 = i / k, (i + 1) / k
            a = arch(t0, 0 if i % 2 else 10)
            b = arch(t1, 10 if i % 2 else 0)
            self.line([a, b], MINW, rng=rng, wob=0.15, trem=0, a0=0.2, a1=0.2)
        # cans hanging under the arch; beams go up and cross
        cans = [0.1, 0.24, 0.38, 0.62, 0.76, 0.9]
        srcs = []
        for i, t in enumerate(cans):
            lx, ly = arch(t, 11)
            can = [(lx - 4, ly), (lx + 4, ly), (lx + 5.5, ly + 9), (lx - 5.5, ly + 9)]
            self.knock(can)
            self.box(can, MINW, rng=rng, over=(-0.4, 1.0))
            if i in (2,):
                self.dot(lx, ly + 11, 2.2, layer='B', rng=rng)
            else:
                self.blob([(lx - 4.5, ly + 9), (lx + 4.5, ly + 9), (lx + 3.5, ly + 13), (lx - 3.5, ly + 13)], 'Y', rng=rng, gap=0, shift=0.4, n=10)
            srcs.append(arch(t, -2))
        # sub stacks either side of the deck
        for (bx, sg) in ((x0 - 30, -1), (x1 + 4, 1)):
            for row in range(2):
                for col in range(2):
                    bx0 = bx + col * 14
                    by0 = deck_bot - 15 - row * 15
                    bb = [(bx0, by0), (bx0 + 13, by0), (bx0 + 13, by0 + 14), (bx0, by0 + 14)]
                    self.knock(bb)
                    self.box(bb, MINW, rng=rng, over=(-0.5, 1.2))
                    ring = [(bx0 + 6.5 + math.cos(a) * 3.6, by0 + 7 + math.sin(a) * 3.6) for a in [TAU * i / 7 for i in range(7)]]
                    self.line(ring, MINW, rng=rng, wob=0.1, trem=0, closed=True, close_frac=1.0)
        # deck
        deck = [(x0, deck_top), (x1, deck_top), (x1 + 3, deck_bot), (x0 - 3, deck_bot)]
        self.knock(deck)
        self.box(deck, lw, rng=rng, over=(-1.0, 4.0))
        for i in range(1, 11):
            xx = x0 + (x1 - x0) * i / 11 + rng.uniform(-3, 3)
            if rng.random() < 0.7:
                self.line([(xx, deck_top + 3), (xx + rng.gauss(0, 0.4), deck_bot - 2)], MINW, rng=rng, wob=0.2, trem=0, a0=0.3, a1=0.4)
        # the dj: tiny, both arms up in a V over the decks
        dx = cx + 6
        tb = [(dx - 20, 757), (dx + 20, 757), (dx + 20, 771), (dx - 20, 771)]
        p = [(dx - 5, 757), (dx - 5, 747), (dx - 3, 743), (dx + 3, 743), (dx + 5, 747), (dx + 5, 757)]
        self.knock(p)
        self.line([(dx - 5.5, 757), (dx - 5, 746), (dx - 2, 742.5)], lw, rng=rng, wob=0.1, trem=0, a0=0.3, a1=0.3)
        self.line([(dx + 5.5, 757), (dx + 5, 746), (dx + 2, 742.5)], lw, rng=rng, wob=0.1, trem=0, a0=0.3, a1=0.3)
        hd = [(dx + math.cos(a) * 4.6, 737.5 + math.sin(a) * 5.2) for a in [TAU * i / 8 for i in range(8)]]
        self.knock(hd)
        self.line(hd, lw * 0.9, rng=rng, wob=0.1, trem=0, closed=True, close_frac=1.03)
        for sg in (-1, 1):
            self.line([(dx + sg * 4.5, 745), (dx + sg * 10, 734), (dx + sg * 14, 722)], lw * 0.9, rng=rng, wob=0.15, trem=0, a0=0.3, a1=0.3)
            self.dot(dx + sg * 14.6, 720.5, 2.0, rng=rng)
        self.knock(tb)
        self.box(tb, lw, rng=rng, over=(-0.5, 2.5))
        self.dot(dx - 12, 764, 1.8, layer='B', rng=rng)
        self.blob([(dx - 2, 760), (dx + 14, 760), (dx + 14, 768), (dx - 2, 768)], 'Y', rng=rng, gap=0, shift=0.5, n=10)
        self.marks['stage'] = (cx, 735)
        return srcs

    def beams(self, srcs, rng):
        """the light goes up and crosses, then stops: no glow, just lines"""
        # left cans lean right, right cans lean left
        targets = [(STX + 120, 486), (STX + 205, 520), (STX + 30, 470), (STX - 40, 476), (STX - 200, 512), (STX - 118, 484)]
        for (sx, sy), (tx, ty) in zip(srcs, targets):
            ang = math.atan2(ty - sy, tx - sx)
            L = math.hypot(tx - sx, ty - sy)
            for k in (-1, 1):
                a = ang + k * rng.uniform(0.018, 0.03)
                ln = L * rng.uniform(0.82, 1.0)
                # broken into two or three dashes, like a pen lifted
                pos = 14.0
                while pos < ln:
                    seg = rng.uniform(40, 95)
                    e = min(ln, pos + seg)
                    pa = (sx + math.cos(a) * pos, sy + math.sin(a) * pos)
                    pb = (sx + math.cos(a) * e, sy + math.sin(a) * e)
                    self.line([pa, ((pa[0] + pb[0]) / 2 + rng.gauss(0, 1), (pa[1] + pb[1]) / 2 + rng.gauss(0, 1)), pb], MINW, rng=rng, layer='Y',
                              wob=0.5, trem=0.6, a0=1.5, a1=4.0, pv=0.2)
                    pos = e + rng.uniform(6, 16)

    def sound_marks(self, rng):
        # coiled sound off the sub stacks, like a phone cord
        for (x, y, ex, ey, ph) in ((STX - 128, 738, STX - 196, 630, 0.0), (STX + 132, 738, STX + 206, 628, 1.4)):
            pts = []
            n = 120
            loops = 6.5
            for i in range(n + 1):
                t = i / n
                bx = x + (ex - x) * t + 10 * math.sin(math.pi * t) * (1 if ex > x else -1)
                by = y + (ey - y) * t
                r = 6.5 * (0.6 + 0.6 * t)
                a = TAU * loops * t + ph
                pts.append((bx + math.cos(a) * r, by + math.sin(a) * r * 0.75))
            self.line(pts[::2], MINW, rng=rng, wob=0.2, trem=0.2, a0=1.5, a1=5.0, pv=0.3)
        # little crosses and ticks over the arch
        for (x, y, s_) in ((STX - 70, 612, 5), (STX + 64, 606, 6), (STX - 6, 596, 4.5), (STX + 150, 640, 4.5), (STX - 160, 646, 4)):
            self.line([(x - s_, y + rng.gauss(0, 0.5)), (x + s_, y + rng.gauss(0, 0.5))], MINW, rng=rng, wob=0.2, trem=0, a0=0.3, a1=0.4)
            self.line([(x + rng.gauss(0, 0.5), y - s_), (x + rng.gauss(0, 0.5), y + s_)], MINW, rng=rng, wob=0.2, trem=0, a0=0.3, a1=0.4)
        for (x, y, a) in ((STX - 44, 622, -2.0), (STX + 40, 618, -1.1), (STX - 118, 636, -2.5), (STX + 120, 634, -0.6)):
            self.line([(x, y), (x + math.cos(a) * 11, y + math.sin(a) * 11)], MINW, rng=rng, wob=0.3, trem=0, a0=0.4, a1=1.0)

    def foh(self, x, y, rng):
        """the sound desk tent out in the crowd"""
        lw = MINW * 1.1
        top = y - 34
        roof = [(x - 34, y - 20), (x - 20, top), (x + 20, top), (x + 34, y - 20)]
        self.knock(roof + [(x + 34, y + 10), (x - 34, y + 10)])
        self.line(roof, lw, rng=rng, wob=0.3, trem=0.2, a0=0.5, a1=0.8)
        self.line([(x - 34, y - 20), (x + 34, y - 20)], lw, rng=rng, wob=0.3, trem=0.2)
        for i in range(1, 6):
            xx = x - 34 + 68 * i / 6
            self.line([(xx, y - 20), (xx + rng.gauss(0, 0.3), y - 16)], MINW, rng=rng, wob=0.1, trem=0, a0=0.2, a1=0.2)
        self.line([(x - 31, y - 19), (x - 31, y + 8)], MINW, rng=rng, wob=0.2, trem=0)
        self.line([(x + 31, y - 19), (x + 31, y + 8)], MINW, rng=rng, wob=0.2, trem=0)
        self.blob([(x - 18, y - 2), (x + 18, y - 2), (x + 18, y + 4), (x - 18, y + 4)], 'Y', rng=rng, gap=0.0, shift=0.5, n=12)
        for hx in (x - 10, x + 9):
            hd = [(hx + math.cos(a) * 4.2, y - 9 + math.sin(a) * 4.6) for a in [TAU * i / 8 for i in range(8)]]
            self.knock(hd)
            self.line(hd, MINW, rng=rng, wob=0.1, trem=0, closed=True, close_frac=1.03)
        self.dot(x + 22, y - 14, 1.8, layer='B', rng=rng)
        self.marks['foh'] = (x, top)

    # ---- the whole picture ------------------------------------------------
    def compose(self):
        R = lambda k: random.Random(SEED * 7919 + k)
        t0 = time.time()
        self.far_arm = 0.24
        self.clip = False

        # sky: a thin moon, three flying foxes; the rest is quiet for the type
        r = R(1)
        self.moon(1052, 498, 14, r)
        for (x, y, s_, a) in ((872, 566, 11, 0.15), (902, 590, 8, -0.2), (1004, 560, 9, 0.1)):
            self.bat(x, y, s_, r, a)
        self.marks['bats'] = (900, 572)

        # far trees behind the halls and the sheds: smaller, lighter, broken
        r = R(15)
        for (cx, rx, ct, cb) in ((770, 30, 690, 712), (842, 24, 696, 714), (1000, 34, 684, 708), (1062, 22, 694, 712), (1140, 30, 688, 710),
                                 (126, 26, 700, 722), (314, 20, 708, 724)):
            self.rain_tree(cx + r.gauss(0, 4), 740, rx, ct + r.gauss(0, 3), cb, r, fill=None, lean=r.gauss(0, 0.2), far=True)
        # far: low buildings, the mast at the interchange, the viaduct + train + station
        r = R(2)
        self.low_buildings(r)
        self.high_mast(1146, 716, 592, r)
        self.viaduct(R(3))
        self.train(R(4))
        self.station(R(5))
        self.road(R(6))
        # the exhibition halls
        r = R(7)
        self.hall(930, 1182, 708, 716, 14, 758, r, gable=False, vault=True)
        self.hall(742, 972, 716, 724, 17, 760, r, gable=True)
        self.marks['halls'] = (850, 712)
        # rain trees
        r = R(8)
        for (cx, rx, ct, cb, fill, lean) in ((226, 36, 680, 708, None, 0.2), (408, 54, 662, 704, 'G', -0.3), (520, 58, 650, 694, None, 0.0),
                                            (800, 66, 642, 692, 'G', 0.3), (936, 82, 628, 686, None, -0.2), (1098, 68, 640, 694, 'G', 0.1)):
            self.rain_tree(cx, 772, rx, ct, cb, r, fill=fill, lean=lean)
        self.marks['trees'] = (936, 628)
        # stage, light, sound
        r = R(9)
        srcs = self.stage(R(10))
        self.beams(srcs, r)
        self.sound_marks(r)
        self.stage(R(10))        # re-draw over the beam roots (same seed, same marks)
        print('  scenery %.1fs' % (time.time() - t0)); sys.stdout.flush()

        # the ground where the crowd hasn't reached: tufts, stones
        r = R(11)
        for i in range(40):
            sg = r.choice((-1, 1))
            x = 600 + sg * r.uniform(330, 560)
            y = r.uniform(798, 880)
            if abs(x - STX) < 340 + (y - 800) * 3.6:
                continue
            if r.random() < 0.5:
                s_ = r.uniform(4, 7)
                self.line([(x - s_, y), (x - s_ * 0.3, y - s_ * 1.2), (x, y)], MINW, rng=r, wob=0.2, trem=0, a0=0.3, a1=0.4)
                self.line([(x, y), (x + s_ * 0.4, y - s_ * 0.9), (x + s_, y)], MINW, rng=r, wob=0.2, trem=0, a0=0.3, a1=0.4)
            else:
                self.dot(x, y, r.uniform(1.5, 2.4), rng=r)
        self.clip = True

        # the crowd, far to near
        r = R(12)
        HZ, K = 780, 520
        z = 17.0
        rows = []
        while z > 1.78:
            rows.append(z)
            z *= r.uniform(0.86, 0.9)
        cnt = 0
        foh_done = False
        for zi in rows:
            w0 = 128 / zi
            y0 = HZ + K / zi
            if not foh_done and y0 > 846:
                self.foh(STX - 150, 846, R(13))
                foh_done = True
            t = (zi - 1.78) / (17 - 1.78)
            hw = 680 - 400 * t ** 0.6
            cxr = STX - 10 * (1 - t)
            if zi > 11.2:
                # the back of the crowd: drawn as running lines of heads
                self.ridge(y0, cxr - hw * r.uniform(0.9, 1.0), cxr + hw * r.uniform(0.9, 1.0), w0 * r.uniform(0.95, 1.08), r,
                           arms=0.07 + 0.05 * (17 - zi) / 6)
                cnt += int(2 * hw / w0)
                continue
            x = cxr - hw + r.uniform(0, w0)
            ppl = []
            while x < cxr + hw:
                ppl.append(x)
                x += w0 * r.uniform(1.15, 1.9)
            r.shuffle(ppl)
            for x in ppl:
                edge = abs(x - cxr) / hw
                if edge > 0.8 and r.random() < (edge - 0.8) * 4:
                    continue
                w = w0 * r.uniform(0.88, 1.12)
                y = y0 + r.gauss(0, 0.12) * w0
                lw = max(MINW, min(3.8, 2.75 + max(0.0, w - 38) / 45))
                if w < 15:
                    self.person_far(x, y, w, lw, r)
                else:
                    o = {}
                    q = r.random()
                    if q < 0.06:
                        o['arms'] = {r.choice((-1, 1)): 'torch'}
                    elif q < 0.15:
                        o['arms'] = {r.choice((-1, 1)): 'phone'}
                    elif q < 0.25:
                        o['arms'] = {r.choice((-1, 1)): r.choice(['open', 'fist', 'peace', 'point', 'open'])}
                    elif q < 0.29:
                        k = r.choice(['open', 'open', 'fist'])
                        o['arms'] = {-1: k, 1: k}
                    o['tilt'] = r.gauss(0, 6)
                    if w > 50:
                        o['gfill'] = None
                    prof = w > 32 and r.random() < 0.06
                    if prof:
                        o['_skiphead'] = True
                        o['tilt'] = 0
                    self.person(x, y, w, lw, r, o)
                    if prof:
                        self.head_profile(x, y, w * 1.02, lw, r, face=r.choice((-1, 1)), back=r.uniform(-8, 18), mouth=r.choice((0.0, 0.0, 0.8)),
                                          hair=r.choice(['bun', 'short', 'curly', 'short', 'beanie']), smile=r.random() < 0.5,
                                          capfill=r.choice([None, 'G', 'Y']))
                cnt += 1
        print('  crowd %d people %.1fs' % (cnt, time.time() - t0)); sys.stdout.flush()

        self.heroes(R(14))
        print('  heroes %.1fs' % (time.time() - t0)); sys.stdout.flush()
        # colour stops a little inside the vignette
        for sg in (-1, 1):
            edge = []
            yp = 640
            while yp <= 1600:
                edge.append((600 + sg * (vig_hw(yp, sg) - 16 + 6 * math.sin(yp * 0.07)), yp))
                yp += 8
            poly = [(600 + sg * 700, 640)] + edge + [(600 + sg * 700, 1600)]
            for k in ('Y', 'G', 'B'):
                self.D[k].polygon([(x * S, y * S) for x, y in poly], fill=0)
        self.marks = {k: (round(v[0], 1), round(v[1] + OY, 1)) for k, v in self.marks.items()}

    def heroes(self, r):
        LW = 4.6
        # --- the torch: a tall guy, arm straight up, phone light on (centre, furthest back)
        Tx, Ty, Tw = 604, 1146, 94
        Th = Tw * 1.13
        self.person(Tx, Ty, Tw, LW, r, {'garment': 'jacket', 'gfill': None, 'hair': 'cap', 'capfill': None, 'sw': 1.22, 'yend': 2.6, 'trail': True,
                                         'tilt': -4, 'arms': {1: 'torch'},
                                         'arm_1': {'elbow': (Tx + 0.95 * Tw, Ty - 0.25 * Th), 'wrist': (Tx + 0.5 * Tw, Ty - 1.7 * Th), 'psize': 0.8 * Tw,
                                                   'reach': 1.6, 'nray': 15}})
        self.marks['torch'] = (Tx + 0.5 * Tw, Ty - 2.3 * Th)

        # --- mallige: a girl with jasmine pinned in her braid (centre-right), arms down, swaying
        Mx, My, Mw = 812, 1226, 110
        self.person(Mx, My, Mw, LW, r, {'garment': 'jacket', 'gfill': None, 'hair': 'braid', 'hairlen': 2.5, 'mallige': True, 'tiefill': 'B',
                                         'sw': 1.1, 'yend': 2.7, 'trail': False, 'tilt': 7, 'lean': 0.04})
        self.marks['mallige'] = (Mx + 0.3 * Mw, My + 0.2 * Mw)

        # --- monkey cap: big, bottom left of centre, both arms up
        Cx, Cy, Cw = 336, 1300, 146
        Ch = Cw * 1.13
        self.person(Cx, Cy, Cw, LW * 1.05, r, {'garment': 'hoodie', 'gfill': 'G', 'hair': 'monkeycap', 'capfill': 'Y', 'pomfill': 'B', 'pompom': True,
                                                'sw': 1.3, 'yend': 2.5, 'trail': False, 'tilt': 3, 'arms': {-1: 'fist', 1: 'open'},
                                                'arm_-1': {'elbow': (Cx - 1.62 * Cw, Cy - 0.05 * Ch), 'wrist': (Cx - 1.32 * Cw, Cy - 1.2 * Ch)},
                                                'arm_1': {'elbow': (Cx + 1.48 * Cw, Cy + 0.05 * Ch), 'wrist': (Cx + 1.02 * Cw, Cy - 1.36 * Ch)}})
        self.marks['monkeycap'] = (Cx, Cy - 0.65 * Ch)

        # --- two friends under one shawl (right, near)
        Lx, Ly, Lw = 980, 1346, 106
        Rx, Ry, Rw = 1108, 1328, 100
        oL = {'garment': 'tee', 'gfill': None, 'hair': 'long', 'hairlen': 1.25, 'sw': 1.16, 'yend': 2.6, 'trail': False, 'tilt': 9, '_skiphead': True}
        oR = {'garment': 'hoodie', 'gfill': None, 'hair': 'beanie', 'capfill': 'G', 'sw': 1.2, 'yend': 2.6, 'trail': False, 'tilt': -8, '_skiphead': True}
        self.person(Lx, Ly, Lw, LW, r, dict(oL))
        self.person(Rx, Ry, Rw, LW, r, dict(oR))
        Lh, Rh = Lw * 1.13, Rw * 1.13
        top = [(Lx - 1.32 * Lw, Ly + 1.2 * Lh), (Lx - 1.05 * Lw, Ly + 0.98 * Lh), (Lx - 0.5 * Lw, Ly + 0.86 * Lh), (Lx + 0.1 * Lw, Ly + 0.9 * Lh),
               (Lx + 0.6 * Lw, Ly + 1.02 * Lh), ((Lx + Rx) / 2 + 8, Ly + 1.08 * Lh), (Rx - 0.55 * Rw, Ry + 0.98 * Rh), (Rx - 0.1 * Rw, Ry + 0.86 * Rh),
               (Rx + 0.5 * Rw, Ry + 0.86 * Rh), (Rx + 1.1 * Rw, Ry + 1.0 * Rh), (Rx + 1.5 * Rw, Ry + 1.25 * Rh)]
        sh_poly = top + [(Rx + 1.5 * Rw, 1660), (Lx - 1.42 * Lw, 1660), (Lx - 1.4 * Lw, Ly + 2.0 * Lh)]
        tp = self.hand(top, wob=1.0, trem=0.8, rng=r)
        left_edge = self.hand([(Lx - 1.32 * Lw, Ly + 1.2 * Lh), (Lx - 1.42 * Lw, Ly + 1.7 * Lh), (Lx - 1.38 * Lw, Ly + 2.4 * Lh), (Lx - 1.45 * Lw, 1640)],
                              wob=1.0, trem=0.8, rng=r)
        self.knock(tp + [(Rx + 1.5 * Rw, 1660), (Lx - 1.42 * Lw, 1660)] + left_edge[::-1])
        self.blob(sh_poly, 'Y', rng=r, scale=(0.99, 1.01), jit=0.01, shift=1.5, gap=0.0, n=60)
        r2 = random.Random(r.random())

        def border(dr, off):
            for dd, wd in ((20, 8.5), (33, 5.0), (44, 5.0)):
                pts = offset_path(tp, -dd)
                pts = self.hand(resample(pts, 30), wob=0.8, trem=0.8, rng=r2)
                self._render(pts, wd, 'G', 0.5, 1.0, 0.2, r2, draw=dr, off=off)
                pts = offset_path(left_edge, dd)
                pts = self.hand(resample(pts, 20), wob=0.8, trem=0.8, rng=r2)
                self._render(pts, wd, 'G', 0.5, 1.0, 0.2, r2, draw=dr, off=off)
            # small woven motifs along the border
            for i in range(14):
                t = (i + 0.5) / 14
                p = tp[int(t * (len(tp) - 1))]
                q = offset_path(tp, -58)[int(t * (len(tp) - 1))]
                x, y = q
                self._render([(x - 4, y), (x, y - 4), (x + 4, y), (x, y + 4), (x - 4, y)], 3.2, 'G', 0.3, 0.3, 0.1, r2, draw=dr, off=off)
        self.masked(sh_poly, 'G', border)
        self.ink(tp, LW, rng=r, a0=0.6, a1=1.0, redraw=0.4)
        self.ink(left_edge, LW, rng=r, a0=0.6, a1=1.0)
        # fringe along the hanging edge
        for i in range(16):
            t = 0.08 + 0.85 * i / 16
            p = left_edge[int(t * (len(left_edge) - 1))]
            self.line([p, (p[0] - r.uniform(10, 16), p[1] + r.uniform(4, 9))], MINW, rng=r, wob=0.3, trem=0, a0=0.3, a1=0.5)
        # folds
        for (fx, fy, ex, ey) in ((Lx - 0.6 * Lw, Ly + 1.05 * Lh, Lx - 0.85 * Lw, 1560), (Lx + 0.35 * Lw, Ly + 1.1 * Lh, Lx + 0.5 * Lw, 1580),
                                 ((Lx + Rx) / 2 + 8, Ly + 1.2 * Lh, (Lx + Rx) / 2 - 6, 1590), (Rx + 0.4 * Rw, Ry + 0.98 * Rh, Rx + 0.62 * Rw, 1570)):
            self.line([(fx, fy), ((fx + ex) / 2 + r.gauss(0, 6), (fy + ey) / 2), (ex, ey)], LW * 0.75, rng=r, wob=1.0, trem=0.8, a0=0.8, a1=3.0)
        # R's hand out from under the shawl, holding it closed at L's shoulder
        self.draw_hand((Lx + 0.62 * Lw, Ly + 1.12 * Lh), math.radians(200), Rw * 0.45, 'mitten', LW * 0.85, r)
        # heads
        oL.update({'nobody': True, '_skiphead': False})
        oR.update({'nobody': True, '_skiphead': False, 'arms': {1: 'fist'},
                   'arm_1': {'elbow': (Rx + 1.25 * Rw, Ry + 0.2 * Rh), 'wrist': (Rx + 0.72 * Rw, Ry - 1.05 * Rh)}})
        self.person(Lx, Ly, Lw, LW, r, oL)
        self.person(Rx, Ry, Rw, LW, r, oR)
        self.marks['shawl'] = ((Lx + Rx) / 2, Ly + 1.3 * Lh)

        # --- the coffee: left edge, a steel tumbler held under his chin, steam
        Fx, Fy, Fw = 104, 1378, 116
        self.person(Fx, Fy, Fw, LW * 1.04, r, {'garment': 'muffler', 'mufflerfill': 'G', 'gfill': None, 'hair': 'short', 'sw': 1.12, 'yend': 2.6,
                                               'trail': False, '_skiphead': True})
        HP = self.head_profile(Fx + 6, Fy - 4, Fw * 1.02, LW * 1.04, r, face=1, back=-4, hair='beanie', capfill='Y', smile=True)
        # tumbler
        rc = HP(0.83, 0.58)
        th, tw0, tw1 = Fw * 0.36, Fw * 0.25, Fw * 0.2
        a = math.radians(8)
        ca, sa = math.cos(a), math.sin(a)

        def T(v, u):
            return (rc[0] + v * ca - u * sa, rc[1] + v * sa + u * ca)
        cup = [T(-tw0 / 2, 0), T(tw0 / 2, 0), T(tw1 / 2, th), T(-tw1 / 2, th)]
        self.knock(cup)
        self.box(cup, LW * 0.85, rng=r, over=(-0.5, 2.0), bow=0.02)
        self.line([T(-tw0 / 2 + 1, 5), T(0, 6), T(tw0 / 2 - 1, 5)], LW * 0.6, rng=r, wob=0.3, trem=0)
        self.line([T(-tw0 / 2 + 2, th * 0.82), T(0, th * 0.84), T(tw0 / 2 - 2, th * 0.82)], LW * 0.6, rng=r, wob=0.3, trem=0)
        self.line([T(tw0 * 0.22, 9), T(tw0 * 0.2, th * 0.72)], LW * 0.6, rng=r, wob=0.3, trem=0, a0=0.5, a1=1.5)
        self.line([T(tw0 * 0.32, 12), T(tw0 * 0.3, th * 0.45)], MINW, rng=r, wob=0.2, trem=0, a0=0.5, a1=1.0)
        # the hand round it, from below
        hand = [T(-tw0 * 0.62, th * 0.35), T(-tw0 * 0.55, th * 0.95), T(-tw0 * 0.2, th * 1.12), T(tw0 * 0.3, th * 1.05),
                T(tw0 * 0.58, th * 0.6), T(tw0 * 0.52, th * 0.42)]
        hp = self.hand(hand, wob=0.6, trem=0.3, rng=r)
        self.knock(hp + [T(tw0 * 0.1, th * 0.5)])
        self.ink(hp, LW * 0.85, rng=r, a0=0.5, a1=0.8)
        for f in (0.52, 0.68, 0.83):
            self.line([T(tw0 * 0.55 - 2, th * f), T(tw0 * 0.25, th * f + 3)], LW * 0.55, rng=r, wob=0.2, trem=0)
        self.line([T(-tw0 * 0.4, th * 1.08), T(-tw0 * 0.55, th * 1.7), T(-tw0 * 0.35, th * 2.4)], LW * 0.9, rng=r, wob=0.8, trem=0.5, a0=0.5)
        self.line([T(tw0 * 0.25, th * 1.06), T(tw0 * 0.3, th * 1.7), T(tw0 * 0.55, th * 2.4)], LW * 0.9, rng=r, wob=0.8, trem=0.5, a0=0.5)
        # steam
        for i, dx in enumerate((-0.2, 0.15)):
            pts = []
            for j in range(9):
                u = j / 8
                pts.append(T(tw0 * dx + 6 * math.sin(u * 5.5 + i * 2.0) * (0.4 + u), -6 - u * Fw * (0.42 if i == 0 else 0.33)))
            self.line(pts, MINW * 1.05, rng=r, wob=0.4, trem=0.3, a0=1.0, a1=4.0, pv=0.3)
        self.marks['coffee'] = rc


STX = 622     # stage centre (a touch right of the page centre)

# allow person() to skip its head (profile drawn separately)
_orig_head_back = Scene.head_back


def _head_back(self, HP, cx, cy, w, h, lw, rng, hair, det, big, o):
    if o.get('_skiphead'):
        return
    return _orig_head_back(self, HP, cx, cy, w, h, lw, rng, hair, det, big, o)


Scene.head_back = _head_back


# ----------------------------------------------------------------- print prep
def shifted(m, dx, dy):
    out = Image.new('L', m.size, 0)
    out.paste(m, (int(round(dx * S)), int(round(dy * S))))
    return out


def clean(m, k=7):
    """morphological open: removes slivers narrower than ~k px (min printed feature)"""
    return m.filter(ImageFilter.MinFilter(k)).filter(ImageFilter.MaxFilter(k))


def close(m, k=5):
    return m.filter(ImageFilter.MaxFilter(k)).filter(ImageFilter.MinFilter(k))


def noise(cell_u, seed, sigma=64):
    random.seed(seed)
    nw, nh = max(2, int(W / (cell_u * S))), max(2, int(H / (cell_u * S)))
    return Image.effect_noise((nw, nh), sigma).convert('L').resize((W, H), Image.BICUBIC)


def grain(m, seed, cut=80, cell=2.6, starve_cell=90, starve=0.45):
    """screen grain: open holes in the solids, more where the screen ran a little dry"""
    # two fine screens at unrelated cell sizes, one shifted half a cell, so the
    # holes don't line up on the noise lattice
    f1 = noise(cell, seed, 60)
    f2 = noise(cell * 0.71, seed + 7, 60)
    f2 = ImageChops.offset(f2, int(cell * S * 0.37), int(cell * S * 0.61))
    fine = Image.blend(f1, f2, 0.5).point(lambda p: max(0, min(255, int((p - 128) * 1.35 + 128))))
    low = noise(starve_cell, seed + 1, 70)
    mix = Image.blend(fine, low, starve)
    holes = mix.point(lambda p: 255 if p < cut else 0)
    holes = clean(holes, 7)                  # no pin-holes the screen can't hold
    holes = holes.filter(ImageFilter.GaussianBlur(3.2)).point(lambda p: 255 if p > 118 else 0)   # round, not square
    return ImageChops.subtract(m, holes)


def separations(art):
    line = clean(art.L['line'], 7)
    seps = {'line': line}
    for i, k in enumerate(('Y', 'G', 'B')):
        m = shifted(art.L[k], *SHIFT[k])
        m = ImageChops.subtract(m, line)
        if k in ('Y', 'G'):
            m = grain(m, SEED + 31 * i)
        seps[k] = clean(m, 7)
    # later screens sit on top: trim what's underneath, drop slivers
    seps['Y'] = clean(ImageChops.subtract(ImageChops.subtract(seps['Y'], seps['G']), seps['B']), 7)
    seps['G'] = clean(ImageChops.subtract(seps['G'], seps['B']), 7)
    # keep clear of the print edge (~40 px)
    safe = Image.new('L', (W, H), 0)
    ImageDraw.Draw(safe).rectangle([42, 42, W - 43, H - 43], fill=255)
    for k in seps:
        seps[k] = ImageChops.multiply(seps[k], safe)
    return seps


def render(seps):
    pal = PAL['black']
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for k in ('Y', 'G', 'B', 'line'):
        out.paste(hexrgb(pal[k]) + (255,), (0, 0), seps[k])
    return out


def main():
    t = time.time()
    sc = Scene(SEED)
    sc.compose()
    seps = separations(sc)
    print('  separations %.1fs' % (time.time() - t)); sys.stdout.flush()
    art = render(seps)
    art.save(os.path.join(HERE, 'art-black.png'), optimize=False, compress_level=6)
    bg = Image.new('RGBA', (W, H), hexrgb(PAL['black']['tee']) + (255,))
    bg.alpha_composite(art)
    bg.convert('RGB').resize((900, 1200), Image.LANCZOS).save(os.path.join(HERE, 'preview-black.png'))
    if os.environ.get('CROP'):
        for i, c in enumerate(os.environ['CROP'].split(';')):
            x, y = [int(v) for v in c.split(',')]
            bg.convert('RGB').crop((x, y, x + 1000, y + 1000)).save(os.path.join(HERE, '_crop%d.png' % i))
    m = sc.marks
    manifest = {
        'concept': ("line drawings of the night, a different night: a cool december night on the city's north-west edge. a hand-inked crowd "
                    "on the nice grounds by biec, madavara, seen from behind, looking at a small loud stage under an arched truss whose "
                    "light goes up and crosses. behind it the green line viaduct comes in on its piers and stops at madavara, the end of the "
                    "line, a train pulling in with people standing in its lit windows; a lorry on tumakuru road; the long low exhibition halls; "
                    "wide rain-tree umbrellas; a high-mast lamp at the interchange; a four-day moon. the crowd is dressed for 15 degrees: hoods "
                    "up, beanies, mufflers, shawls, phone torches held up like small stars. foreground: a guy in a yellow monkey cap with both "
                    "arms up, a tall guy holding up his phone torch, a girl with mallige pinned in her braid, two friends under one shawl, a "
                    "guy with a steel tumbler of coffee steaming under his chin. brush lines with pressure and wobble; spot inks printed loose, "
                    "off-register and grainy. the drawing trails off at the bottom like a sketchbook page."),
        'palette': {'tee': PAL['black']['tee'], 'line': PAL['black']['line'], 'ink_yellow': PAL['black']['Y'], 'ink_green': PAL['black']['G'],
                    'accent_blue': PAL['black']['B']},
        'units': '1200 x 1600 (multiply by 3 for px on the 3600 x 4800 art)',
        'type_zones': TYPE_ZONES,
        'annotations': [
            {'text': 'the green line ends here, madavara', 'x': 120, 'y': 486, 'rotation': -3, 'points_to': list(m['station'])},
            {'text': 'tumakuru road, lorries all night', 'x': 30, 'y': 790, 'rotation': 2, 'points_to': list(m['lorry'])},
            {'text': 'biec halls', 'x': 1020, 'y': 642, 'rotation': -2, 'points_to': list(m['halls'])},
            {'text': 'rain trees, the city\'s umbrellas', 'x': 860, 'y': 538, 'rotation': -4, 'points_to': list(m['trees'])},
            {'text': '15 degrees. monkey caps out', 'x': 24, 'y': 1040, 'rotation': -5, 'points_to': list(m['monkeycap'])},
        ],
        'figures': {k: list(v) for k, v in m.items()},
        'art_bbox': None,
        'seed': SEED,
    }
    a = art.getchannel('A').getbbox()
    manifest['art_bbox'] = {'x': round(a[0] / S), 'y': round(a[1] / S), 'w': round((a[2] - a[0]) / S), 'h': round((a[3] - a[1]) / S)}
    json.dump(manifest, open(os.path.join(HERE, 'manifest.json'), 'w'), indent=2)
    print('done %.1fs' % (time.time() - t))


TYPE_ZONES = [
    {'name': 'city', 'x': 80, 'y': 150, 'w': 1040, 'h': 230},
    {'name': 'dates', 'x': 300, 'y': 392, 'w': 600, 'h': 56},
]

if __name__ == '__main__':
    main()
