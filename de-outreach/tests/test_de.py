"""Offline tests: python3 -m unittest discover -s tests  (no network; every fetch is faked)."""

import functools
import json
import os
import socket
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "api"))
sys.path.insert(0, ROOT)
import de  # noqa: E402

import serve  # noqa: E402


def cf_encode(email, key=0x2A):
    return f"{key:02x}" + "".join(f"{ord(c) ^ key:02x}" for c in email)


def names(people):
    return [(p["name"], p["gender"], p["title"], p["role"]) for p in people]


class Impressum(unittest.TestCase):
    def reps(self, html):
        return de.representatives(de.html_text(html))

    def test_gmbh_with_titles_umlauts_and_hyphens(self):
        html = """<h1>Impressum</h1><p>Angaben gemäß § 5 DDG</p><p>Flowbase GmbH<br>Torstraße 12<br>10119 Berlin</p>
        <p>Geschäftsführer: Dr. Jürgen Müller-Lüdenscheidt, Anna-Lena Schröder</p>
        <p>Registergericht: Amtsgericht Charlottenburg<br>HRB 123456 B</p>"""
        self.assertEqual(
            names(self.reps(html)),
            [("Jürgen Müller-Lüdenscheidt", "", "Dr.", "Geschäftsführer"), ("Anna-Lena Schröder", "", "", "Geschäftsführer")],
        )
        facts = de.impressum_facts(de.html_text(html))
        self.assertEqual(facts, {"legal_name": "Flowbase GmbH", "register": "HRB 123456 B", "city": "Berlin"})

    def test_vertreten_durch_herrn_gives_gender(self):
        people = self.reps("<p>Vertreten durch den Geschäftsführer Herrn Jakob Hofer<br>Musterstr. 20<br>94032 Passau</p>")
        self.assertEqual(names(people), [("Jakob Hofer", "m", "", "Geschäftsführer")])
        self.assertEqual((people[0]["first"], people[0]["last"]), ("Jakob", "Hofer"))

    def test_gmbh_co_kg_names_the_komplementaer_md(self):
        html = """<p>Persönlich haftende Gesellschafterin der Hofer GmbH &amp; Co. KG: Hofer Verwaltungs GmbH<br>
        Geschäftsführer der Hofer Verwaltungs GmbH: Jakob Hofer</p>"""
        self.assertEqual(names(self.reps(html)), [("Jakob Hofer", "", "", "Geschäftsführer")])
        self.assertEqual(de.impressum_facts(de.html_text(html))["legal_name"], "Hofer GmbH & Co. KG")

    def test_names_on_following_lines_and_english_labels(self):
        html = """<div>Represented by the Managing Directors:</div><div>Jane Doe</div><div>Ömer Yılmaz</div>
        <div>Register court: Munich, HRB 98765</div>"""
        self.assertEqual(
            names(self.reps(html)), [("Jane Doe", "", "", "Managing Director"), ("Ömer Yılmaz", "", "", "Managing Director")]
        )

    def test_nested_representation_and_particles(self):
        people = self.reps(
            "<p>Vertreten durch: Muster Holding GmbH, diese vertreten durch Frau Prof. Dr. Sabine von der Heide</p>"
        )
        self.assertEqual(names(people), [("Sabine von der Heide", "f", "Prof. Dr.", "Geschäftsführerin")])
        self.assertEqual(people[0]["last"], "von der Heide")

    def test_board_stops_before_supervisory_board(self):
        people = self.reps("<p>Vorstand: Max Weber (Vorsitzender), Petra Klein; Vorsitzender des Aufsichtsrats: Hans Groß</p>")
        self.assertEqual([p["name"] for p in people], ["Max Weber", "Petra Klein"])

    def test_female_role_and_responsible_person_fallback(self):
        self.assertEqual(
            names(self.reps("<p>Geschäftsführerin: Maria Schulz</p><p>Inhaltlich verantwortlich: Tom Becker</p>")),
            [("Maria Schulz", "f", "", "Geschäftsführerin")],
        )
        self.assertEqual(
            names(self.reps("<p>Verantwortlich für den Inhalt nach § 18 Abs. 2 MStV: Tom Becker</p>")),
            [("Tom Becker", "", "", "Verantwortlich (Inhalt)")],
        )

    def test_rejects_non_names(self):
        for bad in ("Muster GmbH", "Amtsgericht Berlin", "Telefon 030 123", "the team", "Max", "Berlin Mitte"):
            self.assertIsNone(de.clean_name(bad), bad)
        self.assertEqual(de.clean_name("Jack Ma")["last"], "Ma")  # Ma is a surname, not "M.A."
        self.assertEqual(de.clean_name("Jakob Hofer e.K.")["name"], "Jakob Hofer")
        self.assertEqual(de.clean_name("MAX WEBER")["name"], "Max Weber")


