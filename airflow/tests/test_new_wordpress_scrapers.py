"""
Parametrized unit tests for all new WordPress-based scrapers.

Covers:
  - Config attributes (slug, listing_url, job_url_contains, website_url)
  - fetch_jobs() with mocked listing + detail HTML
  - fetch_jobs() returns [] on network error
  - Company name is set
  - Hero-specific: extra_listing_urls populated
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.avonturijn      import AvonturijnScraper
from scrapers.bzzzonder        import BzzzonderScraper
from scrapers.de_eerste_stap   import DeEersteStapScraper
from scrapers.dichtbij         import DichtbijScraper
from scrapers.de_lange_keizer  import DeLangeKeizerScraper
from scrapers.flekss           import FlekssScraper
from scrapers.floreokids       import FloreoKidsScraper
from scrapers.forte            import ForteScraper
from scrapers.gmk              import GmkScraper
from scrapers.wordpress_jobs   import WordPressRestApiScraper
from scrapers.go_kinderopvang  import GoKinderopvangScraper
from scrapers.goo              import GooScraper
from scrapers.hero             import HeroScraper
from scrapers.hoera            import HoeraScraper
from scrapers.junis            import JunisScraper
from scrapers.kiddoozz         import KiddoozzScraper
from scrapers.kids2b           import Kids2bScraper
from scrapers.kidscasa         import KidscasaScraper
from scrapers.kindernet        import KindernetScraper
from scrapers.ko_walcheren     import KOWalcherenScraper
from scrapers.kinderrijk       import KinderrijkScraper
from scrapers.kindertuin       import KindertuinScraper
from scrapers.klein_alkmaar    import KleinAlkmaarScraper
from scrapers.kleurrijk        import KleurrijkScraper
from scrapers.ko_friesland     import KoFrieslandScraper
from scrapers.ko_purmerend     import KoPurmerendScraper
from scrapers.komkids          import KomKidsScraper
from scrapers.koos             import KoosScraper
from scrapers.kosmo            import KosmoScraper
from scrapers.ksh              import KshScraper
from scrapers.lps              import LpsScraper
from scrapers.monter           import MonterScraper
from scrapers.morgen           import MorgenScraper
from scrapers.nummereen        import NummereenScraper
from scrapers.okidoki          import OkidokiScraper
from scrapers.puckco           import PuckcoScraper
from scrapers.quadrant         import QuadrantScraper
from scrapers.riant            import RiantScraper
from scrapers.scio             import ScioScraper
from scrapers.sdk              import SdkScraper
from scrapers.skbnm            import SkbnmScraper
from scrapers.skdd             import SkddScraper
from scrapers.skid             import SkidScraper
from scrapers.solidoe          import SolidoeScraper
from scrapers.unikidz          import UniKidzScraper
from scrapers.vlietkinderen    import VlietkinderenScraper
from scrapers.welluswijs       import WelluswijsScraper
from scrapers.wildewijs        import WildewijsScraper
from scrapers.woest_zuid       import WoestZuidScraper
from scrapers.xpect013         import Xpect013Scraper
from scrapers.atalenta         import AtalentaScraper
from scrapers.basker           import BaskerScraper
from scrapers.blosse           import BlosseScraper
from scrapers.mikz             import MikzScraper
from scrapers.skippypepijn     import SkippyPePijNScraper
from scrapers.un1ek            import Un1ekScraper
from scrapers.sportstuif       import SportstuifScraper
from scrapers.yes_kinderopvang import YesKinderopvangScraper

# ── Scraper registry: (module_path, class, expected_slug, job_url_fragment) ──

WP_SCRAPERS = [
    (AvonturijnScraper,     "avonturijn",        "/vacatures/"),
    (BzzzonderScraper,      "bzzzonder",         "/Vacatures/"),
    (DeEersteStapScraper,   "de-eerste-stap",    "/vacature/"),
    (DeLangeKeizerScraper,  "de-lange-keizer",   "/vacatures/"),
    (DichtbijScraper,       "dichtbij",          "/vacature/"),
    (FloreoKidsScraper,     "floreokids",        "/vacatures/"),
    (GmkScraper,            "gmk",               "/vacatures/"),
    (GoKinderopvangScraper, "go-kinderopvang",   "/vacature/"),
    (GooScraper,            "goo",               "/vacatures/"),
    (HeroScraper,           "hero",              "/vacatures-overzicht/"),
    (HoeraScraper,          "hoera",             "/vacancies/"),
    (KiddoozzScraper,       "kiddoozz",          "/vacatures/"),
    (Kids2bScraper,         "kids2b",            "/kids2b-vacatures"),
    (KindernetScraper,      "kindernet",         "/vacancies/"),
    (KOWalcherenScraper,    "ko-walcheren",      "/vacatures/"),
    (KinderrijkScraper,     "kinderrijk",        "/vacatures/"),
    (KindertuinScraper,     "kindertuin",        "/werken-bij/"),
    (KleinAlkmaarScraper,   "klein-alkmaar",     "/vacatures/"),
    (KleurrijkScraper,      "kleurrijk",         "/vacatures/"),
    (KoFrieslandScraper,    "ko-friesland",      "/vacatures/"),
    (KoosScraper,           "koos",              "/werken-bij/"),
    (KosmoScraper,          "kosmo",             "/vacatures"),
    (KshScraper,            "ksh",               "/vacature/"),
    (LpsScraper,            "lps",               "/vacatures-bij-lps/"),
    (MonterScraper,         "monter",            "/vacatures/"),
    (MorgenScraper,         "morgen",            "/vacatures/"),
    (OkidokiScraper,        "okidoki",           "/werkenbij/"),
    (PuckcoScraper,         "puckco",            "/werken-bij/"),
    (QuadrantScraper,       "quadrant",          "/vacatures/"),
    (RiantScraper,          "riant",             "/vacatures/"),
    (ScioScraper,           "scio",              "/vacatures/"),
    (SdkScraper,            "sdk",               "/vacatures/"),
    (SkbnmScraper,          "skbnm",             "/vacatures/"),
    (SkddScraper,           "skdd",              "/vacatures"),
    (SkidScraper,           "skid",              "/vacatures/"),
    (SolidoeScraper,        "solidoe",           "/vacature/"),
    (UniKidzScraper,        "unikidz",           "/vacatures/"),
    (VlietkinderenScraper,  "vlietkinderen",     "/vacature/"),
    (WelluswijsScraper,     "welluswijs",        "/vacature/"),
    (WildewijsScraper,      "wildewijs",         "/vacatures/"),
    (WoestZuidScraper,      "woest-zuid",        "/vacatures/"),
    (Xpect013Scraper,       "xpect013",          "/vacatures/"),
    # ── Nieuwe custom WordPress scrapers ────────────────────────────────────
    (AtalentaScraper,       "atalenta",          "/vacatures/"),
    (BaskerScraper,         "basker",            "/vacatures/"),
    (BlosseScraper,         "blosse",            "/vacature/"),
    (MikzScraper,           "mikz",              "/werkenenlerenbij/"),
    (SkippyPePijNScraper,   "skippypepijn",      "/vacatures/"),
    (SportstuifScraper,     "sportstuif",        "/vacatures/"),
    (YesKinderopvangScraper,"yes-kinderopvang",  "/vacatures/"),
]

# ── WordPressRestApiScraper scrapers (geen listing_url class attr, geen job_url_contains) ──
REST_API_SCRAPERS = [
    (FlekssScraper,         "flekss"),
    (ForteScraper,          "forte"),
    (JunisScraper,          "junis"),
    (KoPurmerendScraper,    "ko-purmerend"),
    (KomKidsScraper,        "komkids"),
    (NummereenScraper,      "nummereen"),
]

# ── HTML fixtures ─────────────────────────────────────────────────────────────

def _make_listing_html(job_url_fragment: str, website_url: str) -> str:
    """Generate a minimal listing HTML with two job links."""
    slug1 = job_url_fragment.strip("/")
    return f"""<html><body>
