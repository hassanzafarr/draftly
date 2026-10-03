"""DE Outreach API: German companies, the people who run them, and their likely email addresses.

Python standard library only. Runs as a Vercel serverless function (`handler`) and locally via serve.py.

GET  /api/de?action=yc_companies&region=Germany
GET  /api/de?action=arbeitnow[&q=python][&visa=1][&remote=1][&page=1]
GET  /api/de?action=ba_jobs&was=Entwickler[&wo=Berlin][&umkreis=25][&angebotsart=1][&days=30][&page=1]
POST /api/de  {"action": "enrich", "companies": [{"id", "name", "website", "yc_slug", "ba_refnr", "emails", "kind"}]}

Enrichment reads the company's Impressum (German law requires it to name the managing directors and an email
address), its careers page, its YC founder page or BA job ad, then builds email guesses the German way
(Jürgen Müller -> juergen.mueller@). Company sites can come from user input, so every site fetch goes through
check_url() (public http(s) hosts only, re-checked on each redirect) and only extracted names/emails are returned.
"""

import base64
import collections
import concurrent.futures as cf
import html
import ipaddress
import json
import re
import socket
import ssl
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"
CTX = ssl.create_default_context()
MAX_BYTES = 2_000_000
MAX_BODY = 64_000
MAX_COMPANIES = 10
ENRICH_DEADLINE = 25  # seconds per company; whatever is found by then is returned
REGIONS = ("Germany", "Austria", "Switzerland")
BA = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service"
BA_KEY = {"X-API-Key": "jobboerse-jobsuche"}  # public client id of the BA job search app
ARBEITNOW = "https://www.arbeitnow.com/api/job-board-api"

SLUG_RE = re.compile(r"^[a-z0-9-]{1,100}$")
REFNR_RE = re.compile(r"^[0-9A-Za-z-]{5,40}$")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
EMAIL_FULL = re.compile(r"^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
BAD_EMAIL = re.compile(
    r"\.(png|jpe?g|gif|svg|webp|css|js)$|sentry|wixpress|example\.|beispiel|mustermann|musterfrau|@2x|u00"
    r"|domain\.(com|de)|email\.(com|de)|ihre-?firma|yourcompany|yourdomain",
    re.I,
)
FREEMAIL = {
    "gmail.com",
    "googlemail.com",
    "web.de",
    "gmx.de",
    "gmx.net",
    "gmx.at",
    "gmx.ch",
    "t-online.de",
    "outlook.com",
    "outlook.de",
    "hotmail.com",
    "hotmail.de",
    "live.com",
    "live.de",
    "yahoo.com",
    "yahoo.de",
    "icloud.com",
    "me.com",
    "posteo.de",
    "mailbox.org",
    "aol.com",
    "freenet.de",
    "arcor.de",
    "proton.me",
    "protonmail.com",
}
JOB_SITES = re.compile(
    r"(^|\.)(arbeitnow|greenhouse|lever|personio|join|workable|smartrecruiters|recruitee|ashbyhq|softgarden|bamboohr"
    r"|teamtailor|myworkdayjobs|workday|successfactors|linkedin|xing|stepstone|indeed|glassdoor|kununu|google|youtube"
    r"|instagram|facebook|twitter|x|github|arbeitsagentur|europa|bit|t|wa|calendly|typeform|hubspot)\.[a-z.]+$"
)

# --------------------------------------------------------------------------------------------------- fetching


def check_url(url):
    """Raise ValueError unless url is http(s) on a standard port and its host resolves to public IPs only."""
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ValueError("Only http(s) URLs are allowed")
    if p.port not in (None, 80, 443):
        raise ValueError("Only ports 80 and 443 are allowed")
    try:
        infos = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    except OSError as e:
        raise ValueError("Host doesn't resolve") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if not ip.is_global or ip.is_multicast:
            raise ValueError("Host resolves to a non-public address")


class _CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)  # a public site must not bounce us to localhost or the cloud metadata service
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_trusted = urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX))
_checked = urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX), _CheckedRedirect)


def _decode(raw, content_type):
    m = re.search(r"charset=([\w-]+)", content_type or "", re.I) or re.search(
        rb"<meta[^>]+charset=[\"']?([\w-]+)", raw[:4096], re.I
    )
    declared = m.group(1) if m else None
    if isinstance(declared, bytes):
        declared = declared.decode("ascii", "ignore")
    for enc in filter(None, (declared, "utf-8", "cp1252")):  # older German sites still ship latin-1
        try:
            return raw.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("utf-8", "ignore")


def fetch(url, timeout=8, data=None, headers=None, checked=False):
    """One attempt, short timeout. Returns (text, final_url) or (None, None). checked=True for company sites."""
    if timeout <= 0.5:
        return None, None
    try:
        if checked:
            check_url(url)
        req = urllib.request.Request(
            url, data=data, headers={"User-Agent": UA, "Accept-Language": "de,en;q=0.8", **(headers or {})}
        )
        with (_checked if checked else _trusted).open(req, timeout=timeout) as r:
            return _decode(r.read(MAX_BYTES), r.headers.get("Content-Type")), r.geturl()
    except Exception:
        return None, None


def get(url, timeout=8, data=None, headers=None):
    return fetch(url, timeout, data, headers)[0]


# --------------------------------------------------------------------------------------------------- sources

_algolia = None  # (app, key), cached per warm instance


def algolia(params):
    global _algolia
    if not _algolia:
        m = re.search(
            r'window\.AlgoliaOpts = \{"app":"(\w+)","key":"([^"]+)"', get("https://www.ycombinator.com/companies") or ""
        )
        if not m:
            raise RuntimeError("Could not read YC's company search")
        _algolia = m.group(1), m.group(2)
    app, key = _algolia
    body = json.dumps({"params": urllib.parse.urlencode(params)}).encode()
    for host in (f"{app}-dsn.algolia.net", f"{app}-1.algolianet.com", f"{app}-2.algolianet.com"):
        res = get(
            f"https://{host}/1/indexes/YCCompany_production/query",
            data=body,
            headers={"X-Algolia-Application-Id": app, "X-Algolia-API-Key": key},
        )
        if res is not None:
            return json.loads(res)
    _algolia = None  # key may have rotated
    raise RuntimeError("YC company search failed")


