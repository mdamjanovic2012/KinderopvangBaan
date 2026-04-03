"""
Kinderopvang Haarlemmermeer scraper — werkenbijhaarlemmermeer.nl

STATUS: NIET ONDERSTEUND — het portaal gebruikt TSF (Angular router).
Job-links worden niet als <a href> in de DOM gezet, zelfs niet na full
Playwright-rendering. Vacatures zijn niet programmatisch op te halen.

Controleer https://werkenbijhaarlemmermeer.nl/vacatures handmatig.
"""

import logging

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://werkenbijhaarlemmermeer.nl"
JOBS_URL = f"{BASE_URL}/vacatures"


class HaarlemmermeerScraper(BaseScraper):
    company_slug = "haarlemmermeer"

    def fetch_company(self) -> dict:
        return {
            "name":          "Kinderopvang Haarlemmermeer",
            "website":       BASE_URL,
            "job_board_url": JOBS_URL,
            "scraper_class": "HaarlemmermeerScraper",
            "logo_url":      "",
            "description":   "",
        }

    def fetch_jobs(self) -> list[dict]:
        logger.warning(
            f"[{self.company_slug}] Portaal {JOBS_URL} gebruikt TSF (Angular router). "
            "Job-links zijn niet programmatisch beschikbaar. Vacatures overgeslagen."
        )
        return []
