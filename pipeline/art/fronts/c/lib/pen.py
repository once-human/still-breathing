"""
pen.py: the shared set-up for the 01 crowd fronts. Units are millimetres of print.

    import pen
    h, art = pen.boot(100, 120, seed=7, layers=('line', 'Y'))   # canvas in mm, then draw on art (units = mm)
    pen.word(art, 'line', 'again', 'bric', 14, x, y)           # lettering set from the lineup's fonts, worked by hand
    pen.save(art, __file__, order=('Y', 'line'), placement={...})

R=1 (draft): 4.7 px per mm, writes _draft/draft.png (+ crops at print size) next to gen.py.
Otherwise (final): 9.4 px per mm = 94 px per cm of print; writes art.png, preview.png (the art alone on a patch of
the tee's black), placement.json, then runs check.py verify.
The inks are the back's own (art-crowd-tour): cream line, marigold, green, blue on the black tee.
"""
import math, os, sys, random, subprocess, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FONTS = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', 'fonts'))
DRAFT = os.environ.get('R', '9.4') == '1'
PXMM = 4.7 if DRAFT else 9.4
TEE = '#151515'
PAL = {'line': '#F1E7D0', 'Y': '#F6B330', 'G': '#56B27C', 'B': '#4C66F5'}
SHIFT = {'line': (0, 0), 'Y': (0.34, 0.28), 'G': (-0.30, 0.33), 'B': (0.16, -0.14)}   # mm off register per screen
FONT = {
    'bric': 'BricolageGrotesque-Var.ttf',      # the lineup's wordmark face (again..)
    'note': 'GochiHand-Regular.ttf',           # the back's note hand
    'shan': 'ShantellSans-Var.ttf',            # a marker hand
    'gaegu': 'Gaegu-Bold.ttf',
    'deva': 'NotoSansDevanagari-Black.ttf',
    'devab': 'NotoSansDevanagari-Bold.ttf',
    'knda': 'NotoSansKannada-Black.ttf',
    'kndab': 'NotoSansKannada-Bold.ttf',
}
h = None


def boot(w_mm, h_mm, seed=1, layers=('line', 'Y', 'G', 'B')):
    """set the canvas (drawn in mm units) before hand.py is imported, return (hand module, Art)"""
    global h
    os.environ['R'] = str(PXMM)
    os.environ['UW'], os.environ['UH'] = str(int(w_mm)), str(int(h_mm))
    os.environ['MINW'] = '1.1'                        # the thinnest stroke: 1.1 mm (10 px at print)
    import hand as _h
    h = _h
    _h.margin.__defaults__ = (int(round(4.6 * PXMM)),)     # 4.6 mm off the canvas edge at any draft size
    return _h, _h.Art(seed, layers)


# ----------------------------------------------------------------- lettering
def font(name, size_mm, weight=None, axes=None):
    """a font at size_mm (the em, in mm of print) at canvas resolution. weight for the variable faces."""
    from PIL import ImageFont
    f = ImageFont.truetype(os.path.join(FONTS, FONT.get(name, name)), max(4, int(round(size_mm * PXMM))))
    if axes is not None:
        f.set_variation_by_axes(axes)
    elif weight is not None:
        n = len(f.get_variation_axes())
        f.set_variation_by_axes([weight] + [a['default'] for a in f.get_variation_axes()[1:]][:n - 1])
    return f


def glyph(f, txt, rot=0.0, lang=None, bold=0.0):
    """one glyph (or a shaped cluster) as an L mask turned by rot (radians, clockwise on the page), plus its pen origin
    (baseline-left) as an offset (vx, vy) in px from the unturned mask's middle, and the unturned size"""
    from PIL import Image, ImageDraw
    kw = {'anchor': 'ls'}
    if lang:
        kw['language'] = lang
    bb = f.getbbox(txt, **kw)
    pad = int(f.size * 0.3) + 4
    w, hh = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad
    m = Image.new('L', (w, hh), 0)
    ox, oy = pad - bb[0], pad - bb[1]
    ImageDraw.Draw(m).text((ox, oy), txt, font=f, fill=255, **kw)
    if bold > 0:                                      # a fatter pen: grow every stroke by `bold` mm on each side
        from PIL import ImageFilter
        k = 2 * int(round(bold * PXMM)) + 1
        m = m.filter(ImageFilter.MaxFilter(k)).filter(ImageFilter.GaussianBlur(k / 5)).point(lambda p: 255 if p > 127 else 0) if k > 2 else m
    if rot:
        m = m.rotate(math.degrees(-rot), resample=Image.BICUBIC, expand=True).point(lambda p: 255 if p > 120 else 0)
    return m, ox - w / 2, oy - hh / 2


