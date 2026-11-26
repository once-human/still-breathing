# Relaxed hands for people.py's bodies. The artist sculpted the hands open: fingers straight and a little spread,
# the thumb standing off the palm, which reads as a shop mannequin's. A hand hanging at someone's side is never
# like that: the fingers close up side by side and curl, a little at the index and more toward the little finger,
# and the thumb comes in to lie along the side of the index finger, its joints a touch bent.
# MakeHuman's finger bones, fitted into the sculpt, are too rough to pose with (their weights tear the fingers),
# so the hand is read from the sculpt itself and bent directly, in the rest pose, before anything is posed:
#   - the hand: the skin beyond the wrist; every point's distance from the wrist over the surface
#   - the fingertips: the five farthest points (the thumb is the one standing apart)
#   - each finger's web: going down from the tips, the height at which its own piece of the hand first joins a
#     neighbour's (the surface above a height splits into fingers; the web is where two fingers meet)
#   - each finger's line through its own piece; its knuckle (MCP) some way into the palm past the web, its middle
#     and end joints (PIP, DIP) at the bones' share of its length
#   - every point follows its finger by how near it is over the surface (soft between fingers and in the palm), and
#     each joint by where it lies along the finger (soft over a few millimetres, wider over the knuckles)
# Each finger turns end joint first, then middle, then knuckle (so a joint carries what lies beyond it), about the
# line across the finger, toward the palm.
import heapq, math
import numpy as np


def sm(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0); return t * t * (3 - 2 * t)


def rot(P, c, k, a):
    """rotate points P about the line through c along the unit axis k by angles a (one per point; Rodrigues)"""
    v = P - c; ca = np.cos(a)[:, None]; sa = np.sin(a)[:, None]
    return c + v * ca + np.cross(k, v) * sa + k * (v @ k)[:, None] * (1 - ca)


def unit(v): return v / np.linalg.norm(v)


def geodesic(adj, seeds, allowed, reach=math.inf):
    D = np.full(len(adj), np.inf); pq = []
    for i in seeds: D[i] = 0.0; pq.append((0.0, int(i)))
    heapq.heapify(pq)
    while pq:
        d, i = heapq.heappop(pq)
        if d > D[i]: continue
        for j, L in adj[i]:
            if not allowed[j]: continue
            nd = d + L
            if nd > reach: continue
            if nd < D[j]: D[j] = nd; heapq.heappush(pq, (nd, j))
    return D


# degrees at the knuckle, the middle and the end joint; index to little finger. A hand hanging loose at the side:
# about 33 degrees over the index's three joints, about 58 at the little finger
CURL = {"index": (9, 17, 7), "middle": (12, 21, 8), "ring": (15, 25, 9), "little": (18, 29, 11)}
# where the joints sit along the finger, from the knuckle (0) to the tip (1); the knuckle itself lies this share of
# the web-to-tip length back into the palm past the web
PIP, DIP, MCP_BACK = 0.47, 0.74, 0.27


