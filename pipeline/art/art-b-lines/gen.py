#!/usr/bin/env python3
"""
fred again.. india 2026 (fan-made, not for sale) -- MUMBAI tee, direction B
"line drawings of the night": a hand-inked crowd at Mahalaxmi Race Course,
seen from behind, looking at the stage.

Everything is built from one primitive: a pressure-varying brush stroke laid
along a jittered Catmull-Rom path (tremor + swell + lift taper + the odd
re-drawn pass), rendered as filled polygons.  Spot-colour fills are separate
"screens" drawn loosely and printed slightly off-register.

Pillow only.  Re-runnable:  python3 gen.py   (SEED=... to vary)
"""
import math, random, json, os, sys, time
from PIL import Image, ImageDraw, ImageFilter, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = int(os.environ.get('SEED', 81226))
S = 3                       # px per unit (units are 1200 x 1600)
UW, UH = 1200, 1600
W, H = UW * S, UH * S
MINW = 2.75                 # min stroke width, units (8.25 px)
TAU = math.tau
LAYERS = ('line', 'Y', 'B', 'R', 'H', 'Hx')   # H = hair screen (cream tee only), Hx = lines reversed out of it

PAL = {
    'black': {'tee': '#151515', 'line': '#F1E7D0', 'Y': '#F6B330', 'B': '#5A8CF0', 'R': '#E4432D'},
    'cream': {'tee': '#ECE3CE', 'line': '#1C1A17', 'Y': '#F0A417', 'B': '#2F5FD0', 'R': '#D8381F'},
}
# off-register offsets of each screen, in units
SHIFT = {'Y': (4.2, 2.6), 'B': (-3.4, 3.9), 'R': (1.2, -0.9), 'line': (0, 0)}


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
    return 1508 + 22 * math.sin(x * 0.0131 + 2.0) + 11 * math.sin(x * 0.047 + 1.0) + 6 * math.sin(x * 0.17)


OY = -40   # the whole scene sits this far up the page (units)


def vig_hw(yp):
    """half-width of the drawing at page height yp: a rounded, ragged vignette"""
    if yp < 980:
        return 584.0
    t = min(1.0, (yp - 980) / 640)
    return 584.0 * (1 - t ** 3.2) ** (1 / 3.2)


def inside(x, y):
    """scene point -> still on the paper?"""
    yp = y + OY
    if yp > ybot(x):
        return False
    return abs(x - 600) <= vig_hw(yp) - 12 + 7 * math.sin(yp * 0.05 + x * 0.01) + 4 * math.sin(yp * 0.17)


