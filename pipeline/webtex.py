# python3 webtex.py <outdir> : web textures for the real-time viewer
#   color-<tee>.jpg  base colour (sRGB)        orm-<tee>.png  R=AO G=roughness B=ink (sheen off over ink)
#   normal.png       stitches/rib/hems normal  knit-normal.png  tileable jersey loops
import sys, numpy as np
from PIL import Image
OUT = sys.argv[1]; W = 4096; H = round(W * 3040 / 8000)
def normal_from_height(h, strength):
    gy, gx = np.gradient(h.astype(np.float32) / 255.0)
    n = np.dstack([-gx * strength, gy * strength, np.ones_like(gx)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    return Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8))
det = Image.open("detail.png").resize((W, H), Image.LANCZOS)
normal_from_height(np.array(det), 6.0).save(f"{OUT}/normal.png")
normal_from_height(np.array(Image.open("knit.png")), 3.0).save(f"{OUT}/knit-normal.png")
ao = np.array(Image.open(f"{OUT}/ao.png").convert("L").resize((W, H), Image.LANCZOS))
for tee in ("black", "cream"):
    Image.open(f"atlas-B-{tee}.png").convert("RGB").resize((W, H), Image.LANCZOS).save(f"{OUT}/color-{tee}.jpg", quality=90)
    ink = np.array(Image.open(f"inkmask-B-{tee}.png").convert("L").resize((W, H), Image.LANCZOS)).astype(np.float32) / 255
    rough = (0.92 - 0.32 * ink) * 255
    Image.fromarray(np.dstack([ao, rough.astype(np.uint8), (ink * 255).astype(np.uint8)])).save(f"{OUT}/orm-{tee}.png")
print("webtex ok", W, H)
