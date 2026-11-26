#!/usr/bin/env python3
"""
01 crowd, front 01: "filming". Left chest, about 8 cm.
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
ARM = L + R[::-1]
for k, (col, wd) in enumerate((('Y', 1.6), ('B', 2.3))):                         # a thread and a band round the wrist
    y = 92.0 + k * 3.9
    def paint(t, y=y, k=k, col=col, wd=wd):
        t.line([(27.4 + k * 0.6, y + 1.6), (31.0, y + 3.2), (36.0, y + 2.6), (40.6 - k * 0.5, y - 1.0)], wd, layer=col,
               wob=0.08, trem=0.05, a0=0.3, a1=0.3, pv=0.1)
    a.masked(ARM, col, paint)

# ------------------------------------------------------------------ the phone: steady (a made object), the hand round it wobbles
r = 4.6
corners = [(-PW / 2 + r, -PH / 2), (PW / 2 - r, -PH / 2), (PW / 2, -PH / 2 + r), (PW / 2, PH / 2 - r), (PW / 2 - r, PH / 2),
           (-PW / 2 + r, PH / 2), (-PW / 2, PH / 2 - r), (-PW / 2, -PH / 2 + r)]
body = a.hand([T(u, v) for u, v in corners], closed=True, wob=0.05, trem=0.03, step=0.4)
a.knock(body)
SI = 2.7                                            # the bezel
scr = [(-PW / 2 + SI, -PH / 2 + 3.3), (PW / 2 - SI, -PH / 2 + 3.3), (PW / 2 - SI, PH / 2 - 3.3), (-PW / 2 + SI, PH / 2 - 3.3)]

# on the screen, which is dark like the night it films: the drop, as a phone sees it from row forty.
# a small lit stage low on the screen (its LED wall the one sliver of green), beams fanning up off its roof,
# and the heads in front as one cream line, one hand up
SV = 12.5                                           # the deck's top (v)
deck = [T(-10.4, SV), T(10.4, SV - 0.1), T(10.6, SV + 2.2), T(-10.5, SV + 2.3)]
a.blob(deck, 'Y', scale=(0.99, 1.01), jit=0.015, shift=0.08, gap=0.0, n=24)
wall = [T(-4.6, SV - 4.4), T(4.6, SV - 4.5), T(4.7, SV - 1.2), T(-4.6, SV - 1.1)]
a.blob(wall, 'G', scale=(0.99, 1.01), jit=0.015, shift=0.12, gap=0.0, n=24)
# the beams: off the roof, fanning up and out, brush strokes that lift off near the top of the screen
beams = [(-6.6, -0.58, 26), (-4.2, -0.32, 32), (-1.4, -0.09, 35), (1.4, 0.10, 35), (4.2, 0.33, 32), (6.6, 0.60, 26)]
for u0, ang, ln in beams:
    ang += rng.gauss(0, 0.015)
    v0 = SV - 6.8 + abs(u0) * 0.25
    pts = []
    for f in (0.0, 0.5, 1.0):
        uu, vv = u0 + math.sin(ang) * (ln * f + 1.2), v0 - math.cos(ang) * (ln * f + 1.2)
        uu = max(-PW / 2 + SI + 1.0, min(PW / 2 - SI - 1.0, uu))
        vv = max(-PH / 2 + 12.0, vv)
        pts.append(T(uu, vv))
    a.line(pts, 1.25, layer='Y', wob=0.03, trem=0.02, a0=0.4, a1=8.0, pv=0.08)
# the heads in front: one cream line of heads and shoulders across the screen, one hand up holding its own phone
VH = 21.6
heads, u = [], -PW / 2 + SI + 1.0
while u < PW / 2 - SI - 3.0:
    hr = rng.uniform(1.75, 2.15)
    heads.append((u + hr, VH + rng.uniform(-0.9, 0.9), hr))
    u += hr * 2.0 + rng.uniform(0.9, 1.6)
shoulders = [T(-PW / 2 + SI + 0.2, VH + 4.6)]
for hx, hy, hr in heads:               # each head a small closed round in the cream line, its shoulders under it
    ring = [T(hx + hr * math.cos(q / 9 * math.tau), hy + hr * 1.1 * math.sin(q / 9 * math.tau)) for q in range(9)]
    a.ink(a.hand(ring, closed=True, wob=0.06, trem=0.02, step=0.25), 1.12, closed=True, a0=0.4, a1=0.5, pv=0.06)
    shoulders += [T(hx - hr * 1.5, hy + hr * 1.1 + 2.4), T(hx, hy + hr * 1.1 + 1.0), T(hx + hr * 1.5, hy + hr * 1.1 + 2.4)]
shoulders.append(T(PW / 2 - SI - 0.2, VH + 4.6))
a.line(shoulders, 1.15, wob=0.04, trem=0.02, a0=0.4, a1=0.6, pv=0.06)

# the rec dot, top left, blue, with its running time as one short cream tick beside it
pen.disc(a, *T(-PW / 2 + 6.4, -PH / 2 + 8.0), 1.5, 'B', rng=rng)
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
fingers = [(-11.0, 5.0, 3.2, 0.12), (-4.5, 5.8, 3.3, 0.05), (1.9, 4.9, 3.1, -0.04), (7.5, 3.0, 2.4, -0.14)]
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
x0, y0 = 50.0, 97.0
wa = pen.word(a, 'line', 'again', 'bric', S, x0, y0, weight=800, rng=rng, jit=0.02, turn=0.012)
pen.dots(a, 'Y', x0 + wa + 0.9, y0, S, rng=rng)

pen.save(a, __file__, order=('G', 'Y', 'B', 'line'), crops=[(41, 40), (62, 22), (70, 110)],
         placement={'where': 'left chest', 'top_cm': 15})
