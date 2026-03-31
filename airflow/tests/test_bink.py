"""Unit tests for Bink scraper (WordPress, HTML fallback)."""
import json
import sys, os, pytest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scrapers.bink import BinkScraper
from scrapers.wordpress_jobs import _salary_val, extract_job_posting_jsonld
from bs4 import BeautifulSoup

LISTING_HTML = """<html><body>
<a href="/vacatures/pedagogisch-medewerker-kdv/">PM KDV</a>
<a href="/vacatures/groepsleider-bso/">Groepsleider BSO</a>
<a href="/vacatures/">Alle vacatures</a>
</body></html>"""

DETAIL_HTML = """<html><body>
<h1>Pedagogisch Medewerker KDV</h1>
<main><p>We zoeken een PM voor 24 - 32 uur per week in Utrecht.</p></main>
</body></html>"""


class TestWordPressJobsSalaryVal:
    """Tests for the _salary_val helper in wordpress_jobs.py."""
    def test_none_returns_none(self):
        assert _salary_val(None) is None

    def test_string_float(self):
        assert _salary_val("2641.50") == 2641.5

    def test_integer(self):
        assert _salary_val(2641) == 2641.0

    def test_non_numeric_string_returns_none(self):
        assert _salary_val("nvt") is None

    def test_invalid_type_returns_none(self):
        assert _salary_val([1, 2]) is None


class TestExtractJsonldControlChars:
    """Test JSON-LD parsing with invalid control characters (two-pass retry)."""
    def test_parses_json_with_control_chars(self):
        """JSON with literal control chars should be parsed on second attempt."""
        ld_data = {"@type": "JobPosting", "title": "PM KDV"}
        # Inject a literal newline (0x0a) inside the json string
        raw_json = json.dumps(ld_data).replace("PM KDV", "PM\x0bKDV")
        html = f'<html><body><script type="application/ld+json">{raw_json}</script></body></html>'
        soup = BeautifulSoup(html, "lxml")
        result = extract_job_posting_jsonld(soup)
        assert result is not None
        assert "PM" in result["title"]


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

    def test_detail_error_skips_job(self):
        """When detail page request fails, the job is skipped (not added)."""
        scraper = BinkScraper()
        listing_r = MagicMock(); listing_r.text = LISTING_HTML; listing_r.raise_for_status = MagicMock()
        # listing succeeds, detail fails
        with patch("scrapers.wordpress_jobs.requests.get",
                   side_effect=[listing_r, Exception("timeout"), Exception("timeout")]):
            jobs = scraper.fetch_jobs()
        assert jobs == []

    def test_detail_no_h1_skips_job(self):
        """Detail pages without h1 are skipped in HTML fallback."""
        scraper = BinkScraper()
        listing_r = MagicMock(); listing_r.text = LISTING_HTML; listing_r.raise_for_status = MagicMock()
        no_h1_r = MagicMock()
        no_h1_r.text = "<html><body><main><p>Pagina niet gevonden</p></main></body></html>"
        no_h1_r.raise_for_status = MagicMock()
        with patch("scrapers.wordpress_jobs.requests.get",
                   side_effect=[listing_r, no_h1_r, no_h1_r]):
            jobs = scraper.fetch_jobs()
        assert jobs == []


class TestBinkFetchCompany:
    def test_returns_dict_with_name(self):
        scraper = BinkScraper()
        resp = MagicMock()
        resp.text = '<html><head><meta name="description" content="Bink kinderopvang Amsterdam"></head><body></body></html>'
        resp.raise_for_status = MagicMock()
        with patch("scrapers.wordpress_jobs.requests.get", return_value=resp):
            company = scraper.fetch_company()
        assert "Bink" in company["name"]
        assert company["description"] == "Bink kinderopvang Amsterdam"

    def test_graceful_on_error(self):
        scraper = BinkScraper()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=Exception("SSL")):
            company = scraper.fetch_company()
        assert "Bink" in company["name"]
        assert company["logo_url"] == ""


@pytest.mark.integration
class TestBinkLive:
    def test_listing_bereikbaar(self):
        import requests
        assert requests.get(BinkScraper.listing_url, timeout=15).status_code == 200
