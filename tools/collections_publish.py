"""
Collection images in the atelier style (2026-11-11): kie.ai scenes with the real shop product as reference
(tools/kie_collections.json, 2 variants per collection, 1856x2304) -> chosen variant -> .tmp/collections/<id>.png
(1100x1400, the format js/app.js expects) -> tools/optimize_images.py makes assets/collections/<id>.webp + -760.webp.

  python tools/kie_generate.py --jobs tools/kie_collections.json --out .tmp/coll2
  python tools/collections_publish.py
  python tools/optimize_images.py

Picks were made by eye (pot centred and clean, no second planter, no centre seam). The previous shop photos are
kept in .tmp/collections_shop/.
"""
import os, shutil, sys
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PICKS = {"loft": "a", "terra": "a", "antique": "b", "lava": "b", "pure": "a", "granite": "b", "vertical": "b", "empire": "a"}
W, H = 1100, 1400

src_dir, dst_dir = os.path.join(ROOT, ".tmp", "coll2"), os.path.join(ROOT, ".tmp", "collections")
bak = os.path.join(ROOT, ".tmp", "collections_shop")
if not os.path.exists(bak):
    shutil.copytree(dst_dir, bak)
for cid, v in PICKS.items():
    im = Image.open(os.path.join(src_dir, f"{cid}_{v}.png")).convert("RGB")
    cw = round(im.height * W / H); x0 = (im.width - cw) // 2          # 4:5 -> 11:14, trim the sides evenly
    im.crop((x0, 0, x0 + cw, im.height)).resize((W, H), Image.LANCZOS).save(os.path.join(dst_dir, f"{cid}.png"))
    print(f"[ok] {cid} <- {cid}_{v}.png")
