"""
Unit tests for Sinne Kinderopvang scraper (EasyCruit platform).
Tests EasyCruit base class parsing and Sinne config.
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.sinne import SinneScraper
from scrapers.easycruit import EasyCruitScraper, _parse_hours


LISTING_HTML = """<html><body>
<a href="/vacancy/3609929/199901?iso=nl">Pedagogisch professional DOV 0-2 jaar</a>
<a href="/vacancy/3608735/199929?iso=nl">Pedagogisch Medewerker BSO</a>
<a href="/over-sinne">Over Sinne</a>
</body></html>"""

DETAIL_HTML = """<html><body>
<h1>Pedagogisch professional DOV 0-2 jaar</h1>
<main>
  <div class="jd-location">Locatie: Leeuwarden</div>
  <p>27 uur per week (meer uren mogelijk in overleg)</p>
  <p>Ben jij een betrokken pedagogisch professional?</p>
</main>
</body></html>"""


class TestParseHours:
    def test_range(self):
        h_min, h_max = _parse_hours("24 tot 32 uur per week")
        assert h_min == 24
        assert h_max == 32

    def test_single(self):
        h_min, h_max = _parse_hours("27 uur per week")
        assert h_min == 27
        assert h_max == 27

    def test_no_match(self):
        h_min, h_max = _parse_hours("geen uren vermeld")
        assert h_min is None
        assert h_max is None


class TestSinneConfig:
    def test_company_slug(self):
        assert SinneScraper.company_slug == "sinne"

    def test_easycruit_url(self):
        assert "easycruit.com" in SinneScraper.easycruit_url

    def test_company_name(self):
        assert "Sinne" in SinneScraper.company_name

    def test_website_url(self):
        assert "sinnekinderopvang.nl" in SinneScraper.website_url


class TestSinneFetchJobs:
    def test_returns_jobs(self):
        scraper = SinneScraper()

        listing_resp = MagicMock()
        listing_resp.text = LISTING_HTML
        listing_resp.raise_for_status = MagicMock()

        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.easycruit.requests.get",
                   side_effect=[listing_resp, detail_resp, detail_resp]):
            jobs = scraper.fetch_jobs()

        assert len(jobs) == 2
        assert jobs[0]["title"] == "Pedagogisch professional DOV 0-2 jaar"

    def test_city_from_jd_location(self):
        scraper = SinneScraper()

        listing_resp = MagicMock()
        listing_resp.text = LISTING_HTML
        listing_resp.raise_for_status = MagicMock()

        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.easycruit.requests.get",
                   side_effect=[listing_resp, detail_resp, detail_resp]):
            jobs = scraper.fetch_jobs()

        assert jobs[0]["city"] == "Leeuwarden"

    def test_hours_from_text(self):
        scraper = SinneScraper()

        listing_resp = MagicMock()
        listing_resp.text = LISTING_HTML
        listing_resp.raise_for_status = MagicMock()

        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.easycruit.requests.get",
                   side_effect=[listing_resp, detail_resp, detail_resp]):
            jobs = scraper.fetch_jobs()

        assert jobs[0]["hours_min"] == 27
        assert jobs[0]["hours_max"] == 27

    def test_external_id_from_url(self):
        scraper = SinneScraper()
        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()
        with patch("scrapers.easycruit.requests.get", return_value=detail_resp):
            job = scraper._scrape_job_page("https://sinne.easycruit.com/vacancy/3609929/199901?iso=nl")
        assert job["external_id"] == "3609929"

    def test_returns_empty_on_listing_error(self):
        scraper = SinneScraper()
        with patch("scrapers.easycruit.requests.get", side_effect=Exception("timeout")):
            jobs = scraper.fetch_jobs()
        assert jobs == []

    def test_detail_error_returns_none(self):
        """Detail page fetch failure returns None from _scrape_job_page."""
        scraper = SinneScraper()
        with patch("scrapers.easycruit.requests.get", side_effect=Exception("conn")):
            result = scraper._scrape_job_page("https://sinne.easycruit.com/vacancy/123/1?iso=nl")
        assert result is None

    def test_detail_without_h1_returns_none(self):
        """If detail page has no <h1>, _scrape_job_page returns None."""
        scraper = SinneScraper()
        no_h1_resp = MagicMock()
        no_h1_resp.text = "<html><body><p>Geen titel</p></body></html>"
        no_h1_resp.raise_for_status = MagicMock()
        with patch("scrapers.easycruit.requests.get", return_value=no_h1_resp):
            result = scraper._scrape_job_page("https://sinne.easycruit.com/vacancy/123/1?iso=nl")
        assert result is None

    def test_fetch_company_returns_dict(self):
        scraper = SinneScraper()
        website_resp = MagicMock()
        website_resp.text = '<html><head><meta name="description" content="Sinne kinderopvang Friesland"></head><body></body></html>'
        website_resp.raise_for_status = MagicMock()
        with patch("scrapers.easycruit.requests.get", return_value=website_resp):
            company = scraper.fetch_company()
        assert company["name"] == "Sinne Kinderopvang"
        assert "sinnekinderopvang.nl" in company["website"]
        assert company["description"] == "Sinne kinderopvang Friesland"

    def test_fetch_company_graceful_on_error(self):
        scraper = SinneScraper()
        with patch("scrapers.easycruit.requests.get", side_effect=Exception("SSL")):
            company = scraper.fetch_company()
        assert company["name"] == "Sinne Kinderopvang"
        assert company["logo_url"] == ""


@pytest.mark.integration
class TestSinneLive:
    def test_listing_bereikbaar(self):
        import requests
        resp = requests.get(SinneScraper.easycruit_url, timeout=15)
        assert resp.status_code == 200

    def test_full_scrape(self):
        scraper = SinneScraper()
        jobs = scraper.fetch_jobs()
        print(f"\n[INFO] Sinne: {len(jobs)} vacatures found")
        if jobs:
            j = jobs[0]
            print(f"  First: {j['title']} | {j['city']} | {j.get('hours_min')}h")
        assert isinstance(jobs, list)
        if len(jobs) == 0:
            pytest.skip("No vacatures found")
        assert jobs[0]["source_url"].startswith("http")
