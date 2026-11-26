"""primitive test sheet: R=1 python3 sheet.py -> sheet.png (things at their real places in the camera)"""
import time
from kit import *
from lib_life import *
t0 = time.time()
rng = random.Random(5)
dl = street_lamp(-4.9, 19, rng)
dr = street_lamp(4.9, 27, rng)
rain_tree(-6.3, 12.5, rng, d=1.35, rs=10.5, ncl=40)
dl(); dr()
auto_rickshaw(-2.6, 12.6, 0.06, rng)
auto_rickshaw(4.0, 28, math.pi + 0.05, rng, driver=False, sleeper=True)
car(2.4, 34, math.pi, rng)
car(-2.2, 24, 0.0, rng)
two_wheeler(-1.0, 20, False, rng, poncho='ice')
two_wheeler(2.0, 22, True, rng, poncho='green', box=True)
# a line-up of people at the couple's scale and smaller
for i, (x, h, f, arms, top, col) in enumerate([
        (160, 190, 'front', ('wave', 'swing'), 'tee', 'amber'),
        (300, 185, 'front', ('jacket', 'jacket'), 'shirt', 'copper'),
        (470, 175, 'back', ('swing', 'phone'), 'hoodie', None),
        (640, 180, 'left', ('swing', 'swing'), 'tee', 'green'),
        (800, 170, 'right', ('out', 'swing'), 'dress', 'ice'),
        (960, 180, 'front', ('hold', 'pocket'), 'jacket', 'green')]):
    J = figure(x, 1560, h, rng, facing=f, arms=arms, top=top, tcol=col, laugh=(i == 0), face_up=(i == 4),
               hair=['short', 'long', 'curly', 'bun', 'long', 'cap'][i])
    if i == 5:
        umbrella_closed(*J['hands'][0], h, rng)
for i in range(10):
    small_person(100 + i * 100, 1330, 40 + i * 6, rng, umb=('green' if i == 3 else None))
dog_curled(1080, 1200, 70, rng)
render('sheet.png', 'sheet-preview.png')
print('sheet', round(time.time() - t0, 1), 's')
