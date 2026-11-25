# blender -b --factory-startup -P hdr2npy.py -- <in.hdr> <out.npy>
# A Radiance .hdr to a float16 numpy array (rows top first, RGB), read by Blender (fast, any size), for photo_place.py
import bpy, sys
import numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
im = bpy.data.images.load(a[0]); w, h = im.size
px = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(px)
np.save(a[1], px.reshape(h, w, 4)[::-1, :, :3].astype(np.float16))
print("hdr", w, "x", h, "->", a[1])
