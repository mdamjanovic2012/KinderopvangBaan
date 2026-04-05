"""
Unit tests for Humankind scraper (Drupal + JSON-LD, AJAX paginated listing).
"""

import json
import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.humankind import HumankindScraper, _extract_urls_from_ajax, BASE_URL, JOBS_URL


# ── AJAX listing fixtures ──────────────────────────────────────────────────────

def make_ajax_response(urls: list[str], total: int = 10) -> list:
    """Simulate Drupal AJAX response with job URLs."""
    urls_html = "".join(f'<a href="{u}">' for u in urls)
    return [
        {"command": "insert", "data": f'<div>{total} resultaten{urls_html}</div>'},
    ]


AJAX_PAGE_0 = make_ajax_response(["/vacatures/1279245", "/vacatures/1284399"])
AJAX_PAGE_1 = make_ajax_response(["/vacatures/1280001"])
AJAX_EMPTY  = make_ajax_response([])

# ── Detail page fixtures ───────────────────────────────────────────────────────

JOBPOSTING_LD = {
    "@context": "http://schema.org",
    "@type": "JobPosting",
    "title": "Pedagogisch professional peutergroep in Rozenburg - 16 uur",
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
<h1>Pedagogisch professional peutergroep in Rozenburg - 16 uur</h1>
<script type="application/ld+json">{json.dumps(JOBPOSTING_LD)}</script>
</body></html>"""

DETAIL_HTML_TITLE_HOURS = f"""<html><body>
<h1>PM BSO Enschede - 24 uur per week</h1>
<script type="application/ld+json">{json.dumps({
    "@context": "http://schema.org",
    "@type": "JobPosting",
    "title": "PM BSO Enschede - 24 uur per week",
    "description": "<p>Functieomschrijving zonder expliciete uren.</p>",
    "jobLocation": [{"@type": "Place", "address": {
        "@type": "PostalAddress",
        "addressLocality": "Enschede",
        "postalCode": "7511AA",
    }}],
})}</script>
</body></html>"""


# ── _extract_urls_from_ajax ────────────────────────────────────────────────────

class TestExtractUrlsFromAjax:
    def test_extracts_relative_urls(self):
        data = make_ajax_response(["/vacatures/123", "/vacatures/456"])
        urls = _extract_urls_from_ajax(data)
        assert f"{BASE_URL}/vacatures/123" in urls
        assert f"{BASE_URL}/vacatures/456" in urls

    def test_deduplicates(self):
        data = make_ajax_response(["/vacatures/123", "/vacatures/123"])
        urls = _extract_urls_from_ajax(data)
        assert len(urls) == 1

    def test_empty_response(self):
        assert _extract_urls_from_ajax([]) == []

    def test_no_insert_command(self):
        data = [{"command": "settings", "data": {}}]
        assert _extract_urls_from_ajax(data) == []


# ── HumankindScraper._get_all_job_urls ────────────────────────────────────────

class TestHumankindPagination:
    def _make_resp(self, json_data):
        r = MagicMock()
        r.json = MagicMock(return_value=json_data)
        r.raise_for_status = MagicMock()
        return r

    def test_collects_jobs_from_multiple_pages(self):
        scraper = HumankindScraper()
        responses = [
            self._make_resp(AJAX_PAGE_0),
            self._make_resp(AJAX_PAGE_1),
            self._make_resp(AJAX_EMPTY),
        ]
        with patch("scrapers.humankind.requests.get", side_effect=responses):
            urls = scraper._get_all_job_urls()
        assert len(urls) == 3

    def test_stops_on_no_new_links(self):
        scraper = HumankindScraper()
        with patch("scrapers.humankind.requests.get",
                   return_value=self._make_resp(AJAX_EMPTY)) as mock:
            urls = scraper._get_all_job_urls()
        assert mock.call_count == 1
        assert urls == []

    def test_stops_on_error(self):
        scraper = HumankindScraper()
        with patch("scrapers.humankind.requests.get", side_effect=Exception("timeout")):
            urls = scraper._get_all_job_urls()
        assert urls == []


# ── HumankindScraper._scrape_job_page ─────────────────────────────────────────

class TestHumankindScrapeJobPage:
    def _mock_detail(self, html):
        r = MagicMock()
        r.text = html
        r.raise_for_status = MagicMock()
        return r

    def test_salary_from_jsonld(self):
        scraper = HumankindScraper()
        with patch("scrapers.humankind.requests.get", return_value=self._mock_detail(DETAIL_HTML)):
            job = scraper._scrape_job_page(f"{BASE_URL}/vacatures/1279245")
        assert job["salary_min"] == 2641.0
        assert job["salary_max"] == 3630.0

    def test_city_from_jsonld(self):
        scraper = HumankindScraper()
        with patch("scrapers.humankind.requests.get", return_value=self._mock_detail(DETAIL_HTML)):
            job = scraper._scrape_job_page(f"{BASE_URL}/vacatures/1279245")
        assert job["city"] == "Rozenburg"
        assert job["postcode"] == "3181GD"

    def test_hours_from_description(self):
        scraper = HumankindScraper()
        with patch("scrapers.humankind.requests.get", return_value=self._mock_detail(DETAIL_HTML)):
            job = scraper._scrape_job_page(f"{BASE_URL}/vacatures/1279245")
        assert job["hours_min"] == 16
        assert job["hours_max"] == 20

    def test_hours_fallback_from_title(self):
        """When description has no hours, fallback to title parsing."""
        scraper = HumankindScraper()
        with patch("scrapers.humankind.requests.get",
                   return_value=self._mock_detail(DETAIL_HTML_TITLE_HOURS)):
            job = scraper._scrape_job_page(f"{BASE_URL}/vacatures/1284399")
        assert job["hours_min"] == 24
        assert job["hours_max"] == 24

    def test_returns_none_on_error(self):
        scraper = HumankindScraper()
        with patch("scrapers.humankind.requests.get", side_effect=Exception("timeout")):
            assert scraper._scrape_job_page(f"{BASE_URL}/vacatures/test") is None


# ── Config ────────────────────────────────────────────────────────────────────

class TestHumankindConfig:
    def test_company_slug(self): assert HumankindScraper.company_slug == "humankind"
    def test_base_url(self): assert "werkenbijhumankind.nl" in BASE_URL
    def test_jobs_url(self): assert "/vacatures/" in JOBS_URL
    def test_company_name(self): assert "Humankind" in HumankindScraper.company_name


@pytest.mark.integration
class TestHumankindLive:
    def test_listing_bereikbaar(self):
        import requests
        resp = requests.get(JOBS_URL, timeout=15)
        assert resp.status_code == 200

    def test_ajax_returns_urls(self):
        scraper = HumankindScraper()
        urls = scraper._get_all_job_urls()
        print(f"\n[INFO] Humankind AJAX: {len(urls)} URLs found")
        assert len(urls) >= 10

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
