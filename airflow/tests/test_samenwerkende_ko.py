"""
Unit tests voor Samenwerkende Kinderopvang scraper (WordPress + JSON-LD).

Test strategie:
  - extract_job_posting_jsonld: JSON-LD extractie uit HTML
  - parse_job_from_jsonld: schema.org → job dict conversie
  - get_job_links_from_listing: job-URL extractie uit listingpagina
  - SamenwerkendeKOScraper: configuratie + fetch_jobs flow
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.wordpress_jobs import (
    extract_job_posting_jsonld,
    parse_job_from_jsonld,
    get_job_links_from_listing,
    _parse_hours,
    _strip_html,
)
from scrapers.samenwerkende_ko import SamenwerkendeKOScraper
from bs4 import BeautifulSoup


# ── Fixtures ─────────────────────────────────────────────────────────────────

JOBPOSTING_JSONLD = {
    "@context": "http://schema.org",
    "@type": "JobPosting",
    "datePosted": "2026-02-10",
    "identifier": {"@type": "PropertyValue", "name": "SK", "value": "1265621-NL-1044"},
    "title": "Pedagogisch Professional KDV (Ede)",
    "jobLocation": [
        {"@type": "Place", "address": {
            "@type": "PostalAddress",
            "addressLocality": "Ede",
            "postalCode": "6717LM",
        }}
    ],
    "baseSalary": {
        "@type": "MonetaryAmount",
        "currency": "EUR",
        "value": {"@type": "QuantitativeValue", "minValue": 2641, "maxValue": 3630, "unitText": "MONTH"},
    },
    "employmentType": ["PART_TIME"],
    "description": "<p>Wij zoeken een PP KDV voor 24 - 32 uur per week in Ede.</p>",
}

PAGE_WITH_JSONLD = f"""<html><head></head><body>
<h1>Pedagogisch Professional KDV (Ede)</h1>
<script type="application/ld+json">{json.dumps(JOBPOSTING_JSONLD)}</script>
</body></html>"""

PAGE_WITHOUT_JSONLD = """<html><body>
<h1>Locatiemanager Amsterdam</h1>
<main><p>Wij zoeken een locatiemanager voor 32 - 40 uur per week.</p></main>
</body></html>"""

PAGE_WITH_GRAPH_JSONLD = f"""<html><body>
<script type="application/ld+json">{{"@graph": [{json.dumps(JOBPOSTING_JSONLD)}]}}</script>
</body></html>"""

LISTING_HTML = """<html><body>
<a href="/vacatures/pedagogisch-professional-kdv-ede-1265621/">PP KDV Ede</a>
<a href="/vacatures/locatiemanager-amsterdam-1270956/">Locatiemanager</a>
<a href="/vacatures/">Alle vacatures</a>
<a href="/over-ons/">Over ons</a>
<a href="https://example.com/vacatures/externe-job-1/">Extern</a>
</body></html>"""


# ── _parse_hours ─────────────────────────────────────────────────────────────

class TestParseHours:
    def test_range(self):
        assert _parse_hours("24 - 32 uur per week") == (24, 32)

    def test_single(self):
        assert _parse_hours("18 uur") == (18, 18)

    def test_no_hours(self):
        assert _parse_hours("Marktconform salaris") == (None, None)

    def test_with_en_dash(self):
        assert _parse_hours("24–32 uur") == (24, 32)


# ── extract_job_posting_jsonld ────────────────────────────────────────────────

class TestExtractJobPostingJsonld:
    def test_extracts_jobposting(self):
        soup = BeautifulSoup(PAGE_WITH_JSONLD, "lxml")
        data = extract_job_posting_jsonld(soup)
        assert data is not None
        assert data["@type"] == "JobPosting"
        assert data["title"] == "Pedagogisch Professional KDV (Ede)"

    def test_extracts_from_graph(self):
        soup = BeautifulSoup(PAGE_WITH_GRAPH_JSONLD, "lxml")
        data = extract_job_posting_jsonld(soup)
        assert data is not None
        assert data["title"] == "Pedagogisch Professional KDV (Ede)"

    def test_returns_none_without_jsonld(self):
        soup = BeautifulSoup("<html><body><h1>Test</h1></body></html>", "lxml")
        data = extract_job_posting_jsonld(soup)
        assert data is None

    def test_returns_none_for_non_jobposting(self):
        other_ld = '{"@type": "Organization", "name": "Test"}'
        soup = BeautifulSoup(f'<html><body><script type="application/ld+json">{other_ld}</script></body></html>', "lxml")
        assert extract_job_posting_jsonld(soup) is None


# ── parse_job_from_jsonld ─────────────────────────────────────────────────────

class TestParseJobFromJsonld:
    def test_title_extracted(self):
        job = parse_job_from_jsonld("https://example.com/vacatures/1", JOBPOSTING_JSONLD)
        assert job["title"] == "Pedagogisch Professional KDV (Ede)"

    def test_city_extracted(self):
        job = parse_job_from_jsonld("https://example.com/vacatures/1", JOBPOSTING_JSONLD)
        assert job["city"] == "Ede"

    def test_postcode_extracted(self):
        job = parse_job_from_jsonld("https://example.com/vacatures/1", JOBPOSTING_JSONLD)
        assert job["postcode"] == "6717LM"

    def test_salary_extracted(self):
        job = parse_job_from_jsonld("https://example.com/vacatures/1", JOBPOSTING_JSONLD)
        assert job["salary_min"] == 2641.0
        assert job["salary_max"] == 3630.0

    def test_contract_type_parttime(self):
        job = parse_job_from_jsonld("https://example.com/vacatures/1", JOBPOSTING_JSONLD)
        assert job["contract_type"] == "parttime"

    def test_hours_from_description(self):
        job = parse_job_from_jsonld("https://example.com/vacatures/1", JOBPOSTING_JSONLD)
        assert job["hours_min"] == 24
        assert job["hours_max"] == 32

    def test_external_id_from_identifier(self):
        job = parse_job_from_jsonld("https://example.com/vacatures/1", JOBPOSTING_JSONLD)
        assert job["external_id"] == "1265621-NL-1044"

    def test_source_url_preserved(self):
        url = "https://example.com/vacatures/test-job-123/"
        job = parse_job_from_jsonld(url, JOBPOSTING_JSONLD)
        assert job["source_url"] == url

    def test_no_salary_gives_none(self):
        jsonld = {**JOBPOSTING_JSONLD}
        del jsonld["baseSalary"]
        job = parse_job_from_jsonld("https://example.com/1", jsonld)
        assert job["salary_min"] is None
        assert job["salary_max"] is None


# ── get_job_links_from_listing ────────────────────────────────────────────────

class TestGetJobLinksFromListing:
    def test_extracts_job_links(self):
        links = get_job_links_from_listing(
            LISTING_HTML, "https://samenwerkendekinderopvang.nl", "/vacatures/"
        )
        assert len(links) == 3  # 2 local + 1 extern
        assert any("1265621" in l for l in links)
        assert any("1270956" in l for l in links)

    def test_excludes_listing_page_itself(self):
        links = get_job_links_from_listing(
            LISTING_HTML, "https://samenwerkendekinderopvang.nl", "/vacatures/"
        )
        # /vacatures/ zonder verdere slug moet uitgesloten zijn
        assert not any(l.endswith("/vacatures/") for l in links)

    def test_relative_urls_made_absolute(self):
        links = get_job_links_from_listing(
            LISTING_HTML, "https://samenwerkendekinderopvang.nl", "/vacatures/"
        )
        assert all(l.startswith("https://") for l in links)

    def test_empty_page_returns_empty(self):
        links = get_job_links_from_listing("<html><body></body></html>", "https://example.com", "/vacatures/")
        assert links == []


# ── SamenwerkendeKOScraper (gemockt) ──────────────────────────────────────────

class TestSamenwerkendeKOScraper:
    def test_company_slug(self):
        assert SamenwerkendeKOScraper.company_slug == "samenwerkende-ko"

    def test_listing_url_correct(self):
        assert "samenwerkendekinderopvang.nl" in SamenwerkendeKOScraper.listing_url

    def test_fetch_jobs_with_jsonld(self):
        scraper = SamenwerkendeKOScraper()

        listing_resp = MagicMock()
        listing_resp.text = LISTING_HTML
        listing_resp.raise_for_status = MagicMock()

        detail_resp = MagicMock()
        detail_resp.text = PAGE_WITH_JSONLD
        detail_resp.raise_for_status = MagicMock()

        with patch("scrapers.wordpress_jobs.requests.get",
                   side_effect=[listing_resp] + [detail_resp] * 10):
            jobs = scraper.fetch_jobs()

        assert len(jobs) >= 1
        assert jobs[0]["title"] == "Pedagogisch Professional KDV (Ede)"

    def test_fetch_jobs_returns_empty_on_error(self):
        scraper = SamenwerkendeKOScraper()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=Exception("timeout")):
            jobs = scraper.fetch_jobs()
        assert jobs == []


# ── Integratie tests ──────────────────────────────────────────────────────────

@pytest.mark.integration
class TestSamenwerkendeKOLive:
    def test_listing_bereikbaar(self):
        import requests
        resp = requests.get(SamenwerkendeKOScraper.listing_url, timeout=15)
        assert resp.status_code == 200

    def test_volledige_scrape(self):
        scraper = SamenwerkendeKOScraper()
        jobs = scraper.fetch_jobs()
        print(f"\n[INFO] Samenwerkende KO: {len(jobs)} vacatures gevonden")
        if jobs:
            j = jobs[0]
            print(f"  Eerste: {j['title']} | {j['city']} | {j['hours_min']}u | €{j['salary_min']}")
        assert isinstance(jobs, list)
        if len(jobs) == 0:
            pytest.skip("Geen vacatures gevonden")
        assert jobs[0]["source_url"].startswith("http")
        assert len(jobs[0]["title"]) > 3
