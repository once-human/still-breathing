"""lib_show.py: the Namma Metro Green Line (heavy box-girder viaduct on single piers with hammerhead caps, a curved-roof
station, the last train of four stainless coaches) and the show at NICE Grounds built like a real open-ground stage,
lit the Fred again.. way (white and warm white only)."""
from kit import *
from lib_life import *
from lib_v3 import *
from lib_city import gl, SHOW_X, SHOW_Z, footage, carve_rain

# ============================================================ METRO geometry
VX = 10.5
LIFT = 4.0                             # the Green Line rides high here (over the Tumakuru Road flyover)
DB, DT, PT = 8.8, 10.4, 11.5          # soffit, deck top, parapet top
HWD = 4.25                             # half width of the box girder
TF = 45.0                              # the train's nose
NCAR, CARL = 2, 21.0
TROOF = 14.3


def vx(z):
    """the Green Line comes out from the show along the middle of the far street, swings right toward us at TF (where
    the last train's nose is), and the deck nearer than that curves away overhead behind the right-hand trees"""
    if z >= TF:
        return 6.0 + 3.0 * math.exp(-(z - TF) / 5.2)
    d = TF - z
    return 9.0 + 0.58 * d + 0.25 * d * d


def tx(z):
    return vx(z) - 2.55


def VP(dx, y, z):
    return pr(vx(z) + dx, y + LIFT, z)


def TP(dx, y, z):
    return pr(tx(z) + dx, y + LIFT, z)


def zs_(z0, z1, step=1.2):
    n = max(2, int((z1 - z0) / step))
    return [z0 + (z1 - z0) * i / n for i in range(n + 1)]


def via_span(z0, z1, rng):
    """one span of the box girder between two piers: hatched soffit lit by the lamps, the inner face, the parapet with
    wet glints on its coping, and the part of the train riding on it"""
    zs = zs_(z0, z1)
    s = S((z0 + z1) / 2)
    soff_in = [VP(-HWD + 0.7, DB, z) for z in zs]
    soff_out = [VP(HWD - 0.7, DB, z) for z in zs]
    face_b = [VP(-HWD, DB + 0.45, z) for z in zs]
    face_t = [VP(-HWD, PT, z) for z in zs]
    soffit = soff_in + soff_out[::-1]
    face = face_b + face_t[::-1]
    knock(soffit, 0.8)
    knock(face + [soff_in[-1], soff_in[0]], 0.8)
    # soffit: ribs across the deck (constant z), warm where the lamps reach, cool key elsewhere; two long lines
    for z in zs[1:-1:2]:
        a, b = VP(-HWD + 0.8, DB, z), VP(HWD - 0.8, DB, z)
        lit = lamp_lit(vx(z) - 2, DB - 1, z, r=9)
        if abs(a[0] - b[0]) < 6:
            continue
        if lit > 0.2 and rng.random() < 0.8:
            ln([a, lerp(a, b, 0.5), lerp(a, b, rng.uniform(0.45, 0.9))], MINW, 'amber', rng, wob=0.12, a0=1.0, a1=2.0)
    # the train behind the parapet
    train_span(z0, z1, rng)
    knock(face, 0.4)
    # the inner face: heavy soffit edge, chamfer, deck line, parapet coping
    wb = clamp(0.085 * s, MINW, 6.5)
    ln(soff_in, wb, 'key', rng, wob=0.15)
    ln(face_b, MINW * 1.1, 'key', rng, wob=0.15)
    ln([VP(-HWD, DT, z) for z in zs], MINW, 'key', rng, wob=0.15)
    ln(face_t, clamp(0.06 * s, MINW, 5), 'key', rng, wob=0.15)
    # parapet joints and wet glints on the coping
    zz = math.ceil(z0 / 6.0) * 6.0
    while zz < z1:
        a, b = VP(-HWD, DB + 0.5, zz), VP(-HWD, PT, zz)
        if abs(a[1] - b[1]) > 8:
            ln([a, b], MINW, 'key', rng, wob=0.08)
        zz += 6.0
    for z in zs[::3]:
        if rng.random() < 0.35:
            p = VP(-HWD, PT + 0.05, z)
            q = VP(-HWD, PT + 0.05, min(z1, z + 0.9))
            if abs(q[0] - p[0]) > 5:
                ln([p, q], MINW, 'ice', rng, wob=0.05, a0=0.6, a1=1.2)


