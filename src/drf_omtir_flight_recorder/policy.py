from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import Decision, Effect, EvidenceLane


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
    ):
        self.version = version
        self.rules = {rule.name: rule for rule in rules}
        self.unknown_action_decision = unknown_action_decision
        self.proxy = proxy or {}

    @classmethod
    def load(cls, path: str | Path) -> "Policy":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Policy":
        rules = [
            ActionRule(
                name=item["name"],
                effect=Effect(item["effect"]),
                decision=Decision(item["decision"]),
                required_evidence_lanes=[EvidenceLane(value) for value in item.get("required_evidence_lanes", [])],
                executable=bool(item.get("executable", False)),
            )
            for item in raw.get("actions", [])
        ]
        return cls(
            version=raw.get("policy_version", "unknown"),
            rules=rules,
            unknown_action_decision=Decision(raw.get("unknown_action_decision", Decision.DENY.value)),
            proxy=raw.get("proxy", {}),
        )

    def rule_for(self, action: str) -> ActionRule | None:
        return self.rules.get(action)

    def allowed_executable_actions(self) -> list[str]:
        return sorted(
            rule.name
            for rule in self.rules.values()
            if rule.decision == Decision.ALLOW and rule.executable
        )
