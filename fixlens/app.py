"""FixLens scaffold backend — Python standard library only.

No third-party dependencies, so it runs with plain `python3 run.py`.
Routes:
  GET  /               upload page (HTML)
  GET  /health         {"status": "ok", "provider": "mock"}
  POST /api/diagnose   multipart form with a `photo` file field
                       -> JSON: region + diagnosis (mock provider)

Safety: the server only ever serves the mock provider. If
FIXLENS_PROVIDER is set to anything other than "mock", the server
refuses to start rather than risk a paid API call.
"""

from __future__ import annotations

import html
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .providers import get_provider

INDEX_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>FixLens (mock demo)</title>
<style>
body{font-family:system-ui,sans-serif;max-width:640px;margin:2em auto;padding:0 1em}
pre{background:#f4f4f4;padding:1em;white-space:pre-wrap}
.note{color:#666}
</style></head><body>
<h1>FixLens — mock demo</h1>
<p class="note">Upload a photo of a home fault. This scaffold uses a MOCK
provider: the region and diagnosis below are fixed demo output, not a
real SAM / Muse Spark result. No API is called and nothing is spent.</p>
<form id="f" enctype="multipart/form-data">
<input type="file" name="photo" accept="image/*" required>
<button type="submit">Analyze (mock)</button>
</form>
<pre id="out">Result will appear here…</pre>
<script>
document.getElementById('f').addEventListener('submit', async (e) => {
  e.preventDefault();
  const out = document.getElementById('out');
  out.textContent = 'Analyzing (mock)…';
  const res = await fetch('/api/diagnose', {method: 'POST', body: new FormData(e.target)});
  out.textContent = JSON.stringify(await res.json(), null, 2);
});
</script>
</body></html>
"""


def _parse_multipart_photo(body: bytes, boundary: bytes) -> tuple[bytes, str]:
    """Minimal multipart parser: returns (file bytes, filename).

    Only extracts the first part with a filename. Raises ValueError on
    malformed input instead of guessing.
    """
    parts = body.split(b"--" + boundary)
    for part in parts:
        if b"filename=" not in part:
            continue
        header, _, content = part.partition(b"\r\n\r\n")
        if not content:
            continue
        # Strip the trailing CRLF that precedes the next boundary.
        if content.endswith(b"\r\n"):
            content = content[:-2]
        name = ""
        # Only parse the Content-Disposition line: splitting the whole
        # header block on ";" would swallow the following header line
        # into the filename (the bug the first smoke run caught).
        for line in header.decode("utf-8", "replace").split("\r\n"):
            if not line.lower().startswith("content-disposition:"):
                continue
            for token in line.split(";"):
                token = token.strip()
                if token.startswith("filename="):
                    name = token[len("filename="):].strip('"')
        return content, name
    raise ValueError("no file part named 'photo' found")


def build_provider():
    name = os.environ.get("FIXLENS_PROVIDER", "mock")
    if name != "mock":
        raise RuntimeError(
            f"Refusing to start with FIXLENS_PROVIDER={name!r}: only "
            "'mock' is wired in this scaffold. The Meta provider is a "
            "stub and must not be served until credits land and Wen approves."
        )
    return get_provider("mock")


class Handler(BaseHTTPRequestHandler):
    provider = None  # set by make_server()

    def log_message(self, *args):  # keep test output clean
        pass

    def _send_json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802 - stdlib naming
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "provider": "mock"})
        elif self.path in ("/", "/index.html"):
            data = INDEX_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802 - stdlib naming
        if self.path != "/api/diagnose":
            self._send_json(404, {"error": "not found"})
            return
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._send_json(400, {"error": "expected multipart/form-data"})
            return
        boundary = content_type.split("boundary=")[-1].strip().encode()
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b""
        try:
            photo_bytes, filename = _parse_multipart_photo(body, boundary)
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
            return
        if not photo_bytes:
            self._send_json(400, {"error": "uploaded file is empty"})
            return
        analysis = self.provider.analyze(photo_bytes, filename)
        self._send_json(200, {
            "provider": "mock",
            "filename": html.escape(filename),
            "size_bytes": len(photo_bytes),
            **analysis.to_dict(),
        })


def make_server(port: int = 0) -> ThreadingHTTPServer:
    provider = build_provider()
    handler = type("FixLensHandler", (Handler,), {"provider": provider})
    return ThreadingHTTPServer(("127.0.0.1", port), handler)
