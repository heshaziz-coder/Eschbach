"""
kie.ai image generation client (Nano Banana Pro / Nano Banana / Seedream) - stdlib only.

Key:   KIE_API_KEY in Eschbach/.env  (never pass it on the command line)
Docs:  POST https://api.kie.ai/api/v1/jobs/createTask
       GET  https://api.kie.ai/api/v1/jobs/recordInfo?taskId=...
       Errors come back as HTTP 200 with body.code != 200 -> always check "code".
       Results are kept 14 days -> we download immediately.

Usage:
  python tools/kie_generate.py --jobs tools/kie_scenes.json --out assets/scenes
  python tools/kie_generate.py --jobs tools/kie_scenes.json --only terrasse --out assets/scenes
  python tools/kie_generate.py --prompt "..." --id test --out .tmp/kie

Video (Veo 3.1): {"id", "model": "veo-3-1", "ext": "mp4", "image_files": [first, last], "prompt",
       "extra": {"model": "veo3_fast", "generation_type": "FIRST_AND_LAST_FRAMES_2_VIDEO", "aspect_ratio": "16:9",
                 "resolution": "1080p", "duration": 8}}   (same file as first + last frame -> seamless loop)

Jobs file: JSON list of {"id", "prompt", "aspect_ratio"?, "resolution"?, "model"?, "image_input"? (urls), "image_files"? (local paths, auto-uploaded)}
Already-downloaded ids are skipped, so re-running never spends credits twice.
A ledger of every task (id, model, credits, url) is appended to <out>/_kie_log.jsonl.
"""
import argparse, json, os, socket, sys, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The API key is IP-whitelisted. Windows rotates IPv6 privacy addresses (often daily), so force IPv4,
# whose address is stable and whitelisted. Set KIE_ALLOW_IPV6=1 to disable.
if not os.environ.get("KIE_ALLOW_IPV6"):
    _gai = socket.getaddrinfo
    def _ipv4_only(host, *a, **k):
        res = [r for r in _gai(host, *a, **k) if r[0] == socket.AF_INET]
        return res or _gai(host, *a, **k)
    socket.getaddrinfo = _ipv4_only
API = "https://api.kie.ai/api/v1/jobs"


