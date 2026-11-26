# python3 art/wordmark.py : the lineup 01 titles (again.. / i am a party / mumbai / bengaluru / actual life), drawn by rules
#
# Each title is Shantell Sans (SemiBold, fully informal, no bounce): a marker hand, set straight. Every letter the
# same size on one level baseline, no tilt, one ink (the old per-letter jitter made an "a" jump up and a "g" drop).
# A knockout halo in the tee colour clears the art around the letters (thin on black, wider on the busy maps).
# The rhythm tables below are the knobs if a title ever needs a hand-set lean or bounce again; all are flat now.
# The notes and dates stay in the Figma file. Export them per print with the title group hidden
# (pipeline/overlays/notes/back-<d>.png, 3600 x 4800), then this script lays the title under them and writes the
# overlays texture.py / printtex.py read.
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); PIPE = os.path.join(HERE, "..")
FONT = os.path.join(PIPE, "fonts", "ShantellSans-Var.ttf")
AXES = dict(wght=600, INFM=100, BNCE=0, SPAC=0)
SIZE = [1.0, 1.0, 1.0, 1.0]
TILT = [0.0, 0.0, 0.0, 0.0]
LIFT = [0.0, 0.0, 0.0, 0.0]
DRIFT = 0.0
SLIP = (0.0, 0.0)   # a second, blue ink offset behind the letters: off
K = 3   # print px per Figma frame unit (frames are 1200 x 1600, prints 3600 x 4800)
BLACK = dict(ink=(241, 231, 208), blue=(76, 102, 245), halo=(21, 21, 21), hr=5)
CREAM = dict(ink=(34, 32, 29), blue=(44, 70, 190), halo=(255, 250, 231), hr=12)
# design: word, the old title group's box in frame units (x0, y0, x1, y1), inks, overlay file(s)
PRINTS = {
    "c": ("again..", (271, 52, 929, 395), BLACK, ["ov-back-T-black-hi.png"]),
    "e": ("i am a party", (169, 39, 1032, 292), BLACK, ["ov-back-E-black-hi.png"]),
    "a": ("mumbai", (303, 53, 1023, 367), CREAM, ["ov-back-A-cream-hi.png", "ov-back-cream.png"]),
    "d": ("bengaluru", (217, 1196, 971, 1485), CREAM, ["ov-back-D-cream-hi.png"]),
    "f": ("actual life", (236, 68, 964, 241), BLACK, ["ov-back-F-black-hi.png"]),
}

def font(px):
    f = ImageFont.truetype(FONT, max(1, int(round(px))))
    names = {"Weight": "wght", "Informality": "INFM", "Bounce": "BNCE", "Spacing": "SPAC"}
    f.set_variation_by_axes([AXES[names[a["name"].decode() if isinstance(a["name"], bytes) else a["name"]]] for a in f.get_variation_axes()])
    return f

def word_mask(word, px):
    f0 = font(px); asc, desc = f0.getmetrics()
    m = Image.new("L", (int(px * (len(word) + 1)), int((asc + desc) * 1.6)), 0)
    x, base = px * 0.3, m.height * 0.72
    for i, ch in enumerate(word):
        adv = f0.getlength(ch)
        if ch == " ":
            x += adv; continue
        s, t, l = SIZE[i % 4], TILT[i % 4], LIFT[i % 4]
        g = Image.new("L", (int(px * 2), int(px * 2)), 0)
        ImageDraw.Draw(g).text((px * 0.5, px * 1.4), ch, font=font(px * s), fill=255, anchor="ls")
        if t: g = g.rotate(t, resample=Image.BICUBIC, center=(px * 0.5 + adv / 2, px * 1.4))
        m.paste(255, (int(x - px * 0.5), int(base - px * 1.4 - l * px)), g)
        x += adv * s
    if DRIFT: m = m.rotate(DRIFT, resample=Image.BICUBIC, expand=True)
    return m.crop(m.getbbox())

def grow(mask, r, pad):
    h = Image.new("L", (mask.width + 2 * pad, mask.height + 2 * pad), 0); h.paste(mask, (pad, pad))
    while r > 0:
        st = min(r, 20); h = h.filter(ImageFilter.MaxFilter(2 * st + 1)); r -= st
    return h

def solid(mask, col):
    return Image.merge("RGBA", [Image.new("L", mask.size, c) for c in col] + [mask])

def title(d):
    word, box, ink, _ = PRINTS[d]
    x0, y0, x1, y1 = [v * K for v in box]
    m = word_mask(word, 400)
    m = word_mask(word, 400 * min((x1 - x0) * 0.95 / m.width, (y1 - y0) * 0.95 / m.height))
    x, y = int((x0 + x1 - m.width) / 2), int((y0 + y1 - m.height) / 2)
    ox, oy = int(SLIP[0] * m.height), int(SLIP[1] * m.height)
    r = ink["hr"] * K; pad = r + 3
    both = Image.new("L", (m.width + ox, m.height + oy), 0); both.paste(255, (0, 0), m); both.paste(255, (ox, oy), m)
    ov = Image.new("RGBA", (1200 * K, 1600 * K), (0, 0, 0, 0))
    ov.alpha_composite(solid(grow(both, r, pad), ink["halo"]), (x - pad, y - pad))
    if ox or oy: ov.alpha_composite(solid(m, ink["blue"]), (x + ox, y + oy))
    ov.alpha_composite(solid(m, ink["ink"]), (x, y))
    return ov

if __name__ == "__main__":
    import sys
    for d in sys.argv[1:] or PRINTS:
        ov = title(d)
        # the notes and dates sit over the title, as in the Figma file
        ov.alpha_composite(Image.open(os.path.join(PIPE, "overlays", "notes", f"back-{d}.png")).convert("RGBA"))
        for name in PRINTS[d][3]:
            out = ov if name.endswith("-hi.png") else ov.resize((1200, 1600), Image.LANCZOS)
            out.save(os.path.join(PIPE, "overlays", name), optimize=True)
        print("wordmark", d, PRINTS[d][0])
