"""shared set-up for the d fronts. Units are the back's own: 1 unit = 0.3175 mm (the back is 1200 x 1600 units over
38.1 x 50.8 cm), so the toolkit's pen, wobble and 1 mm minimum (MINW 3.4 u) behave exactly as on the back.
R=1 python3 gen.py -> draft; python3 gen.py -> final at R=3 = 94.5 px per cm of print."""
import os, sys

U_PER_CM = 1200 / 38.1        # 31.5 units a centimetre
INK = {'key': '#22201D', 'green': '#2F7D52', 'lake': '#6E95CE', 'sound': '#2C46BE',   # the back's own four inks
       'yellow': '#F2C230', 'red': '#C8372D'}
TEE = '#FFFAE7'


def canvas(w_cm, h_cm):
    draft = os.environ.get('R') == '1'
    uw, uh = round(w_cm * U_PER_CM), round(h_cm * U_PER_CM)
    os.environ['R'] = str(round(min(1.5, 1500.0 / max(uw, uh)), 3)) if draft else '3'
    os.environ['UW'], os.environ['UH'] = str(uw), str(uh)
    os.environ.setdefault('MINW', '3.4')
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    return draft, uw, uh


def save(rgba, here, draft, tag=''):
    import hand
    if draft:
        p = os.path.join(here, f'draft{tag}.png')
        hand.save_preview(rgba, TEE, p, size=rgba.size); print('draft', p, rgba.size)
    else:
        rgba.save(os.path.join(here, 'art.png'))
        hand.save_preview(rgba, TEE, os.path.join(here, 'preview.png'),
                          size=(1000, int(1000 * rgba.height / rgba.width)))
        print('final', rgba.size)
