"""GMK Kinderopvang — https://werkenbijgmk.nl"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class GmkScraper(WordPressJobsScraper):
    company_slug     = "gmk"
    company_name     = "GMK Kinderopvang"
    listing_url      = "https://werkenbijgmk.nl/vacatures/"
    website_url      = "https://werkenbijgmk.nl"
    job_url_contains = "/vacatures/"
