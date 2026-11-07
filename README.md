# Agent-ready and cited: Larkline

Larkline is a fictional invoicing software company. It does not exist, and every fact, price and slot in this repo is made up.

I use it to show both halves of the job in one place:

1. **Make the business agent-ready.** Give it a surface that agents can read and query: a page with JSON-LD, an `llms.txt`, and a read-only MCP server with services, open demo slots and policies. All three state the same facts word for word.
2. **Measure whether AI answers pick it up.** A frozen set of buyer questions goes to AI answer engines, the raw answers are kept, and each result is a plain count: n of N answers got the fact right, n of N cited the site.

## What is in it

- `surface/facts.json`: the business facts, written once.
- `surface/build.js`: builds `site/index.html` (with Organization and FAQPage JSON-LD) and `site/llms.txt` from those facts. `surface/generator.js` is copied unchanged from the structured data generator on my site.
- `mcp/server.py`: the read-only MCP availability server from my site, with Larkline's data in `mcp/data.json`. The only change is two tool descriptions.
- `smoke_test.py`: a scripted agent opens one MCP session and answers three buyer questions. It fails if the MCP server and the published site disagree on price or trial.
- `measure/`: the prompt set (`prompts.json`), the engines (`engines.json`), the runner (`run.py`) and the scorer (`score.py`). Raw answers land in `measure/answers/<date>.jsonl`.

## Run it

Python 3.11 or newer and Node 18 or newer. Nothing to install.

```sh
node surface/build.js          # rebuild site/ after editing surface/facts.json
python3 smoke_test.py          # agent smoke test against the MCP server
python3 measure/test_score.py  # checks the scoring rules
```

To use the server from an MCP client, point it at `python3 mcp/server.py`.

The measurement needs paid API keys:

```sh
OPENAI_API_KEY=... PERPLEXITY_API_KEY=... python3 measure/run.py 3   # each prompt 3 times per engine
python3 measure/score.py
```

Engines without a key are skipped. Model names in `engines.json` are as of November 2026; check the provider's docs if a request fails.

## Results

**Agent smoke test: passing** (7 Nov 2026). The scripted agent's answers:

```
Q: How much does Larkline cost, and is there a trial?
A: Plans start at $19 a month. Solo is $19 a month for one user. Team is $49 a month for up to 50 seats. Yes. 14 days on any plan, no card needed.
Q: Can I get a demo on 17 November?
A: Yes, at 09:30 America/New_York. It takes 30 minutes and costs $0. Calls are booked by email to hello@larkline.example. Agents can read slots but cannot book.
Q: Book me in.
A: I can't book. The server is read-only: Calls are booked by email to hello@larkline.example. Agents can read slots but cannot book.
```

I also connected to the server with the official MCP Python SDK client (version 2.3.0). It completed the handshake, listed the three tools and read demo slots and pricing.

**AI answer measurement: not run yet.** Two things are missing:

- API keys for at least one engine. I have not run anything, so there are no counts to report.
- A public address. `larkline.example` is a reserved domain that no engine can crawl, so a run today would only show what engines say about an unknown name. That is a fair baseline, but the "after" needs `site/` published somewhere public, with `url` in `surface/facts.json` and `domain` in `measure/prompts.json` set to that address.

## Limits

- The MCP server speaks stdio, so it works for local agents. A remote agent would need it served over HTTP.
- The scoring is a regex per question. It is simple to check by hand against the raw answers, which is the point, but it can miss a correct answer phrased in an unexpected way.
