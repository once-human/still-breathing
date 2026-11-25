# python3 pipeline/photo_place.py <place> [width]                                   (numpy, pillow)
# A place behind the person made from a real photograph: a Poly Haven 360 degree HDRI (CC0) of a real room, laid
# onto that room's own floor, walls and ceiling and seen from the viewer's camera as it walks its ring round the
# person (the same camera as pipeline/stage.py), so the floor stays put under the feet as the camera turns.
#   - the room: the photo was taken at height H; each wall is a plane (the photo's azimuth of its normal, its
#     distance), measured from where the floor and the ceiling meet it in the photo
#   - the lens: 85 mm f/5.6 focused on the person, as a blur that grows with distance
#   - the lights: the bright parts of the photo (windows, softboxes) become the viewer's area lights at the same
#     place, size and brightness, printed for src/lib/viewer/scene.ts; everything is exposed so a white tee's front
#     reads 0.8 in the light of the whole room
# Writes public/tee/stage/<place>.webp through pipeline/stage_post.py.
# ROWS=r0,r1 (with width 16384, BAND_ROWS in stage_post.py): only the band the viewer's camera can see, sharp (no lens
# blur) and from the 16k photo, written as public/tee/stage/<place>-band.webp: what the viewer shows behind the
# person. The whole picture (4096) stays for the light on the person and the rest of the sphere.
# The .hdr is read by Blender (pipeline/hdr2npy.py; $BLENDER, default blender) into ~/.cache/polyhaven once.
import json, math, os, subprocess, sys, urllib.request
import numpy as np

PLACE = sys.argv[1]
W = int(sys.argv[2]) if len(sys.argv) > 2 else 4096
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.expanduser("~/.cache/polyhaven")

RING, EYE = 2.857, 1.1          # the viewer camera: its ring round the person, its height over the floor
LENS, FSTOP, FOCUS = 0.085, 5.6, 2.8
FLOOR = 0.35                    # scene.ts FLOOR: three y of the floor

# az: the photo's azimuth in degrees (0 at its left edge, growing to the right); el: degrees over the horizon.
# back: the photo's azimuth that stands straight behind the person in the front view (viewer -z).
# walls: (azimuth of the wall's normal, distance from the camera, m). lights: az0, az1, el0, el1 box, how far (m;
# None: on the wall behind), name. Heights: the photo's camera H over the floor, the ceiling C.
PLACES = {
    # a daylight photo studio in an old building: paper rolls on the wall, a tall window, an octabox and a strip
    # softbox on stands, folding screens, a bathtub prop; the window is ahead of the person, the strip box behind
    "studio": dict(hdri="pav_studio_03", H=1.6, C=2.85, back=5,
                   walls=[(93, 1.49), (183, 2.13), (273, 3.8), (3, 2.66)],
                   lights=[(139, 181, -20, 46, None, "window"), (224, 242, -12, 33, None, "window2"),
                           (204, 228, -13, 10, 2.45, "octa"), (300, 325, 3, 35, 2.05, "strip")]),
    # a sunny flat: a corner window with sheer curtains and a big clear window, the sun across the floorboards,
    # a sofa against a plaster wall, a low bed, plants, a small kitchen; the curtained window lights the front
    "window": dict(hdri="brown_photostudio_04", H=1.5, C=3.05, back=80,
                   walls=[(195, 2.5), (15, 4.9), (102, 3.07), (282, 2.85)],
                   lights=[(181, 221, -17, 21, None, "window"), (238, 300, -32, 34, None, "curtain"),
                           (150, 220, -62, -27, None, "sunfloor")]),
}
P = PLACES[PLACE]


def read_hdr(path):
    """Radiance .hdr (new-style RLE) to float32 HxWx3"""
    b = open(path, "rb").read()
    i = 0
    while True:
        j = b.index(b"\n", i); line = b[i:j]; i = j + 1
        if line.startswith(b"-Y"):
            _, h, _, w = line.split(); h, w = int(h), int(w); break
    out = np.empty((h, w, 4), np.uint8)
    mv = memoryview(b)
    for y in range(h):
        assert b[i] == 2 and b[i + 1] == 2, "old-style hdr"
        i += 4
        for c in range(4):
            x = 0; row = out[y, :, c]
            while x < w:
                n = b[i]; i += 1
                if n > 128:
                    n -= 128; row[x:x + n] = b[i]; i += 1
                else:
                    row[x:x + n] = np.frombuffer(mv[i:i + n], np.uint8); i += n
                x += n
    e = out[..., 3].astype(np.int32)
    f = np.where(e > 0, np.ldexp(1.0, e - 136), 0.0).astype(np.float32)
    return out[..., :3].astype(np.float32) * f[..., None]


ROWS = os.environ.get("ROWS")
RES = "16k" if ROWS else "8k"