class Emails(unittest.TestCase):
    def test_obfuscated_and_cloudflare_emails(self):
        html = (
            f'<p>E-Mail: kontakt [at] flowbase (punkt) de</p><a data-cfemail="{cf_encode("info@flowbase.de")}">x</a>'
            "<p>max.mustermann@firma.de logo@2x.png you@example.com jobs&#64;flowbase.de</p>"
        )
        self.assertEqual(de.emails_in(html), {"kontakt@flowbase.de", "info@flowbase.de", "jobs@flowbase.de"})

    def test_classify(self):
        cases = {
            "bewerbung": "jobs",
            "jobs.berlin": "jobs",
            "karriere": "jobs",
            "info": "generic",
            "kontakt": "generic",
            "datenschutz": "noise",
            "noreply": "noise",
            "gf": "mgmt",
            "anna": "personal",
            "a.schroeder": "personal",
        }
        self.assertEqual({k: de.classify(k) for k in cases}, cases)

    def test_umlaut_guesses_company_order(self):
        p = de.clean_name("Dr. Jürgen Müller")
        self.assertEqual(
            de.guesses(p, "firma.de", de.COMPANY_ORDER)[:7],
            [
                "juergen.mueller@firma.de",
                "juergen@firma.de",
                "j.mueller@firma.de",
                "jmueller@firma.de",
                "juergenmueller@firma.de",
                "mueller@firma.de",
                "jurgen.muller@firma.de",
            ],
        )

    def test_startup_order_and_particles_and_eszett(self):
        self.assertEqual(
            de.guesses(de.clean_name("Sabine von der Heide"), "x.io", de.STARTUP_ORDER)[:2],
            ["sabine@x.io", "sabine.vonderheide@x.io"],
        )
        self.assertEqual(de.guesses(de.clean_name("Hans Groß"), "x.de", ["first.last"]), ["hans.gross@x.de"])

    def test_infer_pattern(self):
        people = [de.clean_name("Anna Schröder"), de.clean_name("Jürgen Müller")]
        self.assertEqual(de.infer_pattern(["a.schroeder@x.de"], people), ("f.last", "a.schroeder@x.de"))
        self.assertEqual(de.infer_pattern(["anna@x.de"], people), ("first", "anna@x.de"))
        self.assertEqual(de.infer_pattern(["lisa.weber@x.de"], people), ("first.last", "lisa.weber@x.de"))  # by shape
        self.assertEqual(de.infer_pattern(["office1@x.de"], people), ("", ""))

    def test_related_domains(self):
        self.assertTrue(de.related("firma-gmbh.de", "firma.com"))
        self.assertTrue(de.related("mail.flowbase.de", "flowbase.de"))
        self.assertFalse(de.related("webagentur.de", "flowbase.de"))

    def test_mx_lookup(self):
        answer = json.dumps({"Status": 0, "Answer": [{"type": 15, "data": "10 mx00.ionos.de."}]})
        with mock.patch.object(de, "get", return_value=answer):
            self.assertEqual(de.mx_lookup("firma.de"), (True, "IONOS"))
        answer = json.dumps({"Status": 0, "Answer": [{"type": 15, "data": "0 firma-de.mail.protection.outlook.com."}]})
        with mock.patch.object(de, "get", return_value=answer):
            self.assertEqual(de.mx_lookup("firma.de"), (True, "Microsoft 365"))
        with mock.patch.object(de, "get", return_value=json.dumps({"Status": 3})):
            self.assertEqual(de.mx_lookup("nope.de"), (False, ""))
        with mock.patch.object(de, "get", return_value=None):
            self.assertEqual(de.mx_lookup("firma.de"), (None, ""))


