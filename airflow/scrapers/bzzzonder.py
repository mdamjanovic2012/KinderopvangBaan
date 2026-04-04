"""
Bzzzonder Kinderopvang — https://www.werkenbijbzzzonder.nl

Detail pages use Avada/Fusion theme. Location name is in an h3/h4 that
contains "Bzzzonder" or "Kindercentrum" (separate from the job title).
"""
import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours
from scrapers.base import SCRAPER_HEADERS

logger = logging.getLogger(__name__)


class BzzzonderScraper(WordPressJobsScraper):
    company_slug     = "bzzzonder"
    company_name     = "Bzzzonder Kinderopvang"
    listing_url      = "https://www.werkenbijbzzzonder.nl/vacatures/"
    website_url      = "https://www.werkenbijbzzzonder.nl"
    job_url_contains = "/Vacatures/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[bzzzonder] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        # Location name: h3/h4 that starts with "Bzzzonder " followed by a location name.
        # Exclude questions, generic headings, and long sentences.
        location_name = ""
        for h in soup.find_all(["h3", "h4"]):
            t = h.get_text(strip=True)
            if (
                t
                and t != title
                and re.match(r"Bzzzonder\s+\w", t)
                and "?" not in t
                and len(t) < 60
                and not re.search(r"bzzzonderheden", t, re.I)
            ):
                location_name = t
                break

        main = soup.find("main")
        desc = main.get_text(separator="\n", strip=True)[:5000] if main else ""
        hours_min, hours_max = _parse_hours(desc)
        external_id = url.rstrip("/").split("/")[-1]

        return {
            "source_url":        url,
            "external_id":       external_id,
            "title":             title,
            "short_description": desc[:300],
            "description":       desc,
            "location_name":     location_name,
            "city":              "",
            "salary_min":        None,
            "salary_max":        None,
            "hours_min":         hours_min,
            "hours_max":         hours_max,
            "age_min":           None,
            "age_max":           None,
            "contract_type":     "",
            "job_type":          "",
        }