def _put(art, layer, m, vx, vy, a, gx, gy, erase):
    """paste a turned glyph so that the point (vx, vy) px from its unturned middle lands on (gx, gy) px"""
    rx, ry = vx * math.cos(a) - vy * math.sin(a), vx * math.sin(a) + vy * math.cos(a)
    art.L[layer].paste(0 if erase else 255, (int(round(gx - m.width / 2 - rx)), int(round(gy - m.height / 2 - ry))), m)


def word(art, layer, txt, fname, size_mm, x, y, weight=None, axes=None, track=0.0, jit=0.035, turn=0.022,
         erase=False, rng=None, per_glyph=True, lang=None, align='left', rot=0.0, bold=0.0):
    """set txt with its baseline-left at (x, y) mm, then work it by hand: each glyph nudged off the baseline by up to
    jit*size and turned by up to `turn` radians. track: extra space between glyphs in mm. rot: the whole word's lean
    (radians, about its start). Returns the width in mm. erase=True cuts it OUT of the layer."""
    rng = rng or art.rng
    f = font(fname, size_mm, weight, axes)
    units = list(txt) if per_glyph else txt.split(' ')
    gap = '' if per_glyph else ' '
    kw = {'language': lang} if lang else {}
    # advances from prefixes, so kerning survives (in px)
    xs, acc = [], ''
    for i, u in enumerate(units):
        xs.append(f.getlength(acc, **kw) / PXMM + track * i)
        acc += u + (gap if i < len(units) - 1 else '')
    total = f.getlength(txt, **kw) / PXMM + track * (len(units) - 1)
    if align == 'centre':
        x -= total / 2 * math.cos(rot)
        y -= total / 2 * math.sin(rot)
    elif align == 'right':
        x -= total * math.cos(rot)
        y -= total * math.sin(rot)
    ca, sa = math.cos(rot), math.sin(rot)
    for u, dx in zip(units, xs):
        if not u.strip():
            continue
        dy = rng.gauss(0, jit * size_mm * 0.5)
        r = rot + rng.gauss(0, turn * 0.6)
        m, vx, vy = glyph(f, u, r, lang, bold)
        gx, gy = x + dx * ca - dy * sa, y + dx * sa + dy * ca
        _put(art, layer, m, vx, vy, r, gx * PXMM, gy * PXMM, erase)
    return total


def width(txt, fname, size_mm, weight=None, axes=None, track=0.0, lang=None):
    f = font(fname, size_mm, weight, axes)
    kw = {'language': lang} if lang else {}
    return f.getlength(txt, **kw) / PXMM + track * (len(txt) - 1)


