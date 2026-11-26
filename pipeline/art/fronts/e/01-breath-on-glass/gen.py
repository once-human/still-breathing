#!/usr/bin/env python3
"""
02 i am a party, front 01: "breath on glass". Left chest, about 12 cm.
The cab home after the show. The bottom corner of the window has fogged with our breath, and someone writes again..
in it with a fingertip, the line drifting up as the cab moves. The fog is one cream screen, cut by hand: it sits in the
corner of the glass, its left and bottom edges following the rubber seal with a strip of clear glass between, its top
and right edges free where the breath thinned out (bulk low and left, where it landed). The word is wiped out of it, so
the shirt's black is the night through the letters; each stroke starts with the fatter pad where the finger pressed.
One drip runs from the n. Behind the glass a sodium streetlamp sits under the dots: the first dot is all orange, the
second is cut by the lamp's edge, half orange, half night. The seal is one steady cream line round the corner.
    python3 gen.py        (ROUND=n keeps round-n.png)
"""
import math, os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import efront as E

WMM, HMM = 132, 84
h, art = E.boot(WMM, HMM, seed=311, layers=('cream', 'orange', 'wipe'))
import letters as L

rng = art.rng

# the window's corner: the seal's centre line, an upright, an 8 mm round corner, the bottom run
SW, SR = 2.3, 8.0
SX, SY = 8.0, 75.0
GAPC = 2.6                                          # clear glass between the seal and the fog
FL, FB = SX + SW / 2 + GAPC, SY - SW / 2 - GAPC     # the fog's left and bottom edges
FR = FL + 104.0                                     # its right end
FR_ = SR - SW / 2 - GAPC                            # the fog's corner radius, concentric with the seal's
ph = [rng.uniform(0, math.tau) for _ in range(4)]


def ftop(x):
    """the fog's free top edge: high at the left where the breath landed, lower to the right, in slow fronts"""
    u = (x - FL) / (FR - FL)
    return FB - 50.0 + 17.0 * u ** 1.25 - 1.8 * math.sin(u * 6.5 + ph[0]) - 0.9 * math.sin(u * 13 + ph[1])


fog = []
for i in range(7):                                  # the rounded bottom-left corner
    t = math.pi / 2 + math.pi / 2 * i / 6
    fog.append((FL + FR_ + FR_ * math.cos(t), FB - FR_ + FR_ * math.sin(t)))
fog = [(FR - 14.0, FB)] + fog
fog += [(FL, ftop(FL) + 2.0)]
xs = [FL + (FR - 12.0 - FL) * i / 40 for i in range(41)]
fog += [(x, ftop(x)) for x in xs[1:]]
rx0, ry0 = xs[-1], ftop(xs[-1])                     # the right end rolls over and comes down in two rounded fronts
for i in range(1, 15):
    t = -math.pi / 2 + math.pi * i / 14
    fog.append((rx0 + 11.0 * math.cos(t) + 1.2 * math.sin(3 * t), (ry0 + FB) / 2 + (FB - ry0) / 2 * math.sin(t)))
art.fill(fog, 'cream')

seal = [(FR + 6.0, SY)]
seal += [(x, SY) for x in (FR - 30.0, FL + 40.0, SX + SR + 4.0)]
for i in range(7):
    t = math.pi / 2 + math.pi / 2 * i / 6
    seal.append((SX + SR + SR * math.cos(t), SY - SR + SR * math.sin(t)))
seal += [(SX, SY - 30.0), (SX, ftop(FL) + 2.0)]
art.line(seal, SW, layer='cream', wob=0.08, trem=0.06, a0=0.0, a1=0.0, pv=0.03)

# the word, wiped with one fingertip: one steady width, a pad where each stroke began, the line drifting up 2.5 degrees
XH, FW, TR = 14.0, 4.1, 0.1
x0, y0 = FL + 8.0, FB - 12.5
marks = L.write(art, 'again..', x0, y0, XH, FW, 'wipe', track=TR, rng=random.Random(31), lay=random.Random(33),
                wob=XH * 0.01, trem=XH * 0.006, rot_j=2.2, base_j=0.03, a0=0.0, a1=0.0, pv=0.03, skip='.',
                pad=1.22, rise=math.tan(math.radians(2.5)), slant=0.05)
dots = [m for m in marks if m['ch'] == '.']
for m in dots:                                       # the dots: two dabs, smeared a little sideways
    dx, dy = m['dot']
    art.line([(dx - 0.55, dy + 0.1), (dx + 0.55, dy - 0.1)], 4.6, layer='wipe', wob=0.05, trem=0.0, a0=0.0, a1=0.0, pv=0.0)

# the drip from the foot of the n: wanders a little, thins as it runs, ends in a bead
n_ = [m for m in marks if m['ch'] == 'n'][0]
fx, fy = n_['T']((0.77, 0.0))
drip = [(fx + 0.1, fy + 0.4), (fx + 0.6, fy + 3.4), (fx + 0.2, fy + 6.8), (fx + 0.7, fy + 9.8)]
art.line(drip, 1.8, layer='wipe', wob=0.15, trem=0.08, a0=0.0, a1=3.5, pv=0.05)
art.dot(fx + 0.75, fy + 11.0, 1.5, layer="wipe")

# behind the glass: the streetlamp, a flat orange disc about 10 mm across under the first dot, its edge through the second
(d1x, d1y), (d2x, d2y) = dots[0]['dot'], dots[1]['dot']
lr = 5.7                                            # covers the first dot, its edge through the middle of the second,
lx, ly = d2x - lr, d1y - 0.5                        # and stops short of the n
pts = [(lx + lr * math.cos(math.tau * i / 30), ly + lr * math.sin(math.tau * i / 30)) for i in range(30)]
art.fill(pts, 'orange')

art.L['cream'].paste(0, (0, 0), art.L['wipe'])
art.L['wipe'].paste(0, (0, 0, art.L['wipe'].width, art.L['wipe'].height))
E.save(art, __file__, order=('orange', 'cream'), trim=False, shifts={'orange': (0, 0), 'cream': (0, 0)},
       crops=[(x0 + 18, y0 - 6), (fx + 4, fy + 2)])
