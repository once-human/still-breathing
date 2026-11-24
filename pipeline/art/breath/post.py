# 02 breath, part 2: the temperatures -> the print.
#   python3 pipeline/art/breath/post.py <dir with temp.npy + scene.json> [out.png] [width]
# temp.npy holds degrees C per pixel (crowd.py). The print is drawn from it the way an illustrator would make a
# heat-camera picture for a shirt, not the way the camera shows it:
#   - the heat in flat bands, like a screen print: each band one colour of the ironbow, the edges clean curves, nothing
#     smaller than a millimetre, no grain
#   - each visible breath rising off the people as a soft warm wisp
#   - depth: the far crowd goes soft and slides into a purple haze, which thins upward and dissolves into the shirt
#   - no frame: the sides and the bottom dissolve into the black of the shirt too; the coldest band isn't printed
# No words: the lettering is drawn in the Figma file and laid over it (pipeline/overlays).
import sys, os, json
import numpy as np
from PIL import Image

D = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "art-e-breath", "art-black.png")
FW = int(sys.argv[3]) if len(sys.argv) > 3 else 4500          # the print: 15 x 20 in at 300 dpi
FH = FW * 4 // 3

T0 = np.load(os.path.join(D, "temp.npy")).astype("f4")
meta = json.load(open(os.path.join(D, "scene.json")))
rng = np.random.default_rng(1213)


def resize(a, w, h, how=Image.BICUBIC):
    return np.asarray(Image.fromarray(a.astype("f4")).resize((w, h), how), "f4")


