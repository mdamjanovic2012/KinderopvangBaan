"""Unit tests for Bink scraper (WordPress, HTML fallback)."""
import sys, os, pytest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scrapers.bink import BinkScraper

LISTING_HTML = """<html><body>
<a href="/vacatures/pedagogisch-medewerker-kdv/">PM KDV</a>
<a href="/vacatures/groepsleider-bso/">Groepsleider BSO</a>
<a href="/vacatures/">Alle vacatures</a>
</body></html>"""

DETAIL_HTML = """<html><body>
<h1>Pedagogisch Medewerker KDV</h1>
<main><p>We zoeken een PM voor 24 - 32 uur per week in Utrecht.</p></main>
</body></html>"""


class TestBinkConfig:
    def test_company_slug(self): assert BinkScraper.company_slug == "bink"
    def test_listing_url(self): assert "werkenbijbink.nl" in BinkScraper.listing_url
    def test_job_url_contains(self): assert BinkScraper.job_url_contains == "/vacatures/"


class TestBinkFetchJobs:
    def test_returns_jobs(self):
        scraper = BinkScraper()
        listing_r = MagicMock(); listing_r.text = LISTING_HTML; listing_r.raise_for_status = MagicMock()
        detail_r = MagicMock(); detail_r.text = DETAIL_HTML; detail_r.raise_for_status = MagicMock()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=[listing_r, detail_r, detail_r]):
            jobs = scraper.fetch_jobs()
        assert len(jobs) == 2

    def test_hours_extracted(self):
        scraper = BinkScraper()
        listing_r = MagicMock(); listing_r.text = LISTING_HTML; listing_r.raise_for_status = MagicMock()
        detail_r = MagicMock(); detail_r.text = DETAIL_HTML; detail_r.raise_for_status = MagicMock()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=[listing_r, detail_r, detail_r]):
            jobs = scraper.fetch_jobs()
        assert jobs[0]["hours_min"] == 24
        assert jobs[0]["hours_max"] == 32

    def test_empty_on_error(self):
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=Exception("err")):
            assert BinkScraper().fetch_jobs() == []


@pytest.mark.integration
class TestBinkLive:
    def test_listing_bereikbaar(self):
        import requests
        assert requests.get(BinkScraper.listing_url, timeout=15).status_code == 200
