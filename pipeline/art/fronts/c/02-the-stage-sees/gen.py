#!/usr/bin/env python3
"""
01 crowd, front 02: "what the stage sees". Full front, 33 cm.
The back is the crowd from behind; this is the reverse shot, from the stage. The lights are behind us, so the beams
come over our head and land on them: the faces are lit, drawn as cream shapes with the features cut out of the light.
The phones are seen from behind, torches on. The people from the back are here too, mirrored, because we are looking
the other way: the girl on her friend's shoulders (back right, here left), the yellow monkey cap (back left, here
right). Out past them the sound-desk tent and the two delay towers of an open-ground show.
    R=1 python3 gen.py   draft (4.7 px/mm)      python3 gen.py   final (94 px/cm)
"""
import math, os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pen

WMM, HMM = 330, 400
h, a = pen.boot(WMM, HMM, seed=20226, layers=('line', 'Y', 'G', 'B'))
rng = a.rng
TAU = math.tau


def rot(p, c, t):
    dx, dy = p[0] - c[0], p[1] - c[1]
    return (c[0] + dx * math.cos(t) - dy * math.sin(t), c[1] + dx * math.sin(t) + dy * math.cos(t))


def ell(cx, cy, rx, ry, n=12, jit=0.03, t0=0.0):
    return [(cx + rx * math.cos(t0 + TAU * i / n) * (1 + rng.gauss(0, jit)),
             cy + ry * math.sin(t0 + TAU * i / n) * (1 + rng.gauss(0, jit))) for i in range(n)]


def limb(ctrl, widths, lw, fill=None):
    sp, L, R = a.tube(ctrl, widths, rng=rng, wob=0.3, trem=0.25)
    poly = L + R[::-1]
    a.knock(poly)
    if fill:
        a.blob(poly[::3], fill, scale=(0.97, 1.0), jit=0.02, shift=0.3, gap=0.1, n=50)
    a.ink(L, lw, a0=1.0, a1=2.0, pv=0.15)
    a.ink(R, lw, a0=1.0, a1=2.0, pv=0.15)
    return sp


