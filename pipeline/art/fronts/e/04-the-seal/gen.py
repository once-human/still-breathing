# python3 gen.py : the i am a party front, "the seal", redrawn from fronts/all/15 to read across a room.
# The ring is 15's: two hand-drawn lines, never filled in, the words standing between them like a rubber stamp's
# lettering, a dot at three and at nine. again.. फिर से.. over the top, पुन्हा.. ಮತ್ತೆ.. upright along the bottom, each
# word's two dots orange. The words are much bigger and heavier, set close to the ring, bent round it, each a little
# off its neighbour's line. Inside, one warm body seen in heat, big: violet, orange, pale yellow, a cream core, each
# colour painted on with round brush strokes going round, so the fill is the strokes and their tails.
# Seeded. Writes art.png (print size, 94 px/cm, binary alpha), preview.png (on the shirt black), then check.py verify.
import math, os, sys, random
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'lib'))
import efront as E

CW, CH = 232, 216                       # canvas, mm (the strip rows need the width; the seal is 200 across)
h, art = E.boot(CW, CH, seed=404, layers=('violet', 'orange', 'yellow', 'cream', 'bv', 'bo', 'by', 'core', 'sL', 'sD'))
PX = E.PXMM
rng = random.Random(404)
lay = random.Random(15)
CX, CY = CW / 2, CH / 2

R_OUT, RW = 99.0, 2.5                   # the outer ring line (centre radius, width), mm
XH = 14.5                               # again..: x-height, mm
DEV_EM = XH * 1.16 / 0.622              # Devanagari: headline as tall as the Latin x-height and a bit
KAN_EM = XH * 1.22 / 0.80
DOT_R = 2.15                            # each word's two orange dots
GAP = 1.7                               # clear shirt between a word and a ring line

# ---------------------------------------------------------------- the words, flat, on the strip layers
ROWS = {'top': 40.0, 'bot': 150.0}      # flat baselines on the strip layers


def flat_dots(x, base, layer='sD'):
    """a word's two dots at the baseline after x; returns the x after them"""
    for i in range(2):
        cx = x + DOT_R + i * DOT_R * 2.75
        art.dot(cx, base - DOT_R * 1.02, DOT_R, layer=layer, rng=rng)
    return x + DOT_R * 2 + DOT_R * 2.75


def script_word(chunks, font, em, x, base):
    """a word in Devanagari or Kannada, set chunk by chunk, each chunk a touch off the line and off the upright,
    as a hand cutting the stamp would leave them"""
    for i, ch in enumerate(chunks):
        if ch == ' ':
            x += em * 0.26
            continue
        m, b = E.font_mask(ch, font, em, baseline=True, grow=1)
        m = m.rotate(lay.uniform(-2.2, 2.2), resample=Image.BICUBIC, expand=True, center=(m.width / 2, b))
        m = m.point(lambda p: 255 if p > 127 else 0)
        bb = m.getbbox()
        dy = lay.uniform(-0.35, 0.35)
        tmp = Image.new('L', art.L['sL'].size, 0)
        tmp.paste(m.crop(bb), (int(round(x * PX)), int(round((base + dy) * PX)) - (b - bb[1])))
        art.add('sL', tmp)
        x += (bb[2] - bb[0]) / PX + em * 0.05
    return x + em * 0.07


def shantell(px):
    from PIL import ImageFont
    f = ImageFont.truetype(os.path.join(E.FONTS, 'ShantellSans-Var.ttf'), int(px), layout_engine=ImageFont.Layout.RAQM)
    axes = {'Weight': 800, 'Informality': 100, 'Bounce': 0, 'Spacing': 0}
    f.set_variation_by_axes([axes[(a['name'].decode() if isinstance(a['name'], bytes) else a['name'])] for a in f.get_variation_axes()])
    return f


def glyph(ch, font):
    """one letter as a mask and its baseline row"""
    from PIL import ImageDraw
    bb = font.getbbox(ch, anchor='ls')
    m = Image.new('L', (bb[2] - bb[0] + 40, bb[3] - bb[1] + 40), 0)
    ImageDraw.Draw(m).text((20 - bb[0], 20 - bb[1]), ch, font=font, fill=255, anchor='ls')
    return m, 20 - bb[1], font.getlength(ch)


