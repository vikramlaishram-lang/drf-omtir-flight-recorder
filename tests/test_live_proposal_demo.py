from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import drf_omtir_flight_recorder.core as core
from drf_omtir_flight_recorder.truefoundry_client import (
    MalformedProposalError,
    MissingTrueFoundryConfig,
    TrueFoundryProposal,
)
from drf_omtir_flight_recorder.verifier import VerificationReport, verify_wal


class _FakeTrueFoundryClient:
    def __init__(
        self,
        proposal: TrueFoundryProposal | None = None,
        exc: Exception | None = None,
    ) -> None:
        self.proposal = proposal
        self.exc = exc

    def get_proposal(self) -> TrueFoundryProposal:
        if self.exc:
            raise self.exc
        if self.proposal is None:
            raise AssertionError("fake client missing proposal")
        return self.proposal


def _proposal(
    *,
    action: str = "search_logs",
    arguments: dict[str, object] | None = None,
) -> TrueFoundryProposal:
    parsed = {
        "intent": "propose_action",
        "action": action,
        "arguments": arguments or {
            "service": "checkout-api",
            "query": "error OR critical OR timeout",
        },
    }
    raw = json.dumps(parsed, separators=(",", ":"), sort_keys=True)
    return TrueFoundryProposal(
        raw_model_output=raw,
        raw_model_output_sha256=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        parsed_proposal=parsed,
        model="mock-gemini-flash-lite",
    )


