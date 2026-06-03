from __future__ import annotations

import json
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
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({"ok": True, "name": message["params"]["name"]}),
                    }
                ]
            },
        }


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
                    "params": {"name": "search_logs", "arguments": {"query": "error", "api_key": "secret"}},
                }
            )
            denied = proxy.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "delete_index", "arguments": {"index": "prod"}},
                }
            )

            self.assertEqual(allowed["id"], 1)
            self.assertEqual(denied["result"]["isError"], True)
            self.assertEqual(len(transport.messages), 1)
            self.assertEqual(transport.messages[0]["params"]["name"], "search_logs")
            records = wal.read()
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["payload"]["proposal"]["arguments"]["api_key"], "[REDACTED]")
            self.assertEqual(records[1]["payload"]["drf_decision"]["decision"], "DENY")
            report = verify_wal(wal.path, root=root)
            self.assertEqual(report.status, "PASS")


if __name__ == "__main__":
    unittest.main()
