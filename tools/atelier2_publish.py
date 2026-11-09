"""
Publish the photo-based atelier: real shop cut-outs + kie.ai scenes + per-scene light config.

  python tools/atelier2_publish.py

Inputs : fotos/index.json, fotos_cut/<coll>/<form>/<colour>.png (tools/cutout.py),
         assets/scenes_v2/<scene>.png (tools/kie_generate.py), tools/scene_light.json
Outputs: assets/pots/<coll>/<form>/<colour>.webp   (alpha, max 900 px high)
         assets/scenes_v2/<scene>.webp + <scene>_thumb.webp
         assets/atelier2/catalog.json  -> read by js/app.js (ATELIER module)
The light/shadow matching itself happens live in the browser (canvas), driven by scene_light.json.
"""
import json, os, re, sys
from PIL import Image, ImageStat

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = lambda *p: os.path.join(ROOT, *p)

SCENE_NAMES = {"terrasse": "Architektur-Terrasse", "lobby": "Hotel-Lobby", "garten": "Mediterraner Garten",
               "penthouse": "Penthouse", "studio": "Studio"}
SCENE_ORDER = ["terrasse", "lobby", "garten", "penthouse"]
COLL_ORDER = ["loft", "terra", "antique-stone", "lava", "pure", "granite", "vertical-lines", "heritage"]
COLL_NAMES = {"antique-stone": "Antique Stone", "vertical-lines": "Vertical Lines"}
COLL_URLS = {
    "loft": "https://eschbach-design.com/collections/pflanzkuebel-kollektion-loft",
    "terra": "https://eschbach-design.com/collections/pflanzkuebel-kollektion-terra",
    "antique-stone": "https://eschbach-design.com/collections/antique-collection",
    "lava": "https://eschbach-design.com/collections/pflanzkuebel-kollektion-lava",
    "pure": "https://eschbach-design.com/collections/pflanzkuebel-kollektion-pure",
    "granite": "https://eschbach-design.com/collections/granite",
    "vertical-lines": "https://eschbach-design.com/collections/kollektion-vertical-stripes",
    "heritage": "https://eschbach-design.com/collections/pflanzkuebel-kollektion-heritage",
}


def swatch(im):
    """Representative colour: median of opaque pixels in the middle band of the pot (avoids rim/inside)."""
    w, h = im.size
    c = im.crop((int(w * .3), int(h * .35), int(w * .7), int(h * .8)))
    px = [p[:3] for p in c.getdata() if p[3] > 250]
    if not px:
        px = [p[:3] for p in im.getdata() if p[3] > 250] or [(128, 128, 128)]
    med = [sorted(ch)[len(ch) // 2] for ch in zip(*px)]
    return "#%02x%02x%02x" % tuple(med)


def main():
    idx = json.load(open(J("fotos", "index.json"), encoding="utf-8"))
    colls = {}
    n = 0
    for r in idx:
        cid, fid, file = r["file"].split("/")[1], r["file"].split("/")[2], r["file"].split("/")[3]
        src = J("fotos_cut", cid, fid, file[:-4] + ".png")
        if not os.path.exists(src):
            print("[fehlt] Freisteller", src); continue
        dst_rel = f"assets/pots/{cid}/{fid}/{file[:-4]}.webp"
        im = Image.open(src).convert("RGBA")
        if im.height > 900:
            im = im.resize((round(im.width * 900 / im.height), 900), Image.LANCZOS)
        if not os.path.exists(J(dst_rel)) or os.path.getmtime(J(dst_rel)) < os.path.getmtime(src):
            os.makedirs(os.path.dirname(J(dst_rel)), exist_ok=True)
            im.save(J(dst_rel), "WEBP", quality=88, method=6)
        c = colls.setdefault(cid, {"id": cid, "name": COLL_NAMES.get(cid, re.sub(r"(?i)\s*collection\s*", "", r["collection"]).strip()),
                                   "url": COLL_URLS.get(cid, ""), "forms": {}})
        f = c["forms"].setdefault(fid, {"id": fid, "name": r["form"], "colours": []})
        f["colours"].append({"id": file[:-4], "name": r["colour"], "hex": swatch(im), "img": dst_rel,
                             "w": im.width, "h": im.height, "url": r["product"]})
        n += 1
    out_colls = []
    for cid in COLL_ORDER + sorted(set(colls) - set(COLL_ORDER)):
        if cid in colls:
            c = colls[cid]; c["forms"] = list(c["forms"].values()); out_colls.append(c)

    light = json.load(open(J("tools", "scene_light.json"), encoding="utf-8"))
    scenes = []
    for sid in SCENE_ORDER:
        if sid not in light:
            print("[warn] kein Licht-Setup fuer", sid); continue
        png = J("assets", "scenes_v2", f"{sid}.png")
        im = Image.open(png).convert("RGB")
        big = im.resize((2400, round(im.height * 2400 / im.width)), Image.LANCZOS)
        big.save(J("assets", "scenes_v2", f"{sid}.webp"), "WEBP", quality=84, method=6)
        th = im.resize((320, round(im.height * 320 / im.width)), Image.LANCZOS)
        th.save(J("assets", "scenes_v2", f"{sid}_thumb.webp"), "WEBP", quality=80)
        cfg = {k: v for k, v in light[sid].items() if k != "image"}
        scenes.append({"id": sid, "name": SCENE_NAMES.get(sid, sid), "image": f"assets/scenes_v2/{sid}.webp",
                       "thumb": f"assets/scenes_v2/{sid}_thumb.webp", "w": big.width, "h": big.height, "light": cfg})
    os.makedirs(J("assets", "atelier2"), exist_ok=True)
    json.dump({"scenes": scenes, "collections": out_colls}, open(J("assets", "atelier2", "catalog.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"[ok] {n} Toepfe, {len(out_colls)} Kollektionen, {len(scenes)} Szenen -> assets/atelier2/catalog.json")


if __name__ == "__main__":
    main()
