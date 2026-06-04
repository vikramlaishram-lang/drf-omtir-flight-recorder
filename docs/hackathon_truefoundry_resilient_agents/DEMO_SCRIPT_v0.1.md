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

2. Run:

```bash
drf-omtir resilient-demo
```

3. Run:

```bash
drf-omtir verify wal/resilient-demo.jsonl
```

4. Run:

```bash
drf-omtir receipt wal/resilient-demo.jsonl
```

5. Open:

```text
receipts/resilient-demo-trust-receipt.md
```

6. End with the boundary:

```text
AWS Bedrock was not used in this bounded run.
This does not claim production reliability, universal failure recovery, enterprise certification, or all-agent safety.
```

## Closing Line

The agent does not keep working by blindly continuing. It keeps working by narrowing authority, rejecting unsupported claims, routing risky actions to review, and producing a verifiable Trust Receipt.
