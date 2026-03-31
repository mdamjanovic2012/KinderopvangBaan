"""
Op Stoom Kinderopvang scraper — werkenbijopstoom.nl

Platform: WordPress. No JSON-LD.
URL pattern: /vacature/{slug}; listing at /vacatures/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class OpStoomScraper(WordPressJobsScraper):
    company_slug     = "op-stoom"
    company_name     = "Op Stoom Kinderopvang"
    listing_url      = "https://www.werkenbijopstoom.nl/vacatures/"
    website_url      = "https://www.werkenbijopstoom.nl"
    job_url_contains = "/vacature/"
