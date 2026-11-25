# 01 one hand: a single raised hand, palm to the stage, cut as a reduction linocut in four heat bands.
#   ulimit -v 2500000; R=2 python3 gen.py     # draft (draft.png)
#   ulimit -v 2500000; python3 gen.py         # final: art.png (9.5 cm at 94 px/cm) + pair.png
import os, sys, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import heat
H = heat.setup(9.5, 12.5)
HERE = os.path.dirname(os.path.abspath(__file__))
rng = random.Random(1)
art = H.Art(seed=11, layers=('violet', 'red', 'amber', 'cream', 'cut'))
art.rng = rng

# the hand in its own frame (units, 30 per cm): palm centre at 0, 0, fingers up (y negative); a left hand, palm out,
# thumb on the viewer's left. Proportions from a real hand: palm about as wide as it is long, the middle finger
# about 0.8 of the palm's length, index and ring about equal, the little finger short and set low.
ANG, OX, OY, S = math.radians(-8), 150, 206, 0.9
def T(pts):
    return heat.rot(pts, ANG, ox=OX, oy=OY, s=S)

# the palm, with the webbing scalloped between the fingers and the thumb's mound bulging out on the left
palm = [(-40, 78), (-8, 84), (24, 82), (50, 72), (64, 40), (68, 0), (66, -34), (58, -52),
        (46, -60), (32, -70), (18, -72), (3, -76), (-12, -78), (-27, -76), (-42, -70), (-56, -60),
        (-64, -40), (-70, -12), (-76, 12), (-74, 38), (-62, 62)]
# fingers: base (a little inside the palm so the web closes over it), lean (deg), bends (deg), length, base width
FING = [((-42, -56), -9, (5, 8), 98, 29),     # index
        ((-12, -64), -2, (4, 7), 112, 30),    # middle
        ((18, -60), 6, (6, 9), 100, 28),      # ring
        ((47, -44), 15, (9, 13), 78, 25)]     # little
def finger(base, d, bends, L, w):
    a = math.radians(d)
    pts = [base]
    for i, f in enumerate((0.45, 0.31, 0.24)):
        if i:
            a += math.radians(bends[i - 1]) * (1 if d >= 0 else -0.6)
        x, y = pts[-1]
        pts.append((x + math.sin(a) * L * f, y - math.cos(a) * L * f))
    return pts, [w * S, w * 0.94 * S, w * 0.86 * S, w * 0.72 * S]

# each finger runs its own temperature (how far the amber and the cream reach from the base)
TEMP = [(0.6, 0.3), (0.62, 0.26), (0.42, 0.0), (0.16, 0.0)]

# 1. RED: the whole hand, the skin's cooler rim. Forearm, palm, thumb, fingers
heat.nested_tube(art, T([(-4, 60), (-2, 96), (0, 124)]), [100 * S, 104 * S, 108 * S], [('red', 1.0, 0, 0)], rng, wob=1.2)
art.fill(heat.wobble_shape(T(palm), rng, 1.4, 44), 'red')
thumb = T([(-60, 42), (-82, 12), (-96, -16), (-100, -38), (-96, -52)])
heat.nested_tube(art, thumb, [44 * S, 34 * S, 28 * S, 24 * S, 20 * S], [('red', 1.0, 0, 0)], rng)
FP = []
for f in FING:
    pts, ws = finger(*f)
    FP.append((T(pts), ws))
    heat.nested_tube(art, T(pts), ws, [('red', 1.0, 0, 0)], rng)

# 2. AMBER: the warm body. Its own cut: the palm inside the rim, into the fingers as far as each one is warm,
# and up the thumb's mound
amber_palm = [(-30, 70), (10, 72), (44, 56), (54, 20), (56, -20), (46, -48), (20, -60), (-14, -64), (-44, -56),
              (-58, -30), (-62, 10), (-58, 44)]
art.fill(heat.wobble_shape(T(amber_palm), rng, 3.0, 26), 'amber')
heat.nested_tube(art, T([(-56, 40), (-78, 12), (-92, -14), (-96, -32)]), [22 * S, 18 * S, 14 * S, 11 * S],
                 [('amber', 1.0, 0, 0)], rng, wob=1.0)
for (pts, ws), (ra, rc) in zip(FP, TEMP):
    if ra > 0.05:
        heat.nested_tube(art, pts, [w * 0.56 * (1 - 0.3 * j / 3) for j, w in enumerate(ws)], [('amber', 1.0, 0.0, 1 - ra)], rng)

