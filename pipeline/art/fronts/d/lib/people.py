"""people for the d fronts, drawn the way the back draws them but closer: solid ink silhouettes side-on (walkers,
standers, friends holding hands) and top-down figures (head, hair, shoulders, arms) for the crowd seen from above.
Every one is built from parts with its own proportions, clothes and gesture, so no two are the same."""
import math
import hand
from hand import TAU


def _poly(art, pts, layer, value=255):
    art.D[layer].polygon(hand.P(pts), fill=value)


def _ell(art, x, y, rx, ry, layer, value=255, rot=0.0):
    pts = [(x + math.cos(t) * rx * math.cos(rot) - math.sin(t) * ry * math.sin(rot),
            y + math.cos(t) * rx * math.sin(rot) + math.sin(t) * ry * math.cos(rot)) for t in (i * TAU / 18 for i in range(18))]
    _poly(art, pts, layer, value)


def _limb(art, a, b, w0, w1, layer, rng, bend=0.0):
    """a tapered limb from a to b, bent a little at the middle"""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1
    m = (mx - dy / L * bend, my + dx / L * bend)
    sp = hand.catmull([a, m, b], step=1.0)
    N = hand.normals(sp)
    n = len(sp)
    left = [(p[0] + q[0] * (w0 + (w1 - w0) * i / (n - 1)) / 2, p[1] + q[1] * (w0 + (w1 - w0) * i / (n - 1)) / 2) for i, (p, q) in enumerate(zip(sp, N))]
    right = [(p[0] - q[0] * (w0 + (w1 - w0) * i / (n - 1)) / 2, p[1] - q[1] * (w0 + (w1 - w0) * i / (n - 1)) / 2) for i, (p, q) in enumerate(zip(sp, N))]
    _poly(art, left + right[::-1], layer)
    _ell(art, b[0], b[1], w1 * 0.55, w1 * 0.55, layer)
    _ell(art, a[0], a[1], w0 * 0.5, w0 * 0.5, layer)


