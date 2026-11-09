"""
Place a cut-out planter photo into a scenery photo and match it to the scene's light.

  python tools/scene_composite.py --pot path/to/pot.png --scene terrasse [--out .tmp/comp] [--layers]

Config per scene: tools/scene_light.json
  contact_y     floor contact of the pot, fraction of image height (pot is always centred horizontally)
  pot_h         pot height as fraction of image height
  tint          0..1  how strongly the pot takes on the scene's average light colour
  exposure      brightness multiplier of the pot
  side          -1..1 directional shading across the pot (+ = light from the right)
  rim           strength of a backlight rim on the pot edges (for scenes lit from behind)
  rim_color     rgb 0..255
  shadow        {"sx": horizontal offset per unit height (+ = to the right),
                 "sy": vertical extent per unit height (+ = towards camera, - = away),
                 "opacity": 0..1, "blur_near": px, "blur_far": px, "color": rgb tint of the shadow}
  contact       opacity of the soft ambient-occlusion ellipse under the pot
  reflection    0..1 opacity of a mirrored pot on glossy floors (0 = none)

Output: <out>/<scene>__<potname>.jpg (preview composite). With --layers also writes
<out>/<scene>__<potname>__pot.png (graded pot, full frame RGBA) and __shadow.png (L, multiply mask),
so the website can swap only the scenery while the pot stays at the same pixel position.
The pot photo must be a cut-out with transparent background (PNG/WebP with alpha).
"""
import argparse, json, os, sys
from PIL import Image, ImageChops, ImageFilter, ImageOps, ImageStat

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_pot(path, alpha_floor=0):
    im = Image.open(path).convert("RGBA")
    if alpha_floor:
        a = im.getchannel("A").point(lambda v: 0 if v < alpha_floor else v)
        im.putalpha(a)
    bb = im.getchannel("A").getbbox()
    return im.crop(bb)


def grade(pot, scene, cfg, box):
    """Tint/expose the pot with the scene light and add directional shading + rim."""
    r, g, b, a = pot.split()
    ref = scene.crop(box).resize((64, 64))
    mean = ImageStat.Stat(ref).mean[:3]
    m = max(mean)
    t = cfg.get("tint", .5)
    gains = [cfg.get("exposure", 1) * ((1 - t) + t * c / m) for c in mean]
    rgb = [ch.point(lambda v, k=k: min(255, int(v * k))) for ch, k in zip((r, g, b), gains)]
    W, H = pot.size
    side = cfg.get("side", 0)
    if side:
        grad = Image.linear_gradient("L").rotate(90 if side < 0 else -90, expand=True).resize((W, H))
        # factor 1-|side|/2 .. 1+|side|/2 across the pot
        lo, hi = 1 - abs(side) / 2, 1 + abs(side) / 2
        rgb = [ImageChops.multiply(ch, grad.point(lambda v: int(255 * (lo + (hi - lo) * v / 255) / hi))).point(lambda v: min(255, int(v * hi)))
               for ch in rgb]
    rim = cfg.get("rim", 0)
    if rim:
        edge = ImageChops.subtract(a, a.filter(ImageFilter.MinFilter(9))).filter(ImageFilter.GaussianBlur(4))
        top = Image.linear_gradient("L").resize((W, H)).point(lambda v: 255 - v)   # stronger at the top
        edge = ImageChops.multiply(edge, top)
        rc = cfg.get("rim_color", (255, 220, 180))
        rgb = [ImageChops.add(ch, edge.point(lambda v, c=c: int(v * rim * c / 255))) for ch, c in zip(rgb, rc)]
    return Image.merge("RGBA", (*rgb, a))


def cast_shadow(alpha_full, base_y, s, size):
    """Project the pot silhouette onto the floor plane (affine), blur more with distance."""
    sx, sy = s.get("sx", .3), s.get("sy", .25)
    # output (x,y) -> source: h=(y-base)/sy ; xs = x - sx*h ; ys = base - h
    coeffs = (1, -sx / sy, sx / sy * base_y, 0, -1 / sy, base_y + base_y / sy)
    sh = alpha_full.transform(size, Image.AFFINE, coeffs, resample=Image.BILINEAR)
    # shadow only on the floor side of the contact line
    W, H = size
    keep = Image.new("L", size, 0)
    if sy > 0:
        keep.paste(255, (0, int(base_y) - 2, W, H))
    else:
        keep.paste(255, (0, 0, W, int(base_y) + 2))
    sh = ImageChops.multiply(sh, keep)
    near = sh.filter(ImageFilter.GaussianBlur(s.get("blur_near", 4)))
    far = sh.filter(ImageFilter.GaussianBlur(s.get("blur_far", 30)))
    # distance ramp from the contact line
    span = max(1, abs(sy) * H * .4)
    col = [min(255, int(255 * abs(y - base_y) / span)) for y in range(H)]
    ramp = Image.new("L", (1, H)); ramp.putdata(col); ramp = ramp.resize(size)
    mix = Image.composite(far, near, ramp)
    # fade out with distance as well
    fade = ramp.point(lambda v: 255 - int(v * .55))
    return ImageChops.multiply(mix, fade).point(lambda v: int(v * s.get("opacity", .6)))


