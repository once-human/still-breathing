# blender -b <body.blend> --factory-startup -P regions.py            (rewrites the regions of a people.py body in place)
# The regions skin.py and hair.py paint by (lips, ears, fingernails, scalp), found on the artist's own mesh.
# Carried over from MakeHuman they land centimetres off (its face is laid out differently: the lips came out on
# one person's nose and the other's chin), so each is found from the sculpt itself:
#   - ears: the sculpt's own UV islands for the ears (the artist cut each ear out as one piece)
#   - lips: the face's profile down the middle gives the nose tip, the base of the nose, the fullest points of
#     both lips and the line between them; the lips are a lens round that line, as tall as the profile says each
#     lip is, as wide as a mouth is for those eyes (0.37 of the distance between them each side; 0.35 on her),
#     with the dip of the cupid's bow, kept to the front of the face
#   - fingernails: the five fingertips are the points of the hand farthest from the wrist over its surface; the
#     nail is on the back of each, 1 to 13 mm behind the tip (scaled to the finger), as wide as the finger allows
#   - scalp: above a hairline that runs round the head, high at the forehead, dipping at the temples, over the
#     ears and down behind them to the nape (lower on her)
# people.py calls mark() before it saves; run on its own, it updates a body .blend.
import heapq, math
import bmesh
import numpy as np
from mathutils import Vector


def sm(e0, e1, x):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def uv_islands(bm):
    uvl = bm.loops.layers.uv.active
    bm.faces.ensure_lookup_table()
    par = list(range(len(bm.faces)))
    def find(k):
        while par[k] != k: par[k] = par[par[k]]; k = par[k]
        return k
    for e in bm.edges:
        if len(e.link_faces) != 2: continue
        f1, f2 = e.link_faces
        u1 = {l.vert.index: l[uvl].uv for l in f1.loops if l.vert in e.verts}
        u2 = {l.vert.index: l[uvl].uv for l in f2.loops if l.vert in e.verts}
        if all((u1[k] - u2[k]).length < 1e-5 for k in u1): par[find(f1.index)] = find(f2.index)
    isl = {}
    for f in bm.faces: isl.setdefault(find(f.index), []).append(f)
    return list(isl.values())