def along(art, layer, txt, fname, size_mm, path, s0=0.0, weight=None, axes=None, track=0.0, jit=0.03, turn=0.02,
          erase=False, rng=None, lift=0.0, bold=0.0):
    """set txt along a polyline path (mm), starting s0 mm along it, each glyph's baseline on the path (lift mm off it,
    toward the path's left normal). Returns the arc length used."""
    rng = rng or art.rng
    f = font(fname, size_mm, weight, axes)
    s = h.cumlen(path)
    L = s[-1]

    def at(d):
        d = max(0.0, min(L - 1e-6, d))
        i = max(1, next(k for k in range(1, len(s)) if s[k] >= d))
        t = (d - s[i - 1]) / ((s[i] - s[i - 1]) or 1e-9)
        (x0, y0), (x1, y1) = path[i - 1], path[i]
        return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, math.atan2(y1 - y0, x1 - x0)
    pos, acc = s0, ''
    for i, ch in enumerate(txt):
        adv = (f.getlength(acc + ch) - f.getlength(acc)) / PXMM
        acc += ch
        if ch.strip():
            x, y, a = at(pos + adv / 2)
            a += rng.gauss(0, turn * 0.6)
            ln = lift + rng.gauss(0, jit * size_mm * 0.5)
            m, vx, vy = glyph(f, ch, a, bold=bold)
            nx, ny = math.sin(a), -math.cos(a)
            # the glyph's baseline middle goes on the path point
            _put(art, layer, m, vx + adv * PXMM / 2, vy, a, (x + nx * ln) * PXMM, (y + ny * ln) * PXMM, erase)
        pos += adv + track
    return pos - s0


# ----------------------------------------------------------------- out
def save(art, gen_file, order=('Y', 'G', 'B', 'line'), shifts=None, palette=None, crops=(), placement=None):
    """finish the inks (spread, register, knockout, clean), composite, write the draft or the final set"""
    from PIL import Image
    out_dir = os.path.dirname(os.path.abspath(gen_file))
    order = [k for k in order if k in art.L]
    inks = art.finish(order=order, shifts={k: v for k, v in (shifts or SHIFT).items() if k in art.L}, spread_amt=0.16)
    rgba = h.composite(inks, palette or PAL, order)
    del inks
    if DRAFT:
        dd = os.path.join(out_dir, '_draft')
        os.makedirs(dd, exist_ok=True)
        bg = Image.new('RGBA', rgba.size, h.hexrgb(TEE) + (255,))
        bg.alpha_composite(rgba)
        bg = bg.convert('RGB')
        s = min(1.0, 1000 / max(bg.size)) if max(bg.size) > 1000 else 1.0
        bg.resize((int(bg.width * s), int(bg.height * s)), Image.LANCZOS).save(os.path.join(dd, 'draft.png'))
        for i, (x, y) in enumerate(crops):           # mm, the centre of a print-size crop (draft res shown 2x)
            X, Y = int(x * PXMM) - 150, int(y * PXMM) - 110
            bg.crop((X, Y, X + 300, Y + 220)).resize((600, 440), Image.NEAREST).save(os.path.join(dd, f'crop-{i}.png'))
        print('draft', bg.size)
        return
    p = os.path.join(out_dir, 'art.png')
    rgba.save(p, optimize=True)
    print('art', rgba.size)
    # the preview: the art alone, on a plain patch of the tee's black with a margin round it, ~1200 px long side
    bb = rgba.getchannel('A').getbbox()
    pad = int(max(bb[2] - bb[0], bb[3] - bb[1]) * 0.16)
    crop = rgba.crop(bb)
    bg = Image.new('RGBA', (crop.width + 2 * pad, crop.height + 2 * pad), h.hexrgb(TEE) + (255,))
    bg.alpha_composite(crop, (pad, pad))
    s = 1200 / max(bg.size)
    bg.convert('RGB').resize((int(bg.width * s), int(bg.height * s)), Image.LANCZOS).save(os.path.join(out_dir, 'preview.png'))
    del rgba, bg, crop
    if placement:
        placement = dict(placement)
        placement.setdefault('w_cm', round((bb[2] - bb[0]) / (PXMM * 10), 1))
        with open(os.path.join(out_dir, 'placement.json'), 'w') as fh:
            json.dump(placement, fh)
            fh.write('\n')
    subprocess.run([sys.executable, os.path.join(HERE, 'check.py'), 'verify', p, '10', '40'])


def dots(art, layer, x, y, size_mm, n=2, r=0.125, gap=0.33, rng=None):
    """the wordmark's two dots, as the brand sets them (rounder and bigger than the face's period): x = where the first
    dot's left edge starts, y = the baseline. Returns the width used in mm."""
    rng = rng or art.rng
    rr = r * size_mm
    for k in range(n):
        cx = x + rr + k * gap * size_mm + rng.gauss(0, 0.04 * rr)
        disc(art, cx, y - rr * 1.02 + rng.gauss(0, 0.04 * rr), rr, layer, rng=rng)
    return 2 * rr + (n - 1) * gap * size_mm


