"""Unit tests for Dichtbij Kinderopvang scraper (WordPress, /vacature/ pattern)."""
import sys, os, pytest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scrapers.dichtbij import DichtbijScraper

LISTING_HTML = """<html><body>
<a href="/vacature/pedagogisch-professional-bso/">PP BSO</a>
<a href="/vacature/locatiemanager-geldermalsen/">LM Geldermalsen</a>
<a href="/vacatures/">Alle vacatures</a>
</body></html>"""

DETAIL_HTML = """<html><body>
<h1>Pedagogisch Professional BSO</h1>
<main><p>We zoeken een PP voor 20-28 uur per week in Geldermalsen.</p></main>
</body></html>"""


class TestDichtbijConfig:
    def test_company_slug(self): assert DichtbijScraper.company_slug == "dichtbij"
    def test_listing_url(self): assert "werkenbijdichtbij.nl" in DichtbijScraper.listing_url
    def test_job_url_contains(self): assert DichtbijScraper.job_url_contains == "/vacature/"


class TestDichtbijFetchJobs:
    def test_returns_jobs(self):
        scraper = DichtbijScraper()
        listing_r = MagicMock(); listing_r.text = LISTING_HTML; listing_r.raise_for_status = MagicMock()
        detail_r = MagicMock(); detail_r.text = DETAIL_HTML; detail_r.raise_for_status = MagicMock()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=[listing_r, detail_r, detail_r]):
            jobs = scraper.fetch_jobs()
        assert len(jobs) == 2

    def test_hours_extracted(self):
        scraper = DichtbijScraper()
        listing_r = MagicMock(); listing_r.text = LISTING_HTML; listing_r.raise_for_status = MagicMock()
        detail_r = MagicMock(); detail_r.text = DETAIL_HTML; detail_r.raise_for_status = MagicMock()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=[listing_r, detail_r, detail_r]):
            jobs = scraper.fetch_jobs()
        assert jobs[0]["hours_min"] == 20
        assert jobs[0]["hours_max"] == 28

    def test_empty_on_error(self):
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=Exception("err")):
            assert DichtbijScraper().fetch_jobs() == []


@pytest.mark.integration
class TestDichtbijLive:
    def test_listing_bereikbaar(self):
        import requests
        assert requests.get(DichtbijScraper.listing_url, timeout=15).status_code == 200
