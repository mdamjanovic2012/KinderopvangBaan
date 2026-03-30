"""
Unit + integratie tests voor de Kinderdam scraper.

Structuur:
  Niveau 1: hoofdpagina → regio-links (_get_regio_urls)
  Niveau 2: regio-pagina → vacaturekaarten (_extract_cards_from_regio_page)
  Niveau 3: detailpagina → beschrijving (_extract_description_from_html)

Unit tests: gesimuleerde HTML, geen netwerk.
Integratie tests (mark=integration): echte site via Playwright.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.kinderdam import (
    _get_regio_urls,
    _extract_cards_from_regio_page,
    _extract_description_from_html,
    _parse_euros,
    _parse_contract,
    _werksoort_to_job_type,
    BANNER_CONTENT_ID,
    BASE_URL,
    JOBS_URL,
)


# ── Helpers ──────────────────────────────────────────────────────────────────────

def make_banner_html(inner: str) -> str:
    return f"""<html><body>
      <div id="{BANNER_CONTENT_ID}">{inner}</div>
    </body></html>"""


def make_card_html(title: str, werksoort: str, location: str, uren: str, href: str) -> str:
    """Simuleer een vacaturekaart zoals Anta CMS die rendert."""
    return f"""
    <a class="vtlink border_5" href="{href}">
      <h2><span class="text" data-row-id="abc">{title}</span></h2>
      <p><span class="freehtmltextweight">Werksoort:</span>
         <span class="text" data-row-id="abc">{werksoort}</span></p>
      <p><span class="freehtmltextweight">Standplaats:</span>
         <span class="text" data-row-id="abc">{location}</span></p>
      <p><span class="freehtmltextweight">Aantal uren per week:</span>
         <span class="text" data-row-id="abc">{uren}</span></p>
    </a>"""


def make_regio_html(*cards_html: str) -> str:
    return f"<html><body>{''.join(cards_html)}</body></html>"


# ── _parse_euros ─────────────────────────────────────────────────────────────────

class TestParseEuros:
    def test_dutch_format(self):
        assert _parse_euros("2.700,50") == 2700.50

    def test_integer(self):
        assert _parse_euros("3400") == 3400.0

    def test_invalid(self):
        assert _parse_euros("geen bedrag") is None

    def test_whitespace(self):
        assert _parse_euros("  3.500  ") == 3500.0


# ── _parse_contract ───────────────────────────────────────────────────────────────

class TestParseContract:
    def test_fulltime(self):
        assert _parse_contract("Full-time") == "fulltime"

    def test_parttime(self):
        assert _parse_contract("parttime 24 uur") == "parttime"

    def test_tijdelijk(self):
        assert _parse_contract("Tijdelijk contract") == "temp"

    def test_unknown(self):
        assert _parse_contract("onbekend") == ""


# ── _werksoort_to_job_type ────────────────────────────────────────────────────────

class TestWerksoortToJobType:
    def test_bso(self):
        assert _werksoort_to_job_type("BSO") == "bso_begeleider"

    def test_kdv(self):
        assert _werksoort_to_job_type("KDV") == "pm3"

    def test_pedagogisch_professional(self):
        assert _werksoort_to_job_type("Pedagogisch Professional") == "senior_pm"

    def test_unknown(self):
        assert _werksoort_to_job_type("onbekend") == ""

    def test_case_insensitive(self):
        assert _werksoort_to_job_type("bso") == "bso_begeleider"


# ── _get_regio_urls ──────────────────────────────────────────────────────────────

class TestGetRegioUrls:
    def test_extracts_banner_links(self):
        html = make_banner_html("""
            <a class="webBanner-banneritem" href="/vacatures-kinderopvang-rotterdam-centrum">Centrum</a>
            <a class="webBanner-banneritem" href="/vacatures-kinderopvang-rotterdam-charlois">Charlois</a>
        """)
        urls = _get_regio_urls(html)
        assert len(urls) == 2
        assert BASE_URL + "/vacatures-kinderopvang-rotterdam-centrum" in urls
        assert BASE_URL + "/vacatures-kinderopvang-rotterdam-charlois" in urls

    def test_absolute_urls_not_doubled(self):
        html = make_banner_html(f"""
            <a class="webBanner-banneritem" href="{BASE_URL}/vacatures-regio">Regio</a>
        """)
        urls = _get_regio_urls(html)
        assert len(urls) == 1
        assert urls[0] == f"{BASE_URL}/vacatures-regio"

    def test_deduplicates(self):
        html = make_banner_html("""
            <a class="webBanner-banneritem" href="/vacatures-regio">Regio</a>
            <a class="webBanner-banneritem" href="/vacatures-regio">Regio (dup)</a>
        """)
        urls = _get_regio_urls(html)
        assert len(urls) == 1

    def test_empty_banner_returns_empty(self):
        html = make_banner_html("<div></div>")
        urls = _get_regio_urls(html)
        assert urls == []

    def test_no_banner_container_uses_whole_page(self):
        html = """<html><body>
            <a class="webBanner-banneritem" href="/vacatures-regio">Regio</a>
        </body></html>"""
        urls = _get_regio_urls(html)
        assert len(urls) == 1


# ── _extract_cards_from_regio_page ────────────────────────────────────────────────

class TestExtractCardsFromRegioPage:

    def test_basic_card(self):
        html = make_regio_html(make_card_html(
            "Pedagogisch medewerker | BSO De Terp",
            "BSO", "Nieuwerkerk aan den IJssel", "20 - 24",
            "/vacaturebeschrijving-kinderdam/pm-bso-de-terp"
        ))
        jobs = _extract_cards_from_regio_page(html)
        assert len(jobs) == 1
        job = jobs[0]
        assert job["title"] == "Pedagogisch medewerker | BSO De Terp"
        assert job["location_name"] == "Nieuwerkerk aan den IJssel"
        assert job["hours_min"] == 20
        assert job["hours_max"] == 24
        assert job["job_type"] == "bso_begeleider"
        assert job["source_url"] == BASE_URL + "/vacaturebeschrijving-kinderdam/pm-bso-de-terp"

    def test_hours_with_dash(self):
        html = make_regio_html(make_card_html(
            "Groepsleider KDV", "KDV", "Rotterdam", "14-24",
            "/vacaturebeschrijving-kinderdam/groepsleider"
        ))
        jobs = _extract_cards_from_regio_page(html)
        assert jobs[0]["hours_min"] == 14
        assert jobs[0]["hours_max"] == 24

    def test_deduplication(self):
        card = make_card_html(
            "Pedagogisch Medewerker", "BSO", "Rotterdam", "24-32",
            "/vacaturebeschrijving-kinderdam/pm-bso"
        )
        html = make_regio_html(card, card, card)  # 3x dezelfde kaart
        jobs = _extract_cards_from_regio_page(html)
        assert len(jobs) == 1

    def test_multiple_unique_cards(self):
        html = make_regio_html(
            make_card_html("PM BSO", "BSO", "Rotterdam", "20-24",
                           "/vacaturebeschrijving-kinderdam/pm-bso"),
            make_card_html("Groepsleider", "KDV", "Capelle", "32-36",
                           "/vacaturebeschrijving-kinderdam/groepsleider"),
        )
        jobs = _extract_cards_from_regio_page(html)
        assert len(jobs) == 2

    def test_relative_url_prefixed(self):
        html = make_regio_html(make_card_html(
            "PM BSO", "BSO", "Rotterdam", "20-24",
            "/vacaturebeschrijving-kinderdam/pm-bso"
        ))
        jobs = _extract_cards_from_regio_page(html)
        assert jobs[0]["source_url"].startswith(BASE_URL)

    def test_external_id_from_slug(self):
        html = make_regio_html(make_card_html(
            "PM BSO", "BSO", "Rotterdam", "20-24",
            "/vacaturebeschrijving-kinderdam/pedagogisch-medewerker-bso-123"
        ))
        jobs = _extract_cards_from_regio_page(html)
        assert jobs[0]["external_id"] == "pedagogisch-medewerker-bso-123"

    def test_skips_non_vacaturebeschrijving_links(self):
        html = """<html><body>
            <a class="vtlink" href="/login"><span class="text">Login</span></a>
            <a class="vtlink" href="/vacaturebeschrijving-kinderdam/pm">
                <span class="text">Pedagogisch Medewerker</span>
            </a>
        </body></html>"""
        jobs = _extract_cards_from_regio_page(html)
        # /login heeft geen 'vacaturebeschrijving' in href → wordt overgeslagen
        assert len(jobs) == 1
        assert "pm" in jobs[0]["source_url"]

    def test_no_hours_gives_none(self):
        card = f"""<a class="vtlink border_5" href="/vacaturebeschrijving-kinderdam/pm">
            <span class="text">PM BSO</span>
            <span class="text">BSO</span>
            <span class="text">Rotterdam</span>
        </a>"""
        html = f"<html><body>{card}</body></html>"
        jobs = _extract_cards_from_regio_page(html)
        assert jobs[0]["hours_min"] is None
        assert jobs[0]["hours_max"] is None


# ── _extract_description_from_html ───────────────────────────────────────────────

class TestExtractDescription:
    def test_from_staticwebform(self):
        html = """<html><body>
            <div class="staticwebform">
                Wij zoeken een enthousiaste pedagogisch medewerker voor onze locatie in Rotterdam.
                Je werkt met kinderen van 4 tot 12 jaar op onze BSO-locatie.
            </div>
        </body></html>"""
        result = _extract_description_from_html(html)
        assert "pedagogisch medewerker" in result

    def test_from_article(self):
        html = """<html><body>
            <article>
                <p>Wij zoeken een enthousiaste pedagogisch medewerker voor onze BSO-locatie.</p>
            </article>
        </body></html>"""
        result = _extract_description_from_html(html)
        assert "pedagogisch medewerker" in result

    def test_empty_page(self):
        html = "<html><body><p>kort</p></body></html>"
        assert _extract_description_from_html(html) == ""

    def test_max_5000_chars(self):
        html = f"<html><body><article>{'x' * 10_000}</article></body></html>"
        assert len(_extract_description_from_html(html)) <= 5000


# ── Integratie tests (echte site, vereist netwerk + Playwright) ───────────────────

@pytest.mark.integration
class TestKinderdamLive:
    """Uitvoeren met: pytest -m integration tests/test_kinderdam.py -v -s"""

    def test_hoofdpagina_geeft_regio_urls(self):
        from playwright.sync_api import sync_playwright
        from scrapers.kinderdam import _render_page

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(locale="nl-NL")
            try:
                html = _render_page(context, JOBS_URL, wait_for_id=BANNER_CONTENT_ID)
            finally:
                context.close()
                browser.close()

        urls = _get_regio_urls(html)
        print(f"\n[INFO] {len(urls)} regio-URL's gevonden")
        for u in urls:
            print(f"  {u}")

        assert len(urls) >= 5, f"Te weinig regio-URL's: {len(urls)}"

    def test_regio_pagina_geeft_vacatures(self):
        from playwright.sync_api import sync_playwright
        from scrapers.kinderdam import _render_page

        # Gebruik Capelle als test-regio
        regio_url = BASE_URL + "/vacatures-kinderopvang-capelle-nieuwerkerk-aan-den-ijssel"

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(locale="nl-NL")
            try:
                html = _render_page(context, regio_url)
            finally:
                context.close()
                browser.close()

        jobs = _extract_cards_from_regio_page(html)
        print(f"\n[INFO] {len(jobs)} vacatures in Capelle-regio")
        if jobs:
            print(f"[INFO] Eerste: {jobs[0]}")

        assert isinstance(jobs, list)
        if len(jobs) == 0:
            pytest.skip("Geen vacatures in Capelle (mogelijk tijdelijk leeg)")

        job = jobs[0]
        assert job["source_url"].startswith("http")
        assert len(job["title"]) > 3
        assert job["hours_min"] is None or isinstance(job["hours_min"], int)

    def test_volledige_scrape(self):
        """Volledig eind-tot-eind test: KinderdamScraper.fetch_jobs()"""
        from scrapers.kinderdam import KinderdamScraper

        scraper = KinderdamScraper()
        jobs = scraper.fetch_jobs()

        print(f"\n[INFO] Totaal gescraped: {len(jobs)} vacatures")
        if jobs:
            for j in jobs[:3]:
                print(f"  - {j['title']} | {j['location_name']} | {j['hours_min']}-{j['hours_max']}u")

        assert isinstance(jobs, list)
        if len(jobs) == 0:
            pytest.skip("Geen vacatures gevonden (mogelijk tijdelijk leeg)")

        job = jobs[0]
        assert job["source_url"].startswith("http")
        assert len(job["title"]) > 3
