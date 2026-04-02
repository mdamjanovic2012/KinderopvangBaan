"""Unit tests for BijdeHandjes scraper (WordPress + JSON-LD in @graph, /vacatures/{id}-slug)."""
import json, sys, os, pytest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scrapers.bijdehandjes import BijdeHandjesScraper

# JSON-LD uses @graph containing a JobPosting (as seen on bijdehandjes.nl)
JOBPOSTING_GRAPH_LD = {
    "@context": "https://schema.org",
    "@graph": [
        {
            "@type": "JobPosting",
            "title": "Pedagogisch medewerker peuters VE",
            "datePosted": "2026-03-12T00:00:00",
            "jobLocation": {
                "@type": "Place",
                "name": "Bennekom",
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": "Bennekom",
                    "postalCode": "6721AB",
                },
            },
            "description": "<p>We zoeken een PM voor 20-28 uur per week.</p>",
        }
    ],
}

LISTING_HTML = """<html><body>
<a href="/vacatures/3057-pedagogisch-medewerker-peuters-ve">PM Peuters VE</a>
<a href="/vacatures/3053-pedagogisch-medewerker-0-tot-2">PM 0-2</a>
<a href="/vacatures/">Alle vacatures</a>
</body></html>"""

DETAIL_HTML = f"""<html><body>
<h1>Pedagogisch medewerker peuters VE</h1>
<script type="application/ld+json">{json.dumps(JOBPOSTING_GRAPH_LD)}</script>
</body></html>"""


class TestBijdeHandjesConfig:
    def test_company_slug(self): assert BijdeHandjesScraper.company_slug == "bijdehandjes"
    def test_listing_url(self): assert "bijdehandjes.nl" in BijdeHandjesScraper.listing_url


class TestBijdeHandjesFetchJobs:
    def test_parses_graph_jsonld(self):
        scraper = BijdeHandjesScraper()
        listing_r = MagicMock(); listing_r.text = LISTING_HTML; listing_r.raise_for_status = MagicMock()
        detail_r = MagicMock(); detail_r.text = DETAIL_HTML; detail_r.raise_for_status = MagicMock()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=[listing_r, detail_r, detail_r]):
            jobs = scraper.fetch_jobs()
        assert len(jobs) == 2
        assert jobs[0]["title"] == "Pedagogisch medewerker peuters VE"
        assert jobs[0]["city"] == "Bennekom"

    def test_empty_on_error(self):
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=Exception("err")):
            assert BijdeHandjesScraper().fetch_jobs() == []


@pytest.mark.integration
class TestBijdeHandjesLive:
    def test_listing_bereikbaar(self):
        import requests
        assert requests.get(BijdeHandjesScraper.listing_url, timeout=15).status_code == 200
