"""
Unit tests voor Doomijn scraper (Teamtailor RSS).
RSS parsing uitgebreid getest in test_norlandia.py (gedeelde base).
Hier: Doomijn-specifieke configuratie en integratie.
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.doomijn import DoomijnScraper


RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Doomijn jobs</title>
    <item>
      <title>Pedagogisch medewerker KDV</title>
      <link>https://komwerkenbij.doomijn.nl/jobs/10-pm-kdv</link>
      <guid>10-pm-kdv</guid>
      <description>&lt;p&gt;Wij zoeken een PM voor 20 - 28 uur per week in Zwolle.&lt;/p&gt;</description>
      <category>Kinderopvang</category>
    </item>
    <item>
      <title>Groepsleider BSO Zwolle</title>
      <link>https://komwerkenbij.doomijn.nl/jobs/11-groepsleider-bso</link>
      <guid>11-groepsleider-bso</guid>
      <description>&lt;p&gt;BSO locatie in Zwolle centrum.&lt;/p&gt;</description>
    </item>
  </channel>
</rss>"""


class TestDoomijnScraperConfig:
    def test_company_slug(self):
        assert DoomijnScraper.company_slug == "doomijn"

    def test_rss_url_correct(self):
        assert "doomijn.nl" in DoomijnScraper.rss_url
        assert DoomijnScraper.rss_url.endswith(".rss")

    def test_company_name(self):
        assert "Doomijn" in DoomijnScraper.company_name


class TestDoomijnScraperFetchJobs:
    def test_returns_jobs_from_rss(self):
        scraper = DoomijnScraper()
        mock_resp = MagicMock()
        mock_resp.text = RSS_SAMPLE
        mock_resp.raise_for_status = MagicMock()

        with patch("scrapers.teamtailor_rss.requests.get", return_value=mock_resp):
            jobs = scraper.fetch_jobs()

        assert len(jobs) == 2
        assert all(j["source_url"].startswith("http") for j in jobs)

    def test_hours_parsed(self):
        scraper = DoomijnScraper()
        mock_resp = MagicMock()
        mock_resp.text = RSS_SAMPLE
        mock_resp.raise_for_status = MagicMock()

        with patch("scrapers.teamtailor_rss.requests.get", return_value=mock_resp):
            jobs = scraper.fetch_jobs()

        pm_job = jobs[0]  # eerste job heeft uren in beschrijving
        assert pm_job["hours_min"] == 20
        assert pm_job["hours_max"] == 28

    def test_returns_empty_on_error(self):
        scraper = DoomijnScraper()
        with patch("scrapers.teamtailor_rss.requests.get", side_effect=Exception("timeout")):
            jobs = scraper.fetch_jobs()
        assert jobs == []


@pytest.mark.integration
class TestDoomijnLive:
    def test_rss_feed_bereikbaar(self):
        import requests
        resp = requests.get(DoomijnScraper.rss_url, timeout=15)
        assert resp.status_code == 200

    def test_volledige_scrape(self):
        scraper = DoomijnScraper()
        jobs = scraper.fetch_jobs()
        print(f"\n[INFO] Doomijn: {len(jobs)} vacatures gevonden")
        assert isinstance(jobs, list)
        if len(jobs) == 0:
            pytest.skip("Geen vacatures gevonden")
        assert jobs[0]["source_url"].startswith("http")
        assert len(jobs[0]["title"]) > 3
