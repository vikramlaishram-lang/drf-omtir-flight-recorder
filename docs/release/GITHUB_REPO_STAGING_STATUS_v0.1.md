# GitHub Repo Staging Status v0.1

Status:

```text
PRODUCT_REPO_ROOT_READY_FOR_MANUAL_GITHUB_PUBLICATION
```

Repository name:

```text
drf-omtir-flight-recorder
```

Description:

```text
Local MCP governance proxy for AI agents.
```

License:

```text
Apache-2.0
```

Prepared local repo root:

```text
drf-omtir-mcp-flight-recorder-v0.1
```

## Verification

```text
Unit tests: PASS
CLI demo: PASS
CLI verifier: PASS
Trust Receipt generation: PASS
Credential-shaped value scan: PASS
```

## Product Entry Point

```bash
drf-omtir init
drf-omtir demo
drf-omtir verify wal/demo.jsonl
drf-omtir receipt wal/demo.jsonl
drf-omtir wrap --policy drf-omtir.yaml -- mcp-server-command
```

## Release Assets To Attach

```text
DRF_OMTIR_MCP_FLIGHT_RECORDER_LOCAL_PROXY_AND_TRUST_RECEIPT_READY_v0_1.zip
DRF_OMTIR_MCP_FLIGHT_RECORDER_LOCAL_PROXY_AND_TRUST_RECEIPT_READY_v0_1_SHA256.txt
DRF_OMTIR_PUBLIC_REVIEW_PACKAGE_v0_1.zip
DRF_OMTIR_PUBLIC_GITHUB_RELEASE_v0_1_WITH_DEMO.zip
```

## Publication Blockers

```text
Rotate or revoke any temporary Elastic API key used only for testing.
Confirm no active credentials appear in public screenshots.
Record the public walkthrough.
Create the GitHub repository and push manually.
```

## Boundary

This staging record means the local product repo root is ready for manual GitHub publication. It does not mean the repository has been published, externally reviewed, security certified, or production hardened.
