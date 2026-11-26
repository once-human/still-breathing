"""
front.py: what the eight Bengaluru fronts (shirt d, 04 map) share.

Units are millimetres of print. `setup(w_mm, h_mm)` sets the canvas before hand.py is imported:
    R=1 python3 gen.py   -> draft (about 7 px per mm), written as draft.png on the shirt colour
    python3 gen.py       -> final at 94 px per cm (9.4 px per mm): art.png (transparent) + preview.png
The inks are the back's own (pipeline/art/art-d-map, render-info.json), printed like riso on paper: they multiply
where they cross, and the shirt is the paper.

The back's map, for anything that has to agree with it: 1 unit = 1 metre, 1200 units across 38 cm, so 100 m on the
back is 31.7 mm; the map is turned so that north points up and 30 degrees to the right.
"""
import math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..', '..'))   # this copy sits one folder deeper
DRAFT = os.environ.get('R', '') == '1'
FULL_PX_MM = 9.4

INK = {
    'key': '#22201D',      # the back's line ink
    'green': '#2F7D52',    # the grounds' grass
    'blue': '#6E95CE',     # the lake
    'accent': '#2C46BE',   # the sound rings (the brand blue on off white)
}
SHIRT = '#FFFAE7'
FONTS = os.path.join(ROOT, 'pipeline', 'fonts')
FONT_NOTE = os.path.join(FONTS, 'GochiHand-Regular.ttf')        # the back's note hand
FONT_WORD = os.path.join(FONTS, 'BricolageGrotesque-Var.ttf')    # the lineup's wordmark face
FONT_DEVA = os.path.join(FONTS, 'NotoSansDevanagari-Bold.ttf')
FONT_DEVA_BLACK = os.path.join(FONTS, 'NotoSansDevanagari-Black.ttf')
FONT_KAN = os.path.join(FONTS, 'NotoSansKannada-Bold.ttf')
FONT_KAN_BLACK = os.path.join(FONTS, 'NotoSansKannada-Black.ttf')
NORTH = (math.sin(math.radians(30)), -math.cos(math.radians(30)))   # north on the back's page (y down)
MM_PER_M = 380.0 / 1200.0                                           # the back's scale


def setup(w_mm, h_mm, draft_px=None):
    """canvas of w_mm x h_mm; returns px per mm. Must run before `import hand`."""
    r = (draft_px or 7.0) if DRAFT else FULL_PX_MM
    os.environ['R'] = repr(r)
    os.environ['UW'] = str(int(w_mm))
    os.environ['UH'] = str(int(h_mm))
    os.environ['MINW'] = '1.1'          # 1.1 mm = 10.3 px at print size: nothing thinner prints
    sys.path.insert(0, HERE)
    return r


# ----------------------------------------------------------------- lettering
def _font(path, px, wght=None, opsz=None):
    from PIL import ImageFont
    f = ImageFont.truetype(path, max(4, int(round(px))))
    if wght is not None:
        try:
            axes = f.get_variation_axes()
            vals = []
            for a in axes:
                nm = a.get('name', b'')
                nm = nm.decode() if isinstance(nm, bytes) else str(nm)
                if nm.lower().startswith('weight') or nm.lower() == 'wght':
                    vals.append(wght)
                elif 'optical' in nm.lower() or nm.lower() == 'opsz':
                    vals.append(opsz if opsz is not None else a['default'])
                else:
                    vals.append(a['default'])
            f.set_variation_by_axes(vals)
        except Exception:
            pass
    return f


def text_mask(txt, size_mm, rot=0.0, font=None, wght=None, weight_mm=None):
    """one line of text as a binary L mask at canvas resolution (size_mm = the font's em in mm). The note hand's
    pen is thinner than 1 mm at chest sizes, so it is thickened to a printable pen (weight_mm added to every stroke,
    default enough to bring Gochi Hand to about 1.2 mm)"""
    import hand
    from PIL import Image, ImageDraw, ImageFilter
    font = font or FONT_NOTE
    f = _font(font, size_mm * hand.R, wght)
    bb = f.getbbox(txt)
    m = Image.new('L', (bb[2] - bb[0] + 16, bb[3] - bb[1] + 16), 0)
    ImageDraw.Draw(m).text((8 - bb[0], 8 - bb[1]), txt, font=f, fill=255)
    if weight_mm is None:
        weight_mm = max(0.0, 1.25 - 0.095 * size_mm) if font == FONT_NOTE else 0.0
    k = int(round(weight_mm * hand.R)) | 1
    if k > 1:
        m = m.filter(ImageFilter.GaussianBlur(hand.R * 0.12)).point(lambda p: 255 if p > 100 else 0)
        m = m.filter(ImageFilter.MaxFilter(k))
    if rot:
        m = m.rotate(rot, resample=Image.BICUBIC, expand=True)
    return m.point(lambda p: 255 if p > 120 else 0)


