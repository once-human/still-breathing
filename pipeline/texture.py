# Panel atlas (left = front panel, right = back panel) at 40 px/cm:
#   atlas-<d>-<tee>.png  colour + print     inkmask-<d>-<tee>.png  where ink sits
#   detail.png           height map: stitching, rib collar, hem folds (same for every design)
import sys, math
from PIL import Image, ImageDraw
from pattern import PANEL_W, PANEL_H, NECK_Y, NECK_W, FRONT_DROP, BACK_DROP, RIB, L, HC, key_points, ay, SIZE_NAME
PX = 40
W, H = int(PANEL_W * PX), int(PANEL_H * PX)
def to_px(x, y, panel): return ((panel * PANEL_W + (x if panel == 0 else -x) + PANEL_W / 2) * PX, (PANEL_H - ay(y)) * PX)
def build_detail():
    img = Image.new("L", (W * 2, H), 128); d = ImageDraw.Draw(img)
    sp, st, sb, ua = key_points()
    def poly(points, panel, fill, width, dash=None):
        pts = [to_px(x, y, panel) for x, y in points]
        if not dash: d.line(pts, fill=fill, width=width, joint="curve"); return
        on, off = dash; acc = 0; draw = True
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            L0 = math.hypot(x1 - x0, y1 - y0); s = 0
            while s < L0:
                take = min((on if draw else off) - acc, L0 - s); t0, t1 = s / L0, (s + take) / L0
                if draw: d.line([(x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0), (x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1)], fill=fill, width=width)
                s += take; acc += take
                if acc >= (on if draw else off): acc = 0; draw = not draw
    def offset_line(a, b, dist, n=60):
        dx, dy = b[0] - a[0], b[1] - a[1]; l = math.hypot(dx, dy); nx, ny = -dy / l * dist, dx / l * dist
        return [(a[0] + dx * k / n + nx, a[1] + dy * k / n + ny) for k in range(n + 1)]
    stitch = (0.32 * PX, 0.12 * PX)  # 3.2 mm stitches, 1.2 mm gaps
    for panel, drop in ((0, FRONT_DROP), (1, BACK_DROP)):
        for sgn in (1, -1):
            m = lambda pts: [(sgn * x, y) for x, y in pts]
            # double-needle hem: fold ridge + two stitch rows
            d.rectangle([to_px(-HC, 2.4, panel)[0] if panel == 0 else to_px(HC, 2.4, panel)[0], to_px(0, 2.4, panel)[1], to_px(HC, 0, panel)[0] if panel == 0 else to_px(-HC, 0, panel)[0], to_px(0, 0, panel)[1]], fill=140)
            for yy in (1.9, 2.5): poly(m([(-HC + 0.3, yy), (HC - 0.3, yy)]), panel, 96, 2, stitch)
            # sleeve hem rows, parallel to the opening
            for off in (1.9, 2.5): poly(m(offset_line(st, sb, off)), panel, 96, 2, stitch)
            # drop-shoulder armhole seam (welded in the kimono cut, so drawn as seam + cover stitch)
            arm = [(sp[0] + (ua[0] - sp[0]) * t + math.sin(math.pi * t) * 1.2, sp[1] + (ua[1] - sp[1]) * t) for t in [k / 40 for k in range(41)]]
            poly(m(arm), panel, 100, 3)
            poly(m([(x - 0.5, y) for x, y in arm]), panel, 96, 2, stitch)
            # shoulder tape stitch
            poly(m(offset_line((NECK_W, L), sp, -0.5)), panel, 96, 2, stitch)
            # side seam ridge
            poly(m([(HC - 0.15, ua[1] - 3), (HC - 0.15, 0)]), panel, 112, 3)
        # rib collar: 2 cm band of 1x1 rib (ridges run across the band), then the joining seam and top stitch
        cx, cy = 0, L
        for k in range(0, 2400):
            t = k / 2399 * math.pi
            a = (NECK_W * math.cos(t), L - drop * math.sin(t))
            nxv, nyv = (math.cos(t) / NECK_W, math.sin(t) / drop); nl = math.hypot(nxv, nyv); nxv, nyv = nxv / nl, -nyv / nl
            if k % 3 == 0:
                b = (a[0] + nxv * RIB, a[1] + nyv * RIB)
                d.line([to_px(*a, panel), to_px(*b, panel)], fill=150 if (k // 3) % 2 else 110, width=2)
        ring = lambda off: [(NECK_W * math.cos(t) + math.cos(t) * off, L - drop * math.sin(t) - math.sin(t) * off) for t in [k / 200 * math.pi for k in range(201)]]
        poly(ring(RIB), panel, 90, 3)
        poly(ring(RIB + 0.35), panel, 96, 2, stitch)
    return img
if __name__ == "__main__":
    if sys.argv[1] == "detail":
        build_detail().save(f"detail-{SIZE_NAME}.png"); print("detail ok", SIZE_NAME); sys.exit()
    design, tee = sys.argv[1], sys.argv[2]
    import os
    HERE = os.path.dirname(os.path.abspath(__file__))
    ROOT = os.path.join(HERE, "art")          # flat artwork from the Figma file
    OV = os.path.join(HERE, "overlays")       # lettering overlays exported from Figma
    # Mumbai (A map, B crowd): art from the Figma file plus a lettering overlay.
    # C, the tour crowd: art from art-crowd-tour/gen.py plus its lettering exported from Figma at print size.
    # D, the Bengaluru map: art from art-d-map/gen.py plus its lettering exported from Figma at print size.
    # E, breath for the tour: art from art/breath (crowd.py on a runner, then post.py) plus its lettering (art/breath/letter.py).
    art = {"A": "art-a-map", "B": "art-b-lines", "C": "art-crowd-tour", "D": "art-d-map", "E": "art-e-breath"}[design]
    TEE = {"black": (21, 21, 21), "cream": (255, 250, 231)}[tee]
    atlas = Image.new("RGBA", (W * 2, H), TEE + (255,)); mask = Image.new("L", (W * 2, H), 0)
    def place(img, cx_cm, top_cm, w_cm, panel):
        # knockout: halos drawn in the tee colour are not ink. On the real print they are holes in the ink
        # that show the fabric, so clear them (and anything that close to the fabric colour) from the file
        import numpy as np
        a = np.array(img); d = np.abs(a[..., :3].astype(int) - np.array(TEE)).sum(-1)
        HALO = {"black": (21, 21, 21), "cream": (236, 227, 206)}[tee]      # halo fill used in the Figma file
        d2 = np.abs(a[..., :3].astype(int) - np.array(HALO)).sum(-1)
        a[..., 3] = np.where((d < 24) | (d2 < 24), 0, a[..., 3]); img = Image.fromarray(a)
        w = int(w_cm * PX); h = int(img.height * w / img.width); im = img.resize((w, h), Image.LANCZOS)
        x = int(panel * W + (cx_cm + PANEL_W / 2) * PX) - w // 2; y = int((PANEL_H - top_cm) * PX)
        atlas.alpha_composite(im, (x, y)); mask.paste(im.split()[3], (x, y), im.split()[3])
    if design in "AB":
        back = Image.open(f"{ROOT}/{art}/art-{tee}-al3.png").convert("RGBA").resize((1200, 1600), Image.LANCZOS)
        back.alpha_composite(Image.open(f"{OV}/ov-back-{tee}.png").convert("RGBA"))
    else:
        back = Image.open(f"{ROOT}/{art}/art-{tee}.png").convert("RGBA")
        back.alpha_composite(Image.open(f"{OV}/ov-back-{'T' if design == 'C' else design}-{tee}-hi.png").convert("RGBA"))
        back = back.resize((1524, 2032), Image.BOX)
    # back: the whole printable area. The blank takes up to 16 x 20 in; the art is 3:4, so it fills the height:
    # 15 x 20 in (38.1 x 50.8 cm), its top 9.5 cm under the high shoulder point (just clear of the collar rib)
    place(back, 0, NECK_Y - 9.5, 38.1, 1)
    # front: again.. in four scripts, stacked, on the wearer's left chest at chest height (top 15 cm under the
    # shoulder point, so the block centres on the chest line), its inner edge 4 cm off the centre front
    W_FRONT = 10.5
    place(Image.open(f"{OV}/ov-front-{tee}.png").convert("RGBA"), 4 + W_FRONT / 2, NECK_Y - 15, W_FRONT, 0)
    atlas.convert("RGB").save(f"atlas-{design}-{tee}.png"); mask.save(f"inkmask-{design}-{tee}.png"); print("ok", atlas.size)
