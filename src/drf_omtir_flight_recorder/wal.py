from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any

ZERO_HASH = "0" * 64

WAL_AUTH_UNKEYED = "UNKEYED_HASH_CHAIN"
WAL_AUTH_HMAC = "HMAC_SHA256_V1"
WAL_AUTH_VERSION = "wal_auth.v0.1"

ENV_WAL_AUTH_MODE = "DRF_OMTIR_WAL_AUTH_MODE"
ENV_WAL_HMAC_KEY = "DRF_OMTIR_WAL_HMAC_KEY"
ENV_WAL_HMAC_KEY_ID = "DRF_OMTIR_WAL_HMAC_KEY_ID"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat() + "Z"


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hmac_sha256_bytes(key: bytes, value: bytes) -> str:
    return hmac.new(key, value, hashlib.sha256).hexdigest()


def load_hmac_key(raw: str | bytes | None) -> bytes | None:
    """
    Load a runtime-held WAL HMAC key.

    Supported forms:
    - plain string: "dev-secret"
    - hex string: "hex:0123abcd..."
    - bytes: b"..."

    Do not store production keys in the repo.
    """
    if raw is None:
        return None

    if isinstance(raw, bytes):
        return raw

    if raw.startswith("hex:"):
        return bytes.fromhex(raw.removeprefix("hex:"))

    return raw.encode("utf-8")


class Wal:
    def __init__(
        self,
        path: str | Path,
        *,
        fresh: bool = False,
        auth_mode: str | None = None,
        hmac_key: str | bytes | None = None,
        key_id: str | None = None,
    ):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self.auth_mode = auth_mode or os.getenv(ENV_WAL_AUTH_MODE, WAL_AUTH_UNKEYED)
        self.key_id = key_id or os.getenv(ENV_WAL_HMAC_KEY_ID, "local-dev-key")
        self.hmac_key = load_hmac_key(hmac_key or os.getenv(ENV_WAL_HMAC_KEY))

        if self.auth_mode not in {WAL_AUTH_UNKEYED, WAL_AUTH_HMAC}:
            raise ValueError(f"Unsupported WAL auth mode: {self.auth_mode}")

        if self.auth_mode == WAL_AUTH_HMAC and not self.hmac_key:
            raise ValueError(
                f"{ENV_WAL_HMAC_KEY} is required when "
                f"{ENV_WAL_AUTH_MODE}={WAL_AUTH_HMAC}"
            )

        if fresh and self.path.exists():
            self.path.unlink()

        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def read(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def next_event_id(self) -> str:
        return f"evt_{len(self.read()) + 1:06d}"

    def get_payload(self, event_id: str) -> dict[str, Any] | None:
        for row in self.read():
            payload = row.get("payload", {})
            if payload.get("event_id") == event_id:
                return payload
        return None

    def append(self, payload: dict[str, Any]) -> dict[str, Any]:
        rows = self.read()
        sequence = len(rows) + 1
        previous_hash = rows[-1]["record_hash"] if rows else ZERO_HASH

        payload = dict(payload)
        payload.setdefault("timestamp", utc_now())
        payload["sequence"] = sequence

        payload_hash = sha256_bytes(canonical_json(payload))

        record: dict[str, Any] = {
            "sequence": sequence,
            "event_id": payload.get("event_id"),
            "timestamp": payload.get("timestamp"),
            "payload": payload,
            "payload_hash": payload_hash,
            "previous_hash": previous_hash,
        }

        if self.auth_mode == WAL_AUTH_HMAC:
            assert self.hmac_key is not None

            record["wal_auth"] = {
                "mode": WAL_AUTH_HMAC,
                "version": WAL_AUTH_VERSION,
                "key_id": self.key_id,
            }

            record["payload_mac"] = hmac_sha256_bytes(
                self.hmac_key,
                canonical_json(payload),
            )

            record["record_mac"] = hmac_sha256_bytes(
                self.hmac_key,
                canonical_json(record),
            )

        else:
            record["wal_auth"] = {
                "mode": WAL_AUTH_UNKEYED,
                "version": WAL_AUTH_VERSION,
                "key_id": None,
            }

        record["record_hash"] = sha256_bytes(canonical_json(record))

        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    record,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                )
                + "\n"
            )

        return record
