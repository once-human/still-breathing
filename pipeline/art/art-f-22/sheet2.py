"""R=3 python3 sheet2.py: test sheet for the round-2 tree primitives"""
import time
from kit import *
from lib_life import *
from lib_v3 import *
rng = random.Random(7)
LAMPS.append((-1.0, 7.9, 12.0))
leaf_mass3(180, 150, 130, 80, rng, lit=0.0)
leaf_mass3(450, 170, 110, 70, rng, lit=0.8)
leaf_mass3(300, 330, 140, 85, rng, lit=0.5)
leaf_mass3(560, 330, 60, 38, rng, lit=0.3, sc=0.8)
limb3([(160, 900), (200, 780), (250, 680), (300, 600)], 70, 26, rng, lit=0.8)
trunk3([(150, 1150), (155, 1040), (165, 940), (178, 880)], [200, 150, 126, 112], rng, lit_side=1, lit=0.75, moss=0.8, knots=2, wc=6.5)
trunk3([(480, 1000), (485, 900), (490, 820)], [80, 56, 50], rng, lit_side=-1, lit=0.6, moss=0.6, knots=1, wc=4.5, roots=[(-0.6, 0.5), (0.1, 0.3), (0.6, 0.5)])
d = street_lamp2(5.1, 13.0, rng); d()
cloud_body2(600, 600, 220, 80, rng)
render('sheet2.png', 'sheet2-preview.png')
im = Image.open('sheet2.png').convert('RGBA')
bg = Image.new('RGBA', im.size, (21, 21, 21, 255)); bg.alpha_composite(im)
bg.crop((0, 0, 2100, 1500)).resize((1050, 750)).save('/tmp/claude-1000/-home-onkar-Documents/a4dfe67b-0718-408b-8186-b5f2b378874d/scratchpad/s_a.png')
bg.crop((0, 1500, 2100, 3600)).resize((1050, 1050)).save('/tmp/claude-1000/-home-onkar-Documents/a4dfe67b-0718-408b-8186-b5f2b378874d/scratchpad/s_b.png')
bg.crop((2100, 900, 3600, 3300)).resize((750, 1200)).save('/tmp/claude-1000/-home-onkar-Documents/a4dfe67b-0718-408b-8186-b5f2b378874d/scratchpad/s_c.png')
