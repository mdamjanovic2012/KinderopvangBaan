"""FloreoKids — https://werkenbijfloreokids.nl"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class FloreoKidsScraper(WordPressJobsScraper):
    company_slug     = "floreokids"
    company_name     = "FloreoKids"
    listing_url      = "https://werkenbijfloreokids.nl/vacatures/"
    website_url      = "https://werkenbijfloreokids.nl"
    job_url_contains = "/vacatures/"
