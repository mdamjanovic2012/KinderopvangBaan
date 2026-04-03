"""Kinderopvang Morgen — https://www.kinderopvangmorgen.nl"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class MorgenScraper(WordPressJobsScraper):
    company_slug     = "morgen"
    company_name     = "Kinderopvang Morgen"
    listing_url      = "https://www.kinderopvangmorgen.nl/vacatures/"
    website_url      = "https://www.kinderopvangmorgen.nl"
    job_url_contains = "/vacatures/"