class SafeFetch(unittest.TestCase):
    def resolve_to(self, ip):
        fam = socket.AF_INET6 if ":" in ip else socket.AF_INET
        return mock.patch.object(socket, "getaddrinfo", return_value=[(fam, socket.SOCK_STREAM, 6, "", (ip, 443))])

    def test_blocks_private_and_odd_urls(self):
        for ip in (
            "127.0.0.1",
            "10.1.2.3",
            "192.168.0.10",
            "169.254.169.254",
            "::1",
            "::ffff:127.0.0.1",
            "100.64.0.1",
            "0.0.0.0",
        ):
            with self.resolve_to(ip), self.assertRaises(ValueError, msg=ip):
                de.check_url("https://evil.example")
        with self.resolve_to("93.184.216.34"):
            de.check_url("https://ok.example")
            for url in ("ftp://ok.example", "https://ok.example:8080/", "file:///etc/passwd", "https:///nohost"):
                with self.assertRaises(ValueError, msg=url):
                    de.check_url(url)

    def test_redirects_are_rechecked(self):
        req = urllib.request.Request("https://ok.example")
        with self.resolve_to("127.0.0.1"), self.assertRaises(ValueError):
            de._CheckedRedirect().redirect_request(req, None, 302, "Found", {}, "http://localhost/admin")

    def test_fetch_returns_none_for_blocked_hosts(self):
        with self.resolve_to("10.0.0.1"), mock.patch.object(de._checked, "open") as opener:
            self.assertEqual(de.fetch("https://intranet.example", checked=True), (None, None))
            opener.assert_not_called()

    def test_decode_latin1(self):
        self.assertEqual(de._decode("Geschäftsführer".encode("cp1252"), "text/html"), "Geschäftsführer")
        self.assertEqual(de._decode("Grüße".encode(), "text/html; charset=utf-8"), "Grüße")


class RealFetch(unittest.TestCase):
    """The real urllib path against a local server. Loopback is allowed only for this test's port."""

    @classmethod
    def setUpClass(cls):
        from http.server import BaseHTTPRequestHandler

        class Site(BaseHTTPRequestHandler):
            def do_GET(self):
                routes = {
                    "/latin1": (
                        200,
                        {"Content-Type": "text/html; charset=iso-8859-1"},
                        "<p>Geschäftsführer: Jürgen Groß</p>".encode("latin-1"),
                    ),
                    "/to-ok": (302, {"Location": "/latin1"}, b""),
                    "/to-metadata": (302, {"Location": "http://169.254.169.254/latest/meta-data/"}, b""),
                }
                status, headers, body = routes.get(self.path, (404, {}, b""))
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Site)
        cls.port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        original = de.check_url
        cls.patch = mock.patch.object(de, "check_url", side_effect=lambda u: None if f":{cls.port}/" in u else original(u))
        cls.patch.start()

    @classmethod
    def tearDownClass(cls):
        cls.patch.stop()
        cls.httpd.shutdown()

    def test_redirect_and_charset(self):
        body, final = de.fetch(f"http://127.0.0.1:{self.port}/to-ok", checked=True)
        self.assertEqual(final, f"http://127.0.0.1:{self.port}/latin1")
        self.assertEqual(de.representatives(de.html_text(body))[0]["name"], "Jürgen Groß")

    def test_redirect_to_metadata_service_is_refused(self):
        self.assertEqual(de.fetch(f"http://127.0.0.1:{self.port}/to-metadata", checked=True), (None, None))