def yc_companies(region):
    hits, page = [], 0
    while True:
        res = algolia({"hitsPerPage": 1000, "page": page, "facetFilters": json.dumps([[f"regions:{region}"]])})
        hits += res.get("hits", [])
        page += 1
        if page >= res.get("nbPages", 0):
            break
    return [
        {
            "id": f"yc:{h['slug']}",
            "name": h.get("name") or h["slug"],
            "yc_slug": h["slug"],
            "batch": h.get("batch") or "",
            "website": h.get("website") or "",
            "one_liner": h.get("one_liner") or "",
            "industry": h.get("subindustry") or "",
            "team_size": h.get("team_size"),
            "location": h.get("all_locations") or "",
            "hiring": bool(h.get("isHiring")),
            "kind": "startup",
            "launched_at": h.get("launched_at") or 0,
        }
        for h in hits
        if h.get("slug") and h.get("status") != "Inactive"
    ]


def yc_company(slug, timeout=8):
    m = re.search(r'data-page="([^"]*)"', get(f"https://www.ycombinator.com/companies/{slug}", timeout) or "")
    if not m:
        return None
    try:
        return json.loads(html.unescape(m.group(1)))["props"]["company"]
    except (ValueError, KeyError, TypeError):
        return None


def arbeitnow(q="", visa=False, remote=False, page=1):
    """Jobs from Arbeitnow (English-friendly, visa filter). Scans up to 3 pages to fill a result page."""
    terms = [re.compile(rf"(?<![\w]){re.escape(t)}(?![\w])", re.I) for t in q.split()]
    jobs, nxt, pages = [], page, 0
    while nxt and pages < 3 and len(jobs) < 20:
        params = {"page": nxt, **({"visa_sponsorship": "true"} if visa else {})}
        body = get(f"{ARBEITNOW}?{urllib.parse.urlencode(params)}", timeout=12)
        if body is None:
            if not pages:
                raise RuntimeError("Arbeitnow is unreachable")
            break
        data = json.loads(body)
        for j in data.get("data") or []:
            desc = j.get("description") or ""
            text = html_text(desc)
            hay = " ".join([j.get("title") or "", " ".join(j.get("tags") or []), " ".join(j.get("job_types") or []), text])
            if any(not t.search(hay) for t in terms) or (remote and not j.get("remote")) or not j.get("company_name"):
                continue
            created = j.get("created_at")
            jobs.append(
                {
                    "source": "arbeitnow",
                    "title": j.get("title") or "",
                    "company": j["company_name"],
                    "location": j.get("location") or "",
                    "remote": bool(j.get("remote")),
                    "url": j.get("url") or "",
                    "tags": j.get("tags") or [],
                    "date": time.strftime("%Y-%m-%d", time.gmtime(created)) if isinstance(created, (int, float)) else "",
                    "emails": sorted(emails_in(text)),
                    "website": website_hint(desc),
                }
            )
        pages += 1
        nxt = nxt + 1 if (data.get("links") or {}).get("next") else None
    return {"jobs": jobs, "next_page": nxt}


def ba_jobs(was="", wo="", umkreis=25, angebotsart=1, days=30, page=1):
    """Bundesagentur für Arbeit job search, without temp agencies and private recruiters."""
    q = {
        "angebotsart": angebotsart,
        "page": page,
        "size": 50,
        "zeitarbeit": "false",
        "pav": "false",
        "veroeffentlichtseit": days,
        **({"was": was} if was else {}),
        **({"wo": wo, "umkreis": umkreis} if wo else {}),
    }
    for path in ("/pc/v4/jobs", "/pc/v6/jobs", "/pc/v4/app/jobs"):  # the API is unofficial and versioned
        body = get(f"{BA}{path}?{urllib.parse.urlencode(q)}", timeout=15, headers=BA_KEY)
        if body:
            data = json.loads(body)
            break
    else:
        raise RuntimeError("The Bundesagentur job search is unreachable")
    jobs = []
    for j in data.get("stellenangebote") or []:
        refnr = j.get("refnr") or j.get("referenznummer") or ""
        place = j.get("arbeitsort") or (j.get("arbeitsorte") or [{}])[0] or {}
        if not refnr or not j.get("arbeitgeber"):
            continue
        jobs.append(
            {
                "source": "ba",
                "title": j.get("titel") or j.get("stellenangebotsTitel") or j.get("beruf") or "",
                "company": j["arbeitgeber"],
                "location": place.get("ort") or "",
                "refnr": refnr,
                "url": f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{urllib.parse.quote(refnr)}",
                "external_url": j.get("externeUrl") or "",
                "date": j.get("aktuelleVeroeffentlichungsdatum") or "",
            }
        )
    total = int(data.get("maxErgebnisse") or 0)
    return {"jobs": jobs, "total": total, "next_page": page + 1 if page * 50 < min(total, 5000) and jobs else None}


def ba_details(refnr, timeout=8):
    code = base64.b64encode(refnr.encode()).decode()
    for path in ("/pc/v4/jobdetails/", "/pc/v3/jobdetails/"):
        body = get(f"{BA}{path}{code}", timeout=timeout, headers=BA_KEY)
        if body:
            try:
                return json.loads(body)
            except ValueError:
                return None
    return None


def group_jobs(jobs):
    """One entry per company, with all of its jobs (used by the CLI; the UI does the same in JS)."""
    out = {}
    for j in jobs:
        key = re.sub(r"\W+", " ", j["company"].lower()).strip()
        c = out.setdefault(
            key,
            {
                "id": f"{j['source']}:{key}",
                "name": j["company"],
                "jobs": [],
                "kind": "company",
                "website": j.get("website") or "",
                "emails": [],
                "ba_refnr": "",
            },
        )
        c["jobs"].append(j)
        c["website"] = c["website"] or j.get("website") or ""
        c["emails"] = sorted(set(c["emails"]) | set(j.get("emails") or []))
        c["ba_refnr"] = c["ba_refnr"] or j.get("refnr") or ""
    return list(out.values())


