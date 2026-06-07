from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .signal import SignalEnvelope, classify_signal_envelope
from .wal import Wal


def _response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
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


def _tools_list(request_id: Any) -> dict[str, Any]:
    return _response(
        request_id,
        {
            "tools": [
                {
                    "name": "ingest_signal",
                    "description": "Validate and classify an external signal into an evidence lane.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "source_id": {"type": "string"},
                            "source_type": {"type": "string"},
                            "payload": {"type": "object"},
                            "ttl_seconds": {"type": "integer"},
                            "source_mac": {"type": "string"},
                            "key_id": {"type": "string"},
                        },
                        "required": ["source_id", "source_type", "payload"],
                    },
                }
            ]
        },
    )


def _call_tool(request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name")
    arguments = params.get("arguments") or {}

    if name != "ingest_signal":
        return _error(request_id, f"unknown tool: {name}")

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

    wal_path = Path(arguments.get("wal_path", "wal/signal-ingest-mcp.jsonl"))
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

    return _response(
        request_id,
        {
            "status": "RECORDED",
            "event_type": "signal_ingest",
            "lane": classification["lane"],
            "admitted": classification["admitted"],
            "validation_status": classification["validation_status"],
            "freshness_status": classification["freshness_status"],
            "payload_hash": classification["payload_hash"],
        },
    )


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue

        try:
            message = json.loads(line)
            request_id = message.get("id")
            method = message.get("method")

            if method == "initialize":
                response = _response(
                    request_id,
                    {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {
                            "name": "drf-omtir-signal-ingest",
                            "version": "0.1.9",
                        },
                    },
                )
            elif method == "tools/list":
                response = _tools_list(request_id)
            elif method == "tools/call":
                response = _call_tool(request_id, message.get("params") or {})
            else:
                response = _error(request_id, f"unsupported method: {method}")

        except Exception as exc:
            response = _error(None, str(exc))

        sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
        sys.stdout.flush()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