def pier2(z, rng):
    """a tall single round pier with a wide hammerhead cap under the girder, on the right pavement"""
    s = S(z)
    xc = vx(z)
    r = 0.95
    g0, g1 = pr(xc - r, 0, z), pr(xc + r, 0, z)
    yc = 6.5 + LIFT
    t0, t1 = pr(xc - r, yc, z), pr(xc + r, yc, z)
    cap = [pr(xc - r * 1.1, yc, z), pr(xc - 3.6, yc + 1.2, z), pr(xc - 3.6, DB + LIFT, z), pr(xc + 3.6, DB + LIFT, z),
           pr(xc + 3.6, yc + 1.2, z), pr(xc + r * 1.1, yc, z)]
    col = [g0, t0, t1, g1]
    knock(col, 1.4)
    knock(cap, 1.4)
    we = clamp(0.08 * s, MINW, 6.5)
    edge(g0, t0, we, 'key', rng)                       # street side, lit
    edge(g1, t1, we * 0.7, 'key', rng)
    # round column: vertical strokes, crowded on the street (lamp) side, a few amber ones there
    lit = lamp_lit(xc - 1, 4, z, r=10)
    span = max(1, g1[0] - g0[0])
    def tone(px, py):
        f = (px - g0[0]) / span
        return clamp(0.85 - 1.0 * f, 0.0, 1.0) ** 1.4
    hatch(col, 'key', math.pi / 2, clamp(0.13 * s, 8.5, 12), rng=rng, gap=0.05, tone=tone, maxlen=60)
    if lit > 0.2:
        a, b = pr(xc - r * 0.75, 0.3, z), pr(xc - r * 0.75, yc - 0.4, z)
        ln([a, b], MINW * 1.1, 'amber', rng, wob=0.1, a0=1.5, a1=3)
    # the hammerhead cap: underside cross-hatched, edges firm
    pline(cap, we * 0.85, 'key', rng, skip=0.05)
    # the cap's underside catches the street light: two or three amber strokes along it
    for f in (0.3, 0.55):
        a_, b_ = lerp(cap[0], cap[1], f), lerp(cap[5], cap[4], f)
        if abs(b_[0] - a_[0]) > 10:
            ln([lerp(a_, b_, 0.1), lerp(a_, b_, 0.9)], MINW * 1.1, 'amber', rng, wob=0.1, a0=1.0, a1=2.0)
    # bearing pads and the plinth
    pl = [pr(xc - 1.4, 0, z - 0.9), pr(xc - 1.4, 0.4, z - 0.9), pr(xc + 1.4, 0.4, z - 0.9), pr(xc + 1.4, 0, z - 0.9)]
    knock(pl, 0.5)
    pline(pl, MINW, 'key', rng, skip=0.2)


def train_span(z0, z1, rng):
    """the part of the last train between z0 and z1: stainless coaches, lit window band full of standing passengers,
    the green stripe, doors, roof with AC housings"""
    zend = TF + NCAR * CARL
    a, b = max(z0, TF), min(z1, zend)
    if a >= b:
        return
    zs = zs_(a, b, 0.8)
    s = S((a + b) / 2)
    side = -1.45                                   # the inner side of the body
    roof = [TP(side + 0.15, TROOF, z) for z in zs]
    roof_c = [TP(0.3, TROOF + 0.3, z) for z in zs]
    low = [TP(side, PT - 0.1, z) for z in zs]
    body = roof + low[::-1]
    knock(body, 7.0)
    knock(roof + roof_c[::-1], 0.5)
    # the stainless body: solid steel-white, catching the city light
    fillp(body, 'ice')
    fillp(roof + roof_c[::-1], 'ice')
    # green stripe under the windows
    gb = [TP(side, 12.15, z) for z in zs] + [TP(side, 11.82, z) for z in zs][::-1]
    knock(gb, 0.2, layers=('ice',))
    fillp(gb, 'green')
    band_t = [TP(side, 13.70, z) for z in zs]
    band_b = [TP(side, 12.35, z) for z in zs]
    wb_poly = band_t + band_b[::-1]
    knock(wb_poly, 0.6, layers=('ice',))
    fillp(wb_poly, 'amber')
    for c in range(NCAR):
        c0 = TF + c * CARL
        zz = c0 + 0.9
        k = 0
        while zz < c0 + CARL - 0.9:
            door = (k % 3 == 1)
            w0, w1 = zz, zz + (1.3 if door else 2.0)
            wide = abs(TP(side, 12.90, w1)[0] - TP(side, 12.90, w0)[0])
            for zq in (w0, w1):
                if a < zq < b and (wide > 11 or (door and zq == w0 and wide > 5)):
                    p0, p1 = TP(side, 12.30, zq), TP(side, 13.75, zq)
                    knock_line([p0, p1], MINW * (1.2 if door else 0.95), layers=('amber',))
                    if door:
                        knock_line([TP(side, 11.60, zq), TP(side, 12.30, zq)], MINW, layers=('ice',))
            if w1 > a and w0 < b:
                q = [TP(side, 12.35, max(w0, a)), TP(side, 13.70, max(w0, a)), TP(side, 13.70, min(w1, b)),
                     TP(side, 12.35, min(w1, b))]
                hh = abs(q[0][1] - q[1][1])
                npx = int(abs(q[2][0] - q[1][0]) / max(7.0, 0.5 * s)) if wide > 11 else 0
                for i in range(npx):
                    if rng.random() < 0.7:
                        t = (i + rng.uniform(0.3, 0.7)) / max(npx, 1)
                        px, py = lerp(q[0], q[3], t)
                        hr = clamp(hh * 0.15, 2.0, 7)
                        shp = [(px - hr * 1.9, py + 1), (px - hr * 1.5, py - hh * 0.42), (px + hr * 1.5, py - hh * 0.42),
                               (px + hr * 1.9, py + 1)]
                        knock(shp, 0, layers=('amber',))
                        knock_ell(px, py - hh * 0.42 - hr * 1.05, hr, hr * 1.2, layers=('amber',))
                        if rng.random() < 0.4:
                            knock_line([(px + hr, py - hh * 0.38), (px + hr * 1.5, py - hh * 0.98)],
                                       max(MINW, hr * 0.7), layers=('amber',))
            zz = w1 + 0.35
            k += 1
        if c > 0 and a <= c0 <= b:                  # gangway
            g0, g1 = TP(side, PT, c0), TP(side, TROOF, c0)
            knock_line([g0, g1], clamp(0.45 * s, MINW, 10))
        for zh in (c0 + 4.5, c0 + CARL - 4.5):     # AC housings on the roof
            if a < zh < b:
                h0, h1 = TP(0.0, TROOF + 0.3, zh - 1.6), TP(0.0, TROOF + 0.3, zh + 1.6)
                hp = [h0, (h0[0], h0[1] - max(4, 0.35 * S(zh))), (h1[0], h1[1] - max(4, 0.35 * S(zh))), h1]
                knock(hp, 0.5)
                pline(hp, MINW, 'key', rng, closed=False)
    ln(roof, clamp(0.06 * s, MINW, 5), 'key', rng, wob=0.12)
    ln(roof_c, MINW, 'key', rng, wob=0.12)
    ln([TP(side, 14.02, z) for z in zs], MINW, 'key', rng, wob=0.12)
    ln(band_b, MINW, 'key', rng, wob=0.1)
    # wet roof: a few glints
    for z in zs[::4]:
        if rng.random() < 0.4:
            p, q = TP(-0.6, TROOF + 0.2, z), TP(-0.6, TROOF + 0.2, z + 1.2)
            if abs(q[0] - p[0]) > 5:
                ln([p, q], MINW, 'ice', rng, wob=0.05, a0=0.6, a1=1.2)


