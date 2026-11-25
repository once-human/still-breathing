#!/usr/bin/env python3
"""
01 crowd, front 01: "turned round". Centre chest, 27 cm.
The girl in the yellow kurta on her friend's shoulders, from the back print, turned round to face you: laughing,
both arms still up, her braid swung over her shoulder, bangles on, her friend under her looking up and holding her
shins. Ink line in the back's cream with its yellow and blue screens.
    R=1 python3 gen.py   draft (4.7 px/mm)      python3 gen.py   final (94 px/cm)
"""
import math, os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pen

WMM, HMM = 240, 300
h, a = pen.boot(WMM, HMM, seed=4107, layers=('line', 'Y', 'G', 'B'), print_w=270)   # printed 27 cm wide
rng = a.rng
LW, LD, LF = 1.6, 1.35, 1.25         # main contour, details, fine


def limb(ctrl, widths, fill=None, lw=LW, ends=False, r=None):
    """a limb as a tube: knocked out, filled on a screen, its two edges inked"""
    r = r or rng
    sp, L, Rr = a.tube(ctrl, widths, rng=r, wob=0.35, trem=0.3)
    poly = L + Rr[::-1]
    a.knock(poly)
    if fill:
        a.blob(poly[::3], fill, rng=r, scale=(0.97, 1.0), jit=0.02, shift=0.35, gap=0.1, n=60)
    a.ink(L, lw, rng=r, a0=1.0, a1=2.2, pv=0.15)
    a.ink(Rr, lw, rng=r, a0=1.0, a1=2.2, pv=0.15)
    if ends:
        a.ink([L[-1], sp[-1], Rr[-1]], lw, rng=r)
    return sp, L, Rr


def ell(cx, cy, rx, ry, n=14, rot=0.0, jit=0.03):
    pts = []
    for i in range(n):
        t = math.tau * i / n
        x, y = rx * math.cos(t) * (1 + rng.gauss(0, jit)), ry * math.sin(t) * (1 + rng.gauss(0, jit))
        pts.append((cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot)))
    return pts


# ------------------------------------------------------------------ the friend underneath (drawn first, she sits on him)
fx, fy, ft = 124, 237, 0.13             # his face centre and the tilt of his head as he looks up at her
def F(x, y):
    return (fx + x * math.cos(ft) - y * math.sin(ft), fy + x * math.sin(ft) + y * math.cos(ft))
# his shoulders in a green tee, dropping out of the drawing
tee = [(96, 253), (66, 259), (46, 270), (38, 288), (60, 293), (121, 291), (184, 293), (204, 286), (197, 270), (176, 258), (146, 253)]
a.knock(tee)
a.blob([(96, 254), (66, 260), (48, 271), (44, 284), (80, 278), (121, 283), (160, 277), (198, 283), (195, 271), (176, 259), (146, 254)], 'G', gap=0.2, jit=0.02)
a.stroke([(38, 287), (46, 270), (66, 259), (96, 253)], LW, a1=5)
a.stroke([(146, 253), (176, 258), (197, 270), (204, 285)], LW, a1=5)
a.stroke([(105, 255), (113, 265), (122, 267), (132, 265), (140, 256)], LD)        # crew neck
a.stroke([(108, 254), (110, 244)], LD)
a.stroke([(136, 254), (135, 245)], LD)
# his head: tilted back to look up at her, hair a mop squashed by her legs
face = [F(-21, -12), F(-20.5, 8), F(-14, 22), F(-1, 28.5), F(12, 23), F(19.5, 9), F(20.5, -12)]
a.knock(face + [F(22, -30), F(-22, -30)])
a.stroke(face, LW, a0=1.2, a1=1.6)
a.stroke([F(-21, -5), F(-26.5, -8), F(-27, 3), F(-21.5, 7)], LD)                     # ears, one more turned than the other
a.stroke([F(20.5, -4), F(24.5, -6), F(24.8, 3), F(20.5, 6)], LD)
for sg in (-1, 1):                                                                   # eyes rolled up at her, brows high
    ex, ey = F(sg * 9, -3)
    eo = ell(ex, ey, 4.3, 3.2, n=9)
    a.stroke(eo + [eo[0]], LF)
    a.dot(ex + 0.3, ey - 1.6, 1.25)
    a.stroke([F(sg * 9 - 5, -11.5 - sg * 0.8), F(sg * 9, -14), F(sg * 9 + 5, -12 + sg * 0.5)], LD)
