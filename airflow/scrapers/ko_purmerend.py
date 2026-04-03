"""
Kinderopvang Purmerend scraper — kinderopvangpurmerend.nl

Platform: WordPress Jobs
URL pattern: /vacatures/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class KoPurmerendScraper(WordPressJobsScraper):
    company_slug     = "ko-purmerend"
    company_name     = "Kinderopvang Purmerend"
    listing_url      = "https://kinderopvangpurmerend.nl/vacatures/"
    website_url      = "https://kinderopvangpurmerend.nl"
    job_url_contains = "/vacatures/"
