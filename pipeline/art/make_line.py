# 04 end of the line (Bengaluru, off white): the back print, drawn from scratch.
#   python3 art/make_line.py   ->  art/art-d-line/art-cream.png  (4500 x 6000, 15 x 20 in at 300 dpi, transparent)
# Namma Metro's Green Line, northbound from Majestic to Madavara, the last station, beside NICE Grounds on
# Tumakuru Road. Bengaluru is the last city of the tour; the show is the end of the line.
# Station order and names checked against the Green Line station list (Nov 2026).
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(HERE, "..", "fonts")
W, H = 4500, 6000
INK = (27, 27, 27, 255)            # near-black ink
GREEN = (0, 150, 72, 255)          # the Green Line's green, a touch deeper so it holds on off white
BLUE = (44, 70, 190, 255)          # the brand blue, used once
QUIET = (27, 27, 27, 150)

def brico(px, wght):
    f = ImageFont.truetype(f"{F}/BricolageGrotesque-Var.ttf", px, layout_engine=ImageFont.Layout.RAQM)
    f.set_variation_by_axes([wght]); return f
def kan(px, w="Medium"): return ImageFont.truetype(f"{F}/NotoSansKannada-{w}.ttf", px, layout_engine=ImageFont.Layout.RAQM)

# northbound, Majestic first; Mahalakshmi is the one that shares a name with the Mumbai show's ground
STATIONS = [
    ("ಮೆಜೆಸ್ಟಿಕ್", "majestic"), ("ಸಂಪಿಗೆ ರಸ್ತೆ", "sampige road"), ("ಶ್ರೀರಾಮಪುರ", "srirampura"),
    ("ಕುವೆಂಪು ರಸ್ತೆ", "kuvempu road"), ("ರಾಜಾಜಿನಗರ", "rajajinagar"), ("ಮಹಾಲಕ್ಷ್ಮಿ", "mahalakshmi"),
    ("ಸ್ಯಾಂಡಲ್ ಸೋಪ್ ಫ್ಯಾಕ್ಟರಿ", "sandal soap factory"), ("ಯಶವಂತಪುರ", "yeshwanthpur"),
    ("ಗೊರಗುಂಟೆಪಾಳ್ಯ", "goraguntepalya"), ("ಪೀಣ್ಯ", "peenya"), ("ಪೀಣ್ಯ ಇಂಡಸ್ಟ್ರಿ", "peenya industry"),
    ("ಜಾಲಹಳ್ಳಿ", "jalahalli"), ("ದಾಸರಹಳ್ಳಿ", "dasarahalli"), ("ನಾಗಸಂದ್ರ", "nagasandra"),
    ("ಮಂಜುನಾಥ ನಗರ", "manjunath nagar"), ("ಚಿಕ್ಕಬಿದರಕಲ್ಲು", "chikkabidarakallu"),
]
END = ("ಮಾದಾವರ", "madavara")

im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
M = 300                                   # outer margin
LX = 2000                                 # the line's centre: English reads in from the left, Kannada out to the right
LW = 150                                  # line weight (1.27 cm on the shirt)
GAP = 210                                 # line edge to text
TICK = 95

# ---- header: where and when, set like a route board ----
d.text((M, M - 60), "bengaluru", font=brico(560, 800), fill=INK)
d.text((M + 14, M + 600), "ಬೆಂಗಳೂರು", font=kan(250, "Bold"), fill=INK)
right = W - M
d.text((right, M + 720), "12 + 13 . 12 . 2026", font=brico(150, 600), fill=INK, anchor="rs")
d.text((right, M + 900), "green line, northbound", font=brico(110, 400), fill=QUIET, anchor="rs")
d.rectangle((M, 1360, W - M, 1360 + 14), fill=INK)          # rule under the header

# ---- the line ----
top, last, y_end = 1760, 4700, 5120
step = (last - top) / (len(STATIONS) - 1)
d.rectangle((LX - LW // 2, top - 120, LX + LW // 2, y_end), fill=GREEN)
# the line comes from further south: an open end of three short dashes above Majestic
for k in range(3):
    y = top - 170 - k * 85; d.rectangle((LX - LW // 2, y - 40, LX + LW // 2, y), fill=GREEN)
en_f, kn_f = brico(100, 400), kan(116, "Medium")
for i, (kn, en) in enumerate(STATIONS):
    y = int(top + i * step)
    d.rectangle((LX - LW // 2 - TICK, y - 20, LX + LW // 2 + TICK, y + 20), fill=GREEN)   # station bar
    d.text((LX - LW // 2 - GAP, y), en, font=en_f, fill=QUIET, anchor="rm")
    d.text((LX + LW // 2 + GAP, y), kn, font=kn_f, fill=INK, anchor="lm")
    if en == "mahalakshmi":   # shares its name with the Mumbai show's ground: two blue dots, like the front's ..
        x = LX + LW // 2 + GAP + d.textlength(kn, font=kn_f) + 70
        for j in range(2): d.ellipse((x + j * 58, y + 22, x + j * 58 + 38, y + 60), fill=BLUE)

# ---- the end: a terminal ring, the name both ways, big ----
R, RING = 250, 66
d.ellipse((LX - R, y_end - R, LX + R, y_end + R), fill=GREEN)
d.ellipse((LX - R + RING, y_end - R + RING, LX + R - RING, y_end + R - RING), fill=(0, 0, 0, 0))
d.ellipse((LX - 90, y_end - 90, LX + 90, y_end + 90), fill=INK)                      # the show
d.text((LX - R - 120, y_end), "madavara", font=brico(250, 800), fill=INK, anchor="rm")
d.text((LX + R + 120, y_end), END[0], font=kan(290, "Black"), fill=INK, anchor="lm")
d.text((LX - R - 120, y_end + 290), "nice grounds, tumakuru road", font=brico(96, 400), fill=QUIET, anchor="rm")
d.text((LX + R + 120, y_end + 300), "end of the line", font=brico(140, 600), fill=INK, anchor="lm")

out = os.path.join(HERE, "art-d-line"); os.makedirs(out, exist_ok=True)
im.save(os.path.join(out, "art-cream.png")); print("ok", im.size)
