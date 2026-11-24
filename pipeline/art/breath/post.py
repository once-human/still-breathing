# 02 breath, part 2: the temperatures -> the print.
#   python3 pipeline/art/breath/post.py <dir with temp.npy + scene.json> [out.png]
# temp.npy holds degrees C per pixel (crowd.py). This adds each visible breath rising off the people and the heat
# haze over the crowd, softens it the way a heat camera's optics do, maps it through an ironbow palette (cold black
# -> indigo -> magenta -> orange -> white-hot) and lets the coldest tones fall away to the black of the shirt.
# Then the camera's readout: the word in four scripts for the three cities, the nights, the scale bar with its real
# end points, one spot reading taken off a real face in the picture.
import sys, os, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

D = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(HERE, "..", "..", "fonts")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "art-e-breath", "art-black.png")
FW, FH = 4500, 6000                       # the print: 15 x 20 in at 300 dpi

T = np.load(os.path.join(D, "temp.npy")).astype("f4")
meta = json.load(open(os.path.join(D, "scene.json"))); h, w = T.shape
rng = np.random.default_rng(1213)
AIR = 16.0


def smooth_noise(shape, cell, octaves=4, seed=0):
    """soft value noise: no speck smaller than the cell, so nothing prints as grit"""
    r = np.random.default_rng(seed); out = np.zeros(shape, "f4"); amp = 1; tot = 0
    for o in range(octaves):
        c = max(4.0, cell / 2 ** o)
        s = max(2, int(shape[0] / c)), max(2, int(shape[1] / c))
        g = Image.fromarray(r.random(s).astype("f4")).resize((shape[1], shape[0]), Image.BICUBIC)
        out += amp * np.asarray(g, "f4"); tot += amp; amp *= 0.55
    return out / tot


def blur(a, sigma):
    if sigma <= 0.3: return a
    r = int(3 * sigma + 1); k = np.exp(-np.arange(-r, r + 1) ** 2 / (2 * sigma * sigma)).astype("f4"); k /= k.sum()
    a = np.pad(a.astype("f4"), r, mode="edge")
    a = sum(k[i] * a[:, i:i + a.shape[1] - 2 * r] for i in range(2 * r + 1))       # rows
    return sum(k[i] * a[i:i + a.shape[0] - 2 * r, :] for i in range(2 * r + 1))      # columns


# ---------- breath: each visible mouth breathes out a few warm puffs that rise, swell, thin and cool ----------
breath = np.zeros((h, w), "f4")
turb = smooth_noise((h, w), 0.02 * h, 4, 7)
for m in meta["mouths"]:
    u, v, s = m["u"] * w, m["v"] * h, m["px_per_m"]
    if s < 0.035 * h: continue                     # too far to see a breath
    iy, ix = int(min(h - 1, max(0, v))), int(min(w - 1, max(0, u)))
    if T[iy, ix] < 28.0: continue                  # no warm face there: someone in front hides the mouth
    lean = rng.uniform(-0.18, 0.18) * s
    phase = rng.uniform(0, 0.34); rise = s * rng.uniform(0.55, 0.9)
    for k in range(3):
        tk = phase + k * 0.34                      # 0 = just out of the mouth, 1 = most of a metre up
        cx = u + lean * tk + rng.uniform(-0.04, 0.04) * s; cy = v - rise * tk - 0.03 * s
        rad = s * (0.045 + 0.11 * tk)
        x0, x1 = int(max(0, cx - 3 * rad)), int(min(w, cx + 3 * rad)); y0, y1 = int(max(0, cy - 3 * rad)), int(min(h, cy + 3 * rad))
        if x1 <= x0 or y1 <= y0: continue
        yy, xx = np.mgrid[y0:y1, x0:x1].astype("f4")
        tt = turb[y0:y1, x0:x1]
        r2 = ((xx - cx) ** 2 + ((yy - cy) * 0.75) ** 2) / rad ** 2      # taller than wide: it rises
        puff = np.exp(-r2 * (0.8 + 1.2 * tt)) * np.clip((tt - 0.28) * 2.4, 0, 1.2)
        breath[y0:y1, x0:x1] += puff * max(0.0, 1 - tk / 1.2) * rng.uniform(0.6, 1.0)
breath = blur(np.clip(breath, 0, 1), 0.0012 * w)

# ---------- the warmth of thousands of people rising into the cold air above them ----------
alive = (T > 24).mean(1)
crowd_top = int(np.argmax(alive > 0.15)) if (alive > 0.15).any() else h // 3
yy = np.arange(h, dtype="f4")[:, None]
band = np.clip((yy - (crowd_top - 0.10 * h)) / (0.10 * h), 0, 1) * np.clip(1 - (yy - crowd_top) / (0.25 * h), 0, 1)
haze = smooth_noise((h, w), 0.12 * h, 3, 3) * band

# thin warm gas in front of whatever is behind it: it pulls the reading toward its own temperature
a = np.clip(breath * 0.95, 0, 0.8)
temp = np.maximum(T, T * (1 - a) + 31.5 * a) + haze * 0.10 * np.clip(AIR + 3 - T, 0, None)
temp = blur(temp, 0.0007 * w)                     # the lens: a heat camera is never razor sharp

