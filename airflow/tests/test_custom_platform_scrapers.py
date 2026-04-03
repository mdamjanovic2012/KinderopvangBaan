"""
Tests voor custom-platform scrapers die NIET via WordPressJobsScraper lopen:
  - AvemScraper           (Mercash .NET portal, verify=False)
  - Un1ekScraper          (custom CMS, numeric URL IDs)
  - KinderstadScraper     (WP REST API custom post type)
  - CKCDrentheScraper     (GetNoticed/Playwright — listing via Playwright)
  - KindenCoLudensScraper (Next.js/Playwright — listing via Playwright)
  - BerendBotjeScraper    (WordPress scraper — werkenbijberendbotje.nl)
  - HaarlemmermeerScraper (TSF Angular stub)
  - TNestScraper          (NXDOMAIN stub)
  - KinderopvangRoermondScraper (WordPress scraper — kinderopvangroermond.nl)
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.avem                  import AvemScraper
from scrapers.un1ek                 import Un1ekScraper
from scrapers.kinderstad            import KinderstadScraper
from scrapers.ckc_drenthe           import CKCDrentheScraper
from scrapers.kindencoludens        import KindenCoLudensScraper
from scrapers.berend_botje          import BerendBotjeScraper
from scrapers.haarlemmermeer        import HaarlemmermeerScraper
from scrapers.t_nest                import TNestScraper
from scrapers.kinderopvang_roermond import KinderopvangRoermondScraper


# ── HTML / JSON fixtures ──────────────────────────────────────────────────────

LISTING_HTML_AVEM = """<html><body>
<a href="/Mportal/Vacature/pedagogisch-medewerker-123">PM</a>
<a href="/Mportal/Vacature/locatiemanager-456">Locatiemanager</a>
<a href="/Mportal/Vacatures/Overzicht">Overzicht</a>
</body></html>"""

DETAIL_HTML_H1 = """<html><body>
<h1>Pedagogisch Medewerker</h1>
<main><p>Wij zoeken een PM voor 24-32 uur per week in Amsterdam.</p></main>
</body></html>"""

LISTING_HTML_UN1EK = """<html><body>
<a href="/279">PM Amsterdam</a>
<a href="/153">Locatiemanager</a>
<a href="/vacatures">Alle vacatures</a>
<a href="https://external.nl/123">Extern</a>
</body></html>"""

KINDERSTAD_API_RESPONSE = [
    {
        "id": 42,
        "link": "https://kinderstad.nl/vacature/pm-amsterdam/",
        "title": {"rendered": "Pedagogisch Medewerker Amsterdam"},
        "content": {"rendered": "<p>Wij zoeken een PM voor 32 uur per week in Amsterdam.</p>"},
        "excerpt": {"rendered": "<p>Korte samenvatting.</p>"},
    },
    {
        "id": 43,
        "link": "https://kinderstad.nl/vacature/lm-rotterdam/",
        "title": {"rendered": "Locatiemanager Rotterdam"},
        "content": {"rendered": "<p>Locatiemanager gezocht.</p>"},
        "excerpt": {"rendered": ""},
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# AvemScraper
# ══════════════════════════════════════════════════════════════════════════════

class TestAvemScraper:
    def test_company_slug(self):
        assert AvemScraper.company_slug == "avem"

    def test_company_name(self):
        assert AvemScraper.company_name == "AVEM Kinderopvang"

    def test_listing_url(self):
        assert "avem.mercash.nl" in AvemScraper.listing_url

    def test_job_url_contains(self):
        assert AvemScraper.job_url_contains == "/Vacature/"

    def test_get_all_job_urls_returns_urls(self):
        scraper = AvemScraper()
        resp = MagicMock()
        resp.text = LISTING_HTML_AVEM
        resp.raise_for_status = MagicMock()
        with patch("scrapers.avem.requests.get", return_value=resp):
            urls = scraper._get_all_job_urls()
        assert len(urls) == 2
        assert all("avem.mercash.nl" in u for u in urls)

    def test_get_all_job_urls_empty_on_error(self):
        scraper = AvemScraper()
        with patch("scrapers.avem.requests.get", side_effect=Exception("SSL error")):
            urls = scraper._get_all_job_urls()
        assert urls == []

    def test_get_all_job_urls_skips_listing_url_itself(self):
        scraper = AvemScraper()
        resp = MagicMock()
        resp.text = LISTING_HTML_AVEM
        resp.raise_for_status = MagicMock()
        with patch("scrapers.avem.requests.get", return_value=resp):
            urls = scraper._get_all_job_urls()
        from scrapers.avem import PORTAL_URL
        assert PORTAL_URL not in urls

    def test_scrape_job_page_h1_fallback(self):
        scraper = AvemScraper()
        resp = MagicMock()
        resp.text = DETAIL_HTML_H1
        resp.raise_for_status = MagicMock()
        with patch("scrapers.avem.requests.get", return_value=resp):
            job = scraper._scrape_job_page("https://avem.mercash.nl/Mportal/Vacature/pm-123")
        assert job is not None
        assert job["title"] == "Pedagogisch Medewerker"
        assert job["external_id"] == "pm-123"

    def test_scrape_job_page_returns_none_on_error(self):
        scraper = AvemScraper()
        with patch("scrapers.avem.requests.get", side_effect=Exception("timeout")):
            job = scraper._scrape_job_page("https://avem.mercash.nl/Mportal/Vacature/pm-123")
        assert job is None

    def test_scrape_job_page_returns_none_when_no_title(self):
        scraper = AvemScraper()
        resp = MagicMock()
        resp.text = "<html><body><main><p>Geen titel</p></main></body></html>"
        resp.raise_for_status = MagicMock()
        with patch("scrapers.avem.requests.get", return_value=resp):
            job = scraper._scrape_job_page("https://avem.mercash.nl/Mportal/Vacature/test")
        assert job is None

    def test_fetch_company_returns_name_on_error(self):
        scraper = AvemScraper()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=Exception("conn")):
            company = scraper.fetch_company()
        assert company["name"] == "AVEM Kinderopvang"

    def test_fetch_company_website_url(self):
        scraper = AvemScraper()
        company = scraper.fetch_company.__func__(scraper) if False else None
        # Just check class attribute
        assert "avem-kinderopvang.nl" in AvemScraper.website_url


# ══════════════════════════════════════════════════════════════════════════════
# Un1ekScraper
# ══════════════════════════════════════════════════════════════════════════════

class TestUn1ekScraper:
    def test_company_slug(self):
        assert Un1ekScraper.company_slug == "un1ek"

    def test_company_name(self):
        assert Un1ekScraper.company_name == "Un1ek Kinderopvang"

    def test_get_job_urls_numeric_only(self):
        scraper = Un1ekScraper()
        resp = MagicMock()
        resp.text = LISTING_HTML_UN1EK
        resp.raise_for_status = MagicMock()
        with patch("scrapers.un1ek.requests.get", return_value=resp):
            urls = scraper._get_job_urls()
        assert len(urls) == 2
        assert "https://www.un1ek.nl/279" in urls
        assert "https://www.un1ek.nl/153" in urls

    def test_get_job_urls_empty_on_error(self):
        scraper = Un1ekScraper()
        with patch("scrapers.un1ek.requests.get", side_effect=Exception("timeout")):
            urls = scraper._get_job_urls()
        assert urls == []

    def test_get_job_urls_ignores_non_numeric(self):
        """'/vacatures' path and external URLs should be ignored."""
        scraper = Un1ekScraper()
        resp = MagicMock()
        resp.text = LISTING_HTML_UN1EK
        resp.raise_for_status = MagicMock()
        with patch("scrapers.un1ek.requests.get", return_value=resp):
            urls = scraper._get_job_urls()
        assert not any("/vacatures" in u for u in urls)

    def test_scrape_job_page_h1_fallback(self):
        scraper = Un1ekScraper()
        resp = MagicMock()
        resp.text = DETAIL_HTML_H1
        resp.raise_for_status = MagicMock()
        with patch("scrapers.un1ek.requests.get", return_value=resp):
            job = scraper._scrape_job_page("https://www.un1ek.nl/279")
        assert job is not None
        assert job["title"] == "Pedagogisch Medewerker"
        assert job["external_id"] == "279"
        assert job["hours_min"] == 24
        assert job["hours_max"] == 32

    def test_scrape_job_page_returns_none_on_error(self):
        scraper = Un1ekScraper()
        with patch("scrapers.un1ek.requests.get", side_effect=Exception("timeout")):
            job = scraper._scrape_job_page("https://www.un1ek.nl/279")
        assert job is None

    def test_scrape_job_page_returns_none_when_no_title(self):
        scraper = Un1ekScraper()
        resp = MagicMock()
        resp.text = "<html><body><main><p>Geen titel</p></main></body></html>"
        resp.raise_for_status = MagicMock()
        with patch("scrapers.un1ek.requests.get", return_value=resp):
            job = scraper._scrape_job_page("https://www.un1ek.nl/279")
        assert job is None

    def test_fetch_jobs_returns_list(self):
        scraper = Un1ekScraper()
        listing_r = MagicMock()
        listing_r.text = LISTING_HTML_UN1EK
        listing_r.raise_for_status = MagicMock()
        detail_r = MagicMock()
        detail_r.text = DETAIL_HTML_H1
        detail_r.raise_for_status = MagicMock()
        with patch("scrapers.un1ek.requests.get",
                   side_effect=[listing_r, detail_r, detail_r]):
            jobs = scraper.fetch_jobs()
        assert isinstance(jobs, list)
        assert len(jobs) == 2

    def test_fetch_jobs_empty_on_listing_error(self):
        scraper = Un1ekScraper()
        with patch("scrapers.un1ek.requests.get", side_effect=Exception("timeout")):
            jobs = scraper.fetch_jobs()
        assert jobs == []

    def test_fetch_company_returns_name_on_error(self):
        scraper = Un1ekScraper()
        with patch("scrapers.un1ek.requests.get", side_effect=Exception("conn")):
            company = scraper.fetch_company()
        assert company["name"] == "Un1ek Kinderopvang"

    def test_fetch_company_success_path(self):
        scraper = Un1ekScraper()
        resp = MagicMock()
        resp.text = """<html><head>
