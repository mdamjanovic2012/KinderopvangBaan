"""
Junis Kinderopvang scraper — werkenbijjunis.nl

Platform: WordPress Jobs
URL pattern: /vacature/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class JunisScraper(WordPressJobsScraper):
    company_slug     = "junis"
    company_name     = "Junis Kinderopvang"
    listing_url      = "https://werkenbijjunis.nl/vacature/"
    website_url      = "https://werkenbijjunis.nl"
    job_url_contains = "/vacature/"