# 3. CREAM: the hot core where the blood is, not a scaled copy: the heel of the hand, the thumb's mound, and a band
# across the base of the index and middle fingers
heel = [(-52, 46), (-36, 26), (-10, 34), (18, 30), (40, 38), (44, 56), (20, 66), (-14, 66), (-44, 62)]
art.fill(heat.wobble_shape(T(heel), rng, 2.6, 20), 'cream')
mound = [(-64, 28), (-54, 6), (-42, 14), (-40, 36), (-50, 52)]
art.fill(heat.wobble_shape(T(mound), rng, 1.8, 14), 'cream')
base = [(-52, -50), (-30, -58), (-4, -60), (12, -52), (4, -42), (-22, -40), (-46, -38)]
art.fill(heat.wobble_shape(T(base), rng, 1.8, 18), 'cream')
for (pts, ws), (ra, rc) in zip(FP, TEMP):
    if rc > 0.05:
        heat.nested_tube(art, pts, [w * 0.3 for w in ws], [('cream', 1.0, 0.0, 1 - rc)], rng, wob=0.5)

# 4. VIOLET: the December jacket sleeve pushed down to the wrist, cold, wider than the arm; a red lip where the
# heat leaks out of its mouth
cuff = T([(-66, 104), (-34, 96), (4, 100), (40, 94), (70, 102), (76, 132), (80, 162), (-2, 168), (-74, 162), (-72, 132)])
art.knock(cuff, ('red', 'amber', 'cream'))
art.fill(heat.wobble_shape(cuff, rng, 1.8, 30), 'violet')
lip = T([(-56, 92), (-20, 84), (20, 86), (58, 92), (44, 102), (0, 100), (-44, 104)])
art.fill(heat.wobble_shape(lip, rng, 1.0, 16), 'red')

# 5. CUTS: gouges start sharp, swell and flick out; taken out of every ink so the shirt shows
def g(pts, w=4.4, local=True, **kw):
    kw.setdefault('pv', 0.45); kw.setdefault('a0', 0.6); kw.setdefault('a1', 4.0)
    heat.gouge(art, T(pts) if local else pts, w, rng, **kw)
g([(62, -30), (36, -36), (12, -40), (-10, -46), (-22, -54)], 4.8)          # heart line, ending between index and middle
g([(-64, -28), (-36, -22), (-6, -10), (22, 6)], 4.4)                        # head line, sloping across
g([(-60, -30), (-46, -10), (-40, 16), (-34, 42), (-24, 66)], 4.6)           # life line, round the thumb's mound
g([(-48, 76), (-14, 82), (20, 80)], 4.0, a1=2.0)                            # the wrist crease
for pts, ws in FP:
    for seg, frac, ln in ((1, 0.98, 0.42), (0, 0.18, 0.36)):   # a crescent at the middle joint, one at the finger's base
        (x0, y0), (x1, y1) = pts[seg], pts[seg + 1]
        cx, cy = x0 + (x1 - x0) * frac, y0 + (y1 - y0) * frac
        ux, uy = (x1 - x0), (y1 - y0)
        d = math.hypot(ux, uy); ux, uy = ux / d, uy / d
        hw = ws[seg] * ln
        g([(cx + uy * hw, cy - ux * hw), (cx - ux * 2.5, cy - uy * 2.5), (cx - uy * hw * 0.8, cy + ux * hw * 0.8)],
          4.0, False, a0=0.5, a1=2.4)
# sleeve folds: horizontal, bunching toward the wrist, coming in from the sides
for (x0, y0, dx, dy) in ((-70, 118, 40, 4), (74, 114, -46, 6), (-72, 142, 56, -2), (76, 140, -34, 4)):
    g([(x0, y0), (x0 + dx * 0.5, y0 + dy * 0.5 + 3), (x0 + dx, y0 + dy)], 4.6)

# the bottom of the block: a ragged cut edge with chatter, not a ruler line
edge = [(0, H.UH)]
x = -10
while x < H.UW + 20:
    edge.append((x, 352 + rng.uniform(-3, 3) + (rng.random() < 0.25) * rng.uniform(-9, -4)))
    x += rng.uniform(7, 15)
edge.append((H.UW, H.UH))
art.knock(edge)
art.knock([(0, 300), (H.UW, 300), (H.UW, H.UH), (0, H.UH)], ('red', 'amber', 'cream'))   # nothing warm below the cuff

order = ('violet', 'red', 'amber', 'cream')
inks = heat.finish(art, order, shifts={'violet': (-0.6, 0.4), 'amber': (2.6, 1.6), 'cream': (1.4, 0.6)})
heat.out(os.environ.get('OUT', 'draft.png'), inks, heat.INK, order, HERE)
if heat.FINAL:
    heat.pair(HERE)
