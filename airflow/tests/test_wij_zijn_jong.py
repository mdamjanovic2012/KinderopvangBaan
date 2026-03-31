"""
Unit tests for Wij zijn JONG scraper (WordPress, paginated, HTML fallback).
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.wij_zijn_jong import WijZijnJONGScraper, BASE_URL, JOBS_URL


LISTING_PAGE_1 = """<html><body>
<a href="/vacatures/pedagogisch-medewerker-bso-eindhoven/">PM BSO Eindhoven</a>
<a href="/vacatures/locatiemanager-tilburg/">Locatiemanager Tilburg</a>
<a href="/vacatures/">Alle vacatures</a>
<a href="/vacatures/page/2/">Volgende</a>
<a href="/vacatures/filter/werkgever:korein/">Korein</a>
</body></html>"""

LISTING_PAGE_2 = """<html><body>
<a href="/vacatures/pedagogisch-medewerker-kdv-breda/">PM KDV Breda</a>
<a href="/vacatures/">Alle vacatures</a>
</body></html>"""

LISTING_EMPTY = """<html><body>
<a href="/vacatures/">Alle vacatures</a>
</body></html>"""

DETAIL_HTML = """<html><body>
<h1>Pedagogisch Medewerker BSO Eindhoven</h1>
<main>
  <p>We zoeken een PM BSO voor 24-32 uur per week in Eindhoven.</p>
  <p>€ 2.641 - € 3.630 per maand</p>
</main>
</body></html>"""


class TestWijZijnJONGConfig:
    def test_company_slug(self):
        assert WijZijnJONGScraper.company_slug == "wij-zijn-jong"

    def test_listing_url(self):
        assert "werkenbijwijzijnjong.nl" in JOBS_URL

    def test_company_name(self):
        assert "JONG" in WijZijnJONGScraper.company_name


class TestWijZijnJONGPagination:
    def test_collects_from_multiple_pages(self):
        scraper = WijZijnJONGScraper()

        def make_resp(html, status=200):
            r = MagicMock()
            r.text = html
            r.status_code = status
            r.raise_for_status = MagicMock()
            return r

        responses = [make_resp(LISTING_PAGE_1), make_resp(LISTING_PAGE_2), make_resp(LISTING_EMPTY)]

        with patch("scrapers.wij_zijn_jong.requests.get", side_effect=responses):
            urls = scraper._get_all_job_urls()

        assert len(urls) == 3

    def test_stops_on_404(self):
        scraper = WijZijnJONGScraper()

        def make_resp(html, status=200):
            r = MagicMock()
            r.text = html
            r.status_code = status
            r.raise_for_status = MagicMock()
            return r

        responses = [make_resp(LISTING_PAGE_1), make_resp("", status=404)]

        with patch("scrapers.wij_zijn_jong.requests.get", side_effect=responses) as mock:
            urls = scraper._get_all_job_urls()

        assert len(urls) == 2  # Only page 1 links
        assert mock.call_count == 2

    def test_filters_pagination_and_filter_links(self):
        scraper = WijZijnJONGScraper()

        r = MagicMock()
        r.text = LISTING_PAGE_1
        r.status_code = 200
        r.raise_for_status = MagicMock()

        empty_r = MagicMock()
        empty_r.text = LISTING_EMPTY
        empty_r.status_code = 200
        empty_r.raise_for_status = MagicMock()

        with patch("scrapers.wij_zijn_jong.requests.get", side_effect=[r, empty_r]):
            urls = scraper._get_all_job_urls()

        # Should not include /page/2/ or /filter/ links
        for url in urls:
            assert "/page/" not in url
            assert "/filter/" not in url


class TestWijZijnJONGFetchJobs:
    def test_title_from_h1(self):
        scraper = WijZijnJONGScraper()
        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.wordpress_jobs.requests.get", return_value=detail_resp):
            job = scraper._scrape_job_page(f"{BASE_URL}/vacatures/pedagogisch-medewerker-bso-eindhoven/")

        assert job is not None
        assert "Pedagogisch" in job["title"]

    def test_hours_from_html(self):
        scraper = WijZijnJONGScraper()
        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.wordpress_jobs.requests.get", return_value=detail_resp):
            job = scraper._scrape_job_page(f"{BASE_URL}/vacatures/pedagogisch-medewerker-bso-eindhoven/")

        assert job["hours_min"] == 24
        assert job["hours_max"] == 32


@pytest.mark.integration
class TestWijZijnJONGLive:
    def test_listing_bereikbaar(self):
        import requests
        resp = requests.get(JOBS_URL, timeout=15)
        assert resp.status_code == 200

    def test_full_scrape(self):
        scraper = WijZijnJONGScraper()
        jobs = scraper.fetch_jobs()
        print(f"\n[INFO] Wij zijn JONG: {len(jobs)} vacatures found")
        if jobs:
            j = jobs[0]
            print(f"  First: {j['title']} | {j.get('city')} | {j.get('hours_min')}h")
        assert isinstance(jobs, list)
        if len(jobs) == 0:
            pytest.skip("No vacatures found")
        assert jobs[0]["source_url"].startswith("http")
        assert len(jobs) > 50  # Should be 100+
