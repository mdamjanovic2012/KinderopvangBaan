"""
Kober Kinderopvang scraper — werkenbijkober.nl

Platform: WordPress + Beaver Builder (custom vacature plugin).
Selectors:
  Uren:    div.uren span  (bijv. "16-24 uur")
  Locatie: div.locatie span  (bijv. "Breda en omgeving")
  Desc:    .fl-rich-text, .entry-content, main
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)


class KoberScraper(WordPressJobsScraper):
    company_slug     = "kober"
    company_name     = "Kober Kinderopvang"
    listing_url      = "https://werkenbijkober.nl/vacatures/"
    website_url      = "https://werkenbijkober.nl"
    job_url_contains = "/vacatures/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[kober] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        # Uren: div.uren span of div.uren of div.aantal-uur
        hours_min = hours_max = None
        uren_el = (
            soup.select_one("div.uren span")
            or soup.select_one("div.uren")
            or soup.select_one("div.aantal-uur")
        )
        if uren_el:
            hours_text = uren_el.get_text(strip=True)
            hours_min, hours_max = _parse_hours(hours_text)

        # Locatie: div.locatie span of div.fl-plaats of div.locatie
        city = ""
        locatie_el = (
            soup.select_one("div.locatie span")
            or soup.select_one("div.fl-plaats")
            or soup.select_one("div.locatie")
        )
        if locatie_el:
            raw = locatie_el.get_text(strip=True)
            # Strip trailing "en omgeving" voor geocoding
            city = re.sub(r"\s+en\s+omgeving\s*$", "", raw, flags=re.I).strip()

        # Beschrijving
        desc_el = (
            soup.select_one(".fl-rich-text")
            or soup.select_one(".entry-content")
            or soup.select_one("main")
        )
        desc = desc_el.get_text(separator="\n", strip=True)[:5000] if desc_el else ""

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
