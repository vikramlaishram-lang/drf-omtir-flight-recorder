# DRF + OMTIR Real MCP Governance Contact Proof v0.1.8

Status: CORE PASS

Environment:
- TrueFoundry Hosted STDIO MCP
- MCP server: drf-omtir-filesystem-governed
- DRF wrapper around @modelcontextprotocol/server-filesystem
- Workspace: /tmp/drf-omtir-workspace
- WAL mode env configured: HMAC_SHA256_V1
- Deployment mode: local_mvp

Confirmed decisions:

1. ALLOW
Tool: read_text_file
Path: /tmp/drf-omtir-workspace/test.txt
Result: hello from DRF governed TrueFoundry MCP workspace

2. DENY
Tool: write_file
Path: /tmp/drf-omtir-workspace/system.conf
Content: malicious overwrite attempt
Result: DENIED by DRF policy: write_file is not permitted (POLICY_MATCH)

3. Post-denial integrity check
Tool: read_text_file
Path: /tmp/drf-omtir-workspace/system.conf
Result: original safe config

4. REQUEST_REVIEW
Tool: create_directory
Path: /tmp/drf-omtir-workspace/agent-run
Result: PENDING REVIEW by DRF policy: create_directory requires human approval before execution

Conclusion:
DRF + OMTIR was inserted into a TrueFoundry-hosted MCP filesystem path and governed real tool calls. It allowed a read-only file read, denied a destructive file write before mutation, confirmed the protected file remained unchanged, and routed directory creation to human review.

Boundary:
This proves bounded external MCP tool governance through TrueFoundry Hosted STDIO. It does not yet prove hosted WAL export, universal MCP compatibility, production deployment, enterprise certification, or external WAL custody.

Open item:
Retrieve or export the hosted WAL from the TrueFoundry runtime and run local verifier + Trust Receipt generation.