# ------------------------------------------------------------------ faces, lit from the stage
def face(cx, cy, w, o):
    """a face toward us. o: lit, hair, eyes, mouth, tilt, beard, specs, bindi, ear (earring ink), cap (ink)"""
    hh = w * o.get('hr', 1.22)
    t = o.get('tilt', 0.0)
    lw = max(1.15, w * 0.034)
    cw = max(1.15, w * 0.03)              # width of a cut feature
    c = (cx, cy)
    R = lambda x, y: rot((cx + x * w, cy + y * hh), c, t)
    hair = o.get('hair', 'short')
    # hair mass first (behind and round the face): only its edge is drawn, the shirt is the hair
    if hair in ('long', 'bun', 'short', 'curly', 'wavy'):
        if hair == 'long':
            hp = [R(-0.62, 0.62), R(-0.66, 0.0), R(-0.58, -0.42), R(-0.3, -0.62), R(0.05, -0.66), R(0.36, -0.6),
                  R(0.6, -0.36), R(0.66, 0.1), R(0.64, 0.66)]
        elif hair == 'curly':
            hp = []
            for i in range(11):
                aa = math.pi * (1.08 + 0.84 * i / 10)
                r = 0.66 + 0.05 * (i % 2)
                hp.append(R(math.cos(aa) * r, math.sin(aa) * r * 0.95 - 0.04))
        elif hair == 'wavy':
            hp = [R(-0.6, 0.18), R(-0.64, -0.2), R(-0.48, -0.55), R(-0.12, -0.66), R(0.25, -0.64), R(0.55, -0.45),
                  R(0.64, -0.1), R(0.58, 0.24)]
        else:
            hp = [R(-0.55, -0.02), R(-0.58, -0.34), R(-0.36, -0.6), R(0.02, -0.66), R(0.38, -0.6), R(0.58, -0.32),
                  R(0.55, 0.0)]
        a.knock(hp + [R(0.4, 0.5), R(-0.4, 0.5)])
        if hair == 'curly':
            for i in range(len(hp) - 1):
                p0, p1 = hp[i], hp[i + 1]
                m = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
                dx, dy = m[0] - cx, m[1] - cy
                d = math.hypot(dx, dy) or 1
                a.stroke([p0, (m[0] + dx / d * w * 0.06, m[1] + dy / d * w * 0.06), p1], lw, a0=0.6, a1=0.8)
        else:
            a.stroke(hp, lw, a0=1.2, a1=2.6)
        if hair == 'bun':
            bp = ell(*R(0.08, -0.74), w * 0.2, w * 0.17, n=10)
            a.knock(bp)
            a.stroke(bp + [bp[0]], lw)
    # the face
    fp = [R(-0.47, -0.3), R(-0.48, 0.04), R(-0.41, 0.3), R(-0.24, 0.47), R(0.0, 0.53), R(0.24, 0.47), R(0.41, 0.3),
          R(0.48, 0.04), R(0.47, -0.3), R(0.32, -0.47), R(0.0, -0.52), R(-0.32, -0.47)]
    lit = o.get('lit', True)
    fpath = a.hand(fp, closed=True, wob=w * 0.006, trem=w * 0.004, step=0.5)
    a.knock(fpath)
    for sg in (-1, 1):                           # ears
        ep = [R(sg * 0.45, -0.1), R(sg * 0.56, -0.13), R(sg * 0.57, 0.06), R(sg * 0.46, 0.14)]
        a.stroke(ep, lw * 0.9)
        if o.get('ear'):
            ex, ey = R(sg * 0.52, 0.2)
            a.dot(ex, ey + w * 0.05, max(1.2, w * 0.045), layer=o['ear'])
    if lit:
        a.fill(fpath, 'line')
        if w >= 16:                               # the shadow side: the light comes from above and to one side
            sd = o.get('shade', rng.choice((-1, 1)))
            cr = [R(sd * 0.5, -0.32), R(sd * 0.31, -0.12), R(sd * 0.27, 0.12), R(sd * 0.18, 0.36), R(sd * 0.0, 0.56),
                  R(sd * 0.3, 0.5), R(sd * 0.47, 0.3), R(sd * 0.52, 0.0)]
            pp = a.hand(cr, closed=True, wob=0.08, trem=0.05, step=0.5)
            a.D['line'].polygon(h.P(pp), fill=0)
    else:
        a.ink(fpath, lw, closed=True, a0=0.8, a1=1.4)
    # hair over the forehead
    cap = o.get('cap')
    if cap == 'monkey':                           # a knitted monkey cap: wraps the chin, the face in an oval window, a bobble
        mp = [R(-0.6, 0.62), R(-0.66, 0.0), R(-0.54, -0.5), R(-0.2, -0.72), R(0.2, -0.72), R(0.54, -0.5), R(0.66, 0.0),
              R(0.6, 0.62), R(0.36, 0.8), R(0.0, 0.84), R(-0.36, 0.8)]
        win = [R(-0.36, -0.2), R(-0.38, 0.12), R(-0.27, 0.4), R(0.0, 0.5), R(0.27, 0.4), R(0.38, 0.12), R(0.36, -0.2),
               R(0.18, -0.3), R(-0.18, -0.3)]
        a.knock(mp)
        a.blob(mp, 'Y', jit=0.02, shift=0.3, gap=0.0)
        mpp = a.hand(mp, closed=True, wob=0.2, trem=0.2, step=0.5)
        for k in range(9):                       # the knit's ribs, all round the window, chin to crown
            x = -0.56 + k * 0.14
            if abs(x) < 0.33:
                a.stroke([R(x * 0.95, -0.66 + abs(x) * 0.4), R(x, -0.36)], cw, a0=0.5, a1=1.2)
            else:
                a.stroke([R(x * 0.95, -0.6 + abs(x) * 0.3), R(x * 1.02, 0.2), R(x * 0.85, 0.66)], cw, a0=0.5, a1=1.2)
        for x in (-0.2, 0.0, 0.2):
            a.stroke([R(x, 0.56), R(x * 1.05, 0.78)], cw, a0=0.5, a1=1.2)
        a.knock(win)
        if lit:
            a.fill(a.hand(win, closed=True, wob=0.15, trem=0.1, step=0.5), 'line')
        a.ink(mpp, lw, closed=True)
        a.stroke(win + [win[0]], lw * 1.25)
        bb = ell(*R(0.0, -0.86), w * 0.17, w * 0.15, n=9)
        a.knock(bb)
        a.blob(bb, 'Y', gap=0)
        a.stroke(bb + [bb[0]], lw * 0.9)
        for k in range(4):
            bx_, by_ = R(-0.1 + k * 0.07, -0.86)
            a.stroke([(bx_, by_ - w * 0.08), (bx_ + w * 0.01, by_ + w * 0.08)], cw, a0=0.4, a1=1.0)
    elif cap == 'cap':                            # a baseball cap, green
        cp = [R(-0.5, -0.24), R(-0.46, -0.52), R(-0.2, -0.7), R(0.15, -0.71), R(0.44, -0.54), R(0.5, -0.24)]
        br = [R(-0.62, -0.2), R(0.0, -0.32), R(0.62, -0.2), R(0.5, -0.1), R(0.0, -0.18), R(-0.5, -0.1)]
        a.shape(cp + [R(0, -0.28)], lw, fill='G')
        a.shape(br, lw, fill='G')
    elif hair != 'none':
        # the hairline cut across the top of the face: a fringe / parting, the hair black
        if hair in ('long', 'wavy'):
            hl = [R(-0.5, -0.05), R(-0.42, -0.3), R(-0.15, -0.42), R(0.02, -0.38), R(0.24, -0.43), R(0.46, -0.3), R(0.5, -0.05),
                  R(0.5, -0.6), R(-0.5, -0.6)]
        elif hair == 'curly':
            hl = [R(-0.48, -0.12), R(-0.36, -0.34), R(-0.18, -0.3), R(0.0, -0.36), R(0.18, -0.3), R(0.36, -0.36), R(0.48, -0.12),
                  R(0.5, -0.6), R(-0.5, -0.6)]
        else:
            hl = [R(-0.48, -0.14), R(-0.3, -0.36), R(0.1, -0.42), R(0.36, -0.36), R(0.48, -0.16), R(0.5, -0.6), R(-0.5, -0.6)]
        a.knock(hl)
        a.stroke(hl[:-2], lw * 0.95, a0=0.8, a1=1.4)
        if hair != 'curly':
            for k in range(2 if w < 30 else 4):
                x0 = -0.3 + k * 0.2 + rng.uniform(-0.04, 0.04)
                a.stroke([R(x0, -0.56), R(x0 + 0.08, -0.48), R(x0 + 0.12, -0.42 + rng.uniform(-0.02, 0.03))], cw * 1.05, a0=0.6, a1=2.5)
    if o.get('band'):                             # a bandana across the forehead, blue
        bd = [R(-0.5, -0.32), R(0.0, -0.4), R(0.5, -0.32), R(0.5, -0.18), R(0.0, -0.26), R(-0.5, -0.18)]
        a.shape(bd, lw, fill='B')
        kx, ky = R(0.56, -0.22)
        a.stroke([(kx, ky), (kx + w * 0.12, ky + w * 0.12)], lw)
        a.stroke([(kx, ky), (kx + w * 0.16, ky + w * 0.02)], lw)
    # features: cut out of the light (or drawn, if unlit)
    def feat(pts, k=1.0):
        if lit:
            a.carve(pts, cw * k, layer='line', a0=0.5, a1=0.8, pv=0.12, wob=0.06 * w / 30, trem=0.04)
        else:
            a.stroke(pts, cw * k * 1.05, a0=0.5, a1=0.8, wob=0.06 * w / 30, trem=0.04)
    def hole(poly):
        pp = a.hand(poly, closed=True, wob=0.05, trem=0.02, step=0.4)
        if lit:
            a.D['line'].polygon(h.P(pp), fill=0)
        else:
            a.ink(pp, cw, closed=True)
    eyes = o.get('eyes', 'shut')
    for sg in (-1, 1):
        ex = sg * 0.19
        if eyes == 'shut':
            feat([R(ex - 0.11, -0.03), R(ex, 0.01), R(ex + 0.11, -0.03)])
        elif eyes == 'happy':
            feat([R(ex - 0.11, 0.0), R(ex, -0.05), R(ex + 0.11, 0.0)])
        elif eyes == 'up':
            hole(ell(*R(ex, -0.05), w * 0.06, w * 0.045, n=8))
        else:
            hole(ell(*R(ex, -0.02), w * 0.055, w * 0.06, n=8))
        bi = 0.18 if eyes != 'up' else 0.22
        feat([R(ex - 0.12, -bi + 0.02 * sg * o.get('brow', 0)), R(ex, -bi - 0.03), R(ex + 0.12, -bi + 0.01)], 1.05)
    if o.get('specs'):
        for sg in (-1, 1):
            g = ell(*R(sg * 0.2, -0.02), w * 0.13, w * 0.11, n=10)
            feat(g + [g[0]], 0.95)
        feat([R(-0.08, -0.04), R(0.0, -0.06), R(0.08, -0.04)], 0.9)
    feat([R(0.02, 0.0), R(-0.03, 0.17), R(0.04, 0.2)], 0.95)            # nose
    mouth = o.get('mouth', 'smile')
    if mouth == 'O':                                                        # singing
        hole(ell(*R(0.0, 0.33), w * 0.09, w * 0.11, n=10))
    elif mouth == 'open':                                                   # shouting the words
        hole([R(-0.17, 0.27), R(0.0, 0.25), R(0.17, 0.27), R(0.12, 0.38), R(0.0, 0.42), R(-0.12, 0.38)])
    elif mouth == 'grin':
        hole([R(-0.18, 0.27), R(0.0, 0.29), R(0.18, 0.26), R(0.1, 0.35), R(-0.1, 0.35)])
    else:
        feat([R(-0.14, 0.28), R(0.0, 0.33), R(0.14, 0.28)])
    if o.get('beard'):                                                      # beard: the dark of the shirt
        bp = [R(-0.47, 0.05), R(-0.36, 0.24), R(-0.18, 0.27), R(0.0, 0.24), R(0.18, 0.27), R(0.36, 0.24), R(0.47, 0.05),
              R(0.42, 0.32), R(0.24, 0.48), R(0.0, 0.55), R(-0.24, 0.48), R(-0.42, 0.32)]
        if lit:
            pp = a.hand(bp, closed=True, wob=0.1, trem=0.1, step=0.5)
            a.D['line'].polygon(h.P(pp), fill=0)
            mp_ = [R(-0.12, 0.33), R(0.0, 0.31), R(0.12, 0.33), R(0.06, 0.39), R(-0.06, 0.39)]
            a.fill(a.hand(mp_, closed=True, wob=0.05, trem=0.02), 'line') if mouth == 'smile' else None
            a.ink(a.hand(bp, closed=True, wob=0.1, trem=0.1, step=0.5)[5:], lw * 0.8, a0=0.5, a1=1.0)
    if o.get('bindi'):
        a.dot(*R(0.0, -0.17), max(1.25, w * 0.04), layer='B')
    return lw


