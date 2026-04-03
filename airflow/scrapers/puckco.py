"""
Puck&Co scraper — puckenco.nl

Platform: WordPress Jobs
URL pattern: /werken-bij/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class PuckcoScraper(WordPressJobsScraper):
    company_slug     = "puckco"
    company_name     = "Puck&Co"
    listing_url      = "https://www.puckenco.nl/werken-bij"
    website_url      = "https://www.puckenco.nl"
    job_url_contains = "/werken-bij/"
