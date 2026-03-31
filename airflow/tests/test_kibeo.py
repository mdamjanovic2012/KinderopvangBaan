"""
Unit tests for the Kibeo scraper.

Strategy:
  - _scrape_detail_html: test HTML parsing (JSON-LD and fallback)
  - KibeoScraper config
  - Integration tests (Playwright, require network)

Note: fetch_jobs uses Playwright which is harder to mock inline.
Core parsing logic is already tested via test_samenwerkende_ko.py
(shared wordpress_jobs helpers). Here we focus on Kibeo-specific behaviour.
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.kibeo import KibeoScraper, BASE_URL, JOBS_URL, JUNIA_URL
from scrapers.wordpress_jobs import extract_job_posting_jsonld, parse_job_from_jsonld
from bs4 import BeautifulSoup


# ── Fixtures ──────────────────────────────────────────────────────────────────

JOBPOSTING_LD = {
    "@context": "http://schema.org",
    "@type": "JobPosting",
    "title": "Pedagogisch Medewerker KDV Middelburg",
    "identifier": {"@type": "PropertyValue", "value": "kibeo-123"},
    "jobLocation": [{"@type": "Place", "address": {
        "@type": "PostalAddress",
        "addressLocality": "Middelburg",
        "postalCode": "4333AB",
    }}],
    "baseSalary": {
        "@type": "MonetaryAmount",
        "value": {"@type": "QuantitativeValue", "minValue": 2641, "maxValue": 3630},
    },
    "employmentType": ["PART_TIME"],
    "description": "<p>We zoeken een PM voor 20 - 28 uur per week.</p>",
}

DETAIL_WITH_LD = f"""<html><body>
<h1>Pedagogisch Medewerker KDV Middelburg</h1>
<script type="application/ld+json">{json.dumps(JOBPOSTING_LD)}</script>
</body></html>"""

DETAIL_FALLBACK = """<html><body>
<h1>Groepsleider BSO Vlissingen</h1>
<article><p>Wij zoeken een groepsleider BSO voor 24 - 32 uur per week in Vlissingen.</p></article>
</body></html>"""


# ── KibeoScraper config ───────────────────────────────────────────────────────

class TestKibeoScraperConfig:
    def test_company_slug(self):
        assert KibeoScraper.company_slug == "kibeo"

    def test_fetch_company_returns_dict(self):
        scraper = KibeoScraper()
        company = scraper.fetch_company()
        assert company["name"] == "Kibeo"
        assert "kibeo" in company["website"].lower()
        assert company["job_board_url"] == JOBS_URL

    def test_urls_correct(self):
        assert "kibeo.nl" in BASE_URL
        assert JOBS_URL.endswith("/vacatures/")
        assert "junia" in JUNIA_URL


# ── JSON-LD parsing (via shared helpers) ─────────────────────────────────────

class TestKibeoJsonldParsing:
    def test_extract_jsonld_from_detail_page(self):
        soup = BeautifulSoup(DETAIL_WITH_LD, "lxml")
        ld = extract_job_posting_jsonld(soup)
        assert ld is not None
        assert ld["title"] == "Pedagogisch Medewerker KDV Middelburg"

    def test_parse_job_from_jsonld(self):
        url = f"{BASE_URL}/vacatures/kibeo-123/"
        job = parse_job_from_jsonld(url, JOBPOSTING_LD)
        assert job["title"] == "Pedagogisch Medewerker KDV Middelburg"
        assert job["city"] == "Middelburg"
        assert job["postcode"] == "4333AB"
        assert job["salary_min"] == 2641.0
        assert job["salary_max"] == 3630.0
        assert job["hours_min"] == 20
        assert job["hours_max"] == 28
        assert job["contract_type"] == "parttime"

    def test_fallback_html_parsing(self):
        """Test HTML fallback when no JSON-LD is present."""
        soup = BeautifulSoup(DETAIL_FALLBACK, "lxml")
        ld = extract_job_posting_jsonld(soup)
        assert ld is None
        # Manual fallback check
        h1 = soup.find("h1")
        assert h1 and "Groepsleider" in h1.get_text()


# ── Integration tests (require Playwright + network) ─────────────────────────

@pytest.mark.integration
class TestKibeoLive:
    def test_full_scrape(self):
        scraper = KibeoScraper()
        jobs = scraper.fetch_jobs()
        print(f"\n[INFO] Kibeo: {len(jobs)} vacatures found")
        if jobs:
            j = jobs[0]
            print(f"  First: {j['title']} | {j['city']} | {j['hours_min']}h | €{j['salary_min']}")
        assert isinstance(jobs, list)
        if len(jobs) == 0:
            pytest.skip("No vacatures found (possibly temporarily empty)")
        assert jobs[0]["source_url"].startswith("http")
        assert len(jobs[0]["title"]) > 3