def body(cx, cy, w, o):
    """neck, shoulders and the arms. o: arms ('up2', 'up1', 'phone', 'peace', 'down', 'fist'), top (ink), side"""
    lw = max(1.15, w * 0.034)
    sy = cy + w * 0.95                     # the shoulder line
    sw = w * o.get('sw', 1.15)
    side = o.get('side', 1)
    t = o.get('lean', 0.0)
    top = o.get('top')
    # shoulders and chest, dropping out of the bottom of the drawing
    drop = o.get('drop', 0.95)                   # how far down the body is drawn before the pen stops
    sh = [(cx - sw * 0.15, sy - w * 0.06), (cx - sw * 0.75, sy + w * 0.04), (cx - sw * 0.98, sy + w * 0.3),
          (cx - sw * 1.02, sy + w * drop)]
    sh2 = [(2 * cx - x, y) for x, y in sh]
    # the bottom of the body is not cut straight: it sags in a loose curve, the colour stopping short of it
    bot = [(cx + sw * 0.9 * math.cos(math.pi * k / 6), sy + w * (drop + 0.25 * math.sin(math.pi * k / 6)) + rng.uniform(-1, 1))
           for k in range(1, 6)]
    poly = sh + bot + sh2[::-1]
    a.knock(poly)
    if top:
        a.blob(sh + [(cx + sw * 0.85 * math.cos(math.pi * k / 6), sy + w * (drop * 0.9 - 0.3 * drop * math.sin(math.pi * k / 6)))
                     for k in range(1, 6)] + sh2[::-1], top, scale=(0.98, 1.0), jit=0.03, gap=0.3)
    a.stroke(sh, lw, a0=0.8, a1=4.5)
    a.stroke(sh2, lw, a0=0.8, a1=4.5)
    a.stroke([(cx - w * 0.2, sy - w * 0.08), (cx, sy + w * 0.12), (cx + w * 0.2, sy - w * 0.08)], lw * 0.9)   # the neckline
    a.stroke([(cx - w * 0.17, cy + w * 0.5), (cx - w * 0.18, sy - w * 0.04)], lw * 0.9)
    a.stroke([(cx + w * 0.17, cy + w * 0.5), (cx + w * 0.18, sy - w * 0.04)], lw * 0.9)
    arms = o.get('arms', 'up2')
    ups = {'up2': (-1, 1), 'up1': (side,), 'phone': (side,), 'peace': (side,), 'fist': (side,), 'down': ()}[arms]
    for sg in ups:
        s0 = (cx + sg * sw * 0.8, sy + w * 0.1)
        el = (cx + sg * sw * (1.25 + rng.uniform(-0.1, 0.15)), sy - w * (0.75 + rng.uniform(-0.1, 0.1)))
        wr = (cx + sg * sw * (1.05 + rng.uniform(-0.15, 0.2)), sy - w * (1.8 + rng.uniform(-0.15, 0.15)))
        limb([s0, ((s0[0] + el[0]) / 2 + sg * w * 0.05, (s0[1] + el[1]) / 2), el], [w * 0.34, w * 0.28], lw, fill=top)
        limb([el, ((el[0] + wr[0]) / 2, (el[1] + wr[1]) / 2), wr], [w * 0.25, w * 0.21], lw)
        ang = math.atan2(wr[1] - el[1], wr[0] - el[0])
        kind = 'open' if arms in ('up2', 'up1') else ('peace' if arms == 'peace' else 'fist')
        if arms == 'phone' and sg == side:
            phone(wr, ang, w * 0.95, lw)
        else:
            a.draw_hand(wr, ang, w * 0.62, kind, lw, mirror=(sg > 0))
        if o.get('bangles') and sg == ups[0]:
            for k, col in enumerate(('B', 'Y')):
                tt = 0.7 + 0.1 * k
                bx, by = el[0] + (wr[0] - el[0]) * tt, el[1] + (wr[1] - el[1]) * tt
                nx, ny = -math.sin(ang), math.cos(ang)
                a.stroke([(bx + nx * w * 0.17, by + ny * w * 0.17), (bx - nx * w * 0.17, by - ny * w * 0.17)], max(1.2, lw), layer=col, a0=0.4, a1=0.5)


