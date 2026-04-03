"""KSH Kinderopvang — https://www.werkenbijksh.nl"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class KshScraper(WordPressJobsScraper):
    company_slug     = "ksh"
    company_name     = "KSH Kinderopvang"
    listing_url      = "https://www.werkenbijksh.nl/vacatures/"
    website_url      = "https://www.werkenbijksh.nl"
    job_url_contains = "/vacatures/"
