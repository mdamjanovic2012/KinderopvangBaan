"""
SKDD Kinderopvang scraper — werkenbijskdd.nl

Platform: WordPress Jobs
URL pattern: /vacatures/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class SkddScraper(WordPressJobsScraper):
    company_slug     = "skdd"
    company_name     = "SKDD Kinderopvang"
    listing_url      = "https://www.werkenbijskdd.nl/vacatures"
    website_url      = "https://www.werkenbijskdd.nl"
    job_url_contains = "/vacatures"
