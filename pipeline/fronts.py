# Where each shirt's front print sits on the chest. Read by texture.py (the render atlas) and printtex.py (the
# viewer's chest texture). Every front is drawn into one chest area of the front panel, the same for every shirt,
# so the viewer maps one rectangle and each shirt's texture carries its own art in its own place.
# Measures in cm: x across the front from the centre line (+ is the wearer's left), y down from the high shoulder
# point. Must match PRINT_FRONT in src/lib/viewer/print.ts.
AREA = dict(x0=-15.0, top=8.0, w=30.0, h=50.0)   # the front area: 30 x 50 cm, its top 8 cm under the shoulder point
AREA_PX_CM = 60                                   # the viewer's front texture: 1800 x 3000

# design: (file under pipeline/, centre x, top, width). None: the lineup's again.. in four scripts, left chest.
LETTERING = (None, 4 + 10.5 / 2, 15.0, 10.5)     # inner edge 4 cm off the centre front, top 15 cm under the shoulder
FRONTS = {
    "a": LETTERING, "b": LETTERING, "c": LETTERING, "d": LETTERING,
    # i am a party: the seal, in exactly the lettering's place and size on the other shirts (left chest, 10.5 cm wide)
    "e": ("art/fronts/e/06-the-seal-left-chest/art.png",) + LETTERING[1:],
    # actual life: the wristband (picks no. 09), turned to hang down the wearer's left front, clasp up, its tail
    # leaning 5 deg toward the centre front. 40 cm tall, from 17 to 57 cm under the shoulder point, centred 10 cm off
    # the centre front: inside the front print box (35.6 x 45.7 cm from the collar seam, 11.5 cm under the shoulder
    # point). art-down.png is art.png cropped to its ink and turned 95 deg.
    "f": ("art/fronts/c/05-wristband/art-down.png", 10.0, 17.0, 40.0 * 288 / 1666),
}
