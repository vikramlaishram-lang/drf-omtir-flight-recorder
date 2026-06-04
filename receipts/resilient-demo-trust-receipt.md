# DRF + OMTIR Flight Recorder Trust Receipt v0.1

Generated: 2026-06-04T18:50:13.681174Z
WAL: C:\Users\vikra\Documents\GitHub\drf-omtir-flight-recorder\wal\resilient-demo.jsonl
WAL SHA-256: a0dc07acf96e1bc405b799ecdaf7d3593e7668d18c2fa654f0b927d779159ee2
Records: 6
Last record hash: 910867d03e96ca728f234b226837c2f803bcf5001c6c2b1e0838521fd582ad9a

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

## Governance Consequences

- Quarantined evidence excluded from confirmed claim set: evt_000003
- Rejected hypotheses excluded from confirmed claim set: evt_000004
- Confirmed claim events admitted: evt_000005
- Pending human review events: evt_000006
- Review queue: reports/resilient-demo-review-queue.jsonl

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
