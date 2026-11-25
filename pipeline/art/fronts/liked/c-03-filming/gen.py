#!/usr/bin/env python3
"""
01 crowd, front 03: "filming". Left chest, 10.6 cm.
The one thing everyone at the show did: a hand holding a phone up over the crowd, the screen toward us, and on it the
stage, tiny: the arched roof truss, the speaker hangs, the beams going up, a figure with both arms up in the light, the
rec dot on. The phones on the back show green screens; this is one of them, up close.
    R=1 python3 gen.py   draft (4.7 px/mm)      python3 gen.py   final (94 px/cm)
"""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pen

WMM, HMM = 95, 120
h, a = pen.boot(WMM, HMM, seed=303, layers=('line', 'G', 'Y', 'B'), print_w=106)   # printed 10.6 cm wide
rng = a.rng
LW, LD = 1.45, 1.2
c, t = (50.0, 50.0), -0.13                       # the phone's centre and its lean
PW, PH = 31.0, 60.0


def T(u, v):
    """phone space (u across, v down, mm from the centre) -> canvas"""
    return (c[0] + u * math.cos(t) - v * math.sin(t), c[1] + u * math.sin(t) + v * math.cos(t))


# ------------------------------------------------------------------ the forearm, from the bottom, inner wrist toward us
arm = a.tube([(30, 116), (36, 100), (45, 86), (49, 78)], [17, 15.5, 13.5, 12.5], rng=rng, wob=0.3, trem=0.25)
sp, L, R = arm
a.knock(L + R[::-1])
a.ink(L[:-3], LW, a0=0.8, a1=4.5)
a.ink(R[:-3], LW, a0=0.8, a1=4.5)
a.line([(37.5, 92), (40, 89.5)], LD, wob=0.1, trem=0, a0=0.5, a1=1.2)          # tendons at the wrist
a.line([(44, 94), (46, 91)], LD, wob=0.1, trem=0, a0=0.5, a1=1.2)
for k, col in enumerate(('Y', 'B')):                                               # a thread and a band round the wrist
    y = 96 + k * 3.6
    a.line([(31 + k * 1.2, y + 3), (42, y + 0.8), (53.5 - k * 0.5, y - 2.5)], 1.7, layer=col, wob=0.15, trem=0.1, a0=0.5, a1=0.6)

# the heel of the hand under the phone
heel = [T(-11, 28), T(-12, 33), T(-7, 36.5), T(2, 37), T(9, 34), T(12, 28)]
a.knock(heel + [T(10, 26), T(-10, 26)])
a.line(heel, LW, a0=0.8, a1=1.4)

# ------------------------------------------------------------------ the phone
r = 4.5
corners = [(-PW / 2 + r, -PH / 2), (PW / 2 - r, -PH / 2), (PW / 2, -PH / 2 + r), (PW / 2, PH / 2 - r), (PW / 2 - r, PH / 2),
           (-PW / 2 + r, PH / 2), (-PW / 2, PH / 2 - r), (-PW / 2, -PH / 2 + r)]
body = a.hand([T(u, v) for u, v in corners], closed=True, wob=0.15, trem=0.08, step=0.4)
a.knock(body)
scr = [(-PW / 2 + 2.6, -PH / 2 + 3.2), (PW / 2 - 2.6, -PH / 2 + 3.2), (PW / 2 - 2.6, PH / 2 - 3.2), (-PW / 2 + 2.6, PH / 2 - 3.2)]
a.blob([T(u, v) for u, v in scr], 'G', scale=(0.99, 1.01), jit=0.012, shift=0.25, gap=0.0, n=40)

# on the screen, cut out of the green: the stage, tiny
def cut(pts, w=1.15):
    a.carve([T(u, v) for u, v in pts], w, layer='G', a0=0.5, a1=0.8, pv=0.08, wob=0.06, trem=0.03)

def solid(pts, layer):
    p = a.hand([T(u, v) for u, v in pts], closed=True, wob=0.08, trem=0.04, step=0.3)
    a.D[layer].polygon(h.P(p), fill=0 if layer == 'G-' else 255) if layer != 'G-' else None

