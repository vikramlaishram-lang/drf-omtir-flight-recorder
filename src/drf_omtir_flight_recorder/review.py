from __future__ import annotations

import datetime as dt
import hmac
from dataclasses import dataclass
from typing import Any

from .wal import canonical_json, hmac_sha256_bytes


REVIEW_EVENT_SCHEMA_VERSION = "drf_omtir_review_event.v0.1"

REVIEW_ACTIONS = {
    "APPROVE",
    "REJECT",
    "REQUEST_CHANGES",
    "HALT",
    "COMMENT",
}

REVIEW_ROLES = {
    "governance_reviewer",
    "security_reviewer",
    "operator",
    "maintainer",
    "auditor",
}


class ReviewValidationError(ValueError):
    """Raised when a reviewer action lacks accountable metadata."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat() + "Z"


@dataclass(frozen=True)
class ReviewerIdentity:
    reviewer_id: str
    reviewer_role: str
    auth_method: str = "local_developer_assertion"

    def validate(self) -> None:
        if not self.reviewer_id or not self.reviewer_id.strip():
            raise ReviewValidationError("reviewer_id is required")

        if not self.reviewer_role or not self.reviewer_role.strip():
            raise ReviewValidationError("reviewer_role is required")

        if self.reviewer_role not in REVIEW_ROLES:
            raise ReviewValidationError(
                f"reviewer_role is not allowed: {self.reviewer_role}"
            )

        if not self.auth_method or not self.auth_method.strip():
            raise ReviewValidationError("auth_method is required")


@dataclass(frozen=True)
class ReviewAction:
    target_event_id: str
    reviewer: ReviewerIdentity
    action: str
    comment: str | None = None
    review_reason: str | None = None
    reviewer_signature: str | None = None

    def validate(self) -> None:
        if not self.target_event_id or not self.target_event_id.strip():
            raise ReviewValidationError("target_event_id is required")

        self.reviewer.validate()

        if self.action not in REVIEW_ACTIONS:
            raise ReviewValidationError(f"review action is not allowed: {self.action}")


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
    """Build an accountable reviewer-action event for WAL append.

    The reviewer_signature field is optional for v0.1.5 local MVP mode.
    If hmac_key is supplied, this function adds review_action_mac.
    """

    if not event_id or not event_id.strip():
        raise ReviewValidationError("event_id is required")

    review.validate()

    payload: dict[str, Any] = {
        "schema_version": REVIEW_EVENT_SCHEMA_VERSION,
        "event_id": event_id,
        "event_type": "reviewer_action",
        "timestamp": utc_now(),
        "target_event_id": review.target_event_id,
        "reviewer": {
            "reviewer_id": review.reviewer.reviewer_id,
            "reviewer_role": review.reviewer.reviewer_role,
            "auth_method": review.reviewer.auth_method,
        },
        "review": {
            "action": review.action,
            "comment": review.comment,
            "review_reason": review.review_reason,
            "reviewer_signature": review.reviewer_signature,
        },
        "policy_version": policy_version,
        "policy_hash": policy_hash,
        "policy_source": policy_source,
        "accountability": {
            "reviewer_identity_required": True,
            "target_event_link_required": True,
            "review_action_recorded": True,
        },
    }

    if hmac_key is not None:
        key_bytes = hmac_key if isinstance(hmac_key, bytes) else hmac_key.encode("utf-8")
        mac_input = {
            "target_event_id": payload["target_event_id"],
            "reviewer": payload["reviewer"],
            "review": payload["review"],
            "policy_version": policy_version,
            "policy_hash": policy_hash,
        }

        payload["review_action_mac"] = hmac_sha256_bytes(
            key_bytes,
            canonical_json(mac_input),
        )
        payload["review_action_mac_key_id"] = key_id or "local-review-key"

    return payload


def verify_review_action_mac(
    *,
    payload: dict[str, Any],
    hmac_key: str | bytes,
) -> bool:
    """Verify optional reviewer-action MAC if present."""

    expected_mac = payload.get("review_action_mac")

    if not expected_mac:
        return False

    key_bytes = hmac_key if isinstance(hmac_key, bytes) else hmac_key.encode("utf-8")

    mac_input = {
        "target_event_id": payload.get("target_event_id"),
        "reviewer": payload.get("reviewer"),
        "review": payload.get("review"),
        "policy_version": payload.get("policy_version"),
        "policy_hash": payload.get("policy_hash"),
    }

    actual_mac = hmac_sha256_bytes(key_bytes, canonical_json(mac_input))
    return hmac.compare_digest(str(expected_mac), actual_mac)
