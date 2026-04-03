"""Vlietkinderen — https://werkenbij.vlietkinderen.nl"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class VlietkinderenScraper(WordPressJobsScraper):
    company_slug     = "vlietkinderen"
    company_name     = "Vlietkinderen"
    listing_url      = "https://werkenbij.vlietkinderen.nl/vacatures/"
    website_url      = "https://werkenbij.vlietkinderen.nl"
    job_url_contains = "/vacature/"
