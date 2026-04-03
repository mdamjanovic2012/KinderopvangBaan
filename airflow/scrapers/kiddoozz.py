"""Kiddoozz — https://kiddoozz.nl"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class KiddoozzScraper(WordPressJobsScraper):
    company_slug     = "kiddoozz"
    company_name     = "Kiddoozz"
    listing_url      = "https://kiddoozz.nl/vacatures/"
    website_url      = "https://kiddoozz.nl"
    job_url_contains = "/vacatures/"
