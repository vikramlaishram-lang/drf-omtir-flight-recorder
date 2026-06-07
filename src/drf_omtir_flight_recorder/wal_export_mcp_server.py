from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_WAL_PATH = "/tmp/drf-omtir-wal/truefoundry-real-mcp-v0.2.0.jsonl"


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
                "name": "drf-omtir-wal-export",
                "version": "0.2.0",
            },
        },
    )


def _tools_list(request_id: Any) -> dict[str, Any]:
    return _mcp_result(
        request_id,
        {
            "tools": [
                {
                    "name": "export_wal",
                    "description": "Read and export a DRF + OMTIR hosted WAL file for local verification.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "wal_path": {
                                "type": "string",
                                "description": "Path to the WAL file to export.",
                                "default": DEFAULT_WAL_PATH,
                            }
                        },
                        "required": [],
                    },
                }
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


def _call_tool(request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name")
    arguments = params.get("arguments") or {}

    if name != "export_wal":
        return _error(request_id, f"unknown tool: {name}")

    wal_path = Path(arguments.get("wal_path") or DEFAULT_WAL_PATH)

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
