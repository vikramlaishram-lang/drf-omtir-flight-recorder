# DRF + OMTIR Flight Recorder v0.3 — MCP Proxy Acceptance Gates

## Phase 0 stub server acceptance

Run:

```powershell
python tests/fixtures/mcp/fixture_harness.py stub-smoke
```

Must test:

```text
initialize -> valid initialize response
notifications/initialized -> accepted with no response
tools/list -> returns search_logs, read_metrics, restart_service, delete_index
tools/call search_logs -> returns fixed non-error result
tools/call read_metrics -> returns fixed non-error result
```

Success output:

```text
STUB_SMOKE_PASS
```

## Future proxy acceptance modes

These are documented in Phase 0 but not implemented yet:

```powershell
python tests/fixtures/mcp/fixture_harness.py proxy-deny
python tests/fixtures/mcp/fixture_harness.py proxy-allow
python tests/fixtures/mcp/fixture_harness.py proxy-review
python tests/fixtures/mcp/fixture_harness.py policy-mutation
```

## Mandatory future policy mutation gate

Required future sequence:

```text
1. Start proxy with policy/example-policy.yaml.
2. Send tools_call_delete_index.json.
3. Assert response result.isError == true.
4. Assert WAL decision DENY.
5. Assert forwarded == false.
6. Stop proxy.

7. Start proxy with tests/fixtures/mcp/policy_mutation_allow_delete_index.yaml.
8. Send tools_call_delete_index.json.
9. Assert response comes from stub server.
10. Assert WAL decision ALLOW.
11. Assert forwarded == true.
12. Run verifier on both WALs.
13. If delete_index is still denied under mutation policy, fail v0.3.
```

## Phase 0 commit acceptance

Must pass:

```powershell
python tests/fixtures/mcp/fixture_harness.py stub-smoke
python -m pytest
```

Credential scan:

```powershell
Get-ChildItem -Recurse -File |
  Where-Object { $_.FullName -notmatch "\.git\" } |
  Select-String -Pattern "eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+|AIza[0-9A-Za-z_\-]{20,}|sk-[0-9A-Za-z_\-]{20,}|Bearer\s+[0-9A-Za-z_\-\.]{20,}|Authorization:\s*Bearer"
```

Expected: no output.
