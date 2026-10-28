"""Smoke tests for the FixLens scaffold (stdlib unittest only).

Covers the whole mock flow a demo needs:
  health endpoint -> upload page -> multipart upload -> JSON with a
  region, a diagnosis, repair steps, parts, and a ticket draft.
Also asserts the Meta provider refuses without a key, so no
test path can accidentally spend credits.
"""

import http.client
import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fixlens.app import MAX_UPLOAD_BYTES, build_provider, make_server
from fixlens.providers import (
    MetaModelProvider,
    MockProvider,
    Region,
    pick_scenario,
)

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
        self.assertIn("Copy ticket", page)
        self.assertIn("ticket-text", page)
        # Submit wiring must not depend on addEventListener alone:
        # inline onsubmit + native POST fallback to /api/diagnose.
        self.assertIn("analyzeForm", page)
        self.assertIn('action="/api/diagnose"', page)

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
        self.assertTrue(payload["photo_data_url"].startswith("data:image/"))
        region = payload["region"]
        self.assertTrue(0 <= region["x"] < 1 and 0 <= region["width"] <= 1)
        diag = payload["diagnosis"]
        self.assertTrue(diag["fault"])
        self.assertIn(diag["severity"], ("low", "moderate", "urgent"))
        self.assertTrue(diag["repair_steps"])
        self.assertTrue(diag["parts"])
        self.assertTrue(diag["ticket_draft"])

    def test_meta_provider_without_key_refuses(self):
        with self.assertRaises(RuntimeError):
            MetaModelProvider(api_key="").analyze(b"fake-bytes")

    def test_mock_provider_shape(self):
        analysis = MockProvider().analyze(b"fake-bytes")
        data = analysis.to_dict()
        self.assertIn("region", data)
        self.assertIn("diagnosis", data)


class SchemaAndScenarioTest(unittest.TestCase):
    """Extended schema, all mock scenarios, and the mock-only guard."""

    def test_all_scenarios_have_full_schema(self):
        cases = [
            ("leak.png", "", "", "water_leak_stain"),
            ("wall.jpg", "", "crack", "wall_crack"),
            ("photo.png", "mould in bathroom", "", "mould_spot"),
            ("photo.png", "peeling paint", "", "peeling_paint"),
        ]
        for filename, notes, scenario, fault_type in cases:
            with self.subTest(fault_type=fault_type):
                data = MockProvider().analyze(
                    b"fake-bytes", filename, notes=notes, scenario=scenario
                ).to_dict()
                self.assertTrue(data["region"])
                region = data["region"]
                self.assertTrue(0 <= region["x"] < 1 and 0 <= region["width"] <= 1)
                diag = data["diagnosis"]
                self.assertEqual(diag["fault_type"], fault_type)
                self.assertIn(diag["severity"], ("low", "moderate", "urgent"))
                self.assertTrue(diag["severity_reason"])
                self.assertTrue(diag["safety_warnings"])
                self.assertIn("SAFETY", diag["safety_warnings"][0])
                self.assertTrue(diag["repair_steps"])
                self.assertTrue(diag["parts"])
                self.assertTrue(diag["difficulty"])
                self.assertIn("estimate", diag["estimated_time"])
                self.assertTrue(diag["responsibility_hint"])
                self.assertEqual(diag["ticket"]["status"], "draft")
                self.assertIn("DRAFT", diag["ticket_draft"])
                # No prices anywhere in the output.
                self.assertNotIn("$", json.dumps(data))

    def test_default_scenario_is_leak(self):
        self.assertEqual(pick_scenario("photo.png", ""), "leak")

    def test_provider_interface_segment_and_diagnose(self):
        provider = MockProvider()
        region = provider.segment(b"fake-bytes", "crack")
        self.assertIsInstance(region, Region)
        self.assertTrue(region.is_valid())
        diag = provider.diagnose(b"fake-bytes", region)
        self.assertEqual(diag.fault_type, "wall_crack")

    def test_meta_without_key_segment_and_diagnose_raise(self):
        stub = MetaModelProvider(api_key="")
        with self.assertRaises(RuntimeError):
            stub.segment(b"fake-bytes", "leak")
        with self.assertRaises(RuntimeError):
            stub.diagnose(b"fake-bytes", Region(0.1, 0.1, 0.5, 0.5))

    def test_provider_guard(self):
        with mock.patch.dict(os.environ, {"FIXLENS_PROVIDER": "meta",
                                          "MODEL_API_KEY": ""}):
            with self.assertRaises(RuntimeError):
                build_provider()
        with mock.patch.dict(os.environ, {"FIXLENS_PROVIDER": "meta",
                                          "MODEL_API_KEY": "test-key"}):
            provider, name = build_provider()
            self.assertEqual(name, "meta")
            self.assertEqual(provider.api_key, "test-key")

    def test_empty_photo_rejected_by_provider(self):
        with self.assertRaises(ValueError):
            MockProvider().analyze(b"")