# --------------------------------------------------------------------------------------------------- page parsing

HREF_RE = re.compile(r"""<a\b[^>]*?\bhref\s*=\s*["']([^"']+)["'][^>]*>(.*?)</a>""", re.I | re.S)
BLOCK_RE = re.compile(
    r"<\s*/?\s*(?:br|p|div|li|ul|ol|tr|td|th|h[1-6]|section|article|address|footer|header|dd|dt|table)\b[^>]*>", re.I
)
URL_RE = re.compile(r"""https?://[^\s<>"')\]]+|\bwww\.[a-z0-9-]+(?:\.[a-z0-9-]+)+""", re.I)
LINK_KINDS = (
    (
        "impressum",
        re.compile(r"impressum|imprint|legal[-_ ]?notice|site[-_ ]?notice|legal[-_ ]?info|anbieterkennzeichnung", re.I),
    ),
    (
        "careers",
        re.compile(
            r"karriere|career|\bjobs?\b|stellenangebote|offene[-_ ]stellen|join[-_ ]?us|arbeiten[-_ ]bei|work[-_ ]with[-_ ]us",
            re.I,
        ),
    ),
    ("contact", re.compile(r"kontakt|contact", re.I)),
)
IMPRESSUM_PATHS = ("/impressum", "/imprint", "/de/impressum", "/legal-notice", "/impressum.html")
IMPRESSUM_HINT = re.compile(
    r"angaben gem(ä|ae)(ß|ss)|§\s*5\s*(ddg|tmg)|handelsregister|registergericht|register court|vertretungsberechtigt"
    r"|vertreten durch|gesch(ä|ae)ftsf(ü|ue)hr|managing director|represented by|ust\.?-?id|umsatzsteuer|inhaber(in)?\s*:|vorstand\s*:",
    re.I,
)
PARKED = re.compile(
    r"domain (is )?for sale|diese domain (kaufen|steht zum verkauf)|sedoparking|parkingcrew|buy this domain|hugedomains", re.I
)
DEOBF_AT = re.compile(r"\s*[\[({<]\s*(?:at|ät|@)\s*[\])}>]\s*", re.I)
DEOBF_DOT = re.compile(r"\s*[\[({<]\s*(?:dot|punkt|\.)\s*[\])}>]\s*", re.I)


def html_text(body):
    body = re.sub(r"(?is)<(script|style|noscript|svg|template|head)\b.*?</\1\s*>", " ", body or "")
    body = re.sub(r"(?s)<!--.*?-->", " ", body)
    body = re.sub(r"<[^>]+>", " ", BLOCK_RE.sub("\n", body))
    lines = (re.sub(r"[ \t\r\f\v ​]+", " ", line).strip() for line in html.unescape(body).split("\n"))
    return "\n".join(line for line in lines if line)


def cf_decode(hexstr):
    """Cloudflare email protection: first byte is the XOR key."""
    try:
        key = int(hexstr[:2], 16)
        return "".join(chr(int(hexstr[i : i + 2], 16) ^ key) for i in range(2, len(hexstr), 2))
    except ValueError:
        return ""


def emails_in(text):
    """All plausible emails in an HTML or text blob, including obfuscated and Cloudflare-protected ones."""
    protected = re.findall(r'data-cfemail="([0-9a-fA-F]+)"|email-protection#([0-9a-fA-F]+)', text or "")
    found = {cf_decode(h) for pair in protected for h in pair if h}
    plain = DEOBF_DOT.sub(".", DEOBF_AT.sub("@", urllib.parse.unquote(html.unescape(text or ""))))
    found.update(EMAIL_RE.findall(plain))
    return {e.lower().strip(".") for e in found if EMAIL_FULL.match(e.strip(".")) and not BAD_EMAIL.search(e)}


def website_hint(body):
    """First link in a job ad that looks like the employer's own site, not a job board or social network."""
    for u in URL_RE.findall(html.unescape(body or "")):
        host = domain_of(u)
        if re.search(r"\.(png|jpe?g|gif|svg|webp|pdf)$", u, re.I) or re.match(r"(cdn|static|assets|img|images|media)\.", host):
            continue
        if host and "." in host and not JOB_SITES.search(host):
            return f"https://{host}"
    return ""


def domain_of(website):
    host = urllib.parse.urlsplit(website if "//" in (website or "") else f"https://{website}").hostname or ""
    return host.lower().removeprefix("www.")


def normalize_url(s):
    """Site root (scheme://host) or ''. We only ever fetch a site's root plus our own fixed paths."""
    s = (s or "").strip()
    if not s:
        return ""
    p = urllib.parse.urlsplit(s if "//" in s else f"https://{s}")
    host = (p.hostname or "").lower()
    if p.scheme not in ("http", "https") or "." not in host or len(host) > 253:
        return ""
    return f"{p.scheme}://{host}"


def same_site(host, domain):
    host = host.lower().removeprefix("www.")
    return host == domain or host.endswith("." + domain) or domain.endswith("." + host)


def find_links(body, base, domain):
    out = {}
    for href, label in HREF_RE.findall(body or ""):
        href = html.unescape(href).strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        u = urllib.parse.urljoin(base, href).split("#")[0]
        if not same_site(urllib.parse.urlsplit(u).hostname or "", domain):
            continue
        hay = f"{href} {re.sub(r'<[^>]+>', ' ', label)}"
        for kind, rx in LINK_KINDS:
            if kind not in out and rx.search(hay):
                out[kind] = u
                break
    return out


# --------------------------------------------------------------------------------------------------- names