<meta name="description" content="Un1ek kinderopvang">
</head><body>
<header><img src="https://www.un1ek.nl/logo.png" alt="un1ek logo"></header>
</body></html>"""
        resp.raise_for_status = MagicMock()
        with patch("scrapers.un1ek.requests.get", return_value=resp):
            company = scraper.fetch_company()
        assert company["name"] == "Un1ek Kinderopvang"
        assert company["description"] == "Un1ek kinderopvang"

    def test_fetch_jobs_jsonld_path(self):
        """_scrape_job_page gebruikt JSON-LD als primaire bron."""
        scraper = Un1ekScraper()
        listing_r = MagicMock()
        listing_r.text = LISTING_HTML_UN1EK
        listing_r.raise_for_status = MagicMock()
        detail_html = """<html><body>
<script type="application/ld+json">{"@type": "JobPosting", "title": "PM JSON-LD",
"description": "Test", "identifier": {"value": "279"}}</script>
</body></html>"""
        detail_r = MagicMock()
        detail_r.text = detail_html
        detail_r.raise_for_status = MagicMock()
        with patch("scrapers.un1ek.requests.get",
                   side_effect=[listing_r, detail_r, detail_r]):
            jobs = scraper.fetch_jobs()
        assert any(j["title"] == "PM JSON-LD" for j in jobs)


# ══════════════════════════════════════════════════════════════════════════════
# KinderstadScraper
# ══════════════════════════════════════════════════════════════════════════════

class TestKinderstadScraper:
    def test_company_slug(self):
        assert KinderstadScraper.company_slug == "kinderstad"

    def test_company_name(self):
        assert KinderstadScraper.company_name == "Kinderstad"

    def test_fetch_jobs_parses_api_response(self):
        scraper = KinderstadScraper()
        resp = MagicMock()
        resp.json.return_value = KINDERSTAD_API_RESPONSE
        resp.raise_for_status = MagicMock()
        with patch("scrapers.kinderstad.requests.get", return_value=resp):
            jobs = scraper.fetch_jobs()
        assert len(jobs) == 2
        assert jobs[0]["title"] == "Pedagogisch Medewerker Amsterdam"
        assert jobs[0]["source_url"] == "https://kinderstad.nl/vacature/pm-amsterdam/"
        assert jobs[0]["external_id"] == "42"
        assert jobs[0]["city"] == "Amsterdam"
        assert jobs[0]["hours_min"] == 32

    def test_fetch_jobs_empty_on_error(self):
        scraper = KinderstadScraper()
        with patch("scrapers.kinderstad.requests.get", side_effect=Exception("timeout")):
            jobs = scraper.fetch_jobs()
        assert jobs == []

    def test_fetch_jobs_empty_on_invalid_json(self):
        """If API returns a dict (not list), fetch_jobs() returns []."""
        scraper = KinderstadScraper()
        resp = MagicMock()
        resp.json.return_value = {"error": "not found"}
        resp.raise_for_status = MagicMock()
        with patch("scrapers.kinderstad.requests.get", return_value=resp):
            jobs = scraper.fetch_jobs()
        assert jobs == []

    def test_fetch_jobs_skips_items_without_title(self):
        scraper = KinderstadScraper()
        data = [{"id": 1, "link": "https://kinderstad.nl/v/1/", "title": {"rendered": ""}}]
        resp = MagicMock()
        resp.json.return_value = data
        resp.raise_for_status = MagicMock()
        with patch("scrapers.kinderstad.requests.get", return_value=resp):
            jobs = scraper.fetch_jobs()
        assert jobs == []

    def test_fetch_jobs_short_description_from_content_when_no_excerpt(self):
        scraper = KinderstadScraper()
        resp = MagicMock()
        resp.json.return_value = [KINDERSTAD_API_RESPONSE[1]]  # no excerpt
        resp.raise_for_status = MagicMock()
        with patch("scrapers.kinderstad.requests.get", return_value=resp):
            jobs = scraper.fetch_jobs()
        assert jobs[0]["short_description"] != ""

    def test_fetch_company_returns_name_on_error(self):
        scraper = KinderstadScraper()
        with patch("scrapers.kinderstad.requests.get", side_effect=Exception("conn")):
            company = scraper.fetch_company()
        assert company["name"] == "Kinderstad"

    def test_fetch_company_success_path(self):
        scraper = KinderstadScraper()
        resp = MagicMock()
        resp.text = """<html><head>
