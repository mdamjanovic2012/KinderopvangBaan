"""Unit tests for Rastergroep scraper (Recruitee API)."""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.rastergroep import RastergroepScraper

SAMPLE_API_RESPONSE = {
    "offers": [
        {
            "title": "Pedagogisch Medewerker",
            "status": "published",
            "city": "Amsterdam",
            "postal_code": "1012 AB",
            "salary": {"min": 2500, "max": 3200},
            "min_hours_per_week": 24,
            "max_hours_per_week": 32,
            "description": "<p>Wij zoeken een enthousiaste PM voor onze locatie in Amsterdam.</p>",
            "careers_url": "https://werkenbijrastergroep.recruitee.com/o/pedagogisch-medewerker",
            "guid": "rastergroep-pm-001",
            "employment_type_code": "parttime",
        },
        {
            "title": "Locatiemanager",
            "status": "published",
            "city": "Rotterdam",
            "postal_code": "3011 CD",
            "salary": {"min": 3500, "max": 4200},
            "min_hours_per_week": 36,
            "max_hours_per_week": 40,
            "description": "<p>Locatiemanager voor onze locatie in Rotterdam, 36-40 uur.</p>",
            "careers_url": "https://werkenbijrastergroep.recruitee.com/o/locatiemanager",
            "guid": "rastergroep-lm-002",
            "employment_type_code": "fulltime",
        },
        {
            "title": "Stagiaire",
            "status": "draft",  # should be excluded
            "city": "Utrecht",
            "postal_code": "",
            "salary": {},
            "min_hours_per_week": 16,
            "max_hours_per_week": 24,
            "description": "<p>Stage plek.</p>",
            "careers_url": "https://werkenbijrastergroep.recruitee.com/o/stagiaire",
            "guid": "rastergroep-st-003",
            "employment_type_code": "internship",
        },
    ]
}

EMPTY_RESPONSE = {"offers": []}


class TestRastergroepConfig:
    def test_company_slug(self):
        assert RastergroepScraper.company_slug == "rastergroep"

    def test_company_name(self):
        assert RastergroepScraper.company_name == "Rastergroep"

    def test_recruitee_id(self):
        assert RastergroepScraper.recruitee_id == 106368

    def test_website_url(self):
        assert RastergroepScraper.website_url.startswith("http")
        assert "rastergroep" in RastergroepScraper.website_url

    def test_job_board_url(self):
        assert "recruitee.com" in RastergroepScraper.job_board_url