UMLAUT = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "ae", "Ö": "oe", "Ü": "ue"})
PARTICLES = {
    "von",
    "van",
    "de",
    "der",
    "den",
    "zu",
    "zur",
    "vom",
    "zum",
    "di",
    "da",
    "del",
    "della",
    "la",
    "le",
    "ten",
    "ter",
    "op",
}
TITLES = {
    "dr",
    "prof",
    "dipl",
    "ing",
    "mag",
    "mba",
    "emba",
    "msc",
    "bsc",
    "llm",
    "phd",
    "med",
    "rer",
    "nat",
    "pol",
    "oec",
    "jur",
    "hc",
    "kfm",
    "kffr",
    "habil",
    "dent",
    "vwl",
    "bwl",
    "ceo",
    "cto",
    "coo",
    "cfo",
    "ek",
    "ev",
}
STOPWORDS = set(
    """
gmbh mbh ggmbh ag se ug kg kgaa ohg gbr co ltd limited inc llc corp holding verwaltungs verwaltung gesellschaft group gruppe
haftungsbeschränkt haftungsbeschraenkt registergericht amtsgericht handelsregister register registernummer sitz telefon tel
fax email e-mail mail kontakt anschrift adresse impressum imprint straße strasse str platz weg allee deutschland germany
berlin münchen muenchen hamburg köln koeln frankfurt stuttgart düsseldorf duesseldorf leipzig dresden hannover nürnberg
bremen essen dortmund bonn mannheim karlsruhe augsburg wien zürich zuerich geschäftsführer geschäftsführerin geschäftsführung
geschaeftsfuehrer vorstand vorstandsvorsitzender vorsitzender vorsitzende inhaber inhaberin founder founders gründer
gründerin managing director directors partner partners team the und and der die das des den dem für for of with ust
umsatzsteuer steuernummer hrb hra datenschutz verantwortlich verantwortlicher haftung information informationen angaben gemäß
nach tmg ddg mstv rstv website webseite online service services solutions software digital technologies technology consulting
media studio labs ventures capital unternehmen firma company copyright rights reserved alle rechte vertreten durch represented
aufsichtsrat chairman board
""".split()
)
REP_LABEL = re.compile(
    r"(gesch(?:ä|ae)ftsf(?:ü|ue)hr\w*|vertreten\s+durch|vertretungsberechtigt\w*|vorstand\w*|inhaber\w*"
    r"|managing\s+directors?|managing\s+partners?|represented\s+by|authori[sz]ed\s+representatives?|\bceo\b"
    r"|\bco-?founders?\b|\bfounders?\b|\bgr(?:ü|ue)nder(?:in|innen)?\b)",
    re.I,
)
RESPONSIBLE_LABEL = re.compile(
    r"verantwortlich\w*\s+(?:f(?:ü|ue)r\s+den\s+inhalt|i\.?\s?s\.?\s?d\.?)|inhaltlich\s+verantwortlich", re.I
)
LEAD_WORDS = re.compile(
    r"^\s*(?:[:\-–]\s*)?(?:(?:die|den|der|des|durch|the|its|our|seine|ihre|unsere)\s+)*"
    r"(?:(?:gesch(?:ä|ae)ftsf(?:ü|ue)hr\w*|gesellschafter\w*|managing\s+directors?|vorstand\w*|vorstände|directors?)\s*:?\s+)*",
    re.I,
)
STOP_SEGMENT = re.compile(
    r"\b(aufsichtsrat\w*|registergericht|amtsgericht|handelsregister|registernummer|sitz der|sitz:|ust|umsatzsteuer|steuer\w*"
    r"|telefon|tel\.|fax|e-?mail|kontakt|anschrift|adresse|verantwortlich\w*|vorsitz\w*|hrb|hra|www\.|http)",
    re.I,
)
NAME_TOKEN = re.compile(r"^[^\W\d_](?:[^\W\d_]|['’])*(?:-[^\W\d_](?:[^\W\d_]|['’])*)*$")
CONTACT_RE = re.compile(
    r"(?:ansprechpartner(?:in)?|ansprechperson|kontaktperson|ihre?\s+kontakt|contact\s+person|your\s+contact)\s*"
    r"(?:ist|is|:|-|–)?\s*((?:herrn?|frau|mr\.?|ms\.?|mrs\.?)?\s*(?:(?:dr|prof)\.\s*)*[^\W\d_][^\n,;:()]{2,60})",
    re.I,
)


def slug(s, umlaut=True):
    s = (s or "").lower()
    s = s.translate(UMLAUT) if umlaut else s.replace("ß", "ss")
    return re.sub(r"[^a-z-]", "", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()).strip("-")


def clean_name(part):
    """'Herrn Dr. Max Mustermann' -> {name, first, last, gender, title}, or None if it isn't a person's name."""
    gender, titles, tokens = "", [], []
    for raw in part.split():
        t = raw.strip(".,:;–-")
        low = t.lower().replace(".", "").replace("-", "")
        if not t:
            continue
        if low in ("herr", "herrn", "mr", "sir"):
            gender = "m"
        elif low in ("frau", "mrs", "ms", "miss"):
            gender = "f"
        elif low.startswith(("dr", "prof")) and ("." in raw or low in ("dr", "prof")) and len(low) <= 8:
            titles.append("Prof." if low.startswith("prof") else "Dr.")
        elif low in TITLES or low.startswith("dipl") or (raw.count(".") >= 2 and len(low) <= 4 and low.isalpha()):
            continue  # Dipl.-Ing., MBA, M.A., B.Sc., e.K.
        else:
            tokens.append(t.title() if t.isupper() and len(t) > 2 else t)
    if not 2 <= len(tokens) <= 5:
        return None
    for i, t in enumerate(tokens):
        if t.lower() in PARTICLES and 0 < i < len(tokens) - 1:
            continue
        if not NAME_TOKEN.match(t) or not t[0].isupper() or t.lower() in STOPWORDS:
            return None
    last_at = next((i for i in range(1, len(tokens)) if tokens[i].lower() in PARTICLES), len(tokens) - 1)
    return {
        "name": " ".join(tokens),
        "first": tokens[0],
        "last": " ".join(tokens[last_at:]),
        "gender": gender,
        "title": " ".join(dict.fromkeys(titles)),
    }


