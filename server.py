"""chordlens server — stdlib http.server, static client + analyze API.

Run:  python3 server.py [--port 8740]
Offline by construction: serves www/ and fixtures/ from the repo, and
the analysis POST body never persists (tempfile, deleted after parse).
"""

import argparse
import json
import os
import posixpath
import tempfile
import threading

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import wave as wavemod

from chordlens.chords import NOTE_NAMES
from chordlens.detect import analyze_detailed
from chordlens import progressions

ROOT = os.path.dirname(os.path.abspath(__file__))
MAX_BODY = 32 * 1024 * 1024  # 32 MB upload cap

# www/ and fixtures/ are both served read-only; /fixtures/ exists so the
# demo loop and the headless smoke test can fetch a real WAV.
STATIC_ROOTS = {
    "/": os.path.join(ROOT, "www"),
    "/fixtures/": os.path.join(ROOT, "fixtures"),
}
MIME = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
        ".js": "text/javascript; charset=utf-8", ".json": "application/json",
        ".wav": "audio/wav", ".svg": "image/svg+xml", ".ico": "image/x-icon"}


def safe_path(base, url_path):
    """Containment check: resolve and verify the path stays under base."""
    path = posixpath.normpath(url_path).lstrip("/")
    if path.startswith("..") or os.path.isabs(path) or "\x00" in path:
        return None
    full = os.path.realpath(os.path.join(base, path))
    if full != base and not full.startswith(base + os.sep):
        return None
    return full


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "chordlens/0.1"

    def log_message(self, fmt, *args):  # quiet: errors still print
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        query = {}
        if "?" in self.path:
            for pair in self.path.split("?", 1)[1].split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    query[k] = v
        # API branches before static
        if path == "/api/progressions":
            key = None
            if "key" in query:
                try:
                    key = int(query["key"]) % 12
                except ValueError:
                    self._send(400, {"error": "key must be an integer"})
                    return
            body = []
            for pid, p in progressions.PROGRESSIONS.items():
                entry = {"id": pid, "name": p["name"], "origin": p["origin"],
                         "native": p.get("native", ""), "description": p["description"],
                         "genre": p.get("genre", ""), "mood": p.get("mood", ""),
                         "degrees": [s["degree"] for s in p["steps"]]}
                if key is not None:
                    entry["chords"] = [c["label"] for c in progressions.chords_for(pid, key)]
                body.append(entry)
            self._send(200, body)
            return
        if path == "/api/key":
            try:
                key_root = int(query.get("key", 0)) % 12
            except ValueError:
                self._send(400, {"error": "key must be an integer"})
                return
            self._send(200, {"key": NOTE_NAMES[key_root], "chords": progressions.key_chords(key_root)})
            return
        if path == "/api/chord.wav":
            try:
                root = int(query.get("root", 0)) % 12
                dur = float(query.get("dur", 1.4))
            except ValueError:
                self._send(400, {"error": "root and dur must be numbers"})
                return
            quality = query.get("quality", "maj")
            if quality not in progressions.QUALITY_INTERVALS:
                self._send(400, {"error": f"unknown quality: {quality!r}"})
                return
            if not 0.3 <= dur <= 5.0:
                self._send(400, {"error": "dur must be 0.3-5.0 seconds"})
                return
            self._send(200, progressions.render_single(root, quality, dur), "audio/wav")
            return
        if path == "/api/progression.wav":
            pid = query.get("id", "")
            if pid not in progressions.PROGRESSIONS:
                self._send(404, {"error": f"unknown progression: {pid!r}"})
                return
            try:
                key_root = int(query.get("key", 0)) % 12
                bpm = int(query.get("bpm", 100))
            except ValueError:
                self._send(400, {"error": "key and bpm must be integers"})
                return
            if not 40 <= bpm <= 200:
                self._send(400, {"error": "bpm must be 40-200"})
                return
            self._send(200, progressions.render(pid, key_root, bpm), "audio/wav")
            return
        # longest prefix wins, so /fixtures/ is not swallowed by /
        for prefix, base in sorted(STATIC_ROOTS.items(), key=lambda kv: -len(kv[0])):
            if prefix == "/" or path.startswith(prefix):
                rel = path[len(prefix):] if prefix != "/" else path.lstrip("/")
                if rel in ("", "/"):
                    rel = "index.html"
                full = safe_path(base, rel)
                if full and os.path.isfile(full):
                    ext = os.path.splitext(full)[1].lower()
                    with open(full, "rb") as f:
                        self._send(200, f.read(), MIME.get(ext, "application/octet-stream"))
                    return
                break
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/analyze":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY:
            self._send(400 if length <= 0 else 413,
                       {"error": f"body must be a WAV between 1 byte and {MAX_BODY} bytes"})
            return
        body = self.rfile.read(length)
        fd, tmp = tempfile.mkstemp(suffix=".wav", dir=tempfile.gettempdir())
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(body)
            segments, frames = analyze_detailed(tmp)
        except (ValueError, wavemod.Error, EOFError) as exc:  # bad WAV
            self._send(422, {"error": f"bad WAV: {exc}"})
            return
        except Exception as exc:  # noqa: BLE001 — surface, never crash the server
            self._send(500, {"error": f"analysis failed: {exc}"})
            return
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        self._send(200, {"segments": [{"start": a, "end": b, "chord": c} for a, b, c in segments],
                         "frames": frames})


def serve(port):
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    httpd.daemon_threads = True
    return httpd


def main():
    ap = argparse.ArgumentParser(description="chordlens web UI")
    ap.add_argument("--port", type=int, default=8740)
    args = ap.parse_args()
    httpd = serve(args.port)
    print(f"chordlens listening on http://127.0.0.1:{args.port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
