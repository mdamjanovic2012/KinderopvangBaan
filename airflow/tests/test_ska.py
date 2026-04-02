"""Unit tests for SKA Kinderopvang scraper (WordPress, /vacature/ URL pattern)."""
import sys, os, pytest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scrapers.ska import SkaScraper

LISTING_HTML = """<html><body>
<a href="/vacature/pedagogisch-medewerker-leeuwarden/">PM Leeuwarden</a>
<a href="/vacature/locatiemanager-assen/">Locatiemanager Assen</a>
<a href="/">Home</a>
</body></html>"""

DETAIL_HTML = """<html><body>
<h1>Pedagogisch Medewerker Leeuwarden</h1>
<main><p>Wij zoeken een PM voor 20-28 uur in Leeuwarden.</p></main>
</body></html>"""


class TestSkaConfig:
    def test_company_slug(self): assert SkaScraper.company_slug == "ska"
    def test_listing_url(self): assert "werkenbijska.nl" in SkaScraper.listing_url
    def test_job_url_contains(self): assert SkaScraper.job_url_contains == "/vacature/"


class TestSkaFetchJobs:
    def test_returns_jobs(self):
        scraper = SkaScraper()
        listing_r = MagicMock(); listing_r.text = LISTING_HTML; listing_r.raise_for_status = MagicMock()
        detail_r = MagicMock(); detail_r.text = DETAIL_HTML; detail_r.raise_for_status = MagicMock()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=[listing_r, detail_r, detail_r]):
            jobs = scraper.fetch_jobs()
        assert len(jobs) == 2

    def test_hours_extracted(self):
        scraper = SkaScraper()
        listing_r = MagicMock(); listing_r.text = LISTING_HTML; listing_r.raise_for_status = MagicMock()
        detail_r = MagicMock(); detail_r.text = DETAIL_HTML; detail_r.raise_for_status = MagicMock()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=[listing_r, detail_r, detail_r]):
            jobs = scraper.fetch_jobs()
        assert jobs[0]["hours_min"] == 20
        assert jobs[0]["hours_max"] == 28

    def test_empty_on_error(self):
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=Exception("err")):
            assert SkaScraper().fetch_jobs() == []


@pytest.mark.integration
class TestSkaLive:
    def test_listing_bereikbaar(self):
        import requests
        assert requests.get(SkaScraper.listing_url, timeout=15).status_code == 200
