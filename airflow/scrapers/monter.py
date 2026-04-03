"""
Monter Kinderopvang scraper — monterkinderopvang.nl

Platform: WordPress Jobs
URL pattern: /vacatures/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class MonterScraper(WordPressJobsScraper):
    company_slug     = "monter"
    company_name     = "Monter Kinderopvang"
    listing_url      = "https://monterkinderopvang.nl/vacatures-bij-monter-kinderopvang/"
    website_url      = "https://monterkinderopvang.nl"
    job_url_contains = "/vacatures/"