def parse_names(s):
    s = re.sub(r"\([^)]*\)", " ", s)
    m = STOP_SEGMENT.search(s)
    s = s[: m.start()] if m else s
    parts = re.split(r"\s*(?:,|;|\||/|&|\+|\bund\b|\band\b|\bsowie\b)\s*", s)
    return [p for p in map(clean_name, parts) if p]


def representatives(text):
    """Managing directors / board / owners named in an Impressum, with their role."""
    people, seen, lines = [], set(), text.split("\n")
    for label_re, role_of in ((REP_LABEL, None), (RESPONSIBLE_LABEL, "Verantwortlich (Inhalt)")):
        for i, line in enumerate(lines):
            for m in label_re.finditer(line):  # "Vertreten durch: X GmbH, diese vertreten durch Max Müller"
                role = role_of or _role(m.group(1), line)
                rest = line[m.end() :]
                if ":" in rest[:80]:  # "Geschäftsführer der X Verwaltungs GmbH: Jakob Hofer"
                    rest = rest.split(":", 1)[1]
                found = parse_names(LEAD_WORDS.sub("", rest))
                if not found and not LEAD_WORDS.sub("", rest).strip(" :.-–"):  # label on its own line, names below
                    for nxt in lines[i + 1 : i + 5]:
                        names = parse_names(LEAD_WORDS.sub("", nxt))
                        if not names or ":" in nxt:
                            break
                        found += names
                for p in found:
                    key = slug(p["first"]) + "|" + slug(p["last"])
                    if key in seen:
                        continue
                    seen.add(key)
                    if role.endswith("in") and len(found) == 1 and not p["gender"]:
                        p["gender"] = "f"  # Geschäftsführerin, Inhaberin
                    female = p["gender"] == "f" and role in ("Geschäftsführer", "Inhaber")
                    people.append({**p, "role": role + "in" if female else role, "source": "impressum"})
        if people:
            break  # only fall back to "Verantwortlich für den Inhalt" when nobody else is named
    return people


def _role(label, line):
    low = label.lower()
    if "managing director" in low or "represented" in low or "authori" in low:
        return "Managing Director"
    if low.startswith("gesch"):
        return "Geschäftsführerin" if re.search(r"gesch(ä|ae)ftsf(ü|ue)hrerin\b", line, re.I) else "Geschäftsführer"
    if low.startswith("vorstand"):
        return "Vorstand"
    if low.startswith("inhaber"):
        return "Inhaberin" if low.startswith("inhaberin") else "Inhaber"
    if "found" in low or low.startswith("gr"):
        return "Founder"
    if low == "ceo":
        return "CEO"
    return "Geschäftsführer" if "vertret" in low else label.strip().title()


def job_ad_contacts(text):
    out = []
    for m in CONTACT_RE.finditer(text or ""):
        for p in parse_names(m.group(1)):
            out.append({**p, "role": "Ansprechpartner (job ad)", "source": "job ad"})
    return out


def impressum_facts(text):
    legal = re.search(
        r"([A-ZÄÖÜ0-9][\w&.,'’+ -]{1,80}?\s(?:GmbH\s*&\s*Co\.\s*KG(?:aA)?|gGmbH|GmbH|AG|SE|"
        r"UG\s*\(haftungsbeschränkt\)|UG|KGaA|KG|OHG|GbR|e\.\s?K\.|PartG(?:\s*mbB)?))(?!\w)",
        text,
    )
    register = re.search(r"\b(HR[AB])\s*[-:.]?\s*(?:Nr\.?\s*)?(\d{2,7}(?:\s?[A-Z]{1,2}\b)?)", text)
    city = ""
    for m in re.finditer(
        r"(?<![\d-])(?:D-)?(\d{5})\s+([A-ZÄÖÜ][\wäöüß.-]+(?:\s(?:am|an|im|bei|ob)\s[A-ZÄÖÜ][\wäöüß.-]+)?)", text
    ):
        if (
            m.group(2).lower() not in ("amtsgericht", "registergericht", "hrb", "hra")
            and "HR" not in text[max(0, m.start() - 6) : m.start()]
        ):
            city = m.group(2)
            break
    legal = re.split(r"\b(?:der|des|die)\s+|:\s*", legal.group(1))[-1].strip() if legal else ""  # "Gesellschafterin der X GmbH"
    return {"legal_name": legal, "register": f"{register.group(1)} {register.group(2).strip()}" if register else "", "city": city}


# --------------------------------------------------------------------------------------------------- emails

PATTERNS = {
    "first": "{f}",
    "first.last": "{f}.{l}",
    "f.last": "{i}.{l}",
    "flast": "{i}{l}",
    "firstlast": "{f}{l}",
    "last": "{l}",
    "first_last": "{f}_{l}",
    "first-last": "{f}-{l}",
    "last.first": "{l}.{f}",
    "firstl": "{f}{j}",
}
STARTUP_ORDER = ["first", "first.last", "f.last", "flast", "firstlast", "last"]
COMPANY_ORDER = ["first.last", "first", "f.last", "flast", "firstlast", "last"]  # vorname.nachname leads in DACH
NOISE_LOCAL = re.compile(
    r"^(datenschutz|privacy|dsb|dpo|gdpr|dsgvo|no-?reply|do-?not-?reply|abuse|postmaster|hostmaster|webmaster|newsletter"
    r"|unsubscribe|bounces?|billing|rechnung(en)?|invoices?|buchhaltung|accounting|security|ssl|dmca|legal|recht"
    r"|compliance|whistleblow\w*|hinweisgeber\w*|cookies?|test)$"
)
JOBS_LOCAL = re.compile(
    r"^(jobs?|karriere|careers?|bewerbung(en)?|bewerber|recruiting|recruitment|recruiter|talents?|hr|personal|people"
    r"|hiring|joinus|join|apply|applications?|ausbildung|stellen|work)([._-][a-z0-9]+)?$"
)
MGMT_LOCAL = re.compile(r"^(ceo|cto|coo|founders?|gf|geschaeftsfuehrung|gl|management|vorstand|leadership|board)$")
GENERIC_LOCAL = re.compile(
    r"^(info|infos|kontakt|contact|hello|hallo|hi|hey|moin|servus|office|buero|mail|post|team|support|service|help|hilfe"
    r"|sales|vertrieb|presse|press|media|marketing|business|anfragen?|zentrale|empfang|verwaltung|feedback|partners?|welcome"
    r"|kunden\w*|orders?|bestellung(en)?|shop|events?|community|general|enquiries|inquiries|ask|questions)([._-][a-z0-9]+)?$"
)


