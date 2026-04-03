"""
KinderRijk scraper — werkenbijkinderrijk.nl

Platform: WordPress Jobs
URL pattern: /vacatures/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class KinderrijkScraper(WordPressJobsScraper):
    company_slug     = "kinderrijk"
    company_name     = "KinderRijk"
    listing_url      = "https://www.werkenbijkinderrijk.nl/vacatures/"
    website_url      = "https://www.werkenbijkinderrijk.nl"
    job_url_contains = "/vacatures/"
