"""
CKO KleurRijk scraper — kleurrijkkinderopvang.nl

Platform: WordPress Jobs
URL pattern: /vacatures/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class KleurrijkScraper(WordPressJobsScraper):
    company_slug     = "kleurrijk"
    company_name     = "CKO KleurRijk"
    listing_url      = "https://www.kleurrijkkinderopvang.nl/vacatures/"
    website_url      = "https://www.kleurrijkkinderopvang.nl"
    job_url_contains = "/vacatures/"
