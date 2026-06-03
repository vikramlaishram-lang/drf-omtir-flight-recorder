# Show HN Post v0.1

## Title

```text
Show HN: DRF + OMTIR Flight Recorder - a local MCP governance proxy for AI agents
```

## Post

I built DRF + OMTIR Flight Recorder, a local MCP governance proxy for
tool-using AI agents.

The idea is simple: the model can propose actions and claims, but executable
authority and confirmed-claim authority stay outside the model.

DRF gates tool actions as `ALLOW`, `DENY`, or `REQUEST_REVIEW`.
OMTIR gates claims as `HYPOTHESIS`, `CONFIRMED`, or `REJECTED_HYPOTHESIS`.
The run is recorded in a hash-chained WAL, checked by a verifier, and
summarized in a Trust Receipt.

The developer-facing MVP has a small local CLI:

```bash
drf-omtir init
drf-omtir demo
drf-omtir verify wal/demo.jsonl
drf-omtir receipt wal/demo.jsonl
drf-omtir wrap --policy drf-omtir.yaml -- mcp-server-command
```

The demo produces this five-event trace:

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

The evidence ladder is deliberately bounded. There are frozen packages for a
Protocol SIFT-style forensic workflow, a real Elastic MCP tool-surface trial,
a Gemini / Google ADK live model-proposed action run, a generic gateway
kernel, a public inspection layer, and the new local Flight Recorder MVP.

The project does not claim production readiness, universal MCP compatibility,
Kubernetes enforcement, enterprise compliance, or domain-wide incident
accuracy. The operating rule is: do not let product vision outrun validation
evidence.

What I am trying to make inspectable is this product pattern:

```text
Model proposes -> DRF gates action -> typed MCP tool runs -> OMTIR gates claim -> WAL -> verifier -> Trust Receipt
```

I would value feedback on the local MCP proxy shape, policy format, and what
reviewers would want to inspect before trusting an agent action trace.