def close_traps(m, size_mm):
    """Bricolage cuts ink traps into its joins; at chest size they print as nicks. Close them (a closing about
    0.07 em across), which leaves real counters open."""
    import hand
    from PIL import ImageFilter
    k = max(3, int(round(size_mm * 0.07 * hand.R))) | 1
    return m.filter(ImageFilter.MaxFilter(k)).filter(ImageFilter.MinFilter(k))


def word_mask(txt, size_mm, rng, font=None, wght=700, track=0.0, jit=1.6, rot_jit=1.2, opsz=None, space=0.72):
    """a wordmark set from the lineup's font and then worked by hand: each glyph drawn on its own, set a hair off the
    baseline, turned a little, the spacing nudged by eye. `track` is extra space in em; `jit` scales the hand.
    Returns (mask, baseline_y_px)."""
    import hand
    from PIL import Image, ImageDraw
    px = size_mm * hand.R
    f = _font(font or FONT_WORD, px, wght, opsz)
    asc, desc = f.getmetrics()
    pad = int(px * 0.5)
    total = int(f.getlength(txt) + px * track * len(txt) + 2 * pad)
    m = Image.new('L', (total, asc + desc + 2 * pad), 0)
    x = pad
    for i, ch in enumerate(txt):
        adv = f.getlength(ch)
        if i + 1 < len(txt):   # keep the font's kerning between this glyph and the next
            adv = f.getlength(txt[i:i + 2]) - f.getlength(txt[i + 1])
        if ch.strip():
            g = Image.new('L', (int(px * 2), asc + desc + 2 * pad), 0)
            sw = int(round(bulk_mm(size_mm, font or FONT_WORD) * hand.R))
            ImageDraw.Draw(g).text((int(px * 0.5), pad), ch, font=f, fill=255, stroke_width=sw, stroke_fill=255)
            g = g.rotate(rng.uniform(-rot_jit, rot_jit) * jit, resample=Image.BICUBIC,
                         center=(px * 0.5 + adv / 2, pad + asc))
            dy = int(round(rng.gauss(0, 0.009) * px * jit))
            m.paste(255, (int(round(x - px * 0.5)), dy), g.point(lambda p: 255 if p > 120 else 0))
        if ch == ' ':
            adv *= space
        x += adv + px * track + rng.uniform(-0.008, 0.008) * px * jit
    if (font or FONT_WORD) == FONT_WORD:
        m = close_traps(m, size_mm)
    bb = m.getbbox()
    m = m.crop((bb[0] - 6, 0, bb[2] + 6, m.height))
    return m, pad + asc


def script_mask(txt, size_mm, font, rng=None, rot=0.0):
    """a whole script word (Devanagari, Kannada) set as one run so its shaping holds; turned a hair by hand"""
    return text_mask(txt, size_mm, rot=rot, font=font)


def paste(layer_img, mask, x_mm, y_mm, anchor='lt', base_px=None):
    """paste a mask into an L layer. anchor: 'lt' left-top, 'c' centre, 'lb' left-baseline (needs base_px)"""
    import hand
    x, y = x_mm * hand.R, y_mm * hand.R
    if anchor == 'c':
        x, y = x - mask.width / 2, y - mask.height / 2
    elif anchor == 'cb':
        x, y = x - mask.width / 2, y - base_px
    elif anchor == 'lb':
        y = y - base_px
    elif anchor == 'rb':
        x, y = x - mask.width, y - base_px
    layer_img.paste(255, (int(round(x)), int(round(y))), mask)


def cut(layer_img, mask, x_mm, y_mm, anchor='c', base_px=None, grow_px=0):
    """knock a mask (grown by grow_px) out of a layer: a gap round the lettering"""
    import hand
    from PIL import Image, ImageFilter
    if grow_px:
        k = grow_px * 2 + 1
        big = Image.new('L', (mask.width + 2 * grow_px, mask.height + 2 * grow_px), 0)
        big.paste(mask, (grow_px, grow_px))
        mask = big.filter(ImageFilter.MaxFilter(k))
        x_mm -= 0 if anchor in ('c', 'cb') else grow_px / hand.R
        y_mm -= 0 if anchor == 'c' else grow_px / hand.R
        if base_px is not None:
            base_px += grow_px
    blank = Image.new('L', layer_img.size, 0)
    paste(blank, mask, x_mm, y_mm, anchor, base_px)
    from PIL import ImageChops
    return ImageChops.subtract(layer_img, blank)


# ----------------------------------------------------------------- output
def out_dir(gen_file):
    return os.path.dirname(os.path.abspath(gen_file))


