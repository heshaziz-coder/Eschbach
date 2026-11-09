"""
Vertical Lines macro (kie.ai refuses the white fluted product photo as reference -> "NSFW" false positive,
and text-only results have irregular, bundled lines). Built deterministically instead:
  grain  = the photoreal Granite macro (.tmp/material/mat_granite.png), desaturated and lifted to warm white
  relief = perfectly regular vertical grooves, pitch measured on the shop photo (~5 mm), raking light from the left

  python tools/material_vertical.py   -> .tmp/material/mat_vertical.png  (then tools/material_publish.py)
"""
import os, sys
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = Image.open(os.path.join(ROOT, ".tmp", "material", "mat_granite.png")).convert("L")
W, H = src.size
g = np.asarray(src).astype(np.float32) / 255.0
g = np.asarray(Image.fromarray((g * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.2))).astype(np.float32) / 255.0
g = (g - g.mean()) * .32                                   # fine, even sandy grain (granite flecks blurred away)
FRAME_CM, PITCH_CM = 25.0, .5
pitch = W / (FRAME_CM / PITCH_CM)                          # px per groove
x = np.arange(W, dtype=np.float32)
rng = np.random.default_rng(7)
jit = np.cumsum(rng.normal(0, .015, W)).astype(np.float32)  # tiny hand-made irregularity, no bundling
ph = ((x + jit) / pitch) % 1.0
# groove profile: flat face, rounded groove occupying 38 % of the pitch
gw = .34
depth = np.where(ph < gw, np.sin(np.pi * ph / gw), 0.0)    # 0 = face, 1 = bottom of groove
slope = np.gradient(depth)                                 # light from the left: walls facing left are lit
shade = np.where(slope > 0, 1 - .30 * np.clip(slope * pitch / 6, 0, 1), 1 + .07 * np.clip(-slope * pitch / 6, 0, 1))
ao = 1 - .10 * depth                                       # occlusion inside the groove
row = (shade * ao).astype(np.float32)
lum = (.905 + g) * row[None, :]
yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]; xx = np.linspace(0, 1, W, dtype=np.float32)[None, :]
lum *= 1.02 - .06 * xx - .03 * (yy - .5) ** 2              # gentle light falloff to the right
warm = np.array([1.0, .985, .955], np.float32)             # warm off-white like "Vertical White"
rgb = np.clip(lum[..., None] * warm * 255, 0, 255).astype(np.uint8)
im = Image.fromarray(rgb).filter(ImageFilter.GaussianBlur(.6))
im.save(os.path.join(ROOT, ".tmp", "material", "mat_vertical.png"))
print("[ok] mat_vertical.png", im.size, f"Rillenabstand {pitch:.0f}px")
