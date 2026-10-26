"""Smoke tests for the FixLens scaffold (stdlib unittest only).

Covers the whole mock flow a demo needs:
  health endpoint -> upload page -> multipart upload -> JSON with a
  region, a diagnosis, repair steps, parts, and a ticket draft.
Also asserts the Meta provider stub refuses to call anything, so no
test path can accidentally spend credits.
"""

import json
import sys
import threading
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fixlens.app import make_server
from fixlens.providers import MetaModelProvider, MockProvider

# Minimal 1x1 PNG (bytes only — content is irrelevant to the mock).
FAKE_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f"
    b"\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _multipart(field: str, filename: str, data: bytes) -> tuple[bytes, str]:
    boundary = "----fixlens-test-boundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
        "Content-Type: image/png\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    return body, boundary


class SmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def test_health(self):
        with urllib.request.urlopen(self._url("/health")) as res:
            payload = json.loads(res.read())
        self.assertEqual(payload, {"status": "ok", "provider": "mock"})

    def test_upload_page(self):
        with urllib.request.urlopen(self._url("/")) as res:
            page = res.read().decode()
        self.assertIn("FixLens", page)
        self.assertIn("photo", page)

    def test_upload_to_mock_diagnosis(self):
        body, boundary = _multipart("photo", "leak.png", FAKE_PNG)
        req = urllib.request.Request(
            self._url("/api/diagnose"), data=body, method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(req) as res:
            payload = json.loads(res.read())
        self.assertEqual(payload["provider"], "mock")
        self.assertEqual(payload["filename"], "leak.png")
        region = payload["region"]
        self.assertTrue(0 <= region["x"] < 1 and 0 <= region["width"] <= 1)
        diag = payload["diagnosis"]
        self.assertTrue(diag["fault"])
        self.assertIn(diag["severity"], ("low", "moderate", "urgent"))
        self.assertTrue(diag["repair_steps"])
        self.assertTrue(diag["parts"])
        self.assertTrue(diag["ticket_draft"])

    def test_meta_provider_never_calls(self):
        with self.assertRaises(RuntimeError):
            MetaModelProvider().analyze(b"fake-bytes")

    def test_mock_provider_shape(self):
        analysis = MockProvider().analyze(b"fake-bytes")
        data = analysis.to_dict()
        self.assertIn("region", data)
        self.assertIn("diagnosis", data)


if __name__ == "__main__":
    unittest.main()
