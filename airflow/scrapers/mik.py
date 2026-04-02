"""
MIK & PIW Groep scraper — werkenbijmikenpiwgroep.nl

Platform: WordPress. No JSON-LD.
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class MIKScraper(WordPressJobsScraper):
    company_slug     = "mik"
    company_name     = "MIK & PIW Groep"
    listing_url      = "https://werkenbijmikenpiwgroep.nl/vacatures/"
    website_url      = "https://werkenbijmikenpiwgroep.nl"
    job_url_contains = "/vacatures/"
