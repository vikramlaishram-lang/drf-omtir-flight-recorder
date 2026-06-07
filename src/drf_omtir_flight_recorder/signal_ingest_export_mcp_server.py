from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from .signal import SignalEnvelope, classify_signal_envelope
from .wal import Wal


DEFAULT_SIGNAL_WAL_PATH = "/tmp/drf-omtir-wal/signal-ingest-mcp-v0.2.1.jsonl"


def _mcp_result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    }


def _tool_response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2, sort_keys=True),
                }
            ],
            "structuredContent": result,
        },
    }


def _error(request_id: Any, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -32000,
            "message": message,
        },
    }


def _initialize(request_id: Any) -> dict[str, Any]:
    return _mcp_result(
        request_id,
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "drf-omtir-signal-ingest-export",
                "version": "0.2.1",
            },
        },
    )


def _tools_list(request_id: Any) -> dict[str, Any]:
    return _mcp_result(
        request_id,
        {
            "tools": [
                {
                    "name": "ingest_signal",
                    "description": "Validate and classify an external signal into an evidence lane.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "source_id": {
                                "type": "string",
                                "description": "Unique source identifier.",
                            },
                            "source_type": {
                                "type": "string",
                                "description": "Signal source type.",
                            },
                            "payload": {
                                "type": "object",
                                "description": "Structured external signal payload.",
                            },
                            "ttl_seconds": {
                                "type": "integer",
                                "description": "Freshness TTL in seconds.",
                                "default": 3600,
                            },
                            "require_mac": {
                                "type": "boolean",
                                "description": "Require source MAC validation.",
                                "default": False,
                            },
                            "signal_key": {
                                "type": "string",
                                "description": "Optional local validation key for demo/MVP use.",
                            },
                            "source_mac": {
                                "type": "string",
                                "description": "Optional source MAC supplied by caller.",
                            },
                            "key_id": {
                                "type": "string",
                                "description": "Optional key identifier.",
                            },
                            "wal_path": {
                                "type": "string",
                                "description": "WAL path for recording signal ingest events.",
                                "default": DEFAULT_SIGNAL_WAL_PATH,
                            },
                        },
                        "required": ["source_id", "source_type", "payload"],
                    },
                },
                {
                    "name": "export_wal",
                    "description": "Read and export the signal ingest WAL file for local verification.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "wal_path": {
                                "type": "string",
                                "description": "Path to the WAL file to export.",
                                "default": DEFAULT_SIGNAL_WAL_PATH,
                            }
                        },
                        "required": [],
                    },
                },
            ]
        },
    )


def _last_record_hash(lines: list[str]) -> str | None:
    if not lines:
        return None

    try:
        last = json.loads(lines[-1])
    except json.JSONDecodeError:
        return None

    return last.get("record_hash")


def _ingest_signal(request_id: Any, arguments: dict[str, Any]) -> dict[str, Any]:
    key = arguments.get("signal_key")
    require_mac = bool(arguments.get("require_mac", False))

    envelope = SignalEnvelope.create(
        source_id=arguments["source_id"],
        source_type=arguments["source_type"],
        payload=arguments["payload"],
        ttl_seconds=int(arguments.get("ttl_seconds", 3600)),
        key=key,
        key_id=arguments.get("key_id"),
    )

    if arguments.get("source_mac"):
        envelope = SignalEnvelope(
            source_id=envelope.source_id,
            source_type=envelope.source_type,
            payload=envelope.payload,
            timestamp_utc=envelope.timestamp_utc,
            ttl_seconds=envelope.ttl_seconds,
            payload_hash=envelope.payload_hash,
            source_mac=arguments.get("source_mac"),
            key_id=envelope.key_id,
        )

    classification = classify_signal_envelope(
        envelope,
        key=key,
        require_mac=require_mac,
        admitted_lane="REFERENCE",
    )

    wal_path = Path(arguments.get("wal_path") or DEFAULT_SIGNAL_WAL_PATH)
    wal_path.parent.mkdir(parents=True, exist_ok=True)
    wal = Wal(wal_path)

    wal.append(
        {
            "event_id": wal.next_event_id(),
            "event_type": "signal_ingest",
            "signal_envelope": envelope.to_dict(),
            "evidence_classification": classification,
            "admitted": classification["admitted"],
            "lane": classification["lane"],
            "validation_status": classification["validation_status"],
            "freshness_status": classification["freshness_status"],
        }
    )

    content = wal_path.read_text(encoding="utf-8")
    lines = [line for line in content.splitlines() if line.strip()]
    wal_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()

    return _tool_response(
        request_id,
        {
            "status": "RECORDED",
            "event_type": "signal_ingest",
            "lane": classification["lane"],
            "admitted": classification["admitted"],
            "validation_status": classification["validation_status"],
            "freshness_status": classification["freshness_status"],
            "payload_hash": classification["payload_hash"],
            "wal_path": str(wal_path),
            "wal_export_status": "EXPORTED",
            "record_count": len(lines),
            "last_record_hash": _last_record_hash(lines),
            "wal_sha256": wal_sha256,
            "wal_content": content,
        },
    )

def _export_wal(request_id: Any, arguments: dict[str, Any]) -> dict[str, Any]:
    wal_path = Path(arguments.get("wal_path") or DEFAULT_SIGNAL_WAL_PATH)

    if not wal_path.exists():
        return _tool_response(
            request_id,
            {
                "status": "MISSING",
                "wal_path": str(wal_path),
                "record_count": 0,
                "last_record_hash": None,
                "wal_sha256": None,
                "wal_content": "",
            },
        )

    content = wal_path.read_text(encoding="utf-8")
    lines = [line for line in content.splitlines() if line.strip()]
    wal_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()

    return _tool_response(
        request_id,
        {
            "status": "EXPORTED",
            "wal_path": str(wal_path),
            "record_count": len(lines),
            "last_record_hash": _last_record_hash(lines),
            "wal_sha256": wal_sha256,
            "wal_content": content,
        },
    )


def _call_tool(request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name")
    arguments = params.get("arguments") or {}

    if name == "ingest_signal":
        return _ingest_signal(request_id, arguments)

    if name == "export_wal":
        return _export_wal(request_id, arguments)

    return _error(request_id, f"unknown tool: {name}")


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue

        request_id = None

        try:
            message = json.loads(line)
            request_id = message.get("id")
            method = message.get("method")

            if method == "initialize":
                response = _initialize(request_id)
            elif method == "tools/list":
                response = _tools_list(request_id)
            elif method == "tools/call":
                response = _call_tool(request_id, message.get("params") or {})
            elif method in {"notifications/initialized", "initialized"}:
                continue
            else:
                response = _error(request_id, f"unsupported method: {method}")

        except Exception as exc:
            response = _error(request_id, str(exc))

        sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
        sys.stdout.flush()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