def _read_wal(path: str | Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class LiveProposalDemoTest(unittest.TestCase):
    def test_success_records_live_model_metadata_and_verifies(self) -> None:
        proposal = _proposal()

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(
                core.TrueFoundryProposalClient,
                "from_env",
                return_value=_FakeTrueFoundryClient(proposal),
            ):
                summary = core.run_live_proposal_demo(tmp)

            self.assertEqual(summary["Status"], "PASS")
            self.assertEqual(summary["provider_route"], "TRUEFOUNDRY_GATEWAY")
            self.assertEqual(summary["model"], proposal.model)
            self.assertEqual(summary["agent_proposal_source"], "LIVE_MODEL_OUTPUT")
            self.assertEqual(summary["policy_evaluation"], "LIVE")
            self.assertEqual(summary["raw_model_output_sha256"], proposal.raw_model_output_sha256)
            self.assertEqual(summary["parsed_action"], "search_logs")
            self.assertEqual(summary["drf_decision"], "ALLOW")
            self.assertEqual(summary["tool_execution_boundary"], "LOCAL_STUB")
            self.assertEqual(summary["claim_status"], "CONFIRMED")
            self.assertEqual(summary["verifier_status"], "PASS")
            self.assertTrue(all(summary["checks"].values()))

            wal_path = Path(summary["wal_path"])
            records = _read_wal(wal_path)
            self.assertEqual(summary["wal_records"], len(records))
            self.assertGreaterEqual(len(records), 2)

            first_payload = records[0]["payload"]
            self.assertEqual(first_payload["agent_proposal_source"], "LIVE_MODEL_OUTPUT")
            self.assertEqual(first_payload["model_provider"], "TRUEFOUNDRY_GATEWAY")
            self.assertEqual(first_payload["model"], proposal.model)
            self.assertEqual(first_payload["raw_model_output_sha256"], proposal.raw_model_output_sha256)
            self.assertEqual(first_payload["parsed_proposal"], proposal.parsed_proposal)
            self.assertEqual(first_payload["policy_evaluation"], "LIVE")
            self.assertEqual(first_payload["tool_execution_boundary"], "LOCAL_STUB")
            self.assertEqual(first_payload["authority"]["source"], "DRF_RULE")
            self.assertEqual(first_payload["authority"]["rule"], "search_logs")
            self.assertEqual(first_payload["proposal"]["action"], "search_logs")
            self.assertEqual(first_payload["drf_decision"]["decision"], "ALLOW")
            self.assertTrue(first_payload["execution"]["executed"])
            self.assertEqual(first_payload["tool_result"]["input_sha256_before"], first_payload["tool_result"]["input_sha256_after"])
            self.assertTrue(first_payload["tool_result"]["input_unchanged"])

            report = verify_wal(wal_path, root=tmp)
            self.assertEqual(report.status, "PASS")
            self.assertTrue(Path(summary["verifier_report_path"]).exists())
            self.assertTrue(Path(summary["trust_receipt_path"]).exists())

    def test_missing_config_fails_closed_without_wal_or_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(
                core.TrueFoundryProposalClient,
                "from_env",
                side_effect=MissingTrueFoundryConfig(["TRUEFOUNDRY_API_KEY"]),
            ):
                summary = core.run_live_proposal_demo(tmp)

            self.assertEqual(summary["Status"], "BLOCKED")
            self.assertEqual(summary["reason"], "missing TrueFoundry environment variables")
            self.assertEqual(summary["missing"], ["TRUEFOUNDRY_API_KEY"])
            root = Path(tmp)
            self.assertFalse((root / "wal" / "live-proposal-demo.jsonl").exists())
            self.assertFalse((root / "reports" / "live-proposal-demo-verifier-report.json").exists())
            self.assertFalse((root / "receipts" / "live-proposal-demo-trust-receipt.md").exists())

    def test_malformed_json_fails_closed_without_wal_or_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(
                core.TrueFoundryProposalClient,
                "from_env",
                return_value=_FakeTrueFoundryClient(exc=MalformedProposalError("invalid JSON")),
            ):
                summary = core.run_live_proposal_demo(tmp)

            self.assertEqual(summary["Status"], "BLOCKED")
            self.assertEqual(summary["reason"], "malformed model proposal after retry")
            self.assertIn("invalid JSON", summary["error"])
            root = Path(tmp)
            self.assertFalse((root / "wal" / "live-proposal-demo.jsonl").exists())
            self.assertFalse((root / "reports" / "live-proposal-demo-verifier-report.json").exists())
            self.assertFalse((root / "receipts" / "live-proposal-demo-trust-receipt.md").exists())

    def test_unknown_action_fails_closed_through_typed_gateway(self) -> None:
        proposal = _proposal(action="destroy_cluster", arguments={"cluster": "prod"})

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(
                core.TrueFoundryProposalClient,
                "from_env",
                return_value=_FakeTrueFoundryClient(proposal),
            ):
                summary = core.run_live_proposal_demo(tmp)

            self.assertEqual(summary["Status"], "PASS")
            self.assertEqual(summary["parsed_action"], "destroy_cluster")
            self.assertEqual(summary["drf_decision"], "DENY")
            self.assertEqual(summary["claim_status"], "HYPOTHESIS")
            self.assertEqual(summary["verifier_status"], "PASS")

            records = _read_wal(summary["wal_path"])
            first_payload = records[0]["payload"]
            self.assertEqual(first_payload["agent_proposal_source"], "LIVE_MODEL_OUTPUT")
            self.assertEqual(first_payload["parsed_proposal"]["action"], "destroy_cluster")
            self.assertEqual(first_payload["proposal"]["action"], "destroy_cluster")
            self.assertIsNone(first_payload["action_contract"])
            self.assertEqual(first_payload["authority"]["source"], "DRF_RULE")
            self.assertEqual(first_payload["authority"]["rule"], "NO_POLICY_RULE")
            self.assertEqual(first_payload["drf_decision"]["decision"], "DENY")
            self.assertEqual(first_payload["drf_decision"]["reason"], "NO_POLICY_RULE")
            self.assertFalse(first_payload["execution"]["executed"])
            self.assertIsNone(first_payload["tool_result"])

            report = verify_wal(summary["wal_path"], root=tmp)
            self.assertEqual(report.status, "PASS")

    def test_verifier_failure_blocks_trust_receipt(self) -> None:
        proposal = _proposal()
        forced_failure = VerificationReport(
            status="FAIL",
            records=1,
            errors=["forced verifier failure"],
            last_record_hash="abc",
        )

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(
                core.TrueFoundryProposalClient,
                "from_env",
                return_value=_FakeTrueFoundryClient(proposal),
            ), patch.object(core, "verify_wal", return_value=forced_failure):
                summary = core.run_live_proposal_demo(tmp)

            self.assertEqual(summary["Status"], "BLOCKED")
            self.assertEqual(summary["reason"], "verifier failed")
            self.assertEqual(summary["verifier_status"], "FAIL")
            root = Path(tmp)
            self.assertTrue((root / "wal" / "live-proposal-demo.jsonl").exists())
            self.assertTrue((root / "reports" / "live-proposal-demo-verifier-report.json").exists())
            self.assertFalse((root / "receipts" / "live-proposal-demo-trust-receipt.md").exists())

            report = json.loads(
                (root / "reports" / "live-proposal-demo-verifier-report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["errors"], ["forced verifier failure"])


if __name__ == "__main__":
    unittest.main()
