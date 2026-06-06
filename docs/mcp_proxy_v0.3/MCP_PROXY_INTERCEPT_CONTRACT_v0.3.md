# DRF + OMTIR Flight Recorder v0.3 — MCP Proxy Intercept Contract

## Scope

v0.3 targets transparent governance of external MCP tool calls.

Target command:

```bash
drf-omtir wrap --policy policy.yaml -- mcp-server-command
```

Final v0.3 goal:

```text
External MCP client sends tools/call
-> drf-omtir wrap intercepts
-> policy decides ALLOW / DENY / REQUEST_REVIEW
-> ALLOW forwards to wrapped MCP server
-> DENY and REQUEST_REVIEW are not forwarded
-> WAL records EXTERNAL_MCP_AGENT
-> verifier PASS
-> Trust Receipt generated
```

Phase 0 does not implement the proxy. It defines the protocol contract, policy schema, fixtures, stub server, and fixture harness.

## MCP stdio transport rules

MCP stdio uses newline-delimited JSON-RPC messages.

The server reads JSON-RPC messages from stdin and writes JSON-RPC messages to stdout.

stdout must contain only valid MCP messages.

stderr may be used for logs.

## Initialize handshake

Fixture initialize request:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-03-26",
    "capabilities": {},
    "clientInfo": {
      "name": "fixture-harness",
      "version": "0.1"
    }
  }
}
```

Stub initialize response:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-03-26",
    "capabilities": {
      "tools": {}
    },
    "serverInfo": {
      "name": "stub-mcp-server",
      "version": "0.1"
    }
  }
}
```

Initialized notification:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```

## Proxy initialize behavior

For v0.3, `drf-omtir wrap` is transparent during initialization.

It forwards `initialize` to the wrapped server and returns the wrapped server response unchanged.

It forwards `notifications/initialized`.

The proxy does not advertise additional capabilities in v0.3.

Governance begins at `tools/call`.

## Tool call shape

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "delete_index",
    "arguments": {
      "index": "demo-logs"
    }
  }
}
```

## DENY response shape

Governance DENY is returned as an MCP tool result with `isError: true`, not as a JSON-RPC protocol error:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "DENIED by DRF policy: delete_index is not permitted"
      }
    ],
    "isError": true
  }
}
```

## REQUEST_REVIEW response shape

REQUEST_REVIEW is also returned as an MCP tool result with `isError: true`:

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "PENDING REVIEW by DRF policy: restart_service requires human approval before execution"
      }
    ],
    "isError": true
  }
}
```

## ALLOW behavior

ALLOW forwards the original `tools/call` request to the wrapped MCP server.

The wrapped server's response is returned to the client unchanged.

WAL writes are synchronous side effects, not fire-and-forget.

Required ALLOW sequence:

```text
1. Receive tools/call from client.
2. Parse params.name and params.arguments.
3. Evaluate policy.
4. If ALLOW, write WAL decision event synchronously with forwarded=true.
5. Forward original request to wrapped server.
6. Receive wrapped server response.
7. Write WAL tool_result event synchronously.
8. Return wrapped server response to client.
```

## v0.3 WAL fields

Every intercepted `tools/call` WAL event must include:

```text
agent_proposal_source: EXTERNAL_MCP_AGENT
mcp_client_id: UNKNOWN_FIXTURE_CLIENT or configured client id
tool_call_id: JSON-RPC id field value
mcp_method: tools/call
parsed_tool_name: params.name
parsed_arguments: params.arguments
drf_decision: ALLOW / DENY / REQUEST_REVIEW
forwarded: true / false
tool_execution_boundary: MCP_PROXY_STUB_SERVER
```

## Boundary

v0.3 does not prove production reliability.

v0.3 does not prove universal MCP compatibility.

v0.3 does not prove enterprise certification.

v0.3 does not prove all-agent safety.

v0.3 Phase 0 does not implement proxy behavior yet.
