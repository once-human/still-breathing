"""lib_r26.py: the last pass, after the owner's verdict on round 25 ("more painterly, brush-based").

- the sky: cloud bands built only from loose wavy horizontal brush strokes with black between them (the round-8 hand),
  in night blue, ice where the white beams cut through
- the stage: a real rig at a real scale: sheet roof in strokes, a clean box truss, ladder legs, hung line arrays,
  subs, a screen of soft grainy dot footage, and one small figure at a booth at the front
- the wet road: one column of stacked horizontal tapered strokes under each light, plus broken painterly puddles
- drizzle: one slant, long fine strokes, only where light is behind it
- brushed(): big flat colour fills turned into directional strokes with black between them
"""
from kit import *
from lib_life import *
from lib_v3 import *
from lib_r18 import *
from lib_r18 import _ink
import lib_r18


def _ink2(img, pts, w, rng, wob=0.12, trem=0.06, a0=1.2, a1=2.0, erase=False):
    """a tapered hand stroke straight into a scratch image"""
    d = ImageDraw.Draw(img)
    keep = A.D.get('_tmp')
    A.D['_tmp'] = d
    try:
        A._render(A.hand(pts, wob=wob, trem=trem, rng=rng), w, '_tmp', a0, a1, 0.15, rng, erase=erase)
    finally:
        if keep is None:
            del A.D['_tmp']
        else:
            A.D['_tmp'] = keep


# ============================================================ flat fills -> brush strokes
def _erode(a, r):
    out = a.copy()
    for s in range(1, r + 1):
        out[s:, :] &= a[:-s, :]
        out[:-s, :] &= a[s:, :]
    b = out.copy()
    for s in range(1, r + 1):
        out[:, s:] &= b[:, :-s]
        out[:, :-s] &= b[:, s:]
    return out


def _dilate(a, r):
    out = a.copy()
    for s in range(1, r + 1):
        out[s:, :] |= a[:-s, :]
        out[:-s, :] |= a[s:, :]
    b = out.copy()
    for s in range(1, r + 1):
        out[:, s:] |= b[:, :-s]
        out[:, :-s] |= b[:, s:]
    return out


def stroke_tex(bb, ang, rng, w=(1.15, 1.55), gap=(1.0, 1.6), L=(14, 40), lgap=(0.8, 2.4), wave=0.0, jit=0.06):
    """a field of directional brush strokes (full-res L image): rows across the direction, each row broken into
    strokes of varied length with black between them, the rows a little uneven"""
    img = Image.new('L', (W, H), 0)
    x0, y0, x1, y1 = bb
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rad = math.hypot(x1 - x0, y1 - y0) / 2 + 10
    ux, uy = math.cos(ang), math.sin(ang)
    nx, ny = -uy, ux
    d = -rad + rng.uniform(0, 4)
    while d < rad:
        wr = MINW * rng.uniform(*w)
        a_ = ang + rng.gauss(0, jit)
        vx, vy = math.cos(a_), math.sin(a_)
        s = -rad + rng.uniform(0, 12)
        while s < rad:
            l = rng.uniform(*L)
            px, py = cx + nx * d + ux * s, cy + ny * d + uy * s
            if x0 - 20 < px < x1 + 20 and y0 - 20 < py < y1 + 20:
                n = max(3, int(l / 4))
                ph = rng.uniform(0, TAU)
                pts = [(px + vx * l * i / n + nx * wave * math.sin(ph + 6.0 * i / n),
                        py + vy * l * i / n + ny * wave * math.sin(ph + 6.0 * i / n)) for i in range(n + 1)]
                _ink2(img, pts, wr * rng.uniform(0.9, 1.1), rng, a0=1.0, a1=1.8)
            s += l + MINW * rng.uniform(*lgap)
        d += wr + MINW * rng.uniform(*gap)
    return img


