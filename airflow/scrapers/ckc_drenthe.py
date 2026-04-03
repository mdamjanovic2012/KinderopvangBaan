"""
CKC Drenthe scraper — www.werkenbijckcdrenthe.nl

Platform: Eigen systeem (GetNoticed recruitment platform), GEEN Teamtailor.
Gecontroleerd op 2026-04-03: geen publieke RSS feed beschikbaar.
De vacatures worden server-side gerenderd via een eigen platform zonder publieke feed-URL.

TODO: CKC Drenthe gebruikt een custom recruitment systeem (GetNoticed).
      Een directe API-integratie of HTML-scraper is nodig.
      Neem contact op met de beheerder of onderzoek de GetNoticed API documentatie:
      https://www.werkenbijckcdrenthe.nl/vacatures

NOTE: Deze klasse is een tijdelijke stub. fetch_jobs() geeft altijd een lege lijst terug
      totdat een werkende integratie is geïmplementeerd.
"""

import logging

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class CKCDrentheScraper(BaseScraper):
    company_slug = "ckc-drenthe"
    company_name = "CKC Drenthe"
    career_url   = "https://www.werkenbijckcdrenthe.nl"

    def fetch_company(self) -> dict:
        return {
            "name":          self.company_name,
            "website":       self.career_url,
            "job_board_url": self.career_url,
            "scraper_class": self.__class__.__name__,
            "logo_url":      "",
            "description":   "",
        }

    def fetch_jobs(self) -> list[dict]:
        logger.warning(
            f"[{self.company_slug}] Geen werkende RSS/API feed beschikbaar. "
            "CKC Drenthe gebruikt een eigen GetNoticed platform. "
            "Implementeer een custom scraper op basis van hun website."
        )
        return []
