from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any


ZERO_HASH = "0" * 64


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat() + "Z"


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Wal:
    def __init__(self, path: str | Path, *, fresh: bool = False):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
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
        record = {
            "sequence": sequence,
            "event_id": payload.get("event_id"),
            "timestamp": payload.get("timestamp"),
            "payload": payload,
            "payload_hash": payload_hash,
            "previous_hash": previous_hash,
        }
        record["record_hash"] = sha256_bytes(canonical_json(record))
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n")
        return record
