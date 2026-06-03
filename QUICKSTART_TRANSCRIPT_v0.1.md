# DRF + OMTIR Flight Recorder Quickstart Transcript v0.1

## Init

```bash
drf-omtir init
```

Expected result:

```text
drf-omtir.yaml created
wal/ created
receipts/ created
examples/ created
reports/ created
```

## Demo

```bash
drf-omtir demo
```

Expected result:

```text
DRF + OMTIR MCP Flight Recorder v0.1
Status: PASS
delete_index             -> DENY
search_logs              -> ALLOW
unsupported CONFIRMED    -> REJECTED_HYPOTHESIS
evidence-linked claim    -> CONFIRMED
restart_service          -> REQUEST_REVIEW
WAL records              -> 5
Verifier                 -> PASS
Trust Receipt            -> generated
```

## Verify

```bash
drf-omtir verify wal/demo.jsonl
```

Expected result:

```json
{
  "errors": [],
  "records": 5,
  "status": "PASS",
  "verifier": "drf_omtir_flight_recorder_verifier"
}
```

## Receipt

```bash
drf-omtir receipt wal/demo.jsonl
```

Expected result:

```text
Trust Receipt: receipts/demo-trust-receipt.md
```

## Wrap

```bash
drf-omtir wrap --policy drf-omtir.yaml -- mcp-server-command
```

Purpose:

```text
Runs a local governance proxy between an MCP client and an existing MCP server. Tool calls are checked against policy before they reach the child MCP server, and governance decisions are recorded in the WAL.
```

## Boundary

```text
This quickstart demonstrates local product behavior only. It does not claim production deployment, cloud service readiness, universal MCP compatibility, external notarization, enterprise compliance, or adversarial security certification.
```
