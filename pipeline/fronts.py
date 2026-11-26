# Where each shirt's front print sits on the chest. Read by texture.py (the render atlas) and printtex.py (the
# viewer's chest texture). Every front is drawn into one chest area of the front panel, the same for every shirt,
# so the viewer maps one rectangle and each shirt's texture carries its own art in its own place.
# Measures in cm: x across the front from the centre line (+ is the wearer's left), y down from the high shoulder
# point. Must match PRINT_FRONT in src/lib/viewer/print.ts.
AREA = dict(x0=-15.0, top=8.0, w=30.0, h=30.0)   # the chest area: 30 x 30 cm, its top 8 cm under the shoulder point
AREA_PX_CM = 60                                   # the viewer's chest texture: 1800 x 1800

# design: (file under pipeline/, centre x, top, width). None: the lineup's again.. in four scripts, left chest.
LETTERING = (None, 4 + 10.5 / 2, 15.0, 10.5)     # inner edge 4 cm off the centre front, top 15 cm under the shoulder
FRONTS = {
    "a": LETTERING, "b": LETTERING, "c": LETTERING, "d": LETTERING,
    # i am a party: the seal, 21.1 cm across on the centre chest. The front neck drops 9.5 cm and its rib is 2 cm, so
    # the collar seam is 11.5 cm under the shoulder point at the centre; the seal starts 3.5 cm under it and centres
    # about on the chest line
    "e": ("art/fronts/e/05-the-seal/art.png", 0.0, 15.0, 21.1),
    # actual life: the wristband (picks no. 09), sized by eye to look as big as the lettering block on the others: a
    # thin band needs far more width than a squarish block, so 18 cm across, from 3 cm past the centre front out to
    # the chest area's edge, top 16 cm under the shoulder point (art-tight.png is art.png cropped to its ink)
    "f": ("art/fronts/c/05-wristband/art-tight.png", -3 + 18.0 / 2, 16.0, 18.0),
}
