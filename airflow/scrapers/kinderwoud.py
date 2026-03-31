"""
Kinderwoud scraper — werkenbijkinderwoud.nl

Platform: WordPress with schema.org JobPosting JSON-LD.
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class KinderwoudScraper(WordPressJobsScraper):
    company_slug     = "kinderwoud"
    company_name     = "Kinderwoud Kinderopvang"
    listing_url      = "https://www.werkenbijkinderwoud.nl/vacatures/"
    website_url      = "https://www.werkenbijkinderwoud.nl"
    job_url_contains = "/vacatures/"
