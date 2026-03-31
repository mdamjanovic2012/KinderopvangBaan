"""
Samenwerkende Kinderopvang scraper — samenwerkendekinderopvang.nl

Platform: WordPress met schema.org JobPosting JSON-LD
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class SamenwerkendeKOScraper(WordPressJobsScraper):
    company_slug     = "samenwerkende-ko"
    company_name     = "Samenwerkende Kinderopvang"
    listing_url      = "https://samenwerkendekinderopvang.nl/vacatures/"
    website_url      = "https://samenwerkendekinderopvang.nl"
    job_url_contains = "/vacatures/"
