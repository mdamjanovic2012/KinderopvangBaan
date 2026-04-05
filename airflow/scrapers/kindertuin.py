"""
Kindertuin scraper — kindertuin.com

Platform: WordPress met Visual Composer theme.
Listing URL: https://www.kindertuin.com/werken-bij/
Job URLs:    /vacatures/{slug}/

HTML structuur detailpagina:
  Titel:       h1
  Stad:        article body-class "vacature_locatie-{city}" (bijv. "vacature_locatie-heeswijk")
  Uren:        regex op beschrijvingstekst (geen dedicated HTML element)
  Beschrijving: div.entry-content
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)

_LOCATIE_CLASS_RE = re.compile(r"\bvacature_locatie-([\w\-]+)\b")


class KindertuinScraper(WordPressJobsScraper):
    company_slug     = "kindertuin"
    company_name     = "Kindertuin"
    listing_url      = "https://www.kindertuin.com/werken-bij/"
    website_url      = "https://www.kindertuin.com"
    job_url_contains = "/werken-bij/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[kindertuin] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        # Stad: article body-class "vacature_locatie-{city}"
        city = ""
        article = soup.find("article")
        if article:
            classes = " ".join(article.get("class", []))
            m = _LOCATIE_CLASS_RE.search(classes)
            if m:
                city = m.group(1).replace("-", " ").title()

        # Beschrijving
        desc_el = soup.select_one("div.entry-content") or soup.select_one("main")
        desc = desc_el.get_text(separator="\n", strip=True)[:5000] if desc_el else ""

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
