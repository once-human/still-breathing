"""lib_r13.py: round 13, after the owner saw it. Lamps that visibly light the street (bigger heads, cones, pools on the
wet ground), every light reflected again as long stroke columns, the show's white river on the road, a proper Bengaluru
auto (short body, one domed yellow hood, green body, black rear curtain), blue low clouds cut by the white beams."""
from kit import *
from lib_life import *
from lib_v3 import *


# ============================================================ LAMPS that light the street
def sheen_pool(cx, z, rxm, rzm, rng, ink='amber', k=1.0, art=None):
    """the pool of lamp light on the wet ground: stacked tapered horizontal strokes, packed under the lamp and breaking
    up toward the rim (laid with the reflections, so whatever stands in it hides it)"""
    art = art or RA
    c = pr(cx, 0, z)
    xa, xb = pr(cx - rxm, 0, z)[0], pr(cx + rxm, 0, z)[0]
    ya, yb = pr(cx, 0, z + rzm)[1], pr(cx, 0, z - rzm)[1]
    rx_s = (xb - xa) / 2
    y = ya
    th = clamp(rx_s * 0.05, MINW, 5.2)
    while y < yb:
        v = (y - c[1]) / ((yb - ya) / 2)
        half = rx_s * math.sqrt(max(0.0, 1 - v * v))
        if half > MINW * 2:
            n = rng.choice((1, 2, 2, 3))
            for _ in range(n):
                f = k * (1 - abs(v) ** 1.6)
                if rng.random() > 0.15 + 0.85 * f:
                    continue
                hl = half * rng.uniform(0.25, 0.7) * (0.6 + 0.4 * f)
                xc = c[0] + rng.uniform(-1, 1) * (half - hl) * 0.9
                if hl < th:
                    continue
                pts = [(xc - hl, y + rng.gauss(0, 0.4)), (xc, y + rng.gauss(0, th * 0.3)), (xc + hl, y + rng.gauss(0, 0.4))]
                art.line(pts, th * rng.uniform(0.9, 1.25), layer=ink, rng=rng, wob=0.3, trem=0.15, a0=1.6, a1=2.6, pv=0.3)
        y += th * rng.uniform(1.75, 2.2)


def street_lamp3(x, z, rng, h=8.2, arm=1.8, dens=1.0, rings=3, r_ft=2.6, pool_m=(1.0, 0.75), head=1.5):
    """a street lamp that does its job: a big lit head with a cream core, a dashed cone of drizzle to the ground and an
    amber pool of wet light where the cone lands; its reflection column starts in the pool"""
    side = -1 if x < 0 else 1
    hx = x - side * arm
    LAMPS.append((hx, h - 0.3, z))
    light(hx, h - 0.3, z, 'amber', wm=0.75, k=1.15, core='key')

    def draw():
        s = S(z)
        g, t = pr(x, 0, z), pr(x, h + 0.15, z)
        w = clamp(0.15 * s, MINW, 6.5)
        knock_line([g, t], w + 3)
        edge(g, t, w, 'key', rng, over=(-0.5, 0.5))
        a0, a1, hd = pr(x, h + 0.1, z), pr(x - side * arm * 0.5, h + 0.5, z), pr(hx, h, z)
        ln([a0, a1, hd], max(MINW, w * 0.8), 'key', rng, wob=0.2)
        hw = clamp(0.55 * s * head, 8, 46)
        hh = clamp(0.16 * s * head, 4.5, 14)
        cx, cy = hd
        house = [(cx - hw, cy - hh * 0.2), (cx - hw * 0.6, cy - hh), (cx + hw * 0.6, cy - hh), (cx + hw, cy - hh * 0.2),
                 (cx + hw * 0.7, cy + hh * 0.55), (cx - hw * 0.7, cy + hh * 0.55)]
        r0 = clamp(1.0 * s, 11, 52) * (1.0 if s > 50 else 0.75)
        if s > 24:
            knock_ell(cx, cy + hh * 0.3, r0 * 1.25, r0 * 1.12)
        knock(house, 1.0)
        lens = [(cx - hw * 0.86, cy), (cx + hw * 0.86, cy), (cx + hw * 0.6, cy + hh * 1.05), (cx - hw * 0.6, cy + hh * 1.05)]
        fillp(lens, 'amber')
        # the hot core of the lamp: cream
        knock_ell(cx, cy + hh * 0.45, hw * 0.5, hh * 0.42, layers=('amber',))
        A.D['key'].ellipse(((cx - hw * 0.44) * R, (cy + hh * 0.45 - hh * 0.34) * R, (cx + hw * 0.44) * R,
                            (cy + hh * 0.45 + hh * 0.34) * R), fill=255)
        pline(house[:4], max(MINW, w * 0.7), 'key', rng, closed=False)
        for k in range(rings if s > 50 else min(rings, 1)):
            rr = r0 * (1 + 0.55 * k) * rng.uniform(0.95, 1.05)
            a = rng.uniform(0, TAU)
            end = a + TAU * rng.uniform(0.7, 0.85)
            dash = rng.uniform(0.28, 0.45) * (1 - 0.2 * k)
            while a < end:
                pts = ell(cx, cy + hh * 0.3, rr, rr * 0.92, n=max(3, int(dash * rr / 6)), a0=a, a1=a + dash, rng=rng)
                knock_line(pts, MINW * 2.4)
                A.line(pts, MINW * (1.15 - 0.1 * k), layer='amber', rng=rng, wob=0.2, trem=0.1, a0=1.0, a1=1.8, pv=0.2)
                a += dash + rng.uniform(0.18, 0.32) * (1 + 0.4 * k)
        # the cone: two broken edges falling from the lens to the ground, drizzle only inside
        foot = [pr(hx - r_ft, 0, z), pr(hx + r_ft, 0, z)]
        apex = (cx, cy + hh)
        poly = [(apex[0] - hw * 0.7, apex[1]), (apex[0] + hw * 0.7, apex[1]), foot[1], foot[0]]
        if dens > 0:
            for p0, p1 in ((poly[0], poly[3]), (poly[1], poly[2])):
                L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
                tt = rng.uniform(0.04, 0.1)
                while tt < 0.62:
                    dl = rng.uniform(0.05, 0.1)
                    q0, q1 = lerp(p0, p1, tt), lerp(p0, p1, min(0.66, tt + dl))
                    if L * dl > 8:
                        A.line([q0, q1], MINW * (1.15 - 0.6 * tt), layer='amber', rng=rng, wob=0.1, trem=0.0, a0=0.8,
                               a1=1.4, pv=0.1)
                    tt += dl + rng.uniform(0.04, 0.08) * (1 + 2 * tt)
            Lc = max(1, foot[0][1] - apex[1])
            half = abs(foot[1][0] - foot[0][0]) * 0.5 + 1

            def fade(px, py):
                v = (py - apex[1]) / Lc
                lat = abs(px - apex[0]) / (hw * 0.7 + (half - hw * 0.7) * clamp(v, 0, 1) + 1)
                return clamp(1.05 - v * 2.1, 0, 1) * clamp((1.02 - lat) * 5, 0, 1)
            sp_ = clamp(0.42 * s, 15.0, 22)
            drizzle_dark(poly, 'amber', rng, sp=sp_, L=(clamp(0.32 * s, 11, 18), clamp(0.6 * s, 16, 30)), ang=RAIN,
                         fade=fade, prob=dens, w=DRW)
        if pool_m:
            sheen_pool(hx, z, pool_m[0], pool_m[1], rng, 'amber', k=1.0)
    return draw


