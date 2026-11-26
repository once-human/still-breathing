"""
letters.py: the wordmarks drawn by hand, letter by letter, with the toolkit's pen.

A monoline lowercase, rounded like the cream hand-lettering on the back ("i am a party"): every letter is a few
strokes through control points in x-height units (baseline y = 0, up is negative), drawn with pressure, wobble and
a soft lift-off. No font is traced. Only the letters the wordmarks need: again.. / fred again.. / actual life, the
digits of 16° and 20°.

    import letters
    marks = letters.write(art, 'again..', x, y, xh=16, w=2.6, layer='cream')
    # marks: one dict per character: {'ch', 'x0', 'x1', 'dot' (centre of a dot, if it has one)}
"""
import math


def arc(cx, cy, rx, ry, t0, t1, n=9):
    """points on an ellipse from t0 to t1 degrees (counter-clockwise, as on paper: y up is negative)"""
    return [(cx + rx * math.cos(math.radians(t0 + (t1 - t0) * i / (n - 1))),
             cy - ry * math.sin(math.radians(t0 + (t1 - t0) * i / (n - 1)))) for i in range(n)]


BOWL = arc(0.42, -0.5, 0.41, 0.5, 38, 352, 11)          # the a/d/g bowl, opened at the top right
G = {
    'a': ([BOWL, [(0.83, -1.02), (0.83, -0.5), (0.84, 0.0)]], 0.84, None),
    'd': ([BOWL, [(0.83, -1.76), (0.83, -0.8), (0.84, 0.0)]], 0.84, None),
    'g': ([BOWL, [(0.83, -1.02), (0.83, -0.4), (0.83, 0.18), (0.78, 0.46), (0.58, 0.64), (0.32, 0.65), (0.1, 0.52)]], 0.84, None),
    'b': ([[(0.0, -1.76), (0.0, -0.8), (0.0, 0.0)], arc(0.42, -0.5, 0.41, 0.5, 168, -170, 11)], 0.84, None),
    'm': ([[(0.0, -1.02), (0.0, -0.5), (0.0, 0.0)],
           [(0.0, -0.62), (0.1, -0.9), (0.28, -1.0), (0.46, -0.92), (0.54, -0.66), (0.55, -0.3), (0.55, 0.0)],
           [(0.55, -0.62), (0.65, -0.9), (0.83, -1.0), (1.01, -0.92), (1.09, -0.66), (1.1, -0.3), (1.1, 0.0)]], 1.1, None),
    ',': ([[(0.12, -0.1), (0.1, 0.1), (0.0, 0.3)]], 0.14, None),
    'c': ([arc(0.42, -0.5, 0.41, 0.5, 42, 322, 10)], 0.78, None),
    'e': ([[(0.04, -0.5), (0.42, -0.51), (0.79, -0.5), (0.75, -0.78), (0.55, -0.97), (0.32, -1.0), (0.1, -0.86),
            (0.0, -0.52), (0.07, -0.17), (0.3, -0.01), (0.56, -0.02), (0.76, -0.16)]], 0.8, None),
    'i': ([[(0.06, -1.0), (0.06, -0.5), (0.06, 0.0)]], 0.12, (0.06, -1.42)),
    'l': ([[(0.06, -1.76), (0.06, -0.8), (0.07, 0.0)]], 0.13, None),
    'n': ([[(0.0, -1.02), (0.0, -0.5), (0.0, 0.0)],
           [(0.0, -0.6), (0.14, -0.88), (0.38, -1.0), (0.62, -0.95), (0.75, -0.72), (0.77, -0.4), (0.77, 0.0)]], 0.77, None),
    'u': ([[(0.0, -1.02), (0.0, -0.42), (0.07, -0.14), (0.25, 0.0), (0.49, 0.0), (0.68, -0.18), (0.76, -0.5)],
           [(0.77, -1.02), (0.77, -0.5), (0.78, 0.0)]], 0.78, None),
    'r': ([[(0.0, -1.02), (0.0, -0.5), (0.0, 0.0)], [(0.0, -0.58), (0.12, -0.86), (0.32, -1.0), (0.56, -0.98)]], 0.56, None),
    'f': ([[(0.22, 0.0), (0.22, -0.7), (0.23, -1.3), (0.31, -1.62), (0.48, -1.76), (0.7, -1.72)],
           [(0.0, -1.0), (0.3, -1.01), (0.58, -1.0)]], 0.6, None),
    't': ([[(0.22, -1.44), (0.22, -0.7), (0.23, -0.22), (0.31, -0.04), (0.48, 0.0), (0.64, -0.08)],
           [(0.0, -1.0), (0.3, -1.01), (0.58, -1.0)]], 0.62, None),
    '.': ([], 0.14, (0.07, -0.08)),
    ' ': ([], 0.36, None),
    '1': ([[(0.0, -0.98), (0.16, -1.14), (0.32, -1.32), (0.32, -0.66), (0.32, 0.0)]], 0.34, None),
    '2': ([[(0.04, -1.04), (0.2, -1.27), (0.46, -1.32), (0.64, -1.13), (0.61, -0.84), (0.36, -0.46), (0.02, 0.0)],
           [(0.0, 0.0), (0.36, -0.01), (0.72, 0.0)]], 0.72, None),
    '6': ([[(0.62, -1.24), (0.4, -1.32), (0.16, -1.12), (0.03, -0.66), (0.05, -0.24), (0.27, -0.01), (0.52, -0.03),
            (0.66, -0.28), (0.6, -0.58), (0.36, -0.72), (0.12, -0.6), (0.04, -0.42)]], 0.68, None),
    '0': ([arc(0.34, -0.66, 0.34, 0.66, 100, 470, 13)], 0.68, None),
    '°': ([arc(0.3, -1.08, 0.29, 0.29, 80, 450, 10)], 0.6, None),
}


