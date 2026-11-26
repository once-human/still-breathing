#!/usr/bin/env python3
"""
01 crowd, front 02: "drawn". Centre chest, about 21 cm.
fred again.. drawn the way the back is drawn: every letter's outline traced from the lineup's face and redrawn with
the back's cream pen, and the back's spot screens laid under it loose and off register, each letter's screen slipping
its own way. The colours wander across the word the way they wander across the crowd on the back (green, marigold,
two letters left bare), and one of the two dots is blue. Under it, small, the two nights.
Nothing taken from the back's picture, only its hand.
    R=1 python3 gen.py   draft (4.7 px/mm)      python3 gen.py   final (94 px/cm)
"""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import pen

WMM, HMM = 228, 76
h, a = pen.boot(WMM, HMM, seed=1808, layers=('line', 'G', 'Y', 'B'))
rng = a.rng
S = 34.0
KW = dict(wob=0.07, trem=0.05, every=2.0, shift_jit=0.04, fill_grow=0.0,
          min_loop=2.0, res=5.0, close={'g': 2.4}, weight=800, lw=1.15, rng=rng)
TR = 2.2
x0, y0 = 8.0, 41.0
w1 = pen.letters(a, 'line', 'fred', 'bric', S, x0, y0, fill=['G', '-', 'Y', 'G'], track=TR,
                 fill_shift=[(0.25, 1.9), (0, 0), (-0.2, 1.75), (0.15, -1.8)], **KW)
sp = (pen.width('fred ', 'bric', S, weight=800) - pen.width('fred', 'bric', S, weight=800)) * 0.7 + TR
x1 = x0 + w1 + sp
w2 = pen.letters(a, 'line', 'again', 'bric', S, x1, y0, fill=['Y', 'G', 'Y', '-', 'Y'], track=TR,
                 fill_shift=[(0.2, 1.85), (-0.25, 1.95), (0.1, -1.75), (0, 0), (0.25, 1.8)], **KW)
# the two dots: cream rings, the first with a blue screen under it, the second bare
rr = 0.125 * S
for k in range(2):
    cx = x1 + w2 + 2.4 + rr + k * 0.34 * S
    cy = y0 - rr * 1.02 + rng.gauss(0, 0.15)
    if k == 0:                     # a cream ring with the blue screen slipped down under it
        pen.disc(a, cx + 0.2, cy + 1.85, rr, 'B', rng=rng)
        ring = [(cx + rr * math.cos(t / 10 * math.tau), cy + rr * math.sin(t / 10 * math.tau)) for t in range(10)]
        p = a.hand(ring, closed=True, wob=0.08, trem=0.05, step=0.35)
        a.ink(p, 1.15, layer='line', closed=True, a0=0.6, a1=1.2, pv=0.14)
    else:                          # the last dot solid cream, the pen pressed down
        pen.disc(a, cx, cy, rr, 'line', rng=rng, wob=0.02)
right = x1 + w2 + 2.4 + 2 * rr + 0.34 * S
# the second line: the two nights, small, in the same lineup face, set under the right half
NS = 7.2
txt = 'mumbai · bengaluru · december 2026'
wn = pen.width(txt, 'bric', NS, weight=700, track=0.25)
pen.word(a, 'line', txt, 'bric', NS, right - wn, y0 + 20.0, weight=700, track=0.25, rng=rng, jit=0.03, turn=0.02,
         bold=0.1)

pen.save(a, __file__, order=('G', 'Y', 'B', 'line'), crops=[(40, 30), (150, 30)],
         placement={'where': 'centre chest', 'top_cm': 11})
