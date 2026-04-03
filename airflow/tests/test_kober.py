"""
Unit tests for Kober scraper (WordPress, HTML fallback).
Core parsing tested via test_samenwerkende_ko.py.
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.kober import KoberScraper


LISTING_HTML = """<html><body>
<a href="/vacatures/pedagogisch-medewerker-zij-instroom/">PM zij-instroom</a>
<a href="/vacatures/stagiaire/">Stagiaire</a>
<a href="/vacatures/">Alle vacatures</a>
<a href="/over-kober/">Over Kober</a>
</body></html>"""

DETAIL_HTML = """<html><body>
<h1>Pedagogisch medewerker zij-instroom</h1>
<main>
  <p>0 - 36 uur | Breda en omgeving</p>
  <p>Is het tijd voor iets anders? Bij Kober kun je via het zij-instroomtraject
  snel gekwalificeerd aan de slag op de groep.</p>
</main>
</body></html>"""


class TestKoberConfig:
    def test_company_slug(self):
        assert KoberScraper.company_slug == "kober"

    def test_listing_url_correct(self):
        assert "werkenbijkober.nl" in KoberScraper.listing_url

    def test_company_name(self):
        assert "Kober" in KoberScraper.company_name


class TestKoberFetchJobs:
    def test_returns_jobs(self):
        scraper = KoberScraper()

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
        assert jobs[0]["title"] == "Pedagogisch medewerker zij-instroom"

    def test_hours_extracted_from_html(self):
        scraper = KoberScraper()

        listing_resp = MagicMock()
        listing_resp.text = LISTING_HTML
        listing_resp.raise_for_status = MagicMock()

        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.wordpress_jobs.requests.get",
                   side_effect=[listing_resp, detail_resp, detail_resp]):
            jobs = scraper.fetch_jobs()

        assert jobs[0]["hours_min"] == 0
        assert jobs[0]["hours_max"] == 36

    def test_returns_empty_on_error(self):
        scraper = KoberScraper()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=Exception("timeout")):
            jobs = scraper.fetch_jobs()
        assert jobs == []


@pytest.mark.integration
class TestKoberLive:
    def test_listing_bereikbaar(self):
        import requests
        resp = requests.get(KoberScraper.listing_url, timeout=15)
        assert resp.status_code == 200

    def test_full_scrape(self):
        scraper = KoberScraper()
        jobs = scraper.fetch_jobs()
        print(f"\n[INFO] Kober: {len(jobs)} vacatures found")
        if jobs:
            j = jobs[0]
            print(f"  First: {j['title']} | {j['city']} | {j['hours_min']}h")
        assert isinstance(jobs, list)
        if len(jobs) == 0:
            pytest.skip("No vacatures found")
        assert jobs[0]["source_url"].startswith("http")
