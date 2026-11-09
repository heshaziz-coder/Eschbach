"""
Convert a rendered PNG sequence to web-ready WebP frames (desktop + mobile).

  python tools/frames_to_webp.py --src .tmp/hero_png --prefix hero
    -> frames/hero_0001.webp ...      (1920 px wide, q80)
    -> frames/m/hero_0001.webp ...    (960 px wide, q74)

Requires ffmpeg on PATH. Renumbers from 0001 contiguously in sorted order.
"""
import argparse, glob, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--prefix", default="hero")
    ap.add_argument("--out", default=os.path.join(ROOT, "frames"))
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--mwidth", type=int, default=960)
    ap.add_argument("--q", type=int, default=80)
    ap.add_argument("--mq", type=int, default=74)
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.src, "*.png")))
    if not files:
        sys.exit(f"Keine PNGs in {a.src}")
    tmp = tempfile.mkdtemp()
    for i, f in enumerate(files, 1):          # contiguous numbering for ffmpeg's %04d input
        shutil.copy(f, os.path.join(tmp, f"f_{i:04d}.png"))
    for width, q, out in ((a.width, a.q, a.out), (a.mwidth, a.mq, os.path.join(a.out, "m"))):
        os.makedirs(out, exist_ok=True)
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(tmp, "f_%04d.png"),
               "-vf", f"scale={width}:-2:flags=lanczos", "-c:v", "libwebp", "-quality", str(q),
               "-compression_level", "6", os.path.join(out, f"{a.prefix}_%04d.webp")]
        subprocess.run(cmd, check=True)
        n = len(glob.glob(os.path.join(out, f"{a.prefix}_*.webp")))
        size = sum(os.path.getsize(p) for p in glob.glob(os.path.join(out, f"{a.prefix}_*.webp"))) / 1e6
        print(f"{out}: {n} Frames, {size:.1f} MB")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
