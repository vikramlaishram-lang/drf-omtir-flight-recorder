from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
STUB_SERVER = HERE / "stub_mcp_server.py"


class HarnessError(RuntimeError):
    pass


def reader_thread(stream, output_queue: queue.Queue[str]) -> None:
    for line in stream:
        output_queue.put(line)


def send(proc: subprocess.Popen[str], message: dict[str, Any]) -> None:
    assert proc.stdin is not None
    proc.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
    proc.stdin.flush()


def read_response(output_queue: queue.Queue[str], timeout: float = 3.0) -> dict[str, Any]:
    try:
        line = output_queue.get(timeout=timeout)
    except queue.Empty as exc:
        raise HarnessError("Timed out waiting for MCP response") from exc
    try:
        return json.loads(line)
    except json.JSONDecodeError as exc:
        raise HarnessError(f"Response was not valid JSON: {line!r}") from exc


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise HarnessError(message)


def initialize_message() -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "fixture-harness", "version": "0.1"},
        },
    }


def initialized_notification() -> dict[str, Any]:
    return {"jsonrpc": "2.0", "method": "notifications/initialized"}


def tools_list_message() -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": 10, "method": "tools/list", "params": {}}


def tools_call(name: str, request_id: int, arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }


def start_stub() -> tuple[subprocess.Popen[str], queue.Queue[str]]:
    proc = subprocess.Popen(
        [sys.executable, str(STUB_SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    output_queue: queue.Queue[str] = queue.Queue()
    threading.Thread(target=reader_thread, args=(proc.stdout, output_queue), daemon=True).start()
    return proc, output_queue


def stub_smoke() -> int:
    proc, output_queue = start_stub()
    try:
        send(proc, initialize_message())
        response = read_response(output_queue)
        assert_true(response["id"] == 1, "initialize response id mismatch")
        result = response.get("result", {})
        assert_true(result.get("protocolVersion") == "2025-03-26", "protocol version mismatch")
        assert_true("tools" in result.get("capabilities", {}), "tools capability missing")
        assert_true(result.get("serverInfo", {}).get("name") == "stub-mcp-server", "serverInfo.name mismatch")

        send(proc, initialized_notification())
        time.sleep(0.2)
        assert_true(output_queue.empty(), "initialized notification should not produce a response")

        send(proc, tools_list_message())
        response = read_response(output_queue)
        tools = response.get("result", {}).get("tools", [])
        names = {tool.get("name") for tool in tools}
        expected = {"search_logs", "read_metrics", "delete_index", "restart_service"}
        assert_true(expected.issubset(names), f"tools/list missing tools: {expected - names}")

        send(proc, tools_call("search_logs", 3, {"query": "error OR timeout", "limit": 10}))
        response = read_response(output_queue)
        assert_true(response["id"] == 3, "search_logs response id mismatch")
        assert_true(response.get("result", {}).get("isError") is False, "search_logs should not be error")
        text = response["result"]["content"][0]["text"]
        assert_true("stub search_logs result" in text, "search_logs text mismatch")

        send(proc, tools_call("read_metrics", 5, {"service": "checkout-api"}))
        response = read_response(output_queue)
        assert_true(response["id"] == 5, "read_metrics response id mismatch")
        assert_true(response.get("result", {}).get("isError") is False, "read_metrics should not be error")
        text = response["result"]["content"][0]["text"]
        assert_true("latency_p95_ms=912" in text, "read_metrics text mismatch")

        print("STUB_SMOKE_PASS")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()


def not_implemented(mode: str) -> int:
    print(f"{mode}: NOT_IMPLEMENTED_IN_PHASE_0")
    return 2


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: fixture_harness.py stub-smoke|proxy-deny|proxy-allow|proxy-review|policy-mutation")
        return 2

    mode = argv[1]
    try:
        if mode == "stub-smoke":
            return stub_smoke()
        if mode in {"proxy-deny", "proxy-allow", "proxy-review", "policy-mutation"}:
            return not_implemented(mode)
        print(f"unknown mode: {mode}")
        return 2
    except HarnessError as exc:
        print(f"FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
