"""lib_life.py: rain trees, street lamps, people, vehicles"""
from kit import *

LAMPS = []   # lamp heads in world (x, h, z)


def lamp_lit(x, y, z, r=7.5):
    best = 0.0
    for lx, lh, lz in LAMPS:
        d2 = (x - lx) ** 2 + 1.6 * (y - lh) ** 2 + (z - lz) ** 2
        best = max(best, math.exp(-d2 / (r * r)))
    return best


# ============================================================ RAIN TREE
def scallop(cx, cy, rx, ry, rng, lobes=None, depth=0.18, rot=0.0):
    n = lobes or rng.randint(6, 10)
    a0 = rng.uniform(0, TAU)
    angs = sorted(a0 + TAU * (i + rng.uniform(-0.22, 0.22)) / n for i in range(n))
    pts = []
    for i in range(n):
        a1 = angs[i]
        a2 = angs[(i + 1) % n] + (TAU if i == n - 1 else 0)
        r1 = rng.uniform(0.86, 1.08)
        for k in range(6):
            t = k / 6
            a = a1 + (a2 - a1) * t
            r = r1 * (1 - depth * 0.55 + depth * math.sin(math.pi * t))
            x, y = math.cos(a) * rx * r, math.sin(a) * ry * r
            pts.append((cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot)))
    return pts


def foliage_clump(cx, cy, rx, ry, rng, lit=0.0, sky_edge=True, dens=1.0, lean=0.0):
    """one leaf mass of a rain tree seen from below at night, drawn like a woodblock: a scalloped rim lit by the lamps
    and echo scallops stacked inside it, stepping up into the dark (amber near the lamps, then green). No specks."""
    out = scallop(cx, cy, rx, ry, rng, depth=0.22 if rx > 25 else 0.16)
    knock(grow(out, 1.8), 0)
    n = len(out)
    # angles of outline points relative to the centre: lower arc = facing the street below
    def lower(p):
        return (p[1] - cy) / max(ry, 1)
    wr = MINW * (1.35 if rx > 45 else 1.2 if rx > 22 else 1.05)
    # rim, drawn lobe by lobe
    i = rng.randint(0, 5)
    while i < n:
        L = rng.randint(5, 8)
        seg = out[i:i + L + 1]
        i += L
        if len(seg) < 3:
            continue
        v = sum(lower(p) for p in seg) / len(seg)
        if v > -0.15:
            ink = 'amber' if lit > 0.22 and rng.random() < 0.85 else 'key' if rng.random() < 0.3 else 'green'
            ln(seg, wr, ink, rng, wob=0.15, a0=1.0, a1=1.8)
        elif sky_edge and rng.random() < 0.55:
            ln(seg, wr * 0.9, 'green' if rng.random() < 0.85 else 'key', rng, wob=0.15, a0=1.0, a1=1.8)
    # echo scallops inside: each one a shrunken, raised copy of the lower rim, broken into lobes
    sp = 8.2 * rng.uniform(0.95, 1.08)
    k = 1
    while True:
        f = 1 - k * sp / max(ry, 1) * 1.0
        if f < 0.12 or k > 7:
            break
        inner = [(cx + (p[0] - cx) * (f + (1 - f) * 0.12), cy + (p[1] - cy) * f - (1 - f) * ry * 0.18) for p in out]
        prob = clamp(dens * (0.95 - 0.12 * k), 0.2, 0.95)
        j = rng.randint(0, 6)
        while j < n:
            L = rng.randint(4, 7)
            seg = inner[j:j + L + 1]
            j += L + (1 if rng.random() < 0.6 else rng.randint(2, 4))
            if len(seg) < 3:
                continue
            v = sum(lower(p) for p in seg) / len(seg)
            if v < -0.45 + 0.06 * k or rng.random() > prob:
                continue
            ink = 'amber' if (lit * (1.2 - 0.3 * k) > 0.25 and rng.random() < 0.8) else 'green'
            ln(seg, MINW * 1.05, ink, rng, wob=0.15, a0=1.2, a1=2.0)
        k += 1
    return out


