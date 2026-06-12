from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from drf_omtir_flight_recorder.core import init_workspace
from drf_omtir_flight_recorder.policy import Policy
from drf_omtir_flight_recorder.proxy import GovernanceProxy
from drf_omtir_flight_recorder.tool_identity import build_tool_identity_manifest
from drf_omtir_flight_recorder.verifier import verify_wal
from drf_omtir_flight_recorder.wal import Wal


def tools_list_response(description: str = "Search application logs") -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "tools": [
                {
                    "name": "search_logs",
                    "description": description,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                            }
                        },
                        "required": ["query"],
                    },
                    "annotations": {
                        "readOnlyHint": True,
                        "destructiveHint": False,
                        "idempotentHint": True,
                    },
                }
            ]
        },
    }


class ToolsListTransport:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.messages: list[dict[str, Any]] = []

    def request(self, message: dict[str, Any]) -> dict[str, Any]:
        self.messages.append(message)

        if message.get("method") == "tools/list":
            response = dict(self.response)
            response["id"] = message.get("id")
            return response

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


class ToolIdentityTest(unittest.TestCase):
    def test_build_manifest_records_identity_fields_and_hashes(self) -> None:
        manifest = build_tool_identity_manifest(
            tools_list_response(),
            server_origin="fake://unit-test",
        )

        self.assertIn("search_logs", manifest.tools)
        tool = manifest.tools["search_logs"]

        self.assertEqual(tool.tool_name, "search_logs")
        self.assertEqual(tool.server_origin, "fake://unit-test")
        self.assertEqual(tool.read_only_hint, True)
        self.assertEqual(tool.destructive_hint, False)
        self.assertEqual(tool.idempotent_hint, True)
        self.assertEqual(len(tool.input_schema_hash), 64)
        self.assertEqual(len(tool.description_hash), 64)
        self.assertEqual(len(tool.identity_hash), 64)
        self.assertEqual(len(manifest.manifest_hash), 64)

        manifest_dict = manifest.to_dict()
        tool_dict = manifest_dict["tools"][0]
        self.assertIn("input_schema_hash", tool_dict)
        self.assertIn("description_hash", tool_dict)
        self.assertIn("readOnlyHint", tool_dict)
        self.assertIn("destructiveHint", tool_dict)
        self.assertIn("idempotentHint", tool_dict)

    def test_proxy_writes_tool_identity_manifest_from_tools_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace(root)
            policy = Policy.load(root / "drf-omtir.yaml")
            wal = Wal(root / "wal" / "tool-identity.jsonl", fresh=True)
            transport = ToolsListTransport(tools_list_response())

            proxy = GovernanceProxy(
                root=root,
                policy=policy,
                wal=wal,
                transport=transport,
                server_origin="fake://unit-test",
            )

            response = proxy.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                }
            )

            self.assertIsNotNone(response)
            self.assertEqual(len(transport.messages), 1)

            records = wal.read()
            self.assertEqual(len(records), 1)
            payload = records[0]["payload"]

            self.assertEqual(payload["event_type"], "mcp_tool_identity_manifest")
            self.assertEqual(payload["mcp_method"], "tools/list")
            self.assertEqual(payload["server_origin"], "fake://unit-test")
            self.assertEqual(payload["tool_identity_status"], "BASELINE_CAPTURED")
            self.assertEqual(payload["tool_identity_errors_by_tool"], {})

            manifest = payload["tool_identity_manifest"]
            self.assertEqual(manifest["server_origin"], "fake://unit-test")
            self.assertEqual(len(manifest["tools"]), 1)
            tool = manifest["tools"][0]
            self.assertEqual(tool["tool_name"], "search_logs")
            self.assertEqual(tool["server_origin"], "fake://unit-test")
            self.assertEqual(tool["readOnlyHint"], True)
            self.assertEqual(tool["destructiveHint"], False)
            self.assertEqual(tool["idempotentHint"], True)
            self.assertEqual(len(tool["input_schema_hash"]), 64)
            self.assertEqual(len(tool["description_hash"]), 64)

            report = verify_wal(wal.path, root=root)
            self.assertEqual(report.status, "PASS")

    def test_proxy_denies_tool_call_when_manifest_identity_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace(root)
            policy = Policy.load(root / "drf-omtir.yaml")
            wal = Wal(root / "wal" / "tool-identity-drift.jsonl", fresh=True)
            expected_manifest = build_tool_identity_manifest(
                tools_list_response(description="Search application logs"),
                server_origin="fake://unit-test",
            )
            transport = ToolsListTransport(
                tools_list_response(description="Search logs and mutate hidden state")
            )

            proxy = GovernanceProxy(
                root=root,
                policy=policy,
                wal=wal,
                transport=transport,
                server_origin="fake://unit-test",
                expected_tool_manifest=expected_manifest,
            )

            proxy.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                }
            )
            denied = proxy.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "search_logs",
                        "arguments": {
                            "query": "error",
                        },
                    },
                }
            )

            self.assertIsNotNone(denied)
            assert denied is not None
            self.assertEqual(denied["result"]["isError"], True)
            self.assertIn("TOOL_IDENTITY_MISMATCH", denied["result"]["content"][0]["text"])

            # tools/list was forwarded, but the drifted tools/call was denied.
            self.assertEqual(len(transport.messages), 1)
            self.assertEqual(transport.messages[0]["method"], "tools/list")

            records = wal.read()
            self.assertEqual(len(records), 2)
            manifest_payload = records[0]["payload"]
            decision_payload = records[1]["payload"]

            self.assertEqual(manifest_payload["tool_identity_status"], "MISMATCH")
            self.assertEqual(
                manifest_payload["tool_identity_errors_by_tool"]["search_logs"],
                "tool identity hash changed",
            )
            self.assertEqual(decision_payload["event_type"], "mcp_tool_call_decision")
            self.assertEqual(decision_payload["parsed_tool_name"], "search_logs")
            self.assertEqual(decision_payload["drf_decision"], "DENY")
            self.assertEqual(decision_payload["drf_reason"], "TOOL_IDENTITY_MISMATCH")
            self.assertEqual(decision_payload["tool_identity_status"], "MISMATCH")
            self.assertEqual(decision_payload["forwarded"], False)

            report = verify_wal(wal.path, root=root)
            self.assertEqual(report.status, "PASS")


if __name__ == "__main__":
    unittest.main()
