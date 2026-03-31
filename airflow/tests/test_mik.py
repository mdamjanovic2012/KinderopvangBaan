"""Unit tests for MIK & PIW Groep scraper (WordPress, HTML fallback)."""
import sys, os, pytest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scrapers.mik import MIKScraper

LISTING_HTML = """<html><body>
<a href="/vacatures/pedagogisch-medewerker-flex">PM Flex</a>
<a href="/vacatures/locatiemanager">Locatiemanager</a>
<a href="/vacatures/">Alle vacatures</a>
</body></html>"""

DETAIL_HTML = """<html><body>
<h1>Pedagogisch Professional (Flex)</h1>
<main><p>Maastricht, Westelijke Mijnstreek</p><p>Salarisschaal 6 (€2.577 - €3.541)</p></main>
</body></html>"""

class TestMIKConfig:
    def test_company_slug(self): assert MIKScraper.company_slug == "mik"
    def test_listing_url(self): assert "mikenpiwgroep.nl" in MIKScraper.listing_url
    def test_company_name(self): assert "MIK" in MIKScraper.company_name

class TestMIKFetchJobs:
    def test_returns_jobs(self):
        scraper = MIKScraper()
        listing_r = MagicMock(); listing_r.text = LISTING_HTML; listing_r.raise_for_status = MagicMock()
        detail_r = MagicMock(); detail_r.text = DETAIL_HTML; detail_r.raise_for_status = MagicMock()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=[listing_r, detail_r, detail_r]):
            jobs = scraper.fetch_jobs()
        assert len(jobs) == 2
        assert "Pedagogisch" in jobs[0]["title"]

    def test_empty_on_error(self):
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=Exception("err")):
            assert MIKScraper().fetch_jobs() == []

@pytest.mark.integration
class TestMIKLive:
    def test_listing_bereikbaar(self):
        import requests
        assert requests.get(MIKScraper.listing_url, timeout=15).status_code == 200
