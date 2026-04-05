"""
LPS Kinderopvang scraper — werkenbijlps.nl

Platform: WordPress Jobs
URL pattern: /vacatures-bij-lps/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class LpsScraper(WordPressJobsScraper):
    company_slug     = "lps"
    company_name     = "LPS Kinderopvang"
    listing_url      = "https://www.werkenbijlps.nl/vacatures-bij-lps/"
    website_url      = "https://www.werkenbijlps.nl"
    job_url_contains = "/vacatures-bij-lps/"
