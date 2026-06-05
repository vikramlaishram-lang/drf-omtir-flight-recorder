# Final 60-90 Second Demo Script v0.1.3

## Prep

Open:

1. GitHub repo / v0.1.3 release page
2. TrueFoundry Request Trace showing HTTP 429
3. PowerShell in repo root

```powershell
cd "C:\Users\vikra\Documents\GitHub\drf-omtir-flight-recorder"
cls
```

## 1. GitHub Repo / Release

Say:

> This is DRF + OMTIR Flight Recorder, a local MCP governance proxy for resilient AI agents. The goal is not only that the agent keeps working after failure, but that its authority stays bounded and its claims remain provable.

Show:

```text
v0.1.3
DRF + OMTIR Flight Recorder
```

## 2. Show Pre-Committed Authority Manifest

Run:

```powershell
Get-Content .\docs\hackathon_truefoundry_resilient_agents\AUTHORITY_MANIFEST_v0.1.md | more
```

Pause on the event/rule table.

Say:

> Before the run, the authority structure is visible. The model can propose, but it cannot execute tools or confirm claims directly. DRF controls action authority. OMTIR controls confirmed-claim authority.

Point to:

```text
delete_index -> DENY -> drf-omtir.yaml
search_logs -> ALLOW -> drf-omtir.yaml
unsupported confirmed claim -> REJECTED_HYPOTHESIS
restart_service -> REQUEST_REVIEW -> drf-omtir.yaml
```

## 3. Show TrueFoundry 429 Trace

Switch to TrueFoundry Request Traces.

Show:

```text
google-gemini/gemini-3.1-flash-lite
Rate limit exceeded
429
Rule: drf-omtir-resilience-rate-limit
```

Say exactly:

> This 429 was captured separately in TrueFoundry Request Traces. The local CLI records a bounded recovery trace anchored to this captured failure; it is not a live TrueFoundry network replay.

Then say:

> AWS Bedrock was not used in this bounded run.

## 4. Run Resilient Demo

Run:

```powershell
drf-omtir resilient-demo
```

Say:

> Now the Flight Recorder records the bounded recovery path.

Point to:

```text
provider_route              -> TRUEFOUNDRY_GATEWAY
model                       -> GEMINI_FLASH_LITE
aws_bedrock                 -> NOT_USED
gateway_failure             -> RATE_LIMIT_EXCEEDED
unsafe_action               -> DENY
read_only_tool              -> ALLOW
bad_tool_result             -> QUARANTINED
unsupported_claim           -> REJECTED_HYPOTHESIS
evidence_linked_claim       -> CONFIRMED
risky_remediation           -> REQUEST_REVIEW
authority_trace             -> recorded
review_queue                -> generated
WAL records                 -> 6
verifier                    -> PASS
trust_receipt               -> generated
```

Say:

> Unsafe action is denied, weak tool output is quarantined, unsupported confirmation is rejected, evidence-linked confirmation is admitted, and risky remediation is routed to human review.

## 5. Optional Bridge: Show Event-Level Trace

Run:

```powershell
Get-Content .\reports\resilient-demo-trace.json | Select-Object -First 30
```

Say:

> The trace connects the terminal decisions back to event-level records.

Keep this section only if it is readable on screen. If it looks messy, skip it.

## 6. Run Verifier And Show Hash Links

Run:

```powershell
drf-omtir verify wal/resilient-demo.jsonl
```

Say:

> The verifier exposes the WAL hash chain, not just a PASS label.

Point to:

```text
previous_hash
record_hash
next_hash
last_record_hash
status: PASS
records: 6
```

Say:

> Each record links to the next, and the final record hash anchors the run.

## 7. Generate And Open Trust Receipt

Run:

```powershell
drf-omtir receipt wal/resilient-demo.jsonl
notepad .\receipts\resilient-demo-trust-receipt.md
```

Say:

> The Trust Receipt binds the human-readable summary back to the WAL.

Show:

```text
WAL SHA-256
Records: 6
Last record hash
Verifier: PASS
```

Then show the Governance Consequences section:

```text
Quarantined evidence excluded from confirmed claim set
Rejected hypotheses excluded from confirmed claim set
Confirmed claim events admitted
Pending human review events
Review queue
```

Say:

> Quarantined and rejected records do not silently disappear. They are explicitly excluded from the confirmed claim set.

## 8. Show Review Queue

Back in PowerShell, run:

```powershell
Get-Content .\reports\resilient-demo-review-queue.jsonl
```

Say:

> REQUEST_REVIEW produces a review artifact. It does not execute the risky remediation.

Point to:

```text
restart_service
REQUEST_REVIEW
PENDING_HUMAN_REVIEW
human_reviewer_required
```

## 9. Close With Boundary

Say:

> This is a bounded resilient-agent demo using TrueFoundry AI Gateway with Gemini Flash Lite and a captured 429 rate-limit trace. It does not claim AWS Bedrock validation, production reliability, universal failure recovery, enterprise certification, or all-agent safety.

Final line:

> In v0.1.3, all governance evidence is visible on screen: authority manifest, WAL hash links, Trust Receipt WAL binding, quarantine and reject consequences, and review queue.

## Execution Tips

Use `| more` for the authority manifest so the rule table does not scroll away.

Resize PowerShell tall enough before recording so the verifier hash links are readable.

Do a private take first. Watch only for two things: whether the authority table is visible long enough, and whether the verifier JSON is readable. If both are readable, record the final take.
