from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from drf_omtir_flight_recorder.policy_loader import load_policy_yaml
from drf_omtir_flight_recorder.proxy import GovernanceProxy
from drf_omtir_flight_recorder.receipt import write_trust_receipt
from drf_omtir_flight_recorder.verifier import verify_wal
from drf_omtir_flight_recorder.wal import Wal


REPO_ROOT = Path(__file__).resolve().parents[1]
GITHUB_POLICY = REPO_ROOT / "policy" / "github-flat-policy-v0.1.yaml"


class MockGithubMcp:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request(self, message: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(message)
        tool_name = message["params"]["name"]
        return {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": f"mocked upstream result for {tool_name}",
                    }
                ],
                "isError": False,
            },
        }

    def notify(self, message: dict[str, Any]) -> None:
        self.calls.append(message)


def _tool_call(request_id: int, tool_name: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": {
                "owner": "example",
                "repo": "demo",
            },
        },
    }


def _read_wal(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_github_mcp_proxy_enforces_flat_policy_and_records_wal(tmp_path: Path) -> None:
    policy = load_policy_yaml(GITHUB_POLICY)
    wal_path = tmp_path / "wal" / "github-mcp-proxy.jsonl"
    wal = Wal(wal_path, fresh=True)
    upstream = MockGithubMcp()
    proxy = GovernanceProxy(
        root=tmp_path,
        policy=policy,
        wal=wal,
        transport=upstream,
        mcp_client_id="github-mcp-policy-test",
        server_origin="mock_github_mcp",
        review_queue_path=tmp_path / "reports" / "github-review-queue.jsonl",
    )

    expected = {
        "get_file_contents": ("ALLOW", "READ_ONLY", True),
        "list_pull_requests": ("ALLOW", "READ_ONLY", True),
        "issue_write": ("REQUEST_REVIEW", "LOW_RISK_WRITE", False),
        "create_pull_request": ("REQUEST_REVIEW", "LOW_RISK_WRITE", False),
        "push_files": ("DENY", "DESTRUCTIVE", False),
        "delete_file": ("DENY", "DESTRUCTIVE", False),
        "create_repository": ("DENY", "ADMIN", False),
        "unknown_github_tool": ("DENY", "UNKNOWN", False),
    }

    for request_id, tool_name in enumerate(expected, start=1):
        response = proxy.handle(_tool_call(request_id, tool_name))
        decision, _effect, forwarded = expected[tool_name]
        assert response is not None
        if forwarded:
            assert response["result"]["isError"] is False
        elif decision == "REQUEST_REVIEW":
            assert response["result"]["isError"] is True
            assert "PENDING REVIEW" in response["result"]["content"][0]["text"]
        else:
            assert response["result"]["isError"] is True
            assert "DENIED" in response["result"]["content"][0]["text"]

    assert [call["params"]["name"] for call in upstream.calls] == [
        "get_file_contents",
        "list_pull_requests",
    ]

    records = _read_wal(wal_path)
    decision_payloads = [
        record["payload"]
        for record in records
        if record["payload"].get("event_type") == "mcp_tool_call_decision"
    ]
    result_payloads = [
        record["payload"]
        for record in records
        if record["payload"].get("event_type") == "mcp_tool_call_result"
    ]
    assert len(decision_payloads) == len(expected)
    assert len(result_payloads) == 2

    by_tool = {payload["parsed_tool_name"]: payload for payload in decision_payloads}
    for tool_name, (decision, effect, forwarded) in expected.items():
        payload = by_tool[tool_name]
        assert payload["drf_decision"] == decision
        assert payload["policy_decision"] == decision
        assert payload["policy_effect"] == effect
        assert payload["forwarded"] is forwarded
        assert payload["forward_result"] == ("FORWARDED" if forwarded else "BLOCKED")

    review_queue = tmp_path / "reports" / "github-review-queue.jsonl"
    review_items = _read_wal(review_queue)
    assert [item["action"] for item in review_items] == [
        "issue_write",
        "create_pull_request",
    ]

    report = verify_wal(wal_path, root=tmp_path)
    assert report.status == "PASS"
    assert report.errors == []

    receipt_path = tmp_path / "receipts" / "github-mcp-proxy-trust-receipt.md"
    receipt = write_trust_receipt(wal_path, receipt_path, root=tmp_path)
    assert receipt["verifier"]["status"] == "PASS"
    receipt_text = receipt_path.read_text(encoding="utf-8")
    assert "## MCP / GitHub Tool Governance" in receipt_text
    assert "get_file_contents -> ALLOW (READ_ONLY) -> FORWARDED" in receipt_text
    assert "issue_write -> REQUEST_REVIEW (LOW_RISK_WRITE) -> BLOCKED" in receipt_text
    assert "push_files -> DENY (DESTRUCTIVE) -> BLOCKED" in receipt_text
