"""Unit tests for Kids First scraper (WordPress, HTML fallback)."""
import sys, os, pytest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scrapers.kids_first import KidsFirstScraper

LISTING_HTML = """<html><body>
<a href="/vacatures/pedagogisch-medewerker-kdv-noordlaren/">PM KDV Noordlaren</a>
<a href="/vacatures/business-analist/">Business Analist</a>
<a href="/vacatures/">Alle vacatures</a>
</body></html>"""

DETAIL_HTML = """<html><body>
<h1>Pedagogisch Medewerker KDV Noordlaren</h1>
<main><p>We zoeken een PM voor 20 - 28 uur per week. Locatie: 9791AL Groningen.</p></main>
</body></html>"""

DETAIL_HTML_TITLE_HOURS = """<html><body>
<h1>PM BSO Almere - 24 uur</h1>
<main><p>Kom werken bij ons in 1234 AB Almere.</p></main>
</body></html>"""

class TestKidsFirstConfig:
    def test_company_slug(self): assert KidsFirstScraper.company_slug == "kids-first"
    def test_listing_url(self): assert "werkenbijkidsfirst.nl" in KidsFirstScraper.listing_url

class TestKidsFirstFetchJobs:
    def test_returns_jobs(self):
        scraper = KidsFirstScraper()
        listing_r = MagicMock(); listing_r.text = LISTING_HTML; listing_r.raise_for_status = MagicMock()
        detail_r = MagicMock(); detail_r.text = DETAIL_HTML; detail_r.raise_for_status = MagicMock()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=[listing_r, detail_r, detail_r]):
            jobs = scraper.fetch_jobs()
        assert len(jobs) == 2

    def test_hours_extracted(self):
        scraper = KidsFirstScraper()
        listing_r = MagicMock(); listing_r.text = LISTING_HTML; listing_r.raise_for_status = MagicMock()
        detail_r = MagicMock(); detail_r.text = DETAIL_HTML; detail_r.raise_for_status = MagicMock()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=[listing_r, detail_r, detail_r]):
            jobs = scraper.fetch_jobs()
        assert jobs[0]["hours_min"] == 20
        assert jobs[0]["hours_max"] == 28

    def test_city_from_postcode(self):
        """HTML fallback extracts city via postcode pattern."""
        scraper = KidsFirstScraper()
        listing_r = MagicMock(); listing_r.text = LISTING_HTML; listing_r.raise_for_status = MagicMock()
        detail_r = MagicMock(); detail_r.text = DETAIL_HTML; detail_r.raise_for_status = MagicMock()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=[listing_r, detail_r, detail_r]):
            jobs = scraper.fetch_jobs()
        assert jobs[0]["city"] == "Groningen"
        assert jobs[0]["postcode"] == "9791AL"

    def test_hours_fallback_from_title(self):
        """When description has no hours range, fall back to title."""
        scraper = KidsFirstScraper()
        listing_r = MagicMock(); listing_r.text = LISTING_HTML; listing_r.raise_for_status = MagicMock()
        detail_r = MagicMock(); detail_r.text = DETAIL_HTML_TITLE_HOURS; detail_r.raise_for_status = MagicMock()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=[listing_r, detail_r, detail_r]):
            jobs = scraper.fetch_jobs()
        assert jobs[0]["hours_min"] == 24
        assert jobs[0]["hours_max"] == 24

    def test_empty_on_error(self):
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=Exception("err")):
            assert KidsFirstScraper().fetch_jobs() == []

@pytest.mark.integration
class TestKidsFirstLive:
    @pytest.mark.xfail(reason="kidsfirst.nl vraća 403 Forbidden (bot protection)", strict=False)
    def test_listing_bereikbaar(self):
        import requests
        assert requests.get(KidsFirstScraper.listing_url, timeout=15).status_code == 200
