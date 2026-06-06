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
ROOT = HERE.parents[2]
STUB_SERVER = HERE / "stub_mcp_server.py"
EXAMPLE_POLICY = ROOT / "policy" / "example-policy.yaml"
MUTATION_POLICY = HERE / "policy_mutation_allow_delete_index.yaml"


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


def start_process(command: list[str]) -> tuple[subprocess.Popen[str], queue.Queue[str]]:
    proc = subprocess.Popen(
        command,
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


def start_stub() -> tuple[subprocess.Popen[str], queue.Queue[str]]:
    return start_process([sys.executable, str(STUB_SERVER)])


def start_proxy(policy_path: Path, wal_path: Path) -> tuple[subprocess.Popen[str], queue.Queue[str]]:
    wal_path.parent.mkdir(parents=True, exist_ok=True)
    if wal_path.exists():
        wal_path.unlink()

    command = [
        sys.executable,
        "-m",
        "drf_omtir_flight_recorder.cli",
        "wrap",
        "--root",
        str(ROOT),
        "--policy",
        str(policy_path),
        "--wal",
        str(wal_path),
        "--",
        sys.executable,
        str(STUB_SERVER),
    ]
    return start_process(command)


def stop_process(proc: subprocess.Popen[str]) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()


def handshake(proc: subprocess.Popen[str], output_queue: queue.Queue[str]) -> None:
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


def assert_tools_list(proc: subprocess.Popen[str], output_queue: queue.Queue[str]) -> None:
    send(proc, tools_list_message())
    response = read_response(output_queue)
    tools = response.get("result", {}).get("tools", [])
    names = {tool.get("name") for tool in tools}
    expected = {"search_logs", "read_metrics", "delete_index", "restart_service"}
    assert_true(expected.issubset(names), f"tools/list missing tools: {expected - names}")


def read_wal(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise HarnessError(f"WAL missing: {path}")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def wal_payloads(path: Path) -> list[dict[str, Any]]:
    return [row.get("payload", {}) for row in read_wal(path)]


def assert_wal_decision(path: Path, *, tool: str, decision: str, forwarded: bool) -> None:
    payloads = wal_payloads(path)
    for payload in payloads:
        if payload.get("event_type") == "mcp_tool_call_decision" and payload.get("parsed_tool_name") == tool:
            assert_true(payload.get("agent_proposal_source") == "EXTERNAL_MCP_AGENT", "WAL source mismatch")
            assert_true(payload.get("drf_decision") == decision, f"WAL decision mismatch: {payload}")
            assert_true(payload.get("forwarded") is forwarded, f"WAL forwarded mismatch: {payload}")
            return
    raise HarnessError(f"No decision WAL event found for {tool}")


def assert_wal_result(path: Path, *, tool: str) -> None:
    payloads = wal_payloads(path)
    for payload in payloads:
        if payload.get("event_type") == "mcp_tool_call_result" and payload.get("parsed_tool_name") == tool:
            assert_true(payload.get("forwarded") is True, f"WAL result forwarded mismatch: {payload}")
            assert_true(payload.get("tool_execution_boundary") == "MCP_PROXY_STUB_SERVER", "tool boundary mismatch")
            return
    raise HarnessError(f"No result WAL event found for {tool}")


def stub_smoke() -> int:
    proc, output_queue = start_stub()
    try:
        handshake(proc, output_queue)
        assert_tools_list(proc, output_queue)

        send(proc, tools_call("search_logs", 3, {"query": "error OR timeout", "limit": 10}))
        response = read_response(output_queue)
        assert_true(response["id"] == 3, "search_logs response id mismatch")
        assert_true(response.get("result", {}).get("isError") is False, "search_logs should not be error")
        assert_true("stub search_logs result" in response["result"]["content"][0]["text"], "search_logs text mismatch")

        send(proc, tools_call("read_metrics", 5, {"service": "checkout-api"}))
        response = read_response(output_queue)
        assert_true(response["id"] == 5, "read_metrics response id mismatch")
        assert_true(response.get("result", {}).get("isError") is False, "read_metrics should not be error")
        assert_true("latency_p95_ms=912" in response["result"]["content"][0]["text"], "read_metrics text mismatch")

        print("STUB_SMOKE_PASS")
        return 0
    finally:
        stop_process(proc)


def proxy_deny() -> int:
    wal_path = ROOT / "wal" / "mcp-proxy-deny.jsonl"
    proc, output_queue = start_proxy(EXAMPLE_POLICY, wal_path)
    try:
        handshake(proc, output_queue)
        send(proc, tools_call("delete_index", 2, {"index": "demo-logs"}))
        response = read_response(output_queue)
        assert_true(response["id"] == 2, "delete_index response id mismatch")
        assert_true(response.get("result", {}).get("isError") is True, "delete_index should be denied")
        assert_true("DENIED by DRF policy" in response["result"]["content"][0]["text"], "deny text mismatch")
        assert_wal_decision(wal_path, tool="delete_index", decision="DENY", forwarded=False)
        print("PROXY_DENY_PASS")
        return 0
    finally:
        stop_process(proc)


def proxy_allow() -> int:
    wal_path = ROOT / "wal" / "mcp-proxy-allow.jsonl"
    proc, output_queue = start_proxy(EXAMPLE_POLICY, wal_path)
    try:
        handshake(proc, output_queue)
        assert_tools_list(proc, output_queue)
        send(proc, tools_call("search_logs", 3, {"query": "error OR timeout", "limit": 10}))
        response = read_response(output_queue)
        assert_true(response["id"] == 3, "search_logs response id mismatch")
        assert_true(response.get("result", {}).get("isError") is False, "search_logs should be allowed")
        assert_true("stub search_logs result" in response["result"]["content"][0]["text"], "allow text mismatch")
        assert_wal_decision(wal_path, tool="search_logs", decision="ALLOW", forwarded=True)
        assert_wal_result(wal_path, tool="search_logs")
        print("PROXY_ALLOW_PASS")
        return 0
    finally:
        stop_process(proc)


def proxy_review() -> int:
    wal_path = ROOT / "wal" / "mcp-proxy-review.jsonl"
    proc, output_queue = start_proxy(EXAMPLE_POLICY, wal_path)
    try:
        handshake(proc, output_queue)
        send(proc, tools_call("restart_service", 4, {"service": "checkout-api"}))
        response = read_response(output_queue)
        assert_true(response["id"] == 4, "restart_service response id mismatch")
        assert_true(response.get("result", {}).get("isError") is True, "restart_service should be review-blocked")
        assert_true("PENDING REVIEW by DRF policy" in response["result"]["content"][0]["text"], "review text mismatch")
        assert_wal_decision(wal_path, tool="restart_service", decision="REQUEST_REVIEW", forwarded=False)
        print("PROXY_REVIEW_PASS")
        return 0
    finally:
        stop_process(proc)


def policy_mutation() -> int:
    deny_wal = ROOT / "wal" / "mcp-proxy-mutation-deny.jsonl"
    allow_wal = ROOT / "wal" / "mcp-proxy-mutation-allow.jsonl"

    proc, output_queue = start_proxy(EXAMPLE_POLICY, deny_wal)
    try:
        handshake(proc, output_queue)
        send(proc, tools_call("delete_index", 2, {"index": "demo-logs"}))
        response = read_response(output_queue)
        assert_true(response.get("result", {}).get("isError") is True, "example policy should deny delete_index")
        assert_wal_decision(deny_wal, tool="delete_index", decision="DENY", forwarded=False)
    finally:
        stop_process(proc)

    proc, output_queue = start_proxy(MUTATION_POLICY, allow_wal)
    try:
        handshake(proc, output_queue)
        send(proc, tools_call("delete_index", 2, {"index": "demo-logs"}))
        response = read_response(output_queue)
        assert_true(response.get("result", {}).get("isError") is False, "mutation policy should allow delete_index")
        assert_true("stub delete_index result" in response["result"]["content"][0]["text"], "mutation allow text mismatch")
        assert_wal_decision(allow_wal, tool="delete_index", decision="ALLOW", forwarded=True)
        assert_wal_result(allow_wal, tool="delete_index")
        print("POLICY_MUTATION_PASS")
        return 0
    finally:
        stop_process(proc)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: fixture_harness.py stub-smoke|proxy-deny|proxy-allow|proxy-review|policy-mutation")
        return 2

    mode = argv[1]
    try:
        if mode == "stub-smoke":
            return stub_smoke()
        if mode == "proxy-deny":
            return proxy_deny()
        if mode == "proxy-allow":
            return proxy_allow()
        if mode == "proxy-review":
            return proxy_review()
        if mode == "policy-mutation":
            return policy_mutation()
        print(f"unknown mode: {mode}")
        return 2
    except HarnessError as exc:
        print(f"FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))