"""
Hero video for the website from the kie.ai loop (Veo 3.1 quality, tools/kie_hero.json: static camera, same still as
first + last frame).

  python tools/hero_video.py [--src .tmp/hero/hero_loop.mp4] [--check] [--fade 1.0] [--crf 23]

  assets/hero.mp4     landscape 16:9 for desktop / tablet (H.264, no audio, faststart)
  assets/hero_m.mp4   portrait 9:16 crop of the SAME video around the planter, for phones
  --check             only measures: loop seam (first vs last frame) and how much the planter changes

What the tool fixes (learned on the first run, 2026-11-10):
  1. Product fidelity: Veo redraws the lava surface (coarser, "boiling" from frame to frame). Camera and planter do
     not move, so the ORIGINAL planter from the still (.tmp/hero/hero_frame.png) is laid over every frame:
     rembg silhouette below the rim line, eroded + feathered, tone-matched half-way to the video.
  2. Loop: first and last frame are close but not identical -> the last --fade seconds are cross-faded into the
     first ones (leaves / water only, so the blend is invisible). Loop length = source length - fade.
  3. Shimmer: static surfaces (floor slabs, hedge, curtains) "boil" slightly from frame to frame, typical for AI
     video. Everything outside the motion mask (olive crown + trunk, pool water) is frozen to ONE video frame
     (the loop start), so only leaves and water move (cinemagraph). Also makes the files much smaller.
  4. Leaf "boiling": Veo redraws the fine olive leaves differently in every frame -> the crown flickers. Averaging
     frames (tmix) only turned that into ghosting. So the crown is frozen too and the wind is SYNTHESISED: the frozen
     crown is warped with a smooth displacement field (amplitude grows towards the branch tips, low-frequency phase
     noise so parts move slightly out of step, 2 sway cycles per loop -> exactly periodic, seamless). Only the pool
     water stays Veo footage. --sway sets the tip amplitude in px (1920 frame). crf 20: fine leaves need bits.
Phone crop centre = horizontal centre of olive tree + planter (rembg on the loop start frame, measured
x 1123-1591 of 1920). A phone (390x844, object-fit:cover) shows ~500 of the 608 px crop width, so the crown
(468 px) only fits completely when the crop is centred on it; the centre of the old portrait photo cut the right edge.
"""
import argparse, json, os, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = lambda *p: os.path.join(ROOT, *p)
ap = argparse.ArgumentParser()
ap.add_argument("--src", default=J(".tmp", "hero", "hero_loop.mp4"))
ap.add_argument("--check", action="store_true")
ap.add_argument("--fade", type=float, default=1.0)
ap.add_argument("--crf", type=int, default=20)
ap.add_argument("--smooth", type=int, default=1, help="tmix frames on the Veo footage (1 = off; >1 ghosts)")
ap.add_argument("--sway", type=float, default=3.5, help="synthetic wind: max leaf displacement in px")
ap.add_argument("--cycles", type=int, default=2, help="sway cycles per loop")
A = ap.parse_args()
STILL, OVERLAY = J(".tmp", "hero", "hero_frame.png"), J(".tmp", "hero", "pot_overlay.png")
POT_BOX = (1120, 610, 1580, 990)     # search box for the planter in the 1920x1080 frame (below the foliage)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                          "stream=width,height,r_frame_rate,nb_read_frames", "-of", "json", path], capture_output=True, text=True).stdout
    s = json.loads(out)["streams"][0]; n, d = s["r_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), int(n) / int(d), int(s["nb_read_frames"])


def sample_frames(fps=4):
    import numpy as np
    from PIL import Image
    tmp = J(".tmp", "hero", "frames"); os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", A.src, "-vf", f"fps={fps}", os.path.join(tmp, "f_%03d.png")], check=True)
    return [np.asarray(Image.open(os.path.join(tmp, f)).convert("RGB")).astype(np.float32) for f in sorted(os.listdir(tmp))]


def pot_overlay(W, H):
    """Original planter from the still as a full-frame RGBA layer."""
    import numpy as np
    from PIL import Image, ImageFilter
    from rembg import new_session, remove
    still = Image.open(STILL).convert("RGB").resize((W, H), Image.LANCZOS)
    m = np.asarray(remove(still.crop(POT_BOX), session=new_session("isnet-general-use"), only_mask=True)) > 127
    wd = m.sum(1); top = int(np.argmax(wd >= .9 * wd.max())); m[:top, :] = False      # start at the rim line: trunk / soil stay video
    full = np.zeros((H, W), np.uint8); full[POT_BOX[1]:POT_BOX[3], POT_BOX[0]:POT_BOX[2]] = m * 255
    mask = Image.fromarray(full).filter(ImageFilter.MinFilter(7)).filter(ImageFilter.GaussianBlur(2.5))
    vid = np.mean(sample_frames()[2::6], axis=0); st = np.asarray(still).astype(np.float32); mk = np.asarray(mask) > 200
    out = st.copy()
    for c in range(3):
        a, b = st[..., c][mk], vid[..., c][mk]
        gain = 1 + (min(1.25, max(.8, b.std() / a.std())) - 1) * .5
        out[..., c] = (st[..., c] - a.mean()) * gain + b.mean()
    pot = Image.fromarray(out.clip(0, 255).astype(np.uint8)); pot.putalpha(mask)
    print(f"[ok] Original-Topf als Ebene: Rand ab y={top + POT_BOX[1]}, Breite {int(wd.max())} px")
    return pot, top + POT_BOX[1]


def static_layer(W, H, F):
    """One frozen video frame everywhere except tree + pool, with the original planter on top -> assets overlay PNG."""
    import numpy as np
    from PIL import Image, ImageFilter
    from rembg import new_session, remove
    pot, rim = pot_overlay(W, H)
    plate_p = J(".tmp", "hero", "plate.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", A.src, "-vf", f"select=eq(n\,{F})", "-frames:v", "1", plate_p], check=True)
    plate = Image.open(plate_p).convert("RGB"); a = np.asarray(plate).astype(np.float32)
    box = (1000, 60, 1700, 700)                                                       # olive tree: salient object above the rim
    m = np.asarray(remove(plate.crop(box), session=new_session("isnet-general-use"), only_mask=True)) > 127
    tree = np.zeros((H, W), bool); tree[box[1]:box[3], box[0]:box[2]] = m; tree[rim + 3:, :] = False
    ys = np.where(tree.any(1))[0]; crown_top = int(ys.min()) if len(ys) else box[1]
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    pool = (b > r * 1.06) & (g > r * 1.02) & (b < 235); pool[:560, :] = False; pool[830:, :] = False   # teal water
    strip = (g > r) & (b > r * .93) & ((r + g + b) < 520); keep = np.zeros((H, W), bool); keep[690:775, 860:1200] = True; strip &= keep
    img = lambda x: Image.fromarray((x * 255).astype(np.uint8))
    region = img(tree).filter(ImageFilter.MaxFilter(41)).filter(ImageFilter.GaussianBlur(9))   # crown + a margin of sky
    parts = [img(pool).filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(17)),
             img(strip).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(13))]
    motion = Image.fromarray(np.maximum.reduce([np.asarray(x) for x in parts])).filter(ImageFilter.GaussianBlur(9))
    motion.save(J(".tmp", "hero", "motion_mask.png"))
    layer = plate.convert("RGBA"); layer.putalpha(Image.fromarray(255 - np.asarray(motion)))
    layer.alpha_composite(pot); layer.save(OVERLAY)
    print(f"[ok] Standbild-Ebene: {float((np.asarray(motion) > 127).mean()):.0%} des Bildes bleiben Video (Poolwasser)")
    return plate, np.asarray(region).astype(np.float32) / 255, crown_top, rim


