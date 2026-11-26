#!/usr/bin/env python3
"""
check.py: look at the work like an artist, and check it like a printer.

    python3 check.py crops art.png [ground=#151515] [out_dir]      1:1 crops (focal grid + thumbnail) to LOOK at with Read
    python3 check.py crop art.png x y [w h] [ground] [out.png]     one 1:1 crop at unit coords x, y (units = px / 3)
    python3 check.py verify art.png [min_px=10] [margin_px=40]     binary alpha, specks/hairlines under min_px, edge margin
"""
import sys, os
import numpy as np
from PIL import Image, ImageFilter


def on_ground(img, ground):
    g = ground.lstrip('#')
    bg = Image.new('RGBA', img.size, tuple(int(g[i:i + 2], 16) for i in (0, 2, 4)) + (255,))
    bg.alpha_composite(img.convert('RGBA'))
    return bg.convert('RGB')


def crops(path, ground='#151515', out=None):
    img = Image.open(path).convert('RGBA')
    out = out or os.path.join(os.path.dirname(os.path.abspath(path)), 'crops')
    os.makedirs(out, exist_ok=True)
    rgb = on_ground(img, ground)
    W, H = rgb.size
    cw, ch = min(1200, W), min(900, H)
    n = 0
    for fy in (0.2, 0.5, 0.8):
        for fx in (0.25, 0.75):
            x, y = int(W * fx - cw / 2), int(H * fy - ch / 2)
            x, y = max(0, min(W - cw, x)), max(0, min(H - ch, y))
            rgb.crop((x, y, x + cw, y + ch)).save(os.path.join(out, f'crop-{n}-{x}-{y}.png'))
            n += 1
    rgb.resize((W // 4, H // 4), Image.LANCZOS).save(os.path.join(out, 'thumb-25pc.png'))
    rgb.resize((max(1, W // 16), max(1, H // 16)), Image.LANCZOS).save(os.path.join(out, 'thumb-across-the-room.png'))
    print('crops in', out)


def crop(path, x, y, w=1200, h=900, ground='#151515', outp=None):
    img = Image.open(path).convert('RGBA')
    s = img.width / 1200.0
    X, Y = int(x * s - w / 2), int(y * s - h / 2)
    X, Y = max(0, min(img.width - w, X)), max(0, min(img.height - h, Y))
    outp = outp or f'crop-{int(x)}-{int(y)}.png'
    on_ground(img, ground).crop((X, Y, X + w, Y + h)).save(outp)
    print(outp)


def verify(path, min_px=10, margin_px=40):
    img = Image.open(path)
    print('size', img.size, img.mode)
    if img.mode != 'RGBA':
        print('FAIL: not RGBA'); return
    a = np.asarray(img.getchannel('A'))
    partial = int(((a > 0) & (a < 255)).sum())
    print('binary alpha:', 'ok' if partial == 0 else f'FAIL ({partial} partial pixels)')
    m = img.getchannel('A').point(lambda p: 255 if p >= 128 else 0)
    k = int(min_px) if int(min_px) % 2 else int(min_px) - 1
    opened = m.filter(ImageFilter.MinFilter(k)).filter(ImageFilter.MaxFilter(k))
    closed = m.filter(ImageFilter.MaxFilter(k)).filter(ImageFilter.MinFilter(k))
    thin = int((np.asarray(m) > np.asarray(opened)).sum())
    gaps = int((np.asarray(closed) > np.asarray(m)).sum())
    ink = int((np.asarray(m) > 0).sum()) or 1
    print(f'ink thinner than {k}px: {thin} px ({100 * thin / ink:.2f}% of ink)', '(ok)' if thin / ink < 0.005 else '(check)')
    print(f'gaps narrower than {k}px: {gaps} px ({100 * gaps / ink:.2f}% of ink)', '(info: also counts the corners where marks meet; look at a crop if it is high)')
    bb = m.getbbox()
    if bb:
        mg = min(bb[0], bb[1], img.width - bb[2], img.height - bb[3])
        print('edge margin', mg, 'px', 'ok' if mg >= margin_px else 'FAIL')


if __name__ == '__main__':
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == 'crops':
        crops(*args)
    elif cmd == 'crop':
        p, x, y = args[0], float(args[1]), float(args[2])
        rest = args[3:]
        w = int(rest[0]) if len(rest) > 0 else 1200
        h = int(rest[1]) if len(rest) > 1 else 900
        crop(p, x, y, w, h, rest[2] if len(rest) > 2 else '#151515', rest[3] if len(rest) > 3 else None)
    elif cmd == 'verify':
        verify(args[0], *[int(v) for v in args[1:]])