def train_nose(rng):
    """the driving cab coming toward us: rounded face, raked windscreen split by the emergency door, the destination
    band, two ringed headlights, the green stripe wrapping round"""
    z = TF
    s = S(z)
    hw = 1.45
    xc = tx(z)
    def Q(dx, y, dz=0.0):
        return pr(xc + dx, y + LIFT, z - dz)
    top = []
    for i in range(11):
        t = i / 10
        a = math.pi * t
        top.append(Q(-hw * math.cos(a), TROOF - 0.55 + 0.55 * math.sin(a) ** 0.6, 0.35 * math.sin(a)))
    face = [Q(-hw, PT - 0.15)] + top + [Q(hw, PT - 0.15)]
    knock(grow(face, 10.0), 0)
    knock(face, 3.0)
    fillp(face, 'ice')
    # one wide raked windscreen wrapping the face (no centre bar: a split pane is a bus), one long wet glint
    ws = [Q(-hw * 0.86, 12.6, 0.1), Q(-hw * 0.7, 13.78, 0.45), Q(hw * 0.7, 13.78, 0.45), Q(hw * 0.86, 12.6, 0.1)]
    knock(ws, 0.5)
    ln([lerp(ws[0], ws[1], 0.2), lerp(ws[3], ws[2], 0.75)], MINW, 'ice', rng, wob=0.05)
    pline(ws, clamp(0.06 * s, MINW, 4.5), 'key', rng)
    dz = [Q(-hw * 0.5, 13.86, 0.5), Q(-hw * 0.48, 14.12, 0.55), Q(hw * 0.48, 14.12, 0.55), Q(hw * 0.5, 13.86, 0.5)]
    knock(dz, 0.3)
    fillp(dz, 'amber')
    band = [Q(-hw, 12.30), Q(0, 12.24), Q(hw, 12.30), Q(hw, 11.9), Q(0, 11.86), Q(-hw, 11.9)]
    knock(band, 0.3, layers=('ice',))
    fillp(band, 'green')
    ln(face, clamp(0.08 * s, MINW, 6), 'key', rng, wob=0.15, redraw=0.4)
    # headlights: two long slits in the green band at the outer corners (round lamps read as a bus's wheels)
    for sx in (-1, 1):
        a_, b_ = Q(sx * hw * 0.82, 12.08), Q(sx * hw * 0.48, 12.08)
        knock_line([a_, b_], MINW * 1.6 + 6.0, layers=('green',))
        ln([a_, b_], MINW * 1.6, 'key', rng, wob=0.03)
        light(xc + sx * hw * 0.65, 12.08 + LIFT, z, 'ice', wm=0.4, k=1.0, stretch=0.8)
    return Q(0, 13.40)


