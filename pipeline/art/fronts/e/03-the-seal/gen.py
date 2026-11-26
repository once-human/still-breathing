# python3 gen.py : the i am a party front, "the seal" (fronts/all/15) made to read from across a room.
# A solid cream band with again.. / फिर से.. / पुन्हा.. / ಮತ್ತೆ.. cut out of it (the shirt shows through the letters),
# each word's two dots in orange; a thin cream ring outside it; inside, one warm body seen in heat: violet, orange,
# pale yellow, a cream core (the back's own heat colours). Centre chest, 13.6 cm. Seeded; writes art.png (print size,
# 94 px/cm, binary alpha), preview.png (on the shirt black) and placement.json.
import json, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); FONTS = os.path.join(HERE, "..", "..", "..", "..", "fonts")
PX_CM, SS = 94, 1                     # print px per cm, supersampling
CREAM, ORANGE, VIOLET, YELLOW = (241, 231, 208), (242, 124, 36), (107, 36, 153), (255, 196, 84)
SHIRT = (21, 21, 21)
rng = np.random.default_rng(15)

D_CM = 13.6
R_RING, RING_W = 6.8, 0.16            # the thin outer ring (outer radius, width), cm
R_OUT, BAND = 6.42, 2.45              # the solid band
R_IN_RING, IN_W = 3.68, 0.16          # a thin ring just inside the band
k = PX_CM * SS
N = int(round(D_CM * k)) + 8
C = N / 2


def shantell(px, wght=700):
    f = ImageFont.truetype(os.path.join(FONTS, "ShantellSans-Var.ttf"), int(px))
    axes = {"Weight": wght, "Informality": 100, "Bounce": 0, "Spacing": 0}
    f.set_variation_by_axes([axes[(a["name"].decode() if isinstance(a["name"], bytes) else a["name"])] for a in f.get_variation_axes()])
    return f


def noto(script, px):
    return ImageFont.truetype(os.path.join(FONTS, f"NotoSans{script}-Black.ttf"), int(px))


def word(text, font, px):
    """the word's letters and its two dots as two masks on one canvas, cropped to the ink, baseline-aligned"""
    w = int(font.getlength(text) + px * 2.2); h = int(px * 2.2)
    let = Image.new("L", (w, h)); ImageDraw.Draw(let).text((px * 0.2, h * 0.66), text, font=font, fill=255, anchor="ls")
    dots = Image.new("L", (w, h)); d = ImageDraw.Draw(dots)
    x = px * 0.2 + font.getlength(text) + px * 0.10; rr = px * 0.085
    for i in range(2):
        cx = x + rr + i * rr * 2.9; d.ellipse([cx - rr, h * 0.66 - 2 * rr, cx + rr, h * 0.66], fill=255)
    both = Image.fromarray(np.maximum(np.asarray(let), np.asarray(dots)))
    box = both.getbbox()
    return np.asarray(let.crop(box)) > 127, np.asarray(dots.crop(box)) > 127


# the band unrolled: a strip as long as the band's middle circle, as tall as the band; column u is the angle clockwise
# from twelve o'clock, row 0 is the band's outer edge
T = int(BAND * k); R_MID = (R_OUT - BAND / 2) * k; L = int(2 * math.pi * R_MID)
let_s = np.zeros((T, L), bool); dot_s = np.zeros((T, L), bool)
SPAN = []                             # each word's angle span, for the holes between them
# again.. level across the top, where it reads first and from furthest; पुन्हा.. upright along the bottom; फिर से..
# down the right side and ಮತ್ತೆ.. up the left, both with their tops to the rim
# again.. gets the most of the band (it leads, and is the one read from across the room)
words = [("again", "latin", 0, False, 0.31), ("फिर से", "Devanagari", 90, False, 0.205),
         ("पुन्हा", "Devanagari", 180, True, 0.205), ("ಮತ್ತೆ", "Kannada", 270, False, 0.205)]
for text, script, at, flip, share in words:
    ARC = share * L
    px = 400
    mk = (lambda p: shantell(p)) if script == "latin" else (lambda p, s=script: noto(s, p))
    l0, _ = word(text, mk(px), px)
    s = min(ARC / l0.shape[1], (0.80 if script == "latin" else 0.72) * T / l0.shape[0]); px = int(px * s)
    l, dt = word(text, mk(px), px)
    if flip: l, dt = l[::-1, ::-1], dt[::-1, ::-1]   # the bottom words read left to right, tops toward the middle
    h, w = l.shape
    u0 = int((at % 360) / 360 * L - w / 2); v0 = (T - h) // 2 + (int(0.04 * T) if flip else -int(0.02 * T))
    cols = (np.arange(w) + u0) % L
    let_s[v0:v0 + h][:, cols] |= l; dot_s[v0:v0 + h][:, cols] |= dt
    SPAN.append((at, w / L * 360))
    print(text, "x-height about", round(px * 0.5 / k, 2), "cm")

