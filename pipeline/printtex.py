# python3 printtex.py <outdir> : the prints as their own sharp textures for the viewer and the path tracer
#   print-back-<d>-<tee>.webp   the back, 2048 x 2731 (54 px/cm over 38.1 x 50.8 cm), RGBA, alpha = ink
#   print-front-<tee>.webp      the chest lettering, 632 x 976 (60 px/cm over 10.5 cm), RGBA
# The fabric itself is one flat colour, so the prints are all the detail there is: they get the pixels.
# Stored premultiplied (colour already times coverage, exact bytes kept under clear pixels), so filtering and
# mipmaps never pull a dark or light fringe in from the clear surround: shaded as fabric*(1-a) + rgb.
import sys, numpy as np
from PIL import Image
OUT = sys.argv[1]
FULL = len(sys.argv) > 3 and sys.argv[3] == "full"   # close-zoom version: 3600 x 4800 (94 px/cm), fetched only on zoom
BW, BH = (3600, 4800) if FULL else (2048, 2731)
TEE = {"black": (21, 21, 21), "cream": (255, 250, 231)}
HALO = {"black": (21, 21, 21), "cream": (236, 227, 206)}   # halo fill used in the Figma file: holes in the ink

def knockout(a, tee):
    # halos drawn in the tee colour are not ink; on the real print they're holes that show the fabric
    d = np.abs(a[..., :3].astype(int) - np.array(TEE[tee])).sum(-1)
    d2 = np.abs(a[..., :3].astype(int) - np.array(HALO[tee])).sum(-1)
    a[..., 3] = np.where((d < 24) | (d2 < 24), 0, a[..., 3])
    return a

def resize_rgba(img, size, f=Image.BOX):
    # premultiplied, so edges don't pick up the colour of transparent pixels. Shrinking line art: an area
    # average (each pixel is the ink that falls in it), as sharp as it gets with no ringing, and it packs 4x
    # smaller than a windowed-sinc resample, whose ripples make every pixel unique
    a = np.array(img.convert("RGBA")).astype(np.float32) / 255
    a[..., :3] *= a[..., 3:4]
    ch = [np.array(Image.fromarray(a[..., i]).resize(size, f)) for i in range(4)]
    out = np.clip(np.dstack(ch), 0, 1)
    out[..., :3] /= np.maximum(out[..., 3:4], 1e-4)
    return out

def recut(img, size):
    # flat-ink vector lettering exported small: scale it up, then cut the edges again to one pixel of
    # antialiasing at the new size, as if it had been exported there
    out = resize_rgba(img, size, Image.LANCZOS)
    k = size[0] / img.width
    out[..., 3] = np.clip((out[..., 3] - 0.5) * k + 0.5, 0, 1)
    return out

def over(dst, src):
    a = src[..., 3:4]
    rgb = src[..., :3] * a + dst[..., :3] * dst[..., 3:4] * (1 - a)
    al = a + dst[..., 3:4] * (1 - a)
    return np.dstack([rgb / np.maximum(al, 1e-4), al])

# the heat picture (breath) is continuous tone, not line art: lossless it's 3.5x the crowd, so its colour goes lossy
# (no visible change at 88 over flat bands) and its alpha stays exact
LOSSY = {"e"}

def save8(a8, path, lossy=False):
    a = a8.astype(np.float32)
    a[..., :3] *= a[..., 3:4] / 255
    im = Image.fromarray((a + 0.5).astype(np.uint8), "RGBA")
    if lossy: im.save(path, quality=88, alpha_quality=100, method=6, exact=True)
    else: im.save(path, lossless=True, quality=100, method=6, exact=True)

def save(arr, path):
    save8((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8), path)

BACK = {("a", "cream"): ("art/art-a-map/art-cream-al3.png", "overlays/ov-back-A-cream-hi.png"),
        ("b", "black"): ("art/art-b-lines/art-black-al3.png", "overlays/ov-back-black.png"),
        ("c", "black"): ("art/art-crowd-tour/art-black.png", "overlays/ov-back-T-black-hi.png"),
        ("d", "cream"): ("art/art-d-map/art-cream.png", "overlays/ov-back-D-cream-hi.png"),
        ("e", "black"): ("art/art-e-breath/art-black.png", "overlays/ov-back-E-black-hi.png")}
pairs = [tuple(p.split("-")) for p in sys.argv[2].split(",")] if len(sys.argv) > 2 else list(BACK)
for d, tee in pairs:
    art, ov = BACK[(d, tee)]
    b = resize_rgba(Image.open(art), (BW, BH))
    if ov:
        o = Image.open(ov)
        # lettering exported at print size or above is simply area-averaged; exported small, it's recut
        b = over(b, resize_rgba(o, (BW, BH)) if o.width >= BW else recut(o, (BW, BH)))
    b8 = knockout((np.clip(b, 0, 1) * 255 + 0.5).astype(np.uint8), tee)
    save8(b8, f"{OUT}/print-back-{d}-{tee}{'-full' if FULL else ''}.webp", d in LOSSY)
if FULL: sys.exit()

# chest: again.. in four scripts, rebuilt at 4x from the Figma export (the old one was these lines at 1x)
hi = np.array(Image.open("overlays/hi/front-B-black.png").convert("RGB")).astype(np.float32)
bg = hi[5, 5]
INK = {"black": [(241, 231, 208), (76, 102, 245)], "cream": [(29, 28, 26), (44, 70, 190)]}
src_inks = np.array(INK["black"], np.float32)
# per pixel: which ink, and how much of it over the background
dist = np.stack([np.linalg.norm(hi - c, axis=-1) for c in src_inks])
which = dist.argmin(0)
span = np.linalg.norm(src_inks - bg, axis=-1)[which]
alpha = np.clip(np.linalg.norm(hi - bg, axis=-1) / span, 0, 1)
LINES = [((138, 333, 535, 1160), (0, 0)), ((374, 563, 120, 744), (2, 59)), ((610, 811, 121, 591), (2, 118)), ((860, 1112, 120, 570), (2, 181))]
for tee in ("black", "cream"):
    inks = np.array(INK[tee], np.float32) / 255
    out = np.zeros((976, 632, 4), np.float32)
    for (y0, y1, x0, x1), (ox, oy) in LINES:
        X, Y = ox * 4, oy * 4
        h, w = min(y1 - y0, 976 - Y), min(x1 - x0, 632 - X)
        out[Y:Y + h, X:X + w, :3] = inks[which[y0:y0 + h, x0:x0 + w]]
        out[Y:Y + h, X:X + w, 3] = alpha[y0:y0 + h, x0:x0 + w]
    save(out, f"{OUT}/print-front-{tee}.webp")
print("prints ok")
