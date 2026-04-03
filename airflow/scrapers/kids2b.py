"""
Kids2b scraper — kids2b.nl

Platform: WordPress Jobs
URL pattern: /kids2b-vacatures
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class Kids2bScraper(WordPressJobsScraper):
    company_slug     = "kids2b"
    company_name     = "Kids2b"
    listing_url      = "https://www.kids2b.nl/kom-werken-bij-kids2b-en-wees-de-expert-in-kindontwikkeling/kids2b-vacatures"
    website_url      = "https://www.kids2b.nl"
    job_url_contains = "/kids2b-vacatures"
