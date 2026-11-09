"""
Publish the material macros for the material loupe (section "Material").

  python tools/material_publish.py

Input : .tmp/material/mat_<id>.png   (kie.ai 4K "flat material scan", tools/kie_material.json; vertical: tools/material_vertical.py)
Output: assets/textures/<id>.webp     (4400 px wide, read by js/app.js renderFlat; the loupe zooms x3)
ids   : loft, terra, antique, lava, granite, vertical  (= matChoices in js/app.js)

Clean-up so the surface reads as a perfectly flat sample (user feedback: no bulge, no falloff, no edges):
  1. crop a 4 % margin (AI images sometimes show an object edge in a corner)
  2. flatten large-scale illumination: divide luminance by a very soft blur of itself (removes bulge shading,
     vignetting and light falloff, keeps pores/grain/grooves)
  3. light unsharp mask for crisp detail under the x3 loupe
"""
import glob, os, sys
import numpy as np
from PIL import Image, ImageFilter

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "textures")
MARGIN, OUT_W, FLATTEN = .04, 4400, .9
os.makedirs(OUT, exist_ok=True)


def flatten(im, strength=FLATTEN):
    W, H = im.size
    small = im.convert("L").resize((max(8, W // 32), max(8, H // 32)), Image.BILINEAR).filter(ImageFilter.GaussianBlur(6))
    low = np.asarray(small.resize((W, H), Image.BICUBIC)).astype(np.float32) + 1
    gain = (low.mean() / low) ** strength
    a = np.asarray(im).astype(np.float32) * gain[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


for p in sorted(glob.glob(os.path.join(ROOT, ".tmp", "material", "mat_*.png"))):
    cid = os.path.basename(p)[4:-4]
    im = Image.open(p).convert("RGB")
    W, H = im.size
    mx, my = round(W * MARGIN), round(H * MARGIN)
    im = im.crop((mx, my, W - mx, H - my))
    im = flatten(im)
    w = min(OUT_W, im.width)
    im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    dst = os.path.join(OUT, f"{cid}.webp")
    im.save(dst, "WEBP", quality=84, method=6)
    print(f"[ok] {cid}: {im.size}  {os.path.getsize(dst) // 1024} KB")
