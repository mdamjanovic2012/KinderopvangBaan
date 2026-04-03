"""
Wij zijn JONG scraper — werkenbijwijzijnjong.nl

Platform: WordPress with paginated listing (/vacatures/page/{n}/).
No JobPosting JSON-LD — uses HTML fallback parsing.
Group of companies: Korein, Skar, Kwink, Spelenderwijs, Edux, KlupPluz.
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.wordpress_jobs import WordPressJobsScraper, get_job_links_from_listing
from scrapers.base import SCRAPER_HEADERS

logger = logging.getLogger(__name__)

BASE_URL = "https://werkenbijwijzijnjong.nl"
JOBS_URL = f"{BASE_URL}/vacatures/"

# Maximum number of listing pages to try
MAX_PAGES = 20


class WijZijnJONGScraper(WordPressJobsScraper):
    company_slug     = "wij-zijn-jong"
    company_name     = "Wij zijn JONG"
    listing_url      = JOBS_URL
    website_url      = BASE_URL
    job_url_contains = "/vacatures/"

    def _get_all_job_urls(self) -> list[str]:
        """Collect job URLs from all WordPress pagination pages."""
        all_urls: set[str] = set()

        for page in range(1, MAX_PAGES + 1):
            url = JOBS_URL if page == 1 else f"{JOBS_URL}page/{page}/"
            try:
                resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=30)
                if resp.status_code == 404:
                    logger.info(f"[wij-zijn-jong] 404 on page {page}, stopping")
                    break
                resp.raise_for_status()
                links = get_job_links_from_listing(resp.text, BASE_URL, "/vacatures/")
                # Filter out pagination links and filter links
                job_links = [
                    l for l in links
                    if "/page/" not in l and "/filter/" not in l and l not in all_urls
                ]
                if not job_links and page > 1:
                    logger.info(f"[wij-zijn-jong] No new jobs on page {page}, stopping")
                    break
                all_urls.update(job_links)
                logger.info(f"[wij-zijn-jong] Page {page}: {len(job_links)} new links ({len(all_urls)} total)")
            except Exception as exc:
                logger.warning(f"[wij-zijn-jong] Page {page} failed: {exc}")
                break

        return list(all_urls)
