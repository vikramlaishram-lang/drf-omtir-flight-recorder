from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .verifier import verify_wal
from .wal import utc_now


BOUNDARY = (
    "This Trust Receipt explains one local DRF + OMTIR Flight Recorder run. "
    "It does not claim production deployment, cloud service readiness, universal MCP compatibility, "
    "external notarization, enterprise compliance, or adversarial security certification."
)


def _resilience_context(records: list[dict[str, Any]]) -> dict[str, Any]:
    for record in records:
        arguments = (
            record.get("payload", {})
            .get("proposal", {})
            .get("arguments", {})
        )
        if isinstance(arguments, dict):
            resilience = arguments.get("resilience")
            if isinstance(resilience, dict):
                return resilience
    return {}


def _governance_consequences(records: list[dict[str, Any]], root: Path) -> dict[str, Any]:
    quarantined_events: list[str] = []
    rejected_claim_events: list[str] = []
    confirmed_claim_events: list[str] = []
    pending_review_events: list[str] = []

    for record in records:
        payload = record.get("payload", {})
        event_id = str(payload.get("event_id", record.get("event_id", "")))
        evidence_packet = payload.get("evidence_packet") or {}
        if evidence_packet.get("has_quarantined"):
            quarantined_events.append(event_id)

        claim = payload.get("claim") or {}
        status = claim.get("status")
        if status == "REJECTED_HYPOTHESIS":
            rejected_claim_events.append(event_id)
        elif status == "CONFIRMED":
            confirmed_claim_events.append(event_id)

        drf = payload.get("drf_decision") or {}
        if drf.get("decision") == "REQUEST_REVIEW":
            pending_review_events.append(event_id)

    excluded = sorted(set(quarantined_events + rejected_claim_events))
    review_queue = root / "reports" / "resilient-demo-review-queue.jsonl"
    return {
        "quarantined_events": quarantined_events,
        "rejected_claim_events": rejected_claim_events,
        "confirmed_claim_events": confirmed_claim_events,
        "pending_review_events": pending_review_events,
        "excluded_from_confirmed_claim_set": excluded,
        "review_queue_path": review_queue.relative_to(root).as_posix() if review_queue.exists() else None,
    }


def build_trust_receipt(path: str | Path, *, root: str | Path = ".") -> dict[str, Any]:
    wal_path = Path(path)
    root_path = Path(root).resolve()
    records = [
        json.loads(line)
        for line in wal_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    decisions: dict[str, int] = {}
    claims: dict[str, int] = {}
    for record in records:
        payload = record.get("payload", {})
        drf = payload.get("drf_decision")
        if drf:
            decisions[drf["decision"]] = decisions.get(drf["decision"], 0) + 1
        claim = payload.get("claim")
        if claim:
            status = claim.get("status", "UNKNOWN")
            claims[status] = claims.get(status, 0) + 1
    verifier = verify_wal(wal_path, root=root)
    return {
        "receipt_version": "drf_omtir_flight_recorder_trust_receipt.v0.1",
        "generated_at": utc_now(),
        "wal_path": str(wal_path),
        "records": len(records),
        "last_record_hash": records[-1].get("record_hash") if records else None,
        "action_decisions": decisions,
        "claim_statuses": claims,
        "verifier": verifier.to_dict(),
        "resilience": _resilience_context(records),
        "governance_consequences": _governance_consequences(records, root_path),
        "boundary": BOUNDARY,
    }


def _join_events(events: list[str]) -> str:
    return ", ".join(events) if events else "none"


def render_markdown(receipt: dict[str, Any]) -> str:
    verifier = receipt["verifier"]
    resilience = receipt.get("resilience") or {}
    consequences = receipt.get("governance_consequences") or {}
    lines = [
            "# DRF + OMTIR Flight Recorder Trust Receipt v0.1",
            "",
            f"Generated: {receipt['generated_at']}",
            f"WAL: {receipt['wal_path']}",
            f"Records: {receipt['records']}",
            f"Last record hash: {receipt['last_record_hash']}",
            "",
            "## Action Decisions",
            "",
            *[f"- {key}: {value}" for key, value in sorted(receipt["action_decisions"].items())],
            "",
            "## Claim Statuses",
            "",
            *[f"- {key}: {value}" for key, value in sorted(receipt["claim_statuses"].items())],
            "",
            "## Verifier",
            "",
            f"- Status: {verifier['status']}",
            f"- Records checked: {verifier['records']}",
            f"- Errors: {json.dumps(verifier['errors'])}",
            "",
            "## Governance Consequences",
            "",
            "- Quarantined evidence excluded from confirmed claim set: "
            f"{_join_events(consequences.get('quarantined_events', []))}",
            "- Rejected hypotheses excluded from confirmed claim set: "
            f"{_join_events(consequences.get('rejected_claim_events', []))}",
            "- Confirmed claim events admitted: "
            f"{_join_events(consequences.get('confirmed_claim_events', []))}",
            "- Pending human review events: "
            f"{_join_events(consequences.get('pending_review_events', []))}",
            f"- Review queue: {consequences.get('review_queue_path') or 'none'}",
            "",
    ]
    if resilience:
        lines.extend(
            [
                "## Resilience Context",
                "",
                f"- Failure introduced: {resilience.get('failure_introduced', resilience.get('gateway_failure'))}",
                f"- Gateway failure: {resilience.get('gateway_failure')}",
                f"- Rate-limit rule: {resilience.get('rate_limit_rule')}",
                f"- Model route: {resilience.get('provider_route')} -> {resilience.get('model')}",
                f"- AWS Bedrock: {resilience.get('aws_bedrock')}",
                f"- First request: {resilience.get('first_request')}",
                f"- Second request: {resilience.get('second_request')}",
                "- TrueFoundry evidence: separate Request Trace screenshot showing the 429 rate-limit response.",
                "- Recovery path: unsafe action denied, weak result quarantined, "
                "unsupported claim rejected, evidence-linked claim confirmed, risky remediation routed to review.",
                "- Boundary: AWS Bedrock was not used in this bounded run. This does not claim AWS Bedrock "
                "validation, production reliability, universal failure recovery, enterprise certification, "
                "or all-agent safety.",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            receipt["boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def write_trust_receipt(path: str | Path, output: str | Path, *, root: str | Path = ".") -> dict[str, Any]:
    receipt = build_trust_receipt(path, root=root)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown(receipt), encoding="utf-8")
    return receipt
