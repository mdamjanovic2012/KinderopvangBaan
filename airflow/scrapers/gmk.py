"""
GMK Kinderopvang — werkenbijgmk.nl

Platform: WordPress + Tailwind CSS custom theme.
GMK is een groep Amsterdamse organisaties: Akros, Combiwel, Impuls.
Alle locaties zijn in Amsterdam — city is altijd 'Amsterdam'.

Detail pagina structuur:
  [data-scroll-item="order-2"]  → divisie/organisatienaam (bijv. "Akros")
  [data-scroll-item="order-3"] span.font-medium → uren (eerste waarde)
"""

import logging

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)


class GmkScraper(WordPressJobsScraper):
    company_slug     = "gmk"
    company_name     = "GMK Kinderopvang"
    listing_url      = "https://werkenbijgmk.nl/vacatures/"
    website_url      = "https://werkenbijgmk.nl"
    job_url_contains = "/vacatures/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[gmk] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        # Divisie/organisatienaam → location_name
        location_name = ""
        org_el = soup.select_one('[data-scroll-item="order-2"]')
        if org_el:
            location_name = org_el.get_text(strip=True)

        # Hours: first span.font-medium in order-3 block
        hours_min = hours_max = None
        meta_block = soup.select_one('[data-scroll-item="order-3"]')
        if meta_block:
            for span in meta_block.select("span.font-medium"):
                text = span.get_text(strip=True)
                h_min, h_max = _parse_hours(text)
                if h_min is not None:
                    hours_min, hours_max = h_min, h_max
                    break

        # Description
        main = soup.select_one("main") or soup.select_one("article")
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
            "city":              "Amsterdam",  # GMK operates exclusively in Amsterdam
            "salary_min":        None,
            "salary_max":        None,
            "hours_min":         hours_min,
            "hours_max":         hours_max,
            "age_min":           None,
            "age_max":           None,
            "contract_type":     "",
            "job_type":          "",
        }
