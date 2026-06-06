\# DRF + OMTIR Live Proposal Authority Manifest v0.2



\## Scope



v0.2 demonstrates live model proposal interception through TrueFoundry AI Gateway.



It replaces the fixed scenario proposal source with LIVE\_MODEL\_OUTPUT.



The downstream governance path remains:



DEFAULT\_POLICY -> TypedGateway -> OMTIR claim admission -> WAL -> verifier -> Trust Receipt



\## Proposal Source



\- Source: LIVE\_MODEL\_OUTPUT

\- Gateway: TrueFoundry AI Gateway

\- Model: google-gemini/gemini-3.1-flash-lite

\- WAL binding: raw\_model\_output\_sha256

\- Parsed form: parsed\_proposal



\## Policy Source



\- Runtime policy source: DEFAULT\_POLICY package built-in

\- Decision boundary: TypedGateway

\- Decision types: ALLOW, DENY, REQUEST\_REVIEW



\## Tool Executor Boundary



\- Tool handlers: LOCAL\_STUB

\- search\_logs: local typed stub only

\- read\_metrics: not production-backed

\- restart\_service: not executed unless explicitly allowed by policy; expected review path

\- delete\_index: not executed when denied

\- Evidence is structurally valid but not production-derived.



\## Boundary



This does not prove live TrueFoundry 429 recovery binding.

This does not prove production reliability.

This does not prove universal MCP compatibility.

This does not prove enterprise certification.

This does not prove all-agent safety.

