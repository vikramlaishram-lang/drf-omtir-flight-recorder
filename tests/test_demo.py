from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from drf_omtir_flight_recorder.core import run_demo
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


if __name__ == "__main__":
    unittest.main()
