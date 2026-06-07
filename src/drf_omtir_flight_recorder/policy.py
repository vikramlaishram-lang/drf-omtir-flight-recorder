from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import Decision, Effect, EvidenceLane
from .wal import sha256_bytes


@dataclass(frozen=True)
class ActionRule:
    name: str
    effect: Effect
    decision: Decision
    required_evidence_lanes: list[EvidenceLane]
    executable: bool


class Policy:
    def __init__(
        self,
        *,
        version: str,
        rules: list[ActionRule],
        unknown_action_decision: Decision = Decision.DENY,
        proxy: dict[str, Any] | None = None,
        policy_hash: str | None = None,
        policy_source: str | None = None,
    ):
        self.version = version
        self.rules = {rule.name: rule for rule in rules}
        self.unknown_action_decision = unknown_action_decision
        self.proxy = proxy or {}
        self.policy_hash = policy_hash
        self.policy_source = policy_source

    @classmethod
    def load(cls, path: str | Path) -> "Policy":
        policy_path = Path(path)
        raw_bytes = policy_path.read_bytes()
        raw = json.loads(raw_bytes.decode("utf-8"))
        policy = cls.from_dict(raw)
        policy.policy_hash = sha256_bytes(raw_bytes)
        policy.policy_source = str(policy_path)
        return policy

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Policy":
        rules = [
            ActionRule(
                name=item["name"],
                effect=Effect(item["effect"]),
                decision=Decision(item["decision"]),
                required_evidence_lanes=[
                    EvidenceLane(value)
                    for value in item.get("required_evidence_lanes", [])
                ],
                executable=bool(item.get("executable", False)),
            )
            for item in raw.get("actions", [])
        ]

        return cls(
            version=raw.get("policy_version", "unknown"),
            rules=rules,
            unknown_action_decision=Decision(
                raw.get("unknown_action_decision", Decision.DENY.value)
            ),
            proxy=raw.get("proxy", {}),
            policy_hash=raw.get("policy_hash"),
            policy_source=raw.get("policy_source"),
        )

    def rule_for(self, action: str) -> ActionRule | None:
        return self.rules.get(action)

    def allowed_executable_actions(self) -> list[str]:
        return sorted(
            rule.name
            for rule in self.rules.values()
            if rule.decision == Decision.ALLOW and rule.executable
        )
