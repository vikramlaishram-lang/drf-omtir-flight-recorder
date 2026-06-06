from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import Decision
from .policy import ActionRule, Policy


@dataclass(frozen=True)
class InterceptionResult:
    governed: bool
    decision: str | None
    response: dict[str, Any] | None
    forwarded: bool
    wal_payload: dict[str, Any] | None


def intercept_mcp_message(
    message: dict[str, Any],
    policy: Policy,
    *,
    mcp_client_id: str = "UNKNOWN_FIXTURE_CLIENT",
) -> InterceptionResult:
    """Intercept one MCP JSON-RPC message.

    Phase 2 is deliberately pure:
    - no subprocess
    - no stdio
    - no WAL file writes
    - no wrapped server forwarding

    It only decides whether a message is governed and whether it should be
    forwarded by the future proxy.
    """

    method = message.get("method")

    if method != "tools/call":
        return InterceptionResult(
            governed=False,
            decision=None,
            response=None,
            forwarded=True,
            wal_payload=None,
        )

    request_id = message.get("id")
    params = message.get("params")

    if not isinstance(params, dict):
        return _protocol_error(
            request_id,
            code=-32602,
            message="Invalid params for tools/call",
            mcp_client_id=mcp_client_id,
            raw_message=message,
        )

    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    if not isinstance(tool_name, str) or not tool_name:
        return _protocol_error(
            request_id,
            code=-32602,
            message="tools/call params.name must be a non-empty string",
            mcp_client_id=mcp_client_id,
            raw_message=message,
        )

    if not isinstance(arguments, dict):
        return _protocol_error(
            request_id,
            code=-32602,
            message="tools/call params.arguments must be an object",
            mcp_client_id=mcp_client_id,
            raw_message=message,
        )

    rule = policy.rule_for(tool_name)
    decision, reason = _decision_for_rule(rule, policy)
    forwarded = decision == Decision.ALLOW

    wal_payload = _wal_payload(
        request_id=request_id,
        tool_name=tool_name,
        arguments=arguments,
        policy=policy,
        decision=decision,
        reason=reason,
        forwarded=forwarded,
        mcp_client_id=mcp_client_id,
    )

    if decision == Decision.ALLOW:
        return InterceptionResult(
            governed=True,
            decision=decision.value,
            response=None,
            forwarded=True,
            wal_payload=wal_payload,
        )

    if decision == Decision.REQUEST_REVIEW:
        return InterceptionResult(
            governed=True,
            decision=decision.value,
            response=_request_review_response(request_id, tool_name),
            forwarded=False,
            wal_payload=wal_payload,
        )

    return InterceptionResult(
        governed=True,
        decision=decision.value,
        response=_deny_response(request_id, tool_name, reason),
        forwarded=False,
        wal_payload=wal_payload,
    )


def _decision_for_rule(rule: ActionRule | None, policy: Policy) -> tuple[Decision, str]:
    if rule is None:
        return policy.unknown_action_decision, "NO_POLICY_RULE"

    if rule.decision != Decision.ALLOW:
        return rule.decision, "POLICY_MATCH"

    if not rule.executable:
        return Decision.DENY, "ACTION_NOT_EXECUTABLE"

    return Decision.ALLOW, "POLICY_MATCH"


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


def _request_review_response(request_id: Any, tool_name: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": f"PENDING REVIEW by DRF policy: {tool_name} requires human approval before execution",
                }
            ],
            "isError": True,
        },
    }


def _json_rpc_error_response(request_id: Any, *, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


def _protocol_error(
    request_id: Any,
    *,
    code: int,
    message: str,
    mcp_client_id: str,
    raw_message: dict[str, Any],
) -> InterceptionResult:
    return InterceptionResult(
        governed=True,
        decision="PROTOCOL_ERROR",
        response=_json_rpc_error_response(request_id, code=code, message=message),
        forwarded=False,
        wal_payload={
            "agent_proposal_source": "EXTERNAL_MCP_AGENT",
            "mcp_client_id": mcp_client_id,
            "tool_call_id": request_id,
            "mcp_method": raw_message.get("method"),
            "parsed_tool_name": None,
            "parsed_arguments": None,
            "drf_decision": "PROTOCOL_ERROR",
            "drf_reason": message,
            "forwarded": False,
            "tool_execution_boundary": "MCP_PROXY",
        },
    )


def _wal_payload(
    *,
    request_id: Any,
    tool_name: str,
    arguments: dict[str, Any],
    policy: Policy,
    decision: Decision,
    reason: str,
    forwarded: bool,
    mcp_client_id: str,
) -> dict[str, Any]:
    return {
        "agent_proposal_source": "EXTERNAL_MCP_AGENT",
        "mcp_client_id": mcp_client_id,
        "tool_call_id": request_id,
        "mcp_method": "tools/call",
        "parsed_tool_name": tool_name,
        "parsed_arguments": arguments,
        "policy_version": policy.version,
        "drf_decision": decision.value,
        "drf_reason": reason,
        "forwarded": forwarded,
        "tool_execution_boundary": "MCP_PROXY",
    }