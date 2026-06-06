from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import Decision, Effect, EvidenceLane
from .policy import ActionRule, Policy


class PolicyLoadError(ValueError):
    """Raised when a v0.3 operator policy file is invalid."""


_ALLOWED_TOP_LEVEL_KEYS = {"version", "default_decision", "actions"}
_ALLOWED_ACTION_KEYS = {
    "name",
    "effect",
    "decision",
    "executable",
    "reason",
    "required_evidence_lanes",
}


def _require_mapping(value: Any, *, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PolicyLoadError(f"{where} must be a mapping/object")
    return value


def _reject_unknown_keys(raw: dict[str, Any], allowed: set[str], *, where: str) -> None:
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise PolicyLoadError(f"{where} contains unknown keys: {', '.join(unknown)}")


def _parse_decision(value: Any, *, where: str) -> Decision:
    if not isinstance(value, str):
        raise PolicyLoadError(f"{where} must be a string")
    try:
        return Decision(value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in Decision)
        raise PolicyLoadError(f"{where} must be one of: {allowed}") from exc


def _parse_effect(value: Any, *, where: str) -> Effect:
    if not isinstance(value, str):
        raise PolicyLoadError(f"{where} must be a string")
    try:
        return Effect(value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in Effect)
        raise PolicyLoadError(f"{where} must be one of: {allowed}") from exc


def _parse_evidence_lanes(value: Any, *, where: str) -> list[EvidenceLane]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise PolicyLoadError(f"{where} must be a list")
    lanes: list[EvidenceLane] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise PolicyLoadError(f"{where}[{index}] must be a string")
        try:
            lanes.append(EvidenceLane(item))
        except ValueError as exc:
            allowed = ", ".join(lane.value for lane in EvidenceLane)
            raise PolicyLoadError(f"{where}[{index}] must be one of: {allowed}") from exc
    return lanes


def load_policy_yaml(path: str | Path) -> Policy:
    """Load a v0.3 operator policy file using yaml.safe_load.

    This is the v0.3 wrap-mode loader. It intentionally does not fall back
    to DEFAULT_POLICY. Invalid or missing policy files fail closed by raising
    PolicyLoadError.
    """

    policy_path = Path(path)
    if not policy_path.exists():
        raise PolicyLoadError(f"policy file missing: {policy_path}")

    try:
        loaded = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PolicyLoadError(f"policy YAML parse failed: {exc}") from exc

    raw = _require_mapping(loaded, where="policy")
    _reject_unknown_keys(raw, _ALLOWED_TOP_LEVEL_KEYS, where="policy")

    version = raw.get("version")
    if not isinstance(version, str) or not version:
        raise PolicyLoadError("policy.version is required and must be a non-empty string")

    default_decision = _parse_decision(raw.get("default_decision"), where="policy.default_decision")

    actions = raw.get("actions")
    if not isinstance(actions, list):
        raise PolicyLoadError("policy.actions is required and must be a list")

    rules: list[ActionRule] = []
    seen_names: set[str] = set()

    for index, item in enumerate(actions):
        action = _require_mapping(item, where=f"policy.actions[{index}]")
        _reject_unknown_keys(action, _ALLOWED_ACTION_KEYS, where=f"policy.actions[{index}]")

        name = action.get("name")
        if not isinstance(name, str) or not name:
            raise PolicyLoadError(f"policy.actions[{index}].name is required and must be a non-empty string")
        if name in seen_names:
            raise PolicyLoadError(f"duplicate action rule: {name}")
        seen_names.add(name)

        executable = action.get("executable")
        if not isinstance(executable, bool):
            raise PolicyLoadError(f"policy.actions[{index}].executable is required and must be boolean")

        rules.append(
            ActionRule(
                name=name,
                effect=_parse_effect(action.get("effect"), where=f"policy.actions[{index}].effect"),
                decision=_parse_decision(action.get("decision"), where=f"policy.actions[{index}].decision"),
                required_evidence_lanes=_parse_evidence_lanes(
                    action.get("required_evidence_lanes", []),
                    where=f"policy.actions[{index}].required_evidence_lanes",
                ),
                executable=executable,
            )
        )

    return Policy(
        version=version,
        rules=rules,
        unknown_action_decision=default_decision,
        proxy={},
    )