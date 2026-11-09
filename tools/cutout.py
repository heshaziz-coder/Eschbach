"""
Cut out the shop product photos (white studio background + soft baked drop shadow) -> transparent PNG.

  python tools/cutout.py [--model isnet-general-use] [--only lava,vertical-lines] [--limit N] [--force]
    fotos/<coll>/<form>/<colour>.jpg -> fotos_cut/<coll>/<form>/<colour>.png  (cropped to the pot, RGBA)

rembg (local, free). First run downloads the model into ~/.u2net.
The baked drop shadow must NOT survive: the scene compositor draws its own shadow. Pixels that are
near-white/grey AND only partially opaque at the bottom are the shadow -> --shadow-cut drops alpha there.
"""
import argparse, glob, json, os, sys, time
from PIL import Image, ImageChops, ImageFilter

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="isnet-general-use")
ap.add_argument("--only", default="")
ap.add_argument("--files", default="", help="comma list of fotos/... paths (tests)")
ap.add_argument("--out", default=os.path.join(ROOT, "fotos_cut"))
ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--force", action="store_true")
A = ap.parse_args()

from rembg import new_session, remove  # noqa: E402
session = new_session(A.model)

files = A.files.split(",") if A.files else sorted(glob.glob(os.path.join(ROOT, "fotos", "*", "*", "*.jpg")))
if A.only:
    keep = set(A.only.split(","))
    files = [f for f in files if os.path.relpath(f, os.path.join(ROOT, "fotos")).replace("\\", "/").split("/")[0] in keep]
if A.limit:
    files = files[:A.limit]

t0 = time.time()
for i, f in enumerate(files, 1):
    f = f if os.path.isabs(f) else os.path.join(ROOT, f)
    rel = os.path.relpath(f, os.path.join(ROOT, "fotos"))
    dst = os.path.join(A.out, os.path.splitext(rel)[0] + ".png")
    if os.path.exists(dst) and not A.force:
        continue
    im = Image.open(f).convert("RGB")
    cut = remove(im, session=session, post_process_mask=True)
    a = cut.getchannel("A")
    # kill faint leftovers (shadow haze / white fringe) but keep the anti-aliased edge
    a = a.point(lambda v: 0 if v < 24 else v)
    # decontaminate edges: white background bleeds into semi-transparent edge pixels -> darken them slightly
    rgb = im.copy()
    edge = ImageChops.subtract(a.point(lambda v: 255 if v > 250 else 0).filter(ImageFilter.MaxFilter(3)),
                               a.point(lambda v: 255 if v > 250 else 0))
    inner = im.filter(ImageFilter.MinFilter(5))
    rgb = Image.composite(inner, rgb, edge)
    out = Image.merge("RGBA", (*rgb.split(), a))
    bb = a.getbbox()
    if bb:
        out = out.crop(bb)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    out.save(dst, optimize=True)
    el = time.time() - t0
    print(f"[{i}/{len(files)}] {rel}  {out.size}  ({el / i:.1f}s/Bild)", flush=True)
print("DONE")