def station2(rng, z0=50.0, z1=66.0):
    """an elevated Namma Metro station over the right lane: a long curved roof on columns, ribbed, the platform edge,
    lit from inside in ice; the train runs through it"""
    zs = zs_(z0, z1, 1.0)
    xi, xo = -HWD - 1.6, HWD + 2.5
    eave, crown_ = 16.6, 18.7
    s = S((z0 + z1) / 2)
    def RP(t, z):
        x = xi + (xo - xi) * t
        y = eave + (crown_ - eave) * math.sin(math.pi * clamp(t * 1.15, 0, 1)) ** 0.7
        return VP(x, y, z)
    roof_in = [RP(0.0, z) for z in zs]
    roof_top = [RP(0.42, z) for z in zs]
    shell = roof_in + roof_top[::-1]
    knock(shell + [RP(0.42, z0), RP(1.0, z0), RP(1.0, z1)], 0.8)
    # underside of the shell seen from below: ribs (constant z), ice light from the platform
    for z in zs:
        rib = [RP(t, z) for t in [i / 8 for i in range(9)]]
        ln(rib[:5], MINW, 'key', rng, wob=0.08, a0=0.8, a1=1.6)
    hatch(shell, 'ice', 0.0, 9.0, rng=rng, gap=0.15, tone=lambda px, py: 0.35, maxlen=50)
    ln(roof_in, clamp(0.08 * s, MINW, 6), 'key', rng, wob=0.12, redraw=0.3)
    ln(roof_top, clamp(0.06 * s, MINW, 5), 'key', rng, wob=0.12)
    end = [RP(t, z0) for t in [i / 10 for i in range(11)]]
    ln(end, clamp(0.07 * s, MINW, 5.5), 'key', rng, wob=0.12)
    # columns along the inner edge and the platform slab
    for z in zs[::4]:
        a, b = VP(xi + 0.3, PT - 0.4, z), VP(xi + 0.3, eave, z)
        knock_line([a, b], clamp(0.25 * S(z), MINW, 9) + 2)
        ln([a, b], clamp(0.12 * S(z), MINW, 5), 'key', rng, wob=0.08)
    plat = [VP(xi, DB + 0.6, z) for z in zs] + [VP(xi, PT - 0.4, z) for z in zs][::-1]
    knock(plat, 0.5)
    ln([VP(xi, PT - 0.4, z) for z in zs], MINW * 1.2, 'key', rng, wob=0.1)
    ln([VP(xi, DB + 0.6, z) for z in zs], MINW * 1.4, 'key', rng, wob=0.1)
    hatch(plat, 'ice', math.pi / 2, 9, rng=rng, gap=0.12, tone=lambda px, py: 0.5, maxlen=30)
    light(vx(z0 + 4) + xi, 13.0, z0 + 4, 'ice', wm=1.4, k=0.7)


# ============================================================ THE SHOW (white and warm white only)
def SP(x, y, z):
    return pr(x, y + gl(z), z)


def scaffold(x0, x1, y0, y1, z, rng, bay=2.0, lift=2.0, w=MINW, brace=True):
    """a scaffold tower face: standards, ledgers and a few diagonal braces"""
    nb = max(1, int(round((x1 - x0) / bay)))
    nl = max(1, int(round((y1 - y0) / lift)))
    for i in range(nb + 1):
        x = x0 + (x1 - x0) * i / nb
        ln([SP(x, y0, z), SP(x, y1, z)], w, 'key', rng, wob=0.05, a0=0.5, a1=0.8)
    for j in range(nl + 1):
        y = y0 + (y1 - y0) * j / nl
        ln([SP(x0, y, z), SP(x1, y, z)], w, 'key', rng, wob=0.05, a0=0.5, a1=0.8)
    if brace:
        for j in range(nl):
            if rng.random() < 0.6:
                ya, yb = y0 + (y1 - y0) * j / nl, y0 + (y1 - y0) * (j + 1) / nl
                if j % 2:
                    ln([SP(x0, ya, z), SP(x1, yb, z)], MINW, 'key', rng, wob=0.05)
                else:
                    ln([SP(x1, ya, z), SP(x0, yb, z)], MINW, 'key', rng, wob=0.05)


