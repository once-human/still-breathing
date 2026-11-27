# python3 printfiles.py <outdir> : the print partner's files, one PNG per placement, at 300 dpi.
#   back-<d>-<tee>.png   13.5 x 18 in, 4050 x 5400: the whole back box, the art where the site shows it
#   front-<d>-<tee>.png  the front's ink only, at its printed size (10.5 cm wide on the chest; 05's wristband 40 cm long)
#   report.json          sizes, how each front was made, and where each front sits (cm from the centre line and shoulder)
# Transparent where there is no ink (halos drawn in the shirt colour are holes too), straight alpha, sRGB, 300 dpi.
# The backs are the very masters the site's viewer is made from, resampled to 300 dpi: nothing on the shirt can differ
# from the page. So are the fronts, scaled to print size with their hard edges cut again there. (Drawing the fronts again
# at print size was tried: the hand's jitter follows the drawing size, so up to a quarter of the ink moved. Not used.)
# Heavy (several 4050 x 5400 float arrays): run it on the farm (printfiles.yml), not on an 8 GB laptop.
# python3 printfiles.py <outdir> fronts : the fronts only (small, fine on the laptop).
import json, os, sys
import numpy as np
from PIL import Image, ImageCms
# from printtex.py (which runs on import), kept the same: the knockout, the resampling, the backs and the lettering
TEE = {"black": (21, 21, 21), "cream": (255, 250, 231)}
HALO = {"black": (21, 21, 21), "cream": (236, 227, 206)}   # halo fill used in the Figma file: holes in the ink

def knockout(a, tee):
    # halos drawn in the tee colour are not ink; on the real print they're holes that show the fabric
    d = np.abs(a[..., :3].astype(int) - np.array(TEE[tee])).sum(-1)
    d2 = np.abs(a[..., :3].astype(int) - np.array(HALO[tee])).sum(-1)
    a[..., 3] = np.where((d < 24) | (d2 < 24), 0, a[..., 3])
    return a

def resize_rgba(img, size, f=Image.BOX):
    # premultiplied, so edges don't pick up the colour of transparent pixels. Shrinking line art: an area
    # average (each pixel is the ink that falls in it), as sharp as it gets with no ringing, and it packs 4x
    # smaller than a windowed-sinc resample, whose ripples make every pixel unique
    a = np.array(img.convert("RGBA")).astype(np.float32) / 255
    a[..., :3] *= a[..., 3:4]
    ch = [np.array(Image.fromarray(a[..., i]).resize(size, f)) for i in range(4)]
    out = np.clip(np.dstack(ch), 0, 1)
    out[..., :3] /= np.maximum(out[..., 3:4], 1e-4)
    return out

def recut(img, size):
    # flat-ink vector lettering exported small: scale it up, then cut the edges again to one pixel of
    # antialiasing at the new size, as if it had been exported there
    out = resize_rgba(img, size, Image.LANCZOS)
    k = size[0] / img.width
    out[..., 3] = np.clip((out[..., 3] - 0.5) * k + 0.5, 0, 1)
    return out

def over(dst, src):
    a = src[..., 3:4]
    rgb = src[..., :3] * a + dst[..., :3] * dst[..., 3:4] * (1 - a)
    al = a + dst[..., 3:4] * (1 - a)
    return np.dstack([rgb / np.maximum(al, 1e-4), al])

BACK = {("a", "cream"): ("art/art-a-map/art-cream-al3.png", "overlays/ov-back-A-cream-hi.png"),
        ("b", "black"): ("art/art-b-lines/art-black-al3.png", "overlays/ov-back-black.png"),
        ("c", "black"): ("art/art-crowd-tour/art-black.png", "overlays/ov-back-T-black-hi.png"),
        ("d", "cream"): ("art/art-d-map/art-cream.png", "overlays/ov-back-D-cream-hi.png"),
        ("e", "black"): ("art/art-e-breath/art-black.png", "overlays/ov-back-E-black-hi.png"),
        ("f", "black"): ("art/art-f-22/art-black.png", "overlays/ov-back-F-black-hi.png")}
INK = {"black": [(241, 231, 208), (76, 102, 245)], "cream": [(29, 28, 26), (44, 70, 190)]}
LINES = [((138, 333, 535, 1160), (0, 0)), ((374, 563, 120, 744), (2, 59)), ((610, 811, 121, 591), (2, 118)), ((860, 1112, 120, 570), (2, 181))]
from fronts import FRONTS, LETTERING

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
DPI, CM = 300, 300 / 2.54                 # px per inch, px per cm
BW, BH = 13.5 * DPI, 18 * DPI             # the back box
BW, BH = int(BW), int(BH)
SRGB = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
SHOP = ("c", "e", "a", "d", "f")          # the five on sale, and their shirt colour
SHIRT = {"c": "black", "e": "black", "a": "cream", "d": "cream", "f": "black"}
report = {}


def write(arr, name):
    """float RGBA (straight) -> 8-bit PNG, halos knocked out, clear pixels zeroed, 300 dpi, sRGB"""
    a8 = (np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)
    a8 = knockout(a8, name.split("-")[2])
    a8[a8[..., 3] == 0] = 0
    p = os.path.join(OUT, name + ".png")
    Image.fromarray(a8, "RGBA").save(p, dpi=(DPI, DPI), icc_profile=SRGB, optimize=True)
    h, w = a8.shape[:2]
    report[name] = dict(px=[w, h], inches=[round(w / DPI, 2), round(h / DPI, 2)], cm=[round(w / CM, 1), round(h / CM, 1)],
                        mb=round(os.path.getsize(p) / 2 ** 20, 1))
    print(name, report[name], flush=True)


