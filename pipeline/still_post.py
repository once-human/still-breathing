# python3 still_post.py <frame.png> <frame.png.cam.json> <show.webp> <out.png>      (numpy, pillow)
# Lays the show in behind a turntable still rendered by render.py (SCENE=show, transparent film), the way the
# viewer's path tracer does it: each pixel looks the 360 degree picture up along its pinhole ray (the picture
# carries its own lens blur, so the aperture never blurs it again), u = 0.5 - atan2(x, z) / 2pi, v = 0 straight up
# in three's axes, through the same Khronos PBR Neutral view transform. The place stays put and the camera walks
# round it, so the ray needs no turn. Composited in display space over the straight-alpha frame, then 8 bits with
# a half-step dither so the dark hall never bands (no grain is added).
import sys, json
import numpy as np
from PIL import Image

FRAME, CAM, ENV, OUT = sys.argv[1:5]
fg = np.asarray(Image.open(FRAME).convert("RGBA"), np.float32) / 255
H, W, _ = fg.shape
cam = json.load(open(CAM))
pos, f, th = np.array(cam["pos"]), np.array(cam["f"]), cam["tanHalf"]

# pinhole rays in Blender's axes (z up), right = f x z, up = right x f (Blender's track-to, three's lookAt)
r = np.cross(f, [0, 0, 1]); r /= np.linalg.norm(r); u = np.cross(r, f)
qx = (np.arange(W) + 0.5) / W * 2 - 1
qy = 1 - (np.arange(H) + 0.5) / H * 2
d = f[None, None] + r[None, None] * (qx[None, :, None] * th * W / H) + u[None, None] * (qy[:, None, None] * th)
d /= np.linalg.norm(d, axis=-1, keepdims=True)
x3, y3, z3 = d[..., 0], d[..., 2], -d[..., 1]   # Blender (x, y, z) -> three (x, z, -y)
U = 0.5 - np.arctan2(x3, z3) / (2 * np.pi)
V = 0.5 - np.arcsin(np.clip(y3, -1, 1)) / np.pi

# bilinear, wrapping round in u (linear filter, no mips, as the GPU samples it), in linear light
env = np.asarray(Image.open(ENV).convert("RGB"), np.float32) / 255
env = np.where(env <= 0.04045, env / 12.92, ((env + 0.055) / 1.055) ** 2.4)
EH, EW, _ = env.shape
px, py = U * EW - 0.5, np.clip(V * EH - 0.5, 0, EH - 1)
x0, y0 = np.floor(px).astype(int), np.floor(py).astype(int)
tx, ty = (px - x0)[..., None], (py - y0)[..., None]
x0 %= EW; x1 = (x0 + 1) % EW; y1 = np.minimum(y0 + 1, EH - 1)
bg = (env[y0, x0] * (1 - tx) + env[y0, x1] * tx) * (1 - ty) + (env[y1, x0] * (1 - tx) + env[y1, x1] * tx) * ty

def neutral(c):   # Khronos PBR Neutral, as pt.wgsl.ts and Cycles' view transform
    start, desat = 0.8 - 0.04, 0.15
    x = c.min(axis=-1, keepdims=True)
    c = c - np.where(x < 0.08, x - 6.25 * x * x, 0.04)
    peak = c.max(axis=-1, keepdims=True)
    dd = 1 - start; npk = 1 - dd * dd / (peak + dd - start)
    g = 1 - 1 / (desat * (peak - npk) + 1)
    t = c * (npk / np.maximum(peak, 1e-6)); t = t * (1 - g) + npk * g
    return np.where(peak < start, c, t)

bg = np.clip(neutral(np.maximum(bg, 0)), 0, 1)
bg = np.where(bg <= 0.0031308, bg * 12.92, 1.055 * np.power(bg, 1 / 2.4) - 0.055)
a = fg[..., 3:]
img = fg[..., :3] * a + bg * (1 - a)
q = np.clip(np.floor(img * 255 + np.random.default_rng(7).uniform(0, 1, img.shape)), 0, 255).astype(np.uint8)
Image.fromarray(q, "RGB").save(OUT)
print("composited", OUT, W, "x", H)
