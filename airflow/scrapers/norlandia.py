"""
Norlandia kinderopvang scraper — werkenbij.norlandia.nl

Platform: Teamtailor (RSS feed, geen API-sleutel nodig)
RSS feed: https://werkenbij.norlandia.nl/jobs.rss
"""

from scrapers.teamtailor_rss import TeamtailorRssScraper


class NorlandiaScraper(TeamtailorRssScraper):
    company_slug = "norlandia"
    rss_url      = "https://werkenbij.norlandia.nl/jobs.rss"
    career_url   = "https://werkenbij.norlandia.nl"
    company_name = "Norlandia kinderopvang"
