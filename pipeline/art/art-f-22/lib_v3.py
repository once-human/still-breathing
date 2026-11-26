"""lib_v3.py: round-2 primitives for 22° (after REVIEW-1).
Rain-tree crowns built from lobed leaf clusters, buttressed trunks with bark / hatching / moss, lamp cones full of
drizzle, lobed low clouds lit from below with halftone, unequal white beams, reflections one-colour-per-light."""
from kit import *
from lib_life import *

RAIN = 1.78          # the one drizzle angle: ~12 degrees off vertical, leaning down-left
DRW = MINW * 1.2     # drizzle stroke width (~12 px)


# ============================================================ halftone restricted to a polygon
def halftone_in(poly, tonef, ink, rng, cell=11.0, angle=0.55, maxf=0.55, min_r=None, knock_under=None):
    """coarse hand-set halftone dots inside poly; tonef(x, y) -> 0..1. Dots under the printable size are dropped."""
    min_r = min_r or MINW * 0.62
    x0, y0, x1, y1 = bbox(poly)
    ca, sa = math.cos(angle), math.sin(angle)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rad = math.hypot(x1 - x0, y1 - y0) / 2 + cell
    n = int(rad / cell) + 1
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            u, v = i * cell + rng.gauss(0, cell * 0.08), j * cell + rng.gauss(0, cell * 0.08)
            x, y = cx + u * ca - v * sa, cy + u * sa + v * ca
            if not (x0 <= x <= x1 and y0 <= y <= y1) or not pip(x, y, poly):
                continue
            t = tonef(x, y)
            r = cell * maxf * math.sqrt(max(0.0, t))
            if r < min_r:
                continue
            if knock_under:
                knock_ell(x, y, r + 1.6, r + 1.6, layers=knock_under)
            dot(x, y, r, ink, rng)


# ============================================================ RAIN TREE: leaf clusters
def lobed(cx, cy, rx, ry, rng, tip=15.0, big=None, depth=0.38):
    """outline of a leaf mass: 3-5 big lobes, and a scalloped edge of leaf tips (each scallop ~tip units wide)"""
    big = big or rng.randint(3, 5)
    ph, ph2 = rng.uniform(0, TAU), rng.uniform(0, TAU)
    per = math.pi * (rx + ry)
    n = max(10, int(per / tip))
    base = []
    for i in range(n):
        a = TAU * i / n + rng.uniform(-0.15, 0.15) * TAU / n
        rr = 1 + 0.14 * math.sin(big * a + ph) + 0.06 * math.sin((big + 2) * a + ph2)
        base.append((a, rr * rng.uniform(0.95, 1.04)))
    base.sort()
    pts = []
    for i in range(n):
        a1, r1 = base[i]
        a2, r2 = base[(i + 1) % n]
        if i == n - 1:
            a2 += TAU
        for k in range(5):
            t = k / 5
            a = a1 + (a2 - a1) * t
            rr = (r1 + (r2 - r1) * t)
            bump = depth * math.sin(math.pi * t) * tip / max(rx, 1) * 0.9
            x, y = math.cos(a) * rx * (rr + bump), math.sin(a) * ry * (rr + bump * rx / max(ry, 1))
            pts.append((cx + x, cy + y))
    return pts


def leaf_group(x, y, ang, L, rng, ink, n=3, sp=7.6, w=None):
    """a clump of leaves: 2-4 short curved strokes side by side, like a pen drawing a rain-tree leaflet spray"""
    w = w or MINW
    ux, uy = math.cos(ang), math.sin(ang)
    nx, ny = -uy, ux
    off0 = -(n - 1) / 2
    for k in range(n):
        o = (off0 + k) * sp
        l = L * rng.uniform(0.75, 1.1) * (1 - 0.12 * abs(off0 + k))
        bx, by = x + nx * o + ux * rng.uniform(-2, 2), y + ny * o + uy * rng.uniform(-2, 2)
        bow = l * 0.22
        p0 = (bx - ux * l / 2, by - uy * l / 2)
        p1 = (bx + ux * l / 2, by + uy * l / 2)
        m = ((p0[0] + p1[0]) / 2 + nx * bow, (p0[1] + p1[1]) / 2 + ny * bow)
        A.line([p0, m, p1], w * rng.uniform(0.95, 1.12), layer=ink, rng=rng, wob=0.2, trem=0.0, a0=0.7, a1=2.2, pv=0.2)


