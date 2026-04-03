"""Bzzzonder Kinderopvang — https://www.werkenbijbzzzonder.nl"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class BzzzonderScraper(WordPressJobsScraper):
    company_slug     = "bzzzonder"
    company_name     = "Bzzzonder Kinderopvang"
    listing_url      = "https://www.werkenbijbzzzonder.nl/vacatures/"
    website_url      = "https://www.werkenbijbzzzonder.nl"
    job_url_contains = "/vacatures/"
