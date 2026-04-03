"""Forte Kinderopvang — https://werkenbijforte.nl"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class ForteScraper(WordPressJobsScraper):
    company_slug     = "forte"
    company_name     = "Forte Kinderopvang"
    listing_url      = "https://werkenbijforte.nl/vacatures/"
    website_url      = "https://werkenbijforte.nl"
    job_url_contains = "/vacatures/"
