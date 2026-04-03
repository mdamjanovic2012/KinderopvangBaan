"""
Hoera Kindercentra scraper — werkenbijhoera.nl

Platform: WordPress Jobs
URL pattern: /vacancies/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class HoeraScraper(WordPressJobsScraper):
    company_slug     = "hoera"
    company_name     = "Hoera Kindercentra"
    listing_url      = "https://werkenbijhoera.nl/vacancies/"
    website_url      = "https://werkenbijhoera.nl"
    job_url_contains = "/vacancies/"
