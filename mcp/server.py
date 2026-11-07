"""Read-only MCP server that lets an AI agent check services, prices and open slots.

Speaks MCP over stdio (newline-delimited JSON-RPC 2.0) using only the standard library.
It never books or changes anything: write tools come later, after the read path is trusted.

Run:  python3 server.py [path/to/data.json]
"""
import json
import sys
from datetime import date
from pathlib import Path

PROTOCOL = "2025-06-18"
DATA = json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).with_name("data.json")).read_text())

TOOLS = [
    {
        "name": "list_services",
        "description": "List the services offered, with duration in minutes and price.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_availability",
        "description": "Open start times for one service on one date (YYYY-MM-DD), in the business's time zone.",
        "inputSchema": {
            "type": "object",
            "properties": {"service": {"type": "string"}, "date": {"type": "string", "format": "date"}},
            "required": ["service", "date"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_policies",
        "description": "Pricing, trial, cancellation and payment policies, quoted exactly.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


class ToolError(Exception):
    pass


def call_tool(name, args):
    services = {s["id"]: s for s in DATA["services"]}
    if name == "list_services":
        return {"business": DATA["business"], "services": DATA["services"]}
    if name == "get_availability":
        service, day = args.get("service"), args.get("date")
        if service not in services:
            raise ToolError(f"Unknown service {service!r}. Known: {', '.join(services)}.")
        try:
            date.fromisoformat(day or "")
        except ValueError:
            raise ToolError("date must be YYYY-MM-DD.")
        slots = DATA["slots"].get(day, {}).get(service, [])
        return {"service": services[service]["name"], "date": day, "timezone": DATA["timezone"], "open": slots}
    if name == "get_policies":
        return DATA["policies"]
    raise ToolError(f"Unknown tool {name!r}.")


def handle(msg):
    method, mid, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
    if mid is None:
        return None  # notifications such as notifications/initialized need no reply
    if method == "initialize":
        result = {
            "protocolVersion": PROTOCOL,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "availability", "version": "1.0.0"},
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        try:
            out = call_tool(params.get("name"), params.get("arguments") or {})
            result = {"content": [{"type": "text", "text": json.dumps(out)}], "structuredContent": out, "isError": False}
        except ToolError as e:
            result = {"content": [{"type": "text", "text": str(e)}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main():
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            reply = handle(json.loads(line))
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
