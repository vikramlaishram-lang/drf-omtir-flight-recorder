from __future__ import annotations

import json
import sys


for line in sys.stdin:
    if not line.strip():
        continue
    message = json.loads(line)
    if message.get("method") == "tools/call":
        name = message.get("params", {}).get("name")
        response = {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": {"content": [{"type": "text", "text": json.dumps({"tool": name, "ok": True})}]},
        }
    else:
        response = {"jsonrpc": "2.0", "id": message.get("id"), "result": {}}
    print(json.dumps(response), flush=True)
