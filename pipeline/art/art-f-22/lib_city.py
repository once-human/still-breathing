"""lib_city.py: buildings, the brewery, the bungalow, small stories (chai stall, guard), the Namma Metro viaduct and
train, the show at NICE Grounds, clouds and beams, the wet road"""
from kit import *
from lib_life import *


# ============================================================ BUILDINGS
def F(side, X, zz, yy):
    return pr(side * X, yy, zz)


def quadw(side, X, z0, z1, y0, y1):
    return [F(side, X, z0, y0), F(side, X, z0, y1), F(side, X, z1, y1), F(side, X, z1, y0)]


def wash(side, X, z0, z1, y0, rng, ymax=4.0):
    """the street lamps warming the face of a building: vertical strokes rising from the shop line, as tall as the lamp
    light is strong"""
    zz = z0 + 0.3
    while zz < z1 - 0.3:
        s = S(zz)
        lit = lamp_lit(side * X, y0 + 1.5, zz, r=8.5)
        if lit > 0.3 and rng.random() < 0.35:
            top = y0 + ymax * lit * rng.uniform(0.6, 1.1)
            a, b = F(side, X, zz, y0 + rng.uniform(0, 0.3)), F(side, X, zz, top)
            if b[1] < a[1] - MINW * 2:
                ln([a, lerp(a, b, 0.5), b], MINW, 'amber', rng, wob=0.2, a0=0.8, a1=3.5)
        zz += max(0.25, 10.5 / s) * rng.uniform(0.85, 1.2)


def window(side, X, z0, z1, y0, y1, rng, lit=False, grille=False, figure_in=False, balcony=False, ac=False, curtain=None):
    q = quadw(side, X, z0, z1, y0, y1)
    wpx = abs(q[2][0] - q[1][0])
    if wpx < 4.5 or abs(q[0][1] - q[1][1]) < 7:
        return
    knock(q, 0.5)
    w = MINW
    if lit:
        blob(grow(q, -0.8), 'amber', rng, gap=0.0, shift=0.6)
        if wpx > 14:
            carve_rain(q, ('amber',), rng, sp=11.0, L=(6, 11))
        if figure_in and wpx > 10:
            # someone up late: a head and shoulders against the lamp inside
            cx_ = (q[1][0] + q[2][0]) / 2 + rng.uniform(-0.2, 0.2) * wpx
            by = (q[0][1] + q[3][1]) / 2
            hh = abs(q[0][1] - q[1][1])
            hr = clamp(hh * 0.12, 2.2, 8)
            sh = [(cx_ - hr * 2.2, by), (cx_ - hr * 1.6, by - hh * 0.38), (cx_ + hr * 1.6, by - hh * 0.38), (cx_ + hr * 2.2, by)]
            knock(sh, 0, layers=('amber',))
            knock_ell(cx_, by - hh * 0.38 - hr * 1.1, hr, hr * 1.2, layers=('amber',))
        if curtain:
            m = lerp(q[1], q[2], rng.uniform(0.3, 0.7))
            knock_line([m, (m[0], (q[0][1] + q[3][1]) / 2)], MINW * 1.2, layers=('amber',))
        pline(q, w, 'key', rng, skip=0.2)
    else:
        if rng.random() < 0.45:
            return                                          # most dark windows are just dark
        edge(q[0], q[3], w * 1.1, 'key', rng)               # sill
        if rng.random() < 0.7:
            edge(q[1], q[2], w, 'key', rng)                 # lintel
        if rng.random() < 0.5:
            edge(q[0], q[1], w, 'key', rng)
        if grille and wpx > 9:
            nb = int(wpx / 7)
            for i in range(1, nb):
                t = i / nb
                ln([lerp(q[0], q[3], t), lerp(q[1], q[2], t)], MINW, 'key', rng, wob=0.1)
    if balcony:
        yb = y0 - 0.85
        qb0, qb1 = F(side, X - 0.9, z0 - 0.4, yb + 1.0), F(side, X - 0.9, z1 + 0.4, yb + 1.0)
        qb2, qb3 = F(side, X - 0.9, z0 - 0.4, yb), F(side, X - 0.9, z1 + 0.4, yb)
        knock([qb2, qb0, qb1, qb3], 0.4)
        edge(qb0, qb1, MINW * 1.1, 'key', rng)
        edge(qb2, qb3, MINW, 'key', rng)
        nb = int(abs(qb1[0] - qb0[0]) / 7)
        for i in range(1, nb):
            t = i / nb
            ln([lerp(qb0, qb1, t), lerp(qb2, qb3, t)], MINW, 'key', rng, wob=0.1)
    if ac and wpx > 10:
        a = quadw(side, X - 0.5, z1 + 0.2, z1 + 1.0, y0 - 0.2, y0 + 0.45)
        knock(a, 0.4)
        pline(a, MINW, 'key', rng, skip=0.25)


def shutter(side, X, z0, z1, rng, top=2.9, half=False, light_in='amber', lock=True):
    q = quadw(side, X, z0, z1, 0.1, top)
    hgt = abs(q[0][1] - q[1][1])
    if abs(q[2][0] - q[1][0]) < 5:
        return
    knock(q, 0.5)
    bottom = 0.1
    if abs(q[2][0] - q[1][0]) < 14:
        # far down the street a shutter is only its slats: no side edges (they make a comb), never half-up
        for yy in (0.1, top * 0.5, top):
            a, b = F(side, X, z0 + 0.05, yy), F(side, X, z1 - 0.05, yy)
            ln([a, b], MINW, 'key', rng, wob=0.1, a0=0.6, a1=1.2)
        return
    if half:
        bottom = top * rng.uniform(0.45, 0.6)
        inn = quadw(side, X + 0.3, z0 + 0.1, z1 - 0.1, 0.1, bottom)
        hatch(inn, light_in, math.pi / 2 + rng.gauss(0, 0.05), 8.0, rng=rng, gap=0.1)
    n = int(clamp(hgt * (1 - bottom / top) / 7.2, 2, 18))
    for i in range(n + 1):
        yy = bottom + (top - bottom) * i / n
        a, b = F(side, X, z0 + 0.05, yy), F(side, X, z1 - 0.05, yy)
        ln([a, lerp(a, b, 0.5), b], MINW * (1.25 if i == 0 else 1.0), 'key', rng, wob=0.15, a0=0.6, a1=1.2)
    edge(F(side, X, z0, 0.1), F(side, X, z0, top + 0.2), MINW * 1.1, 'key', rng)
    edge(F(side, X, z1, 0.1), F(side, X, z1, top + 0.2), MINW, 'key', rng)
    if lock and hgt > 40:
        m = F(side, X, (z0 + z1) / 2, bottom + 0.12)
        r = clamp(0.1 * S((z0 + z1) / 2), 2.0, 4)
        dot(m[0], m[1] - r, r, 'copper', rng)


def sign_board(side, X, z0, z1, y0, y1, rng, ink=None):
    q = quadw(side, X - 0.12, z0, z1, y0, y1)
    if abs(q[2][0] - q[1][0]) < 8:
        return
    knock(q, 0.5)
    ink = ink or rng.choice(('copper', 'green', 'amber', None))
    if ink:
        blob(grow(q, -2.0), ink, rng, gap=0.0, shift=0.8)
    pline(q, MINW * 1.1, 'key', rng, skip=0.1)


def water_tank(x, y, z, rng, r=0.6, hgt=1.2):
    """the black water tank every Bengaluru roof carries: a ribbed cylinder"""
    s = S(z)
    c0, c1 = pr(x, y, z), pr(x, y + hgt, z)
    rx = r * s
    if rx < 3:
        return
    ry = rx * 0.22
    body = [(c0[0] - rx, c1[1]), (c0[0] + rx, c1[1]), (c0[0] + rx, c0[1]), (c0[0] - rx, c0[1])]
    knock(body + ell(c1[0], c1[1], rx, ry, n=10), 0.8)
    ln([(c0[0] - rx, c0[1]), (c0[0] - rx, c1[1])], MINW, 'key', rng)
    ln([(c0[0] + rx, c0[1]), (c0[0] + rx, c1[1])], MINW, 'key', rng)
    ln(ell(c1[0], c1[1], rx, ry, n=12, a0=math.pi, a1=TAU, rng=rng), MINW, 'key', rng)
    ln(ell(c1[0], c1[1], rx, ry, n=12, a0=0, a1=math.pi, rng=rng), MINW, 'key', rng)
    for f in (0.35, 0.68):
        yy = c0[1] + (c1[1] - c0[1]) * f
        ln(ell(c0[0], yy, rx, ry, n=10, a0=0.1, a1=math.pi - 0.1, rng=rng), MINW, 'key', rng)
    dot(c1[0], c1[1] - ry * 0.4, max(MINW * 0.6, rx * 0.18), 'key', rng)