# ============================================================ REFLECTIONS: every light, long, with a core
def reflect_all(lights, rng, ymax=1458, lo=1.6, hi=2.4):
    n = 0
    for L in lights:
        gx, gy = pr(L['x'], 0, L['z'])
        mx, my = pr(L['x'], -L['h'], L['z'])
        if gy > ymax - 10:
            continue
        base = clamp(L['wm'] * S(L['z']), 5.0, 46.0)
        length = (my - gy) * rng.uniform(lo, hi) * min(1.6, L.get('stretch', 1.0)) + base
        y0 = gy + clamp(0.06 * S(L['z']), 1.0, 8.0)
        core = L.get('core') or ('key' if L['ink'] in ('amber', 'ice') and base > 9 else None)
        reflect_column(gx, y0, y0 + length, base, L['ink'], rng, core=core, k=L['k'], ymax=ymax,
                       brk=min(0.16, L.get('brk', 0.16)))
        n += 1
    return n


def show_river(rng, x0=600, y0=612, y1=1440):
    """the show's white light doubled down the middle of the street: broad broken columns of fat tapered strokes,
    white and ice, widening toward us (perspective), wobbling apart and back together"""
    cols = [(-92, 14, 'ice'), (-50, 26, 'ice'), (-12, 34, 'key'), (28, 28, 'ice'), (68, 20, 'key'), (104, 12, 'ice')]
    for dx, base, ink in cols:
        ph, ph2 = rng.uniform(0, TAU), rng.uniform(0, TAU)
        y = y0 + rng.uniform(0, 25)
        yend = y1 - rng.uniform(0, 50)
        span = yend - y
        while y < yend:
            t = (y - y0) / span
            persp = 0.35 + 1.0 * t
            th = clamp((2.6 + 3.2 * t) * (base / 26) ** 0.4, MINW, 6.2) * rng.uniform(0.9, 1.15)
            hl = base * persp * rng.uniform(0.4, 1.15)
            cx = x0 + dx * (0.45 + 0.75 * t) + base * 0.5 * (0.6 * math.sin(y * 0.03 + ph) + 0.4 * math.sin(y * 0.083 + ph2))
            if rng.random() > 0.1 + 0.25 * t and hl > th:
                pts = [(cx - hl, y + rng.gauss(0, 0.5)), (cx + rng.uniform(-0.2, 0.2) * hl, y + rng.gauss(0, th * 0.3)),
                       (cx + hl, y + rng.gauss(0, 0.5))]
                RA.line(pts, th, layer=ink, rng=rng, wob=0.3, trem=0.15, a0=1.6, a1=2.6, pv=0.3)
            y += (th + MINW * 1.15) * rng.uniform(1.0, 1.3) * (1 + 0.35 * t)


