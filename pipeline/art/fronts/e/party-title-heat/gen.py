# python3 gen.py : the party back's title "i am a party" in its own lettering (art/wordmark.py: Shantell Sans, set
# straight) with the warm word's colours (fronts/all/11b): cream letters inside an orange ring and a violet ring, like
# the heat picture's isotherms, then the usual black knockout halo. Writes back.png (the whole back, art + notes +
# this title, on the shirt black) and title.png (the overlay) next to this file. A try, for the owner to see.
import os, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); PIPE = os.path.join(HERE, "..", "..", "..", "..")
sys.path.insert(0, os.path.join(PIPE, "art"))
import wordmark as W

CREAM, ORANGE, VIOLET, BLACK = (241, 231, 208), (242, 124, 36), (107, 36, 153), (21, 21, 21)
ORANGE_W, VIOLET_W, DRIFT = 0.32, 0.32, 0.10   # ring widths and the violet's drift down-right, in letter strokes (as 11b)


def grow(a, r):
    """a round dilation of a bool mask by r px: the mask shifted round a disk, kept where any copy lands"""
    out = a.copy(); r = int(round(r))
    for dy in range(-r, r + 1):
        dx = int((r * r - dy * dy) ** 0.5)
        row = np.zeros_like(a)
        if dy >= 0: row[dy:] = a[:a.shape[0] - dy]
        else: row[:dy] = a[-dy:]
        for sx in range(-dx, dx + 1):   # the row's span, as a running max over its width
            if sx >= 0: out[:, sx:] |= row[:, :row.shape[1] - sx]
            else: out[:, :sx] |= row[:, -sx:]
    return out


def shift(a, dx, dy):
    o = np.zeros_like(a); h, w = a.shape
    o[max(dy, 0):h + min(dy, 0), max(dx, 0):w + min(dx, 0)] = a[max(-dy, 0):h - max(dy, 0), max(-dx, 0):w - max(dx, 0)]
    return o


word, box, ink, _ = W.PRINTS["e"]
x0, y0, x1, y1 = [v * W.K for v in box]
m = W.word_mask(word, 400)
m = W.word_mask(word, 400 * min((x1 - x0) * 0.95 / m.width, (y1 - y0) * 0.95 / m.height))
# the letter stroke: how many 1 px erosions it takes to empty the letters, twice
e, half = m.copy(), 0
while e.getbbox(): e = e.filter(__import__("PIL.ImageFilter", fromlist=["MinFilter"]).MinFilter(3)); half += 1
stroke = 2 * half; print("stroke", stroke, "px")
ro, rv, dv = ORANGE_W * stroke, VIOLET_W * stroke, int(round(DRIFT * stroke))
hr = ink["hr"] * W.K
pad = int(ro + rv + abs(dv) + hr + 6)
L = np.zeros((m.height + 2 * pad, m.width + 2 * pad), bool)
L[pad:pad + m.height, pad:pad + m.width] = np.asarray(m) > 127
O = grow(L, ro)
V = O | shift(grow(O, rv), dv, dv)
H = grow(V, hr)
rgba = np.zeros(L.shape + (4,), np.uint8)
for mask, col in ((H, BLACK), (V, VIOLET), (O, ORANGE), (L, CREAM)):
    rgba[mask] = col + (255,)
x, y = int((x0 + x1 - m.width) / 2) - pad, int((y0 + y1 - m.height) / 2) - pad
ov = Image.new("RGBA", (1200 * W.K, 1600 * W.K), (0, 0, 0, 0))
ov.alpha_composite(Image.fromarray(rgba, "RGBA"), (x, y))
ov.alpha_composite(Image.open(os.path.join(PIPE, "overlays", "notes", "back-e.png")).convert("RGBA"))
ov.save(os.path.join(HERE, "title.png"), optimize=True)
back = Image.new("RGBA", ov.size, BLACK + (255,))
art = Image.open(os.path.join(PIPE, "art", "art-e-breath", "art-black.png")).convert("RGBA").resize(ov.size, Image.LANCZOS)
back.alpha_composite(art); del art
back.alpha_composite(ov)
back.convert("RGB").resize((1200, 1600), Image.LANCZOS).save(os.path.join(HERE, "back.png"))
back.convert("RGB").crop((x - 40, y - 40, x + rgba.shape[1] + 40, y + rgba.shape[0] + 40)).save(os.path.join(HERE, "title-crop.png"))
print("saved")
