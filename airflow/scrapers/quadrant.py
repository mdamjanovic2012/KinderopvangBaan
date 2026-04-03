"""Quadrant Kindercentra — https://werkenbij.quadrantkindercentra.nl"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class QuadrantScraper(WordPressJobsScraper):
    company_slug     = "quadrant"
    company_name     = "Quadrant Kindercentra"
    listing_url      = "https://werkenbij.quadrantkindercentra.nl/vacatures/"
    website_url      = "https://werkenbij.quadrantkindercentra.nl"
    job_url_contains = "/vacatures/"
