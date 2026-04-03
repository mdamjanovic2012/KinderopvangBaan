"""
Kindertuin scraper — kindertuin.com

Platform: WordPress Jobs
URL pattern: /werken-bij/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class KindertuinScraper(WordPressJobsScraper):
    company_slug     = "kindertuin"
    company_name     = "Kindertuin"
    listing_url      = "https://www.kindertuin.com/werken-bij/"
    website_url      = "https://www.kindertuin.com"
    job_url_contains = "/werken-bij/"
