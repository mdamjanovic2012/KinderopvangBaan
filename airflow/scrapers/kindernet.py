"""
KDV Kindernet scraper — kdvkindernet.nl

Platform: WordPress + Elementor Pro + JetEngine
Custom post type: vacancies

Locatie staat in:
  - body class `location-{city}` op detail pagina
  - li met map-marker SVG in elementor-icon-list-items
Uren: regex op paginatitel (bijv. "... 16-32 uur")
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)


class KindernetScraper(WordPressJobsScraper):
    company_slug     = "kindernet"
    company_name     = "KDV Kindernet"
    listing_url      = "https://kdvkindernet.nl/vacancies/"
    website_url      = "https://kdvkindernet.nl"
    job_url_contains = "/vacancies/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[kindernet] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # Title
        h1 = soup.select_one("h1.elementor-heading-title") or soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        # City from body/wrapper class: "location-doetinchem" → "Doetinchem"
        city = ""
        wrapper = soup.select_one("div.elementor-location-single")
        if wrapper:
            for cls in wrapper.get("class", []):
                if cls.startswith("location-") and cls != "elementor-location-single":
                    raw = cls.replace("location-", "").replace("-", " ")
                    city = raw.title()
                    break

        # Fallback: icon list with map-marker SVG
        if not city:
            for li in soup.select("li.elementor-icon-list-item"):
                svg = li.select_one("svg.e-fas-map-marker-alt")
                if svg:
                    text_el = li.select_one("span.elementor-icon-list-text")
                    if text_el:
                        city = text_el.get_text(strip=True)
                    break

        # Hours: regex on title (e.g. "... Doetinchem 16-32 uur")
        hours_min, hours_max = _parse_hours(title)

        # Description
        content_el = soup.select_one(".elementor-widget-theme-post-content .elementor-widget-container")
        if not content_el:
            content_el = soup.select_one("main") or soup.select_one("article")
        desc = content_el.get_text(separator="\n", strip=True)[:5000] if content_el else ""
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
