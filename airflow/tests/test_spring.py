"""
Unit tests voor Spring Kinderopvang scraper.

Test strategie:
  - get_spring_job_urls: extractie van job-URLs uit HTML
  - scrape_spring_job_page: titel, uren, stad, contract parsing
  - SpringKinderopvangScraper.fetch_jobs: flow met gemockte requests
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.spring_kinderopvang import (
    get_spring_job_urls,
    scrape_spring_job_page,
    _parse_euros,
    BASE_URL,
    JOBS_URL,
)
from scrapers.spring_kinderopvang import SpringKinderopvangScraper


# ── Fixtures ─────────────────────────────────────────────────────────────────

LISTING_HTML = """<html><body>
<div class="vacature-block" onclick="window.location = '/nl/vacatures/1538-pedagogisch-medewerker-bso-dn-bogerd-regio-deurne';"></div>
<div class="vacature-block" onclick="window.location = '/nl/vacatures/1535-pedagogisch-medewerker-bso-trudo-regio-helmond';"></div>
<div class="vacature-block" onclick="window.location = '/nl/vacatures/1538-pedagogisch-medewerker-bso-dn-bogerd-regio-deurne';"></div>
</body></html>"""

DETAIL_HTML_18H = """<html><body>
  <h1>Pedagogisch medewerker BSO d'n Bogerd regio Deurne</h1>
  <p>Vaste uren | 18 uur | Deurne</p>
  <div class="page-content-inner">
    <p>Kom jij met jouw ervaring en hart voor kinderen ons gezellige team versterken?
    Je werkt op onze BSO in Deurne met kinderen van 4 tot 12 jaar.</p>
  </div>
</body></html>"""

DETAIL_HTML_RANGE = """<html><body>
  <h1>Pedagogisch medewerker KDV Amsterdam</h1>
  <p>Part-time | 24 - 32 uur | Amsterdam</p>
  <div class="page-content-inner">
    <p>Wij zoeken een PM voor ons KDV in Amsterdam.</p>
  </div>
</body></html>"""

DETAIL_HTML_NO_HOURS = """<html><body>
  <h1>Locatiemanager Utrecht</h1>
  <p>Utrecht</p>
  <div class="page-content-inner">
    <p>Leidinggevende functie voor ervaren manager.</p>
  </div>
