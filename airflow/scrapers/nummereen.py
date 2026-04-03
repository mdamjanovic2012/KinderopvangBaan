"""Nummereen Kinderopvang — https://werkenbijnummereen.com"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class NummereenScraper(WordPressJobsScraper):
    company_slug     = "nummereen"
    company_name     = "Nummereen Kinderopvang"
    listing_url      = "https://werkenbijnummereen.com/vacatures/"
    website_url      = "https://werkenbijnummereen.com"
    job_url_contains = "/vacatures/"
