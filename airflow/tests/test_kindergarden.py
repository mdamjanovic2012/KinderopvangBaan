"""
Unit tests for Kindergarden scraper (custom CMS, Playwright listing + JSON-LD details).
"""

import json
import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.kindergarden import KindergardenScraper, BASE_URL, JOBS_URL

JOBPOSTING_LD = {
    "@context": "https://schema.org/",
    "@type": "JobPosting",
    "title": "Pedagogisch Professional Kinderopvang",
    "identifier": {"@type": "PropertyValue", "value": "pp-10047"},
    "jobLocation": [{"@type": "Place", "address": {
        "@type": "PostalAddress",
        "addressLocality": "Nieuw-Vennep",
        "postalCode": "2152GE",
    }}],
    "baseSalary": {
        "@type": "MonetaryAmount",
        "value": {"@type": "QuantitativeValue", "minValue": 2641, "maxValue": 3992},
    },
    "employmentType": ["PART_TIME"],
    "description": "<p>We zoeken een PP voor 33 uur per week in Nieuw-Vennep.</p>",
}

DETAIL_HTML = f"""<html><body>
<h1>Pedagogisch Professional</h1>
<script type="application/ld+json">{json.dumps(JOBPOSTING_LD)}</script>
</body></html>"""

RENDERED_LISTING = """<html><body>
<a href="/vacatures/pedagogisch-professional-10047">PP Helsinkilaan</a>
<a href="/vacatures/pedagogisch-professional-bso-10042">PP BSO</a>
<a href="/vacatures/">Alle vacatures</a>
</body></html>"""


class TestKindergardenConfig:
    def test_company_slug(self):
        assert KindergardenScraper.company_slug == "kindergarden"

    def test_base_url(self):
        assert "werkenbijkindergarden.nl" in BASE_URL

    def test_jobs_url(self):
        assert "/vacatures/" in JOBS_URL


class TestKindergardenFetchJobs:
    def test_parses_jsonld_from_detail(self):
        scraper = KindergardenScraper()

        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.kindergarden._get_job_urls_playwright",
                   return_value=[f"{BASE_URL}/vacatures/pedagogisch-professional-10047"]):
            with patch("scrapers.kindergarden.requests.get", return_value=detail_resp):
                jobs = scraper.fetch_jobs()

        assert len(jobs) == 1
        assert jobs[0]["title"] == "Pedagogisch Professional Kinderopvang"

    def test_city_from_jsonld(self):
        scraper = KindergardenScraper()
        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.kindergarden._get_job_urls_playwright",
                   return_value=[f"{BASE_URL}/vacatures/pedagogisch-professional-10047"]):
            with patch("scrapers.kindergarden.requests.get", return_value=detail_resp):
                jobs = scraper.fetch_jobs()

        assert jobs[0]["city"] == "Nieuw-Vennep"
        assert jobs[0]["salary_min"] == 2641.0

    def test_returns_empty_when_no_urls(self):
        scraper = KindergardenScraper()
        with patch("scrapers.kindergarden._get_job_urls_playwright", return_value=[]):
            jobs = scraper.fetch_jobs()
        assert jobs == []


@pytest.mark.integration
class TestKindergardenLive:
    def test_full_scrape(self):
        scraper = KindergardenScraper()
        jobs = scraper.fetch_jobs()
        print(f"\n[INFO] Kindergarden: {len(jobs)} vacatures found")
        if jobs:
            j = jobs[0]
            print(f"  First: {j['title']} | {j['city']} | €{j.get('salary_min')}")
        assert isinstance(jobs, list)
        if len(jobs) == 0:
            pytest.skip("No vacatures found")
        assert jobs[0]["source_url"].startswith("http")