def building(side, X, z0, z1, h, rng, floor_h=3.2, ground='shops', lit=0.06, tanks=1, end_wall=True, depth=12.0,
             awning=None, balconies=0.25, grille=0.4, sign=0.6, half_shutter=0.15, glass_lit=False, detail=1.0):
    """a street building at night: shutters down, dark windows with grilles and balconies, one or two lit, the lamps
    warming its face, a black water tank on the roof"""
    x = side * X
    q = quadw(side, X, z0, z1, 0, h)
    knock(q, 0.8)
    s0 = S(z0)
    we = clamp(0.075 * s0, MINW, 6.2)
    if end_wall:
        ew = [pr(x, 0, z0), pr(x, h, z0), pr(x + side * depth, h, z0), pr(x + side * depth, 0, z0)]
        knock(ew, 0.8)
        hatch(ew, 'key', math.pi / 2 + rng.gauss(0, 0.03), clamp(0.2 * s0, 12, 17), rng=rng, gap=0.25,
              tone=lambda px, py: 0.22)
        edge(ew[1], ew[2], we * 0.9, 'key', rng)
        # a window or two in the end wall
        if rng.random() < 0.6 and h > 6:
            fy = floor_h * rng.randint(1, max(1, int(h / floor_h) - 1)) + 0.9
            wq = [pr(x + side * 3, fy, z0), pr(x + side * 3, fy + 1.4, z0), pr(x + side * 4.5, fy + 1.4, z0), pr(x + side * 4.5, fy, z0)]
            knock(wq, 0.6)
            if rng.random() < 0.3:
                blob(wq, 'amber', rng, gap=0.0)
            pline(wq, MINW, 'key', rng, skip=0.2)
    edge(F(side, X, z0, 0), F(side, X, z0, h), we, 'key', rng)
    edge(F(side, X, z0, h), F(side, X, z1, h), we * 0.85, 'key', rng)
    if h > 7:
        edge(F(side, X, z0, h - 0.4), F(side, X, z1, h - 0.4), MINW, 'key', rng)
    wash(side, X, z0, z1, 3.7, rng)
    # floors
    nf = int((h - 3.9) / floor_h)
    for f in range(nf):
        fy = 3.9 + f * floor_h
        if f > 0 and rng.random() < 0.7:
            edge(F(side, X, z0, fy - 0.05), F(side, X, z1, fy - 0.05), MINW, 'key', rng)
        bay = rng.uniform(2.8, 3.6)
        zz = z0 + rng.uniform(0.5, 1.2)
        while zz + bay * 0.7 < z1:
            wl = rng.random() < lit
            window(side, X, zz + 0.4, zz + bay - 0.5, fy + 0.85, fy + 2.35, rng, lit=wl, grille=rng.random() < grille,
                   figure_in=wl and rng.random() < 0.5, balcony=(rng.random() < balconies and f < nf),
                   ac=rng.random() < 0.15, curtain=wl and rng.random() < 0.5)
            zz += bay
    # ground floor
    if ground == 'shops':
        zz = z0 + 0.3
        while zz < z1 - 1.5:
            bw = min(rng.uniform(3.0, 4.6), z1 - zz - 0.3)
            if bw < 1.6:
                break
            shutter(side, X, zz + 0.15, zz + bw - 0.15, rng, half=rng.random() < half_shutter)
            if rng.random() < sign:
                sign_board(side, X, zz + 0.1, zz + bw - 0.1, 3.05, 3.75, rng)
            zz += bw
    elif ground == 'glass':
        g = quadw(side, X, z0 + 0.4, z1 - 0.4, 0.2, 3.3)
        knock(g, 0.5)
        hatch(g, 'amber', math.pi / 2, 8.5, rng=rng, gap=0.06)
        zz = z0 + 0.4
        while zz < z1 - 0.4:
            edge(F(side, X, zz, 0.2), F(side, X, zz, 3.3), MINW * 1.1, 'key', rng, over=(0, 0.5))
            zz += 2.2
        edge(F(side, X, z0 + 0.4, 3.3), F(side, X, z1 - 0.4, 3.3), MINW * 1.2, 'key', rng)
        light(side * (X - 0.2), 1.6, (z0 + z1) / 2, 'amber', wm=0.9, k=0.8)
    if awning:
        za, zb, col = awning
        aw = [F(side, X, za, 3.0), F(side, X - 1.5, za, 2.4), F(side, X - 1.5, zb, 2.4), F(side, X, zb, 3.0)]
        knock(aw, 0.6)
        n = max(3, int(abs(aw[2][0] - aw[1][0]) / 9))
        for i in range(n):
            if i % 2 == 0:
                t0, t1 = i / n, (i + 1) / n
                st = [lerp(aw[0], aw[3], t0), lerp(aw[1], aw[2], t0), lerp(aw[1], aw[2], t1), lerp(aw[0], aw[3], t1)]
                blob(st, col, rng, gap=0.0, shift=0.4)
        pline(aw, MINW * 1.1, 'key', rng, skip=0.1)
        # scalloped valance + a few drips
        for i in range(n):
            a, b = lerp(aw[1], aw[2], i / n), lerp(aw[1], aw[2], (i + 1) / n)
            ln([a, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 3.5), b], MINW, 'key', rng)
    # roof tanks peeking over the parapet
    for i in range(tanks):
        zt = rng.uniform(z0 + 1.5, z1 - 1.5)
        water_tank(side * (X + rng.uniform(1.0, 2.5)), h, zt, rng, r=rng.uniform(0.55, 0.75), hgt=rng.uniform(1.0, 1.4))
    return q


def low_roof(side, X, z0, z1, h, rng, depth=10.0, tanks=2):
    """a low building at the far end, below the eye: its flat roof seen from above, hatched, with tanks"""
    x = side * X
    roof = [pr(x, h, z0), pr(x + side * depth, h, z0), pr(x + side * depth, h, z1), pr(x, h, z1)]
    knock(roof, 0.6)
    hatch(roof, 'key', 0.15 * side, 11, rng=rng, gap=0.15, tone=lambda px, py: 0.6)
    pline(roof, MINW * 1.1, 'key', rng, skip=0.15)
    for i in range(tanks):
        water_tank(x + side * rng.uniform(2, depth - 2), h, rng.uniform(z0 + 1, z1 - 1), rng, r=0.6)


# ============================================================ THE BREWERY (hero, near left)
def silhouette_person(px, py, hh, layers, rng, glass_hand=False):
    """a drinker seen against the warm light inside: head and shoulders cut out of the light (black), no outline"""
    hr = hh * 0.11
    sh = [(px - hr * 2.3, py), (px - hr * 2.1, py - hh * 0.55), (px - hr * 1.2, py - hh * 0.7), (px + hr * 1.2, py - hh * 0.7),
          (px + hr * 2.1, py - hh * 0.55), (px + hr * 2.3, py)]
    knock(sh, 0, layers=layers)
    knock_ell(px + rng.uniform(-0.2, 0.2) * hr, py - hh * 0.7 - hr * 1.05, hr * 1.05, hr * 1.25, layers=layers)
    if glass_hand:
        gx = px + rng.choice((-1, 1)) * hr * 2.6
        knock_line([(px, py - hh * 0.45), (gx, py - hh * 0.62)], max(MINW, hr * 0.8), layers=layers)


def brewery(rng, z0=15.0, z1=31.0, X=7.8):
    """the microbrewery: double-height glass, three copper tanks lit from inside, drinkers at the bar against the warm
    light, a terrace with string lights under the rain tree"""
    side = -1
    x = -X
    HG, HP = 6.4, 7.3
    q = quadw(side, X, z0, z1, 0, HP)
    knock(q, 1.0)
    s0 = S(z0)
    gq = quadw(side, X, z0 + 0.5, z1 - 0.4, 0.25, HG)
    # the warm room: solid amber, broken by a few vertical breaks so it is light, not a slab
    blob(gq, 'amber', rng, gap=0.0, shift=0.5, jit=0.01)
    zz = z0 + 1.0
    while zz < z1 - 0.6:
        a, b = F(side, X, zz, 0.3), F(side, X, zz, HG - rng.uniform(0.3, 2.5))
        knock_line([a, b], MINW * 0.9, layers=('amber',))
        zz += rng.uniform(1.4, 2.6)
    carve_rain(gq, ('amber',), rng, sp=13.0)
    # copper tanks standing in the light, far to near
    for zt in (z1 - 2.6, z1 - 6.4, z1 - 10.2):
        brew_tank(x - 2.6, zt, rng, r=1.05, y0=0.4, y1=5.2)
    # drinkers at the bar: black silhouettes against the amber
    zz = z1 - 1.4
    while zz > z0 + 1.2:
        p = F(side, X - 1.1, zz, 0.35)
        hh = 1.25 * S(zz)
        silhouette_person(p[0], p[1], hh, ('amber', 'copper'), rng, glass_hand=rng.random() < 0.6)
        zz -= rng.uniform(1.3, 2.1)
    # bar counter line
    edge(F(side, X - 0.9, z0 + 1.0, 1.1), F(side, X - 0.9, z1 - 0.8, 1.1), MINW * 1.2, 'key', rng)
    # pendant lamps: small cream bells hanging from the ceiling
    zz = z0 + 2.0
    while zz < z1 - 1:
        top, bulb = F(side, X - 1.3, zz, HG), F(side, X - 1.3, zz, 5.8)
        knock_line([top, bulb], MINW + 2, layers=('amber', 'copper'))
        ln([top, bulb], MINW, 'key', rng, wob=0.05)
        r = clamp(0.24 * S(zz), 3.0, 8)
        bell = ell(bulb[0], bulb[1] + r * 0.6, r * 1.5, r, n=10, a0=math.pi, a1=TAU, rng=rng)
        knock(bell + [bell[0]], 0.8, layers=('amber', 'copper'))
        fillp(bell, 'key')
        zz += 3.2
    # the glass: few strong mullions, one transom
    zz = z0 + 0.5
    while zz <= z1 - 0.3:
        a, b = F(side, X, zz, 0.2), F(side, X, zz, HP - 0.5)
        knock_line([a, b], clamp(0.09 * S(zz), MINW, 6) + 2.0, layers=('amber', 'copper', 'green', 'ice'))
        edge(a, b, clamp(0.09 * S(zz), MINW, 6), 'key', rng, over=(0, 0.6))
        zz += 3.8
    edge(F(side, X, z0 + 0.5, 0.2), F(side, X, z1 - 0.4, 0.2), clamp(0.07 * s0, MINW, 5), 'key', rng)
    edge(F(side, X, z0 + 0.5, HG), F(side, X, z1 - 0.4, HG), clamp(0.07 * s0, MINW, 5), 'key', rng)
    # open door: warm light spills out
    light(x + 0.3, 2.2, z0 + 1.2, 'amber', wm=1.2, k=1.1, core='key')
    light(x + 0.3, 3.0, (z0 + z1) / 2, 'amber', wm=1.6, k=0.9)
    light(x + 0.3, 3.0, z1 - 3, 'amber', wm=1.4, k=0.8)
    # ----- terrace: parapet, three people at the rail, posts, one swag of bulbs
    pz = [z0 + 2.2, z0 + 6.8, z0 + 11.5]
    for zp in pz:
        fx_, fy_ = F(side, X + 0.5, zp, HG + 0.2)
        hgt = 1.7 * S(zp)
        figure(fx_, fy_, hgt, rng, facing=rng.choice(('right', 'front')), stride=0.0,
               arms=rng.choice((('glass', 'swing'), ('fold', 'fold'), ('up', 'swing'))),
               tcol=rng.choice(('copper', 'green', 'ice', None)), hair=rng.choice(('short', 'long', 'bun')), band=False,
               shoes=False)
    par = quadw(side, X, z0, z1, HG + 0.05, HP)
    knock(par, 0.5)
    edge(F(side, X, z0, HP), F(side, X, z1, HP), clamp(0.08 * s0, MINW, 6), 'key', rng)
    edge(F(side, X, z0, HG + 0.05), F(side, X, z1, HG + 0.05), MINW * 1.2, 'key', rng)
    edge(F(side, X, z0, 0), F(side, X, z0, HP), clamp(0.085 * s0, MINW, 6.5), 'key', rng)
    posts = [z0 + 0.4, z0 + 8.0, z1 - 0.4]
    for zp in posts:
        ln([F(side, X + 0.3, zp, HP), F(side, X + 0.3, zp, 9.4)], clamp(0.07 * S(zp), MINW, 5), 'key', rng)
    for i in range(len(posts) - 1):
        string_lights(F(side, X + 0.3, posts[i], 9.3), F(side, X + 0.3, posts[i + 1], 9.3), 0.8 * S(posts[i]) * 0.4, rng,
                      sp=13)
        LAMPS.append((x - 0.3, 9.0, (posts[i] + posts[i + 1]) / 2))
    return q



