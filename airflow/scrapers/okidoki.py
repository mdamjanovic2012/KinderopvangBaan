"""
Okidoki Kinderopvang scraper — okidoki-kdv.nl

Platform: WordPress Jobs
URL pattern: /werkenbij/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class OkidokiScraper(WordPressJobsScraper):
    company_slug     = "okidoki"
    company_name     = "Okidoki Kinderopvang"
    listing_url      = "https://okidoki-kdv.nl/werkenbij/"
    website_url      = "https://okidoki-kdv.nl"
    job_url_contains = "/werkenbij/"