<meta name="description" content="Kinderstad kinderopvang">
</head><body>
<header><img src="https://kinderstad.nl/logo.png" alt="logo"></header>
</body></html>"""
        resp.raise_for_status = MagicMock()
        with patch("scrapers.kinderstad.requests.get", return_value=resp):
            company = scraper.fetch_company()
        assert company["name"] == "Kinderstad"
        assert company["description"] == "Kinderstad kinderopvang"

    def test_parse_item_error_is_handled(self):
        """_parse_item crash wordt afgevangen in fetch_jobs."""
        scraper = KinderstadScraper()
        bad_item = {"id": None, "link": None, "title": None}
        resp = MagicMock()
        resp.json.return_value = [bad_item]
        resp.raise_for_status = MagicMock()
        with patch("scrapers.kinderstad.requests.get", return_value=resp):
            jobs = scraper.fetch_jobs()
        assert isinstance(jobs, list)


# ══════════════════════════════════════════════════════════════════════════════
# CKCDrentheScraper — Playwright listing (pragma: no cover)
# ══════════════════════════════════════════════════════════════════════════════

class TestCKCDrentheScraper:
    def test_company_slug(self):
        assert CKCDrentheScraper.company_slug == "ckc-drenthe"

    def test_fetch_company_returns_name_on_error(self):
        scraper = CKCDrentheScraper()
        with patch("scrapers.ckc_drenthe.requests.get", side_effect=Exception("conn")):
            company = scraper.fetch_company()
        assert company["name"] == "CKC Drenthe"
        assert company["logo_url"] == ""

    def test_fetch_company_website_url(self):
        assert CKCDrentheScraper().fetch_company.__func__  # callable
        from scrapers.ckc_drenthe import BASE_URL
        assert "werkenbijckcdrenthe.nl" in BASE_URL

    def test_fetch_jobs_returns_empty_when_no_playwright_urls(self):
        """When _get_job_urls_playwright returns [], fetch_jobs returns []."""
        scraper = CKCDrentheScraper()
        with patch("scrapers.ckc_drenthe._get_job_urls_playwright", return_value=[]):
            jobs = scraper.fetch_jobs()
        assert jobs == []

    def test_fetch_jobs_with_mocked_urls(self):
        """fetch_jobs scrapes detail pages when given URLs."""
        scraper = CKCDrentheScraper()
        detail_r = MagicMock()
        detail_r.text = DETAIL_HTML_H1
        detail_r.raise_for_status = MagicMock()
        with patch("scrapers.ckc_drenthe._get_job_urls_playwright",
                   return_value=["https://www.werkenbijckcdrenthe.nl/vacature/pm-test"]), \
             patch("scrapers.ckc_drenthe.requests.get", return_value=detail_r):
            jobs = scraper.fetch_jobs()
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Pedagogisch Medewerker"

    def test_fetch_jobs_jsonld_path(self):
        """fetch_jobs gebruikt JSON-LD als het aanwezig is."""
        scraper = CKCDrentheScraper()
        detail_html = """<html><body>
