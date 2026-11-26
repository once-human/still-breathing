"""22° : late night, Bengaluru, after the Fred again.. show, in a soft drizzle under the rain trees.

    R=1 python3 gen.py             draft -> art-black-draft.png, preview-black-draft.png
    R=3 python3 gen.py             full  -> art-black.png, preview-black.png, manifest.json
Seeded; re-running gives the same picture."""
import os, json, time
from kit import *
from lib_life import *
from lib_city import *
import lib_city
from lib_v3 import *
from lib_show import *
import lib_show
from lib_r13 import *
import lib_r13
from lib_r18 import *
import lib_r18
from lib_r26 import *
import lib_r26
PAL['blue'] = '#3E63C9'    # deep night blue for the stroke clouds
lib_city.wash = lambda *a, **k: None    # REVIEW-1: no amber wash on the facades
lib_city.halo = lambda *a, **k: None
_bark3, _bark2 = lib_v3.bark3, lib_v3.bark2
lib_v3.bark3 = lambda *a, **k: _bark3(*a, **dict(k, amber_edge=False))
lib_v3.bark2 = lambda *a, **k: _bark2(*a, **dict(k, amber_edge=False))
bark3, bark2 = lib_v3.bark3, lib_v3.bark2    # OWNER-REVIEW-2: no rings round lights, anywhere
_carve_rain = lib_city.carve_rain
lib_city.carve_rain = lambda poly, layers, rng, sp=12.0, L=(7, 13), ang=None, prob=0.8: _carve_rain(
    poly, layers, rng, sp=max(sp, 14.0), L=L, ang=RAIN2, prob=prob * 0.7)
lib_r13.sheen_pool = lambda *a, **k: None    # round 26: no dot pools anywhere; light on the ground is reflection strokes


# the Green Line: a straight box girder past the right of the stage, a gentle curve away overhead behind the trees
def _vx(z):
    if z >= lib_show.TF:
        return 12.5 - 0.05 * (z - lib_show.TF)
    d = lib_show.TF - z
    return 12.5 + 0.05 * d + 0.012 * d * d


lib_show.vx = _vx

# round 26: every big flat colour fill on the buildings is laid as brush strokes with black between them
building = brushed(building, ('amber', 'copper', 'green', 'ice', 'yellow'))
bungalow = brushed(bungalow, ('amber', 'copper', 'green', 'ice', 'yellow'))

T0 = time.time()
rng = random.Random(SEED)


def log(*a):
    print('[%5.1fs]' % (time.time() - T0), *a, flush=True)


# ============================================================ the sky opening between the canopies
OPEN = [(222, -60), (978, -60), (978, 238), (925, 292), (870, 400), (812, 560), (796, 660), (404, 660), (392, 560),
        (352, 405), (292, 292), (222, 238)]


def reject(sx, sy, rx, ry, rng_):
    # never into the title zone
    if sx + rx * 0.7 > TITLE[0] - 6 and sx - rx * 0.7 < TITLE[2] + 6 and sy + ry * 0.7 > TITLE[1] - 10 and sy - ry * 0.7 < TITLE[3] + 8:
        return True
    for px, py in ((sx, sy), (sx - 0.45 * rx, sy), (sx + 0.45 * rx, sy), (sx, sy + 0.45 * ry)):
        if pip(px, py, OPEN):
            return True
    return False


# ============================================================ a cast-iron post clock: the hour without text
def post_clock(x, z, rng, hour=1, minute=42):
    s = S(z)
    g, t = pr(x, 0, z), pr(x, 3.0, z)
    w = clamp(0.1 * s, MINW, 6)
    knock_line([g, t], w + 3)
    edge(g, t, w, 'key', rng, over=(-0.5, 0.5))
    for f in (0.08, 0.12):   # base mouldings
        p = pr(x, f * 3.0, z)
        ln([(p[0] - w * 1.4, p[1]), (p[0] + w * 1.4, p[1])], MINW, 'key', rng, wob=0.05)
    c = pr(x, 3.45, z)
    r = clamp(0.42 * s, 12, 40)
    face = ell(c[0], c[1], r, r, n=28, rng=rng)
    knock(grow(face, 2.0), 0)
    blob(face, 'amber', rng, gap=0.0, shift=0.4, jit=0.01)
    ln(face + [face[0]], clamp(0.05 * s, MINW, 4.5), 'key', rng, wob=0.1)
    ln(ell(c[0], c[1], r * 1.14, r * 1.14, n=28, a0=-2.6, a1=1.9, rng=rng), MINW, 'key', rng, wob=0.1)
    # hour ticks carved out of the lit face
    for i in range(12):
        a = TAU * i / 12
        p0 = (c[0] + math.sin(a) * r * 0.74, c[1] - math.cos(a) * r * 0.74)
        p1 = (c[0] + math.sin(a) * r * (0.9 if i % 3 else 0.95), c[1] - math.cos(a) * r * (0.9 if i % 3 else 0.95))
        knock_line([p0, p1], MINW * (1.25 if i % 3 == 0 else 1.0), layers=('amber',))
    # 1:42
    ah = TAU * ((hour % 12) + minute / 60) / 12
    am = TAU * minute / 60
    for a, L, wd in ((ah, 0.5, 1.6), (am, 0.8, 1.25)):
        p1 = (c[0] + math.sin(a) * r * L, c[1] - math.cos(a) * r * L)
        knock_line([c, p1], MINW * wd, layers=('amber',))
    knock_ell(c[0], c[1], MINW * 1.0, MINW * 1.0, layers=('amber',))
    # finial and a drip hanging off the rim
    ln([(c[0], c[1] - r * 1.14), (c[0], c[1] - r * 1.45)], MINW * 1.2, 'key', rng)
    dot(c[0], c[1] - r * 1.5, MINW * 0.8, 'key', rng)
    ln([(c[0] + r * 0.5, c[1] + r * 1.05), (c[0] + r * 0.5, c[1] + r * 1.3)], MINW, 'key', rng)
    dot(c[0] + r * 0.5, c[1] + r * 1.55, MINW * 0.62, 'key', rng)
    halo(c[0], c[1], r * 1.55, 'amber', rng, rings=1)
    LAMPS.append((x, 3.45, z))
    light(x, 3.45, z, 'amber', wm=0.5, k=0.7)
    return c


