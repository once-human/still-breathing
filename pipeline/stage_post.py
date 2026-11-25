# python3 stage_post.py <place> <out.webp> <strip0.npy> <strip1.npy> ...      (numpy, pillow)
# Stitches a place's strips (strip 0 at the top) and develops them for the viewer, clipped, sRGB, 8 bits with a
# half-step dither so the gradients never band. No grain is added.
#   studio, window: exposure 1, in the viewer's own units (the picture was lit by the viewer's lights); the lens is
#     already in the render (stage.py's camera), so no blur
#   show: the brightest lamps in the band the viewer looks through just reach white, with a lens's faint glow round
#     them; the depth of field is the render's own (85 mm f/5.6), so the crowd stays people, not a blur
import math, os, sys
import numpy as np
from PIL import Image

PLACE, OUT, STRIPS = sys.argv[1], sys.argv[2], sys.argv[3:]
BLUR = 0.0   # the lens is in the render (stage.py's camera)
# BAND=1: the strips are the band the viewer's camera can see (rows BAND_ROWS of a 16384 x 8192 panorama, sharp),
# written as TILES tiles of 4096 stacked top to bottom (no image format takes 16384 across), plus a half-size copy
# (<out>-lo.webp) for lighter machines. scene.ts BAND matches these numbers.
# ROWS=r0,r1 with BAND: other rows of the same panorama (the canopy's moving part, stage.yml motion), same tiling.
# Writes .png instead of .webp when OUT says so (the motion's frames, made into a video).
BAND = os.environ.get("BAND") == "1"
BAND_W, TILES = 16384, 4
BAND_ROWS = tuple(int(x) for x in os.environ.get("ROWS", "3368,5008").split(","))
img = np.concatenate([np.load(p).astype(np.float32) for p in STRIPS], axis=0)
# the people's mask and distance (stage.py MASK), where the strips have one
MASKS = [p.replace(".npy", "-mask.npy") for p in STRIPS]
mask = np.concatenate([np.load(p).astype(np.float32) for p in MASKS], axis=0) if all(os.path.exists(p) for p in MASKS) else None
H, W, _ = img.shape
print("stitched", W, "x", H)
img = np.nan_to_num(np.maximum(img, 0), nan=0, posinf=0)

def disc(img, R, C=3):
    """a disc blur of radius R px by FFT (C channels); it wraps round the sides, which is right for a panorama"""
    r = int(R) + 2
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    d = np.clip(R + 0.5 - np.hypot(xx, yy), 0, 1).astype(np.float32); d /= d.sum()
    p = r if BAND else 0   # the band does not wrap top to bottom: black above and below it while it blurs
    Hp = H + 2 * p; img = np.pad(img, ((p, p), (0, 0), (0, 0))) if p else img
    k = np.zeros((Hp, W), np.float32); k[:2 * r + 1, :2 * r + 1] = d; k = np.roll(k, (-r, -r), (0, 1))
    K = np.fft.rfft2(k)
    out = np.stack([np.fft.irfft2(np.fft.rfft2(img[..., c]) * K, s=(Hp, W)) for c in range(C)], -1).astype(np.float32)
    return out[p:p + H]


if BLUR:
    img = np.maximum(disc(img, max(1.0, W * BLUR)), 0)

