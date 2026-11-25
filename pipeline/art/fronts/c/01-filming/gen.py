#!/usr/bin/env python3
"""
01 crowd, front 01: "filming". Left chest, about 10 cm.
The one thing everyone at the show did, drawn once and drawn properly: a hand holding a phone up over the crowd, the
screen toward us, and on it the drop as a phone sees it from far back: a handful of marigold beams going up off a
stage too small to see, the black line of heads in front, the rec dot on. The forearm runs down out of the hand and
the drawing stops; beside it, again.., its two dots in the beams' marigold.
The back's pen (cream, pressing and lifting) and its loose spot screens (green, marigold, blue), nothing else.
    R=1 python3 gen.py   draft (4.7 px/mm)      python3 gen.py   final (94 px/cm)
"""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import pen

WMM, HMM = 104, 116
h, a = pen.boot(WMM, HMM, seed=303, layers=('line', 'G', 'Y', 'B'))
rng = a.rng
LW, LD = 1.45, 1.2
c, t = (41.0, 44.0), -0.12                       # the phone's centre and its lean
PW, PH = 31.0, 60.0


def T(u, v):
    """phone space (u across, v down, mm from the centre) -> canvas"""
    return (c[0] + u * math.cos(t) - v * math.sin(t), c[1] + u * math.sin(t) + v * math.cos(t))


# ------------------------------------------------------------------ the forearm, out of the hand and down, fading out
sp, L, R = a.tube([T(-1, 18), T(-2, 33), (31, 95), (26, 108)], [14.0, 13.6, 14.5, 15.5], rng=rng, wob=0.3, trem=0.25)
a.knock(L + R[::-1])
a.ink(L[2:], LW, a0=0.8, a1=9.0, pv=0.14)
a.ink(R[2:], LW, a0=0.8, a1=7.0, pv=0.14)
a.line([(33.4, 89.0), (34.8, 86.4)], LD, wob=0.1, trem=0, a0=0.5, a1=1.2)          # tendons at the wrist
a.line([(38.6, 90.6), (39.8, 87.9)], LD, wob=0.1, trem=0, a0=0.5, a1=1.2)
ARM = L + R[::-1]
for k, (col, wd) in enumerate((('Y', 1.6), ('B', 2.3))):                         # a thread and a band round the wrist
    y = 92.0 + k * 3.9
    def paint(t, y=y, k=k, col=col, wd=wd):
        t.line([(22 + k * 1.0, y + 4.2), (34, y + 1.1), (46 - k * 0.6, y - 3.0)], wd, layer=col, wob=0.1, trem=0.06,
               a0=0.3, a1=0.3, pv=0.1)
    a.masked(ARM, col, paint)

# ------------------------------------------------------------------ the phone: steady (a made object), the hand round it wobbles
r = 4.6
corners = [(-PW / 2 + r, -PH / 2), (PW / 2 - r, -PH / 2), (PW / 2, -PH / 2 + r), (PW / 2, PH / 2 - r), (PW / 2 - r, PH / 2),
           (-PW / 2 + r, PH / 2), (-PW / 2, PH / 2 - r), (-PW / 2, -PH / 2 + r)]
body = a.hand([T(u, v) for u, v in corners], closed=True, wob=0.05, trem=0.03, step=0.4)
a.knock(body)
SI = 2.7                                            # the bezel
scr = [(-PW / 2 + SI, -PH / 2 + 3.3), (PW / 2 - SI, -PH / 2 + 3.3), (PW / 2 - SI, PH / 2 - 3.3), (-PW / 2 + SI, PH / 2 - 3.3)]
a.blob([T(u, v) for u, v in scr], 'G', scale=(0.995, 1.005), jit=0.006, shift=0.15, gap=0.0, n=44)

# on the screen: the drop, as a phone sees it from row forty
# the beams: from lamps hidden behind the heads, fanning up and out (each a brush stroke that lifts off at the top);
# the two middle ones nearly upright, the outer ones leaning away, none crossing: what a phone catches at the drop
SB = 17.0                                           # where the lamps are (v), behind the heads
beams = [(-8.6, -0.36, 26), (-5.2, -0.20, 33), (-1.8, -0.05, 37), (1.6, 0.07, 36), (5.0, 0.22, 32), (8.4, 0.40, 26)]
for u0, ang, ln in beams:
    ang += rng.gauss(0, 0.015)
    pts = []
    for f in (0.0, 0.5, 1.0):
        uu, vv = u0 + math.sin(ang) * ln * f, SB - math.cos(ang) * ln * f
        uu = max(-PW / 2 + SI + 1.4, min(PW / 2 - SI - 1.4, uu))
        vv = max(-PH / 2 + 12.5, vv)
        pts.append(T(uu, vv))
    a.line(pts, 1.3, layer='Y', wob=0.04, trem=0.02, a0=0.4, a1=7.0, pv=0.08)
