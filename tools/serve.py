"""
Local dev server WITHOUT browser caching (python -m http.server lets browsers keep stale js/css).

  python tools/serve.py [port]        -> http://127.0.0.1:8765/index.html
"""
import functools, http.server, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class NoCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Expires", "0")
        super().end_headers()


port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
handler = functools.partial(NoCache, directory=ROOT)
print(f"http://127.0.0.1:{port}/index.html  (no-cache)", flush=True)
http.server.ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()
