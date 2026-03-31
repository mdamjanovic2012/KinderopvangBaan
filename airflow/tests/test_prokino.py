"""
Unit tests for Prokino scraper (AFAS OutSite, Playwright).
Tests card parsing and detail page enrichment logic.
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.prokino import (
    ProkinoScraper,
    _extract_cards_from_listing,
    _enrich_from_detail,
    BASE_URL,
)


# Simulated rendered HTML for a category listing page
LISTING_HTML = """<html><body>
<a class="vtlink linkhover_11 border_5" href="/kinderopvang/pedagogisch-medewerker-flex-nijkerk">
  <div class="back"></div>
  <div>
    <span class="text">Pedagogisch Medewerker flex</span>
    <span class="text">24,00</span>
    <span class="text">Nijkerk</span>
    <span class="text">open</span>
    <span class="text">30-04-2026</span>
  </div>
</a>
<a class="vtlink linkhover_11 border_5" href="/kinderopvang/pedagogisch-medewerker-dordrecht">
  <div class="back"></div>
  <div>
    <span class="text">Pedagogisch Medewerker</span>
    <span class="text">32,00</span>
    <span class="text">Dordrecht</span>
    <span class="text">vervuld</span>
    <span class="text">30-04-2026</span>
  </div>
</a>
<a class="vtlink linkhover_11 border_5" href="/kinderopvang/locatiemanager-veendam">
  <div class="back"></div>
  <div>
    <span class="text">Locatiemanager</span>
    <span class="text">32,00</span>
    <span class="text">Veendam</span>
    <span class="text">open</span>
    <span class="text">15-04-2026</span>
  </div>
</a>
</body></html>"""

DETAIL_HTML = """<html><body>
<h1>Pedagogisch Medewerker flex</h1>
<main>
  <h2>Dit ga je doen</h2>
  <p>Je werkt 16 tot 24 uur per week in Nijkerk.</p>
  <h2>Kenmerken vacature</h2>
  <p>CAO Kinderopvang: schaal 6 (€2.641 – €3.630 o.b.v. fulltime);</p>
</main>
</body></html>"""


class TestProkinoConfig:
    def test_company_slug(self):
        assert ProkinoScraper.company_slug == "prokino"

    def test_base_url(self):
        assert "prokino.nl" in BASE_URL


class TestExtractCardsFromListing:
    def test_extracts_open_vacancies(self):
        seen = set()
        jobs = _extract_cards_from_listing(LISTING_HTML, seen)
        # 2 open, 1 vervuld → 2 jobs
        assert len(jobs) == 2

    def test_skips_vervuld(self):
        seen = set()
        jobs = _extract_cards_from_listing(LISTING_HTML, seen)
        titles = [j["title"] for j in jobs]
        assert "Pedagogisch Medewerker" not in titles or all(
            j["city"] != "Dordrecht" for j in jobs
        )

    def test_title_extracted(self):
        seen = set()
        jobs = _extract_cards_from_listing(LISTING_HTML, seen)
        assert jobs[0]["title"] == "Pedagogisch Medewerker flex"

    def test_city_extracted(self):
        seen = set()
        jobs = _extract_cards_from_listing(LISTING_HTML, seen)
        assert jobs[0]["city"] == "Nijkerk"

    def test_hours_extracted(self):
        seen = set()
        jobs = _extract_cards_from_listing(LISTING_HTML, seen)
        assert jobs[0]["hours_min"] == 24
        assert jobs[0]["hours_max"] == 24

    def test_deduplication(self):
        seen = set()
        _extract_cards_from_listing(LISTING_HTML, seen)
        jobs2 = _extract_cards_from_listing(LISTING_HTML, seen)
        assert len(jobs2) == 0  # All already seen

    def test_source_url_is_absolute(self):
        seen = set()
        jobs = _extract_cards_from_listing(LISTING_HTML, seen)
        assert jobs[0]["source_url"].startswith("https://")


class TestEnrichFromDetail:
    def test_description_populated(self):
        job = {"description": "", "short_description": "", "salary_min": None,
               "salary_max": None, "hours_min": 24, "hours_max": 24}
        _enrich_from_detail(DETAIL_HTML, job)
        assert len(job["description"]) > 0
        assert "Nijkerk" in job["description"]

    def test_salary_parsed(self):
        job = {"description": "", "short_description": "", "salary_min": None,
               "salary_max": None, "hours_min": 24, "hours_max": 24}
        _enrich_from_detail(DETAIL_HTML, job)
        assert job["salary_min"] == 2641.0
        assert job["salary_max"] == 3630.0

    def test_hours_range_refined(self):
        job = {"description": "", "short_description": "", "salary_min": None,
               "salary_max": None, "hours_min": 24, "hours_max": 24}
        _enrich_from_detail(DETAIL_HTML, job)
        assert job["hours_min"] == 16
        assert job["hours_max"] == 24

    def test_empty_html_leaves_job_unchanged(self):
        job = {"description": "existing", "short_description": "", "salary_min": 1000.0,
               "salary_max": 2000.0, "hours_min": 20, "hours_max": 28}
        _enrich_from_detail("", job)
        assert job["salary_min"] == 1000.0


@pytest.mark.integration
class TestProkinoLive:
    def test_full_scrape(self):
        scraper = ProkinoScraper()
        jobs = scraper.fetch_jobs()
        print(f"\n[INFO] Prokino: {len(jobs)} vacatures found")
        if jobs:
            j = jobs[0]
            print(f"  First: {j['title']} | {j['city']} | {j.get('hours_min')}h | €{j.get('salary_min')}")
        assert isinstance(jobs, list)
        if len(jobs) == 0:
            pytest.skip("No vacatures found")
        assert jobs[0]["source_url"].startswith("http")
        assert len(jobs[0]["title"]) > 3