def show3(rng):
    """the stage at NICE Grounds: scaffold roof with a truss header, a pale sheet draped under it, the LED wall with
    coarse lo-fi footage, hanging line arrays, side scaffold wings with scrim, delay towers and the FOH tent in the
    crowd, the crowd as head arcs and raised hands, a strobe burst. Returns the beam roots."""
    zf, zb = SHOW_Z - 5, SHOW_Z + 4
    xc = SHOW_X
    xl, xr = xc - 16.5, xc + 16.5
    ry0, ry1 = 18.0, 20.6
    s = S(zf)
    # BIEC: a long low flat-roofed hall beyond the left of the stage
    hall = [SP(-40, 0, 235), SP(-40, 12.5, 235), SP(xl - 1.5, 12.5, 235), SP(xl - 1.5, 0, 235)]
    knock(hall, 0.6)
    ln([hall[1], hall[2]], MINW * 1.2, 'key', rng)
    ln([SP(-40, 11.4, 235), SP(xl - 1.5, 11.4, 235)], MINW, 'key', rng)
    for t in [i / 7 for i in range(1, 7)]:
        ln([lerp(hall[0], hall[3], t), lerp(hall[1], hall[2], t)], MINW, 'key', rng, wob=0.05, a0=0.5, a1=0.8)
    # the whole stage block knocks what is behind
    knock([SP(xl - 0.5, 0, zf), SP(xl - 0.5, ry1 + 0.5, zf), SP(xr + 0.5, ry1 + 0.5, zf), SP(xr + 0.5, 0, zf)], 0.8)
    # LED wall at the back, the whitest thing in the picture: a dot-matrix of light with lo-fi footage of a raised
    # hand left dark in it, carved scan lines and drizzle
    lx0, lx1, ly0, ly1 = xc - 9.0, xc + 9.0, 4.4, 13.4
    led = [SP(lx0, ly0, zb), SP(lx0, ly1, zb), SP(lx1, ly1, zb), SP(lx1, ly0, zb)]
    led_screen(led, rng)
    pline(led, MINW * 1.3, 'key', rng)
    # side wings: dark scrim (vertical hatching) on the scaffold towers
    for sx in (-1, 1):
        x0, x1 = (xl, xl + 3.2) if sx < 0 else (xr - 3.2, xr)
        wing = [SP(x0, 0, zf + 1.5), SP(x0, ry0, zf + 1.5), SP(x1, ry0, zf + 1.5), SP(x1, 0, zf + 1.5)]
        knock(wing, 0.6)
        pline(wing, MINW * 1.1, 'key', rng, skip=0.1)
        # side screen high on the wing: the same footage, smaller
        ss = [SP(x0 + 0.3, 8.5, zf + 1.4), SP(x0 + 0.3, 13.5, zf + 1.4), SP(x1 - 0.3, 13.5, zf + 1.4), SP(x1 - 0.3, 8.5, zf + 1.4)]
        led_screen(ss, rng, big=False)
        pline(ss, MINW, 'key', rng)
    # the roof: a low-pitched fascia, dark, cut by horizontal hatching, a firm edge; lights hung under it
    eL, eR = SP(xl - 1.2, ry0, zf), SP(xr + 1.2, ry0, zf)
    tL, tR = SP(xl - 1.2, ry0 + 1.6, zf), SP(xr + 1.2, ry0 + 1.6, zf)
    pk = SP(xc, ry0 + 4.6, zf)
    fascia = [eL, tL, pk, tR, eR]
    knock(fascia, 0.8)
    # the roof truss: two chords and a zig-zag of diagonals across the dark fascia
    n_ = 14
    for i in range(n_):
        a_ = lerp(eL, eR, i / n_)
        b_ = lerp(tL, tR, (i + 0.5) / n_)
        c_ = lerp(eL, eR, (i + 1) / n_)
        if b_[1] < a_[1] - 5:
            ln([a_, b_, c_], MINW, 'key', rng, wob=0.03, a0=0.6, a1=1.0)
    ln([tL, pk, tR], MINW * 1.6, 'key', rng, wob=0.1, redraw=0.3)
    ln([eL, eR], MINW * 1.4, 'key', rng, wob=0.08)
    ln([eL, tL], MINW * 1.2, 'key', rng)
    ln([eR, tR], MINW * 1.2, 'key', rng)
    for i in range(1, 12):
        p = lerp(eL, eR, i / 12)
        knock_ell(p[0], p[1] + 4, 3.4, 3.0)
        dot(p[0], p[1] + 4, 2.2, 'key', rng)
    # pale sheet draped under the roof: swags between hang points, fold lines converging to the points
    hangs = [xl + 1.0 + (xr - xl - 2.0) * i / 4 for i in range(5)]
    for i in range(4):
        h0, h1 = hangs[i], hangs[i + 1]
        sag = rng.uniform(1.6, 2.2)
        top_ = [SP(h0 + (h1 - h0) * t, ry0 - 0.25, zf - 0.6) for t in (0, 1)]
        swag = [SP(h0 + (h1 - h0) * t, ry0 - 0.25 - sag * math.sin(math.pi * t) ** 0.85, zf - 0.6) for t in
                [j / 10 for j in range(11)]]
        poly = [top_[0]] + swag + [top_[1]]
        knock(poly, 0.6)
        blob(poly, 'ice', rng, gap=0.0, shift=0.3, jit=0.01)
        # folds: carved lines from each hang point down into the belly
        for t in (0.22, 0.4, 0.6, 0.78):
            p_end = swag[int(t * 10)]
            p_start = top_[0] if t < 0.5 else top_[1]
            knock_line([lerp(p_start, p_end, 0.18), lerp(p_start, p_end, 0.85)], MINW, layers=('ice',))
        ln(swag, MINW * 1.2, 'key', rng, wob=0.1)
    # line arrays: J-curved columns of boxes hanging beside the screen
    for sx in (-1, 1):
        x_ = xc + sx * 12.0
        boxes = []
        for i in range(13):
            t = i / 12
            boxes.append(SP(x_, ry0 - 0.8 - 7.2 * t, zf - 0.8 - 0.8 * t ** 2))
        wdt = clamp(1.0 * s, 5, 12)
        col = [(p[0] - wdt / 2, p[1]) for p in boxes] + [(p[0] + wdt / 2, p[1]) for p in boxes][::-1]
        knock(col, 1.0)
        ln([(p[0] - wdt / 2, p[1]) for p in boxes], MINW, 'key', rng)
        ln([(p[0] + wdt / 2, p[1]) for p in boxes], MINW, 'key', rng)
        for p in boxes[2:-1:2]:
            ln([(p[0] - wdt / 2, p[1]), (p[0] + wdt / 2, p[1])], MINW, 'key', rng, wob=0.03)
        ln([SP(x_, ry0, zf - 0.8), boxes[0]], MINW, 'key', rng)
    # stage deck and the artist at the decks, a silhouette against the screen
    deck = [SP(xl + 3.2, 0, zf), SP(xl + 3.2, 2.0, zf), SP(xr - 3.2, 2.0, zf), SP(xr - 3.2, 0, zf)]
    knock(deck, 0.5)
    ln([deck[1], deck[2]], MINW * 1.5, 'key', rng)
    dk = SP(xc + 0.5, 2.0, zf + 2)
    hgt = 1.8 * S(zf + 2)
    tab = [(dk[0] - hgt * 0.55, dk[1]), (dk[0] - hgt * 0.55, dk[1] - hgt * 0.5), (dk[0] + hgt * 0.55, dk[1] - hgt * 0.5),
           (dk[0] + hgt * 0.55, dk[1])]
    knock(tab, 0.5)
    ln([tab[1], tab[2]], MINW, 'key', rng)
    body = [(dk[0] - hgt * 0.13, dk[1] - hgt * 0.45), (dk[0] - hgt * 0.15, dk[1] - hgt * 0.82),
            (dk[0] + hgt * 0.15, dk[1] - hgt * 0.82), (dk[0] + hgt * 0.13, dk[1] - hgt * 0.45)]
    knock(body, 0.6)
    knock_ell(dk[0], dk[1] - hgt * 0.92, hgt * 0.08, hgt * 0.1)
    knock_line([(dk[0] + hgt * 0.12, dk[1] - hgt * 0.78), (dk[0] + hgt * 0.3, dk[1] - hgt * 1.15)], MINW * 1.2)
    # beam heads along the header
    roots = []
    for t in (0.08, 0.2, 0.3, 0.5, 0.62, 0.72, 0.95):
        p = lerp(SP(xl + 1.5, ry0 - 0.4, zf - 0.5), SP(xr - 1.5, ry0 - 0.4, zf - 0.5), t)
        knock_ell(p[0], p[1], 4.0, 3.4)
        dot(p[0], p[1], 2.6, 'ice', rng)
        roots.append(p)
    # one strobe burst at stage level
    sb = SP(xc + 6.0, 3.2, zf - 0.6)
    knock_ell(sb[0], sb[1], 7, 5)
    fillp([(sb[0] - 6, sb[1] - 2.5), (sb[0] + 6, sb[1] - 2.5), (sb[0] + 6, sb[1] + 2.5), (sb[0] - 6, sb[1] + 2.5)], 'ice')
    for k in range(12):
        a_ = TAU * k / 12 + rng.uniform(-0.08, 0.08)
        r0, r1 = 9.5, 9.5 + (rng.uniform(14, 24) if k % 3 == 0 else rng.uniform(6, 12))
        ln([(sb[0] + math.cos(a_) * r0, sb[1] + math.sin(a_) * r0 * 0.8),
            (sb[0] + math.cos(a_) * r1, sb[1] + math.sin(a_) * r1 * 0.8)], MINW * (1.2 if k % 3 == 0 else 1.0), 'ice',
           rng, wob=0.03, a0=0.6, a1=1.5)
    # reflections of the show on the road
    light(xc, 8.5, zb, 'ice', wm=3.6, k=1.0, stretch=3.8, brk=0.1)
    light(xc - 7, 3.0, zf, 'ice', wm=1.6, k=0.9, stretch=4.2, brk=0.2)
    light(xc + 6, 3.2, zf, 'ice', wm=1.4, k=1.0, stretch=4.4, brk=0.2)
    return roots


