"""
Doomijn Kinderopvang scraper — komwerkenbij.doomijn.nl

Platform: Teamtailor (RSS feed, geen API-sleutel nodig)
RSS feed: https://komwerkenbij.doomijn.nl/jobs.rss
"""

from scrapers.teamtailor_rss import TeamtailorRssScraper


class DoomijnScraper(TeamtailorRssScraper):
    company_slug = "doomijn"
    rss_url      = "https://komwerkenbij.doomijn.nl/jobs.rss"
    career_url   = "https://komwerkenbij.doomijn.nl"
    company_name = "Doomijn Kinderopvang"