SH = shantell(10 * PX)
SH_XH = -SH.getbbox('x', anchor='ls')[1] / PX / 10      # Shantell's x-height per mm of em
LAT_EM = XH * 1.04 / SH_XH


def lat_word(text, x, base):
    """again in the back title's hand at its heaviest, letter by letter, each a touch off the line and the upright"""
    f = shantell(LAT_EM * PX)
    for ch in text:
        m, b, adv = glyph(ch, f)
        m = m.rotate(lay.uniform(-2.6, 2.6), resample=Image.BICUBIC, center=(m.width / 2, b))
        m = m.point(lambda p: 255 if p > 127 else 0)
        tmp = Image.new('L', art.L['sL'].size, 0)
        tmp.paste(m, (int(round(x * PX)) - 20, int(round((base + lay.uniform(-0.4, 0.4)) * PX)) - b))
        art.add('sL', tmp)
        x += adv / PX + LAT_EM * 0.035
    return x


WGAP = 13.0                             # between the two words of a half
spans = {}
# the top: again..  फिर से..
x = 4.0
x = lat_word('again', x, ROWS['top'])
x = flat_dots(x + 1.4, ROWS['top'])
x += WGAP
x = script_word(['फि', 'र', ' ', 'से'], 'NotoSansDevanagari-Black.ttf', DEV_EM, x, ROWS['top'])
x = flat_dots(x, ROWS['top'])
spans['top'] = (4.0, x)


def bottom(scale):
    """the bottom, upright: पुन्हा..  ಮತ್ತೆ.. (they ride the outer, longer part of the band, so they can be bigger)"""
    x = 4.0
    x = script_word(['पु', 'न्हा'], 'NotoSansDevanagari-Black.ttf', DEV_EM * scale, x, ROWS['bot'])
    x = flat_dots(x, ROWS['bot'])
    x += WGAP
    x = script_word(['ಮ', 'ತ್ತೆ'], 'NotoSansKannada-Black.ttf', KAN_EM * scale, x, ROWS['bot'])
    x = flat_dots(x, ROWS['bot'])
    spans['bot'] = (4.0, x)


bottom(1.0)

both = (np.asarray(art.L['sL']) > 127) | (np.asarray(art.L['sD']) > 127)


def extents(row):
    """ink above and below the row's flat baseline, mm"""
    y0, y1 = int((ROWS[row] - 40) * PX), int((ROWS[row] + 40) * PX)
    rows = np.where(both[y0:y1].any(1))[0]
    return ROWS[row] - (y0 + rows[0]) / PX, (y0 + rows[-1]) / PX - ROWS[row]


up_t, dn_t = extents('top')
up_b, dn_b = extents('bot')
BS = min(1.22, (up_t + dn_t) / (up_b + dn_b))       # the bottom words as tall as the band the top words need
for k in ('sL', 'sD'):
    art.L[k].paste(0, (0, int((ROWS['bot'] - 50) * PX), art.L[k].width, int((ROWS['bot'] + 50) * PX)))
bottom(BS)
both = (np.asarray(art.L['sL']) > 127) | (np.asarray(art.L['sD']) > 127)
up_b, dn_b = extents('bot')
sL = np.asarray(art.L['sL']) > 127
sD = np.asarray(art.L['sD']) > 127
EDGE = R_OUT - RW / 2 - GAP              # the words reach this far out
RB_T = EDGE - up_t                       # top: letters' tops toward the rim
RB_B = EDGE - dn_b                       # bottom: upright, so their feet are toward the rim
R_IN = min(RB_T - dn_t, RB_B - up_b) - GAP - RW / 2
print(f'bottom scale {BS:.2f}'); print(f'top {spans["top"][1] - 4:.0f} mm, bottom {spans["bot"][1] - 4:.0f} mm; baselines r {RB_T:.1f} / {RB_B:.1f}; inner ring r {R_IN:.1f}')

# ---------------------------------------------------------------- bend the words round the ring
N_W, N_H = art.L['cream'].size
yy, xx = np.mgrid[0:N_H, 0:N_W].astype(np.float32)
xx = xx / PX - CX
yy = yy / PX - CY
r = np.hypot(xx, yy)
th = np.arctan2(xx, -yy)                 # clockwise from twelve, -pi..pi
del xx, yy


