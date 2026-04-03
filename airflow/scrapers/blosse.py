"""Scraper voor Blosse Kinderopvang — Webflow vacaturepagina."""
from scrapers.wordpress_jobs import WordPressJobsScraper


class BlosseScraper(WordPressJobsScraper):
    company_slug     = "blosse"
    company_name     = "Blosse Kinderopvang"
    listing_url      = "https://www.werkenbijblosse.nl/vacature"
    website_url      = "https://www.werkenbijblosse.nl"
    job_url_contains = "/vacature/"