def phone(wr, ang, size, lw):
    """a phone seen from behind (we are the stage): the camera bump, the torch on, a hand round its sides"""
    up = -math.pi / 2 + max(-0.3, min(0.3, (ang + math.pi / 2) * 0.4))
    ctr = (wr[0] + math.cos(ang) * size * 0.4, wr[1] + math.sin(ang) * size * 0.4)
    ca, sa = math.cos(up), math.sin(up)
    T = lambda v, u: (ctr[0] + u * size * ca - v * size * sa, ctr[1] + u * size * sa + v * size * ca)
    hw, hh, r = 0.25, 0.5, 0.07
    ctrl = [(-hw + r, -hh), (hw - r, -hh), (hw, -hh + r), (hw, hh - r), (hw - r, hh), (-hw + r, hh), (-hw, hh - r), (-hw, -hh + r)]
    o = a.hand([T(v, u) for v, u in ctrl], closed=True, wob=0.1, trem=0.05, step=0.5)
    a.knock(o)
    a.ink(o, lw, closed=True, a0=0.6, a1=1.0, close_frac=1.02)
    # the camera bump high on one side, two lenses and the torch
    bump = [T(-0.2, 0.43), T(-0.02, 0.43), T(-0.02, 0.18), T(-0.2, 0.18)]
    a.stroke(bump + [bump[0]], lw * 0.9, wob=0.05)
    for u in (0.37, 0.25):
        x, y = T(-0.11, u)
        a.stroke(ell(x, y, size * 0.04, size * 0.04, n=8) + [ell(x, y, size * 0.04, size * 0.04, n=8)[0]], lw * 0.85)
    tx, ty = T(0.08, 0.38)
    a.dot(tx, ty, max(1.3, size * 0.035), layer='Y')
    # the torch light: uneven rays, the one thing on the crowd brighter than the stage
    for i in range(11):
        aa = TAU * i / 11 + rng.gauss(0, 0.1)
        r0, r1 = size * 0.12, size * rng.uniform(0.32, 0.55) * (1.2 if i % 2 else 0.85)
        p0 = (tx + math.cos(aa) * r0, ty + math.sin(aa) * r0)
        p1 = (tx + math.cos(aa) * r1, ty + math.sin(aa) * r1)
        if math.sin(aa) > 0.4 and abs(math.cos(aa)) < 0.6:
            continue
        a.stroke([p0, p1], max(1.2, size * 0.028), layer='Y', a0=0.5, a1=2.2, pv=0.2, wob=0.1)
    # fingers wrapping the sides
    for sg, us in ((-1, (-0.25, -0.1)), (1, (-0.3, -0.16, -0.02))):
        for u in us:
            p = [T(sg * hw * 0.95, u - 0.05), T(sg * (hw + 0.07), u), T(sg * hw * 0.95, u + 0.06)]
            a.knock(p + [T(sg * hw * 0.8, u)])
            a.stroke(p, lw * 0.85, a0=0.5, a1=0.8, wob=0.05)