def brushed(fn, layers=('amber', 'copper'), ang=math.pi / 2 + 0.05, thick=6.0, **tk):
    """run fn, then turn every thick flat fill it laid in `layers` into brush strokes (thin parts stay as drawn)"""
    def wrapped(*a, **k):
        before = {l: A.L[l].copy() for l in layers}
        out = fn(*a, **k)
        rng = random.Random(hash((fn.__name__, len(LIGHTS))) & 0xffffff)
        r = max(2, int(thick * R))
        for l in layers:
            added = ImageChops.subtract(A.L[l], before[l])
            bb = added.getbbox()
            if not bb:
                continue
            bb = (max(0, bb[0] - 4), max(0, bb[1] - 4), min(W, bb[2] + 4), min(H, bb[3] + 4))
            ad = np.asarray(added.crop(bb)) > 0
            thick_ = _dilate(_erode(ad, r), r) & ad
            if not thick_.any():
                continue
            tex = stroke_tex(tuple(v / R for v in bb), ang, rng, **tk)
            tx = np.asarray(tex.crop(bb)) > 0
            cur = np.asarray(A.L[l].crop(bb)) > 0
            new = (cur & ~thick_) | (thick_ & tx)
            A.L[l].paste(Image.fromarray((new * 255).astype(np.uint8)), bb[:2])
        return out
    wrapped.__name__ = fn.__name__
    return wrapped


# ============================================================ THE SKY: stroke clouds
def _mass(x0, x1, base, peak, rng, ytop_min=244):
    """a cumulus band outline: lobed heads along the top, a soft wavy flat base"""
    heads = []
    n = max(2, int((x1 - x0) / 95) + 1)
    for i in range(n):
        cx = x0 + (x1 - x0) * (i + 0.5) / n + rng.uniform(-18, 18)
        edge_f = 1.0 - abs((cx - x0) / (x1 - x0) - 0.5) * 1.3
        heads.append((cx, rng.uniform(75, 130), peak * clamp(edge_f, 0.55, 1.0) * rng.uniform(0.78, 1.0)))
    top = []
    m = 80
    for j in range(m + 1):
        x = x0 + (x1 - x0) * j / m
        h = 0.0
        for cx, r, hh in heads:
            u = (x - cx) / r
            if abs(u) < 1:
                h = max(h, hh * math.sqrt(1 - u * u))
        h = max(h, peak * 0.72 * math.sin(math.pi * j / m) ** 0.6)
        top.append((x, max(ytop_min, base - h)))
    bot = [(x0 + (x1 - x0) * j / m, base + 3.5 * math.sin(j * 0.5) + 2 * math.sin(j * 1.3)) for j in range(m, -1, -1)]
    return top + bot, top


def _beam_hit(x, y, beams):
    for (bx, by), ang, top_y in beams:
        if y > by - 8:
            continue
        ux, uy = math.sin(ang), -math.cos(ang)
        t = (by - y) / max(0.2, -uy)
        cx = bx + ux * t
        if abs(x - cx) < 7 + 0.1 * t:
            return True
    return False