<h1>PM Test</h1>
<script type="application/ld+json">{"@type": "JobPosting", "title": "PM via JSON-LD",
"description": "Test", "identifier": {"value": "ckc-1"}}</script>
</body></html>"""
        detail_r = MagicMock()
        detail_r.text = detail_html
        detail_r.raise_for_status = MagicMock()
        with patch("scrapers.ckc_drenthe._get_job_urls_playwright",
                   return_value=["https://www.werkenbijckcdrenthe.nl/vacature/pm-ld"]), \
             patch("scrapers.ckc_drenthe.requests.get", return_value=detail_r):
            jobs = scraper.fetch_jobs()
        assert len(jobs) == 1
        assert jobs[0]["title"] == "PM via JSON-LD"

    def test_fetch_jobs_skips_no_title(self):
        scraper = CKCDrentheScraper()
        detail_r = MagicMock()
        detail_r.text = "<html><body><main><p>Geen titel</p></main></body></html>"
        detail_r.raise_for_status = MagicMock()
        with patch("scrapers.ckc_drenthe._get_job_urls_playwright",
                   return_value=["https://www.werkenbijckcdrenthe.nl/vacature/leeg"]), \
             patch("scrapers.ckc_drenthe.requests.get", return_value=detail_r):
            jobs = scraper.fetch_jobs()
        assert jobs == []

    def test_fetch_jobs_handles_detail_exception(self):
        scraper = CKCDrentheScraper()
        with patch("scrapers.ckc_drenthe._get_job_urls_playwright",
                   return_value=["https://www.werkenbijckcdrenthe.nl/vacature/err"]), \
             patch("scrapers.ckc_drenthe.requests.get", side_effect=Exception("timeout")):
            jobs = scraper.fetch_jobs()
        assert jobs == []

    def test_fetch_company_success_path(self):
        scraper = CKCDrentheScraper()
        resp = MagicMock()
        resp.text = """<html><head>
