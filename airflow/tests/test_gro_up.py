"""
Unit tests voor Gro-up scraper (Nuxt SSR, sitemap-based).

Test strategie:
  - get_ko_job_urls: sitemap parsing + kinderopvang filtering
  - scrape_job_page: HTML parsing, uren/salaris/locatie extractie
  - GroUpScraper.fetch_jobs: volledig flow met gemockte requests
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.gro_up import (
    get_ko_job_urls,
    scrape_job_page,
    BASE_URL,
    SITEMAP_URL,
)
from scrapers.gro_up import GroUpScraper


# ── Fixtures ─────────────────────────────────────────────────────────────────

SITEMAP_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.werkenbijgro-up.nl/</loc></url>
  <url><loc>https://www.werkenbijgro-up.nl/kinderopvang/vacatures/</loc></url>
  <url><loc>https://www.werkenbijgro-up.nl/pedagogisch-medewerker-kdv-toverkunst-11</loc></url>
  <url><loc>https://www.werkenbijgro-up.nl/pedagogisch-medewerker-bso-de-blokkendoos-2</loc></url>
  <url><loc>https://www.werkenbijgro-up.nl/locatiemanager-amsterdam</loc></url>
  <url><loc>https://www.werkenbijgro-up.nl/kraamverzorgende-rotterdam-5</loc></url>
  <url><loc>https://www.werkenbijgro-up.nl/jongerenwerker-gouda-3</loc></url>
  <url><loc>https://www.werkenbijgro-up.nl/buurtverbinder-rotterdam-prins-alexander</loc></url>
  <url><loc>https://www.werkenbijgro-up.nl/artikelen/werken-in-de-kinderopvang</loc></url>
  <url><loc>https://www.werkenbijgro-up.nl/legal/privacy-statement</loc></url>
</urlset>"""

JOB_PAGE_HTML = """<html>
<head><title>Pedagogisch medewerker KDV Toverkunst - gro-up</title></head>
<body>
<main>
  <h1>Pedagogisch medewerker KDV Toverkunst</h1>
  <p>€2.641 tot €3.630 (Kinderopvang) • 28 - 32 uur • Marcel Duchampplein 130, 3059 RD Rotterdam</p>
  <div>Wij zoeken een enthousiaste pedagogisch medewerker voor onze locatie in Rotterdam.
  Je werkt met kinderen van 0 tot 4 jaar op ons kinderdagverblijf.</div>
</main>
</body></html>"""

JOB_PAGE_NO_HOURS = """<html><body><main>
  <h1>Locatiemanager Amsterdam</h1>
  <p>Marktconform salaris • 3042 BZ Amsterdam</p>
  <p>Je geeft leiding aan ons team van 15 medewerkers.</p>
</main></body></html>"""


# ── get_ko_job_urls ──────────────────────────────────────────────────────────

class TestGetKoJobUrls:
    def test_extracts_ko_jobs(self):
        urls = get_ko_job_urls(SITEMAP_SAMPLE)
        assert len(urls) == 3
        assert f"{BASE_URL}/pedagogisch-medewerker-kdv-toverkunst-11" in urls
        assert f"{BASE_URL}/pedagogisch-medewerker-bso-de-blokkendoos-2" in urls
        assert f"{BASE_URL}/locatiemanager-amsterdam" in urls

    def test_excludes_kraamzorg(self):
        urls = get_ko_job_urls(SITEMAP_SAMPLE)
        assert not any("kraamverzorgende" in u for u in urls)

    def test_excludes_jeugdhulp(self):
        urls = get_ko_job_urls(SITEMAP_SAMPLE)
        assert not any("jongerenwerker" in u for u in urls)

    def test_excludes_buurtwerk(self):
        urls = get_ko_job_urls(SITEMAP_SAMPLE)
        assert not any("buurtverbinder" in u for u in urls)

    def test_excludes_non_job_pages(self):
        urls = get_ko_job_urls(SITEMAP_SAMPLE)
        assert not any("/kinderopvang/vacatures/" in u for u in urls)
        assert not any("/artikelen/" in u for u in urls)
        assert not any("/legal/" in u for u in urls)

    def test_empty_sitemap(self):
        xml = """<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>"""
        assert get_ko_job_urls(xml) == []

    def test_broken_xml(self):
        assert get_ko_job_urls("NOT XML") == []


# ── scrape_job_page ──────────────────────────────────────────────────────────

