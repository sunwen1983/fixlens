"""FixLens backend — Python standard library only.

No third-party dependencies, so it runs with plain `python3 run.py`.
Routes:
  GET  /               upload page (HTML form + rendered result)
  GET  /health         {"status": "ok", "provider": "mock"}
  POST /api/diagnose   multipart form with a `photo` file field and
                       optional `scenario`, `notes`, `property`,
                       `tenant`, `landlord` text fields
                       -> JSON: region + extended diagnosis + ticket

Validation (all failures are JSON 4xx, never a crash page):
  - wrong content type -> 400
  - missing boundary -> 400
  - no file part / empty file -> 400
  - file larger than MAX_UPLOAD_BYTES (10 MB) -> 413

Safety: the server serves the mock provider by default. It serves
the Meta provider only when FIXLENS_PROVIDER=meta AND the
MODEL_API_KEY environment variable is set; otherwise it refuses to
start rather than risk a misconfigured paid API call.
"""

from __future__ import annotations

import html
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .providers import get_provider, photo_data_url, with_ticket_overrides

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

# Shared page style (upload page + server-rendered result page).
# Plain string on purpose: it is interpolated into an f-string in
# render_result_html, so it must not contain bare { } itself.
_PAGE_STYLE = """
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:#f4f5f7;color:#1f2937;max-width:760px;margin:2.5em auto;padding:0 1.25em;line-height:1.55}
h1{font-size:1.6em;margin-bottom:.2em}
h2{font-size:1.15em;margin-top:0}
.note{color:#6b7280}
.badge{display:inline-block;background:#e5e7eb;border-radius:999px;padding:.15em .6em;font-size:.85em;font-weight:600}
.warn{background:#fef2f2;border:1px solid #fecaca;border-left:5px solid #e53935;border-radius:12px;padding:1em 1.25em}
.warn h2{color:#b91c1c}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:1.25em 1.5em;margin:1.25em 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.draft{background:#fffbeb;border-color:#fde68a}
button{background:#1f2937;color:#fff;border:0;border-radius:8px;padding:.6em 1.4em;font-size:1em;cursor:pointer}
button:hover{background:#374151}
input[type=text],select{border:1px solid #d1d5db;border-radius:8px;padding:.45em .6em;font-size:1em;background:#fff}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #e5e7eb;padding:.5em .6em;text-align:left}th{background:#f9fafb}
textarea{width:100%;border:1px solid #e5e7eb;border-radius:8px;padding:.6em;font:1em/1.5 system-ui,sans-serif;box-sizing:border-box}
img{border-radius:8px}
ul{padding-left:1.25em}li{margin:.35em 0}
a{color:#1d4ed8}
"""

