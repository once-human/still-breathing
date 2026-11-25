# python3 skin.py <gbuffer dir> <out prefix>      (human.py runs it; numpy + Pillow)
# The person's skin as two maps on MakeHuman's UVs, for the 3D view, the path tracer and the stills:
#   <prefix>-skin.webp     colour (sRGB albedo)
#   <prefix>-skin-n.webp   relief and shine: R, G the normal (tangent space, T = dP/du, B = dP/dv with v down the
#                          image, as three.js and the path tracer build them), B the roughness
# human.py hands over every visible skin texel (2048 square) with its point on the posed body, its normal, the
# body's region weights and its step across the body; everything here is placed by the body itself (the mouth,
# the jaw, each knuckle, the tendons from the wrist to each knuckle). Each texel is the average of four points
# across it, and its relief is the slope across it, so nothing is finer than a texel can show. Features are millimetres and up: knuckle creases, tendons and veins on the back of the hands,
# forearm hair, a short trimmed beard, the lip line, neck creases, the hairline's fade. No pores (they are well
# under a pixel here), no grain.
import sys, os, json
import numpy as np
from PIL import Image

D, OUT = sys.argv[1], sys.argv[2]
z_ = np.load(os.path.join(D, "g.npz"))
RES = int(z_["res"]); YS = z_["ys"].astype(np.int32); XS = z_["xs"].astype(np.int32); G = z_["g"]
LM = {k: np.array(v, np.float64) for k, v in json.load(open(os.path.join(D, "lm.json"))).items()}
print("skin.py texels", len(YS), flush=True)
eyeL, eyeR, jaw = LM["eyeL"], LM["eyeR"], LM["jaw"]
# MakeHuman's mouth joint sits inside the head; the mouth here is the lips themselves, the ears their own centres
_P, _w = G[:, :3].astype(np.float64), G[:, 6:8].astype(np.float64)
mouth = _P[_w[:, 0] > 0.5].mean(0)
EARS = [_P[(_w[:, 1] > 0.5) & (np.sign(_P[:, 0]) == sg)].mean(0) for sg in (1, -1)]
del _P, _w
fwd = np.array([0.0, -1.0, 0.0])
HAIR = np.array([0.013, 0.010, 0.009])
SHE = bool(LM.get("female", np.zeros(1))[0])
HBM = bool(LM.get("hbm", np.zeros(1))[0])        # people.py's bodies: the scalp region is the hairline itself    # human.py says so for a woman: no beard, finer brows, little arm hair,
#                                                 the hair itself a shell over the scalp (the scalp under it dark)
BASE = (0.29, 0.155, 0.094) if SHE else (0.27, 0.142, 0.084)   # Indian browns, linear albedo; hers a shade lighter