def compose(pot_path, scene_id, out, layers=False, alpha_floor=0):
    cfgs = json.load(open(os.path.join(ROOT, "tools", "scene_light.json"), encoding="utf-8"))
    cfg = cfgs[scene_id]
    scene = Image.open(cfg["image"] if os.path.isabs(cfg["image"]) else os.path.join(ROOT, cfg["image"])).convert("RGB")
    W, H = scene.size
    pot = load_pot(pot_path, alpha_floor)
    ph = int(H * cfg["pot_h"]); pw = int(pot.width * ph / pot.height)
    pot = pot.resize((pw, ph), Image.LANCZOS)
    base_y = int(H * cfg["contact_y"]); x0 = W // 2 - pw // 2; y0 = base_y - ph
    box = (max(0, W // 2 - pw), max(0, y0), min(W, W // 2 + pw), min(H, base_y + ph // 3))
    pot = grade(pot, scene, cfg, box)

    alpha_full = Image.new("L", (W, H), 0); alpha_full.paste(pot.getchannel("A"), (x0, y0))
    shadow = cast_shadow(alpha_full, base_y, cfg["shadow"], (W, H))
    # contact / ambient occlusion
    c = cfg.get("contact", .7)
    if c:
        bot = pot.getchannel("A").crop((0, int(ph * .85), pw, ph)).getbbox()
        bw = (bot[2] - bot[0]) if bot else pw * .6
        cx = x0 + ((bot[0] + bot[2]) / 2 if bot else pw / 2)
        ao = Image.new("L", (W, H), 0)
        from PIL import ImageDraw
        ImageDraw.Draw(ao).ellipse((cx - bw * .62, base_y - bw * .07, cx + bw * .62, base_y + bw * .09), fill=int(255 * c))
        ao = ao.filter(ImageFilter.GaussianBlur(bw * .07))
        shadow = ImageChops.lighter(shadow, ao)

    sc = cfg["shadow"].get("color", (40, 34, 30))
    # multiply: scene * (1 - mask*(1 - shadowcolor))
    inv = [shadow.point(lambda v, k=k: 255 - int(v * (1 - k / 255))) for k in sc]
    shaded = ImageChops.multiply(scene, Image.merge("RGB", inv))

    comp = shaded.copy()
    refl = cfg.get("reflection", 0)
    if refl:
        m = ImageOps.flip(pot)
        fade = Image.linear_gradient("L").resize((pw, ph)).point(lambda v: max(0, 255 - int(v * 2.2)))
        ma = ImageChops.multiply(m.getchannel("A"), fade).point(lambda v: int(v * refl))
        m.putalpha(ma); m = m.filter(ImageFilter.GaussianBlur(3))
        comp.paste(m, (x0, base_y - 2), m)
    comp.paste(pot, (x0, y0), pot)

    os.makedirs(out, exist_ok=True)
    name = os.path.splitext(os.path.basename(pot_path))[0]
    dst = os.path.join(out, f"{scene_id}__{name}.jpg")
    comp.save(dst, quality=90)
    print("[ok]", dst)
    if layers:
        full = Image.new("RGBA", (W, H), (0, 0, 0, 0)); full.paste(pot, (x0, y0), pot)
        full.save(os.path.join(out, f"{scene_id}__{name}__pot.png"))
        shadow.save(os.path.join(out, f"{scene_id}__{name}__shadow.png"))
    return dst


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pot", required=True)
    ap.add_argument("--scene", required=True, help="scene id or 'all'")
    ap.add_argument("--out", default=os.path.join(ROOT, ".tmp", "comp"))
    ap.add_argument("--layers", action="store_true")
    ap.add_argument("--alpha-floor", type=int, default=0, help="drop alpha below this (strip baked soft shadows)")
    A = ap.parse_args()
    ids = list(json.load(open(os.path.join(ROOT, "tools", "scene_light.json"), encoding="utf-8"))) if A.scene == "all" else A.scene.split(",")
    for sid in ids:
        compose(A.pot, sid, A.out, A.layers, A.alpha_floor)