</body></html>"""


# ── _parse_euros ──────────────────────────────────────────────────────────────

class TestParseEuros:
    def test_dutch_format(self):
        assert _parse_euros("2.641") == 2641.0

    def test_invalid_returns_none(self):
        assert _parse_euros("nvt") is None


# ── get_spring_job_urls ───────────────────────────────────────────────────────

class TestGetSpringJobUrls:
    def test_extracts_urls(self):
        urls = get_spring_job_urls(LISTING_HTML)
        assert len(urls) == 2
        assert f"{BASE_URL}/nl/vacatures/1538-pedagogisch-medewerker-bso-dn-bogerd-regio-deurne" in urls
        assert f"{BASE_URL}/nl/vacatures/1535-pedagogisch-medewerker-bso-trudo-regio-helmond" in urls

    def test_deduplicates(self):
        urls = get_spring_job_urls(LISTING_HTML)
        assert len(urls) == len(set(urls))

    def test_empty_html_returns_empty(self):
        assert get_spring_job_urls("<html><body></body></html>") == []

    def test_absolute_urls(self):
        urls = get_spring_job_urls(LISTING_HTML)
        assert all(u.startswith("https://") for u in urls)


# ── scrape_spring_job_page ────────────────────────────────────────────────────

class TestScrapeSpringJobPage:
    def _mock_get(self, html):
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    def test_title_extracted(self):
        with patch("scrapers.spring_kinderopvang.requests.get", return_value=self._mock_get(DETAIL_HTML_18H)):
            job = scrape_spring_job_page(f"{BASE_URL}/nl/vacatures/1538-pm-bso")
        assert job["title"] == "Pedagogisch medewerker BSO d'n Bogerd regio Deurne"

    def test_single_hours(self):
        with patch("scrapers.spring_kinderopvang.requests.get", return_value=self._mock_get(DETAIL_HTML_18H)):
            job = scrape_spring_job_page(f"{BASE_URL}/nl/vacatures/1538-pm-bso")
        assert job["hours_min"] == 18
        assert job["hours_max"] == 18

    def test_hours_range(self):
        with patch("scrapers.spring_kinderopvang.requests.get", return_value=self._mock_get(DETAIL_HTML_RANGE)):
            job = scrape_spring_job_page(f"{BASE_URL}/nl/vacatures/1-pm-kdv")
        assert job["hours_min"] == 24
        assert job["hours_max"] == 32

    def test_city_extracted(self):
        with patch("scrapers.spring_kinderopvang.requests.get", return_value=self._mock_get(DETAIL_HTML_18H)):
            job = scrape_spring_job_page(f"{BASE_URL}/nl/vacatures/1538-pm-bso")
        assert job["city"] == "Deurne"

    def test_contract_type_vaste_uren(self):
        with patch("scrapers.spring_kinderopvang.requests.get", return_value=self._mock_get(DETAIL_HTML_18H)):
            job = scrape_spring_job_page(f"{BASE_URL}/nl/vacatures/1538-pm-bso")
        assert job["contract_type"] == "fulltime"

    def test_contract_type_parttime(self):
        with patch("scrapers.spring_kinderopvang.requests.get", return_value=self._mock_get(DETAIL_HTML_RANGE)):
            job = scrape_spring_job_page(f"{BASE_URL}/nl/vacatures/1-pm-kdv")
        assert job["contract_type"] == "parttime"

    def test_no_hours_gives_none(self):
        with patch("scrapers.spring_kinderopvang.requests.get", return_value=self._mock_get(DETAIL_HTML_NO_HOURS)):
            job = scrape_spring_job_page(f"{BASE_URL}/nl/vacatures/2-locatiemanager")
        assert job["hours_min"] is None
        assert job["hours_max"] is None

    def test_external_id_from_slug(self):
        with patch("scrapers.spring_kinderopvang.requests.get", return_value=self._mock_get(DETAIL_HTML_18H)):
            job = scrape_spring_job_page(f"{BASE_URL}/nl/vacatures/1538-pm-bso-deurne")
        assert job["external_id"] == "1538-pm-bso-deurne"

    def test_returns_none_on_error(self):
        with patch("scrapers.spring_kinderopvang.requests.get", side_effect=Exception("timeout")):
            job = scrape_spring_job_page(f"{BASE_URL}/nl/vacatures/1")
        assert job is None

    def test_returns_none_when_no_h1(self):
        no_h1_html = "<html><body><main><p>Pagina niet beschikbaar</p></main></body></html>"
        resp = MagicMock(); resp.text = no_h1_html; resp.raise_for_status = MagicMock()
        with patch("scrapers.spring_kinderopvang.requests.get", return_value=resp):
            job = scrape_spring_job_page(f"{BASE_URL}/nl/vacatures/1")
        assert job is None

    def test_salary_extracted(self):
        salary_html = """<html><body>
            <h1>PM BSO Amsterdam</h1>
            <p>Fulltime | 32 uur | Amsterdam | € 2.641 – € 3.630</p>
        </body></html>"""
        resp = MagicMock(); resp.text = salary_html; resp.raise_for_status = MagicMock()
        with patch("scrapers.spring_kinderopvang.requests.get", return_value=resp):
            job = scrape_spring_job_page(f"{BASE_URL}/nl/vacatures/3-pm-bso")
        assert job["salary_min"] == 2641.0
        assert job["salary_max"] == 3630.0

    def test_postcode_and_street_extracted(self):
        """Postcode + straatnaam in tekst → location_name bevat volledig adres."""
        html = """<html><body>
            <h1>PM KDV Rotterdam</h1>
            <p>Parttime | 24 uur | Rotterdam</p>
            <p>Werk je graag in Rotterdam? Kom werken op Blaakstraat 12, 3011TA Rotterdam!</p>
        </body></html>"""
        resp = MagicMock(); resp.text = html; resp.raise_for_status = MagicMock()
        with patch("scrapers.spring_kinderopvang.requests.get", return_value=resp):
            job = scrape_spring_job_page(f"{BASE_URL}/nl/vacatures/9-pm-kdv")
        assert job["postcode"] == "3011TA"
        assert "Blaakstraat" in job["location_name"]
        assert "12" in job["location_name"]

    def test_postcode_without_street_gives_postcode_city(self):
        """Postcode zonder straatnaam → location_name = postcode + stad."""
        html = """<html><body>
            <h1>BSO Groningen</h1>
            <p>Parttime | 20 uur | Groningen</p>
            <p>Wij zijn gevestigd in 9712AB Groningen.</p>
        </body></html>"""
        resp = MagicMock(); resp.text = html; resp.raise_for_status = MagicMock()
        with patch("scrapers.spring_kinderopvang.requests.get", return_value=resp):
            job = scrape_spring_job_page(f"{BASE_URL}/nl/vacatures/10-bso")
        assert job["postcode"] == "9712AB"
        assert "9712AB" in job["location_name"]

    def test_no_postcode_location_name_falls_back_to_city(self):
        """Geen postcode → location_name = stad."""
        html = """<html><body>
            <h1>BSO Utrecht</h1>
            <p>Parttime | 24 uur | Utrecht</p>
            <p>Leuke functie in Utrecht centrum.</p>
        </body></html>"""
        resp = MagicMock(); resp.text = html; resp.raise_for_status = MagicMock()
        with patch("scrapers.spring_kinderopvang.requests.get", return_value=resp):
            job = scrape_spring_job_page(f"{BASE_URL}/nl/vacatures/11-bso")
        assert job["location_name"] == "Utrecht"
        assert job["postcode"] == ""


# ── SpringKinderopvangScraper.fetch_jobs (gemockt) ────────────────────────────

class TestSpringScraperFetchJobs:
    def test_returns_jobs(self):
        scraper = SpringKinderopvangScraper()
        listing_resp = MagicMock()
        listing_resp.text = LISTING_HTML
        listing_resp.raise_for_status = MagicMock()

        detail_resp = MagicMock()
        detail_resp.text = DETAIL_HTML_18H
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.spring_kinderopvang.requests.get",
                   side_effect=[listing_resp, detail_resp, detail_resp]):
            jobs = scraper.fetch_jobs()

        assert len(jobs) == 2
        assert all(j["source_url"].startswith("http") for j in jobs)

    def test_returns_empty_on_error(self):
        scraper = SpringKinderopvangScraper()
        with patch("scrapers.spring_kinderopvang.requests.get", side_effect=Exception("timeout")):
            jobs = scraper.fetch_jobs()
        assert jobs == []

    def test_company_slug(self):
        assert SpringKinderopvangScraper.company_slug == "spring"


class TestSpringFetchCompany:
    def test_returns_dict_with_name(self):
        scraper = SpringKinderopvangScraper()
        resp = MagicMock()
        resp.text = '<html><head><meta name="description" content="Spring Kinderopvang Brabant"></head><body></body></html>'
        resp.raise_for_status = MagicMock()
        with patch("scrapers.spring_kinderopvang.requests.get", return_value=resp):
            company = scraper.fetch_company()
        assert company["name"] == "Spring Kinderopvang"
        assert company["description"] == "Spring Kinderopvang Brabant"

    def test_graceful_on_error(self):
        scraper = SpringKinderopvangScraper()
        with patch("scrapers.spring_kinderopvang.requests.get", side_effect=Exception("SSL")):
            company = scraper.fetch_company()
        assert company["name"] == "Spring Kinderopvang"
        assert company["logo_url"] == ""


# ── Integratie tests ──────────────────────────────────────────────────────────

@pytest.mark.integration
class TestSpringLive:
    def test_vacaturelijst_bereikbaar(self):
        import requests
        resp = requests.get(JOBS_URL, timeout=15)
        assert resp.status_code == 200

    def test_job_urls_gevonden(self):
        import requests
        resp = requests.get(JOBS_URL, timeout=15)
        urls = get_spring_job_urls(resp.text)
        print(f"\n[INFO] Spring: {len(urls)} vacature-URLs gevonden")
        assert len(urls) >= 3

    def test_volledige_scrape(self):
        scraper = SpringKinderopvangScraper()
        jobs = scraper.fetch_jobs()
        print(f"\n[INFO] Spring: {len(jobs)} vacatures gescraped")
        if jobs:
            j = jobs[0]
            print(f"  Eerste: {j['title']} | {j['city']} | {j['hours_min']}u")
        assert isinstance(jobs, list)
        if len(jobs) == 0:
            pytest.skip("Geen vacatures gevonden")
        assert jobs[0]["source_url"].startswith("http")
        assert len(jobs[0]["title"]) > 3