INDEX_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>FixLens</title>
<style>__PAGE_STYLE__</style></head><body>
<h1>FixLens — __PROVIDER_LABEL__</h1>
<p class="note">__PROVIDER_NOTE__ Ticket text is a DRAFT only — nothing is sent.</p>
<form id="f" class="card" action="/api/diagnose" method="POST" enctype="multipart/form-data" onsubmit="return analyzeForm(event)">
<p><input type="file" name="photo" accept="image/*" required></p>
<p><label>Fault (optional, picks the mock scenario):
<select name="scenario">
<option value="">Auto (from filename / notes)</option>
<option value="leak">Water stain / leak</option>
<option value="crack">Wall crack</option>
<option value="mould">Mould spot</option>
<option value="paint">Peeling paint</option>
</select></label></p>
<p><label>Notes (optional): <input type="text" name="notes" size="50"></label></p>
<p><label>Property: <input type="text" name="property" value="Example Property, Unit A"></label>
<label>Tenant: <input type="text" name="tenant" value="Example Tenant"></label>
<label>Landlord: <input type="text" name="landlord" value="Example Landlord"></label></p>
<button type="submit">Analyze</button>
</form>
<div id="out"></div>
<script>
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
async function analyzeForm(e) {
  e.preventDefault();
  const out = document.getElementById('out');
  out.innerHTML = '<p>Analyzing…</p>';
  const res = await fetch('/api/diagnose', {method: 'POST', body: new FormData(e.target)});
  const d = await res.json();
  if (!res.ok) { out.innerHTML = '<p>Error: ' + esc(d.error || res.status) + '</p>'; return; }
  const diag = d.diagnosis, t = diag.ticket;
  const warn = diag.safety_warnings.map(w => '<li>' + esc(w) + '</li>').join('');
  const steps = diag.repair_steps.map(s => '<li><input type="checkbox"> ' + esc(s) + '</li>').join('');
  const parts = diag.parts.map(p => '<tr><td>' + esc(p.item) + '</td><td>' + esc(p.quantity) + '</td><td>' + esc(p.note) + '</td></tr>').join('');
  const r = d.region;
  const photo = '<div style="position:relative;display:inline-block;max-width:100%">' +
    '<img src="' + esc(d.photo_data_url) + '" style="max-width:100%;display:block">' +
    '<div style="position:absolute;left:' + (r.x * 100) + '%;top:' + (r.y * 100) + '%;width:' + (r.width * 100) + '%;height:' + (r.height * 100) + '%;border:3px solid #e53935;box-sizing:border-box">' +
    '<span style="background:#e53935;color:#fff;padding:0 .3em;font-size:.85em">' + esc(r.label) + '</span></div></div>';
  out.innerHTML =
    '<div class="warn"><h2>⚠ Safety first</h2><ul>' + warn + '</ul></div>' +
    '<div class="card"><h2>' + esc(diag.fault) + '</h2>' +
    '<p>Severity: <span class="badge">' + esc(diag.severity) + '</span> — ' + esc(diag.severity_reason) + '</p>' +
    '<p>Likely cause: ' + esc(diag.likely_cause) + '</p>' +
    '<p>Difficulty: ' + esc(diag.difficulty) + ' · Estimated time: ' + esc(diag.estimated_time) + '</p>' +
    '<p>' + esc(diag.responsibility_hint) + '</p>' +
    '<p>Segmented region: ' + esc(d.region.label) + '</p>' +
    photo + '</div>' +
    '<div class="card"><h2>Repair checklist</h2><ul>' + steps + '</ul>' +
    '<h2>Parts list (quantities only — no prices)</h2><table><tr><th>Item</th><th>Quantity</th><th>Note</th></tr>' + parts + '</table></div>' +
    '<div class="card draft"><h2>Repair ticket <span class="badge">DRAFT — not sent</span></h2>' +
    '<p><b>' + esc(t.title) + '</b> · ' + esc(t.property) + '</p>' +
    '<p>' + esc(t.description) + '</p>' +
    '<p>Next steps: ' + esc(t.next_steps.join('; ')) + '</p>' +
    '<p>Tenant: ' + esc(t.tenant) + ' · Landlord: ' + esc(t.landlord) + '</p>' +
    '<p id="ticket-text">' + esc(diag.ticket_draft) + '</p>' +
    '<button id="ticket-copy">Copy ticket</button></div>';
  document.getElementById('ticket-copy').addEventListener('click', () => {
    navigator.clipboard.writeText(document.getElementById('ticket-text').textContent);
  });
  return false;
}
</script>
</body></html>
"""


def _parse_multipart(body: bytes, boundary: bytes):
    """Parse multipart body -> (file bytes, filename, text fields).

    Raises ValueError on malformed input instead of guessing. Only the
    first file part is returned; text fields are decoded as UTF-8.
    """
    photo_bytes, filename, fields = None, "", {}
    for part in body.split(b"--" + boundary):
        if b"Content-Disposition:" not in part:
            continue
        header, sep, content = part.partition(b"\r\n\r\n")
        if not sep:
            continue
        if content.endswith(b"\r\n"):
            content = content[:-2]
        name, fname = "", None
        for line in header.decode("utf-8", "replace").split("\r\n"):
            if not line.lower().startswith("content-disposition:"):
                continue
            for token in line.split(";"):
                token = token.strip()
                if token.startswith("name="):
                    name = token[len("name="):].strip('"')
                elif token.startswith("filename="):
                    fname = token[len("filename="):].strip('"')
        if fname is not None:
            photo_bytes, filename = content, fname
        elif name:
            fields[name] = content.decode("utf-8", "replace")
    if photo_bytes is None:
        raise ValueError("no file part found in upload")
    return photo_bytes, filename, fields


def build_provider():
    name = os.environ.get("FIXLENS_PROVIDER", "mock")
    if name == "mock":
        return get_provider("mock"), "mock"
    if name == "meta":
        provider = get_provider("meta")
        if not provider.api_key:
            raise RuntimeError(
                "Refusing to start with FIXLENS_PROVIDER='meta': "
                "MODEL_API_KEY is not set in the environment."
            )
        return provider, "meta"
    raise RuntimeError(
        f"Refusing to start with FIXLENS_PROVIDER={name!r}: only "
        "'mock' and 'meta' are supported."
    )


def render_result_html(provider_name: str, filename: str,
                       photo_data_url_str: str, result: dict) -> str:
    """Server-rendered diagnosis page for a native form POST.

    A browser that submits the upload form natively (page JavaScript
    not running, e.g. JS blocked) sends Accept: text/html and would
    otherwise get a raw JSON document with no photo and no box. This
    page renders the same result server-side: photo + red SAM box,
    safety warnings, repair checklist, parts, and the draft ticket in
    a textarea so it can be copied without any JavaScript.
    """
    region = result["region"]
    diag = result["diagnosis"]
    ticket = diag["ticket"]
    warn = "".join(f"<li>{html.escape(w)}</li>"
                   for w in diag["safety_warnings"])
    steps = "".join(f"<li><input type='checkbox'> {html.escape(s)}</li>"
                    for s in diag["repair_steps"])
    parts = "".join(
        f"<tr><td>{html.escape(p['item'])}</td>"
        f"<td>{html.escape(p['quantity'])}</td>"
        f"<td>{html.escape(p['note'])}</td></tr>"
        for p in diag["parts"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>FixLens — diagnosis</title>
<style>{_PAGE_STYLE}</style></head><body>
<h1>FixLens — {html.escape(provider_name)}</h1>
<p><a href="/">← Upload another photo</a> · File: {html.escape(filename)}</p>
<div class="warn"><h2>⚠ Safety first</h2><ul>{warn}</ul></div>
<div class="card"><h2>{html.escape(diag['fault'])}</h2>
<p>Severity: <span class="badge">{html.escape(diag['severity'])}</span> — {html.escape(diag['severity_reason'])}</p>
<p>Likely cause: {html.escape(diag['likely_cause'])}</p>
<p>Difficulty: {html.escape(diag['difficulty'])} · Estimated time: {html.escape(diag['estimated_time'])}</p>
<p>{html.escape(diag['responsibility_hint'])}</p>
<p>Segmented region: {html.escape(region['label'])}</p>
<div style="position:relative;display:inline-block;max-width:100%">
<img src="{html.escape(photo_data_url_str)}" style="max-width:100%;display:block">
<div style="position:absolute;left:{region['x'] * 100}%;top:{region['y'] * 100}%;width:{region['width'] * 100}%;height:{region['height'] * 100}%;border:3px solid #e53935;box-sizing:border-box">
<span style="background:#e53935;color:#fff;padding:0 .3em;font-size:.85em">{html.escape(region['label'])}</span></div></div></div>
<div class="card"><h2>Repair checklist</h2><ul>{steps}</ul>
<h2>Parts list (quantities only — no prices)</h2>
<table><tr><th>Item</th><th>Quantity</th><th>Note</th></tr>{parts}</table></div>
<div class="card draft"><h2>Repair ticket — DRAFT, not sent</h2>
<p><b>{html.escape(ticket['title'])}</b> · {html.escape(ticket['property'])}</p>
<p>{html.escape(ticket['description'])}</p>
<p>Next steps: {html.escape('; '.join(ticket['next_steps']))}</p>
<p>Tenant: {html.escape(ticket['tenant'])} · Landlord: {html.escape(ticket['landlord'])}</p>
<textarea readonly rows="6">{html.escape(diag['ticket_draft'])}</textarea></div>
</body></html>
"""


