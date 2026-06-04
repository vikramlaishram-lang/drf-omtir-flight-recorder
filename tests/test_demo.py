from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from drf_omtir_flight_recorder.core import run_demo, run_resilient_demo
from drf_omtir_flight_recorder.verifier import verify_wal


class DemoTest(unittest.TestCase):
    def test_demo_produces_five_event_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_demo(tmp)
            self.assertEqual(summary["Status"], "PASS")
            checks = summary["checks"]
            self.assertTrue(all(checks.values()))
            wal_path = Path(summary["wal_path"])
            receipt_path = Path(summary["trust_receipt_path"])
            self.assertTrue(wal_path.exists())
            self.assertTrue(receipt_path.exists())
            report = verify_wal(wal_path, root=tmp)
            self.assertEqual(report.status, "PASS")
            self.assertEqual(report.records, 5)

    def test_tampered_wal_fails_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_demo(tmp)
            wal_path = Path(summary["wal_path"])
            rows = [json.loads(line) for line in wal_path.read_text(encoding="utf-8").splitlines()]
            rows[1]["payload"]["proposal"]["arguments"]["query"] = "tampered"
            wal_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            report = verify_wal(wal_path, root=tmp)
            self.assertEqual(report.status, "FAIL")
            self.assertTrue(any("hash mismatch" in error for error in report.errors))

    def test_resilient_demo_produces_recovery_sequence_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_resilient_demo(tmp)
            self.assertEqual(summary["Status"], "PASS")
            checks = summary["checks"]
            self.assertTrue(all(checks.values()))
            self.assertEqual(summary["provider_route"], "TRUEFOUNDRY_GATEWAY")
            self.assertEqual(summary["model"], "GEMINI_FLASH_LITE")
            self.assertEqual(summary["aws_bedrock"], "NOT_USED")
            self.assertEqual(summary["gateway_failure"], "RATE_LIMIT_EXCEEDED")
            self.assertEqual(summary["rate_limit_rule"], "drf-omtir-resilience-rate-limit")
            self.assertEqual(summary["first_request"], "SUCCEEDED")
            self.assertEqual(summary["second_request"], "RATE_LIMITED")
            self.assertFalse(summary["aws_bedrock_used"])
            self.assertEqual(summary["wal_records"], 6)
            self.assertEqual(summary["verifier_status"], "PASS")
            wal_path = Path(summary["wal_path"])
            receipt_path = Path(summary["trust_receipt_path"])
            trace_path = Path(summary["trace_path"])
            self.assertTrue(wal_path.exists())
            self.assertTrue(receipt_path.exists())
            self.assertTrue(trace_path.exists())
            wal_text = wal_path.read_text(encoding="utf-8")
            self.assertIn("RATE_LIMIT_EXCEEDED", wal_text)
            self.assertIn("drf-omtir-resilience-rate-limit", wal_text)
            self.assertIn("NOT_USED", wal_text)
            receipt_text = receipt_path.read_text(encoding="utf-8")
            self.assertIn("TrueFoundry AI Gateway rate limit", receipt_text)
            self.assertIn("AWS Bedrock: NOT_USED", receipt_text)
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            self.assertEqual(trace["gateway_failure"], "RATE_LIMIT_EXCEEDED")
            self.assertEqual(trace["rate_limit_rule"], "drf-omtir-resilience-rate-limit")
            report = verify_wal(wal_path, root=tmp)
            self.assertEqual(report.status, "PASS")
            self.assertEqual(report.records, 6)


if __name__ == "__main__":
    unittest.main()
