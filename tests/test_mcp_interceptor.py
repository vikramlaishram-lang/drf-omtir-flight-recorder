from __future__ import annotations

import json
from pathlib import Path

from drf_omtir_flight_recorder.mcp_interceptor import intercept_mcp_message
from drf_omtir_flight_recorder.policy_loader import load_policy_yaml


ROOT = Path(__file__).resolve().parents[1]


def _load_fixture(name: str) -> dict:
    return json.loads((ROOT / "tests" / "fixtures" / "mcp" / name).read_text(encoding="utf-8"))


def _example_policy():
    return load_policy_yaml(ROOT / "policy" / "example-policy.yaml")


def _mutation_policy():
    return load_policy_yaml(ROOT / "tests" / "fixtures" / "mcp" / "policy_mutation_allow_delete_index.yaml")


def test_delete_index_deny_response_is_error_true() -> None:
    result = intercept_mcp_message(_load_fixture("tools_call_delete_index.json"), _example_policy())

    assert result.governed is True
    assert result.decision == "DENY"
    assert result.response is not None
    assert result.response["id"] == 2
    assert result.response["result"]["isError"] is True
    assert "DENIED by DRF policy" in result.response["result"]["content"][0]["text"]


def test_delete_index_deny_not_forwarded() -> None:
    result = intercept_mcp_message(_load_fixture("tools_call_delete_index.json"), _example_policy())

    assert result.forwarded is False
    assert result.wal_payload is not None
    assert result.wal_payload["parsed_tool_name"] == "delete_index"
    assert result.wal_payload["drf_decision"] == "DENY"
    assert result.wal_payload["drf_reason"] == "POLICY_MATCH"
    assert result.wal_payload["forwarded"] is False


def test_restart_service_request_review_is_error_true() -> None:
    result = intercept_mcp_message(_load_fixture("tools_call_restart_service.json"), _example_policy())

    assert result.governed is True
    assert result.decision == "REQUEST_REVIEW"
    assert result.response is not None
    assert result.response["id"] == 4
    assert result.response["result"]["isError"] is True
    assert "PENDING REVIEW by DRF policy" in result.response["result"]["content"][0]["text"]


def test_restart_service_not_forwarded() -> None:
    result = intercept_mcp_message(_load_fixture("tools_call_restart_service.json"), _example_policy())

    assert result.forwarded is False
    assert result.wal_payload is not None
    assert result.wal_payload["parsed_tool_name"] == "restart_service"
    assert result.wal_payload["drf_decision"] == "REQUEST_REVIEW"
    assert result.wal_payload["forwarded"] is False


def test_search_logs_allow_forwarded() -> None:
    result = intercept_mcp_message(_load_fixture("tools_call_search_logs.json"), _example_policy())

    assert result.governed is True
    assert result.decision == "ALLOW"
    assert result.forwarded is True
    assert result.wal_payload is not None
    assert result.wal_payload["parsed_tool_name"] == "search_logs"
    assert result.wal_payload["parsed_arguments"] == {"query": "error OR timeout", "limit": 10}
    assert result.wal_payload["drf_decision"] == "ALLOW"
    assert result.wal_payload["forwarded"] is True


def test_search_logs_allow_response_is_none() -> None:
    result = intercept_mcp_message(_load_fixture("tools_call_search_logs.json"), _example_policy())

    assert result.decision == "ALLOW"
    assert result.response is None


def test_delete_index_mutation_allow_forwarded() -> None:
    result = intercept_mcp_message(_load_fixture("tools_call_delete_index.json"), _mutation_policy())

    assert result.governed is True
    assert result.decision == "ALLOW"
    assert result.forwarded is True
    assert result.response is None
    assert result.wal_payload is not None
    assert result.wal_payload["parsed_tool_name"] == "delete_index"
    assert result.wal_payload["drf_decision"] == "ALLOW"
    assert result.wal_payload["forwarded"] is True


def test_initialize_not_governed_forwarded() -> None:
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "fixture-harness", "version": "0.1"},
        },
    }

    result = intercept_mcp_message(message, _example_policy())

    assert result.governed is False
    assert result.decision is None
    assert result.response is None
    assert result.forwarded is True
    assert result.wal_payload is None


def test_tools_list_not_governed_forwarded() -> None:
    message = {"jsonrpc": "2.0", "id": 10, "method": "tools/list", "params": {}}

    result = intercept_mcp_message(message, _example_policy())

    assert result.governed is False
    assert result.forwarded is True
    assert result.response is None
    assert result.wal_payload is None


def test_wal_payload_has_v03_external_mcp_fields() -> None:
    result = intercept_mcp_message(_load_fixture("tools_call_delete_index.json"), _example_policy())

    assert result.wal_payload is not None
    assert result.wal_payload["agent_proposal_source"] == "EXTERNAL_MCP_AGENT"
    assert result.wal_payload["mcp_client_id"] == "UNKNOWN_FIXTURE_CLIENT"
    assert result.wal_payload["tool_call_id"] == 2
    assert result.wal_payload["mcp_method"] == "tools/call"
    assert result.wal_payload["tool_execution_boundary"] == "MCP_PROXY"