# ============================================================ THE AUTO, rebuilt
HOOD = [(-0.66, 0.98), (-0.66, 1.5), (-0.63, 1.68), (-0.52, 1.79), (-0.26, 1.85), (0.0, 1.86), (0.26, 1.85), (0.52, 1.79),
        (0.63, 1.68), (0.66, 1.5), (0.66, 0.98)]


def auto3(x, z, yaw, rng, driver=True, sleeper=False, phone=False, lights=True, wave=False, light_side=-1):
    """a Bengaluru auto: short Bajaj body, one domed yellow canvas hood with a wet crown highlight, black rear curtain
    with a small window, green body, copper tail lamps, yellow plate, two rear wheels, one front wheel under a
    mudguard. yaw 0 = driving away from us."""
    pos = (x, 0, z)
    s = S(z)
    w = clamp(0.034 * s, MINW, 4.6)
    T = lambda p: pr(*xf(p, pos, yaw))
    zb, zf = 0.06, 1.95
    fw = 0.92                                     # the hood narrows a little toward the front

    def hp(i, zz):
        x_, y_ = HOOD[i]
        f = 1 + (fw - 1) * (zz - zb) / (zf - zb)
        return (x_ * f, y_ if i in (0, len(HOOD) - 1) else 0.98 + (y_ - 0.98) * (1 - 0.06 * (zz - zb) / (zf - zb)), zz)

    # wheels first (the body covers their tops)
    def wheel(wx, wz_, r, side_):
        nw = xn((side_, 0, 0), yaw)
        pw = [xf((wx, 0.24 + math.sin(a) * r, wz_ + math.cos(a) * r), pos, yaw) for a in [TAU * i / 16 for i in range(16)]]
        sp = [pr(*p) for p in pw]
        knock(sp, 0.6)
        ok, _ = vis(pw, nw)
        lowh = [sp[i % 16] for i in range(8, 17)]           # the lower half: the tyre on the wet road
        ln(lowh, w, 'key', rng, wob=0.1)
        if ok:
            c = T((wx, 0.24, wz_))
            ln(ell(c[0], c[1], r * s * 0.45, r * s * 0.45, n=10, rng=rng), MINW, 'key', rng)
    for sx in (-1, 1):
        wheel(sx * 0.69, 0.42, 0.24, sx)
    wheel(0.0, 2.36, 0.22, 1)

    faces = []
    G = 'green'
    faces.append(([(-0.66, 0.3, 0), (0.66, 0.3, 0), (0.66, 0.96, 0), (-0.66, 0.96, 0)], (0, 0, -1), G, 'all'))
    for sx in (-1, 1):
        box = [(sx * 0.66, 0.3, 0), (sx * 0.66, 0.96, 0), (sx * 0.66, 0.96, 0.78), (sx * 0.66, 0.3, 0.78)]
        sill = [(sx * 0.64, 0.3, 0.78), (sx * 0.64, 0.64, 0.78), (sx * 0.52, 0.7, 2.0), (sx * 0.5, 0.3, 2.02)]
        cow = [(sx * 0.5, 0.3, 2.0), (sx * 0.5, 1.06, 2.0), (sx * 0.3, 1.01, 2.52), (sx * 0.3, 0.3, 2.55)]
        faces.append((box, (sx, 0, 0), G, 'all'))
        faces.append((sill, (sx, 0, 0), G, [1, 2]))
        faces.append((cow, (sx * 0.93, 0, 0.37), G, [0, 1, 2]))
        # canvas side behind the passengers
        side = [(sx * 0.66, 0.97, zb), (sx * 0.66, 0.97, 0.66), (sx * 0.65, 1.48, 0.66), (sx * 0.65, 1.48, zb)]
        faces.append((side, (sx, 0, 0), 'yellow', [1]))
    faces.append(([(-0.3, 0.3, 2.55), (0.3, 0.3, 2.55), (0.3, 1.01, 2.52), (-0.3, 1.01, 2.52)], (0, 0.1, 1), G, 'all'))
    faces.append(([(-0.5, 1.06, 2.0), (0.5, 1.06, 2.0), (0.3, 1.01, 2.52), (-0.3, 1.01, 2.52)], (0, 1, 0.1), G, [1, 2, 3]))
    faces.append(([(-0.5, 1.06, 2.0), (0.5, 1.06, 2.0), (0.55, 1.62, zf - 0.04), (-0.55, 1.62, zf - 0.04)], (0, 0.25, 1),
                  None, 'all'))
    # the hood: a dome in strips (no edges between them), the rear curtain, the front visor
    n = len(HOOD)
    for i in range(1, n - 2):
        a, b = HOOD[i], HOOD[i + 1]
        nrm = (-(b[1] - a[1]), (b[0] - a[0]), 0)
        faces.append(([hp(i, zb), hp(i + 1, zb), hp(i + 1, zf), hp(i, zf)], nrm, 'yellow', None))
    curtain = [hp(i, zb) for i in range(n)]
    faces.append((curtain, (0, 0, -1), 'yellow', None))
    visor = [hp(i, zf) for i in range(1, n - 1)] + [(0.6 * fw, 1.58, zf), (-0.6 * fw, 1.58, zf)]
    faces.append((visor, (0, 0, 1), 'yellow', None))
    pw_all = []
    for f in faces:
        pw_all += [pr(*xf(p, pos, yaw)) for p in f[0]]
    draw_faces(faces, pos, yaw, rng, w)

    camz_rel = (0 - z) * math.cos(yaw) - (0 - x) * math.sin(yaw)
    see_back = camz_rel < 0
    camx_rel = (0 - x) * math.cos(yaw) + (0 - z) * math.sin(yaw)
    sd = 1 if camx_rel > 0 else -1                      # the side we see
    # the hood's outline, firm: back arch, front arch, the two shoulders
    back_arch = [T(hp(i, zb)) for i in range(1, n - 1)]
    front_arch = [T(hp(i, zf)) for i in range(1, n - 1)]
    ln(front_arch, w * 1.1, 'key', rng, wob=0.15)
    for i in (1, n - 2):
        ln([T(hp(i, zb)), T(hp(i, (zb + zf) / 2)), T(hp(i, zf))], w * (1.1 if (i == 1) == (sd < 0) else 0.9), 'key',
           rng, wob=0.15)
    # dome: short carved strokes on the flank away from the light, following the curve
    # dome: one long carved line along the shaded flank, parallel to the shoulder, so the top reads round
    si = 2 if light_side > 0 else n - 3
    fl = [T(hp(si, zz)) for zz in (zb + 0.15, (zb + zf) / 2, zf - 0.12)]
    if s > 40 and math.hypot(fl[2][0] - fl[0][0], fl[2][1] - fl[0][1]) > 12:
        carve(fl, MINW * 1.05, 'yellow', rng)
    # the wet crown: a long broken ice highlight, black-edged so it reads on the yellow
    cs = 0.1 * light_side
    for z0_, z1_ in ((zb + 0.18, zb + 0.75), (zb + 0.95, zf - 0.25)):
        g0, g1 = T((cs, 1.905, z0_)), T((cs * 1.2, 1.9, z1_))
        if s > 40 and math.hypot(g1[0] - g0[0], g1[1] - g0[1]) > 7:
            knock_line([g0, g1], MINW * 2.3)
            ln([g0, g1], MINW * 1.05, 'ice', rng, wob=0.05, a0=0.8, a1=1.4)
    if see_back:
        ln(back_arch, w * 1.15, 'key', rng, wob=0.15, redraw=0.3)
        # the curtain: a black lower flap, the canvas roll seam, the small rear window
        flap = [T(p) for p in [(-0.66, 0.98, zb - 0.01), (0.66, 0.98, zb - 0.01), (0.66, 1.12, zb - 0.01), (-0.66, 1.12, zb - 0.01)]]
        knock(flap, 0.2, layers=('yellow',))
        inner = [T((HOOD[i][0] * 0.9, 0.98 + (HOOD[i][1] - 0.98) * 0.9, zb - 0.005)) for i in range(2, n - 2)]
        carve(inner, MINW, 'yellow', rng)
        rw = [T(p) for p in [(-0.27, 1.3, zb - 0.01), (0.27, 1.3, zb - 0.01), (0.25, 1.52, zb - 0.01), (-0.25, 1.52, zb - 0.01)]]
        knock(rw, 0.8, layers=('yellow',))
        pline(rw, max(MINW, w * 0.8), 'key', rng)
        g0, g1 = lerp(rw[0], rw[3], 0.3), lerp(rw[1], rw[2], 0.75)
        if math.hypot(g1[0] - g0[0], g1[1] - g0[1]) > 10:
            ln([lerp(g0, g1, 0.15), lerp(g0, g1, 0.45)], MINW, 'ice', rng, wob=0.05)
        # tail lamps, plate, bumper
        for sx_ in (-1, 1):
            tl = [T(p) for p in [(sx_ * 0.6, 0.6, -0.01), (sx_ * 0.42, 0.6, -0.01), (sx_ * 0.42, 0.8, -0.01), (sx_ * 0.6, 0.8, -0.01)]]
            knock(tl, 0.3)
            fillp(tl, 'copper')
            if lights:
                p3 = xf((sx_ * 0.51, 0.7, 0), pos, yaw)
                light(p3[0], 0.7, p3[2], 'copper', wm=0.2, k=1.0)
        pl = [T(p) for p in [(-0.21, 0.38, -0.01), (0.21, 0.38, -0.01), (0.21, 0.53, -0.01), (-0.21, 0.53, -0.01)]]
        knock(pl, 0.3)
        fillp(pl, 'yellow')
        pline(pl, MINW, 'key', rng, skip=0.3)
        ln([T((-0.7, 0.32, -0.04)), T((0.7, 0.32, -0.04))], w * 0.9, 'key', rng)
    else:
        hl = T((0, 0.86, 2.56))
        r = clamp(0.1 * s, 2.4, 7)
        knock_ell(hl[0], hl[1], r + 1.5, r + 1.5)
        dot(hl[0], hl[1], r, 'ice', rng)
        if lights:
            light(*xf((0, 0.86, 2.56), pos, yaw), 'ice', wm=0.2, k=0.9, core='key')
    # mudguard over the front wheel (seen from the side)
    mg = [T((0.0, 0.24 + math.sin(a) * 0.3, 2.36 + math.cos(a) * 0.3)) for a in [math.pi * (0.15 + 0.7 * i / 8) for i in range(9)]]
    if abs(math.sin(yaw)) > 0.2:
        ln(mg, max(MINW, w * 0.9), 'key', rng, wob=0.1)
    # the open side we see: the seat, the grab rail, the dark inside
    rail = [T((sd * 0.64, 1.42, zz)) for zz in (0.7, 1.2, 1.8)]
    ln(rail, MINW, 'key', rng, wob=0.1)
    seat = [T((sd * 0.5, yy, zz)) for zz, yy in ((0.72, 1.4), (0.74, 0.86), (1.25, 0.84))]
    ln(seat, max(MINW, w * 0.8), 'key', rng, wob=0.12)
    out = {'sil': pw_all}
    if driver:
        hd = T((0.02, 1.36, 1.72))
        hr = clamp(0.11 * s, 3.4, 12)
        if not see_back:
            knock_ell(hd[0], hd[1], hr * 1.15, hr * 1.3)
            ln(ell(hd[0], hd[1], hr, hr * 1.2, n=12, a0=0.3, a1=TAU - 0.5, rng=rng), MINW, 'key', rng)
        sh = T((sd * 0.2, 1.16, 1.72))
        if wave:
            el, hn = T((-sd * 0.7, 1.05, 1.78)), T((-sd * 1.08, 1.24, 1.7))
            knock_line([sh, el, hn], max(MINW, 0.11 * s) + 3)
            ln([sh, el, hn], max(MINW, 0.1 * s), 'key', rng, wob=0.1)
            knock_ell(hn[0], hn[1], 0.08 * s, 0.07 * s)
            # an open palm: four short fingers and a thumb
            for k_ in range(4):
                a_ = -1.9 + 0.28 * k_ * sd
                ln([hn, (hn[0] - math.cos(a_) * 0.1 * s * sd, hn[1] + math.sin(a_) * 0.11 * s)], MINW, 'key', rng, wob=0.05)
            ln([hn, (hn[0] + sd * 0.07 * s, hn[1] - 0.02 * s)], MINW, 'key', rng, wob=0.05)
        else:
            hb = T((sd * 0.3, 1.02, 2.1))
            ln([sh, ((sh[0] + hb[0]) / 2, sh[1] + hr * 0.6), hb], MINW, 'key', rng)
        if phone:
            ph = T((sd * 0.15, 1.3, 1.95))
            knock_ell(ph[0], ph[1], 0.09 * s, 0.1 * s)
            fillp([(ph[0] - 0.045 * s, ph[1] - 0.07 * s), (ph[0] + 0.045 * s, ph[1] - 0.07 * s),
                   (ph[0] + 0.045 * s, ph[1] + 0.07 * s), (ph[0] - 0.045 * s, ph[1] + 0.07 * s)], 'ice')
    if sleeper:
        f0, f1 = T((sd * 0.6, 0.98, 0.85)), T((sd * 0.98, 0.9, 0.9))
        f3, f2 = T((sd * 0.6, 0.96, 1.15)), T((sd * 0.98, 0.88, 1.1))
        for a_, b_ in ((f0, f1), (f3, f2)):
            ln([a_, b_], max(MINW, 0.07 * s), 'key', rng)
            dot(b_[0], b_[1], max(2.0, 0.06 * s), 'key', rng)
        ln([T((sd * 0.45, 1.06, 0.5)), T((sd * 0.6, 1.1, 1.3))], max(MINW, 0.05 * s), 'copper', rng)
    return out


