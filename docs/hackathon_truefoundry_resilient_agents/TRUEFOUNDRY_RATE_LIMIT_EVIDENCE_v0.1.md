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
- trust_receipt -> generated

## Boundary

This is a bounded resilient-agent demo using TrueFoundry AI Gateway with Gemini Flash Lite route metadata and a captured rate-limit failure marker. The live TrueFoundry evidence is the separate Request Trace screenshot showing the 429 rate-limit response. It does not claim AWS Bedrock validation, production reliability, universal failure recovery, enterprise certification, or all-agent safety.
