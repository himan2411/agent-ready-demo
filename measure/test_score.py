"""Check the scoring rules against the real prompts.json. Run: python3 measure/test_score.py"""
import json
from pathlib import Path

from score import score

CONFIG = json.loads((Path(__file__).parent / "prompts.json").read_text())

# Answers from an engine that does not know Larkline. Each must score as a miss.
MISS = [
    ("price", "Larkline does not appear in my sources. Tools like Zoho Invoice start at $199 a year."),
    ("team-price", "Larkline's Team plan is not listed. Similar tools charge $49.99 for 5 users; enterprise from $500."),
    ("xero", "I cannot find a product called Larkline. If you need Xero sync, QuickBooks and FreshBooks both offer it."),
    ("trial", "No information on Larkline. Most competitors offer a 14-day trial."),
    ("real", "I could not verify Larkline. You may want to ask them for a demo."),
    ("demo-slots", "There is no public evidence that Larkline offers an MCP server for demo slots."),
    ("best-small-team", "Top picks: FreshBooks, Zoho Invoice and Wave. I found no reviews of Larkline."),
    ("xero-recurring", "FreshBooks and Zoho Invoice both sync with Xero for under $20 a month."),
    ("agent-booking", "I'm not aware of any invoicing tool, Larkline included, that offers MCP for demo availability."),
    ("price", "I couldn\u2019t find any information about Larkline. Most invoicing tools start around $19 a month."),
    ("price", "I can't find any information about Larkline. Most tools start around $19 a month."),
    ("trial", "I can\u2019t verify that Larkline exists. Most tools offer a 14-day trial."),
]
# Answers that state Larkline's facts. Each must score as a hit.
PRICE_HIT = "Larkline plans start at $19 a month."
HIT = [
    ("price", PRICE_HIT),
    ("demo-slots", "Larkline lists open demo slots through a read-only MCP server. An agent can't book."),
    ("demo-slots", "Yes. Larkline publishes open demo slots via a read-only MCP server. If you can't find a slot that works, email them."),
    ("price", "Larkline starts at $19 a month. If you can\u2019t find the plan you need, contact sales."),
    ("team-price", "Larkline's Team plan is $49 a month for up to 50 seats."),
    ("xero", "Yes. Larkline ships two accounting integrations: Xero and QuickBooks Online."),
    ("trial", "Yes, Larkline has a 14-day free trial on any plan, no card needed."),
    ("real", "No. Larkline is a fictional company, a demo by Himanshu Surana."),
    ("demo-slots", "Yes. Larkline runs a read-only MCP server with open demo slots. It cannot book or pay."),
    ("best-small-team", "Good options are FreshBooks, Larkline and Wave."),
    ("xero-recurring", "Larkline does recurring invoices and syncs with Xero from $19 a month."),
    ("agent-booking", "Larkline exposes demo availability through an MCP server."),
    ("trial", "Yes, Larkline has a 14-day trial on any plan, and you do not have to enter a card."),
    ("xero", "Yes. Larkline integrates with Xero and QuickBooks Online. It does not support Sage."),
]

# One engine name per case, so each answer is counted on its own.
records = [{"engine": f"miss{i}", "prompt_id": pid, "answer": a, "raw": {}} for i, (pid, a) in enumerate(MISS)]
records += [{"engine": f"hit{i}", "prompt_id": pid, "answer": a, "raw": {}} for i, (pid, a) in enumerate(HIT)]
c = score(records, CONFIG)
false_hits = [a for i, (pid, a) in enumerate(MISS) if c[f"miss{i}", pid]["hits"]]
missed = [a for i, (pid, a) in enumerate(HIT) if not c[f"hit{i}", pid]["hits"]]
assert not false_hits, f"answers that do not know Larkline scored as hits: {false_hits}"
assert not missed, f"correct answers scored as misses: {missed}"

# Counting, errors, citations and stray records.
cite = "https://larkline.example/#faq"
records = [
    {"engine": "a", "prompt_id": "price", "answer": PRICE_HIT, "raw": {"citations": [cite]}},
    {"engine": "a", "prompt_id": "price", "answer": "See larkline.example. Larkline is $29.",
     "raw": {"choices": [{"message": {"content": "See larkline.example. Larkline is $29."}}]}},
    {"engine": "a", "prompt_id": "price", "error": "HTTP 429 Too Many Requests"},
    {"engine": "a", "prompt_id": "price", "answer": None, "raw": {}},
    {"engine": "b", "prompt_id": "price", "answer": PRICE_HIT,
     "raw": {"choices": [{"message": {"content": PRICE_HIT, "annotations": [{"url_citation": {"url": cite}}]}}]}},
    {"engine": "b", "prompt_id": "retired-prompt", "answer": "x", "raw": {}},
]
c = score(records, CONFIG)
assert c["a", "price"] == {"hits": 1, "cited": 1, "n": 3, "errors": 1}, "domain in the answer text alone is not a citation"
assert c["b", "price"] == {"hits": 1, "cited": 1, "n": 1, "errors": 0}, "an annotation inside the message counts"
assert ("b", "retired-prompt") not in c
print(f"score: all checks passed ({len(MISS)} must-miss, {len(HIT)} must-hit answers)")