# ------------------------------------------------------------------ the beams: from behind us, over our head, onto them
for i in range(7):
    x0 = 165 + rng.uniform(-25, 25)
    y0 = -60
    x1 = 165 + (i - 3) * 43 + rng.uniform(-10, 10)
    y1 = 165 + rng.uniform(-20, 30)
    col = 'line' if i == 3 else 'Y'
    L = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    for side in (-1, 1):                                       # each beam a pair of broken strokes, like the back's
        off = side * (2.2 + i % 2)
        t = rng.uniform(0.3, 0.36)
        while t < 0.97:
            seg = rng.uniform(0.28, 0.5)
            pa = (x0 + ux * L * t - uy * off * t * 2.4, y0 + uy * L * t + ux * off * t * 2.4)
            pb = (x0 + ux * L * (t + seg) - uy * off * (t + seg) * 2.4, y0 + uy * L * (t + seg) + ux * off * (t + seg) * 2.4)
            a.stroke([pa, pb], 1.7, layer=col, a0=0.6, a1=4.0, wob=0.15, pv=0.25)
            t += seg + rng.uniform(0.03, 0.06)

# ------------------------------------------------------------------ out past them: the sound-desk tent, two delay towers
def tower(x, ytop, ybot, w):
    a.stroke([(x - w / 2, ybot), (x - w / 2 + 0.5, ytop)], 1.2)
    a.stroke([(x + w / 2, ybot), (x + w / 2 - 0.5, ytop)], 1.2)
    y = ybot
    k = 0
    while y > ytop + 20:
        y2 = y - 12
        a.stroke([(x - w / 2, y), (x + w / 2, y2)] if k % 2 else [(x + w / 2, y), (x - w / 2, y2)], 1.15)
        y = y2
        k += 1
    for j in range(3):                                        # the speaker hang at the top, slightly curved
        yy = ytop - 6 + j * 8.6
        a.shape([(x - w / 2 - 1.5 + j * 0.9, yy), (x + w / 2 + 1.5 - j * 0.9, yy), (x + w / 2 + 0.8 - j * 0.9, yy + 7.4),
                 (x - w / 2 - 0.8 + j * 0.9, yy + 7.4)], 1.35)
