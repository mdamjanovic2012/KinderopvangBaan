"""
Monter Kinderopvang scraper — monterkinderopvang.nl

Platform: WordPress + WP Job Openings plugin (AWSM).
Listing URL: https://monterkinderopvang.nl/vacatures-bij-monter-kinderopvang/
Job URLs:    /vacatures/{slug}/

AWSM plugin structuur detailpagina:
  Stad:  .awsm-job-specification-plaats .awsm-job-specification-term
  Uren:  .awsm-job-specification-aantal-uur .awsm-job-specification-term
         (bijv. "16 tot 32 uur" — "tot" wordt vervangen door "-")
  Beschrijving: .awsm-jobs-single-content
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)


class MonterScraper(WordPressJobsScraper):
    company_slug     = "monter"
    company_name     = "Monter Kinderopvang"
    listing_url      = "https://monterkinderopvang.nl/vacatures-bij-monter-kinderopvang/"
    website_url      = "https://monterkinderopvang.nl"
    job_url_contains = "/vacatures/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[monter] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        # Stad
        city = ""
        city_el = soup.select_one(
            ".awsm-job-specification-plaats .awsm-job-specification-term"
        )
        if city_el:
            city = city_el.get_text(strip=True)

        # Uren: "16 tot 32 uur" → normalize "tot" to "-"
        hours_min = hours_max = None
        uren_el = soup.select_one(
            ".awsm-job-specification-aantal-uur .awsm-job-specification-term"
        )
        if uren_el:
            uren_text = uren_el.get_text(strip=True)
            uren_norm = re.sub(r"\btot\b", "-", uren_text, flags=re.I)
            hours_min, hours_max = _parse_hours(uren_norm)

        # Beschrijving
        desc_el = (
            soup.select_one(".awsm-jobs-single-content")
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
