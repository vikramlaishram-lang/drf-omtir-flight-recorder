from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import Effect
from .wal import ZERO_HASH, canonical_json, sha256_bytes, sha256_file


@dataclass
class VerificationReport:
    status: str
    records: int
    errors: list[str]
    last_record_hash: str | None
    verifier: str = "drf_omtir_flight_recorder_verifier"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "records": self.records,
            "errors": self.errors,
            "last_record_hash": self.last_record_hash,
            "verifier": self.verifier,
        }


def verify_wal(path: str | Path, *, root: str | Path = ".") -> VerificationReport:
    wal_path = Path(path)
    root_path = Path(root).resolve()
    errors: list[str] = []
    records: list[dict[str, Any]] = []

    if not wal_path.exists():
        return VerificationReport("FAIL", 0, [f"WAL missing: {wal_path}"], None)

    for line_no, line in enumerate(wal_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_no}: invalid JSON: {exc}")

    event_ids: set[str] = set()
    payloads: dict[str, dict[str, Any]] = {}
    previous_hash = ZERO_HASH
    for expected_sequence, record in enumerate(records, start=1):
        payload = record.get("payload")
        event_id = record.get("event_id")
        if record.get("sequence") != expected_sequence:
            errors.append(f"record {expected_sequence}: sequence mismatch")
        if not event_id:
            errors.append(f"record {expected_sequence}: missing event_id")
        elif event_id in event_ids:
            errors.append(f"record {expected_sequence}: duplicate event_id {event_id}")
        else:
            event_ids.add(event_id)
        if not isinstance(payload, dict):
            errors.append(f"record {expected_sequence}: payload missing or invalid")
            continue
        payloads[str(event_id)] = payload
        if record.get("previous_hash") != previous_hash:
            errors.append(f"record {expected_sequence}: previous_hash mismatch")
        expected_payload_hash = sha256_bytes(canonical_json(payload))
        if record.get("payload_hash") != expected_payload_hash:
            errors.append(f"record {expected_sequence}: payload_hash mismatch")
        stripped = dict(record)
        actual_record_hash = stripped.pop("record_hash", None)
        expected_record_hash = sha256_bytes(canonical_json(stripped))
        if actual_record_hash != expected_record_hash:
            errors.append(f"record {expected_sequence}: record_hash mismatch")
        previous_hash = str(actual_record_hash)

    for record in records:
        payload = record.get("payload", {})
        event_id = payload.get("event_id")
        execution = payload.get("execution", {})
        action_contract = payload.get("action_contract") or {}
        decision = (payload.get("drf_decision") or {}).get("decision")

        if decision in {"DENY", "REQUEST_REVIEW"} and execution.get("executed"):
            errors.append(f"{event_id}: non-ALLOW decision executed")

        adaptation = payload.get("adaptation")
        if adaptation:
            source = adaptation.get("adapted_from_event_id")
            if source not in payloads:
                errors.append(f"{event_id}: adaptation source missing: {source}")

        feedback = payload.get("feedback")
        if feedback and feedback.get("source_event_id") != event_id:
            errors.append(f"{event_id}: feedback source_event_id mismatch")

        tool_result = payload.get("tool_result")
        if execution.get("executed") and action_contract.get("effect") == Effect.READ_ONLY.value:
            if not tool_result:
                errors.append(f"{event_id}: read-only execution missing tool_result")
            else:
                before = tool_result.get("input_sha256_before")
                after = tool_result.get("input_sha256_after")
                if not before or before != after:
                    errors.append(f"{event_id}: read-only input hash changed")
                if tool_result.get("input_unchanged") is not True:
                    errors.append(f"{event_id}: read-only input_unchanged not true")

        claim = payload.get("claim")
        if claim and claim.get("status") == "CONFIRMED":
            linked_event_id = claim.get("linked_tool_event_id")
            linked_payload = payloads.get(str(linked_event_id))
            if not linked_payload:
                errors.append(f"{event_id}: confirmed claim missing linked tool event")
                continue
            if not linked_payload.get("execution", {}).get("executed"):
                errors.append(f"{event_id}: confirmed claim linked event not executed")
            sources = linked_payload.get("evidence_packet", {}).get("sources", [])
            structural = [
                item for item in sources
                if item.get("lane") == "STRUCTURAL" and item.get("validation") == "VALID"
            ]
            if not structural:
                errors.append(f"{event_id}: confirmed claim lacks structural evidence")
                continue
            expected_hash = claim.get("linked_output_sha256")
            if expected_hash and all(item.get("output_sha256") != expected_hash for item in structural):
                errors.append(f"{event_id}: confirmed claim output hash not in linked evidence")
            for item in structural:
                output_path = item.get("output_path")
                output_hash = item.get("output_sha256")
                if not output_path or not output_hash:
                    errors.append(f"{event_id}: structural evidence missing output link")
                    continue
                output = (root_path / output_path).resolve()
                try:
                    output.relative_to(root_path)
                except ValueError:
                    errors.append(f"{event_id}: structural evidence outside root")
                    continue
                if not output.exists():
                    errors.append(f"{event_id}: structural evidence output missing")
                    continue
                if sha256_file(output) != output_hash:
                    errors.append(f"{event_id}: structural evidence output hash mismatch")

    last_hash = records[-1].get("record_hash") if records else None
    return VerificationReport("PASS" if not errors else "FAIL", len(records), errors, last_hash)
