"""Unit tests for 2Samen scraper (WordPress, /vacature/ singular URL)."""
import sys, os, pytest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scrapers.twee_samen import TweeSamenScraper

LISTING_HTML = """<html><body>
<a href="/vacature/2aan2-pedagogisch-medewerker-bso/">PM BSO 2aan2</a>
<a href="/vacature/2ballonnen-pm-kdv/">PM KDV 2ballonnen</a>
<a href="/vacatures/">Alle vacatures</a>
</body></html>"""

DETAIL_HTML = """<html><body>
<h1>Pedagogisch Medewerker BSO</h1>
<main><p>We zoeken een PM BSO voor 24 - 32 uur per week in Utrecht.</p></main>
</body></html>"""

class TestTweeSamenConfig:
    def test_company_slug(self): assert TweeSamenScraper.company_slug == "2samen"
    def test_listing_url(self): assert "werkenbij2samen.nl" in TweeSamenScraper.listing_url
    def test_job_url_contains(self): assert TweeSamenScraper.job_url_contains == "/vacature/"

class TestTweeSamenFetchJobs:
    def test_returns_jobs(self):
        scraper = TweeSamenScraper()
        listing_r = MagicMock(); listing_r.text = LISTING_HTML; listing_r.raise_for_status = MagicMock()
        detail_r = MagicMock(); detail_r.text = DETAIL_HTML; detail_r.raise_for_status = MagicMock()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=[listing_r, detail_r, detail_r]):
            jobs = scraper.fetch_jobs()
        assert len(jobs) == 2
        assert "Pedagogisch" in jobs[0]["title"]

    def test_hours_from_description(self):
        scraper = TweeSamenScraper()
        listing_r = MagicMock(); listing_r.text = LISTING_HTML; listing_r.raise_for_status = MagicMock()
        detail_r = MagicMock(); detail_r.text = DETAIL_HTML; detail_r.raise_for_status = MagicMock()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=[listing_r, detail_r, detail_r]):
            jobs = scraper.fetch_jobs()
        assert jobs[0]["hours_min"] == 24; assert jobs[0]["hours_max"] == 32

    def test_empty_on_error(self):
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=Exception("err")):
            assert TweeSamenScraper().fetch_jobs() == []

@pytest.mark.integration
class TestTweeSamenLive:
    def test_listing_bereikbaar(self):
        import requests
        assert requests.get(TweeSamenScraper.listing_url, timeout=15).status_code == 200