def classify(local):
    for kind, rx in (("noise", NOISE_LOCAL), ("jobs", JOBS_LOCAL), ("mgmt", MGMT_LOCAL), ("generic", GENERIC_LOCAL)):
        if rx.match(local):
            return kind
    return "personal"


def build_local(pattern, first, last):
    f, lst = first, last.replace(" ", "")
    if not f or (not lst and pattern != "first"):
        return ""
    return PATTERNS[pattern].format(f=f, l=lst, i=f[0], j=lst[:1])


def name_variants(person):
    """(first, last) slugs: Müller -> mueller first, then muller (some mail admins just drop the dots)."""
    return list(dict.fromkeys((slug(person["first"], u), slug(person["last"], u)) for u in (True, False)))


def matches(person, local):
    for f, lst in name_variants(person):
        if any(build_local(p, f, lst) == local for p in PATTERNS) or (len(lst) >= 4 and lst.replace("-", "") in local):
            return True
    return False


def infer_pattern(personal_emails, people):
    """The domain's naming scheme, learned from a real address: matched to a known person, else by its shape."""
    for e in personal_emails:
        local = e.split("@")[0]
        for person in people:
            for f, lst in name_variants(person):
                for p in PATTERNS:
                    if build_local(p, f, lst) == local:
                        return p, e
    for e in personal_emails:
        local = e.split("@")[0]
        if re.fullmatch(r"[a-z]{2,}\.[a-z]{2,}(-[a-z]+)?", local):
            return "first.last", e
        if re.fullmatch(r"[a-z]\.[a-z]{2,}", local):
            return "f.last", e
    return "", ""


def guesses(person, domain, order):
    out = []
    for f, lst in name_variants(person):
        for p in order:
            local = build_local(p, f, lst)
            if local:
                out.append(f"{local}@{domain}")
    return list(dict.fromkeys(out))[:8]


def related(email_domain, site_domain, name=""):
    """Is this email domain the company's? firma.com and firma-gmbh.de count as related."""
    if same_site(email_domain, site_domain):
        return True
    mine = {t for t in re.split(r"[-.]", email_domain.rsplit(".", 1)[0]) if len(t) >= 4}
    theirs = set(re.split(r"[-.]", site_domain.rsplit(".", 1)[0])) | {slug(w) for w in re.split(r"\W+", name)}
    return bool(mine & theirs)


def mx_lookup(domain, timeout=4):
    """(has_mx, provider) via DNS-over-HTTPS; (None, '') if it couldn't be checked."""
    for url in (
        f"https://cloudflare-dns.com/dns-query?name={domain}&type=MX",
        f"https://dns.google/resolve?name={domain}&type=MX",
    ):
        body = get(url, timeout=timeout, headers={"Accept": "application/dns-json"})
        if not body:
            continue
        try:
            data = json.loads(body)
        except ValueError:
            continue
        hosts = " ".join(a.get("data", "") for a in data.get("Answer") or [] if a.get("type") == 15).lower()
        if data.get("Status") == 3 or not hosts:  # NXDOMAIN or no MX
            return False, ""
        for needle, name in (
            ("google", "Google Workspace"),
            ("outlook", "Microsoft 365"),
            ("kundenserver", "IONOS"),
            ("ionos", "IONOS"),
            ("strato", "Strato"),
            ("your-server.de", "Hetzner"),
            ("hetzner", "Hetzner"),
            ("zoho", "Zoho"),
            ("mailbox.org", "mailbox.org"),
            ("protonmail", "Proton"),
            ("all-inkl", "ALL-INKL"),
            ("mimecast", "Mimecast"),
            ("pphosted", "Proofpoint"),
        ):
            if needle in hosts:
                return True, name
        return True, ""
    return None, ""


# --------------------------------------------------------------------------------------------------- website guessing

LEGAL_SUFFIX = re.compile(
    r"(?i)\b(gmbh\s*&\s*co\.?\s*kg(aa)?|ggmbh|gmbh|mbh|ag|se|ug(\s*\(haftungsbeschränkt\))?|kgaa|kg|ohg|gbr|e\.\s?k\.?|e\.\s?v\.?"
    r"|inc|ltd|llc|corp|co|limited|holding|group|gruppe|deutschland|germany)\b\.?"
)


def domain_candidates(name):
    base = re.sub(r"\([^)]*\)", " ", LEGAL_SUFFIX.sub(" ", name or ""))
    stems = []
    for umlaut in (True, False):  # müller -> mueller.de first, then muller.de
        words = [w for w in (slug(w, umlaut) for w in re.split(r"[\s/,+&.|]+", base)) if w]
        if words:
            stems += ["".join(words), "-".join(words)] + ([words[0]] if len(words) > 1 and len(words[0]) >= 4 else [])
    stems = list(dict.fromkeys(stems))
    if not stems:
        return []
    return list(
        dict.fromkeys(
            [f"{s}.{t}" for t in ("de", "com") for s in stems] + [f"{stems[0]}.{t}" for t in ("io", "ai", "eu", "tech")]
        )
    )