def silhouette(art, x, yf, h, rng, face=1, layer='key', stride=None, kind=None, arm_to=None, arm2_to=None, phone=False):
    """a person side-on (or three-quarter), solid ink. x = between the feet, yf = the ground, h = height in units.
    face = +1 walking right, -1 left. arm_to: where the near hand goes (to hold a friend's hand).
    Returns {'hand': (x, y) of the free near hand at rest, 'shoulder': (x, y)}"""
    kind = kind or rng.choice(('jacket', 'tee', 'dress', 'hoodie', 'shirt', 'long'))
    stride = rng.uniform(0.0, 1.0) if stride is None else stride
    hr = h * rng.uniform(0.064, 0.072)                 # head radius
    lean = face * h * rng.uniform(0.0, 0.03)
    hx, hy = x + lean, yf - h + hr
    sh_y = yf - h * 0.81
    hip_y = yf - h * 0.47
    sw = h * rng.uniform(0.11, 0.135)                  # half shoulder depth side-on
    sx = x + lean * 0.7
    # legs: a stride
    s = h * 0.15 * stride
    lw = h * rng.uniform(0.07, 0.085)
    feet = [(x + face * s, yf), (x - face * s * 0.9, yf - (h * 0.015 if stride > 0.4 else 0))]
    for fx, fy in feet:
        _limb(art, (x + lean * 0.3, hip_y), (fx, fy - lw * 0.4), lw * 1.25, lw * 0.75, layer, rng, bend=face * h * 0.01)
        _poly(art, [(fx - face * lw * 0.4, fy - lw * 0.75), (fx + face * lw * 1.5, fy - lw * 0.55), (fx + face * lw * 1.6, fy),
                    (fx - face * lw * 0.5, fy)], layer)           # the shoe
    # torso by clothes
    hw = h * 0.1
    if kind == 'dress':
        hem = yf - h * rng.uniform(0.2, 0.32)
        _poly(art, [(sx - sw * 0.8, sh_y), (sx + sw * 0.8, sh_y), (x + h * 0.16, hem), (x - h * 0.15, hem)], layer)
    elif kind == 'long':          # a long open shirt or overshirt, hanging past the hips
        _poly(art, [(sx - sw, sh_y - h * 0.01), (sx + sw, sh_y), (x + hw * 1.15, hip_y + h * 0.1), (x - hw * 1.2, hip_y + h * 0.12)], layer)
    else:
        bot = hip_y + h * (0.05 if kind in ('jacket', 'hoodie') else 0.02)
        _poly(art, [(sx - sw, sh_y), (sx + sw * 0.95, sh_y + h * 0.005), (x + hw, bot), (x - hw * 1.05, bot)], layer)
        if kind == 'hoodie':      # the hood lying on the back
            _ell(art, sx - face * sw * 0.8, sh_y + h * 0.02, h * 0.06, h * 0.045, layer)
    # neck and head
    _poly(art, [(hx - h * 0.03, hy + hr * 0.6), (hx + h * 0.03, hy + hr * 0.6), (sx + h * 0.035, sh_y + 1), (sx - h * 0.035, sh_y + 1)], layer)
    _ell(art, hx, hy, hr * 0.95, hr * 1.08, layer)
    _poly(art, [(hx + face * hr * 0.8, hy - hr * 0.1), (hx + face * hr * 1.22, hy + hr * 0.25), (hx + face * hr * 0.8, hy + hr * 0.45)], layer)  # nose
    hair = rng.choice(('short', 'bun', 'long', 'cap', 'curls', 'tied'))
    if hair == 'bun':
        _ell(art, hx - face * hr * 0.55, hy - hr * 0.95, hr * 0.5, hr * 0.45, layer)
    elif hair == 'long':
        _poly(art, [(hx - face * hr * 0.2, hy - hr), (hx - face * hr * 1.15, hy - hr * 0.2), (hx - face * hr * 1.0, hy + hr * 2.4),
                    (hx - face * hr * 0.2, hy + hr * 1.9)], layer)
    elif hair == 'cap':
        _poly(art, [(hx - face * hr, hy - hr * 0.35), (hx + face * hr * 1.75, hy - hr * 0.5), (hx + face * hr * 1.6, hy - hr * 0.2),
                    (hx - face * hr, hy - hr * 0.1)], layer)
    elif hair == 'curls':
        _ell(art, hx - face * hr * 0.2, hy - hr * 0.25, hr * 1.2, hr * 1.1, layer)
    elif hair == 'tied':
        _limb(art, (hx - face * hr * 0.8, hy - hr * 0.5), (hx - face * hr * 1.8, hy + hr * 0.7), hr * 0.6, hr * 0.35, layer, rng)
    # arms
    aw = h * rng.uniform(0.048, 0.058)
    shoulder = (sx, sh_y + h * 0.03)
    def arm(to, side):
        if to is None:
            sw_ = -side * face * stride * h * 0.12
            to = (sx + sw_ + face * h * 0.02, hip_y + h * 0.06)
        el = ((shoulder[0] + to[0]) / 2 - face * h * 0.015, (shoulder[1] + to[1]) / 2 + h * 0.01)
        _limb(art, shoulder, el, aw * 1.25, aw, layer, rng)
        _limb(art, el, to, aw, aw * 0.85, layer, rng)
        return to
    hand_far = arm(arm2_to, -1) if arm2_to is not False else None
    if phone:                    # a phone held up, lit side away from us: a small dark slab above the head
        px_, py_ = hx + face * h * 0.12, hy - h * 0.16
        _limb(art, shoulder, (sx + face * h * 0.08, sh_y - h * 0.05), aw * 1.25, aw, layer, rng)
        _limb(art, (sx + face * h * 0.08, sh_y - h * 0.05), (px_, py_ + h * 0.03), aw, aw * 0.85, layer, rng)
        _poly(art, [(px_ - h * 0.02, py_ - h * 0.045), (px_ + h * 0.025, py_ - h * 0.05), (px_ + h * 0.025, py_ + h * 0.035),
                    (px_ - h * 0.02, py_ + h * 0.04)], layer)
        near = (px_, py_)
    else:
        near = arm(arm_to, 1)
    return {'hand': near, 'shoulder': shoulder, 'head': (hx, hy), 'hr': hr}


