"""
Unit tests for KION scraper (Recruitee ATS API).
Tests RecruiteeAPIScraper base class logic.
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.kion import KIONScraper
from scrapers.recruitee_api import RecruiteeAPIScraper, _strip_html, _salary_val


MOCK_API_RESPONSE = {
    "offers": [
        {
            "title": "Pedagogisch Medewerker Flex",
            "city": "Nijmegen",
            "postal_code": "6544AK",
            "salary": {"min": "2641", "max": "3630", "period": "month", "currency": "EUR"},
            "min_hours_per_week": 16,
            "max_hours_per_week": 24,
            "description": "<p>We zoeken een PM flex voor 16-24 uur in Nijmegen.</p>",
            "careers_url": "https://werkenbijkion.nl/vacaturepagina/6001",
            "guid": "pm-flex-kion-001",
            "employment_type_code": "contract",
            "status": "published",
        },
        {
            "title": "Locatiemanager Utrecht",
            "city": "Utrecht",
            "postal_code": "3512AB",
            "salary": {"min": "3630", "max": "5000", "period": "month", "currency": "EUR"},
            "min_hours_per_week": 32,
            "max_hours_per_week": 36,
            "description": "<p>Locatiemanager gezocht voor 32-36 uur.</p>",
            "careers_url": "https://werkenbijkion.nl/vacaturepagina/6002",
            "guid": "lm-kion-002",
            "employment_type_code": "fulltime",
            "status": "published",
        },
        {
            "title": "Unpublished job",
            "city": "Amsterdam",
            "salary": {},
            "description": "",
            "careers_url": "",
            "guid": "draft-001",
            "employment_type_code": "",
            "status": "draft",  # Should be excluded
        },
    ]
}


class TestSalaryVal:
    def test_string_integer(self):
        assert _salary_val("2641") == 2641.0

    def test_string_float(self):
        assert _salary_val("2641.50") == 2641.5

    def test_none(self):
        assert _salary_val(None) is None

    def test_integer(self):
        assert _salary_val(2641) == 2641.0

    def test_non_numeric_string_returns_none(self):
        assert _salary_val("not-a-number") is None

    def test_invalid_type_returns_none(self):
        assert _salary_val([1, 2]) is None


class TestStripHtml:
    def test_strips_tags(self):
        result = _strip_html("<p>Hello <b>world</b></p>")
        assert "Hello" in result
        assert "<p>" not in result
        assert "<b>" not in result


class TestKIONConfig:
    def test_company_slug(self):
        assert KIONScraper.company_slug == "kion"

    def test_recruitee_id(self):
        assert KIONScraper.recruitee_id == 51130

    def test_company_name(self):
        assert "KION" in KIONScraper.company_name

    def test_website_url(self):
        assert "werkenbijkion.nl" in KIONScraper.website_url


class TestKIONFetchJobs:
    def test_returns_published_jobs_only(self):
        scraper = KIONScraper()
        api_resp = MagicMock()
        api_resp.json.return_value = MOCK_API_RESPONSE
        api_resp.raise_for_status = MagicMock()

        with patch("scrapers.recruitee_api.requests.get", return_value=api_resp):
            jobs = scraper.fetch_jobs()

        assert len(jobs) == 2  # draft excluded

    def test_title_and_city(self):
        scraper = KIONScraper()
        api_resp = MagicMock()
        api_resp.json.return_value = MOCK_API_RESPONSE
        api_resp.raise_for_status = MagicMock()

        with patch("scrapers.recruitee_api.requests.get", return_value=api_resp):
            jobs = scraper.fetch_jobs()

        assert jobs[0]["title"] == "Pedagogisch Medewerker Flex"
        assert jobs[0]["city"] == "Nijmegen"

    def test_salary_parsed(self):
        scraper = KIONScraper()
        api_resp = MagicMock()
        api_resp.json.return_value = MOCK_API_RESPONSE
        api_resp.raise_for_status = MagicMock()

        with patch("scrapers.recruitee_api.requests.get", return_value=api_resp):
            jobs = scraper.fetch_jobs()

        assert jobs[0]["salary_min"] == 2641.0
        assert jobs[0]["salary_max"] == 3630.0

    def test_hours_from_api(self):
        scraper = KIONScraper()
        api_resp = MagicMock()
        api_resp.json.return_value = MOCK_API_RESPONSE
        api_resp.raise_for_status = MagicMock()

        with patch("scrapers.recruitee_api.requests.get", return_value=api_resp):
            jobs = scraper.fetch_jobs()

        assert jobs[0]["hours_min"] == 16
        assert jobs[0]["hours_max"] == 24

    def test_postcode_parsed(self):
        scraper = KIONScraper()
        api_resp = MagicMock()
        api_resp.json.return_value = MOCK_API_RESPONSE
        api_resp.raise_for_status = MagicMock()

        with patch("scrapers.recruitee_api.requests.get", return_value=api_resp):
            jobs = scraper.fetch_jobs()

        assert jobs[0]["postcode"] == "6544AK"

    def test_skips_offer_with_empty_title(self):
        scraper = KIONScraper()
        api_resp = MagicMock()
        api_resp.json.return_value = {"offers": [
            {"title": "", "city": "Amsterdam", "status": "published",
             "careers_url": "https://test.nl/job/1", "guid": "g1",
             "salary": {}, "description": "", "employment_type_code": ""},
        ]}
        api_resp.raise_for_status = MagicMock()
        with patch("scrapers.recruitee_api.requests.get", return_value=api_resp):
            jobs = scraper.fetch_jobs()
        assert jobs == []

    def test_external_id_fallback_from_url(self):
        """When guid is empty, external_id falls back to URL slug."""
        scraper = KIONScraper()
        api_resp = MagicMock()
        api_resp.json.return_value = {"offers": [
            {"title": "PM Amsterdam", "city": "Amsterdam", "status": "published",
             "careers_url": "https://test.nl/vacature/pm-amsterdam",
             "guid": "", "id": "",
             "salary": {}, "description": "", "employment_type_code": ""},
        ]}
        api_resp.raise_for_status = MagicMock()
        with patch("scrapers.recruitee_api.requests.get", return_value=api_resp):
            jobs = scraper.fetch_jobs()
        assert len(jobs) == 1
        assert jobs[0]["external_id"] == "pm-amsterdam"

    def test_fetch_company_returns_dict(self):
        scraper = KIONScraper()
        website_resp = MagicMock()
        website_resp.text = '<html><head><meta name="description" content="KION kinderopvang"></head><body></body></html>'
        website_resp.raise_for_status = MagicMock()
        with patch("scrapers.recruitee_api.requests.get", return_value=website_resp):
            company = scraper.fetch_company()
        assert "KION" in company["name"]
        assert "werkenbijkion.nl" in company["website"]

    def test_fetch_company_graceful_on_error(self):
        scraper = KIONScraper()
        with patch("scrapers.recruitee_api.requests.get", side_effect=Exception("conn")):
            company = scraper.fetch_company()
        assert "KION" in company["name"]
        assert company["logo_url"] == ""

    def test_returns_empty_on_api_error(self):
        scraper = KIONScraper()
        with patch("scrapers.recruitee_api.requests.get", side_effect=Exception("timeout")):
            jobs = scraper.fetch_jobs()
        assert jobs == []


@pytest.mark.integration
class TestKIONLive:
    def test_full_scrape(self):
        scraper = KIONScraper()
        jobs = scraper.fetch_jobs()
        print(f"\n[INFO] KION: {len(jobs)} vacatures found")
        if jobs:
            j = jobs[0]
            print(f"  First: {j['title']} | {j['city']} | {j.get('hours_min')}h | €{j.get('salary_min')}")
        assert isinstance(jobs, list)
        if len(jobs) == 0:
            pytest.skip("No vacatures found")
        assert jobs[0]["source_url"].startswith("http")