class TestScrapeJobPage:
    def _mock_get(self, html):
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    def test_basic_fields(self):
        with patch("scrapers.gro_up.requests.get", return_value=self._mock_get(JOB_PAGE_HTML)):
            job = scrape_job_page(f"{BASE_URL}/pedagogisch-medewerker-kdv-toverkunst-11")
        assert job is not None
        assert job["title"] == "Pedagogisch medewerker KDV Toverkunst"
        assert job["source_url"] == f"{BASE_URL}/pedagogisch-medewerker-kdv-toverkunst-11"
        assert job["external_id"] == "pedagogisch-medewerker-kdv-toverkunst-11"

    def test_hours_extracted(self):
        with patch("scrapers.gro_up.requests.get", return_value=self._mock_get(JOB_PAGE_HTML)):
            job = scrape_job_page(f"{BASE_URL}/pm-kdv")
        assert job["hours_min"] == 28
        assert job["hours_max"] == 32

    def test_salary_extracted(self):
        with patch("scrapers.gro_up.requests.get", return_value=self._mock_get(JOB_PAGE_HTML)):
            job = scrape_job_page(f"{BASE_URL}/pm-kdv")
        assert job["salary_min"] == 2641.0
        assert job["salary_max"] == 3630.0

    def test_city_extracted(self):
        with patch("scrapers.gro_up.requests.get", return_value=self._mock_get(JOB_PAGE_HTML)):
            job = scrape_job_page(f"{BASE_URL}/pm-kdv")
        assert "Rotterdam" in job["city"]

    def test_postcode_extracted(self):
        with patch("scrapers.gro_up.requests.get", return_value=self._mock_get(JOB_PAGE_HTML)):
            job = scrape_job_page(f"{BASE_URL}/pm-kdv")
        assert job["postcode"] == "3059RD"

    def test_no_hours_gives_none(self):
        with patch("scrapers.gro_up.requests.get", return_value=self._mock_get(JOB_PAGE_NO_HOURS)):
            job = scrape_job_page(f"{BASE_URL}/locatiemanager-amsterdam")
        assert job["hours_min"] is None
        assert job["hours_max"] is None

    def test_returns_none_on_http_error(self):
        with patch("scrapers.gro_up.requests.get", side_effect=Exception("timeout")):
            job = scrape_job_page(f"{BASE_URL}/pm-kdv")
        assert job is None

    def test_description_max_5000(self):
        long_html = f"<html><body><main><h1>PM KDV</h1><p>{'x' * 10_000}</p></main></body></html>"
        with patch("scrapers.gro_up.requests.get", return_value=self._mock_get(long_html)):
            job = scrape_job_page(f"{BASE_URL}/pm-kdv")
        assert len(job["description"]) <= 5000


# ── GroUpScraper.fetch_jobs (gemockt) ────────────────────────────────────────

class TestGroUpScraperFetchJobs:
    def test_returns_jobs_from_sitemap(self):
        scraper = GroUpScraper()

        sitemap_resp = MagicMock()
        sitemap_resp.text = SITEMAP_SAMPLE
        sitemap_resp.raise_for_status = MagicMock()

        job_resp = MagicMock()
        job_resp.text = JOB_PAGE_HTML
        job_resp.raise_for_status = MagicMock()

        with patch("scrapers.gro_up.requests.get", side_effect=[sitemap_resp, job_resp, job_resp, job_resp]):
            jobs = scraper.fetch_jobs()

        assert len(jobs) == 3
        assert all(j["source_url"].startswith("http") for j in jobs)

    def test_returns_empty_on_sitemap_error(self):
        scraper = GroUpScraper()
        with patch("scrapers.gro_up.requests.get", side_effect=Exception("timeout")):
            jobs = scraper.fetch_jobs()
        assert jobs == []

    def test_company_slug(self):
        assert GroUpScraper.company_slug == "gro-up"


# ── Integratie tests ──────────────────────────────────────────────────────────

@pytest.mark.integration
class TestGroUpLive:
    def test_sitemap_bereikbaar(self):
        import requests
        resp = requests.get(SITEMAP_URL, timeout=15)
        assert resp.status_code == 200

    def test_ko_jobs_gevonden(self):
        import requests
        resp = requests.get(SITEMAP_URL, timeout=15)
        urls = get_ko_job_urls(resp.text)
        print(f"\n[INFO] Gro-up: {len(urls)} KO vacature-URLs in sitemap")
        assert len(urls) >= 5

    def test_volledige_scrape(self):
        scraper = GroUpScraper()
        jobs = scraper.fetch_jobs()
        print(f"\n[INFO] Gro-up: {len(jobs)} vacatures gescraped")
        if jobs:
            j = jobs[0]
            print(f"  Eerste: {j['title']} | {j['city']} | {j['hours_min']}-{j['hours_max']}u | €{j['salary_min']}-{j['salary_max']}")
        assert isinstance(jobs, list)
        if len(jobs) == 0:
            pytest.skip("Geen vacatures gevonden")
        assert jobs[0]["source_url"].startswith("http")
        assert len(jobs[0]["title"]) > 3
