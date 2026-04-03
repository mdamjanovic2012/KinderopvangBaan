"""
Avonturijn scraper — avonturijn.nl

Platform: WordPress Jobs
URL pattern: /vacatures/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class AvonturijnScraper(WordPressJobsScraper):
    company_slug     = "avonturijn"
    company_name     = "Avonturijn"
    listing_url      = "https://avonturijn.nl/vacatures/"
    website_url      = "https://avonturijn.nl"
    job_url_contains = "/vacatures/"