def hole(pts, layers=('G', 'Y')):
    p = a.hand([T(u, v) for u, v in pts], closed=True, wob=0.06, trem=0.03, step=0.3)
    for l in layers:
        a.D[l].polygon(h.P(p), fill=0)

# the stage, small and low on the screen: a dark arched roof on a deck, the speaker hangs, the figure lit yellow under it
S, SV = 0.72, -2.5                                  # its scale and how far down the screen it sits
def st(pts):
    return [(u * S, v * S + SV) for u, v in pts]
hole(st([(-10.5, 8.0), (-10.8, -3.0), (-8.6, -7.4), (-4.2, -9.6), (0.6, -10.2), (5.0, -9.4), (9.0, -7.0), (11.0, -2.6), (10.8, 8.2)]))
for sg in (-1, 1):
    hole(st([(sg * 12.8, -5.6), (sg * 15.4, -5.4), (sg * 15.2, 3.6), (sg * 12.7, 3.4)]))
hole(st([(-15, 8.0), (15, 8.2), (15.2, 10.8), (-15.2, 10.6)]))                       # the deck
# the figure: a small yellow person, arms up, in the dark of the stage
fy = SV + 1.2
a.line([T(-2.2, fy - 4.2), T(-1.0, fy - 1.2), T(0.0, fy - 0.2)], 1.15, layer='Y', wob=0.03, trem=0, a0=0.4, a1=0.5)
a.line([T(2.2, fy - 4.2), T(1.0, fy - 1.2), T(0.0, fy - 0.2)], 1.15, layer='Y', wob=0.03, trem=0, a0=0.4, a1=0.5)
a.line([T(0.0, fy - 0.6), T(0.05, fy + 4.4)], 1.5, layer='Y', wob=0.03, trem=0, a0=0.4, a1=0.5)
a.dot(*T(0.0, fy - 2.2), 1.05, layer='Y')
# the beams, fanning wide off the roof, out to the screen's edges
for ang in (-1.0, -0.6, -0.22, 0.2, 0.58, 0.98):
    x0, y0 = math.sin(ang) * 5.0, SV - 7.6
    x1, y1 = math.sin(ang) * 26, SV - 7.6 - math.cos(ang) * 26
    x1 = max(-PW / 2 + 4.2, min(PW / 2 - 4.2, x1))
    y1 = max(-PH / 2 + 12, y1)
    a.line([T(x0, y0), T((x0 + x1) / 2, (y0 + y1) / 2), T(x1, y1)], 1.3, layer='Y', wob=0.08, trem=0.03, a0=0.5, a1=2.6)
# the crowd in front: heads and shoulders of different heights, two arms up, one tiny phone, dark against the green
crowd = [(-PW / 2 + 1.8, PH / 2 - 2.0), (-PW / 2 + 1.8, 17.5)]
u = -PW / 2 + 1.8
k = 0
while u < PW / 2 - 3:
    hr = rng.uniform(2.0, 3.2)
    vy = 18.5 + rng.uniform(-2.2, 1.6)
    crowd += [(u + 0.4, vy + hr * 1.6), (u + hr * 0.3, vy + 0.2), (u + hr, vy - hr * 0.95), (u + hr * 1.7, vy + 0.2),
              (u + hr * 2.0, vy + hr * 1.5)]
    u += hr * 2.0 + rng.uniform(0.6, 1.6)
    k += 1