def hdri(name):
    os.makedirs(CACHE, exist_ok=True)
    npy = os.path.join(CACHE, f"{name}_{RES}.npy"); src = os.path.join(CACHE, f"{name}_{RES}.hdr")
    if os.path.exists(npy): return np.load(npy)
    if not os.path.exists(src):
        req = urllib.request.Request(f"https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/{RES}/{name}_{RES}.hdr",
                                     headers={"User-Agent": "stage-builder"})
        with urllib.request.urlopen(req) as r, open(src, "wb") as f:
            while True:
                c = r.read(1 << 22)
                if not c: break
                f.write(c)
    subprocess.run([os.environ.get("BLENDER", "blender"), "-b", "--factory-startup", "-P", os.path.join(HERE, "hdr2npy.py"), "--", src, npy], check=True)
    return np.load(npy)


img = hdri(P["hdri"]); HH, HW, _ = img.shape
LUM = np.array([0.2126, 0.7152, 0.0722], np.float32)
H, C, BACK = P["H"], P["C"], P["back"]


def az_to_phi(az):
    """the photo's azimuth to the viewer's phi (atan2(x, z) in three; the front view's background, -z, is pi)"""
    u = (az - BACK) / 360.0
    return (0.5 - u) * 2 * math.pi


def dir3(phi, el):
    return np.stack([np.sin(phi) * np.cos(el), np.sin(el), np.cos(phi) * np.cos(el)], -1)


WALLS = [(np.array([math.sin(az_to_phi(a)), 0.0, math.cos(az_to_phi(a))]), d) for a, d in P["walls"]]


def hit(o, d):
    """first hit of the rays o + t d (floor at y 0, camera point at (0, H, 0)) on the room: floor, ceiling, walls"""
    t = np.full(d.shape[:-1], 1e9, np.float32)
    dy = d[..., 1]
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(dy < -1e-6, np.minimum(t, (0 - o[..., 1]) / dy), t)
        t = np.where(dy > 1e-6, np.minimum(t, (C - o[..., 1]) / dy), t)
        for n, dist in WALLS:
            nd = d @ n; no = o @ n
            t = np.where(nd > 1e-6, np.minimum(t, (dist - no) / nd), t)
    return t


def sample(q):
    """the photo, bilinear, in the direction q (three, from the camera point)"""
    phi = np.arctan2(q[..., 0], q[..., 2]); el = np.arctan2(q[..., 1], np.hypot(q[..., 0], q[..., 2]))
    u = (0.5 - phi / (2 * math.pi)) + BACK / 360.0
    x = (u % 1.0) * HW - 0.5; y = (0.5 - el / math.pi) * HH - 0.5
    x0 = np.floor(x).astype(np.int64); y0 = np.clip(np.floor(y).astype(np.int64), 0, HH - 2)
    fx = (x - x0)[..., None]; fy = np.clip(y - y0, 0, 1)[..., None]
    x0 %= HW; x1 = (x0 + 1) % HW
    return ((img[y0, x0] * (1 - fx) + img[y0, x1] * fx) * (1 - fy) + (img[y0 + 1, x0] * (1 - fx) + img[y0 + 1, x1] * fx) * fy)


# ---------- the panorama the viewer sees, rays from its camera ring ----------
Hh = W // 2
R0, R1 = (int(x) for x in ROWS.split(",")) if ROWS else (0, Hh)
out = np.zeros((R1 - R0, W, 3), np.float32); depth = np.zeros((R1 - R0, W), np.float32)
SS = [(0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)]
for r0 in range(R0, R1, 64 if W <= 8192 else 16):
    rows = np.arange(r0, min(r0 + (64 if W <= 8192 else 16), R1))
    acc = 0; dep = 0
    for sx, sy in SS:
        u = (np.arange(W) + sx) / W; v = (rows + sy) / Hh
        phi = ((0.5 - u) * 2 * math.pi)[None, :].repeat(len(rows), 0); el = ((0.5 - v) * math.pi)[:, None].repeat(W, 1)
        d = dir3(phi, el).astype(np.float32)
        o = np.stack([-RING * np.sin(phi), np.full_like(phi, EYE), -RING * np.cos(phi)], -1).astype(np.float32)
        t = np.maximum(hit(o, d), 0.88 * RING)
        p = o + d * t[..., None]
        acc = acc + sample(p - np.array([0, H, 0], np.float32)); dep = dep + t
    out[rows - R0] = acc / len(SS); depth[rows - R0] = dep / len(SS)
print("projected", W, "x", Hh)

# ---------- the lens: blur by the circle of confusion at each depth, from a stack of disc blurs ----------
coc = (LENS / FSTOP) * np.abs(1 / FOCUS - 1 / depth) * W / (2 * math.pi) / 2   # radius, px


