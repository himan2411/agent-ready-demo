"""Check the scoring rules on hand-written records. Run: python3 measure/test_score.py"""
from score import score

config = {"domain": "larkline.example", "prompts": [
    {"id": "price", "expect": "\\$19"},
    {"id": "best", "expect": "Larkline"},
]}
records = [
    {"engine": "a", "prompt_id": "price", "answer": "Plans start at $19.", "raw": {"citations": ["https://larkline.example/#faq"]}},
    {"engine": "a", "prompt_id": "price", "answer": "It costs $29.", "raw": {}},
    {"engine": "a", "prompt_id": "price", "error": "HTTP Error 429"},
    {"engine": "a", "prompt_id": "best", "answer": "Try\nlarkline or Competitor A.", "raw": {"x": "LARKLINE.EXAMPLE"}},
    {"engine": "b", "prompt_id": "best", "answer": None, "raw": {}},
]
c = score(records, config)
assert c["a", "price"] == {"hits": 1, "cited": 1, "n": 2, "errors": 1}, c["a", "price"]
assert c["a", "best"] == {"hits": 1, "cited": 1, "n": 1, "errors": 0}, "match ignores case and spans lines"
assert c["b", "best"] == {"hits": 0, "cited": 0, "n": 1, "errors": 0}, "an empty answer is a miss, not a crash"
print("score: all checks passed")