# ============================================================ rain trees (screen space, after REVIEW-1)
def far_person(x, z, rng, umb=None):
    """someone walking back from the show, far away: a dark figure against the wet light, rimmed in cream by the stage
    behind them"""
    s = S(z)
    h = 1.7 * s * rng.uniform(0.92, 1.06)
    gx, gy = pr(x, 0, z)
    hw = h * 0.13
    st = rng.uniform(0.0, 0.08) * h
    body = [(gx - hw * 0.55 - st, gy), (gx - hw, gy - h * 0.55), (gx - hw * 0.95, gy - h * 0.8), (gx + hw * 0.95, gy - h * 0.8),
            (gx + hw, gy - h * 0.55), (gx + hw * 0.55 + st, gy)]
    knock(body, 0.8)
    hr = max(h * 0.07, 2.4)
    hc = (gx + rng.uniform(-0.1, 0.1) * hw, gy - h * 0.8 - hr * 1.1)
    knock_ell(hc[0], hc[1], hr + 0.8, hr * 1.15 + 0.8)
    # rim light: head and one shoulder
    side = rng.choice((-1, 1))
    ln(ell(hc[0], hc[1], hr, hr * 1.15, n=8, a0=math.pi * 1.05, a1=math.pi * 1.95, rng=rng), MINW, 'key', rng, wob=0.05)
    ln([(gx + side * hw * 0.95, gy - h * 0.78), (gx + side * hw, gy - h * 0.55)], MINW, 'key', rng, wob=0.05)
    if umb:
        rx = h * 0.32
        cy = hc[1] - hr * 1.6
        dome = ell(hc[0], cy, rx, rx * 0.42, n=12, a0=math.pi, a1=TAU, rng=rng)
        knock(dome + [dome[0]], 0.8)
        fillp(dome, umb)
        ln(dome, MINW, 'key', rng, wob=0.05)



def lamp_screen():
    return [pr(lx, lh, lz) for lx, lh, lz in LAMPS]


def slit(x, y, r=120.0):
    """how strongly a lamp right below lights a leaf mass whose belly is at (x, y)"""
    best = 0.0
    for lx, ly in lamp_screen():
        dy = (ly - y)
        if dy < -30:
            continue
        d2 = (x - lx) ** 2 + 1.6 * dy ** 2
        best = max(best, math.exp(-d2 / (r * r)))
    return best


def cl(cx, cy, rx, ry):
    return (cx, cy, rx, ry, slit(cx, cy + ry * 0.8))


# (cx, cy, rx, ry): the left crown heavier and lower than the right; nothing enters the title pocket
# rain-tree crowns: broad flat plates of leaf in tiers (an umbrella seen from under its edge), dark gaps between the
# tiers where the great limbs show; the left crown lower and heavier than the right
LEFT_CROWN = [(105, 86, 112, 46), (112, 186, 108, 44), (92, 290, 134, 50), (168, 400, 128, 50),
              (350, 440, 62, 26), (58, 470, 100, 42), (232, 490, 124, 44), (108, 550, 92, 36)]
RIGHT_CROWN = [(1110, 86, 100, 44), (1092, 190, 110, 46), (1122, 292, 120, 48), (1010, 310, 62, 34),
               (1060, 392, 116, 44), (1152, 470, 80, 36), (1022, 466, 72, 32)]
FAR_LEFT = [(362, 470, 40, 24), (318, 478, 40, 24)]
FAR_RIGHT = [(838, 512, 36, 22), (880, 486, 42, 26)]


def near_left_tree(rng):
    """the old rain tree at the near left: flared buttressed trunk, three twisting limbs, the heavy low crown"""
    limb3([(84, 790), (62, 700), (34, 612), (6, 540), (-20, 500)], 70, 38, rng, lit=0.4)
    limb3([(92, 780), (104, 680), (122, 580), (150, 500)], 60, 24, rng, lit=0.6)
    limb3([(102, 790), (130, 700), (160, 610), (190, 530), (226, 462)], 64, 22, rng, lit=0.85)
    trunk3([(34, 1172), (42, 1060), (56, 950), (74, 850), (92, 776)], [180, 138, 116, 106, 100], rng, lit_side=1,
           lit=0.75, moss=0.8, knots=2, wc=6.5)


def near_right_tree(rng):
    limb3([(1128, 808), (1150, 716), (1172, 630), (1205, 560)], 70, 46, rng, lit=0.4)
    limb3([(1118, 808), (1106, 690), (1098, 580), (1092, 480)], 60, 26, rng, lit=0.6)
    limb3([(1108, 816), (1062, 730), (1014, 650), (978, 572), (962, 496)], 66, 22, rng, lit=0.85)
    trunk3([(1150, 1090), (1144, 990), (1134, 900), (1122, 820)], [190, 140, 118, 108], rng, lit_side=-1, lit=0.75,
           moss=0.8, knots=2, wc=6.2)


def far_trunk(x, z, rng, limbs, hf=3.3, d=1.25):
    """a rain tree further down the street: its trunk and limbs (its leaves belong to the crowns)"""
    s = S(z)
    side = -1 if x < 0 else 1
    base = pr(x, 0, z)
    fork = pr(x - side * 0.35, hf, z)
    mid = lerp(base, fork, 0.5)
    for pts, w0, w1 in limbs:
        limb3([fork] + pts, w0 if w0 else d * 0.55 * s, w1 if w1 else d * 0.2 * s, rng, lit=0.6,
              wc=clamp(0.06 * s, MINW, 4.5))
    trunk3([base, (mid[0] + side * 0.05 * s, mid[1]), fork], [d * 1.5 * s, d * 1.05 * s, d * 0.95 * s], rng,
           lit_side=-side, lit=0.6, moss=0.6, knots=1 if s > 30 else 0, wc=clamp(0.08 * s, MINW, 5.5),
           roots=[(-0.6, 0.5), (0.1, 0.3), (0.6, 0.5)])


# ============================================================ the couple under one jacket
def cast_shadow(J, lamp_x, lamp_z, rng, L=1.6):
    """a shadow thrown toward us from the lamp behind: it hides the pool and the reflections where it falls"""
    for f in J['feet']:
        x0, y0 = f
        u = J['u']
        d = -1 if lamp_x > 0 else 1
        poly = [(x0 - 0.05 * u, y0), (x0 + 0.05 * u, y0), (x0 + 0.08 * u + d * 0.08 * u, y0 + 0.3 * u * L),
                (x0 - 0.1 * u + d * 0.08 * u, y0 + 0.28 * u * L)]
        OD.polygon(P(poly), fill=255)