class Handler(BaseHTTPRequestHandler):
    provider = None  # set by make_server()
    provider_name = "mock"

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
            self._send_json(200, {"status": "ok",
                                  "provider": self.provider_name})
        elif self.path in ("/", "/index.html"):
            if self.provider_name == "meta":
                label = "Meta Model API (SAM 3.1 + Muse Spark)"
                note = ("Upload a photo of a home fault. This demo "
                        "calls the Meta Model API: SAM 3.1 segments "
                        "the faulty region and Muse Spark writes the "
                        "structured diagnosis. No prices are shown.")
            else:
                label = "mock demo"
                note = ("Upload a photo of a home fault. This demo "
                        "uses a MOCK provider: the region and "
                        "diagnosis below are fixed demo output, not "
                        "a real SAM / Muse Spark result. No API is "
                        "called and nothing is spent.")
            page = INDEX_HTML.replace("__PROVIDER_LABEL__", label)
            page = page.replace("__PROVIDER_NOTE__", note)
            page = page.replace("__PAGE_STYLE__", _PAGE_STYLE)
            data = page.encode("utf-8")
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
        if "multipart/form-data" not in content_type or "boundary=" not in content_type:
            self._send_json(400, {"error": "expected multipart/form-data with a boundary"})
            return
        boundary = content_type.split("boundary=")[-1].strip().strip('"').encode()
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "invalid Content-Length"})
            return
        if length > MAX_UPLOAD_BYTES:
            self._send_json(413, {"error": "uploaded file exceeds 10 MB limit"})
            return
        body = self.rfile.read(length) if length else b""
        try:
            photo_bytes, filename, fields = _parse_multipart(body, boundary)
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
            return
        if not photo_bytes:
            self._send_json(400, {"error": "uploaded file is empty"})
            return
        try:
            analysis = self.provider.analyze(
                photo_bytes, filename,
                notes=fields.get("notes", ""),
                scenario=fields.get("scenario", ""),
            )
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
            return
        except RuntimeError as exc:
            # Meta provider API failures (auth, model, network after
            # retries) must surface as a JSON 502, never as a dropped
            # connection: an uncaught exception here closes the socket
            # with an empty reply (curl 52) and hides the real error.
            self._send_json(502, {"error": str(exc)})
            return
        diagnosis = with_ticket_overrides(analysis.diagnosis, fields)
        analysis = type(analysis)(region=analysis.region, diagnosis=diagnosis)
        payload = {
            "provider": self.provider_name,
            "filename": html.escape(filename),
            "size_bytes": len(photo_bytes),
            "photo_data_url": photo_data_url(photo_bytes),
            **analysis.to_dict(),
        }
        # Native form POSTs arrive with Accept: text/html (a fetch
        # sends */*). Answer those with the server-rendered page so a
        # browser with page JavaScript not running still shows the
        # photo, the red box, and the diagnosis instead of raw JSON.
        if "text/html" in self.headers.get("Accept", ""):
            page = render_result_html(
                self.provider_name, filename,
                photo_data_url(photo_bytes), analysis.to_dict())
            data = page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self._send_json(200, payload)


def make_server(port: int = 0) -> ThreadingHTTPServer:
    provider, provider_name = build_provider()
    handler = type("FixLensHandler", (Handler,),
                   {"provider": provider, "provider_name": provider_name})
    return ThreadingHTTPServer(("127.0.0.1", port), handler)
