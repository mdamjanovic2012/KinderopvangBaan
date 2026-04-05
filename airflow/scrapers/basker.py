"""Scraper voor Basker — Drupal 10 server-side rendered vacaturepagina."""
from scrapers.wordpress_jobs import WordPressJobsScraper


class BaskerScraper(WordPressJobsScraper):
    company_slug     = "basker"
    company_name     = "Basker"
    listing_url      = "https://www.basker.nl/werken-bij/vacatures"
    website_url      = "https://www.basker.nl"
    job_url_contains = "/vacatures/"
