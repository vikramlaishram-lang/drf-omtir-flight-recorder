from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Protocol

from .health import ObserverUnavailableError, RuntimeHealth
from .mcp_interceptor import InterceptionResult, intercept_mcp_message
from .policy import Policy
from .policy_loader import load_policy_yaml
from .runtime_guard import enforce_local_mvp_scope
from .review import ReviewAction, build_review_event
from .signal import SignalEnvelope, build_signal_ingest_event, classify_signal_envelope
from .tool_identity import (
    ToolIdentityManifest,
    build_tool_identity_manifest,
    compare_tool_identity_manifests,
)
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
        runtime_health: RuntimeHealth | None = None,
        server_origin: str = "wrapped_mcp_server",
        expected_tool_manifest: ToolIdentityManifest | None = None,
    ):
        self.root = Path(root).resolve()
        self.policy = policy
        self.wal = wal
        self.transport = transport
        self.mcp_client_id = mcp_client_id
        self.redact_keys = {key.lower() for key in (redact_keys or [])}
        self.runtime_health = runtime_health or RuntimeHealth()
        self.server_origin = server_origin
        self.expected_tool_manifest = expected_tool_manifest
        self.baseline_tool_manifest = expected_tool_manifest
        self.observed_tool_manifest: ToolIdentityManifest | None = None
        self.tool_identity_errors_by_tool: dict[str, str] = {}

    def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        clean_message = redact(message, self.redact_keys)

        try:
            self.runtime_health.require_observer_current()
        except ObserverUnavailableError as exc:
            self._append_runtime_health_failure(clean_message, str(exc))
            return _error_response(clean_message.get("id"), "SHADOW_SAFE_VIOLATION: observer_unavailable")

        if clean_message.get("method") == "tools/list":
            return self._handle_tools_list(clean_message)

        result = intercept_mcp_message(
            clean_message,
            self.policy,
            mcp_client_id=self.mcp_client_id,
        )

        if not result.governed:
            return self._forward_ungoverned(clean_message)

        result = self._apply_tool_identity_guard(result)
        self._append_decision_event(result)

        if not result.forwarded:
            return result.response

        server_response = self.transport.request(clean_message)
        clean_response = redact(server_response, self.redact_keys)
        self._append_tool_result_event(result, clean_response)

        return server_response



    def append_signal_ingest(
        self,
        envelope: SignalEnvelope,
        *,
        key: str | bytes | None = None,
        require_mac: bool = True,
        admitted_lane: str = "REFERENCE",
    ) -> dict[str, Any]:
        """Validate, classify, and record an external signal envelope.

        Signals that are stale, malformed, unsigned, or MAC-invalid are
        recorded but quarantined. They are not admitted as authority.
        """
        classification = classify_signal_envelope(
            envelope,
            key=key,
            require_mac=require_mac,
            admitted_lane=admitted_lane,
        )
        payload = build_signal_ingest_event(
            event_id=self.wal.next_event_id(),
            envelope=envelope,
            classification=classification,
        )
        payload.update(self._policy_metadata())
        return self.wal.append(payload)
    def append_reviewer_action(
        self,
        review: ReviewAction,
        *,
        hmac_key: str | bytes | None = None,
        key_id: str | None = None,
    ) -> dict[str, Any]:
        """Append an accountable reviewer action to the WAL.

        This records reviewer identity, reviewer role, target event link,
        policy metadata, and optional review-action MAC.
        """
        payload = build_review_event(
            event_id=self.wal.next_event_id(),
            review=review,
            policy_version=self.policy.version,
            policy_hash=getattr(self.policy, "policy_hash", None),
            policy_source=getattr(self.policy, "policy_source", None),
            hmac_key=hmac_key,
            key_id=key_id,
        )
        return self.wal.append(payload)
    def _forward_ungoverned(self, message: dict[str, Any]) -> dict[str, Any] | None:
        if "id" not in message:
            notify = getattr(self.transport, "notify", None)

            if notify is not None:
                notify(message)
            else:
                self.transport.request(message)

            return None

        return self.transport.request(message)

    def _policy_metadata(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy.version,
            "policy_hash": getattr(self.policy, "policy_hash", None),
            "policy_source": getattr(self.policy, "policy_source", None),
        }

    def _append_runtime_health_failure(
        self,
        message: dict[str, Any],
        reason: str,
    ) -> None:
        payload = {
            "schema_version": "drf_omtir_mcp_proxy_event.v0.3",
            "event_id": self.wal.next_event_id(),
            "event_type": "runtime_health_failure",
            "agent_proposal_source": "EXTERNAL_MCP_AGENT",
            "mcp_client_id": self.mcp_client_id,
            "tool_call_id": message.get("id"),
            "mcp_method": message.get("method"),
            "parsed_tool_name": (
                message.get("params", {}).get("name")
                if isinstance(message.get("params"), dict)
                else None
            ),
            "drf_decision": "DENY",
            "drf_reason": reason,
            "forwarded": False,
            "tool_execution_boundary": "MCP_PROXY",
            "runtime_health": {
                "observer_required": self.runtime_health.observer_required,
                "observer_status": "UNAVAILABLE",
            },
            **self._policy_metadata(),
        }
        self.wal.append(payload)

    def _append_decision_event(self, result: InterceptionResult) -> None:
        if result.wal_payload is None:
            return

        payload = dict(result.wal_payload)
        payload.update(
            {
                "schema_version": "drf_omtir_mcp_proxy_event.v0.3",
                "event_id": self.wal.next_event_id(),
                "event_type": "mcp_tool_call_decision",
                **self._policy_metadata(),
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
            **self._policy_metadata(),
        }

        self.wal.append(payload)

    def _handle_tools_list(self, message: dict[str, Any]) -> dict[str, Any] | None:
        server_response = self._forward_ungoverned(message)

        if server_response is None:
            return None

        clean_response = redact(server_response, self.redact_keys)
        manifest = build_tool_identity_manifest(
            clean_response,
            server_origin=self.server_origin,
        )
        status = "BASELINE_CAPTURED"
        errors: dict[str, str] = {}

        if self.baseline_tool_manifest is None:
            self.baseline_tool_manifest = manifest
        else:
            errors = compare_tool_identity_manifests(
                self.baseline_tool_manifest,
                manifest,
            )
            status = "MATCH" if not errors else "MISMATCH"

        self.observed_tool_manifest = manifest
        self.tool_identity_errors_by_tool = errors
        self._append_tool_identity_manifest_event(
            message=message,
            manifest=manifest,
            status=status,
            errors=errors,
        )
        return server_response

    def _append_tool_identity_manifest_event(
        self,
        *,
        message: dict[str, Any],
        manifest: ToolIdentityManifest,
        status: str,
        errors: dict[str, str],
    ) -> None:
        payload = {
            "schema_version": "drf_omtir_mcp_proxy_event.v0.3",
            "event_id": self.wal.next_event_id(),
            "event_type": "mcp_tool_identity_manifest",
            "agent_proposal_source": "EXTERNAL_MCP_AGENT",
            "mcp_client_id": self.mcp_client_id,
            "tool_call_id": message.get("id"),
            "mcp_method": message.get("method"),
            "server_origin": self.server_origin,
            "tool_identity_status": status,
            "tool_identity_manifest": manifest.to_dict(),
            "tool_identity_manifest_hash": manifest.manifest_hash,
            "tool_identity_errors_by_tool": errors,
            "forwarded": True,
            "tool_execution_boundary": "MCP_PROXY_TOOLS_LIST",
            **self._policy_metadata(),
        }
        self.wal.append(payload)

    def _apply_tool_identity_guard(
        self,
        result: InterceptionResult,
    ) -> InterceptionResult:
        if result.wal_payload is None:
            return result

        payload = dict(result.wal_payload)
        tool_name = payload.get("parsed_tool_name")
        manifest_error = self._tool_identity_error_for(tool_name)
        self._annotate_tool_identity(payload, tool_name)

        if manifest_error is None:
            return InterceptionResult(
                governed=result.governed,
                decision=result.decision,
                response=result.response,
                forwarded=result.forwarded,
                wal_payload=payload,
            )

        payload.update(
            {
                "drf_decision": "DENY",
                "drf_reason": "TOOL_IDENTITY_MISMATCH",
                "forwarded": False,
                "tool_identity_status": "MISMATCH",
                "tool_identity_error": manifest_error,
            }
        )
        return InterceptionResult(
            governed=True,
            decision="DENY",
            response=_deny_response(
                payload.get("tool_call_id"),
                str(tool_name),
                "TOOL_IDENTITY_MISMATCH",
            ),
            forwarded=False,
            wal_payload=payload,
        )

    def _annotate_tool_identity(self, payload: dict[str, Any], tool_name: Any) -> None:
        if self.observed_tool_manifest is None:
            payload["tool_identity_status"] = "NOT_OBSERVED"

            if self.baseline_tool_manifest is not None:
                payload["tool_identity_expected_manifest_hash"] = (
                    self.baseline_tool_manifest.manifest_hash
                )

            return

        payload["server_origin"] = self.server_origin
        payload["tool_identity_manifest_hash"] = (
            self.observed_tool_manifest.manifest_hash
        )

        if self.baseline_tool_manifest is not None:
            payload["tool_identity_expected_manifest_hash"] = (
                self.baseline_tool_manifest.manifest_hash
            )

        if not isinstance(tool_name, str):
            payload["tool_identity_status"] = "UNKNOWN_TOOL_NAME"
            return

        identity = self.observed_tool_manifest.tools.get(tool_name)

        if identity is None:
            payload["tool_identity_status"] = "UNKNOWN_TOOL_IDENTITY"
            return

        payload["tool_identity_status"] = "MATCH"
        payload["tool_identity"] = identity.to_dict()

    def _tool_identity_error_for(self, tool_name: Any) -> str | None:
        if self.expected_tool_manifest is not None and self.observed_tool_manifest is None:
            return "tool identity manifest not observed before tools/call"

        if not isinstance(tool_name, str):
            return None

        if tool_name in self.tool_identity_errors_by_tool:
            return self.tool_identity_errors_by_tool[tool_name]

        return None


def _error_response(request_id: Any, text: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -32000,
            "message": text,
        },
    }


def _deny_response(request_id: Any, tool_name: str, reason: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": f"DENIED by DRF policy: {tool_name} is not permitted ({reason})",
                }
            ],
            "isError": True,
        },
    }


def run_stdio_proxy(
    *,
    root: str | Path,
    policy_path: str | Path,
    wal_path: str | Path,
    command: list[str],
) -> int:
    enforce_local_mvp_scope()

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
                sys.stdout.write(
                    json.dumps(response, separators=(",", ":"), ensure_ascii=True)
                    + "\n"
                )
                sys.stdout.flush()

    finally:
        transport.close()

    return 0