def drips(outline, n, ink, rng, cy):
    """water hanging from the underside of a lit leaf mass"""
    low = sorted(outline, key=lambda p: -p[1])[:max(3, len(outline) // 4)]
    for _ in range(n):
        x, y = rng.choice(low)
        l = rng.uniform(5, 10)
        ln([(x, y + 3), (x + 0.3, y + 3 + l)], MINW, ink, rng, wob=0.1, a0=0.8, a1=1.4)
        dot(x + 0.3, y + 3 + l + rng.uniform(5, 9), MINW * 0.62, ink, rng)


def tube_poly(spine, widths):
    """outline of a tube along a screen spine with a width per spine point"""
    N = normals(spine)
    Lp = [(p[0] + n[0] * w / 2, p[1] + n[1] * w / 2) for p, n, w in zip(spine, N, widths)]
    Rp = [(p[0] - n[0] * w / 2, p[1] - n[1] * w / 2) for p, n, w in zip(spine, N, widths)]
    return Lp, Rp


def interp_w(n, ws):
    k = len(ws) - 1
    out = []
    for i in range(n):
        t = i / max(n - 1, 1) * k
        j = min(int(t), k - 1)
        u = t - j
        out.append(ws[j] * (1 - u) + ws[j + 1] * u)
    return out


def bark_fill(sp, ws, rng, lit_side, lit=0.4, moss=0.3, sp_u=8.5, ink_lit='amber'):
    """tone inside a trunk or limb: long strokes running along it, crowded on the lamp-lit side, thinning into the dark,
    moss in green on the shadow side"""
    N = normals(sp)
    n = len(sp)
    wmax = max(ws)
    rows = max(1, int(wmax / sp_u))
    for r in list(range(rows)) * max(1, min(3, n // 40)):
        f = (r + 0.5) / rows - 0.5            # -0.5 .. 0.5 across
        g = 0.5 + f * lit_side                 # 1 = the lit edge
        p = 0.08 + 0.62 * g ** 2.0
        if rng.random() > p:
            continue
        i0 = int(n * rng.uniform(0.0, 0.5))
        i1 = min(n - 1, i0 + max(4, int(rng.uniform(18, 45) / 2.0)))
        seg = []
        for i in range(i0, i1, 3):
            o = f * ws[i] * 0.88 + math.sin(i * 0.17 + r * 1.7) * 1.1
            seg.append((sp[i][0] + N[i][0] * o, sp[i][1] + N[i][1] * o))
        if len(seg) < 3 or ws[i0] < sp_u * 1.2:
            continue
        if g > 0.7:
            ink = ink_lit if (lit > 0.25 and rng.random() < 0.7) else 'key'
        elif g > 0.35:
            ink = 'key'
        else:
            ink = 'green' if rng.random() < moss + 0.3 else 'key'
        ln(seg, MINW * rng.uniform(1.0, 1.15), ink, rng, wob=0.4, a0=1.6, a1=3.0)


def limb(p0, p1, d0, d1, rng, lit=0.3, rise=1.5, sway=0.8):
    """a big spreading rain-tree limb in world space: a sinuous tapering tube, toned by bark strokes"""
    m1 = (p0[0] + (p1[0] - p0[0]) * 0.33 + rng.gauss(0, sway), p0[1] + (p1[1] - p0[1]) * 0.45 + rise,
          p0[2] + (p1[2] - p0[2]) * 0.33 + rng.gauss(0, sway))
    m2 = (p0[0] + (p1[0] - p0[0]) * 0.68 + rng.gauss(0, sway), p0[1] + (p1[1] - p0[1]) * 0.82 + rise * 0.6,
          p0[2] + (p1[2] - p0[2]) * 0.68 + rng.gauss(0, sway))
    pts3 = [p0, m1, m2, p1]
    sp = catmull([pr(*p) for p in pts3], step=2.0)
    if len(sp) < 3:
        return None
    zs = [p0[2], m1[2], m2[2], p1[2]]
    ws3 = [d0 * S(zs[0]), (d0 * 0.7 + d1 * 0.3) * S(zs[1]), (d0 * 0.4 + d1 * 0.6) * S(zs[2]), d1 * S(zs[3])]
    ws = [max(MINW * 1.8, w) for w in interp_w(len(sp), [min(w, 75) for w in ws3])]
    Lp, Rp = tube_poly(sp, ws)
    poly = Lp + Rp[::-1]
    knock(poly, 1.6)
    lowL = sum(p[1] for p in Lp) > sum(p[1] for p in Rp)
    lo, hi = (Lp, Rp) if lowL else (Rp, Lp)
    wl = clamp(ws[0] * 0.08, MINW, 5.5)
    ln(lo[::2], wl, 'amber' if lit > 0.35 else 'key', rng, wob=0.4, a0=1.2, a1=3.0)
    k = len(hi)
    a = rng.randint(0, max(1, k // 3))
    ln(hi[a:a + int(k * rng.uniform(0.3, 0.6))][::2], wl * 0.75, 'key', rng, wob=0.4)
    bark_fill(sp, ws, rng, lit_side=(1 if lowL else -1), lit=lit, moss=0.2)
    return poly


def trunk(x, z, d, hf, rng, lit=0.5, moss=0.5):
    """the massive short trunk of an old rain tree, flaring at the root, moss on the shadow side"""
    dirx = -1 if x > 0 else 1
    s = S(z)
    c3 = [(x, -0.05, z), (x + dirx * 0.08, hf * 0.4, z), (x + dirx * 0.3, hf * 0.8, z), (x + dirx * 0.55, hf * 1.08, z)]
    sp = catmull([pr(*p) for p in c3], step=2.0)
    n = len(sp)
    ws = []
    for i in range(n):
        t = i / (n - 1)
        ws.append(d * s * (1.0 + 0.55 * (1 - smooth(t * 4)) + 0.12 * math.sin(t * 7 + x)))
    Lp, Rp = tube_poly(sp, ws)
    poly = Lp + Rp[::-1]
    knock(poly, 1.6)
    lit_side = Rp if dirx > 0 else Lp     # the side facing the street and its lamps
    dark_side = Lp if dirx > 0 else Rp
    w = clamp(d * s * 0.07, MINW, 7.5)
    ln(lit_side[::2], w, 'key', rng, wob=0.6, a0=1.0, a1=3.0, redraw=0.4)
    a = int(n * 0.1)
    ln(dark_side[a::2], w * 0.75, 'key', rng, wob=0.6, a0=1.0, a1=3.0)
    # root flare lines
    base = sp[0]
    wb = ws[0]
    for k in (-1, -0.4, 0.45, 1):
        bx = base[0] + k * wb * 0.5
        ln([(bx, base[1] - wb * 0.25), (bx + k * wb * 0.12, base[1] - wb * 0.05), (bx + k * wb * 0.3, base[1] + 2)],
           MINW * 1.2, 'key', rng, wob=0.3)
    bark_fill(sp, ws, rng, lit_side=(-1 if lit_side is Rp else 1), lit=lit, moss=moss, sp_u=8.0)
    return poly, sp, ws


def rain_tree(x, z, rng, d=1.25, hf=3.6, hb=8.6, ht=16.5, rs=10.0, off=0.4, ncl=34, nlimb=5, reject=None,
              zmin=7.0, maxr=92, dens=1.0, trunk_on=True, drip=True, limb_dz=(-99, 99)):
    """an old rain tree: short massive trunk, long sinuous limbs spreading over the street, a wide umbrella of leaf
    masses lit from below by the street lamps"""
    dirx = -1 if x > 0 else 1
    ccx, ccz = x + dirx * rs * off, z
    clumps = []
    for i in range(ncl):
        a = rng.uniform(0, TAU)
        r = rs * math.sqrt(rng.uniform(0.03, 1.0))
        cxw = ccx + math.cos(a) * r
        czw = ccz + math.sin(a) * r * 0.85
        if czw < zmin:
            czw = zmin + rng.uniform(0, 1.2)
        rr = r / rs
        cyw = hb + (ht - hb) * math.sqrt(max(0.0, 1 - rr * rr)) * rng.uniform(0.35, 1.0) + rng.uniform(-0.5, 0.3)
        rc = rng.uniform(1.6, 3.0) * (1.15 - 0.35 * rr)
        clumps.append((cxw, cyw, czw, rc))
    items = []
    for cxw, cyw, czw, rc in clumps:
        sx, sy = pr(cxw, cyw, czw)
        s = S(czw)
        rx = min(rc * s, maxr * rng.uniform(0.8, 1.05))
        ry = rx * rng.uniform(0.62, 0.78)
        if sy + ry < 16 or sx + rx < 10 or sx - rx > 1190:
            continue
        if reject and reject(sx, sy, rx, ry, rng):
            continue
        dist = math.sqrt(cxw ** 2 + (cyw - HC) ** 2 + czw ** 2)
        items.append((dist, cxw, cyw, czw, sx, sy, rx, ry))
    items.sort(key=lambda t: -t[0])
    fork = (x + dirx * 0.55, hf, z)
    hmid = hb + (ht - hb) * 0.5
    upper = [it for it in items if it[2] > hmid]
    lower = [it for it in items if it[2] <= hmid]
    sil = []

    def draw_clump(it):
        dist, cxw, cyw, czw, sx, sy, rx, ry = it
        lit = lamp_lit(cxw, cyw - 1.0, czw)
        o = foliage_clump(sx, sy, rx, ry, rng, lit=lit, dens=dens, lean=0.0)
        sil.append(o)
        if drip and lit > 0.3 and rx > 18 and rng.random() < 0.45:
            drips(o, rng.randint(1, 3), 'amber' if rng.random() < 0.6 else 'key', rng, sy)

    for it in upper:
        draw_clump(it)
    # limbs to the lower/outer masses
    near = [it for it in items if math.hypot(it[1] - fork[0], it[3] - fork[2]) < rs * 0.75 and it[2] < hmid + 1]
    near = [it for it in items if math.hypot(it[1] - fork[0], it[3] - fork[2]) < rs * 0.95 and it[2] < hmid + 1
            and limb_dz[0] <= it[3] - z <= limb_dz[1]]
    targets = sorted(near, key=lambda it: (it[2] - hb) - 0.55 * math.hypot(it[1] - fork[0], it[3] - fork[2]))[:max(nlimb * 3, 8)]
    rng.shuffle(targets)
    def limb_ok(a, b):
        if not reject:
            return True
        for k in range(6):
            t = k / 5
            px, py = pr(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)
            if reject(px, py, 0.0, 0.0, rng):
                return False
        return True
    done = 0
    for it in targets:
        if done >= nlimb:
            break
        p1 = (it[1], it[2] - 0.6, it[3])
        if not limb_ok(fork, p1):
            continue
        done += 1
        limb(fork, p1, d * 0.62, d * 0.18, rng, lit=lamp_lit(*p1), rise=rng.uniform(0.3, 1.0))
        if rng.random() < 0.6:
            q = (fork[0] + (p1[0] - fork[0]) * 0.55, fork[1] + (p1[1] - fork[1]) * 0.6 + 0.6,
                 fork[2] + (p1[2] - fork[2]) * 0.55)
            close = [o for o in items if math.hypot(o[1] - q[0], o[3] - q[2]) < rs * 0.45 and o is not it
                     and limb_dz[0] <= o[3] - z <= limb_dz[1]]
            if close:
                other = rng.choice(close)
                p2 = (other[1], other[2] - 0.5, other[3])
                if limb_ok(q, p2):
                    limb(q, p2, d * 0.2, d * 0.08, rng, rise=0.5, sway=0.5)
    for it in lower:
        draw_clump(it)
    if trunk_on:
        trunk(x, z, d, hf + 0.4, rng, lit=lamp_lit(x, 3.0, z, 9))
    return sil


# ============================================================ STREET LAMP
def street_lamp(x, z, rng, h=8.2, arm=1.8, cone=True, halo_on=True, refl=True):
    side = -1 if x < 0 else 1
    hx = x - side * arm
    LAMPS.append((hx, h - 0.3, z))
    if refl:
        light(hx, h - 0.3, z, 'amber', wm=0.6, k=1.0, core='key')

    def draw():
        s = S(z)
        g, t = pr(x, 0, z), pr(x, h + 0.15, z)
        w = clamp(0.16 * s, MINW, 7)
        knock_line([g, t], w + 3)
        edge(g, t, w, 'key', rng, over=(-0.5, 0.5))
        a0, a1, hd = pr(x, h + 0.1, z), pr(x - side * arm * 0.5, h + 0.45, z), pr(hx, h, z)
        ln([a0, a1, hd], max(MINW, w * 0.8), 'key', rng, wob=0.2)
        # the head: a flat housing with the lit lens under it
        hw = clamp(0.55 * s, 6, 30)
        hh = clamp(0.16 * s, 3.4, 9)
        cx, cy = hd
        house = [(cx - hw, cy - hh * 0.2), (cx - hw * 0.6, cy - hh), (cx + hw * 0.6, cy - hh), (cx + hw, cy - hh * 0.2),
                 (cx + hw * 0.7, cy + hh * 0.5), (cx - hw * 0.7, cy + hh * 0.5)]
        knock(house, 1.0)
        fillp([(cx - hw * 0.8, cy), (cx + hw * 0.8, cy), (cx + hw * 0.55, cy + hh * 0.9), (cx - hw * 0.55, cy + hh * 0.9)], 'amber')
        pline(house[:4], max(MINW, w * 0.7), 'key', rng, closed=False)
        if halo_on:
            halo(cx, cy + hh * 0.3, clamp(0.85 * s, 10, 36), 'amber', rng, rings=3 if s > 40 else 2)
        if cone:
            # a cone of light falling from the head: drizzle only where it crosses the light
            r0 = 3.4
            foot = [pr(hx - r0, 0, z), pr(hx + r0, 0, z)]
            apex = (cx, cy + hh)
            poly = [(apex[0] - hw * 0.6, apex[1]), (apex[0] + hw * 0.6, apex[1]), foot[1], foot[0]]
            L = max(1, foot[0][1] - apex[1])
            drizzle(poly, 'amber', rng, sp=clamp(0.42 * s, 11, 19), L=(clamp(0.3 * s, 8, 15), clamp(0.55 * s, 12, 26)),
                    fade=lambda px, py: clamp(1.05 - (py - apex[1]) / L * 0.95, 0.0, 1.0) ** 1.3 *
                    clamp(1.2 - abs(px - apex[0]) / (abs(foot[1][0] - foot[0][0]) * 0.5 + 1), 0, 1), prob=0.8)
    return draw


# ============================================================ PEOPLE
ARM = {  # (upper-arm angle, forearm angle) from straight down; positive = outward
    'swing': (0.10, 0.02), 'swing_b': (-0.08, -0.25), 'up': (2.75, 3.0), 'wave': (1.55, 2.75), 'phone': (0.3, -2.55),
    'out': (0.75, 1.35), 'hold': (0.12, -0.35), 'jacket': (2.45, 2.85), 'pocket': (0.14, -0.3), 'around': (1.25, 1.6),
    'umbrella': (0.35, -2.2), 'glass': (0.18, -1.9), 'fold': (0.2, -1.75), 'hang': (0.05, 0.0), 'chin': (0.25, -2.85),
}


def tube(pts, ws, step=1.5):
    sp = catmull(pts, step=step)
    return sp, interp_w(len(sp), ws)


def egg(cx, cy, rx, ry, n=22, jaw=0.2, rot=0.0):
    out = []
    for i in range(n):
        a = TAU * i / n
        x, y = math.cos(a) * rx, math.sin(a) * ry
        if y > 0:
            x *= 1 - jaw * (y / ry) ** 2
        out.append((cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot)))
    return out


def figure(fx, fy, h, rng, facing='front', stride=0.35, arms=('swing', 'swing'), top='tee', bottom='jeans',
           tcol='amber', bcol=None, hair='short', hcol=None, lean=0.0, tilt=0.0, face_up=False, band=True, laugh=False,
           phone_lit=False, shoes=True, draw=True, w=None, fill_top=True, arm_len=1.0, sep=None, beard=False):
    """a person as a hand contour drawing with selective spot fills. (fx, fy) = between the feet, h = height (units).
    Weight shift (hip and shoulder tilt), gesture from the arm modes, clothes, hair. Returns joints + silhouettes."""
    u = h
    side = facing in ('left', 'right')
    dirx = -1 if facing == 'left' else 1 if facing == 'right' else 0
    k = 0.6 if side else 1.0
    w = w or clamp(0.019 * u, MINW, 5.2)
    sep = sep if sep is not None else max(1.0, 0.008 * u)
    sh = lambda f: lean * u * f
    tw = rng.uniform(-1, 1) * 0.014 * u          # contrapposto
    hipc = (fx + sh(0.5) + tw * 0.6, fy - 0.5 * u)
    neck = (fx + sh(0.84) + dirx * 0.012 * u, fy - 0.835 * u)
    hc = (neck[0] + tilt * 0.04 * u + dirx * 0.014 * u, fy - 0.918 * u - (0.004 * u if face_up else 0))
    hrx, hry = 0.052 * u * (0.98 if side else 1), 0.064 * u
    sL = (neck[0] - 0.122 * u * k, neck[1] + 0.03 * u - tw * 0.5)
    sR = (neck[0] + 0.122 * u * k, neck[1] + 0.03 * u + tw * 0.5)
    hL = (hipc[0] - 0.05 * u * k, hipc[1] + tw)
    hR = (hipc[0] + 0.05 * u * k, hipc[1] - tw)
    J = dict(neck=neck, head=hc, hr=(hrx, hry), sL=sL, sR=sR, hipc=hipc, u=u)
    sil = []
    legs = []
    lead_i = rng.choice((-1, 1))
    for i, hp in ((-1, hL), (1, hR)):
        lead = (i == lead_i) and stride > 0
        if side:
            fxo = dirx * stride * 0.16 * u * (1 if lead else -0.8)
            foot = (hp[0] + fxo, fy - (0.0 if lead else stride * 0.035 * u))
            knee = ((hp[0] + foot[0]) / 2 + dirx * 0.03 * u * (1.0 if lead else 0.2), (hp[1] + foot[1]) / 2 + 0.01 * u)
        else:
            lift = stride * 0.045 * u if lead else 0
            weight = (i * tw) > 0
            foot = (hp[0] + i * (0.018 if not weight else 0.0) * u, fy - lift)
            knee = ((hp[0] + foot[0]) / 2 + i * (0.012 * u if not weight else 0.004 * u), (hp[1] + foot[1]) / 2 - lift * 0.3)
        legs.append([hp, knee, foot, i])
    arml = []
    for i, sp_, mode in ((-1, sL, arms[0]), (1, sR, arms[1])):
        if isinstance(mode, tuple):
            a1, a2 = mode
        else:
            a1, a2 = ARM.get(mode, ARM['swing'])
            a1 += rng.gauss(0, 0.06)
            a2 += rng.gauss(0, 0.08)
        o = i
        if side and mode in ('swing', 'swing_b'):
            a1 += rng.uniform(-0.35, 0.35) * i * dirx
        lu, lf = 0.18 * u * arm_len, 0.16 * u * arm_len
        el = (sp_[0] + math.sin(a1) * lu * o, sp_[1] + math.cos(a1) * lu)
        wr = (el[0] + math.sin(a2) * lf * o, el[1] + math.cos(a2) * lf)
        arml.append((sp_, el, wr, i, mode))
    J['wrists'] = [a[2] for a in arml]
    J['elbows'] = [a[1] for a in arml]
    J['feet'] = [l[2] for l in legs]
    if not draw:
        return J
    if bcol is None and bottom in ('jeans',) and rng.random() < 0.45:
        bcol = 'ice'

    def leg(hp, knee, foot, i, inner_from=0.22):
        sp, ws = tube([hp, knee, foot], [0.112 * u, 0.068 * u, 0.05 * u])
        Lp, Rp = tube_poly(sp, ws)
        poly = Lp + Rp[::-1]
        knock(poly, sep)
        fill = bcol if bottom in ('jeans', 'trousers', 'shorts', 'skirt') else None
        cut = len(Lp) if bottom != 'shorts' else int(len(Lp) * 0.58)
        if fill:
            blob(Lp[:cut] + Rp[:cut][::-1], fill, rng, shift=0.7, gap=0.05, jit=0.03)
        outer, inner = (Lp, Rp) if (i < 0) == (Lp[len(Lp) // 2][0] < Rp[len(Rp) // 2][0]) else (Rp, Lp)
        a = int(len(inner) * (inner_from if not side else 0.05))
        ln(outer[::3], w, 'key', rng, wob=0.25, trem=0.25)
        ln(inner[a::3], w * 0.9, 'key', rng, wob=0.25, trem=0.25)
        if bottom == 'shorts':
            ln([Lp[cut], Rp[cut]], w * 0.9, 'key', rng)
        elif u > 70:
            m = len(Lp) - 3
            ln([Lp[m], Rp[m]], w * 0.8, 'key', rng)
        sil.append(poly)
        if shoes:
            fl = 0.075 * u if side else 0.05 * u
            fw = 0.032 * u
            if side:
                shoe = [(foot[0] - dirx * fl * 0.35, foot[1] - fw), (foot[0] + dirx * fl * 0.55, foot[1] - fw * 0.7),
                        (foot[0] + dirx * fl, foot[1] + 0.002 * u), (foot[0] - dirx * fl * 0.4, foot[1] + 0.004 * u)]
            else:
                shoe = [(foot[0] - fl * 0.55, foot[1] - fw), (foot[0] + fl * 0.55, foot[1] - fw),
                        (foot[0] + fl * 0.62 + i * 0.01 * u, foot[1] + 0.004 * u), (foot[0] - fl * 0.62 + i * 0.01 * u, foot[1] + 0.004 * u)]
            knock(shoe, sep * 0.6)
            pline(shoe, w * 0.9, 'key', rng, skip=0.2)

    def torso():
        hem = {'tee': 0.04, 'shirt': 0.05, 'top': 0.0, 'jacket': 0.1, 'hoodie': 0.08, 'kurta': 0.2, 'dress': 0.24,
               'poncho': 0.2}.get(top, 0.04) * u
        flare = {'jacket': 0.012, 'kurta': 0.03, 'dress': 0.07, 'poncho': 0.08}.get(top, 0.004) * u
        dl = (sL[0] - 0.012 * u * k, sL[1] + 0.03 * u)
        dr = (sR[0] + 0.012 * u * k, sR[1] + 0.03 * u)
        aL = (sL[0] + 0.006 * u * k, sL[1] + 0.1 * u)
        aR = (sR[0] - 0.006 * u * k, sR[1] + 0.1 * u)
        wL = (hipc[0] - 0.078 * u * k + sh(0.1), hipc[1] - 0.11 * u)
        wR = (hipc[0] + 0.078 * u * k + sh(0.1), hipc[1] - 0.11 * u)
        eL = (hL[0] - 0.045 * u * k - flare, hL[1] + hem)
        eR = (hR[0] + 0.045 * u * k + flare, hR[1] + hem)
        col = (neck[0], neck[1] + (0.03 * u if facing == 'front' else 0.008 * u))
        nL = (neck[0] - 0.04 * u * k, neck[1] + 0.004 * u)
        nR = (neck[0] + 0.04 * u * k, neck[1] + 0.004 * u)
        poly = [nL, (sL[0] + 0.02 * u * k, sL[1] - 0.012 * u), sL, dl, aL, wL, eL, eR, wR, aR, dr, sR,
                (sR[0] - 0.02 * u * k, sR[1] - 0.012 * u), nR, col]
        knock(poly, sep)
        if fill_top and tcol:
            blob(poly, tcol, rng, shift=0.8, gap=0.08, jit=0.03)
        ln([aL, wL, eL], w, 'key', rng, wob=0.3)
        ln([aR, wR, eR], w, 'key', rng, wob=0.3)
        ln([eL, ((eL[0] + eR[0]) / 2, (eL[1] + eR[1]) / 2 + 0.006 * u), eR], w * 0.9, 'key', rng)
        ln([nL, (sL[0] + 0.02 * u * k, sL[1] - 0.012 * u), sL, dl], w, 'key', rng, wob=0.2)
        ln([nR, (sR[0] - 0.02 * u * k, sR[1] - 0.012 * u), sR, dr], w, 'key', rng, wob=0.2)
        if facing != 'back':
            ln([nL, col, nR], w * 0.85, 'key', rng)
        if top in ('jacket', 'shirt') and facing == 'front' and u > 70:
            ln([col, (col[0] + 0.004 * u, (col[1] + eL[1]) / 2), (col[0] + 0.002 * u, eL[1])], w * 0.8, 'key', rng)
            if top == 'jacket':
                ln([nL, (col[0] - 0.03 * u, col[1] + 0.06 * u)], w * 0.8, 'key', rng)
                ln([nR, (col[0] + 0.03 * u, col[1] + 0.06 * u)], w * 0.8, 'key', rng)
        if u > 110:   # a fold or two where the cloth creases at the waist
            for s_ in (-1, 1):
                if rng.random() < 0.6:
                    p0 = (hipc[0] + s_ * 0.05 * u * k, hipc[1] - 0.06 * u)
                    ln([p0, (p0[0] + s_ * 0.025 * u, p0[1] + 0.02 * u)], MINW, 'key', rng, wob=0.1)
        sil.append(poly)

    def arm(sp_, el, wr, i, mode):
        sp, ws = tube([sp_, el, wr], [0.066 * u, 0.05 * u, 0.038 * u])
        Lp, Rp = tube_poly(sp, ws)
        poly = Lp + Rp[::-1]
        knock(poly, sep)
        sleeve = {'tee': 0.42, 'top': 0.2, 'dress': 0.12, 'shirt': 0.97 if (i + int(u)) % 2 else 0.58, 'jacket': 1.0,
                  'hoodie': 1.0, 'kurta': 0.9, 'poncho': 0.6}.get(top, 0.45)
        ns = int(len(Lp) * sleeve)
        if ns > 2 and fill_top and tcol:
            blob(Lp[:ns] + Rp[:ns][::-1], tcol, rng, shift=0.6, gap=0.0, jit=0.03)
        ln(Lp[2::3], w * 0.95, 'key', rng, wob=0.25)
        ln(Rp[2::3], w * 0.95, 'key', rng, wob=0.25)
        if 2 < ns < len(Lp) - 2:
            ln([Lp[ns - 1], Rp[ns - 1]], w * 0.85, 'key', rng)
        d = (wr[0] - el[0], wr[1] - el[1])
        L = math.hypot(*d) or 1
        hx, hy = wr[0] + d[0] / L * 0.035 * u, wr[1] + d[1] / L * 0.035 * u
        hand_ = egg(hx, hy, 0.026 * u, 0.038 * u, n=10, jaw=0.3, rot=math.atan2(d[1], d[0]) - math.pi / 2)
        knock(hand_, sep * 0.6)
        ln(hand_ + [hand_[0]], w * 0.85, 'key', rng, wob=0.1)
        if u > 120:   # a thumb
            tx, ty = hx - d[1] / L * 0.03 * u * i, hy + d[0] / L * 0.03 * u * i
            ln([(hx, hy), (tx, ty)], MINW, 'key', rng, wob=0.05)
        sil.append(hand_)
        sil.append(poly)
        if band and u > 55 and rng.random() < 0.65:
            nx, ny = -d[1] / L, d[0] / L
            bx, by = wr
            ln([(bx + nx * 0.022 * u, by + ny * 0.022 * u), (bx - nx * 0.022 * u, by - ny * 0.022 * u)],
               max(MINW, 0.014 * u), rng.choice(('copper', 'amber', 'ice')), rng, wob=0.05)
        return (hx, hy)

    def head():
        nk = [(neck[0] - 0.024 * u * k, neck[1] + 0.01 * u), (hc[0] - 0.022 * u, hc[1] + hry * 0.6),
              (hc[0] + 0.022 * u, hc[1] + hry * 0.6), (neck[0] + 0.024 * u * k, neck[1] + 0.01 * u)]
        knock(nk, sep * 0.6)
        ln([nk[0], nk[1]], w * 0.8, 'key', rng)
        ln([nk[3], nk[2]], w * 0.8, 'key', rng)
        rot = tilt * 0.3 + (-0.25 * (dirx or 1) if face_up else 0)
        hd = egg(hc[0], hc[1], hrx, hry, n=22, jaw=0.22, rot=rot)
        knock(grow(hd, 1.0), sep)
        sil.append(hd)
        n = len(hd)
        # hd index: 0 = right, n/4 = bottom (chin), n/2 = left, 3n/4 = crown
        def arc(f0, f1):
            i0, i1 = int(n * f0), int(n * f1)
            return [hd[i % n] for i in range(i0, i1 + 1)]
        if facing == 'back':
            hairmass = arc(0.38, 1.12)
            if hair in ('long', 'pony'):
                fall = 0.17 * u if hair == 'long' else 0.07 * u
                hm = arc(0.47, 1.03) + [(hc[0] + hrx * 1.1, hc[1] + fall), (hc[0], hc[1] + fall * 1.1),
                                        (hc[0] - hrx * 1.1, hc[1] + fall)]
                knock(hm, 0.6)
                if hcol:
                    blob(hm, hcol, rng, gap=0.0, shift=0.5)
                ln(hm + [hm[0]], w, 'key', rng, wob=0.25)
                for j in range(3 if u > 60 else 1):
                    x0 = hc[0] + rng.uniform(-0.6, 0.6) * hrx
                    ln([(x0, hc[1] - hry * 0.5), (x0 + rng.uniform(-2, 2), hc[1] + fall * 0.8)], MINW, 'key', rng)
            else:
                ln(arc(0.3, 1.2), w, 'key', rng, wob=0.2)
                if hcol:
                    blob(hd, hcol, rng, gap=0.0)
                if u > 70:
                    for s_ in (-1, 1):
                        ex = hc[0] + s_ * hrx * 0.98
                        ln(ell(ex, hc[1] + hry * 0.05, 0.013 * u, 0.022 * u, n=6, a0=-1.3 if s_ > 0 else math.pi - 1.3,
                               a1=1.3 if s_ > 0 else math.pi + 1.3, rng=rng), MINW, 'key', rng)
                    ln([(hc[0] - hrx * 0.7, hc[1] + hry * 0.3), (hc[0], hc[1] + hry * 0.42), (hc[0] + hrx * 0.7, hc[1] + hry * 0.3)], MINW, 'key', rng)
            if hair == 'bun':
                bn = ell(hc[0], hc[1] - hry * 0.8, hrx * 0.45, hry * 0.38, n=10, rng=rng)
                knock(bn, 0.5)
                ln(bn, w * 0.9, 'key', rng)
            if hair == 'cap':
                ln([(hc[0] - hrx * 1.05, hc[1] - hry * 0.1), (hc[0] + hrx * 1.05, hc[1] - hry * 0.1)], w, 'key', rng)
            return
        # front / side: face contour, hair, features
        if side:
            # profile: back of the skull + forehead, nose, lips, chin on the facing side
            f = dirx
            pts = [(hc[0] - f * hrx * 0.95, hc[1] - hry * 0.1), (hc[0] - f * hrx * 0.6, hc[1] - hry * 0.9),
                   (hc[0] + f * hrx * 0.4, hc[1] - hry * 0.98), (hc[0] + f * hrx * 0.95, hc[1] - hry * 0.45),
                   (hc[0] + f * hrx * 1.0, hc[1] - hry * 0.05), (hc[0] + f * hrx * 1.28, hc[1] + hry * 0.15),
                   (hc[0] + f * hrx * 1.0, hc[1] + hry * 0.3), (hc[0] + f * hrx * 1.06, hc[1] + hry * 0.5),
                   (hc[0] + f * hrx * 0.95, hc[1] + hry * 0.62), (hc[0] + f * hrx * 0.78, hc[1] + hry * 0.92),
                   (hc[0] + f * hrx * 0.2, hc[1] + hry * 0.85), (hc[0] - f * hrx * 0.15, hc[1] + hry * 0.6)]
            knock(pts, sep)
            ln(pts[3:11], w, 'key', rng, wob=0.15)
            hm = pts[:4] + [(hc[0] + f * hrx * 0.5, hc[1] - hry * 0.55), (hc[0] - f * hrx * 0.05, hc[1] - hry * 0.1),
                            (hc[0] - f * hrx * 0.2, hc[1] + hry * (0.9 if hair in ('long', 'pony') else 0.45))]
            if hair in ('long',):
                hm.insert(0, (hc[0] - f * hrx * 1.1, hc[1] + 0.16 * u))
                hm.append((hc[0] - f * hrx * 0.4, hc[1] + 0.16 * u))
            knock(hm, 0.5)
            if hcol:
                blob(hm, hcol, rng, gap=0.0)
            ln(hm + [hm[0]], w * 0.95, 'key', rng, wob=0.2)
            if u > 80:
                ex = hc[0] + f * hrx * 0.62
                dot(ex, hc[1] - hry * 0.1, MINW * 0.6, 'key', rng)
            return
        face = arc(0.0, 0.5)
        ln(face, w, 'key', rng, wob=0.15)
        for s_ in (-1, 1):   # ears
            if u > 70:
                ex = hc[0] + s_ * hrx * 1.0
                ln(ell(ex + s_ * 0.008 * u, hc[1] + hry * 0.05, 0.012 * u, 0.02 * u, n=6,
                       a0=-1.4 if s_ > 0 else math.pi - 1.4, a1=1.4 if s_ > 0 else math.pi + 1.4, rng=rng), MINW, 'key', rng)
        if hair != 'bald':
            crown = [(hc[0] + math.cos(a) * hrx * 1.1, hc[1] - hry * 0.05 + math.sin(a) * hry * 1.08)
                     for a in [math.pi * (1.0 + i / 12) for i in range(13)]]
            line_ = [(hc[0] + hrx * 1.02, hc[1] - hry * 0.05), (hc[0] + hrx * 0.4, hc[1] - hry * 0.5),
                     (hc[0] - hrx * 0.1, hc[1] - hry * 0.42), (hc[0] - hrx * 0.7, hc[1] - hry * 0.52),
                     (hc[0] - hrx * 1.02, hc[1] - hry * 0.05)]
            hm = crown + line_
            if hair in ('long', 'pony'):
                fall = 0.17 * u if hair == 'long' else 0.06 * u
                hm = [(hc[0] - hrx * 1.3, hc[1] + fall)] + crown + [(hc[0] + hrx * 1.3, hc[1] + fall),
                                                                       (hc[0] + hrx * 0.95, hc[1] + fall * 0.9),
                                                                       (hc[0] + hrx * 0.9, hc[1] - hry * 0.2)] + line_[1:-1] + \
                     [(hc[0] - hrx * 0.9, hc[1] - hry * 0.2), (hc[0] - hrx * 0.95, hc[1] + fall * 0.9)]
            if hair == 'curly':
                hm = scallop(hc[0], hc[1] - hry * 0.35, hrx * 1.25, hry * 0.85, rng, lobes=8, depth=0.3)
                hm = [p for p in hm if p[1] < hc[1] - hry * 0.1] or hm
            knock(hm, 0.6)
            if hcol:
                blob(hm, hcol, rng, gap=0.0, shift=0.5)
            ln(hm + [hm[0]], w * 0.95, 'key', rng, wob=0.2)
            if hair == 'bun':
                bn = ell(hc[0] + hrx * 0.3, hc[1] - hry * 1.15, hrx * 0.42, hry * 0.34, n=10, rng=rng)
                knock(bn, 0.5)
                ln(bn, w * 0.9, 'key', rng)
            if hair == 'cap':
                ln([(hc[0] - hrx * 1.1, hc[1] - hry * 0.45), (hc[0] + hrx * 1.1, hc[1] - hry * 0.45),
                    (hc[0] + hrx * 0.6, hc[1] - hry * 0.25), (hc[0] - hrx * 0.6, hc[1] - hry * 0.25)], w, 'key', rng)
        if u > 120:
            ey = hc[1] + (-0.006 * u if not face_up else -0.016 * u)
            for e in (-1, 1):
                ex = hc[0] + e * 0.021 * u
                if laugh or face_up:
                    ln([(ex - 0.011 * u, ey + 0.003 * u), (ex, ey - 0.005 * u), (ex + 0.011 * u, ey + 0.003 * u)], MINW, 'key', rng, wob=0.05)
                else:
                    dot(ex, ey, MINW * 0.62, 'key', rng)
            nxp = hc[0] + rng.choice((-1, 1)) * 0.004 * u
            ln([(nxp, ey + 0.008 * u), (nxp + 0.006 * u, ey + 0.024 * u), (nxp - 0.002 * u, ey + 0.026 * u)], MINW, 'key', rng, wob=0.05)
            my = ey + 0.04 * u
            if laugh:
                m = ell(hc[0], my, 0.017 * u, 0.011 * u, n=10, a0=0, a1=math.pi, rng=rng)
                ln(m + [m[0]], MINW, 'key', rng, wob=0.05)
            else:
                ln([(hc[0] - 0.012 * u, my), (hc[0] + 0.012 * u, my + 0.002 * u)], MINW, 'key', rng, wob=0.05)
            if beard:
                ln(arc(0.05, 0.45), MINW * 1.2, 'key', rng)

    hands = []
    for lg in sorted(legs, key=lambda l: l[2][1]):
        leg(*lg)
    if facing == 'back':
        torso()
        for a in arml:
            hands.append(arm(*a))
        head()
    else:
        torso()
        later = []
        for a in arml:
            if a[4] in ('up', 'jacket', 'wave', 'umbrella', 'phone', 'chin'):
                later.append(a)
            else:
                hands.append(arm(*a))
        head()
        for a in later:
            hands.append(arm(*a))
    J['hands'] = hands
    J['sil'] = sil
    if phone_lit:
        for a in arml:
            if a[4] in ('phone', 'up'):
                px, py = hands[-1] if a[4] == 'up' else a[2]
                ph = [(px - 0.024 * u, py - 0.08 * u), (px + 0.024 * u, py - 0.08 * u), (px + 0.024 * u, py - 0.005 * u),
                      (px - 0.024 * u, py - 0.005 * u)]
                knock(ph, 0.6)
                fillp(grow(ph, -0.8), 'ice')
                pline(ph, MINW, 'key', rng, skip=0.3)
    return J


def small_person(fx, fy, h, rng, col=None, facing=None, arms=None, umb=None):
    """a far figure: a few decisive marks, still a gesture"""
    facing = facing or rng.choice(('front', 'front', 'back', 'left', 'right'))
    arms = arms or rng.choice((('swing', 'swing'), ('swing', 'swing'), ('pocket', 'swing'), ('swing', 'up'),
                               ('phone', 'swing'), ('swing', 'hold')))
    col = col if col is not None else rng.choice(('amber', 'copper', 'green', 'ice', None, None, 'key'))
    J = figure(fx, fy, h, rng, facing=facing, arms=arms, tcol=col if col != 'key' else None,
               bcol=rng.choice((None, None, 'ice')) if h > 45 else None, hair=rng.choice(('short', 'long', 'curly', 'bun', 'short', 'cap')),
               stride=rng.uniform(0.0, 0.6), w=MINW, band=h > 50, shoes=h > 40, lean=rng.gauss(0, 0.02))
    if umb:
        umbrella_open(J, rng, umb)
    return J


def umbrella_open(J, rng, col='green', hand=1):
    u = J['u']
    hx, hy = J['head']
    cx, cy = hx + rng.uniform(-0.03, 0.05) * u, hy - 0.2 * u
    rx, ry = 0.3 * u, 0.12 * u
    n = rng.randint(6, 8)
    rim = []
    for i in range(n + 1):
        a = math.pi + math.pi * i / n
        rim.append((cx + math.cos(a) * rx, cy + ry * 0.15 + math.sin(a) * 0 + (0 if i % 1 else 0)))
    dome = ell(cx, cy + ry * 0.15, rx, ry, n=16, a0=math.pi, a1=TAU, rng=rng)
    edge_ = []
    for i in range(n):
        a, b = rim[i], rim[i + 1]
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - 0.02 * u)
        edge_ += [a, m]
    edge_.append(rim[-1])
    poly = dome + edge_[::-1]
    knock(poly, 1.2)
    if col:
        blob(poly, col, rng, gap=0.1)
    w = clamp(0.017 * u, MINW, 5)
    ln(dome, w, 'key', rng)
    ln(edge_, w * 0.85, 'key', rng)
    top = (cx, cy + ry * 0.15 - ry)
    for p in rim[1:-1]:
        ln([top, ((top[0] + p[0]) / 2, (top[1] + p[1]) / 2 - 0.01 * u), p], MINW, 'key', rng)
    dot(top[0], top[1] - 0.015 * u, MINW * 0.7, 'key', rng)
    ln([(cx, cy + ry * 0.15), (cx + 0.01 * u, hy + 0.1 * u)], MINW, 'key', rng)
    return poly


def umbrella_closed(x, y, u, rng, col='green', ang=0.15):
    """a furled umbrella hanging from a hand at (x, y)"""
    L = 0.5 * u
    ux, uy = math.sin(ang), math.cos(ang)
    nx, ny = -uy, ux
    hook = ell(x - nx * 0.025 * u, y - 0.015 * u, 0.025 * u, 0.025 * u, n=8, a0=math.pi, a1=TAU, rng=rng)
    b0 = (x + ux * 0.06 * u, y + uy * 0.06 * u)
    mid = (x + ux * L * 0.45, y + uy * L * 0.45)
    tip = (x + ux * L, y + uy * L)
    wdt = 0.03 * u
    poly = [b0, (mid[0] + nx * wdt, mid[1] + ny * wdt), tip, (mid[0] - nx * wdt, mid[1] - ny * wdt)]
    knock(poly, 1.0)
    if col:
        blob(poly, col, rng, gap=0.0)
    pline(poly, MINW, 'key', rng, skip=0.15)
    ln(hook + [b0], MINW, 'key', rng)


def glass(x, y, u, rng):
    gw, gh = 0.03 * u, 0.06 * u
    g = [(x - gw, y - gh), (x + gw, y - gh), (x + gw * 0.8, y + gh * 0.4), (x - gw * 0.8, y + gh * 0.4)]
    knock(g, 0.6)
    fillp(grow(g, -0.5), 'amber')
    ln([(x - gw * 1.1, y - gh), (x + gw * 1.1, y - gh)], MINW, 'key', rng)


def dog_curled(x, y, s, rng):
    """a stray asleep, curled nose to tail; s = body length in units"""
    body = ell(x, y, s * 0.5, s * 0.28, n=18, rng=rng, j=0.04)
    knock(body, 1.2)
    w = clamp(s * 0.05, MINW, 4.5)
    ln(body[3:17], w, 'key', rng)
    head = ell(x - s * 0.33, y + s * 0.02, s * 0.17, s * 0.13, n=12, rng=rng)
    ln(head[:9], w * 0.9, 'key', rng)
    ln([(x - s * 0.38, y - s * 0.1), (x - s * 0.33, y - s * 0.21), (x - s * 0.26, y - s * 0.1)], w * 0.85, 'key', rng)
    ln([(x + s * 0.45, y + s * 0.1), (x + s * 0.2, y + s * 0.22), (x - s * 0.2, y + s * 0.2)], w * 0.9, 'key', rng)
    hatch(body, 'amber', 0.2, 7.5, rng=rng, tone=lambda px, py: 0.8 if py < y else 0.0, maxlen=s * 0.3)


# ============================================================ VEHICLES (small 3D models drawn by hand)
def xf(p, pos, yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return (pos[0] + p[0] * c + p[2] * s, pos[1] + p[1], pos[2] - p[0] * s + p[2] * c)


def xn(n, yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return (n[0] * c + n[2] * s, n[1], -n[0] * s + n[2] * c)


def vis(ptsw, nw):
    cx = sum(p[0] for p in ptsw) / len(ptsw)
    cy = sum(p[1] for p in ptsw) / len(ptsw)
    cz = sum(p[2] for p in ptsw) / len(ptsw)
    return nw[0] * (0 - cx) + nw[1] * (HC - cy) + nw[2] * (0 - cz) > 0, math.sqrt(cx * cx + (cy - HC) ** 2 + cz * cz)


def draw_faces(faces, pos, yaw, rng, w):
    """faces: list of (pts_local, normal_local, fill, edges) ; edges = indices of edges to ink, or 'all'"""
    vf = []
    for f in faces:
        pts, n, fill, eds = f[:4]
        pw = [xf(p, pos, yaw) for p in pts]
        ok, d = vis(pw, xn(n, yaw))
        if ok:
            vf.append((d, [pr(*p) for p in pw], fill, eds, f[4] if len(f) > 4 else None))
    vf.sort(key=lambda t: -t[0])
    for d, sp, fill, eds, extra in vf:
        knock(sp, 0.5)
        if fill:
            blob(sp, fill, rng, gap=0.0, shift=0.5, jit=0.02)
        n = len(sp)
        idx = range(n) if eds == 'all' else (eds or [])
        for i in idx:
            edge(sp[i], sp[(i + 1) % n], w, 'key', rng, over=(-0.6, 1.4), passes=1)
        if extra:
            extra(sp)
    return vf


def auto_rickshaw(x, z, yaw, rng, driver=True, sleeper=False, lights=True, carve_hood=True):
    """a Bengaluru auto: green body, yellow canvas hood, three wheels. yaw 0 = driving away from us."""
    pos = (x, 0, z)
    s = S(z)
    w = clamp(0.035 * s, MINW, 4.8)

    def hw(zz):
        return 0.64 - 0.08 * smooth((zz - 0.3) / 1.9)
    cr = lambda xx, zz: 1.74 + 0.15 * (1 - (xx / hw(zz)) ** 2) ** 0.7
    zt0, zt1 = 0.32, 2.12
    top = []
    for i in range(9):
        xx = -hw(zt0) + 2 * hw(zt0) * i / 8
        top.append((xx, cr(xx, zt0), zt0))
    for zz in (0.9, 1.5, zt1):
        top.append((hw(zz), cr(hw(zz) * 0.999, zz) - 0.005, zz))
    for i in range(9):
        xx = hw(zt1) - 2 * hw(zt1) * i / 8
        top.append((xx, cr(xx, zt1), zt1))
    for zz in (1.5, 0.9):
        top.append((-hw(zz), cr(-hw(zz) * 0.999, zz) - 0.005, zz))
    prof = [(0.32, 1.74), (0.16, 1.69), (0.05, 1.52), (0.0, 1.26), (0.0, 0.98)]
    back = []
    for i in range(9):
        xx = -hw(zt0) + 2 * hw(zt0) * i / 8
        back.append((xx, cr(xx, zt0), zt0))
    for zz, yy in prof[1:]:
        back.append((hw(0.3), yy, zz))
    for i in range(9):
        xx = hw(0.3) - 2 * hw(0.3) * i / 8
        back.append((xx, 0.98, 0.0))
    for zz, yy in prof[::-1][:-1]:
        back.append((-hw(0.3), yy, zz))
    back = back[:9] + back[9:]
    sideR = [(hw(zt1), 1.74, zt1), (hw(zt0), 1.74, zt0)] + [(hw(0.3), yy, zz) for zz, yy in prof[1:]] + \
            [(hw(0.3), 0.98, 0.36), (hw(0.4), 1.52, 0.42), (hw(zt1), 1.58, zt1)]
    sideL = [(-p[0], p[1], p[2]) for p in sideR][::-1]
    bw = 0.66
    rear = [(-bw, 0.33, 0.0), (bw, 0.33, 0.0), (bw, 0.98, 0.0), (-bw, 0.98, 0.0)]
    bodyR = [(bw, 0.33, 0.0), (bw, 0.98, 0.0), (bw, 0.98, 0.36), (bw, 0.78, 0.5), (bw, 0.78, 1.25), (0.6, 0.92, 1.5),
             (0.44, 0.97, 2.3), (0.42, 0.3, 2.36), (0.62, 0.3, 1.5), (bw, 0.33, 0.95)]
    bodyL = [(-p[0], p[1], p[2]) for p in bodyR][::-1]
    nose = [(-0.38, 0.28, 2.62), (0.38, 0.28, 2.62), (0.36, 1.02, 2.52), (-0.36, 1.02, 2.52)]
    cowl = [(-0.44, 0.97, 2.3), (0.44, 0.97, 2.3), (0.36, 1.02, 2.52), (-0.36, 1.02, 2.52)]
    wind = [(-0.5, 1.06, 2.42), (0.5, 1.06, 2.42), (0.55, 1.62, 2.13), (-0.55, 1.62, 2.13)]
    floor_ = [(-bw, 0.33, 0.0), (bw, 0.33, 0.0), (0.42, 0.3, 2.36), (-0.42, 0.3, 2.36)]

    def wheel_face(cx_, cz_, r, side_):
        pts = [(cx_, 0.24 + math.sin(a) * r, cz_ + math.cos(a) * r) for a in [TAU * i / 12 for i in range(12)]]
        return (pts, (side_, 0, 0), None, [], None)

    faces = [
        wheel_face(0.68, 0.45, 0.24, 1), wheel_face(-0.68, 0.45, 0.24, -1), wheel_face(0.0, 2.42, 0.22, 1),
        (rear, (0, 0, -1), 'green', 'all'),
        (bodyR, (1, 0, 0.12), 'green', [0, 1, 2, 3, 4, 5, 6, 7]),
        (bodyL, (-1, 0, 0.12), 'green', [2, 3, 4, 5, 6, 7, 8, 9]),
        (nose, (0, 0.15, 1), 'green', 'all'),
        (cowl, (0, 1, 0.3), 'green', [0, 2]),
        (wind, (0, 0.45, 1), None, 'all'),
        (sideR, (1, 0, 0), 'yellow', [0, 1, 2, 3, 4, 5, 6, 7]),
        (sideL, (-1, 0, 0), 'yellow', [1, 2, 3, 4, 5, 6, 7, 8]),
        (back, (0, 0.35, -1), 'yellow', None),
        (top, (0, 1, 0), 'yellow', None),
    ]
    pw_all = []
    for f in faces:
        pw_all += [pr(*xf(p, pos, yaw)) for p in f[0]]
    vf = draw_faces(faces, pos, yaw, rng, w)
    vis_names = set()
    for d, sp, fill, eds, extra in vf:
        pass
    # hood outline: the top perimeter + the back roll edge, firm
    tp = [pr(*xf(p, pos, yaw)) for p in top]
    bk = [pr(*xf(p, pos, yaw)) for p in back]
    ln(tp + [tp[0]], w * 1.15, 'key', rng, wob=0.2, redraw=0.3)
    camz_rel = (0 - z) * math.cos(yaw) - (0 - x) * math.sin(yaw)
    see_back = camz_rel < 0
    if see_back:
        ln(bk[9:-0] if False else bk[8:], w * 1.1, 'key', rng, wob=0.2)
        # rear window in the roll
        rw = [(-0.3, 1.3, 0.025), (0.3, 1.3, 0.025), (0.28, 1.52, 0.06), (-0.28, 1.52, 0.06)]
        rws = [pr(*xf(p, pos, yaw)) for p in rw]
        knock(rws, 0.3)
        pline(rws, w * 0.9, 'key', rng)
        if carve_hood:
            for yy in (1.12, 1.62):
                zz = 0.0 if yy < 1.3 else 0.08
                carve([pr(*xf((xx, yy, zz), pos, yaw)) for xx in (-0.5, 0, 0.5)], MINW, 'yellow', rng)
        # tail lamps + yellow plate
        for sx_ in (-1, 1):
            tl = [pr(*xf(p, pos, yaw)) for p in [(sx_ * 0.58, 0.62, -0.01), (sx_ * 0.44, 0.62, -0.01), (sx_ * 0.44, 0.76, -0.01), (sx_ * 0.58, 0.76, -0.01)]]
            knock(tl, 0.3)
            fillp(tl, 'copper')
            if lights:
                light(xf((sx_ * 0.51, 0.69, 0), pos, yaw)[0], 0.69, xf((sx_ * 0.51, 0.69, 0), pos, yaw)[2], 'copper', wm=0.16, k=0.9)
        pl = [pr(*xf(p, pos, yaw)) for p in [(-0.2, 0.35, -0.01), (0.2, 0.35, -0.01), (0.2, 0.47, -0.01), (-0.2, 0.47, -0.01)]]
        knock(pl, 0.3)
        fillp(pl, 'yellow')
        pline(pl, MINW, 'key', rng, skip=0.3)
        # the spare wheel strapped to the back
        sc_ = pr(*xf((0.0, 0.73, -0.06), pos, yaw))
        sr_ = 0.19 * s
        knock_ell(sc_[0], sc_[1], sr_ + 2, sr_ * 0.95 + 2)
        ln(ell(sc_[0], sc_[1], sr_, sr_ * 0.95, n=18, rng=rng) + [], w, 'key', rng, wob=0.1)
        ln(ell(sc_[0], sc_[1], sr_ * 0.5, sr_ * 0.48, n=12, a0=0.4, a1=TAU - 0.3, rng=rng), MINW, 'key', rng)
        dot(sc_[0], sc_[1], clamp(0.04 * s, 1.9, 4), 'key', rng)
    else:
        hl = pr(*xf((0, 0.88, 2.63), pos, yaw))
        r = clamp(0.1 * s, 2.2, 7)
        knock_ell(hl[0], hl[1], r + 1, r + 1)
        dot(hl[0], hl[1], r, 'ice', rng)
        if lights:
            light(*xf((0, 0.88, 2.63), pos, yaw), 'ice', wm=0.18, k=0.8, core='key')
    # wet shine: two short ice glints along the crown of the hood
    for zz0, zz1 in ((0.55, 0.95), (1.35, 1.7)):
        g0 = pr(*xf((-0.12, cr(-0.12, zz0) + 0.02, zz0), pos, yaw))
        g1 = pr(*xf((-0.14, cr(-0.14, zz1) + 0.02, zz1), pos, yaw))
        if math.hypot(g1[0] - g0[0], g1[1] - g0[1]) > 8:
            knock_line([g0, g1], MINW * 2.2)
            ln([g0, g1], MINW, 'ice', rng, wob=0.05, a0=0.8, a1=1.4)
    # ribs across the hood top
    for zz in (0.85, 1.45):
        rib = [pr(*xf((xx, cr(xx, zz) + 0.01, zz), pos, yaw)) for xx in [-hw(zz) + 2 * hw(zz) * i / 6 for i in range(7)]]
        ln(rib, MINW, 'key', rng, wob=0.15)
    # chrome rail and seat inside the side opening
    camx_rel = (0 - x) * math.cos(yaw) + (0 - z) * math.sin(yaw)
    sd = 1 if camx_rel > 0 else -1
    rail = [pr(*xf((sd * 0.665, 0.79, zz), pos, yaw)) for zz in (0.45, 0.9, 1.3)]
    ln(rail, MINW, 'key', rng)
    seat = [pr(*xf((sd * 0.6, yy, zz), pos, yaw)) for zz, yy in ((0.12, 1.25), (0.16, 0.86), (0.75, 0.84))]
    ln(seat, MINW, 'key', rng)
    # wheels: black with a cream rim arc and hub
    for wx, wz_, r in ((sd * 0.69, 0.45, 0.24), (0.0, 2.42, 0.22)):
        cc = pr(*xf((wx, 0.24, wz_), pos, yaw))
        rim = [pr(*xf((wx, 0.24 + math.sin(a) * r, wz_ + math.cos(a) * r), pos, yaw)) for a in [TAU * i / 14 for i in range(15)]]
        tire = [pr(*xf((wx, 0.24 + math.sin(a) * r, wz_ + math.cos(a) * r), pos, yaw)) for a in [TAU * i / 14 for i in range(14)]]
        knock(tire, 0.6)
        ln([tire[i % 14] for i in range(0, 8)], w, 'key', rng)
        dot(cc[0], cc[1], clamp(0.045 * s, 1.9, 4), 'key', rng)
    out = {'sil': [p for p in pw_all]}
    if driver:
        # the driver: shoulder, arm to the handlebar, head under the hood front
        hd = pr(*xf((0.05, 1.32, 1.85), pos, yaw))
        hr = clamp(0.11 * s, 3, 12)
        if not see_back:
            knock_ell(hd[0], hd[1], hr * 1.1, hr * 1.25)
            ln(ell(hd[0], hd[1], hr, hr * 1.2, n=12, a0=0.3, a1=TAU - 0.6, rng=rng), MINW, 'key', rng)
            sh_ = pr(*xf((0.22, 1.08, 1.85), pos, yaw))
            hb = pr(*xf((0.3, 1.0, 2.25), pos, yaw))
            ln([sh_, ((sh_[0] + hb[0]) / 2, sh_[1] + hr * 0.6), hb], MINW, 'key', rng)
    if sleeper:
        # driver asleep across the back seat: feet out of the side opening
        f0 = pr(*xf((sd * 0.62, 0.92, 0.7), pos, yaw))
        f1 = pr(*xf((sd * 0.95, 0.88, 0.75), pos, yaw))
        f2 = pr(*xf((sd * 0.95, 0.85, 0.95), pos, yaw))
        f3 = pr(*xf((sd * 0.62, 0.9, 1.0), pos, yaw))
        for a_, b_ in ((f0, f1), (f3, f2)):
            ln([a_, b_], max(MINW, 0.07 * s), 'key', rng)
            dot(b_[0], b_[1], max(2.0, 0.06 * s), 'key', rng)
        # a lungi / blanket edge
        ln([pr(*xf((sd * 0.5, 1.0, 0.4), pos, yaw)), pr(*xf((sd * 0.6, 1.05, 1.1), pos, yaw))], MINW, 'copper', rng)
    return out


def car(x, z, yaw, rng, lights=True, plate='yellow'):
    """a Bengaluru cab: white compact sedan, yellow plate. yaw 0 = away from us, pi = toward us"""
    pos = (x, 0, z)
    s = S(z)
    w = clamp(0.03 * s, MINW, 4.5)
    hw, hwc = 0.86, 0.7
    L = 4.3
    zb0, zb1 = 0.0, L
    ybelt, yroof, ysill = 0.95, 1.5, 0.35
    zc0, zc1, zg0, zg1 = 0.75, 2.95, 1.2, 2.6    # glass base, roof
    faces = [
        ([(-hw, ysill, 0), (hw, ysill, 0), (hw, ybelt, 0.05), (-hw, ybelt, 0.05)], (0, 0, -1), None, 'all'),            # rear
        ([(-hw, ybelt, 0.05), (hw, ybelt, 0.05), (hw, ybelt, zc0), (-hw, ybelt, zc0)], (0, 1, -0.05), None, 'all'),      # boot lid
        ([(-hw, ybelt, zc0), (hw, ybelt, zc0), (hwc, yroof, zg0), (-hwc, yroof, zg0)], (0, 0.8, -0.6), None, 'all'),      # rear glass
        ([(-hwc, yroof, zg0), (hwc, yroof, zg0), (hwc, yroof, zg1), (-hwc, yroof, zg1)], (0, 1, 0), None, 'all'),        # roof
        ([(-hw, ybelt, zc1), (hw, ybelt, zc1), (hwc, yroof, zg1), (-hwc, yroof, zg1)], (0, 0.75, 0.65), None, 'all'),     # windscreen
        ([(-hw, ybelt - 0.03, zc1), (hw, ybelt - 0.03, zc1), (hw, 0.85, L - 0.1), (-hw, 0.85, L - 0.1)], (0, 1, 0.1), None, 'all'),  # bonnet
        ([(-hw, ysill, L), (hw, ysill, L), (hw, 0.85, L - 0.1), (-hw, 0.85, L - 0.1)], (0, 0.1, 1), None, 'all'),       # front
        ([(hw, ysill, 0), (hw, ysill, L), (hw, 0.85, L - 0.1), (hw, ybelt, zc1), (hw, ybelt, 0.05)], (1, 0, 0), None, [0, 1, 2, 3]),
        ([(hw, ybelt, zc0), (hw, ybelt, zc1), (hwc, yroof, zg1), (hwc, yroof, zg0)], (1, 0.35, 0), None, 'all'),         # side glass
        ([(-hw, ysill, 0), (-hw, ybelt, 0.05), (-hw, ybelt, zc1), (-hw, 0.85, L - 0.1), (-hw, ysill, L)], (-1, 0, 0), None, [0, 1, 2, 3]),
        ([(-hw, ybelt, zc0), (-hwc, yroof, zg0), (-hwc, yroof, zg1), (-hw, ybelt, zc1)], (-1, 0.35, 0), None, 'all'),
    ]
    vf = draw_faces(faces, pos, yaw, rng, w)
    # light on the white paint: hatch the upward faces (roof, boot, bonnet) in cream, the glass stays dark
    for d, sp, fill, eds, extra in vf:
        pass
    for f in (faces[1], faces[3], faces[5]):
        pw = [xf(p, pos, yaw) for p in f[0]]
        ok, _ = vis(pw, xn(f[1], yaw))
        if ok:
            sp = [pr(*p) for p in pw]
            hatch(grow(sp, -1.5), 'key', rng.uniform(-0.3, 0.3), clamp(0.12 * s, 7, 11), rng=rng, gap=0.1)
    camz_rel = (0 - z) * math.cos(yaw) - (0 - x) * math.sin(yaw)
    if camz_rel < 0:
        for sx_ in (-1, 1):
            tl = [pr(*xf(p, pos, yaw)) for p in [(sx_ * 0.82, 0.7, -0.01), (sx_ * 0.5, 0.72, -0.01), (sx_ * 0.5, 0.88, 0.02), (sx_ * 0.82, 0.88, 0.02)]]
            knock(tl, 0.3)
            fillp(tl, 'copper')
            if lights:
                light(*xf((sx_ * 0.66, 0.78, 0), pos, yaw), 'copper', wm=0.3, k=0.9)
        pl = [pr(*xf(p, pos, yaw)) for p in [(-0.26, 0.45, -0.01), (0.26, 0.45, -0.01), (0.26, 0.6, -0.01), (-0.26, 0.6, -0.01)]]
    else:
        for sx_ in (-1, 1):
            hl = pr(*xf((sx_ * 0.62, 0.72, L + 0.01), pos, yaw))
            r = clamp(0.09 * s, 2.2, 7)
            knock_ell(hl[0], hl[1], r * 1.5, r)
            fillp(ell(hl[0], hl[1], r * 1.4, r * 0.9, n=10, rng=rng), 'ice')
            if lights:
                light(*xf((sx_ * 0.62, 0.72, L), pos, yaw), 'ice', wm=0.28, k=1.0, core='key')
        pl = [pr(*xf(p, pos, yaw)) for p in [(-0.26, 0.42, L + 0.01), (0.26, 0.42, L + 0.01), (0.26, 0.55, L + 0.01), (-0.26, 0.55, L + 0.01)]]
    knock(pl, 0.3)
    fillp(pl, plate)
    # wheels peeking under the sill
    camx_rel = (0 - x) * math.cos(yaw) + (0 - z) * math.sin(yaw)
    sd = 1 if camx_rel > 0 else -1
    for wz_ in (0.8, L - 0.85):
        rim = [pr(*xf((sd * hw, 0.3 + math.sin(a) * 0.3, wz_ + math.cos(a) * 0.3), pos, yaw)) for a in [math.pi * i / 8 for i in range(9)]]
        ln(rim[::-1], w, 'key', rng)


def two_wheeler(x, z, toward, rng, poncho='green', box=False, pillion=False):
    """a scooter rider in a rain poncho, seen from behind (taillight) or in front (headlight)"""
    s = S(z)
    g = pr(x, 0, z)
    u = 1.75 * s
    wl = clamp(0.03 * s, MINW, 4)
    gx, gy = g
    # wheel (thin, seen end-on) and apron
    ln([(gx, gy - 0.02 * u), (gx, gy - 0.24 * u)], max(MINW, 0.07 * u), 'key', rng)
    apron = [(gx - 0.09 * u, gy - 0.2 * u), (gx + 0.09 * u, gy - 0.2 * u), (gx + 0.07 * u, gy - 0.5 * u), (gx - 0.07 * u, gy - 0.5 * u)]
    knock(apron, 1)
    pline(apron, wl, 'key', rng, skip=0.2)
    # rider: helmet + poncho bell
    hc = (gx + rng.uniform(-0.01, 0.01) * u, gy - 0.9 * u)
    pon = [(hc[0] - 0.05 * u, hc[1] + 0.06 * u), (hc[0] + 0.05 * u, hc[1] + 0.06 * u), (gx + 0.24 * u, gy - 0.42 * u),
           (gx + 0.18 * u, gy - 0.36 * u), (gx - 0.18 * u, gy - 0.36 * u), (gx - 0.24 * u, gy - 0.42 * u)]
    knock(pon, 1.2)
    blob(pon, poncho, rng)
    pline(pon, wl, 'key', rng, skip=0.15)
    for k in (-0.08, 0.06):
        ln([(hc[0] + k * u * 0.5, hc[1] + 0.1 * u), (gx + k * u * 1.6, gy - 0.4 * u)], MINW, 'key', rng)
    hel = ell(hc[0], hc[1], 0.075 * u, 0.085 * u, n=14, rng=rng)
    knock(hel, 1)
    ln(hel, wl, 'key', rng)
    if toward:
        ln([(hc[0] - 0.055 * u, hc[1] + 0.005 * u), (hc[0] + 0.055 * u, hc[1] + 0.005 * u)], MINW, 'key', rng)
        ln([(gx - 0.2 * u, gy - 0.55 * u), (gx + 0.2 * u, gy - 0.55 * u)], wl, 'key', rng)
        hl = (gx, gy - 0.5 * u)
        r = clamp(0.06 * s, 2.2, 6)
        knock_ell(hl[0], hl[1], r + 1, r + 1)
        dot(hl[0], hl[1], r, 'ice', rng)
        light(x, 0.9, z, 'ice', wm=0.15, k=0.9, core='key')
    else:
        tl = (gx, gy - 0.32 * u)
        r = clamp(0.05 * s, 2.0, 5)
        knock_ell(tl[0], tl[1], r + 1, r + 1)
        dot(tl[0], tl[1], r, 'copper', rng)
        light(x, 0.6, z, 'copper', wm=0.12, k=0.9)
    if box:
        b = [(gx - 0.13 * u, gy - 0.5 * u), (gx + 0.13 * u, gy - 0.5 * u), (gx + 0.13 * u, gy - 0.75 * u), (gx - 0.13 * u, gy - 0.75 * u)]
        bt = [(b[3][0], b[3][1]), (b[2][0], b[2][1]), (b[2][0] - 0.03 * u, b[2][1] - 0.06 * u), (b[3][0] + 0.03 * u, b[3][1] - 0.06 * u)]
        knock(b, 1.2)
        knock(bt, 1.2)
        blob(b, 'copper', rng)
        pline(b, wl, 'key', rng)
        pline(bt, wl * 0.8, 'key', rng, skip=0.3)
    return pon
