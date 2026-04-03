"""
TintelTuin scraper — tinteltuin.nl

Platform: WordPress with schema.org JobPosting JSON-LD.
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class TintelTuinScraper(WordPressJobsScraper):
    company_slug     = "tinteltuin"
    company_name     = "TintelTuin"
    listing_url      = "https://tinteltuin.nl/vacatures/"
    website_url      = "https://tinteltuin.nl"
    job_url_contains = "/vacatures/"
