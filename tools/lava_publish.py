"""
Publish the Lava test (fully AI-rendered scenes) for the website atelier.

  python tools/lava_publish.py

Input : .tmp/lava/<scene>__<form>__<colour>.png  (kie.ai, tools/kie_lava_test.json)
Output: assets/lava/<scene>/<form>__<colour>.webp (1200x1500, 4:5), assets/lava/<scene>/thumb.webp and
        thumb__<form>__<colour>.webp (scene button previews per selection),
        assets/lava/catalog.json (read by js/app.js -> LAVA module)

Alignment: the reference image of every scene (REF form/colour) is cut out with rembg to find the pot
(foot line + width just above the foot). One crop per scene is chosen so the reference pot has the SAME
width and foot position in every scene; all images of that scene share the crop, so true size ratios between
forms (U Pot 90x70 vs Long Balloon 50x95) are preserved.
"""
import json, os, sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, ".tmp", "lava")
OUT = os.path.join(ROOT, "assets", "lava")
SCENES = [("lava_paris", "Pariser Altbau"), ("lava_garten", "Formaler Garten")]
FORMS = [("u-pot", "U Pot", "D 90 × H 70 cm", "1.070 €"), ("long-balloon", "Long Balloon", "D 50 × H 95 cm", "520 €")]
COLOURS = [("volcanic-black", "Volcanic Black", "#2e2d2c"), ("antique-white", "Antique White", "#e4ddd0")]
REF = ("u-pot", "volcanic-black")
OUT_W, OUT_H, FOOT_Y = 1200, 1500, .88
THUMB_BOX = (0, 495, 1200, 1395)      # 4:3, full width, ends 75 px below the foot (y 1320): whole planter visible; y 300-1200 cut it off


def pot_geometry(path):
    from rembg import new_session, remove
    im = Image.open(path).convert("RGB")
    a = np.asarray(remove(im, session=new_session("isnet-general-use"), only_mask=True)).astype(float) > 128
    H, W = a.shape
    rows = np.where(a.sum(1) > W * .05)[0]
    foot = rows.max()
    band = a[int(foot - H * .08):int(foot - H * .02)]
    widths = band.sum(1); i = int(np.argmax(widths)); r = band[i]
    xs = np.where(r)[0]
    return {"foot": int(foot), "width": int(xs[-1] - xs[0]), "cx": float((xs[-1] + xs[0]) / 2), "W": W, "H": H}


def main():
    geo = {}
    for sid, _ in SCENES:
        geo[sid] = g = pot_geometry(os.path.join(SRC, f"{sid}__{REF[0]}__{REF[1]}.png"))
        print(f"[pot] {sid}: Fuss y={g['foot']}  Breite={g['width']}px ({g['width'] / g['W']:.0%} der Bildbreite)  Mitte x={g['cx']:.0f}")
    t = max(g["width"] / g["W"] for g in geo.values())     # target pot width as fraction of the crop width (start: no upscaling of the biggest pot)
    crops = None
    for _ in range(60):                                       # zoom in (bigger pot fraction = smaller crop) until every crop fits inside its image
        crops, ok = {}, True
        for sid, g in geo.items():
            cw = g["width"] / t; ch = cw * OUT_H / OUT_W
            left, top = g["cx"] - cw / 2, g["foot"] - FOOT_Y * ch
            if left < 0 or top < 0 or left + cw > g["W"] or top + ch > g["H"]:
                ok = False
            crops[sid] = (left, top, left + cw, top + ch)
        if ok:
            break
        t *= 1.03
    print(f"[crop] Topfbreite einheitlich {t:.1%} der Bildbreite, Fuss bei {FOOT_Y:.0%} der Bildhoehe")
    for sid, box in crops.items():
        if box[0] < 0 or box[1] < 0:
            print(f"[warn] {sid}: Zuschnitt ragt aus dem Bild -> Topf leicht aus der Mitte")
    idx = {(r["form"], r["colour"]): r["product"] for r in json.load(open(os.path.join(ROOT, "fotos", "index.json"), encoding="utf-8"))
           if r["file"].startswith("fotos/lava/")}
    cat = {"collection": "Lava", "url": "https://eschbach-design.com/collections/pflanzkuebel-kollektion-lava",
           "scenes": [], "forms": [], "colours": [{"id": c, "name": n, "hex": h} for c, n, h in COLOURS]}
    for sid, name in SCENES:
        os.makedirs(os.path.join(OUT, sid), exist_ok=True)
        box = tuple(round(v) for v in crops[sid])
        for fid, *_ in FORMS:
            for cid, *_ in COLOURS:
                p = os.path.join(SRC, f"{sid}__{fid}__{cid}.png")
                if not os.path.exists(p):
                    print("[fehlt]", os.path.basename(p)); continue
                try:
                    im = Image.open(p).convert("RGB")
                except OSError:
                    print("[unvollstaendig, uebersprungen]", os.path.basename(p)); continue
                if im.size != (geo[sid]["W"], geo[sid]["H"]):
                    im = im.resize((geo[sid]["W"], geo[sid]["H"]), Image.LANCZOS)
                big = im.crop(box).resize((OUT_W, OUT_H), Image.LANCZOS)
                big.save(os.path.join(OUT, sid, f"{fid}__{cid}.webp"), "WEBP", quality=82, method=6)
                # scene button preview for exactly this form + colour (the atelier swaps them with the selection)
                big.crop(THUMB_BOX).resize((480, 360), Image.LANCZOS).save(os.path.join(OUT, sid, f"thumb__{fid}__{cid}.webp"), "WEBP", quality=78)
        ref = Image.open(os.path.join(OUT, sid, f"{REF[0]}__{REF[1]}.webp"))
        ref.crop(THUMB_BOX).resize((480, 360), Image.LANCZOS).save(os.path.join(OUT, sid, "thumb.webp"), "WEBP", quality=78)
        cat["scenes"].append({"id": sid, "name": name, "thumb": f"assets/lava/{sid}/thumb.webp"})
        print(f"[ok] {sid}")
    for fid, name, size, price in FORMS:
        thumb = f"assets/pots/lava/{fid}/volcanic-black.webp"
        variants = {cid: {"url": idx.get((name, cn), ""), "thumb": f"assets/pots/lava/{fid}/{cid}.webp"} for cid, cn, _ in COLOURS}
        cat["forms"].append({"id": fid, "name": name, "size": size, "price": price, "thumb": thumb, "variants": variants})
    json.dump(cat, open(os.path.join(OUT, "catalog.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[ok] assets/lava/catalog.json")


if __name__ == "__main__":
    main()