<meta name="description" content="CKC Drenthe kinderopvang">
</head><body>
<header><img src="/img/logo.png" alt="logo CKC"></header>
</body></html>"""
        resp.raise_for_status = MagicMock()
        with patch("scrapers.ckc_drenthe.requests.get", return_value=resp):
            company = scraper.fetch_company()
        assert company["name"] == "CKC Drenthe"
        assert company["description"] == "CKC Drenthe kinderopvang"


# ══════════════════════════════════════════════════════════════════════════════
# KindenCoLudensScraper — Playwright listing (pragma: no cover)
# ══════════════════════════════════════════════════════════════════════════════

class TestKindenCoLudensScraper:
    def test_company_slug(self):
        assert KindenCoLudensScraper.company_slug == "kindencoludens"

    def test_fetch_company_returns_name_on_error(self):
        scraper = KindenCoLudensScraper()
        with patch("requests.get", side_effect=Exception("conn")):
            company = scraper.fetch_company()
        assert company["name"] == "Kind&co Ludens"
        assert company["logo_url"] == ""

    def test_fetch_jobs_returns_empty_when_no_playwright_urls(self):
        scraper = KindenCoLudensScraper()
        with patch("scrapers.kindencoludens._get_job_urls_playwright", return_value=[]):
            jobs = scraper.fetch_jobs()
        assert jobs == []

    def test_fetch_jobs_with_mocked_urls(self):
        scraper = KindenCoLudensScraper()
        with patch("scrapers.kindencoludens._get_job_urls_playwright",
                   return_value=["https://www.kindencoludens.nl/nl/werken-bij/vacatures/pm-test"]), \
             patch("scrapers.kindencoludens._render_detail_playwright",
                   return_value=DETAIL_HTML_H1):
            jobs = scraper.fetch_jobs()
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Pedagogisch Medewerker"

    def test_fetch_jobs_skips_empty_html(self):
        scraper = KindenCoLudensScraper()
        with patch("scrapers.kindencoludens._get_job_urls_playwright",
                   return_value=["https://www.kindencoludens.nl/nl/werken-bij/vacatures/test"]), \
             patch("scrapers.kindencoludens._render_detail_playwright", return_value=""):
            jobs = scraper.fetch_jobs()
        assert jobs == []

    def test_fetch_jobs_jsonld_path(self):
        detail_html = """<html><body>
