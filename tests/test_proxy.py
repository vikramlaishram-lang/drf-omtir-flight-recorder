from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from drf_omtir_flight_recorder.core import init_workspace
from drf_omtir_flight_recorder.policy import Policy
from drf_omtir_flight_recorder.proxy import GovernanceProxy
from drf_omtir_flight_recorder.verifier import verify_wal
from drf_omtir_flight_recorder.wal import Wal


class FakeTransport:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    def request(self, message: dict[str, Any]) -> dict[str, Any]:
        self.messages.append(message)
        return {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": {
                "isError": False,
                "content": [
                    {
                        "type": "text",
                        "text": "fake transport response",
                    }
                ],
            },
        }

    def notify(self, message: dict[str, Any]) -> None:
        self.messages.append(message)


class ProxyTest(unittest.TestCase):
    def test_proxy_allows_read_only_and_blocks_denied_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace(root)
            policy = Policy.load(root / "drf-omtir.yaml")
            wal = Wal(root / "wal" / "proxy-test.jsonl", fresh=True)
            transport = FakeTransport()

            proxy = GovernanceProxy(
                root=root,
                policy=policy,
                wal=wal,
                transport=transport,
                redact_keys=["api_key"],
            )

            allowed = proxy.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "search_logs",
                        "arguments": {
                            "query": "error",
                            "api_key": "secret",
                        },
                    },
                }
            )

            denied = proxy.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "delete_index",
                        "arguments": {
                            "index": "prod",
                        },
                    },
                }
            )

            self.assertIsNotNone(allowed)
            self.assertIsNotNone(denied)
            assert allowed is not None
            assert denied is not None

            self.assertEqual(allowed["id"], 1)
            self.assertEqual(allowed["result"]["isError"], False)
            self.assertEqual(denied["result"]["isError"], True)

            # Only the ALLOW call is forwarded to the wrapped MCP server.
            self.assertEqual(len(transport.messages), 1)
            self.assertEqual(transport.messages[0]["params"]["name"], "search_logs")
            self.assertEqual(
                transport.messages[0]["params"]["arguments"]["api_key"],
                "[REDACTED]",
            )

            records = wal.read()

            # Phase 3 writes:
            # 1. ALLOW decision event
            # 2. ALLOW tool_result event
            # 3. DENY decision event
            self.assertEqual(len(records), 3)

            allow_decision = records[0]["payload"]
            allow_result = records[1]["payload"]
            deny_decision = records[2]["payload"]

            self.assertEqual(allow_decision["event_type"], "mcp_tool_call_decision")
            self.assertEqual(allow_decision["parsed_tool_name"], "search_logs")
            self.assertEqual(allow_decision["drf_decision"], "ALLOW")
            self.assertEqual(allow_decision["forwarded"], True)
            self.assertEqual(
                allow_decision["parsed_arguments"]["api_key"],
                "[REDACTED]",
            )

            self.assertEqual(allow_result["event_type"], "mcp_tool_call_result")
            self.assertEqual(allow_result["parsed_tool_name"], "search_logs")
            self.assertEqual(allow_result["forwarded"], True)
            self.assertEqual(
                allow_result["tool_execution_boundary"],
                "MCP_PROXY_STUB_SERVER",
            )

            self.assertEqual(deny_decision["event_type"], "mcp_tool_call_decision")
            self.assertEqual(deny_decision["parsed_tool_name"], "delete_index")
            self.assertEqual(deny_decision["drf_decision"], "DENY")
            self.assertEqual(deny_decision["forwarded"], False)

            report = verify_wal(wal.path, root=root)
            self.assertEqual(report.status, "PASS")


if __name__ == "__main__":
    unittest.main()