a.stroke([F(-0.5, 0), F(-2.5, 8), F(1.5, 9.2)], LF)
mo = [F(-9, 13.5), F(0, 14.5), F(9, 13), F(5.5, 20), F(-0.5, 21.5), F(-6, 19.5)]          # laughing up at her
a.knock(mo)
a.stroke(mo + [mo[0]], LD, a0=0.6, a1=0.8)
a.stroke([F(-6.5, 15.6), F(0, 16.4), F(6.5, 15.4)], LF, a0=0.4, a1=0.4)
a.stroke([F(-11, 12), F(-12, 15)], LF, a0=0.4, a1=1.4)                                    # the crease of the smile
# his hair, squashed under her: tufts sticking out round the temples, a few strands across the forehead
for i in range(10):
    t = i / 9
    x = -25 + 50 * t
    y = -17 - 4 * math.sin(math.pi * t)
    p0 = F(x, y)
    p1 = F(x + rng.uniform(-3.5, 3.5) + (x / 25) * 3, y - rng.uniform(4, 8))
    a.stroke([p0, p1], LD, a0=0.8, a1=2.5)

# ------------------------------------------------------------------ her legs over his shoulders: blue churidar, juttis
for sg, kx in ((-1, 70), (1, 172)):
    hip = (121 + sg * 30, 200)
    knee = (121 + sg * 52, 222)
    ank = (kx + sg * 2, 270)
    limb([hip, ((hip[0] + knee[0]) / 2 + sg * 3, (hip[1] + knee[1]) / 2 - 3), (knee[0] + sg * 2, knee[1] + 6),
          ((knee[0] + ank[0]) / 2 + sg * 2, (knee[1] + ank[1]) / 2 + 3), ank], [32, 28, 24, 19, 16.5], fill='B')
    a.stroke([(knee[0] - sg * 9, knee[1] + 3), (knee[0] - sg * 4, knee[1] + 9)], LF, a0=0.5, a1=2)     # the knee's crease
    a.stroke([(hip[0] + sg * 2, hip[1] + 10), (hip[0] + sg * 12, hip[1] + 16), (knee[0] - sg * 6, knee[1] - 2)], LF, a0=0.6, a1=2.5)
    # a jutti, toe pointing a little out
    fxp = ank[0] + sg * 3
    a.shape([(fxp - 9, ank[1] - 1), (fxp + 9, ank[1] - 1), (fxp + 10 + sg * 4, ank[1] + 10), (fxp + sg * 8, ank[1] + 15),
             (fxp - 6, ank[1] + 13), (fxp - 10, ank[1] + 6)], LW, fill='Y')
    # his forearm coming up from outside, his hand round her shin: back of the hand, knuckles, the thumb over the top
    hx, hy = kx + sg * 2, 250
    limb([(kx + sg * 27, 291), (kx + sg * 21, 276), (hx + sg * 12, hy + 6)], [15, 13])
    # the back of his hand wrapped round the front of her shin, four fingers curling in toward the middle
    hand = [(hx + sg * 14, hy - 5), (hx + sg * 3, hy - 8.5), (hx - sg * 6, hy - 9.5)]
    for k in range(4):                                       # finger tips: four bumps down the inner edge
        y0 = hy - 8 + k * 4.6
        hand += [(hx - sg * (9.5 + (1.5 if k in (1, 2) else 0)), y0 + 0.6), (hx - sg * (12 + (1.5 if k in (1, 2) else 0) - k * 0.6), y0 + 2.3),
                 (hx - sg * (9.5 + (1.5 if k in (1, 2) else 0)), y0 + 4.2)]
    hand += [(hx - sg * 5, hy + 11), (hx + sg * 5, hy + 10.5), (hx + sg * 14, hy + 7)]
    a.shape(hand, LD + 0.15, wob=0.12, trem=0.08)
    for k in range(1, 4):                                    # the gaps between fingers, running back to the knuckles
        y0 = hy - 8 + k * 4.6
        a.stroke([(hx - sg * 10, y0), (hx - sg * 3, y0 + 0.3)], LF, a0=0.4, a1=1.4, wob=0.1)
    for k in range(4):                                       # knuckles
        a.stroke([(hx + sg * 0.5, hy - 6.5 + k * 4.6), (hx + sg * 1.5, hy - 4.5 + k * 4.6)], LF, a0=0.4, a1=0.6, wob=0.1)

