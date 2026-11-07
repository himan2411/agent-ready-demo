"""Count hits as raw n/N per prompt and engine, from the answer logs.

A hit is an answer that names the brand, matches the prompt's 'expect' regex, and does not say it
could not find or verify the brand. 'cited' counts answers whose sources (citations, annotations,
search results: everything in the response except the answer text) contain the business's domain.
Failed requests are counted separately and left out of N. Records for prompts no longer in
prompts.json are skipped.
Run: python3 measure/score.py [answers/*.jsonl ...]  (default: every file in measure/answers)
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
FLAGS = re.IGNORECASE | re.DOTALL
UNKNOWN = re.compile(
    r"(?<!\byou )\b(could ?n[o']t|can'?t|can ?not|unable to|did ?n[o']t|was ?n[o']t able to) (find|verify|locate|confirm)"  # "if you can't find" is advice
    r"|\bno (public |reliable |specific |verified )?(information|evidence|record|reviews?|data|details|mention)"
    r"|\bnot (aware|familiar)|\bdo ?n[o']t have (any )?(specific |reliable )?information"
    r"|\bdoes ?n[o']t appear",
    FLAGS,
)


def sources(raw):
    raw = json.loads(json.dumps(raw))
    for choice in raw.get("choices") or []:
        (choice.get("message") or {}).pop("content", None)
    return json.dumps(raw).lower()


def is_hit(answer, brand, expect):
    answer = (answer or "").replace("\u2019", "'")  # models often write a curly apostrophe (’)
    return bool(brand.search(answer) and expect.search(answer) and not UNKNOWN.search(answer))


def score(records, config):
    brand = re.compile(rf"\b{re.escape(config['brand'])}\b", FLAGS)
    expect = {p["id"]: re.compile(p["expect"], FLAGS) for p in config["prompts"]}
    counts = defaultdict(lambda: {"hits": 0, "cited": 0, "n": 0, "errors": 0})
    for r in records:
        if r["prompt_id"] not in expect:
            continue
        c = counts[r["engine"], r["prompt_id"]]
        if "error" in r:
            c["errors"] += 1
            continue
        c["n"] += 1
        c["hits"] += is_hit(r["answer"], brand, expect[r["prompt_id"]])
        c["cited"] += config["domain"].lower() in sources(r["raw"])
    return dict(counts)


def main():
    config = json.loads((HERE / "prompts.json").read_text())
    files = [Path(a) for a in sys.argv[1:]] or sorted((HERE / "answers").glob("*.jsonl"))
    records = [json.loads(line) for f in files for line in f.read_text().splitlines() if line.strip()]
    if not records:
        sys.exit("no answers yet: run measure/run.py first")
    counts = score(records, config)
    engines = sorted({e for e, _ in counts})
    print(f"{len(records)} records from {', '.join(f.name for f in files)}\n")
    print("| prompt | " + " | ".join(f"{e} hits | {e} cited" for e in engines) + " |")
    print("|---|" + "---|---|" * len(engines))
    for p in config["prompts"]:
        cells = []
        for e in engines:
            c = counts.get((e, p["id"]), {"hits": 0, "cited": 0, "n": 0, "errors": 0})
            err = f" ({c['errors']} failed)" if c["errors"] else ""
            cells += [f"{c['hits']}/{c['n']}{err}", f"{c['cited']}/{c['n']}"]
        print(f"| {p['id']} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()
