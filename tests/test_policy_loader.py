from __future__ import annotations

from pathlib import Path

import pytest

from drf_omtir_flight_recorder.models import Decision
from drf_omtir_flight_recorder.policy_loader import PolicyLoadError, load_policy_yaml


ROOT = Path(__file__).resolve().parents[1]


def test_example_policy_denies_delete_index() -> None:
    policy = load_policy_yaml(ROOT / "policy" / "example-policy.yaml")

    rule = policy.rule_for("delete_index")

    assert rule is not None
    assert rule.decision == Decision.DENY
    assert rule.executable is False


def test_example_policy_allows_read_only_actions() -> None:
    policy = load_policy_yaml(ROOT / "policy" / "example-policy.yaml")

    assert policy.rule_for("search_logs") is not None
    assert policy.rule_for("search_logs").decision == Decision.ALLOW
    assert policy.rule_for("search_logs").executable is True

    assert policy.rule_for("read_metrics") is not None
    assert policy.rule_for("read_metrics").decision == Decision.ALLOW
    assert policy.rule_for("read_metrics").executable is True


def test_mutation_policy_allows_delete_index() -> None:
    policy = load_policy_yaml(ROOT / "tests" / "fixtures" / "mcp" / "policy_mutation_allow_delete_index.yaml")

    rule = policy.rule_for("delete_index")

    assert rule is not None
    assert rule.decision == Decision.ALLOW
    assert rule.executable is True


def test_restart_service_requests_review() -> None:
    policy = load_policy_yaml(ROOT / "policy" / "example-policy.yaml")

    rule = policy.rule_for("restart_service")

    assert rule is not None
    assert rule.decision == Decision.REQUEST_REVIEW
    assert rule.executable is False


def test_unknown_action_uses_default_decision() -> None:
    policy = load_policy_yaml(ROOT / "policy" / "example-policy.yaml")

    assert policy.rule_for("destroy_cluster") is None
    assert policy.unknown_action_decision == Decision.DENY


def test_unknown_top_level_key_rejected(tmp_path: Path) -> None:
    policy_path = tmp_path / "bad-policy.yaml"
    policy_path.write_text(
        """
version: drf-omtir-policy-v0.3
default_decision: DENY
actions: []
surprise: true
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(PolicyLoadError, match="unknown keys"):
        load_policy_yaml(policy_path)


def test_missing_actions_rejected(tmp_path: Path) -> None:
    policy_path = tmp_path / "bad-policy.yaml"
    policy_path.write_text(
        """
version: drf-omtir-policy-v0.3
default_decision: DENY
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(PolicyLoadError, match="actions"):
        load_policy_yaml(policy_path)


def test_invalid_decision_rejected(tmp_path: Path) -> None:
    policy_path = tmp_path / "bad-policy.yaml"
    policy_path.write_text(
        """
version: drf-omtir-policy-v0.3
default_decision: DENY
actions:
  - name: delete_index
    effect: DESTRUCTIVE
    decision: MAYBE
    executable: false
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(PolicyLoadError, match="decision"):
        load_policy_yaml(policy_path)