tower(40, 46, 122, 21)
tower(290, 42, 120, 21)
# the FOH tent: a gabled canopy, the desk, two engineers
tent = [(124, 98), (165, 76), (206, 98)]
a.stroke(tent, 1.5)
a.stroke([(128, 97), (128, 126)], 1.35)
a.stroke([(202, 97), (202, 126)], 1.35)
a.stroke([(132, 98.5), (198, 98.5)], 1.3)
for x, k in ((150, 0), (178, 1)):                    # two engineers at the desk, one with headphones round his neck
    a.shape(ell(x, 108, 3.8, 4.2, n=9), 1.3)
    a.stroke([(x - 6.5, 121), (x - 4, 115), (x, 113.5), (x + 4, 115), (x + 6.5, 121)], 1.3)
    if k:
        a.stroke([(x - 4.5, 112), (x, 115.5), (x + 4.5, 112)], 1.15)
a.stroke([(131, 120), (199, 120)], 1.5)
a.stroke([(140, 120), (143, 116.5), (160, 116.5), (162, 120)], 1.2)      # the desk's faders, a raked top

# ------------------------------------------------------------------ the far crowd: a ragged line of heads and hands
def vig(x, y):
    """the drawing thins out to the sides, more the further back"""
    return abs(x - 165) < 150 - max(0, 190 - y) * 0.35