def load_key():
    key = os.environ.get("KIE_API_KEY")
    env = os.path.join(ROOT, ".env")
    if not key and os.path.exists(env):
        for line in open(env, encoding="utf-8-sig"):
            line = line.strip()
            if line.startswith("KIE_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        sys.exit("KIE_API_KEY fehlt: bitte in Eschbach/.env eintragen (KIE_API_KEY=...).")
    return key


def call(method, url, key, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "eschbach-pipeline/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"code": e.code, "msg": e.read().decode(errors="replace")[:400]}


UPLOAD = "https://kieai.redpandaai.co/api/file-base64-upload"


def upload(path, key):
    """Upload a local image to kie.ai file storage (temporary, ~3 days) -> public URL for image_input."""
    import base64, io, mimetypes
    mime = mimetypes.guess_type(path)[0] or "image/png"
    data = open(path, "rb").read()
    if len(data) > 1_500_000:   # kie file servers can be slow (~10 KB/s): send a q95 JPEG (~1 MB) instead of a 6-8 MB PNG
        from PIL import Image
        buf = io.BytesIO(); Image.open(path).convert("RGB").save(buf, "JPEG", quality=95, subsampling=0)
        data, mime = buf.getvalue(), "image/jpeg"
        path = os.path.splitext(path)[0] + ".jpg"
    b64 = base64.b64encode(data).decode()
    res = call("POST", UPLOAD, key, {"base64Data": f"data:{mime};base64,{b64}", "uploadPath": "eschbach",
                                     "fileName": os.path.basename(path)})
    url = (res.get("data") or {}).get("downloadUrl") or (res.get("data") or {}).get("fileUrl")
    if res.get("code") != 200 or not url:
        sys.exit(f"[FEHLER] Upload {path}: {res.get('code')} {res.get('msg')}")
    print(f"[upload] {os.path.basename(path)} -> {url}", flush=True)
    return url


def build_input(job, model):
    inp = {"prompt": job["prompt"]}
    ar = job.get("aspect_ratio", "16:9")
    if model == "nano-banana-pro":
        inp.update(aspect_ratio=ar, resolution=job.get("resolution", "2K"), output_format="png")
        if job.get("image_input"):
            inp["image_input"] = job["image_input"]
    elif model.startswith("google/nano-banana"):
        inp.update(aspect_ratio=ar, output_format="png")
        if job.get("image_input"):
            inp["image_urls"] = job["image_input"]
    elif model == "veo-3-1":  # video: tier/resolution/duration/generation_type come from job["extra"]
        inp.update(job.get("extra", {}))
        if job.get("image_input"):
            inp["image_urls"] = job["image_input"]
    else:  # pass-through for other market models (e.g. seedream, kling), caller supplies extra fields
        inp.update(job.get("extra", {}))
        if job.get("image_input"):   # kling-3.0-omni/image-to-video: image_urls = [first, last]
            inp[job.get("image_key", "image_urls")] = job["image_input"]
    return inp


def run_job(job, key, out_dir, default_model, poll_max=900):
    model = job.get("model", default_model)
    dest = os.path.join(out_dir, f"{job['id']}.{job.get('ext', 'png')}")   # "ext": "mp4" for video jobs
    if os.path.exists(dest):
        print(f"[skip] {job['id']} existiert bereits"); return dest
    if job.get("image_files"):   # local files -> upload -> image_input urls
        up = {}   # the same file may be listed twice (e.g. first + last frame of a loop): upload once
        for f in job["image_files"]:
            if f not in up:
                up[f] = upload(f if os.path.isabs(f) else os.path.join(ROOT, f), key)
        job = dict(job, image_input=(job.get("image_input") or []) + [up[f] for f in job["image_files"]])
    res = call("POST", f"{API}/createTask", key, {"model": model, "input": build_input(job, model)})
    if res.get("code") != 200:
        print(f"[FEHLER] {job['id']} createTask: {res.get('code')} {res.get('msg')}"); return None
    tid = res["data"]["taskId"]
    print(f"[task] {job['id']} -> {tid} ({model})", flush=True)
    t0, wait = time.time(), 3
    while time.time() - t0 < poll_max:
        time.sleep(wait); wait = min(wait * 1.4, 15)
        q = call("GET", f"{API}/recordInfo?taskId={tid}", key)
        if q.get("code") != 200:
            if q.get("code") == 429:
                continue
            print(f"[FEHLER] {job['id']} recordInfo: {q.get('code')} {q.get('msg')}"); return None
        d = q["data"]; st = d.get("state")
        if st == "success":
            rj = json.loads(d.get("resultJson") or "{}")
            urls = rj.get("resultUrls") or rj.get("result_urls") or (rj.get("data") or {}).get("result_urls") or []
            if not urls:
                print(f"[FEHLER] {job['id']}: keine resultUrls"); return None
            os.makedirs(out_dir, exist_ok=True)
            urllib.request.urlretrieve(urls[0], dest)
            with open(os.path.join(out_dir, "_kie_log.jsonl"), "a", encoding="utf-8") as lg:
                lg.write(json.dumps({"id": job["id"], "task": tid, "model": model, "credits": d.get("creditsConsumed"),
                                     "secs": d.get("costTime"), "url": urls[0], "file": dest}) + "\n")
            print(f"[ok] {job['id']} -> {dest} (credits: {d.get('creditsConsumed')})", flush=True)
            return dest
        if st == "fail":
            print(f"[FEHLER] {job['id']} fail: {d.get('failCode')} {d.get('failMsg')}"); return None
    print(f"[FEHLER] {job['id']}: Timeout nach {poll_max}s (Task {tid} läuft evtl. weiter)"); return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs"); ap.add_argument("--only", default="")
    ap.add_argument("--prompt"); ap.add_argument("--id", default="single")
    ap.add_argument("--out", default=os.path.join(ROOT, ".tmp", "kie"))
    ap.add_argument("--model", default="nano-banana-pro")
    ap.add_argument("--dry-run", action="store_true", help="nur anzeigen, keine Credits")
    a = ap.parse_args()
    jobs = json.load(open(a.jobs, encoding="utf-8")) if a.jobs else [{"id": a.id, "prompt": a.prompt}]
    if a.only:
        keep = set(a.only.split(",")); jobs = [j for j in jobs if j["id"] in keep]
    out = os.path.abspath(a.out)
    if a.dry_run:
        for j in jobs:
            print(j["id"], "->", os.path.join(out, j["id"] + ".png"), "|", j.get("model", a.model))
        return
    key = load_key()
    ok = [run_job(j, key, out, a.model) for j in jobs]
    print(f"\nFertig: {sum(1 for x in ok if x)}/{len(jobs)} Bilder in {out}")


if __name__ == "__main__":
    main()
