"""SKBNM Kinderopvang — https://werkenbij.skbnm.nl"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class SkbnmScraper(WordPressJobsScraper):
    company_slug     = "skbnm"
    company_name     = "SKBNM Kinderopvang"
    listing_url      = "https://werkenbij.skbnm.nl/vacatures/"
    website_url      = "https://werkenbij.skbnm.nl"
    job_url_contains = "/vacatures/"
