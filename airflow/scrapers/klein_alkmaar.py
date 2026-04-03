"""Klein Alkmaar — https://werkenbijkleinalkmaar.nl"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class KleinAlkmaarScraper(WordPressJobsScraper):
    company_slug     = "klein-alkmaar"
    company_name     = "Klein Alkmaar"
    listing_url      = "https://werkenbijkleinalkmaar.nl/vacatures/"
    website_url      = "https://werkenbijkleinalkmaar.nl"
    job_url_contains = "/vacatures/"
