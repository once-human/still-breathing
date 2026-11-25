# python3 motion_post.py <frames dir of f000.png ...> <out.mp4>      (numpy, pillow, ffmpeg)
# The canopy's breathing loop (stage.yml motion: the rows of the show where the cloth is, every frame developed by
# stage_post.py into the band's four stacked tiles) made into the video the viewer plays behind the person.
# Only what moves is taken from each frame: everywhere else (the hall, the crowd, the lamps) every frame is the
# average of the whole loop, so nothing that stands still flickers with the render's own noise from frame to frame.
# The loop is then filled out to 24 frames a second along the cloth's own motion (its end runs into its start), and
# written at full size and at half (<out>-lo.mp4) for phones.
import glob, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image

SRC, OUT = sys.argv[1], sys.argv[2]
files = sorted(glob.glob(os.path.join(SRC, "f*.png")))
n = len(files); print("frames", n)
first = np.asarray(Image.open(files[0]).convert("RGB")); H, W, _ = first.shape
s1 = np.zeros((H, W, 3), np.float64); s2 = np.zeros((H, W, 3), np.float64)
for f in files:
    a = np.asarray(Image.open(f).convert("RGB")).astype(np.float64); s1 += a; s2 += a * a
mean = s1 / n; std = np.sqrt(np.maximum(s2 / n - mean * mean, 0)).max(-1)
del s1, s2


def soften(x, r):
    """a box blur of radius r, twice (rows, then columns), so the moving parts' edges ease into the still ones"""
    for ax in (0, 1):
        c = np.cumsum(np.pad(x, [(r + 1, r) if a_ == ax else (0, 0) for a_ in (0, 1)], mode="edge"), axis=ax)
        x = (np.take(c, range(2 * r + 1, c.shape[ax]), axis=ax) - np.take(c, range(0, c.shape[ax] - 2 * r - 1), axis=ax)) / (2 * r + 1)
    return x


# moving: what changes by more than the render's noise over the loop (a few levels in 255), eased out over a few px
move = np.clip((std - 2.5) / 4.0, 0, 1)
move = np.clip(soften(soften(move, 4) * 2.0, 4), 0, 1)[..., None].astype(np.float32)
print("moving", round(float((move > 0.5).mean()), 3), "of the picture")
tmp = tempfile.mkdtemp()
for i, f in enumerate(files):
    a = np.asarray(Image.open(f).convert("RGB")).astype(np.float32)
    o = a * move + mean.astype(np.float32) * (1 - move)
    Image.fromarray(np.clip(np.round(o), 0, 255).astype(np.uint8)).save(os.path.join(tmp, f"g{i:03d}.png"), compress_level=1)
for j in range(3):   # the loop's start again after its end, to fill toward
    os.symlink(os.path.join(tmp, f"g{j:03d}.png"), os.path.join(tmp, f"g{n + j:03d}.png"))

src_fps, fps = 12, 24
for out, scale in ((OUT, None), (OUT.replace(".mp4", "-lo.mp4"), (W // 2, H // 2))):
    vf = f"minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
    if scale: vf += f",scale={scale[0]}:{scale[1]}:flags=lanczos"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(src_fps), "-i", os.path.join(tmp, "g%03d.png"),
                    "-vf", vf, "-frames:v", str(n * fps // src_fps), "-c:v", "libx264", "-preset", "slow", "-crf", "19",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", out], check=True)
    print("saved", out, os.path.getsize(out) // 1024, "KB")
