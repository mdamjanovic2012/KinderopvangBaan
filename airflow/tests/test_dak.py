"""
Unit tests for Dak Kindercentra scraper (WordPress, HTML fallback).
No JobPosting JSON-LD — uses HTML fallback parsing via WordPressJobsScraper.
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.dak import DakScraper


LISTING_HTML = """<html><body>
<a href="/vacatures/dak-dunkler-sport-bso-tso/">Sport BSO Dunkler</a>
<a href="/vacatures/dak-jfk-kdv/">KDV JFK</a>
<a href="/vacatures/">Alle vacatures</a>
</body></html>"""

DETAIL_HTML = """<html><body>
<h1>Pedagogisch medewerker Sport BSO/TSO</h1>
<main>
  <p>Dak Dunkler - BSO</p>
  <p>24 uur</p>
  <p>€ 2.641 - € 3.630 o.b.v. 36 uur</p>
  <p>Ben jij een enthousiaste pedagogisch medewerker die kinderen een geweldige middag wil bezorgen?</p>
</main>
</body></html>"""


class TestDakConfig:
    def test_company_slug(self):
        assert DakScraper.company_slug == "dak"

    def test_listing_url(self):
        assert "dakkindercentra.nl" in DakScraper.listing_url

    def test_company_name(self):
        assert "Dak" in DakScraper.company_name

    def test_extra_listing_urls(self):
        assert len(DakScraper.extra_listing_urls) >= 1
        assert any("servicebureau" in u for u in DakScraper.extra_listing_urls)


class TestDakFetchJobs:
    def test_returns_jobs(self):
        scraper = DakScraper()

        listing_resp = MagicMock()
        listing_resp.text = LISTING_HTML
        listing_resp.raise_for_status = MagicMock()

        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        # 1 listing page + 1 extra + 2 detail pages
        with patch("scrapers.wordpress_jobs.requests.get",
                   side_effect=[listing_resp, listing_resp, detail_resp, detail_resp]):
            jobs = scraper.fetch_jobs()

        assert len(jobs) == 2
        assert jobs[0]["title"] == "Pedagogisch medewerker Sport BSO/TSO"

    def test_hours_extracted_from_html(self):
        scraper = DakScraper()

        listing_resp = MagicMock()
        listing_resp.text = LISTING_HTML
        listing_resp.raise_for_status = MagicMock()

        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.wordpress_jobs.requests.get",
                   side_effect=[listing_resp, listing_resp, detail_resp, detail_resp]):
            jobs = scraper.fetch_jobs()

        assert jobs[0]["hours_min"] == 24
        assert jobs[0]["hours_max"] == 24

    def test_returns_empty_on_error(self):
        scraper = DakScraper()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=Exception("timeout")):
            jobs = scraper.fetch_jobs()
        assert jobs == []


@pytest.mark.integration
class TestDakLive:
    def test_listing_bereikbaar(self):
        import requests
        resp = requests.get(DakScraper.listing_url, timeout=15)
        assert resp.status_code == 200

    def test_full_scrape(self):
        scraper = DakScraper()
        jobs = scraper.fetch_jobs()
        print(f"\n[INFO] Dak: {len(jobs)} vacatures found")
        if jobs:
            j = jobs[0]
            print(f"  First: {j['title']} | {j.get('city')} | {j.get('hours_min')}h")
        assert isinstance(jobs, list)
        if len(jobs) == 0:
            pytest.skip("No vacatures found")
        assert jobs[0]["source_url"].startswith("http")
