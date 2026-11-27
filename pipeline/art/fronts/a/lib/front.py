"""
front.py: what the eight Mumbai fronts share.

Units are millimetres of print. `setup(w_mm, h_mm)` sets the canvas before hand.py is imported:
    R=1 python3 gen.py   -> draft (a few px per mm, written as draft.png on the shirt colour)
    python3 gen.py       -> final at 94 px per cm (9.4 px per mm), written as art.png (transparent)
The inks are the back's own (pipeline/art/art-a-map, the al3 cream print), printed like riso on paper: they multiply
where they cross, and the shirt is the paper.
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
DRAFT = os.environ.get('R', '') == '1'
FULL_PX_MM = 9.4

INK = {
    'key': '#22201D',      # the back's line ink
    'green': '#2F7D52',    # turf
    'water': '#6890C8',    # the sea's wave lines
    'ring': '#2C46BE',     # the sound rings
    'violet': '#6B3E98',   # the Western line's violet (train only)
}
SHIRT = '#FFFAE7'
FONT_NOTE = os.path.join(ROOT, 'pipeline', 'fonts', 'GochiHand-Regular.ttf')


def setup(w_mm, h_mm, draft_px=None):
    """canvas of w_mm x h_mm; returns px per mm. Must run before `import hand`."""
    if DRAFT:
        r = draft_px or max(2.4, min(7.0, 1100.0 / max(w_mm, h_mm * 0.8)))
    else:
        r = FULL_PX_MM
    os.environ['R'] = repr(r)
    os.environ['UW'] = str(int(w_mm))
    os.environ['UH'] = str(int(h_mm))
    os.environ['MINW'] = '1.1'          # 1.1 mm = 10.3 px at print size: nothing thinner prints
    sys.path.insert(0, HERE)
    return r


# ----------------------------------------------------------------- real geometry (the back's cached OSM)
_OSM = None


def osm():
    global _OSM
    if _OSM is None:
        d = json.load(open(os.path.join(ROOT, 'pipeline', 'art', 'art-a-map', 'osm.json')))
        _OSM = d['elements']
    return _OSM


COURSE_ID, TRACK_REL, HAJI_ALI = 1289073486, 7107871, 53355635
LAT_C, LON_C = 18.984293, 72.820206          # the track's centroid (the back's projection centre)
MLAT = 110574.0
MLON = 111320.0 * math.cos(math.radians(LAT_C))


class Proj:
    """lon/lat -> local metres (cos-lat corrected) -> rotate (deg, + turns the map clockwise) -> mm on the print"""

    def __init__(self, rot_deg, mm_per_m, cx, cy, lat0=LAT_C, lon0=LON_C):
        self.c, self.s = math.cos(math.radians(rot_deg)), math.sin(math.radians(rot_deg))
        self.k, self.cx, self.cy, self.lat0, self.lon0 = mm_per_m, cx, cy, lat0, lon0

    def __call__(self, lat, lon):
        x = (lon - self.lon0) * MLON
        y = (lat - self.lat0) * MLAT
        xr = x * self.c - y * self.s
        yr = x * self.s + y * self.c
        return self.cx + xr * self.k, self.cy - yr * self.k

    def pts(self, geom):
        return [self(p['lat'], p['lon']) for p in geom if p]


def geoms_of(e):
    if 'geometry' in e:
        return [e['geometry']]
    return [m['geometry'] for m in e.get('members', []) if m.get('geometry') and m.get('role') in ('outer', '')]


def by_id(kind, i):
    for e in osm():
        if e['type'] == kind and e['id'] == i:
            return e


def track_rings(pr):
    """the three rings of the race track relation (inner sand track, middle, outer turf with the chute), small first"""
    rel = by_id('relation', TRACK_REL)
    rs = [pr.pts(m['geometry']) for m in rel['members'] if m.get('geometry')]
    return sorted(rs, key=area)


def area(pts):
    return 0.5 * abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])))


def centroid(pts):
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def simplify(pts, tol):
    """drop points closer than tol to the last kept one (a hand does not follow every survey vertex)"""
    out = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) >= tol:
            out.append(p)
    if out[-1] != pts[-1]:
        out.append(pts[-1])
    return out


# ----------------------------------------------------------------- output
def out_dir(gen_file):
    return os.path.dirname(os.path.abspath(gen_file))


def save(art_obj, inks, order, gen_file, tag=None):
    """composite like riso on paper, binary alpha; final -> art.png, draft -> draft.png (on the shirt colour)"""
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
    print('saved', p, rgba.size)
    return p


def stage_of(pr, ring_in):
    """the back's stage: on the track's long axis (25.4 deg from east), 55 m in from the inner ring's far end;
    returns (stage xy, facing unit vector from the stage into the crowd), in print mm"""
    ic = centroid(ring_in)
    ax = math.radians(25.4)
    ex, ey = math.cos(ax), math.sin(ax)                      # metres frame, y north
    ux, uy = ex * pr.c - ey * pr.s, -(ex * pr.s + ey * pr.c)  # on the print (y down)
    half = max((x - ic[0]) * ux + (y - ic[1]) * uy for x, y in ring_in)
    d = half - 55 * pr.k
    return (ic[0] + ux * d, ic[1] + uy * d), (-ux, -uy)


def text_mask(txt, size_mm, rot=0.0):
    """a handwritten note in the back's note hand (Gochi Hand), as an L mask at canvas resolution"""
    import hand
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(FONT_NOTE, max(4, int(round(size_mm * hand.R))))
    bb = f.getbbox(txt)
    m = Image.new('L', (bb[2] + 8, bb[3] + 8), 0)
    ImageDraw.Draw(m).text((4 - bb[0], 4), txt, font=f, fill=255)
    if rot:
        m = m.rotate(rot, resample=Image.BICUBIC, expand=True).point(lambda p: 255 if p > 110 else 0)
    return m


