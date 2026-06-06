
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Protocol

from .mcp_interceptor import InterceptionResult, intercept_mcp_message
from .policy import Policy
from .policy_loader import load_policy_yaml
from .wal import Wal


class ChildTransport(Protocol):
    def request(self, message: dict[str, Any]) -> dict[str, Any]:
        ...

    def notify(self, message: dict[str, Any]) -> None:
        ...


class SubprocessTransport:
    """Newline-delimited JSON-RPC transport for a wrapped MCP server."""

    def __init__(self, command: list[str]):
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )

    def _write(self, message: dict[str, Any]) -> None:
        if not self.process.stdin:
            raise RuntimeError("MCP subprocess stdin is not available")
        self.process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self.process.stdin.flush()

    def request(self, message: dict[str, Any]) -> dict[str, Any]:
        if not self.process.stdout:
            raise RuntimeError("MCP subprocess stdout is not available")
        self._write(message)
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("MCP subprocess closed without response")
        return json.loads(line)

    def notify(self, message: dict[str, Any]) -> None:
        self._write(message)

    def close(self) -> None:
        try:
            if self.process.stdin:
                self.process.stdin.close()
        finally:
            if self.process.poll() is None:
                self.process.terminate()


def redact(value: Any, keys: set[str]) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if key.lower() in keys else redact(item, keys)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item, keys) for item in value]
    return value


class GovernanceProxy:
    """Phase 3 stdio proxy over a wrapped MCP server.

    This is intentionally bounded:
    - newline-delimited JSON-RPC only
    - request/response fixture proof
    - no universal MCP client compatibility claim
    """

    def __init__(
        self,
        *,
        root: str | Path,
        policy: Policy,
        wal: Wal,
        transport: ChildTransport,
        mcp_client_id: str = "UNKNOWN_FIXTURE_CLIENT",
        redact_keys: list[str] | None = None,
    ):
        self.root = Path(root).resolve()
        self.policy = policy
        self.wal = wal
        self.transport = transport
        self.mcp_client_id = mcp_client_id
        self.redact_keys = {key.lower() for key in (redact_keys or [])}

    def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        clean_message = redact(message, self.redact_keys)

        result = intercept_mcp_message(
            clean_message,
            self.policy,
            mcp_client_id=self.mcp_client_id,
        )

        if not result.governed:
            return self._forward_ungoverned(clean_message)

        self._append_decision_event(result)

        if not result.forwarded:
            return result.response

        server_response = self.transport.request(clean_message)
        clean_response = redact(server_response, self.redact_keys)
        self._append_tool_result_event(result, clean_response)
        return server_response

    def _forward_ungoverned(self, message: dict[str, Any]) -> dict[str, Any] | None:
        # Notifications have no id and expect no response.
        if "id" not in message:
            notify = getattr(self.transport, "notify", None)
            if notify is not None:
                notify(message)
            else:
                self.transport.request(message)
            return None

        return self.transport.request(message)

    def _append_decision_event(self, result: InterceptionResult) -> None:
        if result.wal_payload is None:
            return

        payload = dict(result.wal_payload)
        payload.update(
            {
                "schema_version": "drf_omtir_mcp_proxy_event.v0.3",
                "event_id": self.wal.next_event_id(),
                "event_type": "mcp_tool_call_decision",
            }
        )
        self.wal.append(payload)

    def _append_tool_result_event(
        self,
        result: InterceptionResult,
        server_response: dict[str, Any],
    ) -> None:
        if result.wal_payload is None:
            return

        payload = {
            "schema_version": "drf_omtir_mcp_proxy_event.v0.3",
            "event_id": self.wal.next_event_id(),
            "event_type": "mcp_tool_call_result",
            "agent_proposal_source": result.wal_payload.get("agent_proposal_source"),
            "mcp_client_id": result.wal_payload.get("mcp_client_id"),
            "tool_call_id": result.wal_payload.get("tool_call_id"),
            "mcp_method": result.wal_payload.get("mcp_method"),
            "parsed_tool_name": result.wal_payload.get("parsed_tool_name"),
            "drf_decision": result.wal_payload.get("drf_decision"),
            "forwarded": True,
            "tool_execution_boundary": "MCP_PROXY_STUB_SERVER",
            "server_response": server_response,
        }
        self.wal.append(payload)


def _error_response(request_id: Any, text: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -32000,
            "message": text,
        },
    }


def run_stdio_proxy(
    *,
    root: str | Path,
    policy_path: str | Path,
    wal_path: str | Path,
    command: list[str],
) -> int:
    root_path = Path(root).resolve()
    policy = load_policy_yaml(policy_path)
    wal = Wal(wal_path, fresh=True)
    transport = SubprocessTransport(command)

    proxy = GovernanceProxy(
        root=root_path,
        policy=policy,
        wal=wal,
        transport=transport,
    )

    try:
        for line in sys.stdin:
            if not line.strip():
                continue

            request_id: Any = None
            try:
                message = json.loads(line)
                if isinstance(message, dict):
                    request_id = message.get("id")
                else:
                    raise ValueError("JSON-RPC message must be an object")

                response = proxy.handle(message)
            except Exception as exc:  # pragma: no cover - stdio boundary
                response = _error_response(request_id, str(exc))

            if response is not None:
                sys.stdout.write(json.dumps(response, separators=(",", ":"), ensure_ascii=True) + "\n")
                sys.stdout.flush()
    finally:
        transport.close()

    return 0