def ink(img, cut=8):
    a = np.array(img.getchannel("A"))
    return img.crop(Image.fromarray(np.where(a >= cut, 255, 0).astype(np.uint8)).getbbox())


def turn(img, deg):
    """rotate in premultiplied space so the clear surround never bleeds into the edge"""
    a = np.array(img.convert("RGBA")).astype(np.float32) / 255
    a[..., :3] *= a[..., 3:4]
    ch = [np.array(Image.fromarray(a[..., i]).rotate(deg, Image.BICUBIC, expand=True)) for i in range(4)]
    out = np.clip(np.dstack(ch), 0, 1)
    out[..., :3] /= np.maximum(out[..., 3:4], 1e-4)
    return Image.fromarray((out * 255 + 0.5).astype(np.uint8), "RGBA")


# ---- backs: the masters, at 300 dpi
for d in ([] if sys.argv[2:] == ["fronts"] else SHOP):
    art, ov = BACK[(d, SHIRT[d])]
    src = Image.open(art)
    b = resize_rgba(src, (BW, BH), Image.BOX if src.width >= BW else Image.LANCZOS)
    o = Image.open(ov)
    b = over(b, resize_rgba(o, (BW, BH)) if o.width >= BW else recut(o, (BW, BH)))   # the lettering: vector, cut sharp again
    write(b, f"back-{d}-{SHIRT[d]}")
    del b

# ---- fronts
place = {}
for d in SHOP:
    f_file, cx, top, w_cm = FRONTS[d]
    if f_file is None:
        # c: again.. in four scripts, from the 60 px/cm Figma lettering (printtex's chest), cut sharp again at print size
        hi = np.array(Image.open("overlays/hi/front-B-black.png").convert("RGB")).astype(np.float32)
        bg = hi[5, 5]
        src_inks = np.array(INK["black"], np.float32)
        dist = np.stack([np.linalg.norm(hi - c, axis=-1) for c in src_inks])
        which = dist.argmin(0)
        alpha = np.clip(np.linalg.norm(hi - bg, axis=-1) / np.linalg.norm(src_inks - bg, axis=-1)[which], 0, 1)
        # an edge pixel (part ink, part ground) can sit nearer the blue than the cream by colour alone, which
        # outlines the cream letters in blue dots: edge pixels take the ink of the nearest solid pixel instead
        lab = np.where(alpha > 0.85, which, -1)
        for _ in range(8):
            if not (lab[alpha > 0] < 0).any(): break
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                nb = np.roll(lab, (dy, dx), (0, 1))
                lab = np.where((lab < 0) & (nb >= 0), nb, lab)
        which = np.where(lab >= 0, lab, which)
        inks = np.array(INK[SHIRT[d]], np.float32) / 255
        canvas = np.zeros((976, 632, 4), np.float32)
        for (y0, y1, x0, x1), (ox, oy) in LINES:
            X, Y = ox * 4, oy * 4
            h, w = min(y1 - y0, 976 - Y), min(x1 - x0, 632 - X)
            canvas[Y:Y + h, X:X + w, :3] = inks[which[y0:y0 + h, x0:x0 + w]]
            canvas[Y:Y + h, X:X + w, 3] = alpha[y0:y0 + h, x0:x0 + w]
        k = CM / 60
        c8 = Image.fromarray((canvas * 255 + 0.5).astype(np.uint8), "RGBA")
        bb = c8.getchannel("A").getbbox()
        big = recut(c8, (round(632 * k), round(976 * k)))
        x0, y0 = round(bb[0] * k), round(bb[1] * k)
        out = big[y0:round(bb[3] * k), x0:round(bb[2] * k)]
        left, top_ink = cx - w_cm / 2 + bb[0] / 60, top + bb[1] / 60
        write(out, f"front-{d}-{SHIRT[d]}")
        report[f"front-{d}-{SHIRT[d]}"]["match"] = "drawn from the 60 px/cm lettering, recut"
    else:
        # the master itself, exactly what the site shows. Its ink is flat with a hard (binary) edge, so it's scaled up
        # and the edge cut again at print size: one pixel of antialiasing at 300 dpi, the shapes exactly the master's
        tw = round(w_cm * CM)
        if d == "f":
            # the wristband: art-down.png is art-tight.png turned -95 deg with no smoothing. Turn the unturned art
            # here instead, already at print size, so its edges are cut once, cleanly
            tight = Image.open(os.path.join(os.path.dirname(f_file), "art-tight.png"))
            down = Image.open(f_file)
            k = tw / down.width                                  # print px per art px
            big = recut(tight, (round(tight.width * k), round(tight.height * k)))
            big = ink(turn(Image.fromarray((big * 255 + 0.5).astype(np.uint8), "RGBA"), -95))
            th = round(down.height * k)
            out = resize_rgba(big, (tw, th), Image.BOX)
            out[..., 3] = np.clip((out[..., 3] - 0.5) * 1.5 + 0.5, 0, 1)   # the turn softens the edge: cut it again
        else:
            master = ink(Image.open(f_file))
            th = round(master.height * tw / master.width)
            out = recut(master, (tw, th))
        left, top_ink = cx - w_cm / 2, top
        write(out, f"front-{d}-{SHIRT[d]}")
        report[f"front-{d}-{SHIRT[d]}"]["match"] = "the master, scaled to print size and its edge cut again"
    n = f"front-{d}-{SHIRT[d]}"
    place[n] = dict(left_edge_from_centre_cm=round(left, 2), top_from_shoulder_cm=round(top_ink, 2))

rp = os.path.join(OUT, "report.json")
old = json.load(open(rp)) if os.path.exists(rp) else {}
json.dump(dict(report={**old.get("report", {}), **report}, place=place), open(rp, "w"), indent=1)
print(json.dumps(place, indent=1))
print("print files ok")