def mentions(body, name):
    head = (re.search(r"(?is)<title[^>]*>(.*?)</title>", body) or [None, ""])[1] + " " + html_text(body)[:6000]
    words = [slug(w) for w in re.split(r"\W+", LEGAL_SUFFIX.sub(" ", name)) if len(slug(w)) >= 3]
    words = [w for w in words if w not in ("und", "and", "the", "der", "die", "das", "fuer", "for", "von")][:3]
    hay = slug(head.replace(" ", ""))
    return bool(words) and all(w.replace("-", "") in hay for w in words) and not PARKED.search(body)


def guess_website(name, left):
    def check(d):
        body, final = fetch(f"https://{d}", timeout=min(5, left()), checked=True)
        return normalize_url(final) if body and mentions(body, name) else None

    cands = domain_candidates(name)[:10]
    if not cands or left() < 3:
        return ""
    with cf.ThreadPoolExecutor(len(cands)) as ex:
        return next((r for r in ex.map(check, cands) if r), "")


# --------------------------------------------------------------------------------------------------- enrichment


def enrich_one(item):
    try:
        return _enrich(item)
    except Exception as e:  # one bad site must not fail the batch
        return {"id": item.get("id"), "name": item.get("name") or "", "error": f"Lookup failed: {type(e).__name__}"}


def _enrich(item):
    deadline = time.monotonic() + ENRICH_DEADLINE

    def left():
        return deadline - time.monotonic()

    name = item.get("name") or ""
    out = {
        "id": item.get("id"),
        "name": name,
        "website": "",
        "website_guessed": False,
        "domain": "",
        "mail_domain": "",
        "mx": None,
        "mx_provider": "",
        "impressum_url": "",
        "careers_url": "",
        "legal_name": "",
        "register": "",
        "city": "",
        "one_liner": "",
        "linkedin": "",
        "pattern": "",
        "pattern_from": "",
        "people": [],
        "inboxes": [],
        "notes": [],
    }
    people, found = [], {}  # found: email -> where we saw it ("site" | "jobad")
    website = normalize_url(item.get("website"))

    if item.get("yc_slug"):
        yc = yc_company(item["yc_slug"], timeout=min(8, left()))
        if yc:
            website = website or normalize_url(yc.get("website"))
            out["one_liner"], out["linkedin"] = yc.get("one_liner") or "", yc.get("linkedin_url") or ""
            for f in yc.get("founders") or []:
                p = clean_name(f.get("full_name") or "") or _loose_name(f.get("full_name") or "")
                if p:
                    people.append(
                        {
                            **p,
                            "role": f.get("title") or "Founder",
                            "source": "yc",
                            "linkedin": f.get("linkedin_url") or "",
                            "twitter": f.get("twitter_url") or "",
                        }
                    )
        else:
            out["notes"].append("Couldn't load the YC page")

    if item.get("ba_refnr") and left() > 2:
        d = ba_details(item["ba_refnr"], timeout=min(8, left()))
        if d:
            desc = d.get("stellenangebotsBeschreibung") or d.get("stellenbeschreibung") or ""
            text = html_text(desc)
            website = website or normalize_url(d.get("arbeitgeberdarstellungUrl")) or website_hint(desc)
            people += job_ad_contacts(text)
            found.update(dict.fromkeys(emails_in(desc), "jobad"))
            out["industry"] = d.get("branche") or ""

    for e in item.get("emails") or []:
        found.setdefault(e.lower(), "jobad")

    if not website and name and left() > 3:
        website = guess_website(name, left)
        out["website_guessed"] = bool(website)
    if not website:
        out["notes"].append("No website found. Add it on the card and check again.")
        return _finish(out, people, found, "", item, left)

    home, final = fetch(website, timeout=min(6, left()), checked=True)
    if final:
        website = normalize_url(final) or website
    domain = domain_of(website)
    out["website"], out["domain"] = website, domain
    if not home:
        out["notes"].append("The website didn't load")
    links = find_links(home, final or website, domain)
    if home:
        found.update({e: "site" for e in emails_in(home) if e not in found})

    imp_text = ""
    for u in list(dict.fromkeys(([links["impressum"]] if "impressum" in links else []) + [website + p for p in IMPRESSUM_PATHS]))[
        :5
    ]:
        if left() < 2:
            break
        body, final_u = fetch(u, timeout=min(5, left()), checked=True)
        if body and IMPRESSUM_HINT.search(html_text(body)):
            imp_text, out["impressum_url"] = html_text(body), final_u
            found.update({e: "site" for e in emails_in(body) if e not in found})
            break
    if not imp_text and home and IMPRESSUM_HINT.search(html_text(home)):
        imp_text = html_text(home)  # one-page sites put the Impressum on the homepage
    if imp_text:
        people += representatives(imp_text)
        out.update(impressum_facts(imp_text))
    else:
        out["notes"].append("No Impressum found")

    for kind in ("careers", "contact"):
        if kind in links and left() > 2:
            body, final_k = fetch(links[kind], timeout=min(5, left()), checked=True)
            if body:
                out["careers_url"] = final_k if kind == "careers" else out["careers_url"]
                found.update({e: "site" for e in emails_in(body) if e not in found})
    return _finish(out, people, found, domain, item, left)


def _loose_name(full):
    """YC founder names are already names; accept them even when clean_name's Impressum rules are too strict."""
    parts = [p for p in re.split(r"\s+", full.strip()) if p]
    return (
        {"name": " ".join(parts), "first": parts[0], "last": parts[-1] if len(parts) > 1 else "", "gender": "", "title": ""}
        if parts
        else None
    )