# ---------- ironbow ----------
STOPS = [(0.00, (0, 0, 0)), (0.14, (22, 8, 56)), (0.30, (80, 14, 116)), (0.46, (166, 30, 114)),
         (0.60, (222, 66, 50)), (0.74, (246, 140, 30)), (0.88, (255, 208, 92)), (1.0, (255, 250, 228))]
def ironbow(x):
    x = np.clip(x, 0, 1); out = np.zeros(x.shape + (3,), "f4")
    for (a, ca), (b, cb) in zip(STOPS, STOPS[1:]):
        k = (x >= a) & (x <= b); f = ((x - a) / (b - a))[k][:, None]
        out[k] = np.array(ca) * (1 - f) + np.array(cb) * f
    return out

# the scale: just under the night air at the bottom, the inner corner of an eye at the top
LO = float(os.environ.get("LO", 14.6)); HI = float(np.percentile(temp[temp > 30], 99.9)) if (temp > 30).any() else 36.5
HI = max(HI, 36.2)
lin = np.clip((temp - LO) / (HI - LO), 0, 1)
# like the camera's own gain control: part linear, part histogram-equalised over what is warmer than the air, so
# the few degrees across a face (warm eye corners, cold nose, cooler cheeks) get as much of the palette as the
# twenty degrees between a coat and the sky
seen = np.sort(temp[(temp > LO + 2) & (temp < HI)].ravel()[::7])
cdf = np.searchsorted(seen, np.clip(temp, LO, HI)).astype("f4") / max(1, len(seen))
x = np.where(temp > LO, 0.45 * lin + 0.55 * cdf, lin)
rgb = ironbow(x)
alpha = np.clip((x - 0.04) / 0.12, 0, 1)        # the coldest tones are not printed: the black shirt is the cold
art = np.dstack([rgb, alpha * 255]).clip(0, 255).astype("u1")
im = Image.fromarray(art, "RGBA").resize((FW, int(round(FW * h / w))), Image.LANCZOS)

# ---------- the camera's readout ----------
canvas = Image.new("RGBA", (FW, FH), (0, 0, 0, 0)); canvas.alpha_composite(im, (0, FH - im.height))
d = ImageDraw.Draw(canvas)
INK = (255, 250, 231, 255); QUIET = (255, 250, 231, 160)
def brico(px, wght):
    f = ImageFont.truetype(f"{F}/BricolageGrotesque-Var.ttf", px, layout_engine=ImageFont.Layout.RAQM); f.set_variation_by_axes([wght]); return f
def kan(px): return ImageFont.truetype(f"{F}/NotoSansKannada-Black.ttf", px, layout_engine=ImageFont.Layout.RAQM)
def dev(px): return ImageFont.truetype(f"{F}/NotoSansDevanagari-Black.ttf", px, layout_engine=ImageFont.Layout.RAQM)

M = 300
d.text((M, M), "breath", font=brico(360, 760), fill=INK, anchor="lt")
# the same word in the three cities' languages: Delhi, Mumbai, Bengaluru
x0 = M + 6; yb = M + 600
for word, font in (("साँस", dev(190)), ("श्वास", dev(190)), ("ಉಸಿರು", kan(190))):
    d.text((x0, yb), word, font=font, fill=INK, anchor="ls")
    x0 += d.textlength(word, font=font) + 110
d.text((FW - M, M + 30), "india", font=brico(150, 700), fill=INK, anchor="rt")
d.text((FW - M, M + 230), "05 — 13 . 12 . 2026", font=brico(104, 420), fill=QUIET, anchor="rt")
d.text((FW - M, M + 370), "delhi ncr  /  mumbai  /  bengaluru", font=brico(80, 420), fill=QUIET, anchor="rt")

# scale bar on the right edge, the real end points of the palette
bx, by0, by1, bw = FW - M - 64, 960, 1980, 64
bar = ironbow(np.linspace(1, 0, by1 - by0)[:, None].repeat(bw, 1))
canvas.alpha_composite(Image.fromarray(np.dstack([bar, np.full(bar.shape[:2], 255)]).astype("u1"), "RGBA"), (bx, by0))
d.text((bx - 36, by0), f"{HI:.1f}°", font=brico(92, 600), fill=INK, anchor="rt")
d.text((bx - 36, by1), f"{LO:.1f}°", font=brico(92, 600), fill=INK, anchor="rb")

# one spot reading: the warmest face in the upper middle of the crowd, its real temperature
y_a, y_b = int(h * 0.42), int(h * 0.62); x_a, x_b = int(w * 0.25), int(w * 0.75)
win = temp[y_a:y_b, x_a:x_b]
iy, ix = np.unravel_index(np.argmax(win), win.shape)
reading = float(win[iy, ix])
sx, sy = (x_a + ix) * FW / w, FH - im.height + (y_a + iy) * im.height / h
r = 64
for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
    d.line((sx + dx * r * 0.5, sy + dy * r * 0.5, sx + dx * r * 1.6, sy + dy * r * 1.6), fill=INK, width=14)
d.text((sx + r * 1.9, sy - 24), f"{reading:.1f}°", font=brico(96, 600), fill=INK, anchor="lb")

os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True); canvas.save(OUT)
print("ok", OUT, canvas.size, "scale", round(LO, 1), round(HI, 1), "spot", round(reading, 1), "mouths", len(meta["mouths"]))
