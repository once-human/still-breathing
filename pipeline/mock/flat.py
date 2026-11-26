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
panels = []
W20, W0 = 13.3, 4.2
im, d = tee(); put(im, "art/fronts/c/05-wristband/trial/down-20.png", 10 + W20 / 2, 14.0, W20); panels.append((im, "G, the artist's: 30 cm, 20 deg off vertical drifting out, clasp up on the left chest"))
im, d = tee(); put(im, "art/fronts/c/05-wristband/trial/down-0.png", 12.0, 14.0, W0); panels.append((im, "H, yours: 30 cm, straight down from the left chest"))

out = Image.new("RGB", (W * len(panels), H + 30), BG)
for i, (p, t) in enumerate(panels):
    out.paste(p.convert("RGB"), (i * W, 0)); ImageDraw.Draw(out).text((i * W + M, H + 4), t, fill=(50, 50, 50))
out.save(sys.argv[1], quality=90); print(out.size)
