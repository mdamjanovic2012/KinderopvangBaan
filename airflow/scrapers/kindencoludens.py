"""
Kind&co Ludens scraper — kindencoludens.nl

Platform: Eigen systeem (Prepr CMS / Next.js), GEEN Teamtailor of Recruitee.
Gecontroleerd op 2026-04-03: /jobs.rss geeft een HTML-pagina terug, geen RSS feed.
De vacatures worden beheerd via het Prepr CMS met een "CareersVacancies" content type.

TODO: Kind&co Ludens gebruikt een custom Next.js applicatie op Prepr CMS.
      Onderzoek de Prepr GraphQL API of de Next.js data-fetching endpoints
      om vacatures op te halen:
      https://kindencoludens.nl/werken-bij

NOTE: Deze klasse is een tijdelijke stub. fetch_jobs() geeft altijd een lege lijst terug
      totdat een werkende integratie is geïmplementeerd.
"""

import logging

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class KindenCoLudensScraper(BaseScraper):
    company_slug = "kindencoludens"
    company_name = "Kind&co Ludens"
    career_url   = "https://kindencoludens.nl"

    def fetch_company(self) -> dict:
        return {
            "name":          self.company_name,
            "website":       self.career_url,
            "job_board_url": f"{self.career_url}/werken-bij",
            "scraper_class": self.__class__.__name__,
            "logo_url":      "",
            "description":   "",
        }

    def fetch_jobs(self) -> list[dict]:
        logger.warning(
            f"[{self.company_slug}] Geen werkende RSS/API feed beschikbaar. "
            "Kind&co Ludens gebruikt een custom Prepr CMS platform (Next.js). "
            "Implementeer een custom scraper via de Prepr API of HTML scraping."
        )
        return []
