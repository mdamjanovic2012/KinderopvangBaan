"""
Wilde Wijs Kinderopvang scraper — werkenbij.kinderopvangwildewijs.nl

Platform: WordPress Jobs
URL pattern: /vacatures/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class WildewijsScraper(WordPressJobsScraper):
    company_slug     = "wildewijs"
    company_name     = "Wilde Wijs Kinderopvang"
    listing_url      = "https://werkenbij.kinderopvangwildewijs.nl/vacatures/"
    website_url      = "https://werkenbij.kinderopvangwildewijs.nl"
    job_url_contains = "/vacatures/"
