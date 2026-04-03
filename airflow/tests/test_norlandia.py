"""
Unit tests voor Norlandia scraper (Teamtailor RSS).

Test strategie:
  - _parse_rss_items: XML parsing van gesimuleerde RSS feed
  - _extract_job_fields: veld-extractie (uren, salaris, beschrijving)
  - _strip_html: HTML → platte tekst
  - NorlandiaScraper.fetch_jobs: volledig flow met gemockte requests

Geen netwerk vereist. Integratie tests (mark=integration) raken de echte site.
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.teamtailor_rss import (
    _parse_rss_items,
    _extract_job_fields,
    _fetch_detail_location,
    _strip_html,
    _parse_euros,
)
from scrapers.norlandia import NorlandiaScraper


# ── Fixtures ────────────────────────────────────────────────────────────────

RSS_SINGLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Norlandia jobs</title>
    <link>https://werkenbij.norlandia.nl</link>
    <item>
      <title>Pedagogisch medewerker KDV</title>
      <link>https://werkenbij.norlandia.nl/jobs/123-pedagogisch-medewerker</link>
      <guid>https://werkenbij.norlandia.nl/jobs/123-pedagogisch-medewerker</guid>
      <description>&lt;p&gt;Wij zoeken een enthousiaste PM voor 24 - 32 uur per week.&lt;/p&gt;</description>
      <category>Kinderopvang</category>
    </item>
  </channel>
</rss>"""

RSS_TWO_ITEMS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Norlandia jobs</title>
    <item>
      <title>Groepsleider BSO</title>
      <link>https://werkenbij.norlandia.nl/jobs/456-groepsleider-bso</link>
      <guid>456-groepsleider-bso</guid>
      <description>&lt;p&gt;BSO in Amsterdam. Salaris € 2.500 - € 3.000 per maand.&lt;/p&gt;</description>
      <category>BSO</category>
    </item>
    <item>
      <title>Locatiemanager</title>
      <link>https://werkenbij.norlandia.nl/jobs/789-locatiemanager</link>
      <guid>789-locatiemanager</guid>
      <description>&lt;p&gt;Leidinggeven aan ons team in Utrecht.&lt;/p&gt;</description>
    </item>
  </channel>
</rss>"""

RSS_EMPTY = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel><title>Norlandia</title></channel>
</rss>"""

RSS_BROKEN = "THIS IS NOT XML <<<"

RSS_NO_CHANNEL = """<?xml version="1.0"?><root><item><title>X</title></item></root>"""


# ── _parse_euros ──────────────────────────────────────────────────────────────

class TestParseEuros:
    def test_dutch_format(self):
        assert _parse_euros("2.500") == 2500.0

    def test_invalid_returns_none(self):
        assert _parse_euros("onbekend") is None


# ── _strip_html ─────────────────────────────────────────────────────────────

class TestStripHtml:
    def test_removes_tags(self):
        result = _strip_html("<p>Hallo <b>wereld</b></p>")
        assert "Hallo" in result
        assert "<p>" not in result

    def test_max_5000_chars(self):
        long_html = f"<p>{'x' * 10_000}</p>"
        assert len(_strip_html(long_html)) <= 5000

    def test_empty_string(self):
        assert _strip_html("") == ""

    def test_plain_text_passthrough(self):
        result = _strip_html("Geen HTML hier")
        assert "Geen HTML hier" in result


# ── _parse_rss_items ─────────────────────────────────────────────────────────