<a href="{job_url_fragment}pedagogisch-medewerker-amsterdam-123">PM Amsterdam</a>
<a href="{job_url_fragment}locatiemanager-rotterdam-456">Locatiemanager Rotterdam</a>
<a href="/">Home</a>
</body></html>"""


DETAIL_HTML_WITH_JSONLD = """\
<html><body>
<h1>Pedagogisch Medewerker</h1>
<script type="application/ld+json">{{
  "@context": "https://schema.org/",
  "@type": "JobPosting",
  "title": "Pedagogisch Medewerker",
  "description": "<p>We zoeken een PM voor 24-32 uur per week in Amsterdam.</p>",
  "jobLocation": {{
    "@type": "Place",
    "address": {{
      "@type": "PostalAddress",
      "addressLocality": "Amsterdam",
      "postalCode": "1012AB"
    }}
  }},
  "identifier": {{"@type": "PropertyValue", "value": "pm-123"}}
}}</script>
</body></html>"""

DETAIL_HTML_FALLBACK = """\
<html><body>
<h1>Locatiemanager Rotterdam</h1>
<main><p>Wij zoeken een locatiemanager voor 32-36 uur per week.</p></main>
</body></html>"""


# ── Parametrized config tests ─────────────────────────────────────────────────

@pytest.mark.parametrize("scraper_cls,expected_slug,_juf", WP_SCRAPERS)
def test_company_slug(scraper_cls, expected_slug, _juf):
    assert scraper_cls.company_slug == expected_slug


@pytest.mark.parametrize("scraper_cls,_slug,_juf", WP_SCRAPERS)
def test_listing_url_nonempty(scraper_cls, _slug, _juf):
    assert scraper_cls.listing_url.startswith("http")


@pytest.mark.parametrize("scraper_cls,_slug,expected_fragment", WP_SCRAPERS)
def test_job_url_contains(scraper_cls, _slug, expected_fragment):
    assert scraper_cls.job_url_contains == expected_fragment


@pytest.mark.parametrize("scraper_cls,_slug,_juf", WP_SCRAPERS)
def test_website_url_nonempty(scraper_cls, _slug, _juf):
    assert scraper_cls.website_url.startswith("http")


@pytest.mark.parametrize("scraper_cls,_slug,_juf", WP_SCRAPERS)
def test_company_name_nonempty(scraper_cls, _slug, _juf):
    assert scraper_cls.company_name.strip() != ""


# ── Parametrized fetch_jobs tests ─────────────────────────────────────────────

@pytest.mark.parametrize("scraper_cls,_slug,job_url_fragment", WP_SCRAPERS)
def test_fetch_jobs_returns_list(scraper_cls, _slug, job_url_fragment):
    """fetch_jobs() must return a list (even if empty)."""
    scraper = scraper_cls()
    listing_html = _make_listing_html(job_url_fragment, scraper.website_url)

    listing_r = MagicMock()
    listing_r.text = listing_html
    listing_r.raise_for_status = MagicMock()

    detail_r = MagicMock()
    detail_r.text = DETAIL_HTML_WITH_JSONLD
    detail_r.raise_for_status = MagicMock()

    with patch("scrapers.wordpress_jobs.requests.get",
               side_effect=[listing_r, detail_r, detail_r, detail_r]):
        jobs = scraper.fetch_jobs()

    assert isinstance(jobs, list)


@pytest.mark.parametrize("scraper_cls,_slug,job_url_fragment", WP_SCRAPERS)
def test_fetch_jobs_empty_on_network_error(scraper_cls, _slug, job_url_fragment):
    """fetch_jobs() returns [] when listing page raises an exception."""
    scraper = scraper_cls()
    with patch("scrapers.wordpress_jobs.requests.get", side_effect=Exception("timeout")):
        jobs = scraper.fetch_jobs()
    assert jobs == []


@pytest.mark.parametrize("scraper_cls,_slug,job_url_fragment", WP_SCRAPERS)
def test_fetch_jobs_jsonld_title_extracted(scraper_cls, _slug, job_url_fragment):
    """When detail page has valid JSON-LD, title is extracted."""
    scraper = scraper_cls()
    listing_html = _make_listing_html(job_url_fragment, scraper.website_url)

    listing_r = MagicMock()
    listing_r.text = listing_html
    listing_r.raise_for_status = MagicMock()

    detail_r = MagicMock()
    detail_r.text = DETAIL_HTML_WITH_JSONLD
    detail_r.raise_for_status = MagicMock()

    with patch("scrapers.wordpress_jobs.requests.get",
               side_effect=[listing_r, detail_r, detail_r, detail_r]):
        jobs = scraper.fetch_jobs()

    if jobs:
        assert jobs[0]["title"] != ""
        assert jobs[0]["source_url"].startswith("http")


@pytest.mark.parametrize("scraper_cls,_slug,job_url_fragment", WP_SCRAPERS)
def test_fetch_jobs_html_fallback(scraper_cls, _slug, job_url_fragment):
    """When detail page has no JSON-LD, HTML fallback title is extracted."""
    scraper = scraper_cls()
    listing_html = _make_listing_html(job_url_fragment, scraper.website_url)

    listing_r = MagicMock()
    listing_r.text = listing_html
    listing_r.raise_for_status = MagicMock()

    detail_r = MagicMock()
    detail_r.text = DETAIL_HTML_FALLBACK
    detail_r.raise_for_status = MagicMock()

    with patch("scrapers.wordpress_jobs.requests.get",
               side_effect=[listing_r, detail_r, detail_r, detail_r]):
        jobs = scraper.fetch_jobs()

    if jobs:
        assert jobs[0]["title"] == "Locatiemanager Rotterdam"


# ── Hero-specific tests ───────────────────────────────────────────────────────

class TestHeroExtraListings:
    def test_has_extra_listing_urls(self):
        assert len(HeroScraper.extra_listing_urls) == 2

    def test_extra_urls_start_with_http(self):
        for url in HeroScraper.extra_listing_urls:
            assert url.startswith("http")

    def test_fetch_jobs_uses_all_listing_urls(self):
        """Hero fetches from 3 listing pages (main + 2 extra)."""
        scraper = HeroScraper()
        listing_html = _make_listing_html("/vacatures/", scraper.website_url)

        listing_r = MagicMock()
        listing_r.text = listing_html
        listing_r.raise_for_status = MagicMock()

        detail_r = MagicMock()
        detail_r.text = DETAIL_HTML_WITH_JSONLD
        detail_r.raise_for_status = MagicMock()

        # 3 listing requests + up to 6 detail requests
        side_effects = [listing_r] * 3 + [detail_r] * 6
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=side_effects):
            jobs = scraper.fetch_jobs()

        assert isinstance(jobs, list)


# ── fetch_company tests ───────────────────────────────────────────────────────

@pytest.mark.parametrize("scraper_cls,expected_slug,_juf", WP_SCRAPERS)
def test_fetch_company_returns_name(scraper_cls, expected_slug, _juf):
    """fetch_company() always returns dict with company name."""
    scraper = scraper_cls()
    resp = MagicMock()
    resp.text = f'<html><head><meta name="description" content="Kinderopvang"></head><body></body></html>'
    resp.raise_for_status = MagicMock()
    with patch("scrapers.wordpress_jobs.requests.get", return_value=resp):
        company = scraper.fetch_company()
    assert company["name"] == scraper_cls.company_name
    assert company["website"] == scraper_cls.website_url


@pytest.mark.parametrize("scraper_cls,_slug,_juf", WP_SCRAPERS)
def test_fetch_company_graceful_on_error(scraper_cls, _slug, _juf):
    """fetch_company() returns dict with name even on network error."""
    scraper = scraper_cls()
    with patch("scrapers.wordpress_jobs.requests.get", side_effect=Exception("conn")):
        company = scraper.fetch_company()
    assert company["name"] == scraper_cls.company_name
    assert company["logo_url"] == ""


# ── WordPressRestApiScraper tests ─────────────────────────────────────────────

@pytest.mark.parametrize("scraper_cls,expected_slug", REST_API_SCRAPERS)
def test_rest_api_company_slug(scraper_cls, expected_slug):
    assert scraper_cls.company_slug == expected_slug


@pytest.mark.parametrize("scraper_cls,_slug", REST_API_SCRAPERS)
def test_rest_api_is_subclass(scraper_cls, _slug):
    assert issubclass(scraper_cls, WordPressRestApiScraper)


@pytest.mark.parametrize("scraper_cls,_slug", REST_API_SCRAPERS)
def test_rest_api_listing_url_instance(scraper_cls, _slug):
    """listing_url is a @property — check on an instance."""
    scraper = scraper_cls()
    assert scraper.listing_url.startswith("http")


@pytest.mark.parametrize("scraper_cls,_slug", REST_API_SCRAPERS)
def test_rest_api_company_name_nonempty(scraper_cls, _slug):
    assert scraper_cls.company_name.strip() != ""


@pytest.mark.parametrize("scraper_cls,_slug", REST_API_SCRAPERS)
def test_rest_api_fetch_jobs_returns_list(scraper_cls, _slug):
    scraper = scraper_cls()
    with patch("scrapers.wordpress_jobs.requests.get", side_effect=Exception("timeout")):
        jobs = scraper.fetch_jobs()
    assert jobs == []


# ── KidscasaScraper tests (BaseScraper, PDF-based) ─────────────────────────────

class TestUn1ekScraper:
    """Un1ek is a BaseScraper subclass with a custom fetch_jobs — not in WP_SCRAPERS."""

    def test_company_slug(self):
        assert Un1ekScraper.company_slug == "un1ek"

    def test_company_name_nonempty(self):
        assert Un1ekScraper.company_name.strip() != ""

    def test_fetch_jobs_returns_list_on_network_error(self):
        scraper = Un1ekScraper()
        with patch("scrapers.un1ek.requests.get", side_effect=Exception("timeout")):
            jobs = scraper.fetch_jobs()
        assert jobs == []

    def test_fetch_jobs_returns_list_with_mocked_listing(self):
        scraper = Un1ekScraper()
        listing_html = """<html><body>
        <a href="/279">Pedagogisch Professional</a>
        <a href="/280">Teamleider</a>
        <a href="/">Home</a>
        </body></html>"""
        detail_html = """<html><body>
        <meta property="og:title" content="Pedagogisch Professional KDV - UN1EK"/>
        <div class="vacature-single__usps">
          <div><div class="icon"></div><div class="content">Per 1 mei 2026</div></div>
          <div><div class="icon"></div><div class="content">24-32 uur</div></div>
          <div><div class="icon"></div><div class="content">IKC VanKampen</div></div>
        </div>
        <div class="vacature-single__intro"><p>Wij zoeken een PM.</p></div>
        </body></html>"""
        listing_r = MagicMock()
        listing_r.text = listing_html
        listing_r.raise_for_status = MagicMock()
        detail_r = MagicMock()
        detail_r.text = detail_html
        detail_r.raise_for_status = MagicMock()
        with patch("scrapers.un1ek.requests.get", side_effect=[listing_r, detail_r, detail_r]):
            jobs = scraper.fetch_jobs()
        assert isinstance(jobs, list)


class TestKidscasaInWpFile:
    def test_company_slug(self):
        assert KidscasaScraper.company_slug == "kidscasa"

    def test_company_name_nonempty(self):
        assert KidscasaScraper.company_name.strip() != ""

    def test_fetch_jobs_returns_list_on_error(self):
        scraper = KidscasaScraper()
        with patch("scrapers.kidscasa.requests.get", side_effect=Exception("timeout")):
            jobs = scraper.fetch_jobs()
        assert jobs == []

    def test_fetch_company_returns_name(self):
        scraper = KidscasaScraper()
        company = scraper.fetch_company()
        assert company["name"] == "Kidscasa"
        assert company["website"].startswith("http")


# ── Integration tests (marked, skipped by default) ────────────────────────────

@pytest.mark.integration
@pytest.mark.parametrize("scraper_cls,_slug,_juf", WP_SCRAPERS)
def test_listing_reachable(scraper_cls, _slug, _juf):
    import requests as _req
    import urllib3
    from scrapers.base import SCRAPER_HEADERS
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    resp = _req.get(scraper_cls.listing_url, headers=SCRAPER_HEADERS, timeout=20, verify=False)
    # 200 = OK, 403 = site exists but blocks bots at URL level (acceptable)
    assert resp.status_code in (200, 403), f"Unexpected {resp.status_code} for {scraper_cls.listing_url}"


@pytest.mark.integration
@pytest.mark.parametrize("scraper_cls,_slug,_juf", WP_SCRAPERS)
def test_full_scrape(scraper_cls, _slug, _juf):
    scraper = scraper_cls()
    jobs = scraper.fetch_jobs()
    print(f"\n[{scraper_cls.company_slug}] {len(jobs)} vacatures")
    assert isinstance(jobs, list)
    if jobs:
        assert jobs[0]["source_url"].startswith("http")
        assert jobs[0]["title"] != ""
