# Demo Script v0.1

## Flow

1. Show the TrueFoundry Request Trace screenshot or trace details:

```text
first request: successful
second request: rate-limited with HTTP 429
rule: drf-omtir-resilience-rate-limit
model route: google-gemini/gemini-3.1-flash-lite
AWS Bedrock: NOT_USED
```

2. Show the authority manifest:

```text
docs/hackathon_truefoundry_resilient_agents/AUTHORITY_MANIFEST_v0.1.md
```

Point at the hierarchy:

```text
Model proposes only
DRF decides action authority
OMTIR decides confirmed-claim authority
WAL is the source-of-truth trace
Verifier checks the trace
Trust Receipt explains the trace
```

3. Run:

```bash
drf-omtir resilient-demo
```

4. Run:

```bash
drf-omtir verify wal/resilient-demo.jsonl
```

Point at the visible hash chain fields:

```text
previous_hash -> record_hash -> next_hash
status: PASS
records: 6
errors: []
```

5. Run:

```bash
drf-omtir receipt wal/resilient-demo.jsonl
```

6. Open:

```text
receipts/resilient-demo-trust-receipt.md
```

7. Show the governance consequences:

```text
WAL SHA-256
Last record hash
Quarantined evidence excluded from confirmed claim set
Rejected hypotheses excluded from confirmed claim set
Pending human review events
Review queue: reports/resilient-demo-review-queue.jsonl
```

8. End with the boundary:

```text
AWS Bedrock was not used in this bounded run.
This does not claim production reliability, universal failure recovery, enterprise certification, or all-agent safety.
```

## Closing Line

The agent does not keep working by blindly continuing. It keeps working by narrowing authority, rejecting unsupported claims, routing risky actions to review, and producing a verifiable Trust Receipt.
