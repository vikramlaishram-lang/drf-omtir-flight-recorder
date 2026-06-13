from __future__ import annotations

import hmac
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .wal import Wal, canonical_json, sha256_bytes, utc_now


ALLOWED_REVIEW_ACTIONS = {"APPROVE", "REJECT", "REQUEST_CHANGES"}
ALLOWED_REVIEWER_ROLES = {"governance_reviewer", "incident_commander"}
REVIEW_QUEUE_VERSION = "drf_omtir_review_queue.v0.2"
PENDING_REVIEW = "PENDING_HUMAN_REVIEW"
APPROVED_AFTER_REVIEW = "APPROVED_AFTER_REVIEW"
REJECTED_AFTER_REVIEW = "REJECTED_AFTER_REVIEW"


class ReviewValidationError(ValueError):
    """Raised when a reviewer action is missing required accountability data."""


@dataclass(frozen=True)
class ReviewerIdentity:
    reviewer_id: str
    reviewer_role: str


@dataclass(frozen=True)
class ReviewAction:
    target_event_id: str
    reviewer: ReviewerIdentity
    action: str
    comment: str | None = None
    review_reason: str | None = None


def _validate_review_action(review: ReviewAction) -> None:
    if not review.target_event_id.strip():
        raise ReviewValidationError("target_event_id is required")
    if not review.reviewer.reviewer_id.strip():
        raise ReviewValidationError("reviewer_id is required")
    if review.reviewer.reviewer_role not in ALLOWED_REVIEWER_ROLES:
        raise ReviewValidationError(
            f"unsupported reviewer role: {review.reviewer.reviewer_role}"
        )
    if review.action not in ALLOWED_REVIEW_ACTIONS:
        raise ReviewValidationError(f"unsupported review action: {review.action}")


def _review_mac_input(payload: dict[str, Any]) -> dict[str, Any]:
    mac_input = dict(payload)
    mac_input.pop("review_action_mac", None)
    mac_input.pop("sequence", None)
    mac_input.pop("timestamp", None)
    return mac_input


def _review_action_mac(payload: dict[str, Any], hmac_key: str | bytes) -> str:
    key = hmac_key if isinstance(hmac_key, bytes) else hmac_key.encode("utf-8")
    return hmac.new(key, canonical_json(_review_mac_input(payload)), "sha256").hexdigest()


def build_review_event(
    *,
    event_id: str,
    review: ReviewAction,
    policy_version: str | None = None,
    policy_hash: str | None = None,
    policy_source: str | None = None,
    hmac_key: str | bytes | None = None,
    key_id: str | None = None,
) -> dict[str, Any]:
    """Build a signed reviewer-action payload for proxy-level accountability."""
    _validate_review_action(review)

    payload: dict[str, Any] = {
        "event_id": event_id,
        "schema_version": "drf_omtir_reviewer_action.v0.1",
        "event_type": "reviewer_action",
        "target_event_id": review.target_event_id,
        "reviewer": {
            "reviewer_id": review.reviewer.reviewer_id,
            "reviewer_role": review.reviewer.reviewer_role,
        },
        "review": {
            "action": review.action,
            "target_event_id": review.target_event_id,
            "comment": review.comment,
            "review_reason": review.review_reason,
        },
        "authority": {
            "source": "OPERATOR_REVIEW",
            "origin": "OPERATOR_REVIEW/reviewer_action",
            "rule": "reviewer_action",
            "decision": review.action,
            "reason": review.review_reason or review.comment,
        },
        "execution": {
            "executed": False,
            "execution_status": "review_recorded",
        },
        "evidence_packet": {
            "evidence_sources": [],
            "has_structural": False,
            "has_unknown": False,
            "has_quarantined": False,
            "has_research_only": False,
        },
        "policy_version": policy_version,
        "policy_hash": policy_hash,
        "policy_source": policy_source,
    }

    if hmac_key is not None:
        payload["review_action_mac_key_id"] = key_id
        payload["review_action_mac"] = _review_action_mac(payload, hmac_key)

    return payload


def verify_review_action_mac(*, payload: dict[str, Any], hmac_key: str | bytes) -> bool:
    actual = payload.get("review_action_mac")
    if not isinstance(actual, str):
        return False
    expected = _review_action_mac(payload, hmac_key)
    return hmac.compare_digest(actual, expected)


def default_review_queue_path(root: Path) -> Path:
    return root / "reports" / "resilient-demo-review-queue.jsonl"


def default_review_wal_path(root: Path) -> Path:
    return root / "wal" / "resilient-demo.jsonl"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def _find_wal_record(wal_path: Path, event_id: str) -> dict[str, Any] | None:
    for record in _read_jsonl(wal_path):
        if record.get("event_id") == event_id:
            return record
    return None


def _payload_hash(record: dict[str, Any]) -> str:
    payload_hash = record.get("payload_hash")
    if payload_hash:
        return str(payload_hash)
    return sha256_bytes(canonical_json(record.get("payload", {})))


