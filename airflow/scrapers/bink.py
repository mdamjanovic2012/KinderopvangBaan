"""
Bink Kinderopvang scraper — werkenbijbink.nl

Platform: WordPress. No JSON-LD.
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class BinkScraper(WordPressJobsScraper):
    company_slug     = "bink"
    company_name     = "Bink Kinderopvang"
    listing_url      = "https://werkenbijbink.nl/vacatures/"
    website_url      = "https://werkenbijbink.nl"
    job_url_contains = "/vacatures/"