def disc(art, x, y, r, layer, rng=None, wob=0.035):
    """a round dot made by hand, for anything bigger than a few mm (the pen's dot is a 9-gon, lumpy when big):
    a circle wobbled at a few control points, a hair out of round"""
    rng = rng or art.rng
    n = 9
    sq = rng.uniform(0.96, 1.03)
    ph = rng.uniform(0, math.tau)
    pts = [(x + math.cos(ph + k / n * math.tau) * r * (1 + rng.gauss(0, wob)),
            y + math.sin(ph + k / n * math.tau) * r * sq * (1 + rng.gauss(0, wob))) for k in range(n)]
    pts = h.catmull(pts, closed=True, step=max(0.2, r / 30))
    art.D[layer].polygon(h.P(pts), fill=255)


# ----------------------------------------------------------------- drawn letters
def contours(mask):
    """marching squares on a binary numpy mask: the closed outlines (outer edges and counters) as lists of (x, y) px,
    on the pixel-corner grid. Pure python, for small masks (a glyph at a few px per mm)."""
    import numpy as np
    m = np.pad(np.asarray(mask) > 0, 1).astype(np.uint8)
    H_, W_ = m.shape
    code = m[:-1, :-1] * 8 + m[:-1, 1:] * 4 + m[1:, 1:] * 2 + m[1:, :-1] * 1
    # edge midpoints of a cell (i row, j col): top, right, bottom, left
    def mid(i, j, e):
        return ((j + 0.5, i), (j + 1, i + 0.5), (j + 0.5, i + 1), (j, i + 0.5))[e]
    table = {1: [(3, 2)], 2: [(2, 1)], 3: [(3, 1)], 4: [(1, 0)], 5: [(3, 0), (1, 2)], 6: [(2, 0)], 7: [(3, 0)],
             8: [(0, 3)], 9: [(0, 2)], 10: [(0, 1), (2, 3)], 11: [(0, 1)], 12: [(1, 3)], 13: [(1, 2)], 14: [(2, 3)]}
    nxt = {}
    ii, jj = np.nonzero((code > 0) & (code < 15))
    for i, j in zip(ii.tolist(), jj.tolist()):
        for e0, e1 in table[int(code[i, j])]:
            nxt[mid(i, j, e0)] = mid(i, j, e1)
    loops, seen = [], set()
    for start in list(nxt):
        if start in seen:
            continue
        loop, p = [], start
        while p not in seen and p in nxt:
            seen.add(p)
            loop.append((p[0] - 1, p[1] - 1))
            p = nxt[p]
        if len(loop) > 8:
            loops.append(loop)
    return loops


