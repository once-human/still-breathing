# python3 pipeline/art/fronts/pair.py <shirt c|e|a|d> <front art.png> <placement.json> <out.png>
# A front design beside its shirt's own back, both flat on the blank (size M, laid flat, true scale), so every
# front version is judged the same way, paired with the back it will be printed with.
# placement.json: {"x_cm": centre of the art from the centre front (+ = wearer's left, the viewer's right),
#                  "top_cm": top of the art below the high shoulder point, "w_cm": printed width}
# Light on memory: 20 px per cm (about 2700 x 1600), the art shrunk as it is read.
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SHIRT, ART, PL, OUT = sys.argv[1:5]
TEE = {"c": "black", "e": "black", "a": "cream", "d": "cream"}[SHIRT]
GROUND = {"black": (21, 21, 21), "cream": (255, 250, 231)}[TEE]
BACK = {"c": ("pipeline/art/art-crowd-tour/art-black.png", "pipeline/overlays/ov-back-T-black-hi.png"),
        "e": ("pipeline/art/art-e-breath/art-black.png", "pipeline/overlays/ov-back-E-black-hi.png"),
        "a": ("pipeline/art/art-a-map/art-cream-al3.png", "pipeline/overlays/ov-back-cream.png"),
        "d": ("pipeline/art/art-d-map/art-cream.png", "pipeline/overlays/ov-back-D-cream-hi.png")}[SHIRT]

# the shirt laid flat, size M (sizes.json): chest across, length from the high shoulder point (HPS), dropped
# shoulder, a short wide sleeve; y runs up from the hem, cm
cm = json.load(open(os.path.join(ROOT, "public/tee/fred/sizes.json")))["sizes"]["M"]["cm"]
HPS, CH, SH = cm["length"], cm["chest_flat"] / 2, cm["shoulder"] / 2
NW, SL, SA = 9.8, 23.0, 27.0                          # half the neck's width; the sleeve's length and opening


def tee(drop):
    """the flat shirt's outline, its neck dropping `drop` cm at the centre"""
    sx, sy = SH + SL * 0.93, HPS - 4.0 - SL * 0.37   # the sleeve's top corner at the cuff
    side = [(NW, HPS), (SH, HPS - 4.0), (sx, sy), (sx + SA * 0.37, sy - SA * 0.93), (CH, HPS - 31.0), (CH, 0.0)]
    neck = [(NW * math.sin(t), HPS - drop * math.cos(t)) for t in (i * math.pi / 24 for i in range(1, 12))]
    return [(0.0, HPS - drop)] + neck + side + [(-x, y) for x, y in reversed(side)] + [(-x, y) for x, y in reversed(neck)]


PX, PAD = 20, 4                                       # px per cm; cm round each shirt
W_CM = 2 * (SH + SL * 0.93 + SA * 0.37) + 2 * PAD; H_CM = HPS + 2 * PAD
pic = Image.new("RGB", (int(2 * W_CM * PX), int(H_CM * PX)), (120, 120, 118) if TEE == "cream" else (196, 194, 188))


def panel(outline, k):
    """draw shirt k (0 front, 1 back); returns (x cm from the centre, d cm under the HPS) -> pixels"""
    ox = (k * W_CM + W_CM / 2) * PX; oy = (PAD + HPS) * PX
    ImageDraw.Draw(pic).polygon([(ox + x * PX, oy - y * PX) for x, y in outline], fill=GROUND)
    return lambda x, d: (ox + x * PX, oy - (HPS - d) * PX)


def put(img, at, cx, top, w):
    w_px = max(1, round(w * PX)); h_px = max(1, round(img.height * w_px / img.width))
    img = img.resize((w_px, h_px), Image.LANCZOS, reducing_gap=3.0)
    x, y = at(cx, top); pic.paste(img.convert("RGB"), (round(x - w_px / 2), round(y)), img.getchannel("A"))


front_at = panel(tee(9.5), 0); back_at = panel(tee(2.5), 1)
p = json.load(open(PL))
put(Image.open(ART).convert("RGBA"), front_at, p["x_cm"], p["top_cm"], p["w_cm"])   # wearer's left: the viewer's right
art, ov = (Image.open(os.path.join(ROOT, f)).convert("RGBA") for f in BACK)
if art.size != ov.size: ov = ov.resize(art.size, Image.LANCZOS)
art.alpha_composite(ov); del ov
a = np.asarray(art).copy(); a[..., 3] = np.where(np.abs(a[..., :3].astype(np.int16) - GROUND).sum(-1) < 24, 0, a[..., 3])
art = Image.fromarray(a); del a
put(art, back_at, 0, 9.5, 38.1)                       # the back: 15 x 20 in, 9.5 cm under the HPS (texture.py)
pic.save(OUT); print("saved", OUT, pic.size)
