"""
Kinderopvang KOOS scraper — kinderopvangkoos.nl

Platform: WordPress Jobs
URL pattern: /werken-bij/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class KoosScraper(WordPressJobsScraper):
    company_slug     = "koos"
    company_name     = "Kinderopvang KOOS"
    listing_url      = "https://www.kinderopvangkoos.nl/werken-bij/"
    website_url      = "https://www.kinderopvangkoos.nl"
    job_url_contains = "/werken-bij/"