def crown_frames(plate, region, top, rim, L):
    """Synthetic, exactly periodic wind on the frozen crown -> RGBA PNG sequence (cropped) + its position."""
    import numpy as np
    from PIL import Image
    from scipy.ndimage import gaussian_filter, map_coordinates
    ys, xs = np.where(region > .02); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    src = np.asarray(plate).astype(np.float32)[y0:y1, x0:x1]; w = region[y0:y1, x0:x1]; h_, w_ = w.shape
    yy, xx = np.mgrid[0:h_, 0:w_].astype(np.float32)
    lift = np.clip((rim - (yy + y0)) / max(1, rim - top), 0, 1) ** 1.6                 # 0 at the rim (trunk) -> 1 at the crown top
    edge = np.clip(gaussian_filter(w, 12) * 1.6, 0, 1)                                # displacement fades out towards the margin
    amp = A.sway * lift * edge
    rng = np.random.default_rng(11)
    ph = lambda s: gaussian_filter(rng.standard_normal((h_, w_)), s) * (2 * np.pi / max(1e-6, gaussian_filter(rng.standard_normal((h_, w_)), s).std()))
    p1, p2, p3 = ph(70) * .35, ph(45) * .6, ph(70) * .5                                # mostly coherent sway, parts slightly out of step
    out = J(".tmp", "hero", "crown"); os.makedirs(out, exist_ok=True)
    alpha = (w * 255).astype(np.uint8)
    for k in range(L):
        t = 2 * np.pi * A.cycles * k / L
        dx = amp * (.75 * np.sin(t + p1) + .25 * np.sin(2 * t + p2)); dy = amp * .3 * np.sin(t + p3 + .8)
        fr = np.stack([map_coordinates(src[..., c], [yy - dy, xx - dx], order=1, mode="nearest") for c in range(3)], -1)
        Image.fromarray(np.dstack([fr.clip(0, 255).astype(np.uint8), alpha]), "RGBA").save(os.path.join(out, f"c_{k:04d}.png"))
    print(f"[ok] Krone: {L} Bilder synthetischer Wind, max. {A.sway:g} px, {A.cycles} Schwünge pro Schleife")
    return int(x0), int(y0)