def create_review_item(
    *,
    root: Path,
    wal_path: Path,
    review_event: dict[str, Any],
    action: str,
    adapted_from_event_id: str | None,
    boundary: str,
    queue_path: Path | None = None,
) -> Path:
    record = _find_wal_record(wal_path, review_event["event_id"])
    proposal = (record or {}).get("payload", {}).get("proposal", {})
    item = {
        "queue_version": REVIEW_QUEUE_VERSION,
        "event_id": review_event["event_id"],
        "proposal_id": proposal.get("proposal_id") or review_event["event_id"],
        "action": action,
        "decision": review_event["decision"],
        "reason": review_event["reason"],
        "payload_hash": _payload_hash(record or {"payload": review_event}),
        "record_hash": (record or {}).get("record_hash") or review_event.get("record_hash"),
        "reviewer_status": PENDING_REVIEW,
        "reviewer": None,
        "status": PENDING_REVIEW,
        "adapted_from_event_id": adapted_from_event_id,
        "boundary": boundary,
    }
    queue = queue_path or default_review_queue_path(root)
    records = _read_jsonl(queue)
    records = [existing for existing in records if existing.get("event_id") != item["event_id"]]
    records.append(item)
    _write_jsonl(queue, records)
    return queue


def list_review_items(root: Path, queue_path: Path | None = None) -> dict[str, Any]:
    queue = queue_path or default_review_queue_path(root)
    return {
        "Status": "PASS",
        "queue_path": str(queue),
        "review_items": _read_jsonl(queue),
    }


def _blocked(reason: str, *, queue_path: Path, wal_path: Path) -> dict[str, Any]:
    return {
        "Status": "BLOCKED",
        "reason": reason,
        "queue_path": str(queue_path),
        "wal_path": str(wal_path),
    }


def _record_review_decision(
    *,
    root: Path,
    event_id: str,
    reviewer: str | None,
    reviewer_status: str,
    reason: str | None = None,
    queue_path: Path | None = None,
    wal_path: Path | None = None,
) -> dict[str, Any]:
    queue = queue_path or default_review_queue_path(root)
    wal_file = wal_path or default_review_wal_path(root)

    if not reviewer or not reviewer.strip():
        return _blocked("missing reviewer identity", queue_path=queue, wal_path=wal_file)
    if reviewer_status == REJECTED_AFTER_REVIEW and not (reason and reason.strip()):
        return _blocked("missing rejection reason", queue_path=queue, wal_path=wal_file)

    items = _read_jsonl(queue)
    matched_index = next((index for index, item in enumerate(items) if item.get("event_id") == event_id), None)
    if matched_index is None:
        return _blocked("unknown review event", queue_path=queue, wal_path=wal_file)

    item = items[matched_index]
    if item.get("reviewer_status") != PENDING_REVIEW:
        return _blocked("review event already resolved", queue_path=queue, wal_path=wal_file)

    reviewed_at = utc_now()
    wal = Wal(wal_file)
    review_event_id = wal.next_event_id()
    payload = {
        "event_id": review_event_id,
        "schema_version": "drf_omtir_operator_review_event.v0.1",
        "event_type": "review",
        "review": {
            "reviewed_event_id": event_id,
            "proposal_id": item.get("proposal_id"),
            "action": item.get("action"),
            "prior_decision": item.get("decision"),
            "prior_reason": item.get("reason"),
            "payload_hash": item.get("payload_hash"),
            "reviewer": reviewer.strip(),
            "reviewer_status": reviewer_status,
            "review_reason": reason,
            "reviewed_at": reviewed_at,
        },
        "authority": {
            "source": "OPERATOR_REVIEW",
            "origin": "OPERATOR_REVIEW/minimum_operator_workflow",
            "rule": "minimum_operator_workflow",
            "decision": reviewer_status,
            "reason": reason or "Operator approved pending review item.",
        },
        "execution": {
            "executed": False,
            "execution_status": "review_recorded",
        },
        "adaptation": {
            "is_adaptive_retry": True,
            "adapted_from_event_id": event_id,
            "adaptation_result": reviewer_status,
        },
        "evidence_packet": {
            "evidence_sources": [],
            "has_structural": False,
            "has_unknown": False,
            "has_quarantined": False,
            "has_research_only": False,
        },
    }
    review_wal_event = wal.append(payload)

    item.update(
        {
            "reviewer_status": reviewer_status,
            "status": reviewer_status,
            "reviewer": reviewer.strip(),
            "review_reason": reason,
            "reviewed_at": reviewed_at,
            "review_wal_event_id": review_wal_event["event_id"],
            "review_record_hash": review_wal_event["record_hash"],
        }
    )
    items[matched_index] = item
    _write_jsonl(queue, items)

    return {
        "Status": "PASS",
        "event_id": event_id,
        "reviewer_status": reviewer_status,
        "review_wal_event_id": review_wal_event["event_id"],
        "review_record_hash": review_wal_event["record_hash"],
        "queue_path": str(queue),
        "wal_path": str(wal_file),
    }


def approve_review(
    event_id: str,
    *,
    reviewer: str | None,
    root: Path,
    queue_path: Path | None = None,
    wal_path: Path | None = None,
) -> dict[str, Any]:
    return _record_review_decision(
        root=root,
        event_id=event_id,
        reviewer=reviewer,
        reviewer_status=APPROVED_AFTER_REVIEW,
        queue_path=queue_path,
        wal_path=wal_path,
    )


def reject_review(
    event_id: str,
    *,
    reviewer: str | None,
    reason: str | None,
    root: Path,
    queue_path: Path | None = None,
    wal_path: Path | None = None,
) -> dict[str, Any]:
    return _record_review_decision(
        root=root,
        event_id=event_id,
        reviewer=reviewer,
        reviewer_status=REJECTED_AFTER_REVIEW,
        reason=reason,
        queue_path=queue_path,
        wal_path=wal_path,
    )
