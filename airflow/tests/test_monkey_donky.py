"""Unit tests for Monkey Donky scraper (Teamtailor RSS)."""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.monkey_donky import MonkeyDonkyScraper

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Monkey Donky Jobs</title>
    <link>https://www.werkenindekinderopvang.work</link>
    <description>Vacatures bij Monkey Donky</description>
    <item>
      <title>Pedagogisch Medewerker KDV</title>
      <link>https://www.werkenindekinderopvang.work/jobs/pm-kdv-123</link>
      <guid>pm-kdv-123</guid>
      <description>&lt;p&gt;We zoeken een PM voor 24-32 uur per week.&lt;/p&gt;</description>
      <pubDate>Fri, 28 Mar 2026 09:00:00 +0000</pubDate>
      <category>Kinderopvang</category>
    </item>
    <item>
      <title>Locatiemanager BSO</title>
      <link>https://www.werkenindekinderopvang.work/jobs/locatiemgr-bso-456</link>
      <guid>locatiemgr-bso-456</guid>
      <description>&lt;p&gt;Locatiemanager voor 36 uur per week.&lt;/p&gt;</description>
      <pubDate>Thu, 27 Mar 2026 10:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>"""

EMPTY_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel><title>No Jobs</title></channel>
</rss>"""


class TestMonkeyDonkyConfig:
    def test_company_slug(self):
        assert MonkeyDonkyScraper.company_slug == "monkey-donky"

    def test_rss_url(self):
        assert "werkenindekinderopvang.work" in MonkeyDonkyScraper.rss_url
        assert MonkeyDonkyScraper.rss_url.endswith("/jobs.rss")

    def test_career_url(self):
        assert MonkeyDonkyScraper.career_url.startswith("http")

    def test_company_name(self):
        assert MonkeyDonkyScraper.company_name == "Monkey Donky"


class TestMonkeyDonkyFetchJobs:
    def _mock_get(self, rss_text, detail_html="<html><body><p>Amsterdam</p></body></html>"):
        rss_r = MagicMock()
        rss_r.text = rss_text
        rss_r.raise_for_status = MagicMock()

        detail_r = MagicMock()
        detail_r.text = detail_html
        detail_r.raise_for_status = MagicMock()
        return rss_r, detail_r

    def test_returns_two_jobs(self):
        rss_r, detail_r = self._mock_get(SAMPLE_RSS)
        with patch("scrapers.teamtailor_rss.requests.get",
                   side_effect=[rss_r, detail_r, detail_r]):
            jobs = MonkeyDonkyScraper().fetch_jobs()
        assert len(jobs) == 2

    def test_titles_extracted(self):
        rss_r, detail_r = self._mock_get(SAMPLE_RSS)
        with patch("scrapers.teamtailor_rss.requests.get",
                   side_effect=[rss_r, detail_r, detail_r]):
            jobs = MonkeyDonkyScraper().fetch_jobs()
        titles = [j["title"] for j in jobs]
        assert "Pedagogisch Medewerker KDV" in titles
        assert "Locatiemanager BSO" in titles

    def test_source_urls_set(self):
        rss_r, detail_r = self._mock_get(SAMPLE_RSS)
        with patch("scrapers.teamtailor_rss.requests.get",
                   side_effect=[rss_r, detail_r, detail_r]):
            jobs = MonkeyDonkyScraper().fetch_jobs()
        for job in jobs:
            assert job["source_url"].startswith("http")

    def test_external_id_from_guid(self):
        rss_r, detail_r = self._mock_get(SAMPLE_RSS)
        with patch("scrapers.teamtailor_rss.requests.get",
                   side_effect=[rss_r, detail_r, detail_r]):
            jobs = MonkeyDonkyScraper().fetch_jobs()
        guids = [j["external_id"] for j in jobs]
        assert "pm-kdv-123" in guids

    def test_hours_extracted_from_description(self):
        rss_r, detail_r = self._mock_get(SAMPLE_RSS)
        with patch("scrapers.teamtailor_rss.requests.get",
                   side_effect=[rss_r, detail_r, detail_r]):
            jobs = MonkeyDonkyScraper().fetch_jobs()
        pm_job = next(j for j in jobs if "Pedagogisch" in j["title"])
        assert pm_job["hours_min"] == 24
        assert pm_job["hours_max"] == 32

    def test_empty_rss_returns_empty_list(self):
        rss_r, _ = self._mock_get(EMPTY_RSS)
        with patch("scrapers.teamtailor_rss.requests.get", return_value=rss_r):
            jobs = MonkeyDonkyScraper().fetch_jobs()
        assert jobs == []

    def test_network_error_returns_empty_list(self):
        with patch("scrapers.teamtailor_rss.requests.get", side_effect=Exception("timeout")):
            jobs = MonkeyDonkyScraper().fetch_jobs()
        assert jobs == []

    def test_malformed_rss_returns_empty_list(self):
        bad_r = MagicMock()
        bad_r.text = "this is not xml <<>>"
        bad_r.raise_for_status = MagicMock()
        with patch("scrapers.teamtailor_rss.requests.get", return_value=bad_r):
            jobs = MonkeyDonkyScraper().fetch_jobs()
        assert jobs == []


class TestMonkeyDonkyFetchCompany:
    def test_returns_company_name(self):
        resp = MagicMock()
        resp.text = '<html><head><meta name="description" content="Kinderopvang vacatures"></head><body></body></html>'
        resp.raise_for_status = MagicMock()
        with patch("scrapers.teamtailor_rss.requests.get", return_value=resp):
            company = MonkeyDonkyScraper().fetch_company()
        assert company["name"] == "Monkey Donky"

    def test_graceful_on_error(self):
        with patch("scrapers.teamtailor_rss.requests.get", side_effect=Exception("conn")):
            company = MonkeyDonkyScraper().fetch_company()
        assert company["name"] == "Monkey Donky"
        assert company["logo_url"] == ""


@pytest.mark.integration
class TestMonkeyDonkyLive:
    def test_rss_reachable(self):
        import requests
        resp = requests.get(MonkeyDonkyScraper.rss_url, timeout=15)
        assert resp.status_code == 200

    def test_full_scrape(self):
        scraper = MonkeyDonkyScraper()
        jobs = scraper.fetch_jobs()
        print(f"\n[monkey-donky] {len(jobs)} vacatures")
        assert isinstance(jobs, list)
        if jobs:
            assert jobs[0]["source_url"].startswith("http")
            assert jobs[0]["title"] != ""