# ============================================================ BLUE low clouds, cut by the white beams
def cloud_blue(cx, yb, wdt, hgt, rng, beams=(), ymin=246):
    """a low night cloud as a flat cobalt shape: lobed top with a broken cream rim, a firm belly, carved seams where one
    lobe sits on another and a few carved strata; the beams cut clean black slots through it"""
    nl = rng.randint(3, 5)
    lobes = []
    for k in range(nl):
        f = (k + 0.5) / nl + rng.uniform(-0.06, 0.06)
        lr = wdt / nl * rng.uniform(0.62, 0.85)
        ly = yb - hgt * (0.5 + 0.5 * math.sin(math.pi * f)) * rng.uniform(0.82, 1.0) + lr * 0.55
        lobes.append((cx - wdt / 2 + wdt * f, ly, lr))
    xs = [cx - wdt / 2 + wdt * i / 60 for i in range(61)]
    top = []
    for xx in xs:
        best = None
        for lx, ly, lr in lobes:
            dx = xx - lx
            if abs(dx) < lr:
                y = ly - math.sqrt(lr * lr - dx * dx) * 0.78
                best = y if best is None else min(best, y)
        if best is None:
            best = yb - 6
        top.append((xx, max(ymin, min(best, yb - 6))))
    base = [(xx, yb + 3.5 * math.sin(i * 0.5 + cx) + hgt * 0.1 * math.sin(math.pi * i / 60)) for i, xx in enumerate(xs)]
    poly = top + base[::-1]
    knock(grow(poly, 4.0), 0)
    blob(poly, 'blue', rng, gap=0.0, shift=1.2, jit=0.015, n=90)
    for bp in beams:
        knock(grow(bp, 3.5), 0, layers=('blue',))
    # carved seams and strata
    for lx, ly, lr in lobes[1:]:
        if rng.random() < 0.8:
            arc = ell(lx, ly, lr * 0.85, lr * 0.62, n=10, a0=math.pi * 1.08, a1=math.pi * 1.6, rng=rng)
            arc = [p for p in arc if pip(p[0], p[1], grow(poly, -4))]
            if len(arc) > 2:
                carve(arc, MINW, 'blue', rng)
    for k in range(rng.randint(2, 3)):
        yy = yb - hgt * rng.uniform(0.12, 0.4)
        xa = cx - wdt * rng.uniform(0.1, 0.42)
        xb = xa + wdt * rng.uniform(0.18, 0.4)
        pts = [(xa + (xb - xa) * t, yy + 2 * math.sin(t * 5)) for t in (0, 0.33, 0.66, 1)]
        if all(pip(p[0], p[1], grow(poly, -5)) for p in pts):
            carve(pts, MINW, 'blue', rng)
    i = rng.randint(0, 4)
    while i < len(top) - 2:
        L = rng.randint(6, 14)
        if rng.random() < 0.8:
            ln(top[i:i + L], MINW * 1.1, 'key', rng, wob=0.15, a0=1.0, a1=2.0)
        i += L + rng.randint(1, 4)
    i = rng.randint(0, 3)
    while i < len(base) - 2:
        L = rng.randint(10, 20)
        if rng.random() < 0.6:
            ln(base[i:i + L], MINW, 'ice', rng, wob=0.15, a0=1.0, a1=2.0)
        i += L + rng.randint(2, 5)
    return poly