def led_screen(q, rng, big=True):
    """the LED wall as one flat white shape with his lo-fi phone footage: one big grainy silhouette (a raised hand and
    a head) knocked out of it, coarse grain along its edges, two carved scan lines"""
    x0, y0, x1, y1 = bbox(q)
    wq, hq = x1 - x0, y1 - y0
    knock(q, 0.6)
    fillp(q, 'ice')
    cx = x0 + wq * (0.58 if big else 0.5)
    hand = [(cx - wq * 0.13, y1 + 2), (cx - wq * 0.14, y0 + hq * 0.55), (cx - wq * 0.2, y0 + hq * 0.3),
            (cx - wq * 0.16, y0 + hq * 0.26), (cx - wq * 0.09, y0 + hq * 0.45), (cx - wq * 0.08, y0 + hq * 0.12),
            (cx - wq * 0.03, y0 + hq * 0.1), (cx - wq * 0.02, y0 + hq * 0.4), (cx + wq * 0.01, y0 + hq * 0.04),
            (cx + wq * 0.06, y0 + hq * 0.06), (cx + wq * 0.05, y0 + hq * 0.42), (cx + wq * 0.09, y0 + hq * 0.12),
            (cx + wq * 0.135, y0 + hq * 0.15), (cx + wq * 0.11, y0 + hq * 0.5), (cx + wq * 0.16, y0 + hq * 0.36),
            (cx + wq * 0.2, y0 + hq * 0.4), (cx + wq * 0.13, y0 + hq * 0.7), (cx + wq * 0.11, y1 + 2)]
    if not big:
        hand = [(cx - wq * 0.3, y1 + 1), (cx - wq * 0.22, y0 + hq * 0.62), (cx + wq * 0.22, y0 + hq * 0.62),
                (cx + wq * 0.3, y1 + 1)]
    knock(hand, 0, layers=('ice',))
    hd = ell(x0 + wq * (0.24 if big else 0.5), y1 - hq * (0.32 if big else 0.55), wq * (0.11 if big else 0.16),
             hq * (0.27 if big else 0.25), n=18)
    knock(hd, 0, layers=('ice',))
    if big:
        sh = [(x0 + wq * 0.06, y1 + 1), (x0 + wq * 0.1, y1 - hq * 0.12), (x0 + wq * 0.38, y1 - hq * 0.12), (x0 + wq * 0.42, y1 + 1)]
        knock(sh, 0, layers=('ice',))
        # grain: coarse specks of light left inside the dark silhouette near its edge, and dark specks outside it
        for poly in (hand, hd):
            for i in range(0, len(poly), 2):
                p = poly[i]
                if rng.random() < 0.6:
                    knock_ell(p[0] + rng.uniform(-6, 6), p[1] + rng.uniform(-6, 6), 2.4, 2.4, layers=('ice',))
        for k in range(2):
            yy = y0 + hq * (0.3 + 0.35 * k) + rng.uniform(-3, 3)
            knock_line([(x0 + rng.uniform(0, wq * 0.2), yy), (x1 - rng.uniform(0, wq * 0.25), yy)], MINW, layers=('ice',))