class Sources(unittest.TestCase):
    def test_ba_v4_and_fallback_to_v6(self):
        v6 = {
            "maxErgebnisse": "120",
            "stellenangebote": [
                {
                    "referenznummer": "10000-1-S",
                    "stellenangebotsTitel": "Softwareentwickler (m/w/d)",
                    "arbeitgeber": "Flowbase GmbH",
                    "arbeitsorte": [{"ort": "Berlin"}],
                    "aktuelleVeroeffentlichungsdatum": "2026-09-30",
                },
                {"refnr": "10000-2-S", "titel": "Ohne Arbeitgeber"},
            ],
        }
        calls = []

        def fake_get(url, timeout=8, data=None, headers=None):
            calls.append(url)
            return None if "/pc/v4/jobs" in url else json.dumps(v6)

        with mock.patch.object(de, "get", side_effect=fake_get):
            res = de.ba_jobs("Softwareentwickler", "Berlin", 25, 1, 30, 1)
        self.assertIn("zeitarbeit=false", calls[0])
        self.assertIn("pav=false", calls[0])
        self.assertIn("/pc/v6/jobs", calls[1])
        self.assertEqual(res["total"], 120)
        self.assertEqual(res["next_page"], 2)
        self.assertEqual(
            res["jobs"],
            [
                {
                    "source": "ba",
                    "title": "Softwareentwickler (m/w/d)",
                    "company": "Flowbase GmbH",
                    "location": "Berlin",
                    "refnr": "10000-1-S",
                    "url": "https://www.arbeitsagentur.de/jobsuche/jobdetail/10000-1-S",
                    "external_url": "",
                    "date": "2026-09-30",
                }
            ],
        )

    def test_ba_unreachable(self):
        with mock.patch.object(de, "get", return_value=None), self.assertRaises(RuntimeError):
            de.ba_jobs("x")

    def test_arbeitnow_filters_and_hints(self):
        page = {
            "data": [
                {
                    "title": "AI Engineer",
                    "company_name": "Acme",
                    "remote": True,
                    "url": "https://arbeitnow.com/j/1",
                    "tags": ["AI"],
                    "location": "Berlin",
                    "created_at": 1790000000,
                    "description": '<p>Visit <a href="https://www.acme-robotics.de/about">us</a>. Apply via jobs@acme-robotics.de '
                    '<img src="https://cdn.acme.de/logo.png"> or https://acme.jobs.personio.de</p>',
                },
                {"title": "Maintenance Technician", "company_name": "Other", "remote": True, "url": "u2", "description": "x"},
                {"title": "AI Researcher", "company_name": "Onsite", "remote": False, "url": "u3", "description": "y"},
            ],
            "links": {"next": "https://www.arbeitnow.com/api/job-board-api?page=2"},
        }
        with mock.patch.object(de, "get", return_value=json.dumps(page)) as g:
            res = de.arbeitnow("ai", visa=True, remote=True)
        self.assertIn("visa_sponsorship=true", g.call_args_list[0][0][0])
        self.assertEqual([j["company"] for j in res["jobs"]], ["Acme"] * 3)  # same page returned 3 times by the mock
        job = res["jobs"][0]
        self.assertEqual(
            (job["emails"], job["website"], job["date"]), (["jobs@acme-robotics.de"], "https://acme-robotics.de", "2026-09-21")
        )
        self.assertEqual(res["next_page"], 4)

    def test_yc_skips_inactive(self):
        hits = {
            "hits": [
                {"slug": "a", "name": "A", "status": "Active", "isHiring": True},
                {"slug": "b", "name": "B", "status": "Inactive"},
            ],
            "nbPages": 1,
        }
        with mock.patch.object(de, "algolia", return_value=hits):
            self.assertEqual([(c["name"], c["hiring"], c["kind"]) for c in de.yc_companies("Germany")], [("A", True, "startup")])

    def test_group_jobs(self):
        jobs = [
            {"source": "ba", "company": "Flowbase GmbH", "title": "A", "refnr": "1"},
            {"source": "ba", "company": "flowbase gmbh", "title": "B", "emails": ["x@flowbase.de"]},
        ]
        (c,) = de.group_jobs(jobs)
        self.assertEqual((len(c["jobs"]), c["ba_refnr"], c["emails"]), (2, "1", ["x@flowbase.de"]))

    def test_domain_candidates(self):
        cands = de.domain_candidates("Müller Maschinenbau GmbH & Co. KG")
        self.assertEqual(cands[:4], ["muellermaschinenbau.de", "mueller-maschinenbau.de", "mueller.de", "mullermaschinenbau.de"])
        self.assertIn("muellermaschinenbau.com", cands)
        self.assertEqual(de.domain_candidates("GmbH"), [])