# ------------------------------------------------------------------ her: torso in the yellow kurta
cx = 121
sh_l, sh_r = (84, 129), (158, 127)
kurta = [(sh_l[0] + 3, sh_l[1] - 3), (106, 119), (109, 131), (cx, 137), (133, 131), (136, 119), (sh_r[0] - 3, sh_r[1] - 3),
         (sh_r[0] + 4, 142), (153, 166), (158, 190), (166, 207), (146, 213), (cx, 210), (96, 214), (76, 207), (84, 190),
         (89, 166), (sh_l[0] - 4, 143)]
a.shape(kurta, LW, fill='Y', close_frac=0.985)
# the placket, a row of blue block-print marks round the neck and along the hem
a.stroke([(cx, 137), (cx + 0.5, 157)], LD)
a.stroke([(cx - 3.5, 146), (cx + 0.3, 147)], LF)
for k in range(7):
    t = (k + 0.5) / 7
    x = 108.5 + 25 * t
    y = 125 + 11.5 * math.sin(math.pi * t)
    a.dot(x, y, 1.2, layer='B')
# the border at the hem: two hand-drawn blue lines, dipping where the kurta drapes over his head
for dy in (-7.5, -3.8):
    a.stroke([(78, 205 + dy), (98, 209 + dy), (112, 205.5 + dy), (cx + 1, 207.5 + dy), (132, 205 + dy), (146, 208.5 + dy), (164, 204 + dy)],
             1.25, layer='B', a0=0.5, a1=1.5, wob=0.3)
a.stroke([(103, 211), (108, 205), (113, 196)], LD, a0=0.6, a1=3)          # the drape over his head
a.stroke([(140, 210), (135, 203), (131, 193)], LD, a0=0.6, a1=3)
# folds where she twists: a few long pulls from the hip to the chest
a.stroke([(92, 205), (98, 182), (104, 165)], LD, a0=0.6, a1=3)
a.stroke([(150, 206), (146, 186), (143, 172)], LD, a0=0.6, a1=3)
a.stroke([(cx + 4, 207), (cx + 6, 190)], LF, a0=0.6, a1=3)
# a dupatta's end over one shoulder, falling behind
a.stroke([(sh_r[0] - 6, sh_r[1] - 3), (sh_r[0] + 4, sh_r[1] + 14), (sh_r[0] + 6, 168)], LD)

# ------------------------------------------------------------------ her arms, both up (the back's pose), bangles
arms = [((sh_l[0] + 3, sh_l[1] + 6), (58, 92), (46, 40), -1),     # her right arm, our left: high, straight up
        ((sh_r[0] - 3, sh_r[1] + 6), (190, 112), (203, 80), 1)]       # her left: lower, out wide, the hand thrown open
for sh, el, wr, sg in arms:
    sp, L, Rr = limb([sh, ((sh[0] + el[0]) / 2 + sg * 2, (sh[1] + el[1]) / 2 + 2), el], [17.5, 14.5], fill='Y')     # 3/4 sleeve
    limb([el, ((el[0] + wr[0]) / 2 - sg * 1.5, (el[1] + wr[1]) / 2), wr], [12, 9.5])
    a.stroke([L[-1], (el[0] - sg * 1, el[1] + 2), Rr[-1]], LD)                                        # the cuff
    # bangles: three, in blue and yellow, a little loose round the wrist
    ang = math.atan2(wr[1] - el[1], wr[0] - el[0])
    for k, col in enumerate(('B', 'Y', 'B')):
        t = 0.62 + k * 0.08
        bx, by = el[0] + (wr[0] - el[0]) * t, el[1] + (wr[1] - el[1]) * t
        nx, ny = -math.sin(ang), math.cos(ang)
        p0 = (bx + nx * 7.8, by + ny * 7.8)
        p1 = (bx - nx * 7.8, by - ny * 7.8)
        a.stroke([p0, (bx + math.cos(ang) * 1.6, by + math.sin(ang) * 1.6), p1], 1.6, layer=col, a0=0.4, a1=0.6, pv=0.05)
    # the hand, open, fingers spread to the lights
    a.draw_hand((wr[0] + math.cos(ang) * 1, wr[1] + math.sin(ang) * 1), ang + sg * (0.12 if sg < 0 else 0.3), 34 if sg < 0 else 36,
                'open', LD + 0.1, mirror=(sg > 0))

