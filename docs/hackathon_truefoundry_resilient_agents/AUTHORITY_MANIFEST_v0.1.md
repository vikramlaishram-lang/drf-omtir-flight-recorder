# Authority Manifest v0.1

Status: DEMO_AUTHORITY_MANIFEST

Purpose:
Make the decision authority visible for the bounded TrueFoundry resilient demo.

Boundary:
This manifest describes the local DRF + OMTIR Flight Recorder resilient-demo authority structure. It is not an enterprise RBAC model, legal policy, production approval workflow, external notarization layer, or universal MCP governance standard.

## Authority Hierarchy

1. Model / agent proposal
   - Authority: none
   - Role: propose actions and claims only
   - Boundary: cannot execute tools or confirm claims directly

2. DRF action authority
   - Source: DRF_RULE
   - Policy source: drf-omtir.yaml and built-in demo policy rules
   - Function: decide ALLOW, DENY, or REQUEST_REVIEW for proposed actions

3. Typed tool execution
   - Source: action contract in policy
   - Function: execute only when DRF returns ALLOW and the tool is executable
   - Boundary: denied and review-routed actions are not executed

4. OMTIR claim authority
   - Source: OMTIR_RULE
   - Function: decide whether a claim can be CONFIRMED or must remain rejected / hypothesis-only
   - Boundary: confirmed claims require valid STRUCTURAL evidence linkage

5. WAL authority record
   - Source: wal/resilient-demo.jsonl
   - Function: preserve ordered, hash-chained event history
   - Boundary: the WAL is the source-of-truth trace for the demo run

6. Independent verifier
   - Source: drf_omtir_flight_recorder_verifier
   - Function: check WAL hash chain and required governance events
   - Boundary: verifier PASS means the frozen local trace is internally consistent, not production-certified

7. Trust Receipt
   - Source: receipts/resilient-demo-trust-receipt.md
   - Function: human-readable explanation of the run
   - Boundary: the receipt explains the WAL; it does not replace the WAL

## Demo Rule Origins

| Event | Proposed item | Authority origin | Decision / status | Rule source |
| --- | --- | --- | --- | --- |
| evt_000001 | delete_index | DRF_RULE/delete_index | DENY | drf-omtir.yaml |
| evt_000002 | search_logs | DRF_RULE/search_logs | ALLOW | drf-omtir.yaml |
| evt_000003 | parse_tool_result | DRF_RULE/parse_tool_result | ALLOW, QUARANTINED evidence | built-in demo policy |
| evt_000004 | unsupported confirmed claim | OMTIR_RULE/confirmed_claim_requires_valid_structural_link | REJECTED_HYPOTHESIS | OMTIR claim admission rule |
| evt_000005 | evidence-linked confirmed claim | OMTIR_RULE/confirmed_claim_requires_structural_evidence | CONFIRMED | OMTIR claim admission rule |
| evt_000006 | restart_service | DRF_RULE/restart_service | REQUEST_REVIEW | drf-omtir.yaml |

## Reviewer Path

1. Read this manifest to see who is allowed to decide.
2. Run `drf-omtir resilient-demo`.
3. Inspect `reports/resilient-demo-trace.json` for the event-level authority trace.
4. Run `drf-omtir verify wal/resilient-demo.jsonl` to inspect hash links and verifier status.
5. Read `receipts/resilient-demo-trust-receipt.md` to see governance consequences and review queue linkage.

## Non-Claims

This manifest does not claim that TrueFoundry, Gemini, AWS Bedrock, Elastic, Kubernetes, or any production deployment has delegated real enterprise authority to this demo. It documents the local authority boundary used by this exact resilient-demo run.
