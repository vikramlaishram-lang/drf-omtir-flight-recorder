# Product Hunt Teaser Copy v0.1

## Product Name

```text
DRF + OMTIR Flight Recorder
```

## Tagline Options

```text
Keep agent authority bounded. Make every claim provable.
```

```text
A local MCP governance proxy for AI agent actions and claims.
```

```text
The flight recorder for tool-using AI agents.
```

## Short Description

DRF + OMTIR Flight Recorder is a local MCP governance proxy that gates AI
agent tool calls, records action and claim decisions, verifies the WAL, and
generates Trust Receipts.

## Launch Blurb

AI agents are getting better at calling tools, but authority should not live
inside the model.

DRF + OMTIR Flight Recorder keeps model proposals separate from executable
authority and confirmed-claim authority. It can deny unsafe tool calls, allow
read-only evidence-producing actions, reject unsupported confirmed claims,
admit evidence-linked claims, verify the run, and generate a readable Trust
Receipt.

The v0.1 MVP is intentionally local and narrow:

```text
init -> demo -> verify -> receipt -> wrap
```

It is not a hosted platform or production certification. It is a developer
entry point for a bounded, evidence-backed governance mechanism.

## First Comment Draft

Thanks for taking a look.

The core design rule is: do not let product vision outrun validation evidence.

This release includes a local MCP governance proxy MVP plus a public evidence
ledger. The strongest frozen run used Gemini through Google ADK, a real
Elastic MCP tools/call, a five-record WAL, independent verifier PASS, and a
Trust Receipt.

The boundaries matter: this does not claim production readiness, enterprise
compliance, universal MCP compatibility, or incident-detection accuracy.

I would love feedback on the policy format, Trust Receipt format, and what
developers would expect from a local MCP governance proxy.
