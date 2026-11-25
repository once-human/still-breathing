#!/usr/bin/env python3
"""
02 i am a party, front 01: "breath on glass". Left chest, about 11 cm.
The cab home after the show. The window has fogged from the inside with everyone's breath, and someone writes again..
on it with a fingertip. The fog is one cream screen, cut by hand as a breath spreads on cold glass (a bloom of rounded
fronts, no soft edge). The word is wiped out of it, so the shirt's black is the night through the letters. Where the
finger pushed the water it gathered: a few clear beads in the fog under the strokes, two drips running down, and the
heavier condensation beading along the bottom edge of the bloom.
    python3 gen.py        (ROUND=n keeps round-n.png)
"""
import math, os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import efront as E

WMM, HMM = 136, 92
h, art = E.boot(WMM, HMM, seed=311, layers=('cream', 'orange', 'wipe'))
import letters as L
from PIL import ImageChops

rng = art.rng
CX, CY = 66.0, 43.0


def disc(cx, cy, rx, ry, layer, wob=0.03, n=22, rng_=None):
    r_ = rng_ or rng
    ph = r_.uniform(0, math.tau)
    pts = [(cx + rx * math.cos(ph + math.tau * i / n) * r_.uniform(1 - wob, 1 + wob),
            cy + ry * math.sin(ph + math.tau * i / n) * r_.uniform(1 - wob, 1 + wob)) for i in range(n)]
    art.blob(pts, layer, scale=(1.0, 1.0), jit=0.01, shift=0.0, gap=0.0, n=max(24, n * 2))


# 1. the breath: one bloom spread on cold glass, a wide oval, fuller low down where it hit; one flat cream shape
ph = [rng.uniform(0, math.tau) for _ in range(4)]
RX, RY = 44.0, 23.0


def bloom(t):
    r = 1 + 0.018 * math.sin(3 * t + ph[0]) + 0.02 * math.sin(5 * t + ph[1]) + 0.012 * math.sin(9 * t + ph[2])
    y = math.sin(t)
    return (CX + RX * r * math.cos(t), CY + 1.5 + RY * r * y * (1 + 0.06 * y))


art.blob([bloom(math.tau * i / 72) for i in range(72)], 'cream', scale=(1.0, 1.0), jit=0.006, shift=0.0, gap=0.0, n=96)

# 2. the glass ends: the window's lower edge, its rubber seal drawn as one line under the bloom, turning up into the
# rounded corner at the left and stopping; a strip of clear glass between the fog and the seal
SEAL_Y = CY + 31.0
corner_x = CX - 53.0
seal = [(CX + 58.0, SEAL_Y + 0.3), (CX + 20.0, SEAL_Y - 0.1), (CX - 15.0, SEAL_Y + 0.2), (corner_x + 9.0, SEAL_Y),
        (corner_x + 2.6, SEAL_Y - 2.6), (corner_x, SEAL_Y - 9.0), (corner_x - 0.3, SEAL_Y - 34.0)]
art.line(seal, 1.7, layer='cream', wob=0.15, trem=0.12, a0=2.5, a1=3.0, pv=0.1)

# 3. the word, wiped with a fingertip: wide, round-ended, a little clumsy, leaning as handwriting on a window does
XH, FW = 12.5, 3.5
x0 = CX - L.width('again..', XH, FW, 0.11, 0.95) / 2 + 0.5
y0 = CY + 4.5
marks = L.write(art, 'again..', x0, y0, XH, FW, 'wipe', track=0.11, sx=0.95, rng=random.Random(31),
                lay=random.Random(33), wob=XH * 0.016, trem=XH * 0.012, rot_j=3.0, base_j=0.045, a0=0.0, a1=0.0,
                pv=0.07, dot_r=FW * 0.62, slant=0.07)

# 4. where the finger pushed the water: one drip from the foot of the n
def drip(x, y, length, bend):
    pts = [(x, y), (x + bend * 0.3 + rng.uniform(-0.2, 0.2), y + length * 0.35),
           (x + bend * 0.7 + rng.uniform(-0.2, 0.2), y + length * 0.7), (x + bend, y + length)]
    art.line(pts, 1.25, layer='wipe', wob=0.1, trem=0.06, a0=0.0, a1=0.0, pv=0.18)
    art.dot(x + bend + 0.05, y + length + 0.4, 1.35, layer='wipe')


n_ = [m for m in marks if m['ch'] == 'n'][0]
fx, fy = n_['T']((0.77, 0.0))
drip(fx + 0.1, fy + 0.5, 10.0, 0.4)

# behind the glass, a sodium streetlamp sits exactly where the dots were wiped: the fog hides it everywhere else,
# so the dots are the only warm thing, the night's orange showing through two fingertips
for m in marks:
    if m['ch'] == '.':
        dx, dy = m['dot']
        disc(dx, dy, FW * 0.62 + 1.6, FW * 0.62 + 1.6, 'orange', wob=0.04, n=14)
art.L['cream'].paste(0, (0, 0), art.L['wipe'])
art.L['wipe'].paste(0, (0, 0, art.L['wipe'].width, art.L['wipe'].height))
E.save(art, __file__, order=('orange', 'cream'), trim=False, crops=[(CX - 22, CY), (fx, fy + 6)])
