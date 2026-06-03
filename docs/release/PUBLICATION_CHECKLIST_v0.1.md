# Publication Checklist

Status:

```text
PUBLISH_BLOCKED_PENDING_REMAINING_MANUAL_CHECKS
```

## Required Before Public Release

- [x] Revoke the Gemini API key exposed during development. Operator confirmation recorded on 2026-06-02.
- [ ] Rotate or revoke any temporary Elastic API key used only for testing.
- [ ] Confirm no active credentials appear in screenshots selected for public use.
- [x] Confirm `checksums/SHA256SUMS.txt` verifies.
- [x] Confirm the credential-shaped value scan passes.
- [x] Confirm the reviewer wrapper SHA-256 matches the release notes.
- [ ] Record the public walkthrough using `docs/DEMO_SCRIPT_3_MINUTES_v0.1.md`.
- [x] Select and add an open-source license before publishing code. Apache-2.0 recorded on 2026-06-02.

## Scope Check

- [x] Keep the public claim bounded to frozen evidence.
- [x] Preserve the `groups: []` Elastic boundary.
- [x] Do not imply production certification.
- [x] Do not imply Kubernetes enforcement.
- [x] Do not imply domain-wide incident-detection accuracy.

## Credential Hygiene Checkpoint

Recorded on 2026-06-02:

```text
Gemini API key account-side deletion: confirmed by operator
Gemini API-key shell variable removal: confirmed by operator
Gemini trial project recursive Google API-key prefix scan: PASS (0 matches)
Public release wrapper recursive Google API-key prefix scan: PASS (0 matches)
Workspace text Google API-key prefix scan: PASS (0 matching files)
Relevant archive Google API-key prefix scan: PASS (0 matching entries)
```

## Release Decision

Publish only after a human checks every box above.
