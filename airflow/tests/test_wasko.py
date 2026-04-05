"""Unit tests for Wasko Kinderopvang scraper (WordPress, /vacature/ URL pattern)."""
import sys, os, pytest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scrapers.wasko import WaskoScraper

LISTING_HTML = """<html><body>
<a href="/vacature/pedagogisch-medewerker-groep/">PM Groep</a>
<a href="/vacature/zzp-medewerker-bso/">ZZP BSO</a>
<a href="/onze-vacatures/">Alle vacatures</a>
</body></html>"""

DETAIL_HTML = """<html><body>
<h1>Pedagogisch Medewerker Groep</h1>
<main><p>Wij zoeken een PM voor 24-32 uur per week. Locatie: 1321KL Almere.</p></main>
</body></html>"""


class TestWaskoConfig:
    def test_company_slug(self): assert WaskoScraper.company_slug == "wasko"
    def test_listing_url(self): assert "wasko.nl" in WaskoScraper.listing_url
    def test_job_url_contains(self): assert WaskoScraper.job_url_contains == "/vacature/"


class TestWaskoFetchJobs:
    def test_returns_jobs(self):
        scraper = WaskoScraper()
        listing_r = MagicMock(); listing_r.text = LISTING_HTML; listing_r.raise_for_status = MagicMock()
        detail_r = MagicMock(); detail_r.text = DETAIL_HTML; detail_r.raise_for_status = MagicMock()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=[listing_r, detail_r, detail_r]):
            jobs = scraper.fetch_jobs()
        assert len(jobs) == 2

    def test_hours_extracted(self):
        scraper = WaskoScraper()
        listing_r = MagicMock(); listing_r.text = LISTING_HTML; listing_r.raise_for_status = MagicMock()
        detail_r = MagicMock(); detail_r.text = DETAIL_HTML; detail_r.raise_for_status = MagicMock()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=[listing_r, detail_r, detail_r]):
            jobs = scraper.fetch_jobs()
        assert jobs[0]["hours_min"] == 24
        assert jobs[0]["hours_max"] == 32

    def test_city_from_postcode(self):
        """HTML fallback extracts city from postcode pattern."""
        scraper = WaskoScraper()
        listing_r = MagicMock(); listing_r.text = LISTING_HTML; listing_r.raise_for_status = MagicMock()
        detail_r = MagicMock(); detail_r.text = DETAIL_HTML; detail_r.raise_for_status = MagicMock()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=[listing_r, detail_r, detail_r]):
            jobs = scraper.fetch_jobs()
        assert jobs[0]["city"] == "Almere"
        assert jobs[0]["postcode"] == "1321KL"

    def test_empty_on_error(self):
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=Exception("err")):
            assert WaskoScraper().fetch_jobs() == []


@pytest.mark.integration
class TestWaskoLive:
    def test_listing_bereikbaar(self):
        import requests
        assert requests.get(WaskoScraper.listing_url, timeout=15).status_code == 200
