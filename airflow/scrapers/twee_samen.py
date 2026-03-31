"""
2Samen scraper — werkenbij2samen.nl

Platform: WordPress. No JSON-LD.
URL pattern: /vacature/{slug} (singular, not /vacatures/).
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class TweeSamenScraper(WordPressJobsScraper):
    company_slug     = "2samen"
    company_name     = "2Samen Kinderopvang"
    listing_url      = "https://www.werkenbij2samen.nl/vacatures/"
    website_url      = "https://www.werkenbij2samen.nl"
    job_url_contains = "/vacature/"  # Singular — detail pages are /vacature/{slug}
