"""
RIANT Kinderopvang scraper — werkenbijriant.nl

Platform: WordPress Jobs
URL pattern: /vacatures/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class RiantScraper(WordPressJobsScraper):
    company_slug     = "riant"
    company_name     = "RIANT Kinderopvang"
    listing_url      = "https://werkenbijriant.nl/vacatures/"
    website_url      = "https://werkenbijriant.nl"
    job_url_contains = "/vacatures/"