def couple(rng):
    """two people shoulder to shoulder under one copper jacket held up over both heads like a roof: each holds an outer
    corner, the sleeves hang, the hem clears their crowns so both laughing faces stay open. Wristbands. They stand in
    the lamp's pool, rimmed amber by the lamp behind them"""
    zc = 9.6
    s = S(zc)
    h = 1.72 * s
    a = pr(-4.02, 0, zc)
    b = pr(-3.6, 0, zc + 0.05)
    J1 = figure(a[0], a[1], h * 0.95, rng, facing='front', stride=0.3, arms=((2.4, 3.3), 'hold'), top='top',
                bottom='jeans', tcol='green', bcol=None, hair='long', laugh=True, band=True, tilt=0.6, turn=0.7,
                lit=1, rim='amber')
    J2 = figure(b[0], b[1], h, rng, facing='front', stride=0.35, arms=('swing', (2.4, 3.3)), top='tee', tcol='ice',
                hair='curly', band=True, laugh=True, tilt=-0.3, turn=-0.5, lit=1, rim='amber', beard=False)
    cast_shadow(J1, -3.3, 17.5, rng)
    cast_shadow(J2, -3.3, 17.5, rng)
    u = h
    L = J1['hands'][0]
    R_ = max(J2['hands'], key=lambda p: -p[1])
    h1, h2 = J1['head'], J2['head']
    t1 = h1[1] - J1['hr'][1]
    t2 = h2[1] - J2['hr'][1]
    # the jacket held up as a roof: seen from above, its far edge stands above the hands and its near edge (the hem)
    # sags from hand to hand and rests on the two crowns, so both faces stay clear underneath
    hy = min(L[1], R_[1])
    top = catmull([(L[0] - 0.012 * u, L[1] - 0.02 * u), (h1[0] - 0.015 * u, hy - 0.05 * u),
                   ((h1[0] + h2[0]) / 2, hy - 0.06 * u), (h2[0] + 0.015 * u, hy - 0.055 * u),
                   (R_[0] + 0.012 * u, R_[1] - 0.025 * u)], step=3)
    hl1 = t1 - 0.022 * u - 5.0
    hl2 = t2 - 0.022 * u - 5.0
    hem = catmull([(L[0] + 0.006 * u, L[1] + 0.03 * u), (h1[0] - 0.035 * u, hl1 + 0.002 * u), (h1[0] + 0.01 * u, hl1),
                   ((h1[0] + h2[0]) / 2, max(hl1, hl2) - 0.004 * u), (h2[0] - 0.005 * u, hl2),
                   (h2[0] + 0.04 * u, hl2 + 0.004 * u), (R_[0] + 0.008 * u, R_[1] + 0.035 * u)], step=3)
    body = top + hem[::-1]
    # sleeves hanging from the two held corners: hers straight down, his flapping out toward the auto
    sl1 = [(L[0] - 0.01 * u, L[1] + 0.03 * u), (L[0] - 0.045 * u, L[1] + 0.17 * u), (L[0] - 0.05 * u, L[1] + 0.31 * u)]
    sl2 = [(R_[0] + 0.03 * u, R_[1] + 0.05 * u), (R_[0] + 0.1 * u, R_[1] + 0.14 * u), (R_[0] + 0.15 * u, R_[1] + 0.27 * u)]
    sleeves = []
    for sp_, w0, w1 in ((sl1, 0.06, 0.045), (sl2, 0.058, 0.044)):
        sp, ws = tube(sp_, [w0 * u, (w0 + w1) / 2 * u, w1 * u])
        Lp, Rp = tube_poly(sp, ws)
        sleeves.append((Lp, Rp))
    for Lp, Rp in sleeves:
        knock(Lp + Rp[::-1], 1.4)
    knock(grow(body, 1.0), 1.4)
    for Lp, Rp in sleeves:
        blob(Lp + Rp[::-1], 'copper', rng, gap=0.0, shift=0.6, jit=0.02)
    blob(body, 'copper', rng, gap=0.0, shift=0.6, jit=0.015, n=80)
    w = clamp(0.019 * u, MINW, 5.2)
    ln(top, w * 1.15, 'key', rng, wob=0.2)
    # the collar along the front edge: the hem, a fold line just inside it, the notch of the lapels between the heads
    ln(hem, w, 'key', rng, wob=0.2)
    col = [(p[0], p[1] - 0.03 * u) for p in hem[2:-2]]
    col = [p for p in col if pip(p[0], p[1], body)]
    if len(col) > 3:
        ln(col, MINW, 'key', rng, wob=0.15)
    nm = ((h1[0] + h2[0]) / 2, max(hl1, hl2) + 0.03 * u)
    ln([(nm[0] - 0.03 * u, nm[1] - 0.035 * u), (nm[0], nm[1] - 0.005 * u), (nm[0] + 0.03 * u, nm[1] - 0.035 * u)],
       MINW, 'key', rng, wob=0.1)
    # shadow folds in the cloth: carved, pulled from the held corners
    for hp, sgn in ((L, 1), (R_, -1)):
        for k_ in range(3):
            p0 = (hp[0] + sgn * (0.03 + 0.03 * k_) * u, hp[1] + 0.02 * u)
            p1 = (p0[0] + sgn * 0.09 * u, p0[1] + (0.02 + 0.012 * k_) * u)
            if pip(p0[0], p0[1], body) and pip(p1[0], p1[1], body):
                carve([p0, p1], MINW, 'copper', rng)
    # the lamp behind them catches the top of the cloth: an amber rim
    ln([(p[0], p[1] - w - MINW * 0.9) for p in top[len(top) // 3:]], MINW, 'amber', rng, wob=0.2)
    for Lp, Rp in sleeves:
        ln(Lp[1::2], w * 0.9, 'key', rng, wob=0.2)
        ln(Rp[1::2], w * 0.9, 'key', rng, wob=0.2)
        ln([Lp[-1], Rp[-1]], w * 0.9, 'key', rng)
        ln([Lp[-3], Rp[-3]], MINW, 'key', rng)            # cuff
    # the hands on top of the cloth, gripping
    for hp in (L, R_):
        knock_ell(hp[0], hp[1], 0.032 * u, 0.028 * u)
        ln(ell(hp[0], hp[1], 0.027 * u, 0.023 * u, n=12, rng=rng), MINW * 1.1, 'key', rng)
        ln([(hp[0] - 0.02 * u, hp[1] - 0.004 * u), (hp[0] + 0.01 * u, hp[1] - 0.016 * u)], MINW, 'key', rng)
    # his corner waving: three motion ticks
    for k_ in range(3):
        a_ = -0.9 + 0.45 * k_
        r0, r1 = 0.07 * u, 0.1 * u
        ln([(R_[0] + math.cos(a_) * r0, R_[1] + math.sin(a_) * r0 - 0.02 * u),
            (R_[0] + math.cos(a_) * r1, R_[1] + math.sin(a_) * r1 - 0.02 * u)], MINW, 'key', rng, wob=0.05)
    # drizzle beading on the jacket: drips from the hem and the sleeves
    for p in (hem[len(hem) // 4], hem[len(hem) // 2], sl1[-1], sl2[-1]):
        ln([(p[0], p[1] + 5), (p[0], p[1] + rng.uniform(10, 14))], MINW, 'key', rng, wob=0.05)
        dot(p[0], p[1] + rng.uniform(18, 22), MINW * 0.62, 'key', rng)
    # the two laughing faces, drawn big enough to print: the fringe lifted, two eye dots, an open laughing mouth
    for J, hh, tn in ((J1, h * 0.95, 0.7), (J2, h, -0.5)):
        hc = J['head']
        hrx, hry = 0.052 * hh, 0.064 * hh
        knock_ell(hc[0], hc[1] + 0.12 * hry, hrx * 0.82, hry * 0.74)
        fy = hc[1] - 0.62 * hry
        ln([(hc[0] - hrx * 0.86, fy + 0.12 * hry), (hc[0] - hrx * 0.2, fy - 0.04 * hry),
            (hc[0] + hrx * 0.5, fy + 0.02 * hry), (hc[0] + hrx * 0.86, fy + 0.14 * hry)], MINW * 1.05, 'key', rng, wob=0.08)
        ox = hc[0] + tn * 0.12 * hrx
        ey = hc[1] - 0.12 * hry
        for e in (-1, 1):
            dot(ox + e * hrx * 0.38 * (1 - 0.25 * tn * e), ey, MINW * 0.7, 'key', rng)
        my = hc[1] + 0.3 * hry
        mw = hrx * 0.36
        mouth = [(ox - mw, my)] + [(ox + math.cos(a) * mw, my + math.sin(a) * hry * 0.27)
                                   for a in [math.pi * i / 8 for i in range(8, -1, -1)]]
        fillp(mouth, 'key')
    return J1, J2


def friends(rng):
    """three friends walking back toward us arm in arm, overlapping: one with her face up to the drizzle swinging a
    furled umbrella, one holding an open umbrella over the two of them, one with a hand out to feel the rain"""
    out = []
    spec = [(1.86, 9.0, dict(facing='front', arms=('hold', 'around'), top='tee', tcol='green', hair='bun', face_up=True,
                             turn=0.5)),
            (2.3, 9.25, dict(facing='front', arms=('around', 'umbrella'), top='hoodie', tcol='copper', hair='short',
                             laugh=True, beard=True, turn=-0.4)),
            (2.78, 9.05, dict(facing='front', arms=((1.4, 1.75), 'out'), top='kurta', tcol='ice', hair='long', turn=-0.6,
                              laugh=True))]
    for x, z, kw in sorted(spec, key=lambda t: -t[1]):
        g = pr(x, 0, z)
        J = figure(g[0], g[1], 1.7 * S(z), rng, stride=0.4, band=True, lit=-1, rim='amber', **kw)
        cast_shadow(J, 3.3, 11, rng)
        out.append((x, J))
    out = [J for x, J in sorted(out, key=lambda t: t[0])]
    J = out[0]
    umbrella_closed(J['hands'][0][0], J['hands'][0][1], J['u'], rng, col='ice', ang=0.25)
    umbrella_open(out[1], rng, col='green', hand=1)
    # the open hand: a few drops landing on the palm
    hx, hy = out[2]['hands'][-1]
    for k in range(3):
        dx = rng.uniform(-14, 14)
        ln([(hx + dx, hy - 34 - k * 9), (hx + dx + 3, hy - 22 - k * 9)], MINW, 'key', rng, wob=0.05)
    return out


# ============================================================ round 12's couple, put back (owner, after round 26)
import lib_life, lib_life_r12
lib_life_r12.LAMPS = lib_life.LAMPS


def couple_r12(rng, figure=lib_life_r12.figure):
    """two people shoulder to shoulder mid-stride under one denim jacket held up by its corners: she laughs up into the
    drizzle; he lifts his corner high and waves it at the auto, the sleeve flapping; their inner arms round each other"""
    zc = 9.6
    s = S(zc)
    h = 1.72 * s
    a = pr(-4.12, 0, zc)
    b = pr(-3.64, 0, zc + 0.05)
    J2 = figure(b[0], b[1], h, rng, facing='front', stride=0.35, arms=('around', (2.3, 2.75)), top='shirt', tcol='ice',
                hair='curly', band=True, laugh=True, tilt=0.4)
    J1 = figure(a[0], a[1], h * 0.95, rng, facing='front', stride=0.35, arms=((2.55, 3.0), 'swing'), top='top',
                bottom='skirt', tcol='amber', bcol='green', hair='long', laugh=True, band=True, face_up=True, tilt=-0.7)
    u = h
    L = J1['hands'][0]
    R_ = max(J2['hands'], key=lambda p: p[0])
    h1, h2 = J1['head'], J2['head']
    t1 = h1[1] - J1['hr'][1]
    t2 = h2[1] - J2['hr'][1]
    n = 10
    up, low = [], []
    for i in range(n + 1):
        t = i / n
        x = L[0] + (R_[0] - L[0]) * t
        yl = L[1] + (R_[1] - L[1]) * t
        # resting on the two heads in between the hands: the cloth sags onto them
        dip = 0.0
        for hc_, tt in ((h1, t1), (h2, t2)):
            dip = max(dip, max(0.0, 1 - abs(x - hc_[0]) / (0.11 * u)) * (tt - 0.035 * u - yl))
        yt = yl + dip * 0.9 + 0.025 * u * math.sin(math.pi * t)
        up.append((x + rng.gauss(0, 0.003 * u), yt))
        yb = yt + 0.075 * u + 0.02 * u * math.sin(math.pi * t)
        for hc_, tt in ((h1, t1), (h2, t2)):         # never below the hairline: the faces stay clear
            if abs(x - hc_[0]) < 0.08 * u:
                yb = min(yb, tt + 0.02 * u)
        low.append((x, max(yb, yt + 0.04 * u)))
    sleeve = [low[-1], (R_[0] + 0.03 * u, R_[1] + 0.05 * u), (R_[0] + 0.09 * u, R_[1] + 0.24 * u),
              (R_[0] + 0.045 * u, R_[1] + 0.27 * u), (R_[0] - 0.01 * u, R_[1] + 0.09 * u)]
    col = [up[0], (L[0] - 0.045 * u, L[1] + 0.015 * u), (L[0] - 0.035 * u, L[1] + 0.075 * u), low[0]]
    poly = up + low[::-1]
    for p_ in (grow(poly, 1.5), sleeve, col):
        knock(p_, 1.2)
    for p_ in (poly, sleeve, col):
        blob(p_, 'copper', rng, gap=0.0, shift=0.5, jit=0.02)
    w = clamp(0.018 * u, MINW, 5.0)
    ln(up, w * 1.1, 'key', rng, wob=0.2)
    ln(low, w, 'key', rng, wob=0.2)
    pline(sleeve, w * 0.85, 'key', rng, closed=False)
    pline(col, w * 0.85, 'key', rng, closed=False)
    ln([lerp(sleeve[2], sleeve[1], 0.18), lerp(sleeve[3], sleeve[4], 0.18)], MINW, 'key', rng)       # cuff
    # folds pulled from each held corner, one seam with stitching
    for hp, sgn in ((L, 1), (R_, -1)):
        for dx_ in (0.05, 0.1):
            ln([(hp[0] + sgn * 0.02 * u, hp[1] + 0.02 * u), (hp[0] + sgn * dx_ * u * 1.4, hp[1] + 0.06 * u)], MINW,
               'key', rng, wob=0.2)
    ln([lerp(up[3], low[3], 0.5), lerp(up[7], low[7], 0.5)], MINW, 'key', rng, wob=0.3, a0=1.0, a1=3.0)
    for hp in (L, R_):
        knock_ell(hp[0], hp[1], 0.03 * u, 0.026 * u)
        ln(ell(hp[0], hp[1], 0.026 * u, 0.022 * u, n=10, rng=rng), MINW, 'key', rng)
    # drizzle beading on the jacket: drips from its hem and the sleeve
    for p in (low[2], low[5], low[8], sleeve[3]):
        ln([(p[0], p[1] + 4), (p[0], p[1] + rng.uniform(8, 13))], MINW, 'key', rng, wob=0.05)
        dot(p[0], p[1] + rng.uniform(17, 22), MINW * 0.62, 'key', rng)
    return J1, J2


# ============================================================ the scene
def scene():
    # ---------- lamps first (they light the trees). Near pair, a mid pair, far heads with a few dots each
    lamp_draws = []
    couple_bb = (110, 1000, 340, 1140)
    friends_bb = (770, 1010, 1030, 1160)
    for x, z, kw in ((-5.3, 13.0, dict(h=7.3, arm=2.7, pool=(2.3, 3.2), canopy=None, tops=[couple_bb])),
                     (-5.1, 33.0, dict(pool=(1.3, 2.0), cone=0.55, kpool=0.8, head=1.25)),
                     (-5.1, 56.0, dict(pool=(1.0, 1.6), cone=0.0, kpool=0.62, head=1.25)),
                     (5.1, 11.0, dict(h=7.1, arm=1.6, pool=(2.0, 2.5), canopy=None, tops=[friends_bb])),
                     (5.1, 35.0, dict(pool=(1.3, 2.0), cone=0.55, kpool=0.8, head=1.25)),
                     (5.1, 58.0, dict(pool=(1.0, 1.6), cone=0.0, kpool=0.62, head=1.25))):
        d = street_lamp4(x, z, rng, **kw)
        lamp_draws.append((z + (0.01 if x > 0 else 0), d))
    log('lamps')

    # ---------- the far Green Line runs on behind the stage to Madavara (drawn first: the stage hides it)
    rng.seed(SEED + 3)
    for z0_, z1_ in ((58, 72), (72, 86), (86, 104), (104, 130)):
        via_span(z0_, z1_, rng)
    # ---------- BIEC: the long low exhibition halls beyond the left of the stage
    rng.seed(SEED + 4)
    hall = [(286, 560), (286, 493), (414, 489), (414, 560)]
    knock(hall, 0.6)
    ln([hall[1], hall[2]], MINW * 1.2, 'key', rng)
    ln([(288, 501), (412, 497)], MINW, 'key', rng)
    for t in [i / 7 for i in range(1, 7)]:
        ln([lerp(hall[0], hall[3], t), lerp(hall[1], hall[2], t)], MINW, 'key', rng, wob=0.05, a0=0.5, a1=0.8)
    # ---------- the show at the end of the street: a DJ set
    ST = stage_dj3(rng)
    # delay towers and the FOH tent in the crowd, then the crowd
    for xd, top in ((376, 520), (748, 516)):
        knock_line([(xd, 604), (xd, top)], 6)
        ln([(xd, 604), (xd, top)], MINW * 1.1, 'key', rng, wob=0.03)
        bx = [(xd - 7, top), (xd - 7, top + 17), (xd + 7, top + 17), (xd + 7, top)]
        knock(bx, 0.6)
        pline(bx, MINW, 'key', rng)
        ln([(xd - 7, top + 8.5), (xd + 7, top + 8.5)], MINW, 'key', rng)
    crowd_dj4(rng, 340, 800, 588, 612)
    tc = (500, 610)
    tent_ = [(tc[0] - 14, tc[1]), (tc[0] - 14, tc[1] - 13), (tc[0], tc[1] - 21), (tc[0] + 14, tc[1] - 13), (tc[0] + 14, tc[1])]
    knock(grow(tent_, 2), 0.6)
    pline(tent_, MINW * 1.1, 'key', rng, closed=False)
    fillp([(tc[0] - 11, tc[1] - 11), (tc[0] + 11, tc[1] - 11), (tc[0] + 11, tc[1] - 6), (tc[0] - 11, tc[1] - 6)], 'amber')
    ln([(342, 615), (798, 615)], MINW * 1.2, 'key', rng, wob=0.05)     # barricade
    # the show doubled in the road: one column under the screen, widening toward us
    sxw = ground_of(ST['xc'], 615)
    light(sxw[0] if sxw else -1.2, 8.5, 204, 'ice', wm=0.0, k=1.0, stretch=3.8, brk=0.08, core='key')
    LIGHTS[-1]['cw'], LIGHTS[-1]['cw1'], LIGHTS[-1]['y1'], LIGHTS[-1]['dens'] = 38.0, 80.0, 1440, 0.95
    log('show')

    # ---------- the road (marks on the ground; everything standing knocks it)
    rng.seed(SEED + 5)
    road(rng)
    # round 12's puddles: broken ripple rings in the lamp-lit wet, on the near road and round the auto
    for (x, z, rx, rz) in ((-1.6, 10.6, 1.5, 0.8), (1.9, 15.5, 1.3, 0.6), (-2.9, 23.5, 1.6, 0.7), (0.8, 31, 1.4, 0.6)):
        puddle(x, z, rx, rz, rng, rings=2)
    for (x, z, rx, rz, ink) in ((-2.0, 9.1, 1.2, 0.5, 'amber'), (0.5, 8.3, 1.0, 0.4, 'ice'), (2.3, 9.7, 1.1, 0.5, 'amber')):
        puddle(x, z, rx, rz, rng, ink=ink, rings=3)
    # no ripple rings: any ring on the road reads as the halo the owner threw out; the drops are told by splashes

    # ---------- everything that stands, far to near
    items = []
    def add(z, fn):
        items.append((z, len(items), fn))

    # left flank
    add(31.0, lambda: brushed(brewery2, ('amber', 'copper'))(rng))
    add(35.0, lambda: bungalow(rng))
    add(47.0, lambda: building(-1, 7.9, 47, 60, 13.2, rng, lit=0.07, tanks=2, end_wall=True, balconies=0.35))
    add(60.5, lambda: building(-1, 7.9, 60.5, 74, 10.0, rng, lit=0.05, tanks=1, end_wall=False))
    add(74.5, lambda: building(-1, 7.9, 74.5, 92, 15.5, rng, lit=0.06, tanks=2, end_wall=True))
    # right flank: low shops, then the row behind
    add(14.0, lambda: (building(1, 9.0, 14, 26, 7.0, rng, lit=0.15, tanks=1, end_wall=False, awning=(19.6, 21.6, 'green'),
                                sign=0.0), atm_box(1, 9.0, 22.4, 24.4, rng)))
    add(26.2, lambda: building(1, 9.0, 26.2, 33.5, 6.6, rng, ground='glass', lit=0.4, tanks=1, end_wall=True, sign=0.0))
    add(36.0, lambda: building(1, 19.0, 36, 51, 11.0, rng, lit=0.06, tanks=2, end_wall=True))
    add(51.5, lambda: building(1, 19.0, 51.5, 66, 8.5, rng, lit=0.05, tanks=1, end_wall=False))
    add(66.5, lambda: building(1, 19.0, 66.5, 90, 12.0, rng, lit=0.06, tanks=2, end_wall=True))
    # the Green Line: one tall single pier with a T-cap, the straight girder, the last train
    add(59.9, lambda: pier3(60.0, rng))
    for z0_, z1_ in ((24, 36), (36, 45), (45, 58)):
        add(z0_, (lambda z0_=z0_, z1_=z1_: via_span(z0_, z1_, rng)))
    add(44.9, lambda: train_nose(rng))
    # trees: the tunnel. far trunks at their depth, the crowns over everything below them
    add(48.0, lambda: far_trunk(7.0, 48, rng, [([pr(6.2, 6.5, 48), pr(4.6, 8.0, 48)], 0, 0)], d=1.1))
    add(33.2, lambda: far_trunk(-6.9, 33.2, rng, [([pr(-5.9, 5.8, 33.2), (330, 468)], 0, 0), ([pr(-7.8, 6.0, 33.2), (262, 476)], 0, 0)], d=1.15))
    add(22.5, lambda: far_trunk(7.1, 22.5, rng, [([pr(6.2, 5.8, 22.5), (958, 430)], 0, 0), ([pr(8.0, 6.2, 22.5), (1040, 470)], 0, 0)]))
    add(35.9, lambda: crown3([cl(*c) for c in FAR_LEFT], rng, sc=0.8))
    add(47.9, lambda: crown3([cl(*c) for c in FAR_RIGHT], rng, sc=0.75))
    add(12.8, lambda: near_right_tree(rng))
    add(12.6, lambda: near_left_tree(rng))
    add(12.4, lambda: crown3([cl(*c) for c in RIGHT_CROWN], rng))
    add(12.3, lambda: crown3([cl(*c) for c in LEFT_CROWN], rng))
    for z, d in lamp_draws:
        add(12.25 if z < 20 else z, d)     # the near lamps hang just under the leaves: their heads read over the crowns
    add(11.2, lambda: post_clock2(-5.25, 11.2, rng))

    # small stories on the right pavement
    def chai():
        chai_stall(6.05, 15.4, rng, k=1.3)
        cw = pr(6.55, 0, 15.7)
        figure(cw[0], cw[1], 1.6 * S(15.7), rng, facing='front', arms=('hold', 'glass'), top='shirt', tcol='ice',
               hair='short', band=False, beard=True)
    add(15.45, chai)
    for k_, (x, z, f, arms, col, hair) in enumerate(((5.3, 16.6, 'right', ('glass', 'swing'), 'copper', 'short'),
                                                     (5.2, 14.3, 'right', ('fold', 'glass'), 'green', 'long'),
                                                     (4.75, 15.5, 'front', ('glass', 'phone'), None, 'cap'))):
        def cust(x=x, z=z, f=f, arms=arms, col=col, hair=hair):
            g = pr(x, 0, z)
            J = figure(g[0], g[1], 1.68 * S(z), rng, facing=f, arms=arms, tcol=col, hair=hair, band=True, stride=0.1)
            for k, m in enumerate(arms):
                if m == 'glass':
                    glass(*J['hands'][k], J['u'], rng)
        add(min(z, 15.3 - 0.01 * k_), cust)
    add(23.2, lambda: plastic_chair_guard(8.2, 23.2, rng))
    def dog():
        p = pr(8.3, 0, 20.4)
        dog_curled(p[0], p[1] - 0.12 * S(20.4), 0.85 * S(20.4), rng)
    add(20.4, dog)
    # parked autos, drivers asleep across the back seat
    add(34.6, lambda: auto3(4.0, 34.6, math.pi + 0.05, rng, driver=True, phone=True, lights=False, light_side=1))
    add(31.2, lambda: auto3(4.05, 31.2, math.pi - 0.03, rng, driver=False, sleeper=True, lights=False, light_side=1))
    add(27.8, lambda: auto3(4.0, 27.8, math.pi + 0.02, rng, driver=False, lights=False, light_side=1))
    add(24.4, lambda: auto3(4.1, 24.4, math.pi - 0.04, rng, driver=False, sleeper=True, lights=False, light_side=1))

    # brewery pavement: people outside with glasses
    for (x, z, f, arms, col, hair) in ((-6.4, 16.5, 'right', ('glass', 'swing'), 'green', 'long'),
                                       (-5.9, 17.2, 'left', ('swing', 'glass'), 'ice', 'short'),
                                       (-6.6, 19.8, 'front', ('glass', 'out'), 'copper', 'bun'),
                                       (-6.1, 21.3, 'right', ('fold', 'swing'), None, 'cap'),
                                       (-6.5, 23.6, 'front', ('glass', 'phone'), 'amber', 'curly')):
        def bp(x=x, z=z, f=f, arms=arms, col=col, hair=hair):
            g = pr(x, 0, z)
            J = figure(g[0], g[1], 1.7 * S(z), rng, facing=f, arms=arms, tcol=col, hair=hair, band=True, stride=0.05,
                       laugh=rng.random() < 0.5)
            for k, m in enumerate(arms):
                if m == 'glass':
                    glass(*J['hands'][k], J['u'], rng)
        add(z, bp)

    # traffic: the last cab, a car home, a poncho scooter, a delivery rider
    add(44.0, lambda: car(1.9, 44, math.pi, rng, lights=True, plate='yellow'))
    add(33.0, lambda: car(-2.2, 33, 0.02, rng, lights=True, plate='key'))
    add(21.0, lambda: two_wheeler(-1.3, 21, False, rng, poncho='green'))
    add(25.0, lambda: two_wheeler(1.4, 25, True, rng, poncho='ice', box=True))
    # an auto pulling out past the couple, its open side and the driver toward us
    add(12.3, lambda: auto3(-2.3, 12.3, 0.42, rng, driver=True, lights=True, wave=False, light_side=-1))

    # people walking back from the show
    crowd_rng = random.Random(SEED + 7)
    for i in range(17):
        z = 45 + (i / 17) ** 0.9 * 42 + crowd_rng.uniform(-1.5, 1.5)
        x = crowd_rng.uniform(-4.6, 3.2)
        if z < 50 and 1.0 < x < 2.8:
            x -= 2.5
        umb = crowd_rng.choice(('green', 'ice', 'copper', 'ice', 'green', None, None, None))
        def walker(x=x, z=z, umb=umb, seed=crowd_rng.randint(0, 10 ** 6)):
            r2 = random.Random(seed)
            if z > 52:
                far_person(x, z, r2, umb=umb)
            else:
                g = pr(x, 0, z)
                small_person(g[0], g[1], 1.7 * S(z), r2, facing=r2.choice(('front', 'front', 'front', 'left', 'right')), umb=umb)
        add(z, walker)
    for (x, z) in ((-6.0, 28), (-6.6, 30.5), (6.2, 30), (-5.8, 42), (6.0, 34.5), (-6.4, 47)):
        def pw(x=x, z=z, seed=crowd_rng.randint(0, 10 ** 6)):
            r2 = random.Random(seed)
            g = pr(x, 0, z)
            small_person(g[0], g[1], 1.7 * S(z), r2, umb=r2.choice((None, 'green', None)))
        add(z, pw)

    # stories in the crowd coming home: a girl on her friend's shoulders, three singing into their phones
    def shoulders(x=-0.9, z=38.5):
        g_ = pr(x, 0, z)
        u_ = 1.72 * S(z)
        J = figure(g_[0], g_[1], u_, rng, facing='front', stride=0.3, arms=('hold', 'hold'), top='tee', tcol='green',
                   hair='short', band=True)
        nk = J['neck']
        figure(nk[0], nk[1] + 0.33 * u_, 0.8 * u_, rng, facing='front', stride=0.0, arms=('up', (2.4, 2.9)), top='top',
               tcol='amber', bottom='jeans', hair='long', band=True, laugh=True, face_up=True, shoes=True)
    add(38.5, shoulders)
    for k, (x, z) in enumerate(((1.9, 41.0), (2.4, 41.6), (2.95, 40.7))):
        def singer(x=x, z=z, k=k):
            g_ = pr(x, 0, z)
            figure(g_[0], g_[1], 1.7 * S(z), rng, facing='front', stride=0.25,
                   arms=(('phone', 'up') if k != 1 else ('around', 'phone')), top=('tee', 'hoodie', 'kurta')[k],
                   tcol=('ice', None, 'copper')[k], hair=('curly', 'short', 'bun')[k], band=True, laugh=True,
                   face_up=k == 1, phone_lit=True)
        add(z, singer)

    # the couple and the friends, nearest
    add(9.6, lambda: couple_r12(rng))
    add(8.7, lambda: friends(rng))

    items.sort(key=lambda t: (-t[0], t[1]))
    for z, idx, fn in items:
        rng.seed(SEED * 31 + idx)
        fn()
    log('standing things')

    # ---------- every light doubled in the wet road: one column under each, its own width
    rng.seed(SEED + 11)
    nref = reflect_brush(LIGHTS, rng)
    lay_reflections()
    log('reflections: %d of %d lights' % (nref, len(LIGHTS)))

    # ---------- drizzle: one slant, long fine strokes, only where light is behind it (no halftone dots any more)
    rng.seed(SEED + 12)
    drizzle_cones2(rng)
    from lib_city import quadw
    drizzle_glass(quadw(-1, 7.8, 15.6, 30.5, 0.4, 6.2), rng, sp=30.0, L=(18, 40))
    log('drizzle')

    # ---------- the sky last: the round-2 cloud deck (curling echo strokes, now blue) and the fan of white beams,
    # drawn on scratch layers and laid only on black that nothing else claims
    rng.seed(SEED + 13)
    keepL, keepD = A.L, A.D
    A.L = {k: Image.new('L', (W, H), 0) for k in ORDER}
    A.D = {k: ImageDraw.Draw(v) for k, v in A.L.items()}
    _cm = lib_city.cloud_mass
    lib_city.cloud_mass = lambda *a, **k: _cm(*a, **dict(k, ink='blue'))
    try:
        X0, X1, ty = ST['truss']
        roots = [lerp((430, 384), (700, 384), (i + 0.5) / 7) for i in range(7)]
        angs = [-0.52, -0.22, 0.0, 0.09, 0.2, 0.41, 0.63]
        bdefs = []
        for p, a in zip(roots, angs):
            L = (p[1] - 250) / math.cos(a) * rng.uniform(0.9, 1.05)
            bdefs.append((p, a + rng.gauss(0, 0.02), L))
        bpolys = [beam_poly(p, a, L, L * 0.055)[0] for p, a, L in bdefs]
        # round 2's deck of long bellies, its rows lifted to sit in the sky that shows above this stage roof
        for yb, lobe, nr, sp in ((382, (16, 26), 2, 10.0), (356, (22, 34), 2, 11.0), (326, (30, 46), 3, 12.5),
                                 (294, (40, 62), 3, 14.0)):
            x = 190 + rng.uniform(0, 50)
            while x < 1010:
                L = rng.uniform(150, 280)
                if pip(x + L / 2, yb, grow(OPEN, 30)):
                    top = min(nr * sp + 14, yb - TITLE[3] - 16)
                    if top > 10:
                        lib_city.cloud_mass(x, x + L, yb + rng.uniform(-6, 6), rng, beams=bpolys, lobe=lobe, rows=nr,
                                            sp=sp, top=top)
                x += L * rng.uniform(0.7, 0.95)
        for p, a, L in bdefs:
            beam(p, a, L, rng, clip_y=252)
    finally:
        lib_city.cloud_mass = _cm
        T = A.L
        A.L, A.D = keepL, keepD
    reg = Image.new('L', (W, H), 0)
    ImageDraw.Draw(reg).rectangle((60 * R, 243 * R, 1140 * R, 640 * R), fill=255)
    lay_sky(T, rng, region=reg)
    log('sky')


# ============================================================ where the drawing exists
def edge_mask():
    """ragged edge of the whole drawing, with the title and line zones left clean"""
    sc = 2
    w, h = W // (R * sc) if R >= 1 else W, H // (R * sc)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32) * sc + sc / 2
    left = 34 + 7 * np.sin(ys / 61 + 0.4) + 4 * np.sin(ys / 19 + 1.2)
    right = 1166 - 7 * np.sin(ys / 57 + 2.1) - 4 * np.sin(ys / 23)
    top = 36 + 6 * np.sin(xs / 49 + 0.3) + 3 * np.sin(xs / 17)
    bot = 1470 + 8 * np.sin(xs / 43 + 0.9) + 4 * np.sin(xs / 13 + 2.0)
    m = (xs > left) & (xs < right) & (ys > top) & (ys < bot)
    # title: a rounded, slightly ragged pocket
    tx0, ty0, tx1, ty1 = TITLE
    cxt, cyt = (tx0 + tx1) / 2, (ty0 + ty1) / 2
    hx, hy = (tx1 - tx0) / 2 + 10, (ty1 - ty0) / 2 + 10
    dx = np.maximum(np.abs(xs - cxt) - (hx - 30), 0)
    dy = np.maximum(np.abs(ys - cyt) - (hy - 30), 0)
    rr = np.sqrt(dx * dx + dy * dy) + 2.5 * np.sin(xs / 11 + ys / 13)
    m &= ~(rr < 30)
    lx0, ly0, lx1, ly1 = LINEZ
    m &= ~((xs > lx0 - 12) & (xs < lx1 + 12) & (ys > ly0 - 14))
    img = Image.fromarray((m * 255).astype(np.uint8), 'L').resize((W, H), Image.NEAREST)
    return img


# ============================================================ manifest
def to_u(p):
    return [int(round(p[0])), int(round(p[1]))]


def manifest(path):
    show = (559.0, 540.0)                 # the small DJ at his booth, hand up, in front of the LED screen
    clock = pr(-5.25, 3.45, 11.2)
    jacket = pr(-3.9, 2.05, 9.6)
    chai = pr(6.05, 1.5, 15.4)
    train = pr(tx(TF), 12.9 + lib_show.LIFT, TF)
    tree = pr(-6.3, 3.0, 12.0)
    ann = [
        {"text": "always 22° somewhere", "x": 60, "y": 640, "rotation": -4, "points_to": to_u(clock)},
        {"text": "one jacket, two people", "x": 60, "y": 1300, "rotation": -4, "points_to": to_u(jacket)},
        {"text": "chai's still on", "x": 1015, "y": 1000, "rotation": 2, "points_to": to_u(chai)},
        {"text": "last train from madavara", "x": 870, "y": 300, "rotation": -3, "points_to": to_u(train)},
        {"text": "nice grounds, one man at a table", "x": 250, "y": 600, "rotation": -2, "points_to": to_u(show)},
        {"text": "rain trees don't mind", "x": 1010, "y": 560, "rotation": 5, "points_to": to_u(pr(7.3, 4.0, 14.0))},
    ]
    m = {
        "concept": "22°: Bengaluru at 1:42 a.m., after Fred again.. at NICE Grounds, in the soft drizzle the city is "
                   "known for. From a footbridge you look down a wet street (Church Street, 100 Feet Road and MG Road folded "
                   "into one) roofed by huge old rain trees. At the end of it the set is still going: a DJ stage under a pale "
                   "sheet roof on a box truss, line arrays hung each side, one small figure at a booth at the front with one "
                   "hand up, soft grainy footage on the LED screen behind him, a crowd of heads, hands and phones in front, five thin white beams "
                   "fanning up into a low night-blue cloud deck drawn in curling echo strokes. The street lamps' light on the "
                   "ground is only their reflections and a little warm wet shine; the drizzle shows as one slant of long fine "
                   "strokes where light is behind it. Shutters are down, a post clock on its stand says 1:42, the chai stall still steams, autos wait, a "
                   "guard dozes, the last Green Line train comes in from Madavara, and a couple hold one jacket over their "
                   "laughing heads as an auto pulls out past them. Each light lays one column in the road, at its own place "
                   "and width, and a few broken puddles hold the light near the viewer.",
        "medium": "hand-drawn white-line ink on black with misregistered spot screens: pressure-pen contours, continuous "
                  "hatching for tone, woodblock-style echo scallops for the rain-tree canopies, clouds as curling echo strokes "
                  "stepping up from round bellies (ice where the beams pass), white beams as segmented "
                  "strokes cutting their own black slots, colour fills laid as directional brush strokes. Light is never a "
                  "glow, a ring or a dot pool. Drizzle is one slant of long fine strokes only where light is behind it; "
                  "reflections are one broken column per light of stacked tapered horizontal strokes, plus broken puddles. DTG on a black tee, binary alpha, every mark >= 1 mm.",
        "palette": PAL,
        "type_zones": [{"name": "title", "x": TITLE[0], "y": TITLE[1], "w": TITLE[2] - TITLE[0], "h": TITLE[3] - TITLE[1]},
                       {"name": "line", "x": LINEZ[0], "y": LINEZ[1], "w": LINEZ[2] - LINEZ[0], "h": LINEZ[3] - LINEZ[1]}],
        "annotations": ann,
        "focal_point": to_u(show),
    }
    json.dump(m, open(path, 'w'), indent=2, ensure_ascii=False)
    return m


if __name__ == '__main__':
    scene()
    full = R >= 2.5
    tag = '' if full else '-draft'
    render(os.path.join(HERE, 'art-black%s.png' % tag), os.path.join(HERE, 'preview-black%s.png' % tag), mask=edge_mask())
    manifest(os.path.join(HERE, 'manifest.json'))
    log('done')
