from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import drf_omtir_flight_recorder.core as core
from drf_omtir_flight_recorder.cli import main
from drf_omtir_flight_recorder.receipt import write_trust_receipt
from drf_omtir_flight_recorder.review import (
    APPROVED_AFTER_REVIEW,
    PENDING_REVIEW,
    REJECTED_AFTER_REVIEW,
    approve_review,
    list_review_items,
    reject_review,
)
from drf_omtir_flight_recorder.verifier import verify_wal


def _jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _wal_path(root: Path) -> Path:
    return root / "wal" / "resilient-demo.jsonl"


def _review_items(root: Path) -> list[dict]:
    return list_review_items(root)["review_items"]


class OperatorWorkflowTest(unittest.TestCase):
    def test_request_review_creates_durable_review_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = core.run_resilient_demo(root)

            self.assertEqual(summary["Status"], "PASS")
            queue = Path(summary["review_queue_path"])
            self.assertTrue(queue.exists())

            items = _review_items(root)
            self.assertEqual(len(items), 1)
            item = items[0]
            for key in [
                "event_id",
                "proposal_id",
                "action",
                "decision",
                "reason",
                "payload_hash",
                "reviewer_status",
            ]:
                self.assertIn(key, item)
            self.assertEqual(item["action"], "restart_service")
            self.assertEqual(item["decision"], "REQUEST_REVIEW")
            self.assertEqual(item["reviewer_status"], PENDING_REVIEW)
            self.assertEqual(item["status"], PENDING_REVIEW)
            self.assertRegex(item["payload_hash"], r"^[0-9a-f]{64}$")

    def test_approve_review_writes_wal_and_receipt_consequence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            core.run_resilient_demo(root)
            event_id = _review_items(root)[0]["event_id"]

            result = approve_review(event_id, reviewer="analyst-1", root=root)

            self.assertEqual(result["Status"], "PASS")
            self.assertEqual(result["reviewer_status"], APPROVED_AFTER_REVIEW)
            report = verify_wal(_wal_path(root), root=root)
            self.assertEqual(report.status, "PASS")

            records = _jsonl(_wal_path(root))
            payload = records[-1]["payload"]
            self.assertEqual(payload["event_id"], result["review_wal_event_id"])
            self.assertEqual(payload["review"]["reviewed_event_id"], event_id)
            self.assertEqual(payload["review"]["reviewer"], "analyst-1")
            self.assertEqual(payload["review"]["reviewer_status"], APPROVED_AFTER_REVIEW)

            receipt_path = root / "receipts" / "operator-approve-receipt.md"
            write_trust_receipt(_wal_path(root), receipt_path, root=root)
            text = receipt_path.read_text(encoding="utf-8")
            self.assertIn("Approved after review", text)
            self.assertIn(f"{event_id}->{result['review_wal_event_id']}", text)
            self.assertIn("Pending human review events: none", text)

    def test_reject_review_writes_wal_and_receipt_consequence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            core.run_resilient_demo(root)
            event_id = _review_items(root)[0]["event_id"]

            result = reject_review(
                event_id,
                reviewer="analyst-2",
                reason="Need maintenance window",
                root=root,
            )

            self.assertEqual(result["Status"], "PASS")
            self.assertEqual(result["reviewer_status"], REJECTED_AFTER_REVIEW)
            report = verify_wal(_wal_path(root), root=root)
            self.assertEqual(report.status, "PASS")

            records = _jsonl(_wal_path(root))
            payload = records[-1]["payload"]
            self.assertEqual(payload["event_id"], result["review_wal_event_id"])
            self.assertEqual(payload["review"]["reviewed_event_id"], event_id)
            self.assertEqual(payload["review"]["reviewer"], "analyst-2")
            self.assertEqual(payload["review"]["reviewer_status"], REJECTED_AFTER_REVIEW)
            self.assertEqual(payload["review"]["review_reason"], "Need maintenance window")

            receipt_path = root / "receipts" / "operator-reject-receipt.md"
            write_trust_receipt(_wal_path(root), receipt_path, root=root)
            text = receipt_path.read_text(encoding="utf-8")
            self.assertIn("Rejected after review", text)
            self.assertIn(f"{event_id}->{result['review_wal_event_id']}", text)
            self.assertIn("Pending human review events: none", text)

    def test_missing_reviewer_unknown_event_and_missing_reason_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            core.run_resilient_demo(root)
            event_id = _review_items(root)[0]["event_id"]
            before = len(_jsonl(_wal_path(root)))

            self.assertEqual(
                approve_review(event_id, reviewer="", root=root)["Status"],
                "BLOCKED",
            )
            self.assertEqual(
                reject_review(event_id, reviewer="analyst", reason="", root=root)[
                    "Status"
                ],
                "BLOCKED",
            )
            self.assertEqual(
                approve_review("evt_999999", reviewer="analyst", root=root)["Status"],
                "BLOCKED",
            )
            self.assertEqual(len(_jsonl(_wal_path(root))), before)

    def test_review_cli_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            core.run_resilient_demo(root)
            event_id = _review_items(root)[0]["event_id"]

            with contextlib.redirect_stdout(io.StringIO()) as out:
                rc = main(["review", "list", "--root", str(root)])
            self.assertEqual(rc, 0)
            self.assertIn(event_id, out.getvalue())

            with contextlib.redirect_stdout(io.StringIO()) as out:
                rc = main(
                    [
                        "review",
                        "approve",
                        event_id,
                        "--reviewer",
                        "analyst-cli",
                        "--root",
                        str(root),
                    ]
                )
            self.assertEqual(rc, 0)
            self.assertIn(APPROVED_AFTER_REVIEW, out.getvalue())
            self.assertEqual(verify_wal(_wal_path(root), root=root).status, "PASS")


if __name__ == "__main__":
    unittest.main()