def width(text, xh, w, track=0.16, sx=1.0):
    """the drawn width of text in mm (w: the widest stroke; sx: the letters' width scale)"""
    return sum(G[c][1] * xh * sx + w + track * xh for c in text) - track * xh


def write(art, text, x, y, xh, w, layer, rng=None, track=0.16, skip='', dot_r=None, wob=None, trem=None,
          rot_j=1.4, base_j=0.025, size_j=0.03, a0=0.5, a1=0.8, pv=0.1, slant=0.0, sizes=None, lay=None, space_w=None, sx=1.0, pad=0.0, rise=0.0):
    """draw text with its left edge at x and its baseline at y (mm). xh: x-height (mm), w: stroke (mm).
    skip: characters whose strokes AND dots are left out (their places are still returned, so a version can draw
    its own dots). lay: a separate rng for the layout (size, baseline, tilt), so several passes of one word (bands,
    shadows) share their letters' places while each pass gets its own hand. space_w: the stroke width the spacing
    allows for (the widest pass). Returns one dict per character."""
    rng = rng or art.rng
    lay = lay or rng
    sw = space_w or w
    wob = xh * 0.011 if wob is None else wob
    trem = xh * 0.008 if trem is None else trem
    dot_r = dot_r or w * 0.78
    out = []
    cx = x + sw / 2
    for k, ch in enumerate(text):
        strokes, adv, dot = G[ch]
        s = xh * (sizes[k] if sizes else 1.0) * (1 + lay.uniform(-size_j, size_j))
        by = y + lay.uniform(-base_j, base_j) * xh - rise * (cx - x)
        a = math.radians(lay.uniform(-rot_j, rot_j))
        ca, sa = math.cos(a), math.sin(a)
        ox = cx + adv * s * sx / 2

        def T(p, adv=adv, s=s, ox=ox, by=by, ca=ca, sa=sa):
            u, v = (p[0] - adv / 2) * s * sx, p[1] * s
            u -= v * slant
            return (ox + u * ca - v * sa, by + u * sa + v * ca)
        rec = {'ch': ch, 'x0': cx - sw / 2, 'x1': cx + adv * s * sx + sw / 2, 'base': by, 'T': T}
        if dot:
            rec['dot'] = T(dot)
        if ch not in skip:
            for st in strokes:
                pts = [T(p) for p in st]
                art.line(pts, w, layer=layer, rng=rng, wob=wob, trem=trem, a0=a0, a1=a1, pv=pv)
                if pad:                    # a fingertip presses before it moves: a fatter round start
                    art.dot(pts[0][0], pts[0][1], w * pad / 2, layer=layer, rng=rng)
            if dot:
                dx, dy = rec['dot']
                art.dot(dx, dy, dot_r, layer=layer, rng=rng)
        out.append(rec)
        cx += adv * s * sx + sw + track * xh
    return out