# the people, and only the people, as a very fast portrait lens (85 mm wide open, focused on the person in front)
# would draw them: soft shapes in the dark, more so the further back, a little darker than the room round them so
# they stay behind the person, while the hall, the cloth and the lamps stay sharp. Each person is blurred over what
# is behind them (filled in from round them), so the blur spreads past their edges as it would.
if mask is not None:
    m = np.clip(mask[..., 0], 0, 1)
    z = np.where(m > 0.02, mask[..., 1] * 100 / np.maximum(m, 1e-3), 100.0)
    # never less than 40 px (nearly a degree): nobody is made out, only people
    RADII = [40, 56, 74, 94, 116]
    coc = np.clip(0.085 / 0.45 * np.abs(1 / 2.8 - 1 / np.maximum(z, 0.5)) * W / (4 * math.pi), RADII[0], RADII[-1]) * W / 16384
    fill = disc(np.concatenate([img * (1 - m)[..., None], (1 - m)[..., None]], -1), 64 * W / 16384, 4)
    fill = fill[..., :3] / np.maximum(fill[..., 3:], 1e-3)
    base = img * (1 - m)[..., None] + fill * m[..., None]
    acc = np.zeros_like(img); cov = np.zeros((H, W), np.float32)
    for i, R_ in enumerate(RADII):
        lo = RADII[i - 1] if i else 0; hi = RADII[i + 1] if i + 1 < len(RADII) else None
        c_ = coc * 16384 / W
        w = np.clip((c_ - lo) / (R_ - lo), 0, 1) if i else (c_ <= R_).astype(np.float32)
        if hi is not None: w = np.minimum(w, np.clip((hi - c_) / (hi - R_), 0, 1))
        mi = m * w
        if mi.max() <= 0: continue
        b = disc(np.concatenate([img * mi[..., None], mi[..., None]], -1), R_ * W / 16384, 4)
        acc += b[..., :3]; cov += b[..., 3]
    cov = np.clip(cov, 0, 1)
    img = np.maximum(base * (1 - cov)[..., None] + acc * 0.6, 0)
    print("people blurred:", round(float(m.mean()), 3), "of the picture, radius median", round(float(np.median(coc[m > 0.5])), 1) if (m > 0.5).any() else 0)

# the show: a real lens's glow round the lamps and screens (light scattered in the glass), only from what is far
# brighter than the room; it is wide and faint, so it reads as air, never as a filter
if PLACE == "show":
    lum0 = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    t = float(os.environ.get("HOT", "0") or 0) or float(np.percentile(lum0, 99.5)); print("glow from", round(t, 5))
    hot = img * np.clip((lum0 / max(t, 1e-6) - 1.0), 0, 4)[..., None] / 4
    img = img + 0.05 * disc(hot, W * 0.006) + 0.02 * disc(hot, W * 0.02)

# EXPOSE, BLACK (and HOT, where the glow starts): the exposure and black point given (the band takes the whole picture's, so the two meet unseen)
EXPOSE = float(os.environ.get("EXPOSE", "0") or 0)
band = img if BAND else img[int(H * 0.3):int(H * 0.62)]
lum = band @ np.array([0.2126, 0.7152, 0.0722], np.float32)
k = EXPOSE or (1.0 / max(float(np.percentile(lum, 99.7)), 1e-6) if PLACE == "show" else 1.0)
print("exposure", round(k, 3), "band median", round(float(np.median(lum)) * k, 4))
img = img * k
if PLACE == "show":   # the black point a photographer sets for a night show: the haze's faint floor goes to black
    b = float(os.environ.get("BLACK", "0") or 0) or 0.6 * float(np.percentile(lum, 10)) * k
    print("black point", round(b, 5))
    img = np.maximum(img - b, 0) / (1 - b)
img = np.clip(img, 0, 1)
srgb = np.where(img <= 0.0031308, img * 12.92, 1.055 * np.power(img, 1 / 2.4) - 0.055)
q = np.clip(np.floor(srgb * 255 + np.random.default_rng(7).uniform(0, 1, srgb.shape)), 0, 255).astype(np.uint8)
if BAND:
    # the band itself at 16384 across; the canopy's moving rows may come at half that (stage.yml motion)
    assert W in (BAND_W, BAND_W // 2) and H == (BAND_ROWS[1] - BAND_ROWS[0]) * W // BAND_W, (W, H)
    q = np.concatenate([q[:, i * (W // TILES):(i + 1) * (W // TILES)] for i in range(TILES)], axis=0)
    im = Image.fromarray(q, "RGB")
    if OUT.endswith(".png"): im.save(OUT, compress_level=1)   # a frame of the motion: lossless, the video squeezes it
    else:
        im.save(OUT, quality=90, method=6)
        im.resize((im.width // 2, im.height // 2), Image.LANCZOS).save(OUT.replace(".webp", "-lo.webp"), quality=90, method=6)
    print("band", im.size, "tiles", TILES)
else:
    Image.fromarray(q, "RGB").save(OUT, quality=88 if PLACE == "show" else 92, method=6)
print("saved", OUT)
