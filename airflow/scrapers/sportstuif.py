"""Scraper voor Sportstuif — Laravel server-side rendered vacaturepagina."""
from scrapers.wordpress_jobs import WordPressJobsScraper


class SportstuifScraper(WordPressJobsScraper):
    company_slug     = "sportstuif"
    company_name     = "Sportstuif"
    listing_url      = "https://www.sportstuif.nl/vacatures"
    website_url      = "https://www.sportstuif.nl"
    job_url_contains = "/vacatures/"
