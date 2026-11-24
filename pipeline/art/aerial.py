"""People seen from above, for the maps' crowds.

Each person is a little drawn figure, not a dot: the shoulders as an inked oval, the
head filled on top, arms reaching toward the stage with a hand at the end. They're
laid out on a loose grid, then some become friends: pairs holding hands, small rings
of people dancing hand in hand, someone up on another's shoulders, phones held up.

Units are the map's page units (1200 x 1600); R is pixels per unit. Everything is
drawn on the crowd's own ink layer, each figure knocked out of the ones under it so
lines never tangle.
"""
import math


class Crowd:
    def __init__(self, draw, R, toward, s=1.0, accent=None):
        self.d, self.R, self.toward, self.s = draw, R, toward, s
        self.acc = accent                  # optional ImageDraw for lit phones
        self.lw = 2.0 * s                  # ink line, units (the print clean-up drops anything under 1.7)

    # -- geometry ---------------------------------------------------------
    def _frame(self, x, y, a):
        ca, sa = math.cos(a), math.sin(a)
        R = self.R

        def P(u, v):                       # u: toward the stage, v: across
            return ((x + ca * u - sa * v) * R, (y + sa * u + ca * v) * R)
        return P

    def _oval(self, P, du, dv, rng, n=22, jit=0.12):
        pts = []
        for i in range(n):
            t = math.tau * i / n
            k = 1 + rng.gauss(0, jit * 0.25)
            pts.append(P(du * math.cos(t) * k, dv * math.sin(t) * k))
        return pts

    def _line(self, pts, w, fill=255):
        self.d.line(pts, fill=fill, width=max(1, int(round(w * self.R))), joint='curve')
        r = w * self.R / 2
        for p in (pts[0], pts[-1]):
            self.d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=fill)

    def _disc(self, c, r, fill=255):
        rr = r * self.R
        self.d.ellipse([c[0] - rr, c[1] - rr, c[0] + rr, c[1] + rr], fill=fill)

    def _shoulders(self, P, sw, sd, rng, n=14, jit=0.1):
        out, inn = [], []
        for i in range(n + 1):
            t = -1 + 2 * i / n
            u = -0.18 * sd * (1 - t * t)
            h = sd * 0.5 * math.sqrt(max(0.0, 1 - (t * 0.97) ** 2)) ** 0.7 * (1 + rng.gauss(0, jit * 0.2))
            out.append(P(u - h, sw * t))
            inn.append(P(u + h, sw * t))
        return out + inn[::-1]

    def shoulders_of(self, k=1.0):
        s = self.s * k
        return 5.2 * s, 5.0 * s            # half-width across, depth: a solid oval of shoulders ~2.2 heads wide

    # -- one person -------------------------------------------------------
    def person(self, x, y, a, rng, arms=(), k=1.0, phone=False, rider=False, hands=None):
        """arms: sides (-1, 1) raised toward the stage. hands: {side: (x, y) page units}
        to reach for instead (holding someone's hand)."""
        s = self.s * k
        lw = self.lw
        P = self._frame(x, y, a)
        sw, sd = self.shoulders_of(k)
        hr = 2.3 * s
        # arms first, so the body sits over where they leave it
        ends = []
        for sg in arms:
            reach = rng.uniform(8.6, 10.8) * s
            spread = rng.uniform(0.45, 0.85) * sw
            sh = P(0.0, sg * sw * 0.86)
            el = P(reach * 0.45, sg * (sw * 1.05 + rng.uniform(-0.3, 0.8) * s))
            hd = P(reach, sg * spread + rng.gauss(0, 0.5 * s))
            ends.append((sh, el, hd))
        for side, (hx, hy) in (hands or {}).items():
            sh = P(0.0, side * sw * 0.9)
            hd = (hx * self.R, hy * self.R)
            mid = ((sh[0] + hd[0]) / 2, (sh[1] + hd[1]) / 2)
            ends.append((sh, mid, hd))
        for sh, el, hd in ends:
            self._line([sh, el, hd], lw * 2.6, fill=0)
        for sh, el, hd in ends:
            self._line([sh, el, hd], lw * 1.05)
            self._disc(hd, 1.3 * s)
        if phone and ends:
            sh, el, hd = ends[0]
            ux, uy = math.cos(self.toward), math.sin(self.toward)
            c = (hd[0] + ux * 1.6 * s * self.R, hd[1] + uy * 1.6 * s * self.R)
            hw, hh = 1.25 * s * self.R, 1.9 * s * self.R
            ca, sa = math.cos(self.toward + math.pi / 2), math.sin(self.toward + math.pi / 2)
            quad = [(c[0] + ca * dx - sa * dy, c[1] + sa * dx + ca * dy)
                    for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]
            (self.acc if (self.acc is not None and rng.random() < 0.12) else self.d).polygon(quad, fill=255)
        # the body: the shoulders as a solid bar curving round behind the head
        body = self._shoulders(P, sw, sd, rng)
        self.d.polygon(self._shoulders(P, sw + lw * 0.5, sd + lw, rng, jit=0.0), fill=0)
        self.d.polygon(body, fill=255)
        # the head, forward of the shoulders, filled, a hair of paper round it
        hc = P(0.25 * s, rng.gauss(0, 0.15 * s))
        self._disc(hc, hr + lw * 0.42, fill=0)
        self._disc(hc, hr)
        if rider:                          # someone up on these shoulders: a second, smaller body ahead
            r2 = self._frame(*((v / self.R) for v in P(1.6 * s, 0)), a)
            self.d.polygon(self._shoulders(r2, sw * 0.76 + lw * 0.5, sd * 0.76 + lw, rng, jit=0.0), fill=0)
            self.d.polygon(self._shoulders(r2, sw * 0.76, sd * 0.76, rng), fill=255)
            for sg in (-1, 1):
                sh = r2(0.0, sg * sw * 0.66)
                hd = r2(8.0 * s, sg * sw * 0.8)
                self._line([sh, hd], lw * 2.4, fill=0)
                self._line([sh, hd], lw)
                self._disc(hd, 1.2 * s)
            c2 = r2(0.7 * s, 0)
            self._disc(c2, hr * 0.85 + lw * 0.7, fill=0)
            self._disc(c2, hr * 0.85)

    # -- friends ----------------------------------------------------------
    def ring(self, cx, cy, n, rng):
        """n friends in a circle, facing in, hand in hand."""
        sw, _ = self.shoulders_of()
        rad = n * (2 * sw + 4.0 * self.s) / math.tau
        pos = []
        for i in range(n):
            t = math.tau * i / n + rng.uniform(-0.08, 0.08)
            pos.append((cx + rad * math.cos(t), cy + rad * math.sin(t), t + math.pi))
        for i, (x, y, a) in enumerate(pos):
            nx_, ny_, na = pos[(i + 1) % n]
            px_, py_, pa = pos[i - 1]
            # meet each neighbour halfway, a little inside the circle
            mid = lambda q: ((x + q[0]) / 2 + (cx - (x + q[0]) / 2) * 0.08, (y + q[1]) / 2 + (cy - (y + q[1]) / 2) * 0.08)
            # facing the centre, +v (left hand) points one way round
            self.person(x, y, a, rng, hands={1: mid((nx_, ny_)), -1: mid((px_, py_))})
        return rad + 2 * sw

    def pair(self, x, y, a, rng, raise_outer=True):
        """two side by side, the inner hands held; maybe the outer arms up."""
        sw, _ = self.shoulders_of()
        gap = 2 * sw + rng.uniform(3.4, 4.6) * self.s
        ca, sa = math.cos(a), math.sin(a)
        L = (x + sa * gap / 2, y - ca * gap / 2)
        Rr = (x - sa * gap / 2, y + ca * gap / 2)
        hold = (x + ca * 1.2 * self.s, y + sa * 1.2 * self.s)
        self.person(*L, a, rng, arms=((-1,) if raise_outer and rng.random() < 0.7 else ()), hands={1: hold})
        self.person(*Rr, a, rng, arms=((1,) if raise_outer and rng.random() < 0.7 else ()), hands={-1: hold})
        return gap / 2 + sw


