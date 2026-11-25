# heat.py: hand-cut heat bands for the 02 i am a party fronts, on the art-agent pen (hand.py, copied here).
# Every band is its own hand-drawn shape on its own screen, nested like a reduction linocut or riso separation, a little
# off register. Nothing is blurred and thresholded: that smooth thermal look is what read as "AI-ish".
#
# Units: 30 per cm of print. R=1 draft (30 px/cm); the final is 94 px/cm (R = 94/30).
#   import heat; H = heat.setup(w_cm, h_cm)     # call before anything else; returns the hand module
import os, sys, math, json, random, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
FONTS = os.path.join(ROOT, 'pipeline', 'fonts')
U = 30.0                                  # units per cm
FULL_R = 94.0 / U

INK = {   # the back's inks, lifted so they hold on the black shirt
    'violet': '#5B1F8E', 'magenta': '#A3217E', 'red': '#DC3D4B', 'orange': '#F2802A',
    'amber': '#F7C24D', 'cream': '#F6EFD2', 'blue': '#4C66F5', 'night': '#2A1450',
}
GROUND = '#151515'
H = None
FINAL = False


def setup(w_cm, h_cm):
    """size the canvas (cm of print) and import the pen. R env: '1'/'2' draft, unset = final"""
    global H, FINAL
    r = os.environ.get('R')
    FINAL = r is None or r == 'full'
    os.environ['R'] = str(FULL_R if FINAL else float(r))
    os.environ['UW'] = str(int(round(w_cm * U)))
    os.environ['UH'] = str(int(round(h_cm * U)))
    os.environ.setdefault('MINW', '3.4')   # about 1.1 mm
    sys.path.insert(0, HERE)
    import hand
    H = hand
    return hand


# ------------------------------------------------------------------ shapes
def rot(pts, ang, cx=0.0, cy=0.0, ox=0.0, oy=0.0, s=1.0):
    """rotate pts (local) by ang radians about (cx, cy), scale, then move to (ox, oy)"""
    c, sn = math.cos(ang), math.sin(ang)
    return [(ox + s * ((x - cx) * c - (y - cy) * sn), oy + s * ((x - cx) * sn + (y - cy) * c)) for x, y in pts]


def tube_poly(spine, widths, s0=0.0, s1=1.0, cap=True):
    """closed outline of a limb along spine (units) with widths (interpolated along it) for the part s0..s1 of its
    length, round-capped at the ends"""
    s = H.cumlen(spine)
    L = s[-1] or 1.0
    k = len(widths) - 1
    keep = [(p, si / L) for p, si in zip(spine, s) if s0 * L <= si <= s1 * L]
    if len(keep) < 2:
        return []
    pts = [p for p, _ in keep]
    nrm = H.normals(pts)
    left, right, ws = [], [], []
    for (x, y), (nx, ny), (_, t) in zip(pts, nrm, keep):
        u = t * k
        i = min(int(u), k - 1)
        f = u - i
        w = (widths[i] * (1 - f) + widths[i + 1] * f) / 2
        ws.append(w)
        left.append((x + nx * w, y + ny * w))
        right.append((x - nx * w, y - ny * w))
    def capr(p, n, w, sign):
        a0 = math.atan2(n[1], n[0])
        return [(p[0] + math.cos(a0 + sign * math.pi * j / 8) * w, p[1] + math.sin(a0 + sign * math.pi * j / 8) * w)
                for j in range(1, 8)]
    end = capr(pts[-1], nrm[-1], ws[-1], -1) if cap else []
    start = capr(pts[0], (-nrm[0][0], -nrm[0][1]), ws[0], -1) if cap else []
    return left + end + right[::-1] + start


def nested_tube(art, ctrl, widths, bands, rng=None, wob=0.7, trem=0.5):
    """a limb in heat bands. bands: [(layer, width_scale, cut_start, cut_end), ...] outer to inner; each band is its own
    hand-drawn shape (own wobble), cut back from the ends where the limb runs cooler (fingertips, the elbow)"""
    rng = rng or art.rng
    for layer, sc, c0, c1 in bands:
        sp = art.hand(ctrl, wob=wob, trem=trem, rng=rng)
        poly = tube_poly(sp, [w * sc * rng.uniform(0.94, 1.06) for w in widths], c0, 1 - c1)
        if len(poly) > 2:
            art.fill(poly, layer)


def wobble_shape(pts, rng, amt, n=None):
    """a closed shape redrawn by hand: resampled, control points jittered, splined"""
    pts = list(pts)
    if n:
        pts = H.resample(pts + [pts[0]], n)
    pts = [(x + rng.gauss(0, amt), y + rng.gauss(0, amt)) for x, y in pts]
    return H.catmull(pts, closed=True, step=1.2)


def nested_shape(art, pts, bands, hot, rng=None, wob=1.2, n=None):
    """a body part in heat bands: bands [(layer, scale), ...] outer to inner, each the outline shrunk toward the hot
    point and redrawn by hand"""
    rng = rng or art.rng
    hx, hy = hot
    for b in bands:
        layer, sc = b[0], b[1]
        dx, dy = (b[2], b[3]) if len(b) > 3 else (0, 0)
        sh = [(hx + (x - hx) * sc + dx, hy + (y - hy) * sc + dy) for x, y in pts]
        art.fill(wobble_shape(sh, rng, wob, n), layer)


def gouge(art, ctrl, w, rng=None, layer='cut', **kw):
    """a linocut gouge (drawn on the 'cut' screen, taken out of every ink at the end)"""
    rng = rng or art.rng
    p = art.hand(ctrl, wob=kw.pop('wob', 0.4), trem=kw.pop('trem', 0.3), rng=rng)
    art.ink(p, w, layer=layer, rng=rng, a0=kw.pop('a0', 1.2), a1=kw.pop('a1', 3.0), pv=kw.pop('pv', 0.25), **kw)


# ------------------------------------------------------------------ finishing
def finish(art, order, shifts=None, spread_amt=0.16, cut='cut'):
    """print physics on every screen (inner bands knock out outer ones), the gouges taken out of all of them"""
    from PIL import ImageChops
    inks = art.finish(order=order, shifts=shifts or {}, spread_amt=spread_amt)
    if cut in art.L:
        c = H.spread(art.L[cut], random.Random(5), amt=0.12)
        for k in order:
            inks[k] = H.clean(ImageChops.subtract(inks[k], c))
    return inks


def out(name, inks, palette, order, folder):
    """final: art.png (transparent, print size). draft: draft.png on the shirt colour"""
    rgba = H.composite(inks, palette, order)
    if FINAL:
        p = os.path.join(folder, 'art.png')
        rgba.save(p, optimize=True)
        print('saved', p, rgba.size)
    else:
        from PIL import Image
        bg = Image.new('RGBA', rgba.size, H.hexrgb(GROUND) + (255,))
        bg.alpha_composite(rgba)
        p = os.path.join(folder, name)
        bg.convert('RGB').save(p)
        print('saved', p, rgba.size)
    return rgba


def pair(folder, shirt='e'):
    subprocess.run([sys.executable, os.path.join(ROOT, 'pipeline/art/fronts/pair.py'), shirt,
                    os.path.join(folder, 'art.png'), os.path.join(folder, 'placement.json'),
                    os.path.join(folder, 'pair.png')], check=True)
