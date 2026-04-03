"""
BijdeHandjes scraper — bijdehandjes.nl

Platform: WordPress with schema.org JobPosting JSON-LD (in @graph).
URL pattern: /vacatures/{id}-{slug}
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class BijdeHandjesScraper(WordPressJobsScraper):
    company_slug     = "bijdehandjes"
    company_name     = "BijdeHandjes"
    listing_url      = "https://www.bijdehandjes.nl/vacatures/"
    website_url      = "https://www.bijdehandjes.nl"
    job_url_contains = "/vacatures/"
