"""
Welluswijs Kinderopvang scraper — welluswijs.nl

Platform: WordPress + Elementor + ACF (velden niet publiek via REST).
Listing URL: https://www.welluswijs.nl/vacatures/
Job URLs:    /vacature/{slug}/

HTML structuur detailpagina:
  Titel:  Eerste h2.elementor-heading-title (geen H1 op de pagina)
  Stad:   Niet als apart structuurveld; regex op beschrijvingstekst
          ("in {Stad}", "te {Stad}", "locatie {Stad}")
  Uren:   Eerste .elementor-widget-text-editor widget die uren bevat
  Beschrijving: .elementor-widget-theme-post-content
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)

_CITY_RE = re.compile(
    r"\b(?:in|te|locatie|vestiging)\s+([A-Z][A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-]{1,25})\b"
)


class WelluswijsScraper(WordPressJobsScraper):
    company_slug     = "welluswijs"
    company_name     = "Welluswijs Kinderopvang"
    listing_url      = "https://www.welluswijs.nl/vacatures/"
    website_url      = "https://www.welluswijs.nl"
    job_url_contains = "/vacature/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[welluswijs] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # Geen H1; eerste H2 in Elementor single template is de vacaturetitel
        h2 = soup.select_one("h2.elementor-heading-title")
        title = h2.get_text(strip=True) if h2 else ""
        if not title:
            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        # Uren: zoek in text-editor widgets
        hours_min = hours_max = None
        for widget in soup.select(".elementor-widget-text-editor .elementor-widget-container"):
            t = widget.get_text(strip=True)
            if t:
                hours_min, hours_max = _parse_hours(t)
                if hours_min is not None:
                    break

        # Beschrijving
        desc_el = (
            soup.select_one(".elementor-widget-theme-post-content")
            or soup.select_one("main")
            or soup.select_one("article")
        )
        desc = desc_el.get_text(separator="\n", strip=True)[:5000] if desc_el else ""

        if hours_min is None:
            hours_min, hours_max = _parse_hours(desc)

        # Stad: regex op beschrijvingstekst
        city = ""
        m = _CITY_RE.search(desc)
        if m:
            city = m.group(1).strip()

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
