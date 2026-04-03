"""
Dichtbij Kinderopvang scraper — werkenbijdichtbij.nl

Platform: WordPress. No JSON-LD on detail pages (HTML fallback).
URL pattern: /vacature/{slug}
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class DichtbijScraper(WordPressJobsScraper):
    company_slug     = "dichtbij"
    company_name     = "Dichtbij Kinderopvang"
    listing_url      = "https://werkenbijdichtbij.nl/vacatures/"
    website_url      = "https://werkenbijdichtbij.nl"
    job_url_contains = "/vacature/"
