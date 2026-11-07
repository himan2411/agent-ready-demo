"""Count hits as raw n/N per prompt and engine, from the answer logs.

A hit is an answer matching the prompt's 'expect' regex. 'cited' counts answers whose full
response (text, citations, search results) contains the business's domain. Failed requests are
counted separately and left out of N.
Run: python3 measure/score.py [answers/*.jsonl ...]  (default: every file in measure/answers)
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent


def score(records, config):
    expect = {p["id"]: re.compile(p["expect"], re.IGNORECASE | re.DOTALL) for p in config["prompts"]}
    counts = defaultdict(lambda: {"hits": 0, "cited": 0, "n": 0, "errors": 0})
    for r in records:
        c = counts[r["engine"], r["prompt_id"]]
        if "error" in r:
            c["errors"] += 1
            continue
        c["n"] += 1
        c["hits"] += bool(expect[r["prompt_id"]].search(r["answer"] or ""))
        c["cited"] += config["domain"].lower() in json.dumps(r["raw"]).lower()
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
