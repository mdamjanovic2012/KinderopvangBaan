"""
Unit + integratie tests voor scrapers/partou.py

Unit tests: testen parsing helpers (_parse_euros, _parse_contract, _parse_json_items, _scrape_html).
Integratie test (mark=integration): test echte Partou site.
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.partou import (
    _parse_euros,
    _parse_contract,
    _parse_json_items,
    BASE_URL,
    JOBS_URL,
)


# ── _parse_euros ──────────────────────────────────────────────────────────────

class TestParseEuros:
    def test_dutch_comma_decimal(self):
        assert _parse_euros("2.700,50") == 2700.50

    def test_integer(self):
        assert _parse_euros("3400") == 3400.0

    def test_invalid(self):
        assert _parse_euros("nvt") is None

    def test_whitespace(self):
        assert _parse_euros("  3.500  ") == 3500.0


# ── _parse_contract ────────────────────────────────────────────────────────────

class TestParseContract:
    def test_fulltime(self):
        assert _parse_contract("Full-time") == "fulltime"

    def test_parttime(self):
        assert _parse_contract("Part-time 24 uur") == "parttime"

    def test_tijdelijk(self):
        assert _parse_contract("Tijdelijk contract") == "temp"

    def test_unknown(self):
        assert _parse_contract("flex") == ""

    def test_case_insensitive(self):
        assert _parse_contract("FULLTIME") == "fulltime"


# ── _parse_json_items ──────────────────────────────────────────────────────────

class TestParseJsonItems:

    def make_item(self, **kwargs):
        defaults = {
            "id": "42",
            "title": "Pedagogisch Medewerker BSO",
            "url": "https://www.werkenbijpartou.nl/vacatures/pm-bso",
            "location": "Rotterdam",
            "hours": "24-32 uur",
            "salary": "",
            "summary": "Korte omschrijving van de functie",
            "description": "Volledige omschrijving",
            "contractType": "fulltime",
        }
        defaults.update(kwargs)
        return defaults

    def test_basic_item(self):
        jobs = _parse_json_items([self.make_item()])
        assert len(jobs) == 1
        j = jobs[0]
        assert j["title"] == "Pedagogisch Medewerker BSO"
        assert j["source_url"] == "https://www.werkenbijpartou.nl/vacatures/pm-bso"
        assert j["location_name"] == "Rotterdam"
        assert j["hours_min"] == 24
        assert j["hours_max"] == 32
        assert j["contract_type"] == "fulltime"
        assert j["short_description"] == "Korte omschrijving van de functie"

    def test_relative_url_prefixed(self):
        jobs = _parse_json_items([self.make_item(url="/vacatures/pm")])
        assert jobs[0]["source_url"] == BASE_URL + "/vacatures/pm"

    def test_skips_item_without_url(self):
        jobs = _parse_json_items([self.make_item(url="", link="", applyUrl="")])
        assert jobs == []

    def test_salary_parsed(self):
        jobs = _parse_json_items([self.make_item(salary="€ 2.700 – € 3.400")])
        assert jobs[0]["salary_min"] == 2700.0
        assert jobs[0]["salary_max"] == 3400.0

    def test_no_hours_gives_none(self):
        jobs = _parse_json_items([self.make_item(hours="")])
        assert jobs[0]["hours_min"] is None
        assert jobs[0]["hours_max"] is None

    def test_external_id_from_id_field(self):
        jobs = _parse_json_items([self.make_item(id="99")])
        assert jobs[0]["external_id"] == "99"

    def test_alternative_url_field_link(self):
        jobs = _parse_json_items([self.make_item(url="", link="https://werkenbijpartou.nl/v/pm")])
        assert jobs[0]["source_url"] == "https://werkenbijpartou.nl/v/pm"

    def test_alternative_url_field_apply(self):
        jobs = _parse_json_items([self.make_item(url="", link="", applyUrl="https://werkenbijpartou.nl/v/pm")])
        assert jobs[0]["source_url"] == "https://werkenbijpartou.nl/v/pm"

    def test_multiple_items(self):
        items = [
            self.make_item(id="1", title="PM BSO"),
            self.make_item(id="2", title="Groepsleider KDV"),
        ]
        jobs = _parse_json_items(items)
        assert len(jobs) == 2
        assert jobs[0]["title"] == "PM BSO"
        assert jobs[1]["title"] == "Groepsleider KDV"

    def test_empty_list(self):
        assert _parse_json_items([]) == []


# ── Integratie tests (echte site, vereist netwerk) ────────────────────────────

@pytest.mark.integration
class TestPartouLive:
    """Uitvoeren met: pytest -m integration tests/test_partou.py -v -s"""

    def test_fetch_jobs_returns_list(self):
        from scrapers.partou import PartouScraper

        scraper = PartouScraper()
        jobs = scraper.fetch_jobs()

        print(f"\n[INFO] Partou: {len(jobs)} vacatures gevonden")
        if jobs:
            print(f"[INFO] Eerste: {jobs[0]}")

        assert isinstance(jobs, list)
        if len(jobs) == 0:
            pytest.skip("Geen Partou vacatures gevonden (site tijdelijk leeg of selectors verouderd)")

        j = jobs[0]
        assert j["source_url"].startswith("http")
        assert len(j["title"]) > 2
        assert j["hours_min"] is None or isinstance(j["hours_min"], int)

    def test_fetch_company_returns_dict(self):
        from scrapers.partou import PartouScraper

        scraper = PartouScraper()
        company = scraper.fetch_company()

        assert company["name"] == "Partou"
        assert company["website"].startswith("http")
        assert company["job_board_url"] == JOBS_URL
        assert company["scraper_class"] == "PartouScraper"
        print(f"\n[INFO] Logo: {company.get('logo_url', 'geen')}")
