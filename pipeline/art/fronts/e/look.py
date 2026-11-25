# look.py <pair.png> <out.png>: the front panel of a pair, smaller, to look at
import sys
from PIL import Image
im = Image.open(sys.argv[1]); w, h = im.size
im.crop((0, 0, w // 2, h)).resize((w // 4, h // 2), Image.LANCZOS).save(sys.argv[2])