def ybot(x):
    """the drawing trails off along this hand-ragged line at the bottom"""
    return 1566 + 17 * math.sin(x * 0.0105 + 1.1) + 9 * math.sin(x * 0.037 + 0.4) + 5 * math.sin(x * 0.11)


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

    def phone(self, pos, ang, size, lw, rng, screen='B', content=True, rec=False, land=False):
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
            self.dot(x, y, max(size * 0.035, 1.9), layer='R', rng=rng)
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
        garment = o.get('garment') or rng.choice(['tee', 'tee', 'tee', 'hoodie', 'shirt', 'kurta', 'tank', 'jacket', 'tee'])
        gfill = o.get('gfill', 'auto')
        if gfill == 'auto':
            rr = rng.random()
            gfill = 'Y' if rr < 0.10 else 'B' if rr < 0.21 else None
            if garment == 'jacket':
                gfill = 'B'
        arms = o.get('arms', {})
        hair = o.get('hair') or rng.choice(['short', 'short', 'short', 'long', 'long', 'long', 'ponytail', 'ponytail', 'bun', 'curly', 'cap', 'buzz', 'braid', 'topknot', 'short', 'long', 'bandana'])

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
            if gfill and garment != 'tank':
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
            L([(-0.62, 0.85), (-0.55, 1.12), (-0.25, 1.36), (0.0, 1.42), (0.25, 1.35), (0.55, 1.1), (0.63, 0.85)])
            if det:
                L([(-0.33, 0.94), (-0.1, 1.12), (0.12, 1.12), (0.32, 0.95)], 0.8)
            if big:
                L([(-sw * 0.95, 2.55), (0, 2.6), (sw * 0.95, 2.55)], 0.7)
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
        if kind == 'phone':
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
        if kind == 'phone':
            psize = ao.get('psize') or w * rng.uniform(0.8, 1.0)
            self.phone((ex, ey), ang, psize, lw * 0.9, rng, screen=ao.get('screen', 'Y' if rng.random() < 0.7 else 'B'),
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
                    self.line([a, m, b], lw * 0.7, rng=rng, wob=0.005 * w, trem=0, layer=('R' if i == 1 else 'line'))

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
            col = o.get('capfill', rng.choice(['Y', 'B', None, None, None]))
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
            self.knock(d, layers=('Y', 'B'))
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
                col = o.get('bandfill', rng.choice(['B', 'Y', None]))
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
                # tassel (paranda)
                if o.get('paranda'):
                    for j in range(5):
                        dx = (j - 2) * 0.03
                        stroke([(x + dx * 0.4, yy), (x + dx * 1.6, yy + 0.32)], 0.7, layer='R', a0=0.3, a1=0.6)
                    stroke([(x - 0.07, yy + 0.0), (x + 0.07, yy + 0.0)], 0.9)
            elif kind == 'tie':
                d = self.hand(P(data), closed=True, wob=0, trem=0, rng=rng)
                self.knock(d)
                stroke(data, 0.8, closed=True)

    def person_far(self, cx, cy, w, lw, rng):
        """a distant head: a bump, shoulders, maybe an arm with a phone"""
        h = w * 1.12
        sw = rng.uniform(1.15, 1.5)
        body = [(cx - 0.25 * w, cy + 0.55 * h), (cx - sw * w * 0.8, cy + 0.95 * h), (cx - sw * w, cy + 1.3 * h), (cx - sw * w, cy + 3.0 * h),
                (cx + sw * w, cy + 3.0 * h), (cx + sw * w, cy + 1.3 * h), (cx + sw * w * 0.8, cy + 0.95 * h), (cx + 0.25 * w, cy + 0.55 * h)]
        self.knock(body)
        r = rng.random()
        if r < 0.09:
            self.blob(body[1:7], 'Y', rng=rng, shift=0.05 * w, gap=0.3)
        elif r < 0.17:
            self.blob(body[1:7], 'B', rng=rng, shift=0.05 * w, gap=0.3)
        for sg in (-1, 1):
            if rng.random() < 0.85:
                self.line([(cx + sg * 0.35 * w, cy + 0.8 * h), (cx + sg * sw * 0.8 * w, cy + 0.98 * h), (cx + sg * sw * w * 1.02, cy + 1.45 * h)],
                          lw, rng=rng, wob=0.04 * w, trem=0, a0=0.6, a1=1.0)
        # arm up
        if rng.random() < 0.17:
            sg = rng.choice((-1, 1))
            sx, sy = cx + sg * sw * w * 0.75, cy + 1.0 * h
            hx, hy = cx + sg * w * rng.uniform(0.4, 1.4), cy - h * rng.uniform(0.9, 1.7)
            ex, ey = (sx + hx) / 2 + sg * w * 0.25, (sy + hy) / 2
            p = self.hand([(sx, sy), (ex, ey), (hx, hy)], wob=0.03 * w, trem=0, rng=rng)
            self.knock(offset_path(p, 0.18 * w) + offset_path(p, -0.18 * w)[::-1])
            self.ink(p, lw, rng=rng, a0=0.5, a1=0.8)
            q = rng.random()
            if q < 0.55:
                ph = w * rng.uniform(0.7, 0.95)
                pw = ph * 0.55
                ang = rng.gauss(0, 0.2)
                ca, sa = math.cos(ang), math.sin(ang)
                cxp, cyp = hx, hy - ph * 0.45
                rect = [(cxp + (u * pw * ca - v * ph * sa) / 2, cyp + (u * pw * sa + v * ph * ca) / 2) for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
                self.knock(rect)
                lay = 'R' if rng.random() < 0.06 else 'Y'
                self.blob(rect, lay, rng=rng, scale=(1.0, 1.12), shift=0.04 * w, gap=0.0, n=12)
                if w > 11:
                    self.box(rect, lw * 0.8, rng=rng, over=(-0.5, 1.0), wob=0.1)
            else:
                self.dot(hx, hy - 0.15 * w, max(0.22 * w, 1.6), rng=rng)
        # head
        nz = lambda: rng.gauss(0, 0.02)
        hair = rng.random()
        if hair < 0.22:  # long hair
            ctrl = [(-0.5, 0.9), (-0.55, 0.3), (-0.5, -0.25), (0.0, -0.55), (0.5, -0.25), (0.55, 0.3), (0.5, 0.9)]
        else:
            ctrl = [(-0.42, 0.45), (-0.52, 0.0), (-0.42, -0.35), (0.0, -0.55), (0.42, -0.35), (0.52, 0.0), (0.42, 0.45)]
        ctrl = [(cx + (x + nz()) * w, cy + (y + nz()) * h) for x, y in ctrl]
        d = self.hand(ctrl, wob=0, trem=0, rng=rng)
        self.knock(d + [(cx, cy + 0.6 * h)])
        if hair < 0.22 or rng.random() < 0.8:
            self.hfill(d + [(cx + 0.3 * w, cy + 0.25 * h), (cx - 0.3 * w, cy + 0.25 * h)] if hair >= 0.22 else d)
        self.ink(d, lw, rng=rng, a0=0.6, a1=0.9, pv=0.15)
        if hair > 0.22:
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
                     earring=False, gajra=False, smile=False, beard=False, neck=True):
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
        else:  # curly mop
            hm = [(0.40, -0.33), (0.30, -0.55), (0.0, -0.66), (-0.34, -0.60), (-0.58, -0.35), (-0.62, -0.02), (-0.50, 0.26), (-0.34, 0.36),
                  (-0.12, 0.22), (-0.02, 0.02), (0.08, -0.12), (0.22, -0.22)]
        d = self.hand(P(hm), closed=True, wob=0, trem=0, rng=rng)
        self.knock(d)
        self.hfill(d)
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
            self.dot(x, y, max(0.03 * w, 2.0), layer='R', rng=rng)
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

    # ---- the city -------------------------------------------------------
    def building(self, x0, x1, top, base, lw, rng, kind='slab', lit=0.15):
        b = base
        pts = []
        if kind == 'crown':        # stepped crown + spire
            wd = x1 - x0
            pts = [(x0, b), (x0, top + wd * 0.5), (x0 + wd * 0.12, top + wd * 0.5), (x0 + wd * 0.12, top + wd * 0.25), (x0 + wd * 0.28, top + wd * 0.25),
                   (x0 + wd * 0.28, top), (x1 - wd * 0.28, top), (x1 - wd * 0.28, top + wd * 0.25), (x1 - wd * 0.12, top + wd * 0.25),
                   (x1 - wd * 0.12, top + wd * 0.5), (x1, top + wd * 0.5), (x1, b)]
        elif kind == 'slant':
            pts = [(x0, b), (x0, top + (x1 - x0) * 0.35), (x1, top), (x1, b)]
        elif kind == 'round':
            wd = x1 - x0
            pts = [(x0, b), (x0, top + wd * 0.3), (x0 + wd * 0.15, top + wd * 0.08), (x0 + wd * 0.5, top), (x1 - wd * 0.15, top + wd * 0.08),
                   (x1, top + wd * 0.3), (x1, b)]
        else:
            pts = [(x0, b), (x0, top), (x1, top), (x1, b)]
        self.knock(pts)
        # edges
        n = len(pts)
        self.box(pts, lw, rng=rng, over=(-1.0, 3.0), bow=0.004)
        wd = x1 - x0
        if kind == 'crown':
            self.line([(x0 + wd / 2, top), (x0 + wd / 2 + rng.gauss(0, 0.4), top - wd * 0.55)], lw, rng=rng, wob=0.2, trem=0, a0=0.4, a1=0.5)
            self.dot(x0 + wd / 2, top - wd * 0.55, 1.6, layer='R', rng=rng)
        if kind == 'flat_tank':
            tx = rng.uniform(x0 + 3, x1 - 14)
            tk = [(tx, top - 9), (tx + 10, top - 9), (tx + 10, top - 2), (tx, top - 2)]
            self.knock(tk)
            self.box(tk, lw * 0.9, rng=rng, over=(-0.5, 1.5))
            self.line([(tx + 2, top - 2), (tx + 1, top)], lw * 0.8, rng=rng, wob=0.1, trem=0)
            self.line([(tx + 8, top - 2), (tx + 9, top)], lw * 0.8, rng=rng, wob=0.1, trem=0)
        # windows: hand-ticked, not a grid
        mode = rng.choice(['dash', 'dash', 'dots', 'cols', 'none'])
        if wd < 16:
            mode = rng.choice(['cols', 'none', 'dots'])
        y = top + (wd * 0.55 if kind == 'crown' else 9 if kind != 'slant' else (x1 - x0) * 0.4 + 8)
        step = rng.uniform(8.5, 12)
        while y < b - 6:
            if mode == 'dash':
                cols = max(1, int((wd - 6) / 10))
                for c in range(cols):
                    if rng.random() < 0.55:
                        xx = x0 + 5 + (wd - 10) * (c + 0.5) / cols
                        if rng.random() < lit:
                            self.blob([(xx - 2.8, y - 2.3), (xx + 2.8, y - 2.3), (xx + 2.8, y + 2.3), (xx - 2.8, y + 2.3)], 'Y', rng=rng, gap=0, shift=0.6, n=10)
                        else:
                            self.line([(xx - 2.2, y), (xx + 2.2, y + rng.gauss(0, 0.3))], MINW, rng=rng, wob=0.15, trem=0, a0=0.2, a1=0.2)
            elif mode == 'dots':
                cols = max(1, int((wd - 6) / 9))
                for c in range(cols):
                    if rng.random() < 0.4:
                        xx = x0 + 5 + (wd - 10) * (c + 0.5) / cols
                        if rng.random() < lit:
                            self.blob([(xx - 2.6, y - 2.6), (xx + 2.6, y - 2.6), (xx + 2.6, y + 2.6), (xx - 2.6, y + 2.6)], 'Y', rng=rng, gap=0, shift=0.6, n=10)
                        else:
                            self.dot(xx, y, 1.45, rng=rng)
            y += step
        if mode == 'cols':
            for c in range(1, max(2, int(wd / 9))):
                xx = x0 + wd * c / max(2, int(wd / 9))
                self.line([(xx, top + 6 + rng.uniform(0, 8)), (xx + rng.gauss(0, 0.5), b - rng.uniform(4, 20))], MINW, rng=rng, wob=0.3, trem=0.3, a0=0.3, a1=1.0)

    def crane(self, x, base, top, jib, lw, rng):
        # tower crane: lattice mast + jib + counter-jib + hook line
        mw = 5.5
        self.line([(x, base), (x + rng.gauss(0, 0.3), top)], lw, rng=rng, wob=0.2, trem=0.2)
        self.line([(x + mw, base), (x + mw + rng.gauss(0, 0.3), top)], lw, rng=rng, wob=0.2, trem=0.2)
        y = base
        k = 0
        while y > top + 7:
            y2 = y - 8.5
            self.line([(x + (0 if k % 2 else mw), y), (x + (mw if k % 2 else 0), y2)], MINW, rng=rng, wob=0.1, trem=0, a0=0.2, a1=0.2)
            y = y2
            k += 1
        jy = top
        self.line([(x - jib * 0.3, jy), (x + mw + jib, jy + rng.gauss(0, 0.4))], lw, rng=rng, wob=0.2, trem=0.2)
        self.line([(x + mw * 0.5, jy - 11), (x + mw + jib * 0.95, jy)], MINW, rng=rng, wob=0.2, trem=0)
        self.line([(x + mw * 0.5, jy - 11), (x - jib * 0.28, jy)], MINW, rng=rng, wob=0.2, trem=0)
        self.line([(x + mw * 0.5, jy), (x + mw * 0.5, jy - 12)], lw, rng=rng, wob=0.1, trem=0)
        cw = [(x - jib * 0.28, jy), (x - jib * 0.14, jy), (x - jib * 0.14, jy + 7), (x - jib * 0.28, jy + 7)]
        self.knock(cw)
        self.box(cw, MINW, rng=rng, over=(-0.5, 1.0))
        hx = x + mw + jib * rng.uniform(0.45, 0.7)
        self.line([(hx, jy), (hx, jy + rng.uniform(25, 45))], MINW, rng=rng, wob=0.1, trem=0.1)
        self.dot(x + mw + jib, jy - 1, 1.7, layer='R', rng=rng)

    def canopy(self, cx, cy, rx, ry, lw, rng):
        n = rng.randint(6, 10)
        ph = rng.uniform(0, TAU)
        ctrl = []
        for i in range(n):
            a = ph + TAU * i / n
            ctrl.append((cx + math.cos(a) * rx, cy + math.sin(a) * ry))
        # bottom flattened: canopies sit on each other
        ctrl = [(x, min(y, cy + ry * 0.55)) for x, y in ctrl]
        d = self.hand(ctrl, closed=True, wob=0, trem=0, rng=rng)
        self.knock(d)
        # draw the top half as loopy arcs
        for i in range(n):
            a0 = ph + TAU * i / n
            a1 = a0 + TAU / n * rng.uniform(1.0, 1.2)
            am = (a0 + a1) / 2
            if math.sin(am) > 0.35:
                continue
            p0 = (cx + math.cos(a0) * rx, cy + math.sin(a0) * ry)
            p1 = (cx + math.cos(a1) * rx, cy + math.sin(a1) * ry)
            pm = (cx + math.cos(am) * rx * 1.22, cy + math.sin(am) * ry * 1.22)
            self.line([p0, pm, p1], lw, rng=rng, wob=0.3, trem=0.2, a0=0.4, a1=0.8)

    def kite_bird(self, x, y, s, lw, rng, ang=0.0):
        """a black kite (Milvus migrans) gliding: bent wings, forked tail"""
        def T(u, v):
            ca, sa = math.cos(ang), math.sin(ang)
            return (x + (u * ca - v * sa) * s, y + (u * sa + v * ca) * s)
        fl = rng.uniform(-0.1, 0.15)
        lw_ = [(-1.0, 0.05 + fl), (-0.6, -0.12 - fl), (-0.28, -0.02), (0.0, 0.05)]
        rw = [(0.0, 0.05), (0.28, -0.03), (0.62, -0.14 - fl), (1.0, 0.02 + fl)]
        self.line([T(*p) for p in lw_], lw, rng=rng, wob=0.03 * s, trem=0, a0=0.3, a1=0.6)
        self.line([T(*p) for p in rw], lw, rng=rng, wob=0.03 * s, trem=0, a0=0.6, a1=0.3)
        tail = [T(-0.06, 0.08), T(-0.08, 0.34), T(0.0, 0.29), T(0.08, 0.34), T(0.06, 0.08)]
        self.knock(tail)
        self.line(tail, lw * 0.85, rng=rng, wob=0.01 * s, trem=0, a0=0.3, a1=0.4)

    # ---- the stage ------------------------------------------------------
    def stage(self, rng):
        lw = 3.0
        cx = 600
        deck_top, deck_bot = 772, 790
        x0, x1 = 472, 728
        tw0, tw1 = 486, 714   # rig towers
        ttop = 676
        # LED screen behind
        scr = [(512, 700), (688, 700), (688, 764), (512, 764)]
        self.knock(scr)

        def scribble(dr, off):
            r2 = random.Random(rng.random())
            y = 702
            while y < 768:
                pts = [(512 + r2.uniform(-3, 3), y), (688 + r2.uniform(-3, 3), y + r2.uniform(5, 9))]
                self._render(self.hand(pts, wob=0.5, trem=0.6, rng=r2), 5.2, 'B', 0.5, 0.8, 0.15, r2, draw=dr, off=off, clip=False)
                y += r2.uniform(6.5, 8.5)
        self.masked([(509, 697), (691, 697), (691, 767), (509, 767)], 'B', scribble)
        self.box(scr, lw, rng=rng)
        # the screen shows the crowd's raised hands (a few marks)
        for i in range(7):
            hx = 530 + i * 23 + rng.uniform(-4, 4)
            self.line([(hx, 764), (hx + rng.uniform(-3, 3), 748 - rng.uniform(0, 10))], MINW, rng=rng, wob=0.3, trem=0, a0=0.3, a1=0.6)
            self.dot(hx + rng.uniform(-1, 1), 744 - rng.uniform(0, 10), 2.2, rng=rng)
        # towers
        for tx in (tw0, tw1):
            pts = [(tx - 5, deck_top), (tx - 5, ttop), (tx + 5, ttop), (tx + 5, deck_top)]
            self.knock(pts)
            self.line([(tx - 5, deck_top), (tx - 5 + rng.gauss(0, 0.4), ttop)], lw, rng=rng, wob=0.3, trem=0.3)
            self.line([(tx + 5, deck_top), (tx + 5 + rng.gauss(0, 0.4), ttop)], lw, rng=rng, wob=0.3, trem=0.3)
            y = deck_top
            k = 0
            while y > ttop + 8:
                self.line([(tx + (-5 if k % 2 else 5), y), (tx + (5 if k % 2 else -5), y - 10)], MINW, rng=rng, wob=0.15, trem=0, a0=0.2, a1=0.2)
                y -= 10
                k += 1
        # top truss
        tr = [(468, ttop - 4), (732, ttop - 4), (732, ttop + 8), (468, ttop + 8)]
        self.knock(tr)
        self.line([(462, ttop - 4), (600, ttop - 5), (738, ttop - 3)], lw, rng=rng, wob=0.4, trem=0.5)
        self.line([(464, ttop + 8), (600, ttop + 8.5), (736, ttop + 7)], lw, rng=rng, wob=0.4, trem=0.5)
        x = 470
        k = 0
        while x < 728:
            self.line([(x, ttop + (8 if k % 2 else -4)), (x + 11, ttop + (-4 if k % 2 else 8))], MINW, rng=rng, wob=0.15, trem=0, a0=0.2, a1=0.2)
            x += 11
            k += 1
        # hanging lights (cans) + red dots
        cans = [500, 532, 566, 634, 668, 700]
        for i, lx in enumerate(cans):
            can = [(lx - 4, ttop + 9), (lx + 4, ttop + 9), (lx + 6, ttop + 19), (lx - 6, ttop + 19)]
            self.knock(can)
            self.box(can, MINW, rng=rng, over=(-0.4, 1.2))
            if i in (1, 4):
                self.dot(lx, ttop + 21, 2.3, layer='R', rng=rng)
            else:
                self.blob([(lx - 5, ttop + 19), (lx + 5, ttop + 19), (lx + 4, ttop + 24), (lx - 4, ttop + 24)], 'Y', rng=rng, gap=0, shift=0.5, n=10)
        # line arrays hanging outside the towers
        for sx, sg in ((451, -1), (749, 1)):
            self.line([(sx, ttop - 4), (sx, ttop + 14)], MINW, rng=rng, wob=0.1, trem=0)
            y = ttop + 14
            for j in range(6):
                bw = 15 - j * 0.6
                ofs = sg * j * j * 0.25
                bx = sx + ofs
                bxs = [(bx - bw / 2, y), (bx + bw / 2, y), (bx + bw / 2 + sg * 0.6, y + 8), (bx - bw / 2 + sg * 0.6, y + 8)]
                self.knock(bxs)
                self.box(bxs, MINW, rng=rng, over=(-0.5, 1.2))
                y += 8.6
        # deck
        deck = [(x0, deck_top), (x1, deck_top), (x1 + 4, deck_bot), (x0 - 4, deck_bot)]
        self.knock(deck)
        self.box(deck, lw, rng=rng, over=(-1.0, 4.0))
        for i in range(1, 9):
            xx = x0 + (x1 - x0) * i / 9
            self.line([(xx, deck_top + 3), (xx + rng.gauss(0, 0.4), deck_bot - 2)], MINW, rng=rng, wob=0.2, trem=0, a0=0.3, a1=0.4)
        # the dj (tiny) at the table, one arm up
        tb = [(578, 757), (622, 757), (622, 772), (578, 772)]
        p = [(594, 757), (594, 746), (590, 741), (594, 734), (600, 731), (606, 734), (609, 741), (606, 746), (606, 757)]
        self.knock(p)
        self.line([(593, 757), (591, 748), (588, 746)], lw, rng=rng, wob=0.1, trem=0, a0=0.3, a1=0.3)
        self.line([(607, 757), (609, 748), (612, 746)], lw, rng=rng, wob=0.1, trem=0, a0=0.3, a1=0.3)
        hd = [(600 + math.cos(a) * 5.0, 738 + math.sin(a) * 5.6) for a in [TAU * i / 8 for i in range(8)]]
        self.knock(hd)
        self.line(hd, lw * 0.9, rng=rng, wob=0.1, trem=0, closed=True, close_frac=1.03)
        self.line([(611, 746), (618, 735), (619, 722)], lw * 0.9, rng=rng, wob=0.15, trem=0, a0=0.3, a1=0.3)
        self.dot(619.5, 720.5, 2.0, rng=rng)
        self.knock(tb)
        self.box(tb, lw, rng=rng, over=(-0.5, 2.5))
        self.blob([(583, 760), (598, 760), (598, 769), (583, 769)], 'Y', rng=rng, gap=0, shift=0.5, n=10)
        self.marks['stage'] = (600, 735)

    def beams(self, rng):
        srcs = [(498, 770), (530, 772), (670, 772), (702, 770)]
        tg = [(48, 580), (240, 572), (960, 572), (1152, 580)]
        for (sx, sy), (tx, ty) in zip(srcs, tg):
            ang = math.atan2(ty - sy, tx - sx)
            L = math.hypot(tx - sx, ty - sy)
            spread = rng.uniform(0.045, 0.06)
            for k in (-1, -0.3, 0.35, 1):
                a = ang + k * spread
                ln = L * (rng.uniform(0.78, 1.0) if abs(k) == 1 else rng.uniform(0.45, 0.8))
                ex, ey = sx + math.cos(a) * ln, sy + math.sin(a) * ln
                pts = [(sx + math.cos(a) * 30, sy + math.sin(a) * 30), ((sx + ex) / 2 + rng.gauss(0, 1.5), (sy + ey) / 2 + rng.gauss(0, 1.5)), (ex, ey)]
                self.line(pts, MINW, rng=rng, layer='Y', wob=0.5, trem=0.7, a0=2.0, a1=10.0, pv=0.2)

    def sound_marks(self, rng):
        # wobbly sound rising off the rig
        for (x0, amp, top, ph) in ((548, 4.5, 598, 0.0), (600, 5.5, 584, 1.7), (652, 4.5, 600, 3.1)):
            pts = []
            y = 662
            while y > top:
                pts.append((x0 + amp * math.sin((662 - y) / 7.5 + ph) + (x0 - 600) * (662 - y) / 260, y))
                y -= 3.5
            self.line(pts, MINW, rng=rng, wob=0.25, trem=0.3, a0=1.5, a1=6.0, pv=0.25)
        for sg in (-1, 1):
            cx, cy = 600 + sg * 172, 712
            for i, r in enumerate((14, 25, 37, 51)):
                a0, a1 = -0.75, 0.75
                pts = []
                for j in range(7):
                    a = a0 + (a1 - a0) * j / 6
                    pts.append((cx + sg * math.cos(a) * r, cy + math.sin(a) * r * 1.1))
                self.line(pts, MINW * 1.05, rng=rng, wob=0.6, trem=0.4, a0=0.6, a1=1.6)
        # little zig-zag shouts above the truss
        for (x, y, s) in ((548, 650, 1.0), (640, 645, 1.1), (596, 628, 0.8)):
            pts = [(x + i * 6 * s, y + (-4 if i % 2 else 4) * s) for i in range(5)]
            self.line(pts, MINW, rng=rng, wob=0.3, trem=0, a0=0.5, a1=0.8)
        for (x, y, a) in ((520, 655, -2.2), (680, 652, -0.9), (455, 668, -2.6), (746, 664, -0.5)):
            self.line([(x, y), (x + math.cos(a) * 12, y + math.sin(a) * 12)], MINW, rng=rng, wob=0.3, trem=0, a0=0.4, a1=1.0)

    def plane(self, x, y, s, lw, rng):
        # an airliner banking toward the airport, landing light on
        f = [(x - s, y + 0.1 * s), (x + s * 0.9, y - 0.12 * s)]
        self.line(f, lw, rng=rng, wob=0.05 * s, trem=0, a0=0.4, a1=0.4)
        self.line([(x - 0.05 * s, y), (x - 0.35 * s, y + 0.45 * s)], lw, rng=rng, wob=0.03 * s, trem=0, a0=0.3, a1=0.3)
        self.line([(x + 0.05 * s, y - 0.03 * s), (x + 0.25 * s, y - 0.42 * s)], lw * 0.9, rng=rng, wob=0.03 * s, trem=0, a0=0.3, a1=0.3)
        self.line([(x - 0.85 * s, y + 0.08 * s), (x - 1.0 * s, y - 0.25 * s)], lw * 0.9, rng=rng, wob=0.03 * s, trem=0, a0=0.3, a1=0.3)
        self.dot(x - 0.36 * s, y + 0.48 * s, 1.8, layer='R', rng=rng)
        self.dot(x + 0.95 * s, y - 0.13 * s, 1.7, layer='Y', rng=rng)

    # ---- the whole picture ----------------------------------------------
    def compose(self):
        R = lambda k: random.Random(SEED * 7919 + k)
        t0 = time.time()

        # sky: birds, plane
        r = R(1)
        self.plane(150, 546, 36, MINW, r)
        self.marks['plane'] = (150, 546)
        birds = [(1062, 552, 22, 0.12), (1126, 536, 16, -0.15), (1162, 572, 13, 0.25), (262, 598, 15, -0.2), (318, 572, 11, 0.1)]
        for (x, y, s, a) in birds:
            self.kite_bird(x, y, s, MINW, r, a)
        self.marks['birds'] = (1100, 548)

        # skyline (far towers first)
        r = R(2)
        self.clip = False
        HB = 772
        blds = []
        # left cluster (tall, slim)
        blds += [(40, 72, 640, 'slab'), (70, 98, 668, 'slant'), (118, 150, 612, 'crown'), (150, 186, 655, 'slab'), (200, 222, 690, 'flat_tank'),
                 (226, 262, 640, 'round'), (268, 296, 684, 'slab'), (300, 336, 662, 'flat_tank'), (350, 380, 700, 'slab')]
        # right cluster: the twins + others
        blds += [(818, 848, 690, 'flat_tank'), (852, 878, 662, 'slab'), (902, 936, 586, 'crown'), (948, 982, 592, 'crown'),
                 (996, 1030, 660, 'slant'), (1040, 1070, 690, 'flat_tank'), (1080, 1114, 640, 'round'), (1120, 1158, 676, 'slab')]
        # behind the stage, low
        blds += [(390, 430, 712, 'flat_tank'), (760, 800, 708, 'slab'), (430, 470, 705, 'slab'), (730, 762, 716, 'flat_tank')]
        blds.sort(key=lambda b: b[2])
        for (x0, x1, top, kind) in blds:
            self.building(x0 + r.gauss(0, 1), x1 + r.gauss(0, 1), top + r.gauss(0, 2), HB, MINW, r, kind=kind, lit=0.12)
        self.marks['twins'] = (942, 585)
        self.crane(338, 700, 628, 58, MINW, r)
        self.crane(1004, 662, 600, 46, MINW, r)

        # trees around the course
        r = R(3)
        x = 34
        while x < 1170:
            edge = min(x - 20, 1180 - x)
            k = 0.55 if edge < 40 else 1.0
            ry = r.uniform(14, 24) * k
            rx = r.uniform(20, 36) * k
            self.canopy(x, 748 + r.uniform(-6, 6), rx, ry, MINW, r)
            x += rx * r.uniform(1.1, 1.5)
        # trunks in gaps
        # race-course rails
        r = R(4)
        for y0, kk in ((768, 1.0), (781, 0.9)):
            for seg in ((24 + r.uniform(0, 10), 470), (730, 1176 - r.uniform(0, 10))):
                pts = [(seg[0], y0 + 2), ((seg[0] + seg[1]) / 2, y0 - 1), (seg[1], y0 + 1)]
                q = [(px, py + (0 if py < 0 else 0)) for px, py in pts]
                band = [(seg[0], y0 - 2), (seg[1], y0 - 2), (seg[1], y0 + 5), (seg[0], y0 + 5)]
                self.knock(band)
                self.line(q, MINW * kk, rng=r, wob=0.4, trem=0.6, a0=1.0, a1=2.0)
        x = 34
        while x < 1170:
            if not (462 < x < 738):
                pst = [(x - 2.5, 763), (x + 2.5, 763), (x + 2.5, 793), (x - 2.5, 793)]
                self.knock(pst)
                self.line([(x, 762), (x + r.gauss(0, 0.4), 793)], MINW, rng=r, wob=0.2, trem=0, a0=0.3, a1=0.5)
            x += r.uniform(26, 33)
        self.marks['rails'] = (90, 775)

        # light beams over the city, the sound, the stage
        r = R(5)
        self.beams(r)
        self.sound_marks(r)
        self.stage(R(6))
        print('  scenery %.1fs' % (time.time() - t0)); sys.stdout.flush()

        # grass tufts where the crowd hasn't reached
        r = R(7)
        for i in range(26):
            sg = r.choice((-1, 1))
            x = 600 + sg * r.uniform(330, 555)
            y = r.uniform(800, 880)
            if abs(x - 600) < 330 + (y - 800) * 3.5:
                continue
            if y < 838 and (x < 245 or x > 965):   # leave room for the hand-lettered notes
                continue
            s = r.uniform(4, 7)
            self.line([(x - s, y), (x - s * 0.4, y - s * 1.1), (x, y)], MINW, rng=r, wob=0.2, trem=0, a0=0.3, a1=0.4)
            self.line([(x, y), (x + s * 0.5, y - s * 1.3), (x + s, y)], MINW, rng=r, wob=0.2, trem=0, a0=0.3, a1=0.4)
        self.clip = True

        # the crowd, far to near
        r = R(8)
        HZ, K = 774, 520
        z = 17.0
        rows = []
        while z > 1.75:
            rows.append(z)
            z *= r.uniform(0.86, 0.9)
        cnt = 0
        for zi in rows:
            w0 = 128 / zi
            y0 = HZ + K / zi
            t = (zi - 1.75) / (17 - 1.75)
            hw = 670 - 390 * t ** 0.6
            x = 600 - hw + r.uniform(0, w0)
            ppl = []
            while x < 600 + hw:
                ppl.append(x)
                x += w0 * r.uniform(1.2, 1.95)
            r.shuffle(ppl)
            for x in ppl:
                edge = abs(x - 600) / hw
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
                    if q < 0.15:
                        o['arms'] = {r.choice((-1, 1)): 'phone'}
                    elif q < 0.24:
                        o['arms'] = {r.choice((-1, 1)): r.choice(['open', 'fist', 'peace', 'point', 'open'])}
                    elif q < 0.27:
                        k = r.choice(['open', 'open', 'fist'])
                        o['arms'] = {-1: k, 1: k}
                    o['tilt'] = r.gauss(0, 6)
                    if w > 50:
                        o['gfill'] = None
                    if w > 40:
                        o['hair'] = r.choice(['short', 'short', 'long', 'long', 'ponytail', 'bun', 'curly', 'cap', 'buzz', 'topknot', 'short', 'long'])
                    if r.random() < 0.04:
                        o['hair'] = 'turban'
                    prof = w > 32 and r.random() < 0.09
                    if prof:
                        o['_skiphead'] = True
                        o['tilt'] = 0
                    self.person(x, y, w, lw, r, o)
                    if prof:
                        self.head_profile(x, y, w * 1.02, lw, r, face=r.choice((-1, 1)), back=r.uniform(-8, 18), mouth=r.choice((0.0, 0.0, 0.8)),
                                          hair=r.choice(['bun', 'short', 'curly', 'short']), smile=r.random() < 0.5)
                cnt += 1
        print('  crowd %d people %.1fs' % (cnt, time.time() - t0)); sys.stdout.flush()

        # ------------ the people we know
        self.heroes(R(9))
        print('  heroes %.1fs' % (time.time() - t0)); sys.stdout.flush()
        # colour stops a little inside the vignette
        for sg in (-1, 1):
            edge = []
            yp = 640
            while yp <= 1600:
                edge.append((600 + sg * (vig_hw(yp) - 16 + 6 * math.sin(yp * 0.07)), yp))
                yp += 8
            poly = [(600 + sg * 700, 640)] + edge + [(600 + sg * 700, 1600)]
            for k in ('Y', 'B', 'R', 'H'):
                self.D[k].polygon([(x * S, y * S) for x, y in poly], fill=0)
        self.marks = {k: (round(v[0], 1), round(v[1] + OY, 1)) for k, v in self.marks.items()}

    def heroes(self, r):
        LW = 4.6
        # --- carrier + the girl on his shoulders (centre-left, furthest back of the heroes)
        cx, cy, w = 468, 1296, 124
        h = w * 1.13
        self.person(cx, cy, w, LW, r, {'garment': 'tee', 'gfill': None, 'hair': 'short', 'sw': 1.36, 'yend': 2.4, 'trail': False})
        # carrier's elbows sticking out (he's holding her shins)
        for sg in (-1, 1):
            sx, sy = cx + sg * w * 1.3, cy + 1.2 * h
            ctrl = [(sx, sy - 12), (sx + sg * 26, sy + 60), (sx + sg * 12, sy + 125), (sx - sg * 24, sy + 150)]
            sp, left, right = self.tube(ctrl, [0.42 * w, 0.40 * w, 0.36 * w, 0.32 * w], LW, r, wob=1.0, trem=0.8)
            self.knock(left + right[::-1])
            outer, inner = (left, right) if sg < 0 else (right, left)
            self.ink(outer, LW, rng=r, a0=0.5)
            self.ink(inner[int(len(inner) * 0.45):], LW, rng=r, a0=0.8)
            k = int(len(sp) * 0.3)
            self.line([left[k], ((left[k][0] + right[k][0]) / 2, left[k][1] + 6), right[k]], LW * 0.85, rng=r, wob=0.8, trem=0)
        # the girl's thighs over his shoulders
        gx, gw = cx + 2, 100
        gh = gw * 1.13
        hip_y = cy + 0.80 * h
        for sg in (-1, 1):
            th = [(gx + sg * 28, hip_y - 26), (gx + sg * 92, hip_y - 30), (gx + sg * 126, hip_y - 8), (gx + sg * 120, hip_y + 24),
                  (gx + sg * 68, hip_y + 32), (gx + sg * 28, hip_y + 22)]
            d = self.hand(th, closed=True, wob=1.0, trem=0.6, rng=r)
            self.knock(d)
            self.blob(th, 'B', rng=r, shift=2.0, gap=0.4)
            self.ink(d, LW, closed=True, rng=r, close_frac=0.9)
            self.line([(gx + sg * 100, hip_y - 22), (gx + sg * 108, hip_y + 0), (gx + sg * 98, hip_y + 18)], LW * 0.7, rng=r, wob=0.5, trem=0)
        # her: kurta, long braid with a paranda, both arms up, bangles
        gy = hip_y - 3.3 * gh
        self.person(gx, gy, gw, LW, r, {'garment': 'kurta', 'gfill': 'Y', 'hair': 'braid', 'hairlen': 2.2, 'paranda': True, 'sw': 1.12, 'yend': 3.3, 'trail': False,
                                         'tilt': -7, 'arms': {-1: 'open', 1: 'open'},
                                         'arm_-1': {'elbow': (gx - 1.45 * gw, gy + 0.1 * gh), 'wrist': (gx - 1.45 * gw, gy - 0.95 * gh), 'bangles': True},
                                         'arm_1': {'elbow': (gx + 1.4 * gw, gy - 0.02 * gh), 'wrist': (gx + 1.2 * gw, gy - 1.05 * gh), 'bangles': True}})
        self.marks['shoulders'] = (gx, gy)

        # --- the huggers (centre-right)
        Lx, Ly, Lw = 760, 1290, 108
        Rx, Ry, Rw = 905, 1302, 112
        self.person(Lx, Ly, Lw, LW, r, {'garment': 'tank', 'gfill': 'B', 'hair': 'bun', 'sw': 1.1, 'yend': 2.8, 'lean': 0.03, 'trail': False, '_skiphead': True})
        self.head_profile(Lx + 4, Ly - 4, Lw * 1.02, LW, r, face=1, back=-6, bindi=True, earring=True, gajra=True, smile=True, hair='bun')
        self.marks['huggers'] = (Lx + 40, Ly - 40)
        # R: back view, bandana, striped shirt
        self.person(Rx, Ry, Rw, LW, r, {'garment': 'shirt', 'gfill': None, 'hair': 'bandana', 'bandfill': 'B', 'sw': 1.22, 'tilt': -9, 'yend': 2.8, 'trail': False})
        Rh = Rw * 1.13
        body = [(Rx - 1.2 * Rw, Ry + 1.0 * Rh), (Rx + 1.2 * Rw, Ry + 1.0 * Rh), (Rx + 1.3 * Rw, Ry + 2.8 * Rh), (Rx - 1.3 * Rw, Ry + 2.8 * Rh)]
        r2 = random.Random(r.random())

        def stripes(dr, off):
            x = Rx - 1.4 * Rw
            while x < Rx + 1.4 * Rw:
                pts = self.hand([(x, Ry + 0.9 * Rh), (x + r2.gauss(0, 2), Ry + 1.9 * Rh), (x + r2.gauss(0, 3), Ry + 2.9 * Rh)], wob=1.0, trem=1.2, rng=r2)
                self._render(pts, 7.0, 'Y', 0.5, 1.0, 0.25, r2, draw=dr, off=off)
                x += r2.uniform(17, 22)
        self.masked(body, 'Y', stripes)
        # R's arm around L's shoulders
        sx, sy = Rx - 1.1 * Rw, Ry + 1.05 * Rh
        Lh = Lw * 1.13
        ctrl = [(sx + 10, sy + 6), (sx - 28, sy - 14), (Lx + 30, Ly + 0.98 * Lh), (Lx - 0.45 * Lw, Ly + 1.0 * Lh)]
        sp, left, right = self.tube(ctrl, [0.44 * Rw, 0.38 * Rw, 0.32 * Rw, 0.27 * Rw], LW, r, wob=1.0, trem=0.8)
        self.knock(left + right[::-1])
        self.ink(left, LW, rng=r, a0=0.6)
        self.ink(right, LW, rng=r, a0=0.6)
        k = int(len(sp) * 0.3)
        self.line([left[k], ((left[k][0] + right[k][0]) / 2 + 4, (left[k][1] + right[k][1]) / 2), right[k]], LW * 0.85, rng=r, wob=0.6, trem=0)
        ex, ey = sp[-1]
        self.draw_hand((ex, ey), math.radians(115), Rw * 0.45, 'mitten', LW * 0.85, r)
        # L's arm around R's waist
        sx, sy = Lx + 1.0 * Lw, Ly + 1.4 * Lh
        ctrl = [(sx - 8, sy - 8), (sx + 12, sy + 55), (Rx - 30, Ly + 2.05 * Lh), (Rx + 30, Ly + 1.95 * Lh)]
        sp, left, right = self.tube(ctrl, [0.36 * Lw, 0.32 * Lw, 0.28 * Lw, 0.24 * Lw], LW, r, wob=1.0, trem=0.8)
        self.knock(left + right[::-1])
        self.ink(left, LW, rng=r, a0=0.6)
        self.ink(right, LW, rng=r, a0=0.6)
        ex, ey = sp[-1]
        self.draw_hand((ex, ey), math.radians(-8), Lw * 0.5, 'open', LW * 0.8, r)
        k = int(len(sp) * 0.88)
        self.line([left[k], ((left[k][0] + right[k][0]) / 2 - 5, (left[k][1] + right[k][1]) / 2), right[k]], LW * 0.75, rng=r, wob=0.5, trem=0, layer='R')

        # --- the singer (right, nearest): body from behind, head turned and thrown back
        Sx, Sy, Sw = 1086, 1338, 118
        self.person(Sx, Sy, Sw, LW * 1.04, r, {'garment': 'tee', 'gfill': None, 'hair': 'curly', 'sw': 0.98, 'yend': 2.6, 'trail': False, '_skiphead': True})
        self.head_profile(Sx - 6, Sy - 6, Sw * 1.02, LW * 1.04, r, face=-1, back=24, mouth=1.0, specs=True, hair='curly', beard=True)
        self.marks['singer'] = (Sx - 60, Sy - 60)

        # --- the filmer (left, nearest)
        Fx, Fy, Fw = 150, 1334, 126
        self.person(Fx, Fy, Fw, LW * 1.04, r, {'garment': 'hoodie', 'gfill': 'B', 'hair': 'short', 'specs': True, 'sw': 1.18, 'yend': 2.6, 'trail': False, 'tilt': 4,
                                               'arms': {1: 'phone'},
                                               'arm_1': {'elbow': (Fx + 1.3 * Fw, Fy + 0.05 * Fw), 'wrist': (Fx + 0.8 * Fw, Fy - 0.78 * Fw), 'psize': 1.0 * Fw, 'land': False,
                                                         'screen': 'B', 'rec': True, 'content': True}})
        self.marks['filmer'] = (Fx + 0.9 * Fw, Fy - 1.5 * Fw)


# patch: allow person() to skip its head (profile drawn separately)
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


def clean(m, k=5):
    """morphological open: removes slivers narrower than ~k px"""
    return m.filter(ImageFilter.MinFilter(k)).filter(ImageFilter.MaxFilter(k))


def separations(art, way):
    line = art.L['line']
    if way == 'cream':
        # dark hair on the cream tee: the hair screen prints in line ink, strands reversed out
        line = ImageChops.subtract(ImageChops.lighter(line, art.L['H']), art.L['Hx'])
    line = clean(line, 5)
    seps = {'line': line}
    for k in ('Y', 'B', 'R'):
        m = shifted(art.L[k], *SHIFT[k])
        seps[k] = clean(ImageChops.subtract(m, line), 7)
    # later screens sit on top: trim what's underneath, drop slivers
    seps['Y'] = clean(ImageChops.subtract(ImageChops.subtract(seps['Y'], seps['B']), seps['R']), 7)
    seps['B'] = clean(ImageChops.subtract(seps['B'], seps['R']), 7)
    return seps


def render(seps, way):
    pal = PAL[way]
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for k in ('Y', 'B', 'R', 'line'):
        out.paste(hexrgb(pal[k]) + (255,), (0, 0), seps[k])
    return out


def main():
    t = time.time()
    sc = Scene(SEED)
    sc.compose()
    for way in ('black', 'cream'):
        seps = separations(sc, way)
        print('  separations %s %.1fs' % (way, time.time() - t)); sys.stdout.flush()
        art = render(seps, way)
        art.save(os.path.join(HERE, 'art-%s.png' % way), optimize=False, compress_level=6)
        bg = Image.new('RGBA', (W, H), hexrgb(PAL[way]['tee']) + (255,))
        bg.alpha_composite(art)
        bg.convert('RGB').resize((900, 1200), Image.LANCZOS).save(os.path.join(HERE, 'preview-%s.png' % way))
        if os.environ.get('CROP'):
            x, y = [int(v) for v in os.environ['CROP'].split(',')]
            bg.convert('RGB').crop((x, y, x + 1000, y + 1000)).save(os.path.join(HERE, '_crop-%s.png' % way))
    m = sc.marks
    manifest = {
        'concept': ("line drawings of the night: a hand-inked crowd at mahalaxmi race course, seen from behind, looking at a small, loud stage "
                    "under the mumbai towers. brush lines with pressure and wobble, spot colour printed loose and off-register. foreground: a girl "
                    "on someone's shoulders (kurta, braid with a red paranda, bangles), a guy filming with the stage on his screen, two friends "
                    "hugging (bindi, jhumka, gajra; bandana, striped shirt), a guy with his head thrown back singing. behind them a sea of black "
                    "hair and phone screens. the drawing trails off at the bottom like a sketchbook page. cream tee: hair is printed solid in the "
                    "line ink with strands reversed out; black tee: hair is the tee."),
        'palette_black': {'tee': PAL['black']['tee'], 'line': PAL['black']['line'], 'ink_yellow': PAL['black']['Y'], 'ink_blue': PAL['black']['B'],
                          'accent_red': PAL['black']['R']},
        'palette_cream': {'tee': PAL['cream']['tee'], 'line_and_hair': PAL['cream']['line'], 'ink_yellow': PAL['cream']['Y'],
                          'ink_blue': PAL['cream']['B'], 'accent_red': PAL['cream']['R']},
        'units': '1200 x 1600 (multiply by 3 for px on the 3600 x 4800 art)',
        'type_zones': [
            {'name': 'wordmark', 'x': 150, 'y': 70, 'w': 900, 'h': 135},
            {'name': 'city', 'x': 100, 'y': 215, 'w': 1000, 'h': 200},
            {'name': 'dates', 'x': 330, 'y': 428, 'w': 540, 'h': 52},
            {'name': 'signoff', 'x': 420, 'y': 494, 'w': 360, 'h': 30},
        ],
        'annotations': [
            {'text': 'the imperial twins, tardeo', 'x': 850, 'y': 494, 'rotation': -3, 'points_to': list(m['twins'])},
            {'text': 'black kites, doing laps', 'x': 1000, 'y': 458, 'rotation': -4, 'points_to': list(m['birds'])},
            {'text': 'a plane lining up for bom', 'x': 36, 'y': 448, 'rotation': 3, 'points_to': list(m['plane'])},
            {'text': 'still a working race course', 'x': 20, 'y': 760, 'rotation': -2, 'points_to': list(m['rails'])},
            {'text': 'our turf for two nights', 'x': 1012, 'y': 760, 'rotation': 2, 'points_to': [960, 800]},
        ],
        'figures': {k: list(v) for k, v in m.items()},
        'art_bbox': None,
        'seed': SEED,
    }
    a = Image.open(os.path.join(HERE, 'art-black.png')).getchannel('A').getbbox()
    manifest['art_bbox'] = {'x': round(a[0] / S), 'y': round(a[1] / S), 'w': round((a[2] - a[0]) / S), 'h': round((a[3] - a[1]) / S)}
    json.dump(manifest, open(os.path.join(HERE, 'manifest.json'), 'w'), indent=2)
    print('done %.1fs' % (time.time() - t))


if __name__ == '__main__':
    main()
