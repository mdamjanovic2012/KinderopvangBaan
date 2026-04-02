"""
Dak Kindercentra scraper — dakkindercentra.nl

Platform: WordPress. No JobPosting JSON-LD — uses HTML fallback parsing.
Two listing pages: pedagogisch medewerkers and servicebureau.
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class DakScraper(WordPressJobsScraper):
    company_slug       = "dak"
    company_name       = "Dak Kindercentra"
    listing_url        = "https://www.dakkindercentra.nl/vacatures/"
    website_url        = "https://www.dakkindercentra.nl"
    job_url_contains   = "/vacatures/"
    extra_listing_urls = [
        "https://www.dakkindercentra.nl/vacatures-servicebureau/",
    ]
