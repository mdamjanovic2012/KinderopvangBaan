"""
Unit tests for TintelTuin scraper (WordPress + JSON-LD).
Core parsing is shared with test_samenwerkende_ko.py (WordPressJobsScraper).
"""

import json
import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.tinteltuin import TintelTuinScraper


LISTING_HTML = """<html><body>
<a href="/vacatures/pedagogisch-professional-bso-de-hoeksteen/">PP BSO Hoeksteen</a>
<a href="/vacatures/flex-pedagogisch-professional-ikc/">PP Flex IKC</a>
<a href="/vacatures/">Alle vacatures</a>
</body></html>"""

JOBPOSTING_LD = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    "title": "Pedagogisch Professional BSO",
    "identifier": {"@type": "PropertyValue", "name": "TintelTuin", "value": "tt-bso-001"},
    "jobLocation": [{"@type": "Place", "address": {
        "@type": "PostalAddress",
        "addressLocality": "Krommenie",
        "postalCode": "1521AB",
    }}],
    "baseSalary": {
        "@type": "MonetaryAmount",
        "currency": "EUR",
        "value": {"@type": "QuantitativeValue", "minValue": 2641, "maxValue": 3630},
    },
    "employmentType": "Parttime",
    "description": "<p>Wij zoeken een PP BSO voor 24 - 32 uur per week in Krommenie.</p>",
    "hiringOrganization": {
        "@type": "Organization",
        "name": "TintelTuin",
        "logo": "https://tinteltuin.nl/wp-content/uploads/2021/05/logo-tinteltuin.svg",
    },
}

DETAIL_HTML = f"""<html><body>
<h1>Pedagogisch Professional BSO</h1>
<script type="application/ld+json">{json.dumps(JOBPOSTING_LD)}</script>
</body></html>"""


class TestTintelTuinConfig:
    def test_company_slug(self):
        assert TintelTuinScraper.company_slug == "tinteltuin"

    def test_listing_url(self):
        assert "tinteltuin.nl" in TintelTuinScraper.listing_url

    def test_company_name(self):
        assert "TintelTuin" in TintelTuinScraper.company_name

    def test_job_url_contains(self):
        assert TintelTuinScraper.job_url_contains == "/vacatures/"


class TestTintelTuinFetchJobs:
    def test_returns_jobs(self):
        scraper = TintelTuinScraper()

        listing_resp = MagicMock()
        listing_resp.text = LISTING_HTML
        listing_resp.raise_for_status = MagicMock()

        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.wordpress_jobs.requests.get",
                   side_effect=[listing_resp, detail_resp, detail_resp]):
            jobs = scraper.fetch_jobs()

        assert len(jobs) == 2
        assert jobs[0]["title"] == "Pedagogisch Professional BSO"

    def test_city_extracted_from_jsonld(self):
        scraper = TintelTuinScraper()

        listing_resp = MagicMock()
        listing_resp.text = LISTING_HTML
        listing_resp.raise_for_status = MagicMock()

        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.wordpress_jobs.requests.get",
                   side_effect=[listing_resp, detail_resp, detail_resp]):
            jobs = scraper.fetch_jobs()

        assert jobs[0]["city"] == "Krommenie"
        assert jobs[0]["postcode"] == "1521AB"

    def test_salary_extracted_from_jsonld(self):
        scraper = TintelTuinScraper()

        listing_resp = MagicMock()
        listing_resp.text = LISTING_HTML
        listing_resp.raise_for_status = MagicMock()

        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.wordpress_jobs.requests.get",
                   side_effect=[listing_resp, detail_resp, detail_resp]):
            jobs = scraper.fetch_jobs()

        assert jobs[0]["salary_min"] == 2641.0
        assert jobs[0]["salary_max"] == 3630.0

    def test_hours_extracted_from_description(self):
        scraper = TintelTuinScraper()

        listing_resp = MagicMock()
        listing_resp.text = LISTING_HTML
        listing_resp.raise_for_status = MagicMock()

        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.wordpress_jobs.requests.get",
                   side_effect=[listing_resp, detail_resp, detail_resp]):
            jobs = scraper.fetch_jobs()

        assert jobs[0]["hours_min"] == 24
        assert jobs[0]["hours_max"] == 32

    def test_returns_empty_on_error(self):
        scraper = TintelTuinScraper()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=Exception("timeout")):
            jobs = scraper.fetch_jobs()
        assert jobs == []


@pytest.mark.integration
class TestTintelTuinLive:
    def test_listing_bereikbaar(self):
        import requests
        resp = requests.get(TintelTuinScraper.listing_url, timeout=15)
        assert resp.status_code == 200

    def test_full_scrape(self):
        scraper = TintelTuinScraper()
        jobs = scraper.fetch_jobs()
        print(f"\n[INFO] TintelTuin: {len(jobs)} vacatures found")
        if jobs:
            j = jobs[0]
            print(f"  First: {j['title']} | {j['city']} | {j.get('hours_min')}h | €{j.get('salary_min')}")
        assert isinstance(jobs, list)
        if len(jobs) == 0:
            pytest.skip("No vacatures found")
        assert jobs[0]["source_url"].startswith("http")