def blur(a, sigma):
    """gaussian blur; big radii are done on a smaller copy (the same result, a fraction of the work)"""
    if sigma <= 0.3: return a
    if sigma > 8:
        k = int(sigma / 4); h, w = a.shape
        return resize(blur(resize(a, max(2, w // k), max(2, h // k)), sigma / k), w, h)
    r = int(3 * sigma + 1); g = np.exp(-np.arange(-r, r + 1) ** 2 / (2 * sigma * sigma)).astype("f4"); g /= g.sum()
    p = np.pad(a.astype("f4"), r, mode="edge")
    p = sum(g[i] * p[:, i:i + a.shape[1]] for i in range(2 * r + 1))
    return sum(g[i] * p[i:i + a.shape[0], :] for i in range(2 * r + 1))


def smooth_noise(shape, cell, octaves=4, seed=0):
    """soft value noise: no speck smaller than the cell"""
    r = np.random.default_rng(seed); out = np.zeros(shape, "f4"); amp = 1; tot = 0
    for o in range(octaves):
        c = max(4.0, cell / 2 ** o)
        s = max(2, int(shape[0] / c)), max(2, int(shape[1] / c))
        out += amp * resize(r.random(s), shape[1], shape[0]); tot += amp; amp *= 0.55
    return out / tot


# work at the print's own size: the bands are cut there, so their edges are as clean as the file allows
h, w = FH, FW
T = resize(T0, w, h)
S = w / 900                                             # sizes below are tuned at 900 px wide

# ---------- breath: each visible mouth breathes out a few warm puffs that rise, swell and thin ----------
breath = np.zeros((h, w), "f4")
turb = smooth_noise((h, w), 0.03 * h, 4, 7)
for m in meta["mouths"]:
    u, v, s = m["u"] * w, m["v"] * h, m["px_per_m"] * w / meta["w"]
    if s < 0.035 * h: continue                          # too far to see a breath
    iy, ix = int(min(h - 1, max(0, v))), int(min(w - 1, max(0, u)))
    if T[iy, ix] < 28.0: continue                       # someone in front hides the mouth
    lean = rng.uniform(-0.2, 0.2) * s; phase = rng.uniform(0, 0.34); rise = s * rng.uniform(0.6, 1.0)
    for k in range(3):
        tk = phase + k * 0.34
        cx = u + lean * tk + rng.uniform(-0.04, 0.04) * s; cy = v - rise * tk - 0.03 * s
        rad = s * (0.05 + 0.12 * tk)
        x0, x1 = int(max(0, cx - 3 * rad)), int(min(w, cx + 3 * rad)); y0, y1 = int(max(0, cy - 3 * rad)), int(min(h, cy + 3 * rad))
        if x1 <= x0 or y1 <= y0: continue
        yy, xx = np.mgrid[y0:y1, x0:x1].astype("f4"); tt = turb[y0:y1, x0:x1]
        r2 = ((xx - cx) ** 2 + ((yy - cy) * 0.75) ** 2) / rad ** 2
        puff = np.exp(-r2 * (0.8 + 1.2 * tt)) * np.clip((tt - 0.25) * 2.4, 0, 1.2)
        breath[y0:y1, x0:x1] += puff * max(0.0, 1 - tk / 1.3) * rng.uniform(0.8, 1.2)
breath = blur(np.clip(breath, 0, 1), 2.0 * S)
a = np.clip(breath * 0.95, 0, 0.8)
temp = np.maximum(T, T * (1 - a) + 33.0 * a)

# ---------- the scale: the night air at the bottom, the warmest skin at the top ----------
LO = 14.6
HI = max(36.0, float(np.percentile(temp[temp > 30], 99.5))) if (temp > 30).any() else 36.0
lin = np.clip((temp - LO) / (HI - LO), 0, 1)
seen = np.sort(temp[(temp > LO + 2) & (temp < HI)].ravel()[::97])
cdf = np.searchsorted(seen, np.clip(temp, LO, HI)).astype("f4") / max(1, len(seen))
x = np.where(temp > LO, 0.5 * lin + 0.5 * cdf, lin)

# ---------- depth: the far crowd softens and slides into the haze ----------
alive = (T > 24).mean(1)
top = int(np.argmax(alive > 0.15)) if (alive > 0.15).any() else h // 4      # where the crowd begins
yy = np.arange(h, dtype="f4")[:, None] / h
t0 = top / h
far = np.clip((0.5 - yy) / (0.5 - t0), 0, 1) ** 1.8                      # 0 near, 1 at the back row
# blur grows with distance: a stack of a few blurs, picked per row
levels = [0, 1.5 * S, 3.5 * S, 7 * S]
stack = [blur(x, s) for s in levels]
f = far * (len(levels) - 1); i0 = np.clip(np.floor(f).astype(int), 0, len(levels) - 2); fr = f - i0
xs = np.zeros_like(x)
for k in range(len(levels) - 1):
    sel = (i0 == k).astype("f4")
    xs += sel * (stack[k] * (1 - fr) + stack[k + 1] * fr)
# the edges of the bands are cut on a slightly softened field, so they come out as clean curves
xs = blur(xs, 0.9 * S)

# ---------- flat bands ----------
# the ironbow in eight inks; the first isn't printed (the black shirt is the cold)
INKS = [(0, 0, 0), (38, 12, 84), (84, 18, 120), (148, 30, 122), (212, 58, 78), (242, 124, 36), (255, 192, 78), (255, 241, 205)]
EDGES = [0.07, 0.2, 0.34, 0.48, 0.61, 0.74, 0.88]
aa = 0.006                                                                  # edge softness in the heat scale: a pixel or so
# near, the bands are cut clean; toward the back their edges melt, so the far crowd is a soft glow, not a shelf
soft = aa + 0.07 * far ** 1.5
rgb = np.zeros((h, w, 3), "f4"); rgb[:] = INKS[0]
cover = np.zeros((h, w), "f4")
for k, e in enumerate(EDGES):
    step = np.clip((xs - e) / (2 * soft) + 0.5, 0, 1)                       # 0 below the edge, 1 above
    rgb += step[..., None] * (np.array(INKS[k + 1], "f4") - np.array(INKS[k], "f4"))
    if k == 0: cover = step

# ---------- haze: warm air over the crowd, purple, thinning upward into the shirt ----------
HAZE = np.array((70, 22, 118), "f4")
haze_n = smooth_noise((h, w), 0.18 * h, 3, 3)
ss = lambda v: (lambda c: c * c * (3 - 2 * c))(np.clip(v, 0, 1))
band = ss((yy - (t0 - 0.24)) / 0.24) ** 1.6 * ss(1 - (yy - t0) / 0.2)
hz = np.clip(band * (0.55 + 0.6 * haze_n), 0, 0.85) * (0.35 + 0.65 * far)
# the back rows lose their colour to the haze before they lose their shape
mix = np.clip(far * 0.85, 0, 0.85)[..., None] * cover[..., None]
rgb = rgb * (1 - mix) + HAZE * mix * (0.55 + 0.45 * (rgb.mean(2, keepdims=True) / 255))
rgb = rgb * (1 - hz[..., None]) + HAZE * hz[..., None]
alpha = np.maximum(cover * 1.0, hz * 1.05)

# ---------- no frame: the sides, the bottom and the top dissolve into the shirt ----------
xx = np.arange(w, dtype="f4")[None, :] / w
side = np.clip(np.minimum(xx, 1 - xx) / 0.07, 0, 1)
bottom = np.clip((1 - yy) / 0.09, 0, 1)
fade_top = ss((yy - (t0 - 0.3)) / 0.32)
edge = (side * bottom * fade_top) ** 1.2
# a little wander in the dissolve, so it reads as drawn, not masked
edge = np.clip(edge + (smooth_noise((h, w), 0.05 * h, 2, 11) - 0.5) * 0.25 * (edge < 0.999), 0, 1)
alpha = np.clip(alpha * edge, 0, 1)
# DTG: nothing faint enough to print as a speckle
alpha = np.where(alpha < 0.06, 0, alpha)

art = np.dstack([rgb, alpha * 255]).clip(0, 255).astype("u1")
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
Image.fromarray(art, "RGBA").save(OUT)
print("ok", OUT, (w, h), "scale", round(LO, 1), round(HI, 1), "crowd top", round(t0, 3))
