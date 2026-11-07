// Builds the agent-facing site from facts.json: index.html (with JSON-LD) and llms.txt.
// generator.js is copied unchanged from my personal site's structured data generator.
// Run: node surface/build.js
const fs = require("node:fs");
const path = require("node:path");
const Gen = require("./generator.js");

const facts = JSON.parse(fs.readFileSync(path.join(__dirname, "facts.json"), "utf8"));
const errors = Gen.validate(facts);
if (errors.length) throw new Error(errors.join(" "));

const out = path.join(__dirname, "..", "site");
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const ld = JSON.stringify(Gen.buildJsonLd(facts), null, 2).replace(/</g, "\\u003c");
const faq = Gen.parseFaq(facts.faq).map(({ q, a }) => `      <dt>${esc(q)}</dt>\n      <dd>${esc(a)}</dd>`).join("\n");

const html = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${esc(facts.name)} (fictional demo company)</title>
  <meta name="description" content="${esc(facts.description)}">
  <link rel="alternate" type="text/plain" href="llms.txt" title="llms.txt">
  <script type="application/ld+json">
${ld}
  </script>
  <style>
    :root { color-scheme: light dark; --bg: #fbfaf7; --fg: #1d1c1a; --muted: #5d5a54; --line: #dedad2; --note: #fff4d6; }
    @media (prefers-color-scheme: dark) { :root { --bg: #151514; --fg: #ecebe7; --muted: #a8a59e; --line: #34332f; --note: #3a3220; } }
    body { margin: 0; background: var(--bg); color: var(--fg); font: 17px/1.55 system-ui, sans-serif; }
    main { max-width: 680px; margin: 0 auto; padding: 32px 16px 64px; }
    .note { background: var(--note); border: 1px solid var(--line); border-radius: 6px; padding: 10px 14px; font-size: 15px; }
    h1 { font-size: 34px; margin: 28px 0 8px; }
    h2 { font-size: 21px; margin: 40px 0 12px; }
    p.lede, dd, li { color: var(--muted); }
    dt { font-weight: 600; margin-top: 16px; }
    dd { margin: 4px 0 0; }
    code { font-size: 15px; }
    a { color: inherit; }
  </style>
</head>
<body>
  <main>
    <p class="note"><strong>Fictional company.</strong> ${esc(facts.name)} does not exist. Every fact, price and slot here is made up for a demo.</p>
    <h1>${esc(facts.name)}</h1>
    <p class="lede">${esc(facts.description)}</p>
    <h2 id="faq">Questions</h2>
    <dl>
${faq}
    </dl>
    <h2 id="agents">For AI agents</h2>
    <ul>
      <li><a href="llms.txt">llms.txt</a> has the same facts as plain text.</li>
      <li>This page carries Organization and FAQPage JSON-LD that matches the answers above word for word.</li>
      <li>A read-only MCP server answers <code>list_services</code>, <code>get_availability</code> and <code>get_policies</code>. Its code is in <a href="https://github.com/himan2411/agent-ready-demo/tree/main/mcp">the demo's repository</a>; run it with <code>python3 mcp/server.py</code>.</li>
    </ul>
  </main>
</body>
</html>
`;

fs.writeFileSync(path.join(out, "index.html"), html);
fs.writeFileSync(path.join(out, "llms.txt"), Gen.buildLlms(facts));
console.log("wrote site/index.html and site/llms.txt");
