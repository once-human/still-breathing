"""R=3 python3 sheet_auto.py: test sheet for the round-13 auto"""
import sys
from kit import *
from lib_life import *
from lib_r13 import *
rng = random.Random(7)
for x, yaw, kw in ((-4.2, 0.0, {}), (-1.0, -0.32, dict(wave=True)), (2.2, -0.6, dict(wave=True))):
    auto3(x, 12.3, yaw, rng, driver=True, **kw)
for x, yaw, kw in ((-1.5, math.pi + 0.05, dict(phone=True)), (1.0, math.pi - 0.03, dict(driver=False, sleeper=True))):
    auto3(x, 27.8, yaw, rng, light_side=1, **kw)
render('/tmp/claude-1000/-home-onkar-Documents/a4dfe67b-0718-408b-8186-b5f2b378874d/scratchpad/sa.png', '/tmp/claude-1000/-home-onkar-Documents/a4dfe67b-0718-408b-8186-b5f2b378874d/scratchpad/sa-prev.png')
im = Image.open('/tmp/claude-1000/-home-onkar-Documents/a4dfe67b-0718-408b-8186-b5f2b378874d/scratchpad/sa.png').convert('RGBA')
bg = Image.new('RGBA', im.size, (21, 21, 21, 255)); bg.alpha_composite(im)
bg.crop((0, 2400, 3600, 3450)).resize((1800, 525)).save('/tmp/claude-1000/-home-onkar-Documents/a4dfe67b-0718-408b-8186-b5f2b378874d/scratchpad/sa_near.png')
bg.crop((1350, 2000, 2400, 2500)).save('/tmp/claude-1000/-home-onkar-Documents/a4dfe67b-0718-408b-8186-b5f2b378874d/scratchpad/sa_far.png')
