# DE Outreach: plan and research notes

Goal: the workflow of [yc-outreach](https://github.com/adityajha2005/yc-outreach) (pick a batch, get founders and
emails, write one template, send to everyone) rebuilt for the **German job market**.

The original only covers YC companies, which are mostly in the US. In Germany most hiring happens at startups and
Mittelstand companies that aren't in any YC batch, so this version needs other sources. Germany also offers a
source the US doesn't: every commercial website must publish an **Impressum** that names the managing director.

---

## 1. Research findings

### Where German companies come from

| Source | What it gives | Access | Used for |
|---|---|---|---|
| **YC directory, `regions=Germany`** (Algolia index `YCCompany_production`) | ~50–60 German YC startups, website, one-liner, batch, `isHiring`, `status` | Public, read-only search key embedded in ycombinator.com | "YC startups (DACH)" source. Founders come from each company's YC page, as in the original |
| **Bundesagentur für Arbeit Jobsuche API** (`rest.arbeitsagentur.de/jobboerse/jobsuche-service`) | The largest job database in Germany: `was`/`wo`/`umkreis`/`angebotsart`/`veroeffentlichtseit`, filters out temp agencies (`zeitarbeit=false`) and private recruiters (`pav=false`) | Free, header `X-API-Key: jobboerse-jobsuche` ([bundesAPI/jobsuche-api](https://github.com/bundesAPI/jobsuche-api)) | "Jobs: Bundesagentur" source. Job details (`/pc/v4/jobdetails/{base64(refnr)}`) include **`arbeitgeberdarstellungUrl` (employer website)** and the ad text, which often names an *Ansprechpartner* |
| **Arbeitnow API** (`arbeitnow.com/api/job-board-api`) | Berlin-built board for English-speaking roles; `visa_sponsorship=true`, `remote` | Free, no key, paginated (`links.next`) | "Jobs: Arbeitnow" source for English-language and visa-sponsored roles. No company website in the payload, so the domain is found from links in the ad or guessed from the name and verified |
| **Your own list** | Anything: LinkedIn, Berlin Startup Map, startbase.de, Gründerszene lists | Paste `Company, https://site` lines | "My list" source |

Dealroom, Crunchbase, North Data and Handelsregister bulk data are paid or restricted, so they were left out.

### The Impressum: the German founder directory

§ 5 DDG (the Digitale-Dienste-Gesetz, which replaced § 5 TMG on 14 May 2024) requires every commercial site to publish:

- the name and legal form of the company and **the authorised representative** (*Vertretungsberechtigter*:
  Geschäftsführer for a GmbH/UG, Vorstand for an AG, the Komplementär's Geschäftsführer for a GmbH & Co. KG),
- **an email address** (a contact form alone is not enough),
- the register court and number (HRB/HRA) where applicable.

Typical wording to parse: `Geschäftsführer: Dr. Max Mustermann, Erika Musterfrau`,
`Vertreten durch den Geschäftsführer Herrn Jakob Hofer`, `Geschäftsführer der Hofer Verwaltungs GmbH: Jakob Hofer`,
`Vertretungsberechtigte Gesellschafter: …`, `Vorstand: …`, `Managing Directors: …`, `Represented by: …`.
`Herr`/`Frau` give the gender needed for a formal German greeting (`Sehr geehrter Herr Hofer`).
Emails are often obfuscated (`info (at) firma (punkt) de`, Cloudflare `data-cfemail`), so the parser decodes both.

### German email patterns

Reported distribution across DACH B2B addresses (Overloop, 12M verified emails):
`vorname.nachname@` 41% (dominant in Mittelstand), `vorname@` 17% (startups and teams under 50),
`v.nachname@` 11%, `vornamenachname@` 6%, `nachname@` 4%. Managing directors almost always use the company's
standard format. Two things matter in Germany specifically:

1. **Umlauts are transliterated**: `Jürgen Müller` becomes `juergen.mueller@`, not `jurgen.muller@` (the
   original tool's NFKD normalisation gets this wrong). Both spellings are generated, the `ae/oe/ue/ss` one first.
2. **The mail domain is not always the website domain** (`firma.com` website, `firma-gmbh.de` mail). The
   Impressum email reveals the real mail domain, so guesses use that.

Pattern order: startups (YC, small teams) `first, first.last, f.last, flast, firstlast, last`; everything else
`first.last, first, f.last, flast, firstlast, last`. If a real personal address is found on the same domain and
matches a known person (or looks like `x.y@`), that pattern goes first and the label becomes **pattern** instead of
**guess**.

German companies also publish **application inboxes** (`bewerbung@`, `jobs@`, `karriere@`), which are the official
channel for an *Initiativbewerbung*. They're shown as a fallback recipient with their own label.

### Conventions for a German cold application (Initiativbewerbung)

- Subject: `Initiativbewerbung als …` or `Bewerbung als <Stelle>`.
- Formal (Sie) by default for Mittelstand: `Sehr geehrte Frau Dr. Müller,`, or `Guten Tag Vorname Nachname,` when
  the gender is unknown, or `Sehr geehrte Damen und Herren,` with no name. Startups are often fine with
  `Hallo Vorname,` (du), and many Berlin startups work in English.
- The first line after the greeting starts lowercase in German.
- Expected details: earliest start date (*frühestmöglicher Eintritt*), salary expectation (*Gehaltsvorstellung*,
  often requested), work permit status (EU Blue Card, Chancenkarte, needs sponsorship), CV link, phone.
- Close with `Mit freundlichen Grüßen` (Sie) or `Viele Grüße` (du).

### Legal (not legal advice)

- **UWG § 7(2)** bans *advertising* by email without prior consent, B2B included. A job application from a
  private person is not advertising goods or services, and speculative applications by email are normal in
  Germany. **Pitching freelance or agency services is advertising**, though, and is not allowed without consent.
  The tool is for job applications only.
- **GDPR**: a business email of a named person is personal data. Use it only for a one-to-one application, keep
  the data local (the tool stores everything in your browser only), don't build or share lists, and stop
  immediately if someone says no.

---

## 2. Design

Same shape as the original on purpose: **Python standard library only, one HTML file, no build, no database**.
It runs locally with `python3 serve.py` or deploys to Vercel as-is.

```
index.html  ──GET /api/de?action=yc_companies|arbeitnow|ba_jobs──▶  api/de.py  ──▶ YC Algolia / Arbeitnow / BA
            ──POST /api/de {action: enrich, companies: [≤10]}────▶  api/de.py  ──▶ company site: home → Impressum
                                                                                  → careers page, YC founder page,
                                                                                  BA job details, DNS-over-HTTPS MX
browser localStorage: your details, templates, sent marks, chosen recipients, last 6 result sets
browser → Apify (optional, your own token): verified emails
```

### Enrichment pipeline (per company, bounded by a 25 s deadline with partial results)

1. **Website**: given (list/YC) → BA job details `arbeitgeberdarstellungUrl` → links in the job ad → guess
   `name.de/.com/.io/...` from the company name, keeping a candidate only if its homepage mentions the company.
2. **Homepage** → find the Impressum, careers and contact links (`impressum|imprint|legal notice`,
   `karriere|jobs|careers`), falling back to `/impressum`, `/imprint`, `/de/impressum`, `/legal-notice`.
3. **Impressum** → representatives (name, gender, Dr./Prof. title, role), legal name, HRB/HRA number, city,
   emails.
4. **Careers page** → application inbox.
5. **People** = YC founders ∪ Impressum representatives ∪ the job ad's *Ansprechpartner* (deduplicated).
6. **Emails**: classify into personal / application inbox / management inbox / generic; drop noise
   (`datenschutz@`, `noreply@`, …). Infer the pattern, then build guesses per person on the real mail domain.
7. **MX check** over DNS-over-HTTPS (Cloudflare, Google fallback) so domains that can't receive mail get no
   guesses. It also shows the mail provider (Google Workspace, Microsoft 365, IONOS, Strato, …).

### Email labels, best first

`verified` / `unverified` (Apify) › `on site` (personal address found on the site or in the Impressum) ›
`in job ad` › `pattern` (guess using a pattern seen on this domain) › `guess` › `jobs inbox` › `mgmt inbox` ›
`generic`.

### Security

The original only fetched websites that came from YC's data. Here users can paste their own URLs, so every
fetch of a company site goes through `check_url`: http(s) only, ports 80/443, and the host must resolve to public
IPs only (no loopback, private, link-local or metadata addresses). The check runs again on every redirect hop.
Responses are capped at 2 MB, and the API only returns extracted names and emails, never page content. Everything
from the network is escaped in the UI, and only `http(s)` URLs are turned into links.

### UI changes from the original

- Source tabs (YC DACH / Arbeitnow / Bundesagentur / My list) replace the batch picker. All companies are listed
  right away, and contacts are filled in 10 at a time (automatically for the first 10).
- Template **language (DE/EN)** and **tone (du/Sie)**. `{greeting}`, `{closing}` and `{hook}` adapt to the
  language, the tone, the recipient's gender and title, and the source (YC one-liner vs job title).
- Extra details: target role, LinkedIn, phone, location, start date, salary, work permit. A line whose
  placeholder is empty is dropped.
- A recipient picker on each card lists every person, guess and inbox.
- Gmail compose button, editable website with re-check, CSV export.

---

## 3. Build order

1. `api/de.py`: sources, safe fetch, Impressum parser, email logic, enrichment, HTTP handler
2. `serve.py` (GET + POST), `vercel.json`
3. `index.html`
4. `cli.py`: bulk export to JSON/CSV for a list or a BA search
5. Tests: `tests/test_de.py` (stdlib `unittest`, offline fixtures) and `tests/smoke.mjs` (Playwright, mocked API)
6. README

## 4. Known limits and next steps

- Impressum parsing is heuristic. Names written surname-first (`Hofer Jakob`) aren't detected as such.
- Name-based domain guessing can miss companies with unusual domains; the card has an editable website field.
- No SMTP mailbox check: port 25 is blocked on most networks and catch-all servers make the result unreliable.
  Use the optional Apify lookup for verified addresses.
- The BA API is unofficial and versioned (`v4`/`v6`). The client tries both and normalises their field names.
- Possible later additions: Personio/Join company job feeds, Handelsregister lookup via OffeneRegister, a
  follow-up reminder after N days.
