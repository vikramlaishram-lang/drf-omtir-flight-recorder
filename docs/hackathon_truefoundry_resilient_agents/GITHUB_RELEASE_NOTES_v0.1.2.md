# DRF + OMTIR Flight Recorder v0.1.2

## Governance Visibility Hardening

This release keeps the v0.1.1 TrueFoundry resilient-demo claim intact and makes the governance mechanism easier to inspect.

## What Changed

- WAL records now include explicit authority origin metadata, such as `DRF_RULE/delete_index` and `OMTIR_RULE/confirmed_claim_requires_valid_structural_link`.
- Verifier output now includes visible hash-chain links: `previous_hash -> record_hash -> next_hash`.
- The resilient Trust Receipt now shows governance consequences:
  - quarantined evidence is excluded from the confirmed claim set
  - rejected hypotheses are excluded from the confirmed claim set
  - confirmed claim events are listed
  - pending review events are listed
- `REQUEST_REVIEW` now produces a local review queue artifact at `reports/resilient-demo-review-queue.jsonl`.
- The resilient demo trace records the authority trace and review queue path.

## Demo

```bash
drf-omtir resilient-demo
drf-omtir verify wal/resilient-demo.jsonl
drf-omtir receipt wal/resilient-demo.jsonl
```

Expected:

```text
provider_route              -> TRUEFOUNDRY_GATEWAY
model                       -> GEMINI_FLASH_LITE
aws_bedrock                 -> NOT_USED
gateway_failure             -> RATE_LIMIT_EXCEEDED
rate_limit_rule             -> drf-omtir-resilience-rate-limit
unsafe_action               -> DENY
read_only_tool              -> ALLOW
bad_tool_result             -> QUARANTINED
unsupported_claim           -> REJECTED_HYPOTHESIS
evidence_linked_claim       -> CONFIRMED
risky_remediation           -> REQUEST_REVIEW
authority_trace             -> recorded
review_queue                -> generated
WAL records                 -> 6
verifier                    -> PASS
trust_receipt               -> generated
```

## Boundary

This release improves inspectability of the bounded TrueFoundry/Gemini resilient-demo story. It does not claim AWS Bedrock validation, production reliability, universal MCP compatibility, external notarization, enterprise compliance, or adversarial security certification.
