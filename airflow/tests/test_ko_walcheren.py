"""Unit tests for KO Walcheren scraper (WordPress, protocol-relative URL handling)."""
import sys, os, pytest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scrapers.ko_walcheren import KOWalcherenScraper

# Mix of protocol-relative and regular URLs as seen on werkenbijkow.nl
LISTING_HTML = """<html><body>
<a href="//www.werkenbijkow.nl/vacatures/pedagogisch-medewerker-middelburg/">PM Middelburg</a>
<a href="//www.werkenbijkow.nl/vacatures/locatiemanager-vlissingen/">LM Vlissingen</a>
<a href="//www.werkenbijkow.nl/vacatures/">Alle vacatures</a>
<a href="https://www.werkenbijkow.nl/vacatures/groepsleider-bso-goes/">GL Goes</a>
</body></html>"""

DETAIL_HTML = """<html><body>
<h1>Pedagogisch Medewerker Middelburg</h1>
<main><p>We zoeken een PM voor 24-32 uur per week in Middelburg.</p></main>
</body></html>"""


class TestKOWalcherenConfig:
    def test_company_slug(self): assert KOWalcherenScraper.company_slug == "ko-walcheren"
    def test_listing_url(self): assert "werkenbijkow.nl" in KOWalcherenScraper.listing_url
    def test_job_url_contains(self): assert KOWalcherenScraper.job_url_contains == "/vacatures/"


class TestKOWalcherenGetAllJobUrls:
    def test_resolves_protocol_relative_urls(self):
        scraper = KOWalcherenScraper()
        listing_r = MagicMock(); listing_r.text = LISTING_HTML; listing_r.raise_for_status = MagicMock()
        with patch("scrapers.ko_walcheren.requests.get", return_value=listing_r):
            urls = scraper._get_all_job_urls()
        # All returned URLs must start with https://
        assert all(u.startswith("https://") for u in urls)
        # Listing page itself (/vacatures/ with no slug) is excluded
        assert all("/vacatures/" in u for u in urls)
        assert len(urls) == 3  # 2 protocol-relative + 1 absolute

    def test_returns_empty_on_error(self):
        with patch("scrapers.ko_walcheren.requests.get", side_effect=Exception("conn")):
            assert KOWalcherenScraper()._get_all_job_urls() == []


class TestKOWalcherenFetchJobs:
    JOB_URLS = [
        "https://www.werkenbijkow.nl/vacatures/pedagogisch-medewerker-middelburg/",
        "https://www.werkenbijkow.nl/vacatures/locatiemanager-vlissingen/",
    ]

    def test_returns_jobs(self):
        scraper = KOWalcherenScraper()
        detail_r = MagicMock(); detail_r.text = DETAIL_HTML; detail_r.raise_for_status = MagicMock()
        with patch.object(scraper, "_get_all_job_urls", return_value=self.JOB_URLS):
            with patch("scrapers.wordpress_jobs.requests.get", return_value=detail_r):
                jobs = scraper.fetch_jobs()
        assert len(jobs) == 2

    def test_hours_extracted(self):
        scraper = KOWalcherenScraper()
        detail_r = MagicMock(); detail_r.text = DETAIL_HTML; detail_r.raise_for_status = MagicMock()
        with patch.object(scraper, "_get_all_job_urls", return_value=self.JOB_URLS):
            with patch("scrapers.wordpress_jobs.requests.get", return_value=detail_r):
                jobs = scraper.fetch_jobs()
        assert jobs[0]["hours_min"] == 24
        assert jobs[0]["hours_max"] == 32


@pytest.mark.integration
class TestKOWalcherenLive:
    def test_listing_bereikbaar(self):
        import requests
        assert requests.get(KOWalcherenScraper.listing_url, timeout=15).status_code == 200
