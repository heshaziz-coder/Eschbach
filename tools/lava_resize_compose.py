"""
True-size recomposition for the Lava test (kie.ai does not keep exact sizes when swapping planters).

  python tools/lava_resize_compose.py --scene lava_paris --form long-balloon --colour volcanic-black --diam 50

Inputs : .tmp/lava/<scene>__u-pot__volcanic-black.png  (reference: U Pot = 90 cm diameter -> px/cm, foot line, plant)
         .tmp/lava/<scene>__plate.png                   (same scene without planter/plant, kie.ai edit)
         fotos_cut/lava/<form>/<colour>.png             (real shop cut-out)
Output : .tmp/lava/<scene>__<form>__<colour>__raw.png  -> then kie.ai plants the reference plant + integrates soil/shadow/light
(default: planter only; rembg misses airy crowns, and a transplanted plant drags the wider U Pot rim along)
"""
import argparse, os, sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("--scene", required=True); ap.add_argument("--form", required=True); ap.add_argument("--colour", required=True)
ap.add_argument("--diam", type=float, required=True, help="real diameter of the new planter in cm")
ap.add_argument("--ref-diam", type=float, default=90)
ap.add_argument("--with-plant", action="store_true", help="transplant the plant from the reference (fails for airy crowns like maples)")
A = ap.parse_args()
J = lambda *p: os.path.join(ROOT, *p)


def widest(a):  # max opaque row width of a boolean mask
    return int(a.sum(1).max())


from rembg import new_session, remove  # noqa: E402
S = new_session("isnet-general-use")
ref = Image.open(J(".tmp", "lava", f"{A.scene}__u-pot__volcanic-black.png")).convert("RGB")
plate = Image.open(J(".tmp", "lava", f"{A.scene}__plate.png")).convert("RGB").resize(ref.size, Image.LANCZOS)
m = np.asarray(remove(ref, session=S, only_mask=True)) > 128
H, W = m.shape
rows = np.where(m.sum(1) > W * .05)[0]; foot = int(rows.max())

# reference pot in the scene: scale the U Pot cut-out onto the scene pot (its widest row = 90 cm)
ucut = Image.open(J("fotos_cut", "lava", "u-pot", "volcanic-black.png")).convert("RGBA")
ua = np.asarray(ucut.getchannel("A")) > 128
band = m[int(foot - H * .35):foot + 1]
pot_w = int(band.sum(1).max())                                  # scene U Pot width (pot only: lower band)
pxcm = pot_w / A.ref_diam
u_h = ucut.height * pot_w / widest(ua)                          # visible U Pot height in the scene
rim_u = foot - u_h
cx = float(np.mean([np.where(r)[0].mean() for r in band if r.any()]))
print(f"Massstab {pxcm:.2f} px/cm, Fuss y={foot}, U-Pot-Rand y={rim_u:.0f}, Mitte x={cx:.0f}")

# new planter at true size
cut = Image.open(J("fotos_cut", "lava", A.form, f"{A.colour}.png")).convert("RGBA")
ca = np.asarray(cut.getchannel("A")) > 128
s = A.diam * pxcm / widest(ca)
nw, nh = round(cut.width * s), round(cut.height * s)
cut = cut.resize((nw, nh), Image.LANCZOS)
x0, y0 = round(cx - nw / 2), foot - nh
print(f"neuer Topf {nw}x{nh}px ({A.diam:.0f} cm breit), Rand y={y0}  (U Pot Rand {rim_u:.0f}) -> Pflanze {rim_u - y0:+.0f}px")

# plant from the reference image: salient mask above the U Pot rim (+ a few px into the opening)
pm = m.copy(); pm[int(rim_u + u_h * .06):, :] = False
plant = ref.copy(); plant.putalpha(Image.fromarray((pm * 255).astype(np.uint8)))
dy = round(rim_u - y0)
comp = plate.copy()
comp.paste(cut, (x0, y0), cut)
if A.with_plant:
    comp.paste(plant, (0, -dy), plant)
out = J(".tmp", "lava", f"{A.scene}__{A.form}__{A.colour}__raw.png")
comp.save(out); print("[ok]", out)
