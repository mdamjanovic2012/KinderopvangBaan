"""
Unit tests for Humankind scraper (custom site + JSON-LD, paginated listing).
"""

import json
import sys
import os
import pytest
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.humankind import HumankindScraper, BASE_URL, JOBS_URL


LISTING_PAGE_0 = """<html><body>
<a href="/vacatures/1279245">Pedagogisch professional peutergroep</a>
<a href="/vacatures/1284399">PM BSO Enschede</a>
<a href="/vacatures/">Alle vacatures</a>
<a href="?page=1">Volgende</a>
</body></html>"""

LISTING_PAGE_1 = """<html><body>
<a href="/vacatures/1280001">Locatiemanager Amsterdam</a>
<a href="/vacatures/">Alle vacatures</a>
</body></html>"""

LISTING_EMPTY = """<html><body>
<a href="/vacatures/">Alle vacatures</a>
</body></html>"""

JOBPOSTING_LD = {
    "@context": "http://schema.org",
    "@type": "JobPosting",
    "title": "Pedagogisch professional peutergroep in Rozenburg",
    "identifier": {"@type": "PropertyValue", "name": "Humankind", "value": "1279245-NL-1221"},
    "jobLocation": [{"@type": "Place", "address": {
        "@type": "PostalAddress",
        "addressLocality": "Rozenburg",
        "postalCode": "3181GD",
    }}],
    "baseSalary": {
        "@type": "MonetaryAmount",
        "value": {"@type": "QuantitativeValue", "minValue": 2641, "maxValue": 3630},
    },
    "description": "<p>We zoeken een PP voor 16 - 20 uur per week.</p>",
}

DETAIL_HTML = f"""<html><body>
<h1>Pedagogisch professional peutergroep in Rozenburg</h1>
<script type="application/ld+json">{json.dumps(JOBPOSTING_LD)}</script>
</body></html>"""


class TestHumankindConfig:
    def test_company_slug(self):
        assert HumankindScraper.company_slug == "humankind"

    def test_base_url(self):
        assert "werkenbijhumankind.nl" in BASE_URL

    def test_jobs_url(self):
        assert "/vacatures/" in JOBS_URL

    def test_company_name(self):
        assert "Humankind" in HumankindScraper.company_name


class TestHumankindPagination:
    def test_collects_jobs_from_multiple_pages(self):
        scraper = HumankindScraper()

        def make_resp(html):
            r = MagicMock()
            r.text = html
            r.raise_for_status = MagicMock()
            return r

        responses = [make_resp(h) for h in [LISTING_PAGE_0, LISTING_PAGE_1, LISTING_EMPTY]]

        with patch("scrapers.humankind.requests.get", side_effect=responses):
            urls = scraper._get_all_job_urls()

        assert len(urls) == 3

    def test_stops_on_no_new_links(self):
        scraper = HumankindScraper()
        empty_resp = MagicMock()
        empty_resp.text = LISTING_EMPTY
        empty_resp.raise_for_status = MagicMock()

        with patch("scrapers.humankind.requests.get", return_value=empty_resp) as mock:
            urls = scraper._get_all_job_urls()

        # Should stop after first empty page
        assert mock.call_count == 1
        assert urls == []


class TestHumankindFetchJobs:
    def test_salary_from_jsonld(self):
        scraper = HumankindScraper()
        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.wordpress_jobs.requests.get", return_value=detail_resp):
            job = scraper._scrape_job_page(f"{BASE_URL}/vacatures/1279245")

        assert job is not None
        assert job["salary_min"] == 2641.0
        assert job["salary_max"] == 3630.0

    def test_city_from_jsonld(self):
        scraper = HumankindScraper()
        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.wordpress_jobs.requests.get", return_value=detail_resp):
            job = scraper._scrape_job_page(f"{BASE_URL}/vacatures/1279245")

        assert job["city"] == "Rozenburg"
        assert job["postcode"] == "3181GD"

    def test_hours_from_description(self):
        scraper = HumankindScraper()
        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.wordpress_jobs.requests.get", return_value=detail_resp):
            job = scraper._scrape_job_page(f"{BASE_URL}/vacatures/1279245")

        assert job["hours_min"] == 16
        assert job["hours_max"] == 20


@pytest.mark.integration
class TestHumankindLive:
    def test_listing_bereikbaar(self):
        import requests
        resp = requests.get(JOBS_URL, timeout=15)
        assert resp.status_code == 200

    def test_full_scrape(self):
        scraper = HumankindScraper()
        jobs = scraper.fetch_jobs()
        print(f"\n[INFO] Humankind: {len(jobs)} vacatures found")
        if jobs:
            j = jobs[0]
            print(f"  First: {j['title']} | {j.get('city')} | {j.get('hours_min')}h | €{j.get('salary_min')}")
        assert isinstance(jobs, list)
        if len(jobs) == 0:
            pytest.skip("No vacatures found")
        assert jobs[0]["source_url"].startswith("http")