def place(art_obj, layer, mask, cx_mm, cy_mm):
    import hand
    art_obj.L[layer].paste(255, (int(cx_mm * hand.R - mask.width / 2), int(cy_mm * hand.R - mask.height / 2)), mask)


# ----------------------------------------------------------------- added for the a fronts (round 3)
FONTS = os.path.join(ROOT, 'pipeline', 'fonts')
FONT = {
    'brico': os.path.join(FONTS, 'BricolageGrotesque-Var.ttf'),
    'deva': os.path.join(FONTS, 'NotoSansDevanagari-Black.ttf'),
    'deva-bold': os.path.join(FONTS, 'NotoSansDevanagari-Bold.ttf'),
    'kann': os.path.join(FONTS, 'NotoSansKannada-Black.ttf'),
    'kann-bold': os.path.join(FONTS, 'NotoSansKannada-Bold.ttf'),
    'note': FONT_NOTE,
    'shantell': os.path.join(FONTS, 'ShantellSans-Var.ttf'),   # monoline: 0.175 em stroke at 800, the small type
}


def font(name, size_mm, wght=None):
    """a lineup font at canvas resolution; size_mm is the em size in mm of print"""
    import hand
    from PIL import ImageFont
    f = ImageFont.truetype(FONT[name], max(4, int(round(size_mm * hand.R))))
    if wght is not None:
        axes = f.get_variation_axes()
        f.set_variation_by_axes([wght] + [a['default'] for a in axes[1:]])
    return f


