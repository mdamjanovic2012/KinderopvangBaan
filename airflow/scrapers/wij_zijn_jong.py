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

from scrapers.wordpress_jobs import WordPressJobsScraper, get_job_links_from_listing, _parse_hours
from scrapers.base import SCRAPER_HEADERS

SALARY_RE = re.compile(r"€\s*([\d.,]+)\s*[-–]\s*€?\s*([\d.,]+)", re.I)


def _parse_euros(raw: str) -> float | None:
    try:
        return float(raw.replace(".", "").replace(",", ".").strip())
    except ValueError:
        return None

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

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[wij-zijn-jong] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        h1 = soup.select_one("h1.twz-hero__title") or soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        city_el = soup.select_one("li.location-place")
        city = city_el.get_text(strip=True) if city_el else ""

        hours_el = soup.select_one("li.hours")
        hours_text = hours_el.get_text(strip=True) if hours_el else ""
        hours_min, hours_max = _parse_hours(hours_text) if hours_text else (None, None)

        content = soup.select_one("div.content")
        desc = content.get_text(separator="\n", strip=True)[:5000] if content else ""

        salary_min = salary_max = None
        sm = SALARY_RE.search(desc)
        if sm:
            salary_min = _parse_euros(sm.group(1))
            salary_max = _parse_euros(sm.group(2))

        external_id = url.rstrip("/").split("/")[-1]

        return {
            "source_url":        url,
            "external_id":       external_id,
            "title":             title,
            "short_description": desc[:300],
            "description":       desc,
            "location_name":     city,
            "city":              city,
            "salary_min":        salary_min,
            "salary_max":        salary_max,
            "hours_min":         hours_min,
            "hours_max":         hours_max,
            "age_min":           None,
            "age_max":           None,
            "contract_type":     "",
            "job_type":          "",
        }
