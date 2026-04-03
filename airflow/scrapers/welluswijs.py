"""
Welluswijs Kinderopvang scraper — welluswijs.nl

Platform: WordPress Jobs
URL pattern: /vacatures/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class WelluswijsScraper(WordPressJobsScraper):
    company_slug     = "welluswijs"
    company_name     = "Welluswijs Kinderopvang"
    listing_url      = "https://www.welluswijs.nl/vacatures/"
    website_url      = "https://www.welluswijs.nl"
    job_url_contains = "/vacatures/"
