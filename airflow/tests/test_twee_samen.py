"""Unit tests for 2Samen scraper (WordPress, /vacature/ singular URL)."""
import sys, os, pytest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scrapers.twee_samen import TweeSamenScraper

LISTING_HTML = """<html><body>
<a href="/vacature/2aan2-pedagogisch-medewerker-bso/">PM BSO 2aan2</a>
<a href="/vacature/2ballonnen-pm-kdv/">PM KDV 2ballonnen</a>
<a href="/vacatures/">Alle vacatures</a>
</body></html>"""

DETAIL_HTML = """<html><body>
<h1>Pedagogisch Medewerker BSO</h1>
<main>
  <p>Gedempte Sloot 7, Centrum, 2513 TC Den Haag</p>
  <p>24 – 32 uur, Buitenschoolse Opvang, € 2.641 – 3.630 bruto op basis van fulltime</p>
  <p>Wij zoeken een enthousiaste pedagogisch medewerker voor onze BSO locatie.</p>
</main>
</body></html>"""

DETAIL_HTML_NO_ADDRESS = """<html><body>
<h1>Open sollicitatie</h1>
<main>
  <p>Wij zoeken medewerkers voor 32 uur per week.</p>
</main>
</body></html>"""


class TestTweeSamenConfig:
    def test_company_slug(self): assert TweeSamenScraper.company_slug == "2samen"
    def test_listing_url(self): assert "werkenbij2samen.nl" in TweeSamenScraper.listing_url
    def test_job_url_contains(self): assert TweeSamenScraper.job_url_contains == "/vacature/"


class TestTweeSamenScrapeJobPage:
    def _mock(self, html):
        r = MagicMock(); r.text = html; r.raise_for_status = MagicMock()
        return r

    def test_title_extracted(self):
        scraper = TweeSamenScraper()
        with patch("scrapers.twee_samen.requests.get", return_value=self._mock(DETAIL_HTML)):
            job = scraper._scrape_job_page("https://www.werkenbij2samen.nl/vacature/pm-bso/")
        assert job is not None
        assert job["title"] == "Pedagogisch Medewerker BSO"

    def test_hours_from_uur_paragraph(self):
        scraper = TweeSamenScraper()
        with patch("scrapers.twee_samen.requests.get", return_value=self._mock(DETAIL_HTML)):
            job = scraper._scrape_job_page("https://www.werkenbij2samen.nl/vacature/pm-bso/")
        assert job["hours_min"] == 24
        assert job["hours_max"] == 32

    def test_city_from_postcode_paragraph(self):
        scraper = TweeSamenScraper()
        with patch("scrapers.twee_samen.requests.get", return_value=self._mock(DETAIL_HTML)):
            job = scraper._scrape_job_page("https://www.werkenbij2samen.nl/vacature/pm-bso/")
        assert job["city"] == "Den Haag"
        assert job["postcode"] == "2513TC"

    def test_salary_extracted(self):
        scraper = TweeSamenScraper()
        with patch("scrapers.twee_samen.requests.get", return_value=self._mock(DETAIL_HTML)):
            job = scraper._scrape_job_page("https://www.werkenbij2samen.nl/vacature/pm-bso/")
        assert job["salary_min"] == 2641.0
        assert job["salary_max"] == 3630.0

    def test_hours_fallback_from_description(self):
        scraper = TweeSamenScraper()
        with patch("scrapers.twee_samen.requests.get", return_value=self._mock(DETAIL_HTML_NO_ADDRESS)):
            job = scraper._scrape_job_page("https://www.werkenbij2samen.nl/vacature/open/")
        assert job["hours_min"] == 32
        assert job["hours_max"] == 32

    def test_returns_none_on_error(self):
        scraper = TweeSamenScraper()
        with patch("scrapers.twee_samen.requests.get", side_effect=Exception("timeout")):
            assert scraper._scrape_job_page("https://www.werkenbij2samen.nl/vacature/test/") is None

    def test_returns_none_without_h1(self):
        scraper = TweeSamenScraper()
        html = "<html><body><main><p>Geen titel</p></main></body></html>"
        with patch("scrapers.twee_samen.requests.get", return_value=self._mock(html)):
            assert scraper._scrape_job_page("https://www.werkenbij2samen.nl/vacature/test/") is None


class TestTweeSamenFetchJobs:
    def test_empty_on_error(self):
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=Exception("err")):
            assert TweeSamenScraper().fetch_jobs() == []


@pytest.mark.integration
class TestTweeSamenLive:
    def test_listing_bereikbaar(self):
        import requests
        assert requests.get(TweeSamenScraper.listing_url, timeout=15).status_code == 200

    def test_full_scrape(self):
        scraper = TweeSamenScraper()
        jobs = scraper.fetch_jobs()
        print(f"\n[INFO] 2Samen: {len(jobs)} vacatures found")
        if jobs:
            j = jobs[0]
            print(f"  First: {j['title']} | {j['city']} | {j['hours_min']}h | sal={j['salary_min']}")
        assert isinstance(jobs, list)
        if len(jobs) == 0:
            pytest.skip("No vacatures found")
        assert jobs[0]["source_url"].startswith("http")