crowd += [(PW / 2 - 1.8, 17.6), (PW / 2 - 1.8, PH / 2 - 2.0)]
hole(crowd)
hole([(-8.2, 18), (-9.8, 11.2), (-8.0, 10.4), (-6.7, 17.4)])                         # an arm up
hole([(-10.4, 10.8), (-9.0, 8.6), (-7.2, 9.6), (-7.6, 11.6)])                         # its hand
hole([(6.0, 18), (7.4, 12.6), (9.2, 12.8), (8.2, 18)])                                # an arm with a phone
pp = a.hand([T(6.6, 9.6), T(9.8, 9.4), T(10.0, 13.6), T(6.8, 13.8)], closed=True, wob=0.04, trem=0)
a.D['Y'].polygon(h.P(pp), fill=255)                                                    # its screen, lit
# the rec dot top left with its running time beside it (two short ticks), the camera slit at the top
a.dot(*T(-PW / 2 + 6.2, -PH / 2 + 7.0), 1.6, layer='B')
for k in range(2):
    x0 = -PW / 2 + 9.4 + k * 4.4
    a.line([T(x0, -PH / 2 + 7.0), T(x0 + 3.0, -PH / 2 + 7.0)], 1.2, wob=0.03, trem=0, a0=0.4, a1=0.5)
a.line([T(-4.0, -PH / 2 + 1.6), T(4.0, -PH / 2 + 1.6)], 1.15, wob=0.04, trem=0, a0=0.4, a1=0.6)
a.ink(body, LW, closed=True, a0=0.6, a1=1.0, pv=0.18, close_frac=1.03)

# ------------------------------------------------------------------ the fingers wrapping the right edge, the thumb on the left
for k, (v, ln, tw) in enumerate(((-11.5, 4.4, 0.18), (-3.6, 6.2, 0.06), (4.6, 5.6, -0.05), (12.4, 3.8, -0.16))):
    def F(du, dv):
        return T(PW / 2 + du, v + dv + du * tw)
    tip = [F(-0.6, -3.1), F(-ln * 0.55, -2.9), F(-ln, -0.2), F(-ln * 0.6, 2.9), F(-0.3, 3.2), F(3.6, 3.3), F(4.4, -2.9)]
    p = a.hand(tip, closed=True, wob=0.08, trem=0.04, step=0.3)
    a.knock(p)
    a.ink(p[:len(p) * 5 // 7], LD, a0=0.5, a1=1.0)
    a.line([F(-ln * 0.78, -1.2), F(-ln * 0.62, 0.9)], 1.1, wob=0.04, trem=0, a0=0.4, a1=0.8)              # a nail
    if k < 3:
        a.line([F(2.2, 3.4), F(4.6, 3.9)], 1.1, wob=0.04, trem=0, a0=0.4, a1=1.2)                       # the crease to the next
# the back of the fingers outside the right edge, knuckles
a.line([T(PW / 2 + 4.6, -16), T(PW / 2 + 6.8, -4), T(PW / 2 + 6.2, 9), T(PW / 2 + 3.4, 18), T(PW / 2 - 1, 23)], LW, a0=0.8, a1=1.5)
for v in (-7.6, 0.6, 8.6):
    a.line([T(PW / 2 + 6.6, v), T(PW / 2 + 8.2, v + 1.2)], 1.15, wob=0.04, trem=0, a0=0.4, a1=1.0)
# the thumb pressed along the left edge, its tip over the screen, the nail showing
thumb = [T(-PW / 2 + 1.2, 9.5), T(-PW / 2 + 5.6, 10.6), T(-PW / 2 + 6.4, 13.6), T(-PW / 2 + 4.2, 17.0), T(-PW / 2 + 0.2, 21),
         T(-PW / 2 - 2.6, 26), T(-PW / 2 - 4.6, 24), T(-PW / 2 - 4.2, 17), T(-PW / 2 - 2.0, 11.5)]
p = a.hand(thumb, closed=True, wob=0.08, trem=0.05, step=0.3)
a.knock(p)
a.ink(p, LW, closed=True, a0=0.6, a1=1.0, close_frac=0.97)
a.line([T(-PW / 2 + 2.4, 11.6), T(-PW / 2 + 4.6, 12.0), T(-PW / 2 + 4.8, 14.4)], 1.15, wob=0.04, trem=0)            # the nail
a.line([T(-PW / 2 - 1.2, 18.5), T(-PW / 2 + 1.2, 18.2)], 1.1, wob=0.04, trem=0, a0=0.4, a1=1.0)                    # the knuckle crease

pen.save(a, __file__, order=('G', 'Y', 'B', 'line'), crops=[(50, 45), (50, 85)])
