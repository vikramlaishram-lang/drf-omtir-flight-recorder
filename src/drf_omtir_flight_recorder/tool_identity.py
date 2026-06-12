from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .wal import canonical_json, sha256_bytes


@dataclass(frozen=True)
class ToolIdentity:
    tool_name: str
    server_origin: str
    input_schema_hash: str
    description_hash: str
    read_only_hint: bool | None
    destructive_hint: bool | None
    idempotent_hint: bool | None
    identity_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "server_origin": self.server_origin,
            "input_schema_hash": self.input_schema_hash,
            "description_hash": self.description_hash,
            "readOnlyHint": self.read_only_hint,
            "destructiveHint": self.destructive_hint,
            "idempotentHint": self.idempotent_hint,
            "identity_hash": self.identity_hash,
        }


@dataclass(frozen=True)
class ToolIdentityManifest:
    server_origin: str
    manifest_hash: str
    tools: dict[str, ToolIdentity]

    def to_dict(self) -> dict[str, Any]:
        return {
            "server_origin": self.server_origin,
            "manifest_hash": self.manifest_hash,
            "tools": [
                self.tools[name].to_dict()
                for name in sorted(self.tools)
            ],
        }


def build_tool_identity_manifest(
    tools_list_response: dict[str, Any],
    *,
    server_origin: str,
) -> ToolIdentityManifest:
    tools = _extract_tools(tools_list_response)
    identities: dict[str, ToolIdentity] = {}

    for tool in tools:
        if not isinstance(tool, dict):
            continue

        tool_name = tool.get("name")

        if not isinstance(tool_name, str) or not tool_name:
            continue

        annotations = tool.get("annotations")
        if not isinstance(annotations, dict):
            annotations = {}

        input_schema = tool.get("inputSchema", tool.get("input_schema", {}))
        if input_schema is None:
            input_schema = {}

        description = tool.get("description", "")
        if description is None:
            description = ""

        input_schema_hash = sha256_bytes(canonical_json(input_schema))
        description_hash = sha256_bytes(canonical_json(str(description)))
        read_only_hint = _hint(tool, annotations, "readOnlyHint", "read_only_hint")
        destructive_hint = _hint(tool, annotations, "destructiveHint", "destructive_hint")
        idempotent_hint = _hint(tool, annotations, "idempotentHint", "idempotent_hint")
        identity_body = {
            "tool_name": tool_name,
            "server_origin": server_origin,
            "input_schema_hash": input_schema_hash,
            "description_hash": description_hash,
            "readOnlyHint": read_only_hint,
            "destructiveHint": destructive_hint,
            "idempotentHint": idempotent_hint,
        }
        identity_hash = sha256_bytes(canonical_json(identity_body))
        identities[tool_name] = ToolIdentity(
            tool_name=tool_name,
            server_origin=server_origin,
            input_schema_hash=input_schema_hash,
            description_hash=description_hash,
            read_only_hint=read_only_hint,
            destructive_hint=destructive_hint,
            idempotent_hint=idempotent_hint,
            identity_hash=identity_hash,
        )

    manifest_body = {
        "server_origin": server_origin,
        "tools": [
            identities[name].to_dict()
            for name in sorted(identities)
        ],
    }
    manifest_hash = sha256_bytes(canonical_json(manifest_body))
    return ToolIdentityManifest(
        server_origin=server_origin,
        manifest_hash=manifest_hash,
        tools=identities,
    )


def compare_tool_identity_manifests(
    expected: ToolIdentityManifest,
    observed: ToolIdentityManifest,
) -> dict[str, str]:
    errors: dict[str, str] = {}

    for tool_name, expected_tool in expected.tools.items():
        observed_tool = observed.tools.get(tool_name)

        if observed_tool is None:
            errors[tool_name] = "tool missing from observed manifest"
            continue

        if observed_tool.identity_hash != expected_tool.identity_hash:
            errors[tool_name] = "tool identity hash changed"

    for tool_name in observed.tools:
        if tool_name not in expected.tools:
            errors[tool_name] = "tool not present in expected manifest"

    return errors


def _extract_tools(tools_list_response: dict[str, Any]) -> list[Any]:
    result = tools_list_response.get("result")

    if isinstance(result, dict) and isinstance(result.get("tools"), list):
        return result["tools"]

    if isinstance(tools_list_response.get("tools"), list):
        return tools_list_response["tools"]

    return []


def _hint(tool: dict[str, Any], annotations: dict[str, Any], *names: str) -> bool | None:
    for source in (annotations, tool):
        for name in names:
            value = source.get(name)

            if isinstance(value, bool):
                return value

    return None
