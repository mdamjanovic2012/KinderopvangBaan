"""
Kinderstad scraper — kinderstad.nl

Platform: WordPress met custom post type `vacature`.
API:      https://kinderstad.nl/wp-json/wp/v2/vacature?per_page=50

Aanpak:
  1. Roep WP REST API aan, ontvang JSON-array
  2. Elke entry: id, title.rendered, link, content.rendered, excerpt.rendered
  3. Strip HTML uit content.rendered voor beschrijving
  4. Extraheer uren via _parse_hours
  5. Probeer stad te herkennen uit beschrijvingstekst (patroon "in <Stad>" / "te <Stad>")
"""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, SCRAPER_HEADERS
from scrapers.wordpress_jobs import _parse_hours, _strip_html

logger = logging.getLogger(__name__)

API_URL     = "https://kinderstad.nl/wp-json/wp/v2/vacature?per_page=50"
WEBSITE_URL = "https://kinderstad.nl"
BOARD_URL   = "https://kinderstad.nl/vacatures/"

# Patroon om stad te herkennen: "in Amsterdam", "te Rotterdam", "in Den Haag"
_CITY_RE = re.compile(
    r"\b(?:in|te)\s+([A-Z][a-zA-ZÀ-ÿ'-]+(?:\s+[A-Z][a-zA-ZÀ-ÿ'-]+){0,2})",
    re.UNICODE,
)


def _extract_city(text: str) -> str:
    """Zoek eerste plaatsnaam in tekst via 'in X' / 'te X' patroon."""
    m = _CITY_RE.search(text)
    return m.group(1).strip() if m else ""


class KinderstadScraper(BaseScraper):
    company_slug = "kinderstad"
    company_name = "Kinderstad"

    # ── Bedrijfsinfo ──────────────────────────────────────────────────────────

    def fetch_company(self) -> dict:
        logo_url = description = ""
        try:
            resp = requests.get(WEBSITE_URL, headers=SCRAPER_HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            for sel in ["header img[src]", ".logo img[src]", "img[alt*='logo' i][src]"]:
                el = soup.select_one(sel)
                if el:
                    src = el.get("src", "")
                    if src.startswith("data:"):
                        continue
                    logo_url = src if src.startswith("http") else WEBSITE_URL.rstrip("/") + src
                    if len(logo_url) > 199:
                        logo_url = ""
                    break
            meta = soup.select_one("meta[name='description']")
            if meta:
                description = meta.get("content", "")
        except Exception as exc:
            logger.warning(f"[{self.company_slug}] Bedrijfsinfo ophalen mislukt: {exc}")

        return {
            "name":          self.company_name,
            "website":       WEBSITE_URL,
            "job_board_url": BOARD_URL,
            "scraper_class": self.__class__.__name__,
            "logo_url":      logo_url,
            "description":   description,
        }

    # ── Vacatures ophalen ────────────────────────────────────────────────────

    def fetch_jobs(self) -> list[dict]:
        logger.info(f"[{self.company_slug}] Fetching WP REST API: {API_URL}")

        try:
            resp = requests.get(API_URL, headers=SCRAPER_HEADERS, timeout=30)
            resp.raise_for_status()
            items = resp.json()
        except Exception as exc:
            logger.warning(f"[{self.company_slug}] API request mislukt: {exc}")
            return []

        if not isinstance(items, list):
            logger.warning(f"[{self.company_slug}] Onverwacht API-formaat: {type(items)}")
            return []

        logger.info(f"[{self.company_slug}] {len(items)} items van API")

        jobs = []
        for item in items:
            try:
                job = self._parse_item(item)
                if job:
                    jobs.append(job)
            except Exception as exc:
                logger.warning(f"[{self.company_slug}] Item parse mislukt: {exc}")
            time.sleep(0.1)

        logger.info(f"[{self.company_slug}] {len(jobs)} vacatures verwerkt")
        return jobs

    # ── Item parser ──────────────────────────────────────────────────────────

    def _parse_item(self, item: dict) -> dict | None:
        external_id = str(item.get("id", "")).strip()
        source_url  = item.get("link", "").strip()

        title_obj = item.get("title", {})
        title = (
            title_obj.get("rendered", "") if isinstance(title_obj, dict) else str(title_obj)
        ).strip()
        # Decode HTML entities (WordPress encodes & → &amp; etc.)
        title = BeautifulSoup(title, "lxml").get_text(strip=True)

        if not title or not source_url:
            return None

        # Beschrijving
        content_obj = item.get("content", {})
        content_html = (
            content_obj.get("rendered", "") if isinstance(content_obj, dict) else str(content_obj)
        )
        desc = _strip_html(content_html) if content_html else ""

        # Samenvatting (excerpt)
        excerpt_obj = item.get("excerpt", {})
        excerpt_html = (
            excerpt_obj.get("rendered", "") if isinstance(excerpt_obj, dict) else ""
        )
        short_desc = BeautifulSoup(excerpt_html, "lxml").get_text(strip=True)[:300] if excerpt_html else desc[:300]

        # Uren
        hours_min, hours_max = _parse_hours(desc)

        # Stad
        city = _extract_city(desc) or _extract_city(title)

        # Locatienaam voor PDOK geocoding
        location_name = city

        return {
            "source_url":        source_url,
            "external_id":       external_id,
            "title":             title,
            "short_description": short_desc,
            "description":       desc,
            "location_name":     location_name,
            "city":              city,
            "postcode":          "",
            "salary_min":        None,
            "salary_max":        None,
            "hours_min":         hours_min,
            "hours_max":         hours_max,
            "age_min":           None,
            "age_max":           None,
            "contract_type":     "",
            "job_type":          "",
        }
