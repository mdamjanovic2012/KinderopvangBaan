"""
De Lange Keizer scraper — delangekeizer.nl

Platform: WordPress Jobs
URL pattern: /vacatures/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class DeLangeKeizerScraper(WordPressJobsScraper):
    company_slug     = "de-lange-keizer"
    company_name     = "De Lange Keizer"
    listing_url      = "https://delangekeizer.nl/personeel/vacatures/"
    website_url      = "https://delangekeizer.nl"
    job_url_contains = "/vacatures/"
