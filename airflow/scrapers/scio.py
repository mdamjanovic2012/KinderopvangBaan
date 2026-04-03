"""
SCIO Kinderopvang scraper — werkenbij.sciogroep.nl

Platform: WordPress Jobs
URL pattern: /vacatures/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class ScioScraper(WordPressJobsScraper):
    company_slug     = "scio"
    company_name     = "SCIO Kinderopvang"
    listing_url      = "https://werkenbij.sciogroep.nl/"
    website_url      = "https://werkenbij.sciogroep.nl"
    job_url_contains = "/vacatures/"