# A fake company website: homepage -> Impressum + careers page
SITE = {
    "https://flowbase.de": (
        '<a href="/impressum">Impressum</a> <a href="/karriere">Karriere</a> <a href="/kontakt">Kontakt</a>'
        "<p>Write to anna.schroeder@flowbase.de</p>"
    ),
    "https://flowbase.de/impressum": """<h1>Impressum</h1><p>Flowbase GmbH, Torstraße 12, 10119 Berlin</p>
        <p>Geschäftsführer: Herr Dr. Jürgen Müller, Anna Schröder</p><p>E-Mail: info@flowbase.de</p>
        <p>Datenschutz: datenschutz@flowbase.de</p><p>Registergericht: Amtsgericht Charlottenburg, HRB 123456 B</p>""",
    "https://flowbase.de/karriere": "<p>Initiativbewerbung an bewerbung@flowbase.de</p>",
    "https://flowbase.de/kontakt": "<p>hello@flowbase.de</p>",
}


def fake_fetch(site):
    def fetch(url, timeout=8, data=None, headers=None, checked=False):
        key = url.rstrip("/").replace("http://www.", "https://")  # like a real http -> https redirect
        return (site[key], key + "/") if key in site else (None, None)

    return fetch


class Enrich(unittest.TestCase):
    def run_enrich(self, item, site=SITE, mx=(True, "Google Workspace"), **patches):
        with (
            mock.patch.object(de, "fetch", side_effect=fake_fetch(site)),
            mock.patch.object(de, "mx_lookup", return_value=mx),
            mock.patch.multiple(de, **patches) if patches else mock.patch.object(de, "UA", de.UA),
        ):
            return de.enrich_one(item)

    def test_full_pipeline(self):
        out = self.run_enrich({"id": "1", "name": "Flowbase", "website": "flowbase.de"})
        self.assertEqual(
            (out["website"], out["mail_domain"], out["impressum_url"]),
            ("https://flowbase.de", "flowbase.de", "https://flowbase.de/impressum/"),
        )
        self.assertEqual(
            (out["legal_name"], out["register"], out["city"], out["mx_provider"]),
            ("Flowbase GmbH", "HRB 123456 B", "Berlin", "Google Workspace"),
        )
        self.assertEqual((out["pattern"], out["pattern_from"]), ("first.last", "anna.schroeder@flowbase.de"))
        juergen, anna = out["people"]
        self.assertEqual((juergen["name"], juergen["gender"], juergen["title"]), ("Jürgen Müller", "m", "Dr."))
        self.assertEqual(juergen["emails"][0], {"email": "juergen.mueller@flowbase.de", "label": "pattern"})
        self.assertEqual(juergen["emails"][1]["label"], "guess")
        self.assertEqual(anna["emails"][0], {"email": "anna.schroeder@flowbase.de", "label": "site"})
        self.assertNotIn("anna.schroeder@flowbase.de", [e["email"] for e in anna["emails"][1:]])
        self.assertEqual(
            out["inboxes"],
            [
                {"email": "bewerbung@flowbase.de", "label": "jobs"},
                {"email": "hello@flowbase.de", "label": "generic"},
                {"email": "info@flowbase.de", "label": "generic"},
            ],
        )

    def test_mail_domain_from_impressum(self):
        site = {
            "https://flowbase.com": "<p>Imprint below</p>",
            "https://flowbase.com/impressum": "<p>Geschäftsführer: Lena Vogel</p><p>kontakt@flowbase-gmbh.de</p>",
        }
        out = self.run_enrich({"id": "1", "name": "Flowbase", "website": "https://flowbase.com/careers?x=1"}, site)
        self.assertEqual(out["mail_domain"], "flowbase-gmbh.de")
        self.assertEqual(out["people"][0]["emails"][0]["email"], "lena.vogel@flowbase-gmbh.de")

    def test_no_mx_means_no_guesses(self):
        out = self.run_enrich({"id": "1", "name": "Flowbase", "website": "flowbase.de"}, mx=(False, ""))
        self.assertEqual(out["people"][0]["emails"], [])
        self.assertTrue(any("no mail server" in n for n in out["notes"]))

    def test_ba_job_ad_gives_website_and_contact(self):
        details = {
            "arbeitgeberdarstellungUrl": "http://www.flowbase.de",
            "stellenangebotsBeschreibung": "Ihre Ansprechpartnerin: Frau Lena Vogel, lena.vogel@flowbase.de",
            "branche": "Software",
        }
        out = self.run_enrich(
            {"id": "1", "name": "Flowbase GmbH", "ba_refnr": "10000-1-S"}, ba_details=mock.Mock(return_value=details)
        )
        self.assertEqual(out["website"], "https://flowbase.de")
        lena = next(p for p in out["people"] if p["name"] == "Lena Vogel")
        self.assertEqual(
            (lena["gender"], lena["source"], lena["emails"][0]),
            ("f", "job ad", {"email": "lena.vogel@flowbase.de", "label": "jobad"}),
        )
        self.assertEqual(out["industry"], "Software")

    def test_website_guessed_from_name(self):
        site = {
            "https://mueller-maschinenbau.de": "<title>Müller Maschinenbau – Startseite</title><p>Willkommen</p>",
            "https://mueller.de": "<title>Müller Drogerie</title>",
            "https://mueller-maschinenbau.de/impressum": "<p>Inhaber: Karl Müller</p>",
        }
        out = self.run_enrich({"id": "1", "name": "Müller Maschinenbau GmbH"}, site)
        self.assertEqual((out["website"], out["website_guessed"]), ("https://mueller-maschinenbau.de", True))
        self.assertEqual(out["people"][0]["role"], "Inhaber")

    def test_parked_domain_is_not_accepted(self):
        site = {"https://flowbase.de": "<title>Flowbase</title> This domain is for sale!"}
        out = self.run_enrich({"id": "1", "name": "Flowbase"}, site)
        self.assertEqual(out["website"], "")
        self.assertTrue(out["notes"])

    def test_yc_founders_merge_with_impressum(self):
        yc = {
            "website": "https://flowbase.de",
            "one_liner": "Workflow AI for SMEs",
            "linkedin_url": "https://linkedin.com/company/f",
            "founders": [{"full_name": "Anna Schröder", "title": "Founder/CEO", "linkedin_url": "https://linkedin.com/in/anna"}],
        }
        out = self.run_enrich(
            {"id": "1", "name": "Flowbase", "yc_slug": "flowbase", "kind": "startup"}, yc_company=mock.Mock(return_value=yc)
        )
        anna = next(p for p in out["people"] if p["first"] == "Anna")
        self.assertEqual(
            (anna["role"], anna["linkedin"], out["one_liner"]),
            ("Founder/CEO · Geschäftsführer", "https://linkedin.com/in/anna", "Workflow AI for SMEs"),
        )
        self.assertEqual(len(out["people"]), 2)

    def test_errors_are_contained(self):
        with mock.patch.object(de, "_enrich", side_effect=KeyError("boom")):
            self.assertEqual(
                de.enrich_one({"id": "x", "name": "X"}), {"id": "x", "name": "X", "error": "Lookup failed: KeyError"}
            )


