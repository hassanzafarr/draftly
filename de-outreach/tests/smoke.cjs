// Browser smoke test of index.html with a mocked API (no network).
// Run: NODE_PATH="$(npm root -g)" node tests/smoke.cjs     (needs the `playwright` package + a Chromium)
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..");
const PORT = 8800 + Math.floor(Math.random() * 150);
const BASE = `http://127.0.0.1:${PORT}`;

const person = (name, first, last, gender, title, role, emails) => ({ name, first, last, gender, title, role, source: "impressum", linkedin: "", twitter: "", emails });
const info = (id, name, extra) => ({ id, name, website: "", domain: "", mail_domain: "", mx: true, mx_provider: "", impressum_url: "", careers_url: "",
  legal_name: "", register: "", city: "", one_liner: "", linkedin: "", pattern: "", pattern_from: "", people: [], inboxes: [], notes: [], ...extra });
const ENRICH = {
  "list:flowbase.de": info("list:flowbase.de", "Flowbase", {
    website: "https://flowbase.de", domain: "flowbase.de", mail_domain: "flowbase.de", mx_provider: "Google Workspace", city: "Berlin",
    impressum_url: "https://flowbase.de/impressum", legal_name: "Flowbase GmbH", pattern: "first.last", pattern_from: "anna.schroeder@flowbase.de",
    people: [person("Jürgen Müller", "Jürgen", "Müller", "m", "Dr.", "Geschäftsführer", [
      { email: "juergen.mueller@flowbase.de", label: "pattern" }, { email: "juergen@flowbase.de", label: "guess" }])],
    inboxes: [{ email: "bewerbung@flowbase.de", label: "jobs" }, { email: "info@flowbase.de", label: "generic" }] }),
  "list:evil.de": info("list:evil.de", "x", { website: "javascript:alert(1)", notes: ["<b>bold?</b>"],
    people: [person("Eve <script>", "Eve", "<script>", "", "", "<i>role</i>", [{ email: "eve@evil.de", label: "guess" }])] }),
  "an:acme gmbh": info("an:acme gmbh", "Acme GmbH", { website: "https://acme.de", domain: "acme.de", mail_domain: "acme.de",
    people: [person("Lena Vogel", "Lena", "Vogel", "f", "", "Geschäftsführerin", [{ email: "lena.vogel@acme.de", label: "site" }])] }),
  "an:gamma": info("an:gamma", "Gamma", { inboxes: [{ email: "jobs@gamma.io", label: "jobs" }] }),
};
const JOBS = {
  1: { jobs: [
    { source: "arbeitnow", title: "Backend Engineer (m/w/d)", company: "Acme GmbH", location: "Berlin", remote: false, url: "https://arbeitnow.com/1", tags: [], date: "2026-10-01", emails: ["jobs@acme.de"], website: "" },
    { source: "arbeitnow", title: "Python Developer (all genders)", company: "Acme GmbH", location: "Berlin", remote: true, url: "https://arbeitnow.com/2", tags: [], date: "2026-10-01", emails: [], website: "" },
    { source: "arbeitnow", title: "Data Engineer", company: "Beta AG", location: "Hamburg", remote: false, url: "https://arbeitnow.com/3", tags: [], date: "2026-09-30", emails: [], website: "" }],
    next_page: 2 },
  2: { jobs: [{ source: "arbeitnow", title: "ML Engineer", company: "Gamma", location: "München", remote: false, url: "https://arbeitnow.com/4", tags: [], date: "", emails: [], website: "" }], next_page: null },
};