def sm(e0, e1, t):
    t = np.clip((t - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def hsh(ix, iy, iz):
    h = (ix * 0x8DA6B343) ^ (iy * 0xD8163841) ^ (iz * 0xCB1AB31F)
    h &= 0xFFFFFFFF; h ^= h >> 13; h = (h * 0x5BD1E995) & 0xFFFFFFFF; h ^= h >> 15
    return h.astype(np.float64) / 4294967296.0


def vnoise(p):
    """smooth value noise in [-1, 1]"""
    i = np.floor(p).astype(np.int64); f = p - i; w = f * f * (3 - 2 * f)
    out = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                c = hsh(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz)
                out = out + c * np.where(dx, w[:, 0], 1 - w[:, 0]) * np.where(dy, w[:, 1], 1 - w[:, 1]) * np.where(dz, w[:, 2], 1 - w[:, 2])
    return out * 2 - 1


def fbm(p, oct=3):
    a, s, t = 1.0, 0.0, 0.0
    for k in range(oct):
        s = s + a * vnoise(p * (2.0 ** k) + 17.3 * k); t += a; a *= 0.5
    return s / t


def along(p, d, k):
    """stretch space k times along the unit direction d (per texel): features long along d"""
    return p - d * (np.sum(p * d, axis=1, keepdims=True) * (1 - 1 / k))


def seg(p, a, b):
    """distance to the segment a-b and the parameter along it"""
    ab = b - a; t = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1), t


def shade(P, N, lips, ears, nails, scalp, handw, hairw=None, flow=None):
    """colour (linear), roughness and relief (metres out of the skin) at these points"""
    n = len(P); x, y, z = P[:, 0], P[:, 1], P[:, 2]
    H = np.zeros(n)                     # relief, metres (out of the skin)
    C = np.tile(np.array(BASE), (n, 1))
    R = np.full(n, 0.5)                 # roughness

    # slow variation of tone and warmth, centimetres across: no texture you can see, only a skin that isn't paint
    C *= (1 + 0.05 * fbm(P * 14.0))[:, None]
    C[:, 0] *= 1 + 0.025 * fbm(P * 22.0 + 5.1)
    C[:, 2] *= 1 - 0.03 * fbm(P * 18.0 + 9.7)
    # skin that breathes: a gentle undulation a few millimetres across, so a highlight breaks the way it does on skin
    H += 0.00004 * fbm(P * 260.0, 2)
    # and its fine surface: the shallow lines skin is crossed by, about a millimetre apart in two directions, too
    # shallow to see as lines, enough that a highlight on skin is broken up and never a smooth sheen
    d1 = np.tile(np.array([0.71, 0.0, 0.71]), (n, 1)); d2 = np.tile(np.array([0.71, 0.0, -0.71]), (n, 1))
    H += 0.000011 * (np.abs(vnoise(along(P * 1300.0, d1, 3.0))) + np.abs(vnoise(along(P * 1300.0, d2, 3.0)) + 0.4) - 0.9)

    # ---------- head ----------
    isHead = (z > mouth[2] - 0.13) & (np.abs(x) < 0.14)
    d = P - mouth
    facing = N @ fwd
    # edges are never ruled lines: a hairline or a beard line wanders a few millimetres
    edge = 0.006 * vnoise(P * 90.0) + 0.003 * vnoise(P * 260.0)
    earD = np.minimum(*(np.linalg.norm((P - e) * np.array([1.0, 1.0, 0.7]), axis=1) for e in EARS))
    # hair: a short cut. MakeHuman's scalp group, a hairline above the brows at the front, clear of the ears by a
    # finger's width, and at the back a nape that fades out over three centimetres. Hers: the scalp under her
    # hair, a hairline a little lower and softer at the front, down to the nape behind the ears
    front = 1 - sm(0.05, 0.1, d[:, 1])
    hl = (0.044, 0.06) if SHE else (0.05, 0.062)
    hairline = 1 - front * (1 - sm(eyeL[2] + hl[0], eyeL[2] + hl[1], z + edge))
    nape = sm(mouth[2] - (0.03 if SHE else 0.012), mouth[2] + (0.0 if SHE else 0.025), z + edge)
    hairv = sm(0.3, 0.6, scalp) * hairline * nape * sm(0.02 if SHE else 0.038, 0.032 if SHE else 0.05, earD + edge) * isHead
    if HBM:      # regions.py drew the hairline round the head: it only needs to wander, and stay off the ears
        hairv = sm(0.2, 0.8, scalp + (edge * 60.0 if SHE else edge * 10.0) * 4 * scalp * (1 - scalp)) * sm(0.006, 0.012, earD + 0.5 * edge) * isHead
    # a short trimmed beard: moustache, chin and jaw; the cheek line rises from the mouth's corner to the
    # sideburn, the neck line sits a finger's width under the jaw; thinner high on the cheeks
    dy = d[:, 1]
    cheek = mouth[2] + 0.008 + 0.45 * np.maximum(0, dy - 0.015) + edge
    neckl = mouth[2] - 0.085 + 0.6 * np.maximum(0, dy - 0.04) + edge
    beard = (1 - sm(cheek - 0.008, cheek + 0.004, z)) * sm(neckl - 0.004, neckl + 0.01, z)
    sideburn = sm(0.075, 0.085, dy) * sm(mouth[2] + 0.0, mouth[2] + 0.015, z) * (1 - sm(eyeL[2] - 0.005, eyeL[2] + 0.008, z + edge))
    beard = np.maximum(beard, sideburn) * (1 - sm(0.095, 0.105, dy)) * sm(0.03, 0.04, earD + edge)
    mous = (1 - sm(0.024, 0.032, np.abs(d[:, 0]) - edge)) * sm(0.005, 0.009, d[:, 2]) * (1 - sm(0.018, 0.024, d[:, 2] + edge)) * (dy < 0.03)
    beard = np.maximum(beard, mous) * (1 - sm(0.08, 0.35, lips)) * isHead * (0.0 if SHE else 1.0)
    beard *= 1 - 0.4 * sm(mouth[2] + 0.005, mouth[2] + 0.035, z) * sm(0.025, 0.05, np.abs(d[:, 0]))   # thinner high on the cheek
    # hair grows down the face: strands a few millimetres long
    dn = np.tile(np.array([0.0, 0.0, 1.0]), (n, 1))
    dens_b = np.clip(beard * (0.8 + 0.12 * vnoise(along(P * 900.0, dn, 5.0))), 0, 1)
    C = C * (1 - dens_b[:, None]) + HAIR * dens_b[:, None]
    R = R * (1 - dens_b) + 0.72 * dens_b
    H += 0.00006 * dens_b * vnoise(along(P * 700.0, dn, 4.0))
    dens_h = np.clip(hairv * ((0.94 if HBM else 0.9) + 0.05 * vnoise(P * 700.0)), 0, 1)
    if HBM and not SHE:      # his fade: the sides and back shorter toward the bottom, more skin showing through
        dens_h *= 0.1 + 0.85 * sm(eyeL[2] - 0.03, eyeL[2] + 0.075, z + 0.15 * edge) ** 1.3
        dens_h *= 0.8 + 0.4 * sm(-0.3, 0.5, vnoise(P * 1800.0))       # each short hair a dot: the skin between them
    C = C * (1 - 0.95 * dens_h[:, None]) + HAIR * (0.95 * dens_h[:, None])
    R = R * (1 - dens_h) + 0.75 * dens_h
    # brows: along each brow sx runs from its inner end (about 1.6 cm in from the eye's middle) out to its tail
    # (about 2.5 cm out); the lower edge rises to an arch and falls to the tail, the brow thick at the inner end
    # and tapering out. His fuller, lower and straighter; hers finer, the arch two thirds of the way out.
    for e in (eyeL, eyeR):
        de = P - e
        sx = de[:, 0] * np.sign(e[0])
        if SHE:
            lo = 0.0135 + 0.0045 * np.exp(-((sx - 0.009) / 0.012) ** 2) - 0.003 * sm(0.014, 0.026, sx)
            th_ = 0.0055 - 0.003 * sm(-0.01, 0.024, sx)
            ends = sm(-0.0175, -0.0145, sx) * (1 - sm(0.021, 0.026, sx))
        else:
            lo = 0.0115 + 0.0025 * np.exp(-((sx - 0.006) / 0.014) ** 2) - 0.0025 * sm(0.016, 0.028, sx)
            th_ = 0.0085 - 0.0045 * sm(-0.012, 0.026, sx)
            ends = sm(-0.0185, -0.015, sx) * (1 - sm(0.023, 0.029, sx))
        dz = de[:, 2] + 0.35 * edge
        brow = sm(lo - 0.002, lo + 0.001, dz) * (1 - sm(lo + th_ - 0.0015, lo + th_ + 0.0015, dz)) * ends * sm(0.2, 0.5, facing)
        # hairs lie out and a little up from the inner end
        hd = np.tile(np.array([np.sign(e[0]) * 0.97, 0.0, 0.25]), (n, 1))
        brow *= 0.8 + 0.18 * vnoise(along(P * 1100.0, hd, 4.0))
        C = C * (1 - 0.8 * brow[:, None]) + HAIR * (0.8 * brow[:, None]); R = R * (1 - brow) + 0.7 * brow
        H += 0.00005 * brow
    # lashes: where the lids meet the eyeball (the skin nearest each eye's middle), a dark line, heavier on the
    # upper lid and running out past the outer corner; people.py's eyes are 12 mm round
    if HBM:
        for e in (eyeL, eyeR):
            de = P - e; dE = np.linalg.norm(de, axis=1); sx = de[:, 0] * np.sign(e[0])
            rim = sm(0.0152, 0.0128, dE) * (de[:, 1] < 0.004)
            up = sm(-0.003, 0.001, de[:, 2]) * (1 + 0.25 * sm(0.004, 0.012, sx))
            lash = np.clip(rim * (0.85 * up + 0.35 * (1 - up)), 0, 1)
            C = C * (1 - 0.75 * lash[:, None]) + HAIR * (0.75 * lash[:, None]); R = R * (1 - lash) + 0.6 * lash
    # lips: brown-mauve, darker at the line, fine vertical lines; the skin round the mouth a shade darker
    lw = sm(0.12, 0.6, lips)
    peri = sm(0.03, 0.012, np.linalg.norm(d * np.array([0.8, 1.0, 1.4]), axis=1)) * (1 - lw) * isHead
    C *= (1 - 0.1 * peri[:, None])
    C = C * (1 - lw[:, None]) + np.array([0.13, 0.058, 0.048] if SHE else [0.13, 0.064, 0.052]) * lw[:, None] * (1 + 0.15 * (1 - sm(0.6, 0.95, lips)))[:, None] * 0.95
    R = R * (1 - lw) + 0.42 * lw
    H -= 0.00005 * lw * (0.5 + 0.5 * np.sin(x * 2 * np.pi / 0.0011 + 2 * vnoise(P * 300.0)))
    # the face's own colours: the skin round the eyes darker (a brown-violet shadow under each eye and in the
    # inner corner, as most Indian faces have), the cheekbones a little warmer, the forehead and temples, in the
    # sun the most, a touch darker and more golden; oilier down the middle (forehead, nose), matte on the cheeks
    for e in (eyeL, eyeR):
        de = P - e; dE = np.linalg.norm(de * np.array([1.0, 1.0, 1.25]), axis=1)
        sx = de[:, 0] * np.sign(e[0])
        ring = sm(0.011, 0.015, dE) * (1 - sm(0.021, 0.03, dE + 0.004 * edge / 0.006)) * (de[:, 1] < 0.012)
        ring *= np.where(de[:, 2] < 0, 1.0, 0.55) * (1 + 0.35 * sm(-0.004, -0.014, sx)) * isHead
        C *= (1 - np.clip(ring, 0, 1.2)[:, None] * np.array([0.15, 0.19, 0.13]))
        cb = sm(0.028, 0.01, np.linalg.norm(P - (e + np.array([np.sign(e[0]) * 0.012, -0.004, -0.034])), axis=1)) * isHead
        C[:, 0] *= 1 + 0.06 * cb; C[:, 2] *= 1 - 0.04 * cb
        R += 0.03 * cb
    eyeZ = (eyeL[2] + eyeR[2]) / 2
    fh = sm(eyeZ + 0.018, eyeZ + 0.035, z) * sm(0.0, 0.5, facing) * isHead
    C *= (1 - fh[:, None] * np.array([0.03, 0.04, 0.08]))
    tz = (fh * (1 - sm(0.02, 0.04, np.abs(x))) + sm(0.03, 0.012, np.linalg.norm(P - (mouth + np.array([0, -0.012, 0.04])), axis=1))) * isHead
    R -= 0.08 * np.clip(tz, 0, 1)
    # warm where blood is near the surface: ears, the nose's tip and wings, the cheeks a touch
    nose = sm(0.03, 0.012, np.linalg.norm((P - (mouth + np.array([0, -0.015, 0.035]))) * np.array([1.0, 1.0, 0.8]), axis=1)) * isHead
    warm = np.clip(0.6 * ears + 0.5 * nose, 0, 1)
    C[:, 0] *= 1 + 0.1 * warm; C[:, 2] *= 1 - 0.05 * warm
    R -= 0.12 * nose                     # the nose's oil
    # the neck: two soft creases across the front
    neck = sm(mouth[2] - 0.13, mouth[2] - 0.115, z) * (1 - sm(mouth[2] - 0.075, mouth[2] - 0.065, z)) * sm(0.0, 0.5, facing)
    wob = 0.003 * vnoise(P * 40.0)
    for zc in (mouth[2] - 0.088, mouth[2] - 0.106):
        H -= 0.00018 * neck * np.exp(-(((z + wob) - zc) / 0.0014) ** 2)

    # ---------- arms and hands ----------
    for sd, s in (("L", 1.0), ("R", -1.0)):
        side = (x * s) > 0.12
        elbow, wrist = LM[f"lowerarm01.{sd}"][0], LM[f"wrist.{sd}"][0]
        i0, p0 = LM[f"finger2-1.{sd}"][0], LM[f"finger5-1.{sd}"][0]
        palm = np.cross(p0 - i0, i0 - wrist); palm /= np.linalg.norm(palm)
        if palm @ np.array([-s, 0, 0]) < 0: palm = -palm
        dorsal = -palm
        adir = (wrist - elbow) / np.linalg.norm(wrist - elbow)
        dist_arm, t_arm = seg(P, elbow - adir * 0.12, wrist)
        fore = side & (dist_arm < 0.07) & (handw < 0.5)
        hand = side & (handw > 0.05)
        hw = np.where(side, sm(0.05, 0.6, handw), 0)
        # sun on the back of the hands and the outside of the forearms; the inside of the arm paler
        out = N @ dorsal
        C *= np.where(side, 1 - 0.07 * sm(-0.2, 0.6, out) + 0.07 * sm(-0.2, -0.7, out), 1)[:, None]
        # forearm hair: on the back and outer side, thinning at the wrist, lying toward the hand
        dens = sm(-0.4, 0.5, out) * 0.55 + 0.2
        dens *= sm(1.02, 0.85, t_arm) * fore * (0.25 if SHE else 1.0)
        st = vnoise(along(P * 650.0, np.tile(adir, (n, 1)), 6.0))
        a_ = np.clip(dens * (0.17 + 0.06 * st), 0, 1)
        C = C * (1 - a_[:, None]) + HAIR * a_[:, None]
        R += 0.1 * dens
        # palms and the inside of the fingers: lighter and pinker
        pal = sm(0.1, 0.6, N @ palm) * hw
        C = C * (1 - 0.7 * pal[:, None]) + np.array([0.42, 0.25, 0.185]) * (0.7 * pal[:, None])
        R += 0.08 * pal
        # nails: pale pink-beige with a lighter free edge, glossy
        nw = sm(0.2, 0.7, nails) * side
        C = C * (1 - nw[:, None]) + np.array([0.5, 0.34, 0.29]) * nw[:, None]
        R = R * (1 - nw) + 0.22 * nw
        back = sm(0.0, 0.5, N @ dorsal) * hw
        # tendons fanning from the wrist to each knuckle, under the skin of the back of the hand
        base = LM[f"wrist.{sd}"][1]
        for f in range(2, 6):
            k = LM[f"finger{f}-1.{sd}"][0]
            dd, tt = seg(P, base + (k - base) * 0.15, k - (k - base) * 0.05)
            H += 0.00045 * back * np.exp(-(dd / 0.0026) ** 2) * sm(0.0, 0.3, tt) * sm(1.0, 0.75, tt)
        # veins: a branching network on the back of the hand and up the forearm, raised and a little blue
        rv = 1 - np.abs(vnoise(along(P * 38.0, np.tile(adir, (n, 1)), 2.2) + 3.3))
        vein = sm(0.93, 0.985, rv) * np.clip(back + 0.8 * fore * sm(-0.6, 0.3, -out) * sm(0.2, 0.9, t_arm), 0, 1)
        H += 0.0005 * vein
        C *= (1 - 0.06 * vein[:, None] * np.array([1.0, 0.6, -0.4]))
        # knuckles: darker and creased across the back of each finger joint
        for f in range(2, 6):
            for j, depth in ((1, 0.00012), (2, 0.0002), (3, 0.00014)):
                J = LM[f"finger{f}-{j}.{sd}"][0]
                fd = LM[f"finger{f}-{j}.{sd}"][1] - J; fd /= np.linalg.norm(fd)
                rel = P - J
                al = rel @ fd
                rad = np.linalg.norm(rel - np.outer(al, fd), axis=1)
                dors = sm(-0.1, 0.5, (rel - np.outer(al, fd)) @ dorsal / (rad + 1e-6))
                near = sm(0.011, 0.006, rad) * dors * side
                k_dark = near * np.exp(-(al / (0.006 if j == 1 else 0.0045)) ** 2)
                C *= (1 - 0.16 * k_dark[:, None] * np.array([1.0, 1.05, 1.1]))
                for c_ in (-1.5, -0.5, 0.5, 1.5) if j > 1 else (-0.5, 0.5):
                    H -= depth * near * np.exp(-((al - c_ * 0.0016) / 0.0006) ** 2) * (1 - 0.3 * abs(c_) / 1.5)
        # elbows: a darker, drier patch at the back
        e_ = sm(0.04, 0.015, np.linalg.norm(P - elbow, axis=1)) * sm(-0.1, 0.6, N @ np.array([0.0, 1.0, 0.0])) * side
        C *= (1 - 0.14 * e_[:, None]); R += 0.08 * e_



    # ---------- the hair itself (hair.py's shell and bun): strands along the flow ----------
    if hairw is not None and hairw.max() > 0:
        hw = sm(0.0, 0.55, hairw)                           # grows out of the painted fade as the hair deepens
        f = flow / (np.linalg.norm(flow, axis=1, keepdims=True) + 1e-9)
        fine = vnoise(along(P * 2400.0, f, 16.0))           # single strands, under half a millimetre across
        clump = vnoise(along(P * 420.0, f, 9.0))            # locks a few millimetres across
        broad = fbm(P * 40.0, 2)                            # where the light catches more or less of it
        col = HAIR * (1.0 + 0.22 * fine + 0.3 * clump + 0.15 * broad)[:, None]
        col = col * np.array([1.0, 0.97, 0.94]) + np.array([0.004, 0.0025, 0.0015]) * sm(0.2, 0.9, clump)[:, None]
        rough = (0.48 if SHE else 0.58) + 0.06 * fine
        groove = vnoise(along(P * 900.0, f, 22.0))            # fine grooves along the strands, ~1 mm apart
        hh = 0.00008 * fine + 0.00022 * groove + (0.00012 if SHE else 0.00035) * clump
        C = C * (1 - hw[:, None]) + col * hw[:, None]
        R = R * (1 - hw) + rough * hw
        H = H * (1 - hw) + hh * hw
    return np.clip(C, 0.003, 0.9), np.clip(R, 0.18, 0.85), H

# ---------- texel by texel: four points across each, the relief's slope across it ----------
CI = np.zeros((RES, RES, 3), np.float32); NI = np.zeros((RES, RES, 3), np.float32); RI = np.zeros((RES, RES), np.float32)
OFF = ((-0.25, -0.25), (0.25, -0.25), (-0.25, 0.25), (0.25, 0.25))
for c0 in range(0, len(YS), 200000):
    g = G[c0:c0 + 200000].astype(np.float64)
    P, N = g[:, 0:3], g[:, 3:6]
    N = N / (np.linalg.norm(N, axis=1, keepdims=True) + 1e-12)
    Pu, Pv = g[:, 11:14], g[:, 14:17]
    cs, rs, hs = [], [], []
    for ox, oy in OFF:
        c, r, h = shade(P + Pu * ox + Pv * oy, N, *(g[:, k] for k in range(6, 11)),
                        *((g[:, 17], g[:, 18:21]) if g.shape[1] > 17 else ()))
        cs.append(c); rs.append(r); hs.append(h)
    lu, lv = np.maximum(np.linalg.norm(Pu, axis=1), 1e-7), np.maximum(np.linalg.norm(Pv, axis=1), 1e-7)
    gx = ((hs[1] + hs[3]) - (hs[0] + hs[2])) / 2 / (0.5 * lu)
    gy = ((hs[2] + hs[3]) - (hs[0] + hs[1])) / 2 / (0.5 * lv)      # rows run down the image: v increases
    nt = np.stack([-gx, -gy, np.ones_like(gx)], 1); nt /= np.linalg.norm(nt, axis=1, keepdims=True)
    ys, xs = YS[c0:c0 + 200000], XS[c0:c0 + 200000]
    CI[ys, xs] = sum(cs) / 4; RI[ys, xs] = sum(rs) / 4; NI[ys, xs] = nt
    print("  texels", c0 + len(ys), flush=True)
mask = np.zeros((RES, RES), bool); mask[YS, XS] = True


def dilate(a, m, steps):
    """push the island colours outward so mip levels and filtering never pull in the empty page"""
    a = a.copy(); m = m.copy()
    for _ in range(steps):
        acc = np.zeros_like(a); cnt = np.zeros(m.shape, np.float32)
        for dy_, dx_ in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sh = np.roll(m, (dy_, dx_), (0, 1))
            acc += np.roll(a, (dy_, dx_), (0, 1)) * (sh[..., None] if a.ndim == 3 else sh)
            cnt += sh
        new = (~m) & (cnt > 0)
        a[new] = (acc[new].T / cnt[new]).T if a.ndim == 3 else acc[new] / cnt[new]
        m |= new
    return a, m


CI, m2 = dilate(CI, mask, 24); NI, _ = dilate(NI, mask, 24); RI, _ = dilate(RI, mask, 24)
CI[~m2] = BASE; NI[~m2] = (0, 0, 1); RI[~m2] = 0.5
NI /= np.maximum(np.linalg.norm(NI, axis=-1, keepdims=True), 1e-6)


def srgb(c):
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(np.clip(c, 0, 1), 1 / 2.4) - 0.055)


alb = (np.clip(srgb(CI), 0, 1) * 255 + 0.5).astype(np.uint8)
nrm = (np.clip(np.concatenate([NI[..., :2] * 0.5 + 0.5, RI[..., None]], -1), 0, 1) * 255 + 0.5).astype(np.uint8)
Image.fromarray(alb, "RGB").save(OUT + "-skin.webp", quality=90, method=6)
Image.fromarray(nrm, "RGB").save(OUT + "-skin-n.webp", quality=92, method=6)
print("skin maps", OUT + "-skin.webp", os.path.getsize(OUT + "-skin.webp"), OUT + "-skin-n.webp", os.path.getsize(OUT + "-skin-n.webp"), flush=True)
