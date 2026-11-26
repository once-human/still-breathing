# python3 gen.py : the i am a party front, "the seal", the version he picked (the first draw of 04, before its fixes).
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
h, art = E.boot(CW, CH, seed=404, layers=('violet', 'orange', 'yellow', 'cream', 'sL', 'sD'))
import letters
PX = E.PXMM
rng = random.Random(404)
lay = random.Random(15)
CX, CY = CW / 2, CH / 2

R_OUT, RW = 99.0, 2.5                   # the outer ring line (centre radius, width), mm
XH, LW = 14.0, 3.5                      # again..: x-height and stroke
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


def lat_word(text, x, base):
    marks = letters.write(art, text, x, base, XH, LW, 'sL', rng=rng, lay=lay, skip='.', track=0.2,
                          rot_j=2.2, base_j=0.03, size_j=0.035, wob=XH * 0.012, trem=XH * 0.01, pv=0.12, a0=0.7, a1=0.9)
    end = [m for m in marks if m['ch'] != '.'][-1]['x1']
    return end


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
# the bottom, upright: पुन्हा..  ಮತ್ತೆ..
x = 4.0
x = script_word(['पु', 'न्हा'], 'NotoSansDevanagari-Black.ttf', DEV_EM, x, ROWS['bot'])
x = flat_dots(x, ROWS['bot'])
x += WGAP
x = script_word(['ಮ', 'ತ್ತೆ'], 'NotoSansKannada-Black.ttf', KAN_EM, x, ROWS['bot'])
x = flat_dots(x, ROWS['bot'])
spans['bot'] = (4.0, x)

sL = np.asarray(art.L['sL']) > 127
sD = np.asarray(art.L['sD']) > 127
both = sL | sD


def extents(row):
    """ink above and below the row's flat baseline, mm"""
    y0, y1 = int((ROWS[row] - 40) * PX), int((ROWS[row] + 40) * PX)
    rows = np.where(both[y0:y1].any(1))[0]
    return ROWS[row] - (y0 + rows[0]) / PX, (y0 + rows[-1]) / PX - ROWS[row]


up_t, dn_t = extents('top')
up_b, dn_b = extents('bot')
EDGE = R_OUT - RW / 2 - GAP              # the words reach this far out
RB_T = EDGE - up_t                       # top: letters' tops toward the rim
RB_B = EDGE - dn_b                       # bottom: upright, so their feet are toward the rim
R_IN = min(RB_T - dn_t, RB_B - up_b) - GAP - RW / 2
print(f'top {spans["top"][1] - 4:.0f} mm, bottom {spans["bot"][1] - 4:.0f} mm; baselines r {RB_T:.1f} / {RB_B:.1f}; inner ring r {R_IN:.1f}')

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


def circle(rad, n=30, jit=0.45):
    ph = rng.uniform(0, math.tau)
    return [(CX + math.sin(ph + math.tau * i / n) * (rad + rng.uniform(-jit, jit)),
             CY - math.cos(ph + math.tau * i / n) * (rad + rng.uniform(-jit, jit))) for i in range(n + 1)]


art.line(circle(R_OUT), RW, layer='cream', closed=True, wob=0.3, trem=0.5, pv=0.16, a0=0.6, a1=1.6, close_frac=1.035)
art.line(circle(R_IN, 24), RW * 0.96, layer='cream', closed=True, wob=0.3, trem=0.5, pv=0.16, a0=0.6, a1=1.6, close_frac=1.03)
RM = (R_OUT + R_IN) / 2
for a in (math.pi / 2, -math.pi / 2):     # a dot at three and at nine, between the halves
    art.dot(CX + math.sin(a) * RM, CY - math.cos(a) * (RM), 2.2, layer='cream', rng=rng)

# ---------------------------------------------------------------- the warm body, painted with a round brush
RV = R_IN * 0.735                         # the body's outer edge (violet), mm
shape_ph = [(f, 0.055 / f * 1.6, rng.uniform(0, math.tau)) for f in (2, 3, 4, 5)]


def edge(t):
    """the body's outline factor at angle t: a warm, slightly egg-shaped lump, fuller at the top"""
    return 1 + sum(a * math.sin(f * t + p) for f, a, p in shape_ph) + 0.05 * math.cos(t)


BODY = [  # colour, outer radius (fraction of RV), centre offset (mm), brush width (mm)
    ('violet', 1.00, (0.0, 1.5), 5.6),
    ('orange', 0.72, (-1.2, -3.2), 5.0),
    ('yellow', 0.46, (-2.2, -6.6), 4.4),
    ('cream', 0.22, (-2.8, -9.2), 3.9),
]
for col, frac, (ox, oy), bw in BODY:
    Ro = RV * frac
    step = bw * 0.72
    rad = Ro - bw / 2
    ring = 0
    while rad > bw * 0.35:
        n = max(1, int(math.tau * rad / 70)) + 1
        a0 = rng.uniform(0, math.tau)
        for k in range(n):
            s = a0 + math.tau * k / n + rng.uniform(-0.15, 0.15)
            span = math.tau / n * rng.uniform(1.22, 1.42)
            m = max(4, int(span * rad / 3.5))
            pts = []
            for i in range(m + 1):
                t = s + span * i / m
                rr = rad * edge(t) + rng.gauss(0, 0.15)
                pts.append((CX + ox + math.sin(t) * rr, CY + oy - math.cos(t) * rr * 1.04))
            art.line(pts, bw * rng.uniform(0.93, 1.07), layer=col, wob=0.3, trem=0.35, pv=0.17, a0=0.7, a1=2.4)
        rad -= step * rng.uniform(0.95, 1.05)
        ring += 1
    # the middle: one short swirl dab where the rings run out
    c = [(CX + ox + math.sin(t) * rad * 0.6, CY + oy - math.cos(t) * rad * 0.6) for t in np.linspace(0, 4.4, 6)]
    art.line(c, bw * 1.05, layer=col, wob=0.2, trem=0.2, pv=0.1, a0=0.6, a1=1.6)

for col in ('violet', 'orange', 'yellow'):
    art.add(col, h.close_gaps(art.L[col]))

del r, th, band, top, bot
E.save(art, __file__, order=('violet', 'orange', 'yellow', 'cream'), shifts={}, trim=False)
