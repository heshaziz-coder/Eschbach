"""Normalize a WHITE tint-body layer so its lit side sits at ~96 % (shared by preview + publish).
The browser multiplies these layers by the swatch colour, so their absolute level sets the vessel's brightness."""
from PIL import Image


def normalize_white_body(im, target=245, pct=0.985):
    im = im.convert("RGBA")
    r, g, b, a = im.split()
    lum = Image.merge("RGB", (r, g, b)).convert("L")
    vals = sorted(v for v, al in zip(lum.getdata(), a.getdata()) if al > 250)
    if not vals:
        return im
    ref = max(1, vals[int(len(vals) * pct) - 1])
    k = target / ref
    lut = [min(255, int(round(i * k))) for i in range(256)]
    return Image.merge("RGBA", (r.point(lut), g.point(lut), b.point(lut), a))
