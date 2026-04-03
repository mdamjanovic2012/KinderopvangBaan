"""
Stichting GOO scraper — stichtinggoo.nl

Platform: WordPress Jobs
URL pattern: /vacatures/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class GooScraper(WordPressJobsScraper):
    company_slug     = "goo"
    company_name     = "Stichting GOO"
    listing_url      = "https://www.stichtinggoo.nl/vacatures"
    website_url      = "https://www.stichtinggoo.nl"
    job_url_contains = "/vacatures"
