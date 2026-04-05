"""
Ska Kinderopvang scraper — werkenbijska.nl

Platform: WordPress. No JSON-LD.
URL pattern: /vacature/{slug}
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class SkaScraper(WordPressJobsScraper):
    company_slug     = "ska"
    company_name     = "Ska Kinderopvang"
    listing_url      = "https://werkenbijska.nl/"
    website_url      = "https://werkenbijska.nl"
    job_url_contains = "/vacature/"
