"""Agent smoke test: a scripted agent answers three buyer questions about Larkline through the MCP server.

It keeps one live stdio session open, as an MCP client does, and checks the answers
against the facts the public site publishes. Run: python3 smoke_test.py
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
FACTS = json.loads((HERE / "surface/facts.json").read_text())
LLMS = (HERE / "site/llms.txt").read_text()


class Session:
    def __init__(self):
        self.proc = subprocess.Popen([sys.executable, str(HERE / "mcp/server.py")],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.next_id = 0

    def send(self, method, params=None, notify=False):
        msg = {"jsonrpc": "2.0", "method": method, **({"params": params} if params else {})}
        if not notify:
            self.next_id += 1
            msg["id"] = self.next_id
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        if notify:
            return None
        reply = json.loads(self.proc.stdout.readline())
        assert reply["id"] == msg["id"], reply
        return reply

    def tool(self, name, **args):
        return self.send("tools/call", {"name": name, "arguments": args})["result"]

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=5)


def faq_answer(question):
    lines = FACTS["faq"].splitlines()
    return lines[lines.index("Q: " + question) + 1].removeprefix("A: ")


s = Session()
init = s.send("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "smoke", "version": "0"}})
assert init["result"]["serverInfo"]["name"] == "availability"
s.send("notifications/initialized", notify=True)
tools = [t["name"] for t in s.send("tools/list")["result"]["tools"]]
assert tools == ["list_services", "get_availability", "get_policies"], tools

# 1. "How much does Larkline cost, and is there a trial?"
policies = s.tool("get_policies")["structuredContent"]
price = faq_answer("How much does Larkline cost?")
trial = faq_answer("Is there a free trial?")
assert policies["pricing"] == price and price in LLMS, "MCP pricing must match the site word for word"
assert policies["trial"] == trial and trial in LLMS, "MCP trial must match the site word for word"
print("Q: How much does Larkline cost, and is there a trial?\nA:", policies["pricing"], policies["trial"])

# 2. "Can I get a demo on 17 November, and what does it cost?"
listed = s.tool("list_services")["structuredContent"]
assert "fictional" in listed["business"]
demo = next(x for x in listed["services"] if "demo" in x["name"].lower())
slots = s.tool("get_availability", service=demo["id"], date="2026-11-17")["structuredContent"]
assert slots["open"] == ["09:30"], slots
print(f"Q: Can I get a demo on 17 November?\nA: Yes, at {slots['open'][0]} {slots['timezone']}. "
      f"It takes {demo['minutes']} minutes and costs ${demo['price_usd']}. {policies['booking']}")

# 3. A bad request gets an error the agent can read, and there is no way to book.
bad = s.tool("get_availability", service="consulting", date="2026-11-17")
assert bad["isError"] and "Known: demo" in bad["content"][0]["text"], bad
assert s.send("bookings/create")["error"]["code"] == -32601
print("Q: Book me in.\nA: I can't book. The server is read-only:", policies["booking"])

s.close()
print("\nsmoke test: all checks passed")
