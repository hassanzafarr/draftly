# DE Outreach

Cold-apply to companies in Germany. Pick a source (YC startups in DACH, English-friendly jobs on Arbeitnow,
Germany's federal job board, or your own list), and the tool finds the people who run each company and their likely
email addresses. You write one template (German or English, *du* or *Sie*) and get a personalised draft per company.
Free, with no API keys or sign-up, and everything stays in your browser.

```
python3 serve.py        # open http://localhost:8765
```

Python 3.9+, standard library only. Nothing to install. (On Windows: `py serve.py`.)

Adapted from [yc-outreach](https://github.com/adityajha2005/yc-outreach) for the German job market. Research notes
and design are in [PLAN.md](PLAN.md).

## Why it works in Germany: the Impressum

German law (§ 5 DDG) requires every commercial website to publish an **Impressum** that names the managing directors
(*Geschäftsführer*, *Vorstand*, *Inhaber*) and gives an email address. That makes it a public directory of the people
who run each company. The tool reads it, along with the careers page and, for YC companies, the founder list, and
builds email addresses the German way:

- `Jürgen Müller` becomes `juergen.mueller@`, not `jurgen.muller@`; both spellings are generated, `ae/oe/ue/ss` first.
- Order: `vorname.nachname@` first for established companies (41% of DACH addresses), `vorname@` first for startups.
- If any real address on the domain is found (`a.schroeder@`), its pattern is used for everyone, labelled **pattern**.
- The mail domain comes from the Impressum when it differs from the website (`firma.com` site, `firma-gmbh.de` mail).
- A DNS MX check skips domains that can't receive mail and shows the provider (Google Workspace, Microsoft 365, IONOS, …).
- Application inboxes (`bewerbung@`, `jobs@`, `karriere@`) are listed as a fallback recipient.

## What it does

1. **Your details**: name, target role, links, CV, start date, salary expectation, work permit (Blue Card, Chancenkarte, …).
2. **Template**: German or English, formal (*Sie*) or casual (*du*). Special placeholders:

   | Placeholder | Becomes |
   |---|---|
   | `{greeting}` | `Sehr geehrter Herr Dr. Müller,` · `Sehr geehrte Frau Vogel,` · `Guten Tag Anna Schröder,` (gender unknown) · `Sehr geehrte Damen und Herren,` (inbox) · `Hallo Jürgen,` · `Hi Jürgen,` |
   | `{hook}` | A first sentence about the job you found (*…dass Sie eine Stelle als Backend Engineer ausgeschrieben haben…*), the YC one-liner, or a plain speculative application (*Initiativbewerbung*) |
   | `{closing}` | `Mit freundlichen Grüßen` · `Viele Grüße` · `Best regards,` · `Best,` |
   | `{position}` | The job title without `(m/w/d)`, or your target role |

   Also `{first_name} {last_name} {company} {one_liner} {job_title} {city}` plus all your details. Any line whose
   placeholder is empty is dropped, so `Gehaltsvorstellung: {salary}` disappears if you leave salary blank.
3. **Find companies**:

   | Source | What you get |
   |---|---|
   | **YC startups (DACH)** | Every active YC company in Germany, Austria or Switzerland, with founders from YC and directors from the Impressum |
   | **Jobs: Arbeitnow** | English-friendly roles in Germany, optionally only with **visa sponsorship**, grouped by company |
   | **Jobs: Bundesagentur** | Germany's largest job database, by title, city and radius, without temp agencies and private recruiters. The employer's website and the ad's *Ansprechpartner* come from the job details |
   | **My list** | Paste `Company, https://site` lines from anywhere. With no website, it's guessed from the name and only kept if the homepage mentions the company |

   Contacts are looked up 10 companies at a time (about 10–30 s). Each card lets you fix the website and check again.
4. **Verified emails (optional)**: paste your own Apify token. Lookups go from your browser straight to Apify.

Each card shows the people found, a **Send to** picker with every address and inbox, the draft, and buttons to copy
it, open it in your mail app or in Gmail, and mark it as sent. **Export CSV** saves the current list.

### Email labels, most reliable first

| Label | Meaning |
|---|---|
| `verified` / `unverified` | Apify lookup (optional) |
| `on site` | A personal address found on the company's site or Impressum |
| `in job ad` | Address of the job ad's contact person |
| `pattern` | Built from a naming pattern seen on this domain |
| `guess` | The most common German pattern. It may bounce |
| `jobs inbox` / `mgmt inbox` | `bewerbung@`, `jobs@`, `karriere@` / `gf@`, `founders@` |
| `generic` | `info@`, `kontakt@` |

## Before you send

- **Job applications only.** A speculative application (*Initiativbewerbung*) from a private person is normal in
  Germany. Pitching freelance or agency services by cold email is advertising under **UWG § 7** and needs prior
  consent. Not legal advice.
- Director emails are personal data (**GDPR**). Write one person at a time, don't build or share lists, and stop
  when someone says no. The tool keeps everything in your browser, and CLI output is gitignored.
- Formal *Sie* is the safe default for the Mittelstand. Many Berlin startups are fine with *du* or English.
- Replace the `[bracketed]` lines with something specific. Send a few `guess` emails first and watch for bounces.

## Deploy

On [Vercel](https://vercel.com/new), import the repo and set **Root Directory** to `de-outreach`. There's no build step
and no environment variables. `index.html` is static and `api/de.py` runs as a Python function (`vercel.json` allows
60 s). It is meant as a personal tool: the API fetches company websites, so every site fetch is restricted to public
http(s) hosts on ports 80/443, re-checked on each redirect, and only extracted names and emails are returned.
DNS rebinding is out of scope for a local tool.

## HTTP API

`GET` returns JSON. Errors are `{"error": "..."}` with status 400 (bad input) or 502 (upstream unreachable).

| Request | Returns |
|---|---|
| `GET /api/de?action=yc_companies&region=Germany` | `[{id, name, yc_slug, batch, website, one_liner, hiring, kind, ...}]`. Regions: `Germany`, `Austria`, `Switzerland` |
| `GET /api/de?action=arbeitnow&q=python&visa=1&remote=1&page=1` | `{jobs: [{title, company, location, url, emails, website, ...}], next_page}` |
| `GET /api/de?action=ba_jobs&was=Entwickler&wo=Berlin&umkreis=25&angebotsart=1&days=30&page=1` | `{jobs: [{title, company, location, refnr, url, ...}], total, next_page}` |
| `POST /api/de` `{"action":"enrich","companies":[{id, name, website, yc_slug, ba_refnr, emails, kind}]}` (max 10) | Per company: `website, mail_domain, mx, mx_provider, impressum_url, legal_name, register, city, pattern, people: [{name, first, last, gender, title, role, source, emails: [{email, label}]}], inboxes, notes` |

## Command line

For bulk exports to `<out>.json` and `<out>.csv` (gitignored):

```
python3 cli.py list companies.txt --out leads
python3 cli.py ba --was "Softwareentwickler" --wo Berlin --pages 2
python3 cli.py arbeitnow --q python --visa
python3 cli.py yc --region Germany
```

## Tests

```
python3 -m unittest discover -s tests          # 42 offline tests, every fetch faked or local
NODE_PATH="$(npm root -g)" node tests/smoke.cjs # browser test with a mocked API (needs Playwright + Chromium)
```

## Project layout

| File | Role |
|---|---|
| `index.html` | The whole UI: one file with inline CSS and JS, no framework, no build |
| `api/de.py` | Sources, safe fetching, Impressum parser, email logic, enrichment, HTTP handler (Vercel's `handler`) |
| `serve.py` | Local server: serves `index.html`, routes `/api/de` to the same handler |
| `cli.py` | Bulk export |
| `tests/` | `test_de.py` (unittest) and `smoke.cjs` (Playwright) |
| `PLAN.md` | Research, design decisions, known limits |

## Data sources

- YC directory: YC's public Algolia search (key read from ycombinator.com at runtime) and the `data-page` JSON on each
  company page.
- [Arbeitnow job board API](https://www.arbeitnow.com/blog/job-board-api): public, no key.
- [Bundesagentur für Arbeit Jobsuche API](https://github.com/bundesAPI/jobsuche-api): public client id
  `jobboerse-jobsuche`. It's unofficial and versioned, so the tool tries `v4` then `v6`.
- Company websites: homepage, Impressum, careers and contact pages.
- MX records: DNS-over-HTTPS (Cloudflare, Google fallback).

## License

MIT. Parts are adapted from yc-outreach (MIT, © 2026 yc-founder-outreach contributors). See [LICENSE](LICENSE).
