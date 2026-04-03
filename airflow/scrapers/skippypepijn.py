"""
SkippyPePijN scraper — www.skippypepijn.nl

Platform: Eigen CMS, server-side HTML.
Listing URL: https://www.skippypepijn.nl/over-ons/werken-bij-skippypepijn/
Job URLs:    /over-ons/werken-bij-skippypepijn/vacatures/{slug}/

Aanpak: WordPressJobsScraper met job_url_contains="/vacatures/"
De listing bevat links naar losse vacaturepagina's; elke pagina heeft
een JSON-LD JobPosting of valt terug op HTML parsing.
"""

import logging

from scrapers.wordpress_jobs import WordPressJobsScraper

logger = logging.getLogger(__name__)


class SkippyPePijNScraper(WordPressJobsScraper):
    company_slug     = "skippypepijn"
    company_name     = "SkippyPePijN"
    listing_url      = "https://www.skippypepijn.nl/over-ons/werken-bij-skippypepijn/"
    website_url      = "https://www.skippypepijn.nl"
    job_url_contains = "/vacatures/"
