"""
Publish Atelier assets for the website.

  python tools/atelier_publish.py
    reads  tools/atelier_scenes.json, assets/scenes/<id>.png (kie.ai), .tmp/atelier_png/<scene>/<form>/*.png (Blender)
    writes assets/scenes/<id>.jpg (1600w) + <id>_thumb.jpg (360w)
           assets/atelier/<scene>/<form>/*.webp  (alpha WebP)
           assets/atelier/manifest.json          (only scenes whose layers exist for every form)
"""
import glob, json, os, sys
sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tint_normalize import normalize_white_body  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TINT_BODIES = {"body_concrete.png", "body_sand.png", "body_lava.png"}
CFG = json.load(open(os.path.join(ROOT, "tools", "atelier_scenes.json"), encoding="utf-8"))
SRC = os.path.join(ROOT, ".tmp", "atelier_png")
OUT = os.path.join(ROOT, "assets", "atelier")
FORMS = ["balloon", "highballoon", "egg", "talleg", "bowl", "box"]
W, H = CFG.get("resolution", [1600, 900])


def main():
    scenes = []
    for s in CFG["scenes"]:
        png = os.path.join(ROOT, s["image"])
        if not os.path.exists(png):
            print(f"[skip] {s['id']}: Szenenbild fehlt ({s['image']})"); continue
        im = Image.open(png).convert("RGB")
        # crop/scale to the render aspect so layers align 1:1
        tw = im.height * W / H
        if abs(tw - im.width) > 2:
            if tw < im.width:
                x = (im.width - tw) / 2; im = im.crop((int(x), 0, int(x + tw), im.height))
            else:
                th = im.width * H / W; y = (im.height - th) / 2; im = im.crop((0, int(y), im.width, int(y + th)))
        base = os.path.join(ROOT, "assets", "scenes", s["id"])
        im.resize((W, H), Image.LANCZOS).save(base + ".jpg", quality=86, optimize=True, progressive=True)
        im.resize((360, int(360 * H / W)), Image.LANCZOS).save(base + "_thumb.jpg", quality=80, optimize=True)
        complete = True
        for f in FORMS:
            pngs = glob.glob(os.path.join(SRC, s["id"], f, "*.png"))
            if not any(p.endswith("env.png") for p in pngs):
                complete = False; continue
            od = os.path.join(OUT, s["id"], f); os.makedirs(od, exist_ok=True)
            for p in pngs:
                dst = os.path.join(od, os.path.basename(p)[:-4] + ".webp")
                if os.path.exists(dst) and os.path.getmtime(dst) > os.path.getmtime(p):
                    continue
                im = Image.open(p).convert("RGBA")
                if os.path.basename(p) in TINT_BODIES:   # white layers: lit side -> ~96 % before the browser tints them
                    im = normalize_white_body(im)
                im.save(dst, "WEBP", quality=84, method=6)
        if not complete:
            print(f"[warn] {s['id']}: nicht alle Formen gerendert, Szene wird nicht veröffentlicht"); continue
        scenes.append({"id": s["id"], "name": s["name"], "image": f"assets/scenes/{s['id']}.jpg",
                       "thumb": f"assets/scenes/{s['id']}_thumb.jpg"})
        print(f"[ok] {s['id']}")
    os.makedirs(OUT, exist_ok=True)
    man = {"scenes": scenes, "forms": FORMS, "tint": ["concrete", "sand", "lava"]}
    json.dump(man, open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    size = sum(os.path.getsize(p) for p in glob.glob(os.path.join(OUT, "**", "*.webp"), recursive=True)) / 1e6
    print(f"manifest: {len(scenes)} Szenen, Layer gesamt {size:.1f} MB")


if __name__ == "__main__":
    sys.exit(main())