def relax(me, rig, she=False, ease=None):
    """bend the hands of the mesh `me` (rest pose, world = object space) in place. ease: per side a factor on the
    curl ({"L": 1.1, "R": 0.92}: nobody holds both hands the same)"""
    ease = ease or {"L": 1.0, "R": 1.0}
    P = np.array([v.co for v in me.vertices], dtype=np.float64)
    adj = [[] for _ in range(len(P))]
    for e in me.edges:
        a, b = e.vertices; L = float(np.linalg.norm(P[a] - P[b])); adj[a].append((b, L)); adj[b].append((a, L))
    out = P.copy()
    for sd, s in (("L", 1.0), ("R", -1.0)):
        wr = np.array(rig.data.bones["wrist." + sd].head_local); el = np.array(rig.data.bones["lowerarm01." + sd].head_local)
        arm = unit(wr - el)
        t = (P - wr) @ arm
        side = np.sign(P[:, 0]) == s
        hand = side & (t > -0.004) & (np.linalg.norm(P - wr, axis=1) < 0.25)
        ring = np.where(side & (np.abs(t + 0.002) < 0.003) & (np.linalg.norm(P - wr, axis=1) < 0.06))[0]
        D = geodesic(adj, ring, hand)
        hv = np.where(hand & np.isfinite(D))[0]
        # fingertips: the farthest points from the wrist that nothing within 3 cm over the surface is farther than
        # (a point partway down a long finger is not a tip, however far it is)
        tips = []; gone = np.zeros(len(P), bool)
        for i in hv[np.argsort(-D[hv])]:
            i = int(i)
            if gone[i]: continue
            near = np.isfinite(geodesic(adj, [i], hand, 0.03))
            gone |= near
            if (D[near] > D[i] + 1e-9).any(): continue
            tips.append(i)
            if len(tips) == 5: break
        T = P[tips]
        thumb = int(np.argmax([min(np.linalg.norm(T[a] - T[b]) for b in range(5) if b != a) for a in range(5)]))
        # each tip's web: the surface above a height falls apart into the fingers; going down, the height at which a
        # finger's piece first meets another's
        order = hv[np.argsort(-D[hv])]
        parent = {}
        def find(x):
            while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
            return x
        tipset = {i: k for k, i in enumerate(tips)}; owns = {}; web = [None] * 5
        for i in order:
            i = int(i); parent[i] = i; owns[i] = {tipset[i]} if i in tipset else set()
            for j, _ in adj[i]:
                if j not in parent: continue
                a, b = find(i), find(j)
                if a == b: continue
                if owns[a] and owns[b]:
                    for k in owns[a] | owns[b]:
                        if web[k] is None: web[k] = D[i]
                parent[b] = a; owns[a] |= owns.pop(b)
        # each finger's own piece above its web, and its line
        fingers = []
        for k, ti in enumerate(tips):
            above = hand & (D > web[k])
            Dt = geodesic(adj, [ti], above)
            own = np.where(np.isfinite(Dt))[0]
            Q = P[own]; c = Q.mean(0)
            a = np.linalg.svd(Q - c, full_matrices=False)[2][0]
            if (P[ti] - c) @ a < 0: a = -a
            tipu = (P[ti] - c) @ a; webu = ((Q - c) @ a).min()
            fingers.append(dict(k=k, tip=ti, c=c, a=a, tipu=tipu, webu=webu, n=len(own)))
        # the hand's frame: its back (dorsal) faces away from the thumb, measured on the four fingertips and the wrist
        four = [k for k in range(5) if k != thumb]
        wc = P[ring].mean(0)
        q = np.vstack([T[four], wc]); qc = q.mean(0)
        dors = np.linalg.svd(q - qc)[2][2]
        if (T[thumb] - qc) @ dors > 0: dors = -dors
        # the four in order across the hand, the index next to the thumb
        four.sort(key=lambda k: np.linalg.norm(T[k] - T[thumb]))
        names = dict(zip(four, ("index", "middle", "ring", "little")))
        # how much each point belongs to each digit, over the surface (soft between them and into the palm)
        Dts = np.stack([geodesic(adj, [ti], hand) for ti in tips])
        Dts[~np.isfinite(Dts)] = 10.0
        # (the thumb's share falls off slower: the web between it and the index finger stretches, never creases)
        sig = np.full((5, 1), 0.008); sig[thumb] = 0.016
        m = np.exp(-(Dts - Dts.min(0)) / sig); m /= m.sum(0)
        X = out.copy()
        mid = fingers[four[1]]
        for f in fingers:
            k = f["k"]
            if k == thumb: continue
            a, c = f["a"], f["c"]
            Lw = f["tipu"] - f["webu"]
            mcp_u = f["webu"] - MCP_BACK * Lw; Lt = f["tipu"] - mcp_u
            J = {"mcp": c + a * mcp_u, "pip": c + a * (mcp_u + PIP * Lt), "dip": c + a * (mcp_u + DIP * Lt)}
            curl_ax = unit(np.cross(dors, a))                   # turning about it brings the tip toward the palm
            dm, dp, dd = CURL[names[k]]; ek = ease[sd]
            u = (P - c) @ a
            wk = m[k] * hand
            for jn, deg, h in (("dip", dd, 0.004), ("pip", dp, 0.005), ("mcp", dm, 0.011)):
                ju = (J[jn] - c) @ a
                w = wk * sm(ju - h, ju + h, u)
                X = np.where(w[:, None] > 0, rot(X, J[jn], curl_ax, np.radians(deg * ek) * w), X)
            # fingers together: each turns at its knuckle toward lying beside the middle finger (spread taken out)
            if k != mid["k"]:
                a_ = a - dors * (a @ dors); m_ = mid["a"] - dors * (mid["a"] @ dors)
                ang = math.atan2(np.cross(a_, m_) @ dors, a_ @ m_)
                ju = (J["mcp"] - c) @ a
                w = wk * sm(ju - 0.011, ju + 0.011, u)
                X = np.where(w[:, None] > 0, rot(X, J["mcp"], dors, 0.75 * ang * w), X)
            f["J"] = J
        # the thumb: in toward the side of the index finger, about its base by the wrist, then its two joints bent
        f = fingers[thumb]; a, c = f["a"], f["c"]; ix = fingers[four[0]]
        Lw = f["tipu"] - f["webu"]
        mcp = c + a * f["webu"]; ipj = c + a * (f["webu"] + 0.5 * Lw)
        cmc = wr + 0.35 * (mcp - wr)
        u = (P - c) @ a; wk = m[thumb] * hand
        # its joints, the end one first, bent toward the palm's middle
        palm_mid = np.mean([fingers[k]["J"]["mcp"] for k in four], axis=0) - dors * 0.012
        for jc, deg, h in ((ipj, 10, 0.005), (mcp, 5, 0.008)):
            ax = unit(np.cross(a, palm_mid - jc))
            ju = (jc - c) @ a
            w = wk * sm(ju - h, ju + h, u)
            X = np.where(w[:, None] > 0, rot(X, jc, ax, np.radians(deg * ease[sd]) * w), X)
        # then the whole thumb from its base, most of the way to lying along the index finger's side
        side_of_index = (ix["J"]["mcp"] + ix["J"]["pip"]) / 2 - dors * 0.004
        cur = unit(X[tips[thumb]] - cmc); want = unit(side_of_index - cmc)
        ang = math.acos(float(np.clip(cur @ want, -1, 1))) * 0.45
        ax = unit(np.cross(cur, want))
        bu = (cmc - c) @ a
        w = wk * sm(bu, bu + 0.045, u)
        X = np.where(w[:, None] > 0, rot(X, cmc, ax, ang * w), X)
        out = np.where(hand[:, None], X, out)
        print("hand", sd, "tips", len(tips), "thumb", thumb, "webs (cm from wrist)", [round(float(w_) * 100, 1) for w_ in web],
              "verts", int(hand.sum()), "thumb in", round(math.degrees(ang), 1), flush=True)
    for v, p in zip(me.vertices, out): v.co = p
    me.update()