far = []
x = 20
while x < 310:
    far.append(x)
    x += rng.uniform(7, 11)
y = 128
pts = []
for x in far:
    if not vig(x, y):
        continue
    yy = y + rng.uniform(-3, 3)
    a.knock(ell(x, yy, 4.5, 5, n=8) + [(x + 6, yy + 14), (x - 6, yy + 14)])
    a.stroke([(x - 4.2, yy + 4), (x - 4.6, yy - 1.5), (x, yy - 5.4), (x + 4.4, yy - 1.5), (x + 4.2, yy + 4)], 1.2, a0=0.6, a1=0.8)
    if rng.random() < 0.3:
        sg = rng.choice((-1, 1))
        a.stroke([(x + sg * 4, yy + 2), (x + sg * 7, yy - 9), (x + sg * 6, yy - 16)], 1.2, a0=0.6, a1=1.5)
        if rng.random() < 0.45:
            a.dot(x + sg * 6, yy - 19, 1.9, layer='Y')

# rows, back to front: (y of the face, face width, spacing)
ROWS = [(146, 12, 16.5), (172, 17, 24), (206, 24, 33)]
HAIRS = ['short', 'long', 'curly', 'wavy', 'bun', 'short', 'long', 'curly']
for ri, (ry, fw, sp) in enumerate(ROWS):
    x = 18 + rng.uniform(0, sp * 0.5)
    while x < 312:
        xx = x + rng.uniform(-sp * 0.2, sp * 0.2)
        yy = ry + rng.uniform(-3, 3) * (ri + 1)
        x += sp * rng.uniform(0.9, 1.15)
        if not vig(xx, yy):
            continue
        if ri == 1 and 58 < xx < 112:
            continue                                     # room for the girl on the shoulders
        o = {'hair': rng.choice(HAIRS), 'eyes': rng.choice(('shut', 'shut', 'open', 'happy', 'up')),
             'mouth': rng.choice(('smile', 'O', 'open', 'grin')), 'tilt': rng.gauss(0, 0.1), 'lit': ri > 0 or rng.random() < 0.5,
             'bindi': rng.random() < 0.12, 'beard': rng.random() < 0.2, 'specs': rng.random() < 0.12}
        if rng.random() < 0.05:
            o['cap'] = 'cap'
        bo = {'arms': rng.choice(('up2', 'up1', 'down', 'down', 'phone', 'peace', 'fist')), 'side': rng.choice((-1, 1)),
              'top': rng.choice((None, None, None, None, 'G', 'B', 'Y')) if ri > 0 else None}
        body(xx, yy, fw, bo)
        face(xx, yy, fw, o)
    if ri == 1:
        # the girl on her friend's shoulders, from the back print, seen from the front and so on the left
        gx, gy = 82, 134
        body(gx, gy, 25, {'arms': 'up2', 'top': 'Y', 'bangles': True, 'sw': 1.05, 'drop': 1.3})
        face(gx, gy, 25, {'hair': 'long', 'eyes': 'happy', 'mouth': 'open', 'bindi': True, 'tilt': -0.08, 'ear': 'Y'})
        body(gx, gy + 47, 19, {'arms': 'down', 'sw': 1.1})
        face(gx, gy + 47, 18, {'hair': 'short', 'eyes': 'up', 'mouth': 'grin'})
        for sg in (-1, 1):                                # her legs over his shoulders, his hands on her shins
            limb([(gx + sg * 9, gy + 46), (gx + sg * 17, gy + 52), (gx + sg * 18, gy + 72)], [9, 8, 6.5], 1.2, fill='B')
            a.shape(ell(gx + sg * 18, gy + 64, 4.4, 3.4, n=8), 1.15)

