# python3 motion_post.py <frames dir of f000.png ...> <out.mp4> [band.webp]      (numpy, pillow, ffmpeg)
# The canopy's breathing loop (stage.yml motion: the rows of the show where the cloth is, every frame developed by
# stage_post.py into the band's four stacked tiles) made into the video the viewer plays behind the person.
# Only what moves is taken from each frame: everywhere else (the hall, the crowd, the lamps) every frame is the
# sharp band itself (its same rows; or the loop's average without it), so nothing that stands still flickers with
# the render's own noise, and it is as sharp as the band. Frames rendered at half the band's width are scaled up.
# The loop is then filled out to 24 frames a second along the cloth's own motion (its end runs into its start), and
# written at full size and at half (<out>-lo.mp4) for phones.
import glob, os, shutil, subprocess, sys, tempfile
import numpy as np
from PIL import Image

SRC, OUT = sys.argv[1], sys.argv[2]
BAND = sys.argv[3] if len(sys.argv) > 3 else None
TILES = 4
files = sorted(glob.glob(os.path.join(SRC, "f*.png")))
n = len(files); print("frames", n)


def load(f):
    """a frame, at the band's own size (4096 across, four tiles stacked)"""
    im = Image.open(f).convert("RGB")
    if im.width < 4096: im = im.resize((4096, im.height * 4096 // im.width), Image.LANCZOS)
    return np.asarray(im)


first = load(files[0]); H, W, _ = first.shape
s1 = np.zeros((H, W, 3), np.float64); s2 = np.zeros((H, W, 3), np.float64)
for f in files:
    a = load(f).astype(np.float64); s1 += a; s2 += a * a
mean = s1 / n; std = np.sqrt(np.maximum(s2 / n - mean * mean, 0)).max(-1)
del s1, s2
if BAND:   # the band's same rows: the top H / TILES of each of its tiles
    b = np.asarray(Image.open(BAND).convert("RGB")); th, h = b.shape[0] // TILES, H // TILES
    mean = np.concatenate([b[i * th:i * th + h] for i in range(TILES)], 0).astype(np.float64)
    print("still parts from", BAND)


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
    a = load(f).astype(np.float32)
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
shutil.rmtree(tmp)
