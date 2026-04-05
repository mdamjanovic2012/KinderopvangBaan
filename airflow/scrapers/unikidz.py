"""UniKidz — https://werkenbijunikidz.nl"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class UniKidzScraper(WordPressJobsScraper):
    company_slug     = "unikidz"
    company_name     = "UniKidz"
    listing_url      = "https://werkenbijunikidz.nl/vacatures/"
    website_url      = "https://werkenbijunikidz.nl"
    job_url_contains = "/vacatures/"
