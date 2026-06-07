from pathlib import Path

from drf_omtir_flight_recorder.verifier import verify_wal
from drf_omtir_flight_recorder.wal import WAL_AUTH_HMAC, WAL_AUTH_UNKEYED, Wal


def test_hmac_wal_verifies(tmp_path: Path):
    wal_path = tmp_path / "hmac.jsonl"

    wal = Wal(
        wal_path,
        fresh=True,
        auth_mode=WAL_AUTH_HMAC,
        hmac_key="test-secret",
        key_id="test-key-v1",
    )

    wal.append(
        {
            "event_id": "evt_000001",
            "event_type": "decision",
            "drf_decision": "DENY",
            "execution": {"executed": False},
        }
    )

    report = verify_wal(
        wal_path,
        hmac_key="test-secret",
        require_hmac=True,
    )

    assert report.status == "PASS"
    assert report.errors == []


def test_hmac_wal_rejects_wrong_key(tmp_path: Path):
    wal_path = tmp_path / "hmac.jsonl"

    wal = Wal(
        wal_path,
        fresh=True,
        auth_mode=WAL_AUTH_HMAC,
        hmac_key="correct-secret",
        key_id="test-key-v1",
    )

    wal.append(
        {
            "event_id": "evt_000001",
            "event_type": "decision",
            "drf_decision": "DENY",
            "execution": {"executed": False},
        }
    )

    report = verify_wal(
        wal_path,
        hmac_key="wrong-secret",
        require_hmac=True,
    )

    assert report.status == "FAIL"
    assert any("payload_mac mismatch" in err for err in report.errors)


def test_legacy_unkeyed_wal_still_verifies(tmp_path: Path):
    wal_path = tmp_path / "legacy.jsonl"

    wal = Wal(wal_path, fresh=True, auth_mode=WAL_AUTH_UNKEYED)

    wal.append(
        {
            "event_id": "evt_000001",
            "event_type": "decision",
            "drf_decision": "DENY",
            "execution": {"executed": False},
        }
    )

    report = verify_wal(wal_path)

    assert report.status == "PASS"
    assert report.errors == []


def test_strict_hmac_mode_rejects_legacy_record(tmp_path: Path):
    wal_path = tmp_path / "legacy.jsonl"

    wal = Wal(wal_path, fresh=True, auth_mode=WAL_AUTH_UNKEYED)

    wal.append(
        {
            "event_id": "evt_000001",
            "event_type": "decision",
            "drf_decision": "DENY",
            "execution": {"executed": False},
        }
    )

    report = verify_wal(
        wal_path,
        hmac_key="test-secret",
        require_hmac=True,
    )

    assert report.status == "FAIL"
    assert any("HMAC required" in err for err in report.errors)
