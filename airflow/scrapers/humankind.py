"""
Humankind scraper — werkenbijhumankind.nl

Platform: Custom site with schema.org JobPosting JSON-LD.
URL pattern: /vacatures/{id}
Paginated listing: ?page=0..N
"""

import logging

import requests
from bs4 import BeautifulSoup

from scrapers.wordpress_jobs import (
    WordPressJobsScraper,
    get_job_links_from_listing,
)
from scrapers.base import SCRAPER_HEADERS

logger = logging.getLogger(__name__)

BASE_URL = "https://www.werkenbijhumankind.nl"
JOBS_URL = f"{BASE_URL}/vacatures/"

# Number of listing pages to check (0-indexed)
MAX_PAGES = 8


class HumankindScraper(WordPressJobsScraper):
    company_slug     = "humankind"
    company_name     = "Humankind Kinderopvang"
    listing_url      = JOBS_URL
    website_url      = BASE_URL
    job_url_contains = "/vacatures/"

    def _get_all_job_urls(self) -> list[str]:
        """Collect job URLs across all listing pages."""
        all_urls: set[str] = set()

        for page in range(MAX_PAGES):
            url = JOBS_URL if page == 0 else f"{JOBS_URL}?page={page}"
            try:
                resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=30)
                resp.raise_for_status()
                links = get_job_links_from_listing(resp.text, BASE_URL, "/vacatures/")
                new_links = [l for l in links if l not in all_urls]
                if not new_links:
                    logger.info(f"[humankind] No new links on page {page}, stopping")
                    break
                all_urls.update(new_links)
                logger.info(f"[humankind] Page {page}: {len(new_links)} new links ({len(all_urls)} total)")
            except Exception as exc:
                logger.warning(f"[humankind] Listing page {page} failed: {exc}")
                break

        return list(all_urls)