def type_mask(txt, name, size_mm, wght=None, rot=0.0, track_mm=0.0, bold=None):
    """set text as a binary L mask, tight to the ink. m.info['base'] is the baseline in mm from the mask's top
    (unrotated text only). track_mm spaces letters (Latin only)."""
    import hand
    from PIL import Image, ImageDraw
    f = font(name, size_mm, wght)
    widths = [f.getlength(ch) for ch in txt] if track_mm else None
    W_ = int((sum(widths) + track_mm * hand.R * len(txt) if track_mm else f.getlength(txt)) + size_mm * hand.R)
    H_ = int(size_mm * hand.R * 2.4)
    y0 = size_mm * hand.R * 1.5
    m = Image.new('L', (W_, H_), 0)
    d = ImageDraw.Draw(m)
    if track_mm:
        x = size_mm * hand.R * 0.3
        for ch, w in zip(txt, widths):
            d.text((x, y0), ch, font=f, fill=255, anchor='ls')
            x += w + track_mm * hand.R
    else:
        d.text((size_mm * hand.R * 0.3, y0), txt, font=f, fill=255, anchor='ls')
    if rot:
        m = m.rotate(rot, resample=Image.BICUBIC, expand=True)
    m = m.point(lambda p: 255 if p >= 128 else 0)
    if bold is None:   # Bricolage's joins (the d's bowl into its stem) fall under 1 mm below ~14 mm: fill them out
        bold = 3 if (name == 'brico' and size_mm < 14) else 0
    if bold:
        from PIL import ImageFilter
        m = m.filter(ImageFilter.MaxFilter(bold if bold % 2 else bold + 1))
    bb = m.getbbox()
    m = m.crop(bb)
    m.info['base'] = (y0 - bb[1]) / hand.R
    return m


def paste_mm(img_L, mask, x_mm, y_mm):
    """paste a mask's top-left at (x_mm, y_mm)"""
    import hand
    img_L.paste(255, (int(round(x_mm * hand.R)), int(round(y_mm * hand.R))), mask)


def write_placement(gen_file, where, w_cm, top_cm, **extra):
    d = dict(where=where, w_cm=w_cm, top_cm=top_cm)
    d.update(extra)
    json.dump(d, open(os.path.join(out_dir(gen_file), 'placement.json'), 'w'), indent=2)


def preview(art_png, out_png, long_side=1200, margin_frac=0.14):
    """the art alone on a plain patch of the shirt colour, with a margin round it"""
    from PIL import Image
    a = Image.open(art_png).convert('RGBA')
    bb = a.getchannel('A').getbbox()
    a = a.crop(bb)
    m = int(max(a.size) * margin_frac)
    bg = Image.new('RGBA', (a.width + 2 * m, a.height + 2 * m), tuple(int(SHIRT[i:i + 2], 16) for i in (1, 3, 5)) + (255,))
    bg.alpha_composite(a, (m, m))
    s = long_side / max(bg.size)
    bg.convert('RGB').resize((int(bg.width * s), int(bg.height * s)), Image.LANCZOS).save(out_png)
    print('preview', out_png)


def finish_out(art_obj, inks, order, gen_file):
    """last clean-up of every ink (type set after the physics included: its hairlines and knife corners go), then save
    (draft.png or art.png); after a final, also the preview"""
    import hand
    for k in order:
        inks[k] = hand.clean(inks[k])
    p = save(art_obj, inks, order, gen_file)
    if not DRAFT:
        preview(p, os.path.join(out_dir(gen_file), 'preview.png'))
    return p


def ink_type(inks, layer, mask, x_mm, y_mm):
    """set type after the print physics (crisp, never eroded by the clean-up): mask's top-left at (x_mm, y_mm)"""
    import hand
    inks[layer].paste(255, (int(round(x_mm * hand.R)), int(round(y_mm * hand.R))), mask)


def embolden(mask, px=3):
    """a slightly fuller pen for small hand lettering, so its tapers survive the 1 mm clean-up"""
    from PIL import Image, ImageFilter
    big = Image.new('L', (mask.width + 2 * px, mask.height + 2 * px), 0)
    big.paste(mask, (px, px))
    return big.filter(ImageFilter.MaxFilter(px if px % 2 else px + 1))
