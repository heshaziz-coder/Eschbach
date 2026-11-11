"""
Responsive image variants + icons (page weight). Run after new source images arrive.

  python tools/optimize_images.py

  collections  .tmp/collections/<id>.png (shop collection photos, 1100x1400)
               -> assets/collections/<id>.webp (1100w) + <id>-760.webp   (srcset in js/app.js)
  hero         assets/hero_src.png|jpg if present, else the published assets/hero.webp
               -> assets/hero.webp (max 1856w) + hero-1280.webp
               .tmp/hero/hero_wide_final.png -> assets/hero-wide.webp + hero-wide-1600.webp (desktop, 16:9) + hero_m.webp (phone crop)
  textures     assets/textures/<id>.webp -> <id>-2400.webp (loupe picks by screen) + <id>-480.webp (preview), js/app.js renderFlat
  icons        assets/brand/logo-mark.png -> favicon-32.png, favicon-180.png (apple-touch-icon)

Sources that are missing are skipped (published files stay as they are).
"""
import glob, os, sys
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = lambda *p: os.path.join(ROOT, *p)


def save(im, path, w=None, q=80):
    if w and im.width > w:
        im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    im.save(path, "WEBP", quality=q, method=6)
    print(f"[ok] {os.path.relpath(path, ROOT):42s} {im.width}x{im.height}  {os.path.getsize(path) // 1024} KB")


def collections():
    for p in sorted(glob.glob(J(".tmp", "collections", "*.png"))):
        cid = os.path.basename(p)[:-4]; im = Image.open(p).convert("RGB")
        save(im, J("assets", "collections", f"{cid}.webp"), 1100, 80)
        save(im, J("assets", "collections", f"{cid}-760.webp"), 760, 78)


def hero():
    src = next((f for f in (J("assets", "hero_src.png"), J("assets", "hero_src.jpg"),
                            J(".tmp", "lava", "lava_villa__u-pot__volcanic-black.png")) if os.path.exists(f)), None)
    if not src:
        print("[skip] hero: keine Quelle"); return
    im = Image.open(src).convert("RGB")
    save(im, J("assets", "hero.webp"), 1856, 82)
    save(im, J("assets", "hero-1280.webp"), 1280, 80)
    # 16:9 outpaint of the same scene (tools/kie_hero.json), desktop hero + video poster; since 2026-11-11 the version with
    # the gently rippled pool (tools/hero_cinemagraph.py still) so the poster matches the first video frame
    wide = next((f for f in (J(".tmp", "hero2", "still_wide.png"), J(".tmp", "hero", "hero_wide_final.png")) if os.path.exists(f)), "")
    if os.path.exists(wide):
        w = Image.open(wide).convert("RGB")
        save(w, J("assets", "hero-wide.webp"), 2752, 82)
        save(w, J("assets", "hero-wide-1600.webp"), 1600, 80)
        # phone poster = exactly the phone video crop (tools/hero_video.py: 608 px wide, centred on x=1357 of the
        # 1920 frame, which is the wide still trimmed by 10 px per side) -> no jump when the video fades in
        cw, cx0 = 864, 10 + 1498                  # = VIEWS["hero_m.mp4"] in tools/hero_cinemagraph.py (still frame + 10 px trim)
        save(w.crop((cx0, 0, cx0 + cw, w.height)), J("assets", "hero_m.webp"), 900, 82)


def textures():
    for p in sorted(glob.glob(J("assets", "textures", "*.webp"))):
        if p.endswith("-2400.webp") or p.endswith("-480.webp"):
            continue
        im = Image.open(p).convert("RGB")
        save(im, p[:-5] + "-2400.webp", 2400, 80)
        save(im, p[:-5] + "-480.webp", 480, 70)      # instant preview while the big one loads (js/app.js renderFlat)


def icons():
    src = J("assets", "brand", "logo-mark.png")
    if not os.path.exists(src):
        print("[skip] icons: assets/brand/logo-mark.png fehlt"); return
    im = Image.open(src).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im); im = bg.convert("RGB")
    for s in (32, 180):
        out = J("assets", "brand", f"favicon-{s}.png"); im.resize((s, s), Image.LANCZOS).save(out, optimize=True)
        print(f"[ok] {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    collections(); hero(); textures(); icons()
