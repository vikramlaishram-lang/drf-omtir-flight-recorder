# DRF + OMTIR 3-Minute Demo Script v0.1

## Title

**DRF + OMTIR: Governing AI Agent Actions and Claims**

## Duration

Approximately 3 minutes.

---

## 0:00-0:20 - Opening

**On screen:** Open `README.md`, then show the architecture diagram.

Today I am showing DRF + OMTIR, a governed action-accountability layer for
tool-using AI agents.

The core idea is simple:

The model can propose actions and claims, but executable authority and
confirmed-claim authority stay outside the model.

DRF decides whether an action can execute. OMTIR decides whether a claim can
be treated as confirmed. The WAL records the run. The verifier checks the
trace. The Trust Receipt explains the result.

---

## 0:20-0:50 - Problem

**On screen:** Keep the architecture diagram visible and highlight the
separation between the model and the authority boundary.

AI agents are increasingly able to call tools, search systems, trigger
workflows, and produce operational conclusions.

That creates two risks.

First: the model may propose an unsafe action.

Second: the model may make a confident claim without evidence.

DRF + OMTIR addresses both risks by separating model proposal from
operational authority.

---

## 0:50-1:25 - Evidence Ladder

**On screen:** Open `docs/DRF_OMTIR_EVIDENCE_LEDGER_v0.1.md` and scroll
through the five numbered entries.

This repository contains a public reviewer package that indexes five earned
layers.

First, a Protocol SIFT proof showed the mechanism in a bounded forensic
workflow.

Second, the mechanism was extracted into a reusable generic gateway.

Third, a live Elastic MCP trial showed the same governance path over a real
authenticated MCP tool surface.

Fourth, the public inspection layer packaged the evidence ledger, verifier
format, Trust Receipt template, and boundary statements.

Fifth, the strongest current run used Gemini through Google ADK. In that run,
Gemini proposed actions and claims, while DRF and OMTIR remained the authority
boundary.

---

## 1:25-2:15 - Strongest Frozen Run

**On screen:** Show the strongest frozen milestone in `README.md`, then keep
the five-event sequence visible.

The strongest frozen milestone is:

`DRF + OMTIR Gemini / Google ADK Trial v0.1:
LIVE_MODEL_PROPOSED_ACTION_GATE_AND_VERIFIER_PASS`

In that run:

An unsafe shell action was proposed and denied.

A real authenticated read-only Elastic MCP tool call was allowed.

An unsupported model-only confirmed claim was denied.

A narrower evidence-linked confirmed claim was admitted.

A restart action was routed to review.

The result was a five-record WAL, independent verifier PASS, and a generated
Trust Receipt.

This proves live model-proposed action and claim governance in one bounded
workflow.

---

## 2:15-2:40 - What This Does Not Claim

**On screen:** Open `docs/BOUNDARY_STATEMENT_v0.1.md`.

The boundary is important.

This does not claim production readiness.

It does not claim universal portability.

It does not claim Kubernetes enforcement.

It does not claim incident-detection accuracy.

The Elastic response returned `groups: []`, so the Elastic run proves the live
governance path, not populated incident evidence.

The rule is: do not let product vision outrun validation evidence.

---

## 2:40-3:00 - Reviewer Path

**On screen:** Return to the Reviewer Path section in `README.md`.

For reviewers, start with `README.md`.

Then open the executive summary, architecture diagram, and evidence ledger.

From there, inspect the frozen packages, WALs, verifier reports, Trust
Receipts, and SHA-256 records.

The product thesis is this:

DRF + OMTIR does not try to make the model perfectly trustworthy. It makes
the model's authority conditional on deterministic checks, evidence links,
and verifiable records.

---

## Pre-Publication Blockers

Before publishing the GitHub release:

```text
1. Revoke the exposed Gemini API key in Google AI Studio.
2. Select and add a license.
```

Recommended license:

```text
Apache-2.0
```

Reason: this project is infrastructure and governance middleware, so a
permissive license with explicit patent language is a good default.