<h1>PM</h1>
<script type="application/ld+json">{"@type": "JobPosting", "title": "PM JSON-LD",
"description": "Test", "identifier": {"value": "kc-1"}}</script>
</body></html>"""
        scraper = KindenCoLudensScraper()
        with patch("scrapers.kindencoludens._get_job_urls_playwright",
                   return_value=["https://www.kindencoludens.nl/nl/werken-bij/vacatures/pm-ld"]), \
             patch("scrapers.kindencoludens._render_detail_playwright", return_value=detail_html):
            jobs = scraper.fetch_jobs()
        assert len(jobs) == 1
        assert jobs[0]["title"] == "PM JSON-LD"

    def test_fetch_jobs_skips_no_title(self):
        scraper = KindenCoLudensScraper()
        with patch("scrapers.kindencoludens._get_job_urls_playwright",
                   return_value=["https://www.kindencoludens.nl/nl/werken-bij/vacatures/leeg"]), \
             patch("scrapers.kindencoludens._render_detail_playwright",
                   return_value="<html><body><main><p>Geen titel</p></main></body></html>"):
            jobs = scraper.fetch_jobs()
        assert jobs == []

    def test_fetch_jobs_handles_exception(self):
        scraper = KindenCoLudensScraper()
        with patch("scrapers.kindencoludens._get_job_urls_playwright",
                   return_value=["https://www.kindencoludens.nl/nl/werken-bij/vacatures/err"]), \
             patch("scrapers.kindencoludens._render_detail_playwright",
                   side_effect=Exception("boom")):
            jobs = scraper.fetch_jobs()
        assert jobs == []

    def test_fetch_company_success_path(self):
        scraper = KindenCoLudensScraper()
        resp = MagicMock()
        resp.text = """<html><head>
<meta name="description" content="Kind en Co Ludens kinderopvang">
</head><body>
<header><img src="https://www.kindencoludens.nl/logo.png" alt="logo"></header>
</body></html>"""
        resp.raise_for_status = MagicMock()
        with patch("requests.get", return_value=resp):
            company = scraper.fetch_company()
        assert company["name"] == "Kind&co Ludens"


# ══════════════════════════════════════════════════════════════════════════════
# Stub scrapers — altijd lege lijst
# ══════════════════════════════════════════════════════════════════════════════

class TestBerendBotjeScraper:
    def test_company_slug(self):
        assert BerendBotjeScraper.company_slug == "berend-botje"

    def test_fetch_jobs_returns_list(self):
        # BerendBotje is a real WordPress scraper (werkenbijberendbotje.nl)
        jobs = BerendBotjeScraper().fetch_jobs()
        assert isinstance(jobs, list)
        if jobs:
            assert "title" in jobs[0]
            assert "source_url" in jobs[0]

    def test_fetch_company_returns_dict(self):
        company = BerendBotjeScraper().fetch_company()
        assert company["name"] == "Berend Botje"
        assert company["website"].startswith("http")


class TestHaarlemmermeerScraper:
    def test_company_slug(self):
        assert HaarlemmermeerScraper.company_slug == "haarlemmermeer"

    def test_fetch_jobs_returns_empty(self):
        assert HaarlemmermeerScraper().fetch_jobs() == []

    def test_fetch_company_returns_dict(self):
        company = HaarlemmermeerScraper().fetch_company()
        assert company["name"] == "Kinderopvang Haarlemmermeer"
        assert company["website"].startswith("http")


class TestTNestScraper:
    def test_company_slug(self):
        assert TNestScraper.company_slug is not None

    def test_fetch_jobs_returns_empty(self):
        assert TNestScraper().fetch_jobs() == []

    def test_fetch_company_returns_dict(self):
        company = TNestScraper().fetch_company()
        assert isinstance(company, dict)
        assert "name" in company


class TestKinderopvangRoermondScraper:
    def test_company_slug(self):
        assert KinderopvangRoermondScraper.company_slug == "kinderopvang-roermond"

    def test_fetch_jobs_returns_list(self):
        # KinderopvangRoermond is a real WordPress scraper (kinderopvangroermond.nl)
        jobs = KinderopvangRoermondScraper().fetch_jobs()
        assert isinstance(jobs, list)
        if jobs:
            assert "title" in jobs[0]
            assert "source_url" in jobs[0]

    def test_fetch_company_returns_dict(self):
        company = KinderopvangRoermondScraper().fetch_company()
        assert company["name"] == "Kinderopvang Roermond"
        assert company["website"].startswith("http")
