# python3 stage_post.py <place> <out.webp> <strip0.npy> <strip1.npy> ...      (numpy, pillow)
# Stitches a place's strips (strip 0 at the top) and develops them for the viewer, clipped, sRGB, 8 bits with a
# half-step dither so the gradients never band. No grain is added.
#   studio, window: exposure 1, in the viewer's own units (the picture was lit by the viewer's lights); the lens is
#     already in the render (stage.py's camera), so no blur
#   show: the brightest lamps in the band the viewer looks through just reach white, and the stage's lamps open into
#     wide soft discs (a disc 0.34 % of the width across, the look the show has had from the start)
import os, sys
import numpy as np
from PIL import Image

PLACE, OUT, STRIPS = sys.argv[1], sys.argv[2], sys.argv[3:]
BLUR = {"show": 0.0017}.get(PLACE, 0.0)
img = np.concatenate([np.load(p).astype(np.float32) for p in STRIPS], axis=0)
H, W, _ = img.shape
print("stitched", W, "x", H)
img = np.nan_to_num(np.maximum(img, 0), nan=0, posinf=0)

# lens blur: a disc 0.34 % of the width across, by FFT; it wraps round the sides, which is right for a panorama
# (the top and bottom rows are the dark roof and floor, so the wrap there shows nothing)
if BLUR:
    R = max(1.0, W * BLUR)
    r = int(R) + 2
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disc = np.clip(R + 0.5 - np.hypot(xx, yy), 0, 1).astype(np.float32); disc /= disc.sum()
    k = np.zeros((H, W), np.float32); k[:2 * r + 1, :2 * r + 1] = disc; k = np.roll(k, (-r, -r), (0, 1))
    K = np.fft.rfft2(k)
    for c in range(3):
        img[..., c] = np.fft.irfft2(np.fft.rfft2(img[..., c]) * K, s=(H, W))
    img = np.maximum(img, 0)

EXPOSE = float(os.environ.get("EXPOSE", "0") or 0)
band = img[int(H * 0.3):int(H * 0.62)]
lum = band @ np.array([0.2126, 0.7152, 0.0722], np.float32)
k = EXPOSE or (1.0 / max(float(np.percentile(lum, 99.7)), 1e-6) if PLACE == "show" else 1.0)
print("exposure", round(k, 3), "band median", round(float(np.median(lum)) * k, 4))
img = np.clip(img * k, 0, 1)
srgb = np.where(img <= 0.0031308, img * 12.92, 1.055 * np.power(img, 1 / 2.4) - 0.055)
q = np.clip(np.floor(srgb * 255 + np.random.default_rng(7).uniform(0, 1, srgb.shape)), 0, 255).astype(np.uint8)
Image.fromarray(q, "RGB").save(OUT, quality=88 if PLACE == "show" else 92, method=6)
print("saved", OUT)