class ValidationTest(SmokeTest):
    """HTTP validation: empty / missing / wrong-type / oversize uploads.

    Reuses SmokeTest's server (setUpClass) but overrides the flow
    tests by only adding validation cases here.
    """

    def _post_raw(self, body: bytes, content_type: str):
        req = urllib.request.Request(
            self._url("/api/diagnose"), data=body, method="POST",
            headers={"Content-Type": content_type},
        )
        try:
            with urllib.request.urlopen(req) as res:
                return res.status, json.loads(res.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_empty_file_rejected(self):
        body, boundary = _multipart("photo", "empty.png", b"")
        status, payload = self._post_raw(
            body, f"multipart/form-data; boundary={boundary}")
        self.assertEqual(status, 400)
        self.assertIn("empty", payload["error"])

    def test_missing_file_rejected(self):
        boundary = "----fixlens-test-boundary"
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="notes"\r\n\r\n'
            "hello\r\n"
            f"--{boundary}--\r\n"
        ).encode()
        status, _payload = self._post_raw(
            body, f"multipart/form-data; boundary={boundary}")
        self.assertEqual(status, 400)

    def test_wrong_content_type_rejected(self):
        status, _payload = self._post_raw(b"{}", "application/json")
        self.assertEqual(status, 400)

    def test_oversize_rejected(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.putrequest("POST", "/api/diagnose")
        conn.putheader("Content-Type",
                       "multipart/form-data; boundary=----fixlens-test-boundary")
        conn.putheader("Content-Length", str(MAX_UPLOAD_BYTES + 1))
        conn.endheaders()
        res = conn.getresponse()
        payload = json.loads(res.read())
        conn.close()
        self.assertEqual(res.status, 413)
        self.assertIn("10 MB", payload["error"])

    def test_ticket_fields_editable_but_still_draft(self):
        boundary = "----fixlens-test-boundary"
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="photo"; filename="leak.png"\r\n'
            "Content-Type: image/png\r\n\r\n"
        ).encode() + FAKE_PNG + (
            f"\r\n--{boundary}\r\n"
            'Content-Disposition: form-data; name="property"\r\n\r\n'
            "Example Property, Unit B\r\n"
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="tenant"\r\n\r\n'
            "Example Tenant B\r\n"
            f"--{boundary}--\r\n"
        ).encode()
        status, payload = self._post_raw(
            body, f"multipart/form-data; boundary={boundary}")
        self.assertEqual(status, 200)
        self.assertEqual(payload["diagnosis"]["ticket"]["property"],
                         "Example Property, Unit B")
        self.assertEqual(payload["diagnosis"]["ticket"]["tenant"],
                         "Example Tenant B")
        self.assertEqual(payload["diagnosis"]["ticket"]["status"], "draft")


class ProviderFailureTest(unittest.TestCase):
    """A provider RuntimeError (e.g. Meta API failure) must return a
    JSON 502, never drop the connection (regression: curl 52 empty
    reply on the Oct 27 Mac live test)."""

    @classmethod
    def setUpClass(cls):
        cls.server = make_server(0)
        cls.port = cls.server.server_address[1]

        class FailingProvider:
            def analyze(self, *args, **kwargs):
                raise RuntimeError(
                    "Meta Model API call failed: HTTP 401")

        cls.server.RequestHandlerClass.provider = FailingProvider()
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_provider_runtime_error_returns_502_json(self):
        body, boundary = _multipart("photo", "leak.png", FAKE_PNG)
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/diagnose",
            data=body, method="POST",
            headers={"Content-Type":
                     f"multipart/form-data; boundary={boundary}"},
        )
        try:
            with urllib.request.urlopen(req) as res:
                status, payload = res.status, json.loads(res.read())
        except urllib.error.HTTPError as exc:
            status, payload = exc.code, json.loads(exc.read())
        self.assertEqual(status, 502)
        self.assertIn("401", payload["error"])


if __name__ == "__main__":
    unittest.main()