def leaf_cluster(cx, cy, rx, ry, rng, lit=0.0, gapm=4.5, sc=1.0, rim=True, top_fade=0.85, contour_w=None,
                 halftone_on=True, drip_n=None, key_rim=True):
    """one leaf mass of a rain tree seen from below at night. Scalloped leaf-tip contour, strongest underneath where
    the lamps catch it; grouped curved leaf strokes, dense low and fading to black toward the top; an amber halftone
    belly only when a lamp is right under it, with water dripping off it."""
    out = lobed(cx, cy, rx, ry, rng, tip=15.0 * sc)
    knock(grow(out, gapm), 0)
    knock(out, 0)
    y_top, y_bot = cy - ry * 1.1, cy + ry * 1.1
    def tpos(y):
        return clamp((y - y_top) / (y_bot - y_top), 0, 1)        # 0 top .. 1 bottom
    # leaf groups on a jittered grid, following a gentle flow (leaves hang and fan out)
    sp = 17.0 * sc
    inner = grow(out, -5 * sc)
    yy = cy - ry
    row = 0
    while yy < cy + ry:
        xx = cx - rx + (sp * 0.5 if row % 2 else 0)
        while xx < cx + rx:
            px, py = xx + rng.gauss(0, sp * 0.22), yy + rng.gauss(0, sp * 0.22)
            if pip(px, py, inner):
                t = tpos(py)
                p = clamp((t - (1 - top_fade)) / top_fade, 0, 1) ** 1.25
                if rng.random() < 0.08 + 0.92 * p:
                    # direction: fan around hanging-down, turned by position in the mass
                    ang = math.pi / 2 + 0.85 * (px - cx) / max(rx, 1) + rng.gauss(0, 0.28)
                    ang += 0.4 * math.sin(py / 37 + px / 53)
                    ink = 'green'
                    if lit > 0.35 and t > 0.72 and rng.random() < 0.35 * lit:
                        ink = 'key'
                    leaf_group(px, py, ang, 12.5 * sc, rng, ink, n=rng.choice((2, 3, 3, 4)), sp=7.6)
            xx += sp * rng.uniform(0.9, 1.15)
        yy += sp * 0.82 * rng.uniform(0.9, 1.1)
        row += 1
    # amber halftone belly: only above a lamp
    if halftone_on and lit > 0.3:
        belly = [p for p in out]
        halftone_in(belly, lambda x, y: lit * clamp((tpos(y) - 0.58) / 0.42, 0, 1) ** 1.3 * 0.95, 'amber', rng,
                    cell=11.5 * sc, angle=0.5, maxf=0.5, knock_under=('green', 'key'))
    # the scalloped contour, drawn scallop-run by scallop-run: firm underneath, gone at the top
    if rim:
        n = len(out)
        wr = contour_w or MINW * (1.45 if rx > 60 else 1.25 if rx > 30 else 1.05)
        i = rng.randint(0, 6)
        while i < n:
            L = rng.randint(8, 18)
            seg = out[i:i + L + 1]
            i += L + rng.choice((0, 0, 3, 5))
            if len(seg) < 3:
                continue
            t = sum(tpos(p[1]) for p in seg) / len(seg)
            if t > 0.55:
                ink = 'amber' if (lit > 0.4 and rng.random() < 0.6) else ('key' if key_rim else 'green')
                ln(seg, wr, ink, rng, wob=0.15, a0=1.0, a1=1.8)
            elif t > 0.3 and rng.random() < 0.55:
                ln(seg, MINW, 'green', rng, wob=0.15, a0=1.0, a1=1.8)
    # drips off the lit underside
    nd = drip_n if drip_n is not None else (rng.randint(2, 4) if lit > 0.3 and rx > 30 else 0)
    if nd:
        low = sorted(out, key=lambda p: -p[1])[:max(4, len(out) // 5)]
        for _ in range(nd):
            x, y = rng.choice(low)
            l = rng.uniform(9, 18) * sc
            ink = 'amber' if lit > 0.4 else 'key'
            ln([(x, y + 4), (x + 0.4, y + 4 + l)], MINW, ink, rng, wob=0.1, a0=0.8, a1=1.4)
            dot(x + 0.5, y + 4 + l + rng.uniform(6, 10), MINW * 0.66, ink, rng)
    return out


def crown(clusters, rng, sc=1.0, **kw):
    """clusters: (cx, cy, rx, ry, lit), drawn top/back first so nearer masses cut black gaps into them"""
    outs = []
    for c in sorted(clusters, key=lambda c: (c[1] + c[3] * 0.5)):
        cx, cy, rx, ry, lit = c[:5]
        outs.append(leaf_cluster(cx, cy, rx, ry, rng, lit=lit, sc=sc, **kw))
    return outs


# ============================================================ RAIN TREE: trunk and limbs (screen space)
def bark2(sp, ws, rng, lit_side, lit=0.5, moss=0.5, knots=(), row_sp=8.6, hatch_sp=9.5, amber_edge=True):
    """tone inside a trunk/limb: bark strokes along it on the lamp-lit side, diagonal hatching on the shadow side,
    moss stipple in green on the shadow side, knots"""
    N = normals(sp)
    n = len(sp)
    s = cumlen(sp)
    wmax = max(ws)
    knot_pts = [(k[0], k[1], k[2] * 1.5) for k in knots]

    def in_knot(x, y):
        return any((x - kx) ** 2 + (y - ky) ** 2 < kr * kr for kx, ky, kr in knot_pts)

    def at(i, f):
        o = f * ws[i] * 0.9 + math.sin(s[i] * 0.06 + f * 9) * 1.4
        return (sp[i][0] + N[i][0] * o, sp[i][1] + N[i][1] * o)

    # bark strokes: rows across the width
    rows = max(2, int(wmax / row_sp))
    for r in range(rows):
        f = (r + 0.5) / rows - 0.5
        g = 0.5 + f * lit_side                    # 1 = lit edge
        if g < 0.38:
            continue
        i = rng.randint(0, 6)
        while i < n - 3:
            seg_len = rng.uniform(22, 60)
            j = i
            while j < n - 1 and s[j] - s[i] < seg_len:
                j += 1
            if rng.random() < 0.15 + 0.8 * g ** 1.6 and ws[i] > row_sp * 1.6:
                pts = [at(k, f) for k in range(i, j + 1, 3)]
                pts = [p for p in pts if not in_knot(*p)]
                if len(pts) >= 3:
                    ink = 'amber' if (amber_edge and g > 0.86 and lit > 0.3 and rng.random() < 0.55) else 'key'
                    ln(pts, MINW * rng.uniform(1.0, 1.15), ink, rng, wob=0.3, a0=1.5, a1=2.8)
            i = j + rng.randint(2, 6)
    # shadow-side hatching: short diagonal strokes
    k = 0.0
    while k < s[-1] - 4:
        i = min(n - 1, int(np.searchsorted(s, k)))
        if ws[i] > 14:
            fa, fb = -0.48 * lit_side, -0.06 * lit_side
            fa += rng.uniform(-0.03, 0.03)
            j = min(n - 1, int(np.searchsorted(s, k + ws[i] * 0.35)))
            p0, p1 = at(i, fa), at(j, fb)
            if not in_knot(*p0) and rng.random() < 0.78:
                ln([p0, lerp(p0, p1, 0.5), p1], MINW, 'key', rng, wob=0.15, a0=0.8, a1=1.6)
        k += hatch_sp * rng.uniform(0.9, 1.15)
    # moss stipple on the shadow side (dots >= 12 px), in clumps
    if moss > 0:
        nclump = int(s[-1] / 55 * moss) + 1
        for _ in range(nclump):
            i = rng.randint(0, n - 1)
            if ws[i] < 14:
                continue
            f0 = -lit_side * rng.uniform(0.15, 0.42)
            for _ in range(rng.randint(3, 7)):
                ii = min(n - 1, max(0, i + rng.randint(-8, 8)))
                p = at(ii, f0 + rng.uniform(-0.08, 0.08))
                if not in_knot(*p):
                    r = rng.uniform(2.1, 2.9)
                    knock_ell(p[0], p[1], r + 1.6, r + 1.6, layers=('key',))
                    dot(p[0], p[1], r, 'green', rng)
    # knots: an eye of bark
    for kx, ky, kr in knots:
        knock_ell(kx, ky, kr * 1.3, kr * 1.7, layers=('key', 'green', 'amber'))
        e = ell(kx, ky, kr, kr * 1.4, n=14, rng=rng, j=0.04)
        ln(e + [e[0]], MINW * 1.1, 'key', rng, wob=0.1)
        if kr > 6:
            ln(ell(kx + 0.5, ky + 1, kr * 0.4, kr * 0.65, n=8, a0=0.3, a1=TAU - 0.8, rng=rng), MINW, 'key', rng, wob=0.1)
        for sgn in (-1, 1):
            ln([(kx, ky + sgn * kr * 1.45), (kx + rng.uniform(-2, 2), ky + sgn * kr * 2.4)], MINW, 'key', rng, wob=0.1)


def trunk2(spine, widths, rng, lit_side=1, lit=0.5, moss=0.6, knots=0, wc=6.0, roots=None, sil_only=False,
           contour_lit='key'):
    """a flared, buttressed old trunk in screen space: knocked mass, contour heavy on the silhouette, root flanges
    gripping the pavement, bark/hatching/moss inside. spine from the base up."""
    sp = catmull([(p[0] + rng.gauss(0, 1.5), p[1] + rng.gauss(0, 1.5)) for p in spine], step=2.0)
    ws = interp_w(len(sp), widths)
    Lp, Rp = tube_poly(sp, ws)
    poly = Lp + Rp[::-1]
    # buttress roots: flanges spreading from the base
    rpolys = []
    base, wb = sp[0], ws[0]
    N0 = normals(sp)[0]
    roots = roots if roots is not None else [(-0.62, 0.55), (-0.2, 0.3), (0.3, 0.38), (0.68, 0.6)]
    for f, reach in roots:
        bx = base[0] + N0[0] * f * wb
        by = base[1] + N0[1] * f * wb
        dirx = 1 if f > 0 else -1
        dirx *= (1 if N0[0] >= 0 else -1)
        top = (base[0] + N0[0] * f * wb * 0.5, base[1] - wb * 0.55 * reach)
        foot = (bx + dirx * wb * 0.32 * reach, by + rng.uniform(1, 5))
        w2 = wb * 0.16 * reach
        rp = [top, (bx - dirx * w2, by - wb * 0.05), foot, (bx + dirx * w2 * 0.3, by - wb * 0.18)]
        rpolys.append((rp, top, foot, bx, by, dirx))
    for rp, *_ in rpolys:
        knock(catmull(rp + [rp[0]], step=2), 1.8)
    knock(poly, 1.8)
    if sil_only:
        return sp, ws, poly
    # contour: heavy on the lit edge, a little lighter on the dark edge, broken
    litE, darkE = (Lp, Rp) if lit_side < 0 else (Rp, Lp)
    # normals point to the left of the spine direction; spine goes up, so Lp is on the screen-left. lit_side +1 = right
    litE, darkE = (Rp, Lp) if lit_side > 0 else (Lp, Rp)
    ln(litE[::2], wc, contour_lit, rng, wob=0.4, a0=1.0, a1=3.0, redraw=0.35)
    a = rng.randint(2, 6)
    ln(darkE[a::2], wc * 0.72, 'key', rng, wob=0.4, a0=1.0, a1=3.0)
    for rp, top, foot, bx, by, dirx in rpolys:
        ln([top, lerp(top, foot, 0.55), foot], max(MINW * 1.2, wc * 0.6), 'key', rng, wob=0.3, a0=1.0, a1=2.5)
    # knots placed along the spine
    kn = []
    s = cumlen(sp)
    for _ in range(knots):
        i = rng.randint(int(len(sp) * 0.25), int(len(sp) * 0.85))
        f = rng.uniform(-0.2, 0.2)
        N = normals(sp)[i]
        kn.append((sp[i][0] + N[0] * f * ws[i], sp[i][1] + N[1] * f * ws[i], clamp(ws[i] * 0.07, 4.5, 9)))
    bark2(sp, ws, rng, lit_side, lit=lit, moss=moss, knots=kn)
    return sp, ws, poly


def limb2(pts, w0, w1, rng, lit_side=1, lit=0.5, moss=0.3, wc=None, under='amber'):
    """a twisting limb in screen space: tapering knocked tube, contour (underside lit by the lamps), bark inside"""
    sp = catmull([(p[0] + rng.gauss(0, 1.5), p[1] + rng.gauss(0, 1.5)) for p in pts], step=2.0)
    n = len(sp)
    ws = [w0 + (w1 - w0) * (i / max(1, n - 1)) ** 0.85 for i in range(n)]
    Lp, Rp = tube_poly(sp, ws)
    poly = Lp + Rp[::-1]
    knock(poly, 1.8)
    lowL = sum(p[1] for p in Lp) > sum(p[1] for p in Rp)
    lo, hi = (Lp, Rp) if lowL else (Rp, Lp)
    wc = wc or clamp(w0 * 0.08, MINW, 6.0)
    ln(lo[::2], wc, under if lit > 0.3 else 'key', rng, wob=0.3, a0=1.0, a1=3.0)
    a = rng.randint(0, max(1, len(hi) // 6))
    ln(hi[a:][::2], wc * 0.78, 'key', rng, wob=0.3, a0=1.0, a1=3.0)
    if w0 > 18:
        bark2(sp, ws, rng, (1 if lowL else -1), lit=lit, moss=moss, row_sp=8.2, hatch_sp=10.5)
    return sp, ws, poly


# ============================================================ STREET LAMP with a cone full of drizzle
def street_lamp2(x, z, rng, h=8.2, arm=1.8, dens=1.0, refl=True, rings=3):
    side = -1 if x < 0 else 1
    hx = x - side * arm
    LAMPS.append((hx, h - 0.3, z))
    if refl:
        light(hx, h - 0.3, z, 'amber', wm=0.6, k=1.0)

    def draw():
        s = S(z)
        g, t = pr(x, 0, z), pr(x, h + 0.15, z)
        w = clamp(0.15 * s, MINW, 6.5)
        knock_line([g, t], w + 3)
        edge(g, t, w, 'key', rng, over=(-0.5, 0.5))
        a0, a1, hd = pr(x, h + 0.1, z), pr(x - side * arm * 0.5, h + 0.45, z), pr(hx, h, z)
        ln([a0, a1, hd], max(MINW, w * 0.8), 'key', rng, wob=0.2)
        hw = clamp(0.55 * s, 6, 30)
        hh = clamp(0.16 * s, 3.4, 9)
        cx, cy = hd
        house = [(cx - hw, cy - hh * 0.2), (cx - hw * 0.6, cy - hh), (cx + hw * 0.6, cy - hh), (cx + hw, cy - hh * 0.2),
                 (cx + hw * 0.7, cy + hh * 0.5), (cx - hw * 0.7, cy + hh * 0.5)]
        r0 = clamp(1.0 * s, 11, 46) * (1.0 if s > 50 else 0.7)
        if s > 24:      # the lamp's own glare: a clear dark ring around the head so the light reads against the leaves
            knock_ell(cx, cy + hh * 0.3, r0 * 1.2, r0 * 1.1)
        knock(house, 1.0)
        fillp([(cx - hw * 0.8, cy), (cx + hw * 0.8, cy), (cx + hw * 0.55, cy + hh * 0.9), (cx - hw * 0.55, cy + hh * 0.9)],
              'amber')
        pline(house[:4], max(MINW, w * 0.7), 'key', rng, closed=False)
        # mist: dashed broken rings
        for k in range(rings if s > 50 else 1):
            rr = r0 * (1 + 0.55 * k) * rng.uniform(0.95, 1.05)
            a = rng.uniform(0, TAU)
            end = a + TAU * rng.uniform(0.7, 0.85)
            dash = rng.uniform(0.28, 0.45) * (1 - 0.2 * k)
            while a < end:
                pts = ell(cx, cy + hh * 0.3, rr, rr * 0.92, n=max(3, int(dash * rr / 6)), a0=a, a1=a + dash, rng=rng)
                knock_line(pts, MINW * 2.4)
                A.line(pts, MINW * (1.1 - 0.1 * k), layer='amber', rng=rng, wob=0.2, trem=0.1, a0=1.0, a1=1.8, pv=0.2)
                a += dash + rng.uniform(0.18, 0.32) * (1 + 0.4 * k)
        # cone of light to the ground: drizzle only inside it, one slant
        r_ft = 2.6
        foot = [pr(hx - r_ft, 0, z), pr(hx + r_ft, 0, z)]
        apex = (cx, cy + hh)
        poly = [(apex[0] - hw * 0.7, apex[1]), (apex[0] + hw * 0.7, apex[1]), foot[1], foot[0]]
        Lc = max(1, foot[0][1] - apex[1])
        half = abs(foot[1][0] - foot[0][0]) * 0.5 + 1
        def fade(px, py):
            v = (py - apex[1]) / Lc
            lat = abs(px - apex[0]) / (hw * 0.7 + (half - hw * 0.7) * clamp(v, 0, 1) + 1)
            return clamp(1.08 - v * 0.95, 0, 1) ** 1.1 * clamp(1.25 - lat, 0, 1)
        sp_ = clamp(0.36 * s, 12.5, 18)
        drizzle_dark(poly, 'amber', rng, sp=sp_, L=(clamp(0.32 * s, 11, 18), clamp(0.6 * s, 16, 30)), ang=RAIN, fade=fade,
                     prob=0.95 * dens, w=DRW)
    return draw


def drizzle_dark(poly, ink, rng, **kw):
    """drizzle that only shows against the dark (rain is invisible against a lit wall): drawn on a scratch layer and
    kept only where nothing has been inked yet"""
    tmp = Image.new('L', (W, H), 0)
    keep_L, keep_D = A.L[ink], A.D[ink]
    A.L[ink], A.D[ink] = tmp, ImageDraw.Draw(tmp)
    try:
        drizzle(poly, ink, rng, **kw)
    finally:
        A.L[ink], A.D[ink] = keep_L, keep_D
    x0, y0, x1, y1 = [int(v * R) for v in bbox(poly)]
    x0, y0 = max(0, x0 - 40), max(0, y0 - 40)
    x1, y1 = min(W, x1 + 40), min(H, y1 + 40)
    box = (x0, y0, x1, y1)
    used = Image.new('L', (x1 - x0, y1 - y0), 0)
    for k in ORDER:
        used = ImageChops.lighter(used, A.L[k].crop(box))
    used = used.filter(ImageFilter.MaxFilter(max(3, int(2.2 * R) | 1)))
    piece = ImageChops.multiply(tmp.crop(box), ImageChops.invert(used))
    A.L[ink].paste(255, box, piece)


# ============================================================ LOW CLOUDS lit from below
def cloud_body(cx, yb, wdt, hgt, rng, beams=(), lit=1.0):
    """a low cloud seen from below: a flattish lobed belly, cauliflower lobes on top. Thin broken cream contour; the
    belly lit warm from the city with amber halftone fading upward to black; ice hatching where a beam passes."""
    # outline: base wave (left->right), then top lobes (right->left)
    nb = 14
    base = []
    for i in range(nb + 1):
        t = i / nb
        x = cx - wdt / 2 + wdt * t
        y = yb + 4 * math.sin(t * 7 + cx) + hgt * 0.1 * math.sin(math.pi * t) * rng.uniform(0.6, 1.0)
        base.append((x, y))
    nl = rng.randint(3, 5)
    tops = []
    xs = sorted(rng.uniform(0.12, 0.88) for _ in range(nl))
    edgeL, edgeR = base[0], base[-1]
    top = [edgeR]
    for k, f in enumerate(reversed(xs)):
        lx = cx - wdt / 2 + wdt * f
        lr = wdt / (nl + 0.8) * rng.uniform(0.55, 0.8)
        ly = yb - hgt * (0.55 + 0.45 * math.sin(math.pi * f)) * rng.uniform(0.8, 1.0) + lr * 0.6
        for i in range(9):
            a = -0.1 + (math.pi + 0.2) * i / 8
            top.append((lx + math.cos(a) * lr, ly - math.sin(a) * lr * 0.8))
    top.append(edgeL)
    poly = base + top
    poly = catmull(poly + [poly[0]], closed=False, step=3.0)
    knock(grow(poly, 4.0), 0)
    y_top = min(p[1] for p in poly)
    def tone(x, y):
        v = (y - y_top) / max(1, yb + 6 - y_top)
        return lit * clamp((v - 0.32) / 0.68, 0, 1) ** 1.4
    # beam crossings: ice hatching parallel to the beam, amber suppressed there
    bpolys = [b for b in beams]
    def in_beam(x, y):
        return any(pip(x, y, bp) for bp in bpolys)
    halftone_in(poly, lambda x, y: 0.0 if in_beam(x, y) else tone(x, y), 'amber', rng, cell=10.5, angle=0.42, maxf=0.52)
    for bp, ang in beams.items() if isinstance(beams, dict) else []:
        pass
    # contour: thin broken cream on the lobes, the belly edge a little firmer in amber
    n = len(poly)
    i = rng.randint(0, 5)
    while i < n - 2:
        L = rng.randint(6, 16)
        seg = poly[i:i + L]
        i += L + rng.randint(2, 6)
        if len(seg) < 3:
            continue
        mid = seg[len(seg) // 2]
        onbase = mid[1] > yb - hgt * 0.15
        if onbase:
            ln(seg, MINW * 1.25, 'amber', rng, wob=0.15, a0=1.0, a1=2.0)
        elif rng.random() < 0.8:
            ln(seg, MINW, 'key', rng, wob=0.15, a0=1.0, a1=2.0)
    return poly


def beam_cloud_light(poly, bpoly, ang, rng):
    """where a beam goes through a cloud: short ice strokes along the beam inside the cloud body"""
    x0, y0, x1, y1 = bbox(poly)
    ux, uy = math.sin(ang), -math.cos(ang)
    nx, ny = -uy, ux
    sp = 8.0
    for k in range(-30, 31):
        o = k * sp
        # a line along the beam through the cloud
        bx0, by0, bx1, by1 = bbox(bpoly)
        c = ((bx0 + bx1) / 2 + nx * o, (by0 + by1) / 2 + ny * o)
        p0 = (c[0] - ux * 400, c[1] - uy * 400)
        p1 = (c[0] + ux * 400, c[1] + uy * 400)
        for t0, t1 in seg_in_poly(p0, p1, poly):
            q0, q1 = lerp(p0, p1, t0), lerp(p0, p1, t1)
            for u0, u1 in seg_in_poly(q0, q1, bpoly):
                a, b = lerp(q0, q1, u0), lerp(q0, q1, u1)
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                if L > 8 and rng.random() < 0.85:
                    ink = 'key' if rng.random() < 0.4 else 'ice'
                    ln([a, lerp(a, b, 0.5), b], MINW, ink, rng, wob=0.1, a0=1.0, a1=2.0)


# ============================================================ BEAMS
def beam2(root, ang, L, wend, rng, clip_y=250, core_w=2.2, drz=0.75, ink='ice', drz_top=None):
    """a white beam through haze and drizzle: edges as long strokes breaking up as it climbs, a solid core near the
    head, drizzle inside it"""
    ux, uy = math.sin(ang), -math.cos(ang)
    nx, ny = -uy, ux
    end = (root[0] + ux * L, root[1] + uy * L)
    poly = [(root[0] + nx * 2, root[1] + ny * 2), (end[0] + nx * wend, end[1] + ny * wend),
            (end[0] - nx * wend, end[1] - ny * wend), (root[0] - nx * 2, root[1] - ny * 2)]

    def clipseg(p0, p1):
        if p0[1] < clip_y and p1[1] < clip_y:
            return None
        if p1[1] < clip_y:
            tt = (p0[1] - clip_y) / max(1e-6, p0[1] - p1[1])
            p1 = lerp(p0, p1, tt)
        return p0, p1
    for f, solid, w, ink_ in ((0.0, 0.62, core_w, 'key'), (-1.0, 0.5, 1.35, ink), (1.0, 0.5, 1.35, ink),
                              (-0.45, 0.3, 1.0, ink), (0.5, 0.25, 1.0, ink)):
        tip = (end[0] + nx * wend * f, end[1] + ny * wend * f)
        root2 = (root[0] + nx * 1.5 * f, root[1] + ny * 1.5 * f)
        t0, t1 = 0.0, solid * rng.uniform(0.9, 1.1)
        while t0 < 1.0:
            cs = clipseg(lerp(root2, tip, t0), lerp(root2, tip, min(1.0, t1)))
            if cs:
                p0, p1 = cs
                knock_line([p0, p1], MINW * max(1.0, w - 0.6 * t0) + 6.0, layers=('blue',))
                ln([p0, lerp(p0, p1, 0.5), p1], MINW * max(1.0, w - 0.6 * t0), ink_ if t0 < 0.5 else ink, rng,
                   wob=0.05, a0=0.5, a1=1.5)
            gap = rng.uniform(0.05, 0.1) * (1 + t1)
            t0 = t1 + gap
            t1 = t0 + rng.uniform(0.06, 0.15) * (1.3 - t0)
    drizzle(poly, ink, rng, sp=13, L=(11, 19), ang=RAIN,
            fade=lambda px, py: (0.0 if py < (drz_top or clip_y + 12) else clamp(1.05 - math.hypot(px - root[0], py - root[1]) / L, 0.15, 1.0)),
            prob=drz, w=MINW * 1.05)
    return poly


# ============================================================ REFLECTIONS: one colour per light
def reflect2(L, rng, ymax=1436, art=None):
    """painterly reflection under one light, in that light's colour only: tapered strokes that grow longer and
    thicker toward the viewer, gathering in clusters, wobbling and drifting, thinning out before the line zone"""
    art = art or RA
    gx, gy = pr(L['x'], 0, L['z'])
    mx, my = pr(L['x'], -L['h'], L['z'])
    if gy > ymax - 20:
        return
    base = clamp(L['wm'] * S(L['z']), 4.0, 40.0)
    length = (my - gy) * rng.uniform(1.0, 1.3) * L.get('stretch', 1.0) + base
    y0 = gy + clamp(0.06 * S(L['z']), 1.0, 8.0)
    y1 = min(ymax, y0 + length)
    span = max(1.0, y1 - y0)
    thick0 = clamp(base * 0.12, MINW, 4.5)
    ph, ph2 = rng.uniform(0, TAU), rng.uniform(0, TAU)
    drift = rng.uniform(-1, 1) * base * 0.25
    y = y0
    in_cluster = rng.randint(2, 4)
    ink = L['ink']
    while y < y1:
        t = (y - y0) / span
        grow_ = 1 + 1.1 * t
        th = min(7.0, thick0 * (0.9 + 0.9 * t)) * rng.uniform(0.85, 1.15)
        hl = base * (0.3 + 0.38 * t) * rng.uniform(0.6, 1.15) * L['k'] * (1 - 0.6 * smooth(clamp((t - 0.7) / 0.3, 0, 1)))
        cxp = gx + drift * t ** 1.4 + base * 0.14 * grow_ * (0.6 * math.sin(y * 0.04 + ph) + 0.4 * math.sin(y * 0.105 + ph2))
        cxp += rng.gauss(0, base * 0.04)
        thin_out = 0.12 + 0.75 * smooth(clamp((t - 0.6) / 0.4, 0, 1))
        if rng.random() > thin_out and hl > th * 0.9 and hl > MINW * 0.9:
            sag = rng.gauss(0, th * 0.35)
            pts = [(cxp - hl, y + rng.gauss(0, 0.5)), (cxp + rng.uniform(-0.2, 0.2) * hl, y + sag),
                   (cxp + hl, y + rng.gauss(0, 0.5))]
            art.line(pts, max(MINW, th), layer=ink, rng=rng, wob=0.3, trem=0.15, a0=1.6, a1=2.6, pv=0.3)
        step = max(th * 1.5, th + MINW * 1.1) * rng.uniform(1.0, 1.25)
        in_cluster -= 1
        if in_cluster <= 0:
            step += th * rng.uniform(1.5, 3.5) * (1 + 1.5 * t)
            in_cluster = rng.randint(2, 4)
        y += step


def pick_reflections(lights, keep=0.6):
    """one column per real light; drop weak lights and lights whose column would sit on top of a stronger one"""
    scored = []
    for L in lights:
        gx, gy = pr(L['x'], 0, L['z'])
        b = L['wm'] * S(L['z']) * L['k']
        scored.append((b, gx, gy, L))
    scored.sort(key=lambda t: -t[0])
    chosen = []
    for b, gx, gy, L in scored:
        if b < 5.5:
            continue
        if any(abs(gx - cx) < max(14, 0.6 * cb) and abs(gy - cy) < 80 for cb, cx, cy, _ in chosen):
            continue
        chosen.append((b, gx, gy, L))
    n = max(1, int(len(chosen) * keep + 0.5)) if keep < 1 else len(chosen)
    return [c[3] for c in chosen[:n]]


# ============================================================ round 2 of the primitives: printmaker foliage and bark
def scallop_arc(cx, cy, rx, ry, a0, a1, rng, tip=9.0, depth=0.45):
    """an arc of an ellipse whose edge is a run of small leaf-tip scallops bulging outward"""
    L = (a1 - a0) * (rx + ry) / 2
    n = max(2, int(L / tip))
    pts = []
    for i in range(n):
        for k in range(4):
            t = (i + k / 4) / n
            a = a0 + (a1 - a0) * t
            b = depth * math.sin(math.pi * (k / 4)) * tip
            pts.append((cx + math.cos(a) * (rx + b), cy + math.sin(a) * (ry + b)))
    pts.append((cx + math.cos(a1) * rx, cy + math.sin(a1) * ry))
    return pts


def fringe(arc, inward, rng, ink, L=(10, 17), sp=7.6, prob=0.9, w=None, every=None):
    """short leaf strokes hanging off a lit edge into the mass, alternating long and short (hatching that reads as
    leaves). inward(p) -> unit vector into the mass"""
    w = w or MINW
    s = cumlen(arc)
    d = rng.uniform(0, sp)
    k = 0
    while d < s[-1]:
        i = min(len(arc) - 1, int(np.searchsorted(s, d)))
        p = arc[i]
        if rng.random() < prob:
            ux, uy = inward(p)
            l = rng.uniform(*L) * (1.0 if k % 2 == 0 else 0.62)
            a = math.atan2(uy, ux) + rng.gauss(0, 0.18)
            ux, uy = math.cos(a), math.sin(a)
            q0 = (p[0] + ux * 2.5, p[1] + uy * 2.5)
            q1 = (p[0] + ux * l, p[1] + uy * l)
            m = ((q0[0] + q1[0]) / 2 - uy * l * 0.12, (q0[1] + q1[1]) / 2 + ux * l * 0.12)
            A.line([q0, m, q1], w * rng.uniform(0.95, 1.1), layer=ink, rng=rng, wob=0.15, trem=0.0, a0=0.9, a1=2.4, pv=0.15)
        d += sp * rng.uniform(0.88, 1.15)
        k += 1


def leaf_mass(cx, cy, rx, ry, rng, lit=0.0, sc=1.0, gapm=5.0, rimw=None, halftone_on=True, drip_n=None,
              key_rim=True, density=1.0):
    """a rain-tree leaf mass seen from below at night, cut like a woodblock: a scalloped lower edge caught by the lamp
    light with leaf strokes hanging into the mass, smaller clumps inside each with its own lit lower edge and fringe,
    fading to black toward the top; amber halftone belly only above a lamp; water dripping"""
    out = lobed(cx, cy, rx, ry, rng, tip=16.0 * sc, depth=0.42)
    knock(grow(out, gapm), 0)
    y_top, y_bot = cy - ry, cy + ry
    tpos = lambda y: clamp((y - y_top) / (y_bot - y_top), 0, 1)
    # inner clumps, top first (lower clumps overlap and cut the ones above)
    nsub = int(clamp(rx * ry / (36.0 * 24.0 * sc * sc) * density, 1, 16))
    subs = []
    for _ in range(nsub * 3):
        if len(subs) >= nsub:
            break
        u = rng.random()
        sx = cx + rng.uniform(-0.78, 0.78) * rx
        sy = cy - ry * 0.75 + ry * 1.35 * math.sqrt(u)
        if not pip(sx, sy + 6, grow(out, -10 * sc)):
            continue
        rs = rng.uniform(17, 30) * sc * (0.8 + 0.4 * tpos(sy))
        subs.append((sx, sy, rs, rs * rng.uniform(0.5, 0.62)))
    subs.sort(key=lambda c: c[1])
    for sx, sy, rs, rsy in subs:
        t = tpos(sy)
        st = 0.2 + 0.8 * t ** 1.2
        knock(ell(sx, sy - rsy * 0.35, rs * 1.02, rsy * 1.05, n=16), 0, layers=('green', 'key', 'amber'))
        a0, a1 = 0.12 * math.pi + rng.uniform(-0.1, 0.1), 0.88 * math.pi + rng.uniform(-0.1, 0.1)
        arc = scallop_arc(sx, sy, rs, rsy, a0, a1, rng, tip=9.5 * sc)
        arc = [p for p in arc if pip(p[0], p[1], out)]
        if len(arc) < 4:
            continue
        ink = 'key' if (lit > 0.45 and t > 0.7 and rng.random() < 0.5) else 'green'
        if rng.random() < 0.35 + 0.6 * st:
            ln(arc, MINW * 1.05, ink, rng, wob=0.12, a0=1.0, a1=1.8)
        fringe(arc, lambda p, sx=sx, sy=sy: _unit(sx - p[0], (sy - rsy * 0.9) - p[1]), rng, 'green',
               L=(9 * sc, 16 * sc * (0.6 + 0.5 * st)), prob=0.25 + 0.7 * st)
    # the main lower edge: firm, scalloped, lit; its fringe the densest marks in the mass
    n = len(out)
    lower = [i for i, p in enumerate(out) if p[1] > cy - ry * 0.05]
    runs, cur = [], []
    for i in range(n):
        if i in lower:
            cur.append(out[i])
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        if runs and lower and lower[0] == 0:
            runs[0] = cur + runs[0]
        else:
            runs.append(cur)
    wr = rimw or MINW * (1.55 if rx > 60 else 1.3 if rx > 30 else 1.1)
    for run in runs:
        j = 0
        while j < len(run) - 2:
            L = rng.randint(10, 22)
            seg = run[j:j + L + 1]
            j += L + rng.choice((0, 0, 0, 4))
            if len(seg) < 3:
                continue
            ink = 'amber' if (lit > 0.4 and rng.random() < 0.55) else ('key' if key_rim else 'green')
            ln(seg, wr, ink, rng, wob=0.15, a0=1.0, a1=1.8)
            fringe(seg, lambda p: _unit(cx - p[0], (cy - ry * 0.6) - p[1]), rng, 'green', L=(12 * sc, 21 * sc),
                   prob=0.85)
    # the shoulders of the mass catch a little light: a few green scallops on the upper edge
    upper = [p for p in out if p[1] < cy - ry * 0.25]
    if len(upper) > 6:
        j = rng.randint(0, 6)
        while j < len(upper) - 3:
            L = rng.randint(4, 8)
            if rng.random() < 0.4:
                ln(upper[j:j + L], MINW, 'green', rng, wob=0.12, a0=1.0, a1=1.8)
            j += L + rng.randint(4, 12)
    if halftone_on and lit > 0.3:
        band = [p for p in out]
        halftone_in(band, lambda x, y: lit * clamp((tpos(y) - 0.55) / 0.45, 0, 1) ** 1.2, 'amber', rng,
                    cell=11.0 * sc, angle=0.5, maxf=0.48, knock_under=('green',))
    nd = drip_n if drip_n is not None else (rng.randint(2, 4) if lit > 0.3 and rx > 30 else 0)
    if nd:
        low = sorted(out, key=lambda p: -p[1])[:max(4, len(out) // 5)]
        for _ in range(nd):
            x, y = rng.choice(low)
            l = rng.uniform(10, 18) * sc
            ink = 'amber' if lit > 0.4 else 'key'
            ln([(x, y + 5), (x + 0.4, y + 5 + l)], MINW, ink, rng, wob=0.1, a0=0.8, a1=1.4)
            dot(x + 0.5, y + 5 + l + rng.uniform(6, 10), MINW * 0.68, ink, rng)
    return out


def _unit(dx, dy):
    d = math.hypot(dx, dy) or 1.0
    return dx / d, dy / d


def crown2(clusters, rng, sc=1.0, **kw):
    outs = []
    for c in sorted(clusters, key=lambda c: (c[1] + c[3] * 0.5)):
        cx, cy, rx, ry, lit = c[:5]
        outs.append(leaf_mass(cx, cy, rx, ry, rng, lit=lit, sc=sc, **kw))
    return outs


def bark3(sp, ws, rng, lit_side, lit=0.5, moss=0.5, knots=(), row_sp=9.0, amber_edge=True, xhatch=1.0):
    """bark at night: broken vertical furrows crowded on the lamp side, thinning across; on the shadow side only short
    curved cross-contour hatches near the edge (round form) and green moss stipple; knots"""
    N = normals(sp)
    n = len(sp)
    s = cumlen(sp)
    wmax = max(ws)
    kn = [(k[0], k[1], k[2] * 1.6) for k in knots]
    in_knot = lambda x, y: any((x - a) ** 2 + (y - b) ** 2 < r * r for a, b, r in kn)

    def at(i, f):
        o = f * ws[i] * 0.92 + math.sin(s[i] * 0.05 + f * 11) * 1.6
        return (sp[i][0] + N[i][0] * o, sp[i][1] + N[i][1] * o)
    rows = max(2, int(wmax / row_sp))
    for r in range(rows):
        f = (r + 0.5) / rows - 0.5 + rng.uniform(-0.15, 0.15) / rows
        g = 0.5 + f * lit_side
        if g < 0.42:
            continue
        p_on = 0.12 + 0.8 * ((g - 0.42) / 0.58) ** 1.3
        i = rng.randint(0, 8)
        while i < n - 3:
            seg_len = rng.uniform(14, 34) * (1.2 if g > 0.8 else 1.0)
            j = i
            while j < n - 1 and s[j] - s[i] < seg_len:
                j += 1
            if rng.random() < p_on and ws[i] > row_sp * 1.5:
                pts = [at(k, f) for k in range(i, j + 1, 2)]
                if len(pts) >= 3 and not any(in_knot(*p) for p in pts):
                    ink = 'amber' if (amber_edge and g > 0.84 and lit > 0.3 and rng.random() < 0.5) else 'key'
                    ln(pts, MINW * rng.uniform(1.0, 1.12), ink, rng, wob=0.25, a0=1.2, a1=2.2)
            i = j + max(2, int(rng.uniform(4, 12) / 2.0))
    # cross-contour hatching on the shadow edge
    k = rng.uniform(0, 8)
    while k < s[-1] - 6:
        i = min(n - 1, int(np.searchsorted(s, k)))
        if ws[i] > 22 and rng.random() < 0.7 * xhatch:
            f0 = -0.47 * lit_side
            f1 = f0 + 0.24 * lit_side * rng.uniform(0.8, 1.2)
            p0, p1 = at(i, f0), at(i, f1)
            j = min(n - 1, i + 3)
            p1 = (p1[0] + (sp[j][0] - sp[i][0]) * 0.5, p1[1] + (sp[j][1] - sp[i][1]) * 0.5)
            if not in_knot(*p0):
                ln([p0, lerp(p0, p1, 0.5), p1], MINW, 'key', rng, wob=0.12, a0=0.8, a1=1.8)
        k += (11.0 if xhatch >= 1 else 17.0) * rng.uniform(0.85, 1.2)
    if moss > 0:
        nclump = int(s[-1] / 45 * moss) + 1
        for _ in range(nclump):
            i = rng.randint(0, n - 1)
            if ws[i] < 16:
                continue
            f0 = -lit_side * rng.uniform(0.05, 0.35)
            for _ in range(rng.randint(4, 9)):
                ii = min(n - 1, max(0, i + rng.randint(-7, 7)))
                p = at(ii, f0 + rng.uniform(-0.1, 0.1))
                if not in_knot(*p):
                    r = rng.uniform(2.2, 3.0)
                    knock_ell(p[0], p[1], r + 1.8, r + 1.8, layers=('key',))
                    dot(p[0], p[1], r, 'green', rng)
    for kx, ky, kr in knots:
        knock_ell(kx, ky, kr * 1.4, kr * 1.8, layers=('key', 'green', 'amber'))
        e = ell(kx, ky, kr, kr * 1.4, n=14, rng=rng, j=0.04)
        ln(e + [e[0]], MINW * 1.15, 'key', rng, wob=0.1)
        if kr > 6:
            dot(kx, ky + kr * 0.2, MINW * 0.75, 'key', rng)


def trunk3(spine, widths, rng, lit_side=1, lit=0.5, moss=0.6, knots=0, wc=6.0, roots=None, contour_lit='key'):
    sp = catmull([(p[0] + rng.gauss(0, 1.2), p[1] + rng.gauss(0, 1.2)) for p in spine], step=2.0)
    ws = interp_w(len(sp), widths)
    Lp, Rp = tube_poly(sp, ws)
    poly = Lp + Rp[::-1]
    base, wb = sp[0], ws[0]
    roots = roots if roots is not None else [(-0.62, 0.55), (-0.18, 0.3), (0.3, 0.38), (0.66, 0.6)]
    rp_all = []
    for f, reach in roots:
        bx = base[0] + f * wb
        dirx = 1 if f > 0 else -1
        top = (base[0] + f * wb * 0.55, base[1] - wb * 0.6 * reach)
        foot = (bx + dirx * wb * 0.3 * reach, base[1] + rng.uniform(2, 6))
        inner = (bx - dirx * wb * 0.12 * reach, base[1] + 1)
        rp = [top, (top[0] + dirx * wb * 0.1, top[1] + wb * 0.15 * reach), foot, inner]
        rp_all.append((rp, top, foot, inner, dirx))
        knock(rp, 1.8)
    knock(poly, 1.8)
    litE, darkE = (Rp, Lp) if lit_side > 0 else (Lp, Rp)
    # which tube edge is screen-right depends on normals; pick by x
    if sum(p[0] for p in Lp) > sum(p[0] for p in Rp):
        litE, darkE = (Lp, Rp) if lit_side > 0 else (Rp, Lp)
    ln(litE[::2], wc, contour_lit, rng, wob=0.4, a0=1.0, a1=3.0, redraw=0.35)
    a = rng.randint(2, 6)
    ln(darkE[a::2], wc * 0.7, 'key', rng, wob=0.4, a0=1.0, a1=3.0)
    for rp, top, foot, inner, dirx in rp_all:
        outer_ = [top, (top[0] + dirx * wb * 0.1, top[1] + wb * 0.15), foot]
        ln(outer_, max(MINW * 1.2, wc * 0.6), 'key', rng, wob=0.3, a0=1.0, a1=2.5)
        if dirx == lit_side:
            ln([lerp(top, foot, 0.35), lerp(top, foot, 0.8)], MINW, 'key', rng, wob=0.2)
    kn = []
    for _ in range(knots):
        i = rng.randint(int(len(sp) * 0.3), int(len(sp) * 0.85))
        f = rng.uniform(-0.05, 0.25) * lit_side
        N = normals(sp)[i]
        kn.append((sp[i][0] + N[0] * f * ws[i], sp[i][1] + N[1] * f * ws[i], clamp(ws[i] * 0.06, 4.5, 8)))
    bark3(sp, ws, rng, lit_side, lit=lit, moss=moss, knots=kn)
    return sp, ws, poly


def limb3(pts, w0, w1, rng, lit=0.5, moss=0.3, wc=None, under='amber'):
    sp = catmull([(p[0] + rng.gauss(0, 1.2), p[1] + rng.gauss(0, 1.2)) for p in pts], step=2.0)
    n = len(sp)
    ws = [w0 + (w1 - w0) * (i / max(1, n - 1)) ** 0.85 for i in range(n)]
    Lp, Rp = tube_poly(sp, ws)
    knock(Lp + Rp[::-1], 1.8)
    lowL = sum(p[1] for p in Lp) > sum(p[1] for p in Rp)
    lo, hi = (Lp, Rp) if lowL else (Rp, Lp)
    wc = wc or clamp(w0 * 0.075, MINW, 5.5)
    ln(lo[::2], wc, under if lit > 0.3 else 'key', rng, wob=0.3, a0=1.0, a1=3.0)
    a = rng.randint(0, max(1, len(hi) // 6))
    ln(hi[a:][::2], wc * 0.75, 'key', rng, wob=0.3, a0=1.0, a1=3.0)
    # which side is lit (lamp below): the lower edge; lit_side sign in normal terms
    if w0 > 24:
        bark3(sp, ws, rng, (1 if lowL else -1), lit=lit, moss=moss, row_sp=9.0, xhatch=0.3)
    return sp, ws


# ============================================================ round 3: leaf masses with real leaf texture
def leaf_band(sx, sy, rs, rsy, rng, ink_fn, clip, sc=1.0, depth=1.1, prob=0.9, sp=15.0):
    """leaf groups packed in the crescent just above a clump's lit lower edge, fanning out from the clump's heart,
    thinning upward into the dark"""
    y0 = sy - rsy * depth
    yy = y0
    row = 0
    while yy < sy + rsy:
        xx = sx - rs + (sp * 0.5 if row % 2 else 0) + rng.uniform(0, sp * 0.3)
        while xx < sx + rs:
            px, py = xx + rng.gauss(0, sp * 0.18), yy + rng.gauss(0, sp * 0.18)
            e = ((px - sx) / rs) ** 2 + ((py - sy) / rsy) ** 2
            if e < 0.92 and (clip is None or pip(px, py, clip)):
                v = clamp((py - y0) / (sy + rsy * 0.9 - y0), 0, 1)       # 0 high .. 1 at the lit edge
                if rng.random() < prob * (0.22 + 0.78 * v ** 1.2):
                    ang = math.pi / 2 + 1.05 * (px - sx) / rs + rng.gauss(0, 0.22)
                    leaf_group(px, py, ang, (12.5 + 4.0 * v) * sc, rng, ink_fn(v), n=rng.choice((2, 3, 3)), sp=7.4)
            xx += sp * rng.uniform(0.9, 1.12)
        yy += sp * 0.8 * rng.uniform(0.92, 1.08)
        row += 1


def leaf_mass3(cx, cy, rx, ry, rng, lit=0.0, sc=1.0, gapm=5.5, rimw=None, halftone_on=True, drip_n=None,
               key_rim=True, density=1.0):
    """a rain-tree leaf mass seen from below at night: clumps inside clumps, each with a scalloped lower edge and a
    crescent of leaf strokes fanning up from it into the dark; the outer lower edge caught firm by the lamp light;
    amber halftone only on the belly over a lamp; water dripping off it"""
    out = lobed(cx, cy, rx, ry, rng, tip=16.0 * sc, depth=0.42)
    # a mass only hides what is behind its leafy lower part (its top is dark anyway): knock the lower 70% + a gap
    occ = [p for p in grow(out, gapm)]
    cut = cy - ry * 0.45
    occ = [(x, max(y, cut)) for x, y in occ]
    knock(occ, 0)
    y_top, y_bot = cy - ry, cy + ry
    tpos = lambda y: clamp((y - y_top) / (y_bot - y_top), 0, 1)
    clip = grow(out, -3.0)
    nsub = int(clamp(rx * ry / (34.0 * 22.0 * sc * sc) * density, 1, 18))
    subs = []
    for _ in range(nsub * 4):
        if len(subs) >= nsub:
            break
        sx = cx + rng.uniform(-0.8, 0.8) * rx
        sy = cy - ry * 0.8 + ry * 1.25 * math.sqrt(rng.random())
        if not pip(sx, sy, grow(out, -12 * sc)):
            continue
        rs = rng.uniform(20, 34) * sc * (0.85 + 0.35 * tpos(sy))
        subs.append((sx, sy, rs, rs * rng.uniform(0.5, 0.62)))
    subs.sort(key=lambda c: c[1])
    # the deepest layer: a dense band of leaves along the whole lower edge; the clumps then cut into it
    leaf_band(cx, cy + ry * 0.02, rx * 0.97, ry * 0.95, rng, lambda v: 'green', clip, sc=sc, depth=0.35, prob=0.9)
    for sx, sy, rs, rsy in subs:
        t = tpos(sy)
        st = 0.15 + 0.85 * t ** 1.3
        knock([(x, max(y, sy - rsy * 0.3)) for x, y in ell(sx, sy, rs * 1.06, rsy * 1.12, n=18)], 0.6,
              layers=('green', 'key', 'amber'))
        if rng.random() > 0.3 + 0.7 * st:
            continue
        lit_here = lit > 0.3 and t > 0.55
        leaf_band(sx, sy, rs, rsy, rng,
                  (lambda v: 'amber' if (v > 0.62 and rng.random() < 0.25 + 0.7 * lit) else 'green') if lit_here else
                  (lambda v: 'green'), clip, sc=sc, prob=0.95 * (0.35 + 0.65 * st))
        a0, a1 = 0.1 * math.pi + rng.uniform(-0.1, 0.1), 0.9 * math.pi + rng.uniform(-0.1, 0.1)
        arc = [p for p in scallop_arc(sx, sy, rs, rsy, a0, a1, rng, tip=10 * sc) if pip(p[0], p[1], clip)]
        if len(arc) > 4 and rng.random() < 0.3 + 0.7 * st:
            ink = 'key' if (lit > 0.45 and t > 0.72 and rng.random() < 0.6) else 'green'
            ln(arc, MINW * 1.1, ink, rng, wob=0.12, a0=1.0, a1=1.8)
    lower = [p for p in out if p[1] > cy - ry * 0.02]
    wr = rimw or MINW * (1.6 if rx > 60 else 1.35 if rx > 30 else 1.15)
    # order lower points along the outline
    idx = [i for i, p in enumerate(out) if p[1] > cy - ry * 0.02]
    runs, cur, prev = [], [], None
    for i in idx:
        if prev is not None and i != prev + 1:
            runs.append(cur)
            cur = []
        cur.append(out[i])
        prev = i
    if cur:
        runs.append(cur)
    if len(runs) > 1 and idx[0] == 0 and idx[-1] == len(out) - 1:
        runs[0] = runs[-1] + runs[0]
        runs.pop()
    for run in runs:
        j = 0
        while j < len(run) - 2:
            L = rng.randint(12, 26)
            seg = run[j:j + L + 1]
            j += L + rng.choice((0, 0, 0, 5))
            if len(seg) < 3:
                continue
            ink = 'amber' if (lit > 0.4 and rng.random() < 0.6) else ('key' if key_rim else 'green')
            ln(seg, wr, ink, rng, wob=0.15, a0=1.0, a1=1.8)
    upper = [p for p in out if p[1] < cy - ry * 0.3]
    j = rng.randint(0, 6)
    while j < len(upper) - 3:
        L = rng.randint(4, 8)
        if rng.random() < 0.45:
            ln(upper[j:j + L], MINW, 'green', rng, wob=0.12, a0=1.0, a1=1.8)
        j += L + rng.randint(4, 12)
    if False and halftone_on and lit > 0.3:
        halftone_in(out, lambda x, y: lit * clamp((tpos(y) - 0.6) / 0.4, 0, 1) ** 1.2, 'amber', rng,
                    cell=11.0 * sc, angle=0.5, maxf=0.46, knock_under=('green',))
    nd = drip_n if drip_n is not None else (rng.randint(2, 4) if lit > 0.3 and rx > 30 else rng.randint(0, 1))
    if nd:
        low = sorted(out, key=lambda p: -p[1])[:max(4, len(out) // 5)]
        for _ in range(nd):
            x, y = rng.choice(low)
            l = rng.uniform(10, 18) * sc
            ink = 'amber' if lit > 0.4 else 'key'
            ln([(x, y + 5), (x + 0.4, y + 5 + l)], MINW, ink, rng, wob=0.1, a0=0.8, a1=1.4)
            dot(x + 0.5, y + 5 + l + rng.uniform(6, 10), MINW * 0.68, ink, rng)
    return out


def crown3(clusters, rng, sc=1.0, **kw):
    outs = []
    for c in sorted(clusters, key=lambda c: (c[1] + c[3] * 0.5)):
        cx, cy, rx, ry, lit = c[:5]
        outs.append(leaf_mass3(cx, cy, rx, ry, rng, lit=lit, sc=c[5] if len(c) > 5 else sc, **kw))
    return outs


def cloud_body2(cx, yb, wdt, hgt, rng, beams=(), lit=1.0):
    """a low cloud seen from below: one clean outline (wavy belly, cauliflower envelope on top), thin broken cream
    contour on the lobes, the belly lit warm from the city with amber halftone fading upward to black"""
    nl = rng.randint(3, 5)
    lobes = []
    for k in range(nl):
        f = (k + 0.5) / nl + rng.uniform(-0.06, 0.06)
        lr = wdt / nl * rng.uniform(0.62, 0.85)
        ly = yb - hgt * (0.5 + 0.5 * math.sin(math.pi * f)) * rng.uniform(0.82, 1.0) + lr * 0.55
        lobes.append((cx - wdt / 2 + wdt * f, ly, lr))
    xs = [cx - wdt / 2 + wdt * i / 60 for i in range(61)]
    top = []
    for x in xs:
        best = None
        for lx, ly, lr in lobes:
            dx = x - lx
            if abs(dx) < lr:
                y = ly - math.sqrt(lr * lr - dx * dx) * 0.78
                best = y if best is None else min(best, y)
        if best is None:
            best = yb - 6
        top.append((x, min(best, yb - 6)))
    base = [(x, yb + 3.5 * math.sin(i * 0.5 + cx) + hgt * 0.12 * math.sin(math.pi * i / 60)) for i, x in enumerate(xs)]
    poly = top + base[::-1]
    knock(grow(poly, 4.0), 0)
    y_top = min(p[1] for p in top)
    def tone(x, y):
        v = (y - y_top) / max(1, yb + 4 - y_top)
        return lit * clamp((v - 0.3) / 0.7, 0, 1) ** 1.35
    in_beam = lambda x, y: any(pip(x, y, bp) for bp in beams)
    halftone_in(poly, lambda x, y: 0.0 if in_beam(x, y) else tone(x, y), 'amber', rng, cell=10.5, angle=0.42, maxf=0.52)
    # contour: broken cream on the lobes; the belly edge firmer, amber
    i = rng.randint(0, 4)
    while i < len(top) - 2:
        L = rng.randint(5, 12)
        if rng.random() < 0.75:
            ln(top[i:i + L], MINW, 'key', rng, wob=0.15, a0=1.0, a1=2.0)
        i += L + rng.randint(1, 4)
    i = rng.randint(0, 3)
    while i < len(base) - 2:
        L = rng.randint(8, 18)
        ln(base[i:i + L], MINW * 1.3, 'amber', rng, wob=0.15, a0=1.0, a1=2.0)
        i += L + rng.randint(1, 3)
    # inner lobe seams: one or two short arcs where a lobe sits in front of another
    for lx, ly, lr in lobes[1:-1]:
        if rng.random() < 0.7:
            arc = ell(lx, ly, lr * 0.8, lr * 0.62, n=8, a0=math.pi * 1.1, a1=math.pi * 1.55, rng=rng)
            arc = [p for p in arc if pip(p[0], p[1], poly)]
            if len(arc) > 2:
                ln(arc, MINW, 'key', rng, wob=0.1)
    return poly