def smooth_field(amp, cells, seed):
    """a slow wander (mm) over the canvas: a stamp's letters are never quite on their line"""
    g = np.random.default_rng(seed).uniform(-1, 1, (cells, cells)).astype(np.float32)
    im = Image.fromarray(((g + 1) * 127.5).astype(np.uint8)).resize((N_W, N_H), Image.BICUBIC)
    return (np.asarray(im, np.float32) / 127.5 - 1) * amp


du, dv = smooth_field(0.45, 14, 1), smooth_field(0.35, 14, 2)
band = (r > R_IN + RW / 2 + 0.3) & (r < R_OUT - RW / 2 - 0.3)
fx = np.zeros_like(r)
fy = np.zeros_like(r)
top = band & (np.abs(th) < math.radians(95))
bot = band & (np.abs(th) > math.radians(95))
mid_t = sum(spans['top']) / 2
mid_b = sum(spans['bot']) / 2
fx[top] = mid_t + th[top] * RB_T
fy[top] = ROWS['top'] - (r[top] - RB_T)
thb = np.where(th > 0, th - math.pi, th + math.pi)
fx[bot] = mid_b - thb[bot] * RB_B
fy[bot] = ROWS['bot'] + (r[bot] - RB_B)
del thb
fx += du
fy += dv
del du, dv
ix = np.clip((fx * PX).astype(np.int32), 0, N_W - 1)
iy = np.clip((fy * PX).astype(np.int32), 0, N_H - 1)
del fx, fy
txt = band & sL[iy, ix]
dts = band & sD[iy, ix]
del ix, iy, sL, sD, both


def rounded(mask, rad_mm=0.45):
    """ink on rubber: the corners soften a little"""
    im = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rad_mm * PX))
    return im.point(lambda p: 255 if p > 127 else 0)


art.add('cream', rounded(txt))
art.add('orange', rounded(dts, 0.3))
del txt, dts
art.L['sL'] = Image.new('L', (1, 1))
art.L['sD'] = Image.new('L', (1, 1))

# ---------------------------------------------------------------- the ring: two lines, drawn, not filled


def ring(rad, w):
    """a circle drawn in two goes: two arcs, each a little over half way round, their ends overlapping and tapering
    into each other; the radius wanders slowly, the way a hand's does"""
    wan = [(f, rng.uniform(0.25, 0.55) / f, rng.uniform(0, math.tau)) for f in (2, 3, 5)]
    a0 = rng.uniform(0, math.tau)
    for k in range(2):
        s0 = a0 + math.pi * k + rng.uniform(-0.08, 0.08)
        span = math.pi * rng.uniform(1.12, 1.2)
        n = 26
        pts = []
        for i in range(n + 1):
            t = s0 + span * i / n
            rr = rad + sum(a * math.sin(f * t + p) for f, a, p in wan)
            pts.append((CX + math.sin(t) * rr, CY - math.cos(t) * rr))
        art.line(pts, w * rng.uniform(0.96, 1.04), layer='cream', wob=0.12, trem=0.3, pv=0.14, a0=0.5, a1=4.0)


ring(R_OUT, RW)
ring(R_IN, RW * 0.94)
RM = (R_OUT + R_IN) / 2
half_t = (spans['top'][1] - spans['top'][0]) / 2 / RB_T     # each half's angular reach, radians
half_b = (spans['bot'][1] - spans['bot'][0]) / 2 / RB_B
A_SEP = (half_t + math.pi - half_b) / 2
print(f'top reaches {math.degrees(half_t):.0f} deg, bottom {math.degrees(half_b):.0f} deg; dots at {math.degrees(A_SEP):.0f}')
for a in (A_SEP, -A_SEP):                 # a dot in each gap between the halves
    art.dot(CX + math.sin(a) * RM, CY - math.cos(a) * RM, 2.8, layer='cream', rng=rng)

# ---------------------------------------------------------------- the warm body, painted with a round brush
RV = R_IN * 0.735                         # the body's outer edge (violet), mm
shape_ph = [(f, 0.055 / f * 1.6, rng.uniform(0, math.tau)) for f in (2, 3, 4, 5)]


