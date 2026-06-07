from __future__ import annotations

from pathlib import Path

import pytest

from drf_omtir_flight_recorder.core import init_workspace
from drf_omtir_flight_recorder.policy import Policy
from drf_omtir_flight_recorder.proxy import GovernanceProxy
from drf_omtir_flight_recorder.review import (
    ReviewAction,
    ReviewValidationError,
    ReviewerIdentity,
    build_review_event,
    verify_review_action_mac,
)
from drf_omtir_flight_recorder.verifier import verify_wal
from drf_omtir_flight_recorder.wal import Wal


class FakeTransport:
    def request(self, message: dict) -> dict:
        return {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": {"ok": True},
        }

    def notify(self, message: dict) -> None:
        return None


def test_build_review_event_requires_reviewer_identity():
    review = ReviewAction(
        target_event_id="evt_000001",
        reviewer=ReviewerIdentity(
            reviewer_id="",
            reviewer_role="governance_reviewer",
        ),
        action="APPROVE",
        comment="Approved for bounded retry.",
    )

    with pytest.raises(ReviewValidationError):
        build_review_event(event_id="evt_000002", review=review)


def test_build_review_event_rejects_unknown_role():
    review = ReviewAction(
        target_event_id="evt_000001",
        reviewer=ReviewerIdentity(
            reviewer_id="reviewer-1",
            reviewer_role="super_admin",
        ),
        action="APPROVE",
    )

    with pytest.raises(ReviewValidationError):
        build_review_event(event_id="evt_000002", review=review)


def test_build_review_event_rejects_unknown_action():
    review = ReviewAction(
        target_event_id="evt_000001",
        reviewer=ReviewerIdentity(
            reviewer_id="reviewer-1",
            reviewer_role="governance_reviewer",
        ),
        action="AUTO_EXECUTE",
    )

    with pytest.raises(ReviewValidationError):
        build_review_event(event_id="evt_000002", review=review)


def test_review_action_mac_verifies():
    review = ReviewAction(
        target_event_id="evt_000001",
        reviewer=ReviewerIdentity(
            reviewer_id="reviewer-1",
            reviewer_role="governance_reviewer",
        ),
        action="APPROVE",
        comment="Approved after evidence check.",
    )

    payload = build_review_event(
        event_id="evt_000002",
        review=review,
        policy_version="policy-v1",
        policy_hash="abc123",
        hmac_key="review-secret",
        key_id="review-key-v1",
    )

    assert payload["review_action_mac_key_id"] == "review-key-v1"
    assert verify_review_action_mac(payload=payload, hmac_key="review-secret") is True
    assert verify_review_action_mac(payload=payload, hmac_key="wrong-secret") is False


def test_proxy_appends_reviewer_action_to_wal(tmp_path: Path):
    init_workspace(tmp_path)
    policy_path = tmp_path / "drf-omtir.yaml"
    policy = Policy.load(policy_path)
    wal = Wal(tmp_path / "wal" / "reviewer-action.jsonl", fresh=True)

    proxy = GovernanceProxy(
        root=tmp_path,
        policy=policy,
        wal=wal,
        transport=FakeTransport(),
    )

    review = ReviewAction(
        target_event_id="evt_000001",
        reviewer=ReviewerIdentity(
            reviewer_id="reviewer-1",
            reviewer_role="governance_reviewer",
        ),
        action="REQUEST_CHANGES",
        comment="Add structural evidence before retry.",
        review_reason="missing_structural_evidence",
    )

    record = proxy.append_reviewer_action(
        review,
        hmac_key="review-secret",
        key_id="review-key-v1",
    )

    payload = record["payload"]

    assert payload["event_type"] == "reviewer_action"
    assert payload["target_event_id"] == "evt_000001"
    assert payload["reviewer"]["reviewer_id"] == "reviewer-1"
    assert payload["reviewer"]["reviewer_role"] == "governance_reviewer"
    assert payload["review"]["action"] == "REQUEST_CHANGES"
    assert payload["policy_version"] == policy.version
    assert payload["policy_hash"] == policy.policy_hash
    assert verify_review_action_mac(payload=payload, hmac_key="review-secret") is True

    report = verify_wal(wal.path, root=tmp_path)
    assert report.status == "PASS"