W, H, fps, N = probe(A.src)
print(f"Quelle: {W}x{H}, {fps:.2f} fps, {N} Bilder, {N / fps:.2f} s")
g = json.load(open(J(".tmp", "hero", "geom.json")))
trim = (g["W"] - round(g["H"] * 16 / 9)) // 2                      # sides trimmed when the 2752x1536 still became 16:9
cx = 1357 * W / 1920                                               # centre of tree + planter (see docstring)
pw = int(round(H * 9 / 16 / 2) * 2); px = int(max(0, min(W - pw, round(cx - pw / 2))))

if A.check:
    import numpy as np
    fr = [f.mean(2) for f in sample_frames()]
    x0, y0, x1, y1 = POT_BOX[0] + 80, POT_BOX[1] + 90, POT_BOX[2] - 80, POT_BOX[3] - 50
    print("Schleife (erstes vs. letztes Stichbild):", round(float(np.abs(fr[0] - fr[-1]).mean()), 2))
    print("Topf-Abweichung je Stichbild :", " ".join(f"{float(np.abs(f[y0:y1, x0:x1] - fr[0][y0:y1, x0:x1]).mean()):.1f}" for f in fr))
    print("Gesamtbild-Abweichung        :", " ".join(f"{float(np.abs(f - fr[0]).mean()):.1f}" for f in fr))
    sys.exit()

T = N - 1; F = int(round(A.fade * fps))                             # frames used / frames cross-faded
plate, region, top, rim = static_layer(W, H, F)
cx0, cy0 = crown_frames(plate, region, top, rim, T - F)
sm = "" if A.smooth <= 1 else f"tmix=frames={A.smooth}:weights='{' '.join(str(min(i + 1, A.smooth - i)) for i in range(A.smooth))}',"
graph = (f"[0:v]{sm}fps={fps:g},settb=AVTB[v];[v][1:v]overlay=0:0:format=auto[o];[o]split=3[a][b][c];"
         f"[a]trim=start_frame=0:end_frame={F},setpts=PTS-STARTPTS[head];"
         f"[b]trim=start_frame={F}:end_frame={T - F},setpts=PTS-STARTPTS[body];"
         f"[c]trim=start_frame={T - F}:end_frame={T},setpts=PTS-STARTPTS[tail];"
         f"[tail][head]xfade=transition=fade:duration={F / fps:.4f}:offset=0[x];[body][x]concat=n=2:v=1:a=0[lp0];"
         f"[lp0][2:v]overlay={cx0}:{cy0}:format=auto:shortest=1[lp]")
# ipratio/pbratio = 1: I, P and B frames get the same quality -> no sharpness "pop" of the leaves at the loop point
enc = ["-an", "-c:v", "libx264", "-preset", "slow", "-crf", str(A.crf), "-x264-params", "ipratio=1.0:pbratio=1.0",
       "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
for name, tail in (("hero.mp4", "[lp]null[out]"), ("hero_m.mp4", f"[lp]crop={pw}:{H}:{px}:0[out]")):
    out = J("assets", name)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", A.src, "-i", OVERLAY, "-framerate", f"{fps:g}", "-i", J(".tmp", "hero", "crown", "c_%04d.png"), "-filter_complex", graph + ";" + tail, "-map", "[out]", *enc, out], check=True)
    w, h, r, n = probe(out)
    print(f"[ok] assets/{name}  {w}x{h}  {n} Bilder ({n / r:.2f} s)  {os.path.getsize(out) // 1024} KB")