def save(art_obj, inks, order, gen_file, tag=None):
    """composite like riso on paper, binary alpha; final -> art.png + preview.png, draft -> draft.png"""
    import hand
    from PIL import Image
    pal = {k: INK[k] for k in order}
    rgba = hand.composite_overprint(inks, pal, order, paper='#FFFFFF')
    a = rgba.getchannel('A').point(lambda p: 255 if p >= 128 else 0)
    rgba.putalpha(a)
    d = out_dir(gen_file)
    if DRAFT:
        bg = Image.new('RGBA', rgba.size, hand.hexrgb(SHIRT) + (255,))
        bg.alpha_composite(rgba)
        p = os.path.join(d, f'draft{"-" + tag if tag else ""}.png')
        bg.convert('RGB').save(p)
    else:
        p = os.path.join(d, 'art.png')
        rgba.save(p, optimize=True)
        preview(rgba, os.path.join(d, 'preview.png'))
    print('saved', p, rgba.size)
    return p


def preview(rgba, path, long_side=1200):
    """the art alone on a plain patch of the shirt colour, a margin round it; no shirt shape"""
    import hand
    from PIL import Image
    bb = rgba.getchannel('A').getbbox()
    art = rgba.crop(bb)
    m = int(max(art.size) * 0.16)
    bg = Image.new('RGBA', (art.width + 2 * m, art.height + 2 * m), hand.hexrgb(SHIRT) + (255,))
    bg.alpha_composite(art, (m, m))
    s = long_side / max(bg.size)
    bg.convert('RGB').resize((int(bg.width * s), int(bg.height * s)), Image.LANCZOS).save(path)


def wordmark(art_obj, word, x_mm, base_mm, size_mm, rng, layer='key', dot_layer='accent', wght=720, track=0.0,
             jit=1.0, dots=2, dot_r=0.075, dot_gap=0.05, dot_step=0.205, font=None, anchor='l'):
    """`word` + its two dots: the word set from the lineup's face and worked by hand (word_mask), the dots drawn as
    hand dots on their own ink. size_mm is the em. anchor 'l' (x is the left edge) or 'c' (x is the centre).
    Returns (left, right, top) in mm."""
    import hand
    m, base_px = word_mask(word, size_mm, rng, font=font, wght=wght, track=track, jit=jit)
    r = max(0.8, dot_r * size_mm)
    wmm = m.width / hand.R + dot_gap * size_mm + r * 2 + (dots - 1) * dot_step * size_mm if dots else m.width / hand.R
    left = x_mm - (wmm / 2 if anchor == 'c' else 0)
    paste(art_obj.L[layer], m, left, base_mm, 'lb', base_px)
    xd = left + m.width / hand.R + dot_gap * size_mm + r
    for k in range(dots):
        art_obj.dot(xd + k * dot_step * size_mm + rng.uniform(-0.01, 0.01) * size_mm,
                    base_mm - r * rng.uniform(0.98, 1.06), r * rng.uniform(0.96, 1.05), layer=dot_layer)
    top = base_mm - base_px / hand.R + (m.getbbox()[1] / hand.R if m.getbbox() else 0)
    return left, left + wmm, top


def bulk_mm(size_mm, font):
    """extra stroke (each side) that small lettering in the wordmark face needs so its thin joins (where a bowl
    meets a stem) still reach 1 mm. Nothing at 13 mm and up."""
    if font != FONT_WORD:
        return 0.0
    return max(0.0, min(0.2, (13.0 - size_mm) * 0.04))


def glyph_mask(ch, size_mm, font, wght=None, rot=0.0):
    """one glyph on its own, centred on its advance box at half the x-height; returns (mask, advance_mm)"""
    import hand
    from PIL import Image, ImageDraw
    px = size_mm * hand.R
    f = _font(font, px, wght)
    asc, desc = f.getmetrics()
    adv = f.getlength(ch)
    S = int(px * 2.2)
    g = Image.new('L', (S, S), 0)
    xh = px * 0.25                      # half an x-height, roughly
    sw = int(round(bulk_mm(size_mm, font) * hand.R))
    ImageDraw.Draw(g).text((S / 2 - adv / 2, S / 2 + xh), ch, font=f, fill=255, anchor='ls', stroke_width=sw,
                           stroke_fill=255)
    if font == FONT_WORD:
        g = close_traps(g, size_mm)
    if font == FONT_NOTE:              # the note hand thickened to a printable pen, as in text_mask
        from PIL import ImageFilter
        k = int(round(max(0.0, 1.25 - 0.095 * size_mm) * hand.R)) | 1
        if k > 1:
            g = g.filter(ImageFilter.MaxFilter(k))
    if rot:
        g = g.rotate(rot, resample=Image.BICUBIC)
    return g.point(lambda p: 255 if p > 120 else 0), adv / hand.R


