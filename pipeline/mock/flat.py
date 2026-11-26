# Flat 2D mockups of a front print on a size M black tee, at true scale (pattern.py's outline), for eyeballing.
# python3 mock/flat.py <out.jpg>
import os, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from pattern import outline, L, NECK_W, FRONT_DROP
PX, M = 22, 40                                    # px per cm, margin
TEE, BG, RIB = (24, 24, 24), (226, 222, 214), (40, 40, 40)
HERE = os.path.dirname(os.path.abspath(__file__)); PIPE = os.path.join(HERE, "..")
pts = [p for p, *_ in outline(True)]
xs = [p[0] for p in pts]; W = int((max(xs) - min(xs)) * PX) + 2 * M; H = int(L * PX) + 2 * M
def to(x, y_from_hsp): return (W / 2 + x * PX, M + y_from_hsp * PX)
def tee():
    im = Image.new("RGBA", (W, H), BG + (255,)); d = ImageDraw.Draw(im)
    d.polygon([to(x, L - y) for x, y in pts], fill=TEE)
    neck = [to(x, L - y) for x, y in pts if y > L - FRONT_DROP - 0.01 and abs(x) <= NECK_W + 0.01]
    return im, d
def put(im, file, cx, top, w, rot=0.0):
    a = Image.open(os.path.join(PIPE, file)).convert("RGBA")
    a = a.resize((int(w * PX), max(1, int(w * PX * a.height / a.width))), Image.LANCZOS)
    if rot: a = a.rotate(rot, resample=Image.BICUBIC, expand=True)
    x, y = to(cx, top); im.alpha_composite(a, (int(x - a.width / 2), int(y)))
def label(im, txt):
    ImageDraw.Draw(im).text((M, H - M + 6), txt, fill=(60, 60, 60))
from fronts import FRONTS
BOX = (-14 * 2.54 / 2, 11.5, 14 * 2.54, 18 * 2.54)   # the front print box: 35.6 x 45.7 cm from the collar seam
def box(im):
    d = ImageDraw.Draw(im); x0, y0 = to(BOX[0], BOX[1]); x1, y1 = to(BOX[0] + BOX[2], BOX[1] + BOX[3])
    for x in range(int(x0), int(x1), 24): d.line([(x, y0), (x + 12, y0)], fill=(90, 90, 90), width=2); d.line([(x, y1), (x + 12, y1)], fill=(90, 90, 90), width=2)
    for y in range(int(y0), int(y1), 24): d.line([(x0, y), (x0, y + 12)], fill=(90, 90, 90), width=2); d.line([(x1, y), (x1, y + 12)], fill=(90, 90, 90), width=2)
panels = []
for dsg in (sys.argv[2:] or ["c", "f"]):
    f_file, cx, top, w = FRONTS[dsg]
    im, d = tee(); box(im); put(im, f_file or "overlays/ov-front-black.png", cx, top, w)
    panels.append((im, f"{dsg}: front as printed; dashed: the front print box"))
out = Image.new("RGB", (W * len(panels), H + 30), BG)
for i, (p, t) in enumerate(panels):
    out.paste(p.convert("RGB"), (i * W, 0)); ImageDraw.Draw(out).text((i * W + M, H + 4), t, fill=(50, 50, 50))
out.save(sys.argv[1], quality=90); print(out.size)