def string_lights(a, b, sag, rng, ink='amber', sp=11.0):
    """bulbs hanging on a sagging wire: the wire barely there, the bulbs carry it"""
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    n = max(2, int(L / sp))
    pts = []
    for i in range(n + 1):
        t = i / n
        pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t + sag * 4 * t * (1 - t)))
    ln(pts, MINW, 'key', rng, wob=0.1, a0=0.4, a1=0.6)
    for i in range(1, n):
        p = pts[i]
        if rng.random() < 0.92:
            knock_ell(p[0], p[1] + 3.2, 3.6, 4.2, layers=('key',))
            dot(p[0], p[1] + 3.2, 2.6, ink, rng)


def brew_tank(x, z, rng, r=0.95, y0=0.5, y1=5.0):
    """a tall copper brewing tank: conical foot on legs, cylinder, domed top, a manway and a valve"""
    s = S(z)
    c0, c1 = pr(x, y1, z), pr(x, y0 + 0.6, z)
    rx = r * s
    ry = rx * clamp((HC - y1) / 6.0, 0.08, 0.3)
    cx = c0[0]
    top_y, bot_y = c0[1], c1[1]
    body = [(cx - rx, top_y), (cx - rx, bot_y), (cx, bot_y + rx * 0.55), (cx + rx, bot_y), (cx + rx, top_y)]
    dome = ell(cx, top_y, rx, rx * 0.45, n=14, a0=math.pi, a1=TAU, rng=rng)
    sil = dome + body[::-1]
    knock(sil, 1.2)
    # copper: a solid lit body, a dark seam down the shadow side, one cream highlight where the bar light hits
    blob(sil, 'copper', rng, gap=0.0, shift=0.5, jit=0.01)
    knock_line([(cx + rx * 0.55, top_y + rx * 0.1), (cx + rx * 0.55, bot_y)], max(MINW, rx * 0.16), layers=('copper',))
    ln([(cx - rx * 0.5, top_y + rx * 0.05), (cx - rx * 0.5, bot_y - rx * 0.1)], max(MINW * 1.2, rx * 0.14), 'key', rng, wob=0.1)
    ln(dome, clamp(0.05 * s, MINW, 4), 'key', rng)
    # the cylinder's two sides, firm on the lit side, thin on the shadow side
    ln([(cx - rx, top_y), (cx - rx, bot_y)], clamp(0.05 * s, MINW, 4) * 1.15, 'key', rng, wob=0.1)
    ln([(cx + rx, top_y), (cx + rx, bot_y)], MINW, 'key', rng, wob=0.1)
    ln([(cx - rx, bot_y), (cx, bot_y + rx * 0.55), (cx + rx, bot_y)], MINW, 'key', rng, wob=0.1)
    for f in (0.33, 0.66):
        yy = top_y + (bot_y - top_y) * f
        knock_line(ell(cx, yy, rx, ry, n=10, a0=0.15, a1=math.pi - 0.15, rng=rng), MINW * 0.9, layers=('copper',))
    # a valve on a short pipe stub (an open ring here read as a letter in a row of three tanks)
    vy = top_y + (bot_y - top_y) * 0.8
    ln([(cx + rx * 0.1, vy), (cx + rx * 0.55, vy)], MINW * 1.2, 'key', rng, wob=0.05)
    ln([(cx + rx * 0.45, vy - rx * 0.16), (cx + rx * 0.45, vy + rx * 0.16)], MINW * 1.2, 'key', rng, wob=0.05)
    # legs
    for k_ in (-0.7, 0.7):
        ln([(cx + rx * k_, bot_y + rx * 0.2), (cx + rx * k_ * 1.05, pr(x, y0 - 0.3, z)[1])], MINW, 'key', rng)
    # top fitting
    ln([(cx, top_y - rx * 0.45), (cx, top_y - rx * 0.75), (cx + rx * 0.3, top_y - rx * 0.75)], MINW, 'key', rng)


def bungalow(rng, z0=35.0, z1=45.0, X=12.0):
    """an old bungalow with a sloping Mangalore-tile roof, set back behind its compound wall"""
    side = -1
    x = -X
    q = quadw(side, X, z0, z1, 0, 4.2)
    knock(q, 0.8)
    # veranda pillars and a lit window
    for zp in (z0 + 0.8, z0 + 3.6, z1 - 3.6, z1 - 0.8):
        a, b = F(side, X - 1.6, zp, 0.2), F(side, X - 1.6, zp, 3.9)
        knock_line([a, b], clamp(0.3 * S(zp), MINW, 8) + 2)
        ln([a, b], MINW, 'key', rng)
        ln([(a[0] + clamp(0.28 * S(zp), 3, 8), a[1]), (b[0] + clamp(0.28 * S(zp), 3, 8), b[1])], MINW, 'key', rng)
    window(side, X, z0 + 4.4, z0 + 6.2, 1.0, 2.7, rng, lit=True, curtain=True)
    window(side, X, z1 - 2.6, z1 - 1.2, 1.0, 2.7, rng, lit=False, grille=True)
    light(x + 0.5, 1.8, z0 + 5.3, 'amber', wm=0.6, k=0.8)
    # the roof: eave line, ridge line, tile courses
    eave = [pr(x + 1.0, 4.2, z0 - 1.0), pr(x + 1.0, 4.2, z1 + 1.0)]
    ridge = [pr(x - 4.0, 7.8, z0 + 2.5), pr(x - 4.0, 7.8, z1 - 2.5)]
    roof = [eave[0], ridge[0], ridge[1], eave[1]]
    knock(roof, 1.0)
    hip_near = [eave[0], ridge[0], pr(x - 9.0, 4.2, z0 - 1.0)]
    knock(hip_near, 1.0)
    hatch(hip_near, 'copper', 2.1, 10, rng=rng, gap=0.08)
    for i in range(1, 7):
        t = i / 7
        a = (eave[0][0] + (ridge[0][0] - eave[0][0]) * t, eave[0][1] + (ridge[0][1] - eave[0][1]) * t)
        b = (eave[1][0] + (ridge[1][0] - eave[1][0]) * t, eave[1][1] + (ridge[1][1] - eave[1][1]) * t)
        ln([a, lerp(a, b, 0.5), b], MINW, 'copper', rng, wob=0.2)
    # tile ends along the eave: little arches
    n = int(abs(eave[1][0] - eave[0][0]) / 7)
    for i in range(n):
        a, b = lerp(eave[0], eave[1], i / n), lerp(eave[0], eave[1], (i + 1) / n)
        ln([a, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - 3), b], MINW, 'key', rng, wob=0.1)
    pline(roof, MINW * 1.3, 'key', rng, skip=0.0)
    edge(eave[0], hip_near[2], MINW * 1.2, 'key', rng)
    # wet tiles glisten: a few long cream highlights along the slope
    for i in range(3):
        t = rng.uniform(0.2, 0.8)
        u_ = rng.uniform(0.2, 0.7)
        a = lerp(lerp(eave[0], eave[1], t), lerp(ridge[0], ridge[1], t), u_)
        b = lerp(lerp(eave[0], eave[1], t + 0.12), lerp(ridge[0], ridge[1], t + 0.12), u_ + 0.05)
        ln([a, b], MINW, 'key', rng)
    # compound wall + gate with a gate lamp
    wall = [F(side, 7.9, z0 - 2, 0), F(side, 7.9, z0 - 2, 1.7), F(side, 7.9, z1 + 2, 1.7), F(side, 7.9, z1 + 2, 0)]
    knock(wall, 0.6)
    edge(wall[1], wall[2], MINW * 1.3, 'key', rng)
    edge(F(side, 7.9, z0 - 2, 1.5), F(side, 7.9, z1 + 2, 1.5), MINW, 'key', rng)
    zg0, zg1 = z0 + 3.0, z0 + 6.0
    gq = quadw(side, 7.9, zg0, zg1, 0, 1.6)
    knock(gq, 0.3)
    n = int(abs(gq[2][0] - gq[1][0]) / 6.5)
    for i in range(n + 1):
        t = i / max(n, 1)
        ln([lerp(gq[0], gq[3], t), lerp(gq[1], gq[2], t)], MINW, 'key', rng, wob=0.1)
    for zp in (zg0, zg1):
        p0, p1 = F(side, 7.9, zp, 0), F(side, 7.9, zp, 2.1)
        ln([p0, p1], MINW * 1.5, 'key', rng)
    gl = F(side, 7.9, zg0, 2.35)
    dot(gl[0], gl[1], clamp(0.12 * S(zg0), 2.2, 5), 'amber', rng)
    halo(gl[0], gl[1], clamp(0.35 * S(zg0), 6, 14), 'amber', rng, rings=1)
    LAMPS.append((-7.9, 2.35, zg0))
    light(-7.9, 2.35, zg0, 'amber', wm=0.3, k=0.8)