def arc_text(layer_img, txt, cx, cy, r, theta_mid_deg, size_mm, font, rng, wght=None, track=0.04, bottom=False,
             jit=1.0, align='mid'):
    """letters along a circle (seal lettering), glyph by glyph, each a hair off by hand. top text runs clockwise
    with its tops outward; bottom=True runs the other way with its tops toward the centre.
    Returns the angles (deg) where the text starts and ends."""
    import hand
    advs = [glyph_mask(c, size_mm, font, wght)[1] + track * size_mm for c in txt]
    total = sum(advs)
    span = math.degrees(total / r)
    sgn = -1 if bottom else 1
    th = {'mid': theta_mid_deg - sgn * span / 2, 'start': theta_mid_deg, 'end': theta_mid_deg - sgn * span}[align]
    start = th
    for c, a in zip(txt, advs):
        tc = th + sgn * math.degrees(a / 2 / r)
        if c.strip():
            rot = (90 - tc) if bottom else -(tc + 90)
            rot += rng.uniform(-1.2, 1.2) * jit
            g, _ = glyph_mask(c, size_mm, font, wght, rot=rot)
            rr = r + rng.uniform(-0.12, 0.12) * jit
            x = cx + math.cos(math.radians(tc)) * rr
            y = cy + math.sin(math.radians(tc)) * rr
            paste(layer_img, g, x, y, 'c')
        th += sgn * math.degrees(a / r)
    return start, th


def run_mask(txt, size_mm, font, wght=None):
    """a whole run set at once (keeps Devanagari and Kannada shaping); returns (mask, origin_x_px, baseline_px)"""
    import hand
    from PIL import Image, ImageDraw
    px = size_mm * hand.R
    f = _font(font, px, wght)
    pad = int(px * 0.6)
    L = f.getlength(txt)
    m = Image.new('L', (int(L + 2 * pad), int(px * 1.6 + 2 * pad)), 0)
    ox, base = pad, int(pad + px * 1.05)
    ImageDraw.Draw(m).text((ox, base), txt, font=f, fill=255, anchor='ls')
    return m, ox, base


def mark(art_obj, txt, size_mm, x_mm, base_mm, rng, font=None, wght=None, rot=0.0, per_glyph=False, track=0.0,
         layer='key', dot_layer='accent', dots=2, dot_r=0.075, dot_gap=0.06, dot_step=0.2, jit=1.0):
    """a wordmark + its two hand dots, turned `rot` degrees (counter-clockwise) about the start of its baseline.
    per_glyph=True works a Latin word glyph by glyph (word_mask); scripts are set as one run. Returns the end of
    the dots along the baseline (mm)."""
    import hand
    from PIL import Image
    font = font or FONT_WORD
    if per_glyph:
        m, base = word_mask(txt, size_mm, rng, font=font, wght=wght, track=track, jit=jit)
        bb = m.getbbox()
        ox = 0
        wpx = bb[2]
    else:
        m, ox, base = run_mask(txt, size_mm, font, wght)
        wpx = m.getbbox()[2]
    rr = rot + rng.uniform(-0.4, 0.4) * jit
    if rr:
        big = Image.new('L', (m.width * 2 + 2 * max(m.height, 0), m.height * 2 + m.width), 0)
        offx, offy = big.width // 2 - ox, big.height // 2 - base
        big.paste(m, (offx, offy))
        big = big.rotate(rr, resample=Image.BICUBIC, center=(big.width // 2, big.height // 2))
        big = big.point(lambda p: 255 if p > 120 else 0)
        bb = big.getbbox()
        if bb:
            art_obj.L[layer].paste(255, (int(round(x_mm * hand.R - big.width // 2 + bb[0])),
                                         int(round(base_mm * hand.R - big.height // 2 + bb[1]))), big.crop(bb))
    else:
        art_obj.L[layer].paste(255, (int(round(x_mm * hand.R - ox)), int(round(base_mm * hand.R - base))), m)
    a = math.radians(rr)
    dx, dy = math.cos(a), -math.sin(a)
    ux, uy = -math.sin(a), -math.cos(a)
    r = max(0.8, dot_r * size_mm)
    s = (wpx - ox) / hand.R + dot_gap * size_mm + r
    for k in range(dots):
        t = s + k * dot_step * size_mm + rng.uniform(-0.01, 0.01) * size_mm
        art_obj.dot(x_mm + dx * t + ux * r, base_mm + dy * t + uy * r, r * rng.uniform(0.96, 1.05), layer=dot_layer)
    return s + (dots - 1) * dot_step * size_mm + r
