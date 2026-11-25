# 02 breath, part 3: the lettering, in the tour crowd's hand (its overlay is pipeline/overlays/ov-back-T-black-hi.png):
# the big word in Gaegu Bold, the tour line in the brand blue, notes in Gochi Hand with a drawn arrow to what they mean.
#   python3 pipeline/art/breath/letter.py [notes.json] [out.png]
# notes.json: [{"text": ..., "at": [x, y], "anchor": "la"|"ra"|"ma"..., "to": [x, y], "bow": 0.2}, ...] in 0..1 of the
# print, pointing at people in the picture (picked on the print made by post.py). Writes a 4500 x 6000 RGBA overlay
# the size of art-e-breath/art-black.png. Flat inks only; lines are at least 0.8 mm at print size.
import sys, os, json, math
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(HERE, "..", "..", "fonts")
NOTES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "notes.json")
# The shipped lettering (envelops me, 0.16.0) is drawn in the Figma file and exported to overlays/ov-back-E-black-hi.png;
# this sketch writes beside it, never over it
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "..", "overlays", "ov-back-E-black-sketch.png")
W, H = 4500, 6000                     # 15 x 20 in at 300 dpi: 11.8 px a millimetre
SS = 2                                # drawn at twice the size, then area-averaged: clean edges, one pixel of antialias
INK = (241, 231, 208, 255)            # the tour crowd's cream
BLUE = (76, 102, 245, 255)            # the brand blue on black

im = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
def font(name, px): return ImageFont.truetype(os.path.join(F, name), int(px * SS), layout_engine=ImageFont.Layout.RAQM)
def P(x, y): return (x * W * SS, y * H * SS)

def spaced(text, cx, y, f, fill, track):
    """a line with open tracking, centred on cx"""
    ws = [d.textlength(c, font=f) for c in text]; total = sum(ws) + track * SS * (len(text) - 1); x = cx - total / 2
    for c, w in zip(text, ws):
        d.text((x, y), c, font=f, fill=fill, anchor="ls"); x += w + track * SS

# ---------- the big word and the tour ----------
big = font("Gaegu-Bold.ttf", 820)
d.text(P(0.5, 0.155), "breath..", font=big, fill=INK, anchor="ms")
spaced("india . 12 . 2026", W * SS * 0.5, H * SS * 0.205, font("Gaegu-Bold.ttf", 190), BLUE, 8)

# ---------- notes, each with an arrow drawn like the crowd's: a light bow, an open head ----------
note = font("GochiHand-Regular.ttf", 96)
LW = 11 * SS                          # about 0.9 mm
def arrow(a, b, bow):
    (x0, y0), (x1, y1) = a, b
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2; dx, dy = x1 - x0, y1 - y0
    cx, cy = mx - dy * bow, my + dx * bow
    pts = [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1, (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1)
           for t in [k / 64 for k in range(65)]]
    d.line(pts, fill=INK, width=LW, joint="curve")
    for p in (pts[0], pts[-1]): d.ellipse((p[0] - LW / 2, p[1] - LW / 2, p[0] + LW / 2, p[1] + LW / 2), fill=INK)
    hx, hy = pts[-1]; tx, ty = pts[-6]; ang = math.atan2(hy - ty, hx - tx); L = 62 * SS
    for s in (-1, 1):
        e = (hx - L * math.cos(ang + s * 0.5), hy - L * math.sin(ang + s * 0.5))
        d.line([e, (hx, hy)], fill=INK, width=LW)
        d.ellipse((e[0] - LW / 2, e[1] - LW / 2, e[0] + LW / 2, e[1] + LW / 2), fill=INK)

for n in json.load(open(NOTES)):
    x, y = P(*n["at"]); anc = n.get("anchor", "la")
    d.text((x, y), n["text"], font=note, fill=INK, anchor=anc)
    if "to" in n:
        l, t, r, b = d.textbbox((x, y), n["text"], font=note, anchor=anc)
        tx, ty = P(*n["to"])
        # leave from the side of the words that faces the target, a little clear of them
        sx = r + 30 * SS if tx > r else l - 30 * SS if tx < l else (l + r) / 2
        sy = (t + b) / 2 if l - 30 * SS <= sx <= r + 30 * SS and (tx > r or tx < l) else (b + 30 * SS if ty > b else t - 30 * SS)
        arrow((sx, sy), (tx, ty), n.get("bow", 0.18))

im = im.resize((W, H), Image.BOX)
# a halo round every mark, in the shirt's own black: texture.py and printtex.py knock it out, so on the shirt it's a
# thin gap in the heat picture that lets the words read wherever they cross it (as the Figma halos do on the crowd)
from PIL import ImageFilter
a = im.split()[3].point(lambda v: 255 if v > 8 else 0).filter(ImageFilter.MaxFilter(29)).filter(ImageFilter.GaussianBlur(1.2))
halo = Image.new("RGBA", (W, H), (21, 21, 21, 0)); halo.putalpha(a); halo.alpha_composite(im); im = halo
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True); im.save(OUT); print("ok", OUT, im.size)
