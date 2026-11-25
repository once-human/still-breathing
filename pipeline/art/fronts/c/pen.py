"""
pen.py: the shared set-up for the 01 crowd fronts. Units are millimetres of print.

    import pen
    h, art = pen.boot(240, 280, seed=7, layers=('line', 'Y', 'B'))   # canvas in mm, then draw on art (units = mm)
    ...
    pen.save(art, __file__, order=('Y', 'B', 'line'))

R=1 (draft): 4.7 px per mm, writes draft.png (+ crop-*.png) next to gen.py.
Otherwise (final): 9.4 px per mm = 94 px per cm of print, writes art.png and runs check.py verify.
The inks are the back's own (art-crowd-tour/manifest.json): cream line, yellow, green, blue on the black tee.
"""
import math, os, sys, random, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DRAFT = os.environ.get('R', '9.4') == '1'
PXMM = 4.7 if DRAFT else 9.4
TEE = '#151515'
PAL = {'line': '#F1E7D0', 'Y': '#F6B330', 'G': '#56B27C', 'B': '#4C66F5'}
SHIFT = {'line': (0, 0), 'Y': (0.38, 0.30), 'G': (-0.33, 0.36), 'B': (0.15, -0.12)}   # mm off register per screen
h = None


def boot(w_mm, h_mm, seed=1, layers=('line', 'Y', 'G', 'B'), print_w=None):
    """set the canvas (drawn in mm units) before hand.py is imported, return (hand module, Front).
    print_w: the printed width in mm when it differs from the drawing's w_mm (the art is then scaled up, still 94 px/cm)"""
    global h, PXMM
    PXMM *= (print_w or w_mm) / w_mm
    os.environ['R'] = str(PXMM)
    os.environ['UW'], os.environ['UH'] = str(int(w_mm)), str(int(h_mm))
    os.environ['MINW'] = '1.1'                        # the thinnest stroke: 1.1 mm (10 px at print)
    import hand as _h
    h = _h
    _h.margin.__defaults__ = (int(round(46 * PXMM / 9.4)),)     # 46 px at print = 4.9 mm, whatever the draft size
    F = _front_class(_h)
    return _h, F(seed, layers)


def _hand_outline(kind, rng, splay=1.0):
    """the back's hand shapes (art-crowd-tour/gen.py): v across, u along the fingers, 0 = wrist"""
    extra = []
    if kind == 'open':
        fl = [0.36, 0.47, 0.50, 0.42]
        fv = [-0.24, -0.08, 0.08, 0.23]
        pts = [(-0.27, 0.0), (-0.31, 0.22)]
        fw = 0.16
        for i in range(4):
            ang = (i - 1.5) * 0.12 * splay + rng.gauss(0, 0.04)
            bx, by = fv[i], 0.42
            L = fl[i] * rng.uniform(0.9, 1.08)
            tip = (bx + math.sin(ang) * L, by + math.cos(ang) * L)
            pts.append((bx - fw / 2 + math.sin(ang) * 0.05, by + 0.04))
            pts.append((tip[0] - fw * 0.45 * math.cos(ang), tip[1] - 0.05))
            pts.append((tip[0] + math.sin(ang) * 0.04, tip[1] + 0.03))
            pts.append((tip[0] + fw * 0.45 * math.cos(ang), tip[1] - 0.05))
            pts.append((bx + fw / 2 + math.sin(ang) * 0.05, by + 0.02))
        pts += [(0.31, 0.36), (0.47, 0.5), (0.53, 0.47), (0.36, 0.2), (0.27, 0.0)]
        return pts, extra
    if kind == 'fist':
        pts = [(-0.27, 0.0), (-0.32, 0.25), (-0.31, 0.47), (-0.18, 0.56), (0.0, 0.57), (0.18, 0.56), (0.33, 0.45),
               (0.36, 0.22), (0.27, 0.0)]
        for v in (-0.15, 0.02, 0.17):
            extra.append([(v, 0.56), (v + 0.02, 0.44)])
        return pts, extra
    if kind == 'peace':
        pts = [(-0.27, 0.0), (-0.32, 0.25), (-0.30, 0.44), (-0.12, 0.47), (-0.20, 0.95), (-0.12, 1.0), (-0.03, 0.95),
               (-0.01, 0.5), (0.04, 0.95), (0.12, 1.0), (0.19, 0.93), (0.12, 0.46), (0.30, 0.42), (0.35, 0.2), (0.27, 0.0)]
        extra.append([(-0.28, 0.44), (-0.05, 0.40)])
        return pts, extra
    pts = [(-0.27, 0.0), (-0.33, 0.3), (-0.25, 0.62), (0.0, 0.7), (0.22, 0.6), (0.3, 0.4), (0.45, 0.42), (0.36, 0.15),
           (0.27, 0.0)]
    return pts, extra