def cloud_strokes(specs, rng, beams=(), ymin=244):
    """specs far to near: (x0, x1, base, peak). Each band is only rows of loose wavy horizontal strokes; a nearer band
    clears a black seam round itself; strokes the white beams pass through turn ice"""
    T = {k: Image.new('L', (W, H), 0) for k in ('blue', 'ice', 'key')}
    for x0, x1, base, peak in specs:
        poly, top = _mass(x0, x1, base, peak, rng, ymin)
        # seam: clear the far strokes behind this band
        for k in T:
            d = ImageDraw.Draw(T[k])
            pp = P(poly)
            d.polygon(pp, fill=0)
            d.line(pp + [pp[0]], fill=0, width=int(MINW * 2.6 * R), joint='curve')
        msk = Image.new('L', (1200, 1600), 0)
        ImageDraw.Draw(msk).polygon(poly, fill=255)
        mk = np.asarray(msk) > 0
        y = base - rng.uniform(1, 3)
        while y > ymin:
            yi = int(y)
            if 0 <= yi < 1600:
                row = mk[yi, :]
                x = x0 + rng.uniform(0, 14)
                while x < x1:
                    l = rng.uniform(20, 72)
                    xe = min(x1, x + l)
                    if row[int(clamp(x, 0, 1199))] and row[int(clamp(xe, 0, 1199))] and row[int(clamp((x + xe) / 2, 0, 1199))]:
                        amp = rng.uniform(1.0, 2.3)
                        lam = rng.uniform(15, 28)
                        ph = rng.uniform(0, TAU)
                        n = max(4, int((xe - x) / 3))
                        pts = [(x + (xe - x) * i / n, y + amp * math.sin(ph + TAU * (xe - x) * i / n / lam)) for i in range(n + 1)]
                        mx = (x + xe) / 2
                        ink = 'ice' if _beam_hit(mx, y, beams) else ('ice' if (base - y < 7 and rng.random() < 0.18) else 'blue')
                        _ink2(T[ink], pts, MINW * rng.uniform(1.05, 1.4), rng, wob=0.15, trem=0.08, a0=1.3, a1=2.2)
                    x = xe + MINW * rng.uniform(1.5, 4.5)
            y -= MINW * rng.uniform(2.35, 2.85)
        # the top edge of the band: a few strokes riding the lobes
        i = rng.randint(0, 4)
        while i < len(top) - 4:
            n_ = rng.randint(4, 9)
            seg = [(px, py + 1.5) for px, py in top[i:i + n_] if py > ymin + 2]
            if len(seg) >= 3 and rng.random() < 0.7:
                mx, my = seg[len(seg) // 2]
                _ink2(T['ice' if _beam_hit(mx, my, beams) else 'blue'], seg, MINW * 1.15, rng, wob=0.1, trem=0.05)
            i += n_ + rng.randint(2, 5)
    return T


def beam7(T, root, ang, top_y, rng, w0=None, w1=None):
    """beam6, but its slot is cut through every cloud ink (blue and ice) so it always reads in front"""
    w0 = MINW * 1.3 if w0 is None else w0
    w1 = MINW * 2.1 if w1 is None else w1
    ux, uy = math.sin(ang), -math.cos(ang)
    nx, ny = -uy, ux
    L = (root[1] - top_y) / max(0.2, math.cos(ang))
    D = {k: ImageDraw.Draw(v) for k, v in T.items()}
    t0, t1 = 0.0, rng.uniform(0.34, 0.42)
    while t0 < 0.9:
        t1 = min(t1, 0.92)
        wa, wb = (w0 + (w1 - w0) * t0) / 2, (w0 + (w1 - w0) * t1) / 2
        if t0 > 0.55:
            wa, wb = wa * 0.8, wb * 0.75
        a = (root[0] + ux * L * t0, root[1] + uy * L * t0)
        b = (root[0] + ux * L * t1, root[1] + uy * L * t1)
        q = [(a[0] + nx * wa, a[1] + ny * wa), (b[0] + nx * wb, b[1] + ny * wb),
             (b[0] - nx * wb, b[1] - ny * wb), (a[0] - nx * wa, a[1] - ny * wa)]
        for k in ('blue', 'ice'):
            D[k].polygon(P(grow(q, MINW * 1.25)), fill=0)
        D['ice'].polygon(P(q), fill=255)
        if t0 < 0.2:
            _ink(D['key'], [lerp(a, b, 0.04), lerp(a, b, 0.92)], MINW * 1.0, 255, rng)
        t0 = t1 + rng.uniform(0.03, 0.05) * (1 + 3.0 * t1)
        t1 = t0 + rng.uniform(0.1, 0.16) * (1.25 - t0)
    end = (root[0] + ux * L, root[1] + uy * L)
    return [(root[0] + nx * 2, root[1] + ny * 2), (end[0] + nx * 8, end[1] + ny * 8),
            (end[0] - nx * 8, end[1] - ny * 8), (root[0] - nx * 2, root[1] - ny * 2)]


def sky_drizzle2(T, polys, rng, sp=26.0):
    """drizzle inside the beams: long fine ice strokes at the one slant, on black only"""
    ux, uy = math.cos(RAIN2), math.sin(RAIN2)
    for poly, root, L in polys:
        x0, y0, x1, y1 = bbox(poly)
        y = y0 + rng.uniform(0, sp)
        row = 0
        while y < y1:
            x = x0 + (sp * 0.5 if row % 2 else 0)
            while x < x1:
                px, py = x + rng.gauss(0, 4), y + rng.gauss(0, 4)
                if pip(px, py, poly):
                    d = math.hypot(px - root[0], py - root[1]) / L
                    if rng.random() < 0.8 * (1 - d) and d > 0.08:
                        l = rng.uniform(16, 40)
                        _ink2(T['ice'], [(px, py), (px + ux * l / 2, py + uy * l / 2), (px + ux * l, py + uy * l)],
                              MINW * 1.08, rng, wob=0.0, trem=0.0, a0=1.3, a1=1.8)
                x += sp * rng.uniform(0.9, 1.25)
            y += sp * rng.uniform(0.85, 1.1)
            row += 1


lib_r18.sky_drizzle = sky_drizzle2


# ============================================================ THE STAGE, at a real scale
def footage_soft(x0, y0, x1, y1, rng, p=9.0):
    """soft grainy phone footage on the LED screen as an AM dot screen in ice: a soft bright wash (a light over the
    crowd) where the screen is lit ice with dark grain holes, falling off into ice dots on black, a dark band of heads
    along the foot of the shot"""
    wq, hq = int(x1 - x0), int(y1 - y0)
    nz = np.asarray(Image.fromarray((np.random.RandomState(rng.randint(0, 1 << 30)).rand(10, 16) * 255).astype(np.uint8))
                    .resize((wq, hq), Image.BICUBIC).filter(ImageFilter.GaussianBlur(4)), dtype=np.float32) / 255.0
    vv, uu = np.mgrid[0:hq, 0:wq].astype(np.float32)
    uu, vv = uu / wq, vv / hq
    tone = 0.12 + 0.85 * np.exp(-((uu - 0.55) ** 2) / 0.1 - ((vv - 0.36) ** 2) / 0.1) + 0.55 * (nz - 0.5)
    tone -= 0.45 * np.clip((vv - 0.66) / 0.34, 0, 1)
    tone = np.clip(tone, 0, 1)
    lit = Image.fromarray(((tone >= 0.6) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2)).point(lambda v: 255 if v > 127 else 0)
    big = lit.resize((wq * int(R), hq * int(R)) if R >= 1 else (wq, hq), Image.BILINEAR).point(lambda v: 255 if v > 127 else 0)
    A.L['ice'].paste(255, (int(x0 * R), int(y0 * R)), big)
    rmin, rmax = MINW * 0.58, (p - MINW * 1.2) / 2
    for x, y in grid45((x0 + 3, y0 + 3, x1 - 3, y1 - 3), p):
        t = float(tone[min(hq - 1, int(y - y0)), min(wq - 1, int(x - x0))]) + rng.uniform(-0.08, 0.08)
        inside = lit.getpixel((min(wq - 1, int(x - x0)), min(hq - 1, int(y - y0)))) > 0
        if inside:
            r = rmin + (rmax - rmin) * clamp((0.95 - t) / 0.35, 0, 1)
            if t < 0.93:
                knock_ell(x + rng.gauss(0, 0.3), y + rng.gauss(0, 0.3), r, r, layers=('ice',))
        else:
            if rng.random() > t * 1.6:
                continue
            r = rmin + (rmax - rmin) * clamp((t - 0.2) / 0.4, 0, 1)
            dot(x + rng.gauss(0, 0.35), y + rng.gauss(0, 0.35), r, 'ice', rng)


def stage_dj3(rng, X0=398.0, X1=726.0, YR=392.0, YD=566.0):
    xc = (X0 + X1) / 2
    knock([(X0 - 8, YR - 12), (X1 + 8, YR - 12), (X1 + 8, YD + 16), (X0 - 8, YD + 16)], 0.8)
    # --- the screen: soft grainy footage in a clean frame
    sx0, sx1, sy0, sy1 = X0 + 56, X1 - 56, YR + 36, YD - 8
    footage_soft(sx0 + 3, sy0 + 3, sx1 - 3, sy1 - 3, rng)
    scr = [(sx0, sy0), (sx1, sy0), (sx1, sy1), (sx0, sy1)]
    pline(scr, MINW * 1.2, 'key', rng, over=(-0.5, 1.0), wob=0.05)
    # --- the box truss across the front: two chords, a clean zig-zag
    ty0, ty1 = YR + 11, YR + 24
    ln([(X0, ty0), (X1, ty0)], MINW * 1.2, 'key', rng, wob=0.04)
    ln([(X0, ty1), (X1, ty1)], MINW * 1.2, 'key', rng, wob=0.04)
    n = 14
    for i in range(n):
        a_ = (X0 + (X1 - X0) * i / n, ty1)
        b_ = (X0 + (X1 - X0) * (i + 0.5) / n, ty0)
        c_ = (X0 + (X1 - X0) * (i + 1) / n, ty1)
        ln([a_, b_, c_], MINW, 'key', rng, wob=0.02, a0=0.5, a1=0.8)
    # --- ladder-truss legs, straight down to the deck
    for lx in (X0 + 6, X1 - 6):
        knock([(lx - 9, ty1), (lx + 9, ty1), (lx + 9, YD + 14), (lx - 9, YD + 14)], 0.3)
        for dx in (-6.0, 6.0):
            ln([(lx + dx, ty0), (lx + dx, YD + 14)], MINW * 1.15, 'key', rng, wob=0.02)
        y_, s_ = ty1 + 4, 1
        while y_ + 16 < YD + 10:
            ln([(lx - 6 * s_, y_), (lx + 6 * s_, y_ + 16)], MINW, 'key', rng, wob=0.02, a0=0.5, a1=0.8)
            y_ += 16
            s_ = -s_
    # --- the sheet roof: a pale span laid in two long strokes, not a fill
    sag = [(X0 - 10 + (X1 - X0 + 20) * i / 20, YR + 8 + 3.0 * math.sin(math.pi * i / 20)) for i in range(21)]
    topl = [(X0 - 8, YR - 5), (xc - 70, YR - 8), (xc, YR - 9), (xc + 70, YR - 8), (X1 + 8, YR - 5)]
    knock(topl + sag[::-1], 1.0)
    for f, w_ in ((0.32, 1.25), (0.72, 1.1)):
        x = X0 - 4 + rng.uniform(0, 10)
        while x < X1:
            xe = min(X1 + 4, x + rng.uniform(60, 130))
            pts = [(xx, lerp((0, YR - 7.5), (0, YR + 9), f)[1] + 2.2 * math.sin(math.pi * (xx - X0) / (X1 - X0)))
                   for xx in (x, (x + xe) / 2, xe)]
            ln(pts, MINW * w_, 'ice', rng, wob=0.06, a0=1.2, a1=1.8)
            x = xe + rng.uniform(6, 14)
    ln(sag, MINW * 1.35, 'key', rng, wob=0.06)
    ln(topl, MINW * 1.15, 'key', rng, wob=0.06)
    # --- line arrays hung from the truss, a gentle J at the foot
    for sgn in (-1, 1):
        x_ = (X0 + 32) if sgn < 0 else (X1 - 32)
        y_ = ty1 + 4
        ln([(x_, ty1), (x_, y_)], MINW, 'key', rng)
        for i in range(8):
            hb = 8.6
            tilt = sgn * (0.0 if i < 5 else (i - 4) * 1.6)
            wt, wb = 19.0 - i * 0.25, 17.0 - i * 0.25
            box = [(x_ - wt / 2 + tilt * 0.3, y_), (x_ + wt / 2 + tilt * 0.3, y_), (x_ + wb / 2 + tilt, y_ + hb),
                   (x_ - wb / 2 + tilt, y_ + hb)]
            knock(grow(box, 1.0), 0.6)
            pline(box, MINW, 'key', rng, over=(-0.3, 0.5), wob=0.03)
            y_ += hb + 0.4
    # --- the deck, and subs stacked at each end of it
    for sgn in (-1, 1):
        bx = (X0 + 30) if sgn < 0 else (X1 - 30)
        for j in range(2):
            yb = YD - 14 * (j + 1)
            sub = [(bx - 16, yb), (bx + 16, yb), (bx + 16, yb + 13), (bx - 16, yb + 13)]
            knock(grow(sub, 1.5), 0.6)
            pline(sub, MINW, 'key', rng, over=(-0.3, 0.5), wob=0.03)
    ln([(X0 + 12, YD), (X1 - 12, YD)], MINW * 1.5, 'key', rng, wob=0.04)
    ln([(X0 + 18, YD + 13), (X1 - 18, YD + 13)], MINW, 'key', rng, wob=0.04)
    # --- the booth at the front and one small figure behind it (a person ~1/7 of the stage height)
    xd = xc - 3
    ttop = YD - 12
    knock([(xd - 13, YD - 34), (xd + 11, YD - 34), (xd + 13, ttop), (xd - 15, ttop)], 0.0, layers=('ice',))
    # body: shoulders and torso, head, one arm up
    body = [(xd - 6.5, ttop), (xd - 7.0, ttop - 9), (xd - 4.5, ttop - 13.5), (xd + 4.5, ttop - 13.5), (xd + 7.0, ttop - 9),
            (xd + 6.5, ttop)]
    knock(grow(body, 1.8), 0.0)
    head = (xd + 0.5, ttop - 18.5)
    knock_ell(head[0], head[1], 5.2, 5.6)
    ln(ell(head[0], head[1], 3.6, 3.9, n=14, a0=math.pi * 0.95, a1=math.pi * 2.05, rng=rng), MINW, 'key', rng, wob=0.02)
    ln([(xd - 7.2, ttop - 1), (xd - 6.8, ttop - 9.5), (xd - 3.8, ttop - 13.8), (xd + 4.0, ttop - 13.8)], MINW, 'key', rng,
       wob=0.02)
    arm = [(xd + 5.0, ttop - 12.5), (xd + 9.5, ttop - 20), (xd + 10.5, ttop - 29)]
    knock_line(arm, MINW + 3.6)
    ln(arm, MINW, 'key', rng, wob=0.02, a0=0.6, a1=1.2)
    # the booth: a black block, a cream top edge, a laptop lid
    booth = [(xd - 26, ttop), (xd + 26, ttop), (xd + 24, YD), (xd - 24, YD)]
    knock(grow(booth, 1.5), 0.6)
    ln([(xd - 27, ttop), (xd + 27, ttop)], MINW * 1.2, 'key', rng, wob=0.02)
    lap = [(xd - 18, ttop), (xd - 14, ttop - 7), (xd - 6, ttop - 7)]
    ln(lap, MINW, 'key', rng, wob=0.02, a0=0.6, a1=1.0)
    return dict(truss=(X0, X1, ty0), screen=(sx0, sy0, sx1, sy1), xc=xd, roof=YR - 22)


def crowd_dj4(rng, xa, xb, y_top, y_bot):
    """crowd_dj3 with more hands up: rows of heads as bumpy rims, arms and phones raised over them"""
    knock([(xa, y_top - 30), (xb, y_top - 30), (xb, y_bot + 2), (xa, y_bot + 2)], 0)
    rows = 3
    for r in range(rows):
        f = r / (rows - 1)
        hy = y_top + (y_bot - y_top) * (0.15 + 0.75 * f)
        hr = 4.6 + 1.6 * f
        x = xa + rng.uniform(0, hr) + (rows - r) * 3
        pts = []
        last_arm = -99
        while x < xb - hr:
            yj = hy + rng.uniform(-1.2, 1.2)
            for a_ in (math.pi * 1.0, math.pi * 1.25, math.pi * 1.5, math.pi * 1.75, math.pi * 2.0):
                pts.append((x + math.cos(a_) * hr, yj + math.sin(a_) * hr * 1.1))
            pts.append((x + hr * 1.35, yj + hr * 0.5))
            if r < 2 and rng.random() < 0.36 and x - last_arm > 13:
                last_arm = x
                for side in ((1,) if rng.random() < 0.7 else (-1, 1)):
                    ex = x + side * rng.uniform(0.2, 0.9) * hr
                    ey = yj - hr * rng.uniform(3.0, 4.3)
                    ln([(x + side * hr * 0.8, yj - hr * 0.2), (ex, ey)], MINW, 'key', rng, wob=0.03)
                    if side == 1 and rng.random() < 0.3:
                        ph = [(ex - 2.5, ey - 8), (ex + 2.7, ey - 8), (ex + 2.7, ey - 1), (ex - 2.5, ey - 1)]
                        knock(grow(ph, 1.6), 0)
                        fillp(ph, 'ice')
            x += hr * 2.7 + rng.uniform(0.3, 2.0)
        i = 0
        while i < len(pts) - 3:
            n_ = rng.randint(14, 30)
            ln(pts[i:i + n_], MINW, 'ice' if r != 1 else 'key', rng, wob=0.05, a0=0.6, a1=1.0)
            i += n_ + rng.randint(1, 3)


# ============================================================ THE WET ROAD
def col2(x, y0, y1, w0, w1, ink, rng, core=None, ymax=1458, art=None, dens=1.0):
    """a reflection column in the brush hand of the references: stacked horizontal tapered strokes of every length
    and weight, splitting, breaking into gaps, wobbling sideways, longer and wider toward us, dissolving at the end"""
    art = art or RA
    yend = min(y1, ymax)
    span = max(1.0, yend - y0)
    ph, ph2 = rng.uniform(0, TAU), rng.uniform(0, TAU)
    y = y0 + rng.uniform(0, 2)
    hole = 0
    while y < yend:
        t = (y - y0) / span
        wd = w0 + (w1 - w0) * t
        cx = x + wd * 0.13 * (0.6 * math.sin(y * 0.031 + ph) + 0.4 * math.sin(y * 0.083 + ph2))
        th = MINW * rng.uniform(1.0, 1.75) * (1 + 0.35 * t) * (1.15 if rng.random() < 0.12 else 1.0)
        if hole > 0:
            hole -= 1
        elif rng.random() > (0.1 + 0.58 * t ** 2.2) / dens:
            r_ = rng.random()
            if r_ < 0.66:
                segs = [(rng.uniform(-0.08, 0.08) * wd, wd * 0.5 * rng.uniform(0.4, 1.25))]
            elif r_ < 0.86:
                g = rng.uniform(0.04, 0.12) * wd
                segs = [(-g - wd * 0.18, wd * rng.uniform(0.12, 0.28)), (g + wd * 0.18, wd * rng.uniform(0.12, 0.28))]
            else:
                segs = [(rng.choice((-1, 1)) * rng.uniform(0.12, 0.35) * wd, wd * rng.uniform(0.12, 0.26))]
            for off, hl in segs:
                hl = max(hl, th * 1.1)
                c = cx + off
                pts = [(c - hl, y + rng.gauss(0, 0.5)), (c + rng.uniform(-0.2, 0.2) * hl, y + rng.gauss(0, th * 0.2)),
                       (c + hl, y + rng.gauss(0, 0.5))]
                art.line(pts, th, layer=ink, rng=rng, wob=0.35, trem=0.2, a0=1.5, a1=2.6, pv=0.3)
                if core and t < 0.45 and hl > wd * 0.3 and rng.random() < 0.5 and hl * 0.4 > MINW:
                    cc = c + rng.uniform(-0.15, 0.15) * hl
                    art.line([(cc - hl * 0.4, y + 0.3), (cc + hl * 0.4, y - 0.3)], max(MINW, th * 0.8), layer=core,
                             rng=rng, wob=0.2, trem=0.1, a0=1.2, a1=2.0, pv=0.2)
            if rng.random() < 0.06 + 0.1 * t:
                hole = rng.randint(1, 3)
        y += th + MINW * rng.uniform(0.8, 1.55) * (1 + 1.1 * t * t) / min(1.0, 0.5 + 0.5 * dens)


def reflect_brush(lights, rng, ymax=1458):
    n = 0
    for L in lights:
        if L.get('norefl'):
            continue
        gx, gy = pr(L['x'], 0, L['z'])
        my = pr(L['x'], -L['h'], L['z'])[1]
        if gy > ymax - 10:
            continue
        w0 = L.get('cw') or clamp(L['wm'] * S(L['z']), 6.0, 80.0)
        w1 = L.get('cw1') or w0 * 1.7
        length = (my - gy) * rng.uniform(1.35, 1.8) * min(1.8, L.get('stretch', 1.0)) + w0
        length = max(length, (ymax - gy) * L.get('reach', 0.24) * rng.uniform(0.85, 1.15))
        if L.get('y1'):
            length = L['y1'] - gy
        y0 = gy + clamp(0.05 * S(L['z']), 1.0, 6.0)
        core = L.get('core') if w0 > 12 else None
        dens = L.get('dens') or min(1.0, 0.55 + 0.45 * L['k']) * clamp(1.5 - L['z'] / 40.0, 0.4, 1.0)
        col2(gx, y0, gy + length, w0, w1, L['ink'], rng, core=core, ymax=ymax, dens=dens)
        # a street lamp also leaves a little warm wet shine on the ground either side of its column
        if L['ink'] == 'amber' and L['h'] > 5 and S(L['z']) > 25:
            s = S(L['z'])
            for _ in range(rng.randint(2, 3)):
                sx = gx + rng.choice((-1, 1)) * rng.uniform(0.7, 2.0) * w0
                sy = gy + rng.uniform(-0.35, 1.2) * 0.9 * s
                hl = rng.uniform(0.07, 0.16) * s
                if sy < ymax:
                    RA.line([(sx - hl, sy), (sx, sy + rng.gauss(0, 0.6)), (sx + hl, sy)], MINW * rng.uniform(1.0, 1.3),
                            layer='amber', rng=rng, wob=0.3, trem=0.15, a0=1.6, a1=2.6, pv=0.3)
        n += 1
    return n


def puddle2(cx, cy, rx, ry, rng, inks=('amber',), nlight=8):
    """a painterly puddle on the wet road: a broken cream outline (lost on one side), the light it holds as a few
    horizontal strokes inside, a drop landing in it"""
    ph = rng.uniform(0, TAU)
    m = 28
    pts = []
    for j in range(m + 1):
        a = TAU * j / m
        rr = 1 + 0.2 * math.sin(2 * a + ph) + 0.14 * math.sin(3 * a + 1.7 * ph) + 0.07 * math.sin(5 * a + 0.6 * ph)
        pts.append((cx + math.cos(a) * rx * rr, cy + math.sin(a) * ry * rr))
    j = rng.randint(0, 6)
    while j < m - 2:
        n_ = rng.randint(3, 7)
        if rng.random() < 0.55:
            RA.line(pts[j:j + n_ + 1], MINW * rng.uniform(1.0, 1.2), layer='key', rng=rng, wob=0.15, trem=0.1, a0=1.4, a1=2.2)
        j += n_ + rng.randint(2, 4)
    y = cy - ry * 0.55
    k = 0
    while y < cy + ry * 0.7 and k < nlight:
        f = math.sqrt(max(0.0, 1 - ((y - cy) / ry) ** 2))
        hl = rx * f * rng.uniform(0.3, 0.75)
        off = rng.uniform(-0.3, 0.3) * rx * f
        if hl > MINW * 1.5:
            RA.line([(cx + off - hl, y), (cx + off, y + rng.gauss(0, 0.5)), (cx + off + hl, y)], MINW * rng.uniform(1.0, 1.5),
                    layer=rng.choice(inks), rng=rng, wob=0.3, trem=0.15, a0=1.6, a1=2.6, pv=0.3)
        y += MINW * rng.uniform(2.2, 2.9)
        k += 1
    splash(cx + rng.uniform(-0.35, 0.35) * rx, cy + ry * rng.uniform(-0.1, 0.3), 90, rng.choice(inks), rng)


# ============================================================ DRIZZLE in the lamp light
def drizzle_cones2(rng):
    for poly, tone, ay, Lc, snap in CONES:
        gy = poly[2][1]

        def tf(px, py, poly=poly, ay=ay, gy=gy):
            v = (py - ay) / max(1.0, gy - ay)
            half = (poly[1][0] - poly[0][0]) / 2 + ((poly[2][0] - poly[3][0]) / 2 - (poly[1][0] - poly[0][0]) / 2) * v
            lat = abs(px - (poly[0][0] + poly[1][0]) / 2) / max(1.0, half)
            ramp = clamp((v - 0.1) / 0.18, 0, 1) * clamp((0.95 - v) / 0.2, 0, 1)
            return ramp * clamp((1.0 - lat) * 2.2, 0, 1)
        drizzle_in(poly, tf, 'amber', rng, sp=30.0, L=(22, 54), prob=0.7, snap=snap)
