# DRF + OMTIR Flight Recorder v0.1.1 - TrueFoundry Resilient Demo

Adds `drf-omtir resilient-demo`, a bounded resilient-agent workflow for the TrueFoundry Resilient Agents hackathon.

This release records:

- TrueFoundry AI Gateway route metadata
- Gemini Flash Lite model use
- AWS Bedrock non-use
- Captured rate-limit failure marker
- Rate-limit rule: drf-omtir-resilience-rate-limit
- unsafe_action -> DENY
- read_only_tool -> ALLOW
- bad_tool_result -> QUARANTINED
- unsupported_claim -> REJECTED_HYPOTHESIS
- evidence_linked_claim -> CONFIRMED
- risky_remediation -> REQUEST_REVIEW
- verifier PASS over 6 WAL records
- Trust Receipt generation

## Boundary

This is a bounded resilient-agent demo using TrueFoundry/Gemini route metadata and a captured rate-limit marker. The live TrueFoundry evidence is the separate Request Trace screenshot showing the 429 rate-limit response. It does not claim AWS Bedrock validation, production reliability, universal failure recovery, enterprise certification, or all-agent safety.
