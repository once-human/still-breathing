"""
script.py: lowercase lettering drawn with the pen, letter by letter (no font): the hand that lettered the wordmark.
Glyphs are strokes in x-height units (x-height = 1, baseline y = 0, up is negative), drawn with hand.Art.line, so
every letter wobbles, swells and lifts like a marker. Only the letters the wordmarks need.
"""
import math

G = {   # letter: (advance, [strokes]) ; a stroke is a list of control points
    'a': (1.0, [[(0.80, -0.78), (0.56, -0.99), (0.24, -0.93), (0.04, -0.58), (0.08, -0.16), (0.34, 0.01), (0.62, -0.16), (0.79, -0.56)],
                [(0.82, -1.0), (0.80, -0.35), (0.86, -0.02), (0.98, -0.06)]]),
    'g': (1.0, [[(0.80, -0.78), (0.56, -0.99), (0.24, -0.93), (0.04, -0.58), (0.08, -0.16), (0.34, 0.01), (0.62, -0.16), (0.79, -0.56)],
                [(0.82, -1.0), (0.81, 0.18), (0.70, 0.58), (0.40, 0.74), (0.10, 0.56)]]),
    'd': (1.0, [[(0.80, -0.78), (0.56, -0.99), (0.24, -0.93), (0.04, -0.58), (0.08, -0.16), (0.34, 0.01), (0.62, -0.16), (0.79, -0.56)],
                [(0.83, -1.78), (0.81, -0.35), (0.87, -0.02), (0.98, -0.06)]]),
    'i': (0.44, [[(0.14, -0.96), (0.13, -0.18), (0.24, -0.01), (0.34, -0.05)]]),
    'n': (1.0, [[(0.08, -1.0), (0.08, 0.0)],
                [(0.09, -0.6), (0.30, -0.94), (0.58, -0.99), (0.76, -0.74), (0.78, -0.18), (0.86, -0.01), (0.96, -0.05)]]),
    'f': (0.6, [[(0.64, -1.62), (0.46, -1.77), (0.28, -1.66), (0.21, -1.25), (0.20, 0.0)],
                [(0.0, -0.95), (0.52, -0.98)]]),
    'r': (0.68, [[(0.08, -1.0), (0.08, 0.0)],
                 [(0.09, -0.58), (0.26, -0.91), (0.48, -1.0), (0.64, -0.92)]]),
    'e': (0.88, [[(0.08, -0.5), (0.74, -0.54), (0.69, -0.84), (0.43, -1.0), (0.14, -0.86), (0.03, -0.5), (0.12, -0.12), (0.42, 0.01), (0.74, -0.16)]]),
    'c': (0.84, [[(0.76, -0.80), (0.46, -1.0), (0.14, -0.86), (0.03, -0.5), (0.12, -0.12), (0.43, 0.01), (0.76, -0.16)]]),
    't': (0.64, [[(0.26, -1.48), (0.25, -0.2), (0.38, -0.01), (0.60, -0.08)],
                 [(0.0, -0.95), (0.56, -0.98)]]),
    'u': (1.0, [[(0.07, -1.0), (0.07, -0.36), (0.20, -0.03), (0.46, 0.0), (0.70, -0.24), (0.76, -0.72)],
                [(0.79, -1.0), (0.79, -0.16), (0.87, -0.01), (0.97, -0.05)]]),
    'l': (0.44, [[(0.13, -1.78), (0.12, -0.18), (0.24, -0.01), (0.34, -0.05)]]),
    ' ': (0.48, []),
    # figures, 1.4 x-heights tall
    '8': (0.80, [[(0.37, -0.74), (0.13, -0.95), (0.18, -1.27), (0.40, -1.40), (0.62, -1.27), (0.60, -0.96), (0.37, -0.74),
                  (0.08, -0.48), (0.10, -0.12), (0.38, 0.01), (0.66, -0.12), (0.68, -0.46), (0.40, -0.72)]]),
    '9': (0.80, [[(0.64, -1.04), (0.44, -1.40), (0.16, -1.32), (0.08, -1.02), (0.24, -0.76), (0.50, -0.80), (0.66, -1.06)],
                 [(0.67, -1.30), (0.62, -0.42), (0.44, 0.0)]]),
}
DOT_R = 0.14     # the full stop's radius, x-heights


def write(art, text, x, y, xh, w, layer, dot_layer=None, slant=0.10, rng=None, kern=0.0, dot_r=DOT_R, dots=None, wob=0.022):
    """letter `text` with its baseline at (x, y) mm, x-height xh mm, stroke w mm. Returns (end x, list of dot centres).
    `dots` collects the centres of '.' so a caller can do something else with them (dots=False: don't draw them)."""
    rng = rng or art.rng
    cx = x
    centres = []
    for ch in text:
        if ch == '.':
            px, py = cx + 0.16 * xh, y - dot_r * xh
            centres.append((px, py))
            if dots is not False:
                art.dot(px, py, dot_r * xh * rng.uniform(0.95, 1.05), layer=dot_layer or layer, rng=rng)
            cx += 0.40 * xh + kern * xh
            continue
        adv, strokes = G[ch]
        for s in strokes:
            pts = [(cx + (u - v * slant) * xh, y + v * xh) for u, v in s]
            if len(pts) == 2:
                pts = [pts[0], ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2), pts[1]]
            art.line(pts, w, layer=layer, wob=wob * xh, trem=0.012 * xh, a0=0.9, a1=1.6, pv=0.14, rng=rng)
        if ch == 'i':   # the tittle
            art.dot(cx + (0.15 + 1.42 * slant) * xh, y - 1.42 * xh, dot_r * 0.85 * xh, layer=layer, rng=rng)
        cx += (adv + kern) * xh * rng.uniform(0.98, 1.02)
    return cx, centres


def width(text, xh, kern=0.0):
    return sum((0.40 if c == '.' else G[c][0]) + kern for c in text) * xh
