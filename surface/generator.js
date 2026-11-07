// Business facts in, JSON-LD and llms.txt out. Pure functions first so they can be tested in Node.
(function (exports) {
  const lines = (s) => String(s || "").split("\n").map((l) => l.trim()).filter(Boolean);

  function isUrl(s) {
    try { const u = new URL(s); return u.protocol === "https:" || u.protocol === "http:"; } catch { return false; }
  }

  function parseFaq(s) {
    const out = [];
    let q = null;
    for (const l of lines(s)) {
      const m = /^([QA]):\s*(.*)$/i.exec(l);
      if (!m) { if (q && q.a !== undefined) q.a += " " + l; continue; }
      if (m[1].toUpperCase() === "Q") { q = { q: m[2] }; out.push(q); }
      else if (q) q.a = q.a === undefined ? m[2] : q.a + " " + m[2];
    }
    return out.filter((x) => x.q && x.a);
  }

  function parsePages(s) {
    return lines(s).map((l) => l.split("|").map((p) => p.trim())).filter((p) => p[0] && isUrl(p[1]))
      .map(([title, url, note]) => ({ title, url, note: note || "" }));
  }

  function validate(f) {
    const errors = [];
    if (!f.name?.trim()) errors.push("Add a company name.");
    if (!isUrl(f.url)) errors.push("Website must be a full URL, starting with https://.");
    if (!f.description?.trim()) errors.push("Add a one-sentence description.");
    if (f.logo && !isUrl(f.logo)) errors.push("Logo must be a full URL.");
    if (f.foundingDate && !/^\d{4}$/.test(f.foundingDate.trim())) errors.push("Founding year should be four digits.");
    const bad = lines(f.sameAs).filter((u) => !isUrl(u));
    if (bad.length) errors.push("Not a URL: " + bad[0]);
    return errors;
  }

  function buildJsonLd(f) {
    const url = f.url.trim().replace(/\/?$/, "/");
    const org = { "@type": f.type || "Organization", "@id": url + "#org", name: f.name.trim(), url, description: f.description.trim() };
    if (f.logo) org.logo = f.logo.trim();
    if (f.foundingDate) org.foundingDate = f.foundingDate.trim();
    if (f.founder) org.founder = { "@type": "Person", name: f.founder.trim() };
    if (f.email) org.email = f.email.trim();
    const same = lines(f.sameAs);
    if (same.length) org.sameAs = same;
    const graph = [org];
    const faq = parseFaq(f.faq);
    if (faq.length) {
      graph.push({
        "@type": "FAQPage",
        mainEntity: faq.map(({ q, a }) => ({ "@type": "Question", name: q, acceptedAnswer: { "@type": "Answer", text: a } })),
      });
    }
    return { "@context": "https://schema.org", "@graph": graph };
  }

  function buildLlms(f) {
    const out = ["# " + f.name.trim(), "", "> " + f.description.trim(), ""];
    const facts = [];
    if (f.foundingDate) facts.push("- Founded: " + f.foundingDate.trim());
    if (f.founder) facts.push("- Founder: " + f.founder.trim());
    if (f.email) facts.push("- Contact: " + f.email.trim());
    facts.push("- Website: " + f.url.trim());
    out.push(...facts, "");
    const pages = parsePages(f.pages);
    if (pages.length) {
      out.push("## Key pages", "");
      for (const p of pages) out.push("- [" + p.title + "](" + p.url + ")" + (p.note ? ": " + p.note : ""));
      out.push("");
    }
    const faq = parseFaq(f.faq);
    if (faq.length) {
      out.push("## FAQ", "");
      for (const { q, a } of faq) out.push("- " + q + " " + a);
      out.push("");
    }
    return out.join("\n");
  }

  Object.assign(exports, { parseFaq, parsePages, validate, buildJsonLd, buildLlms, isUrl });
})(typeof module !== "undefined" ? module.exports : (window.Gen = {}));

if (typeof document !== "undefined") {
  const form = document.getElementById("gen");
  const ld = document.getElementById("ld");
  const llms = document.getElementById("llms");
  const errorsEl = document.getElementById("errors");
  const live = document.getElementById("live");

  const render = () => {
    const f = Object.fromEntries(new FormData(form));
    const errors = Gen.validate(f);
    errorsEl.textContent = errors.join(" ");
    form.querySelectorAll("[required]").forEach((el) => el.setAttribute("aria-invalid", String(!el.value.trim())));
    if (errors.length) return;
    ld.textContent = '<script type="application/ld+json">\n' + JSON.stringify(Gen.buildJsonLd(f), null, 2) + "\n</" + "script>";
    llms.textContent = Gen.buildLlms(f);
  };
  form.addEventListener("input", render);
  render();

  document.querySelectorAll("[data-copy]").forEach((btn) => btn.addEventListener("click", async () => {
    const text = document.getElementById(btn.dataset.copy).textContent;
    try { await navigator.clipboard.writeText(text); live.textContent = "Copied."; btn.textContent = "Copied"; }
    catch { live.textContent = "Copy failed. Select the text and copy it by hand."; }
    setTimeout(() => { btn.textContent = "Copy"; }, 1500);
  }));

  document.getElementById("dl").addEventListener("click", () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([llms.textContent], { type: "text/plain" }));
    a.download = "llms.txt";
    a.click();
    URL.revokeObjectURL(a.href);
  });
}
