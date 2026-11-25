#!/usr/bin/env python3
"""
01 crowd, front 08: "drawn". Centre chest, about 20 cm.
fred again.. drawn the way the back is drawn: every letter's outline traced from the lineup's face and then redrawn
with the back's cream pen, wobbling and pressing, and the back's spot screens laid under it loose and off register:
fred in green, again in marigold, the two dots in blue. Nothing taken from the back's picture, only its hand.
    R=1 python3 gen.py   draft (4.7 px/mm)      python3 gen.py   final (94 px/cm)
"""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import pen

WMM, HMM = 222, 58
h, a = pen.boot(WMM, HMM, seed=1808, layers=('line', 'G', 'Y', 'B'))
rng = a.rng
S = 34.0
TR = 1.3
x0, y0 = 8.0, 41.0
w1 = pen.letters(a, 'line', 'fred', 'bric', S, x0, y0, weight=760, fill='G', rng=rng, lw=1.25, track=TR)
sp = pen.width('fred ', 'bric', S, weight=760) - pen.width('fred', 'bric', S, weight=760) + TR
w2 = pen.letters(a, 'line', 'again', 'bric', S, x0 + w1 + sp, y0, weight=760, fill='Y', rng=rng, lw=1.25, track=TR)
# the two dots: a blue screen under a cream ring, like the letters
rr = 0.125 * S
for k in range(2):
    cx = x0 + w1 + sp + w2 + 2.4 + rr + k * 0.34 * S
    cy = y0 - rr * 1.02 + rng.gauss(0, 0.15)
    pen.disc(a, cx + 0.9, cy + 0.7, rr - 0.3, 'B', rng=rng)
    ring = [(cx + rr * math.cos(t / 10 * math.tau), cy + rr * math.sin(t / 10 * math.tau)) for t in range(10)]
    p = a.hand(ring, closed=True, wob=0.15, trem=0.1, step=0.35)
    a.ink(p, 1.25, layer='line', closed=True, a0=0.6, a1=1.2, pv=0.14)

pen.save(a, __file__, order=('G', 'Y', 'B', 'line'), crops=[(40, 30), (150, 30)],
         placement={'where': 'centre chest', 'top_cm': 11})
