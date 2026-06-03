from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Protocol

from .gateway import TypedGateway
from .models import EvidenceLane, EvidenceRef, ToolResult
from .policy import Policy
from .wal import Wal, canonical_json, sha256_bytes, sha256_file


class ChildTransport(Protocol):
    def request(self, message: dict[str, Any]) -> dict[str, Any]:
        ...


class SubprocessTransport:
    def __init__(self, command: list[str]):
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            text=True,
            encoding="utf-8",
        )

    def request(self, message: dict[str, Any]) -> dict[str, Any]:
        if not self.process.stdin or not self.process.stdout:
            raise RuntimeError("MCP subprocess pipes are not available")
        self.process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("MCP subprocess closed without response")
        return json.loads(line)

    def close(self) -> None:
        if self.process.stdin:
            self.process.stdin.close()
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
    def __init__(
        self,
        *,
        root: str | Path,
        policy: Policy,
        wal: Wal,
        transport: ChildTransport,
        redact_keys: list[str] | None = None,
    ):
        self.root = Path(root).resolve()
        self.policy = policy
        self.wal = wal
        self.transport = transport
        self.gateway = TypedGateway(self.root, policy, wal)
        self.redact_keys = {key.lower() for key in (redact_keys or [])}
        self.call_counter = 0

    def handle(self, message: dict[str, Any]) -> dict[str, Any]:
        if message.get("method") != "tools/call":
            return self.transport.request(message)
        params = message.get("params") or {}
        action = str(params.get("name", ""))
        arguments = params.get("arguments") or {}
        clean_arguments = redact(arguments, self.redact_keys)
        rule = self.policy.rule_for(action)
        if not rule or rule.decision.value != "ALLOW" or not rule.executable:
            result = self.gateway.propose_action(action, clean_arguments)
            return self._governance_response(message, result)

        response_holder: dict[str, Any] = {}

        def forward_handler(args: dict[str, Any]) -> ToolResult:
            before = sha256_bytes(canonical_json(args))
            response = self.transport.request(message)
            response_holder["response"] = response
            sanitized_response = redact(response, self.redact_keys)
            self.call_counter += 1
            output_path = self.root / "outputs" / "proxy" / f"call_{self.call_counter:06d}.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(sanitized_response, indent=2, sort_keys=True), encoding="utf-8")
            after = sha256_bytes(canonical_json(args))
            evidence = EvidenceRef(
                source=action,
                lane=EvidenceLane.STRUCTURAL,
                output_path=output_path.relative_to(self.root).as_posix(),
                output_sha256=sha256_file(output_path),
                validation="VALID",
            )
            return ToolResult(
                output=sanitized_response,
                evidence=evidence,
                input_sha256_before=before,
                input_sha256_after=after,
                input_unchanged=before == after,
            )

        self.gateway.handlers[action] = forward_handler
        self.gateway.propose_action(action, clean_arguments)
        return response_holder.get("response") or self._error_response(message, "Allowed tool returned no response")

    @staticmethod
    def _governance_response(message: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": {
                "isError": True,
                "content": [{"type": "text", "text": json.dumps({"governance": result}, sort_keys=True)}],
            },
        }

    @staticmethod
    def _error_response(message: dict[str, Any], text: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": message.get("id"), "error": {"code": -32000, "message": text}}


def run_stdio_proxy(
    *,
    root: str | Path,
    policy_path: str | Path,
    wal_path: str | Path,
    command: list[str],
) -> int:
    root_path = Path(root).resolve()
    policy = Policy.load(policy_path)
    wal = Wal(wal_path)
    transport = SubprocessTransport(command)
    proxy = GovernanceProxy(
        root=root_path,
        policy=policy,
        wal=wal,
        transport=transport,
        redact_keys=policy.proxy.get("redact_keys", []),
    )
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
                response = proxy.handle(message)
            except Exception as exc:  # pragma: no cover - stdio boundary
                response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": str(exc)}}
            sys.stdout.write(json.dumps(response, separators=(",", ":"), ensure_ascii=True) + "\n")
            sys.stdout.flush()
    finally:
        transport.close()
    return 0
