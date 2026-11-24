# 03 breath, part 2: temperature image -> the print.
#   python3 art/breath_post.py <dir with temp.exr + mouths.json> [out.png]
# Adds every visible breath and the heat rising off the crowd, maps temperature through an ironbow palette (the
# classic thermal look: cold black -> indigo -> magenta -> orange -> white-hot), lets the coldest parts fall away
# to the black of the shirt, and sets the camera's readout: a scale bar, one spot reading, the place and the night.
import sys, os, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

D = sys.argv[1]; OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "art-c-breath", "art-black.png")
HERE = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(HERE, "..", "fonts")
FW, FH = 4500, 6000                       # the print: 15 x 20 in at 300 dpi

T = np.load(os.path.join(D, "temp.npy")).astype("f4")
meta = json.load(open(os.path.join(D, "mouths.json"))); h, w = T.shape
rng = np.random.default_rng(1213)

# ---------- value noise, for breath and rising heat ----------
def noise(shape, scale, octaves=4, seed=0):
    r = np.random.default_rng(seed); out = np.zeros(shape, "f4"); amp = 1; tot = 0
    for o in range(octaves):
        s = max(2, int(shape[0] / (scale / 2 ** o))), max(2, int(shape[1] / (scale / 2 ** o)))
        g = r.random(s).astype("f4")
        up = np.asarray(Image.fromarray(g).resize((shape[1], shape[0]), Image.BICUBIC), "f4")
        out += amp * up; tot += amp; amp *= 0.5
    return out / tot

breath = np.zeros((h, w), "f4")
turb = noise((h, w), 0.012 * h, 5, 7)
for i, m in enumerate(meta["mouths"]):
    u, v, s = m["u"] * w, m["v"] * h, m["px_per_m"]
    if s < 0.01 * h: continue
    iy, ix = int(min(h - 1, max(0, v))), int(min(w - 1, max(0, u)))
    if T[iy, ix] < 0.45: continue                   # no warm face there: someone in front hides it
    # breathing out, a few times: each exhale a warm puff that leaves the mouth, rises, swells and cools
    lean = m["fx"] * 0.5 + rng.uniform(-0.25, 0.25) * s
    phase = rng.uniform(0, 0.33); rise = s * rng.uniform(0.9, 1.5)
    for k in range(4):
        tk = phase + k * 0.33                        # 0 = just out of the mouth, 1 = about a metre up
        cx = u + lean * tk + rng.uniform(-0.06, 0.06) * s; cy = v - rise * tk - 0.04 * s
        rad = s * (0.04 + 0.1 * tk)
        x0, x1 = int(max(0, cx - 3 * rad)), int(min(w, cx + 3 * rad)); y0, y1 = int(max(0, cy - 3 * rad)), int(min(h, cy + 3 * rad))
        if x1 <= x0 or y1 <= y0: continue
        yy, xx = np.mgrid[y0:y1, x0:x1].astype("f4")
        tt = turb[y0:y1, x0:x1]
        r2 = ((xx - cx) ** 2 + ((yy - cy) * 0.7) ** 2) / rad ** 2       # taller than wide: it rises
        puff = np.exp(-r2 * (0.7 + 1.4 * tt)) * ((tt - 0.3) * 2.2).clip(0, 1.3)        # wisps, not a fog
        breath[y0:y1, x0:x1] += puff * max(0, 1 - tk / 1.25) * rng.uniform(0.7, 1.0)
breath = np.clip(breath, 0, 1.2)

# the heat of a few thousand people: a slow warm haze rising off the crowd into the cold air
crowd_top = np.argmax((T > 0.3).any(1)) if (T > 0.3).any() else h // 3
yy, xx = np.mgrid[0:h, 0:w].astype("f4")
haze = noise((h, w), 0.2 * h, 4, 3) * np.clip((yy - (crowd_top - h * 0.18)) / (h * 0.35), 0, 1) * np.clip(1 - (yy - crowd_top) / (h * 0.5), 0, 1)

temp = np.maximum(T, 0) + 0.62 * breath + 0.12 * haze
k = np.array([0.25, 0.5, 0.25], "f4")                # a thermal sensor's slight softness
temp = np.apply_along_axis(lambda r: np.convolve(r, k, "same"), 1, temp)
temp = np.apply_along_axis(lambda c: np.convolve(c, k, "same"), 0, temp)