def disc(a, R):
    if R < 0.3: return a
    r = int(R) + 2; yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    k = np.clip(R + 0.5 - np.hypot(xx, yy), 0, 1).astype(np.float32); k /= k.sum()
    K = np.zeros(a.shape[:2], np.float32); K[:2 * r + 1, :2 * r + 1] = k; K = np.fft.rfft2(np.roll(K, (-r, -r), (0, 1)))
    return np.stack([np.fft.irfft2(np.fft.rfft2(a[..., c]) * K, s=a.shape[:2]) for c in range(3)], -1).astype(np.float32)


radii = [0, 1, 2, 3, 4.5, 6.5] if not ROWS else [0]   # the band the viewer shows is sharp
stack = [disc(out, R) for R in radii]
cc = np.clip(coc, 0, radii[-1]); res = np.zeros_like(out)
for i in range(len(radii) - 1):
    a, b = radii[i], radii[i + 1]
    w = np.clip((cc - a) / (b - a), 0, 1)
    m = ((cc >= a) & (cc <= b))[..., None]
    res = np.where(m, stack[i] * (1 - w[..., None]) + stack[i + 1] * w[..., None], res)
out = np.maximum(res, 0) if len(radii) > 1 else out
print("lens: blur radius px, median", round(float(np.median(coc)), 2), "max", round(float(coc.max()), 2))

# ---------- exposure: a white tee's front reads 0.8 in the whole room's light ----------
ys = (np.arange(HH) + 0.5) / HH; els = (0.5 - ys) * math.pi
dw = (2 * math.pi / HW) * (math.pi / HH) * np.cos(els)                        # solid angle of a photo pixel
azs = (np.arange(HW) + 0.5) / HW * 360
front = BACK + 180                                                            # the person faces the camera
cosf = np.cos(els)[:, None] * np.cos(np.radians(azs - front))[None, :]       # normal level, toward the camera
E = float(np.sum((img @ LUM) * np.clip(cosf, 0, None) * dw[:, None]))
K = 0.8 * math.pi / (0.8 * E)                                                 # white (0.8): 0.8 E K / pi = 0.8
print("front irradiance", round(E, 3), "exposure", round(K, 4))
out *= K
band = (out if ROWS else out[int(Hh * 0.3):int(Hh * 0.62)]) @ LUM
print("background band median", round(float(np.median(band)), 3), "p95", round(float(np.percentile(band, 95)), 3))

# ---------- the lights: the bright parts of the photo, where they are ----------
med = float(np.median(img @ LUM)); thr = 4 * med
lights = []
for az0, az1, e0, e1, dist, name in P["lights"]:
    x0, x1 = int(az0 / 360 * HW), int(az1 / 360 * HW); y0, y1 = int((0.5 - e1 / 180) * HH), int((0.5 - e0 / 180) * HH)
    a = img[y0:y1, x0:x1]; l = a @ LUM; m = l > thr
    if m.sum() < 10: print("no light in", name); continue
    w = dw[y0:y1, None] * m
    flux = (a * w[..., None]).reshape(-1, 3).sum(0)                         # sum L dw over the bright pixels
    omega = float(w.sum())
    yy, xx = np.nonzero(m)
    lw = (l * w)[yy, xx]
    caz = float(np.sum(azs[x0:x1][xx] * lw) / lw.sum()); cel = float(np.sum(np.degrees(els[y0:y1][yy]) * lw) / lw.sum())
    q = dir3(np.array(az_to_phi(caz)), np.array(math.radians(cel)))
    if dist is None:
        dist = float(hit(np.array([0, H, 0], np.float32)[None], q[None].astype(np.float32))[0])
    pos = np.array([0, H, 0]) + q * dist
    spanx = math.radians(np.ptp(azs[x0:x1][xx])) * math.cos(math.radians(cel)) * dist
    spany = math.radians(np.ptp(np.degrees(els[y0:y1][yy]))) * dist
    A = max(spanx * spany, 1e-4)
    # the same light seen from the person: radiance L = flux / omega, area A at that distance; Blender watts P = L pi A
    Lrgb = flux / omega * K
    power = float(Lrgb @ LUM) * math.pi * A
    tint = Lrgb / max(Lrgb.max(), 1e-9)
    lights.append(dict(name=name, pos=[round(float(pos[0]), 2), round(float(pos[1]) + FLOOR, 2), round(float(pos[2]), 2)],
                       size=[round(spanx, 2), round(spany, 2)], power=round(power, 1),
                       tint=[round(float(c), 3) for c in tint]))
world = (out.reshape(-1, 3).mean(0))
print(json.dumps(dict(lights=lights, world=[round(float(c), 3) for c in world]), indent=1))

npy = os.path.join(CACHE, f"{PLACE}_photo{'_band' if ROWS else ''}.npy"); np.save(npy, out.astype(np.float16))
dst = os.path.join(HERE, "..", "public", "tee", "stage", f"{PLACE}{'-band' if ROWS else ''}.webp")
subprocess.run([sys.executable, os.path.join(HERE, "stage_post.py"), PLACE, dst, npy], check=True, env={**os.environ, "BAND": "1" if ROWS else ""})
