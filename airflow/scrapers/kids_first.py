"""
Kids First scraper — werkenbijkidsfirst.nl

Platform: WordPress. No JSON-LD.
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class KidsFirstScraper(WordPressJobsScraper):
    company_slug     = "kids-first"
    company_name     = "Kids First Kinderopvang"
    listing_url      = "https://werkenbijkidsfirst.nl/vacatures/"
    website_url      = "https://werkenbijkidsfirst.nl"
    job_url_contains = "/vacatures/"
