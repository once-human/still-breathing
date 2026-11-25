# python3 stage_post.py <place> <out.webp> <strip0.npy> <strip1.npy> ...      (numpy, pillow)
# Stitches a place's strips (strip 0 at the top) and develops them for the viewer, clipped, sRGB, 8 bits with a
# half-step dither so the gradients never band. No grain is added.
#   studio, window: exposure 1, in the viewer's own units (the picture was lit by the viewer's lights); the lens is
#     already in the render (stage.py's camera), so no blur
#   show: the brightest lamps in the band the viewer looks through just reach white, with a lens's faint glow round
#     them; the depth of field is the render's own (85 mm f/5.6), so the crowd stays people, not a blur
import os, sys
import numpy as np
from PIL import Image

PLACE, OUT, STRIPS = sys.argv[1], sys.argv[2], sys.argv[3:]
BLUR = 0.0   # the lens is in the render (stage.py's camera)
# BAND=1: the strips are the band the viewer's camera can see (rows BAND_ROWS of a 16384 x 8192 panorama, sharp),
# written as TILES tiles of 4096 stacked top to bottom (no image format takes 16384 across), plus a half-size copy
# (<out>-lo.webp) for lighter machines. scene.ts BAND matches these numbers.
BAND = os.environ.get("BAND") == "1"
BAND_W, BAND_ROWS, TILES = 16384, (3368, 5008), 4
img = np.concatenate([np.load(p).astype(np.float32) for p in STRIPS], axis=0)
H, W, _ = img.shape
print("stitched", W, "x", H)
img = np.nan_to_num(np.maximum(img, 0), nan=0, posinf=0)

def disc(img, R):
    """a disc blur of radius R px by FFT; it wraps round the sides, which is right for a panorama"""
    r = int(R) + 2
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    d = np.clip(R + 0.5 - np.hypot(xx, yy), 0, 1).astype(np.float32); d /= d.sum()
    p = r if BAND else 0   # the band does not wrap top to bottom: black above and below it while it blurs
    Hp = H + 2 * p; img = np.pad(img, ((p, p), (0, 0), (0, 0))) if p else img
    k = np.zeros((Hp, W), np.float32); k[:2 * r + 1, :2 * r + 1] = d; k = np.roll(k, (-r, -r), (0, 1))
    K = np.fft.rfft2(k)
    out = np.stack([np.fft.irfft2(np.fft.rfft2(img[..., c]) * K, s=(Hp, W)) for c in range(3)], -1).astype(np.float32)
    return out[p:p + H]


if BLUR:
    img = np.maximum(disc(img, max(1.0, W * BLUR)), 0)

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
    assert (W, H) == (BAND_W, BAND_ROWS[1] - BAND_ROWS[0]), (W, H)
    q = np.concatenate([q[:, i * (W // TILES):(i + 1) * (W // TILES)] for i in range(TILES)], axis=0)
    im = Image.fromarray(q, "RGB"); im.save(OUT, quality=90, method=6)
    im.resize((im.width // 2, im.height // 2), Image.LANCZOS).save(OUT.replace(".webp", "-lo.webp"), quality=90, method=6)
    print("band", im.size, "tiles", TILES)
else:
    Image.fromarray(q, "RGB").save(OUT, quality=88 if PLACE == "show" else 92, method=6)
print("saved", OUT)