# ============================================================ SMALL STORIES
def chai_stall(x, z, rng, k=1.0):
    """the chai stall still open at 1:42: tarp, a bare bulb lighting the back of the stall amber, the big kettle
    steaming against it, cutting glasses"""
    s = S(z)
    zz0, zz1 = z - 0.9 * k, z + 0.9 * k
    xi = x + 0.5 * k
    xo = x - 0.4 * k
    top = 1.05
    front = [pr(xo, 0.1, zz0), pr(xo, top, zz0), pr(xo, top, zz1), pr(xo, 0.1, zz1)]
    end = [pr(xo, 0.1, zz0), pr(xo, top, zz0), pr(xi, top, zz0), pr(xi, 0.1, zz0)]
    knock(front, 1.0)
    knock(end, 1.0)
    blob(front, 'green', rng, gap=0.0)
    hatch(end, 'green', math.pi / 2, 8, rng=rng, gap=0.05)
    pline(front, clamp(0.04 * s, MINW, 4.5), 'key', rng, skip=0.1)
    pline(end, clamp(0.04 * s, MINW, 4.5), 'key', rng, skip=0.3)
    for t in (0.33, 0.66):   # plank lines
        ln([lerp(front[0], front[3], 0) if False else lerp(front[0], front[1], t), lerp(front[3], front[2], t)], MINW, 'key', rng)
    # counter top
    ct = [pr(xo - 0.1, top, zz0 - 0.05), pr(xi + 0.1, top, zz0 - 0.05), pr(xi + 0.1, top, zz1 + 0.05), pr(xo - 0.1, top, zz1 + 0.05)]
    knock(ct, 0.6)
    pline(ct, MINW * 1.2, 'key', rng)
    # posts + tarp roof, sagging and dripping
    tH = 2.35 * (1 + (k - 1) * 0.6)
    # the bulb lights the back of the stall: one flat amber panel the kettle and the chaiwala stand against
    back = [pr(xi, top + 0.05, zz0 + 0.05), pr(xi, tH - 0.12, zz0 + 0.05), pr(xi, tH - 0.12, zz1 - 0.05), pr(xi, top + 0.05, zz1 - 0.05)]
    knock(back, 0.6)
    blob(back, 'amber', rng, gap=0.0, shift=0.6)
    for zp in (zz0, zz1):
        for xp in (xo, xi):
            ln([pr(xp, top, zp), pr(xp, tH, zp)], MINW, 'key', rng)
    tarp = [pr(xo - 0.5, tH - 0.15, zz0 - 0.3), pr(xi + 0.3, tH + 0.15, zz0 - 0.3), pr(xi + 0.3, tH + 0.15, zz1 + 0.3),
            pr(xo - 0.5, tH - 0.15, zz1 + 0.3)]
    knock(tarp, 1.0)
    n = 4
    for i in range(n):
        if i % 2 == 0:
            t0, t1 = i / n, (i + 1) / n
            st = [lerp(tarp[0], tarp[1], t0), lerp(tarp[0], tarp[1], t1), lerp(tarp[3], tarp[2], t1), lerp(tarp[3], tarp[2], t0)]
            blob(st, 'copper', rng, gap=0.0)
    pline(tarp, MINW * 1.2, 'key', rng)
    # bare bulb
    bb = pr(x + 0.05, tH - 0.45, z)
    ln([pr(x + 0.05, tH, z), bb], MINW, 'key', rng)
    knock_ell(bb[0], bb[1], 5, 5)
    dot(bb[0], bb[1], clamp(0.07 * s, 2.5, 5), 'amber', rng)
    halo(bb[0], bb[1], clamp(0.3 * s, 8, 18), 'amber', rng, rings=2)
    LAMPS.append((x + 0.05, tH - 0.45, z))
    light(x + 0.05, tH - 0.45, z, 'amber', wm=0.35, k=1.0, core='key')
    # the kettle on its stove, steam rising
    kc = pr(x, top + 0.32 * k, z + 0.2)
    kr = clamp(0.2 * s * k, 6, 22)
    body = ell(kc[0], kc[1], kr, kr * 0.85, n=16, rng=rng)
    knock(body, 1.0)
    hatch(body, 'key', 0.3, 7.5, rng=rng, gap=0.1, tone=lambda px, py: 0.8 if px > kc[0] else 0.25)
    ln(body, clamp(0.03 * s, MINW, 4), 'key', rng)
    sp_ = [(kc[0] - kr * 0.8, kc[1] + kr * 0.1), (kc[0] - kr * 1.5, kc[1] - kr * 0.4), (kc[0] - kr * 1.75, kc[1] - kr * 0.55)]
    ln(sp_, MINW * 1.3, 'key', rng)
    ln(ell(kc[0], kc[1] - kr * 0.9, kr * 0.6, kr * 0.5, n=10, a0=math.pi, a1=TAU, rng=rng), MINW * 1.2, 'key', rng)
    st0 = (kc[0] - kr * 0.7, kc[1] + kr * 0.85)
    ln([st0, (st0[0] + kr * 1.4, st0[1])], MINW * 1.4, 'key', rng)
    # three curls of steam, parallel, each in its own black slot
    for k_ in range(3):
        x0, y0 = sp_[-1][0] + (k_ - 0.5) * kr * 0.8, sp_[-1][1] - 5 - abs(k_ - 1) * 4
        hgt = kr * (1.25 - 0.2 * abs(k_ - 1))
        pts = [(x0 + math.sin(t / 13 * TAU * 1.35) * kr * 0.22 * (0.5 + t / 13), y0 - t / 13 * hgt)
               for t in range(14)]
        knock_line(pts, MINW + 4.5, layers=('amber', 'green', 'copper', 'ice', 'yellow', 'blue'))
        ln(pts, MINW * 1.05, 'key', rng, wob=0.03, trem=0.0, a0=0.6, a1=2.6)
    # glasses on the counter
    for i in range(5):
        g = pr(xo + 0.05, top + 0.06, zz0 + 0.25 + i * 0.13)
        gw = clamp(0.035 * s, 2.0, 3.5)
        ln([(g[0] - gw, g[1] - gw * 2.6), (g[0] - gw * 0.8, g[1]), (g[0] + gw * 0.8, g[1]), (g[0] + gw, g[1] - gw * 2.6)], MINW, 'key', rng, wob=0.05)
    return (bb, kc)


def plastic_chair_guard(x, z, rng):
    """the night guard asleep on a plastic chair, cap down, arms folded, legs out"""
    s = S(z)
    u = 1.7 * s
    g = pr(x, 0, z)
    gx, gy = g
    w = clamp(0.02 * u, MINW, 4.5)
    # chair: seat, back, legs (white monobloc)
    seat = [(gx - 0.14 * u, gy - 0.27 * u), (gx + 0.12 * u, gy - 0.27 * u), (gx + 0.14 * u, gy - 0.24 * u), (gx - 0.12 * u, gy - 0.24 * u)]
    back = [(gx + 0.1 * u, gy - 0.27 * u), (gx + 0.16 * u, gy - 0.58 * u), (gx + 0.05 * u, gy - 0.6 * u), (gx - 0.01 * u, gy - 0.29 * u)]
    for p in (back, seat):
        knock(p, 1)
        pline(p, w, 'key', rng, skip=0.1)
    for k in (-0.13, 0.12):
        ln([(gx + k * u, gy - 0.25 * u), (gx + k * u * 1.15, gy)], w, 'key', rng)
    # body: slumped back, legs stretched toward the street
    hip = (gx + 0.02 * u, gy - 0.3 * u)
    sh = (gx + 0.06 * u, gy - 0.62 * u)
    knee = (gx - 0.18 * u, gy - 0.3 * u)
    foot = (gx - 0.33 * u, gy - 0.02 * u)
    for a, b, wd in ((hip, knee, 0.09), (knee, foot, 0.065)):
        sp, ws = tube([a, b], [wd * u, wd * u * 0.85])
        Lp, Rp = tube_poly(sp, ws)
        knock(Lp + Rp[::-1], 1)
        blob(Lp + Rp[::-1], 'ice', rng, gap=0.0)
        ln(Lp[::3], w, 'key', rng)
        ln(Rp[::3], w, 'key', rng)
    tor = [(sh[0] - 0.1 * u, sh[1]), (sh[0] + 0.08 * u, sh[1] + 0.01 * u), (hip[0] + 0.08 * u, hip[1]), (hip[0] - 0.09 * u, hip[1])]
    knock(tor, 1)
    blob(tor, 'ice', rng, gap=0.0)
    pline(tor, w, 'key', rng, skip=0.2)
    # folded arms
    arm = [(sh[0] - 0.09 * u, sh[1] + 0.05 * u), (sh[0] - 0.13 * u, sh[1] + 0.16 * u), (sh[0] + 0.05 * u, sh[1] + 0.17 * u)]
    knock_line(arm, 0.06 * u)
    ln(offset_path(catmull(arm), 0.03 * u)[::3], w, 'key', rng)
    ln(offset_path(catmull(arm), -0.03 * u)[::3], w, 'key', rng)
    # head dropped forward, cap
    hc = (sh[0] - 0.04 * u, sh[1] - 0.06 * u)
    hd = ell(hc[0], hc[1], 0.05 * u, 0.06 * u, n=14, rng=rng)
    knock(hd, 1)
    ln(hd, w, 'key', rng)
    cap = [(hc[0] - 0.06 * u, hc[1] - 0.015 * u), (hc[0] - 0.1 * u, hc[1] + 0.005 * u)]
    ln(ell(hc[0], hc[1] - 0.02 * u, 0.055 * u, 0.045 * u, n=10, a0=math.pi, a1=TAU, rng=rng), w * 1.1, 'key', rng)
    ln(cap, w * 1.2, 'key', rng)
    # a lathi leaning on the chair
    ln([(gx + 0.17 * u, gy), (gx + 0.24 * u, gy - 0.55 * u)], w, 'copper', rng)


def atm_box(side, X, z0, z1, rng):
    """an ATM kiosk: the only cool white light on the street side, glass door, a blank sign box"""
    q = quadw(side, X, z0, z1, 0.1, 2.8)
    knock(q, 0.5)
    hatch(q, 'ice', math.pi / 2, 8.0, rng=rng, gap=0.05, tone=lambda px, py: 0.85)
    pline(q, MINW * 1.2, 'key', rng)
    zm = (z0 + z1) / 2
    edge(F(side, X, zm, 0.1), F(side, X, zm, 2.8), MINW, 'key', rng)
    sb = quadw(side, X - 0.1, z0 - 0.1, z1 + 0.1, 3.0, 3.6)
    knock(sb, 0.5)
    blob(grow(sb, -1.5), 'ice', rng, gap=0.0)
    pline(sb, MINW, 'key', rng)
    light(side * (X - 0.1), 1.6, zm, 'ice', wm=0.8, k=0.8, core='key')


# ============================================================ NAMMA METRO GREEN LINE
def via_x(z):
    if z < 40:
        return 7.6 + 0.06 * (40 - z) ** 2
    if z < 75:
        return 7.6
    return 7.6 + 0.004 * (z - 75) ** 2


