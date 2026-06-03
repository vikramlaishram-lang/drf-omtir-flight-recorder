# DRF + OMTIR Evidence Ledger v0.1

Status:

```text
FROZEN_EVIDENCE_INDEX
```

Recorded:

```text
2026-06-02
```

## Internal Rule

```text
Do not let product vision outrun validation evidence.
```

This ledger indexes earned validation claims. Each entry records a bounded
result and its boundary. A later application domain must earn its own frozen
evidence record.

## 1. Protocol SIFT v0.2.4

Milestone:

```text
DRF + OMTIR Protocol SIFT Testbed v0.2.4:
LIVE_MCP_TYPED_ACTION_GATE_AND_VERIFIER_PASS
```

Status:

```text
PASS
Bounded live forensic / SIFT validation anchor
```

Frozen anchor package:

```text
DRF_OMTIR_SIFT_LIVE_MCP_TYPED_ACTION_GATE_AND_VERIFIER_PASS_v0_2_4.zip
SHA-256:
6e0b61d7a7ce805e74e03d86be5122dade9a5f41aac701ea5b846cc90648f3ce
```

Workspace documentation spine:

```text
DRF_OMTIR_SIFT_JUDGE_SUBMISSION_SPINE_v0_2_4.zip
SHA-256:
DFC8DD9CABDD12076988F7176B65EE4E8498C570E88D0F304B709A90331E2474
```

What it proves:

```text
- A live Protocol SIFT-style typed MCP workflow denied generic shell execution.
- A typed read-only `fls` action executed and emitted STRUCTURAL evidence.
- Evidence hashes before and after execution were identical for the frozen run.
- A model-only CONFIRMED claim was denied.
- A STRUCTURAL-linked CONFIRMED claim was admitted.
- Four WAL records passed independent verification.
```

What it does not prove:

```text
- Full DFIR ground-truth accuracy
- Complete artifact coverage
- Production certification
- Universal immutability
- Autonomous senior-analyst equivalence
- Validation in non-forensic domains
```

Note:

```text
The frozen anchor ZIP was generated inside the SIFT workstation. This
workspace contains its judge-submission documentation spine, not a replacement
for the immutable anchor.
```

## 2. Generic Gateway v0.1

Milestone:

```text
DRF + OMTIR Gateway v0.1:
GENERIC_KERNEL_EXTRACTED_AND_CONFORMANCE_TESTED
```

Status:

```text
PASS
Reusable generic kernel conformance tested
```

Package:

```text
DRF_OMTIR_GATEWAY_GENERIC_KERNEL_v0_1.zip
SHA-256:
4045DDEFBB6F06A69BAD77BB095D1AC91B99ADC1CE17BB9A44505DD1A6DBD1FF
```

What it proves:

```text
- The SIFT-earned mechanism was extracted into a generic typed
  action-accountability kernel.
- Deterministic conformance fixtures test action gating, evidence-linked claim
  admission, WAL generation, independent verification, Trust Receipt
  generation, and tamper rejection.
```

What it does not prove:

```text
- A second live-domain validation
- Standards-complete MCP compatibility
- Production deployment readiness
- Enterprise security certification
- Universal portability
```

## 3. DevOps / Elastic v0.1

Milestone:

```text
DRF + OMTIR DevOps Portability Trial v0.1:
LIVE_DEVOPS_ELASTIC_MCP_ACTION_GATE_AND_VERIFIER_PASS
```

Status:

```text
PASS
Second bounded live tool-surface validation
```

Package:

```text
DRF_OMTIR_DEVOPS_LIVE_ELASTIC_MCP_ACTION_GATE_AND_VERIFIER_PASS_v0_1.zip
SHA-256:
19569FE1DC589A437FB536B0F370F8E0FE2B5639E3D42CA5C7D19533711BEC1E
```

What it proves:

```text
- A real Elastic MCP endpoint authenticated successfully.
- MCP initialize and tools/list discovery passed.
- One real authenticated observability_get_log_groups tools/call executed.
- Unsafe generic shell execution was denied.
- The allowed Elastic MCP result was persisted as STRUCTURAL evidence.
- An unsupported model-only CONFIRMED claim was denied.
- A narrower STRUCTURAL-linked CONFIRMED claim was admitted.
- restart_deployment was routed to REQUEST_REVIEW.
- Five WAL records passed independent verification.
- A Trust Receipt was generated.
```

What it does not prove:

```text
- Populated operational evidence: the Elastic response returned groups: []
- Incident-detection accuracy
- Elastic observability quality
- Remote Elastic dataset immutability
- Kubernetes enforcement
- Gemini / Google ADK integration
- Production readiness
- Universal portability
```

## 4. Public Inspection Layer v0.1

Milestone:

```text
DRF + OMTIR Public Inspection Layer v0.1:
EVIDENCE_LEDGER_AND_TRUST_RECEIPT_FORMAT_READY
```

Status:

```text
PASS
Reusable public inspection format ready
```

Package:

```text
DRF_OMTIR_PUBLIC_INSPECTION_LAYER_EVIDENCE_LEDGER_AND_TRUST_RECEIPT_FORMAT_READY_v0_1.zip
SHA-256:
4ae1ea359bd69bec0d732f7e04ec82149a4a5233a3eab1cbe17efd7a63e4af85
```

What it proves:

```text
- Frozen runs can be indexed by milestone, package hash, WAL, verifier report,
  Trust Receipt, proof scope, and non-claims.
- A reviewer-facing evidence ledger, Trust Receipt schema and template,
  verifier CLI usage, example verifier reports, boundary template, package
  hash table, and bundle checksums are packaged together.
```

What it does not prove:

```text
- A new runtime mechanism
- A new live-domain validation
- Production certification
- Universal portability
- Domain-wide accuracy
```

