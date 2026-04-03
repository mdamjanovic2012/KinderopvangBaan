"""Berend Botje Kinderopvang — werkenbijberendbotje.nl"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class BerendBotjeScraper(WordPressJobsScraper):
    company_slug     = "berend-botje"
    company_name     = "Berend Botje"
    listing_url      = "https://werkenbijberendbotje.nl/vacatures"
    website_url      = "https://werkenbijberendbotje.nl"
    job_url_contains = "/vacatures/"
