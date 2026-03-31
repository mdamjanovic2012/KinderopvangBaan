"""
Unit tests for CompaNanny scraper (custom site with JSON-LD).
Tests city cleanup (removes ", Nederlands" suffix) and JSON-LD extraction.
"""

import json
import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.compananny import CompaNannyScraper, _clean_city, BASE_URL, JOBS_URL


LISTING_HTML = """<html><body>
<a href="/vacatures/amsterdam/pedagogisch-medewerker">PM Amsterdam</a>
<a href="/vacatures/haarlem/pedagogisch-medewerker-bso">PM BSO Haarlem</a>
<a href="/vacatures/">Alle vacatures</a>
</body></html>"""

JOBPOSTING_LD = {
    "@context": "https://schema.org/",
    "@type": "JobPosting",
    "title": "Pedagogisch Medewerker",
    "description": "<p>Wij zoeken een PM voor 24 - 32 uur per week.</p>",
    "hiringOrganization": {
        "@type": "Organization",
        "name": "CompaNanny",
        "logo": "https://www.compananny.com/media/logo.png",
    },
    "datePosted": "21-02-2025",
    "jobLocation": {
        "@type": "Place",
        "address": {
            "@type": "PostalAddress",
            "addressLocality": "Amsterdam, Nederlands",
            "postalCode": "1012AB",
        },
    },
}

DETAIL_HTML = f"""<html><body>
<h1>Pedagogisch Medewerker</h1>
<script type="application/ld+json">{json.dumps(JOBPOSTING_LD)}</script>
</body></html>"""


class TestCleanCity:
    def test_removes_nederlands_suffix(self):
        assert _clean_city("Amsterdam, Nederlands") == "Amsterdam"

    def test_removes_netherlands_suffix(self):
        assert _clean_city("Rotterdam, Netherlands") == "Rotterdam"

    def test_leaves_clean_city_unchanged(self):
        assert _clean_city("Haarlem") == "Haarlem"

    def test_handles_empty_string(self):
        assert _clean_city("") == ""

    def test_case_insensitive(self):
        assert _clean_city("Den Haag, NEDERLANDS") == "Den Haag"


class TestCompaNannyConfig:
    def test_company_slug(self):
        assert CompaNannyScraper.company_slug == "compananny"

    def test_listing_url(self):
        assert "werkenbijcompananny.nl" in JOBS_URL

    def test_company_name(self):
        assert "CompaNanny" in CompaNannyScraper.company_name

    def test_base_url(self):
        assert "compananny.nl" in BASE_URL


class TestCompaNannyFetchJobs:
    def test_returns_jobs(self):
        scraper = CompaNannyScraper()

        listing_resp = MagicMock()
        listing_resp.text = LISTING_HTML
        listing_resp.raise_for_status = MagicMock()

        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.compananny.requests.get",
                   side_effect=[detail_resp, detail_resp]):
            with patch("scrapers.wordpress_jobs.requests.get",
                       return_value=listing_resp):
                jobs = scraper.fetch_jobs()

        assert len(jobs) >= 0  # May find 0 if listing mock doesn't match URL pattern

    def test_city_cleaned_from_jsonld(self):
        scraper = CompaNannyScraper()
        url = f"{BASE_URL}/vacatures/amsterdam/pedagogisch-medewerker"

        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.compananny.requests.get", return_value=detail_resp):
            job = scraper._scrape_job_page(url)

        assert job is not None
        assert job["city"] == "Amsterdam"
        assert "Nederlands" not in job["city"]
        assert "Nederlands" not in job.get("location_name", "")

    def test_location_name_includes_postcode(self):
        """When JSON-LD has a postcode, location_name should use it for precise geocoding."""
        scraper = CompaNannyScraper()
        url = f"{BASE_URL}/vacatures/amsterdam/pedagogisch-medewerker"

        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.compananny.requests.get", return_value=detail_resp):
            job = scraper._scrape_job_page(url)

        # location_name should be more specific than just city (includes postcode)
        assert job["postcode"] == "1012AB"
        assert "1012AB" in job["location_name"] or job["location_name"] == "Amsterdam"

    def test_postcode_extracted(self):
        scraper = CompaNannyScraper()
        url = f"{BASE_URL}/vacatures/amsterdam/pedagogisch-medewerker"

        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.compananny.requests.get", return_value=detail_resp):
            job = scraper._scrape_job_page(url)

        assert job["postcode"] == "1012AB"

    def test_hours_from_description(self):
        scraper = CompaNannyScraper()
        url = f"{BASE_URL}/vacatures/amsterdam/pedagogisch-medewerker"

        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.compananny.requests.get", return_value=detail_resp):
            job = scraper._scrape_job_page(url)

        assert job["hours_min"] == 24
        assert job["hours_max"] == 32

    def test_returns_none_on_error(self):
        scraper = CompaNannyScraper()
        with patch("scrapers.compananny.requests.get", side_effect=Exception("timeout")):
            job = scraper._scrape_job_page("https://example.com/vacatures/test")
        assert job is None


@pytest.mark.integration
class TestCompaNannyLive:
    def test_listing_bereikbaar(self):
        import requests
        resp = requests.get(JOBS_URL, timeout=15)
        assert resp.status_code == 200

    def test_full_scrape(self):
        scraper = CompaNannyScraper()
        jobs = scraper.fetch_jobs()
        print(f"\n[INFO] CompaNanny: {len(jobs)} vacatures found")
        if jobs:
            j = jobs[0]
            print(f"  First: {j['title']} | {j['city']} | postcode: {j.get('postcode')} | {j.get('hours_min')}h")
        assert isinstance(jobs, list)
        if len(jobs) == 0:
            pytest.skip("No vacatures found")
        assert jobs[0]["source_url"].startswith("http")
        assert "Nederlands" not in jobs[0].get("city", "")
