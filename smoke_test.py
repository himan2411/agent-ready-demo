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
HTML = (HERE / "site/index.html").read_text()


class Session:
    def __init__(self):
        self.proc = subprocess.Popen([sys.executable, str(HERE / "mcp/server.py")],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.next_id = 0

    def send(self, method, params=None, notify=False):
        msg = {"jsonrpc": "2.0", "method": method, **({"params": params} if params else {})}
        if notify:
            self.proc.stdin.write(json.dumps(msg) + "\n")
            self.proc.stdin.flush()
            return None
        self.next_id += 1
        msg["id"] = self.next_id
        reply = self.raw(msg)
        assert reply["id"] == msg["id"], reply
        return reply

    def raw(self, msg):
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        assert line, f"server exited after {msg}"
        return json.loads(line)

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
assert policies["pricing"] == price and price in LLMS and f"<dd>{price}</dd>" in HTML, "MCP pricing must match the page and llms.txt word for word"
assert policies["trial"] == trial and trial in LLMS and f"<dd>{trial}</dd>" in HTML, "MCP trial must match the page and llms.txt word for word"
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

# 4. Models send odd arguments. Each gets an error, and the session stays up.
assert s.tool("get_availability", service="demo", date=20261117)["isError"], "a number is not a date"
assert s.tool("get_availability", service=["demo"], date="2026-11-17")["isError"], "a list is not a service"
assert s.send("tools/call", {"name": "get_policies", "arguments": "x"})["error"]["code"] == -32602
assert s.send("tools/call", ["x"])["error"]["code"] == -32602
assert s.raw([{"jsonrpc": "2.0", "id": 99, "method": "ping"}])["error"]["code"] == -32600, "batches are not supported"
assert s.tool("get_availability", service="demo", date="20261117")["structuredContent"]["open"] == ["09:30"], \
    "a basic ISO date must find the same slots as 2026-11-17"
unpublished = s.tool("get_availability", service="demo", date="2026-12-01")
assert unpublished["isError"] and "No schedule published" in unpublished["content"][0]["text"], \
    "a date with no schedule must not look fully booked"
assert s.send("ping")["result"] == {}

s.close()
print("\nsmoke test: all checks passed")