# the stage's light behind the heads: one flat marigold band the heads stand against (the deck's glare)
glow = [T(-PW / 2 + SI - 0.4, SB - 1.2), T(0, SB - 2.2), T(PW / 2 - SI + 0.4, SB - 1.2), T(PW / 2 - SI + 0.4, PH / 2 - 3.0),
        T(-PW / 2 + SI - 0.4, PH / 2 - 3.0)]
a.blob(glow, 'Y', scale=(1.0, 1.0), jit=0.01, shift=0.05, gap=0.0, n=30)
a.knock([T(-PW / 2 - 1, PH / 2 - 3.3), T(PW / 2 + 1, PH / 2 - 3.3), T(PW / 2 + 1, PH / 2 + 3), T(-PW / 2 - 1, PH / 2 + 3)],
        layers=('Y',))


# the heads in front: one black silhouette across the bottom of the screen (the shirt showing through the green),
# heads of different sizes, two pairs of arms up
def hole(pts, layers=('G', 'Y')):
    p = a.hand([T(u, v) for u, v in pts], closed=True, wob=0.05, trem=0.02, step=0.3)
    for l in layers:
        a.D[l].polygon(h.P(p), fill=0)


VH = 24.0                                           # where the heads' crowns are (v)
crowd = [(-PW / 2 + SI - 0.6, PH / 2 - 2.0), (-PW / 2 + SI - 0.6, VH + 1.8)]
u = -PW / 2 + SI - 0.6
heads = []
while u < PW / 2 - SI - 3.0:
    hr = rng.uniform(1.7, 2.3)
    heads.append((u + hr, VH + rng.uniform(-0.8, 0.8), hr))
    u += hr * 2.0 - rng.uniform(0.1, 0.6)
for hx, hy, hr in heads:                      # each head a round, a little taller than wide, on its shoulders
    head = [(hx + hr * math.cos(q / 12 * math.tau), hy + hr * 1.1 * math.sin(q / 12 * math.tau)) for q in range(12)]
    hole(head)
crowd += [(PW / 2 - SI + 0.6, VH + 1.8), (PW / 2 - SI + 0.6, PH / 2 - 2.0)]
hole(crowd)                                   # the shoulders, one dark mass under the heads
hole([(-5.6, VH + 1.0), (-7.2, VH - 7.0), (-5.6, VH - 7.4), (-4.0, VH + 0.6)])          # one arm up, a fist
hole([(-7.9, VH - 6.6), (-7.4, VH - 9.4), (-5.2, VH - 9.6), (-4.9, VH - 6.8)])
hole([(5.2, VH + 1.0), (6.2, VH - 5.6), (7.8, VH - 5.4), (7.0, VH + 1.0)])             # one arm up with a phone
hole([(5.4, VH - 5.0), (5.8, VH - 9.6), (8.6, VH - 9.6), (8.3, VH - 5.0)])

# the rec dot, top left, blue, with its running time as one short cream tick beside it
a.knock([T(-PW / 2 + 6.4 + 2.5 * math.cos(k / 10 * math.tau), -PH / 2 + 8.0 + 2.5 * math.sin(k / 10 * math.tau)) for k in range(10)],
        layers=('G',))
pen.disc(a, *T(-PW / 2 + 6.4, -PH / 2 + 8.0), 1.5, 'B', rng=rng)
a.knock([T(-PW / 2 + 9.6, -PH / 2 + 6.6), T(-PW / 2 + 16.4, -PH / 2 + 6.6), T(-PW / 2 + 16.4, -PH / 2 + 9.4),
         T(-PW / 2 + 9.6, -PH / 2 + 9.4)], layers=('G',))