DECK_B, DECK_T, PARA = 10.4, 12.0, 13.1
TRAIN_F = 38.0
TRAIN_CARS = 3
CAR_L = 21.0


def via_segment(z0, z1, rng, with_train=True):
    """one length of the box-girder viaduct (underside, web, parapet), with whatever part of the train rides on it"""
    def P_(dx, y, z):
        return pr(via_x(z) + dx, y, z)
    n = max(2, int((z1 - z0) / 1.5))
    zs = [z0 + (z1 - z0) * i / n for i in range(n + 1)]
    under_l = [P_(-3.0, DECK_B, z) for z in zs]
    under_r = [P_(3.0, DECK_B, z) for z in zs]
    web_t = [P_(-4.25, 11.3, z) for z in zs]
    par_b = [P_(-4.25, DECK_T, z) for z in zs]
    par_t = [P_(-4.25, PARA, z) for z in zs]
    poly = under_l + under_r[::-1]
    side_poly = under_l + par_t[::-1]
    knock(poly, 0.6)
    knock(side_poly, 0.6)
    s = S((z0 + z1) / 2)
    # the underside: long lines along the deck, warm from the street lamps below
    for f in (0.12, 0.34, 0.56, 0.78):
        pts = [P_(-3.0 + 6.0 * f, DECK_B, z) for z in zs]
        if rng.random() < 0.85:
            ln(pts, MINW, 'amber', rng, wob=0.15)
    # train riding behind the parapet
    if with_train:
        train_piece(z0, z1, rng)
    knock(side_poly, 0.4)
    wb = clamp(0.06 * s, MINW, 6)
    ln(under_l, wb, 'key', rng, wob=0.2)
    ln(web_t, MINW * 1.1, 'key', rng, wob=0.2)
    ln(par_b, MINW, 'key', rng, wob=0.2)
    ln(par_t, clamp(0.05 * s, MINW, 5), 'key', rng, wob=0.2)
    # parapet panel joints, far apart
    zz = math.ceil(z0 / 6.0) * 6.0
    while zz < z1:
        a, b = P_(-4.25, DECK_T + 0.05, zz), P_(-4.25, PARA - 0.05, zz)
        if abs(a[1] - b[1]) > 6:
            ln([a, b], MINW, 'key', rng, wob=0.1)
        zz += 6.0


def train_track_x(z):
    return via_x(z) - 1.9


def train_piece(z0, z1, rng):
    """the part of the last train between z0 and z1: stainless body, green band, lit windows with standing passengers"""
    zf = TRAIN_F
    zend = zf + TRAIN_CARS * CAR_L
    a, b = max(z0, zf), min(z1, zend)
    if a >= b:
        return
    def P_(y, z):
        return pr(train_track_x(z) - 1.45, y, z)
    n = max(2, int((b - a) / 1.0))
    zs = [a + (b - a) * i / n for i in range(n + 1)]
    roof = [P_(16.0, z) for z in zs]
    roof2 = [pr(train_track_x(z) + 0.6, 16.25, z) for z in zs]
    low = [P_(PARA - 0.2, z) for z in zs]
    body = roof + low[::-1]
    knock(body + roof2[::-1][-1:], 0.4)
    knock(roof + roof2[::-1], 0.4)
    s = S((a + b) / 2)
    # green band below the windows
    gb = [P_(13.75, z) for z in zs] + [P_(13.45, z) for z in zs][::-1]
    blob(gb, 'green', rng, gap=0.0, shift=0.3, jit=0.01)
    # windows and doors along each car
    for c in range(TRAIN_CARS):
        c0 = zf + c * CAR_L
        # doors at 4 places per car, windows between
        zz = c0 + 0.8
        k = 0
        while zz < c0 + CAR_L - 0.8:
            is_door = (k % 3 == 1)
            wz0, wz1 = zz, zz + (1.3 if is_door else 1.9)
            if wz1 > a and wz0 < b:
                lo_, hi_ = (13.9, 15.3)
                q = [P_(lo_, max(wz0, a)), P_(hi_, max(wz0, a)), P_(hi_, min(wz1, b)), P_(lo_, min(wz1, b))]
                if abs(q[2][0] - q[1][0]) > 3:
                    knock(q, 0.4)
                    blob(grow(q, -0.6), 'ice', rng, gap=0.0, shift=0.3, jit=0.01)
                    # standing passengers against the light
                    np_ = int(abs(q[2][0] - q[1][0]) / max(6, 0.55 * s))
                    for i in range(np_):
                        if rng.random() < 0.65:
                            t = (i + 0.5) / max(np_, 1)
                            px, py = lerp(q[0], q[3], t)
                            hh = abs(q[0][1] - q[1][1])
                            hr = clamp(hh * 0.13, 1.9, 6)
                            shp = [(px - hr * 1.9, py + 1), (px - hr * 1.4, py - hh * 0.45), (px + hr * 1.4, py - hh * 0.45), (px + hr * 1.9, py + 1)]
                            knock(shp, 0, layers=('ice',))
                            knock_ell(px, py - hh * 0.45 - hr * 1.1, hr, hr * 1.2, layers=('ice',))
                            if rng.random() < 0.35:   # a raised arm holding the rail
                                knock_line([(px + hr, py - hh * 0.4), (px + hr * 1.6, py - hh * 0.95)], max(MINW, hr * 0.7), layers=('ice',))
                    pline(q, MINW, 'key', rng, skip=0.35)
                if is_door:
                    d0, d1 = P_(13.2, max(wz0, a)), P_(15.6, max(wz0, a))
                    ln([d0, d1], MINW, 'key', rng, wob=0.1)
                    d0, d1 = P_(13.2, min(wz1, b)), P_(15.6, min(wz1, b))
                    ln([d0, d1], MINW, 'key', rng, wob=0.1)
            zz = wz1 + 0.35
            k += 1
        # gangway between cars
        if c > 0 and a <= c0 <= b:
            g0, g1 = P_(PARA - 0.2, c0), P_(16.0, c0)
            knock_line([g0, g1], clamp(0.5 * s, MINW, 10))
            ln([g0, g1], MINW, 'key', rng)
    ln(roof, clamp(0.05 * s, MINW, 5), 'key', rng, wob=0.15)
    ln(roof2, MINW, 'key', rng, wob=0.15)
    ln([P_(15.55, z) for z in zs], MINW, 'key', rng, wob=0.15)


def train_front(rng):
    """the driving cab coming toward us: rounded nose, big windscreen, destination band, two headlights"""
    zf = TRAIN_F
    xc = train_track_x(zf)
    s = S(zf)
    def Q(dx, y):
        return pr(xc + dx, y, zf - 0.6 * math.cos(dx / 1.45 * math.pi / 2) * (1 if y > 14.8 else 0.5))
    hw = 1.45
    pts = []
    for i in range(9):
        t = i / 8
        a = math.pi * t
        pts.append(Q(-hw * math.cos(a) * 0.98, 15.55 + 0.45 * math.sin(a)))
    face = [Q(-hw, PARA - 0.2)] + pts + [Q(hw, PARA - 0.2)]
    knock(face, 1.0)
    # body below the windscreen: stainless, with the green band wrapping round
    band = [Q(-hw, 13.75), Q(-hw * 0.5, 13.72), Q(0, 13.7), Q(hw * 0.5, 13.72), Q(hw, 13.75), Q(hw, 13.45), Q(0, 13.4), Q(-hw, 13.45)]
    blob(band, 'green', rng, gap=0.0, shift=0.3)
    ws = [Q(-hw * 0.82, 14.05), Q(-hw * 0.86, 15.15), Q(hw * 0.86, 15.15), Q(hw * 0.82, 14.05)]
    knock(ws, 0.4)
    hatch(ws, 'ice', 0.5, 7.0, rng=rng, gap=0.1, tone=lambda px, py: 0.55)
    pline(ws, clamp(0.06 * s, MINW, 4.5), 'key', rng)
    ln([lerp(ws[0], ws[3], 0.5), lerp(ws[1], ws[2], 0.5)], MINW, 'key', rng)
    dz = [Q(-hw * 0.55, 15.25), Q(-hw * 0.55, 15.5), Q(hw * 0.55, 15.5), Q(hw * 0.55, 15.25)]
    knock(dz, 0.3)
    fillp(dz, 'amber')
    ln(face, clamp(0.07 * s, MINW, 5.5), 'key', rng, wob=0.15, redraw=0.4)
    for sx in (-1, 1):
        hl = Q(sx * hw * 0.62, 13.55)
        r = clamp(0.13 * s, 2.5, 6)
        knock_ell(hl[0], hl[1], r + 1.2, r + 1.2)
        dot(hl[0], hl[1], r, 'ice', rng)
        halo(hl[0], hl[1], r * 2.6, 'ice', rng, rings=2)
        light(xc + sx * hw * 0.62, 13.55, zf, 'ice', wm=0.35, k=1.0, core='key', stretch=0.85)


def pier(z, rng):
    """a tall single round pier with a wide hammerhead cap holding the deck"""
    xc = via_x(z)
    s = S(z)
    r = 0.9
    g0, g1 = pr(xc - r, 0, z), pr(xc + r, 0, z)
    t0, t1 = pr(xc - r, 8.4, z), pr(xc + r, 8.4, z)
    col = [g0, t0, t1, g1]
    capb = [pr(xc - 1.2, 8.4, z), pr(xc - 3.4, 9.6, z), pr(xc - 3.4, DECK_B, z), pr(xc + 3.4, DECK_B, z), pr(xc + 3.4, 9.6, z), pr(xc + 1.2, 8.4, z)]
    knock(col, 1.2)
    knock(capb, 1.2)
    we = clamp(0.07 * s, MINW, 6)
    edge(g0, t0, we, 'key', rng)
    edge(g1, t1, we * 0.8, 'key', rng)
    # the round column: vertical strokes crowded on the shadow side, amber on the lamp side
    lit = lamp_lit(xc, 4, z, r=9)
    def tone(px, py):
        f = (px - g0[0]) / max(1, g1[0] - g0[0])
        return clamp(0.15 + 0.85 * f ** 1.5, 0, 1)
    hatch(col, 'key', math.pi / 2, clamp(0.12 * s, 7.5, 11), rng=rng, gap=0.05, tone=tone)
    if lit > 0.15:
        hatch(col, 'amber', math.pi / 2, 9, rng=rng, gap=0.1, tone=lambda px, py: lit * (1 - (px - g0[0]) / max(1, g1[0] - g0[0])))
    pline(capb, we * 0.9, 'key', rng, skip=0.1)
    hatch(capb, 'key', 0.12, clamp(0.13 * s, 8, 12), rng=rng, gap=0.08, tone=lambda px, py: 0.5)
    # plinth in the median
    pl = [pr(xc - 1.3, 0, z - 0.8), pr(xc - 1.3, 0.35, z - 0.8), pr(xc + 1.3, 0.35, z - 0.8), pr(xc + 1.3, 0, z - 0.8)]
    knock(pl, 0.5)
    pline(pl, MINW, 'key', rng, skip=0.2)