def topdown(art, x, y, s, rng, ang, layer='key', arms=None, kind=None):
    """a person seen from straight above, facing angle ang (radians, 0 = +x). s = shoulder width in units.
    Head with its hair, shoulders as a soft bar, arms as given: list of (hand_x, hand_y) or None to rest."""
    ca, sa = math.cos(ang), math.sin(ang)
    def T(u, v):                       # u forward, v to the left side
        return (x + u * ca - v * sa, y + u * sa + v * ca)
    hr = s * rng.uniform(0.22, 0.27)
    # shoulders: a rounded bar, slightly behind the head centre
    sd = s * rng.uniform(0.2, 0.26)
    bar = [T(-sd * 0.9, -s / 2), T(sd * 0.5, -s / 2 + s * 0.04), T(sd * 0.7, 0), T(sd * 0.5, s / 2 - s * 0.04), T(-sd * 0.9, s / 2),
           T(-sd * 1.2, 0)]
    pts = hand.catmull(bar, closed=True, step=1.0)
    _poly(art, pts, layer)
    if (kind or rng.random()) == 'bag' or (kind is None and rng.random() < 0.18):     # a backpack on the back
        _poly(art, [T(-sd * 1.0, -s * 0.24), T(-sd * 2.4, -s * 0.22), T(-sd * 2.5, s * 0.2), T(-sd * 1.0, s * 0.22)], layer)
    # head: hair from above (the crown, a parting, a bun or a cap brim pointing forward)
    hx, hy = T(sd * 0.05, rng.uniform(-0.03, 0.03) * s)
    return {'T': T, 'head': (hx, hy), 'hr': hr, 'sd': sd}


def mini(art, x, yf, h, rng, face=1, layer='key', stride=None, bag=None, arm_to=None):
    """a small person (15-30 units tall) as one solid silhouette, its parts never thinner than the 1 mm minimum:
    head, a tapered body by clothes, two legs in stride, the near arm swinging or reaching (arm_to)"""
    m = hand.MINW * 1.05
    stride = rng.uniform(0.2, 1.0) if stride is None else stride
    hr = max(h * 0.1, m * 0.95)
    hx, hy = x + face * h * 0.02, yf - h + hr
    sh, hip = yf - h * 0.8, yf - h * 0.46
    sw = max(h * 0.13, m * 0.9)
    kind = rng.random()
    if kind < 0.25:   # a long coat or dress
        _poly(art, [(x - sw, sh), (x + sw, sh), (x + sw * 1.35, yf - h * 0.24), (x - sw * 1.3, yf - h * 0.24)], layer)
    else:
        _poly(art, [(x - sw, sh), (x + sw, sh), (x + sw * 0.85, hip + h * 0.04), (x - sw * 0.85, hip + h * 0.04)], layer)
    s = h * 0.17 * stride
    for fx in (x + face * s, x - face * s * 0.8):
        _poly(art, [(x - m * 0.55, hip), (x + m * 0.55, hip), (fx + m * 0.55, yf), (fx - m * 0.55, yf)], layer)
        _poly(art, [(fx - m * 0.5, yf - m * 0.8), (fx + face * m * 1.3, yf - m * 0.6), (fx + face * m * 1.3, yf), (fx - m * 0.5, yf)], layer)
    _poly(art, [(hx - m * 0.5, hy + hr * 0.5), (hx + m * 0.5, hy + hr * 0.5), (x + m * 0.5, sh + 1), (x - m * 0.5, sh + 1)], layer)
    _ell(art, hx, hy, hr, hr * 1.1, layer)
    if rng.random() < 0.35:   # hair: a bun or long hair or a cap
        r = rng.random()
        if r < 0.4:
            _ell(art, hx - face * hr * 0.5, hy - hr * 0.9, hr * 0.55, hr * 0.5, layer)
        elif r < 0.75:
            _poly(art, [(hx - face * hr * 0.2, hy - hr), (hx - face * hr * 1.2, hy), (hx - face * hr * 1.05, hy + hr * 2.0), (hx - face * hr * 0.1, hy + hr * 1.5)], layer)
        else:
            _poly(art, [(hx - face * hr, hy - hr * 0.4), (hx + face * hr * 1.9, hy - hr * 0.5), (hx + face * hr * 1.8, hy - hr * 0.05), (hx - face * hr, hy)], layer)
    if bag or (bag is None and rng.random() < 0.3):      # a backpack
        _poly(art, [(x - face * sw * 0.8, sh + h * 0.02), (x - face * (sw + h * 0.1), sh + h * 0.04), (x - face * (sw + h * 0.11), hip - h * 0.02), (x - face * sw * 0.8, hip)], layer)
    to = arm_to or (x + face * h * rng.uniform(-0.06, 0.12), hip + h * 0.06)
    _limb(art, (x + face * sw * 0.3, sh + m * 0.4), to, m, m, layer, rng)
    return to
