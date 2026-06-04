# DRF + OMTIR Flight Recorder Trust Receipt v0.1

Generated: 2026-06-04T08:52:42.769744Z
WAL: wal\resilient-demo.jsonl
Records: 6
Last record hash: c4948e138432bd9d50d0a98534a9e977f1763898f1cced27ec0487957fd426ec

## Action Decisions

- ALLOW: 2
- DENY: 1
- REQUEST_REVIEW: 1

## Claim Statuses

- CONFIRMED: 1
- REJECTED_HYPOTHESIS: 1

## Verifier

- Status: PASS
- Records checked: 6
- Errors: []

## Resilience Context

- Failure introduced: TrueFoundry AI Gateway rate limit
- Gateway failure: RATE_LIMIT_EXCEEDED
- Rate-limit rule: drf-omtir-resilience-rate-limit
- Model route: TRUEFOUNDRY_GATEWAY -> GEMINI_FLASH_LITE
- AWS Bedrock: NOT_USED
- First request: SUCCEEDED
- Second request: RATE_LIMITED
- Recovery path: unsafe action denied, weak result quarantined, unsupported claim rejected, evidence-linked claim confirmed, risky remediation routed to review.

## Boundary

This Trust Receipt explains one local DRF + OMTIR Flight Recorder run. It does not claim production deployment, cloud service readiness, universal MCP compatibility, external notarization, enterprise compliance, or adversarial security certification.
