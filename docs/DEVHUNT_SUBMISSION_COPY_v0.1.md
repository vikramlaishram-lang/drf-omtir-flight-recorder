# DevHunt Submission Copy v0.1

## Product Name

```text
DRF + OMTIR Flight Recorder
```

## Tagline

```text
A local MCP governance proxy that keeps agent authority bounded and makes claims provable.
```

## Short Description

DRF + OMTIR Flight Recorder is a local governance proxy for tool-using AI
agents. It sits between an agent and an MCP tool surface, gates proposed
actions with deterministic policy, gates confirmed claims on evidence linkage,
records the run in a hash-chained WAL, verifies the trace, and generates a
human-readable Trust Receipt.

## What It Does

```text
- Initializes a local governance workspace.
- Runs a five-event accountability demo.
- Wraps a local MCP server path in a governance proxy.
- Denies unsafe actions before execution.
- Allows read-only actions and records STRUCTURAL evidence.
- Rejects unsupported model-only CONFIRMED claims.
- Admits evidence-linked CONFIRMED claims.
- Routes higher-impact actions to REQUEST_REVIEW.
- Verifies the WAL.
- Generates a Trust Receipt.
```

## Why It Matters

Tool-using AI agents can propose actions and operational conclusions faster
than humans can inspect them. DRF + OMTIR separates proposal from authority:
the model can suggest, but the governance layer decides what can execute and
what can be treated as confirmed.

## Demo Command

```bash
drf-omtir demo
```

Expected result:

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

## Evidence

The public review package indexes six evidence layers:

```text
1. SIFT v0.2.4 - bounded live forensic / MCP validation.
2. Gateway v0.1 - generic kernel extracted and conformance tested.
3. DevOps / Elastic v0.1 - second bounded live MCP tool-surface validation.
4. Public Inspection Layer v0.1 - reviewer evidence format.
5. Gemini / Google ADK v0.1 - live model-proposed governance proof.
6. MCP Flight Recorder v0.1 - local developer-facing governance proxy MVP.
```

## Boundary

This is not a production certification, hosted governance service, universal
MCP compatibility claim, Kubernetes enforcement claim, or incident-detection
accuracy claim. It is a local product MVP backed by bounded frozen evidence.
