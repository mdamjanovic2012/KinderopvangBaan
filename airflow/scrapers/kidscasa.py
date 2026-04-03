"""
Kidscasa scraper — kidscasa.nl

Alle vacatures zijn PDF-bestanden gelinkt vanuit de listing-pagina.
Er zijn geen HTML detail-pagina's; wij extraheren titel en uren
direct van de listing-pagina (PDF-link in een <h5>-tag).
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, SCRAPER_HEADERS

logger = logging.getLogger(__name__)

LISTING_URL = "https://kidscasa.nl/organisatie/vacatures/"


def _parse_hours(text: str) -> tuple[int | None, int | None]:
    m = re.search(r"(\d+)\s*(?:[-–]\s*(\d+))?\s*uur", text, re.IGNORECASE)
    if m:
        lo = int(m.group(1))
        hi = int(m.group(2)) if m.group(2) else lo
        return lo, hi
    return None, None


class KidscasaScraper(BaseScraper):
    company_slug = "kidscasa"
    company_name = "Kidscasa"
    website_url  = "https://kidscasa.nl"

    def fetch_company(self) -> dict:
        return {
            "name":          self.company_name,
            "website":       self.website_url,
            "job_board_url": LISTING_URL,
            "scraper_class": self.__class__.__name__,
        }

    def fetch_jobs(self) -> list[dict]:
        try:
            resp = requests.get(LISTING_URL, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[{self.company_slug}] Listing mislukt: {exc}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        jobs = []

        pdf_links = [
            a for a in soup.find_all("a", href=True)
            if ".pdf" in a["href"] and "vacature" in a["href"].lower()
        ]

        seen = set()
        for a in pdf_links:
            url = a["href"]
            if url in seen:
                continue
            seen.add(url)

            title = a.get_text(strip=True)
            if not title:
                continue

            slug = url.rstrip("/").split("/")[-1].replace(".pdf", "")
            hours_min, hours_max = _parse_hours(title)

            jobs.append({
                "source_url":        url,
                "external_id":       slug,
                "title":             title,
                "short_description": "",
                "description":       "",
                "location_name":     "",
                "city":              "",
                "salary_min":        None,
                "salary_max":        None,
                "hours_min":         hours_min,
                "hours_max":         hours_max,
                "age_min":           None,
                "age_max":           None,
                "contract_type":     "",
                "job_type":          "",
            })

        logger.info(f"[{self.company_slug}] {len(jobs)} vacatures gevonden")
        return jobs
