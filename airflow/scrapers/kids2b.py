"""
Kids2b scraper — kids2b.nl (iWink CMS)

Listing URL: https://www.kids2b.nl/.../kids2b-vacatures
Job URLs:    /kids2b-vacatures/{slug}

HTML structuur detailpagina (dl.meta.meta-data-job-post-detail):
  Stad:  div.meta-item.meta-item-city > dd.meta-item-value
  Uren:  div.meta-item.meta-item-contract > dd.meta-item-value  (bijv. "28 uren per week")
"""

import logging

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)


class Kids2bScraper(WordPressJobsScraper):
    company_slug     = "kids2b"
    company_name     = "Kids2b"
    listing_url      = "https://www.kids2b.nl/kom-werken-bij-kids2b-en-wees-de-expert-in-kindontwikkeling/kids2b-vacatures"
    website_url      = "https://www.kids2b.nl"
    job_url_contains = "/kids2b-vacatures"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[kids2b] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        # Stad en uren uit meta-items
        city = ""
        hours_min = hours_max = None

        city_el = soup.select_one("div.meta-item.meta-item-city dd.meta-item-value")
        if city_el:
            city = city_el.get_text(strip=True)

        contract_el = soup.select_one("div.meta-item.meta-item-contract dd.meta-item-value")
        if contract_el:
            hours_min, hours_max = _parse_hours(contract_el.get_text(strip=True))

        # Beschrijving
        desc_parts = []
        for el in soup.select("div.component-block.component-paragraph"):
            t = el.get_text(separator="\n", strip=True)
            if t:
                desc_parts.append(t)
        desc = "\n\n".join(desc_parts)[:5000]
        if not desc:
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
