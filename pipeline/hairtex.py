# python3 hairtex.py <out-hair.webp> male|female
# The strands the hair cards (cards.py) are made of: our own, drawn here one strand at a time (no photo, no scan).
# 16 strips side by side, 64 x 1024 each; every strip is one card's worth of hair, its roots at the top, tips at
# the bottom (the cards run their v from root to tip). Each strand a thin line, a little wavy, drifting, tapering to
# its tip, coming in softly at its root; laid one over another, the later ones on top.
#   R  how bright the strand is (lighter on top of the pile, darker under it; the viewer multiplies the hair's colour)
#   G  how far along its strand the texel is (0 root, 1 tip)
#   B  which strand (a random number per strand)
#   A  how much of the texel the strands cover
# Strips 0-9 the main cards (hers: long sleek hair, dense, thinning only toward the card's sides; his: a short crop,
# strands gathered into a few tufts toward their tips), 10-15 sparse ones (a few strands, for the hairline and the
# loose hairs over the top). The texels no strand reaches keep the strip's mean colour, so nothing dark bleeds in
# from the empty parts as the picture is filtered down.
import sys
import numpy as np
from PIL import Image

OUT, SEX = sys.argv[1], sys.argv[2]
SHE = SEX == "female"
W, H, NS = 1024, 1024, 16
SW = W // NS
rng = np.random.default_rng(1618 if SHE else 175)


def sm(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def strip(kind):
    P = np.zeros((H, SW, 3)); A = np.zeros((H, SW))          # premultiplied colour, coverage
    if kind == "sleek":   n, root, tip, wid, wav, clumps = 190, (0.0, 0.07), (0.9, 1.0), (0.9, 1.5), 0.5, 0
    elif kind == "crop":  n, root, tip, wid, wav, clumps = 95, (0.0, 0.14), (0.45, 0.97), (1.0, 1.7), 0.35, 4
    elif kind == "wisp":  n, root, tip, wid, wav, clumps = 24, (0.0, 0.3), (0.55, 1.0), (0.8, 1.2), 1.4, 0
    else:                 n, root, tip, wid, wav, clumps = 18, (0.0, 0.3), (0.35, 0.8), (0.9, 1.3), 0.6, 0   # short sparse
    cl = 4 + rng.uniform(0, SW - 8, clumps) if clumps else None
    for s in range(n):
        y0, y1 = rng.uniform(*root) * H, rng.uniform(*tip) * H
        if y1 - y0 < 40: continue
        rows = np.arange(int(y0), min(H, int(np.ceil(y1))))
        t = np.clip((rows + 0.5 - y0) / (y1 - y0), 0, 1)
        # across the strip: thick in the middle, thinning to the sides, never cut by the strip's edge
        x0 = SW / 2 + (SW / 2 - 4) * np.clip(rng.normal(0, 0.42), -1, 1)
        xc = x0 + rng.normal(0, 2.2) * t + wav * np.sin(2 * np.pi * (rng.uniform(0.6, 2.2) * t + rng.uniform(0, 1))) \
            + 0.4 * wav * np.sin(2 * np.pi * (rng.uniform(3, 6) * t + rng.uniform(0, 1)))
        if cl is not None:                                   # gathered into its tuft toward the tip
            c = cl[np.argmin(np.abs(cl - x0))]
            xc = xc + (c - xc) * 0.7 * t ** 1.6
        xc = np.clip(xc, 2.5, SW - 3.5)
        w0 = rng.uniform(*wid)
        wpx = w0 * (1 - 0.7 * sm(0.55, 1.0, t))
        fade = sm(0.0, 0.05, t) * (1 - sm(0.93, 1.0, t))
        # brighter on top of the pile; a little lighter along it, slowly
        b = rng.uniform(0.5, 0.82) + 0.22 * s / n
        bv = b * (1 + 0.1 * np.sin(2 * np.pi * (rng.uniform(0.5, 1.5) * t + rng.uniform(0, 1))))
        sid = rng.uniform()
        base = np.floor(xc).astype(int)
        for dc in range(-2, 3):
            col = base + dc
            ok = (col >= 0) & (col < SW)
            d = np.abs(col + 0.5 - xc)
            cov = np.clip(wpx / 2 + 0.5 - d, 0, np.minimum(1.0, wpx)) * fade
            r, c_, cv = rows[ok], col[ok], cov[ok]
            val = np.stack([bv[ok], t[ok], np.full(ok.sum(), sid)], 1)
            P[r, c_] = P[r, c_] * (1 - cv[:, None]) + val * cv[:, None]
            A[r, c_] = A[r, c_] * (1 - cv) + cv
    C = np.where(A[..., None] > 1e-4, P / np.maximum(A[..., None], 1e-4), 0)
    mean = (C * A[..., None]).sum((0, 1)) / max(A.sum(), 1e-4)
    C = np.where(A[..., None] > 1e-3, C, mean)
    return np.concatenate([C, A[..., None]], 2)


main = "sleek" if SHE else "crop"
img = np.concatenate([strip(main if k < 10 else ("wisp" if SHE else "short")) for k in range(NS)], 1)
q = np.clip(np.round(img * 255), 0, 255).astype(np.uint8)
Image.fromarray(q, "RGBA").save(OUT, "WEBP", quality=90, exact=True, method=6)
print("hair strands", OUT, "coverage %.2f" % img[..., 3].mean(), flush=True)