# ------------------------------------------------------------------ her head: turned to us, laughing
hx, hy = 115, 77
tilt = -0.2
def R(x, y):
    dx, dy = x - hx, y - hy
    return (hx + dx * math.cos(tilt) - dy * math.sin(tilt), hy + dx * math.sin(tilt) + dy * math.cos(tilt))
# neck
a.stroke([R(hx - 7, hy + 22), R(hx - 7.5, hy + 34), R(hx - 10.5, hy + 44)], LD)
a.stroke([R(hx + 8, hy + 22), R(hx + 8.5, hy + 33), R(hx + 11.5, hy + 42)], LD)
a.stroke([(113, 142), (cx, 144.5), (129, 141)], LF, a0=0.5, a1=1.2)                       # collarbones

# hair mass behind the head (black = the shirt; only its edge is drawn), centre parting, pulled back
hair = [R(hx - 26, hy + 14), R(hx - 29, hy - 6), R(hx - 25, hy - 27), R(hx - 10, hy - 37.5), R(hx + 6, hy - 38),
        R(hx + 22, hy - 31), R(hx + 29, hy - 11), R(hx + 28, hy + 12)]
a.knock(hair + [R(hx + 20, hy + 24), R(hx - 20, hy + 24)])
a.stroke(hair, LW, a0=1.4, a1=2.4)
# face
face = [R(hx - 19.5, hy - 12), R(hx - 19.5, hy + 4), R(hx - 15, hy + 18), R(hx - 6, hy + 27), R(hx + 2, hy + 28.5),
        R(hx + 10, hy + 25), R(hx + 17, hy + 15), R(hx + 20.5, hy + 2), R(hx + 20, hy - 12)]
a.stroke(face, LW, a0=1.0, a1=1.6)
# hairline: a parting and two sweeps back over the ears
a.stroke([R(hx + 0.5, hy - 27), R(hx - 1, hy - 20)], LD, a0=0.5, a1=2)
for sg in (-1, 1):                                           # two loose strands at the temples, out of the braid
    bx_, by_ = R(hx + sg * 27, hy - 14)
    a.stroke([(bx_, by_), (bx_ + sg * 3.5, by_ + 8), (bx_ + sg * 2.5, by_ + 17)], LF, a0=0.4, a1=2.5)
a.stroke([R(hx - 1, hy - 20), R(hx - 10, hy - 19.5), R(hx - 18, hy - 15), R(hx - 21, hy - 7)], LD)
a.stroke([R(hx - 1, hy - 20), R(hx + 9, hy - 19.8), R(hx + 17, hy - 15.5), R(hx + 21, hy - 7)], LD)
for k in range(3):                                         # strands
    a.stroke([R(hx - 3 - 4 * k, hy - 27 + 2 * k), R(hx - 10 - 4 * k, hy - 25 + 3 * k), R(hx - 17 - 3 * k, hy - 18 + 4 * k)], LF, a0=0.6, a1=2.6)
    a.stroke([R(hx + 4 + 4 * k, hy - 28 + 2 * k), R(hx + 11 + 4 * k, hy - 25.5 + 3 * k), R(hx + 17 + 3 * k, hy - 19 + 4 * k)], LF, a0=0.6, a1=2.6)
# ears and jhumkas (yellow, swinging)
for sg in (-1, 1):
    ex = hx + sg * 21
    a.stroke([R(ex, hy - 4), R(ex + sg * 3.6, hy - 5), R(ex + sg * 4, hy + 3), R(ex, hy + 6)], LD)
    jx, jy = R(ex + sg * 1.5, hy + 8)
    jx += sg * 2.5
    a.stroke([(jx, jy), (jx + sg * 0.5, jy + 4)], LF)
    a.shape([(jx - 4.2, jy + 9), (jx, jy + 3.5), (jx + 4.2, jy + 9), (jx + 3.2, jy + 10.5), (jx - 3.2, jy + 10.5)], LF, fill='Y')
