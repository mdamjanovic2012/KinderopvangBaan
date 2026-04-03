"""
KDV Kindernet scraper — kdvkindernet.nl

Platform: WordPress Jobs
URL pattern: /vacancies/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class KindernetScraper(WordPressJobsScraper):
    company_slug     = "kindernet"
    company_name     = "KDV Kindernet"
    listing_url      = "https://kdvkindernet.nl/vacancies/"
    website_url      = "https://kdvkindernet.nl"
    job_url_contains = "/vacancies/"
