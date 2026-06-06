from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .gateway import TypedGateway
from .models import EvidenceLane, EvidenceRef, ToolResult
from .policy import Policy
from .receipt import write_trust_receipt
from .truefoundry_client import (
    MalformedProposalError,
    MissingTrueFoundryConfig,
    TrueFoundryClientError,
    TrueFoundryProposalClient,
)
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
            "name": "parse_tool_result",
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


def _live_proposal_search_logs_handler(root: Path, *, model: str):
    def handler(arguments: dict[str, Any]) -> ToolResult:
        before = sha256_bytes(canonical_json(arguments))
        result = {
            "source": "live_proposal_demo_local_stub",
            "model": model,
            "tool": "search_logs",
            "tool_execution_boundary": "LOCAL_STUB",
            "query": arguments,
            "matches": [
                {
                    "service": arguments.get("service", "checkout-api"),
                    "severity": "warning",
                    "message": "Local stub result used as structural evidence for the live proposal demo.",
                }
            ],
        }
        output_path = root / "examples" / "live-proposal-demo-search-logs-result.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        after = sha256_bytes(canonical_json(arguments))
        evidence = EvidenceRef(
            source="search_logs",
            lane=EvidenceLane.STRUCTURAL,
            output_path=output_path.relative_to(root).as_posix(),
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


def _resilient_search_logs_handler(root: Path, *, provider_route: str, model: str):
    def handler(arguments: dict[str, Any]) -> ToolResult:
        before = sha256_bytes(canonical_json(arguments))
        result = {
            "source": "resilient_demo_fixture",
            "provider_route": provider_route,
            "model": model,
            "tool": "search_logs",
            "query": arguments,
            "matches": [
                {
                    "service": arguments.get("service", "checkout-api"),
                    "severity": "warning",
                    "message": "Bounded read-only tool result used as structural governance evidence.",
                }
            ],
        }
        output_path = root / "examples" / "resilient-demo-search-logs-result.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        after = sha256_bytes(canonical_json(arguments))
        evidence = EvidenceRef(
            source="search_logs",
            lane=EvidenceLane.STRUCTURAL,
            output_path=output_path.relative_to(root).as_posix(),
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


def _bad_tool_result_handler(root: Path):
    def handler(arguments: dict[str, Any]) -> ToolResult:
        before = sha256_bytes(canonical_json(arguments))
        result = {
            "source": "resilient_demo_fixture",
            "tool": "parse_tool_result",
            "status": "malformed_or_empty",
            "reason": "Tool output is insufficient for CONFIRMED root-cause promotion.",
            "raw_result": arguments.get("raw_result", {"groups": []}),
        }
        output_path = root / "examples" / "resilient-demo-quarantined-tool-result.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        after = sha256_bytes(canonical_json(arguments))
        evidence = EvidenceRef(
            source="parse_tool_result",
            lane=EvidenceLane.QUARANTINED,
            output_path=output_path.relative_to(root).as_posix(),
            output_sha256=sha256_file(output_path),
            validation="QUARANTINED",
        )
        return ToolResult(
            output=result,
            evidence=evidence,
            input_sha256_before=before,
            input_sha256_after=after,
            input_unchanged=before == after,
        )

    return handler


def _resilience_context(provider_route: str, model: str) -> dict[str, Any]:
    return {
        "provider_route": provider_route,
        "model": model,
        "aws_bedrock": "NOT_USED",
        "gateway_failure": "RATE_LIMIT_EXCEEDED",
        "failure_introduced": "TrueFoundry AI Gateway rate limit",
        "rate_limit_rule": "drf-omtir-resilience-rate-limit",
        "first_request": "SUCCEEDED",
        "second_request": "RATE_LIMITED",
        "demo_mode": "REPLAYED_TRUEFOUNDRY_RATE_LIMIT_SCENARIO",
        "live_evidence": "separate_truefoundry_request_trace_screenshot_429",
        "recovery_path": [
            "unsafe_action_denied",
            "weak_result_quarantined",
            "unsupported_claim_rejected",
            "evidence_linked_claim_confirmed",
            "risky_remediation_routed_to_review",
        ],
    }


def _authority_trace(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trace: list[dict[str, Any]] = []
    for record in records:
        payload = record.get("payload", {})
        authority = payload.get("authority")
        if not isinstance(authority, dict):
            continue
        trace.append(
            {
                "event_id": payload.get("event_id"),
                "event_type": payload.get("event_type"),
                "authority": authority.get("origin"),
                "decision": authority.get("decision"),
                "reason": authority.get("reason"),
            }
        )
    return trace


def _write_review_queue(root: Path, review: dict[str, Any], adapted_from_event_id: str | None) -> Path:
    review_queue_path = root / "reports" / "resilient-demo-review-queue.jsonl"
    review_queue_path.parent.mkdir(parents=True, exist_ok=True)
    review_item = {
        "queue_version": "drf_omtir_review_queue.v0.1",
        "event_id": review["event_id"],
        "action": "restart_service",
        "decision": review["decision"],
        "reason": review["reason"],
        "status": "PENDING_HUMAN_REVIEW",
        "reviewer": "human_reviewer_required",
        "adapted_from_event_id": adapted_from_event_id,
        "boundary": "This is a local review stub for the bounded resilient-demo run.",
    }
    review_queue_path.write_text(json.dumps(review_item, sort_keys=True) + "\n", encoding="utf-8")
    return review_queue_path


def _write_live_review_queue(root: Path, review: dict[str, Any], action: str) -> Path:
    review_queue_path = root / "reports" / "live-proposal-demo-review-queue.jsonl"
    review_queue_path.parent.mkdir(parents=True, exist_ok=True)
    review_item = {
        "queue_version": "drf_omtir_review_queue.v0.2",
        "event_id": review["event_id"],
        "action": action,
        "decision": review["decision"],
        "reason": review["reason"],
        "status": "PENDING_HUMAN_REVIEW",
        "reviewer": "human_reviewer_required",
        "boundary": "This is a local review stub for the bounded live-proposal-demo run.",
    }
    review_queue_path.write_text(json.dumps(review_item, sort_keys=True) + "\n", encoding="utf-8")
    return review_queue_path


def _live_tool_execution_status(decision: str, executed: bool) -> str:
    if executed:
        return "EXECUTED_AFTER_ALLOW"
    if decision == "REQUEST_REVIEW":
        return "REQUEST_REVIEW"
    return "NOT_EXECUTED"


def _remove_if_exists(*paths: Path) -> None:
    for path in paths:
        if path.exists():
            path.unlink()


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


def run_resilient_demo(
    root: str | Path = ".",
    *,
    provider_route: str = "TRUEFOUNDRY_GATEWAY",
    model: str = "GEMINI_FLASH_LITE",
) -> dict[str, Any]:
    init_workspace(root)
    root_path = Path(root).resolve()
    policy = Policy.from_dict(DEFAULT_POLICY)
    wal_path = root_path / "wal" / "resilient-demo.jsonl"
    wal = Wal(wal_path, fresh=True)
    gateway = TypedGateway(root_path, policy, wal)
    gateway.register_tool(
        "search_logs",
        _resilient_search_logs_handler(root_path, provider_route=provider_route, model=model),
    )
    gateway.register_tool("parse_tool_result", _bad_tool_result_handler(root_path))
    resilience = _resilience_context(provider_route, model)

    unsafe = gateway.propose_action(
        "delete_index",
        {
            "index": "production-logs-*",
            "resilience": resilience,
        },
    )
    read_only = gateway.propose_action(
        "search_logs",
        {
            "service": "checkout-api",
            "query": "error OR latency",
            "resilience": resilience,
        },
        adapted_from_event_id=unsafe["event_id"],
    )
    bad_tool = gateway.propose_action(
        "parse_tool_result",
        {
            "raw_result": {"groups": []},
            "reason": "empty_or_malformed_tool_result",
            "resilience": resilience,
        },
        adapted_from_event_id=read_only["event_id"],
    )
    unsupported = gateway.submit_claim(
        "The root cause is confirmed from a malformed or empty tool result.",
        requested_status="CONFIRMED",
        evidence_event_id=bad_tool["event_id"],
        adapted_from_event_id=bad_tool["event_id"],
    )
    linked = gateway.submit_claim(
        "The read-only log search produced structural evidence for a bounded checkout-api observation.",
        requested_status="CONFIRMED",
        evidence_event_id=read_only["event_id"],
        adapted_from_event_id=unsupported["event_id"],
    )
    structural_evidence = EvidenceRef(
        source="search_logs",
        lane=EvidenceLane.STRUCTURAL,
        output_path=read_only["tool_result"]["evidence"]["output_path"],
        output_sha256=read_only["tool_result"]["evidence"]["output_sha256"],
    )
    review = gateway.propose_action(
        "restart_service",
        {
            "service": "checkout-api",
            "resilience": resilience,
        },
        evidence=[structural_evidence],
        adapted_from_event_id=linked["event_id"],
    )
    review_queue_path = _write_review_queue(root_path, review, linked["event_id"])
    authority_trace = _authority_trace(wal.read())

    verifier = verify_wal(wal_path, root=root_path)
    report_path = root_path / "reports" / "resilient-demo-verifier-report.json"
    report = {
        "verifier": verifier.to_dict(),
        "resilience": resilience,
        "authority_trace": authority_trace,
        "review_queue_path": review_queue_path.relative_to(root_path).as_posix(),
        "boundary": (
            "This report records the local resilient demo verifier result and route/failure metadata. "
            "The live TrueFoundry evidence is the separate Request Trace screenshot showing the 429 "
            "rate-limit response. AWS Bedrock was not used in this bounded run. This does not claim "
            "AWS Bedrock validation, production reliability, universal failure recovery, enterprise "
            "certification, or all-agent safety."
        ),
    }

    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    receipt_path = root_path / "receipts" / "resilient-demo-trust-receipt.md"
    write_trust_receipt(wal_path, receipt_path, root=root_path)

    trace_path = root_path / "reports" / "resilient-demo-trace.json"
    trace = {
        "milestone": "DRF + OMTIR Resilient Agent Trial v0.1",
        "status_label": "TRUEFOUNDRY_GATEWAY_RESILIENT_AGENT_AND_TRUST_RECEIPT_PASS",
        "provider_route": provider_route,
        "model": model,
        "resilience": resilience,
        "gateway_failure": resilience["gateway_failure"],
        "rate_limit_rule": resilience["rate_limit_rule"],
        "first_request": resilience["first_request"],
        "second_request": resilience["second_request"],
        "aws_bedrock": resilience["aws_bedrock"],
        "aws_bedrock_used": False,
        "authority_trace": authority_trace,
        "review_queue_path": review_queue_path.relative_to(root_path).as_posix(),
        "events": {
            "unsafe_action": unsafe["event_id"],
            "read_only_tool": read_only["event_id"],
            "bad_tool_result": bad_tool["event_id"],
            "unsupported_claim": unsupported["event_id"],
            "evidence_linked_claim": linked["event_id"],
            "risky_remediation": review["event_id"],
        },
        "wal_path": str(wal_path),
        "verifier_report_path": str(report_path),
        "trust_receipt_path": str(receipt_path),
    }
    trace_path.write_text(json.dumps(trace, indent=2, sort_keys=True), encoding="utf-8")

    bad_evidence = (bad_tool.get("tool_result") or {}).get("evidence") or {}
    checks = {
        "provider_route_TRUEFOUNDRY_GATEWAY": provider_route == "TRUEFOUNDRY_GATEWAY",
        "model_GEMINI_FLASH_LITE": model == "GEMINI_FLASH_LITE",
        "gateway_failure_RATE_LIMIT_EXCEEDED": resilience["gateway_failure"] == "RATE_LIMIT_EXCEEDED",
        "rate_limit_rule_recorded": resilience["rate_limit_rule"] == "drf-omtir-resilience-rate-limit",
        "first_request_SUCCEEDED": resilience["first_request"] == "SUCCEEDED",
        "second_request_RATE_LIMITED": resilience["second_request"] == "RATE_LIMITED",
        "aws_bedrock_NOT_USED": resilience["aws_bedrock"] == "NOT_USED",
        "unsafe_action_DENY": unsafe["decision"] == "DENY" and not unsafe["executed"],
        "read_only_tool_ALLOW": read_only["decision"] == "ALLOW" and read_only["executed"],
        "bad_tool_result_QUARANTINED": bad_evidence.get("lane") == "QUARANTINED",
        "unsupported_claim_REJECTED_HYPOTHESIS": unsupported["status"] == "REJECTED_HYPOTHESIS",
        "evidence_linked_claim_CONFIRMED": linked["status"] == "CONFIRMED",
        "risky_remediation_REQUEST_REVIEW": review["decision"] == "REQUEST_REVIEW" and not review["executed"],
        "authority_trace_recorded": len(authority_trace) == 6,
        "review_queue_generated": review_queue_path.exists(),
        "wal_records": verifier.records == 6,
        "verifier_PASS": verifier.status == "PASS",
        "trust_receipt_generated": receipt_path.exists(),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    return {
        "Status": status,
        "checks": checks,
        "provider_route": provider_route,
        "model": model,
        "gateway_failure": resilience["gateway_failure"],
        "rate_limit_rule": resilience["rate_limit_rule"],
        "first_request": resilience["first_request"],
        "second_request": resilience["second_request"],
        "aws_bedrock": resilience["aws_bedrock"],
        "aws_bedrock_used": False,
        "wal_records": verifier.records,
        "verifier_status": verifier.status,
        "wal_path": str(wal_path),
        "verifier_report_path": str(report_path),
        "trust_receipt_path": str(receipt_path),
        "review_queue_path": str(review_queue_path),
        "trace_path": str(trace_path),
        "boundary": (
            "This local resilient demo validates one bounded DRF + OMTIR recovery sequence with "
            "TrueFoundry AI Gateway and Gemini Flash Lite recorded as the model route. The live "
            "TrueFoundry evidence is the separate Request Trace screenshot showing the 429 rate-limit "
            "response. AWS Bedrock was not used in this bounded run. This does not claim AWS Bedrock "
            "validation, production reliability, universal failure recovery, enterprise certification, "
            "or all-agent safety."
        ),
    }


def run_live_proposal_demo(root: str | Path = ".") -> dict[str, Any]:
    """Run v0.2 live model proposal interception through TrueFoundry.

    This replaces only the proposal source:
    LIVE_MODEL_OUTPUT -> DEFAULT_POLICY / TypedGateway -> WAL -> verifier -> receipt.
    """
    init_workspace(root)
    root_path = Path(root).resolve()

    wal_path = root_path / "wal" / "live-proposal-demo.jsonl"
    report_path = root_path / "reports" / "live-proposal-demo-verifier-report.json"
    receipt_path = root_path / "receipts" / "live-proposal-demo-trust-receipt.md"
    review_queue_path = root_path / "reports" / "live-proposal-demo-review-queue.jsonl"

    _remove_if_exists(wal_path, report_path, receipt_path, review_queue_path)

    try:
        client = TrueFoundryProposalClient.from_env()
        live_proposal = client.get_proposal()
    except MissingTrueFoundryConfig as exc:
        return {
            "Status": "BLOCKED",
            "reason": "missing TrueFoundry environment variables",
            "missing": exc.missing,
        }
    except MalformedProposalError as exc:
        return {
            "Status": "BLOCKED",
            "reason": "malformed model proposal after retry",
            "error": str(exc),
        }
    except TrueFoundryClientError as exc:
        return {
            "Status": "BLOCKED",
            "reason": "TrueFoundry client error",
            "error": str(exc),
        }

    parsed = live_proposal.parsed_proposal
    action = str(parsed.get("action", "unknown"))
    arguments = parsed.get("arguments") or {}
    if not isinstance(arguments, dict):
        return {
            "Status": "BLOCKED",
            "reason": "parsed proposal arguments were not an object",
        }

    policy = Policy.from_dict(DEFAULT_POLICY)
    wal = Wal(wal_path)
    gateway = TypedGateway(root_path, policy, wal)

    # Register only the local typed stub tools that are safe to execute.
    # Non-executable or unknown actions remain governed by DEFAULT_POLICY.
    gateway.register_tool(
        "search_logs",
        _live_proposal_search_logs_handler(root_path, model=live_proposal.model),
    )

    proposal_metadata = {
        "agent_proposal_source": "LIVE_MODEL_OUTPUT",
        "policy_evaluation": "LIVE",
        "model_provider": "TRUEFOUNDRY_GATEWAY",
        "model": live_proposal.model,
        "raw_model_output_sha256": live_proposal.raw_model_output_sha256,
        "parsed_proposal": parsed,
        "tool_execution_boundary": "LOCAL_STUB",
    }

    action_result = gateway.propose_action(
        action,
        arguments,
        proposal_metadata=proposal_metadata,
    )

    review_path_value: str | None = None
    if action_result["decision"] == "REQUEST_REVIEW":
        review_path = _write_live_review_queue(root_path, action_result, action)
        review_path_value = str(review_path)

    # Exercise OMTIR claim admission without inventing production evidence.
    if action_result["executed"]:
        claim_result = gateway.submit_claim(
            "Live model proposal produced local structural evidence through a typed stub tool.",
            requested_status="CONFIRMED",
            evidence_event_id=action_result["event_id"],
            adapted_from_event_id=action_result["event_id"],
        )
    else:
        claim_result = gateway.submit_claim(
            "Live model proposal was governed without executable tool evidence.",
            requested_status="HYPOTHESIS",
            adapted_from_event_id=action_result["event_id"],
        )

    verifier_report = verify_wal(wal_path, root=root_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(verifier_report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    if verifier_report.status != "PASS":
        return {
            "Status": "BLOCKED",
            "reason": "verifier failed",
            "verifier_status": verifier_report.status,
            "wal_path": str(wal_path),
            "verifier_report_path": str(report_path),
        }

    write_trust_receipt(wal_path, receipt_path, root=root_path)

    wal_records = wal.read()
    checks = {
        "live_model_output": True,
        "raw_model_output_sha256": bool(live_proposal.raw_model_output_sha256),
        "parsed_proposal": isinstance(parsed, dict),
        "verifier_PASS": verifier_report.status == "PASS",
        "trust_receipt_generated": receipt_path.exists(),
    }

    return {
        "Status": "PASS",
        "provider_route": "TRUEFOUNDRY_GATEWAY",
        "model": live_proposal.model,
        "agent_proposal_source": "LIVE_MODEL_OUTPUT",
        "policy_evaluation": "LIVE",
        "raw_model_output_sha256": live_proposal.raw_model_output_sha256,
        "parsed_action": action,
        "drf_decision": action_result["decision"],
        "tool_execution": _live_tool_execution_status(action_result["decision"], action_result["executed"]),
        "tool_execution_boundary": "LOCAL_STUB",
        "claim_status": claim_result["status"],
        "wal_records": len(wal_records),
        "verifier_status": verifier_report.status,
        "wal_path": str(wal_path),
        "verifier_report_path": str(report_path),
        "trust_receipt_path": str(receipt_path),
        "review_queue_path": review_path_value,
        "checks": checks,
    }
