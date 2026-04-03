"""
Unit tests for Kanteel scraper (WordPress + JSON-LD, numeric URLs, SSL disabled).
"""
import json, sys, os, pytest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scrapers.kanteel import KanteelScraper

# Kanteel JSON-LD has literal control characters (newlines) in description strings
JOBPOSTING_LD = {
    "@context": "https://schema.org/",
    "@type": "JobPosting",
    "title": "Locatiemanager KC de Haren",
    "jobLocation": {"@type": "Place", "address": {
        "@type": "PostalAddress",
        "addressLocality": "Den Bosch",
        "postalCode": "5212AB",
    }},
    "employmentType": ["PART_TIME"],
    "description": "<p>We zoeken een locatiemanager voor 32 uur per week in Den Bosch.</p>",
}

LISTING_HTML = """<html><body>
<a href="/vacature/408">Locatiemanager</a>
<a href="/vacature/407">Pedagogisch Medewerker</a>
<a href="/vacature/open-sollicitatie">Open sollicitatie</a>
<a href="/vacatures/">Alle vacatures</a>
</body></html>"""

DETAIL_HTML = f"""<html><body>
<h1>Locatiemanager KC de Haren</h1>
<script type="application/ld+json">{json.dumps(JOBPOSTING_LD)}</script>
</body></html>"""

DETAIL_HTML_NO_LD = """<html><body>
<h1>Pedagogisch Medewerker</h1>
<main><p>We zoeken een PM voor 24-32 uur in Tilburg.</p></main>
</body></html>"""


class TestKanteelConfig:
    def test_company_slug(self): assert KanteelScraper.company_slug == "kanteel"
    def test_listing_url(self): assert "werkenbijkanteel.nl" in KanteelScraper.listing_url


class TestKanteelGetAllJobUrls:
    def test_only_numeric_urls(self):
        scraper = KanteelScraper()
        r = MagicMock(); r.text = LISTING_HTML; r.raise_for_status = MagicMock()
        with patch("scrapers.kanteel.requests.get", return_value=r):
            urls = scraper._get_all_job_urls()
        # /vacature/408 and /vacature/407 — numeric only; open-sollicitatie excluded
        assert len(urls) == 2
        assert all("/vacature/" in u for u in urls)
        assert all(u.split("/vacature/")[-1].isdigit() for u in urls)

    def test_returns_empty_on_error(self):
        with patch("scrapers.kanteel.requests.get", side_effect=Exception("SSL")):
            assert KanteelScraper()._get_all_job_urls() == []


class TestKanteelFetchJobs:
    def test_parses_jsonld(self):
        scraper = KanteelScraper()
        r = MagicMock(); r.text = DETAIL_HTML; r.raise_for_status = MagicMock()
        with patch.object(scraper, "_get_all_job_urls",
                          return_value=["https://werkenbijkanteel.nl/vacature/408"]):
            with patch("scrapers.kanteel.requests.get", return_value=r):
                jobs = scraper.fetch_jobs()
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Locatiemanager KC de Haren"
        assert jobs[0]["city"] == "Den Bosch"

    def test_html_fallback(self):
        scraper = KanteelScraper()
        r = MagicMock(); r.text = DETAIL_HTML_NO_LD; r.raise_for_status = MagicMock()
        with patch.object(scraper, "_get_all_job_urls",
                          return_value=["https://werkenbijkanteel.nl/vacature/407"]):
            with patch("scrapers.kanteel.requests.get", return_value=r):
                jobs = scraper.fetch_jobs()
        assert len(jobs) == 1
        assert jobs[0]["hours_min"] == 24
        assert jobs[0]["hours_max"] == 32

    def test_empty_on_error(self):
        scraper = KanteelScraper()
        with patch.object(scraper, "_get_all_job_urls",
                          return_value=["https://werkenbijkanteel.nl/vacature/408"]):
            with patch("scrapers.kanteel.requests.get", side_effect=Exception("err")):
                jobs = scraper.fetch_jobs()
        assert jobs == []


@pytest.mark.integration
class TestKanteelLive:
    def test_listing_bereikbaar(self):
        import requests, urllib3
        urllib3.disable_warnings()
        r = requests.get(KanteelScraper.listing_url, timeout=15, verify=False)
        assert r.status_code == 200