yy, xx = np.mgrid[0:N, 0:N].astype(np.float32) - C + 0.5
r = np.hypot(xx, yy); th = np.mod(np.arctan2(xx, -yy), 2 * math.pi)
art = np.zeros((N, N, 4), np.uint8)


def paint(mask, col):
    art[mask] = col + (255,)


def wob(base, amp, n=5):
    """a hand-drawn edge: the radius wanders a little, slowly, round the circle"""
    out = np.full_like(th, base)
    for f in range(2, 2 + n):
        out += amp / f * np.sin(f * th + rng.uniform(0, 2 * math.pi))
    return out


paint((r <= wob(R_RING * k, 0.03 * k)) & (r >= wob((R_RING - RING_W) * k, 0.03 * k)), CREAM)
band = (r <= wob(R_OUT * k, 0.025 * k)) & (r >= wob((R_OUT - BAND) * k, 0.025 * k))
v = np.clip(((R_OUT * k) - r).astype(int), 0, T - 1); u = np.clip((th * R_MID).astype(int), 0, L - 1)
cut = let_s[v, u] | dot_s[v, u]
paint(band & ~cut, CREAM)
paint(band & dot_s[v, u], ORANGE)
paint((r <= wob(R_IN_RING * k, 0.03 * k)) & (r >= wob((R_IN_RING - IN_W) * k, 0.03 * k)), CREAM)
# between the words, on the diagonals: a round hole punched through the band
holes = []
for (a0, s0), (a1, s1) in zip(SPAN, SPAN[1:] + SPAN[:1]):
    e0, b1 = a0 + s0 / 2, a1 - s1 / 2 + (360 if a1 < a0 else 0); holes.append((e0 + b1) / 2)
for ang in holes:
    a = math.radians(ang); cx, cy = math.sin(a) * R_MID, -math.cos(a) * R_MID
    m = band & (np.hypot(xx - cx, yy - cy) <= 0.17 * k); paint(m, SHIRT); art[m, 3] = 0

# the warm body: isotherms, each a wobbly closed shape, hotter toward a core set a little high and left
ox, oy = -0.18 * k, -0.30 * k
rb = np.hypot(xx - ox * 0.0, yy - oy * 0.0); tb = np.arctan2(xx, -yy)
for rad, col, sx, sy in ((2.55, VIOLET, 0.0, 0.0), (1.85, ORANGE, -0.10, -0.18), (1.18, YELLOW, -0.16, -0.30),
                         (0.58, CREAM, -0.20, -0.40)):
    rr_ = np.hypot(xx - sx * k, (yy - sy * k) * 0.92)
    t_ = np.arctan2(xx - sx * k, -(yy - sy * k))
    edge = rad * k * (1 + sum(0.05 / f * np.sin(f * t_ + rng.uniform(0, 6.3)) for f in range(2, 6)))
    paint(rr_ <= edge, col)

# down to print size: each ink kept where it covers most, alpha binary
img = Image.fromarray(art, "RGBA").resize((N // SS, N // SS), Image.BOX)
a = np.asarray(img).copy(); a[..., 3] = np.where(a[..., 3] >= 128, 255, 0)
pal = np.array([CREAM, ORANGE, VIOLET, YELLOW], np.float32)
on = a[..., 3] > 0
near = np.argmin(((a[on][:, None, :3].astype(np.float32) - pal[None]) ** 2).sum(-1), 1)
a[on, :3] = pal[near].astype(np.uint8); a[~on, :3] = 0
out = Image.fromarray(a, "RGBA"); out = out.crop(out.getbbox())
out.save(os.path.join(HERE, "art.png"), optimize=True)
pv = Image.new("RGBA", (out.width + 240, out.height + 240), SHIRT + (255,)); pv.alpha_composite(out, (120, 120))
pv.convert("RGB").resize((1200, 1200 * pv.height // pv.width), Image.LANCZOS).save(os.path.join(HERE, "preview.png"))
json.dump({"where": "centre chest", "w_cm": round(out.width / PX_CM, 1), "top_cm": 10.5}, open(os.path.join(HERE, "placement.json"), "w"))
print("art", out.size, round(out.width / PX_CM, 1), "cm")
