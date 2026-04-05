"""
Monkey Donky scraper — www.werkenindekinderopvang.work

Platform: Teamtailor (RSS feed bevestigd op 2026-04-03)
RSS feed: https://www.werkenindekinderopvang.work/jobs.rss
"""

from scrapers.teamtailor_rss import TeamtailorRssScraper


class MonkeyDonkyScraper(TeamtailorRssScraper):
    company_slug = "monkey-donky"
    rss_url      = "https://www.werkenindekinderopvang.work/jobs.rss"
    career_url   = "https://www.werkenindekinderopvang.work"
    company_name = "Monkey Donky"
