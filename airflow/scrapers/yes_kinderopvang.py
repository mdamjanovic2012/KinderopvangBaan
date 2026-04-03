"""Scraper voor Yes! Kinderopvang — WordPress vacaturepagina."""
from scrapers.wordpress_jobs import WordPressJobsScraper


class YesKinderopvangScraper(WordPressJobsScraper):
    company_slug     = "yes-kinderopvang"
    company_name     = "Yes! Kinderopvang"
    listing_url      = "https://www.werkenbijyes.nl/vacatures/"
    website_url      = "https://www.werkenbijyes.nl"
    job_url_contains = "/vacatures/"
