"""Kosmo Kinderopvang — https://www.kosmo.nl"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class KosmoScraper(WordPressJobsScraper):
    company_slug     = "kosmo"
    company_name     = "Kosmo Kinderopvang"
    listing_url      = "https://www.kosmo.nl/vacatures"
    website_url      = "https://www.kosmo.nl"
    job_url_contains = "/vacatures"
