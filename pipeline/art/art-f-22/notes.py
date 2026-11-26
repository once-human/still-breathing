# python3 art/art-f-22/notes.py : the notes and the line for 05 (22°), in the hand the Figma notes use
# (Gochi Hand for notes, Gaegu for the line, cream / blue ink with a dark edge, small drawn arrows).
# Writes overlays/notes/back-f.png (3600 x 4800); art/wordmark.py then lays the title under it.
import math, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); PIPE = os.path.join(HERE, "..", "..")
K = 3                                   # print px per frame unit (1200 x 1600)
CREAM, BLUE, EDGE = (241, 231, 208), (76, 102, 245), (21, 21, 21)
NOTE = ImageFont.truetype(os.path.join(PIPE, "fonts", "GochiHand-Regular.ttf"), 30 * K)
LINE = ImageFont.truetype(os.path.join(PIPE, "fonts", "Gaegu-Bold.ttf"), 46 * K)

# text, anchor point (units), text anchor, tilt (deg), arrow from (units) -> to (units), arrow bend
NOTES = [
    ("who needs an umbrella", (60, 1345), "ls", -2, (170, 1310), (175, 1240), 0.3),
    ("nobody's going home yet", (1165, 1435), "rs", -2, (1010, 1398), (930, 1325), 0.3),
    ("coffee's still on", (1170, 1065), "rs", 3, (1050, 1040), (1010, 975), 0.35),
    ("last train from madavara", (1170, 405), "rs", -2, (975, 372), (880, 318), -0.3),
]
LINE_TEXT, LINE_AT = "bengaluru . 1:42 am . 22°c", (600, 1540)

def layer():
    return Image.new("L", (1200 * K, 1600 * K), 0)

def text_mask(txt, font, at, anchor, tilt):
    m = layer(); x, y = at[0] * K, at[1] * K
    ImageDraw.Draw(m).text((x, y), txt, font=font, fill=255, anchor=anchor)
    return m.rotate(tilt, resample=Image.BICUBIC, center=(x, y)) if tilt else m

def arrow_mask(a, b, bend):
    m = layer(); d = ImageDraw.Draw(m)
    (x0, y0), (x1, y1) = [(p[0] * K, p[1] * K) for p in (a, b)]
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2; nx, ny = -(y1 - y0), x1 - x0
    cx, cy = mx + nx * bend, my + ny * bend
    pts = [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1, (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1)
           for t in [i / 40 for i in range(41)]]
    w = 3 * K
    d.line(pts, fill=255, width=w, joint="curve")
    ang = math.atan2(pts[-1][1] - pts[-4][1], pts[-1][0] - pts[-4][0]); L = 13 * K
    for s in (2.6, -2.6):
        d.line([pts[-1], (pts[-1][0] + L * math.cos(ang + s), pts[-1][1] + L * math.sin(ang + s))], fill=255, width=w)
    for p in (pts[0], pts[-1]):
        d.ellipse((p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2), fill=255)
    return m

def grow(m, r):
    return m.filter(ImageFilter.MaxFilter(2 * r + 1))

def ink(m, col):
    return Image.merge("RGBA", [Image.new("L", m.size, c) for c in col] + [m.point(lambda v: 255 if v > 110 else 0)])

out = Image.new("RGBA", (1200 * K, 1600 * K), (0, 0, 0, 0))
cream = layer()
for txt, at, anc, tilt, a, b, bend in NOTES:
    cream.paste(255, (0, 0), text_mask(txt, NOTE, at, anc, tilt)); cream.paste(255, (0, 0), arrow_mask(a, b, bend))
# the line's font has no degree sign: the text is set with a gap there and the ring drawn by hand
pre, post = LINE_TEXT.split("°")
GAP = "\u2009\u2009"
blue = text_mask(pre + GAP + post, LINE, LINE_AT, "ms", 0)
x0 = LINE_AT[0] * K - LINE.getlength(pre + GAP + post) / 2 + LINE.getlength(pre)
gw = LINE.getlength(GAP); r = max(gw * 0.42, 14); cx, cy = x0 + gw / 2, LINE_AT[1] * K - 46 * K * 0.62
ImageDraw.Draw(blue).ellipse((cx - r, cy - r, cx + r, cy + r), outline=255, width=11)
both = layer(); both.paste(255, (0, 0), cream); both.paste(255, (0, 0), blue)
out.alpha_composite(ink(grow(both, 14), EDGE))
out.alpha_composite(ink(blue, BLUE)); out.alpha_composite(ink(cream, CREAM))
out.save(os.path.join(PIPE, "overlays", "notes", "back-f.png"), optimize=True)
print("notes f ok")