def edge(t):
    """the body's outline factor at angle t: a warm, slightly egg-shaped lump, fuller at the top"""
    return 1 + sum(a * math.sin(f * t + p) for f, a, p in shape_ph) + 0.05 * math.cos(t)


BODY = [  # colour, outer radius (fraction of RV), centre offset (mm), brush width (mm)
    ('bv', 1.00, (0.0, 1.5), 5.6),
    ('bo', 0.72, (-1.2, -3.2), 5.0),
    ('by', 0.46, (-2.2, -6.6), 4.4),
    ('core', 0.22, (-2.8, -9.2), 3.9),
]
for col, frac, (ox, oy), bw in BODY:
    Ro = RV * frac
    rad = Ro - bw / 2
    first = True
    while rad > bw * 0.35:
        n = max(1, int(math.tau * rad / 62)) + 1
        a0 = rng.uniform(0, math.tau)
        for k in range(n):
            s = a0 + math.tau * k / n + rng.uniform(-0.2, 0.2)
            span = math.tau / n * rng.uniform(1.12, 1.3)
            m = max(4, int(span * rad / 3.5))
            pts = []
            for i in range(m + 1):
                t = s + span * i / m
                rr = rad * edge(t) + rng.gauss(0, 0.12)
                if first and i > m * 0.8:          # the outer strokes lift off a little wide, as a brush does
                    rr += ((i - m * 0.8) / (m * 0.2)) ** 1.5 * bw * 0.85
                pts.append((CX + ox + math.sin(t) * rr, CY + oy - math.cos(t) * rr * 1.04))
            art.line(pts, bw * rng.uniform(0.92, 1.06), layer=col, wob=0.25, trem=0.4, pv=0.2, a0=0.6, a1=3.0)
        rad -= bw * rng.uniform(0.86, 0.94)
        first = False
    # the middle: one short swirl dab where the rings run out
    c = [(CX + ox + math.sin(t) * rad * 0.6, CY + oy - math.cos(t) * rad * 0.6) for t in np.linspace(0, 4.4, 6)]
    art.line(c, bw * 1.05, layer=col, wob=0.2, trem=0.2, pv=0.1, a0=0.6, a1=1.6)



def fill_pinholes(m, max_mm=10.0):
    """a loaded brush leaves no pinholes: any hole in a colour smaller than max_mm across is filled. The long gaps
    where one stroke ran past the next stay open: those are the brush."""
    bb = m.getbbox()
    sub = m.crop(bb).resize(((bb[2] - bb[0]) // 2, (bb[3] - bb[1]) // 2), Image.NEAREST)
    a = np.asarray(sub) == 0
    H_, W_ = a.shape
    seen = np.zeros_like(a)
    fill = np.zeros_like(a)
    for y in range(H_):
        for x in np.nonzero(a[y] & ~seen[y])[0]:
            if seen[y, x]:
                continue
            stack, pts, edge_ = [(y, x)], [], False
            seen[y, x] = True
            while stack:
                cy, cx = stack.pop()
                pts.append((cy, cx))
                for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                    if not (0 <= ny < H_ and 0 <= nx < W_):
                        edge_ = True
                    elif a[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            ys, xs = zip(*pts)
            if not edge_ and max(max(ys) - min(ys), max(xs) - min(xs)) * 2 / PX < max_mm:
                fill[list(ys), list(xs)] = True
    f = Image.fromarray((fill * 255).astype(np.uint8)).resize(sub.size and (bb[2] - bb[0], bb[3] - bb[1]), Image.NEAREST)
    full = Image.new('L', m.size, 0)
    full.paste(h.dilate(f, 5), bb[:2])
    m.paste(255, (0, 0), full)


for src, dst in (('bv', 'violet'), ('bo', 'orange'), ('by', 'yellow'), ('core', 'cream')):
    m = h.close_gaps(art.L[src])
    fill_pinholes(m)
    art.add(dst, m)
    art.L[src] = Image.new('L', (1, 1))

del r, th, band, top, bot
E.save(art, __file__, order=('violet', 'orange', 'yellow', 'cream'), shifts={}, trim=False,
       crops=[(CX - 40, CY - 80), (CX, CY + 85), (CX + 10, CY - 5)])
