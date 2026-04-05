"""
CKO KleurRijk scraper — kleurrijkkinderopvang.nl

Platform: WordPress + Divi page builder.
Vacature-samenvatting staat in het eerste .et_pb_cta_1 blok als free-form tekst:
  Functie: ...
  Locatie: <adres of vrijeTekst>
  Uren: ...
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)

# Postcode pattern to extract city after it: "8021 WB Zwolle" → "Zwolle"
_POSTCODE_CITY_RE = re.compile(r"\d{4}\s*[A-Z]{2}\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-\s]{1,30}?)(?:\s+en\s|\s*[,\n]|$)", re.I)
# "in Deventer" or "te Zwolle"
_IN_CITY_RE = re.compile(r"\b(?:in|te)\s+([A-Z][A-Za-zÀ-ÿ\-]{2,25})", re.I)


def _extract_city(location_text: str) -> str:
    """Extract city from a raw location string."""
    m = _POSTCODE_CITY_RE.search(location_text)
    if m:
        return m.group(1).strip().rstrip(",")
    m = _IN_CITY_RE.search(location_text)
    if m:
        return m.group(1).strip()
    # Fallback: last capitalized token (handles "... Zwolle en omstreken" → "Zwolle")
    words = location_text.split()
    for word in reversed(words):
        w = word.strip(",.:")
        if w and w[0].isupper() and len(w) >= 3 and not w.isupper():
            return w
    return ""


class KleurrijkScraper(WordPressJobsScraper):
    company_slug     = "kleurrijk"
    company_name     = "CKO KleurRijk"
    listing_url      = "https://www.kleurrijkkinderopvang.nl/vacatures/"
    website_url      = "https://www.kleurrijkkinderopvang.nl"
    job_url_contains = "/vacatures/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[{self.company_slug}] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # Title: H1 or H2
        heading = soup.find("h1") or soup.find("h2")
        title = heading.get_text(strip=True) if heading else ""
        if not title:
            return None

        # Summary block: first .et_pb_cta_* promo description
        location_name = city = ""
        hours_min = hours_max = None

        cta_p = soup.select_one(".et_pb_cta_1 .et_pb_promo_description p")
        if not cta_p:
            # Fallback: any et_pb_cta promo description
            cta_p = soup.select_one("[class*='et_pb_cta'] .et_pb_promo_description p")

        if cta_p:
            summary = cta_p.get_text(" ", strip=True)
            # Locatie
            loc_m = re.search(r"Locatie[:\s]+(.*?)(?:Uren:|Startdatum:|$)", summary, re.I | re.S)
            if loc_m:
                location_name = loc_m.group(1).strip().rstrip(".")
                city = _extract_city(location_name)
            # Uren
            uren_m = re.search(r"Uren[:\s]+(.*?)(?:Start|Functie|$)", summary, re.I | re.S)
            if uren_m:
                hours_min, hours_max = _parse_hours(uren_m.group(1))

        # Description: main content
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
            "location_name":     location_name,
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