def lay_out(cands, crowd, rng, rings=3, pairs=14, riders=0.05, phones=0.08, one=0.22, both=0.17, min_p=0.42):
    """cands: [(x, y, p, dist)] accepted grid points, p = how packed it is there.
    Picks the friends first, then draws everyone, nearest the stage first."""
    import random as _r
    sw, sd = crowd.shoulders_of()
    taken = []                              # (x, y, radius) kept clear for the friends

    def clear(x, y, r):
        return all(math.hypot(x - a, y - b) > r + c for a, b, c in taken)
    good = [c for c in cands if c[2] > min_p]
    rng.shuffle(good)
    plans = []
    for c in good:
        if rings <= 0:
            break
        rad = 6 * (2 * sw + 3.2 * crowd.s) / math.tau + 2 * sw
        if clear(c[0], c[1], rad + 4):
            n = rng.choice((5, 6, 6, 7))
            taken.append((c[0], c[1], rad + 2))
            plans.append(('ring', c, n))
            crowd.rings_at = getattr(crowd, 'rings_at', []) + [(round(c[0]), round(c[1]))]
            rings -= 1
    for c in good:
        if pairs <= 0:
            break
        if clear(c[0], c[1], 2 * sw + 6):
            taken.append((c[0], c[1], 2 * sw + 3))
            plans.append(('pair', c, None))
            pairs -= 1
    singles = [c for c in cands if clear(c[0], c[1], sw * 0.9)]
    every = [(c[3], 'one', c) for c in singles] + [(p[1][3], p[0], p[1], p[2]) for p in plans]
    every.sort(key=lambda e: e[0])
    for e in every:
        kind, c = e[1], e[2]
        x, y = c[0], c[1]
        a = crowd.toward + rng.gauss(0, 0.22)
        if kind == 'ring':
            crowd.ring(x, y, e[3], rng)
        elif kind == 'pair':
            crowd.pair(x, y, a, rng)
        else:
            u = rng.random()
            if u < riders:
                crowd.person(x, y, a, rng, k=1.12, rider=True)
            elif u < riders + phones:
                crowd.person(x, y, a, rng, arms=(rng.choice((-1, 1)),), phone=True)
            elif u < riders + phones + both:
                crowd.person(x, y, a, rng, arms=(-1, 1))
            elif u < riders + phones + both + one:
                crowd.person(x, y, a, rng, arms=(rng.choice((-1, 1)),))
            else:
                crowd.person(x, y, a, rng, k=rng.uniform(0.94, 1.04))
