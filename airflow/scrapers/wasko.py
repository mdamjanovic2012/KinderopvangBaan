"""
Wasko Kinderopvang scraper — werkenbij.wasko.nl

Platform: WordPress. No JSON-LD.
URL pattern: /vacature/{slug}; listing at /onze-vacatures/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class WaskoScraper(WordPressJobsScraper):
    company_slug     = "wasko"
    company_name     = "Wasko Kinderopvang"
    listing_url      = "https://werkenbij.wasko.nl/onze-vacatures/"
    website_url      = "https://werkenbij.wasko.nl"
    job_url_contains = "/vacature/"
