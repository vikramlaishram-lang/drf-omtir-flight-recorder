from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from drf_omtir_flight_recorder.core import init_workspace
from drf_omtir_flight_recorder.health import RuntimeHealth
from drf_omtir_flight_recorder.policy import Policy
from drf_omtir_flight_recorder.runtime_guard import (
    DeploymentGuardError,
    enforce_local_mvp_scope,
)
from drf_omtir_flight_recorder.proxy import GovernanceProxy
from drf_omtir_flight_recorder.verifier import verify_wal
from drf_omtir_flight_recorder.wal import Wal


class FakeTransport:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    def request(self, message: dict) -> dict:
        self.messages.append(message)
        return {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": {
                "isError": False,
                "content": [{"type": "text", "text": "fake transport response"}],
            },
        }

    def notify(self, message: dict) -> None:
        self.messages.append(message)


def test_policy_hash_is_recorded_in_proxy_events(tmp_path: Path):
    init_workspace(tmp_path)
    policy_path = tmp_path / "drf-omtir.yaml"
    policy = Policy.load(policy_path)
    wal = Wal(tmp_path / "wal" / "policy-hash.jsonl", fresh=True)
    transport = FakeTransport()

    proxy = GovernanceProxy(
        root=tmp_path,
        policy=policy,
        wal=wal,
        transport=transport,
        redact_keys=["api_key"],
    )

    proxy.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search_logs",
                "arguments": {"query": "error", "api_key": "secret"},
            },
        }
    )

    records = wal.read()
    assert len(records) == 2

    for record in records:
        payload = record["payload"]
        assert payload["policy_version"] == policy.version
        assert payload["policy_hash"] == policy.policy_hash
        assert payload["policy_source"] == str(policy_path)

    report = verify_wal(wal.path, root=tmp_path)
    assert report.status == "PASS"


def test_deployment_guard_blocks_production_mode(monkeypatch):
    monkeypatch.setenv("DRF_OMTIR_DEPLOYMENT_MODE", "production")

    with pytest.raises(DeploymentGuardError):
        enforce_local_mvp_scope()


def test_deployment_guard_allows_local_mvp_mode(monkeypatch):
    monkeypatch.setenv("DRF_OMTIR_DEPLOYMENT_MODE", "local_mvp")
    enforce_local_mvp_scope()


def test_observer_unavailable_fails_closed_and_does_not_forward(tmp_path: Path):
    init_workspace(tmp_path)
    policy = Policy.load(tmp_path / "drf-omtir.yaml")
    wal = Wal(tmp_path / "wal" / "observer-health.jsonl", fresh=True)
    transport = FakeTransport()

    stale_time = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=60)

    proxy = GovernanceProxy(
        root=tmp_path,
        policy=policy,
        wal=wal,
        transport=transport,
        runtime_health=RuntimeHealth(
            observer_required=True,
            observer_last_heartbeat_at=stale_time,
            observer_heartbeat_ttl_seconds=5,
        ),
    )

    response = proxy.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search_logs",
                "arguments": {"query": "error"},
            },
        }
    )

    assert response is not None
    assert response["error"]["message"] == "SHADOW_SAFE_VIOLATION: observer_unavailable"
    assert transport.messages == []

    records = wal.read()
    assert len(records) == 1
    payload = records[0]["payload"]

    assert payload["event_type"] == "runtime_health_failure"
    assert payload["drf_decision"] == "DENY"
    assert payload["forwarded"] is False
    assert payload["runtime_health"]["observer_status"] == "UNAVAILABLE"

    report = verify_wal(wal.path, root=tmp_path)
    assert report.status == "PASS"