class TestParseRssItems:
    def test_single_item(self):
        items = _parse_rss_items(RSS_SINGLE)
        assert len(items) == 1
        item = items[0]
        assert item["title"] == "Pedagogisch medewerker KDV"
        assert "123-pedagogisch-medewerker" in item["link"]
        assert "24 - 32 uur per week" in item["description_html"]
        assert "Kinderopvang" in item["categories"]

    def test_two_items(self):
        items = _parse_rss_items(RSS_TWO_ITEMS)
        assert len(items) == 2
        titles = [i["title"] for i in items]
        assert "Groepsleider BSO" in titles
        assert "Locatiemanager" in titles

    def test_empty_feed(self):
        items = _parse_rss_items(RSS_EMPTY)
        assert items == []

    def test_broken_xml(self):
        items = _parse_rss_items(RSS_BROKEN)
        assert items == []

    def test_no_category_gives_empty_list(self):
        items = _parse_rss_items(RSS_TWO_ITEMS)
        locatiemanager = next(i for i in items if i["title"] == "Locatiemanager")
        assert locatiemanager["categories"] == []

    def test_no_channel_element_returns_empty(self):
        """RSS without <channel> element returns empty list."""
        items = _parse_rss_items(RSS_NO_CHANNEL)
        assert items == []

    def test_guid_falls_back_to_link(self):
        rss = """<?xml version="1.0"?>
        <rss version="2.0"><channel>
          <item>
            <title>Test vacature</title>
            <link>https://example.com/jobs/1</link>
            <description>Test</description>
          </item>
        </channel></rss>"""
        items = _parse_rss_items(rss)
        assert items[0]["guid"] == "https://example.com/jobs/1"


# ── _extract_job_fields ──────────────────────────────────────────────────────

class TestExtractJobFields:
    def _make_item(self, desc_html="", categories=None, title="Test", link="https://example.com/jobs/1", guid="1"):
        return {
            "title": title,
            "link": link,
            "guid": guid,
            "description_html": desc_html,
            "categories": categories or [],
        }

    def test_basic_fields(self):
        item = self._make_item(title="PM KDV", link="https://norlandia.nl/jobs/1", guid="guid-1")
        job = _extract_job_fields(item)
        assert job["title"] == "PM KDV"
        assert job["source_url"] == "https://norlandia.nl/jobs/1"
        assert job["external_id"] == "guid-1"

    def test_hours_extracted_from_description(self):
        item = self._make_item(desc_html="<p>Werken voor 24 - 32 uur per week</p>")
        job = _extract_job_fields(item)
        assert job["hours_min"] == 24
        assert job["hours_max"] == 32

    def test_no_hours_gives_none(self):
        item = self._make_item(desc_html="<p>Leuk werk in Amsterdam</p>")
        job = _extract_job_fields(item)
        assert job["hours_min"] is None
        assert job["hours_max"] is None

    def test_salary_extracted(self):
        item = self._make_item(desc_html="<p>Salaris € 2.500 - € 3.000 per maand</p>")
        job = _extract_job_fields(item)
        assert job["salary_min"] == 2500.0
        assert job["salary_max"] == 3000.0

    def test_no_salary_gives_none(self):
        item = self._make_item(desc_html="<p>Marktconform salaris</p>")
        job = _extract_job_fields(item)
        assert job["salary_min"] is None
        assert job["salary_max"] is None

    def test_short_description_max_300(self):
        item = self._make_item(desc_html=f"<p>{'x' * 1000}</p>")
        job = _extract_job_fields(item)
        assert len(job["short_description"]) <= 300

    def test_html_stripped_from_description(self):
        item = self._make_item(desc_html="<p>Wij zoeken een <b>enthousiaste</b> PM</p>")
        job = _extract_job_fields(item)
        assert "<b>" not in job["description"]
        assert "enthousiaste" in job["description"]


# ── NorlandiaScraper.fetch_jobs (gemockt) ────────────────────────────────────

class TestNorlandiaScraperFetchJobs:
    def test_returns_jobs_from_rss(self):
        scraper = NorlandiaScraper()
        mock_resp = MagicMock()
        mock_resp.text = RSS_TWO_ITEMS
        mock_resp.raise_for_status = MagicMock()

        with patch("scrapers.teamtailor_rss.requests.get", return_value=mock_resp):
            jobs = scraper.fetch_jobs()

        assert len(jobs) == 2
        assert all(j["source_url"].startswith("http") for j in jobs)
        assert all(j["title"] for j in jobs)

    def test_returns_empty_on_http_error(self):
        scraper = NorlandiaScraper()
        with patch("scrapers.teamtailor_rss.requests.get", side_effect=Exception("Connection refused")):
            jobs = scraper.fetch_jobs()
        assert jobs == []

    def test_returns_empty_on_broken_xml(self):
        scraper = NorlandiaScraper()
        mock_resp = MagicMock()
        mock_resp.text = RSS_BROKEN
        mock_resp.raise_for_status = MagicMock()

        with patch("scrapers.teamtailor_rss.requests.get", return_value=mock_resp):
            jobs = scraper.fetch_jobs()
        assert jobs == []

    def test_company_slug(self):
        assert NorlandiaScraper.company_slug == "norlandia"

    def test_rss_url_correct(self):
        assert "norlandia.nl" in NorlandiaScraper.rss_url
        assert NorlandiaScraper.rss_url.endswith(".rss")


