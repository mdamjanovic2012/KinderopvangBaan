"""
Kinderopvang Walcheren scraper — werkenbijkow.nl

Platform: WordPress. No JSON-LD.
Job links use protocol-relative URLs (//www.werkenbijkow.nl/vacatures/{slug}).
Custom _get_all_job_urls to handle // prefix.
"""

import logging

import requests
from bs4 import BeautifulSoup

from scrapers.wordpress_jobs import WordPressJobsScraper
from scrapers.base import SCRAPER_HEADERS

logger = logging.getLogger(__name__)

BASE_URL  = "https://www.werkenbijkow.nl"
JOBS_URL  = f"{BASE_URL}/vacatures/"


class KOWalcherenScraper(WordPressJobsScraper):
    company_slug     = "ko-walcheren"
    company_name     = "Kinderopvang Walcheren"
    listing_url      = JOBS_URL
    website_url      = BASE_URL
    job_url_contains = "/vacatures/"

    def _get_all_job_urls(self) -> list[str]:
        """Override to handle protocol-relative URLs (//www.werkenbijkow.nl/...)."""
        try:
            resp = requests.get(self.listing_url, headers=SCRAPER_HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[ko-walcheren] Listing failed: {exc}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        seen = set()
        links = []

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            # Resolve protocol-relative URLs
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = BASE_URL + href

            if self.job_url_contains not in href:
                continue

            path = href.replace(BASE_URL, "")
            segments = [s for s in path.strip("/").split("/") if s]
            if len(segments) >= 2 and href not in seen:
                seen.add(href)
                links.append(href)

        logger.info(f"[ko-walcheren] {len(links)} job URLs found")
        return links
