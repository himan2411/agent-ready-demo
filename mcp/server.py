"""Read-only MCP server that lets an AI agent check services, prices and open slots.

Speaks MCP over stdio (newline-delimited JSON-RPC 2.0) using only the standard library.
It never books or changes anything.

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
        if not isinstance(service, str) or service not in services:
            raise ToolError(f"Unknown service {service!r}. Known: {', '.join(services)}.")
        try:
            day = date.fromisoformat(day).isoformat()  # also normalizes 20261117 to 2026-11-17
        except (TypeError, ValueError):
            raise ToolError("date must be a string, YYYY-MM-DD.")
        if day not in DATA["slots"]:
            raise ToolError(f"No schedule published for {day}. Published dates: {', '.join(DATA['slots'])}.")
        slots = DATA["slots"][day].get(service, [])
        return {"service": services[service]["name"], "date": day, "timezone": DATA["timezone"], "open": slots}
    if name == "get_policies":
        return DATA["policies"]
    raise ToolError(f"Unknown tool {name!r}.")


def handle(msg):
    if not isinstance(msg, dict):
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid request: send one JSON object per line."}}
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
        args = (params.get("arguments") or {}) if isinstance(params, dict) else None
        if not isinstance(args, dict):
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": "params and params.arguments must be objects."}}
        try:
            out = call_tool(params.get("name"), args)
            result = {"content": [{"type": "text", "text": json.dumps(out)}], "structuredContent": out, "isError": False}
        except ToolError as e:
            result = {"content": [{"type": "text", "text": str(e)}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main():
    sys.stdin.reconfigure(errors="replace")  # a non-UTF-8 line becomes a parse error, not a crash
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        else:
            try:
                reply = handle(msg)
            except Exception as e:  # noqa: BLE001 - one bad request must not end the session
                mid = msg.get("id") if isinstance(msg, dict) else None
                reply = {"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": f"Internal error: {e}"}}
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