def _finish(out, people, found, domain, item, left):
    # Sort emails: keep the company's own (or a free-mail owner's), drop noise like datenschutz@
    by_kind = collections.defaultdict(list)
    for e, where in found.items():
        local, dom = e.split("@", 1)
        own = domain and related(dom, domain, out["name"])
        if where != "jobad" and not own and dom not in FREEMAIL:
            continue
        kind = classify(local)
        if kind != "noise":
            by_kind[kind].append((e, where, own))
    doms = collections.Counter(e.split("@")[1] for kind in by_kind for e, _, own in by_kind[kind] if own)
    mail_domain = domain if (not doms or domain in doms) else doms.most_common(1)[0][0]
    out["mail_domain"] = mail_domain

    merged = {}
    for p in people:
        key = slug(p["first"]) + "|" + slug(p["last"])
        if key in merged:
            m = merged[key]
            for k in ("gender", "title", "linkedin", "twitter"):
                m[k] = m.get(k) or p.get(k) or ""
            if p["source"] == "impressum" and m["source"] == "yc":
                m["role"] = f"{m['role']} · {p['role']}"
        else:
            merged[key] = {"linkedin": "", "twitter": "", **p}
    people = list(merged.values())

    personal = [e for e, _, own in by_kind["personal"] if own and e.endswith("@" + mail_domain)]
    pattern, pattern_from = infer_pattern(personal, people)
    out["pattern"], out["pattern_from"] = pattern, pattern_from
    if mail_domain and left() > 1:
        out["mx"], out["mx_provider"] = mx_lookup(mail_domain, timeout=min(4, left()))
        if out["mx"] is False:
            out["notes"].append(f"{mail_domain} has no mail server (MX), so guesses would bounce")
    base = STARTUP_ORDER if item.get("kind") == "startup" or item.get("yc_slug") else COMPANY_ORDER
    order = ([pattern] if pattern else []) + [p for p in base if p != pattern]

    used = set()
    for p in people:
        emails = []
        for e, where, _ in by_kind["personal"]:
            if matches(p, e.split("@")[0]):
                emails.append({"email": e, "label": "jobad" if where == "jobad" else "site"})
                used.add(e)
        if mail_domain and out["mx"] is not False:
            for i, g in enumerate(guesses(p, mail_domain, order)):
                if g not in used and all(g != x["email"] for x in emails):
                    emails.append({"email": g, "label": "pattern" if pattern and i == 0 else "guess"})
        p["emails"] = emails
    out["people"] = people
    for kind, label in (("jobs", "jobs"), ("mgmt", "mgmt"), ("personal", "other"), ("generic", "generic")):
        out["inboxes"] += [{"email": e, "label": label} for e, _, _ in sorted(by_kind[kind]) if e not in used]
    return out


# --------------------------------------------------------------------------------------------------- HTTP


def _one(q, k, default=""):
    return (q.get(k) or [default])[0].strip()


def _int(q, k, default, allowed):
    try:
        v = int(_one(q, k, str(default)))
    except ValueError:
        v = default
    return v if v in allowed else default


def route_get(query):
    q = urllib.parse.parse_qs(query)
    action = _one(q, "action")
    if action == "yc_companies":
        region = _one(q, "region", "Germany")
        if region not in REGIONS:
            return 400, {"error": "Invalid region"}, 0
        return 200, yc_companies(region), 3600
    if action == "arbeitnow":
        text = _one(q, "q")
        if len(text) > 100:
            return 400, {"error": "Search text too long"}, 0
        return 200, arbeitnow(text, _one(q, "visa") == "1", _one(q, "remote") == "1", _int(q, "page", 1, range(1, 201))), 900
    if action == "ba_jobs":
        was, wo = _one(q, "was"), _one(q, "wo")
        if len(was) > 100 or len(wo) > 80:
            return 400, {"error": "Search text too long"}, 0
        if not was and not wo:
            return 400, {"error": "Enter a job title or a place"}, 0
        return (
            200,
            ba_jobs(
                was,
                wo,
                _int(q, "umkreis", 25, (0, 10, 15, 20, 25, 50, 100, 200)),
                _int(q, "angebotsart", 1, (1, 4, 34)),
                _int(q, "days", 30, range(0, 101)),
                _int(q, "page", 1, range(1, 101)),
            ),
            900,
        )
    return 400, {"error": "Unknown action"}, 0


def _valid_item(c):
    if not isinstance(c, dict):
        return None
    s = {k: c.get(k) if isinstance(c.get(k), str) else "" for k in ("id", "name", "website", "yc_slug", "ba_refnr", "kind")}
    if len(s["id"]) > 120 or len(s["name"]) > 200 or len(s["website"]) > 300:
        return None
    if (s["yc_slug"] and not SLUG_RE.match(s["yc_slug"])) or (s["ba_refnr"] and not REFNR_RE.match(s["ba_refnr"])):
        return None
    if not (s["name"] or s["website"] or s["yc_slug"]):
        return None
    emails = c.get("emails") if isinstance(c.get("emails"), list) else []
    s["emails"] = [e for e in emails[:10] if isinstance(e, str) and EMAIL_FULL.match(e)]
    return s


def route_post(raw):
    try:
        req = json.loads(raw or b"{}")
    except ValueError:
        return 400, {"error": "Invalid JSON"}, 0
    if not isinstance(req, dict) or req.get("action") != "enrich":
        return 400, {"error": "Unknown action"}, 0
    items = req.get("companies")
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_COMPANIES:
        return 400, {"error": f"Send 1-{MAX_COMPANIES} companies"}, 0
    items = [_valid_item(c) for c in items]
    if not all(items):
        return 400, {"error": "Each company needs a name, website or YC slug (valid values only)"}, 0
    with cf.ThreadPoolExecutor(len(items)) as ex:
        return 200, list(ex.map(enrich_one, items)), 0


def respond(h, status, body, cache=0):
    data = json.dumps(body, ensure_ascii=False).encode()
    h.send_response(status)
    h.send_header("Content-Type", "application/json; charset=utf-8")
    h.send_header("Content-Length", str(len(data)))
    if cache:
        h.send_header("Cache-Control", f"public, s-maxage={cache}, stale-while-revalidate=86400")
    h.end_headers()
    h.wfile.write(data)


def _call(fn, arg):
    try:
        return fn(arg)
    except Exception as e:
        return 502, {"error": str(e) or "Upstream error"}, 0


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        respond(self, *_call(route_get, urllib.parse.urlparse(self.path).query))

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        if not 0 <= n <= MAX_BODY:
            return respond(self, 413, {"error": "Request too large"})
        respond(self, *_call(route_post, self.rfile.read(n)))
