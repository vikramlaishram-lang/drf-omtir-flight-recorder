from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .gateway import TypedGateway
from .models import EvidenceLane, EvidenceRef, ToolResult
from .policy import Policy
from .receipt import write_trust_receipt
from .verifier import verify_wal
from .wal import Wal, canonical_json, sha256_bytes, sha256_file


DEFAULT_POLICY: dict[str, Any] = {
    "policy_version": "drf-omtir-flight-recorder-v0.1",
    "unknown_action_decision": "DENY",
    "actions": [
        {
            "name": "delete_index",
            "effect": "DESTRUCTIVE",
            "decision": "DENY",
            "required_evidence_lanes": [],
            "executable": False,
        },
        {
            "name": "search_logs",
            "effect": "READ_ONLY",
            "decision": "ALLOW",
            "required_evidence_lanes": [],
            "executable": True,
        },
        {
            "name": "restart_service",
            "effect": "STATE_CHANGING",
            "decision": "REQUEST_REVIEW",
            "required_evidence_lanes": ["STRUCTURAL"],
            "executable": False,
        },
    ],
    "proxy": {
        "wal_path": "wal/proxy.jsonl",
        "redact_keys": ["authorization", "api_key", "token", "password", "secret"],
    },
}


def init_workspace(root: str | Path = ".", *, force: bool = False) -> dict[str, str]:
    root_path = Path(root).resolve()
    root_path.mkdir(parents=True, exist_ok=True)
    for name in ["wal", "receipts", "examples", "reports"]:
        (root_path / name).mkdir(parents=True, exist_ok=True)
    policy_path = root_path / "drf-omtir.yaml"
    if force or not policy_path.exists():
        policy_path.write_text(json.dumps(DEFAULT_POLICY, indent=2), encoding="utf-8")
    return {
        "root": str(root_path),
        "policy": str(policy_path),
        "wal": str(root_path / "wal"),
        "receipts": str(root_path / "receipts"),
        "examples": str(root_path / "examples"),
    }


def _search_logs_handler(root: Path):
    def handler(arguments: dict[str, Any]) -> ToolResult:
        before = sha256_bytes(canonical_json(arguments))
        result = {
            "source": "local_demo_fixture",
            "tool": "search_logs",
            "query": arguments,
            "matches": [
                {
                    "service": "checkout-api",
                    "severity": "warning",
                    "message": "Synthetic demo log result for governance evidence.",
                }
            ],
        }
        output_path = root / "examples" / "demo-search-logs-result.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        after = sha256_bytes(canonical_json(arguments))
        relative_output = output_path.relative_to(root).as_posix()
        evidence = EvidenceRef(
            source="search_logs",
            lane=EvidenceLane.STRUCTURAL,
            output_path=relative_output,
            output_sha256=sha256_file(output_path),
            validation="VALID",
        )
        return ToolResult(
            output=result,
            evidence=evidence,
            input_sha256_before=before,
            input_sha256_after=after,
            input_unchanged=before == after,
        )

    return handler


def run_demo(root: str | Path = ".", policy_path: str | Path | None = None) -> dict[str, Any]:
    init_workspace(root)
    root_path = Path(root).resolve()
    policy_file = Path(policy_path) if policy_path else root_path / "drf-omtir.yaml"
    policy = Policy.load(policy_file)
    wal_path = root_path / "wal" / "demo.jsonl"
    wal = Wal(wal_path, fresh=True)
    gateway = TypedGateway(root_path, policy, wal)
    gateway.register_tool("search_logs", _search_logs_handler(root_path))

    deleted = gateway.propose_action("delete_index", {"index": "production-logs-*"})
    searched = gateway.propose_action(
        "search_logs",
        {"service": "checkout-api", "query": "error OR latency"},
        adapted_from_event_id=deleted["event_id"],
    )
    unsupported = gateway.submit_claim(
        "The outage root cause is confirmed by the model alone.",
        requested_status="CONFIRMED",
    )
    linked = gateway.submit_claim(
        "Search logs returned structural evidence for a bounded checkout-api observation.",
        requested_status="CONFIRMED",
        evidence_event_id=searched["event_id"],
        adapted_from_event_id=unsupported["event_id"],
    )
    evidence = EvidenceRef(
        source="search_logs",
        lane=EvidenceLane.STRUCTURAL,
        output_path=searched["tool_result"]["evidence"]["output_path"],
        output_sha256=searched["tool_result"]["evidence"]["output_sha256"],
    )
    review = gateway.propose_action(
        "restart_service",
        {"service": "checkout-api"},
        evidence=[evidence],
        adapted_from_event_id=linked["event_id"],
    )

    verifier = verify_wal(wal_path, root=root_path)
    report_path = root_path / "reports" / "demo-verifier-report.json"
    report_path.write_text(json.dumps(verifier.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    receipt_path = root_path / "receipts" / "demo-trust-receipt.md"
    write_trust_receipt(wal_path, receipt_path, root=root_path)

    checks = {
        "delete_index_DENY": deleted["decision"] == "DENY" and not deleted["executed"],
        "search_logs_ALLOW": searched["decision"] == "ALLOW" and searched["executed"],
        "unsupported_CONFIRMED_REJECTED_HYPOTHESIS": unsupported["status"] == "REJECTED_HYPOTHESIS",
        "evidence_linked_claim_CONFIRMED": linked["status"] == "CONFIRMED",
        "restart_service_REQUEST_REVIEW": review["decision"] == "REQUEST_REVIEW" and not review["executed"],
        "wal_records": verifier.records == 5,
        "verifier_PASS": verifier.status == "PASS",
        "trust_receipt_generated": receipt_path.exists(),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    return {
        "Status": status,
        "checks": checks,
        "wal_path": str(wal_path),
        "verifier_report_path": str(report_path),
        "trust_receipt_path": str(receipt_path),
        "boundary": (
            "This local demo proves the v0.1 Flight Recorder governance path only. "
            "It does not claim production deployment, cloud service readiness, universal MCP compatibility, "
            "external notarization, enterprise compliance, or adversarial security certification."
        ),
    }
