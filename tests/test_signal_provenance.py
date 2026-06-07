from __future__ import annotations

import datetime as dt
from pathlib import Path

from drf_omtir_flight_recorder.core import init_workspace
from drf_omtir_flight_recorder.policy import Policy
from drf_omtir_flight_recorder.proxy import GovernanceProxy
from drf_omtir_flight_recorder.signal import (
    FRESHNESS_FRESH,
    FRESHNESS_STALE,
    LANE_QUARANTINED,
    LANE_REFERENCE,
    SIGNAL_INVALID,
    SIGNAL_VALID,
    SignalEnvelope,
    classify_signal_envelope,
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


def test_fresh_signed_signal_is_admitted():
    envelope = SignalEnvelope.create(
        source_id="bright_data:feed_A",
        source_type="external_api",
        payload={"risk_score": 72},
        key="signal-secret",
        key_id="signal-key-v1",
    )

    result = classify_signal_envelope(
        envelope,
        key="signal-secret",
        require_mac=True,
        admitted_lane=LANE_REFERENCE,
    )

    assert result["validation_status"] == SIGNAL_VALID
    assert result["freshness_status"] == FRESHNESS_FRESH
    assert result["lane"] == LANE_REFERENCE
    assert result["admitted"] is True


def test_wrong_signal_key_is_quarantined():
    envelope = SignalEnvelope.create(
        source_id="bright_data:feed_A",
        source_type="external_api",
        payload={"risk_score": 72},
        key="correct-secret",
        key_id="signal-key-v1",
    )

    result = classify_signal_envelope(
        envelope,
        key="wrong-secret",
        require_mac=True,
        admitted_lane=LANE_REFERENCE,
    )

    assert result["validation_status"] == SIGNAL_INVALID
    assert result["lane"] == LANE_QUARANTINED
    assert result["admitted"] is False


def test_unsigned_signal_is_quarantined_when_mac_required():
    envelope = SignalEnvelope.create(
        source_id="open_web:page",
        source_type="web",
        payload={"title": "example"},
        key=None,
    )

    result = classify_signal_envelope(
        envelope,
        key="signal-secret",
        require_mac=True,
        admitted_lane=LANE_REFERENCE,
    )

    assert result["validation_status"] == SIGNAL_INVALID
    assert result["lane"] == LANE_QUARANTINED
    assert result["admitted"] is False


def test_stale_signal_is_quarantined():
    old_time = (
        dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=120)
    ).replace(tzinfo=None).isoformat() + "Z"

    envelope = SignalEnvelope.create(
        source_id="bright_data:feed_A",
        source_type="external_api",
        payload={"risk_score": 72},
        ttl_seconds=10,
        key="signal-secret",
        key_id="signal-key-v1",
        timestamp_utc=old_time,
    )

    result = classify_signal_envelope(
        envelope,
        key="signal-secret",
        require_mac=True,
        admitted_lane=LANE_REFERENCE,
    )

    assert result["validation_status"] == SIGNAL_VALID
    assert result["freshness_status"] == FRESHNESS_STALE
    assert result["lane"] == LANE_QUARANTINED
    assert result["admitted"] is False


def test_payload_hash_mismatch_is_quarantined():
    envelope = SignalEnvelope.create(
        source_id="bright_data:feed_A",
        source_type="external_api",
        payload={"risk_score": 72},
        key="signal-secret",
        key_id="signal-key-v1",
    )

    tampered = SignalEnvelope(
        source_id=envelope.source_id,
        source_type=envelope.source_type,
        payload={"risk_score": 99},
        timestamp_utc=envelope.timestamp_utc,
        ttl_seconds=envelope.ttl_seconds,
        payload_hash=envelope.payload_hash,
        source_mac=envelope.source_mac,
        key_id=envelope.key_id,
    )

    result = classify_signal_envelope(
        tampered,
        key="signal-secret",
        require_mac=True,
        admitted_lane=LANE_REFERENCE,
    )

    assert result["validation_status"] == SIGNAL_INVALID
    assert result["lane"] == LANE_QUARANTINED
    assert result["admitted"] is False


def test_proxy_records_signal_ingest_event(tmp_path: Path):
    init_workspace(tmp_path)
    policy_path = tmp_path / "drf-omtir.yaml"
    policy = Policy.load(policy_path)
    wal = Wal(tmp_path / "wal" / "signal-ingest.jsonl", fresh=True)

    proxy = GovernanceProxy(
        root=tmp_path,
        policy=policy,
        wal=wal,
        transport=FakeTransport(),
    )

    envelope = SignalEnvelope.create(
        source_id="bright_data:feed_A",
        source_type="external_api",
        payload={"risk_score": 72},
        key="signal-secret",
        key_id="signal-key-v1",
    )

    record = proxy.append_signal_ingest(
        envelope,
        key="signal-secret",
        require_mac=True,
        admitted_lane=LANE_REFERENCE,
    )

    payload = record["payload"]

    assert payload["event_type"] == "signal_ingest"
    assert payload["lane"] == LANE_REFERENCE
    assert payload["admitted"] is True
    assert payload["validation_status"] == SIGNAL_VALID
    assert payload["freshness_status"] == FRESHNESS_FRESH
    assert payload["policy_version"] == policy.version
    assert payload["policy_hash"] == policy.policy_hash

    report = verify_wal(wal.path, root=tmp_path)
    assert report.status == "PASS"