class Routes(unittest.TestCase):
    def test_get_validation(self):
        self.assertEqual(de.route_get("action=yc_companies&region=Mars")[0], 400)
        self.assertEqual(de.route_get("action=ba_jobs")[0], 400)
        self.assertEqual(de.route_get("action=arbeitnow&q=" + "x" * 101)[0], 400)
        self.assertEqual(de.route_get("action=nope")[0], 400)

    def test_ba_params_are_whitelisted(self):
        with mock.patch.object(de, "ba_jobs", return_value={"jobs": []}) as ba:
            de.route_get("action=ba_jobs&was=Dev&umkreis=9999&angebotsart=7&days=500&page=0")
        ba.assert_called_once_with("Dev", "", 25, 1, 30, 1)

    def test_post_validation(self):
        bad = [
            b"not json",
            b"[]",
            b'{"action":"x"}',
            b'{"action":"enrich","companies":[]}',
            json.dumps({"action": "enrich", "companies": [{"name": "x"}] * 11}).encode(),
            json.dumps({"action": "enrich", "companies": [{"name": "x", "yc_slug": "../etc"}]}).encode(),
            json.dumps({"action": "enrich", "companies": [{"id": "1"}]}).encode(),
        ]
        for body in bad:
            self.assertEqual(de.route_post(body)[0], 400, body[:60])

    def test_post_sanitises_items(self):
        with mock.patch.object(de, "enrich_one", side_effect=lambda c: c):
            status, res, _ = de.route_post(
                json.dumps(
                    {
                        "action": "enrich",
                        "companies": [
                            {"id": "1", "name": "X", "website": 5, "emails": ["ok@x.de", "bad", 3], "extra": "dropped"}
                        ],
                    }
                ).encode()
            )
        self.assertEqual(status, 200)
        self.assertEqual(
            res, [{"id": "1", "name": "X", "website": "", "yc_slug": "", "ba_refnr": "", "kind": "", "emails": ["ok@x.de"]}]
        )


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(serve.Handler, directory=ROOT))
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def req(self, path, data=None):
        try:
            with urllib.request.urlopen(urllib.request.Request(self.base + path, data=data), timeout=5) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    def test_serves_page_but_not_source(self):
        status, body = self.req("/")
        self.assertEqual(status, 200)
        self.assertIn("<title>DE Outreach</title>", body)
        for path in ("/serve.py", "/api/de.py", "/.env", "/leads.csv"):
            self.assertEqual(self.req(path)[0], 404, path)

    def test_api_get_and_post(self):
        status, body = self.req("/api/de?action=nope")
        self.assertEqual((status, json.loads(body)), (400, {"error": "Unknown action"}))
        with mock.patch.object(de, "enrich_one", side_effect=lambda c: {"id": c["id"], "people": []}):
            status, body = self.req("/api/de", json.dumps({"action": "enrich", "companies": [{"id": "1", "name": "X"}]}).encode())
        self.assertEqual((status, json.loads(body)), (200, [{"id": "1", "people": []}]))

    def test_upstream_errors_are_502(self):
        with mock.patch.object(de, "yc_companies", side_effect=RuntimeError("YC company search failed")):
            status, body = self.req("/api/de?action=yc_companies&region=Germany")
        self.assertEqual((status, json.loads(body)), (502, {"error": "YC company search failed"}))


if __name__ == "__main__":
    unittest.main()