def mark(body, eyes, she, rig):
    me = body.data
    P = np.array([v.co[:] for v in me.vertices])
    N = np.array([v.normal[:] for v in me.vertices])
    ec = [np.array([v.co[:] for v in e.data.vertices]).mean(0) for e in eyes]
    eyeC = (ec[0] + ec[1]) / 2; E = eyeC[2]; ipd = abs(ec[0][0] - ec[1][0])
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    W = {}

    # ---------- ears: the artist's islands beside the head, at eye level ----------
    ear = np.zeros(len(P))
    for fs in uv_islands(bm):
        vs = {v.index for f in fs for v in f.verts}
        c = P[list(vs)].mean(0)
        if 0.05 < abs(c[0]) < 0.12 and abs(c[2] - E) < 0.05 and c[1] > eyeC[1] + 0.04 and len(fs) < 2500:
            ear[list(vs)] = 1.0
    W["ears"] = ear
    earC = [P[(ear > 0) & (np.sign(P[:, 0]) == s)].mean(0) for s in (1, -1)]
    earTop = max(P[ear > 0, 2])

    # ---------- lips: from the profile down the middle of the face ----------
    mid = (np.abs(P[:, 0]) < 0.004) & (P[:, 1] < eyeC[1] + 0.02)
    zs = np.arange(E - 0.16, E + 0.02, 0.0015)
    prof = np.array([P[mid & (np.abs(P[:, 2] - z) < 0.0012), 1].min() if (mid & (np.abs(P[:, 2] - z) < 0.0012)).any() else np.nan for z in zs])
    def arg(lo, hi, f):
        i = np.where((zs >= lo) & (zs <= hi) & ~np.isnan(prof))[0]; j = i[f(prof[i])]; return zs[j]
    nose = arg(E - 0.065, E - 0.02, np.argmin); subn = arg(nose - 0.035, nose - 0.008, np.argmax)
    upk = arg(subn - 0.022, subn - 0.004, np.argmin); stom = arg(upk - 0.016, upk - 0.002, np.argmax)
    lpk = arg(stom - 0.02, stom - 0.002, np.argmin)
    hU, hL = (upk - stom) + 0.0015, (stom - lpk) + 0.0035
    w = (0.35 if she else 0.37) * ipd
    yfront = np.interp(P[:, 2], zs[~np.isnan(prof)], prof[~np.isnan(prof)])
    x = P[:, 0]; u = np.clip(np.abs(x) / w, 0, 1.5)
    bow = 1 - 0.16 * np.exp(-(x / 0.0035) ** 2) + 0.05 * np.exp(-((np.abs(x) - 0.006) / 0.003) ** 2)
    zu = stom + hU * np.sqrt(np.clip(1 - u ** 2, 0, 1)) * bow
    zl = stom - hL * np.clip(1 - u ** 2, 0, 1) ** 0.65
    soft = 0.0009
    lips = sm(zl - soft, zl + soft, P[:, 2]) * (1 - sm(zu - soft, zu + soft, P[:, 2])) * (1 - sm(0.92, 1.0, u))
    lips *= (1 - sm(0.006, 0.012, P[:, 1] - (yfront + 0.03 * u ** 2)))       # the front of the face, round to the corners
    lips *= (np.abs(P[:, 2] - stom) < 0.03) & (np.abs(x) < w + 0.004)
    W["lips"] = lips
    print("regions: eyes", round(E, 3), "nose", round(nose - E, 4), "stomion", round(stom - E, 4), "lips up/down",
          round(hU * 1000, 1), round(hL * 1000, 1), "mm, half width", round(w * 1000, 1), "mm, verts", int((lips > 0.5).sum()), flush=True)

    # ---------- scalp: above a hairline running round the head ----------
    headc = np.array([0.0, (earC[0][1] + earC[1][1]) / 2, E])
    th = np.degrees(np.arctan2(np.abs(P[:, 0]), -(P[:, 1] - headc[1])))         # 0 the front, 180 the back
    A = [0, 35, 70, 92, 120, 150, 180]
    H = ([E + 0.05, E + 0.046, E + 0.03, earTop + 0.006, earTop - 0.02, stom + 0.01, stom - 0.004] if she else
         [E + 0.058, E + 0.052, E + 0.036, earTop + 0.008, earTop - 0.012, stom + 0.03, stom + 0.018])
    hz = np.interp(th, A, H)
    head = (P[:, 2] > stom - 0.06) & (np.abs(P[:, 0]) < 0.13)
    W["scalp"] = sm(hz - 0.003, hz + 0.005, P[:, 2]) * head * (ear < 0.5)

    # ---------- fingernails: the fingertips are the farthest points of each hand from its wrist ----------
    nails = np.zeros(len(P))
    adj = [[] for _ in range(len(P))]
    for e in bm.edges:
        a, b = e.verts[0].index, e.verts[1].index; L = e.calc_length(); adj[a].append((b, L)); adj[b].append((a, L))
    for s in (1, -1):
        sd = "L" if s > 0 else "R"
        side = np.sign(P[:, 0]) == s
        # the hand: beyond the wrist (the rig's), along the forearm
        wr = np.array(rig.matrix_world @ rig.data.bones["wrist." + sd].head_local)
        el = np.array(rig.matrix_world @ rig.data.bones["lowerarm01." + sd].head_local)
        axis = (wr - el) / np.linalg.norm(wr - el)
        t = (P - wr) @ axis
        hand = side & (t > 0) & (np.linalg.norm(P - wr, axis=1) < 0.25)
        wristring = np.where(side & (np.abs(t) < 0.003) & (np.linalg.norm(P - wr, axis=1) < 0.06))[0]
        D = np.full(len(P), np.inf); pq = []
        for i in wristring: D[i] = 0.0; pq.append((0.0, i))
        heapq.heapify(pq)
        while pq:
            d, i = heapq.heappop(pq)
            if d > D[i]: continue
            for j, L in adj[i]:
                if not hand[j]: continue
                nd = d + L
                if nd < D[j]: D[j] = nd; heapq.heappush(pq, (nd, j))
        hv = np.where(hand & np.isfinite(D))[0]
        # tips: local maxima of that distance (none farther within 1.5 cm on the surface)
        order = hv[np.argsort(-D[hv])]
        tips = []
        for i in order:
            if all(np.linalg.norm(P[i] - P[k]) > 0.016 for k in tips): tips.append(i)
            if len(tips) == 5: break
        tipsP = P[tips]
        thumb = int(np.argmax([min(np.linalg.norm(tipsP[a] - tipsP[b]) for b in range(5) if b != a) for a in range(5)]))
        four = [k for k in range(5) if k != thumb]
        # the hand's plane through the four fingertips and the wrist; its back is away from the thumb
        wc = P[wristring].mean(0)
        q = np.vstack([tipsP[four], wc]); qc = q.mean(0)
        nrm = np.linalg.svd(q - qc)[2][2]
        if (tipsP[thumb] - qc) @ nrm > 0: nrm = -nrm
        for k, i in enumerate(tips):
            T = P[i]
            # the finger's line: from the point 2.5 cm back over the surface to the tip
            back = hv[np.argmin(np.abs(D[hv] - (D[i] - 0.025)) + 1e3 * (np.linalg.norm(P[hv] - T, axis=1) > 0.035))]
            ax = (T - P[back]); ax /= np.linalg.norm(ax)
            L = 0.013 if k != thumb else 0.014
            rel = P - T; al = rel @ ax; perp = rel - np.outer(al, ax)
            dors = perp @ nrm
            wdt = 0.0062 if k != thumb else 0.0072
            m = sm(-L - 0.0015, -L + 0.0015, al) * (1 - sm(-0.0025, -0.0005, al)) * sm(0.001, 0.003, dors) \
                * (1 - sm(wdt - 0.0012, wdt + 0.0008, np.linalg.norm(perp - np.outer(dors, nrm), axis=1))) * (N @ nrm > 0.2) * hand
            nails = np.maximum(nails, m)
        print("regions: hand", "L" if s > 0 else "R", "tips", len(tips), "thumb", thumb, "nail verts", int((nails * side > 0.5).sum()), flush=True)
    W["fingernails"] = nails
    bm.free()

    for name, w_ in W.items():
        g = body.vertex_groups.get(name)
        if g: body.vertex_groups.remove(g)
        g = body.vertex_groups.new(name=name)
        for i in np.where(w_ > 1e-3)[0]: g.add([int(i)], float(min(1.0, w_[i])), "REPLACE")


if __name__ == "__main__":
    import bpy
    body = bpy.data.objects["body"]; eyes = [bpy.data.objects["eye.L"], bpy.data.objects["eye.R"]]
    mark(body, eyes, body.get("sex") == "female", bpy.data.objects["rig"])
    bpy.ops.wm.save_mainfile(compress=True)
    print("saved", bpy.data.filepath, flush=True)
