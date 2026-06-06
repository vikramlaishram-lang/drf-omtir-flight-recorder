# DRF + OMTIR Flight Recorder v0.3 — Policy YAML Schema

## Runtime policy source

v0.3 wrap mode must use the operator-supplied `--policy` file.

No silent `DEFAULT_POLICY` fallback is allowed in wrap mode.

## YAML loading security

Policy files must be loaded with `yaml.safe_load()`.

Do not use `yaml.load()`.

Arbitrary Python tags in `policy.yaml` must not execute.

Unknown top-level keys must be rejected.

## Minimum schema

```yaml
version: drf-omtir-policy-v0.3
default_decision: DENY
actions:
  - name: delete_index
    effect: DESTRUCTIVE
    decision: DENY
    executable: false
    reason: destructive_action
  - name: search_logs
    effect: READ_ONLY
    decision: ALLOW
    executable: true
    reason: read_only_observation
  - name: read_metrics
    effect: READ_ONLY
    decision: ALLOW
    executable: true
    reason: read_only_observation
  - name: restart_service
    effect: STATE_CHANGING
    decision: REQUEST_REVIEW
    executable: false
    reason: human_approval_required
```

## Validation rules

```text
version required
default_decision required
actions required and must be list
action.name required string
action.decision must be ALLOW / DENY / REQUEST_REVIEW
action.effect must be READ_ONLY / STATE_CHANGING / DESTRUCTIVE
action.executable required boolean
unknown action -> default_decision
default_decision should be DENY for governance use
unknown top-level keys rejected
```
