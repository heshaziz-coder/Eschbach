"""
Fetch ESCHBACH product data + photos from the public Shopify store (eschbach-design.com).

  python tools/shop_fetch.py sitemap              -> fotos/<collection>/<form>/<colour>.jpg + fotos/index.json  (USE THIS)
  python tools/shop_fetch.py meta                 -> .tmp/shop/<collection>.json  (products, variants, image urls)
  python tools/shop_fetch.py images [--max 2000]  -> fotos/<collection>/<product>/<nn>__<variant>.<ext>

Polite by design: the store answers 429 "local_rate_limited" when hit quickly, so every request
waits DELAY seconds and backs off (30s, 60s, 120s, 240s) on 429. Already downloaded files are skipped.
"""
import json, os, re, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://eschbach-design.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
DELAY = 4
COLLECTIONS = {
    "loft": "pflanzkuebel-kollektion-loft",
    "terra": "pflanzkuebel-kollektion-terra",
    "antique": "antique-collection",
    "lava": "pflanzkuebel-kollektion-lava",
    "pure": "pflanzkuebel-kollektion-pure",
    "granite": "granite",
    "vertical": "kollektion-vertical-stripes",
    "heritage": "pflanzkuebel-kollektion-heritage",
}
META = os.path.join(ROOT, ".tmp", "shop")


def get(url, binary=False):
    for wait in (0, 30, 60, 120, 240):
        if wait:
            print(f"  429 -> warte {wait}s", flush=True); time.sleep(wait)
        time.sleep(DELAY)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
                return data if binary else data.decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
    raise RuntimeError(f"still rate limited: {url}")


def meta():
    os.makedirs(META, exist_ok=True)
    for cid, handle in COLLECTIONS.items():
        dst = os.path.join(META, f"{cid}.json")
        if os.path.exists(dst):
            print("[skip]", cid); continue
        data = json.loads(get(f"{BASE}/collections/{handle}/products.json?limit=250"))
        json.dump(data, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        ps = data["products"]
        print(f"[ok] {cid}: {len(ps)} Produkte, {sum(len(p['images']) for p in ps)} Bilder", flush=True)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")).strip("-")[:60]


def images(maxw=2000):
    for cid in COLLECTIONS:
        p = os.path.join(META, f"{cid}.json")
        if not os.path.exists(p):
            continue
        for prod in json.load(open(p, encoding="utf-8"))["products"]:
            vname = {}
            for v in prod["variants"]:
                if v.get("featured_image"):
                    vname[v["featured_image"]["id"]] = v["title"]
            out = os.path.join(ROOT, "fotos", cid, slug(prod["handle"]))
            os.makedirs(out, exist_ok=True)
            for i, im in enumerate(prod["images"], 1):
                src = im["src"].split("?")[0]
                ext = os.path.splitext(src)[1] or ".jpg"
                tag = slug(vname.get(im["id"], "")) or "bild"
                dst = os.path.join(out, f"{i:02d}__{tag}{ext}")
                if os.path.exists(dst):
                    continue
                open(dst, "wb").write(get(f"{src}?width={maxw}", binary=True))
                print("[ok]", os.path.relpath(dst, ROOT), flush=True)


def sitemap():
    """Product sitemap is NOT rate limited (collection pages + products.json are).
    Each product = one form x collection x colour, with its studio cut-out (<...>-cut-01.jpg, 2048 px)."""
    idx = get(f"{BASE}/sitemap.xml")
    maps = [m.replace("&amp;", "&") for m in re.findall(r"<loc>([^<]*sitemap_products[^<]*)</loc>", idx)]
    rows = []
    for m in maps:
        xml = get(m)
        for block in re.findall(r"<url>(.*?)</url>", xml, re.S):
            loc = re.search(r"<loc>([^<]*)</loc>", block)
            img = re.search(r"<image:loc>([^<]*)</image:loc>", block)
            tit = re.search(r"<image:title>([^<]*)</image:title>", block)
            if loc and img and tit:
                rows.append({"url": loc.group(1), "img": img.group(1).replace("&amp;", "&"), "title": tit.group(1).replace("&amp;", "&")})
    os.makedirs(META, exist_ok=True)
    json.dump(rows, open(os.path.join(META, "sitemap_products.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(rows)} Produkte mit Bild in der Sitemap", flush=True)
    index = []
    for r in rows:
        parts = [p.strip() for p in r["title"].split("|")]
        if len(parts) < 3:
            print("[?] unbekanntes Titelformat:", r["title"]); continue
        form, coll, colour = parts[0], parts[1], parts[-1]
        cid = slug(re.sub(r"(?i)\bcollection\b|\bkollektion\b", "", coll))
        out = os.path.join(ROOT, "fotos", cid, slug(form))
        os.makedirs(out, exist_ok=True)
        src = r["img"].split("?")[0]
        dst = os.path.join(out, slug(colour) + (os.path.splitext(src)[1] or ".jpg"))
        index.append({"collection": coll, "form": form, "colour": colour, "file": os.path.relpath(dst, ROOT).replace("\\", "/"), "product": r["url"]})
        if os.path.exists(dst):
            continue
        req = urllib.request.Request(src, headers={"User-Agent": UA})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    open(dst, "wb").write(resp.read())
                break
            except urllib.error.HTTPError as e:
                if e.code not in (429, 500, 502, 503, 504) or attempt == 3:
                    raise
                time.sleep(30 * (attempt + 1))
        time.sleep(.4)
        print("[ok]", os.path.relpath(dst, ROOT), flush=True)
    json.dump(index, open(os.path.join(ROOT, "fotos", "index.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Fertig: {len(index)} Fotos, Index in fotos/index.json")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "meta"
    if cmd == "sitemap":
        DELAY = 1
        sitemap()
    elif cmd == "meta":
        meta()
    else:
        mw = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 2000
        images(mw)