def _front_class(H):
    class Front(H.Art):
        def draw_hand(self, pos, ang, size, kind, lw, rng=None, mirror=False, layer='line'):
            """pos = wrist, ang = where the fingers point (radians), size = hand length (mm)"""
            rng = rng or self.rng
            ca, sa = math.cos(ang), math.sin(ang)
            m = -1 if mirror else 1

            def T(v, u):
                v *= m
                return (pos[0] + u * size * ca - v * size * sa, pos[1] + u * size * sa + v * size * ca)
            pts, extra = _hand_outline(kind, rng)
            p = self.hand([T(v, u) for v, u in pts], wob=size * 0.015, trem=size * 0.008, rng=rng, step=0.5)
            self.knock(p)
            self.ink(p, lw, layer=layer, rng=rng, a0=1.0, a1=2.0, redraw=0.08)
            for e in extra:
                self.line([T(v, u) for v, u in e], lw * 0.9, layer=layer, rng=rng, wob=size * 0.01, trem=0)
            return T

        def stroke(self, pts, w, layer='line', rng=None, **kw):
            """a plain hand line, softer wobble for small work"""
            kw.setdefault('wob', 0.25)
            kw.setdefault('trem', 0.18)
            return self.line(pts, w, layer=layer, rng=rng, **kw)

        def shape(self, pts, w, layer='line', rng=None, fill=None, knock=True, **kw):
            """a closed hand shape: knocked out of what's behind, loosely filled on a spot screen, then outlined"""
            rng = rng or self.rng
            p = self.hand(pts, closed=True, wob=kw.pop('wob', 0.25), trem=kw.pop('trem', 0.2), rng=rng, step=0.5)
            if knock:
                self.knock(p)
            if fill:
                self.blob(pts, fill, rng=rng, scale=(0.96, 1.02), jit=0.03, shift=0.3, gap=kw.pop('gap', 0.25))
            self.ink(p, w, layer=layer, closed=True, rng=rng, a0=0.8, a1=1.6, pv=0.14, **kw)
            return p
    return Front


def save(art, gen_file, order=('Y', 'G', 'B', 'line'), shifts=None, palette=None, crops=()):
    """finish the inks (spread, register, knockout, clean), composite, write draft.png or art.png"""
    from PIL import Image
    out_dir = os.path.dirname(os.path.abspath(gen_file))
    order = [k for k in order if k in art.L]
    inks = art.finish(order=order, shifts={k: v for k, v in (shifts or SHIFT).items() if k in art.L}, spread_amt=0.16)
    rgba = h.composite(inks, palette or PAL, order)
    del inks
    if DRAFT:
        bg = Image.new('RGBA', rgba.size, h.hexrgb(TEE) + (255,))
        bg.alpha_composite(rgba)
        bg = bg.convert('RGB')
        s = min(1.0, 1100 / max(bg.size))
        bg.resize((int(bg.width * s), int(bg.height * s)), Image.LANCZOS).save(os.path.join(out_dir, 'draft.png'))
        for i, (x, y) in enumerate(crops):           # mm, the centre of a 1:1-at-print crop (half res, shown 2x)
            X, Y = int(x * PXMM) - 160, int(y * PXMM) - 120
            bg.crop((X, Y, X + 320, Y + 240)).resize((640, 480), Image.NEAREST).save(os.path.join(out_dir, f'crop-{i}.png'))
        print('draft', bg.size)
    else:
        p = os.path.join(out_dir, 'art.png')
        rgba.save(p, optimize=True)
        print('art', rgba.size)
        del rgba
        subprocess.run([sys.executable, os.path.join(HERE, 'check.py'), 'verify', p])
