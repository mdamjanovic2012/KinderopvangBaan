"""
Woest Zuid scraper — werkenbij.woestzuid.nl

Platform: WordPress Jobs
URL pattern: /vacatures/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class WoestZuidScraper(WordPressJobsScraper):
    company_slug     = "woest-zuid"
    company_name     = "Woest Zuid"
    listing_url      = "https://werkenbij.woestzuid.nl/vacatures/pedagogisch-sportmedewerker/"
    website_url      = "https://werkenbij.woestzuid.nl"
    job_url_contains = "/vacatures/"