def station(rng):
    """Madavara, the end of the Green Line, beside the grounds: a long platform deck under a curved roof"""
    z0, z1 = 160.0, 182.0
    def P_(dx, y, z):
        return pr(via_x(z) + dx, y, z)
    n = 8
    zs = [z0 + (z1 - z0) * i / n for i in range(n + 1)]
    deck = [P_(-6, 10.4, z) for z in zs] + [P_(-6, 12.6, z) for z in zs][::-1]
    roof_e = [P_(-6.5, 17.5, z) for z in zs]
    roof_c = [P_(0, 21.5, z) for z in zs]
    knock(deck, 0.6)
    knock(roof_e + roof_c[::-1], 0.6)
    ln([P_(-6, 12.6, z) for z in zs], MINW * 1.2, 'key', rng)
    ln([P_(-6, 10.4, z) for z in zs], MINW, 'key', rng)
    ln(roof_e, MINW * 1.3, 'key', rng)
    ln(roof_c, MINW * 1.2, 'key', rng)
    # curved ribs of the roof
    for z in zs:
        rib = [P_(-6.5 + 6.5 * t, 17.5 + 4.0 * math.sin(t * math.pi / 2), z) for t in [i / 5 for i in range(6)]]
        ln(rib, MINW, 'key', rng, wob=0.1)
    # lit platform band under the roof
    band = [P_(-6, 12.7, z) for z in zs] + [P_(-6, 15.2, z) for z in zs][::-1]
    hatch(band, 'ice', math.pi / 2, 8, rng=rng, gap=0.1, tone=lambda px, py: 0.6)
    for z in zs[::2]:
        ln([P_(-6, 12.6, z), P_(-6.5, 17.5, z)], MINW, 'key', rng)
        ln([P_(-5, 0, z), P_(-5, 10.4, z)], MINW, 'key', rng)


# ============================================================ THE SHOW AT NICE GROUNDS (white light only)
SHOW_X = -2.0
SHOW_Z = 200.0
GROUND_LIFT = 1.2


def gl(z):
    return GROUND_LIFT * clamp((z - 92) / 12, 0, 1)


def truss_line(a, b, rng, w=MINW, n=None, ink='key', zig=True):
    """a lattice truss beam: two chords and a zigzag"""
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    if L < 3:
        return
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, ny = -uy, ux
    d = 3.4
    a1, b1 = (a[0] + nx * d, a[1] + ny * d), (b[0] + nx * d, b[1] + ny * d)
    ln([a, b], w, ink, rng, wob=0.15)
    ln([a1, b1], w, ink, rng, wob=0.15)
    if zig and L > 20:
        n = n or int(L / 8)
        pts = []
        for i in range(n + 1):
            t = i / n
            p = lerp(a, b, t) if i % 2 == 0 else lerp(a1, b1, t)
            pts.append(p)
        ln(pts, MINW, ink, rng, wob=0.1, a0=0.5, a1=0.5)


def show_stage(rng):
    """the stage as a real open-ground show: ground-support roof, pale sheet, LED wall with grainy footage, IMAG
    screens, hanging line arrays, strobes and moving heads on the truss. Returns beam roots."""
    zf, zb = SHOW_Z - 5, SHOW_Z + 4
    xc = SHOW_X
    hw = 14.0
    g = lambda z: gl(z)
    P_ = lambda x, y, z: pr(x, y + g(z), z)
    s = S(zf)
    # towers
    roofy = 18.5
    towers = [(xc - hw, zf), (xc + hw, zf), (xc - hw, zb), (xc + hw, zb)]
    # LED wall at the back
    led = [P_(xc - 8.5, 3.2, zb - 0.5), P_(xc - 8.5, 12.2, zb - 0.5), P_(xc + 8.5, 12.2, zb - 0.5), P_(xc + 8.5, 3.2, zb - 0.5)]
    knock(led, 0.8)
    footage(led, rng, kind='hand')
    carve_rain(led, ('ice',), rng, sp=7.5, L=(5, 9))
    pline(led, MINW * 1.2, 'key', rng)
    # IMAG side screens (portrait), hung outside the towers
    for sx in (-1, 1):
        sc = [P_(xc + sx * 17.0 - 2.4, 6.5, zf), P_(xc + sx * 17.0 - 2.4, 14.5, zf), P_(xc + sx * 17.0 + 2.4, 14.5, zf), P_(xc + sx * 17.0 + 2.4, 6.5, zf)]
        knock(sc, 0.8)
        footage(sc, rng, kind='face' if sx < 0 else 'crowd')
        pline(sc, MINW * 1.1, 'key', rng)

    # stage deck
    deck = [P_(xc - hw, 0, zf), P_(xc - hw, 2.0, zf), P_(xc + hw, 2.0, zf), P_(xc + hw, 0, zf)]
    knock(deck, 0.5)
    ln([deck[1], deck[2]], MINW * 1.4, 'key', rng)

    # towers (truss columns)
    for x_, z_ in towers[:2]:
        a, b = P_(x_, 0, z_), P_(x_, roofy, z_)
        knock_line([a, b], 9)
        truss_line(a, b, rng)
    # roof: front truss with a shallow gable, side wings
    peak = P_(xc, roofy + 3.0, zf)
    fl, fr = P_(xc - hw - 1.5, roofy, zf), P_(xc + hw + 1.5, roofy, zf)
    knock([fl, peak, fr, P_(xc + hw + 1.5, roofy - 1.2, zf), P_(xc - hw - 1.5, roofy - 1.2, zf)], 0.6)
    truss_line(fl, peak, rng, w=MINW * 1.2)
    truss_line(peak, fr, rng, w=MINW * 1.2)
    truss_line(P_(xc - hw - 1.5, roofy - 1.2, zf), P_(xc + hw + 1.5, roofy - 1.2, zf), rng, w=MINW)
    # the pale sheet: a big fabric hung in a billow under the roof (Fred's white canopy)
    sheet = []
    for i in range(13):
        t = i / 12
        sx_ = xc - hw + 2 * hw * t
        sag = 4.2 * math.sin(math.pi * t) + 0.6 * math.sin(t * 9)
        sheet.append(P_(sx_, roofy - 1.6 - sag, zf - 0.5))
    top_e = [P_(xc - hw, roofy - 1.3, zf - 0.5), P_(xc + hw, roofy - 1.3, zf - 0.5)]
    sh_poly = [top_e[0]] + sheet + [top_e[1]]
    knock(sh_poly, 0.6)
    # the sheet hangs in swags: a few catenaries in ice, and its pale belly
    for k in range(1, 4):
        f = k / 4
        sw = [lerp(top_e[0], top_e[1], i / 12) for i in range(13)]
        sw = [(p[0], p[1] + (sheet[i][1] - p[1]) * f + rng.gauss(0, 0.6)) for i, p in enumerate(sw)]
        ln(sw, MINW, 'ice', rng, wob=0.2, a0=1.5, a1=3.0)
    blob(sheet[3:10] + [lerp(top_e[0], top_e[1], 0.75), lerp(top_e[0], top_e[1], 0.25)], 'ice', rng, gap=0.25, shift=0.6)
    ln(sheet, MINW * 1.3, 'key', rng, wob=0.2)
    # line arrays hanging from the wings: J-curved columns of boxes
    for sx in (-1, 1):
        x_ = xc + sx * (hw - 1.0)
        top = P_(x_, roofy - 1.2, zf - 1)
        nbox = 12
        boxes = []
        for i in range(nbox + 1):
            t = i / nbox
            yy = roofy - 1.4 - 7.5 * t
            dz = -0.9 * t ** 2
            boxes.append(P_(x_ + sx * 0.0, yy, zf - 1 + dz))
        wdt = clamp(0.9 * s, 4, 14)
        col = [(p[0] - wdt / 2, p[1]) for p in boxes] + [(p[0] + wdt / 2, p[1]) for p in boxes][::-1]
        knock(col, 0.8)
        ln([(p[0] - wdt / 2, p[1]) for p in boxes], MINW, 'key', rng)
        ln([(p[0] + wdt / 2, p[1]) for p in boxes], MINW, 'key', rng)
        for p in boxes[2::2]:
            ln([(p[0] - wdt / 2, p[1]), (p[0] + wdt / 2, p[1])], MINW, 'key', rng, wob=0.05)
        ln([top, boxes[0]], MINW, 'key', rng)
    # the artist: a small figure at the decks, lit from behind (a silhouette with a white rim)
    dx_, dy_ = P_(xc + 0.5, 2.0, zf + 2)
    hgt = 1.8 * S(zf + 2)
    table = [(dx_ - hgt * 0.5, dy_), (dx_ - hgt * 0.5, dy_ - hgt * 0.5), (dx_ + hgt * 0.5, dy_ - hgt * 0.5), (dx_ + hgt * 0.5, dy_)]
    knock(table, 0.6)
    pline(table, MINW, 'key', rng, skip=0.3)
    figure(dx_, dy_, hgt, rng, facing='front', arms=('up', 'hold'), tcol=None, hair='cap', w=MINW, shoes=False, band=False)
    # moving heads + strobes on the front truss
    roots = []
    for i in range(7):
        t = (i + 0.5) / 7
        p = lerp(P_(xc - hw + 1, roofy - 1.0, zf), P_(xc + hw - 1, roofy - 1.0, zf), t)
        knock_ell(p[0], p[1], 3.2, 3.2)
        dot(p[0], p[1], 2.4, 'ice', rng)
        roots.append(p)
    for i in range(4):
        t = (i + 0.7) / 4.4
        p = lerp(P_(xc - hw + 2, 2.6, zf - 0.2), P_(xc + hw - 2, 2.6, zf - 0.2), t)
        strobe = [(p[0] - 6, p[1] - 2.2), (p[0] + 6, p[1] - 2.2), (p[0] + 6, p[1] + 2.2), (p[0] - 6, p[1] + 2.2)]
        knock(strobe, 0.6)
        fillp(strobe, 'ice')
        for a in (-0.5, 0.0, 0.5, math.pi - 0.5, math.pi, math.pi + 0.5):
            r0, r1 = 7.5, 7.5 + rng.uniform(5, 11)
            ln([(p[0] + math.cos(a) * r0, p[1] - abs(math.sin(a)) * r0 * 0.6), (p[0] + math.cos(a) * r1, p[1] - abs(math.sin(a)) * r1 * 0.6)],
               MINW, 'ice', rng, wob=0.05)
    # floor glow of the stage on the crowd: register the show's lights for the road
    light(xc, 8.0, zb, 'ice', wm=4.0, k=1.0, core='key', stretch=4.2, brk=0.12)
    light(xc - 5, 3.0, zf, 'ice', wm=1.8, k=0.9, core='key', stretch=4.6, brk=0.2)
    light(xc + 5, 3.0, zf, 'ice', wm=1.8, k=0.9, core='key', stretch=4.6, brk=0.2)
    light(xc - 17, 10.0, zf, 'ice', wm=1.4, k=0.7, stretch=3.2, brk=0.3)
    light(xc + 17, 10.0, zf, 'ice', wm=1.4, k=0.7, stretch=3.2, brk=0.3)
    return roots


