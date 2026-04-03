"""SKID Kinderopvang — https://skidkinderopvang.nl"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class SkidScraper(WordPressJobsScraper):
    company_slug     = "skid"
    company_name     = "SKID Kinderopvang"
    listing_url      = "https://skidkinderopvang.nl/vacatures/"
    website_url      = "https://skidkinderopvang.nl"
    job_url_contains = "/vacatures/"
