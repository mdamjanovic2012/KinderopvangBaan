"""
Kidscasa scraper — kidscasa.nl

Platform: WordPress Jobs
URL pattern: /vacatures/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class KidscasaScraper(WordPressJobsScraper):
    company_slug     = "kidscasa"
    company_name     = "Kidscasa"
    listing_url      = "https://kidscasa.nl/organisatie/vacatures/"
    website_url      = "https://kidscasa.nl"
    job_url_contains = "/vacatures/"
