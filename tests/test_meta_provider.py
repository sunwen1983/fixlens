"""Meta provider tests — canned responses only, zero network.

Covers the official SAM output_text grammar (box + mask, frame
marker), box-to-fraction conversion, zero-match handling, the
Spark text.format structured-output path (never response_format on
Responses), and retry on 404 model_not_found without retrying 400.
No test here sets a real key or touches the network.
"""

import io
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fixlens.providers import (
    MetaModelProvider,
    concept_for,
    parse_sam_output_text,
)

SAM_TEXT = (
    "<0f>0<|box;x1=100;y1=100;x2=199;y2=199;w=400;h=400|>"
    "<|mask;x=0;y=0;data=10,10,~AAAA|>"
)

SPARK_DIAGNOSIS = {
    "fault": "Water stain / suspected leak",
    "fault_type": "water_leak_stain",
    "severity": "moderate",
    "severity_reason": "Spreads if left, no active flooding seen.",
    "likely_cause": "Possible slow plumbing leak above the stain.",
    "safety_warnings": ["SAFETY FIRST: keep water away from electrics."],
    "repair_steps": ["Inspect plumbing above.", "Dry and repaint."],
    "parts": [{"item": "Pipe sealant", "quantity": "1", "note": ""}],
    "difficulty": "moderate",
    "estimated_time": "Inspection 30-60 min (estimate)",
    "responsibility_hint": "Hint only: usually the landlord's.",
}


def _sam_response(text=SAM_TEXT):
    return {"output": [{"type": "message", "content": [
        {"type": "output_text", "text": text}]}]}


def _spark_response(diag=None):
    return {"output_text": json.dumps(diag or SPARK_DIAGNOSIS)}


class SamParsingTest(unittest.TestCase):
    def test_box_to_fraction_region(self):
        records = parse_sam_output_text(SAM_TEXT)
        self.assertEqual(len(records), 1)
        rec = records[0]
        # x2/y2 are inclusive: (199-100+1)/400 = 0.25.
        self.assertEqual((rec["x1"], rec["y1"], rec["w"], rec["h"]),
                         (100, 100, 400, 400))
        self.assertEqual(rec["mask_encoding"], "~")

    def test_zero_matches_raises(self):
        with self.assertRaises(ValueError):
            parse_sam_output_text("")

    def test_zero_match_message_is_friendly(self):
        with self.assertRaises(ValueError) as ctx:
            parse_sam_output_text("")
        self.assertIn("clearer, closer photo", str(ctx.exception))
        self.assertNotIn("400", str(ctx.exception))

    def test_largest_sam_box_wins(self):
        from fixlens.providers import _largest_sam_record
        small = {"x1": 0, "y1": 0, "x2": 9, "y2": 9}
        big = {"x1": 0, "y1": 0, "x2": 99, "y2": 99}
        self.assertIs(_largest_sam_record([small, big]), big)
        self.assertIs(_largest_sam_record([big, small]), big)

    def test_concept_is_single_noun_phrase(self):
        self.assertEqual(concept_for("photo.png", "", "crack"), "wall crack")
        self.assertEqual(concept_for("leak.png", ""), "water stain")
        self.assertEqual(concept_for("photo.png", "mould here"), "mould")


class MetaProviderCannedTest(unittest.TestCase):
    def _provider(self):
        seen = []

        def request_fn(payload):
            seen.append(payload)
            if payload["model"] == "sam-3.1":
                return _sam_response()
            return _spark_response()

        return MetaModelProvider(api_key="test-key",
                                 request_fn=request_fn), seen

    def test_analyze_uses_sam_then_spark_with_text_format(self):
        provider, seen = self._provider()
        analysis = provider.analyze(b"fake-bytes", "leak.png")
        self.assertEqual(len(seen), 2)
        sam_payload, spark_payload = seen
        self.assertEqual(sam_payload["model"], "sam-3.1")
        sam_text = sam_payload["input"][0]["content"][0]["text"]
        self.assertEqual(sam_text, "water stain")
        self.assertEqual(spark_payload["model"], "muse-spark-1.3")
        # Responses structured output: text.format, never response_format.
        self.assertIn("text", spark_payload)
        self.assertEqual(spark_payload["text"]["format"]["type"],
                         "json_schema")
        self.assertNotIn("response_format", spark_payload)
        region = analysis.region
        self.assertAlmostEqual(region.x, 0.25)
        self.assertAlmostEqual(region.width, 0.25)
        self.assertTrue(region.is_valid())
        diag = analysis.diagnosis
        self.assertEqual(diag.fault_type, "water_leak_stain")
        self.assertEqual(diag.severity, "moderate")
        self.assertEqual(diag.ticket.status, "draft")
        self.assertNotIn("$", json.dumps(analysis.to_dict()))

    def test_sam_zero_match_surfaces_as_value_error(self):
        def request_fn(payload):
            return _sam_response(text="")
        provider = MetaModelProvider(api_key="test-key",
                                     request_fn=request_fn)
        with self.assertRaises(ValueError):
            provider.segment(b"fake-bytes", "leak")

    def test_invalid_severity_rejected(self):
        bad = dict(SPARK_DIAGNOSIS, severity="critical")

        def request_fn(payload):
            return _spark_response(bad)
        provider = MetaModelProvider(api_key="test-key",
                                     request_fn=request_fn)
        from fixlens.providers import Region
        with self.assertRaises(RuntimeError):
            provider.diagnose(b"fake-bytes", Region(0.25, 0.25, 0.25, 0.25))


class RetryTest(unittest.TestCase):
    def test_retries_404_then_succeeds(self):
        ok_body = json.dumps(_sam_response()).encode()
        ok = mock.MagicMock()
        ok.__enter__.return_value.read.return_value = ok_body
        err = urllib.error.HTTPError(
            "https://api.meta.ai/v1/responses", 404, "not found",
            {}, io.BytesIO(b'{"error": "model_not_found"}'))
        provider = MetaModelProvider(api_key="test-key")
        with mock.patch("fixlens.providers.urllib.request.urlopen",
                        side_effect=[err, ok]):
            with mock.patch("fixlens.providers.time.sleep"):
                text = provider._call({"model": "sam-3.1"})["output"][0]
        self.assertEqual(text["content"][0]["type"], "output_text")

    def test_does_not_retry_400(self):
        err = urllib.error.HTTPError(
            "https://api.meta.ai/v1/responses", 400, "bad request",
            {}, io.BytesIO(b'{"error": "bad prompt"}'))
        provider = MetaModelProvider(api_key="test-key")
        with mock.patch("fixlens.providers.urllib.request.urlopen",
                        side_effect=err):
            with mock.patch("fixlens.providers.time.sleep") as slept:
                with self.assertRaises(RuntimeError):
                    provider._call({"model": "sam-3.1"})
        slept.assert_not_called()


if __name__ == "__main__":
    unittest.main()
