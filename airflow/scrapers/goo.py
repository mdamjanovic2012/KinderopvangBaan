"""
Stichting GOO scraper — stichtinggoo.nl

Job URLs zijn single-segment met mixed case: /Vacature-xxx of /vacature-xxx
Daarom custom _get_all_job_urls die case-insensitief matcht en 1-segment URLs toelaat.
"""

import logging

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS

logger = logging.getLogger(__name__)
from scrapers.wordpress_jobs import WordPressJobsScraper


class GooScraper(WordPressJobsScraper):
    company_slug = "goo"
    company_name = "Stichting GOO"
    listing_url  = "https://www.stichtinggoo.nl/vacatures"
    website_url  = "https://www.stichtinggoo.nl"

    def _get_all_job_urls(self) -> list[str]:
        try:
            resp = requests.get(self.listing_url, headers=SCRAPER_HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[{self.company_slug}] Listing mislukt: {exc}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        seen = set()
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("/"):
                href = self.website_url.rstrip("/") + href
            if "vacature" in href.lower() and href != self.listing_url and href not in seen:
                seen.add(href)
                links.append(href)
        return links
