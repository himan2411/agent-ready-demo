"""Send every prompt to every engine whose API key is set, and append the raw answers to answers/<date>.jsonl.

Each prompt goes out as a fresh single-turn request, with no history. Errors are recorded, not retried.
An HTTP error is logged as its status only; the response body, which can echo part of the key, goes to the terminal.
Run: python3 measure/run.py [repeats, default 3]
"""
import http.client
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).parent
PROMPTS = json.loads((HERE / "prompts.json").read_text())["prompts"]
ENGINES = json.loads((HERE / "engines.json").read_text())


def ask(engine, key, text):
    body = {**engine["body"], "messages": [{"role": "user", "content": text}]}
    req = urllib.request.Request(engine["url"], data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def main():
    try:
        repeats = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    except ValueError:
        sys.exit("usage: python3 measure/run.py [repeats, a whole number]")
    ready = [e for e in ENGINES if os.environ.get(e["key_env"])]
    for e in ENGINES:
        if e not in ready:
            print(f"skip {e['name']}: {e['key_env']} is not set")
    if not ready:
        sys.exit("no engine has a key set, nothing to run")
    now = datetime.now(UTC)
    out = HERE / "answers" / f"{now:%Y-%m-%d}.jsonl"
    out.parent.mkdir(exist_ok=True)
    with out.open("a") as f:
        for e in ready:
            for p in PROMPTS:
                for run in range(1, repeats + 1):
                    rec = {"at": datetime.now(UTC).isoformat(timespec="seconds"), "engine": e["name"],
                           "model": e["body"]["model"], "prompt_id": p["id"], "prompt": p["text"], "run": run}
                    try:
                        raw = ask(e, os.environ[e["key_env"]], p["text"])
                        rec |= {"answer": raw["choices"][0]["message"]["content"], "raw": raw}
                    except urllib.error.HTTPError as err:
                        rec["error"] = f"HTTP {err.code} {err.reason}"
                        print(err.read().decode(errors="replace")[:500], file=sys.stderr)
                    except (OSError, http.client.HTTPException, KeyError, IndexError, TypeError, ValueError) as err:
                        rec["error"] = f"{type(err).__name__}: {err}"
                    f.write(json.dumps(rec) + "\n")
                    f.flush()
                    print(e["name"], p["id"], run, "error" if "error" in rec else "ok")
    print("wrote", out)


if __name__ == "__main__":
    main()
