"""
efront.py: what the eight "i am a party" fronts share. Units are millimetres of print.

    import efront as E
    h, art = E.boot(100, 50, seed=7, layers=('violet', 'orange', 'cream'))
    ...                                   # draw in mm
    E.save(art, __file__, order=('violet', 'orange', 'cream'), crops=[(30, 20)])

Every run renders at print size (94 px per cm: the pieces are small) and writes, next to gen.py:
art.png (transparent, binary alpha), preview.png (the art alone on a plain patch of the shirt colour, ~1200 px on its
long side), crop-N.png (1:1 at print, to look at), then runs check.py verify.
ROUND=n also keeps round-n.png (a small copy of the preview) while working.
The inks are the back's (pipeline/art/art-e-breath): cream lettering, pale yellow, orange, violet; brand blue.
"""
import os, sys, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
PXMM = 9.4
TEE = '#151515'
PAL = {'cream': '#F1E7D0', 'yellow': '#FFC04E', 'orange': '#F27C24', 'violet': '#6B2499', 'blue': '#4C66F5'}
SHIFT = {'cream': (0, 0), 'yellow': (0.22, 0.18), 'orange': (-0.2, 0.22), 'violet': (0.16, -0.14), 'blue': (0.1, 0.12)}
FONTS = os.path.join(ROOT, 'pipeline', 'fonts')
h = None


def boot(w_mm, h_mm, seed=1, layers=('cream',)):
    global h
    os.environ['R'] = str(PXMM)
    os.environ['UW'], os.environ['UH'] = str(int(w_mm)), str(int(h_mm))
    os.environ['MINW'] = '1.1'                        # the thinnest stroke: 1.1 mm (10 px at print)
    sys.path.insert(0, HERE)
    import hand as _h
    h = _h
    return _h, _h.Art(seed=seed, layers=layers)


def font_mask(text, font, size_mm, variation=None, baseline=False, grow=0):
    """text set from one of the lineup's fonts, as an L mask at print resolution (size_mm = the font's em).
    baseline=True also returns the baseline's row in the mask (px). grow: px added to every stroke's edge, so small
    settings keep their thinnest joins at the printable minimum"""
    from PIL import ImageFilter
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(os.path.join(FONTS, font), max(4, int(round(size_mm * PXMM))), layout_engine=ImageFont.Layout.RAQM)
    if variation:
        try:
            f.set_variation_by_name(variation)
        except Exception:
            pass
    bb = f.getbbox(text, anchor='ls')
    m = Image.new('L', (bb[2] - bb[0] + 16, bb[3] - bb[1] + 16), 0)
    ImageDraw.Draw(m).text((8 - bb[0], 8 - bb[1]), text, font=f, fill=255, anchor='ls')
    for _ in range(grow):
        m = m.filter(ImageFilter.MaxFilter(3))
    return (m, 8 - bb[1]) if baseline else m


def settle(inks, order):
    """overprinted screens (knockout in order, later on top), then every ink's VISIBLE part is checked: any sliver
    of it thinner than the minimum feature is handed to the ink printed over it (so no hairline of colour and no
    black gap is left between bands); the top ink's slivers are cut."""
    from PIL import ImageChops
    order = list(order)
    for i, k in enumerate(order):
        above = None
        for j in order[i + 1:]:
            above = inks[j] if above is None else ImageChops.lighter(above, inks[j])
        vis = inks[k] if above is None else ImageChops.subtract(inks[k], above)
        thin = ImageChops.subtract(vis, h.clean(vis))
        if i + 1 < len(order):
            nxt = order[i + 1]
            inks[nxt] = ImageChops.lighter(inks[nxt], thin)
        inks[k] = ImageChops.subtract(inks[k], thin)
    return inks


def save(art, gen_file, order, shifts=None, palette=None, crops=(), trim=True):
    """finish the inks (spread, register, knockout, clean), composite, write art.png, preview.png, crops; verify"""
    from PIL import Image
    out_dir = os.path.dirname(os.path.abspath(gen_file))
    order = [k for k in order if k in art.L]
    sh = shifts if shifts is not None else SHIFT
    inks = art.finish(order=order, shifts={k: v for k, v in sh.items() if k in art.L}, spread_amt=0.14, trim=trim)
    if not trim:
        inks = settle(inks, order)
    rgba = h.composite(inks, palette or PAL, order)
    a = rgba.getchannel('A').point(lambda p: 255 if p >= 128 else 0)
    rgba.putalpha(a)
    del inks
    bb = a.getbbox()                     # trim to the ink, 46 px (4.9 mm) of clear shirt round it
    if bb:
        M = 46
        rgba = rgba.crop((bb[0] - M, bb[1] - M, bb[2] + M, bb[3] + M))
    p = os.path.join(out_dir, 'art.png')
    rgba.save(p, optimize=True)
    # preview: the art alone on a plain patch of shirt colour, a margin round it
    W, H = rgba.size
    m = int(max(W, H) * 0.12)
    bg = Image.new('RGBA', (W + 2 * m, H + 2 * m), h.hexrgb(TEE) + (255,))
    bg.alpha_composite(rgba, (m, m))
    bg = bg.convert('RGB')
    s = 1200 / max(bg.size)
    bg.resize((int(bg.width * s), int(bg.height * s)), Image.LANCZOS).save(os.path.join(out_dir, 'preview.png'))
    rnd = os.environ.get('ROUND')
    if rnd:
        s2 = 700 / max(bg.size)
        bg.resize((int(bg.width * s2), int(bg.height * s2)), Image.LANCZOS).save(os.path.join(out_dir, f'round-{rnd}.png'))
    full = Image.new('RGBA', rgba.size, h.hexrgb(TEE) + (255,))
    full.alpha_composite(rgba)
    full = full.convert('RGB')
    for i, (x, y) in enumerate(crops):            # mm on the drawing canvas, the centre of a 1:1-at-print crop
        X, Y = int(x * PXMM) - 300 - (bb[0] - 46), int(y * PXMM) - 220 - (bb[1] - 46)
        full.crop((X, Y, X + 600, Y + 440)).save(os.path.join(out_dir, f'crop-{i}.png'))
    print('art', rgba.size, f'{W / PXMM / 10:.1f} x {H / PXMM / 10:.1f} cm')
    subprocess.run([sys.executable, os.path.join(HERE, 'check.py'), 'verify', p])
