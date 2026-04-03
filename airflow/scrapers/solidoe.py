"""Solidoe Kinderopvang — https://solidoe.nl"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class SolidoeScraper(WordPressJobsScraper):
    company_slug     = "solidoe"
    company_name     = "Solidoe Kinderopvang"
    listing_url      = "https://solidoe.nl/werken-bij-solidoe/vacatures/"
    website_url      = "https://solidoe.nl"
    job_url_contains = "/vacatures/"
