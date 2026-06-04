# DRF + OMTIR Flight Recorder Trust Receipt v0.1

Generated: 2026-06-04T09:58:12.538651Z
WAL: wal\resilient-demo.jsonl
Records: 6
Last record hash: 8f80895ae6cea638d131af716c3eaaafadca9495bd863425ccfc081bba4aca28

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
- TrueFoundry evidence: separate Request Trace screenshot showing the 429 rate-limit response.
- Recovery path: unsafe action denied, weak result quarantined, unsupported claim rejected, evidence-linked claim confirmed, risky remediation routed to review.
- Boundary: AWS Bedrock was not used in this bounded run. This does not claim AWS Bedrock validation, production reliability, universal failure recovery, enterprise certification, or all-agent safety.

## Boundary

This Trust Receipt explains one local DRF + OMTIR Flight Recorder run. It does not claim production deployment, cloud service readiness, universal MCP compatibility, external notarization, enterprise compliance, or adversarial security certification.
