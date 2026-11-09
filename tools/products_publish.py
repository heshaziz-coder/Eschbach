"""
Publish Blender product shots + surface macros for the website.

  python tools/products_publish.py
    .tmp/products_png/products/<id>.png  -> assets/products/<id>.webp   (900x900, alpha)
    .tmp/products_png/textures/<id>.png  -> assets/textures/<id>.webp   (1920x1080)
"""
import glob, os, sys
from PIL import Image, ImageChops

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, ".tmp", "products_png")


def feather_shadow(im, edge=.16):
    """The shadow catcher darkens the whole floor -> hard rectangle at the image border.
    Fade only the semi-transparent shadow pixels towards the edges; opaque vessel pixels stay."""
    W, H = im.size
    r, g, b, a = im.split()
    ex, ey = int(W * edge), int(H * edge)
    mask = Image.new("L", (W, H), 0)
    px = mask.load()
    for y in range(H):
        fy = min(1, y / ey, (H - 1 - y) / ey)
        for x in range(W):
            fx = min(1, x / ex, (W - 1 - x) / ex)
            px[x, y] = int(255 * max(0, min(fx, fy)) ** 1.5)
    faded = ImageChops.multiply(a, mask)
    a2 = Image.composite(a, faded, a.point(lambda v: 255 if v >= 250 else 0))
    return Image.merge("RGBA", (r, g, b, a2))

for sub, size, q in (("products", (900, 900), 86), ("textures", None, 84)):
    out = os.path.join(ROOT, "assets", sub); os.makedirs(out, exist_ok=True)
    for p in sorted(glob.glob(os.path.join(SRC, sub, "*.png"))):
        im = Image.open(p)
        im = im.convert("RGBA") if sub == "products" else im.convert("RGB")
        if size:
            im = im.resize(size, Image.LANCZOS)
        if sub == "products":
            im = feather_shadow(im)
        dst = os.path.join(out, os.path.basename(p)[:-4] + ".webp")
        im.save(dst, "WEBP", quality=q, method=6)
        print(f"[ok] {sub}/{os.path.basename(dst)}  {os.path.getsize(dst) // 1024} KB")