def footage(q, rng, kind='hand'):
    """the big screen: grainy lo-fi phone footage, shapes only (a raised hand, a face in profile, the crowd), coarse
    halftone and scan lines in ice"""
    x0, y0, x1, y1 = bbox(q)
    wq, hq = x1 - x0, y1 - y0
    tone = Image.new('L', (W, H), 0)
    td = ImageDraw.Draw(tone)
    td.polygon(P(q), fill=70)
    if kind == 'hand':
        # a hand reaching up into the light, from the bottom edge
        cx = x0 + wq * 0.55
        palm = [(cx - wq * 0.1, y1), (cx - wq * 0.12, y0 + hq * 0.5), (cx - wq * 0.14, y0 + hq * 0.2), (cx - wq * 0.09, y0 + hq * 0.18),
                (cx - wq * 0.07, y0 + hq * 0.4), (cx - wq * 0.05, y0 + hq * 0.08), (cx, y0 + hq * 0.06), (cx + wq * 0.01, y0 + hq * 0.38),
                (cx + wq * 0.04, y0 + hq * 0.1), (cx + wq * 0.08, y0 + hq * 0.12), (cx + wq * 0.06, y0 + hq * 0.42),
                (cx + wq * 0.1, y0 + hq * 0.25), (cx + wq * 0.13, y0 + hq * 0.3), (cx + wq * 0.09, y0 + hq * 0.6), (cx + wq * 0.08, y1)]
        td.polygon(P(palm), fill=235)
    elif kind == 'face':
        cx = x0 + wq * 0.45
        face = [(x0, y1), (x0 + wq * 0.1, y0 + hq * 0.6), (cx - wq * 0.1, y0 + hq * 0.25), (cx + wq * 0.2, y0 + hq * 0.15),
                (cx + wq * 0.4, y0 + hq * 0.32), (cx + wq * 0.48, y0 + hq * 0.45), (cx + wq * 0.38, y0 + hq * 0.5),
                (cx + wq * 0.42, y0 + hq * 0.62), (cx + wq * 0.3, y0 + hq * 0.75), (cx + wq * 0.2, y1)]
        td.polygon(P(face), fill=220)
    else:
        for i in range(9):
            hx = x0 + wq * (0.05 + 0.9 * i / 8) + rng.uniform(-2, 2)
            hy = y0 + hq * rng.uniform(0.55, 0.75)
            td.ellipse(P([(hx - wq * 0.07, hy - wq * 0.07), (hx + wq * 0.07, hy + wq * 0.07)]), fill=200)
            td.line(P([(hx, hy), (hx + rng.uniform(-3, 3), hy - hq * rng.uniform(0.25, 0.5))]), fill=200, width=int(4 * R))
        td.rectangle(P([(x0, y0 + hq * 0.72), (x1, y1)]), fill=200)
    mask = Image.new('L', (W, H), 0)
    ImageDraw.Draw(mask).polygon(P(grow(q, -1.5)), fill=255)
    ht = halftone(tone, cell=6.2, angle=0.4, rng=rng, jitter=0.08)
    A.add('ice', ImageChops.multiply(ht, mask))
    # scan lines over it
    for i in range(int(hq / 9)):
        yy = y0 + 4 + i * 9
        if rng.random() < 0.35:
            ln([(x0 + 2, yy), (x1 - 2, yy)], MINW, 'ice', rng, wob=0.05)


def tent(x, z, wdt, dep, hgt, rng, lights='amber', ink=None):
    P_ = lambda xx, y, zz: pr(xx, y + gl(zz), zz)
    a, b = P_(x - wdt / 2, hgt * 0.6, z), P_(x + wdt / 2, hgt * 0.6, z)
    pk = P_(x, hgt, z + dep / 2)
    g0, g1 = P_(x - wdt / 2, 0, z), P_(x + wdt / 2, 0, z)
    poly = [g0, a, pk, b, g1]
    knock(poly, 0.8)
    if lights:
        inner = [g0, a, b, g1]
        hatch(inner, lights, math.pi / 2, 7.5, rng=rng, gap=0.05)
    pline(poly, MINW * 1.1, 'key', rng, closed=False)
    ln([a, b], MINW, 'key', rng)


def show_ground(rng):
    """the field in front of the stage: barricade, crowd (a skyline of heads and hands against the light), delay
    towers, FOH tent, bar tents, BIEC halls"""
    P_ = lambda xx, y, zz: pr(xx, y + gl(zz), zz)
    # BIEC exhibition halls on the left: long sheds with ribbed curved roofs
    for (x0, x1, z0, z1, hh) in ((-64, -28, 198, 250, 17), (-34, -19, 180, 222, 13)):
        fr = [P_(x1, 0, z0), P_(x1, hh, z0), P_(x0, hh, z0), P_(x0, 0, z0)]
        sd = [P_(x1, 0, z0), P_(x1, hh, z0), P_(x1, hh, z1), P_(x1, 0, z1)]
        roof = [P_(x1, hh, z0)] + [P_(x1 + (x0 - x1) * t, hh + 2.5 * math.sin(math.pi * t), z0) for t in [i / 8 for i in range(9)]]
        for p in (fr, sd, roof + [P_(x0, hh, z1), P_(x1, hh, z1)]):
            knock(p, 0.6)
        ln(roof, MINW * 1.2, 'key', rng)
        pline(fr, MINW, 'key', rng, skip=0.3)
        ln([P_(x1, hh, z0), P_(x1, hh, z1)], MINW, 'key', rng)
        for t in [i / 10 for i in range(1, 10)]:
            ln([lerp(fr[0], fr[3], t), lerp(fr[1], fr[2], t)], MINW, 'key', rng, wob=0.05)
        hatch(sd, 'key', math.pi / 2, 9, rng=rng, gap=0.08, tone=lambda px, py: 0.5)
    # light masts (warm white)

    # bar tents at the sides
    tent(-17, 168, 8, 5, 4.5, rng)
    tent(13.5, 170, 7, 5, 4.2, rng)


def crowd_band(rng, z_front=168.0, z_back=194.0, xl=-16.5, xr=12.5):
    """the crowd seen from the street: rows of heads and raised hands against the light, packed toward the stage"""
    P_ = lambda xx, y, zz: pr(xx, y + gl(zz), zz)
    rows = []
    z = z_back
    while z > z_front:
        rows.append(z)
        z -= rng.uniform(1.6, 2.4)
    for i, z in enumerate(rows):
        s = S(z)
        hr = max(MINW * 0.62, 0.13 * s)
        x = xl + rng.uniform(0, 0.6)
        heads = []
        while x < xr:
            heads.append(x)
            x += rng.uniform(0.38, 0.62) * (1.0 if z > 182 else 1.25)
        for x in heads:
            hx, hy = P_(x, 1.62 + rng.uniform(-0.12, 0.1), z)
            knock_ell(hx, hy + hr * 1.6, hr * 1.5, hr * 2.4)
            if rng.random() < 0.88:
                dot(hx, hy, hr, 'key', rng)
            if rng.random() < 0.13:
                # raised hand (or a phone light)
                ex, ey = hx + rng.uniform(-1.5, 1.5) * hr, hy - hr * rng.uniform(3.0, 4.5)
                ln([(hx + hr * 0.6, hy), (ex, ey)], MINW, 'key', rng, wob=0.05)
                if rng.random() < 0.4:
                    dot(ex, ey - 1, MINW * 0.65, 'ice', rng)
    # delay towers and the FOH tent stand up out of the crowd
    for xd in (-9.0, 6.0):
        z = 178.0
        a, b = P_(xd, 0, z), P_(xd, 11.5, z)
        knock_line([a, b], 5)
        ln([a, b], MINW, 'key', rng, wob=0.05)
        sp = [P_(xd - 0.6, 11.8, z), P_(xd - 0.6, 9.0, z), P_(xd + 0.6, 9.0, z), P_(xd + 0.6, 11.8, z)]
        sp = [(p[0] + (-4 if i < 2 else 4) * 0, p[1]) for i, p in enumerate(sp)]
        cx_ = (sp[0][0] + sp[2][0]) / 2
        box = [(cx_ - 6, sp[0][1]), (cx_ - 6, sp[1][1]), (cx_ + 6, sp[1][1]), (cx_ + 6, sp[0][1])]
        knock(box, 0.6)
        pline(box, MINW, 'key', rng)
        ln([(cx_ - 6, (box[0][1] + box[1][1]) / 2), (cx_ + 6, (box[0][1] + box[1][1]) / 2)], MINW, 'key', rng)
    tent(-1.5, 175.5, 6.5, 6, 4.6, rng, lights='amber')
    # barricade in front of the stage
    zb = 194.5
    a, b = P_(-14, 1.1, zb), P_(10, 1.1, zb)
    ln([a, b], MINW * 1.2, 'key', rng)


