"""Scraper voor Atalenta — InSite/ColdFusion CMS server-side rendered vacaturepagina."""
from scrapers.wordpress_jobs import WordPressJobsScraper


class AtalentaScraper(WordPressJobsScraper):
    company_slug     = "atalenta"
    company_name     = "Atalenta"
    listing_url      = "https://werkenbij.atalenta.nl/vacatures/"
    website_url      = "https://werkenbij.atalenta.nl"
    job_url_contains = "/vacatures/"
