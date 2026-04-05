"""
SKBNM Kinderopvang — werkenbij.skbnm.nl

Gestructureerde USP-blokken op detailpagina:
  .usps-wrapper .usp  → [0]=uren, [1]=stad
"""

import logging

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)


class SkbnmScraper(WordPressJobsScraper):
    company_slug     = "skbnm"
    company_name     = "SKBNM Kinderopvang"
    listing_url      = "https://werkenbij.skbnm.nl/vacatures/"
    website_url      = "https://werkenbij.skbnm.nl"
    job_url_contains = "/vacatures/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[skbnm] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        usps = soup.select(".usps-wrapper .usp")
        hours_min = hours_max = None
        city = ""
        if len(usps) >= 1:
            hours_min, hours_max = _parse_hours(usps[0].get_text(strip=True))
        if len(usps) >= 2:
            city = usps[1].get_text(strip=True)

        main = soup.select_one("main") or soup.select_one("article") or soup.select_one(".entry-content")
        desc = main.get_text(separator="\n", strip=True)[:5000] if main else ""
        if hours_min is None:
            hours_min, hours_max = _parse_hours(desc)

        external_id = url.rstrip("/").split("/")[-1]

        return {
            "source_url":        url,
            "external_id":       external_id,
            "title":             title,
            "short_description": desc[:300],
            "description":       desc,
            "location_name":     city,
            "city":              city,
            "salary_min":        None,
            "salary_max":        None,
            "hours_min":         hours_min,
            "hours_max":         hours_max,
            "age_min":           None,
            "age_max":           None,
            "contract_type":     "",
            "job_type":          "",
        }
