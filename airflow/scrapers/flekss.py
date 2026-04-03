"""
Sport-BSO Flekss scraper — flekss.nl

Platform: WordPress Jobs
URL pattern: /werken-bij-flekss/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class FlekssScraper(WordPressJobsScraper):
    company_slug     = "flekss"
    company_name     = "Sport-BSO Flekss"
    listing_url      = "https://flekss.nl/werken-bij-flekss/"
    website_url      = "https://flekss.nl"
    job_url_contains = "/werken-bij-flekss/"
