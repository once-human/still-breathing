"""22° : 1:42 a.m., Bengaluru, after the Fred again.. show, in a soft drizzle under the rain trees.

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
lib_city.wash = lambda *a, **k: None    # REVIEW-1: no amber wash on the facades

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
LEFT_CROWN = [(105, 86, 112, 46), (112, 186, 108, 44), (92, 290, 134, 50), (305, 306, 112, 42), (190, 396, 152, 52),
              (385, 420, 82, 32), (58, 470, 100, 42), (232, 490, 124, 44), (108, 550, 92, 36)]
RIGHT_CROWN = [(1110, 86, 100, 44), (1092, 190, 110, 46), (1122, 292, 120, 48), (935, 300, 112, 40),
               (1052, 386, 124, 46), (1152, 470, 80, 36), (1022, 466, 72, 32)]
FAR_LEFT = [(392, 404, 46, 29), (440, 438, 38, 24), (352, 452, 42, 26)]
FAR_RIGHT = [(838, 512, 36, 22), (880, 486, 42, 26)]


def near_left_tree(rng):
    """the old rain tree at the near left: flared buttressed trunk, three twisting limbs, the heavy low crown"""
    limb3([(132, 790), (108, 700), (70, 612), (28, 540), (-10, 500)], 74, 40, rng, lit=0.4)
    limb3([(140, 780), (150, 680), (166, 580), (190, 500)], 64, 26, rng, lit=0.6)
    limb3([(150, 790), (196, 712), (238, 628), (262, 548), (296, 470)], 72, 24, rng, lit=0.85)
    trunk3([(92, 1172), (98, 1060), (108, 950), (124, 850), (140, 776)], [205, 152, 126, 114, 108], rng, lit_side=1,
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
def couple(rng):
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


def friends(rng):
    """three friends walking back toward us arm in arm: one with her face turned up to the drizzle, one with a hand out
    to feel it, one swinging a furled umbrella"""
    out = []
    spec = [(1.75, 9.0, dict(facing='front', arms=('hold', 'swing'), top='tee', tcol='green', hair='bun', face_up=True)),
            (2.32, 8.8, dict(facing='front', arms=('pocket', (1.15, 1.9)), top='hoodie', tcol=None, hair='short', laugh=True,
                             beard=True)),
            (2.95, 9.05, dict(facing='front', arms=((1.5, 1.7), 'out'), top='kurta', tcol='ice', hair='long'))]
    for x, z, kw in spec:
        g = pr(x, 0, z)
        J = figure(g[0], g[1], 1.7 * S(z), rng, stride=0.4, band=True, **kw)
        out.append(J)
    J = out[0]
    umbrella_closed(J['hands'][0][0], J['hands'][0][1], J['u'], rng, col='ice', ang=0.2)
    # the open hand: a few drops landing on the palm
    hx, hy = out[2]['hands'][-1]
    for k in range(3):
        dx = rng.uniform(-14, 14)
        ln([(hx + dx, hy - 34 - k * 9), (hx + dx + 3, hy - 22 - k * 9)], MINW, 'key', rng, wob=0.05)
    return out


# ============================================================ the scene
def scene():
    # ---------- lamps first (they light the trees). Near pair with big drizzle cones, a mid pair, far heads only
    lamp_draws = []
    for x, z, dn, cone in ((-5.1, 14.0, 1.0, True), (-5.1, 33.0, 0.32, True), (-5.1, 56.0, 0, False),
                           (5.1, 11.0, 1.0, True), (5.1, 35.0, 0.32, True), (5.1, 58.0, 0, False)):
        d = street_lamp2(x, z, rng, dens=dn if cone else 0.0, rings=3 if z < 20 else 2 if cone else 1)
        lamp_draws.append((z + (0.01 if x > 0 else 0), d))
    log('lamps')

    # ---------- sky: four low clouds lit from below, five unequal white beams cutting up through them
    zf = SHOW_Z - 5
    xl_, xr_ = SHOW_X - 15.0, SHOW_X + 15.0
    rp = lambda t: lerp(SP(xl_, 17.6, zf - 0.5), SP(xr_, 17.6, zf - 0.5), t)
    bdefs = [(rp(0.08), -0.58, 20), (rp(0.3), -0.24, 30), (rp(0.5), 0.04, 13), (rp(0.68), 0.27, 34), (rp(0.95), 0.6, 18)]
    beams_ = []
    for p, a_, we in bdefs:
        L = (p[1] - 252) / math.cos(a_)
        ux, uy = math.sin(a_), -math.cos(a_)
        nx, ny = -uy, ux
        end = (p[0] + ux * L, p[1] + uy * L)
        poly = [(p[0] + nx * 2, p[1] + ny * 2), (end[0] + nx * we, end[1] + ny * we), (end[0] - nx * we, end[1] - ny * we),
                (p[0] - nx * 2, p[1] - ny * 2)]
        beams_.append((p, a_, L, we, poly))
    clouds = [(432, 356, 176, 72), (552, 302, 170, 60), (530, 404, 112, 36)]
    cpolys = []
    for cx_, yb_, w_, h_ in clouds:
        cpolys.append(cloud_body2(cx_, yb_, w_, h_, rng, beams=[b_[4] for b_ in beams_]))
    for cp in cpolys:
        for p, a_, L, we, poly in beams_:
            beam_cloud_light(cp, poly, a_, rng)
    for p, a_, L, we, poly in beams_:
        beam2(p, a_, L, we, rng, clip_y=252, core_w=2.4 if we > 25 else 1.9)
    log('sky')

    # ---------- the show at the end of the street
    rng.seed(SEED + 4)
    show3(rng)
    crowd3(rng)
    log('show')

    # ---------- the road (marks on the ground; everything standing knocks it)
    rng.seed(SEED + 5)
    road(rng)
    for (x, z, rx, rz) in ((-1.6, 10.6, 1.5, 0.8), (1.9, 15.5, 1.3, 0.6), (-2.9, 23.5, 1.6, 0.7), (0.8, 31, 1.4, 0.6)):
        puddle(x, z, rx, rz, rng, rings=2)
    # near puddles where the drizzle lands: rings in the lamp-lit wet, readable from across a room
    for (x, z, rx, rz, ink) in ((-2.0, 9.1, 1.2, 0.5, 'amber'), (0.5, 8.3, 1.0, 0.4, 'ice'), (2.3, 9.7, 1.1, 0.5, 'amber')):
        puddle(x, z, rx, rz, rng, ink=ink, rings=3)

    # ---------- everything that stands, far to near
    items = []
    def add(z, fn):
        items.append((z, len(items), fn))

    # left flank
    add(31.0, lambda: brewery(rng))
    add(35.0, lambda: bungalow(rng))
    add(47.0, lambda: building(-1, 7.9, 47, 60, 13.2, rng, lit=0.07, tanks=2, end_wall=True, balconies=0.35))
    add(60.5, lambda: building(-1, 7.9, 60.5, 74, 10.0, rng, lit=0.05, tanks=1, end_wall=False))
    add(74.5, lambda: building(-1, 7.9, 74.5, 92, 15.5, rng, lit=0.06, tanks=2, end_wall=True))
    # right flank: low shops under the curve of the viaduct, then the row behind it
    add(14.0, lambda: (building(1, 9.0, 14, 26, 7.0, rng, lit=0.15, tanks=1, end_wall=False, awning=(19.6, 21.6, 'green'),
                                sign=0.0), atm_box(1, 9.0, 22.4, 24.4, rng)))
    add(26.2, lambda: building(1, 9.0, 26.2, 33.5, 6.6, rng, ground='glass', lit=0.4, tanks=1, end_wall=True, sign=0.0))
    add(36.0, lambda: building(1, 19.0, 36, 51, 11.0, rng, lit=0.06, tanks=2, end_wall=True))
    add(51.5, lambda: building(1, 19.0, 51.5, 66, 8.5, rng, lit=0.05, tanks=1, end_wall=False))
    add(66.5, lambda: building(1, 19.0, 66.5, 90, 12.0, rng, lit=0.06, tanks=2, end_wall=True))
    # the Green Line: piers, girder spans, the station, the last train
    for zp in (30, 45, 60, 76, 94):
        add(zp - 0.1, (lambda zp=zp: pier2(zp, rng)))
    for z0_, z1_ in ((15, 30), (30, 45), (45, 60), (60, 76), (76, 94), (94, 115), (115, 140)):
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
    add(11.2, lambda: post_clock(-5.25, 11.2, rng))

    # small stories on the right pavement
    def chai():
        chai_stall(6.05, 15.4, rng)
        cw = pr(6.5, 0, 15.5)
        figure(cw[0], cw[1], 1.6 * S(15.5), rng, facing='front', arms=('hold', 'glass'), top='shirt', tcol='ice',
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
    add(34.5, lambda: auto_rickshaw(4.0, 34.5, math.pi + 0.04, rng, driver=False, sleeper=False, lights=False))
    add(30.5, lambda: auto_rickshaw(4.0, 30.5, math.pi - 0.03, rng, driver=False, sleeper=True, lights=False))
    add(26.5, lambda: auto_rickshaw(4.05, 26.5, math.pi + 0.02, rng, driver=False, sleeper=True, lights=False))

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
    # the auto pulling up for the couple
    add(12.3, lambda: auto_rickshaw(-2.45, 12.3, 0.1, rng, driver=True, lights=True))

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
    add(9.6, lambda: couple(rng))
    add(8.7, lambda: friends(rng))

    items.sort(key=lambda t: (-t[0], t[1]))
    for z, idx, fn in items:
        rng.seed(SEED * 31 + idx)
        fn()
    log('standing things')

    # ---------- every light doubled in the wet road
    chosen = pick_reflections(LIGHTS, keep=0.62)
    log('reflections: %d of %d lights' % (len(chosen), len(LIGHTS)))
    for L in chosen:
        reflect2(L, rng)
    lay_reflections()
    log('reflections')


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
    show = pr(SHOW_X, 9 + gl(SHOW_Z), SHOW_Z)
    clock = pr(-5.25, 3.45, 11.2)
    jacket = pr(-3.9, 2.05, 9.6)
    chai = pr(6.05, 1.5, 15.4)
    train = pr(tx(TF), 12.9, TF)
    tree = pr(-6.3, 3.0, 12.0)
    ann = [
        {"text": "1:42, soft rain", "x": 60, "y": 640, "rotation": -4, "points_to": to_u(clock)},
        {"text": "one jacket, two people", "x": 60, "y": 1300, "rotation": -4, "points_to": to_u(jacket)},
        {"text": "chai's still on", "x": 1015, "y": 1000, "rotation": 2, "points_to": to_u(chai)},
        {"text": "last train from madavara", "x": 870, "y": 300, "rotation": -3, "points_to": to_u(train)},
        {"text": "nice grounds, 12 + 13 dec", "x": 250, "y": 600, "rotation": -2, "points_to": to_u(show)},
        {"text": "rain trees don't mind", "x": 1010, "y": 560, "rotation": 5, "points_to": to_u(pr(7.3, 4.0, 14.0))},
    ]
    m = {
        "concept": "22°: Bengaluru at 1:42 a.m., after the Fred again.. show at NICE Grounds, in the soft drizzle the city "
                   "is known for. From a footbridge you look down a wet street (Church Street, 100 Feet Road and MG Road "
                   "folded into one) roofed by huge old rain trees whose leaf masses are lit amber from below by the street "
                   "lamps. Drizzle shows only in the lamp light and in the show's white beams, which climb into low clouds "
                   "warmed by the city. Shutters are down, a post clock says 1:42, the chai stall still steams, autos wait "
                   "with their drivers asleep, a guard dozes, a dog sleeps under an awning, the last Green Line train comes "
                   "in from Madavara, and a couple share one jacket over their heads as an auto pulls up. Every light is "
                   "doubled in the road.",
        "medium": "hand-drawn white-line ink on black with misregistered spot screens: pressure-pen contours, continuous "
                  "hatching for tone, woodblock-style echo scallops for the rain-tree canopies and the cloud bellies, flat "
                  "light shapes with broken halo rings (never glows), drizzle strokes only inside lamp cones and beams, "
                  "reflections as stacked tapered brush strokes. DTG on a black tee, binary alpha, every mark >= 1 mm.",
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
