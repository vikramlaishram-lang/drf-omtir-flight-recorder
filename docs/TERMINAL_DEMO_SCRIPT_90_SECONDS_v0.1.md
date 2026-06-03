# Terminal Demo Script 60-90 Seconds v0.1

## Goal

Show the developer-facing MVP without making new validation claims.

## 0:00-0:10 Opening

Say:

```text
This is DRF + OMTIR Flight Recorder, a local MCP governance proxy for
tool-using AI agents.
```

Show:

```bash
drf-omtir --help
```

## 0:10-0:25 Initialize

Say:

```text
First I initialize a local governance workspace.
```

Run:

```bash
drf-omtir init
```

Show the created files:

```text
drf-omtir.yaml
wal/
receipts/
examples/
```

## 0:25-0:50 Demo

Say:

```text
Now I run the five-event accountability demo.
```

Run:

```bash
drf-omtir demo
```

Point at:

```text
delete_index             -> DENY
search_logs              -> ALLOW
unsupported CONFIRMED    -> REJECTED_HYPOTHESIS
evidence-linked claim    -> CONFIRMED
restart_service          -> REQUEST_REVIEW
WAL records              -> 5
Verifier                 -> PASS
Trust Receipt            -> generated
```

## 0:50-1:05 Verify

Say:

```text
The WAL is hash-chained and independently checked.
```

Run:

```bash
drf-omtir verify wal/demo.jsonl
```

Point at:

```text
status: PASS
records: 5
errors: []
```

## 1:05-1:20 Receipt

Say:

```text
The Trust Receipt turns the run into something a human can inspect.
```

Run:

```bash
drf-omtir receipt wal/demo.jsonl
```

Open or print the receipt path:

```text
receipts/demo-trust-receipt.md
```

## 1:20-1:30 Boundary

Say:

```text
This is a local product MVP, not a production certification. The evidence
ledger separates what has been proven from what is still future work.
```

End on:

```text
Model proposes. DRF decides action authority. OMTIR decides confirmation
authority. WAL records. Verifier checks. Trust Receipt explains.
```
