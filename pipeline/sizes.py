# python3 sizes.py <out.json> : Qikink UC22 size chart graded onto our pattern, for the site's tech flat.
import json, sys, pattern as P
CHART = {"XS": (40, 27, 18), "S": (42, 28, 19), "M": (44, 29, 20), "L": (46, 30, 21), "XL": (48, 31, 22), "2XL": (50, 32, 23)}  # chest, length, shoulder (in)
out = {}
for s, (c, l, sh) in CHART.items():
    P.L = l * 2.54; P.HC = c * 2.54 / 2; P.HS = sh * 2.54 / 2      # chest is round-the-body inches -> flat half = c*2.54/2... see note
    # Qikink lists chest as the flat-lay measure doubled? Their M "44 in" matches 111.8 cm round = 55.9 flat, used since the start.
    pts = [[round(x, 2), round(y, 2)] for (x, y), *_ in P.outline(True, 2.0)]
    back = [[round(x, 2), round(y, 2)] for (x, y), *_ in P.outline(False, 2.0)]
    out[s] = {"in": {"chest": c, "length": l, "shoulder": sh},
              "cm": {"chest_round": round(c * 2.54, 1), "chest_flat": round(c * 2.54 / 2, 1), "length": round(l * 2.54, 1), "shoulder": round(sh * 2.54, 1)},
              "front": pts, "back": back, "simulated": s == "M"}
json.dump({"neck": {"width": P.NECK_W * 2, "front_drop": P.FRONT_DROP, "back_drop": P.BACK_DROP, "rib": P.RIB},
           "sleeve": {"length": P.SLEEVE_LEN, "opening_flat": P.SLEEVE_OPEN}, "sizes": out}, open(sys.argv[1], "w"))
print("sizes ok", len(out["M"]["front"]))
