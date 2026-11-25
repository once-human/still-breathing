# the mirror ball render (discoball.py) cut into the shirt's flat inks. Every tile gets one flat tone, from the mean of
# its own reflection: cream for the tiles that blaze, warm greys down to a dark grey, the rest the shirt's own black
# (knocked out to fabric by printtex/texture), and so is the grout between them.
#   python3 pipeline/art/breath/discoball_ink.py <render.png> <out.png> <px>   (reads <render>-id.png beside it)
import sys, numpy as np
from PIL import Image
src, out, px = sys.argv[1], sys.argv[2], int(sys.argv[3])
beauty = np.asarray(Image.open(src).convert("RGBA").resize((px, px), Image.BOX)).astype(np.float32) / 255
idp = np.asarray(Image.open(src.replace(".png", "-id.png")).convert("RGB").resize((px, px), Image.NEAREST)).astype(np.int32)
tid = idp[..., 0] + idp[..., 1] * 256                       # 0 is grout or empty
inside = beauty[..., 3] > 0.5
# the grout stays the shirt: the gaps between the mirrors are what make it read as tiles
n = tid.max() + 1
cnt = np.bincount(tid.ravel(), minlength=n).astype(np.float32) + 1e-6
mean = np.stack([np.bincount(tid.ravel(), beauty[..., c].ravel(), n) / cnt for c in range(3)], 1)
lum = mean.mean(1); coolness = mean[:, 2] / np.maximum(mean[:, 0], 1e-3)
# no two real mirror tiles sit at quite the same angle: a small tilt per tile, so neighbours rarely share a tone
lum = lum + np.random.default_rng(12).normal(0, 0.06, n)
TONES = [(0.82, (241, 231, 208)), (0.66, (212, 205, 190)), (0.52, (178, 172, 160)), (0.39, (140, 135, 127)),
         (0.27, (104, 101, 97)), (0.16, (70, 68, 66))]
DARK, BLUE = np.array((21, 21, 21), np.float32), np.array((76, 102, 245), np.float32)
col = np.tile(DARK, (n, 1))
for t, c in reversed(TONES): col[lum > t] = c
col[0] = DARK
rgb = col[tid].round().clip(0, 255).astype(np.uint8)
alpha = (inside * 255).astype(np.uint8)
o = Image.fromarray(rgb).convert("RGBA"); o.putalpha(Image.fromarray(alpha)); o.save(out); print("ink ok", out, n - 1, "tiles")
