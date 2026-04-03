"""Kinderopvang Friesland — https://www.kinderopvangfriesland.nl"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class KoFrieslandScraper(WordPressJobsScraper):
    company_slug     = "ko-friesland"
    company_name     = "Kinderopvang Friesland"
    listing_url      = "https://www.kinderopvangfriesland.nl/vacatures/"
    website_url      = "https://www.kinderopvangfriesland.nl"
    job_url_contains = "/vacatures/"