def gate(rng, z=93.0):
    """the end of the street: two floodlight poles where the venue's exit road begins"""
    P_ = lambda xx, y, zz: pr(xx, y + gl(zz), zz)
    for x in (-6.0, 6.0):
        a, b = P_(x, 0, z), P_(x, 8.5, z)
        knock_line([a, b], 5)
        ln([a, b], MINW, 'key', rng, wob=0.1)
        f = P_(x, 8.6, z)
        knock_ell(f[0], f[1], 6, 4)
        fillp([(f[0] - 4.5, f[1] - 2), (f[0] + 4.5, f[1] - 2), (f[0] + 3.5, f[1] + 2.5), (f[0] - 3.5, f[1] + 2.5)], 'ice')
        halo(f[0], f[1], 9, 'ice', rng, rings=2)
        light(x, 8.6, z, 'ice', wm=0.7, k=1.0, core='key', stretch=3.0)


# ============================================================ SKY: low clouds lit from below, the beams
def carve_rain(poly, layers, rng, sp=12.0, L=(7, 13), ang=1.78, prob=0.8):
    """drizzle seen against a lit surface: thin dark strokes cut out of the light (woodcut rain)"""
    x0, y0, x1, y1 = bbox(poly)
    ux, uy = math.cos(ang), math.sin(ang)
    y = y0 + rng.uniform(0, sp)
    row = 0
    while y < y1:
        x = x0 + (sp * 0.5 if row % 2 else 0) + rng.uniform(0, sp * 0.4)
        while x < x1:
            px, py = x + rng.gauss(0, sp * 0.22), y + rng.gauss(0, sp * 0.22)
            if pip(px, py, poly) and rng.random() < prob:
                l = rng.uniform(*L)
                knock_line([(px, py), (px + ux * l, py + uy * l)], MINW, layers=layers)
            x += sp * rng.uniform(0.85, 1.2)
        y += sp * rng.uniform(0.9, 1.15)
        row += 1


def cloud_mass(x0, x1, yb, rng, beams=(), ink='amber', lobe=(24, 40), rows=4, sp=9.0, top=None):
    """a long low cloud seen from below: a belly of round lobes lit warm by the city, parallel echo lines stepping up
    into it and dissolving into the dark (no top edge); white where a beam passes through"""
    pts = []
    x = x0
    while x < x1:
        r = rng.uniform(*lobe)
        r = min(r, (x1 - x) * 0.5 + 6)
        depth = r * rng.uniform(0.26, 0.36)
        cy = yb + rng.uniform(-4, 4)
        for i in range(9):
            a = math.pi * i / 8
            pts.append((x + r - math.cos(a) * r, cy + math.sin(a) * depth))
        x += 2 * r * rng.uniform(0.92, 1.0)
    hgt = top if top is not None else rows * sp + 14
    poly = pts + [(pts[-1][0], yb - hgt), (pts[0][0], yb - hgt)]
    knock(grow(poly, 1.5), 0, layers=ORDER)
    def in_beam(p):
        return any(pip(p[0], p[1], bp) for bp in beams)
    def stroke(seg, w):
        run, cur = [], None
        def put(run, cur):
            if cur and len(run) >= 3:
                ln(run, max(MINW, w * 0.6), 'ice', rng, wob=0.1, a0=1.0, a1=2.5)
            elif not cur and len(run) > 1:
                ln(run, w, ink, rng, wob=0.1, a0=1.0, a1=2.5)
        for p in seg:
            ib = in_beam(p)
            if cur is None or ib == cur:
                run.append(p)
            else:
                put(run, cur)
                run = [run[-1], p]
            cur = ib
        put(run, cur)
    cxm = (x0 + x1) / 2
    for k in range(rows + 1):
        sh = k * sp
        shrink = 1 - 0.035 * k
        row = [(cxm + (p[0] - cxm) * shrink, p[1] - sh - (p[1] - yb) * 0.25 * k / max(1, rows)) for p in pts]
        n = len(row)
        i = rng.randint(0, 4) if k else 0
        wk = MINW * max(1.0, 2.1 - 0.4 * k)
        while i < n - 2:
            L = rng.randint(14, 30) if k < 2 else rng.randint(6, 16)
            seg = row[i:i + L]
            if k < 2 or rng.random() < 0.9 - 0.15 * k:
                stroke(seg, wk)
            i += L - 1 + (0 if k < 2 else rng.randint(2, 7))


def cloud_deck(rng, beams=(), reject=None):
    """the low cloud deck over the opening: long bellies, far and thin near the horizon, big near overhead"""
    rows = [(445, (16, 26), 2, 10.0), (400, (22, 34), 2, 11.0), (350, (30, 46), 3, 12.5), (296, (40, 62), 3, 14.0)]
    for yb, lobe, nr, sp in rows:
        x = 210 + rng.uniform(0, 60)
        while x < 1000:
            L = rng.uniform(160, 300)
            if not (reject and reject(x + L / 2, yb)):
                top = min(nr * sp + 14, yb - TITLE[3] - 16)
                if top > 10:
                    cloud_mass(x, x + L, yb + rng.uniform(-8, 8), rng, beams=beams, lobe=lobe, rows=nr, sp=sp,
                               top=top)
            x += L * rng.uniform(0.75, 1.05)


def beam_poly(root, ang, L, wend):
    ux, uy = math.sin(ang), -math.cos(ang)
    nx, ny = -uy, ux
    end = (root[0] + ux * L, root[1] + uy * L)
    return [(root[0] + nx * 1.5, root[1] + ny * 1.5), (end[0] + nx * wend, end[1] + ny * wend),
            (end[0] - nx * wend, end[1] - ny * wend), (root[0] - nx * 1.5, root[1] - ny * 1.5)], end


def beam(root, ang, L, rng, wend=None, clip_y=255):
    """a white beam cutting up through the drizzle: a few long strokes fanning from the head, solid at the root and
    breaking into dashes as it climbs; drizzle visible only inside it"""
    wend = wend or L * 0.055
    poly, end = beam_poly(root, ang, L, wend)
    ux, uy = math.sin(ang), -math.cos(ang)
    nx, ny = -uy, ux
    def clipseg(p0, p1):
        if p0[1] < clip_y and p1[1] < clip_y:
            return None
        if p1[1] < clip_y:
            tt = (p0[1] - clip_y) / max(1e-6, p0[1] - p1[1])
            p1 = lerp(p0, p1, tt)
        return p0, p1
    for f, solid, w, ink in ((0.0, 0.66, 2.1, 'key'), (-0.75, 0.45, 1.4, 'ice'), (0.75, 0.45, 1.4, 'ice'),
                             (-0.3, 0.3, 1.0, 'ice'), (0.35, 0.25, 1.0, 'ice')):
        tip = (end[0] + nx * wend * f, end[1] + ny * wend * f)
        root2 = (root[0] + nx * 1.2 * f, root[1] + ny * 1.2 * f)
        t0, t1 = 0.0, solid * rng.uniform(0.9, 1.1)
        while t0 < 1.0:
            cs = clipseg(lerp(root2, tip, t0), lerp(root2, tip, min(1.0, t1)))
            if cs:
                p0, p1 = cs
                ln([p0, lerp(p0, p1, 0.5), p1], MINW * max(1.0, w - 0.5 * t0), ink if t0 < 0.5 else 'ice', rng,
                   wob=0.05, a0=0.5, a1=1.5)
            gap = rng.uniform(0.04, 0.09) * (1 + t1)
            t0 = t1 + gap
            t1 = t0 + rng.uniform(0.06, 0.16) * (1.3 - t0)
    # drizzle in the beam
    clipped = [p for p in poly]
    drizzle(clipped, 'ice', rng, sp=14, L=(8, 15), ang=1.78,
            fade=lambda px, py: (0.0 if py < clip_y + 10 else clamp(1.0 - math.hypot(px - root[0], py - root[1]) / L, 0.1, 1.0)), prob=0.55)
    return poly


# ============================================================ THE ROAD
ROAD_HW = 5.0
PAVE = 8.0


def road(rng, z0=7.2, z1=92.0):
    """kerbs (painted stones near), worn lane dashes, the median kerb under the viaduct, puddles with ripple rings"""
    for side in (-1, 1):
        zs = [z0 + (z1 - z0) * (i / 40) ** 1.6 for i in range(41)]
        top = [pr(side * ROAD_HW, 0.16, z) for z in zs]
        bot = [pr(side * ROAD_HW, 0.0, z) for z in zs]
        ln(top[:20], clamp(0.05 * S(z0), MINW, 5), 'key', rng, wob=0.2)
        ln(top[19:], MINW, 'key', rng, wob=0.2)
        # painted kerb stones (alternate) near the viewer
        z = z0
        k = 0
        while z < 34:
            if k % 2 == 0:
                q = [pr(side * ROAD_HW, 0.0, z), pr(side * ROAD_HW, 0.16, z), pr(side * ROAD_HW, 0.16, z + 1.0), pr(side * ROAD_HW, 0.0, z + 1.0)]
                if abs(q[0][1] - q[1][1]) > 3:
                    fillp(q, 'key')
            z += 1.0
            k += 1
    # lane dashes down the middle, worn thin; none in the near puddled stretch
    z = 17.0
    while z < 88:
        a, b = pr(0, 0, z), pr(0, 0, z + 3.0 * rng.uniform(0.55, 1.0))
        if abs(a[1] - b[1]) > 3 and rng.random() < 0.8:
            ln([a, b], clamp(0.12 * S(z), MINW, 5), 'key', rng, wob=0.05)
        z += 6.0 * (1 + (z - z0) / 140)


def puddle(x, z, rx, rz, rng, ink='amber', rings=2):
    """a puddle is only its rings: where the drizzle lands, small flat broken ellipses in the reflected light"""
    for k in range(rings):
        px, pz = x + rng.uniform(-0.5, 0.5) * rx, z + rng.uniform(-0.5, 0.5) * rz
        c = pr(px, 0, pz)
        s = S(pz)
        for j in range(2):
            rr = (0.16 + 0.16 * j) * s
            a0 = rng.uniform(0.1, 0.5)
            arc = ell(c[0], c[1], rr, rr * 0.24, n=12, a0=a0, a1=math.pi - rng.uniform(0.1, 0.5), rng=rng)
            RA.line(arc, MINW, layer=ink if j == 0 else 'key', rng=rng, wob=0.05, trem=0.0, a0=1, a1=2)
