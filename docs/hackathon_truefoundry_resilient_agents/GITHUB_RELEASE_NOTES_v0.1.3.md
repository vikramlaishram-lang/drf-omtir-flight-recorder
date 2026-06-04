# DRF + OMTIR Flight Recorder v0.1.3

## Reviewer Inspectability Patch

This release keeps the v0.1.2 TrueFoundry resilient-demo claim intact and improves how reviewers inspect authority and WAL binding.

## What Changed

- Added a human-readable authority manifest:
  - `docs/hackathon_truefoundry_resilient_agents/AUTHORITY_MANIFEST_v0.1.md`
- Trust Receipts now include `WAL SHA-256` in addition to `last_record_hash`.
- The TrueFoundry demo script now shows the authority manifest before running the demo.
- README now points reviewers to the authority manifest and calls out WAL SHA-256 binding in the receipt.
- Package metadata version is now `0.1.3`.

## What This Proves

This release improves the inspectability of the existing bounded resilient-demo evidence. Reviewers can now see:

```text
who decides
where the rule source is declared
how WAL file integrity is bound into the receipt
where quarantined / rejected / review-routed events go
```

## What This Does Not Prove

This is not a new live-domain validation and does not claim AWS Bedrock validation, production reliability, universal MCP compatibility, external notarization, enterprise compliance, or adversarial security certification.
