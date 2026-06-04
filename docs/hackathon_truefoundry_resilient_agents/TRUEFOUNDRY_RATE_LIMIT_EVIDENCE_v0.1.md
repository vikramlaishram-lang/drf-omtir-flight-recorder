# TrueFoundry Rate-Limit Evidence v0.1

```text
DRF + OMTIR Resilient Agent Trial v0.1:
TRUEFOUNDRY_GATEWAY_RESILIENT_AGENT_AND_TRUST_RECEIPT_PASS
```

## TrueFoundry Evidence

- Provider route: TrueFoundry AI Gateway
- Model: google-gemini/gemini-3.1-flash-lite
- Gateway zone: BOM
- Gateway region: IN
- Rate-limit rule: drf-omtir-resilience-rate-limit
- First request: SUCCEEDED
- Second request: RATE_LIMITED / HTTP 429
- AWS Bedrock: NOT_USED

## Local Proof

- Command: `drf-omtir resilient-demo`
- WAL: `wal/resilient-demo.jsonl`
- Verifier report: `reports/resilient-demo-verifier-report.json`
- Review queue: `reports/resilient-demo-review-queue.jsonl`
- Trust Receipt: `receipts/resilient-demo-trust-receipt.md`
- WAL records: 6
- Verifier: PASS

## Recovery Path

- unsafe_action -> DENY
- read_only_tool -> ALLOW
- bad_tool_result -> QUARANTINED
- unsupported_claim -> REJECTED_HYPOTHESIS
- evidence_linked_claim -> CONFIRMED
- risky_remediation -> REQUEST_REVIEW
- authority_trace -> recorded
- review_queue -> generated
- trust_receipt -> generated

## Governance Visibility

- Authority source is recorded in the WAL for each governed event.
- Example authority origins: `DRF_RULE/delete_index`, `DRF_RULE/restart_service`, and `OMTIR_RULE/confirmed_claim_requires_valid_structural_link`.
- Verifier output exposes hash links for reviewer inspection: `previous_hash -> record_hash -> next_hash`.
- The Trust Receipt explicitly excludes quarantined evidence and rejected hypotheses from the confirmed claim set.
- `REQUEST_REVIEW` produces a local review artifact at `reports/resilient-demo-review-queue.jsonl`.

## Boundary

This is a bounded resilient-agent demo using TrueFoundry AI Gateway with Gemini Flash Lite route metadata and a captured rate-limit failure marker. The live TrueFoundry evidence is the separate Request Trace screenshot showing the 429 rate-limit response. It does not claim AWS Bedrock validation, production reliability, universal failure recovery, enterprise certification, or all-agent safety.
