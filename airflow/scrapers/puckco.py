"""
Puck&Co scraper — puckenco.nl

Platform: Custom PHP/Apache (geen WordPress REST API).
Listing URL: https://www.puckenco.nl/werken-bij
Job URLs:    /werken-bij/{slug}

HTML structuur detailpagina (Tailwind CSS):
  Titel: h2 met class die "text-text-header" bevat (geen <h1>)
  Stad:  span.text-2xl.italic.text-text-p  → "{Locatienaam} - {Stad}" → split op " - "
  Uren:  div.text-2xl.text-text-header  (bijv. "24-32 uur uur" — dubbel uur is site-bug)
  Beschrijving: div.content
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from scrapers.base import SCRAPER_HEADERS
from scrapers.wordpress_jobs import WordPressJobsScraper, _parse_hours

logger = logging.getLogger(__name__)


class PuckcoScraper(WordPressJobsScraper):
    company_slug     = "puckco"
    company_name     = "Puck&Co"
    listing_url      = "https://www.puckenco.nl/werken-bij"
    website_url      = "https://www.puckenco.nl"
    job_url_contains = "/werken-bij/"

    def _scrape_job_page(self, url: str) -> dict | None:
        try:
            resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"[puckco] Detailpagina mislukt {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # Geen H1 — titel in H2 met Tailwind "text-text-header" class
        h2 = None
        for el in soup.find_all("h2"):
            cls = " ".join(el.get("class", []))
            if "text-text-header" in cls:
                h2 = el
                break
        title = h2.get_text(strip=True) if h2 else ""
        if not title:
            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else ""
        if not title:
            return None

        # Stad: span "Locatienaam - Stad" → laatste deel na " - "
        city = ""
        loc_span = soup.select_one("span.text-2xl.italic")
        if not loc_span:
            # Fallback: zoek span met italic klasse
            for span in soup.find_all("span"):
                cls = " ".join(span.get("class", []))
                if "italic" in cls and "text-2xl" in cls:
                    loc_span = span
                    break
        if loc_span:
            loc_text = loc_span.get_text(strip=True)
            if " - " in loc_text:
                city = loc_text.rsplit(" - ", 1)[-1].strip()
            else:
                city = loc_text

        # Uren: div met Tailwind "text-2xl text-text-header"
        hours_min = hours_max = None
        for div in soup.find_all("div"):
            cls = " ".join(div.get("class", []))
            if "text-2xl" in cls and "text-text-header" in cls:
                uren_text = div.get_text(strip=True)
                # Verwijder dubbele "uur uur" site-bug
                uren_clean = re.sub(r"\buur\s+uur\b", "uur", uren_text, flags=re.I)
                hours_min, hours_max = _parse_hours(uren_clean)
                if hours_min is not None:
                    break

        # Beschrijving
        desc_el = soup.select_one("div.content") or soup.select_one("main")
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
