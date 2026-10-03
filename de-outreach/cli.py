#!/usr/bin/env python3
"""Bulk export: find companies, look up their contacts, write <out>.json and <out>.csv (one row per company).

  python3 cli.py list companies.txt                       # lines: "Name, https://site" or just one of them
  python3 cli.py ba --was "Softwareentwickler" --wo Berlin --pages 2
  python3 cli.py arbeitnow --q python --visa
  python3 cli.py yc --region Germany

Common options: --out leads  --limit N  --workers 8. Output files are gitignored: contact data stays local.
"""

import argparse
import concurrent.futures as cf
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "api"))
import de  # noqa: E402

RANK = {"site": 0, "jobad": 1, "pattern": 2, "guess": 3}


def read_list(path):
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            parts = [p.strip() for p in re.split(r"[,;\t]", line) if p.strip()]
            if not parts or parts[0].startswith("#"):
                continue
            site = next((p for p in parts if re.fullmatch(r"(https?://)?[\w-]+(\.[\w-]+)+(/\S*)?", p)), "")
            name = ", ".join(p for p in parts if p != site) or de.domain_of(site)
            out.append({"id": f"list:{de.domain_of(site) or name.lower()}", "name": name, "website": site, "kind": ""})
    return out


def companies(a):
    if a.source == "yc":
        return de.yc_companies(a.region)
    if a.source == "list":
        return read_list(a.file)
    jobs, page = [], 1
    for _ in range(a.pages):
        if a.source == "arbeitnow":
            res = de.arbeitnow(a.q, a.visa, a.remote, page)
        else:
            res = de.ba_jobs(a.was, a.wo, a.umkreis, a.angebotsart, a.days, page)
        jobs += res["jobs"]
        page = res["next_page"]
        if not page:
            break
    out = de.group_jobs(jobs)
    for c in out:
        c["kind"] = "startup" if a.source == "arbeitnow" else "company"
    return out


def best(info):
    """(person, email) with the most reliable address; falls back to the jobs inbox, then any inbox."""
    cands = [(RANK.get(e["label"], 9), i, p, e) for i, p in enumerate(info.get("people") or []) for e in p.get("emails") or []]
    if cands:
        _, _, person, email = min(cands, key=lambda x: x[:2])
        return person, email
    return None, next(iter(info.get("inboxes") or []), None)


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--out", default="leads")
    common.add_argument("--limit", type=int, default=0, help="only the first N companies")
    common.add_argument("--workers", type=int, default=8)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="source", required=True)
    p = sub.add_parser("yc", parents=[common], help="YC companies in a DACH country")
    p.add_argument("--region", default="Germany", choices=de.REGIONS)
    p = sub.add_parser("list", parents=[common], help="your own list of companies")
    p.add_argument("file")
    p = sub.add_parser("ba", parents=[common], help="Bundesagentur für Arbeit job search")
    p.add_argument("--was", default="")
    p.add_argument("--wo", default="")
    p.add_argument("--umkreis", type=int, default=25)
    p.add_argument("--angebotsart", type=int, default=1, choices=(1, 4, 34), help="1 job, 34 internship, 4 Ausbildung")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--pages", type=int, default=1, help="50 jobs per page")
    p = sub.add_parser("arbeitnow", parents=[common], help="Arbeitnow (English-friendly) jobs")
    p.add_argument("--q", default="")
    p.add_argument("--visa", action="store_true")
    p.add_argument("--remote", action="store_true")
    p.add_argument("--pages", type=int, default=2, help="each call scans up to 3 Arbeitnow pages")
    a = ap.parse_args()
    if a.source == "ba" and not (a.was or a.wo):
        ap.error("ba needs --was and/or --wo")

    items = companies(a)
    items = items[: a.limit] if a.limit else items
    print(f"{len(items)} companies", file=sys.stderr)
    results = []
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for i, (item, info) in enumerate(zip(items, ex.map(de.enrich_one, items)), 1):
            _, email = best(info)
            results.append({**item, "info": info})
            found = "{email} ({label})".format(**email) if email else info.get("error") or "no email"
            print(f"[{i}/{len(items)}] {item['name']}: {found}", file=sys.stderr)

    with open(f"{a.out}.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)
    cols = [
        "company",
        "website",
        "jobs",
        "contact",
        "role",
        "gender",
        "email",
        "label",
        "other_emails",
        "jobs_inbox",
        "impressum",
        "legal_name",
        "register",
        "city",
        "mail_provider",
        "notes",
    ]
    with open(f"{a.out}.csv", "w", newline="", encoding="utf-8-sig") as fh:  # BOM so Excel shows umlauts
        w = csv.writer(fh)
        w.writerow(cols)
        for r in results:
            info = r["info"]
            person, email = best(info)
            others = [
                e["email"] for p in info.get("people") or [] for e in p.get("emails") or [] if e["label"] in ("site", "jobad")
            ]
            w.writerow(
                [
                    r["name"],
                    info.get("website", ""),
                    " | ".join(j["title"] for j in r.get("jobs") or []),
                    person["name"] if person else "",
                    person["role"] if person else "",
                    person.get("gender", "") if person else "",
                    email["email"] if email else "",
                    email["label"] if email else "",
                    " ".join(e for e in others if not email or e != email["email"]),
                    " ".join(x["email"] for x in info.get("inboxes") or [] if x["label"] == "jobs"),
                    info.get("impressum_url", ""),
                    info.get("legal_name", ""),
                    info.get("register", ""),
                    info.get("city", ""),
                    info.get("mx_provider", ""),
                    "; ".join(info.get("notes") or ([info["error"]] if info.get("error") else [])),
                ]
            )
    print(f"Wrote {a.out}.json and {a.out}.csv", file=sys.stderr)


if __name__ == "__main__":
    main()
