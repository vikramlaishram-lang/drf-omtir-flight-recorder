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


def build_trust_receipt(path: str | Path, *, root: str | Path = ".") -> dict[str, Any]:
    wal_path = Path(path)
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
        "boundary": BOUNDARY,
    }


def render_markdown(receipt: dict[str, Any]) -> str:
    verifier = receipt["verifier"]
    return "\n".join(
        [
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
            "## Boundary",
            "",
            receipt["boundary"],
            "",
        ]
    )


def write_trust_receipt(path: str | Path, output: str | Path, *, root: str | Path = ".") -> dict[str, Any]:
    receipt = build_trust_receipt(path, root=root)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown(receipt), encoding="utf-8")
    return receipt
