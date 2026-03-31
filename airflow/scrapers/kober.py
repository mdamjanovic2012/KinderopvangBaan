"""
Kober Kinderopvang scraper — werkenbijkober.nl

Platform: WordPress (no JSON-LD — uses HTML fallback parsing)
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class KoberScraper(WordPressJobsScraper):
    company_slug     = "kober"
    company_name     = "Kober Kinderopvang"
    listing_url      = "https://werkenbijkober.nl/vacatures/"
    website_url      = "https://werkenbijkober.nl"
    job_url_contains = "/vacatures/"