class TestNorlandiaFetchCompany:
    def test_returns_dict_with_name(self):
        scraper = NorlandiaScraper()
        resp = MagicMock()
        resp.text = '<html><head><meta name="description" content="Norlandia kinderopvang"></head><body></body></html>'
        resp.raise_for_status = MagicMock()
        with patch("scrapers.teamtailor_rss.requests.get", return_value=resp):
            company = scraper.fetch_company()
        assert "Norlandia" in company["name"]
        assert company["description"] == "Norlandia kinderopvang"

    def test_graceful_on_error(self):
        scraper = NorlandiaScraper()
        with patch("scrapers.teamtailor_rss.requests.get", side_effect=Exception("SSL")):
            company = scraper.fetch_company()
        assert "Norlandia" in company["name"]
        assert company["logo_url"] == ""


# ── _fetch_detail_location ───────────────────────────────────────────────────

class TestFetchDetailLocation:
    def _mock_get(self, html):
        resp = MagicMock()
        resp.text = html
        resp.raise_for_status = MagicMock()
        return resp

    def test_teamtailor_location_selector(self):
        html = """<html><body>
            <span data-qa="job-location">Amsterdam</span>
        </body></html>"""
        with patch("scrapers.teamtailor_rss.requests.get", return_value=self._mock_get(html)):
            city, postcode, location_name = _fetch_detail_location("https://example.com/jobs/1")
        assert city == "Amsterdam"
        assert location_name == "Amsterdam"

    def test_fallback_to_postcode_scan(self):
        html = """<html><body>
            <p>Kom werken op Laan van Noi 12, 2593BH Den Haag</p>
        </body></html>"""
        with patch("scrapers.teamtailor_rss.requests.get", return_value=self._mock_get(html)):
            city, postcode, location_name = _fetch_detail_location("https://example.com/jobs/2")
        assert postcode == "2593BH"
        assert "2593BH" in location_name

    def test_returns_empty_on_error(self):
        with patch("scrapers.teamtailor_rss.requests.get", side_effect=Exception("timeout")):
            city, postcode, location_name = _fetch_detail_location("https://example.com/jobs/3")
        assert city == ""
        assert postcode == ""
        assert location_name == ""

    def test_no_location_info_returns_empty(self):
        html = """<html><body><p>Leuke vacature zonder adres.</p></body></html>"""
        with patch("scrapers.teamtailor_rss.requests.get", return_value=self._mock_get(html)):
            city, postcode, location_name = _fetch_detail_location("https://example.com/jobs/4")
        assert city == ""
        assert postcode == ""
        assert location_name == ""


# ── Integratie tests (echte site, vereist netwerk) ───────────────────────────

@pytest.mark.integration
class TestNorlandiaLive:
    """Uitvoeren met: pytest -m integration tests/test_norlandia.py -v -s"""

    def test_rss_feed_bereikbaar(self):
        import requests
        resp = requests.get(NorlandiaScraper.rss_url, timeout=15)
        assert resp.status_code == 200
        assert "xml" in resp.headers.get("content-type", "").lower() or resp.text.strip().startswith("<")

    def test_volledige_scrape(self):
        scraper = NorlandiaScraper()
        jobs = scraper.fetch_jobs()
        print(f"\n[INFO] Norlandia: {len(jobs)} vacatures gevonden")
        if jobs:
            print(f"  Eerste: {jobs[0]['title']} | {jobs[0]['source_url']}")
        assert isinstance(jobs, list)
        if len(jobs) == 0:
            pytest.skip("Geen vacatures gevonden (mogelijk tijdelijk leeg)")
        job = jobs[0]
        assert job["source_url"].startswith("http")
        assert len(job["title"]) > 3
