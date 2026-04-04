"""
Dichtbij Kinderopvang scraper — werkenbijdichtbij.nl

Platform: WordPress + Elementor + custom SCRP plugin.
Taxonomy classes op de post wrapper bevatten locatie en uren:
  locatie-{stad}   → stad
  uur-{range}      → uren klasse (bijv. uur-11-20)
Badge selector:
  .scrp-locatie-badge span  → stad tekst
  .scrp-uur-term span:last-child → uren tekst
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)


class DichtbijScraper(WordPressJobsScraper):
    company_slug     = "dichtbij"
    company_name     = "Dichtbij Kinderopvang"
    listing_url      = "https://werkenbijdichtbij.nl/vacatures/"
    website_url      = "https://werkenbijdichtbij.nl"
    job_url_contains = "/vacature/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[dichtbij] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        # City: badge selector (most reliable on detail page)
        city = ""
        badge = soup.select_one(".scrp-locatie-badge span")
        if badge:
            city = badge.get_text(strip=True)

        # Fallback: taxonomy class on post wrapper e.g. "locatie-vianen" → "Vianen"
        if not city:
            wrapper = soup.select_one("[data-elementor-type='single-post']")
            if wrapper:
                for cls in wrapper.get("class", []):
                    if cls.startswith("locatie-") and cls != "locatie-":
                        raw = cls.replace("locatie-", "").replace("-", " ")
                        city = raw.title()
                        break

        # Hours: uur-term span on detail page
        hours_min = hours_max = None
        uur_term = soup.select_one(".scrp-uur-term span:last-child")
        if uur_term:
            hours_min, hours_max = _parse_hours(uur_term.get_text(strip=True))

        # Description
        content = soup.select_one(".sc-vacature-tekst") or soup.select_one("main") or soup.select_one("article")
        desc = content.get_text(separator="\n", strip=True)[:5000] if content else ""
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