a.line([T(-PW / 2 + 10.6, -PH / 2 + 8.0), T(-PW / 2 + 15.4, -PH / 2 + 8.0)], 1.25, wob=0.03, trem=0, a0=0.4, a1=0.5)
# the camera slit at the top of the bezel, then the phone's edge over everything
a.line([T(-4.0, -PH / 2 + 1.6), T(4.0, -PH / 2 + 1.6)], 1.15, wob=0.03, trem=0, a0=0.4, a1=0.6)
nb = len(body)
k0 = min(range(nb), key=lambda i: (body[i][0] - T(0, PH / 2)[0]) ** 2 + (body[i][1] - T(0, PH / 2)[1]) ** 2)
a.ink(body[k0:] + body[1:k0 + 1], LW, a0=0.6, a1=0.6, pv=0.1)

# ------------------------------------------------------------------ the fingers round the right edge, the thumb on the left
# four pads curled round the phone from behind, nails toward us, each overlapping the one below; drawn top to bottom
# so each lower finger's knock cuts the line of the one above it cleanly
E = PW / 2
fingers = [(-10.6, 4.4, 3.1, 0.10), (-4.2, 5.6, 3.3, 0.04), (2.2, 5.2, 3.2, -0.03), (8.2, 3.8, 2.7, -0.10)]
for k, (v, ln, hf, tw) in enumerate(fingers):
    def F(du, dv):
        return T(E + du, v + dv + du * tw)
    tip = -ln
    outline = [F(5.2, -hf), F(1.0, -hf - 0.15), F(tip + hf * 0.75, -hf + 0.05), F(tip, -0.1), F(tip + hf * 0.7, hf),
               F(1.0, hf + 0.1), F(5.0, hf - 0.1)]
    p = a.hand(outline, wob=0.05, trem=0.02, step=0.3)
    a.knock(p + [F(6.0, 0)])
    a.ink(p, LD + 0.05, a0=0.5, a1=0.9, pv=0.1)
# the back of the hand behind the fingers: one smooth line from the top finger down into the heel
a.line([T(E + 5.0, -14.0), T(E + 6.6, -6.0), T(E + 6.4, 4.0), T(E + 4.6, 12.0), T(E + 1.0, 19.0), T(E - 3.0, 24.0)], LW,
       a0=0.6, a1=2.0, wob=0.08, trem=0.05, pv=0.12)
# the thumb: out of the palm at lower left, lying up along the edge, its tip on the glass with the nail toward us
thumb = [T(-E - 6.4, 25.5), T(-E - 5.0, 18.0), T(-E - 1.6, 12.6), T(-E + 2.2, 9.6), T(-E + 4.6, 10.0), T(-E + 4.9, 12.6),
         T(-E + 2.4, 15.6), T(-E - 0.2, 19.0), T(-E - 1.0, 24.5)]
p = a.hand(thumb, wob=0.06, trem=0.03, step=0.3)
a.knock(p + [T(-E - 4.0, 27.0)])
a.ink(p, LW, a0=0.7, a1=1.6, pv=0.12)
nail = [T(-E + 1.6, 10.9), T(-E + 3.5, 10.6), T(-E + 3.9, 12.2), T(-E + 2.6, 13.4)]
a.ink(a.hand(nail, wob=0.02, trem=0, step=0.25), 1.1, a0=0.4, a1=0.5, pv=0.05)
a.line([T(-E - 2.8, 17.6), T(-E - 0.8, 18.6)], 1.1, wob=0.03, trem=0, a0=0.4, a1=1.0)                    # the knuckle crease
# the palm's outer edge: from the root of the thumb down and in, into the forearm's line under the phone
a.line([T(-E - 6.4, 25.0), T(-E - 5.6, 30.0), T(-E - 2.0, 34.0), T(-8.6, 36.5)], LW, wob=0.08, trem=0.04, a0=0.6, a1=0.8,
       pv=0.12)

# ------------------------------------------------------------------ the word, beside the forearm
S = 14.0
x0, y0 = 48.5, 103.0
wa = pen.word(a, 'line', 'again', 'bric', S, x0, y0, weight=800, rng=rng, jit=0.02, turn=0.012)
pen.dots(a, 'Y', x0 + wa + 0.9, y0, S, rng=rng)

pen.save(a, __file__, order=('G', 'Y', 'B', 'line'), crops=[(41, 40), (62, 22), (70, 110)],
         placement={'where': 'left chest', 'top_cm': 15})
