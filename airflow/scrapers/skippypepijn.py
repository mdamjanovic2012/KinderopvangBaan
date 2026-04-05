"""
SkippyPePijN scraper — www.skippypepijn.nl

Platform: Eigen CMS, server-side HTML.
Listing URL: https://www.skippypepijn.nl/over-ons/werken-bij-skippypepijn/
Job URLs:    /over-ons/werken-bij-skippypepijn/vacatures/{slug}/

HTML structuur detailpagina:
  Titel:       h1
  Uren:        h2.heading-3 > span  (bijv. "27,5 uur | Ma, Di, Do")
  Stad:        postcode-regex op paginatekst (footer .text-6 span bevat adres)
  Beschrijving: div.text-2
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)

_POSTCODE_CITY_RE = re.compile(
    r"\d{4}\s*[A-Z]{2}\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-]{1,30}?)(?:\s*[|,\n]|$)"
)
_UUR_PART_RE = re.compile(r"^(.*?uur)", re.I)


class SkippyPePijNScraper(WordPressJobsScraper):
    company_slug     = "skippypepijn"
    company_name     = "SkippyPePijN"
    listing_url      = "https://www.skippypepijn.nl/over-ons/werken-bij-skippypepijn/"
    website_url      = "https://www.skippypepijn.nl"
    job_url_contains = "/vacatures/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[skippypepijn] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        # Uren: h2.heading-3 > span bevat "27,5 uur | Ma, Di, Do"
        hours_min = hours_max = None
        heading3 = soup.select_one("h2.heading-3")
        if heading3:
            span = heading3.find("span")
            if span:
                uren_text = span.get_text(strip=True)
                # Pak alleen het deel voor de "|"
                uren_part = uren_text.split("|")[0].strip()
                # Vervang komma-decimaal ("27,5 uur") door "27 uur" voor _parse_hours
                uren_clean = re.sub(r"(\d+),\d+", lambda m: m.group(1), uren_part)
                hours_min, hours_max = _parse_hours(uren_clean)

        # Stad: zoek postcode-patroon op de pagina (footer bevat adres van de locatie)
        city = ""
        page_text = soup.get_text(" ", strip=True)
        m = _POSTCODE_CITY_RE.search(page_text)
        if m:
            city = m.group(1).strip()

        # Beschrijving
        desc_el = soup.select_one("div.text-2")
        if not desc_el:
            desc_el = soup.select_one("main") or soup.select_one("article")
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
