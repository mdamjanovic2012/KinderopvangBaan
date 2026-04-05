"""
Xpect013 scraper — xpect013.nl

Platform: WordPress Jobs
URL pattern: /vacatures/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class Xpect013Scraper(WordPressJobsScraper):
    company_slug     = "xpect013"
    company_name     = "Xpect013"
    listing_url      = "https://www.xpect013.nl/werken-bij/vacatures"
    website_url      = "https://www.xpect013.nl"
    job_url_contains = "/vacatures/"
