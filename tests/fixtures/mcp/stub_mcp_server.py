from __future__ import annotations

import json
import sys
from typing import Any


PROTOCOL_VERSION = "2025-03-26"


def write_message(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def make_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def make_tool_result(request_id: Any, text: str, *, is_error: bool = False) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [{"type": "text", "text": text}],
            "isError": is_error,
        },
    }


def tools_list(request_id: Any) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "tools": [
                {
                    "name": "search_logs",
                    "description": "Stub search over demo logs.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "limit": {"type": "integer"},
                        },
                    },
                },
                {
                    "name": "read_metrics",
                    "description": "Stub metric read.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "service": {"type": "string"},
                        },
                    },
                },
                {
                    "name": "delete_index",
                    "description": "Stub destructive action used for governance tests.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "index": {"type": "string"},
                        },
                    },
                },
                {
                    "name": "restart_service",
                    "description": "Stub state-changing action used for review tests.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "service": {"type": "string"},
                        },
                    },
                },
            ]
        },
    }


def handle_message(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "stub-mcp-server", "version": "0.1"},
            },
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return tools_list(request_id)

    if method == "tools/call":
        params = message.get("params")
        if not isinstance(params, dict):
            return make_error(request_id, -32602, "Invalid params for tools/call")
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return make_error(request_id, -32602, "Tool arguments must be an object")

        if name == "search_logs":
            query = arguments.get("query", "error OR timeout")
            return make_tool_result(request_id, f"stub search_logs result: {query}")

        if name == "read_metrics":
            return make_tool_result(
                request_id,
                "stub read_metrics result: latency_p95_ms=912 error_rate=0.07",
            )

        if name == "delete_index":
            return make_tool_result(
                request_id,
                "stub delete_index result: forwarded to wrapped server",
            )

        if name == "restart_service":
            return make_tool_result(
                request_id,
                "stub restart_service result: forwarded to wrapped server",
            )

        return make_error(request_id, -32602, f"Unknown tool: {name}")

    return make_error(request_id, -32601, f"Method not found: {method}")


def main() -> int:
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            write_message(make_error(None, -32700, "Parse error"))
            continue

        if not isinstance(message, dict):
            write_message(make_error(None, -32600, "Invalid Request"))
            continue

        response = handle_message(message)
        if response is not None:
            write_message(response)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
