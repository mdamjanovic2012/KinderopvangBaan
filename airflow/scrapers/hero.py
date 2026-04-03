"""
Hero Kindercentra scraper — herokindercentra.nl

Platform: WordPress Jobs
URL pattern: /vacatures/
Listing pages: kinderdagverblijf, bso, peuteropvang
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class HeroScraper(WordPressJobsScraper):
    company_slug        = "hero"
    company_name        = "Hero Kindercentra"
    listing_url         = "https://www.herokindercentra.nl/vacatures/kinderdagverblijf/"
    extra_listing_urls  = [
        "https://www.herokindercentra.nl/vacatures/bso/",
        "https://www.herokindercentra.nl/vacatures/peuteropvang/",
    ]
    website_url         = "https://www.herokindercentra.nl"
    job_url_contains    = "/vacatures-overzicht/"
