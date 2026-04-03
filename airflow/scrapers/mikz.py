"""Scraper voor Mikz — SilverStripe server-side rendered vacaturepagina."""
from scrapers.wordpress_jobs import WordPressJobsScraper


class MikzScraper(WordPressJobsScraper):
    company_slug     = "mikz"
    company_name     = "Mikz"
    listing_url      = "https://www.mikz.nl/werkenenlerenbij/"
    website_url      = "https://www.mikz.nl"
    job_url_contains = "/werkenenlerenbij/"
