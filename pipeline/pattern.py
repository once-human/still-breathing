# Qikink UC22 Unisex Oversized Classic, size M, flat-lay pattern (cm).
# Published: chest 44 in (flat width 55.9), length 29 in (73.7 HPS to hem), shoulder 20 in (50.8 seam to seam).
# Not published, standard oversized drop-shoulder values until a real sample is measured:
#   neck width 19.6, front drop 9.5, back drop 2.5, rib 2.0, sleeve length 22, sleeve opening 20 flat,
#   armhole 25 straight, shoulder slope 3.2, sleeve angle 15 deg below the shoulder line.
# Other sizes: SIZE=<XS..2XL> in the environment grades the body from the published chart; the neck,
# sleeve and rib stay the same (they are not graded on this blank).
import math, os
CHART = {"XS": (40, 27, 18), "S": (42, 28, 19), "M": (44, 29, 20), "L": (46, 30, 21), "XL": (48, 31, 22), "2XL": (50, 32, 23)}  # chest, length, shoulder (in)
SIZE_NAME = os.environ.get("SIZE", "M")
_c, _l, _s = CHART[SIZE_NAME]
SIZE = {"chest": _c * 2.54 / 2, "length": _l * 2.54, "shoulder": _s * 2.54}
NECK_W, FRONT_DROP, BACK_DROP, RIB = 9.8, 9.5, 2.5, 2.0
SLOPE, ARMHOLE, SLEEVE_LEN, SLEEVE_OPEN, SLEEVE_ANG = 3.2, 25.0, 22.0, 20.0, 15.0
L = SIZE["length"]; HC = SIZE["chest"] / 2; HS = SIZE["shoulder"] / 2
def lerp(a, b, t): return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
def seg(a, b, step):
    n = max(1, round(math.dist(a, b) / step)); return [lerp(a, b, k / n) for k in range(n)]
def key_points():
    sp = (HS, L - SLOPE)                                                # shoulder seam point (drop shoulder)
    a = math.radians(-SLEEVE_ANG - math.degrees(math.atan2(SLOPE, HS - NECK_W)))
    st = (sp[0] + SLEEVE_LEN * math.cos(a), sp[1] + SLEEVE_LEN * math.sin(a))   # sleeve top corner
    sb = (st[0] + SLEEVE_OPEN * math.sin(a), st[1] - SLEEVE_OPEN * math.cos(a))  # sleeve bottom corner
    ua = (HC, sp[1] - ARMHOLE)                                          # underarm / armhole bottom
    return sp, st, sb, ua
def half_outline(front, step=1.0):
    drop = FRONT_DROP if front else BACK_DROP
    sp, st, sb, ua = key_points(); out = []
    n = max(8, round((NECK_W + drop) * 1.2 / step))
    for k in range(n):
        t = k / n * math.pi / 2; out.append(((NECK_W * math.sin(t), L - drop * math.cos(t)), "neck"))
    out += [(p, "shoulder") for p in seg((NECK_W, L), sp, step)]
    out += [(p, "sleevetop") for p in seg(sp, st, step)]
    out += [(p, "sleevehem") for p in seg(st, sb, step)]
    # sleeve underside meets the body at the underarm with a 3 cm round
    c = (ua[0] + 3, ua[1] - 3); r = 3
    out += [(p, "underarm") for p in seg(sb, (ua[0] + 3, ua[1]), step)]
    m = max(2, round(math.pi / 2 * r / step))
    out += [((c[0] + r * math.cos(math.pi / 2 + math.pi / 2 * k / m), c[1] + r * math.sin(math.pi / 2 + math.pi / 2 * k / m)), "underarm") for k in range(m)]
    out += [(p, "side") for p in seg((ua[0], ua[1] - 3), (HC, 0), step)]
    out += [(p, "hem") for p in seg((HC, 0), (0, 0), step)]
    return out
def outline(front, step=1.0):
    r = half_outline(front, step); left = [((-p[0], p[1]), t) for p, t in reversed(r)]
    pts, counts = [], {}
    for side, half in (("R", r), ("L", left)):
        for p, t in half:
            key = (t, side); i = counts.get(key, 0); counts[key] = i + 1; pts.append((p, t, side, i))
    clean = []
    for q in pts:
        if clean and math.dist(clean[-1][0], q[0]) < 1e-6: continue
        clean.append(q)
    if math.dist(clean[0][0], clean[-1][0]) < 1e-6: clean.pop()
    return clean
SEWN = {"shoulder", "sleevetop", "underarm", "side"}
# Texture atlas: one 110 x 86 cm cell per panel, anchored at the neck (the high shoulder point sits at NECK_Y
# for every size), so the prints stay where they are printed whatever the length of the body below them.
PANEL_W, PANEL_H, NECK_Y = 110.0, 86.0, 82.0
def ay(y): return y - L + NECK_Y          # pattern y (from the hem) -> atlas y