class TestRastergroepFetchJobs:
    def _mock_api(self, data):
        resp = MagicMock()
        resp.json.return_value = data
        resp.raise_for_status = MagicMock()
        return resp

    def test_returns_only_published_jobs(self):
        with patch("scrapers.recruitee_api.requests.get",
                   return_value=self._mock_api(SAMPLE_API_RESPONSE)):
            jobs = RastergroepScraper().fetch_jobs()
        # draft job should be excluded
        assert len(jobs) == 2

    def test_titles_extracted(self):
        with patch("scrapers.recruitee_api.requests.get",
                   return_value=self._mock_api(SAMPLE_API_RESPONSE)):
            jobs = RastergroepScraper().fetch_jobs()
        titles = [j["title"] for j in jobs]
        assert "Pedagogisch Medewerker" in titles
        assert "Locatiemanager" in titles

    def test_city_extracted(self):
        with patch("scrapers.recruitee_api.requests.get",
                   return_value=self._mock_api(SAMPLE_API_RESPONSE)):
            jobs = RastergroepScraper().fetch_jobs()
        pm = next(j for j in jobs if "Pedagogisch" in j["title"])
        assert pm["city"] == "Amsterdam"

    def test_postcode_stripped(self):
        with patch("scrapers.recruitee_api.requests.get",
                   return_value=self._mock_api(SAMPLE_API_RESPONSE)):
            jobs = RastergroepScraper().fetch_jobs()
        pm = next(j for j in jobs if "Pedagogisch" in j["title"])
        assert pm["postcode"] == "1012AB"   # spaces stripped

    def test_salary_extracted(self):
        with patch("scrapers.recruitee_api.requests.get",
                   return_value=self._mock_api(SAMPLE_API_RESPONSE)):
            jobs = RastergroepScraper().fetch_jobs()
        pm = next(j for j in jobs if "Pedagogisch" in j["title"])
        assert pm["salary_min"] == 2500.0
        assert pm["salary_max"] == 3200.0

    def test_hours_extracted(self):
        with patch("scrapers.recruitee_api.requests.get",
                   return_value=self._mock_api(SAMPLE_API_RESPONSE)):
            jobs = RastergroepScraper().fetch_jobs()
        pm = next(j for j in jobs if "Pedagogisch" in j["title"])
        assert pm["hours_min"] == 24
        assert pm["hours_max"] == 32

    def test_contract_type_parttime(self):
        with patch("scrapers.recruitee_api.requests.get",
                   return_value=self._mock_api(SAMPLE_API_RESPONSE)):
            jobs = RastergroepScraper().fetch_jobs()
        pm = next(j for j in jobs if "Pedagogisch" in j["title"])
        assert pm["contract_type"] == "parttime"

    def test_contract_type_fulltime(self):
        with patch("scrapers.recruitee_api.requests.get",
                   return_value=self._mock_api(SAMPLE_API_RESPONSE)):
            jobs = RastergroepScraper().fetch_jobs()
        lm = next(j for j in jobs if "Locatiemanager" in j["title"])
        assert lm["contract_type"] == "fulltime"

    def test_external_id_from_guid(self):
        with patch("scrapers.recruitee_api.requests.get",
                   return_value=self._mock_api(SAMPLE_API_RESPONSE)):
            jobs = RastergroepScraper().fetch_jobs()
        pm = next(j for j in jobs if "Pedagogisch" in j["title"])
        assert pm["external_id"] == "rastergroep-pm-001"

    def test_source_url_set(self):
        with patch("scrapers.recruitee_api.requests.get",
                   return_value=self._mock_api(SAMPLE_API_RESPONSE)):
            jobs = RastergroepScraper().fetch_jobs()
        for job in jobs:
            assert job["source_url"].startswith("http")

    def test_location_name_has_postcode_and_city(self):
        with patch("scrapers.recruitee_api.requests.get",
                   return_value=self._mock_api(SAMPLE_API_RESPONSE)):
            jobs = RastergroepScraper().fetch_jobs()
        pm = next(j for j in jobs if "Pedagogisch" in j["title"])
        assert "1012AB" in pm["location_name"]
        assert "Amsterdam" in pm["location_name"]

    def test_empty_offers_returns_empty_list(self):
        with patch("scrapers.recruitee_api.requests.get",
                   return_value=self._mock_api(EMPTY_RESPONSE)):
            jobs = RastergroepScraper().fetch_jobs()
        assert jobs == []

    def test_api_error_returns_empty_list(self):
        with patch("scrapers.recruitee_api.requests.get",
                   side_effect=Exception("API unavailable")):
            jobs = RastergroepScraper().fetch_jobs()
        assert jobs == []

    def test_http_error_returns_empty_list(self):
        resp = MagicMock()
        resp.raise_for_status.side_effect = Exception("403 Forbidden")
        with patch("scrapers.recruitee_api.requests.get", return_value=resp):
            jobs = RastergroepScraper().fetch_jobs()
        assert jobs == []


class TestRastergroepFetchCompany:
    def test_returns_company_name(self):
        resp = MagicMock()
        resp.text = '<html><head><meta name="description" content="Rastergroep kinderopvang"></head><body></body></html>'
        resp.raise_for_status = MagicMock()
        with patch("scrapers.recruitee_api.requests.get", return_value=resp):
            company = RastergroepScraper().fetch_company()
        assert company["name"] == "Rastergroep"
        assert company["website"] == RastergroepScraper.website_url

    def test_graceful_on_error(self):
        with patch("scrapers.recruitee_api.requests.get", side_effect=Exception("conn")):
            company = RastergroepScraper().fetch_company()
        assert company["name"] == "Rastergroep"
        assert company["logo_url"] == ""


@pytest.mark.integration
class TestRastergroepLive:
    def test_api_reachable(self):
        import requests
        api_url = f"https://api.recruitee.com/c/{RastergroepScraper.recruitee_id}/careers/offers?lang=nl"
        resp = requests.get(api_url, timeout=15)
        assert resp.status_code == 200
        data = resp.json()
        assert "offers" in data

    def test_full_scrape(self):
        scraper = RastergroepScraper()
        jobs = scraper.fetch_jobs()
        print(f"\n[rastergroep] {len(jobs)} vacatures")
        assert isinstance(jobs, list)
        if jobs:
            assert jobs[0]["source_url"].startswith("http")
            assert jobs[0]["title"] != ""
