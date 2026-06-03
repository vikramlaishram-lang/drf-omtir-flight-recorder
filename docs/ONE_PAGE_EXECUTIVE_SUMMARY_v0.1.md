# DRF + OMTIR Executive Summary v0.1

## Problem

Tool-using AI agents can propose actions and operational claims faster than
humans can verify them.

An unsafe design collapses proposal, execution, and trust into one step:

```text
Model decides -> tool executes -> model claim is accepted
```

## Mechanism

DRF + OMTIR separates those authorities:

```text
Model proposes
        |
        v
DRF decides whether the action may execute
        |
        v
Typed MCP tool executes only after ALLOW
        |
        v
OMTIR decides whether evidence supports confirmation
        |
        v
WAL records the action-and-claim trace
        |
        v
Independent verifier checks the run
        |
        v
Trust Receipt explains the result
```

DRF governs executable authority. OMTIR governs confirmed-claim authority.
Both decisions remain outside the model.

## Frozen Evidence Ladder

```text
1. SIFT v0.2.4
   First bounded live forensic / MCP mechanism proof.

2. Generic Gateway v0.1
   Reusable kernel extracted and conformance tested.

3. DevOps / Elastic v0.1
   Second bounded live tool-surface validation with real Elastic MCP.

4. Public Inspection Layer v0.1
   Reusable evidence ledger and Trust Receipt inspection format.

5. Gemini / Google ADK v0.1
   Live model-proposed action and claim governance proof.

6. MCP Flight Recorder v0.1
   Local developer-facing governance proxy MVP.
```

## Strongest Current Claim

DRF + OMTIR has demonstrated live model-proposed action and claim governance
in a bounded Gemini / Google ADK workflow. Gemini proposed actions and claims,
while DRF controlled executable authority and OMTIR controlled
confirmed-claim authority.

## Boundary

The evidence does not prove production readiness, universal portability,
Gemini reliability, Kubernetes enforcement, populated incident evidence,
remote Elastic dataset immutability, enterprise deployment certification, or
domain-wide accuracy.

The Elastic result returned:

```text
groups: []
```

The earned claim is governance-path validation, not incident-detection
accuracy.

## Product MVP

DRF + OMTIR Flight Recorder is the current local product shape. It exposes a
small command surface:

```text
init -> demo -> verify -> receipt -> wrap
```

The MVP demonstrates developer-facing usability. It does not expand the live
validation claims beyond the frozen evidence ladder.