# ============================================================ THE BREWERY, rebuilt so it reads past the trunk
def brewery2(rng, z0=15.0, z1=31.0, X=7.8):
    """a Bengaluru microbrewery: double-height glass on a mullion grid, three big copper tanks with domed tops, pipes
    and a catwalk, drinkers at the bar against the warm light, a terrace with string lights and people at the rail,
    warm light spilling onto the wet pavement"""
    from lib_city import quadw, F, string_lights, silhouette_person, brew_tank
    side = -1
    x = -X
    HG, HP = 6.4, 7.3
    q = quadw(side, X, z0, z1, 0, HP)
    knock(q, 1.0)
    s0 = S(z0)
    gq = quadw(side, X, z0 + 0.5, z1 - 0.4, 0.25, HG)
    blob(gq, 'amber', rng, gap=0.0, shift=0.5, jit=0.01)
    # the back wall: dark shelves of kegs (black bands knocked out of the light), high up
    for yy in (4.9, 5.6):
        knock_line([F(side, X + 3.4, z0 + 0.8, yy), F(side, X + 3.4, z1 - 0.6, yy)], MINW * 1.3, layers=('amber',))
    # drinkers at the bar: black silhouettes against the amber, behind the tanks' line
    zz = z1 - 1.4
    while zz > z0 + 1.2:
        p = F(side, X + 1.1, zz, 0.35)
        hh = 1.3 * S(zz)
        silhouette_person(p[0], p[1], hh, ('amber', 'copper'), rng, glass_hand=rng.random() < 0.6)
        zz -= rng.uniform(1.5, 2.3)
    edge(F(side, X + 0.9, z0 + 1.0, 1.1), F(side, X + 0.9, z1 - 0.8, 1.1), MINW * 1.3, 'key', rng)
    # three copper tanks standing in the light, far to near
    tz = (z1 - 0.6, z1 - 3.9, z1 - 7.2)
    for zt in tz:
        c = pr(x - 2.6, 3.0, zt)
        knock_ell(c[0], c[1], 1.35 * S(zt), 3.0 * S(zt), layers=('amber',))
        brew_tank(x - 2.6, zt, rng, r=1.0, y0=0.4, y1=5.3)
    # pipes from dome to dome and the catwalk in front of the tanks
    for i in range(len(tz) - 1):
        a, b = pr(x - 2.6, 5.75, tz[i]), pr(x - 2.6, 5.75, tz[i + 1])
        knock_line([a, b], MINW * 3.2, layers=('amber', 'copper'))
        ln([a, b], MINW * 1.1, 'key', rng, wob=0.08)
    za, zb_ = tz[-1] - 1.4, tz[0] + 0.6
    for yy, wv in ((3.7, 1.3), (4.6, 1.0)):
        a, b = pr(x - 1.25, yy, za), pr(x - 1.25, yy, zb_)
        knock_line([a, b], MINW * wv + 4.0, layers=('amber', 'copper'))
        ln([a, b], MINW * wv, 'key', rng, wob=0.06)
    zz = za + 0.4
    while zz < zb_:
        a, b = pr(x - 1.25, 3.7, zz), pr(x - 1.25, 4.6, zz)
        knock_line([a, b], MINW + 3.0, layers=('amber', 'copper'))
        ln([a, b], MINW, 'key', rng, wob=0.05)
        zz += 1.5
    # pendant lamps over the bar
    zz = z0 + 2.0
    while zz < z1 - 1:
        top, bulb = F(side, X + 0.6, zz, HG), F(side, X + 0.6, zz, 5.9)
        knock_line([top, bulb], MINW + 2, layers=('amber', 'copper'))
        ln([top, bulb], MINW, 'key', rng, wob=0.05)
        r = clamp(0.24 * S(zz), 3.4, 9)
        bell = ell(bulb[0], bulb[1] + r * 0.6, r * 1.5, r, n=10, a0=math.pi, a1=TAU, rng=rng)
        knock(bell + [bell[0]], 0.8, layers=('amber', 'copper'))
        fillp(bell, 'key')
        zz += 3.4
    # the glass: a mullion grid (verticals and two transoms), firm, knocked clear of the light
    zz = z0 + 0.5
    while zz <= z1 - 0.3:
        a, b = F(side, X, zz, 0.2), F(side, X, zz, HP - 0.5)
        wv = clamp(0.085 * S(zz), MINW, 6)
        knock_line([a, b], wv + 3.0, layers=('amber', 'copper', 'green', 'ice'))
        edge(a, b, wv, 'key', rng, over=(0, 0.6))
        zz += 3.2
    for yy in (2.9, HG - 0.9):
        a, b = F(side, X, z0 + 0.5, yy), F(side, X, z1 - 0.4, yy)
        knock_line([a, b], MINW + 3.0, layers=('amber', 'copper', 'ice'))
        edge(a, b, MINW * 1.05, 'key', rng)
    edge(F(side, X, z0 + 0.5, 0.2), F(side, X, z1 - 0.4, 0.2), clamp(0.07 * s0, MINW, 5), 'key', rng)
    edge(F(side, X, z0 + 0.5, HG), F(side, X, z1 - 0.4, HG), clamp(0.07 * s0, MINW, 5), 'key', rng)
    # open door: warm light spills onto the wet pavement
    light(x + 0.3, 2.2, z0 + 1.2, 'amber', wm=1.2, k=1.1, core='key')
    light(x + 0.3, 3.0, z1 - 4, 'amber', wm=1.4, k=0.9)
    sheen_pool(x + 1.6, z0 + 2.4, 1.3, 1.6, rng, 'amber', k=0.9)
    # ----- terrace: parapet, people at the rail, posts, swags of big bulbs
    pz = [z0 + 2.2, z0 + 5.2, z0 + 8.6, z0 + 12.0]
    for k_, zp in enumerate(pz):
        fx_, fy_ = F(side, X + 0.5, zp, HG + 0.2)
        hgt = 1.7 * S(zp)
        figure(fx_, fy_, hgt, rng, facing=('right', 'front', 'right', 'front')[k_], stride=0.0,
               arms=(('glass', 'swing'), ('fold', 'fold'), ('up', 'swing'), ('swing', 'glass'))[k_],
               tcol=('copper', 'green', 'ice', None)[k_], hair=('short', 'long', 'bun', 'curly')[k_], band=False,
               shoes=False)
    par = quadw(side, X, z0, z1, HG + 0.05, HP)
    knock(par, 0.5)
    edge(F(side, X, z0, HP), F(side, X, z1, HP), clamp(0.08 * s0, MINW, 6), 'key', rng)
    edge(F(side, X, z0, HG + 0.05), F(side, X, z1, HG + 0.05), MINW * 1.2, 'key', rng)
    edge(F(side, X, z0, 0), F(side, X, z0, HP), clamp(0.085 * s0, MINW, 6.5), 'key', rng)
    posts = [z0 + 0.4, z0 + 6.0, z0 + 11.0, z1 - 0.4]
    for zp in posts:
        ln([F(side, X + 0.3, zp, HP), F(side, X + 0.3, zp, 9.4)], clamp(0.07 * S(zp), MINW, 5), 'key', rng)
    for i in range(len(posts) - 1):
        a, b = F(side, X + 0.3, posts[i], 9.3), F(side, X + 0.3, posts[i + 1], 9.3)
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(3, int(L / 20))
        pts = [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t + 0.35 * S(posts[i]) * 4 * t * (1 - t))
               for t in [j / n for j in range(n + 1)]]
        ln(pts, MINW, 'key', rng, wob=0.1, a0=0.4, a1=0.6)
        for p in pts[1:-1]:
            r = clamp(0.09 * S(posts[i]), 2.6, 4.6)
            knock_ell(p[0], p[1] + r + 1.5, r + 1.8, r * 1.15 + 1.8, layers=('key', 'green', 'copper'))
            dot(p[0], p[1] + r + 1.5, r, 'amber', rng)
        LAMPS.append((x - 0.3, 9.0, (posts[i] + posts[i + 1]) / 2))
    return q