# ---------- ironbow ----------
STOPS = [(0.00, (0, 0, 0)), (0.16, (20, 8, 52)), (0.32, (78, 14, 112)), (0.48, (168, 32, 112)),
         (0.62, (226, 72, 46)), (0.76, (248, 148, 28)), (0.9, (255, 214, 96)), (1.0, (255, 250, 228))]
def ironbow(x):
    x = np.clip(x, 0, 1); out = np.zeros(x.shape + (3,), "f4")
    for (a, ca), (b, cb) in zip(STOPS, STOPS[1:]):
        k = ((x >= a) & (x <= b)); f = ((x - a) / (b - a))[k][:, None]
        out[k] = np.array(ca) * (1 - f) + np.array(cb) * f
    return out
lo, hi = 0.06, 0.98                       # the scale: the ground at the bottom, a raised hand at the top
x = (temp - lo) / (hi - lo)
rgb = ironbow(x)
# the coldest tones are not printed: the black shirt is the cold
alpha = np.clip((x - 0.06) / 0.14, 0, 1)
# the bottom of the picture sinks into the shirt: the nearest people dissolve into the cold, the crowd reads as one
fy = np.linspace(0, 1, h)[:, None]
alpha *= np.clip((0.97 - fy) / 0.24, 0, 1) ** 1.6
art = np.dstack([rgb, alpha * 255]).astype("u1")
im = Image.fromarray(art, "RGBA").resize((FW, int(FW * h / w)), Image.LANCZOS)

# ---------- the camera's readout ----------
canvas = Image.new("RGBA", (FW, FH), (0, 0, 0, 0)); canvas.alpha_composite(im, (0, FH - im.height))
d = ImageDraw.Draw(canvas)
INK = (255, 250, 231, 255); QUIET = (255, 250, 231, 150)
def brico(px, wght):
    f = ImageFont.truetype(f"{F}/BricolageGrotesque-Var.ttf", px, layout_engine=ImageFont.Layout.RAQM); f.set_variation_by_axes([wght]); return f
def kan(px, wt="Bold"): return ImageFont.truetype(f"{F}/NotoSansKannada-{wt}.ttf", px, layout_engine=ImageFont.Layout.RAQM)
M = 300
d.text((M, M - 40), "ಉಸಿರು", font=kan(300, "Black"), fill=INK)
d.text((M + 8, M + 330), "breath", font=brico(170, 700), fill=INK)
d.text((FW - M, M + 40), "bengaluru", font=brico(150, 700), fill=INK, anchor="ra")
d.text((FW - M, M + 230), "12 + 13 . 12 . 2026", font=brico(110, 400), fill=QUIET, anchor="ra")
# scale bar on the right edge: the palette, with the night's air at the bottom and skin at the top
bx, by0, by1, bw = FW - M - 70, 1250, 2650, 70
bar = ironbow(np.linspace(1, 0, by1 - by0)[:, None].repeat(bw, 1))
canvas.alpha_composite(Image.fromarray(np.dstack([bar, np.full(bar.shape[:2], 255)]).astype("u1"), "RGBA"), (bx, by0))
d.text((bx - 40, by0), "36.4°", font=brico(96, 600), fill=INK, anchor="rt")
d.text((bx - 40, by1), "15.2°", font=brico(96, 600), fill=INK, anchor="rb")
# one spot reading, on the warmest raised hand in the upper crowd
ys, xs = np.nonzero(temp[: int(h * 0.75)] > np.percentile(temp, 99.7))
if len(xs):
    k = np.argmin(ys); sx, sy = xs[k] * FW / w, FH - im.height + ys[k] * im.height / h
    r = 70
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        d.line((sx + dx * r * 0.45, sy + dy * r * 0.45, sx + dx * r * 1.6, sy + dy * r * 1.6), fill=INK, width=12)
    d.text((sx + r * 1.9, sy - 20), "34.1°", font=brico(100, 600), fill=INK, anchor="lb")
os.makedirs(os.path.dirname(OUT), exist_ok=True); canvas.save(OUT); print("ok", OUT, canvas.size)
