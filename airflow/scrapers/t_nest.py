"""
't Nest Kinderopvang scraper — werkenbijtnest.nl

STATUS: OFFLINE — domein werkenbijtnest.nl is NXDOMAIN (niet meer actief).
fetch_jobs() geeft altijd een lege lijst terug totdat het domein weer bereikbaar is.
"""

import logging

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

DOMAIN = "werkenbijtnest.nl"


class TNestScraper(BaseScraper):
    company_slug = "t-nest"

    def fetch_company(self) -> dict:
        return {
            "name":          "'t Nest Kinderopvang",
            "website":       f"https://www.{DOMAIN}",
            "job_board_url": f"https://www.{DOMAIN}",
            "scraper_class": "TNestScraper",
            "logo_url":      "",
            "description":   "",
        }

    def fetch_jobs(self) -> list[dict]:
        logger.warning(
            f"[{self.company_slug}] Domein {DOMAIN} is NXDOMAIN (offline). "
            "Geen vacatures opgehaald. Controleer of het domein weer actief is."
        )
        return []