def letters(art, layer, txt, fname, size_mm, x, y, weight=None, lw=1.4, fill=None, fill_shift=(0.9, 0.7), res=2.5,
            rng=None, lang=None, jit=0.025, turn=0.015, wob=0.16, every=1.4, track=0.0, fill_grow=-0.3, trem=0.12,
            shift_jit=0.25, min_loop=0.0, close=None, shift_turn=0.0):
    """draw txt as hand-drawn outline letters: each glyph's outline (and its counters) traced from the font, then
    redrawn with the pen, wobbling and pressing; `fill` = a spot layer (or a list, one per glyph) laid under it,
    loose and off register like the back's spot screens. Baseline-left at (x, y) mm. Returns the width in mm."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    rng = rng or art.rng
    f = ImageFont.truetype(os.path.join(FONTS, FONT.get(fname, fname)), max(4, int(round(size_mm * res))))
    if weight is not None:
        f.set_variation_by_axes([weight] + [a_['default'] for a_ in f.get_variation_axes()[1:]])
    kw = {'language': lang} if lang else {}
    acc = ''
    for i, ch in enumerate(txt):
        dx = f.getlength(acc, **kw) / res + track * i
        acc += ch
        if not ch.strip():
            continue
        bb = f.getbbox(ch, anchor='ls', **kw)
        pad = 6
        m = Image.new('L', (bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad), 0)
        ox, oy = pad - bb[0], pad - bb[1]
        ImageDraw.Draw(m).text((ox, oy), ch, font=f, fill=255, anchor='ls', **kw)
        m = m.filter(ImageFilter.GaussianBlur(0.6)).point(lambda p: 255 if p > 127 else 0)
        if close and ch in close:                 # close narrow gaps (mm) so near-touching strokes trace as one form
            kk = int(close[ch] * res) | 1
            m = m.filter(ImageFilter.MaxFilter(kk)).filter(ImageFilter.MinFilter(kk))
        dy = rng.gauss(0, jit * size_mm * 0.5)
        r = rng.gauss(0, turn * 0.6)
        gx, gy = x + dx, y + dy
        ca, sa = math.cos(r), math.sin(r)

        def to_mm(px, py):
            u, v = (px - ox) / res, (py - oy) / res
            return (gx + u * ca - v * sa, gy + u * sa + v * ca)
        loops = [lp for lp in contours(np.asarray(m)) if abs(_area(lp)) / res ** 2 >= min_loop]
        layer_fill = fill[i % len(fill)] if isinstance(fill, (list, tuple)) else fill
        if layer_fill == '-':
            layer_fill = None
        if layer_fill:
            # the spot screen: the glyph's own shape, shifted off register and grown or shrunk a hair
            fs = fill_shift[i % len(fill_shift)] if isinstance(fill_shift[0], (list, tuple)) else fill_shift
            sx, sy = fs[0] + rng.gauss(0, shift_jit), fs[1] + rng.gauss(0, shift_jit)
            if shift_turn:                        # each screen slips its own way (turned up to shift_turn radians)
                q = rng.uniform(-shift_turn, shift_turn)
                sx, sy = sx * math.cos(q) - sy * math.sin(q), sx * math.sin(q) + sy * math.cos(q)
            mm_ = Image.new('L', (art.L[layer_fill].width, art.L[layer_fill].height), 0)
            dr = ImageDraw.Draw(mm_)
            sgn = math.copysign(1, _area(max(loops, key=lambda q: abs(_area(q))))) if loops else 1
            outer = [lp for lp in loops if _area(lp) * sgn > 0]
            holes = [lp for lp in loops if _area(lp) * sgn <= 0]
            for lp in outer:
                dr.polygon([(px_ * PXMM, py_ * PXMM) for px_, py_ in [to_mm(*q) for q in lp[::2]]], fill=255)
            for lp in holes:
                dr.polygon([(px_ * PXMM, py_ * PXMM) for px_, py_ in [to_mm(*q) for q in lp[::2]]], fill=0)
            if fill_grow:
                k = 2 * int(round(abs(fill_grow) * PXMM)) + 1
                mm_ = mm_.filter(ImageFilter.MinFilter(k) if fill_grow < 0 else ImageFilter.MaxFilter(k))
            art.L[layer_fill].paste(255, (int(round(sx * PXMM)), int(round(sy * PXMM))), mm_)
            del mm_
        # the pen: every outline, resampled to control points about `every` mm apart, then drawn by hand
        for lp in loops:
            pts = [to_mm(*q) for q in lp]
            L = h.cumlen(pts)[-1]
            n = max(6, int(L / every))
            ctrl = h.resample(pts + [pts[0]], n)
            p = art.hand(ctrl, closed=True, wob=wob, trem=trem, rng=rng, step=0.35)
            art.ink(p, lw, layer=layer, closed=True, rng=rng, a0=0.6, a1=1.2, pv=0.14, close_frac=rng.uniform(0.98, 1.03))
    return f.getlength(txt, **kw) / res + track * (len(txt) - 1)


def _area(lp):
    """signed area of a loop (sign tells outer edge from counter for the marching-squares winding)"""
    s = 0.0
    for (x0, y0), (x1, y1) in zip(lp, lp[1:] + lp[:1]):
        s += x0 * y1 - x1 * y0
    return s / 2