# laughing: eyes shut in two arcs, brows up, cheeks pushed up, open mouth
for sg in (-1, 1):
    ex = hx + sg * 8.4
    a.stroke([R(ex - 4.8, hy - 1.2), R(ex, hy - 4.2), R(ex + 4.8, hy - 1.2)], LD, a0=0.6, a1=1.0)
    a.stroke([R(ex + sg * 4.6, hy - 1.6), R(ex + sg * 7, hy - 2.8)], LF, a0=0.5, a1=1.6)                # a flick of lashes
    a.stroke([R(ex - 5.5, hy - 9.5 - sg * 0.5), R(ex, hy - 11.8), R(ex + 5.5, hy - 10 + sg * 0.6)], LD)
    a.stroke([R(ex - 3, hy + 6.5), R(ex + sg * 2.5, hy + 7.6)], LF, a0=0.4, a1=1.2)                   # cheek
a.dot(*R(hx, hy - 15.5), 1.6, layer='B')                                                                # bindi
a.stroke([R(hx + 0.8, hy - 2), R(hx - 1.5, hy + 7.5), R(hx + 1.8, hy + 9.2), R(hx + 4, hy + 8.4)], LD, a0=0.6, a1=1.0)
mouth = [R(hx - 10, hy + 12.6), R(hx, hy + 13.6), R(hx + 10, hy + 12.2), R(hx + 7.5, hy + 20.5), R(hx, hy + 23.5), R(hx - 7.5, hy + 21)]
a.knock(mouth)
a.stroke(mouth + [mouth[0]], LW, a0=0.6, a1=0.8)
teeth = [R(hx - 8, hy + 13.8), R(hx + 8, hy + 13.4), R(hx + 7, hy + 16.4), R(hx - 7, hy + 16.8)]   # top teeth, the light on them
a.fill(a.hand(teeth, closed=True, wob=0.1, trem=0.05), 'line')
tongue = [R(hx - 4.5, hy + 22.6), R(hx - 3, hy + 19.4), R(hx + 3, hy + 19.2), R(hx + 4.5, hy + 22.4)]
a.blob(tongue, 'Y', gap=0, jit=0.02, shift=0.1)
for sg in (-1, 1):                                                                                   # laugh lines
    a.stroke([R(hx + sg * 11.5, hy + 10), R(hx + sg * 13, hy + 15)], LF, a0=0.4, a1=1.6)

# ------------------------------------------------------------------ the braid, swung forward over her left shoulder (our right)
bx0, by0 = R(hx + 22, hy + 14)
braid = [(bx0, by0), (bx0 + 8, by0 + 22), (bx0 + 11, by0 + 46), (bx0 + 8, by0 + 70), (bx0 + 12, by0 + 90)]
spine = a.hand(braid, wob=0.3, trem=0.2, step=0.5)
s = h.cumlen(spine)
Lb = s[-1]
n = 11
for k in range(n):
    t0, t1 = k / n + rng.uniform(-0.01, 0.01), (k + 1.15) / n + rng.uniform(-0.012, 0.012)
    i0 = min(len(spine) - 1, int(t0 * (len(spine) - 1)))
    i1 = min(len(spine) - 1, int(t1 * (len(spine) - 1)))
    p0, p1 = spine[i0], spine[i1]
    wdt = 6.2 * (1 - 0.35 * k / n) * rng.uniform(0.85, 1.12)
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    d = math.hypot(dx, dy) or 1
    nx, ny = -dy / d, dx / d
    sg = 1 if k % 2 else -1
    pts = [(p0[0] + nx * sg * wdt * 0.2, p0[1] + ny * sg * wdt * 0.2), ((p0[0] + p1[0]) / 2 - nx * sg * wdt, (p0[1] + p1[1]) / 2 - ny * sg * wdt),
           (p1[0] - nx * sg * wdt * 0.1, p1[1] - ny * sg * wdt * 0.1), ((p0[0] + p1[0]) / 2 + nx * sg * wdt * 0.6, (p0[1] + p1[1]) / 2 + ny * sg * wdt * 0.6)]
    a.knock(pts)
    a.stroke(pts + [pts[0]], LD, a0=0.6, a1=1.0)
# the tassel (paranda) in blue at its end
ex_, ey_ = spine[-1]
a.shape([(ex_ - 3.5, ey_ - 1), (ex_ + 3.5, ey_ - 1), (ex_ + 5.5, ey_ + 15), (ex_ + 1, ey_ + 17.5), (ex_ - 4.5, ey_ + 14.5)], LD, fill='B')
a.stroke([(ex_ - 4, ey_ + 2.4), (ex_ + 4, ey_ + 2.2)], LD)

pen.save(a, __file__, order=('Y', 'B', 'G', 'line'), crops=[(117, 76), (121, 236), (40, 40)])
