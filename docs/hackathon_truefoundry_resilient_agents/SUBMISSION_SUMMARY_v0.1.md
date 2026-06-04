# DRF + OMTIR Flight Recorder for Resilient Agents

## Problem

AI agents can continue acting after provider failures, weak tool results, or model overclaims. Resilience alone can keep an agent moving, but it does not decide whether the next action is safe or whether a claim is evidence-backed.

## Solution

DRF + OMTIR Flight Recorder is a local MCP governance proxy. DRF keeps executable authority outside the model. OMTIR keeps confirmed-claim authority tied to evidence. The WAL records the run, the verifier checks it, and the Trust Receipt explains the recovery path.

## Failure Introduced

The bounded resilient-agent story uses TrueFoundry AI Gateway route metadata and a captured rate-limit failure marker.

```text
Provider route: TrueFoundry AI Gateway
Model route: Gemini Flash Lite
Rate-limit rule: drf-omtir-resilience-rate-limit
First request: SUCCEEDED
Second request: RATE_LIMITED / HTTP 429
AWS Bedrock: NOT_USED
```

## Handling And Recovery Path

```text
unsafe_action         -> DENY
read_only_tool        -> ALLOW
bad_tool_result       -> QUARANTINED
unsupported_claim     -> REJECTED_HYPOTHESIS
evidence_linked_claim -> CONFIRMED
risky_remediation     -> REQUEST_REVIEW
authority_trace       -> recorded
review_queue          -> generated
trust_receipt         -> generated
```

The agent does not keep working by blindly continuing. It keeps working by narrowing authority, rejecting unsupported claims, routing risky actions to review, and producing a verifiable Trust Receipt.

The trace now makes the authority hierarchy explicit: every governed event includes an authority origin such as `DRF_RULE/delete_index` or `OMTIR_RULE/confirmed_claim_requires_valid_structural_link`. The Trust Receipt also records the downstream consequence of governance states: quarantined evidence and rejected hypotheses are excluded from the confirmed claim set, and the risky remediation event is written to a local human-review queue.

## Final User Experience

Reviewers can run:

```bash
drf-omtir resilient-demo
drf-omtir verify wal/resilient-demo.jsonl
drf-omtir receipt wal/resilient-demo.jsonl
```

The expected result is a six-record WAL, verifier PASS, and a Trust Receipt that records the TrueFoundry/Gemini route metadata, rate-limit marker, action decisions, claim decisions, and recovery boundary.

## Evidence Artifacts

- `wal/resilient-demo.jsonl`
- `reports/resilient-demo-verifier-report.json`
- `reports/resilient-demo-trace.json`
- `reports/resilient-demo-review-queue.jsonl`
- `receipts/resilient-demo-trust-receipt.md`
- `examples/resilient-demo-search-logs-result.json`
- `examples/resilient-demo-quarantined-tool-result.json`
- TrueFoundry Request Trace screenshot showing the HTTP 429 rate-limit response

The verifier report includes visible hash-chain links for reviewer inspection:

```text
previous_hash -> record_hash -> next_hash
status: PASS
records: 6
errors: []
```

## Boundary

This is a bounded resilient-agent demo using TrueFoundry/Gemini route metadata and a captured rate-limit marker. The Elastic-style read-only tool output in the local demo is a deterministic fixture, and the live TrueFoundry evidence is the separate Request Trace screenshot. This does not claim AWS Bedrock validation, production reliability, universal failure recovery, enterprise certification, or all-agent safety.