async function main() {
  const server = spawn("python3", ["serve.py"], { cwd: ROOT, env: { ...process.env, PORT: String(PORT) }, stdio: "ignore" });
  const browser = await chromium.launch();
  try {
    for (let i = 0; i < 50; i++) { try { await fetch(BASE); break } catch { await new Promise(r => setTimeout(r, 100)) } }
    const ctx = await browser.newContext({ acceptDownloads: true });
    const page = await ctx.newPage();
    const errors = [], posts = [];
    page.on("pageerror", e => errors.push(e.message));
    page.on("dialog", d => d.accept());
    await page.route("**/api/de**", async route => {
      const req = route.request();
      if (req.method() === "POST") {
        const body = JSON.parse(req.postData());
        posts.push(body);
        return route.fulfill({ json: body.companies.map(c => ENRICH[c.id] || { id: c.id, name: c.name, error: "Lookup failed: TimeoutError" }) });
      }
      const u = new URL(req.url());
      if (u.searchParams.get("action") === "arbeitnow") return route.fulfill({ json: JOBS[u.searchParams.get("page")] });
      return route.fulfill({ status: 400, json: { error: "Unknown action" } });
    });
    await page.goto(BASE);
    const pre = n => page.locator("#list details").nth(n).locator("pre");
    const subj = n => page.locator("#list details").nth(n).locator(".subj");
    const open = async n => {  // the toggle event that fills the draft fires asynchronously
      await page.locator("#list details").nth(n).locator("summary").click();
      await page.waitForFunction(i => document.querySelectorAll("#list details")[i].querySelector("pre").textContent.length > 0, n);
    };

    // 1. Details + a pasted list, German formal template
    await page.fill('[data-k="my_name"]', "Hassan Zafar");
    await page.fill('[data-k="role"]', "Backend Engineer");
    await page.fill('[data-k="start_date"]', "ab sofort");
    await page.fill('[data-k="cv"]', "https://cv.example/hz.pdf");
    await page.click('.tabs button[data-tab="list"]');
    await page.fill("#list_text", "Flowbase, https://flowbase.de\n<img src=x onerror=window.__xss=1>, https://evil.de\n=cmd|' /C calc'!A0, https://x.de\nFlowbase, flowbase.de");
    await page.click('.tab[data-tab="list"] .go');
    await page.waitForFunction(() => document.querySelectorAll("#list details .badge").length === 3 && ![...document.querySelectorAll("#list .badge")].some(b => b.textContent === "checking…"));
    assert.equal(await page.locator("#list details").count(), 3, "duplicate list line is merged");
    assert.equal(await page.locator("#list details").nth(0).locator(".badge").textContent(), "pattern");
    assert.equal(await page.locator("#list details").nth(2).locator(".badge").textContent(), "error");
    await open(0);
    let text = await pre(0).textContent();
    assert.ok(text.startsWith("Sehr geehrter Herr Dr. Müller,\n\nich bin auf Flowbase aufmerksam geworden und bewerbe mich initiativ als Backend Engineer."), text);
    assert.ok(text.includes("Frühestmöglicher Eintritt: ab sofort\n"), "filled line kept");
    assert.ok(!text.includes("Gehaltsvorstellung") && !text.includes("Arbeitserlaubnis") && !text.includes("{"), "empty lines dropped");
    assert.ok(text.endsWith("Mit freundlichen Grüßen\nHassan Zafar"), text);
    assert.equal(await subj(0).textContent(), "Bewerbung als Backend Engineer – Hassan Zafar");
    assert.ok((await page.locator("#list details").nth(0).locator(".mail").getAttribute("href")).startsWith("mailto:juergen.mueller%40flowbase.de?subject=Bewerbung"));
    assert.ok((await page.locator("#list details").nth(0).locator(".gmail").getAttribute("href")).includes("to=juergen.mueller%40flowbase.de"));

    // 2. du, then an inbox recipient, then English
    await page.click('#tone button[data-v="du"]');
    text = await pre(0).textContent();
    assert.ok(text.startsWith("Hallo Jürgen,") && text.endsWith("Viele Grüße\nHassan Zafar"), text);
    await page.locator("#list details").nth(0).locator("select.to").selectOption("bewerbung@flowbase.de");
    assert.ok((await pre(0).textContent()).startsWith("Hallo Flowbase-Team,"));
    assert.equal(await page.locator("#list details").nth(0).locator(".badge").textContent(), "jobs inbox");
    await page.click('#lang button[data-v="en"]');
    text = await pre(0).textContent();
    assert.ok(text.startsWith("Hi Flowbase team,\n\nI came across Flowbase and wanted to reach out about joining as Backend Engineer."), text);
    assert.ok(text.includes("Earliest start: ab sofort") && text.endsWith("Best,\nHassan Zafar"), text);
    assert.equal(await subj(0).textContent(), "Backend Engineer at Flowbase – Hassan Zafar");

    // 3. Untrusted data is shown as text, never as HTML or links
    await open(1);
    assert.equal(await page.evaluate(() => window.__xss), undefined);
    assert.equal(await page.locator("#list img, #list script, #list b:has-text('bold'), #list i:has-text('role')").count(), 0);
    assert.ok((await page.locator("#list details").nth(1).locator("summary .name").textContent()).includes("<img"));
    assert.equal(await page.locator('#list a[href^="javascript"]').count(), 0);

    // 4. CSV export (BOM, quoting, formula injection guard)
    const [dl] = await Promise.all([page.waitForEvent("download"), page.click("#csv")]);
    const csv = fs.readFileSync(await dl.path(), "utf8");
    assert.ok(csv.startsWith("﻿\"company\",\"source\""), csv.slice(0, 40));
    assert.ok(csv.includes('"Flowbase","list","https://flowbase.de"') && csv.includes('"bewerbung@flowbase.de","jobs inbox"'), csv);
    assert.ok(csv.includes(`"'=cmd|' /C calc'!A0"`), "formula cells are neutralised");

    // 5. Everything survives a reload
    await page.reload();
    await page.waitForSelector("#list details");
    assert.equal(await page.locator("#list details").count(), 3);
    assert.equal(await page.inputValue('[data-k="my_name"]'), "Hassan Zafar");
    assert.equal(await page.getAttribute('#lang button[data-v="en"]', "aria-pressed"), "true");
    await open(0);
    assert.ok((await pre(0).textContent()).startsWith("Hi Flowbase team,"), "chosen recipient persisted");
    await page.locator("#list details").nth(0).locator('[data-a="sent"]').check();
    await page.check("#hideSent");
    assert.equal(await page.locator("#list details:visible").count(), 2);
    await page.uncheck("#hideSent");

    // 6. Arbeitnow jobs: grouped per company, job-specific hook, pagination
    await page.click('#lang button[data-v="de"]');
    await page.click('#tone button[data-v="sie"]');
    await page.click('.tabs button[data-tab="an"]');
    await page.fill("#an_q", "python");
    await page.click('.tab[data-tab="an"] .go');
    await page.waitForFunction(() => document.querySelectorAll("#list details").length === 2 && ![...document.querySelectorAll("#list .badge")].some(b => /checking|not checked/.test(b.textContent)));
    const acme = posts.at(-1).companies.find(c => c.id === "an:acme gmbh");
    assert.deepEqual([acme.kind, acme.emails], ["startup", ["jobs@acme.de"]]);
    assert.ok((await page.locator("#list details").nth(0).locator(".meta").textContent()).includes("2 jobs"));
    await open(0);
    text = await pre(0).textContent();
    assert.ok(text.startsWith("Sehr geehrte Frau Vogel,\n\nich habe gesehen, dass Sie bei Acme eine Stelle als Backend Engineer ausgeschrieben haben, und möchte mich gern darauf bewerben."), text);
    assert.equal(await subj(0).textContent(), "Bewerbung als Backend Engineer – Hassan Zafar");
    await open(1);
    assert.equal(await page.locator("#list details").nth(1).locator('button[data-a="lookup"]').textContent(), "Try again");
    assert.ok(await page.isVisible("#moreResults"));
    await page.click("#moreResults");
    await page.waitForFunction(() => document.querySelectorAll("#list details").length === 3 && document.querySelectorAll("#list details")[2].querySelector(".badge").textContent === "jobs inbox");
    assert.ok(await page.isHidden("#moreResults"), "no more pages");

    assert.deepEqual(errors, []);
    console.log("smoke test passed");
  } finally {
    await browser.close();
    server.kill();
  }
}

main().catch(e => { console.error(e); process.exit(1) });
