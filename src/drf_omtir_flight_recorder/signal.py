from __future__ import annotations

import datetime as dt
import hmac
import os
from dataclasses import dataclass
from typing import Any

from .wal import canonical_json, hmac_sha256_bytes, sha256_bytes


SIGNAL_SCHEMA_VERSION = "drf_omtir_signal_envelope.v0.1"

SIGNAL_VALID = "VALID"
SIGNAL_INVALID = "INVALID"
SIGNAL_UNKNOWN = "UNKNOWN"

FRESHNESS_FRESH = "FRESH"
FRESHNESS_STALE = "STALE"

LANE_STRUCTURAL = "STRUCTURAL"
LANE_REFERENCE = "REFERENCE"
LANE_RESEARCH_ONLY = "RESEARCH_ONLY"
LANE_UNKNOWN = "UNKNOWN"
LANE_QUARANTINED = "QUARANTINED"

ENV_SIGNAL_SECRET = "DRF_OMTIR_SIGNAL_HMAC_KEY"


class SignalValidationError(ValueError):
    """Raised when a signal envelope is malformed or inadmissible."""


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def utc_now_text() -> str:
    return utc_now().replace(tzinfo=None).isoformat() + "Z"


def parse_utc_timestamp(value: str) -> dt.datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    parsed = dt.datetime.fromisoformat(value)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)

    return parsed.astimezone(dt.timezone.utc)


def signal_mac_input(
    *,
    source_id: str,
    source_type: str,
    timestamp_utc: str,
    ttl_seconds: int,
    payload_hash: str,
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "source_type": source_type,
        "timestamp_utc": timestamp_utc,
        "ttl_seconds": ttl_seconds,
        "payload_hash": payload_hash,
    }


def compute_signal_mac(
    *,
    key: str | bytes,
    source_id: str,
    source_type: str,
    timestamp_utc: str,
    ttl_seconds: int,
    payload_hash: str,
) -> str:
    key_bytes = key if isinstance(key, bytes) else key.encode("utf-8")

    return hmac_sha256_bytes(
        key_bytes,
        canonical_json(
            signal_mac_input(
                source_id=source_id,
                source_type=source_type,
                timestamp_utc=timestamp_utc,
                ttl_seconds=ttl_seconds,
                payload_hash=payload_hash,
            )
        ),
    )


@dataclass(frozen=True)
class SignalEnvelope:
    source_id: str
    source_type: str
    payload: dict[str, Any]
    timestamp_utc: str
    ttl_seconds: int = 60
    payload_hash: str | None = None
    source_mac: str | None = None
    key_id: str | None = None

    @classmethod
    def create(
        cls,
        *,
        source_id: str,
        source_type: str,
        payload: dict[str, Any],
        ttl_seconds: int = 60,
        key: str | bytes | None = None,
        key_id: str | None = None,
        timestamp_utc: str | None = None,
    ) -> "SignalEnvelope":
        timestamp = timestamp_utc or utc_now_text()
        payload_hash = sha256_bytes(canonical_json(payload))

        source_mac = None

        if key is not None:
            source_mac = compute_signal_mac(
                key=key,
                source_id=source_id,
                source_type=source_type,
                timestamp_utc=timestamp,
                ttl_seconds=ttl_seconds,
                payload_hash=payload_hash,
            )

        return cls(
            source_id=source_id,
            source_type=source_type,
            payload=payload,
            timestamp_utc=timestamp,
            ttl_seconds=ttl_seconds,
            payload_hash=payload_hash,
            source_mac=source_mac,
            key_id=key_id,
        )

    def validate_structure(self) -> None:
        if not self.source_id or not self.source_id.strip():
            raise SignalValidationError("source_id is required")

        if not self.source_type or not self.source_type.strip():
            raise SignalValidationError("source_type is required")

        if not isinstance(self.payload, dict):
            raise SignalValidationError("payload must be an object")

        if self.ttl_seconds <= 0:
            raise SignalValidationError("ttl_seconds must be positive")

        if not self.timestamp_utc:
            raise SignalValidationError("timestamp_utc is required")

    def computed_payload_hash(self) -> str:
        return sha256_bytes(canonical_json(self.payload))

    def freshness_status(self, *, now: dt.datetime | None = None) -> str:
        current = now or utc_now()
        signal_time = parse_utc_timestamp(self.timestamp_utc)
        age = current - signal_time

        if age.total_seconds() <= self.ttl_seconds:
            return FRESHNESS_FRESH

        return FRESHNESS_STALE

    def validation_status(
        self,
        *,
        key: str | bytes | None = None,
        require_mac: bool = True,
    ) -> str:
        try:
            self.validate_structure()
        except SignalValidationError:
            return SIGNAL_INVALID

        if self.payload_hash != self.computed_payload_hash():
            return SIGNAL_INVALID

        if require_mac:
            if not key or not self.source_mac:
                return SIGNAL_INVALID

            expected = compute_signal_mac(
                key=key,
                source_id=self.source_id,
                source_type=self.source_type,
                timestamp_utc=self.timestamp_utc,
                ttl_seconds=self.ttl_seconds,
                payload_hash=str(self.payload_hash),
            )

            if not hmac.compare_digest(str(self.source_mac), expected):
                return SIGNAL_INVALID

        return SIGNAL_VALID

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SIGNAL_SCHEMA_VERSION,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "timestamp_utc": self.timestamp_utc,
            "ttl_seconds": self.ttl_seconds,
            "payload": self.payload,
            "payload_hash": self.payload_hash,
            "source_mac": self.source_mac,
            "key_id": self.key_id,
        }


def classify_signal_envelope(
    envelope: SignalEnvelope,
    *,
    key: str | bytes | None = None,
    require_mac: bool = True,
    now: dt.datetime | None = None,
    admitted_lane: str = LANE_REFERENCE,
) -> dict[str, Any]:
    validation_status = envelope.validation_status(
        key=key,
        require_mac=require_mac,
    )
    freshness_status = envelope.freshness_status(now=now)

    if validation_status != SIGNAL_VALID or freshness_status != FRESHNESS_FRESH:
        lane = LANE_QUARANTINED
        admitted = False
    else:
        lane = admitted_lane
        admitted = True

    return {
        "lane": lane,
        "admitted": admitted,
        "validation_status": validation_status,
        "freshness_status": freshness_status,
        "source_id": envelope.source_id,
        "source_type": envelope.source_type,
        "payload_hash": envelope.payload_hash,
        "key_id": envelope.key_id,
    }


def build_signal_ingest_event(
    *,
    event_id: str,
    envelope: SignalEnvelope,
    classification: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "drf_omtir_signal_ingest_event.v0.1",
        "event_id": event_id,
        "event_type": "signal_ingest",
        "signal_envelope": envelope.to_dict(),
        "evidence_classification": classification,
        "admitted": classification.get("admitted") is True,
        "lane": classification.get("lane"),
        "validation_status": classification.get("validation_status"),
        "freshness_status": classification.get("freshness_status"),
    }


def signal_key_from_env() -> str | None:
    return os.getenv(ENV_SIGNAL_SECRET)