def crowd_silhouettes(rng, xa, xb, y_top, y_bot, scale=1.0):
    """the crowd as black silhouettes against the stage wash: an ice band of light low over the field, cut by rows
    of heads, shoulders, raised arms and phones"""
    band = [(xa, y_top), (xb, y_top), (xb, y_bot), (xa, y_bot)]
    hatch(band, 'ice', 0.0, 6.4, rng=rng, gap=0.0, jit=0.1, tone=lambda px, py: 1.0, wob=0.1)
    fillp([(xa + 6, y_top + (y_bot - y_top) * 0.45), (xb - 6, y_top + (y_bot - y_top) * 0.45), (xb - 6, y_bot), (xa + 6, y_bot)], 'ice')
    rows = 4
    for r in range(rows):
        f = r / (rows - 1)
        hy = y_top + (y_bot - y_top) * (0.45 + 0.4 * f)
        hr = (3.0 + 1.3 * f) * scale
        x = xa + rng.uniform(0, 5)
        while x < xb - 2:
            yj = hy + rng.uniform(-2, 2)
            knock_ell(x, yj, hr, hr * 1.12, layers=('ice', 'key'))
            knock([(x - hr * 2.0, y_bot + 2), (x - hr * 1.7, yj + hr * 1.2), (x + hr * 1.7, yj + hr * 1.2), (x + hr * 2.0, y_bot + 2)], 0,
                  layers=('ice', 'key'))
            if rng.random() < 0.22:
                ex = x + rng.uniform(-0.5, 1.5) * hr
                ey = y_top - rng.uniform(2, 9)
                knock_line([(x + hr * 1.2, yj + hr * 0.5), ((x + ex) / 2 + hr * 0.6, (yj + ey) / 2), (ex, ey)],
                           max(MINW, hr * 0.75), layers=('ice', 'key'))
                if rng.random() < 0.3:
                    dot(ex, ey - 3, MINW * 0.75, 'key', rng)
            x += hr * 2.2 + rng.uniform(0.8, 3.0)


