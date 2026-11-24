# python3 knit.py -> knit.png: tileable height map of single-jersey knit, face side.
# 240 GSM combed cotton jersey: ~14 wales/cm and ~18 courses/cm; each loop shows as a V of two yarn legs.
import numpy as np
from PIL import Image
WALES, COURSES, PX = 16, 20, 512          # tile = 16 wales x 20 courses = 11.4 x 11.1 mm
rng = np.random.default_rng(7)
y, x = np.mgrid[0:PX, 0:PX] / PX
cx = x * WALES; cy = y * COURSES
i, j = np.floor(cx), np.floor(cy); u, v = cx - i, cy - j          # position inside one loop cell
jit = rng.normal(0, 0.035, (COURSES, WALES))                       # yarn tension varies loop to loop
jj = jit[j.astype(int) % COURSES, i.astype(int) % WALES]
r = 0.23                                                           # yarn radius in wale widths
def leg(ax, ay, bx, by, uu, vv):
    dx, dy = bx - ax, by - ay; t = np.clip(((uu - ax) * dx + (vv - ay) * dy) / (dx * dx + dy * dy), 0, 1)
    d = np.hypot(uu - ax - t * dx, (vv - ay - t * dy) * WALES / COURSES * 1.25)
    return np.sqrt(np.clip(1 - (d / r) ** 2, 0, 1))
h = np.zeros_like(u)
for dv in (-1, 0, 1):                                              # legs overlap into the next course
    vv = v - dv
    h = np.maximum(h, leg(0.08 + jj, -0.1, 0.5, 1.1, u, vv) * 0.95)
    h = np.maximum(h, leg(0.92 + jj, -0.1, 0.5, 1.1, u, vv))
fuzz = rng.normal(0, 0.05, (PX, PX))
h = np.clip(h * 0.9 + fuzz, 0, 1)
Image.fromarray((h * 255).astype(np.uint8)).save("knit.png"); print("knit ok")
