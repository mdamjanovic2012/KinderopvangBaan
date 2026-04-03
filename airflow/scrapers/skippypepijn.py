"""
SkippyPePijN scraper — www.skippypepijn.nl

Platform: Eigen website (geen extern ATS), GEEN Teamtailor of Recruitee.
Gecontroleerd op 2026-04-03:
  - https://www.skippypepijn.nl/jobs.rss            → 404
  - https://skippypepijn.teamtailor.com/jobs.rss    → 404
  - https://www.skippypepijn.nl/over-ons/werken-bij-skippypepijn/ → eigen pagina zonder ATS widget

De vacatures staan als losse HTML-pagina's op /over-ons/werken-bij-skippypepijn/vacatures/...
Sollicitaties gaan via sollicitaties@skippypepijn.nl (formulier op de website).

TODO: SkippyPePijN heeft geen publieke feed of ATS-integratie.
      Mogelijke aanpak: HTML-scraper op de vacaturepagina
      https://www.skippypepijn.nl/over-ons/werken-bij-skippypepijn/
      die links naar individuele vacatures verzamelt en per pagina parseert.

NOTE: Deze klasse is een tijdelijke stub. fetch_jobs() geeft altijd een lege lijst terug
      totdat een werkende integratie is geïmplementeerd.
"""

import logging

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class SkippyPePijNScraper(BaseScraper):
    company_slug = "skippypepijn"
    company_name = "SkippyPePijN"
    career_url   = "https://www.skippypepijn.nl/over-ons/werken-bij-skippypepijn/"

    def fetch_company(self) -> dict:
        return {
            "name":          self.company_name,
            "website":       "https://www.skippypepijn.nl",
            "job_board_url": self.career_url,
            "scraper_class": self.__class__.__name__,
            "logo_url":      "",
            "description":   "",
        }

    def fetch_jobs(self) -> list[dict]:
        logger.warning(
            f"[{self.company_slug}] Geen werkende RSS/API feed beschikbaar. "
            "SkippyPePijN beheert vacatures op eigen website zonder extern ATS. "
            "Implementeer een custom HTML-scraper voor hun vacaturepagina."
        )
        return []