# ------------------------------------------------------------------ the front row: five people, big
HEROES = [
    (52, 266, 40, {'hair': 'long', 'eyes': 'shut', 'mouth': 'smile', 'tilt': 0.16, 'ear': 'Y', 'bindi': True, 'shade': -1, 'hr': 1.18},
     {'arms': 'up1', 'side': -1, 'top': 'G', 'bangles': True, 'drop': 0.95}),
    (124, 292, 46, {'hair': 'curly', 'eyes': 'up', 'mouth': 'open', 'beard': True, 'tilt': -0.16, 'hr': 1.28, 'shade': 1},
     {'arms': 'up2', 'top': None, 'sw': 1.2, 'drop': 0.6}),
    (205, 276, 42, {'hair': 'bun', 'eyes': 'happy', 'mouth': 'open', 'specs': True, 'tilt': 0.1, 'ear': 'B', 'shade': -1},
     {'arms': 'phone', 'side': 1, 'top': 'B', 'drop': 0.82}),
    (280, 258, 38, {'cap': 'monkey', 'eyes': 'up', 'mouth': 'O', 'tilt': -0.1, 'shade': 1},
     {'arms': 'up2', 'top': 'G', 'drop': 1.05}),
]
for hx, hy, hw, fo, bo in HEROES:
    body(hx, hy, hw, bo)
    face(hx, hy, hw, fo)
# someone behind us, closer than anyone: a forearm rising out of the bottom, filming, the torch on
limb([(176, 388), (172, 360), (166, 338)], [15, 13, 12], 1.5)
phone((166, 338), -math.pi / 2 - 0.08, 44, 1.5)

pen.save(a, __file__, order=('Y', 'G', 'B', 'line'), crops=[(124, 292), (205, 260), (84, 170), (165, 105)])
