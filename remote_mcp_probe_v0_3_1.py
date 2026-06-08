import json
import os
import requests

TRUEFOUNDRY_GATEWAY_URL = "https://gateway.truefoundry.ai/drf-omtir"

TARGET_MCP_URL = (
    TRUEFOUNDRY_GATEWAY_URL
    + "/mcp/drf-omtir-filesystem-governed/server"
)

API_KEY = os.environ.get("TRUEFOUNDRY_API_KEY")

if not API_KEY:
    raise SystemExit("Missing TRUEFOUNDRY_API_KEY environment variable")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def call_mcp(method, params=None, request_id=1):
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
    }
    if params is not None:
        payload["params"] = params

    response = requests.post(
        TARGET_MCP_URL,
        headers=headers,
        json=payload,
        timeout=30,
    )

    print("\n--- REQUEST ---")
    print(json.dumps(payload, indent=2))

    print("\n--- STATUS ---")
    print(response.status_code)

    print("\n--- RESPONSE TEXT ---")
    print(response.text)

    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    print("Target MCP URL:", TARGET_MCP_URL)

    # 1. Discover tools
    call_mcp("tools/list", request_id=1)

    # 2. ALLOW: read safe test file
    call_mcp(
        "tools/call",
        {
            "name": "read_text_file",
            "arguments": {
                "path": "/tmp/drf-omtir-workspace/test.txt"
            },
        },
        request_id=2,
    )

    # 3. DENY: attempt destructive overwrite
    call_mcp(
        "tools/call",
        {
            "name": "write_file",
            "arguments": {
                "path": "/tmp/drf-omtir-workspace/system.conf",
                "content": "malicious overwrite attempt from remote v0.3.1 probe",
            },
        },
        request_id=3,
    )

    # 4. ALLOW: post-denial integrity check
    call_mcp(
        "tools/call",
        {
            "name": "read_text_file",
            "arguments": {
                "path": "/tmp/drf-omtir-workspace/system.conf"
            },
        },
        request_id=4,
    )