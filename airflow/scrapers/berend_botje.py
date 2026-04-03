"""
Berend Botje scraper — berekendbotje.nl

STATUS: OFFLINE — domein berekendbotje.nl is NXDOMAIN (niet meer actief).
fetch_jobs() geeft altijd een lege lijst terug totdat het domein weer bereikbaar is.
"""

import logging

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

DOMAIN = "berekendbotje.nl"


class BerendBotjeScraper(BaseScraper):
    company_slug = "berend-botje"

    def fetch_company(self) -> dict:
        return {
            "name":          "Berend Botje",
            "website":       f"https://www.{DOMAIN}",
            "job_board_url": f"https://www.{DOMAIN}",
            "scraper_class": "BerendBotjeScraper",
            "logo_url":      "",
            "description":   "",
        }

    def fetch_jobs(self) -> list[dict]:
        logger.warning(
            f"[{self.company_slug}] Domein {DOMAIN} is NXDOMAIN (offline). "
            "Geen vacatures opgehaald. Controleer of het domein weer actief is."
        )
        return []