## 5. Gemini / Google ADK v0.1

Milestone:

```text
DRF + OMTIR Gemini / Google ADK Trial v0.1:
LIVE_MODEL_PROPOSED_ACTION_GATE_AND_VERIFIER_PASS
```

Status:

```text
PASS
Bounded live-model action-governance validation
```

Package:

```text
DRF_OMTIR_GEMINI_ADK_LIVE_MODEL_PROPOSED_ACTION_GATE_AND_VERIFIER_PASS_v0_1.zip
SHA-256:
28abd8113d086d1365cdef8c58a16b933e04767998af76a9e0ea9b743c8b7e23
```

What it proves:

```text
- Gemini, running through Google ADK, proposed the governed sequence.
- Unsafe generic shell execution was denied before execution.
- Gemini adapted to a typed read-only Elastic MCP action.
- One real authenticated observability_get_log_groups tools/call executed.
- The allowed MCP result was persisted as STRUCTURAL evidence.
- An unsupported model-only CONFIRMED claim was denied.
- A narrower STRUCTURAL-linked CONFIRMED claim was admitted.
- restart_deployment was routed to REQUEST_REVIEW.
- Five WAL records passed independent verification.
- A Trust Receipt was generated.
```

What it does not prove:

```text
- Populated operational evidence: the Elastic response returned groups: []
- Incident-detection accuracy
- Remote Elastic dataset immutability
- Kubernetes enforcement
- Production readiness
- Universal portability
- Universal model reliability
```

## 6. MCP Flight Recorder v0.1

Milestone:

```text
DRF + OMTIR MCP Flight Recorder v0.1:
LOCAL_MCP_PROXY_AND_TRUST_RECEIPT_READY
```

Status:

```text
PASS
Developer-facing local governance proxy MVP ready
Product MVP milestone, not a new live-domain validation
```

Package:

```text
DRF_OMTIR_MCP_FLIGHT_RECORDER_LOCAL_PROXY_AND_TRUST_RECEIPT_READY_v0_1.zip
SHA-256:
53b3f074a9e5c87a32a1ee4623951f6ac9c9f36f03a4dbd3b13d102e0c6e90d0
Size:
36,372 bytes
Archive entries:
30
Internal checksums:
27 files
```

What it proves:

```text
- A local CLI package exposes init, demo, verify, receipt, and wrap commands.
- The demo command produces a five-record hash-chained WAL.
- Deterministic action policy denies delete_index.
- A read-only search_logs action is allowed and emits STRUCTURAL evidence.
- An unsupported CONFIRMED claim is rejected as REJECTED_HYPOTHESIS.
- A STRUCTURAL-linked CONFIRMED claim is admitted.
- restart_service is routed to REQUEST_REVIEW.
- The verifier returns PASS.
- A readable Trust Receipt is generated.
- The wrap command can run as a local governance proxy between an MCP client
  and a child MCP server in the smoke test.
- Apache-2.0 license is included.
- Credential-prefix scan passed.
```

What it does not prove:

```text
- A new live-domain validation
- Production deployment readiness
- Cloud service readiness
- Universal MCP compatibility
- External notarization
- Enterprise compliance
- Adversarial security certification
- Hosted dashboard readiness
- Multi-agent governance
```

## Current Evidence Ladder

```text
1. SIFT v0.2.4
   LIVE_MCP_TYPED_ACTION_GATE_AND_VERIFIER_PASS
   -> bounded live forensic / SIFT validation anchor

2. Gateway v0.1
   GENERIC_KERNEL_EXTRACTED_AND_CONFORMANCE_TESTED
   -> reusable generic kernel conformance tested

3. DevOps / Elastic v0.1
   LIVE_DEVOPS_ELASTIC_MCP_ACTION_GATE_AND_VERIFIER_PASS
   -> second bounded live tool-surface validation

4. Public Inspection Layer v0.1
   EVIDENCE_LEDGER_AND_TRUST_RECEIPT_FORMAT_READY
   -> reusable public inspection format ready

5. Gemini / Google ADK v0.1
   LIVE_MODEL_PROPOSED_ACTION_GATE_AND_VERIFIER_PASS
   -> bounded live-model action-governance validation

6. MCP Flight Recorder v0.1
   LOCAL_MCP_PROXY_AND_TRUST_RECEIPT_READY
   -> developer-facing local governance proxy MVP ready
```

## Current Public Claim

DRF + OMTIR is a governed action-accountability layer for AI agents.

The frozen evidence demonstrates the mechanism in two bounded live
tool-using workflows and one bounded live model-driven proposal loop: a
Protocol SIFT-style forensic workflow, a real authenticated Elastic MCP
DevOps tool-surface trial, and a Gemini / Google ADK trial in which model
proposals remained subject to deterministic action and claim governance. The
Flight Recorder v0.1 package adds a developer-facing local MCP governance
proxy MVP, but it is a product milestone rather than a new live-domain
validation. The evidence does not establish production readiness, universal
portability, or domain-wide accuracy.

## Credential Hygiene

If the Elastic API key was created only for the DevOps proof, revoke or rotate
it in the Elastic Cloud console after freezing the evidence package. Do not
store the replacement key in this ledger, source files, screenshots, logs, or
public archives.

If a Gemini API key was pasted into chat or exposed in any screenshot, revoke
or delete it in Google AI Studio before any further use. Create a replacement
only when needed, keep it local, and do not store it in this ledger, source
files, screenshots, logs, or public archives.

## Reviewer Entry Point

Start with:

```text
DRF_OMTIR_EXTERNAL_TECHNICAL_BRIEF_v0.1.md
```

Then use this ledger to inspect the frozen packages, hashes, WALs, verifier
reports, Trust Receipts, proof scopes, and non-claims.
