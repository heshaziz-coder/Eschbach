"""
Hero cinemagraph v2 (2026-11-11). Replaces tools/hero_video.py, whose synthetic wind the user rejected as unnatural.

  python tools/hero_cinemagraph.py still     # still with gently rippled water + model input frames + masks
  python tools/kie_generate.py --jobs tools/kie_hero2.json --only tree_kling2,pool_kling --out .tmp/hero2
  python tools/hero_cinemagraph.py build --tree .tmp/hero2/tree_kling.mp4 --full .tmp/hero2/pool_kling.mp4 --pool
         -> assets/hero.mp4 (1920x1080) + assets/hero_m.mp4 (864x1536, phone)
  python tools/hero_cinemagraph.py build --encode-only    # re-encode the lossless masters only

Pipeline and why (measured 2026-11-11):
  1. Still: kie (nano-banana-pro) edit of the published hero still "pool water gently rippled by a breeze". The model
     redraws the whole picture (lava texture, leaves...), so ONLY the water is taken over (colour mask), rest = original.
  2. Video models render internally at ~720p. In the full 16:9 frame an olive leaf is only 2-3 px there, so Veo 3.1
     re-invents the leaves in every frame (crown "boils", ratio 2nd/1st temporal difference 1.6-1.8). Fix: animate
     the crown from a TIGHT 9:16 crop around the tree (leaves ~2x larger) with the same still as first + last frame.
     Kling 3.0 Omni (kling-3.0-omni/image-to-video, 1080p, 8 s, 162 credits) keeps every leaf and moves it gently,
     camera locked (< 0.2 px drift). Veo 3.1 quality on the same crop still redrew the crown -> rejected.
  3. Water: Veo full frame produced circular "drop" ripples -> rejected. Kling on a 16:9 pool crop: natural wind
     ripples drifting steadily, no rings.
  4. Composite: still everywhere; water from the pool video (colour mask + hand polygon for the narrow channel);
     crown + trunk from the tree video (crown mask dilated so swaying leaves stay inside, never over the planter rim);
     planter therefore always the original photo. Per-frame exposure match of the tree clip on the sky/wall ring.
  5. Loop: tail cross-faded into the head (0.75 s); the last loop frame equals comp[F-1] so the wrap is a normal step.
  6. Encode: see encode() - bits are spent on the crown only (x264 addroi), otherwise the subtle leaf motion goes stale
     and the loop point pops.
  The phone version is composited separately at the native resolution of the still (864x1536) instead of being cut
  from the 1920 frame (608x1080 would be upscaled ~2x on a phone).
"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = lambda *p: os.path.join(ROOT, *p)
T2 = J(".tmp", "hero2")
TRIM = 10                                      # px trimmed per side of the 2752 still to get exact 16:9 (2732x1536)
SW, SH = 2732, 1536                            # still frame (= model input) size
TREE_BOX = (1550, 16, 2310, 1368)              # 9:16 tree crop in the still frame (760x1352) -> tree video
POOL_BOX = (1180, 560, 2732, 1433)             # 16:9 pool crop in the still frame (1552x873) -> water video
K = 1920 / SW                                  # still frame -> 1920 frame
# views: (name, x0, y0 in still-frame px, scale, width, height of the output)
VIEWS = [("hero.mp4", 0, 0, K, 1920, 1080),
         ("hero_m.mp4", 1498, 0, 1.0, 864, 1536)]   # phone: 9:16 around tree + planter (x=1357 of 1920 -> 1931 of 2732)
ROI = (1080, 0, 560, 700)                      # crown in the 1920 frame (see encode)
CRF = {"hero.mp4": (22, 0), "hero_m.mp4": (26, 0)}   # crf, x264 quantiser offset on the crown (0 = no ROI) -> ~2.1 / 1.6 MB


def obj_mask(im, box):
    from rembg import new_session, remove
    m = np.asarray(remove(im.crop(box), session=new_session("isnet-general-use"), only_mask=True)) > 127
    full = np.zeros((im.height, im.width), bool); full[box[1]:box[3], box[0]:box[2]] = m
    return full


def still():
    orig = Image.open(J(".tmp", "hero", "hero_wide_final.png")).convert("RGB")
    new = Image.open(J(T2, "water_still.png")).convert("RGB").resize(orig.size, Image.LANCZOS)
    W, H = orig.size
    teal = lambda a: (a[..., 2] > a[..., 0] * 1.06) & (a[..., 1] > a[..., 0] * 1.02) & (a[..., 2] < 235)
    a, b = np.asarray(orig).astype(np.float32), np.asarray(new).astype(np.float32)
    pool = teal(a) | teal(b); pool[:int(.52 * H), :] = False; pool[int(.76 * H):, :] = False
    img = lambda x: Image.fromarray((x * 255).astype(np.uint8))
    pool = np.asarray(img(pool).filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(31)).filter(ImageFilter.MinFilter(25))) > 127
    obj = obj_mask(orig, (int(W * .55), int(H * .02), int(W * .86), int(H * .93)))     # tree + planter stay original
    pool &= ~np.asarray(img(obj).filter(ImageFilter.MaxFilter(3))).astype(bool)
    m = img(pool).filter(ImageFilter.GaussianBlur(2.5)); m.save(J(T2, "water_mask.png"))
    nb = b.copy()
    for c in range(3):                         # tone of the new water -> old water (kie brightens slightly)
        nb[..., c] = (b[..., c] - b[..., c][pool].mean()) + a[..., c][pool].mean()
    al = np.asarray(m).astype(np.float32)[..., None] / 255
    s = Image.fromarray((a * (1 - al) + nb * al).clip(0, 255).astype(np.uint8)); s.save(J(T2, "still_wide.png"))
    frame = s.crop((TRIM, 0, W - TRIM, H)); frame.save(J(T2, "still_frame.png"))
    s19 = frame.resize((1920, 1080), Image.LANCZOS); s19.save(J(T2, "still_1920.png"))
    Image.fromarray(obj_mask(s19, (1000, 40, 1720, 1000)).astype(np.uint8) * 255).save(J(T2, "obj_1920.png"))
    frame.crop(TREE_BOX).resize((1080, 1920), Image.LANCZOS).save(J(T2, "tree_first.png"))
    frame.crop(POOL_BOX).resize((1920, 1080), Image.LANCZOS).save(J(T2, "pool_first.png"))
    print(f"[ok] still_wide.png {s.size}, Wasseranteil {pool.mean():.1%}; still_frame/1920, tree_first, pool_first, obj_1920")


# ---------------------------------------------------------------------------------------------- build
def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                          "stream=width,height,r_frame_rate,nb_read_frames", "-of", "json", path], capture_output=True, text=True).stdout
    st = json.loads(out)["streams"][0]; n, d = st["r_frame_rate"].split("/")
    return int(st["width"]), int(st["height"]), int(n) / int(d), int(st["nb_read_frames"])


def frames(path, fps=None):
    """Decode a video frame by frame as RGB uint8 arrays (streaming)."""
    w, h, r, n = probe(path)
    vf = ["-vf", f"fps={fps}"] if fps and abs(fps - r) > .01 else []
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, *vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    size = w * h * 3
    while True:
        b = p.stdout.read(size)
        if len(b) < size:
            break
        yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
    p.wait()


GROW = 25                                      # crown mask margin in px (1920 frame); build --grow


def masks():
    """Tree mask (crown dilated so swaying leaves stay inside, trunk tight) + water mask, 1920x1080 float 0..1."""
    CW, CH = 1920, 1080
    img = lambda x: Image.fromarray((np.clip(x, 0, 1) * 255).astype(np.uint8))
    obj = np.asarray(Image.open(J(T2, "obj_1920.png"))) > 127
    rim = 668                                                         # planter rim line in the 1920 frame
    tree = obj.copy(); tree[rim - 2:, :] = False
    crown = tree.copy(); crown[470:, :] = False                       # crown (branch split at ~y 470)
    trunk = tree & ~crown
    big = np.asarray(img(crown).filter(ImageFilter.MaxFilter(2 * GROW + 1)).filter(ImageFilter.GaussianBlur(8))) / 255
    small = np.asarray(img(trunk).filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(2))) / 255
    yy = np.arange(CH)[:, None]; xx = np.arange(CW)[None, :]
    tm = np.maximum(big, small) * np.clip((rim - 4 - yy) / 6, 0, 1)  # never over the planter rim
    x0, y0, x1, y1 = [v * K for v in TREE_BOX]                         # stay inside the tree crop
    tm = tm * np.clip((xx - x0 - 3) / 8, 0, 1) * np.clip((x1 - 3 - xx) / 8, 0, 1) * np.clip((yy - y0 - 3) / 8, 0, 1)
    wm = np.asarray(Image.open(J(T2, "water_mask.png")).crop((TRIM, 0, 2752 - TRIM, 1536)).resize((CW, CH), Image.LANCZOS)) / 255
    # narrow channel left of the planter: curtain reflections are not "teal", so the colour mask misses most of it
    ch = Image.new("L", (CW, CH), 0); ImageDraw.Draw(ch).polygon([(908, 760), (1192, 688), (1194, 768), (908, 765)], fill=255)
    ch = np.asarray(ch.filter(ImageFilter.GaussianBlur(1.5))) / 255 * (1 - np.asarray(img(obj).filter(ImageFilter.MaxFilter(5))) / 255)
    wm = np.maximum(wm, ch)
    img(tm).save(J(T2, "mask_tree.png")); img(wm).save(J(T2, "mask_water.png"))
    return tm.astype(np.float32), np.clip(wm, 0, 1).astype(np.float32)


def view_of(arr, v):
    """A 1920-frame float map (mask) -> the given view (resample + crop)."""
    _, vx, vy, s, w, h = v
    if s == K and vx == 0 and vy == 0:
        return arr
    k = s / K                                                          # 1920 frame -> view scale
    big = Image.fromarray(arr.astype(np.float32), "F").resize((round(1920 * k), round(1080 * k)), Image.BILINEAR)
    x0, y0 = round(vx * s), round(vy * s)
    return np.asarray(big.crop((x0, y0, x0 + w, y0 + h)), np.float32)


def place(fr, box, v):
    """Crop-video frame -> (rect, pixels) in the view canvas (sub-pixel exact, clipped to the canvas)."""
    _, vx, vy, s, w, h = v
    X0, Y0, X1, Y1 = (box[0] - vx) * s, (box[1] - vy) * s, (box[2] - vx) * s, (box[3] - vy) * s
    xi0, yi0 = max(0, int(np.ceil(X0))), max(0, int(np.ceil(Y0)))
    xi1, yi1 = min(w, int(np.floor(X1))), min(h, int(np.floor(Y1)))
    fh, fw = fr.shape[:2]; sx, sy = fw / (X1 - X0), fh / (Y1 - Y0)
    src = ((xi0 - X0) * sx, (yi0 - Y0) * sy, (xi1 - X0) * sx, (yi1 - Y0) * sy)
    im = Image.fromarray(fr).resize((xi1 - xi0, yi1 - yi0), Image.LANCZOS, box=src)
    return (xi0, yi0, xi1, yi1), np.asarray(im).astype(np.float32)


def stabilize(tf, rad):
    """Flow-compensated temporal smoothing (DIS optical flow): each frame = weighted mean of its neighbours warped onto
    it. Option for clips whose leaves re-draw slightly per frame; not needed for the Kling clips."""
    import cv2
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    gray = [cv2.cvtColor(f, cv2.COLOR_RGB2GRAY) for f in tf]
    h, w = gray[0].shape; gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    out = []
    for i in range(len(tf)):
        acc = tf[i].astype(np.float32); wsum = np.ones(tf[i].shape[:2] + (1,), np.float32)
        for d in range(-rad, rad + 1):
            j = (i + d) % len(tf)
            if d == 0:
                continue
            fl = dis.calc(gray[i], gray[j], None)
            wj = cv2.remap(tf[j], gx + fl[..., 0], gy + fl[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
            wgt = (1.0 / (1 + abs(d))) * np.exp(-np.abs(wj - tf[i]).mean(2, keepdims=True) / 18)
            acc += wj * wgt; wsum += wgt
        out.append((acc / wsum).clip(0, 255).astype(np.uint8))
    print(f"[ok] Baum-Video geglaettet (Radius {rad})")
    return out


def report(loop, tm, label=""):
    """Flicker metric on the crown: mean |2nd temporal difference| vs mean |1st difference| (re-drawn leaves ~1.7+)."""
    sel = tm > .5
    g = [fr.astype(np.float32).mean(2)[sel] for fr in loop]
    d1 = np.mean([np.abs(g[i + 1] - g[i]).mean() for i in range(len(g) - 1)])
    d2 = np.mean([np.abs(g[i - 1] + g[i + 1] - 2 * g[i]).mean() for i in range(1, len(g) - 1)])
    print(f"[flimmern{label}] Krone: Bewegung/Bild {d1:.2f}, Zittern {d2:.2f}, Verhaeltnis {d2 / max(1e-6, d1):.2f}, "
          f"Loop-Sprung {np.abs(g[0] - g[-1]).mean():.2f}")


def master(name):
    return J(T2, "master_" + name.replace(".mp4", ".mkv"))


def encode(out_dir, crf=None, params="ipratio=1.0:pbratio=1.0"):
    # Encoder notes (2026-11-11, decoded loop vs lossless master, test scripts in .tmp/hero2/enc_*.py): the leaves move so
    # little per frame that x264 skips most of the change -> the decoded crown lags behind ("stale") and catches up at
    # the next I-frame = the loop point pops (crf 18 default: wrap step 2.2 vs 0.2 normal, half of the leaf motion lost).
    # No B-frames / keyint / deadzone did not help. Spending bits on the crown only does: addroi qoffset -0.32 at crf 22
    # -> wrap 1.1, 80 % of the motion kept, 3.4 MB (whole frame at crf 16 is bigger and worse).
    # Phone (864x1536, crown = 60 % of the frame): crf 27 / -0.25 -> 1.9 MB, wrap 2.0 (crf 24 / -0.32 would be 4.5 MB).
    # Update 2026-11-11 (stronger breeze, tree_kling2): with real sway the ROI makes the files 3-6 MB. Instead the file
    # starts shortly after the gust begins (build --start): the I-frame pop at the wrap is hidden by the motion.
    rx, ry, rw, rh = ROI
    for v in VIEWS:
        name, vx, vy, s, w, h = v
        k = s / K; x0, y0 = vx * s, vy * s; c, rq = CRF[name]
        roi = f"addroi=x={round(rx * k - x0)}:y={round(ry * k - y0)}:w={round(rw * k)}:h={round(rh * k)}:qoffset={rq}" if rq else "null"
        dst = os.path.join(out_dir, name)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", master(name), "-vf", roi, "-c:v", "libx264", "-preset", "slow",
                        "-crf", str(crf or c), "-x264-params", params, "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", dst], check=True)
        print(f"[ok] {os.path.relpath(dst, ROOT)}  {w}x{h}  {os.path.getsize(dst) // 1024} KB")


def build():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("cmd")
    ap.add_argument("--tree", default=J(T2, "tree_kling2.mp4")); ap.add_argument("--full", default=J(T2, "pool_kling.mp4"))
    ap.add_argument("--pool", action="store_true", help="--full is the pool-crop video (POOL_BOX), not the whole frame")
    ap.add_argument("--fade", type=float, default=.75); ap.add_argument("--fps", type=float, default=24)
    ap.add_argument("--crf", type=int, default=0, help="override the per-view CRF")
    ap.add_argument("--stab", type=int, default=0, help="flow-compensated smoothing radius on the tree clip (0 = off)")
    ap.add_argument("--out", default=J("assets")); ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--encode-only", action="store_true", help="only re-encode the lossless masters")
    ap.add_argument("--start", type=int, default=12, help="rotate the loop: the file starts at this loop frame (hide the wrap in motion)")
    ap.add_argument("--grow", type=int, default=45, help="crown mask margin (px, 1920 frame): >= max leaf sway")
    a = ap.parse_args()
    if a.encode_only:
        return encode(a.out, a.crf)
    globals()["GROW"] = a.grow
    full_still = np.asarray(Image.open(J(T2, "still_frame.png")).convert("RGB"))
    tm19, wm19 = masks()
    tf = list(frames(a.tree, a.fps)); fv = list(frames(a.full, a.fps))
    if a.stab:
        tf = stabilize(tf, a.stab)
    if len(tf) != len(fv):   # both clips run keyframe -> keyframe: stretch the tree clip onto the water clip
        src = [k * (len(tf) - 1) / (len(fv) - 1) for k in range(len(fv))]
        tf = [tf[int(t)] if t == int(t) else ((1 - (t - int(t))) * tf[int(t)].astype(np.float32) + (t - int(t)) * tf[int(t) + 1]).astype(np.uint8)
              for t in src]
        print(f"[info] Baum-Video auf {len(fv)} Bilder angepasst")
    n = min(len(tf), len(fv)); F = int(round(a.fade * a.fps)); T = n - 1   # last frame == first keyframe -> dropped
    for v in VIEWS:
        name, vx, vy, s, w, h = v
        st = Image.fromarray(full_still)
        if s != 1.0:
            st = st.resize((round(SW * s), round(SH * s)), Image.LANCZOS)
        x0, y0 = round(vx * s), round(vy * s)
        still = np.asarray(st.crop((x0, y0, x0 + w, y0 + h))).astype(np.float32)
        tm, wm = view_of(tm19, v), view_of(wm19, v); tw, ww = tm[..., None], wm[..., None]
        ring = (tm > .02) & (tm < .9)                                  # sky / wall around the crown: exposure reference
        comp, woff = [], None
        for i in range(n):
            if a.pool:
                (px0, py0, px1, py1), pp = place(fv[i], POOL_BOX, v)
                f = still.copy(); f[py0:py1, px0:px1] = pp
            else:
                (px0, py0, px1, py1), pp = place(fv[i], (0, 0, SW, SH), v)
                f = still.copy(); f[py0:py1, px0:px1] = pp
            if woff is None:
                sel = wm > .9; woff = still[sel].mean(0) - f[sel].mean(0)   # tone of the video water -> still
            out = still * (1 - ww) + np.clip(f + woff, 0, 255) * ww
            (tx0, ty0, tx1, ty1), tp = place(tf[i], TREE_BOX, v)
            r = ring[ty0:ty1, tx0:tx1]; off = still[ty0:ty1, tx0:tx1][r].mean(0) - tp[r].mean(0)   # exposure drift
            mk = tw[ty0:ty1, tx0:tx1]
            out[ty0:ty1, tx0:tx1] = out[ty0:ty1, tx0:tx1] * (1 - mk) + np.clip(tp + off, 0, 255) * mk
            comp.append(out.clip(0, 255).astype(np.uint8))
        # tail cross-fades into the head; the last loop frame is exactly comp[F-1], so the wrap to comp[F] is a normal step
        loop = comp[F:T - F] + [((1 - (j + 1) / F) * comp[T - F + j].astype(np.float32) + (j + 1) / F * comp[j]).round().astype(np.uint8)
                                for j in range(F)] if F else comp[:T]
        loop = loop[a.start:] + loop[:a.start]
        print(f"[info] {name}: {w}x{h}, Loop {len(loop)} Bilder = {len(loop) / a.fps:.2f} s (Ueberblendung {F})")
        report(loop, tm, " " + name)
        if not a.no_write:
            p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", f"{a.fps:g}",
                                  "-i", "-", "-c:v", "ffv1", "-pix_fmt", "bgr0", master(name)], stdin=subprocess.PIPE)
            for fr in loop:
                p.stdin.write(fr.tobytes())
            p.stdin.close(); p.wait()
        del comp, loop
    if not a.no_write:
        encode(a.out, a.crf)


if __name__ == "__main__":
    {"still": still, "build": build}[sys.argv[1]]()
