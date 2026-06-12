# Tool Identity Manifest Hardening

Status: IMPLEMENTED_AND_TESTED

Scope:
DRF + OMTIR MCP Flight Recorder local proxy hardening.

## Purpose

This patch adds Tool Identity Manifest support to the local MCP proxy path.

The purpose is to make MCP tool governance bind to the discovered tool surface, not only to a tool name. The proxy now captures `tools/list`, computes deterministic identity hashes for exposed tools, records the manifest in the WAL, and fails closed if a later `tools/call` observes identity drift before forwarding.

## Threat Addressed

MCP tool-surface drift between discovery and execution.

Before this patch, a gateway could govern a tool call by action name, but the proxy did not preserve enough tool identity metadata to prove that the tool being called still matched the tool discovered earlier.

This patch records and checks:

- tool name
- server origin
- input schema hash
- description hash
- `readOnlyHint`
- `destructiveHint`
- `idempotentHint`
- per-tool identity hash
- full manifest hash

If a previously discovered tool identity changes, the proxy denies the later call before forwarding.

## Files Changed

- `src/drf_omtir_flight_recorder/tool_identity.py`
- `src/drf_omtir_flight_recorder/proxy.py`
- `tests/test_tool_identity.py`

## Covered Behavior

- `tools/list` is captured by the proxy.
- A Tool Identity Manifest is generated from the returned tool list.
- Tool identity hashes are deterministic.
- Tool annotations are preserved when present.
- The manifest is written to the WAL.
- A later `tools/call` fails closed if the matching tool identity hash changes.
- WAL verification still passes for the manifest and denied-call records.

## Not Covered

This patch does not claim:

- production MCP security certification
- universal protection against all tool-poisoning attacks
- compatibility with every remote MCP server
- external notarization
- enterprise deployment readiness
- a new live-domain validation

The scope is local proxy hardening with unit and proxy-level tests.

## Test Evidence

```text
python -m pytest
49 passed
```

## Boundary

This is an MCP tool-surface integrity hardening patch. It strengthens the governed proxy path by making tool identity visible and fail-closed on detected drift. It does not start v0.2, v0.3, or any new live runtime claim.