# ============================================================ THE BLUE CLOUD, drawn in strata like the water below
def cloud_strata(cx, yb, wdt, hgt, rng, beams=(), ymin=250, dens=1.0, rim=True):
    """a low cloud over the show as stacked tapered horizontal strokes in blue (the same hand as the reflections, so
    sky and street rhyme): dense in the belly, breaking up toward the lobed top, so the lobes are made by where the
    strokes stop. Inside a beam the strata are lit (ice), so the light reads as hitting the cloud; a broken cream rim
    on the highest lobes and a broken ice belly where the city lights it from under."""
    nl = rng.randint(4, 6)
    lobes = []
    for k in range(nl):
        f = (k + 0.5) / nl + rng.uniform(-0.05, 0.05)
        lr = wdt / nl * rng.uniform(0.7, 0.95)
        ly = yb - hgt * (0.45 + 0.55 * math.sin(math.pi * f)) * rng.uniform(0.85, 1.0) + lr * 0.55
        lobes.append((cx - wdt / 2 + wdt * f, ly, lr))

    def top_at(xx):
        best = None
        for lx, ly, lr in lobes:
            dx = xx - lx
            if abs(dx) < lr:
                y = ly - math.sqrt(lr * lr - dx * dx) * 0.78
                best = y if best is None else min(best, y)
        return None if best is None else max(ymin, min(best, yb - 8))

    def base_at(xx):
        return yb + 3.0 * math.sin(xx * 0.05 + cx) + 5 * math.sin(math.pi * (xx - cx + wdt / 2) / wdt)

    bpolys = []
    for root, ang, L, we in beams:
        ux, uy = math.sin(ang), -math.cos(ang)
        nx, ny = -uy, ux
        end = (root[0] + ux * L, root[1] + uy * L)
        hw = we * 0.38 + 3
        bpolys.append([(root[0] + nx * 3, root[1] + ny * 3), (end[0] + nx * hw, end[1] + ny * hw),
                       (end[0] - nx * hw, end[1] - ny * hw), (root[0] - nx * 3, root[1] - ny * 3)])
    th = MINW * 1.65
    xs = [cx - wdt / 2 + wdt * i / 80 for i in range(81)]
    top = [(xx, top_at(xx)) for xx in xs]
    top = [(x_, y_) for x_, y_ in top if y_ is not None]
    poly = top + [(xx, base_at(xx)) for xx in xs[::-1]]
    knock(grow(poly, 2.0), 0, layers=('green', 'amber', 'yellow', 'copper', 'blue'))
    y = min(p[1] for p in top) + th * 0.6
    while y < yb + 6:
        x = cx - wdt / 2 + rng.uniform(0, 14)
        while x < cx + wdt / 2:
            Ls = rng.uniform(26, 80)
            xa, xb = x, x + Ls
            xm = (xa + xb) / 2
            ta, tb, tm = top_at(xa), top_at(xb), top_at(xm)
            ok = all(t_ is not None and y > t_ + th * 0.4 and y < base_at(xx_) for t_, xx_ in ((ta, xa), (tb, xb), (tm, xm)))
            if ok:
                depth = (y - tm) / max(1.0, base_at(xm) - tm)      # 0 at the top of the lobe, 1 at the belly
                if rng.random() < dens * (0.66 + 0.6 * depth):
                    lit = any(pip(xm, y, bp) for bp in bpolys)
                    ink = 'ice' if lit else 'blue'
                    w = th * rng.uniform(0.9, 1.2) * (1.12 if depth > 0.6 else 1.0)
                    A.line([(xa, y + rng.gauss(0, 0.5)), (xm, y + rng.gauss(0, 0.9)), (xb, y + rng.gauss(0, 0.5))], w,
                           layer=ink, rng=rng, wob=0.3, trem=0.15, a0=1.6, a1=2.6, pv=0.3)
            x = xb + rng.uniform(4, 11)
        y += th * rng.uniform(1.65, 1.85)
    if rim:
        i = rng.randint(0, 4)
        while i < len(top) - 2:
            L = rng.randint(5, 12)
            seg = [(p[0], p[1] - 1) for p in top[i:i + L]]
            if rng.random() < 0.6 and all(p[1] > ymin + 2 for p in seg):
                ln(seg, MINW * 1.05, 'key', rng, wob=0.15, a0=1.0, a1=2.0)
            i += L + rng.randint(2, 6)
    i = rng.randint(0, 3)
    bl = [(xx, base_at(xx) + 4) for xx in xs]
    while i < len(bl) - 2:
        L = rng.randint(8, 18)
        if rng.random() < 0.55:
            ln(bl[i:i + L], MINW, 'ice', rng, wob=0.15, a0=1.0, a1=2.0)
        i += L + rng.randint(3, 7)
    return poly
