"""
Sinne Kinderopvang scraper — sinne.easycruit.com

Platform: EasyCruit (Visma ATS).
"""

from scrapers.easycruit import EasyCruitScraper


class SinneScraper(EasyCruitScraper):
    company_slug  = "sinne"
    company_name  = "Sinne Kinderopvang"
    easycruit_url = "https://sinne.easycruit.com/"
    website_url   = "https://www.sinnekinderopvang.nl"