def crowd_arcs(rng, xa, xb, y_top, y_bot, scale=1.0):
    """the crowd drawn the way the rest of the street is drawn: white head arcs and shoulder lines catching the stage
    light, rows staggered, raised arms with a few phone lights; black between them"""
    knock([(xa, y_top - 14), (xb, y_top - 14), (xb, y_bot + 2), (xa, y_bot + 2)], 0)
    rows = 4
    for r in range(rows):
        f = r / (rows - 1)
        hy = y_top + (y_bot - y_top) * (0.25 + 0.65 * f)
        hr = (3.6 + 1.0 * f) * scale
        x = xa + rng.uniform(0, hr * 2)
        while x < xb - hr:
            yj = hy + rng.uniform(-1.5, 1.5)
            ink = 'ice' if rng.random() < 0.55 else 'key'
            arc = ell(x, yj, hr, hr * 1.1, n=8, a0=math.pi * 1.05, a1=math.pi * 1.95, rng=rng)
            ln(arc, MINW, ink, rng, wob=0.05)
            if r == rows - 1 and rng.random() < 0.5:     # front row: a shoulder line
                ln([(x - hr * 2.0, yj + hr * 2.0), (x - hr * 1.1, yj + hr * 1.3)], MINW, 'key', rng, wob=0.05)
            if rng.random() < 0.32:
                ex = x + rng.uniform(-0.6, 1.2) * hr
                ey = yj - hr * rng.uniform(3.2, 4.4)
                ln([(x + hr * 1.1, yj + hr * 0.4), (ex, ey)], MINW, 'key', rng, wob=0.05)
                if rng.random() < 0.35:
                    dot(ex, ey - 2.5, MINW * 0.7, 'ice', rng)
            x += hr * 2.6 + rng.uniform(0.5, 2.5)


def crowd3(rng, z_front=166.0, z_back=193.0, xl=-20.0, xr=15.5):
    """the crowd seen from the street: rows of head arcs, raised arms and a few phone lights, delay towers and the FOH
    tent standing up out of it"""
    # delay towers + FOH tent first (the crowd in front cuts their feet)
    for xd in (-11.0, 7.0):
        z = 179.0
        a, b = SP(xd, 0, z), SP(xd, 12.0, z)
        knock_line([a, b], 6)
        ln([a, b], MINW * 1.1, 'key', rng, wob=0.05)
        for yy in (3.0, 6.0, 9.0):
            ln([SP(xd - 0.6, yy, z), SP(xd + 0.6, yy + 1.5, z)], MINW, 'key', rng, wob=0.03)
        top = SP(xd, 12.0, z)
        bx = [(top[0] - 7, top[1]), (top[0] - 7, top[1] + 16), (top[0] + 7, top[1] + 16), (top[0] + 7, top[1])]
        knock(bx, 0.6)
        pline(bx, MINW, 'key', rng)
        ln([(top[0] - 7, top[1] + 8), (top[0] + 7, top[1] + 8)], MINW, 'key', rng)
    tc = SP(-1.5, 0, 176.0)
    tw, th = 26, 22
    tent_ = [(tc[0] - tw / 2, tc[1]), (tc[0] - tw / 2, tc[1] - th * 0.6), (tc[0], tc[1] - th), (tc[0] + tw / 2, tc[1] - th * 0.6),
             (tc[0] + tw / 2, tc[1])]
    knock(tent_, 0.6)
    pline(tent_, MINW * 1.1, 'key', rng, closed=False)
    fillp([(tc[0] - tw / 2 + 3, tc[1] - th * 0.55), (tc[0] + tw / 2 - 3, tc[1] - th * 0.55), (tc[0] + tw / 2 - 3, tc[1] - th * 0.3),
           (tc[0] - tw / 2 + 3, tc[1] - th * 0.3)], 'amber')
    a_, b_ = SP(xl + 1.5, 1.4, 186), SP(xr - 1.5, 1.4, 186)
    crowd_arcs(rng, a_[0], b_[0], a_[1] - 26, a_[1] + 10, scale=1.15)
    # barricade
    ln([SP(xl + 3, 1.1, 194.5), SP(xr - 3, 1.1, 194.5)], MINW * 1.2, 'key', rng)
