"""De Eerste Stap — https://werkenbijdeeerstestap.nl"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class DeEersteStapScraper(WordPressJobsScraper):
    company_slug     = "de-eerste-stap"
    company_name     = "De Eerste Stap"
    listing_url      = "https://werkenbijdeeerstestap.nl/vacatures"
    website_url      = "https://werkenbijdeeerstestap.nl"
    job_url_contains = "/vacature/"
