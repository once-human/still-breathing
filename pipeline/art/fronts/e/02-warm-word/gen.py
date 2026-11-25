#!/usr/bin/env python3
"""
02 i am a party, front 02: "warm word". Centre chest, about 18 cm.
fred again.. drawn by hand in the back's cream, and round it the warmth it gives off, drawn the way a heat camera
draws it but by hand: two contour lines following the letters, orange close in, violet further out, with a band of
black between, so the name sits inside its own heat like the crowd on the back. The contours are drawn a little higher
than the letters, wider apart above than below: the warmth rises. Between the letters they run together into one
outline. No picture, no gradient, no camera interface: just the name and the heat round it.
    python3 gen.py        (ROUND=n keeps round-n.png)
"""
import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import efront as E

WMM, HMM = 236, 62
h, art = E.boot(WMM, HMM, seed=202, layers=('violet', 'orange', 'cream', 'tmp'))
import letters as L
from PIL import ImageChops

XH, CORE, TR, SX = 14.5, 3.1, 0.05, 0.94
GAP, LINE = 1.75, 1.3                       # black between, and each contour line's width (mm)
SPACE = CORE + 4 * (GAP + LINE)             # letters spaced for the outer contour, so it runs together between them
x0 = (WMM - L.width('fred again..', XH, SPACE * 0.62, TR, SX)) / 2
y0 = 44.0


def word(layer, w, lift, erase=False):
    """the word's one hand-drawn path, at width w, lifted (mm); drawn into layer (or into tmp, to be cut away)"""
    L.write(art, 'fred again..', x0, y0 - lift, XH, w, layer, rng=random.Random(7), lay=random.Random(42),
            space_w=SPACE * 0.62, track=TR, sx=SX, dot_r=w * 0.6, a0=0.0, a1=0.0, pv=0.0 if layer != 'cream' else 0.08,
            wob=XH * 0.008, trem=XH * 0.005)


def contour(layer, k, lift):
    """the k-th contour line: the word drawn wide, minus the word drawn a line's width narrower"""
    outer = CORE + 2 * k * (GAP + LINE)
    word(layer, outer, lift)
    art.L['tmp'].paste(0, (0, 0, art.L['tmp'].width, art.L['tmp'].height))
    word('tmp', outer - 2 * LINE, lift)
    art.L[layer].paste(0, (0, 0), art.L['tmp'])


contour('violet', 2, 1.1)
contour('orange', 1, 0.5)
word('cream', CORE, 0.0)
art.L['tmp'].paste(0, (0, 0, art.L['tmp'].width, art.L['tmp'].height))

# the counters stay dark: the heat is drawn round the outside of the word, never inside an a, e, d or g
# (the e and the bowls are open shapes, so their counters are found on the letters thickened by 3 mm, then grown back)
from PIL import Image, ImageDraw
K = 2 * int(1.6 * E.PXMM) + 1
fat = h.dilate(art.L['cream'], K)
outside = fat.point(lambda p: 0 if p else 255)
ImageDraw.floodfill(outside, (0, 0), 128)
holes = h.dilate(outside.point(lambda p: 255 if p == 255 else 0), K)
for k in ('orange', 'violet'):
    art.L[k].paste(0, (0, 0), holes)

E.save(art, __file__, order=('violet', 'orange', 'cream'), trim=False,
       shifts={'violet': (0.12, 0.0), 'orange': (-0.08, 0.0), 'cream': (0, 0)}, crops=[(40, 34), (150, 36)])
