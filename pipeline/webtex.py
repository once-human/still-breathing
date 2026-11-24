# python3 webtex.py <outdir> [design-colour pairs, default B-black,A-cream] : web textures for the viewer and the in-browser path tracer
#   color-<d>-<tee>.jpg  base colour (sRGB)    orm-<d>-<tee>.png  R=1 (AO lives in the mesh) G=roughness B=ink
#   normal-<size>.png  stitches/rib/hems normal (hems and seams move with the size)  knit-normal.png  jersey loops
import sys, numpy as np
from PIL import Image
from pattern import CHART, PANEL_W, PANEL_H
# each shirt has one colour: B (crowd) is black, A (map) is off white
OUT = sys.argv[1]; PAIRS = [p.split("-") for p in (sys.argv[2] if len(sys.argv) > 2 else "B-black,A-cream").split(",")]; W = 4096; H = round(W * PANEL_H / (2 * PANEL_W))
def normal_from_height(h, strength):
    gy, gx = np.gradient(h.astype(np.float32) / 255.0)
    n = np.dstack([-gx * strength, gy * strength, np.ones_like(gx)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    return Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8))
for size in CHART:
    det = Image.open(f"detail-{size}.png").resize((W, H), Image.LANCZOS)
    normal_from_height(np.array(det), 6.0).save(f"{OUT}/normal-{size}.png")
normal_from_height(np.array(Image.open("knit.png")), 3.0).save(f"{OUT}/knit-normal.png")
ao = np.full((H, W), 255, np.uint8)
for d, tee in PAIRS:
    dl = d.lower()
    Image.open(f"atlas-{d}-{tee}.png").convert("RGB").resize((W, H), Image.LANCZOS).save(f"{OUT}/color-{dl}-{tee}.jpg", quality=90)
    ink = np.array(Image.open(f"inkmask-{d}-{tee}.png").convert("L").resize((W, H), Image.LANCZOS)).astype(np.float32) / 255
    rough = (0.92 - 0.32 * ink) * 255
    Image.fromarray(np.dstack([ao, rough.astype(np.uint8), (ink * 255).astype(np.uint8)])).save(f"{OUT}/orm-{dl}-{tee}.png")
print("webtex ok", W, H)
