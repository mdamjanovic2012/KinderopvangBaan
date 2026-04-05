"""
Unit tests for Kober scraper (WordPress + Beaver Builder).
Custom _scrape_job_page uses div.uren and div.locatie selectors.
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
<main class="fl-rich-text">
  <div class="uren"><span>16-24 uur</span></div>
  <div class="locatie"><span>Breda en omgeving</span></div>
  <div class="entry-content">
    <p>Is het tijd voor iets anders? Bij Kober kun je via het zij-instroomtraject
    snel gekwalificeerd aan de slag op de groep in Breda.</p>
  </div>
</main>
</body></html>"""

DETAIL_HTML_NO_DIVS = """<html><body>
<h1>Open sollicitatie</h1>
<main>
  <p>Wij zoeken medewerkers voor 32 uur per week in Tilburg.</p>
</main>
</body></html>"""


class TestKoberConfig:
    def test_company_slug(self):
        assert KoberScraper.company_slug == "kober"

    def test_listing_url_correct(self):
        assert "werkenbijkober.nl" in KoberScraper.listing_url

    def test_company_name(self):
        assert "Kober" in KoberScraper.company_name


class TestKoberScrapeJobPage:
    def _mock_resp(self, html):
        r = MagicMock()
        r.text = html
        r.raise_for_status = MagicMock()
        return r

    def test_title_extracted(self):
        scraper = KoberScraper()
        with patch("scrapers.kober.requests.get", return_value=self._mock_resp(DETAIL_HTML)):
            job = scraper._scrape_job_page("https://werkenbijkober.nl/vacatures/pm-zij-instroom/")
        assert job is not None
        assert job["title"] == "Pedagogisch medewerker zij-instroom"

    def test_hours_from_div_uren(self):
        scraper = KoberScraper()
        with patch("scrapers.kober.requests.get", return_value=self._mock_resp(DETAIL_HTML)):
            job = scraper._scrape_job_page("https://werkenbijkober.nl/vacatures/pm-zij-instroom/")
        assert job["hours_min"] == 16
        assert job["hours_max"] == 24

    def test_city_from_div_locatie_strips_omgeving(self):
        scraper = KoberScraper()
        with patch("scrapers.kober.requests.get", return_value=self._mock_resp(DETAIL_HTML)):
            job = scraper._scrape_job_page("https://werkenbijkober.nl/vacatures/pm-zij-instroom/")
        assert job["city"] == "Breda"

    def test_hours_fallback_from_description(self):
        """When div.uren is absent, hours are parsed from description text."""
        scraper = KoberScraper()
        with patch("scrapers.kober.requests.get", return_value=self._mock_resp(DETAIL_HTML_NO_DIVS)):
            job = scraper._scrape_job_page("https://werkenbijkober.nl/vacatures/open/")
        assert job["hours_min"] == 32
        assert job["hours_max"] == 32

    def test_external_id_from_url(self):
        scraper = KoberScraper()
        with patch("scrapers.kober.requests.get", return_value=self._mock_resp(DETAIL_HTML)):
            job = scraper._scrape_job_page("https://werkenbijkober.nl/vacatures/pm-zij-instroom/")
        assert job["external_id"] == "pm-zij-instroom"

    def test_returns_none_on_error(self):
        scraper = KoberScraper()
        with patch("scrapers.kober.requests.get", side_effect=Exception("timeout")):
            job = scraper._scrape_job_page("https://werkenbijkober.nl/vacatures/test/")
        assert job is None

    def test_returns_none_without_h1(self):
        scraper = KoberScraper()
        html = "<html><body><main><p>Geen titel</p></main></body></html>"
        with patch("scrapers.kober.requests.get", return_value=self._mock_resp(html)):
            job = scraper._scrape_job_page("https://werkenbijkober.nl/vacatures/test/")
        assert job is None


class TestKoberFetchJobs:
    def test_returns_empty_on_listing_error(self):
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
